"""STRATEGY ENGINE. Consumes price ticks and evaluates the strategy.

Two clocks: indicators are refreshed on each closed candle (REST sync) and stored
as an IndicatorSnapshot; this loop fires on each price tick (WS), reads the latest
snapshot, and hands both to the strategy.

Ticks are coalesced: if several have queued up while the strategy was busy, only the
most recent price is evaluated and the intermediate ones are dropped (no lag).
"""

import asyncio

from loguru import logger

from trading_bot.models.market import SpotTickerDTO
from trading_bot.models.signals import SignalType
from trading_bot.storage.state import InMemoryState
from trading_bot.strategy.interfaces import IStrategy
from trading_bot.strategy.risk import RiskManager


class TradingEngine:
    def __init__(
        self,
        state: InMemoryState,
        strategy: IStrategy | None,
        risk_manager: RiskManager | None = None,
    ) -> None:
        self._state = state
        self._strategy = strategy
        self._risk_manager = risk_manager
        self._is_running = True
        self._symbol = strategy.symbol if strategy else None
        self._last_eval_price: float | None = None
        self._last_eval_snap_ts = None

    async def run_market_loop(self, ticker_queue: asyncio.Queue) -> None:
        if self._strategy is None:
            logger.warning("No strategy configured; trading engine idle.")
            return

        logger.info(f"Starting market loop for {self._symbol}...")
        while self._is_running:
            ticker, drained = await self._next_ticker(ticker_queue)
            try:
                price = ticker.last_price
                await self._state.set_last_price(self._symbol, price)

                snapshot = await self._state.get_indicator_snapshot(self._symbol)
                snap_ts = snapshot.timestamp if snapshot else None

                # Skip recompute when nothing relevant changed (same price and snapshot).
                if (
                    price == self._last_eval_price
                    and snap_ts == self._last_eval_snap_ts
                ):
                    continue
                self._last_eval_price = price
                self._last_eval_snap_ts = snap_ts

                signal = await self._strategy.on_tick(ticker, snapshot)
                if signal is None or signal.type is SignalType.HOLD:
                    continue
                logger.info(f"Signal: {signal.type.value} | {signal.reason}")

                if self._risk_manager is None:
                    continue
                intent = self._risk_manager.evaluate(signal, snapshot)
                if intent is not None:
                    logger.info(
                        f"OrderIntent: {intent.side} size={intent.size:.6f} "
                        f"stop={intent.stop_loss:.2f} | {intent.reason}"
                    )
            except Exception as e:
                logger.error(f"Error in trading loop: {e}", exc_info=True)
            finally:
                for _ in range(drained):
                    ticker_queue.task_done()

    @staticmethod
    async def _next_ticker(
        ticker_queue: asyncio.Queue,
    ) -> tuple[SpotTickerDTO, int]:
        """Block for one ticker, then drain any backlog and keep the latest.

        Returns the most recent ticker and the number of items taken off the queue
        (so the caller can balance ``task_done`` calls)."""
        ticker: SpotTickerDTO = await ticker_queue.get()
        count = 1
        while True:
            try:
                ticker = ticker_queue.get_nowait()
                count += 1
            except asyncio.QueueEmpty:
                break
        return ticker, count

    def stop(self) -> None:
        self._is_running = False
