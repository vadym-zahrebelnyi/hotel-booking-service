import os

import requests
from celery import shared_task

from booking.models import Booking
from notifications.messages import (
    generate_no_show_message,
    generate_success_payment_message,
)
from payment.models import Payment


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 10},
)
def send_telegram_notification(self, message: str):
    """
    Send notification message to all subscribed Telegram admins
    """
    chat_id = os.getenv("CHAT_ID")
    if not chat_id:
        raise ValueError("CHAT_ID is missing")
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN is missing")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
    }

    response = requests.post(url, json=payload, timeout=5)
    response.raise_for_status()


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
