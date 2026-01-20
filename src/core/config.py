import json
import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from core.constants import (
    DEFAULT_SYMBOLS_STR,
    MAX_RETRIES,
    RETRY_DELAY_SECONDS,
    Timeouts,
)


def load_ha_options() -> dict:
    """Load options from Home Assistant add-on config."""
    options_path = Path("/data/options.json")
    if options_path.exists():
        try:
            return json.loads(options_path.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


# Load HA options once at module level
_ha_options = load_ha_options()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Application
    APP_NAME: str = "crypto-inspect"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/crypto_inspect"
    DATABASE_URL_SYNC: str = "postgresql://postgres:postgres@localhost:5432/crypto_inspect"

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
        # Override with HA options if available (priority: HA options > env > default)
        if _ha_options:
            if _ha_options.get("bybit_api_key"):
                self.BYBIT_API_KEY = _ha_options["bybit_api_key"]
            if _ha_options.get("bybit_api_secret"):
                self.BYBIT_API_SECRET = _ha_options["bybit_api_secret"]
            if "bybit_testnet" in _ha_options:
                self.BYBIT_TESTNET = _ha_options["bybit_testnet"]
            # API settings
            if "api_enabled" in _ha_options:
                self.API_ENABLED = _ha_options["api_enabled"]
            if "api_port" in _ha_options:
                self.API_PORT = _ha_options["api_port"]
            
            # MCP settings
            if "mcp_enabled" in _ha_options:
                self.MCP_ENABLED = _ha_options["mcp_enabled"]
            if "mcp_port" in _ha_options:
                self.MCP_PORT = _ha_options["mcp_port"]
            # Backfill settings
            if "backfill_enabled" in _ha_options:
                self.BACKFILL_ENABLED = _ha_options["backfill_enabled"]
            if "backfill_crypto_years" in _ha_options:
                self.BACKFILL_CRYPTO_YEARS = _ha_options["backfill_crypto_years"]
            if "backfill_traditional_years" in _ha_options:
                self.BACKFILL_TRADITIONAL_YEARS = _ha_options["backfill_traditional_years"]
            # AI settings
            if "ai_enabled" in _ha_options:
                self.AI_ENABLED = _ha_options["ai_enabled"]
            if "ai_provider" in _ha_options:
                self.AI_PROVIDER = _ha_options["ai_provider"]
            if _ha_options.get("openai_api_key"):
                self.OPENAI_API_KEY = _ha_options["openai_api_key"]
            if _ha_options.get("ollama_host"):
                self.OLLAMA_HOST = _ha_options["ollama_host"]
            if _ha_options.get("ollama_model"):
                self.OLLAMA_MODEL = _ha_options["ollama_model"]
            if "ai_analysis_interval_hours" in _ha_options:
                self.AI_ANALYSIS_INTERVAL_HOURS = _ha_options["ai_analysis_interval_hours"]
            if _ha_options.get("ai_language"):
                self.AI_LANGUAGE = _ha_options["ai_language"]
            # UX Feature settings
            if "goal_enabled" in _ha_options:
                self.GOAL_ENABLED = _ha_options["goal_enabled"]
            if "goal_target_value" in _ha_options:
                self.GOAL_TARGET_VALUE = _ha_options["goal_target_value"]
            if _ha_options.get("goal_name"):
                self.GOAL_NAME = _ha_options["goal_name"]
            if _ha_options.get("goal_name_ru"):
                self.GOAL_NAME_RU = _ha_options["goal_name_ru"]
            if "briefing_morning_enabled" in _ha_options:
                self.BRIEFING_MORNING_ENABLED = _ha_options["briefing_morning_enabled"]
            if "briefing_evening_enabled" in _ha_options:
                self.BRIEFING_EVENING_ENABLED = _ha_options["briefing_evening_enabled"]
            if _ha_options.get("notification_mode"):
                self.NOTIFICATION_MODE = _ha_options["notification_mode"]

    def get_streaming_symbols(self) -> list[str]:
        """Parse streaming symbols from dynamic currency list or config.
        
        This method now uses the centralized currency list from Home Assistant input_select helper,
        falling back to environment variables and defaults for backward compatibility.
        """
        # Try to get from dynamic currency list first
        try:
            from services.ha_sensors import get_currency_list
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
