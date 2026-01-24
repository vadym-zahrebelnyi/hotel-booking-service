import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import (
    AiogramError,
    DetailedAiogramError,
    TelegramAPIError,
    TelegramNetworkError,
    TelegramRetryAfter,
)
from django.conf import settings

logger = logging.getLogger(__name__)


class TelegramNotificationService:
    def __init__(self):
        token = settings.TELEGRAM_BOT_TOKEN
        if not token:
            logger.error("TELEGRAM_BOT_TOKEN is not set!")
            raise ValueError("TELEGRAM_BOT_TOKEN is missing!")

        self.bot = Bot(token=token, timeout=10)

    async def _send_message_async(self, chat_id: int, text: str) -> None:
        try:
            text = text[:4000]

            await self.bot.send_message(chat_id=chat_id, text=text)
            logger.info("Successfully sent message to chat_id=%s", chat_id)

        except TelegramRetryAfter as e:
            logger.warning(
                "Rate limited for chat_id=%s, retry after %s seconds",
                chat_id,
                e.retry_after,
            )
            raise

        except TelegramNetworkError:
            logger.warning("Telegram network error for chat_id=%s", chat_id)
            raise

        except TelegramAPIError as e:
            logger.error("Telegram API error for chat_id=%s: %s", chat_id, e)
            raise

        except DetailedAiogramError as e:
            logger.error("Detailed aiogram error for chat_id=%s: %s", chat_id, e)
            raise

        except AiogramError as e:
            logger.error("General aiogram error for chat_id=%s: %s", chat_id, e)
            raise

        except Exception:
            logger.exception(
                "Unexpected error when sending message to chat_id=%s",
                chat_id,
            )
            raise

    def send_sync(self, chat_id: int, text: str) -> None:
        asyncio.run(self._send_message_async(chat_id, text))

    async def close_bot_session(self) -> None:
        if self.bot.session:
            await self.bot.session.close()
