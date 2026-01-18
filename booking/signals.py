import logging

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from booking.models import Booking
from notifications.tasks import send_telegram_notification
from payment.models import Payment
from payment.tasks import create_stripe_payment_task

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Booking)
def booking_notification(sender, instance, created, **kwargs):
    if created:
        message = (
            "🆕 New booking created\n"
            f"User: {instance.user.email}\n"
            f"Room: {instance.room.number}\n"
            f"Check-in: {instance.check_in_date}\n"
            f"Check-out: {instance.check_out_date}\n"
            f"Price per night: {instance.price_per_night}"
        )
        send_telegram_notification.delay(message)

    else:
        if instance.status == "Cancelled":
            message = (
                "❌ Booking Canceled\n"
                f"User: {instance.user.email}\n"
                f"Room: {instance.room.number}\n"
                f"Dates: {instance.check_in_date} - {instance.check_out_date}"
            )
            send_telegram_notification.delay(message)

        elif instance.status == "No show":
            message = (
                "⚠️ Guest No-show\n"
                f"User: {instance.user.email}\n"
                f"Room: {instance.room.number}\n"
                "Description: Guest did not check in on time."
            )
            send_telegram_notification.delay(message)


@receiver(post_save, sender=Booking)
def booking_payment_signal(sender, instance: Booking, created, **kwargs):
    """
    Handles creation of Stripe payments on booking events:
    - BOOKED -> BOOKING payment
    - COMPLETED -> booking payment + OVERSTAY_FEE if late checkout
    - NO_SHOW -> NO_SHOW_FEE payment
    - CANCELLED -> CANCELLATION_FEE if less than 24h to check-in
    """
    if created and instance.status == Booking.BookingStatus.BOOKED:
        transaction.on_commit(
            lambda: create_stripe_payment_task.delay(
                instance.id, Payment.PaymentType.BOOKING
            )
        )
        logger.info(f"Created BOOKING payment task for Booking {instance.id}")
        return

    if instance.status == Booking.BookingStatus.COMPLETED:
        has_booking_payment = instance.payments.filter(
            type=Payment.PaymentType.BOOKING
        ).exists()
        if not has_booking_payment:
            transaction.on_commit(
                lambda: create_stripe_payment_task.delay(
                    instance.id, Payment.PaymentType.BOOKING
                )
            )
            logger.info(f"Created COMPLETED payment task for Booking {instance.id}")

        if (
            instance.actual_check_out_date
            and instance.actual_check_out_date > instance.check_out_date
        ):
            has_overstay = instance.payments.filter(
                type=Payment.PaymentType.OVERSTAY_FEE
            ).exists()
            if not has_overstay:
                transaction.on_commit(
                    lambda: create_stripe_payment_task.delay(
                        instance.id, Payment.PaymentType.OVERSTAY_FEE
                    )
                )
                logger.info(
                    f"Created OVERSTAY_FEE payment task for Booking {instance.id}"
                )

    elif instance.status == Booking.BookingStatus.NO_SHOW:
        has_no_show = instance.payments.filter(
            type=Payment.PaymentType.NO_SHOW_FEE
        ).exists()
        if not has_no_show:
            transaction.on_commit(
                lambda: create_stripe_payment_task.delay(
                    instance.id, Payment.PaymentType.NO_SHOW_FEE
                )
            )
            logger.info(f"Created NO_SHOW_FEE payment task for Booking {instance.id}")

    elif instance.status == Booking.BookingStatus.CANCELLED:
        has_cancel_fee = instance.payments.filter(
            type=Payment.PaymentType.CANCELLATION_FEE
        ).exists()
        hours_to_checkin = (
            instance.check_in_date - timezone.now().date()
        ).total_seconds() / 3600
        if not has_cancel_fee and hours_to_checkin < 24:
            transaction.on_commit(
                lambda: create_stripe_payment_task.delay(
                    instance.id, Payment.PaymentType.CANCELLATION_FEE
                )
            )
            logger.info(
                f"Created CANCELLATION_FEE payment task for Booking {instance.id}"
            )
