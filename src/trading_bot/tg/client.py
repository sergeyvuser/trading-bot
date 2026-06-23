from loguru import logger
from trading_bot.config.settings import settings
from zapros import AsyncClient


class TelegramHandler:
    def __init__(self, tg_bot_url: str | None):
        self.tg_bot_url = tg_bot_url

    async def send_message(self, chat_id: str, message: str):
        if not self.tg_bot_url or not chat_id:
            logger.debug("Check TG settings: tg_bot_url or chat_id is missing")
            return

        try:
            async with AsyncClient() as client:
                response = await client.post(
                    f"{self.tg_bot_url}/sendMessage",
                    json={"chat_id": chat_id, "text": message},
                )

                if response.status != 200:
                    logger.error(f"Telegram API error {response.status}: {response.text}")

        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")


async def notify_telegram(telegram_handler: TelegramHandler, message: str):
    if telegram_handler:
        await telegram_handler.send_message(chat_id=settings.TELEGRAM_CHAT_ID, message=message)