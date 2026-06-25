"""Trading signal DTO produced by a strategy on each price tick."""

import enum

import msgspec


class SignalType(enum.Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class Signal(msgspec.Struct, frozen=True):
    symbol: str
    type: SignalType
    price: float  # live price the signal was evaluated against
    reason: str = ""
