"""Strategy registry: strategy name -> strategy class."""

from typing import Any

from trading_bot.strategy.interfaces import IStrategy
from trading_bot.strategy.logic.trend_following import TrendFollowing

_REGISTRY: dict[str, type[IStrategy]] = {
    TrendFollowing.name: TrendFollowing,
}


def make_strategy(name: str, symbol: str, params: dict[str, Any]) -> IStrategy:
    strategy_cls = _REGISTRY.get(name)
    if strategy_cls is None:
        raise ValueError(f"Unknown strategy '{name}'. Available: {sorted(_REGISTRY)}")
    return strategy_cls(symbol=symbol, params=params)


def available_strategies() -> list[str]:
    return sorted(_REGISTRY)
