"""InMemoryState - in-memory, queue-safe (asyncio.Lock) cache. Not persistent.

Single source of truth for klines is a polars DataFrame per symbol. Indicator
results are stored as a lightweight IndicatorSnapshot, refreshed on each closed
candle and read on each price tick.
"""

import asyncio

import polars as pl

from trading_bot.models.analysis import IndicatorSnapshot
from trading_bot.models.position import Position


class InMemoryState:
    def __init__(self):
        self._klines_dataframes: dict[str, pl.DataFrame] = {}  # {"BTCUSDT": DataFrame}
        self._indicator_snapshots: dict[str, IndicatorSnapshot] = {}
        self._last_prices: dict[str, float] = {}  # live price from WS ticks
        self._positions: dict[str, Position] = {}  # open position per symbol
        self._realized_pnl: dict[str, float] = {}  # cumulative paper PnL per symbol

        self._klines_lock = asyncio.Lock()
        self._snapshot_lock = asyncio.Lock()
        self._price_lock = asyncio.Lock()
        self._position_lock = asyncio.Lock()

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

    # --- Live price (from WS ticks) ---
    async def set_last_price(self, symbol: str, price: float) -> None:
        async with self._price_lock:
            self._last_prices[symbol] = price

    async def get_last_price(self, symbol: str) -> float | None:
        async with self._price_lock:
            return self._last_prices.get(symbol)

    # --- Indicator snapshot (computed on closed candles) ---
    async def set_indicator_snapshot(self, snapshot: IndicatorSnapshot) -> None:
        async with self._snapshot_lock:
            self._indicator_snapshots[snapshot.symbol] = snapshot

    async def get_indicator_snapshot(self, symbol: str) -> IndicatorSnapshot | None:
        async with self._snapshot_lock:
            return self._indicator_snapshots.get(symbol)

    # --- Position + realized PnL (local, paper until exchange sync lands) ---
    async def get_position(self, symbol: str) -> Position | None:
        async with self._position_lock:
            return self._positions.get(symbol)

    async def set_position(self, position: Position) -> None:
        async with self._position_lock:
            self._positions[position.symbol] = position

    async def clear_position(self, symbol: str) -> None:
        async with self._position_lock:
            self._positions.pop(symbol, None)

    async def get_realized_pnl(self, symbol: str) -> float:
        async with self._position_lock:
            return self._realized_pnl.get(symbol, 0.0)

    async def add_realized_pnl(self, symbol: str, pnl: float) -> None:
        async with self._position_lock:
            self._realized_pnl[symbol] = self._realized_pnl.get(symbol, 0.0) + pnl
