"""Analysis result DTO.

Lightweight snapshot of indicator values computed on the last *closed* candle.
Written on each candle tick (REST sync) and read on each price tick (WS), so it
must be cheap to read — hence a flat msgspec.Struct over a dict, not a DataFrame row.
"""

from datetime import datetime

import msgspec


class IndicatorSnapshot(msgspec.Struct, frozen=True):
    symbol: str
    timestamp: datetime  # start_time of the last closed candle
    last_close: float
    indicators: dict[str, float]  # e.g. {"ema_200": 65000.0, "rsi_14": 42.3}
