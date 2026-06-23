"""STRATEGY ENGINE. Consumes price ticks and evaluates the strategy.

Two clocks: indicators are refreshed on each closed candle (REST sync) and stored
as an IndicatorSnapshot; this loop fires on each price tick (WS), reads the latest
snapshot, and hands both to the strategy.
"""

import asyncio

from loguru import logger

from trading_bot.models.market import SpotTickerDTO
from trading_bot.storage.state import InMemoryState
from trading_bot.strategy.interfaces import IStrategy


class TradingEngine:
    def __init__(self, state: InMemoryState, strategy: IStrategy | None) -> None:
        self._state = state
        self._strategy = strategy
        self._is_running = True
        self._symbol = strategy.symbol if strategy else None

    async def run_market_loop(self, ticker_queue: asyncio.Queue) -> None:
        if self._strategy is None:
            logger.warning("No strategy configured; trading engine idle.")
            return

        logger.info(f"Starting market loop for {self._symbol}...")
        while self._is_running:
            ticker: SpotTickerDTO = await ticker_queue.get()
            try:
                snapshot = await self._state.get_indicator_snapshot(self._symbol)
                await self._strategy.on_tick(ticker, snapshot)
            except Exception as e:
                logger.error(f"Error in trading loop: {e}", exc_info=True)
            finally:
                ticker_queue.task_done()

    def stop(self) -> None:
        self._is_running = False
