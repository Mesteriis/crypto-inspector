"""
ML Predictor - Прогнозирование на основе исторических паттернов

Методы:
1. Pattern Fingerprinting - создание "отпечатков" рыночных ситуаций
2. Similarity Search - поиск похожих ситуаций в истории
3. Outcome Statistics - статистика исходов похожих ситуаций

Используется для:
- Предсказания вероятного движения цены
- Оценки риска текущей ситуации
- Рекомендаций по действиям
"""

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime

from analysis import TechnicalAnalyzer
from database import CryptoDatabase, get_database

logger = logging.getLogger(__name__)


@dataclass
class MarketFingerprint:
    """Отпечаток рыночной ситуации"""

    symbol: str
    date: str

    # Технические индикаторы (нормализованные)
    rsi: float = 50.0
    price_vs_sma200: float = 0.0  # % от SMA200
    price_vs_sma50: float = 0.0
    macd_histogram: float = 0.0
    bb_position: float = 50.0  # 0-100
    volume_ratio: float = 1.0  # vs SMA

    # Тренд
    trend_4h: str = "neutral"
    trend_daily: str = "neutral"
    trend_weekly: str = "neutral"

    # Внешние факторы
    fear_greed: float | None = None
    funding_rate: float | None = None

    # Цикл
    days_since_halving: int | None = None
    cycle_phase: str | None = None

    # Исход (заполняется позже)
    outcome_7d: float | None = None
    outcome_30d: float | None = None
    outcome_90d: float | None = None

    def to_vector(self) -> list[float]:
        """Преобразовать в числовой вектор для сравнения"""
        # Нормализуем все значения к диапазону 0-1
        vector = [
            self.rsi / 100,
            (self.price_vs_sma200 + 100) / 200,  # -100% to +100% -> 0-1
            (self.price_vs_sma50 + 50) / 100,
            (self.macd_histogram + 1) / 2,  # Примерная нормализация
            self.bb_position / 100,
            min(self.volume_ratio, 3) / 3,  # Cap at 3x
            {"bearish": 0, "neutral": 0.5, "bullish": 1}.get(self.trend_daily, 0.5),
            (self.fear_greed or 50) / 100,
        ]
        return vector

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "date": self.date,
            "indicators": {
                "rsi": self.rsi,
                "price_vs_sma200": self.price_vs_sma200,
                "price_vs_sma50": self.price_vs_sma50,
                "macd_histogram": self.macd_histogram,
                "bb_position": self.bb_position,
                "volume_ratio": self.volume_ratio,
            },
            "trends": {
                "4h": self.trend_4h,
                "daily": self.trend_daily,
                "weekly": self.trend_weekly,
            },
            "external": {
                "fear_greed": self.fear_greed,
                "funding_rate": self.funding_rate,
            },
            "cycle": {
                "days_since_halving": self.days_since_halving,
                "phase": self.cycle_phase,
            },
            "outcomes": {
                "7d": self.outcome_7d,
                "30d": self.outcome_30d,
                "90d": self.outcome_90d,
            },
        }


