import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from payment.models import Payment
from payment.tasks import notify_successful_payment_telegram

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Payment)
def payment_notification(sender, instance, created, **kwargs):
    """
    Sends a Telegram notification when a payment status changes to PAID.
    We check `not created` to ensure this only runs on updates from the webhook.
    """
    if not created and instance.status == Payment.PaymentStatus.PAID:
        logger.info(
            f"Payment {instance.id} for Booking {instance.booking.id} status changed to PAID. Notifying..."
        )
        notify_successful_payment_telegram.delay(instance.booking.id)
