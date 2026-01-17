from pydantic_settings import BaseSettings, SettingsConfigDict


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
    STREAMING_SYMBOLS: str = "BTC/USDT,ETH/USDT,SOL/USDT,TON/USDT,AR/USDT"
    STREAMING_INTERVAL: str = "1m"  # 1m, 5m, 15m, 1h, etc.

    def get_streaming_symbols(self) -> list[str]:
        """Parse streaming symbols from config."""
        return [s.strip() for s in self.STREAMING_SYMBOLS.split(",") if s.strip()]


settings = Settings()
