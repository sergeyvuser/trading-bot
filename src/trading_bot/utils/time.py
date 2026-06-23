"""Time utilities. Handles exchange timestamps conversion."""

import time
from datetime import UTC, datetime, timedelta

from trading_bot.config import settings


def interval_timedelta(interval: str) -> timedelta:
    return timedelta(minutes=settings.intervals.get(interval))


def current_time_to_timestamp_ms() -> int:
    return int(time.time() * 1000)


def ms_to_utc_datetime(timestamp_ms: int) -> datetime:
    return datetime.fromtimestamp(
        timestamp_ms / 1000, UTC
    )  # strftime("%Y-%m-%d %H:%M:%S")


def interval_to_timestamp_ms(interval: str) -> int:
    return settings.intervals[interval] * 60 * 1000


def convert_exchange_timestamp_to_datetime(exchange_timestamp: int) -> datetime:
    return datetime.fromtimestamp(exchange_timestamp / 1000)


def timestamp_to_datetime_str(exchange_timestamp: int) -> str:
    return convert_exchange_timestamp_to_datetime(exchange_timestamp).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
