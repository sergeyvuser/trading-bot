"""Interfaces for exchange."""

import asyncio
from abc import ABC, abstractmethod
from decimal import Decimal

from loguru import logger

from trading_bot.models.account import InstrumentInfo, OrderDTO
from trading_bot.models.market import KlineRestDTO


class IExchangeRestClient(ABC):
    """Interface for REST client.
    :ivar base_url: Base URL of the exchange.
    :type base_url: str
    """

    def __init__(self, base_url: str):
        """Initialize the REST client.

        :param base_url: Base URL of the exchange.
        :type base_url: str
        """
        self.base_url = base_url
        # self.logger = logger  # .bind(name=self.__class__.__name__)
        logger.info(
            f"Initializing {self.__class__.__name__} with base URL: {self.base_url}"
        )

    @abstractmethod
    async def _get_json(self, path: str, params: dict | None = None):
        pass

    @abstractmethod
    async def get_history_klines(
        self,
        path: str,
        category: str,
        symbol: str,
        interval: str,
        limit: str,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> list[KlineRestDTO]:
        pass

    @abstractmethod
    async def get_raw_klines_data(
        self,
        path: str,
        category: str,
        symbol: str,
        interval: str,
        limit: str,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> list:
        pass

    @abstractmethod
    async def place_market_order(
        self, category: str, symbol: str, side: str, qty: Decimal
    ) -> OrderDTO | None:
        """Place a market order; returns the accepted order or None on failure."""
        pass

    @abstractmethod
    async def get_instruments_info(
        self, category: str, symbol: str
    ) -> InstrumentInfo | None:
        """Fetch contract specs (tick_size/qty_step/minimums) for quantization."""
        pass


class IExchangeWSClient(ABC):
    """Interface for WebSocket client."""

    @abstractmethod
    async def _get_subscriptions(self) -> list[str]:
        """Return list of topics to subscribe, e.g. ['kline.1.BTCUSDT']"""
        pass

    @abstractmethod
    async def _handle_message(
        self, raw_msg_data: str, ticker_queue: asyncio.Queue
    ) -> None:
        """Process incoming message payload."""
        pass

    @abstractmethod
    async def listen(self, ticker_queue: asyncio.Queue) -> None:
        """Listens to the WebSocket stream and puts TickerDTO objects into the queue."""
        pass
