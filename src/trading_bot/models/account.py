"""Account / exchange-boundary DTOs.

These sit on the exchange boundary where precision matters (positions, orders,
instrument step/tick), so monetary fields are ``Decimal``. ``msgspec`` decodes
``Decimal`` natively from JSON strings, so this stays fast and precise.
"""

from decimal import Decimal

import msgspec


class InstrumentInfo(msgspec.Struct, frozen=True):
    """Contract specs used to quantize order price/qty to exchange precision."""

    symbol: str
    base_coin: str
    quote_coin: str
    status: str
    min_order_qty: Decimal
    max_order_qty: Decimal
    min_order_amt: Decimal
    tick_size: Decimal  # price precision
    qty_step: Decimal  # qty precision


class PositionDTO(msgspec.Struct, frozen=True):
    symbol: str
    side: str
    size: Decimal


class OrderDTO(msgspec.Struct, frozen=True):
    symbol: str
    side: str
    size: Decimal
    price: Decimal
