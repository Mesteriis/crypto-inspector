"""Constants for Crypto Inspect integration."""

from typing import Final

DOMAIN: Final = "crypto_inspect"

# Configuration
CONF_HOST: Final = "host"
CONF_PORT: Final = "port"
CONF_LANGUAGE: Final = "language"
CONF_UPDATE_INTERVAL: Final = "update_interval"

# Defaults
# For HA Add-on: use addon hostname (e.g. a0d7b954_crypto_inspect)
# For standalone: use localhost or actual IP
DEFAULT_HOST: Final = "a0d7b954_crypto_inspect"
DEFAULT_PORT: Final = 9999
DEFAULT_LANGUAGE: Final = "ru"
DEFAULT_UPDATE_INTERVAL: Final = 60  # seconds

# API endpoints
API_SENSORS_ALL: Final = "/api/integration/sensors"
API_SENSORS_REGISTRY: Final = "/api/integration/registry"
API_HEALTH: Final = "/health"

# Device info
DEVICE_NAME: Final = "Crypto Inspect"
DEVICE_MANUFACTURER: Final = "Crypto Inspect"
DEVICE_MODEL: Final = "Market Intelligence"

# Sensor categories
SENSOR_CATEGORIES: Final = [
    "price",
    "market",
    "investor",
    "technical",
    "volatility",
    "alerts",
    "gas",
    "ml",
    "portfolio",
    "risk",
    "correlation",
    "whales",
    "exchange",
    "bybit",
    "dca",
    "diagnostic",
    "traditional",
    "economic",
    "smart_summary",
    "backtest",
    "ai",
    "misc",
]

# Sensor data types
SENSOR_TYPE_SCALAR: Final = "scalar"
SENSOR_TYPE_DICT: Final = "dict"
SENSOR_TYPE_STATUS: Final = "status"
SENSOR_TYPE_COUNT: Final = "count"
SENSOR_TYPE_BOOL: Final = "bool"
SENSOR_TYPE_PERCENT: Final = "percent"
SENSOR_TYPE_COMPOSITE: Final = "composite"

# Translation mappings for sensor values
VALUE_TRANSLATIONS: Final = {
    # Trading signals
    "HOLD": {"ru": "Удержание", "en": "Hold"},
    "BUY": {"ru": "Покупка", "en": "Buy"},
    "SELL": {"ru": "Продажа", "en": "Sell"},
    # MACD signals
    "Bullish": {"ru": "Бычий", "en": "Bullish"},
    "Bearish": {"ru": "Медвежий", "en": "Bearish"},
    "Neutral": {"ru": "Нейтральный", "en": "Neutral"},
    # Trends
    "Uptrend": {"ru": "Восходящий", "en": "Uptrend"},
    "Downtrend": {"ru": "Нисходящий", "en": "Downtrend"},
    "Sideways": {"ru": "Боковик", "en": "Sideways"},
    # Fear & Greed
    "Extreme Fear": {"ru": "Крайний страх", "en": "Extreme Fear"},
    "Fear": {"ru": "Страх", "en": "Fear"},
    "Greed": {"ru": "Жадность", "en": "Greed"},
    "Extreme Greed": {"ru": "Крайняя жадность", "en": "Extreme Greed"},
    # Market phases
    "Accumulation": {"ru": "Накопление", "en": "Accumulation"},
    "Distribution": {"ru": "Распределение", "en": "Distribution"},
    "Markup": {"ru": "Рост", "en": "Markup"},
    "Markdown": {"ru": "Падение", "en": "Markdown"},
    # Risk levels
    "Low": {"ru": "Низкий", "en": "Low"},
    "Medium": {"ru": "Средний", "en": "Medium"},
    "High": {"ru": "Высокий", "en": "High"},
    "Critical": {"ru": "Критический", "en": "Critical"},
    # Status
    "completed": {"ru": "завершено", "en": "completed"},
    "partial": {"ru": "частично", "en": "partial"},
    "running": {"ru": "выполняется", "en": "running"},
    "idle": {"ru": "ожидание", "en": "idle"},
    "error": {"ru": "ошибка", "en": "error"},
    # Boolean-like
    "Yes": {"ru": "Да", "en": "Yes"},
    "No": {"ru": "Нет", "en": "No"},
    # Gas
    "very_cheap": {"ru": "очень дёшево", "en": "very cheap"},
    "cheap": {"ru": "дёшево", "en": "cheap"},
    "normal": {"ru": "нормально", "en": "normal"},
    "expensive": {"ru": "дорого", "en": "expensive"},
    "very_expensive": {"ru": "очень дорого", "en": "very expensive"},
    # Altseason
    "altcoin_season": {"ru": "сезон альткоинов", "en": "altcoin season"},
    "btc_season": {"ru": "сезон BTC", "en": "BTC season"},
    # Whale signals
    "accumulating": {"ru": "накопление", "en": "accumulating"},
    "distributing": {"ru": "распределение", "en": "distributing"},
    "neutral": {"ru": "нейтрально", "en": "neutral"},
}
