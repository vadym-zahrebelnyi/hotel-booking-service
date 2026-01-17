from django.urls import reverse
from datetime import datetime, time, timedelta
from django.utils import timezone
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets, status
from rest_framework.response import Response
from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiTypes,
)
from rest_framework_simplejwt.authentication import JWTAuthentication

from booking.filters import BookingFilter
from booking.models import Booking
from booking.serializers import (
    BookingReadSerializer,
    BookingCreateSerializer
)
from payment.services.payment_service import create_booking_payment
from payment.services.stripe_service import create_checkout_session


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
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = serializer.save()

        # payment = create_booking_payment(booking)
        #
        # if payment:
        #     success_url = request.build_absolute_uri(
        #         reverse("payments:success")
        #     )
        #     cancel_url = request.build_absolute_uri(
        #         reverse("payments:cancel")
        #     )
        #
        #     create_checkout_session(
        #         payment=payment,
        #         success_url=success_url,
        #         cancel_url=cancel_url,
        #     )

        response_serializer = BookingReadSerializer(booking)
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED
        )

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

    @action(detail=True, methods=["post"], url_path="check-in")
    def check_in(self, request, pk=None):
        booking = self.get_object()
        today = timezone.localdate()

        if booking.status != Booking.BookingStatus.BOOKED:
            return Response(
                {"detail": "Only BOOKED bookings can be checked in."},
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

        booking.status = Booking.BookingStatus.ACTIVE
        booking.save(update_fields=["status"])

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

        # only before check-in date
        if today >= booking.check_in_date:
            return Response(
                {"detail": "Cancellation is allowed only before check-in date."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # hook: cancellation fee if <24h before check-in
        # (поки Payment Service немає у нас — просто TODO)
        check_in_dt = timezone.make_aware(
            datetime.combine(booking.check_in_date, time.min)
        )
        if timezone.now() >= check_in_dt - timedelta(hours=24):
            # TODO: create CANCELLATION_FEE payment when Payment Service is implemented
            pass

        booking.status = Booking.BookingStatus.CANCELLED
        booking.save(update_fields=["status"])

        return Response(BookingReadSerializer(booking).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="check-out")
    def check_out(self, request, pk=None):
        booking = self.get_object()
        today = timezone.localdate()

        if booking.status != Booking.BookingStatus.ACTIVE:
            return Response(
                {"detail": "Only ACTIVE bookings can be checked out."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        booking.status = Booking.BookingStatus.COMPLETED
        booking.actual_check_out_date = today
        booking.save(update_fields=["status", "actual_check_out_date"])

        # TODO: create main Payment when Payment Service is implemented

        # late checkout hook
        if today > booking.check_out_date:
            # TODO: create OVERSTAY_FEE Payment when Payment Service is implemented
            pass

        return Response(BookingReadSerializer(booking).data, status=status.HTTP_200_OK)