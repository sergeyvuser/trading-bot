from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Literal

import msgspec
from pydantic import (
    BaseModel,
    Field,
    HttpUrl,
    SecretStr,
    WebsocketUrl,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

from trading_bot.strategy.models import IndicatorConfig, StrategyMeta, StrategyProfile

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
CONFIG_DIR = BASE_DIR / "src" / "trading_bot" / "config"
ENV_FILE_PATH = BASE_DIR / ".env"
STRATEGIES_DIR = CONFIG_DIR / "strategies"


class LoggingConfig(BaseModel):
    level: Literal["INFO", "DEBUG", "WARNING", "ERROR", "TRACE"] = "INFO"
    format: str
    to_file: bool = False
    rotation: str = "10 MB"
    retention: str = "7 days"


class Hosts(BaseModel):
    api_mainnet: HttpUrl
    api_testnet: HttpUrl
    ws_mainnet: WebsocketUrl
    ws_testnet: WebsocketUrl
    api_telegram: HttpUrl


class WSCategories(BaseModel):
    spot: str
    option: str
    linear: str
    inverse: str
    rfq: str


class WSCoreConfig(BaseModel):
    ping_interval: int = 20
    reconnect_delay: int = 5


class MarketKlineApi(BaseModel):
    path: str
    limit: str


class BotCoreConfig(BaseModel):
    api_delay_sec: int = 5
    maxlen: int = 1500


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
        env_nested_delimiter="__",
    )

    # --- 1. .env variables ---
    # API keys and secrets and core settings
    BYBIT_API_KEY: SecretStr
    BYBIT_API_SECRET: SecretStr
    ACTIVE_STRATEGY: str = "btc_spot"
    TESTNET: bool = True
    DRY_RUN: bool = True
    RISK_PER_TRADE: float = 0.02
    MAX_DAILY_LOSS: float = 0.05

    # Telegram settings
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_CHAT_ID: str

    # --- 2. config.yaml variables ---
    logging: LoggingConfig
    hosts: Hosts
    ws_categories: WSCategories
    ws_core_config: WSCoreConfig
    market_kline_api: MarketKlineApi
    intervals: Dict[str, int]
    bot: BotCoreConfig

    # --- 3. Strategy settings (from config/strategies/<ACTIVE_STRATEGY>.yaml) ---
    symbol: str
    category: Literal["spot", "option", "linear", "inverse", "rfq"]
    interval: str
    strategy: StrategyMeta
    indicators: List[IndicatorConfig] = []

    orderbook_depth: int = Field(50, alias="ORDERBOOK_DEPTH")

    # REST polling
    oi_poll_interval: int = Field(60, alias="OI_POLL_INTERVAL")  # seconds

    # Dynamic URLs
    resolved_rest_url: str = ""
    resolved_public_ws_url: str = ""

    # --- Validation ---

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        symbol = v.strip().upper()
        if not symbol:
            raise ValueError("Symbol cannot be empty")
        return symbol

    @field_validator("interval")
    @classmethod
    def validate_interval(cls, v: str, info) -> str:
        intervals_dict = info.data.get("intervals", {})
        if intervals_dict and v not in intervals_dict:
            raise ValueError(
                f"Invalid interval: {v}. Available intervals: {list(intervals_dict.keys())}"
            )
        return v

    @model_validator(mode="after")
    def resolve_urls(self) -> "Settings":
        """Resolve dynamic URLs based on config settings (TESTNET flag, category)."""
        self.resolved_rest_url = str(
            self.hosts.api_testnet if self.TESTNET else self.hosts.api_mainnet
        )

        base_ws_url = str(
            self.hosts.ws_testnet if self.TESTNET else self.hosts.ws_mainnet
        )
        category_suffix = getattr(self.ws_categories, self.category)
        self.resolved_public_ws_url = f"{base_ws_url}v5/public/{category_suffix}"

        return self

    # --- Derived URLs ---
    @property
    def base_api_url(self) -> str:
        return str(self.hosts.api_testnet if self.TESTNET else self.hosts.api_mainnet)

    @property
    def base_ws_url(self) -> str:
        return str(self.hosts.ws_testnet if self.TESTNET else self.hosts.ws_mainnet)

    @property
    def public_ws_url(self) -> str:
        return f"{self.base_ws_url}v5/public/{self.category}"

    @property
    def spot_ws_url(self) -> str:
        return f"{self.base_ws_url}v5/public/spot"

    @property
    def linear_ws_url(self) -> str:
        return f"{self.base_ws_url}v5/public/linear"

    @property
    def tg_bot_url(self):
        return f"{self.hosts.api_telegram}bot{self.TELEGRAM_BOT_TOKEN}"

    @property
    def strategy_profile(self) -> StrategyProfile:
        """Single source of truth for the running pair/strategy/interval."""
        return StrategyProfile(
            symbol=self.symbol,
            category=self.category,
            interval=self.interval,
            strategy=self.strategy,
            indicators=self.indicators,
        )


@lru_cache(maxsize=1)
def load_settings() -> Settings:
    # Load environment variables from .env file to retrieve active strategy name
    class EnvReader(BaseSettings):
        ACTIVE_STRATEGY: str = "btc_spot"
        model_config = SettingsConfigDict(
            env_file=ENV_FILE_PATH, env_file_encoding="utf-8", extra="ignore"
        )

    env_vars = EnvReader()
    strategy_name = env_vars.ACTIVE_STRATEGY

    # Load base config
    with open(CONFIG_DIR / "config.yaml", "rb") as f:  # use encoding="utf-8" for "r"
        # config_data = yaml.safe_load(f)
        config_data = msgspec.yaml.decode(f.read(), type=dict)

    # Load strategy config
    strategy_path = STRATEGIES_DIR / f"{strategy_name}.yaml"
    if not strategy_path.exists():
        raise FileNotFoundError(f"Strategy config not found: {strategy_path}")

    with open(strategy_path, "rb") as f:  # msgspec decodes bytes on the C side, so open in "rb"
        # strategy_data = yaml.safe_load(f)
        strategy_data = msgspec.yaml.decode(f.read(), type=dict)

    # Merge config and strategy config
    merged_data = {**config_data, **strategy_data}

    # Validate and return merged config
    return Settings(**merged_data)


settings = load_settings()
