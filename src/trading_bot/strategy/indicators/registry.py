"""Indicator registry: indicator name -> polars expression builder."""

from collections.abc import Callable

import polars as pl

from trading_bot.strategy.indicators import pl_indicators as ind

IndicatorBuilder = Callable[..., list[pl.Expr]]

_REGISTRY: dict[str, IndicatorBuilder] = {
    "ema": ind.ema_exprs,
    "sma": ind.sma_exprs,
    "rsi": ind.rsi_exprs,
    "macd": ind.macd_exprs,
}


def get_builder(name: str) -> IndicatorBuilder:
    builder = _REGISTRY.get(name.lower())
    if builder is None:
        raise ValueError(
            f"Unknown indicator '{name}'. Available: {sorted(_REGISTRY)}"
        )
    return builder


def available_indicators() -> list[str]:
    return sorted(_REGISTRY)
