"""Base class for strategies."""

from typing import Any

from trading_bot.models.analysis import IndicatorSnapshot
from trading_bot.models.market import SpotTickerDTO
from trading_bot.strategy.interfaces import IStrategy
from trading_bot.strategy.models import IndicatorConfig


class BaseStrategy(IStrategy):
    """Base strategy. Indicators come from the profile; a strategy may add its own
    via ``required_indicators``. ``on_tick`` is invoked on every price tick with the
    latest indicator snapshot (computed on the last closed candle)."""

    def __init__(self, symbol: str, params: dict[str, Any] | None = None) -> None:
        self.symbol = symbol
        self._params = params or {}

    def required_indicators(self) -> list[IndicatorConfig]:
        return []

    async def on_tick(
        self, ticker: SpotTickerDTO, snapshot: IndicatorSnapshot | None
    ) -> None:
        raise NotImplementedError
