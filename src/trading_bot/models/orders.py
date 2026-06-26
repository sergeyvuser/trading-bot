"""Order-intent DTO — the bridge from RiskManager to OrderManager.

Produced by the RiskManager (sizing + stop) in the analysis domain (``float``).
The OrderManager quantizes ``size``/price to exchange precision (``Decimal``,
``tick_size``/``qty_step``) before sending — that conversion is the next stage.
"""

import msgspec


class OrderIntent(msgspec.Struct, frozen=True):
    symbol: str
    side: str  # "BUY" | "SELL"
    size: float  # base-coin quantity
    stop_loss: float
    reason: str = ""
