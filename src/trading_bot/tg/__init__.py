"""NOTIFICATION LAYER. Handles Telegram notifications.
REST or aiogram - choose one!?
"""

from .client import TelegramHandler, notify_telegram

__all__ = ["TelegramHandler", "notify_telegram"]
__version__ = "0.1.0"
__author__ = "Sergey Vorobiev"
__license__ = "MIT"
__url__ = "https://github.com/sergeyvuser/trading-bot"
__package__ = "trading_bot.tg"