@dataclass
class PredictionResult:
    """Результат предсказания"""

    symbol: str
    timestamp: int

    # Текущий fingerprint
    current_fingerprint: MarketFingerprint = None

    # Похожие ситуации
    similar_count: int = 0
    similar_situations: list[dict] = field(default_factory=list)

    # Статистика исходов
    avg_outcome_7d: float | None = None
    avg_outcome_30d: float | None = None
    avg_outcome_90d: float | None = None

    positive_outcomes_pct: float | None = None  # % положительных исходов

    # Предсказание
    prediction: str = "neutral"  # 'bullish', 'bearish', 'neutral'
    prediction_ru: str = "Нейтрально"
    confidence: float = 0.0  # 0-100

    # Риск
    risk_level: str = "medium"
    max_drawdown_historical: float | None = None

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "current": self.current_fingerprint.to_dict() if self.current_fingerprint else None,
            "similar": {
                "count": self.similar_count,
                "situations": self.similar_situations[:5],  # Top 5
            },
            "statistics": {
                "avg_outcome_7d": self.avg_outcome_7d,
                "avg_outcome_30d": self.avg_outcome_30d,
                "avg_outcome_90d": self.avg_outcome_90d,
                "positive_pct": self.positive_outcomes_pct,
            },
            "prediction": {
                "direction": self.prediction,
                "direction_ru": self.prediction_ru,
                "confidence": self.confidence,
            },
            "risk": {
                "level": self.risk_level,
                "max_drawdown": self.max_drawdown_historical,
            },
        }

    def get_summary_ru(self) -> str:
        """Получить резюме на русском"""
        parts = [
            f"🔮 **ML Прогноз: {self.symbol}**",
            "",
            f"📊 Найдено похожих ситуаций: {self.similar_count}",
        ]

        if self.similar_count > 0:
            parts.append("")
            parts.append("**Статистика исходов:**")

            if self.avg_outcome_7d is not None:
                emoji_7d = "📈" if self.avg_outcome_7d > 0 else "📉"
                parts.append(f"  • 7 дней: {emoji_7d} {self.avg_outcome_7d:+.1f}%")

            if self.avg_outcome_30d is not None:
                emoji_30d = "📈" if self.avg_outcome_30d > 0 else "📉"
                parts.append(f"  • 30 дней: {emoji_30d} {self.avg_outcome_30d:+.1f}%")

            if self.positive_outcomes_pct is not None:
                parts.append(f"  • Положительных: {self.positive_outcomes_pct:.0f}%")

        parts.extend(
            [
                "",
                f"**Прогноз:** {self.prediction_ru}",
                f"**Уверенность:** {self.confidence:.0f}%",
                f"**Уровень риска:** {self.risk_level}",
            ]
        )

        return "\n".join(parts)


