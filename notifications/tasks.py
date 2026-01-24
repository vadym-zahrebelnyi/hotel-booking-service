from aiogram.exceptions import TelegramNetworkError, TelegramRetryAfter
from celery import shared_task
from django.conf import settings

from booking.models import Booking
from notifications.messages import (
    generate_no_show_message,
    generate_success_payment_message,
)
from notifications.services.telegram import TelegramNotificationService
from payment.models import Payment

telegram_notification_service = TelegramNotificationService()


@shared_task(
    bind=True,
    autoretry_for=(TelegramRetryAfter, TelegramNetworkError),
    retry_kwargs={"max_retries": 5, "countdown": 30},
)
def send_telegram_notification(self, message: str) -> None:
    """
    Sends notification message to a specific Telegram chat.
    """
    chat_id = settings.CHAT_ID
    if not chat_id:
        raise ValueError("CHAT_ID is missing in settings.")

    try:
        telegram_notification_service.send_sync(
            chat_id=int(chat_id),
            text=message,
        )

    except (TelegramRetryAfter, TelegramNetworkError) as e:
        self.request.logger.warning(
            "Retryable Telegram error: %s. Retrying task...",
            e,
        )
        raise self.retry(exc=e) from e

    except Exception:
        self.request.logger.exception(
            "Unexpected error in send_telegram_notification task"
        )
        raise


@shared_task
def notify_no_show_telegram(booking_id: int):
    booking = Booking.objects.select_related("room", "user").get(id=booking_id)
    send_telegram_notification.delay(generate_no_show_message(booking))


@shared_task
def notify_successful_payment_telegram(booking_id: int):
    try:
        booking = Booking.objects.select_related("room", "user").get(id=booking_id)
        payment = booking.payments.filter(status=Payment.PaymentStatus.PAID).latest(
            "id"
        )

    except (Booking.DoesNotExist, Payment.DoesNotExist):
        return f"Could not find booking or payment for booking_id {booking_id}"

    send_telegram_notification.delay(generate_success_payment_message(booking, payment))
    return "Successfully triggered success notification."
