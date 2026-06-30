"""Local open-position state (analysis domain).

Tracked in-process by the OrderManager/engine, not synced from the exchange yet.
Fields are ``float`` so the per-tick stop check stays cheap; the exchange-precise
``Decimal`` quantity lives only inside the order call itself.
"""

from datetime import datetime

import msgspec


class Position(msgspec.Struct, frozen=True):
    symbol: str
    side: str  # "BUY" (spot long); spot has no shorting
    qty: float  # executed base-coin quantity
    entry_price: float
    stop_loss: float
    opened_at: datetime
