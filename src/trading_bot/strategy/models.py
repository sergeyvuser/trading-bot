"""Strategy configuration models (cold path -> pydantic).

A StrategyProfile is the single source of truth for a running container:
which pair, market category, interval, strategy and its indicators. Loaded once
at startup from ``config/strategies/<ACTIVE_STRATEGY>.yaml``.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class IndicatorConfig(BaseModel):
    name: str  # registry key, e.g. "ema", "rsi", "macd"
    params: dict[str, Any] = Field(default_factory=dict)


class StrategyMeta(BaseModel):
    name: str
    params: dict[str, Any] = Field(default_factory=dict)


class StrategyProfile(BaseModel):
    symbol: str
    category: Literal["spot", "option", "linear", "inverse", "rfq"]
    interval: str
    strategy: StrategyMeta
    indicators: list[IndicatorConfig] = Field(default_factory=list)
