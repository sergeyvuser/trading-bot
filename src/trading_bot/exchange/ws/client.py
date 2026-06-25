import asyncio

import aiohttp
from loguru import logger

from trading_bot.exchange.interfaces import IExchangeWSClient
from trading_bot.exchange.rest.extractors import BybitTickerExtractor


class BybitWSClient(IExchangeWSClient):
    def __init__(
        self,
        ws_url: str,
        symbol: str,
        interval: str,
        orderbook_depth: int,
        reconnect_delay: int = 5,
        ping_interval: int = 20,
    ):
        self._url = ws_url
        self._symbol = symbol.upper()
        self._is_running = False
        self._interval = interval
        self._orderbook_depth = orderbook_depth
        self._reconnect_delay = reconnect_delay
        self._ping_interval = ping_interval

    async def _get_subscriptions(self) -> list[str]:
        # Stage 2 part 1: price ticks only. publicTrade/orderbook are added later
        # (scalping / liquidity-aware risk).
        return [f"tickers.{self._symbol}"]

    async def _subscribe(self, ws: aiohttp.ClientWebSocketResponse) -> None:
        topics = await self._get_subscriptions()
        payload = {"op": "subscribe", "args": topics}
        await ws.send_json(payload)
        logger.info(f"Subscribed to {topics}")

    async def _heartbeat(self, ws: aiohttp.ClientWebSocketResponse) -> None:
        while self._is_running:
            try:
                await ws.send_json({"op": "ping"})
                logger.debug("Heartbeat (ping) sent")
                await asyncio.sleep(self._ping_interval)
            except Exception:
                break

    async def listen(self, ticker_queue: asyncio.Queue) -> None:
        self._is_running = True
        logger.info(f"Listening to {self._url} for {self._symbol}")
        while self._is_running:
            try:
                async with aiohttp.client.ClientSession() as session:
                    async with session.ws_connect(self._url, heartbeat=None) as ws:
                        logger.info(f"Connected to {self._url}")

                        await self._subscribe(ws)
                        heartbeat_task = asyncio.create_task(self._heartbeat(ws))

                        async for msg in ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                await self._handle_message(msg.data, ticker_queue)
                            elif msg.type in (
                                aiohttp.WSMsgType.CLOSED,
                                aiohttp.WSMsgType.ERROR,
                            ):
                                logger.error(
                                    f"WebSocket connection closed with exception: {ws.exception()}"
                                )
                                break
                        heartbeat_task.cancel()
            except ConnectionError as e:
                logger.error(f"WebSocket connection error: {e}")

            except Exception as e:
                logger.error(
                    f"WebSocket connection error: {e}. Reconnecting in {self._reconnect_delay} seconds..."
                )
            await asyncio.sleep(self._reconnect_delay)

    async def _handle_message(
        self, raw_msg_data: str, ticker_queue: asyncio.Queue
    ) -> None:
        try:
            ticker_dto = BybitTickerExtractor.decode(raw_msg_data)
            if ticker_dto is None:
                return  # subscription ack / pong / non-ticker frame
            ticker_queue.put_nowait(ticker_dto)
            logger.debug(f"[Spot] Ticker last price={ticker_dto.last_price}")
        except Exception as e:
            logger.error(f"Error processing WS message: {e}")
