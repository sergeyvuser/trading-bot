"""Trend-following strategy.

Trend filter on EMAs computed on closed candles, momentum filter on RSI; evaluated
against the live tick price. Emits a Signal — order execution is wired in stage 2.
"""

from loguru import logger

from trading_bot.models.analysis import IndicatorSnapshot
from trading_bot.models.market import SpotTickerDTO
from trading_bot.models.signals import Signal, SignalType
from trading_bot.strategy.base import BaseStrategy
from trading_bot.strategy.models import IndicatorConfig


class TrendFollowing(BaseStrategy):
    name = "trend_following"

    def required_indicators(self) -> list[IndicatorConfig]:
        return [
            IndicatorConfig(name="ema", params={"timeperiod": 12}),
            IndicatorConfig(name="ema", params={"timeperiod": 26}),
            IndicatorConfig(name="ema", params={"timeperiod": 200}),
            IndicatorConfig(name="rsi", params={"timeperiod": 14}),
        ]

    async def on_tick(
        self, ticker: SpotTickerDTO, snapshot: IndicatorSnapshot | None
    ) -> Signal | None:
        price = ticker.last_price

        if snapshot is None:
            return Signal(
                symbol=self.symbol,
                type=SignalType.HOLD,
                price=price,
                reason="no indicator snapshot yet",
            )

        ind = snapshot.indicators
        ema_fast = ind.get("ema_12")
        ema_slow = ind.get("ema_26")
        ema_trend = ind.get("ema_200")
        rsi = ind.get("rsi_14")

        if None in (ema_fast, ema_slow, ema_trend, rsi):
            return Signal(
                symbol=self.symbol,
                type=SignalType.HOLD,
                price=price,
                reason="indicators not warmed up",
            )

        uptrend = price > ema_trend and ema_fast > ema_slow
        downtrend = price < ema_trend and ema_fast < ema_slow

        if uptrend and rsi < 70:
            signal_type = SignalType.BUY
        elif downtrend and rsi > 30:
            signal_type = SignalType.SELL
        else:
            signal_type = SignalType.HOLD

        reason = f"price={price:.2f} ema200={ema_trend:.2f} ema12/26={ema_fast:.2f}/{ema_slow:.2f} rsi={rsi:.1f}"
        logger.debug(f"[{self.name}] {signal_type.value}: {reason}")
        return Signal(symbol=self.symbol, type=signal_type, price=price, reason=reason)
