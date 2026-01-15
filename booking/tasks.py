from celery import shared_task
from django.utils.timezone import localdate
from booking.models import Booking


@shared_task
def mark_no_show_bookings():
    """Mark bookings as NO_SHOW if check-in date passed and status still BOOKED"""
    today = localdate()

    bookings = Booking.objects.filter(
        status=Booking.BookingStatus.BOOKED,
        check_in_date__lt=today
    )
    marked_count = 0

    for booking in bookings:
        booking.status = Booking.BookingStatus.NO_SHOW
        booking.save(update_fields=["status"])
        marked_count += 1

        notify_no_show_telegram.delay(booking.id)

    return f"Marked {marked_count} bookings as NO_SHOW"


@shared_task
def notify_no_show_telegram(booking_id):
    """Send notification to Telegram (stub for now)"""
    pass
