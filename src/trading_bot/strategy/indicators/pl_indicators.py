"""polars_talib expression builders.

Each builder returns a list of polars expressions (already aliased with the
canonical lowercase column names, e.g. ``ema_200``, ``rsi_14``, ``macd``).
The engine collects them and evaluates everything in a single lazy pass, so
common subexpressions (e.g. the macd struct) are computed once via CSE.
"""

import polars as pl
import polars_talib as plta


def ema_exprs(timeperiod: int, column: str = "close", **_) -> list[pl.Expr]:
    return [plta.ema(real=pl.col(column), timeperiod=timeperiod).alias(f"ema_{timeperiod}")]


def sma_exprs(timeperiod: int, column: str = "close", **_) -> list[pl.Expr]:
    return [plta.sma(real=pl.col(column), timeperiod=timeperiod).alias(f"sma_{timeperiod}")]


def rsi_exprs(timeperiod: int = 14, column: str = "close", **_) -> list[pl.Expr]:
    return [plta.rsi(real=pl.col(column), timeperiod=timeperiod).alias(f"rsi_{timeperiod}")]


def macd_exprs(
    fastperiod: int = 12,
    slowperiod: int = 26,
    signalperiod: int = 9,
    column: str = "close",
    **_,
) -> list[pl.Expr]:
    macd = plta.macd(
        real=pl.col(column),
        fastperiod=fastperiod,
        slowperiod=slowperiod,
        signalperiod=signalperiod,
    )
    return [
        macd.struct.field("macd").alias("macd"),
        macd.struct.field("macdsignal").alias("macd_signal"),
        macd.struct.field("macdhist").alias("macd_hist"),
    ]
