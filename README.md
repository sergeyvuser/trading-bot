# trading-bot

Async-first trading bot for Bybit, built on a fast data stack
(`msgspec` + `polars` + `polars_talib`). `pydantic` is used only on the cold path
(config/startup validation).

## Architecture

```
Repository (source) -> Extractor (format) -> InMemoryState (storage)
    -> IndicatorEngine -> IndicatorSnapshot
    -> Strategy (Signal) -> RiskManager (OrderIntent) -> (Order, not yet implemented)
```

- **Two clocks** — indicators are computed on each *closed candle* (REST sync) and
  stored as a lightweight `IndicatorSnapshot`; the strategy fires on each *price tick*
  (WS) reading that snapshot, so heavy polars work never runs per tick.
- **Data-type boundary** — hot DTOs (WS ticks/trades) are `msgspec.Struct`; klines and
  indicators live in one `pl.DataFrame` per symbol as `float64`; `Decimal` is used only
  at the exchange boundary (account, positions, orders).
- **Single source of truth** — one `StrategyProfile` per running container
  (`config/strategies/<ACTIVE_STRATEGY>.yaml`) defines the pair, market category,
  interval, strategy and its indicators.

## Setup

Requires Python >= 3.14 and [`uv`](https://docs.astral.sh/uv/).

```bash
make install            # uv sync
cp .env.example .env    # then fill in your keys (see below)
```

Required env vars: `BYBIT_API_KEY`, `BYBIT_API_SECRET`, `ACTIVE_STRATEGY`
(selects the strategy YAML), `TESTNET`, `DRY_RUN`, `TELEGRAM_BOT_TOKEN`,
`TELEGRAM_CHAT_ID`.

## Run

```bash
make run                # python -m trading_bot.main
make dev                # run with --debug
make lint               # ruff check
make format             # ruff format
uv run pytest           # tests
```

Multi-bot Docker deployment (one container per pair/strategy/interval):

```bash
docker compose up
```

## Configuration

A strategy profile is the single source of truth. Example
(`src/trading_bot/config/strategies/btcusdt_spot_60_trend_following.yaml`):

```yaml
symbol: "BTCUSDT"
category: "spot"
interval: "60"
strategy:
  name: "trend_following"
  params: { }
indicators:
  - { name: "ema", params: { timeperiod: 200 } }
  - { name: "rsi", params: { timeperiod: 14 } }
  - { name: "macd", params: { fastperiod: 12, slowperiod: 26, signalperiod: 9 } }
risk:
  risk_per_trade: 0.02      # fraction of equity risked per trade
  max_daily_loss: 0.05      # fraction of equity
  starting_equity: 10000    # paper equity (USDT) until account API
  atr_period: 14
  atr_mult: 1.5             # stop distance = atr_mult * ATR
```

Indicator columns use canonical lowercase names: `ema_200`, `rsi_14`,
`macd` / `macd_signal` / `macd_hist`, `atr_14`.

The `RiskManager` sizes positions with ATR fractional risk
(`size = equity * risk_per_trade / (atr_mult * ATR)`) and produces an `OrderIntent`;
order execution (Decimal quantization, account/PnL) is not yet implemented.

## License

MIT — see [LICENSE](LICENSE).
