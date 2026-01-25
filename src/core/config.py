import json
import logging
import os
from pathlib import Path

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

from core.constants import (
    DEFAULT_SYMBOLS_STR,
    MAX_RETRIES,
    RETRY_DELAY_SECONDS,
    Timeouts,
)

logger = logging.getLogger(__name__)


def load_ha_options() -> dict:
    """Load options from Home Assistant add-on config."""
    options_path = Path("/data/options.json")
    if options_path.exists():
        try:
            return json.loads(options_path.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def load_ha_secrets() -> dict:
    """Load secrets from Home Assistant secrets.yaml."""
    secrets_path = Path("/config/secrets.yaml")
    if secrets_path.exists():
        try:
            content = secrets_path.read_text()
            return yaml.safe_load(content) or {}
        except (yaml.YAMLError, OSError) as e:
            logger.warning(f"Failed to load secrets.yaml: {e}")
    return {}


def resolve_secret(value: str | None, secrets: dict) -> str | None:
    """Resolve !secret reference to actual value."""
    if not value or not isinstance(value, str):
        return value
    if value.startswith("!secret "):
        secret_key = value[8:].strip()
        return secrets.get(secret_key)
    return value


def load_ha_configuration() -> dict:
    """Load crypto_inspect config from dedicated crypto_inspect.yaml file.

    Reads /config/crypto_inspect.yaml and resolves !secret references.
    Priority: crypto_inspect.yaml > options.json > env > defaults
    """
    config_path = Path("/config/crypto_inspect.yaml")
    if not config_path.exists():
        logger.info("crypto_inspect.yaml not found, using defaults")
        return {}

    try:
        # Custom loader to handle !secret tags
        class SecretLoader(yaml.SafeLoader):
            pass

        def secret_constructor(loader, node):
            return f"!secret {loader.construct_scalar(node)}"

        SecretLoader.add_constructor("!secret", secret_constructor)

        content = config_path.read_text()
        crypto_config = yaml.load(content, Loader=SecretLoader) or {}

        if not crypto_config:
            return {}

        # Load secrets and resolve references
        secrets = load_ha_secrets()
        resolved = {}
        for key, value in crypto_config.items():
            resolved[key] = resolve_secret(value, secrets)

        logger.info(f"Loaded {len(resolved)} settings from crypto_inspect.yaml")
        return resolved

    except (yaml.YAMLError, OSError) as e:
        logger.warning(f"Failed to load crypto_inspect.yaml: {e}")
        return {}


# Load HA options once at module level
_ha_options = load_ha_options()
_ha_config = load_ha_configuration()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Application
    APP_NAME: str = "crypto-inspect"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://crypto_user:C3uX%WNa8#J!0^OR@192.168.1.25:5432/crypto_inspector"
    DATABASE_URL_SYNC: str = "postgresql://crypto_user:C3uX%WNa8#J!0^OR@192.168.1.25:5432/crypto_inspector"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # WebSocket Streaming
    STREAMING_ENABLED: bool = True
    STREAMING_SYMBOLS: str = ""  # Will be set from HA_SYMBOLS env
    STREAMING_INTERVAL: str = "1m"  # 1m, 5m, 15m, 1h, etc.

    # Default symbols if not configured
    DEFAULT_SYMBOLS: str = DEFAULT_SYMBOLS_STR

    # Retry configuration
    MAX_RETRIES: int = MAX_RETRIES
    RETRY_DELAY_SECONDS: int = RETRY_DELAY_SECONDS

    # Timeout defaults
    DEFAULT_TIMEOUT: float = Timeouts.DEFAULT
    CANDLESTICK_FETCH_TIMEOUT: float = Timeouts.CANDLESTICK_FETCH
    AI_TIMEOUT: float = Timeouts.OPENAI
    OLLAMA_TIMEOUT: float = Timeouts.OLLAMA

    # Bybit Exchange API (read from HA options or env)
    BYBIT_API_KEY: str = ""
    BYBIT_API_SECRET: str = ""
    BYBIT_TESTNET: bool = False

    # Own API Server
    API_ENABLED: bool = True
    API_PORT: int = 9999
    API_HOST: str = "0.0.0.0"

    # MCP Server (Model Context Protocol)
    MCP_ENABLED: bool = True
    MCP_PORT: int = 9998
    MCP_HOST: str = "0.0.0.0"

    # Backfill Settings
    BACKFILL_ENABLED: bool = True
    BACKFILL_CRYPTO_YEARS: int = 10
    BACKFILL_TRADITIONAL_YEARS: int = 1
    BACKFILL_INTERVALS: str = "1d,4h,1h"

    # AI Analysis Settings
    AI_ENABLED: bool = False
    AI_PROVIDER: str = "ollama"  # "ollama" or "openai"
    OPENAI_API_KEY: str = ""
    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"
    AI_ANALYSIS_INTERVAL_HOURS: int = 24
    AI_LANGUAGE: str = "en"  # "en" or "ru"

    # UX Feature Settings
    GOAL_ENABLED: bool = False
    GOAL_TARGET_VALUE: int = 100000
    GOAL_NAME: str = "Financial Freedom"
    GOAL_NAME_RU: str = "Финансовая свобода"
    BRIEFING_MORNING_ENABLED: bool = True
    BRIEFING_EVENING_ENABLED: bool = True
    NOTIFICATION_MODE: str = "smart"  # all, smart, digest_only, critical_only, silent

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Priority: configuration.yaml > options.json > env > default
        # First apply options.json (add-on UI settings)
        self._apply_config(_ha_options)
        # Then apply configuration.yaml (overrides options.json)
        self._apply_config(_ha_config)

    def _apply_config(self, config: dict) -> None:
        """Apply configuration from dict (options.json or configuration.yaml)."""
        if not config:
            return

        # Database settings (highest priority - from crypto_inspect.yaml)
        if config.get("database_url"):
            self.DATABASE_URL = config["database_url"]
            # Also set sync URL if async URL provided
            if "asyncpg" in self.DATABASE_URL:
                self.DATABASE_URL_SYNC = self.DATABASE_URL.replace("+asyncpg", "")
        if config.get("database_url_sync"):
            self.DATABASE_URL_SYNC = config["database_url_sync"]

        # Bybit settings
        if config.get("bybit_api_key"):
            self.BYBIT_API_KEY = config["bybit_api_key"]
        if config.get("bybit_api_secret"):
            self.BYBIT_API_SECRET = config["bybit_api_secret"]
        if "bybit_testnet" in config:
            self.BYBIT_TESTNET = config["bybit_testnet"]

        # API settings
        if "api_enabled" in config:
            self.API_ENABLED = config["api_enabled"]
        if "api_port" in config:
            self.API_PORT = config["api_port"]

        # MCP settings
        if "mcp_enabled" in config:
            self.MCP_ENABLED = config["mcp_enabled"]
        if "mcp_port" in config:
            self.MCP_PORT = config["mcp_port"]

        # Backfill settings
        if "backfill_enabled" in config:
            self.BACKFILL_ENABLED = config["backfill_enabled"]
        if "backfill_crypto_years" in config:
            self.BACKFILL_CRYPTO_YEARS = config["backfill_crypto_years"]
        if "backfill_traditional_years" in config:
            self.BACKFILL_TRADITIONAL_YEARS = config["backfill_traditional_years"]

        # AI settings
        if "ai_enabled" in config:
            self.AI_ENABLED = config["ai_enabled"]
        if "ai_provider" in config:
            self.AI_PROVIDER = config["ai_provider"]
        if config.get("openai_api_key"):
            self.OPENAI_API_KEY = config["openai_api_key"]
        if config.get("ollama_host"):
            self.OLLAMA_HOST = config["ollama_host"]
        if config.get("ollama_model"):
            self.OLLAMA_MODEL = config["ollama_model"]
        if "ai_analysis_interval_hours" in config:
            self.AI_ANALYSIS_INTERVAL_HOURS = config["ai_analysis_interval_hours"]
        if config.get("ai_language"):
            self.AI_LANGUAGE = config["ai_language"]

        # UX Feature settings
        if "goal_enabled" in config:
            self.GOAL_ENABLED = config["goal_enabled"]
        if "goal_target_value" in config:
            self.GOAL_TARGET_VALUE = config["goal_target_value"]
        if config.get("goal_name"):
            self.GOAL_NAME = config["goal_name"]
        if config.get("goal_name_ru"):
            self.GOAL_NAME_RU = config["goal_name_ru"]
        if "briefing_morning_enabled" in config:
            self.BRIEFING_MORNING_ENABLED = config["briefing_morning_enabled"]
        if "briefing_evening_enabled" in config:
            self.BRIEFING_EVENING_ENABLED = config["briefing_evening_enabled"]
        if config.get("notification_mode"):
            self.NOTIFICATION_MODE = config["notification_mode"]

    def get_streaming_symbols(self) -> list[str]:
        """Parse streaming symbols from dynamic currency list or config.

        This method now uses the centralized currency list from Home Assistant input_select helper,
        falling back to environment variables and defaults for backward compatibility.
        """
        # Try to get from dynamic currency list first
        try:
            from service.ha import get_currency_list

            symbols = get_currency_list()
            if symbols:
                return symbols
        except Exception:
            pass

        # Fallback to environment variable
        symbols_str = os.environ.get("HA_SYMBOLS", "").strip()
        if not symbols_str:
            symbols_str = self.STREAMING_SYMBOLS or self.DEFAULT_SYMBOLS

        # Parse and normalize format (BTCUSDT -> BTC/USDT)
        symbols = []
        for s in symbols_str.split(","):
            s = s.strip()
            if not s:
                continue
            # Convert BTCUSDT to BTC/USDT if no slash
            if "/" not in s and "USDT" in s:
                s = s.replace("USDT", "/USDT")
            elif "/" not in s and "USDC" in s:
                s = s.replace("USDC", "/USDC")
            elif "/" not in s and "BUSD" in s:
                s = s.replace("BUSD", "/BUSD")
            symbols.append(s)
        return symbols

    def has_bybit_credentials(self) -> bool:
        """Check if Bybit API credentials are configured."""
        return bool(self.BYBIT_API_KEY and self.BYBIT_API_SECRET)

    def get_backfill_intervals(self) -> list[str]:
        """Parse backfill intervals from config."""
        return [i.strip() for i in self.BACKFILL_INTERVALS.split(",") if i.strip()]

    def is_ai_enabled(self) -> bool:
        """Check if AI analysis is enabled."""
        return self.AI_ENABLED and (self.OPENAI_API_KEY or self.OLLAMA_HOST)


settings = Settings()
