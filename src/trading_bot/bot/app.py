"""APPLICATION LAYER (BOT Orchestrator)."""

import asyncio

from loguru import logger

from trading_bot.bot.sync_service import MarketDataSyncService
from trading_bot.config import settings
from trading_bot.exchange import BybitRestClient
from trading_bot.storage import BybitMarketRepository, InMemoryState
from trading_bot.strategy.engine import TradingEngine
from trading_bot.strategy.indicators import IndicatorEngine
from trading_bot.strategy.interfaces import IStrategy
from trading_bot.tg import TelegramHandler


class TradingBotPolars:
    def __init__(self):
        self.state = InMemoryState()
        self.ticker_queue: asyncio.Queue = asyncio.Queue()
        self.strategy: IStrategy | None = None

    async def start(self) -> None:
        logger.info(f"Starting trading bot container for symbol {settings.symbol}...")

        rest_client = BybitRestClient(base_url=settings.base_api_url)
        market_repo = BybitMarketRepository(state=self.state, rest_client=rest_client)
        indicator_engine = IndicatorEngine(indicators=settings.indicators)

        sync_service = MarketDataSyncService(
            market_repo=market_repo,
            state=self.state,
            symbol=settings.symbol,
            interval=settings.interval,
            limit=settings.market_kline_api.limit,
            category=settings.category,
            indicator_engine=indicator_engine,
        )

        # Strategy execution loop (WS price ticks) — wired in stage 2.
        engine = TradingEngine(state=self.state, strategy=self.strategy)  # noqa: F841

        tg_bot = TelegramHandler(tg_bot_url=settings.tg_bot_url)

        logger.info("All components initialized successfully.")

        async with asyncio.TaskGroup() as tg:
            tg.create_task(
                sync_service.start_sync_loop(rest_path=settings.market_kline_api.path)
            )
            tg.create_task(
                tg_bot.send_message(
                    chat_id=settings.TELEGRAM_CHAT_ID,
                    message=(
                        f"🚀 Trading bot started\n"
                        f"symbol={settings.symbol} testnet={settings.TESTNET}"
                    ),
                )
            )
