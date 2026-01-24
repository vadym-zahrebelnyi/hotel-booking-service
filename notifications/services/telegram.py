import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import (
    AiogramError,
    DetailedAiogramError,
    TelegramAPIError,
)
from django.conf import settings

logger = logging.getLogger(__name__)

bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)


async def send_telegram_message(chat_id: int, text: str) -> None:
    try:
        await bot.send_message(chat_id=chat_id, text=text)

    except TelegramAPIError as e:
        logger.error(f"Telegram API error: {e}")

    except DetailedAiogramError as e:
        logger.error(f"Detailed aiogram error: {e}")

    except AiogramError as e:
        logger.error(f"Aiogram error: {e}")


def send_telegram_message_sync(chat_id: int, text: str) -> None:
    asyncio.run(send_telegram_message(chat_id, text))
