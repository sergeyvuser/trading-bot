"""Interfaces for repositories and strategy (dependency inversion)."""

from abc import ABC, abstractmethod

from trading_bot.models.analysis import IndicatorSnapshot
from trading_bot.models.market import SpotTickerDTO


class IMarketRepository(ABC):
    """Interface for market data repository."""

    @abstractmethod
    async def sync_historical_klines_dataframe(
        self,
        path: str,
        category: str,
        symbol: str,
        interval: str,
        limit: str,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> None:
        """Fetch klines from the exchange and store them as a DataFrame in state."""
        ...


class IStrategy(ABC):
    """Interface for a trading strategy.

    Indicators are computed on closed candles (candle tick) and exposed as an
    ``IndicatorSnapshot``; the strategy is invoked on each price tick to evaluate it.
    """

    symbol: str

    @abstractmethod
    def required_indicators(self) -> list:
        """Extra indicators (beyond the profile) this strategy needs, if any."""
        ...

    @abstractmethod
    async def on_tick(
        self, ticker: SpotTickerDTO, snapshot: IndicatorSnapshot | None
    ) -> None:
        """Evaluate the strategy against the latest price and indicator snapshot."""
        ...
