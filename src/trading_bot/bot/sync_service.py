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
        self._delay_seconds = (
            2.0  # Technical delay between syncs to avoid Bybit cache not updating
        )

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

        current_time: datetime = datetime.now(UTC)

        klines = await self._state.get_klines_dataframe(self._symbol)
        if klines.is_empty():
            return 10.0

        last_kline_dataframe = await self._state.get_last_kline_dataframe(self._symbol)
        last_kline_start_time: datetime = last_kline_dataframe["start_time"].item()

        next_kline_start_time: datetime = (
            last_kline_start_time + 2 * self._interval_delta
        )  # !refactor based on BybitKlineExtractor.to_pl_dataframe drop_unclosed attr
        time_to_next_kline = (next_kline_start_time - current_time).total_seconds()
        final_sleep_seconds = time_to_next_kline + self._delay_seconds
        first_kline_dataframe = await self._state.get_first_kline_dataframe(
            self._symbol
        )
        first_kline_start_time = first_kline_dataframe["start_time"].item()

        logger.debug(
            f"Current time: {current_time}\n"
            f"Next kline start time: {next_kline_start_time}\n"
            f"First kline start time: {first_kline_start_time}"
        )

        # Sleep for at least 1 second (to avoid negative sleep)
        return max(final_sleep_seconds, 1.0)
