import os

import requests
from celery import shared_task

from notifications.models import TelegramSubscriber


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
    # subscribers = TelegramSubscriber.objects.all()

    # for subscriber in subscribers:
    #     payload = {
    #         "chat_id": subscriber.chat_id,
    #         "text": message,
    #     }
    #
    #     response = requests.post(url, json=payload, timeout=5)
    #     response.raise_for_status()
