"""APPLICATION LAYER (BOT Orchestrator)."""

import asyncio

from loguru import logger

from trading_bot.bot.sync_service import MarketDataSyncService
from trading_bot.config import settings
from trading_bot.exchange import BybitRestClient, BybitWSClient
from trading_bot.storage import BybitMarketRepository, InMemoryState
from trading_bot.strategy.engine import TradingEngine
from trading_bot.strategy.indicators import IndicatorEngine
from trading_bot.strategy.models import IndicatorConfig
from trading_bot.strategy.registry import make_strategy
from trading_bot.tg import TelegramHandler


def _merge_indicators(
    *sources: list[IndicatorConfig],
) -> list[IndicatorConfig]:
    """Merge indicator configs from several sources, de-duplicating by name+params."""
    merged: list[IndicatorConfig] = []
    seen: set[tuple] = set()
    for source in sources:
        for cfg in source:
            key = (cfg.name, tuple(sorted(cfg.params.items())))
            if key not in seen:
                seen.add(key)
                merged.append(cfg)
    return merged


class TradingBotPolars:
    def __init__(self):
        self.state = InMemoryState()
        self.ticker_queue: asyncio.Queue = asyncio.Queue()
        self.strategy = make_strategy(
            name=settings.strategy.name,
            symbol=settings.symbol,
            params=settings.strategy.params,
        )

    async def start(self) -> None:
        logger.info(
            f"Starting trading bot container for {settings.symbol} "
            f"(strategy={self.strategy.name})..."
        )

        rest_client = BybitRestClient(base_url=settings.resolved_rest_url)
        market_repo = BybitMarketRepository(state=self.state, rest_client=rest_client)

        # Indicators: profile base + whatever the strategy needs (hybrid), de-duplicated.
        indicators = _merge_indicators(
            settings.indicators, self.strategy.required_indicators()
        )
        indicator_engine = IndicatorEngine(indicators=indicators)

        sync_service = MarketDataSyncService(
            market_repo=market_repo,
            state=self.state,
            symbol=settings.symbol,
            interval=settings.interval,
            limit=settings.market_kline_api.limit,
            category=settings.category,
            indicator_engine=indicator_engine,
        )

        ws_client = BybitWSClient(
            ws_url=settings.resolved_public_ws_url,
            symbol=settings.symbol,
            interval=settings.interval,
            orderbook_depth=settings.orderbook_depth,
            reconnect_delay=settings.ws_core_config.reconnect_delay,
            ping_interval=settings.ws_core_config.ping_interval,
        )

        engine = TradingEngine(state=self.state, strategy=self.strategy)
        tg_bot = TelegramHandler(tg_bot_url=settings.tg_bot_url)

        logger.info("All components initialized successfully.")

        async with asyncio.TaskGroup() as tg:
            tg.create_task(
                sync_service.start_sync_loop(rest_path=settings.market_kline_api.path)
            )
            tg.create_task(ws_client.listen(ticker_queue=self.ticker_queue))
            tg.create_task(engine.run_market_loop(ticker_queue=self.ticker_queue))
            tg.create_task(
                tg_bot.send_message(
                    chat_id=settings.TELEGRAM_CHAT_ID,
                    message=(
                        f"🚀 Trading bot started\n"
                        f"symbol={settings.symbol} testnet={settings.TESTNET}"
                    ),
                )
            )
