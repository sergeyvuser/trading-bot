"""Quantization at the analysis -> exchange boundary.

The RiskManager sizes positions in the analysis domain (``float``). Before an order
can be sent it must be snapped to the instrument's ``qty_step`` and validated against
the exchange minimums, all in ``Decimal`` to avoid float drift.
"""

from decimal import Decimal

from loguru import logger

from trading_bot.models.account import InstrumentInfo


def quantize_qty(
    size: float, price: float, info: InstrumentInfo
) -> Decimal | None:
    """Floor ``size`` to ``qty_step`` and validate exchange minimums.

    Returns the quantized base-coin quantity, or ``None`` if it falls below
    ``min_order_qty`` or the notional is below ``min_order_amt``.
    """
    if size <= 0:
        return None

    size_dec = Decimal(str(size))
    step = info.qty_step
    qty = (size_dec // step) * step  # floor to the step grid

    if qty < info.min_order_qty:
        logger.warning(
            f"Quantized qty {qty} < min_order_qty {info.min_order_qty} for "
            f"{info.symbol}; rejecting."
        )
        return None

    notional = qty * Decimal(str(price))
    if notional < info.min_order_amt:
        logger.warning(
            f"Notional {notional} < min_order_amt {info.min_order_amt} for "
            f"{info.symbol}; rejecting."
        )
        return None

    return qty
