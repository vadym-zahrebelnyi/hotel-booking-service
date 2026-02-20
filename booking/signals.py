from django.db.models.signals import post_save
from django.dispatch import receiver

from booking.models import Booking
from notifications.messages import (
    generate_booking_cancellation_message,
    generate_booking_creation_message,
)
from notifications.tasks import send_telegram_notification


@receiver(post_save, sender=Booking)
def booking_notification(sender, instance, created, **kwargs):
    """
    Send Telegram notifications when bookings are created or cancelled.

    Signal Handler: Triggered after any Booking instance is saved.

    Sends notifications to hotel staff via Telegram for monitoring and
    operational awareness of booking activities.
    """
    if created:
        send_telegram_notification.delay(generate_booking_creation_message(instance))
    else:
        if instance.status == "CANCELLED":
            send_telegram_notification.delay(
                generate_booking_cancellation_message(instance)
            )
