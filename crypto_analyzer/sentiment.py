"""
Sentiment Analyzer - Анализ настроений рынка

Источники:
- Fear & Greed Index (Alternative.me)
- Social Volume (placeholder для LunarCrush)
- Google Trends (через pytrends)

Функции:
- Сбор индексов настроений
- Анализ социальной активности
- Трендовый анализ
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime

import aiohttp
from config_loader import get_api_key
from database import CryptoDatabase, get_database

logger = logging.getLogger(__name__)


# API Endpoints
FEAR_GREED_URL = "https://api.alternative.me/fng/"


@dataclass
class SentimentData:
    """Данные sentiment анализа"""

    timestamp: int

    # Fear & Greed Index
    fear_greed: int = 50
    fear_greed_class: str = "Neutral"  # Extreme Fear, Fear, Neutral, Greed, Extreme Greed
    fear_greed_class_ru: str = "Нейтрально"
    fear_greed_history: list[dict] = field(default_factory=list)

    # Social Volume (placeholder)
    social_volume: int = 0
    social_change_24h: float = 0.0
    social_dominance: float = 0.0

    # Google Trends (placeholder)
    google_trend: int = 0
    google_trend_change: float = 0.0

    # Комбинированный score
    combined_score: float = 50.0  # 0-100
    combined_signal: str = "neutral"
    combined_signal_ru: str = "Нейтрально"

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "fear_greed": {
                "value": self.fear_greed,
                "class": self.fear_greed_class,
                "class_ru": self.fear_greed_class_ru,
                "history_7d": self.fear_greed_history[:7],
            },
            "social": {
                "volume": self.social_volume,
                "change_24h": self.social_change_24h,
                "dominance": self.social_dominance,
            },
            "google_trends": {
                "value": self.google_trend,
                "change": self.google_trend_change,
            },
            "combined": {
                "score": self.combined_score,
                "signal": self.combined_signal,
                "signal_ru": self.combined_signal_ru,
            },
        }

    def get_summary_ru(self) -> str:
        """Резюме на русском"""
        # Emoji для Fear & Greed
        if self.fear_greed <= 20:
            fg_emoji = "😱"
        elif self.fear_greed <= 40:
            fg_emoji = "😨"
        elif self.fear_greed <= 60:
            fg_emoji = "😐"
        elif self.fear_greed <= 80:
            fg_emoji = "😊"
        else:
            fg_emoji = "🤑"

        parts = [
            "📊 **Sentiment Analysis**",
            "",
            f"{fg_emoji} Fear & Greed: **{self.fear_greed}** ({self.fear_greed_class_ru})",
        ]

        if self.social_volume > 0:
            change = (
                f"+{self.social_change_24h:.1f}%"
                if self.social_change_24h > 0
                else f"{self.social_change_24h:.1f}%"
            )
            parts.append(f"💬 Social Volume: {self.social_volume:,} ({change})")

        if self.google_trend > 0:
            parts.append(f"🔍 Google Trends: {self.google_trend}")

        parts.extend(
            [
                "",
                f"🎯 Комбинированный score: **{self.combined_score:.0f}**/100",
                f"📈 Сигнал: **{self.combined_signal_ru}**",
            ]
        )

        # Рекомендация
        if self.combined_score <= 25:
            parts.append(
                "\n💡 *Экстремальный страх - потенциально хорошая возможность для покупки*"
            )
        elif self.combined_score >= 75:
            parts.append("\n⚠️ *Экстремальная жадность - рассмотрите фиксацию прибыли*")

        return "\n".join(parts)


class SentimentAnalyzer:
    """Анализатор рыночных настроений"""

    # Маппинг Fear & Greed классов на русский
    FG_CLASS_MAP = {
        "Extreme Fear": "Экстремальный страх",
        "Fear": "Страх",
        "Neutral": "Нейтрально",
        "Greed": "Жадность",
        "Extreme Greed": "Экстремальная жадность",
    }

    def __init__(self, db: CryptoDatabase | None = None):
        self.db = db or get_database()
        self._session: aiohttp.ClientSession | None = None

        # API ключи (загружаются из config/secrets)
        self.lunarcrush_key = get_api_key("lunarcrush")
        self.santiment_key = get_api_key("santiment")

        if self.lunarcrush_key:
            logger.info("LunarCrush API key configured - social volume available")

    async def _get_session(self) -> aiohttp.ClientSession:
        """Получить HTTP сессию"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self):
        """Закрыть сессию"""
        if self._session and not self._session.closed:
            await self._session.close()

    async def fetch_fear_greed_index(self, days: int = 30) -> dict | None:
        """
        Получить Fear & Greed Index

        Args:
            days: Количество дней истории

        Returns:
            Данные индекса
        """
        session = await self._get_session()

        try:
            params = {"limit": days}
            async with session.get(FEAR_GREED_URL, params=params) as response:
                if response.status != 200:
                    logger.error(f"Fear & Greed API error: {response.status}")
                    return None

                data = await response.json()

                if not data.get("data"):
                    return None

                current = data["data"][0]

                return {
                    "value": int(current.get("value", 50)),
                    "class": current.get("value_classification", "Neutral"),
                    "timestamp": int(current.get("timestamp", 0)),
                    "history": [
                        {
                            "value": int(d.get("value", 50)),
                            "class": d.get("value_classification", "Neutral"),
                            "timestamp": int(d.get("timestamp", 0)),
                        }
                        for d in data["data"][:30]
                    ],
                }

        except Exception as e:
            logger.error(f"Fear & Greed error: {e}")
            return None

    async def fetch_social_volume(self, symbol: str = "BTC") -> dict | None:
        """
        Получить social volume
        Placeholder - требуется API LunarCrush или аналог

        Args:
            symbol: Символ монеты

        Returns:
            Данные social volume
        """
        # Placeholder - вернём демо данные
        # В реальности нужен API LunarCrush, Santiment и т.д.
        return {"volume": 0, "change_24h": 0.0, "dominance": 0.0, "source": "placeholder"}

    async def fetch_google_trends(self, query: str = "bitcoin") -> dict | None:
        """
        Получить данные Google Trends
        Placeholder - требуется pytrends

        Args:
            query: Поисковый запрос

        Returns:
            Данные трендов
        """
        # Placeholder - для реализации нужен pytrends
        # from pytrends.request import TrendReq
        return {"value": 0, "change": 0.0, "source": "placeholder"}

    def _calculate_combined_score(
        self, fear_greed: int, social_volume: int = 0, google_trend: int = 0
    ) -> tuple:
        """
        Рассчитать комбинированный score

        Returns:
            (score, signal, signal_ru)
        """
        # Веса компонентов
        # Fear & Greed - основной индикатор
        weights = {
            "fear_greed": 0.7,
            "social": 0.2,
            "google": 0.1,
        }

        # Нормализуем все к 0-100
        # Fear & Greed уже 0-100
        fg_normalized = fear_greed

        # Social volume - если данных нет, не учитываем
        if social_volume > 0:
            # Примерная нормализация
            social_normalized = min(100, social_volume / 10000)
        else:
            social_normalized = 50  # Нейтрально
            weights["social"] = 0
            weights["fear_greed"] += 0.15
            weights["google"] += 0.05

        # Google Trends - если данных нет, не учитываем
        if google_trend > 0:
            google_normalized = google_trend
        else:
            google_normalized = 50  # Нейтрально
            weights["google"] = 0
            weights["fear_greed"] += 0.05

        # Комбинированный score
        score = (
            fg_normalized * weights["fear_greed"]
            + social_normalized * weights["social"]
            + google_normalized * weights["google"]
        )

        # Определяем сигнал
        if score <= 20:
            signal = "extreme_fear"
            signal_ru = "Экстремальный страх"
        elif score <= 40:
            signal = "fear"
            signal_ru = "Страх"
        elif score <= 60:
            signal = "neutral"
            signal_ru = "Нейтрально"
        elif score <= 80:
            signal = "greed"
            signal_ru = "Жадность"
        else:
            signal = "extreme_greed"
            signal_ru = "Экстремальная жадность"

        return score, signal, signal_ru

    async def analyze(self, symbol: str = "BTC") -> SentimentData:
        """
        Полный анализ sentiment

        Args:
            symbol: Символ для анализа

        Returns:
            SentimentData
        """
        data = SentimentData(timestamp=int(datetime.now().timestamp() * 1000))

        # Собираем данные параллельно
        tasks = [
            self.fetch_fear_greed_index(),
            self.fetch_social_volume(symbol),
            self.fetch_google_trends(symbol.lower()),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Fear & Greed
        fg_data = results[0] if not isinstance(results[0], Exception) else None
        if fg_data:
            data.fear_greed = fg_data.get("value", 50)
            data.fear_greed_class = fg_data.get("class", "Neutral")
            data.fear_greed_class_ru = self.FG_CLASS_MAP.get(data.fear_greed_class, "Нейтрально")
            data.fear_greed_history = fg_data.get("history", [])

        # Social Volume
        social_data = results[1] if not isinstance(results[1], Exception) else None
        if social_data:
            data.social_volume = social_data.get("volume", 0)
            data.social_change_24h = social_data.get("change_24h", 0.0)
            data.social_dominance = social_data.get("dominance", 0.0)

        # Google Trends
        google_data = results[2] if not isinstance(results[2], Exception) else None
        if google_data:
            data.google_trend = google_data.get("value", 0)
            data.google_trend_change = google_data.get("change", 0.0)

        # Комбинированный score
        data.combined_score, data.combined_signal, data.combined_signal_ru = (
            self._calculate_combined_score(data.fear_greed, data.social_volume, data.google_trend)
        )

        return data

    def get_trading_signal(self, sentiment: SentimentData) -> dict:
        """
        Получить торговый сигнал на основе sentiment

        Стратегия:
        - Extreme Fear (< 20) - потенциальная покупка
        - Fear (20-40) - присмотреться к покупке
        - Neutral (40-60) - держать
        - Greed (60-80) - присмотреться к продаже
        - Extreme Greed (> 80) - потенциальная продажа

        Args:
            sentiment: Данные sentiment

        Returns:
            Сигнал
        """
        score = sentiment.combined_score

        if score <= 20:
            return {
                "signal": "strong_buy",
                "signal_ru": "Сильный сигнал к покупке",
                "confidence": 0.8,
                "description": "Экстремальный страх на рынке - исторически хорошая точка входа",
                "description_ru": "Экстремальный страх на рынке - исторически хорошая точка входа",
            }
        elif score <= 35:
            return {
                "signal": "buy",
                "signal_ru": "Сигнал к покупке",
                "confidence": 0.6,
                "description": "Страх на рынке - рассмотрите покупку",
                "description_ru": "Страх на рынке - рассмотрите покупку",
            }
        elif score <= 45:
            return {
                "signal": "weak_buy",
                "signal_ru": "Слабый сигнал к покупке",
                "confidence": 0.4,
                "description": "Умеренный страх - можно присматриваться",
                "description_ru": "Умеренный страх - можно присматриваться",
            }
        elif score <= 55:
            return {
                "signal": "hold",
                "signal_ru": "Держать",
                "confidence": 0.5,
                "description": "Нейтральный рынок - без явного сигнала",
                "description_ru": "Нейтральный рынок - без явного сигнала",
            }
        elif score <= 65:
            return {
                "signal": "weak_sell",
                "signal_ru": "Слабый сигнал к продаже",
                "confidence": 0.4,
                "description": "Умеренная жадность - осторожность",
                "description_ru": "Умеренная жадность - проявите осторожность",
            }
        elif score <= 80:
            return {
                "signal": "sell",
                "signal_ru": "Сигнал к продаже",
                "confidence": 0.6,
                "description": "Жадность на рынке - рассмотрите фиксацию прибыли",
                "description_ru": "Жадность на рынке - рассмотрите фиксацию прибыли",
            }
        else:
            return {
                "signal": "strong_sell",
                "signal_ru": "Сильный сигнал к продаже",
                "confidence": 0.8,
                "description": "Экстремальная жадность - возможна коррекция",
                "description_ru": "Экстремальная жадность - высокий риск коррекции",
            }


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import json

    logging.basicConfig(level=logging.INFO)

    async def main():
        analyzer = SentimentAnalyzer()

        try:
            print("Analyzing sentiment...")
            sentiment = await analyzer.analyze("BTC")

            print("\n" + "=" * 60)
            print("SENTIMENT DATA")
            print("=" * 60)
            print(json.dumps(sentiment.to_dict(), indent=2, ensure_ascii=False))

            print("\n" + "=" * 60)
            print("SUMMARY (RU)")
            print("=" * 60)
            print(sentiment.get_summary_ru())

            print("\n" + "=" * 60)
            print("TRADING SIGNAL")
            print("=" * 60)
            signal = analyzer.get_trading_signal(sentiment)
            print(json.dumps(signal, indent=2, ensure_ascii=False))

        finally:
            await analyzer.close()

    asyncio.run(main())
