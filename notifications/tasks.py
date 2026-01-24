import os

from celery import shared_task
from django.conf import settings # Import settings to get TELEGRAM_CHAT_ID

from booking.models import Booking
from notifications.messages import (
    generate_no_show_message,
    generate_success_payment_message,
)
from notifications.services.telegram import TelegramNotificationService
from payment.models import Payment

from aiogram.exceptions import TelegramRetryAfter, TelegramNetworkError

telegram_notification_service = TelegramNotificationService()


@shared_task(
    bind=True,
    autoretry_for=(TelegramRetryAfter, TelegramNetworkError, ValueError, Exception,),
    retry_kwargs={"max_retries": 5, "countdown": 30},
)
def send_telegram_notification(self, message: str):
    """
    Sends notification message to a specific Telegram chat.
    """
    chat_id = settings.CHAT_ID
    if not chat_id:
        raise self.retry(exc=ValueError("CHAT_ID is missing in settings."))

    try:
        telegram_notification_service.send_sync(
            chat_id=int(chat_id),
            text=message,
        )
    except (TelegramRetryAfter, TelegramNetworkError, ValueError) as e:
        self.request.logger.warning(f"Caught retryable error: {e}. Retrying task...")
        raise self.retry(exc=e)
    except Exception as e:
        self.request.logger.exception(
            f"Unexpected error in send_telegram_notification task: {e}"
        )
        raise


@shared_task
def notify_no_show_telegram(booking_id):
    """Send detailed notification to Telegram about NO_SHOW booking"""
    booking = Booking.objects.select_related("room", "user").get(id=booking_id)
    send_telegram_notification.delay(generate_no_show_message(booking))


@shared_task
def notify_successful_payment_telegram(booking_id):
    """Send detailed notification to Telegram about successful payment"""
    try:
        booking = Booking.objects.select_related("room", "user").get(id=booking_id)
        payment = booking.payments.filter(status=Payment.PaymentStatus.PAID).latest(
            "id"
        )
    except (Booking.DoesNotExist, Payment.DoesNotExist):
        return f"Could not find booking or payment for booking_id {booking_id}"

    send_telegram_notification.delay(generate_success_payment_message(booking, payment))
    return "Successfully triggered success notification."
