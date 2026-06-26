"""RiskManager — turns a Signal into a sized OrderIntent (or rejects it).

Sizing is ATR fractional risk: risk a fixed fraction of equity per trade, with the
stop placed `atr_mult * ATR` away, so position size scales inversely with volatility.
Equity is paper (from config) until the account API lands. Order quantization to
exchange precision happens later in the OrderManager.
"""

from loguru import logger

from trading_bot.models.analysis import IndicatorSnapshot
from trading_bot.models.orders import OrderIntent
from trading_bot.models.signals import Signal, SignalType
from trading_bot.strategy.models import RiskConfig


class RiskManager:
    def __init__(self, config: RiskConfig):
        self._cfg = config
        self._equity = config.starting_equity
        self._atr_key = f"atr_{config.atr_period}"

    def evaluate(
        self,
        signal: Signal,
        snapshot: IndicatorSnapshot | None,
        in_position: bool = False,
        realized_pnl: float = 0.0,
    ) -> OrderIntent | None:
        if signal.type is SignalType.HOLD:
            return None

        # Daily loss limit (paper PnL until account/position tracking lands).
        if abs(realized_pnl) >= self._equity * self._cfg.max_daily_loss:
            logger.warning("Daily loss limit reached; rejecting signal.")
            return None

        # One position at a time for now (real position tracking is a later stage).
        if in_position:
            logger.debug("Already in position; rejecting signal.")
            return None

        if snapshot is None or self._atr_key not in snapshot.indicators:
            logger.debug("No ATR yet; cannot size position.")
            return None

        atr = snapshot.indicators[self._atr_key]
        stop_distance = self._cfg.atr_mult * atr
        if stop_distance <= 0:
            logger.debug("Non-positive stop distance; rejecting signal.")
            return None

        price = signal.price
        risk_amount = self._equity * self._cfg.risk_per_trade
        size = risk_amount / stop_distance

        if signal.type is SignalType.BUY:
            stop_loss = price - stop_distance
        else:  # SELL
            stop_loss = price + stop_distance

        reason = (
            f"risk={risk_amount:.2f} atr={atr:.4f} stop_dist={stop_distance:.4f} "
            f"entry={price:.2f}"
        )
        return OrderIntent(
            symbol=signal.symbol,
            side=signal.type.value,
            size=size,
            stop_loss=stop_loss,
            reason=reason,
        )
