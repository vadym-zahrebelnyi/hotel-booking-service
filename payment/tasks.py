from celery import shared_task

from booking.models import Booking
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
