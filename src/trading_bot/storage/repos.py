"""Storage repositories (STORAGE LAYER).

A repository knows *where* data comes from (the exchange REST client). It delegates
formatting to the Extractor and hands the result to the State:
    Repository (source) -> Extractor (format) -> State (storage)
"""

from loguru import logger

from trading_bot.config import settings
from trading_bot.exchange.interfaces import IExchangeRestClient
from trading_bot.exchange.rest.extractors import BybitKlineExtractor
from trading_bot.storage.state import InMemoryState
from trading_bot.strategy.interfaces import IMarketRepository


class BybitMarketRepository(IMarketRepository):
    def __init__(self, state: InMemoryState, rest_client: IExchangeRestClient):
        self._state = state
        self._rest_client = rest_client
        self._kline_extractor = BybitKlineExtractor()

    async def sync_historical_klines_dataframe(
        self,
        path: str,
        category: str,
        symbol: str,
        interval: str,
        limit: str,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> None:
        raw_klines_data = await self._rest_client.get_raw_klines_data(
            path=path,
            category=category,
            symbol=symbol,
            interval=interval,
            limit=limit,
            start_time=start_time,
            end_time=end_time,
        )
        interval_minutes = settings.intervals.get(interval)
        klines_dataframe = self._kline_extractor.to_pl_dataframe(
            raw_kline_data=raw_klines_data,
            interval_minutes=interval_minutes,
        )
        logger.debug(f"Klines DataFrame for {symbol}: {klines_dataframe}")
        await self._state.set_klines_dataframe(symbol, klines_dataframe)
