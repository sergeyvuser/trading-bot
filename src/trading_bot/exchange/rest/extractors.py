"""EXTRACTORS (format layer).

Sits between the Repository (where data comes from) and the State (where it is kept).
Turns raw exchange payloads into the representation each consumer needs:
  - REST klines  -> polars.DataFrame (float64, analysis domain)
  - WS tickers    -> msgspec.Struct (hot DTO)
  - single kline  -> KlineRestDTO (precise Decimal, on demand)
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import msgspec
import polars as pl
from loguru import logger

from trading_bot.models.account import InstrumentInfo
from trading_bot.models.market import KlineRestDTO, SpotTickerDTO
from trading_bot.models.polars_schemas import BYBIT_KLINE_RAW_SCHEMA
from trading_bot.utils.time import ms_to_utc_datetime


class BybitKlineExtractor:
    @classmethod
    def to_dto(
        cls, symbol: str, category: str, interval: str, kline_data: list
    ) -> KlineRestDTO:
        """Build a single precise (Decimal) kline DTO from a raw Bybit kline list."""
        return KlineRestDTO(
            category=category,
            symbol=symbol,
            interval=interval,
            start_time=ms_to_utc_datetime(int(kline_data[0])),
            open_price=Decimal(kline_data[1]),
            high_price=Decimal(kline_data[2]),
            low_price=Decimal(kline_data[3]),
            close_price=Decimal(kline_data[4]),
            volume=Decimal(kline_data[5]),
            turnover=Decimal(kline_data[6]),
        )

    @classmethod
    def to_pl_dataframe(
        cls,
        raw_kline_data: list,
        interval_minutes: int | None = None,
        drop_unclosed: bool = True,
    ) -> pl.DataFrame:
        """Convert a raw Bybit kline list into a typed, sorted DataFrame.

        Bybit returns klines newest-first and the newest one is usually still
        forming. With ``drop_unclosed`` and ``interval_minutes`` the trailing
        forming candle is removed so indicators are computed on closed candles only.
        """
        if not raw_kline_data:
            logger.warning("Empty kline response from Bybit")
            return pl.DataFrame()

        raw_df = pl.DataFrame(
            raw_kline_data, schema=BYBIT_KLINE_RAW_SCHEMA, orient="row"
        )

        validated_df = raw_df.with_columns(
            [
                pl.col("start_time")
                .cast(pl.Int64, strict=False)
                .cast(pl.Datetime("ms", "UTC")),
                pl.col("open").cast(pl.Float64, strict=False),
                pl.col("high").cast(pl.Float64, strict=False),
                pl.col("low").cast(pl.Float64, strict=False),
                pl.col("close").cast(pl.Float64, strict=False),
                pl.col("volume").cast(pl.Float64, strict=False),
                pl.col("turnover").cast(pl.Float64, strict=False),
            ]
        )

        initial_len = len(validated_df)
        validated_df = validated_df.filter(
            pl.col("start_time").is_not_null() & pl.col("close").is_not_null()
        )
        if len(validated_df) < initial_len:
            logger.warning(
                f"Filtered out {initial_len - len(validated_df)} invalid klines"
            )

        validated_df = validated_df.unique(subset=["start_time"], keep="last").sort(
            "start_time"
        )

        if drop_unclosed and interval_minutes is not None:
            validated_df = cls._drop_forming_candle(validated_df, interval_minutes)

        return validated_df

    @staticmethod
    def _drop_forming_candle(df: pl.DataFrame, interval_minutes: int) -> pl.DataFrame:
        """Drop the trailing candle if its period has not closed yet."""
        if df.is_empty():
            return df
        last_start: datetime = df["start_time"].item(-1)
        candle_end = last_start + timedelta(minutes=interval_minutes)
        if candle_end > datetime.now(UTC):
            logger.debug(f"Dropping forming candle starting at {last_start}")
            return df.head(df.height - 1)
        return df


class _BybitTickerData(
    msgspec.Struct,
    rename={
        "last_price": "lastPrice",
        "high_price_24h": "highPrice24h",
        "low_price_24h": "lowPrice24h",
        "prev_price_24h": "prevPrice24h",
        "volume_24h": "volume24h",
        "turnover_24h": "turnover24h",
        "price_pcnt_24h": "price24hPcnt",
    },
):
    """Bybit WS `tickers.<symbol>` data payload (prices arrive as JSON strings;
    decoded with strict=False so msgspec casts str -> float on the C side)."""

    symbol: str
    last_price: float
    high_price_24h: float
    low_price_24h: float
    prev_price_24h: float
    volume_24h: float
    turnover_24h: float
    price_pcnt_24h: float


class _BybitWsMessage(msgspec.Struct):
    """Envelope tolerant of non-data frames (subscription ack / pong have no `data`)."""

    topic: str | None = None
    ts: int = 0
    data: _BybitTickerData | None = None


class BybitInstrumentExtractor:
    """Maps a raw `/v5/market/instruments-info` spot item into InstrumentInfo.

    Spot has no explicit qty step — ``basePrecision`` (the base-coin precision) is
    the quantity grid; the price grid is ``priceFilter.tickSize``.
    """

    @staticmethod
    def to_dto(raw: dict) -> InstrumentInfo:
        lot = raw["lotSizeFilter"]
        price = raw["priceFilter"]
        return InstrumentInfo(
            symbol=raw["symbol"],
            base_coin=raw["baseCoin"],
            quote_coin=raw["quoteCoin"],
            status=raw["status"],
            min_order_qty=Decimal(lot["minOrderQty"]),
            max_order_qty=Decimal(lot["maxOrderQty"]),
            min_order_amt=Decimal(lot["minOrderAmt"]),
            tick_size=Decimal(price["tickSize"]),
            qty_step=Decimal(lot["basePrecision"]),
        )


class BybitTickerExtractor:
    """Decodes a raw WS frame straight into a typed struct (no intermediate dict)."""

    _decoder = msgspec.json.Decoder(_BybitWsMessage, strict=False)

    @classmethod
    def decode(cls, raw: str | bytes) -> SpotTickerDTO | None:
        msg = cls._decoder.decode(raw)
        if (
            msg.data is None
            or msg.topic is None
            or not msg.topic.startswith("tickers.")
        ):
            return None
        d = msg.data
        return SpotTickerDTO(
            timestamp=msg.ts,
            symbol=d.symbol,
            last_price=d.last_price,
            high_price_24h=d.high_price_24h,
            low_price_24h=d.low_price_24h,
            prev_price_24h=d.prev_price_24h,
            volume_24h=d.volume_24h,
            turnover_24h=d.turnover_24h,
            price_pcnt_24h=d.price_pcnt_24h,
        )
