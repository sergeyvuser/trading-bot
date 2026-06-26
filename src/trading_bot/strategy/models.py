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


class RiskConfig(BaseModel):
    risk_per_trade: float = Field(gt=0, le=1)  # fraction of equity risked per trade
    max_daily_loss: float = Field(gt=0, le=1)  # fraction of equity
    starting_equity: float = Field(gt=0)  # paper equity until account API
    atr_period: int = Field(default=14, ge=2)
    atr_mult: float = Field(default=1.5, gt=0)  # stop distance = atr_mult * ATR


class StrategyProfile(BaseModel):
    symbol: str
    category: Literal["spot", "option", "linear", "inverse", "rfq"]
    interval: str
    strategy: StrategyMeta
    indicators: list[IndicatorConfig] = Field(default_factory=list)
    risk: RiskConfig
