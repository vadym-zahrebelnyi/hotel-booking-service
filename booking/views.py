from django.db import transaction
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
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
from booking.validators import validate_user_has_no_pending_payments, validate_booking_can_check_in, \
    validate_booking_can_cancel, is_late_cancellation, validate_booking_can_check_out, is_overstay
from payment.models import Payment
from payment.services.payment_service import (
    calculate_payment_amount,
    renew_payment_session,
)
from payment.services.stripe_service import create_checkout_session


class BookingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing hotel bookings.
    Provides CRUD operations for bookings with role-based access control,
    filtering capabilities, and custom actions for booking lifecycle management.
    """
    serializer_class = BookingReadSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = BookingFilter

    def get_queryset(self):
        """Get queryset of bookings based on user permissions."""
        queryset = Booking.objects.select_related("room", "user")

        if self.request.user.is_staff:
            return queryset

        return queryset.filter(user=self.request.user)

    def get_serializer_class(self):
        """Return appropriate serializer class based on action."""
        if self.action == "create":
            return BookingCreateSerializer
        return BookingReadSerializer

    @extend_schema(
        request=BookingCreateSerializer,
        responses={
            201: BookingReadSerializer,
            400: OpenApiResponse(
                description="Validation error or user has pending payment"
            ),
            401: OpenApiResponse(
                description="Authentication credentials were not provided or are invalid"
            ),
        },
        summary="Create booking",
        description=(
                "Create a new hotel room booking."
        ),
    )
    def create(self, request, *args, **kwargs):
        """
        Create a new booking.
        Validates that the user doesn't have any pending payments before
        allowing a new booking creation.
        """
        validate_user_has_no_pending_payments(request.user)
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
        """List bookings with optional filtering."""
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Retrieve booking",
        description=(
                "Retrieve detailed information about a specific booking."
        ),
        responses={
            200: BookingReadSerializer,
            401: OpenApiResponse(
                description="Authentication credentials were not provided or are invalid"
            ),
            404: OpenApiResponse(
                description="Booking not found or user doesn't have permission to view it"
            ),
        },
    )
    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a single booking by ID.
        """
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        request=None,
        summary="Check in",
        description=("Performs check in"),
        responses={
            200: BookingReadSerializer,
            400: OpenApiResponse(description="Business logic validation error"),
            401: OpenApiResponse(
                description="Authentication credentials were not provided or are invalid"
            ),
            404: OpenApiResponse(description="Booking not found"),
        },
    )
    @action(detail=True, methods=["post"], url_path="check-in")
    def check_in(self, request, pk=None):
        """
        Check in to a booking.

        Transitions booking status to ACTIVE and ensures payment session exists.
        Can recover NO_SHOW bookings by checking them in.
        """
        booking = self.get_object()
        validate_booking_can_check_in(booking)
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

    @extend_schema(
        request=None,
        summary="Cancel",
        description=("Performs cancellation of booking"),
        responses={
            200: BookingReadSerializer,
            400: OpenApiResponse(description="Business logic validation error"),
            401: OpenApiResponse(
                description="Authentication credentials were not provided or are invalid"
            ),
            404: OpenApiResponse(description="Booking not found"),
        },
    )
    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        """
        Cancel a booking.
        Cancels the booking and applies cancellation fee
        if within 24 hours of check-in.
        """
        booking = self.get_object()
        validate_booking_can_cancel(booking)
        with transaction.atomic():
            if not is_late_cancellation(booking) > 24:
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

    @extend_schema(
        request=None,
        summary="Check out",
        description=("Performs check out from room"),
        responses={
            200: BookingReadSerializer,
            400: OpenApiResponse(description="Business logic validation error"),
            401: OpenApiResponse(
                description="Authentication credentials were not provided or are invalid"
            ),
            404: OpenApiResponse(description="Booking not found"),
        },
    )
    @action(detail=True, methods=["post"], url_path="check-out")
    def check_out(self, request, pk=None):
        """
        Check out from a booking.

        Completes the booking and handles overstay fees if applicable.
        Automatically renews expired payment sessions.
        """
        booking = self.get_object()

        validate_booking_can_check_out(booking)

        with transaction.atomic():
            today = timezone.localdate()
            if is_overstay(booking, today):
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
