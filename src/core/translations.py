"""
Sensor values translations.

Provides translation of sensor values (signals, trends, etc.) based on configured language.
"""

from __future__ import annotations

from typing import Any

# All sensor value translations
# Key: English value, Value: dict with "ru" translation
SENSOR_VALUE_TRANSLATIONS: dict[str, dict[str, str]] = {
    # Trading signals
    "HOLD": {"ru": "Удержание"},
    "BUY": {"ru": "Покупка"},
    "SELL": {"ru": "Продажа"},
    # MACD signals
    "Bullish": {"ru": "Бычий"},
    "Bearish": {"ru": "Медвежий"},
    "Neutral": {"ru": "Нейтральный"},
    # Trend directions
    "Uptrend": {"ru": "Восходящий"},
    "Downtrend": {"ru": "Нисходящий"},
    "Sideways": {"ru": "Боковик"},
    # Bollinger Bands positions
    "Above Upper": {"ru": "Выше верхней"},
    "Below Lower": {"ru": "Ниже нижней"},
    "Upper Half": {"ru": "Верхняя половина"},
    "Lower Half": {"ru": "Нижняя половина"},
    # Sentiment / Fear & Greed
    "Greedy": {"ru": "Жадность"},
    "Optimistic": {"ru": "Оптимизм"},
    "Cautious": {"ru": "Осторожность"},
    "Fearful": {"ru": "Страх"},
    "Extreme Fear": {"ru": "Крайний страх"},
    "Fear": {"ru": "Страх"},
    "Greed": {"ru": "Жадность"},
    "Extreme Greed": {"ru": "Крайняя жадность"},
    # Zone descriptions
    "Extreme": {"ru": "Экстремум"},
    "Overbought": {"ru": "Перекупленность"},
    "Oversold": {"ru": "Перепроданность"},
    # Divergence
    "No divergence": {"ru": "Нет дивергенций"},
    "Bullish divergence": {"ru": "Бычья дивергенция"},
    "Bearish divergence": {"ru": "Медвежья дивергенция"},
    "Hidden bullish": {"ru": "Скрытая бычья"},
    "Hidden bearish": {"ru": "Скрытая медвежья"},
    "Insufficient data": {"ru": "Недостаточно данных"},
    # Strength
    "weak": {"ru": "слабая"},
    "moderate": {"ru": "умеренная"},
    "strong": {"ru": "сильная"},
    # Market phases
    "Accumulation": {"ru": "Накопление"},
    "Distribution": {"ru": "Распределение"},
    "Markup": {"ru": "Рост"},
    "Markdown": {"ru": "Падение"},
    # Risk levels
    "Low": {"ru": "Низкий"},
    "Medium": {"ru": "Средний"},
    "High": {"ru": "Высокий"},
    "Critical": {"ru": "Критический"},
    "low": {"ru": "низкий"},
    "medium": {"ru": "средний"},
    "high": {"ru": "высокий"},
    "extreme": {"ru": "экстремальный"},
    # Whale signals (enum values)
    "accumulating": {"ru": "накопление"},
    "distributing": {"ru": "распределение"},
    "neutral": {"ru": "нейтрально"},
    # Exchange flow signals (enum values)
    "strong_inflow": {"ru": "сильный приток"},
    "inflow": {"ru": "приток"},
    "outflow": {"ru": "отток"},
    "strong_outflow": {"ru": "сильный отток"},
    # Gas status (enum values)
    "very_cheap": {"ru": "очень дёшево"},
    "cheap": {"ru": "дёшево"},
    "normal": {"ru": "нормально"},
    "expensive": {"ru": "дорого"},
    "very_expensive": {"ru": "очень дорого"},
    # Altseason status (enum values)
    "altcoin_season": {"ru": "сезон альткоинов"},
    "btc_season": {"ru": "сезон BTC"},
    # Sync/system status
    "completed": {"ru": "завершено"},
    "partial": {"ru": "частично"},
    "running": {"ru": "выполняется"},
    "idle": {"ru": "ожидание"},
    "error": {"ru": "ошибка"},
    # ML/AI status
    "Unavailable": {"ru": "Недоступно"},
    "Normal": {"ru": "Нормально"},
    "Low confidence": {"ru": "Низкая уверенность"},
    # Status
    "Active": {"ru": "Активно"},
    "Inactive": {"ru": "Неактивно"},
    "Enabled": {"ru": "Включено"},
    "Disabled": {"ru": "Отключено"},
    # Placeholder
    "—": {"ru": "—"},
    "N/A": {"ru": "Н/Д"},
    "Нет": {"ru": "Нет"},
}


def get_language() -> str:
    """Get configured sensor language from settings."""
    try:
        from core.config import settings

        return settings.AI_LANGUAGE or "en"
    except Exception:
        return "en"


def translate_value(value: str, language: str | None = None) -> str:
    """
    Translate a single sensor value.

    Args:
        value: English value to translate
        language: Target language ('en' or 'ru'). If None, uses config.

    Returns:
        Translated value or original if no translation exists
    """
    if language is None:
        language = get_language()

    if language == "en":
        return value

    translation = SENSOR_VALUE_TRANSLATIONS.get(value)
    if translation and language in translation:
        return translation[language]

    return value


def translate_dict(data: dict[str, Any], language: str | None = None) -> dict[str, Any]:
    """
    Translate all string values in a dictionary.

    Args:
        data: Dictionary with values to translate
        language: Target language ('en' or 'ru'). If None, uses config.

    Returns:
        Dictionary with translated values
    """
    if language is None:
        language = get_language()

    if language == "en":
        return data

    result = {}
    for key, value in data.items():
        if isinstance(value, str):
            result[key] = translate_value(value, language)
        elif isinstance(value, dict):
            # Recursively translate nested dicts
            result[key] = translate_dict(value, language)
        else:
            result[key] = value

    return result


def t(value: str) -> str:
    """
    Shorthand for translate_value with auto language detection.

    Usage:
        from core.translations import t
        signal = t("HOLD")  # Returns "Удержание" if language is "ru"
    """
    return translate_value(value)


def td(data: dict[str, Any]) -> dict[str, Any]:
    """
    Shorthand for translate_dict with auto language detection.

    Usage:
        from core.translations import td
        signals = td({"BTC": "HOLD", "ETH": "BUY"})
    """
    return translate_dict(data)
