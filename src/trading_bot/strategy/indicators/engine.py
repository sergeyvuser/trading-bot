"""IndicatorEngine: compute the indicators declared by a strategy on closed candles."""

import polars as pl
from loguru import logger

from trading_bot.models.analysis import IndicatorSnapshot
from trading_bot.strategy.indicators.registry import get_builder
from trading_bot.strategy.models import IndicatorConfig

_OHLCV_COLUMNS = frozenset(
    {"start_time", "open", "high", "low", "close", "volume", "turnover"}
)


class IndicatorEngine:
    """Builds polars_talib expressions from an indicator config and evaluates them
    in a single lazy pass, extracting the last closed candle into a snapshot."""

    def __init__(self, indicators: list[IndicatorConfig]):
        self._indicators = indicators

    def _build_exprs(self) -> list[pl.Expr]:
        exprs: list[pl.Expr] = []
        for cfg in self._indicators:
            exprs.extend(get_builder(cfg.name)(**cfg.params))
        return exprs

    def calculate(self, df: pl.DataFrame) -> pl.DataFrame:
        if df.is_empty():
            return df
        exprs = self._build_exprs()
        if not exprs:
            return df
        return df.lazy().with_columns(exprs).collect()

    def snapshot(self, symbol: str, df: pl.DataFrame) -> IndicatorSnapshot | None:
        """Compute indicators and return a snapshot of the last closed candle.

        The extractor already dropped the forming candle, so ``row(-1)`` is the
        last closed candle.
        """
        calculated = self.calculate(df)
        if calculated.is_empty():
            logger.warning(f"No klines to compute indicators for {symbol}")
            return None

        row = calculated.row(-1, named=True)
        indicators = {
            name: float(value)
            for name, value in row.items()
            if name not in _OHLCV_COLUMNS and value is not None
        }
        return IndicatorSnapshot(
            symbol=symbol,
            timestamp=row["start_time"],
            last_close=float(row["close"]),
            indicators=indicators,
        )
