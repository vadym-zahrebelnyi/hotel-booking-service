from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from booking.models import Booking
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
