"""NOTIFICATION LAYER. Handles Telegram notifications.
REST or aiogram - choose one!?
"""

import aiohttp
from loguru import logger

from trading_bot.config.settings import settings
from zapros import AsyncClient

from .client import TelegramHandler, notify_telegram

__all__ = ["TelegramHandler", "notify_telegram"]
__version__ = "0.1.0"
__author__ = "Your Name"
__license__ = "MIT"
__copyright__ = "2023 Your Name"
__doc__ = """
"""
__url__ = "https://github.com/yourusername/trading-bot"
__package__ = "trading_bot.tg"
__email__ = "your.email@example.com"


"""class TelegramHandler:
    def __init__(self):
        self.chat_id = settings.TELEGRAM_CHAT_ID
        self.bot_url = settings.tg_bot_url
        self._client: AsyncClient | None = None

    async def send_message(self, message: str):
        if not self.bot_url or not self.chat_id:
            return
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(
                    f"{self.bot_url}/sendMessage",
                    json={"chat_id": self.chat_id, "text": message},
                )
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")

    async def send_message2(self, chat_id: str, message: str):
        if not self.bot_url or not chat_id:
            logger.debug("Check TG settings")
            return
        try:
            async with AsyncClient() as self._client:
                await self._client.post(
                    f"{self.bot_url}/sendMessage",
                    json={"chat_id": chat_id, "text": message},
                )
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")

"""

