from django.db.models.signals import post_save
from django.dispatch import receiver

from booking.models import Booking
from notifications.services.telegram import send_message_to_all


@receiver(post_save, sender=Booking)
def notify_booking_created(sender, instance, created, **kwargs):
    if not created:
        return

    text = (
        f"New booking created!\n"
        f"Booking ID: {instance.id}\n"
        f"Room: {instance.room.id}"
    )

    send_message_to_all(text)