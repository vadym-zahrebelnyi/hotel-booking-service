import django_filters

from booking.models import Booking


class BookingFilter(django_filters.FilterSet):
    """
    Provides filtering capabilities for bookings based on dates,
    room type, user, room ID, and booking status.
    """

    from_date = django_filters.DateFilter(field_name="check_in_date", lookup_expr="gte")
    to_date = django_filters.DateFilter(field_name="check_out_date", lookup_expr="lte")

    room_type = django_filters.CharFilter(field_name="room__type", lookup_expr="iexact")

    class Meta:
        """Meta configuration for BookingFilter."""

        model = Booking
        fields = ["user", "room", "status"]
