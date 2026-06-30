"""OrderManager — turns a sized OrderIntent into a real (or simulated) order and
tracks the resulting position locally.

Stage 2 part 3 scope: spot, market entry only, one position at a time. The stop is
managed by the engine (local monitoring), not natively on the exchange. Everything
is gated by ``dry_run``: when true, fills are simulated at the current price and no
API call is made.
"""

from datetime import UTC, datetime

from loguru import logger

from trading_bot.exchange.interfaces import IExchangeRestClient
from trading_bot.exchange.rest.quantize import quantize_qty
from trading_bot.models.account import InstrumentInfo
from trading_bot.models.orders import OrderIntent
from trading_bot.models.position import Position
from trading_bot.storage.state import InMemoryState

# Bybit expects title-cased order sides; our domain uses BUY/SELL.
_BYBIT_SIDE = {"BUY": "Buy", "SELL": "Sell"}


class OrderManager:
    def __init__(
        self,
        rest_client: IExchangeRestClient,
        state: InMemoryState,
        instrument_info: InstrumentInfo,
        category: str,
        dry_run: bool = True,
    ) -> None:
        self._rest = rest_client
        self._state = state
        self._info = instrument_info
        self._category = category
        self._dry_run = dry_run

    async def open(self, intent: OrderIntent, price: float) -> Position | None:
        """Enter a spot long: quantize, (maybe) place a market buy, store position."""
        qty = quantize_qty(intent.size, price, self._info)
        if qty is None:
            return None

        if self._dry_run:
            logger.info(
                f"DRY RUN: would BUY {qty} {intent.symbol} @ ~{price:.2f} "
                f"stop={intent.stop_loss:.2f}"
            )
        else:
            order = await self._rest.place_market_order(
                self._category, intent.symbol, _BYBIT_SIDE["BUY"], qty
            )
            if order is None:
                return None

        position = Position(
            symbol=intent.symbol,
            side="BUY",
            qty=float(qty),
            entry_price=price,
            stop_loss=intent.stop_loss,
            opened_at=datetime.now(UTC),
        )
        await self._state.set_position(position)
        logger.info(
            f"Opened position: {position.qty} {position.symbol} @ {price:.2f} "
            f"stop={position.stop_loss:.2f}"
        )
        return position

    async def close(self, position: Position, exit_price: float, reason: str) -> None:
        """Exit the spot long with a market sell; record realized (paper) PnL."""
        qty = quantize_qty(position.qty, exit_price, self._info)
        if qty is None:
            logger.error(
                f"Cannot quantize exit qty {position.qty} {position.symbol}; "
                f"position left open."
            )
            return

        if self._dry_run:
            logger.info(
                f"DRY RUN: would SELL {qty} {position.symbol} @ ~{exit_price:.2f} "
                f"({reason})"
            )
        else:
            order = await self._rest.place_market_order(
                self._category, position.symbol, _BYBIT_SIDE["SELL"], qty
            )
            if order is None:
                logger.error("Exit order failed; position left open.")
                return

        pnl = (exit_price - position.entry_price) * position.qty  # long only on spot
        await self._state.add_realized_pnl(position.symbol, pnl)
        await self._state.clear_position(position.symbol)
        logger.info(
            f"Closed position ({reason}): {position.symbol} "
            f"entry={position.entry_price:.2f} exit={exit_price:.2f} pnl={pnl:.2f}"
        )
