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
