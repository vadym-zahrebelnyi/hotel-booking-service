from django.db import transaction
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiTypes,
    extend_schema,
)
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from booking.filters import BookingFilter
from booking.models import Booking
from booking.serializers import BookingCreateSerializer, BookingReadSerializer
from payment.models import Payment
from payment.services.payment_service import (
    calculate_payment_amount,
    renew_payment_session,
)
from payment.services.stripe_service import create_checkout_session
from payment.tasks import create_stripe_payment_task


class BookingViewSet(viewsets.ModelViewSet):
    serializer_class = BookingReadSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = BookingFilter

    def get_queryset(self):
        queryset = Booking.objects.select_related("room", "user")

        if self.request.user.is_staff:
            return queryset

        return queryset.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == "create":
            return BookingCreateSerializer
        return BookingReadSerializer

    def create(self, request, *args, **kwargs):
        """Create new booking with user auto-attachment and price from room."""
        has_pending_payment = Payment.objects.filter(
            booking__user=request.user,
            status=Payment.PaymentStatus.PENDING,
        ).exists()

        if has_pending_payment:
            raise ValidationError(
                "You cannot create a new booking while you have a pending payment."
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = serializer.save()

        response_serializer = BookingReadSerializer(booking)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="List bookings",
        description=(
            "Retrieve a list of bookings.\n\n"
            "- Regular users see only their own bookings.\n"
            "- Staff users see all bookings.\n"
            "- Supports filtering by user, room, status, date range and room type."
        ),
        parameters=[
            OpenApiParameter(
                name="user",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter by user ID (staff only)",
                required=False,
            ),
            OpenApiParameter(
                name="room",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter by room ID",
                required=False,
            ),
            OpenApiParameter(
                name="status",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Booking status (Booked, Active, Completed, Cancelled, No show)",
                required=False,
            ),
            OpenApiParameter(
                name="from_date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description="Filter bookings with check-in date from this date",
                required=False,
            ),
            OpenApiParameter(
                name="to_date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description="Filter bookings with check-out date to this date",
                required=False,
            ),
            OpenApiParameter(
                name="room_type",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter by room type (SINGLE, DOUBLE, SUITE)",
                required=False,
            ),
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(request=None)
    @action(detail=True, methods=["post"], url_path="check-in")
    def check_in(self, request, pk=None):
        booking = self.get_object()
        today = timezone.localdate()

        if booking.status not in (
            Booking.BookingStatus.BOOKED,
            Booking.BookingStatus.NO_SHOW,
        ):
            return Response(
                {"detail": "Check-in is allowed only for BOOKED or NO_SHOW bookings."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if today < booking.check_in_date:
            return Response(
                {"detail": "Too early to check in."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if today >= booking.check_out_date:
            return Response(
                {"detail": "Check-in is not possible after check-out date."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        payment_type = (
            Payment.PaymentType.NO_SHOW_FEE
            if booking.status == Booking.BookingStatus.NO_SHOW
            else Payment.PaymentType.BOOKING
        )

        payment, _ = Payment.objects.get_or_create(
            booking=booking,
            type=payment_type,
            status=Payment.PaymentStatus.PENDING,
            money_to_pay=calculate_payment_amount(booking, payment_type),
        )

        if not payment.session_id:
            session = create_checkout_session(
                amount=payment.money_to_pay,
                name=f"Booking #{booking.id}",
            )
            payment.session_id = session["id"]
            payment.session_url = session["url"]
            payment.save(update_fields=["session_id", "session_url"])

        return Response(BookingReadSerializer(booking).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        booking = self.get_object()
        today = timezone.localdate()

        if booking.status != Booking.BookingStatus.BOOKED:
            return Response(
                {"detail": "Only BOOKED bookings can be cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if today >= booking.check_in_date:
            return Response(
                {"detail": "Cancellation is allowed only before check-in date."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        hours_to_checkin = (booking.check_in_date - today).total_seconds() / 3600
        with transaction.atomic():
            if hours_to_checkin > 24:
                booking.status = Booking.BookingStatus.CANCELLED
                booking.save(update_fields=["status"])
            else:
                payment, _ = Payment.objects.get_or_create(
                    booking=booking,
                    type=Payment.PaymentType.CANCELLATION_FEE,
                    status=Payment.PaymentStatus.PENDING,
                    money_to_pay=calculate_payment_amount(
                        booking, Payment.PaymentType.CANCELLATION_FEE
                    ),
                )

                if not payment.session_id:
                    session = create_checkout_session(
                        amount=payment.money_to_pay,
                        name=f"Cancellation Fee for Booking #{booking.id}",
                    )
                    payment.session_id = session["id"]
                    payment.session_url = session["url"]
                    payment.save(update_fields=["session_id", "session_url"])

            return Response(
                BookingReadSerializer(booking).data,
                status=status.HTTP_200_OK,
            )

    @action(detail=True, methods=["post"], url_path="check-out")
    def check_out(self, request, pk=None):
        booking = self.get_object()

        if booking.status != Booking.BookingStatus.ACTIVE:
            return Response(
                {"detail": "Only ACTIVE bookings can be checked out."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            today = timezone.localdate()
            if today > booking.check_out_date:
                payment, _ = Payment.objects.get_or_create(
                    booking=booking,
                    type=Payment.PaymentType.OVERSTAY_FEE,
                    status=Payment.PaymentStatus.PENDING,
                    money_to_pay=calculate_payment_amount(
                        booking, Payment.PaymentType.OVERSTAY_FEE
                    ),
                )
                session = create_checkout_session(
                    amount=payment.money_to_pay,
                    name=f"Overstay fee for booking #{booking.id}",
                )
                payment.session_id = session["id"]
                payment.session_url = session["url"]
                payment.save(update_fields=["session_id", "session_url"])
            else:
                booking.status = Booking.BookingStatus.COMPLETED
                today = timezone.localdate()
                booking.actual_check_out_date = today
                booking.save(update_fields=["status", "actual_check_out_date"])
        expired_payments = booking.payments.filter(status=Payment.PaymentStatus.EXPIRED)

        renewed_payments = []
        for payment in expired_payments:
            renewed_payment = renew_payment_session(payment)
            renewed_payments.append(renewed_payment)

        response_data = BookingReadSerializer(booking).data

        if renewed_payments:
            response_data["renewed_payments"] = [
                {
                    "id": payment.id,
                    "session_url": payment.session_url,
                    "status": payment.status,
                }
                for payment in renewed_payments
            ]

        return Response(
            BookingReadSerializer(booking).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="no-show")
    def no_show(self, request, pk=None):
        booking = self.get_object()

        if booking.status != Booking.BookingStatus.BOOKED:
            return Response(
                {"detail": "Only BOOKED bookings can be marked as NO_SHOW."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            booking.status = Booking.BookingStatus.NO_SHOW
            booking.save(update_fields=["status"])

            if not booking.payments.filter(
                type=Payment.PaymentType.NO_SHOW_FEE
            ).exists():
                transaction.on_commit(
                    lambda: create_stripe_payment_task.delay(
                        booking.id,
                        Payment.PaymentType.NO_SHOW_FEE,
                    )
                )

        return Response(
            BookingReadSerializer(booking).data,
            status=status.HTTP_200_OK,
        )
