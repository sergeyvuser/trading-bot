import polars as pl

BYBIT_KLINE_RAW_SCHEMA = pl.Schema(
    {
        "start_time": pl.String,  # timestamp
        "open": pl.String,  # open
        "high": pl.String,  # high
        "low": pl.String,  # low
        "close": pl.String,  # close
        "volume": pl.String,  # volume
        "turnover": pl.String,  # turnover
    }
)
