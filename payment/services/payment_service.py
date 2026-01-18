from decimal import Decimal

from payment.models import Payment
from payment.services.stripe_service import create_checkout_session


def calculate_payment_amount(booking, event) -> Decimal | None:
    nights = (booking.check_out_date - booking.check_in_date).days
    price = booking.price_per_night * nights

    if event == Payment.PaymentType.CANCELLATION_FEE:
        return price * Decimal("0.5")
    elif event == Payment.PaymentType.OVERSTAY_FEE:
        overstay_days = max(
            (booking.actual_check_out_date - booking.check_out_date).days, 0
        )
        return overstay_days * booking.price_per_night * Decimal("1.5")
    elif event == Payment.PaymentType.NO_SHOW_FEE:
        return price * Decimal("1.2")

    return price


def create_booking_payment(booking, event):
    amount = calculate_payment_amount(booking, event)

    stripe_session = create_checkout_session(
        amount=amount, name=f"{event} payment for Booking {booking.id}"
    )

    payment = Payment.objects.create(
        booking=booking,
        type=event,
        status=Payment.PaymentStatus.PENDING,
        money_to_pay=amount,
        session_id=stripe_session.id,
        session_url=stripe_session.url,
    )

    return payment
