import asyncio

import aiohttp
import msgspec
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
        self._decoder = msgspec.json.Decoder()

    async def _get_subscriptions(self) -> list[str]:
        return [
            f"publicTrade.{self._symbol}",
            f"orderbook.{self._orderbook_depth}.{self._symbol}",
            f"tickers.{self._symbol}",
        ]

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
            # data = json.loads(raw_msg_data)
            data = self._decoder.decode(raw_msg_data)

            logger.debug(f"Received message: {data}")
            if "topic" not in data or "data" not in data:
                return

            topic: str = data.get("topic", "")
            if topic.startswith("kline."):
                self._handle_kline(data)
            elif topic.startswith("publicTrade."):
                self._handle_trades(data)
            elif topic.startswith("orderbook."):
                self._handle_orderbook(data)
            elif topic.startswith("tickers."):
                self._handle_ticker(data, ticker_queue)
            else:
                logger.debug(f"[Spot] Unknown topic: {topic}\n{data}")
        except Exception as e:
            logger.error(f"Error processing WS message: {e}")

    @classmethod
    def _handle_ticker(cls, data: dict, ticker_queue: asyncio.Queue) -> None:
        payload = data.get("data", {})
        ts = data.get("ts", 0)
        try:
            ticker_dto = BybitTickerExtractor.to_spot_ticker(payload, ts)
            ticker_queue.put_nowait(ticker_dto)
            logger.debug(f"[Spot] Ticker last price={ticker_dto.last_price}")
        except Exception as e:
            logger.error(f"Error processing ticker message: {e}")

    def _handle_kline(self, data):
        pass

    def _handle_trades(self, data):
        pass

    def _handle_orderbook(self, data):
        pass
