from datetime import timedelta

from celery import shared_task
from django.utils import timezone
from django.utils.timezone import localdate

from booking.models import Booking
from notifications.tasks import send_telegram_notification
from payment.models import Payment


@shared_task
def mark_no_show_bookings():
    """Mark bookings as NO_SHOW if check-in date passed and status still BOOKED"""
    today = localdate()

    bookings = Booking.objects.filter(
        status=Booking.BookingStatus.BOOKED, check_in_date__lt=today
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
    booking = Booking.objects.select_related("room", "user").get(id=booking_id)
    message = (
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
    send_telegram_notification.delay(message)

@shared_task
def expire_stripe_sessions():
    expiration_threshold = timezone.now() - timedelta(hours=24)

    expired_payments = Payment.objects.filter(
        status=Payment.PaymentStatus.PENDING,
        created_at__lte=expiration_threshold,
    )

    count = expired_payments.update(
        status=Payment.PaymentStatus.EXPIRED
    )

    return f"Expired {count} payments older than 24 hours"