class MLPredictor:
    """ML предиктор на основе исторических паттернов"""

    def __init__(self, db: CryptoDatabase | None = None):
        self.db = db or get_database()
        self.ta = TechnicalAnalyzer(self.db)

    def create_fingerprint(
        self, symbol: str, date: str | None = None, indicators=None
    ) -> MarketFingerprint:
        """
        Создать fingerprint для даты

        Args:
            symbol: Символ монеты
            date: Дата (по умолчанию сегодня)
            indicators: Уже рассчитанные индикаторы (опционально)

        Returns:
            MarketFingerprint
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        fp = MarketFingerprint(symbol=symbol.upper(), date=date)

        # Получаем индикаторы
        if indicators is None:
            indicators = self.ta.analyze(symbol, "1d")

        if indicators:
            fp.rsi = indicators.rsi or 50
            fp.bb_position = indicators.bb_position or 50
            fp.volume_ratio = indicators.volume_ratio or 1.0

            if indicators.macd_histogram:
                fp.macd_histogram = indicators.macd_histogram

            if indicators.sma_200 and indicators.price:
                fp.price_vs_sma200 = (
                    (indicators.price - indicators.sma_200) / indicators.sma_200
                ) * 100

            if indicators.sma_50 and indicators.price:
                fp.price_vs_sma50 = (
                    (indicators.price - indicators.sma_50) / indicators.sma_50
                ) * 100

        return fp

    def calculate_similarity(self, fp1: MarketFingerprint, fp2: MarketFingerprint) -> float:
        """
        Рассчитать схожесть двух fingerprints

        Returns:
            Similarity score 0-100 (100 = идентичны)
        """
        v1 = fp1.to_vector()
        v2 = fp2.to_vector()

        # Евклидово расстояние
        distance = math.sqrt(sum((a - b) ** 2 for a, b in zip(v1, v2)))

        # Преобразуем в similarity (0-100)
        # max_distance примерно sqrt(8) ≈ 2.83 для вектора из 8 элементов
        max_distance = math.sqrt(len(v1))
        similarity = (1 - distance / max_distance) * 100

        return max(0, min(100, similarity))

    def find_similar_situations(
        self, current: MarketFingerprint, min_similarity: float = 70, limit: int = 50
    ) -> list[tuple[MarketFingerprint, float]]:
        """
        Найти похожие исторические ситуации

        Args:
            current: Текущий fingerprint
            min_similarity: Минимальный порог схожести
            limit: Максимум результатов

        Returns:
            Список (fingerprint, similarity)
        """
        # Получаем исторические fingerprints из БД
        historical = self.db.find_similar_fingerprints(
            symbol=current.symbol,
            current={
                "rsi": current.rsi,
                "price_vs_sma200": current.price_vs_sma200,
                "fear_greed": current.fear_greed,
                "cycle_phase": current.cycle_phase,
            },
            limit=limit * 2,  # Берём больше для фильтрации
        )

        results = []

        for hist in historical:
            # Создаём fingerprint из записи БД
            hist_fp = MarketFingerprint(
                symbol=hist["symbol"],
                date=hist["date"],
                rsi=hist.get("rsi", 50),
                price_vs_sma200=hist.get("price_vs_sma200", 0),
                price_vs_sma50=hist.get("price_vs_sma50", 0),
                macd_histogram=hist.get("macd_histogram", 0),
                bb_position=hist.get("bb_position", 50),
                volume_ratio=hist.get("volume_sma_ratio", 1),
                fear_greed=hist.get("fear_greed"),
                days_since_halving=hist.get("days_since_halving"),
                cycle_phase=hist.get("cycle_phase"),
                outcome_7d=hist.get("outcome_7d"),
                outcome_30d=hist.get("outcome_30d"),
                outcome_90d=hist.get("outcome_90d"),
            )

            similarity = self.calculate_similarity(current, hist_fp)

            if similarity >= min_similarity:
                results.append((hist_fp, similarity))

        # Сортируем по схожести
        results.sort(key=lambda x: x[1], reverse=True)

        return results[:limit]

    def calculate_outcome_statistics(self, similar: list[tuple[MarketFingerprint, float]]) -> dict:
        """
        Рассчитать статистику исходов похожих ситуаций

        Returns:
            Dict со статистикой
        """
        if not similar:
            return {}

        outcomes_7d = [fp.outcome_7d for fp, _ in similar if fp.outcome_7d is not None]
        outcomes_30d = [fp.outcome_30d for fp, _ in similar if fp.outcome_30d is not None]
        outcomes_90d = [fp.outcome_90d for fp, _ in similar if fp.outcome_90d is not None]

        stats = {}

        if outcomes_7d:
            stats["avg_7d"] = sum(outcomes_7d) / len(outcomes_7d)
            stats["positive_7d_pct"] = (
                sum(1 for o in outcomes_7d if o > 0) / len(outcomes_7d)
            ) * 100
            stats["max_gain_7d"] = max(outcomes_7d)
            stats["max_loss_7d"] = min(outcomes_7d)

        if outcomes_30d:
            stats["avg_30d"] = sum(outcomes_30d) / len(outcomes_30d)
            stats["positive_30d_pct"] = (
                sum(1 for o in outcomes_30d if o > 0) / len(outcomes_30d)
            ) * 100
            stats["max_gain_30d"] = max(outcomes_30d)
            stats["max_loss_30d"] = min(outcomes_30d)

        if outcomes_90d:
            stats["avg_90d"] = sum(outcomes_90d) / len(outcomes_90d)
            stats["positive_90d_pct"] = (
                sum(1 for o in outcomes_90d if o > 0) / len(outcomes_90d)
            ) * 100

        return stats

    def predict(self, symbol: str) -> PredictionResult:
        """
        Сделать предсказание для символа

        Args:
            symbol: Символ монеты

        Returns:
            PredictionResult
        """
        result = PredictionResult(
            symbol=symbol.upper(), timestamp=int(datetime.now().timestamp() * 1000)
        )

        # Создаём текущий fingerprint
        current_fp = self.create_fingerprint(symbol)
        result.current_fingerprint = current_fp

        # Ищем похожие ситуации
        similar = self.find_similar_situations(current_fp, min_similarity=60)
        result.similar_count = len(similar)

        # Сохраняем топ похожих для отображения
        result.similar_situations = [
            {
                "date": fp.date,
                "similarity": round(sim, 1),
                "outcome_7d": fp.outcome_7d,
                "outcome_30d": fp.outcome_30d,
            }
            for fp, sim in similar[:10]
        ]

        if not similar:
            result.prediction = "neutral"
            result.prediction_ru = "⚪ Недостаточно данных"
            result.confidence = 0
            return result

        # Рассчитываем статистику
        stats = self.calculate_outcome_statistics(similar)

        result.avg_outcome_7d = stats.get("avg_7d")
        result.avg_outcome_30d = stats.get("avg_30d")
        result.avg_outcome_90d = stats.get("avg_90d")
        result.positive_outcomes_pct = stats.get("positive_30d_pct", 50)
        result.max_drawdown_historical = stats.get("max_loss_30d")

        # Определяем предсказание
        avg_30d = stats.get("avg_30d", 0)
        positive_pct = stats.get("positive_30d_pct", 50)

        if avg_30d > 5 and positive_pct > 60:
            result.prediction = "bullish"
            result.prediction_ru = "🟢 Бычий прогноз"
            result.confidence = min(90, positive_pct)
        elif avg_30d > 2 and positive_pct > 55:
            result.prediction = "slightly_bullish"
            result.prediction_ru = "🟢 Умеренно бычий"
            result.confidence = min(75, positive_pct)
        elif avg_30d < -5 and positive_pct < 40:
            result.prediction = "bearish"
            result.prediction_ru = "🔴 Медвежий прогноз"
            result.confidence = min(90, 100 - positive_pct)
        elif avg_30d < -2 and positive_pct < 45:
            result.prediction = "slightly_bearish"
            result.prediction_ru = "🔴 Умеренно медвежий"
            result.confidence = min(75, 100 - positive_pct)
        else:
            result.prediction = "neutral"
            result.prediction_ru = "⚪ Нейтрально"
            result.confidence = 50

        # Определяем риск
        max_loss = abs(stats.get("max_loss_30d", 0))
        if max_loss > 30:
            result.risk_level = "extreme"
        elif max_loss > 20:
            result.risk_level = "high"
        elif max_loss > 10:
            result.risk_level = "medium"
        else:
            result.risk_level = "low"

        return result

    def generate_fingerprints_for_history(self, symbol: str, days: int = 365) -> int:
        """
        Сгенерировать fingerprints для исторических данных

        Args:
            symbol: Символ
            days: Количество дней

        Returns:
            Количество созданных fingerprints
        """
        candles = self.db.get_ohlcv(symbol, "1d", limit=days + 200)

        if len(candles) < 250:
            logger.warning(f"Недостаточно данных для {symbol}")
            return 0

        count = 0
        closes = [c["close"] for c in candles]

        for i in range(200, len(candles)):
            candle = candles[i]
            date = datetime.fromtimestamp(candle["timestamp"] / 1000).strftime("%Y-%m-%d")

            # Рассчитываем индикаторы для этой точки
            window_closes = closes[: i + 1]

            rsi = self.ta.calc_rsi(window_closes, 14) or 50
            sma_200 = self.ta.calc_sma(window_closes, 200)
            sma_50 = self.ta.calc_sma(window_closes, 50)
            bb_upper, bb_mid, bb_lower, bb_pos = self.ta.calc_bollinger_bands(window_closes)

            price = window_closes[-1]

            # Рассчитываем outcomes
            outcome_7d = None
            outcome_30d = None
            outcome_90d = None

            if i + 7 < len(candles):
                outcome_7d = ((closes[i + 7] - price) / price) * 100
            if i + 30 < len(candles):
                outcome_30d = ((closes[i + 30] - price) / price) * 100
            if i + 90 < len(candles):
                outcome_90d = ((closes[i + 90] - price) / price) * 100

            # Сохраняем в БД
            self.db.insert_fingerprint(
                symbol,
                date,
                {
                    "rsi": rsi,
                    "price_vs_sma200": ((price - sma_200) / sma_200 * 100) if sma_200 else None,
                    "price_vs_sma50": ((price - sma_50) / sma_50 * 100) if sma_50 else None,
                    "bb_position": bb_pos,
                    "outcome_7d": outcome_7d,
                    "outcome_30d": outcome_30d,
                    "outcome_90d": outcome_90d,
                },
            )

            count += 1

        logger.info(f"Создано {count} fingerprints для {symbol}")
        return count


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import json

    logging.basicConfig(level=logging.INFO)

    predictor = MLPredictor()

    # Генерируем fingerprints (если нужно)
    # predictor.generate_fingerprints_for_history('BTC', days=365)

    # Делаем предсказание
    result = predictor.predict("BTC")

    print("\n" + "=" * 60)
    print("ML PREDICTION")
    print("=" * 60)
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))

    print("\n" + "=" * 60)
    print("SUMMARY (RU)")
    print("=" * 60)
    print(result.get_summary_ru())
