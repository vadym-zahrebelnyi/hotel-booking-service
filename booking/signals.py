from django.db.models.signals import post_save
from django.dispatch import receiver

from booking.models import Booking
from notifications.tasks import send_telegram_notification


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