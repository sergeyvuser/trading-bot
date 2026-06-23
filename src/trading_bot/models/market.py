"""Market DTOs (hot path).

Hot-path objects parsed from the exchange on every message use ``msgspec.Struct``
for fast decoding. Prices used purely for analysis/comparison are ``float`` (float64
matches the polars/polars_talib domain). ``KlineRestDTO`` keeps ``Decimal`` because it
is the precise, on-demand representation (klines themselves live in a polars DataFrame).
"""

from datetime import datetime
from decimal import Decimal

import msgspec


class SpotTickerDTO(msgspec.Struct, frozen=True):
    """Live spot ticker (WebSocket). Prices are float for fast signal evaluation."""

    timestamp: int
    symbol: str
    last_price: float
    high_price_24h: float
    low_price_24h: float
    prev_price_24h: float
    volume_24h: float
    turnover_24h: float
    price_pcnt_24h: float
    usd_index_price: float | None = None


class TradeDTO(msgspec.Struct, frozen=True):
    """Single public trade (WebSocket)."""

    timestamp: int
    symbol: str
    side: str  # "Buy" | "Sell"
    price: float
    size: float


class OrderBookDTO(msgspec.Struct, frozen=True):
    symbol: str
    bids: list[tuple[float, float]]
    asks: list[tuple[float, float]]
    timestamp: int


class FundingRateDTO(msgspec.Struct, frozen=True):
    symbol: str
    funding_rate: float
    timestamp: int


class OpenInterestDTO(msgspec.Struct, frozen=True):
    symbol: str
    open_interest: float
    timestamp: int


class KlineRestDTO(msgspec.Struct, frozen=True):
    """Precise single kline (REST). Built on demand from the DataFrame when exact
    Decimal values are required; klines are stored as a polars DataFrame, not as DTOs."""

    category: str
    symbol: str
    interval: str
    start_time: datetime
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    volume: Decimal
    turnover: Decimal
