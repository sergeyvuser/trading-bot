"""Unit tests for order-quantity quantization at the analysis -> exchange boundary."""

from decimal import Decimal

from trading_bot.exchange.rest.quantize import quantize_qty
from trading_bot.models.account import InstrumentInfo

# BTCUSDT spot-like specs.
INFO = InstrumentInfo(
    symbol="BTCUSDT",
    base_coin="BTC",
    quote_coin="USDT",
    status="Trading",
    min_order_qty=Decimal("0.000048"),
    max_order_qty=Decimal("71.73956243"),
    min_order_amt=Decimal("1"),
    tick_size=Decimal("0.01"),
    qty_step=Decimal("0.000001"),
)


def test_floors_to_qty_step():
    # 0.00123456789 floored to 0.000001 grid -> 0.001234
    qty = quantize_qty(0.00123456789, price=60000.0, info=INFO)
    assert qty == Decimal("0.001234")


def test_rejects_below_min_qty():
    # Below min_order_qty (0.000048).
    assert quantize_qty(0.00001, price=60000.0, info=INFO) is None


def test_rejects_below_min_notional():
    # qty above min_qty but notional < min_order_amt (1 USDT): 0.0001 * 5000 = 0.5
    assert quantize_qty(0.0001, price=5000.0, info=INFO) is None


def test_accepts_valid_order():
    qty = quantize_qty(0.001, price=60000.0, info=INFO)
    assert qty == Decimal("0.001")
    assert qty * Decimal("60000") >= INFO.min_order_amt


def test_rejects_nonpositive():
    assert quantize_qty(0.0, price=60000.0, info=INFO) is None
    assert quantize_qty(-1.0, price=60000.0, info=INFO) is None
