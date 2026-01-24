from django.utils import timezone
from rest_framework.exceptions import ValidationError

from booking.models import Booking
from payment.models import Payment


def validate_user_has_no_pending_payments(user):
    """
    Validate that user doesn't have any pending payments.
    """
    has_pending_payment = Payment.objects.filter(
        booking__user=user,
        status=Payment.PaymentStatus.PENDING,
    ).exists()

    if has_pending_payment:
        raise ValidationError(
            "You cannot create a new booking while you have a pending payment."
        )


def validate_booking_can_check_in(booking):
    """Validate that booking can be checked in."""
    today = timezone.localdate()

    if booking.status not in (
        Booking.BookingStatus.BOOKED,
        Booking.BookingStatus.NO_SHOW,
    ):
        raise ValidationError(
            "Check-in is allowed only for BOOKED or NO_SHOW bookings."
        )

    if today < booking.check_in_date:
        raise ValidationError("Too early to check in.")

    if today >= booking.check_out_date:
        raise ValidationError("Check-in is not possible after check-out date.")


def validate_booking_can_cancel(booking):
    """Validate that booking can be cancelled."""
    today = timezone.localdate()

    if booking.status != Booking.BookingStatus.BOOKED:
        raise ValidationError("Only BOOKED bookings can be cancelled.")

    if today >= booking.check_in_date:
        raise ValidationError("Cancellation is allowed only before check-in date.")


def validate_booking_can_check_out(booking):
    """Validate that booking can be checked out."""
    if booking.status != Booking.BookingStatus.ACTIVE:
        raise ValidationError("Only ACTIVE bookings can be checked out.")


def calculate_hours_to_checkin(booking):
    """
    Calculate hours remaining until check-in.
    """
    today = timezone.localdate()
    return (booking.check_in_date - today).total_seconds() / 3600


def is_late_cancellation(booking, hours_threshold=24):
    """
    Check if cancellation is considered "late" (within threshold of check-in).
    """
    hours_to_checkin = calculate_hours_to_checkin(booking)
    return hours_to_checkin <= hours_threshold


def is_overstay(booking, checkout_date):
    """
    Check if checkout date indicates an overstay.
    """
    return checkout_date > booking.check_out_date
