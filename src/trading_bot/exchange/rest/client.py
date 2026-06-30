import asyncio
import hashlib
import hmac
import time
from decimal import Decimal

import msgspec
import zapros
from loguru import logger
from zapros import AsyncClient

from trading_bot.exchange.interfaces import IExchangeRestClient
from trading_bot.exchange.rest.extractors import (
    BybitInstrumentExtractor,
    BybitKlineExtractor,
)
from trading_bot.models.account import InstrumentInfo, OrderDTO
from trading_bot.models.market import KlineRestDTO


class BybitRestClient(IExchangeRestClient):
    def __init__(
        self,
        base_url: str,
        api_key: str = "",
        api_secret: str = "",
        recv_window: int = 5000,
    ):
        super().__init__(base_url)
        self._api_key = api_key
        self._api_secret = api_secret.encode()
        self._recv_window = str(recv_window)

    async def _get_json(self, path: str, params: dict | None = None) -> dict:
        """Get JSON data from Bybit API.
        Args:
            path: API endpoint path.
            params: Query parameters.
        Returns:
            dict: JSON data."""
        try:
            async with AsyncClient() as client:
                url = f"{self.base_url}{path}"
                response = await client.get(url=url, params=params)
                response.raise_for_status()  # raise exception on 4xx or 5xx
                return response.json
        except asyncio.TimeoutError:
            logger.error("Timeout API Bybit REST Client")
            return {}
        except zapros.ConnectionError as ce:
            logger.error(f"Connection error API Bybit REST Client: {ce}", exc_info=True)
            return {}
        except Exception as e:
            logger.error(f"Error API Bybit REST Client: {e}", exc_info=True)
            return {}

    async def get_history_klines(
        self,
        path: str,
        category: str,
        symbol: str,
        interval: str,
        limit: str,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> list[KlineRestDTO]:
        params = {
            "category": category,
            "symbol": symbol,
            "interval": interval,
            "limit": limit,
        }
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time

        response_json = await self._get_json(path, params)
        raw_klines_data = response_json["result"]["list"]

        return [
            BybitKlineExtractor().to_dto(
                symbol=symbol,
                category=category,
                interval=interval,
                kline_data=kline_data,
            )
            for kline_data in raw_klines_data
        ]

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
        params = {
            "category": category,
            "symbol": symbol,
            "interval": interval,
            "limit": limit,
        }
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time

        response_json = await self._get_json(path, params)
        # logger.debug(f"Raw klines json: {response_json} \n")
        ret_code = response_json.get("retCode")
        if ret_code != 0:
            logger.error(
                f"Error API Bybit (retCode={ret_code}): {response_json.get('retMsg')}"
            )
            return []

        result_klines_list = response_json.get("result", {}).get("list", [])

        return result_klines_list

    async def _post_signed(self, path: str, body: dict) -> dict:
        """Signed POST (Bybit v5). Returns the parsed JSON; never swallows errors —
        callers must know whether an order was accepted.

        The signature covers ``timestamp + api_key + recv_window + raw_body``, so the
        body is serialized once and the exact bytes are both signed and sent.
        """
        timestamp = str(int(time.time() * 1000))
        body_bytes = msgspec.json.encode(body)
        payload = (timestamp + self._api_key + self._recv_window).encode() + body_bytes
        signature = hmac.new(self._api_secret, payload, hashlib.sha256).hexdigest()

        headers = {
            "X-BAPI-API-KEY": self._api_key,
            "X-BAPI-TIMESTAMP": timestamp,
            "X-BAPI-RECV-WINDOW": self._recv_window,
            "X-BAPI-SIGN": signature,
            "Content-Type": "application/json",
        }
        async with AsyncClient() as client:
            url = f"{self.base_url}{path}"
            response = await client.post(url=url, headers=headers, body=body_bytes)
            response.raise_for_status()
            return response.json

    async def place_market_order(
        self, category: str, symbol: str, side: str, qty: Decimal
    ) -> OrderDTO | None:
        """Place a spot market order. ``side`` is Bybit-cased ("Buy"/"Sell")."""
        body = {
            "category": category,
            "symbol": symbol,
            "side": side,
            "orderType": "Market",
            "qty": str(qty),
        }
        try:
            response_json = await self._post_signed("/v5/order/create", body)
        except Exception as e:
            logger.error(f"place_market_order request failed: {e}", exc_info=True)
            return None

        if response_json.get("retCode") != 0:
            logger.error(
                f"Order rejected (retCode={response_json.get('retCode')}): "
                f"{response_json.get('retMsg')}"
            )
            return None

        order_id = response_json.get("result", {}).get("orderId")
        logger.info(f"Order accepted: {side} {qty} {symbol} (orderId={order_id})")
        return OrderDTO(symbol=symbol, side=side, size=qty, price=Decimal(0))

    async def get_instruments_info(
        self, category: str, symbol: str
    ) -> InstrumentInfo | None:
        params = {"category": category, "symbol": symbol}
        response_json = await self._get_json("/v5/market/instruments-info", params)
        if response_json.get("retCode") != 0:
            logger.error(
                f"instruments-info error (retCode={response_json.get('retCode')}): "
                f"{response_json.get('retMsg')}"
            )
            return None

        items = response_json.get("result", {}).get("list", [])
        if not items:
            logger.error(f"No instrument info for {symbol}")
            return None
        logger.debug(f"Instrument info: {items[0]}")
        return BybitInstrumentExtractor.to_dto(items[0])
