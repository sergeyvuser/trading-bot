import asyncio
from datetime import UTC, datetime

from loguru import logger

from trading_bot.storage.state import InMemoryState
from trading_bot.strategy.indicators import IndicatorEngine
from trading_bot.strategy.interfaces import IMarketRepository
from trading_bot.utils.time import interval_timedelta


class MarketDataSyncService:
    def __init__(
        self,
        market_repo: IMarketRepository,
        state: InMemoryState,
        symbol: str,
        interval: str,
        limit: str,
        category: str,
        indicator_engine: IndicatorEngine,
    ):
        self._market_repo = market_repo
        self._state = state
        self._symbol = symbol
        self._interval = interval
        self._limit = limit
        self._category = category
        self._indicator_engine = indicator_engine
        self._interval_delta = interval_timedelta(self._interval)
        # Technical delay between syncs to avoid Bybit cache not updating
        self._delay_seconds = 2.0

    async def start_sync_loop(self, rest_path: str) -> None:
        logger.info(
            f"Starting market data sync loop for {self._symbol}.{self._category}(interval={self._interval})..."
        )

        while True:
            logger.debug(f"Force REST sync of {self._symbol}.{self._category}...")

            try:
                await self._market_repo.sync_historical_klines_dataframe(
                    path=rest_path,
                    category=self._category,
                    symbol=self._symbol,
                    interval=self._interval,
                    limit=self._limit,
                )
            except Exception as e:
                logger.error(f"Failed to sync market data: {e}", exc_info=True)

            await self._refresh_indicator_snapshot()

            sleep_seconds = await self._calculate_sleep_seconds()
            logger.info(f"Next kline sync in {round(sleep_seconds, 2)} seconds")
            await asyncio.sleep(sleep_seconds)

    async def _refresh_indicator_snapshot(self) -> None:
        """Compute indicators on the freshly synced klines and store the snapshot."""
        klines_df = await self._state.get_klines_dataframe(self._symbol)
        snapshot = self._indicator_engine.snapshot(self._symbol, klines_df)
        if snapshot is None:
            return
        await self._state.set_indicator_snapshot(snapshot)
        logger.info(
            f"Indicators for {self._symbol} @ {snapshot.timestamp} "
            f"close={snapshot.last_close}: {snapshot.indicators}"
        )

    async def stop(self) -> None:
        pass

    async def _calculate_sleep_seconds(self) -> float:
        """Sleep until the currently-forming candle closes (+ a small delay).

        Bybit candles are aligned to the epoch on the interval grid, so the next
        close time is derived directly from ``now`` — independent of how many
        forming candles the extractor drops (``drop_unclosed``).
        """
        current_time: datetime = datetime.now(UTC)

        klines = await self._state.get_klines_dataframe(self._symbol)
        if klines.is_empty():
            return 10.0

        interval_seconds = self._interval_delta.total_seconds()
        now_ts = current_time.timestamp()
        # Next candle boundary on the interval grid = close of the forming candle.
        next_close_ts = (now_ts // interval_seconds + 1) * interval_seconds
        final_sleep_seconds = (next_close_ts - now_ts) + self._delay_seconds

        logger.debug(
            f"Current time: {current_time}\n"
            f"Next kline close: {datetime.fromtimestamp(next_close_ts, UTC)}"
        )

        # Sleep for at least 1 second (to avoid negative sleep)
        return max(final_sleep_seconds, 1.0)
