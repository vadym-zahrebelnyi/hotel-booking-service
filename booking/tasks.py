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
    ).select_related("room", "user")
    marked_count = 0

    for booking in bookings:
        booking.status = Booking.BookingStatus.NO_SHOW
        booking.save(update_fields=["status"])
        marked_count += 1

        notify_no_show_telegram.delay(booking.id)

    return f"Marked {marked_count} bookings as NO_SHOW"


@shared_task
def notify_no_show_telegram(booking_id):
    """Send detailed notification to Telegram about NO_SHOW booking"""
    booking = Booking.objects.select_related('room', 'user').get(id=booking_id)
    return (
            f"⚠️ NO SHOW ALERT ⚠️\n"
            f"\n"
            f"📋 Booking ID: {booking.id}\n"
            f"🚪 Room: {booking.room.number} ({booking.room.type})\n"
            f"👤 Guest: {booking.user.first_name} {booking.user.last_name}\n"
            f"📧 Email: {booking.user.email}\n"
            f"📅 Check-in Date: {booking.check_in_date}\n"
            f"📅 Check-out Date: {booking.check_out_date}\n"
            f"💰 Price per night: ${booking.price_per_night}\n"
            f"📊 Status: {booking.status}\n"
            f"\n"
            f"⏰ Marked at: {localdate()}"
        )
