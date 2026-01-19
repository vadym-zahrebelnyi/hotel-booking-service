from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from booking.models import Booking
from notifications.tasks import send_telegram_notification
from payment.models import Payment
from payment.services.payment_service import create_booking_payment


@shared_task
def create_stripe_payment_task(booking_id, payment_type):
    """
    Celery task to create a Stripe payment for a Booking.
    """
    try:
        booking = Booking.objects.get(id=booking_id)
    except Booking.DoesNotExist:
        return f"Booking {booking_id} does not exist"

    payment = create_booking_payment(booking, payment_type)
    return (
        f"Payment {payment.id} of type {payment_type} created for Booking {booking_id}"
    )


@shared_task
def expire_stripe_sessions():
    """
    Fallback task:
    Marks payments as EXPIRED if Stripe session
    was created more than 24 hours ago
    and payment is still PENDING.
    """
    expiration_threshold = timezone.now() - timedelta(minutes=1)

    expired_payments = Payment.objects.filter(
        status=Payment.PaymentStatus.PENDING,
        created_at__lte=expiration_threshold,
    )

    count = expired_payments.update(status=Payment.PaymentStatus.EXPIRED)

    return f"Expired {count} payments older than 24 hours"


@shared_task
def notify_successful_payment_telegram(booking_id):
    """Send detailed notification to Telegram about successful payment"""
    try:
        booking = Booking.objects.select_related("room", "user").get(id=booking_id)
        payment = booking.payments.filter(status=Payment.PaymentStatus.PAID).latest(
            "id"
        )
    except (Booking.DoesNotExist, Payment.DoesNotExist):
        return f"Could not find booking or payment for booking_id {booking_id}"

    message = (
        f"✅ Payment Successful\n"
        f"Booking ID: {booking.id}\n"
        f"User: {booking.user.email}\n"
        f"Room: {booking.room.number}\n"
        f"Check-in: {booking.check_in_date}\n"
        f"Check-out: {booking.check_out_date}\n"
        f"Amount Paid: ${payment.money_to_pay}"
    )
    send_telegram_notification.delay(message)
    return "Successfully triggered success notification."
