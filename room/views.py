from datetime import timedelta

from django.utils.dateparse import parse_date
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from booking.models import Booking
from room.models import Room
from room.permissions import IsAdminOrReadOnly
from room.serializers import RoomCalendarSerializer, RoomSerializer
from room.validators import validate_calendar_request


@extend_schema(tags=["Rooms"])
class RoomViewSet(ModelViewSet):
    """
    ViewSet for managing rooms.

    Supports listing, retrieving, creating, updating rooms
    and retrieving room availability calendar.
    """

    queryset = Room.objects.all().order_by("id")
    serializer_class = RoomSerializer
    permission_classes = (IsAdminOrReadOnly,)

    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ("type", "capacity")

    def get_serializer_class(self):
        """Return serializer class depending on the current action."""

        if self.action == "calendar":
            return RoomCalendarSerializer
        return RoomSerializer

    @extend_schema(
        request=None,
        parameters=[
            OpenApiParameter(
                name="date_from",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description="Початкова дата (YYYY-MM-DD)",
                required=True,
            ),
            OpenApiParameter(
                name="date_to",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description="Кінцева дата (YYYY-MM-DD)",
                required=True,
            ),
        ],
        responses={
            200: RoomCalendarSerializer(many=True),
            400: {
                "description": "Bad Request",
                "examples": [
                    {"detail": "date_from and date_to are required"},
                    {"detail": "date_from must be before date_to"},
                ],
            },
        },
        description=(
            "Get room availability calendar for a given date range.\n\n"
            "Only bookings with status BOOKED or ACTIVE are considered as occupying dates. "
            "Availability is calculated per day."
        ),
    )
    @action(methods=["GET"], detail=True, url_path="calendar", filter_backends=[])
    def get_calendar(self, request, pk=None):
        """
        Return room availability calendar for a given date range.

        Dates between date_from and date_to (inclusive) are returned
        with availability status.
        """

        room = self.get_object()

        date_from_str = request.query_params.get("date_from")
        date_to_str = request.query_params.get("date_to")

        date_from = parse_date(date_from_str) if date_from_str else None
        date_to = parse_date(date_to_str) if date_to_str else None

        validate_calendar_request(date_from_str,date_to_str, date_from, date_to)

        bookings = Booking.objects.filter(
            room=room,
            status__in=[Booking.BookingStatus.BOOKED, Booking.BookingStatus.ACTIVE],
            check_in_date__lt=date_to + timedelta(days=1),
            check_out_date__gt=date_from,
        )

        booked_dates = set()
        for booking in bookings:
            current = booking.check_in_date
            while current < booking.check_out_date:
                booked_dates.add(current)
                current += timedelta(days=1)

        calendar = []
        current_date = date_from
        while current_date <= date_to:
            calendar.append(
                {
                    "date": current_date,
                    "available": current_date not in booked_dates,
                }
            )
            current_date += timedelta(days=1)

        serializer = RoomCalendarSerializer(calendar, many=True)
        return Response(serializer.data)
