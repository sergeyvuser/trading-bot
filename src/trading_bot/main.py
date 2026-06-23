import asyncio

from loguru import logger

from trading_bot.bot import TradingBotPolars
from trading_bot.config import settings
from trading_bot.utils.logging import setup_logging


async def main() -> None:
    setup_logging()
    logger.info(
        f"Starting trading | symbol={settings.symbol} "
        f"category={settings.category} interval={settings.interval} "
        f"testnet={settings.TESTNET}"
    )

    bot = TradingBotPolars()
    await bot.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down…")
