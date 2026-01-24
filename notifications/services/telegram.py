import asyncio
import logging
from aiogram import Bot
from aiogram.exceptions import (
    AiogramError,
    DetailedAiogramError,
    TelegramAPIError,
    TelegramRetryAfter,
    TelegramNetworkError,
)
from django.conf import settings


logger = logging.getLogger(__name__)


class TelegramNotificationService:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'bot'):
            token = settings.TELEGRAM_BOT_TOKEN
            if not token:
                logger.error("TELEGRAM_BOT_TOKEN is not set!")
                raise ValueError("TELEGRAM_BOT_TOKEN is missing!")
            self.bot = Bot(token=token)

    async def _send_message_async(self, chat_id: int, text: str):
        try:
            await self.bot.send_message(chat_id=chat_id, text=text)
            logger.info(f"Successfully sent message to chat_id {chat_id}")

        except TelegramRetryAfter as e:
            logger.warning(
                f"Rate limited for chat_id {chat_id}. Retrying in {e.retry_after} seconds."
            )
            raise e

        except TelegramNetworkError as e:
            logger.warning(f"Telegram network error for chat_id {chat_id}: {e}. Retrying.")
            raise e

        except TelegramAPIError as e:
            logger.error(f"Telegram API error for chat_id {chat_id}: {e}")
            pass

        except DetailedAiogramError as e:
            logger.error(f"Detailed Aiogram error for chat_id {chat_id}: {e}")
            pass

        except AiogramError as e:
            logger.error(f"General Aiogram error for chat_id {chat_id}: {e}")
            pass

        except Exception as e:
            logger.exception(f"Unexpected error when sending message to chat_id {chat_id}: {e}")
            raise e

    def send_sync(self, chat_id: int, text: str) -> None:
        try:
            asyncio.run(self._send_message_async(chat_id, text))
        except (TelegramRetryAfter, TelegramNetworkError, ValueError, Exception) as e:
            raise e

    async def close_bot_session(self):
        """Closes the aiohttp session associated with the bot."""
        if self.bot.session:
            await self.bot.session.close()
