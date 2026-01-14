import os
import requests
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


def send_message_to_all(text: str) -> None:
    from notifications.models import TelegramSubscriber

    if not BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not found")

    subscribers = TelegramSubscriber.objects.all()

    for sub in subscribers:
        try:
            requests.post(
                f"{BASE_URL}/sendMessage",
                json={
                    "chat_id": sub.chat_id,
                    "text": text,
                },
                timeout=10,
            )
        except Exception as e:
            print(f"Failed to send to {sub.chat_id}: {e}")