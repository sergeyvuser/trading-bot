"""InMemoryState - in-memory, queue-safe (asyncio.Lock) cache. Not persistent.

Single source of truth for klines is a polars DataFrame per symbol. Indicator
results are stored as a lightweight IndicatorSnapshot, refreshed on each closed
candle and read on each price tick.
"""

import asyncio

import polars as pl

from trading_bot.models.analysis import IndicatorSnapshot


class InMemoryState:
    def __init__(self):
        self._klines_dataframes: dict[str, pl.DataFrame] = {}  # {"BTCUSDT": DataFrame}
        self._indicator_snapshots: dict[str, IndicatorSnapshot] = {}

        self._klines_lock = asyncio.Lock()
        self._snapshot_lock = asyncio.Lock()

    # --- Klines (DataFrame, source of truth) ---
    async def set_klines_dataframe(
        self, symbol: str, klines_dataframe: pl.DataFrame
    ) -> None:
        async with self._klines_lock:
            self._klines_dataframes[symbol] = klines_dataframe

    async def get_klines_dataframe(self, symbol: str) -> pl.DataFrame:
        async with self._klines_lock:
            return self._klines_dataframes.get(symbol, pl.DataFrame())

    async def get_last_kline_dataframe(self, symbol: str) -> pl.DataFrame:
        async with self._klines_lock:
            return self._klines_dataframes.get(symbol, pl.DataFrame()).tail(1)

    async def get_first_kline_dataframe(self, symbol: str) -> pl.DataFrame:
        async with self._klines_lock:
            return self._klines_dataframes.get(symbol, pl.DataFrame()).head(1)

    # --- Indicator snapshot (computed on closed candles) ---
    async def set_indicator_snapshot(self, snapshot: IndicatorSnapshot) -> None:
        async with self._snapshot_lock:
            self._indicator_snapshots[snapshot.symbol] = snapshot

    async def get_indicator_snapshot(self, symbol: str) -> IndicatorSnapshot | None:
        async with self._snapshot_lock:
            return self._indicator_snapshots.get(symbol)
