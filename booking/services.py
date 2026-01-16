from django.utils import timezone
from booking.models import Booking


def mark_no_show_bookings() -> int:
    today = timezone.localdate()

    return Booking.objects.filter(
        status=Booking.BookingStatus.BOOKED,
        check_in_date__lt=today,
    ).update(status=Booking.BookingStatus.NO_SHOW)
