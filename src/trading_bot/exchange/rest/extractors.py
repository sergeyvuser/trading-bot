"""EXTRACTORS (format layer).

Sits between the Repository (where data comes from) and the State (where it is kept).
Turns raw exchange payloads into the representation each consumer needs:
  - REST klines  -> polars.DataFrame (float64, analysis domain)
  - WS tickers    -> msgspec.Struct (hot DTO)
  - single kline  -> KlineRestDTO (precise Decimal, on demand)
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import polars as pl
from loguru import logger

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


class BybitTickerExtractor:
    @classmethod
    def to_spot_ticker(cls, payload: dict, ts: int) -> SpotTickerDTO:
        """Build a hot spot ticker DTO from a WS ticker payload."""
        usd_index = payload.get("usdIndexPrice")
        return SpotTickerDTO(
            timestamp=ts,
            symbol=payload["symbol"],
            last_price=float(payload["lastPrice"]),
            high_price_24h=float(payload["highPrice24h"]),
            low_price_24h=float(payload["lowPrice24h"]),
            prev_price_24h=float(payload["prevPrice24h"]),
            volume_24h=float(payload["volume24h"]),
            turnover_24h=float(payload["turnover24h"]),
            price_pcnt_24h=float(payload["price24hPcnt"]),
            usd_index_price=float(usd_index) if usd_index else None,
        )
