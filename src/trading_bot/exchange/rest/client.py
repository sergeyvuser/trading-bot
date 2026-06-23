import asyncio

import zapros
from loguru import logger
from zapros import AsyncClient

from trading_bot.exchange.interfaces import IExchangeRestClient
from trading_bot.exchange.rest.extractors import BybitKlineExtractor
from trading_bot.models.account import OrderDTO, PositionDTO
from trading_bot.models.market import KlineRestDTO


class BybitRestClient(IExchangeRestClient):
    def __init__(self, base_url: str):
        super().__init__(base_url)

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

    async def get_active_position(self, symbol: str) -> PositionDTO | None:
        pass
        """params = {"symbol": symbol}
        response_json = await self._get_json("/v5/position/position-info", params)
        return response_json["result"][0]
        """

    async def get_open_orders(self) -> list[OrderDTO]:
        pass
