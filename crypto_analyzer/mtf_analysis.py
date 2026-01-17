"""
Multi-Timeframe Analysis - Анализ на нескольких таймфреймах

Таймфреймы:
- 4H: Краткосрочные сигналы, точки входа
- Daily (1D): Основной таймфрейм, среднесрочные тренды
- Weekly (1W): Долгосрочные тренды, cycle analysis

Функции:
- MTF Confluence scoring - схождение сигналов
- Divergence detection - расхождения между TF
- Key levels по таймфреймам
"""

import logging
from dataclasses import dataclass, field

from analysis import TechnicalAnalyzer, TechnicalIndicators
from database import CryptoDatabase, get_database

logger = logging.getLogger(__name__)


@dataclass
class TimeframeAnalysis:
    """Анализ одного таймфрейма"""

    timeframe: str
    indicators: TechnicalIndicators | None
    trend: str  # 'bullish', 'bearish', 'neutral'
    trend_ru: str
    strength: int  # 1-10
    signal: str
    signal_ru: str
    details: list[dict] = field(default_factory=list)


@dataclass
class MTFAnalysis:
    """Результат Multi-Timeframe анализа"""

    symbol: str
    timestamp: int
    price: float

    # Анализ по таймфреймам
    tf_4h: TimeframeAnalysis | None = None
    tf_daily: TimeframeAnalysis | None = None
    tf_weekly: TimeframeAnalysis | None = None

    # Confluence
    confluence_score: float = 50.0  # 0-100
    confluence_signal: str = "neutral"
    confluence_signal_ru: str = "Нейтрально"

    # Divergences
    has_divergence: bool = False
    divergence_type: str | None = None
    divergence_description: str | None = None

    # Key levels
    key_levels: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Преобразование в словарь"""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "price": self.price,
            "timeframes": {
                "4h": self._tf_to_dict(self.tf_4h),
                "1d": self._tf_to_dict(self.tf_daily),
                "1w": self._tf_to_dict(self.tf_weekly),
            },
            "confluence": {
                "score": self.confluence_score,
                "signal": self.confluence_signal,
                "signal_ru": self.confluence_signal_ru,
            },
            "divergence": {
                "has_divergence": self.has_divergence,
                "type": self.divergence_type,
                "description": self.divergence_description,
            },
            "key_levels": self.key_levels,
        }

    @staticmethod
    def _tf_to_dict(tf: TimeframeAnalysis | None) -> dict | None:
        if not tf:
            return None
        return {
            "timeframe": tf.timeframe,
            "trend": tf.trend,
            "trend_ru": tf.trend_ru,
            "strength": tf.strength,
            "signal": tf.signal,
            "signal_ru": tf.signal_ru,
            "details": tf.details,
            "indicators": tf.indicators.to_dict() if tf.indicators else None,
        }


class MTFAnalyzer:
    """Multi-Timeframe Analyzer"""

    # Веса таймфреймов для confluence
    TIMEFRAME_WEIGHTS = {
        "4h": 0.2,  # 20% - краткосрок
        "1d": 0.5,  # 50% - основной
        "1w": 0.3,  # 30% - долгосрок
    }

    def __init__(self, db: CryptoDatabase | None = None):
        self.db = db or get_database()
        self.ta = TechnicalAnalyzer(self.db)

    def analyze_timeframe(self, symbol: str, timeframe: str) -> TimeframeAnalysis | None:
        """
        Анализ одного таймфрейма

        Args:
            symbol: Символ монеты
            timeframe: Таймфрейм ('4h', '1d', '1w')

        Returns:
            TimeframeAnalysis или None
        """
        # Получаем индикаторы
        indicators = self.ta.analyze(symbol, timeframe)

        if not indicators:
            return None

        # Определяем тренд
        trend, trend_ru, strength = self._determine_trend(indicators)

        # Формируем сигнал
        signal, signal_ru, details = self._generate_signal(indicators, trend)

        return TimeframeAnalysis(
            timeframe=timeframe,
            indicators=indicators,
            trend=trend,
            trend_ru=trend_ru,
            strength=strength,
            signal=signal,
            signal_ru=signal_ru,
            details=details,
        )

    def _determine_trend(self, indicators: TechnicalIndicators) -> tuple[str, str, int]:
        """
        Определить тренд на основе индикаторов

        Returns:
            Tuple (trend, trend_ru, strength 1-10)
        """
        bullish_points = 0
        bearish_points = 0
        total_points = 0

        # SMA200 (вес 3)
        if indicators.sma_200 and indicators.price:
            total_points += 3
            if indicators.price > indicators.sma_200:
                bullish_points += 3
            else:
                bearish_points += 3

        # SMA50 vs SMA200 (вес 2)
        if indicators.sma_50 and indicators.sma_200:
            total_points += 2
            if indicators.sma_50 > indicators.sma_200:
                bullish_points += 2
            else:
                bearish_points += 2

        # Price vs SMA50 (вес 2)
        if indicators.sma_50 and indicators.price:
            total_points += 2
            if indicators.price > indicators.sma_50:
                bullish_points += 2
            else:
                bearish_points += 2

        # RSI (вес 2)
        if indicators.rsi:
            total_points += 2
            if indicators.rsi > 50:
                bullish_points += 2
            elif indicators.rsi < 50:
                bearish_points += 2

        # MACD (вес 1)
        if indicators.macd_histogram is not None:
            total_points += 1
            if indicators.macd_histogram > 0:
                bullish_points += 1
            else:
                bearish_points += 1

        # Определяем тренд
        if total_points == 0:
            return "neutral", "Нейтрально", 5

        ratio = (bullish_points - bearish_points) / total_points
        strength = int(5 + ratio * 5)  # 0-10
        strength = max(1, min(10, strength))

        if ratio > 0.3:
            return "bullish", "Бычий", strength
        elif ratio < -0.3:
            return "bearish", "Медвежий", strength
        else:
            return "neutral", "Нейтральный", strength

    def _generate_signal(
        self, indicators: TechnicalIndicators, trend: str
    ) -> tuple[str, str, list[dict]]:
        """
        Сгенерировать сигнал для таймфрейма

        Returns:
            Tuple (signal, signal_ru, details)
        """
        details = []

        # EMA trend
        if indicators.ema_12 and indicators.ema_26:
            if indicators.ema_12 > indicators.ema_26:
                details.append({"indicator": "EMA", "status": "bullish", "text": "EMA12 > EMA26"})
            else:
                details.append({"indicator": "EMA", "status": "bearish", "text": "EMA12 < EMA26"})

        # RSI status
        if indicators.rsi:
            if indicators.rsi < 30:
                details.append(
                    {
                        "indicator": "RSI",
                        "status": "oversold",
                        "text": f"RSI {indicators.rsi:.0f} (перепродан)",
                    }
                )
            elif indicators.rsi > 70:
                details.append(
                    {
                        "indicator": "RSI",
                        "status": "overbought",
                        "text": f"RSI {indicators.rsi:.0f} (перекуплен)",
                    }
                )
            else:
                details.append(
                    {"indicator": "RSI", "status": "neutral", "text": f"RSI {indicators.rsi:.0f}"}
                )

        # SMA status
        if indicators.sma_200 and indicators.price:
            pct_from_sma = ((indicators.price - indicators.sma_200) / indicators.sma_200) * 100
            details.append(
                {
                    "indicator": "SMA200",
                    "status": "above" if pct_from_sma > 0 else "below",
                    "text": f"{pct_from_sma:+.1f}% от SMA200",
                }
            )

        # Bollinger position
        if indicators.bb_position is not None:
            details.append(
                {
                    "indicator": "BB",
                    "status": "low"
                    if indicators.bb_position < 30
                    else "high"
                    if indicators.bb_position > 70
                    else "mid",
                    "text": f"BB позиция: {indicators.bb_position:.0f}%",
                }
            )

        # Формируем текст сигнала
        if trend == "bullish":
            signal = "long_bias"
            signal_ru = "🟢 Бычий тренд"
        elif trend == "bearish":
            signal = "short_bias"
            signal_ru = "🔴 Медвежий тренд"
        else:
            signal = "neutral"
            signal_ru = "⚪ Боковик"

        return signal, signal_ru, details

    def calculate_confluence(
        self,
        tf_4h: TimeframeAnalysis | None,
        tf_daily: TimeframeAnalysis | None,
        tf_weekly: TimeframeAnalysis | None,
    ) -> tuple[float, str, str]:
        """
        Рассчитать confluence score

        Returns:
            Tuple (score 0-100, signal, signal_ru)
        """
        score = 50.0  # Начинаем с нейтрального

        timeframes = [
            (tf_4h, self.TIMEFRAME_WEIGHTS["4h"]),
            (tf_daily, self.TIMEFRAME_WEIGHTS["1d"]),
            (tf_weekly, self.TIMEFRAME_WEIGHTS["1w"]),
        ]

        total_weight = 0
        weighted_score = 0

        for tf, weight in timeframes:
            if tf:
                total_weight += weight

                # Конвертируем trend в score
                if tf.trend == "bullish":
                    tf_score = 50 + (tf.strength * 5)  # 55-100
                elif tf.trend == "bearish":
                    tf_score = 50 - (tf.strength * 5)  # 0-45
                else:
                    tf_score = 50  # Нейтрально

                weighted_score += tf_score * weight

        if total_weight > 0:
            score = weighted_score / total_weight

        # Определяем сигнал
        if score >= 75:
            signal = "strong_bullish"
            signal_ru = "🟢🟢🟢 Сильный бычий"
        elif score >= 60:
            signal = "bullish"
            signal_ru = "🟢🟢 Бычий"
        elif score >= 55:
            signal = "slightly_bullish"
            signal_ru = "🟢 Умеренно бычий"
        elif score <= 25:
            signal = "strong_bearish"
            signal_ru = "🔴🔴🔴 Сильный медвежий"
        elif score <= 40:
            signal = "bearish"
            signal_ru = "🔴🔴 Медвежий"
        elif score <= 45:
            signal = "slightly_bearish"
            signal_ru = "🔴 Умеренно медвежий"
        else:
            signal = "neutral"
            signal_ru = "⚪ Нейтрально"

        return round(score, 1), signal, signal_ru

    def detect_divergence(
        self,
        tf_4h: TimeframeAnalysis | None,
        tf_daily: TimeframeAnalysis | None,
        tf_weekly: TimeframeAnalysis | None,
    ) -> tuple[bool, str | None, str | None]:
        """
        Обнаружить расхождения между таймфреймами

        Returns:
            Tuple (has_divergence, type, description)
        """
        # Проверяем наличие данных
        available_tfs = []
        if tf_4h:
            available_tfs.append(("4h", tf_4h))
        if tf_daily:
            available_tfs.append(("1d", tf_daily))
        if tf_weekly:
            available_tfs.append(("1w", tf_weekly))

        if len(available_tfs) < 2:
            return False, None, None

        # Проверка: 4H vs Daily
        if tf_4h and tf_daily:
            if (
                tf_4h.trend != tf_daily.trend
                and tf_4h.trend != "neutral"
                and tf_daily.trend != "neutral"
            ):
                return (
                    True,
                    "temporal",
                    (
                        f"4H ({tf_4h.trend_ru}) расходится с Daily ({tf_daily.trend_ru}). "
                        f"Возможна краткосрочная коррекция в рамках основного тренда."
                    ),
                )

        # Проверка: Daily vs Weekly
        if tf_daily and tf_weekly:
            if (
                tf_daily.trend != tf_weekly.trend
                and tf_daily.trend != "neutral"
                and tf_weekly.trend != "neutral"
            ):
                return (
                    True,
                    "structural",
                    (
                        f"Daily ({tf_daily.trend_ru}) расходится с Weekly ({tf_weekly.trend_ru}). "
                        f"Возможен среднесрочный разворот."
                    ),
                )

        # Проверка RSI дивергенции
        if tf_daily and tf_weekly:
            if tf_daily.indicators and tf_weekly.indicators:
                daily_rsi = tf_daily.indicators.rsi
                weekly_rsi = tf_weekly.indicators.rsi

                if daily_rsi and weekly_rsi:
                    # Daily RSI перекуплен, но Weekly нет
                    if daily_rsi > 70 and weekly_rsi < 65:
                        return (
                            True,
                            "rsi_divergence",
                            (
                                f"RSI дивергенция: Daily RSI {daily_rsi:.0f} (перекуплен), "
                                f"Weekly RSI {weekly_rsi:.0f}. Возможен откат."
                            ),
                        )

                    # Daily RSI перепродан, но Weekly нет
                    if daily_rsi < 30 and weekly_rsi > 35:
                        return (
                            True,
                            "rsi_divergence",
                            (
                                f"RSI дивергенция: Daily RSI {daily_rsi:.0f} (перепродан), "
                                f"Weekly RSI {weekly_rsi:.0f}. Возможен отскок."
                            ),
                        )

        return False, None, None

    def get_key_levels(self, symbol: str) -> dict:
        """
        Получить ключевые уровни по всем таймфреймам

        Returns:
            Dict с уровнями по TF
        """
        levels = {}

        for tf in ["1w", "1d", "4h"]:
            candles = self.db.get_ohlcv(symbol, tf, limit=100)
            if candles:
                sr = self.ta.find_support_resistance(candles)
                levels[tf] = {
                    "resistance": sr.get("resistance", [])[:3],
                    "support": sr.get("support", [])[:3],
                    "nearest_resistance": sr.get("nearest_resistance"),
                    "nearest_support": sr.get("nearest_support"),
                    "importance": "high" if tf == "1w" else "medium" if tf == "1d" else "low",
                }

        return levels

    def analyze(self, symbol: str) -> MTFAnalysis:
        """
        Полный Multi-Timeframe анализ

        Args:
            symbol: Символ монеты

        Returns:
            MTFAnalysis с полным анализом
        """
        # Анализ каждого таймфрейма
        tf_4h = self.analyze_timeframe(symbol, "4h")
        tf_daily = self.analyze_timeframe(symbol, "1d")
        tf_weekly = self.analyze_timeframe(symbol, "1w")

        # Получаем текущую цену из daily
        price = tf_daily.indicators.price if tf_daily and tf_daily.indicators else 0
        timestamp = tf_daily.indicators.timestamp if tf_daily and tf_daily.indicators else 0

        # Confluence
        confluence_score, confluence_signal, confluence_signal_ru = self.calculate_confluence(
            tf_4h, tf_daily, tf_weekly
        )

        # Divergence
        has_div, div_type, div_desc = self.detect_divergence(tf_4h, tf_daily, tf_weekly)

        # Key levels
        key_levels = self.get_key_levels(symbol)

        return MTFAnalysis(
            symbol=symbol.upper(),
            timestamp=timestamp,
            price=price,
            tf_4h=tf_4h,
            tf_daily=tf_daily,
            tf_weekly=tf_weekly,
            confluence_score=confluence_score,
            confluence_signal=confluence_signal,
            confluence_signal_ru=confluence_signal_ru,
            has_divergence=has_div,
            divergence_type=div_type,
            divergence_description=div_desc,
            key_levels=key_levels,
        )

    def get_summary(self, symbol: str) -> dict:
        """
        Получить краткую сводку MTF анализа

        Returns:
            Словарь с основными выводами
        """
        analysis = self.analyze(symbol)

        summary = {
            "symbol": analysis.symbol,
            "price": analysis.price,
            "confluence": {
                "score": analysis.confluence_score,
                "signal": analysis.confluence_signal_ru,
            },
            "timeframes": {},
            "divergence": None,
            "recommendation": "",
            "recommendation_ru": "",
        }

        # Добавляем TF сводки
        for tf_name, tf in [
            ("4h", analysis.tf_4h),
            ("1d", analysis.tf_daily),
            ("1w", analysis.tf_weekly),
        ]:
            if tf:
                summary["timeframes"][tf_name] = {
                    "trend": tf.trend_ru,
                    "strength": tf.strength,
                    "rsi": tf.indicators.rsi if tf.indicators else None,
                }

        # Divergence
        if analysis.has_divergence:
            summary["divergence"] = analysis.divergence_description

        # Recommendation
        if analysis.confluence_score >= 70:
            if not analysis.has_divergence:
                summary["recommendation"] = "strong_buy_signal"
                summary["recommendation_ru"] = (
                    "🟢 Сильный бычий тренд на всех таймфреймах. "
                    "Хорошее время для наращивания позиции."
                )
            else:
                summary["recommendation"] = "buy_with_caution"
                summary["recommendation_ru"] = (
                    "🟢 Бычий тренд, но есть расхождение между TF. "
                    "Можно покупать, но с осторожностью."
                )
        elif analysis.confluence_score <= 30:
            summary["recommendation"] = "risk_off"
            summary["recommendation_ru"] = (
                "🔴 Медвежий тренд. Рассмотрите защитные меры или фиксацию прибыли."
            )
        else:
            summary["recommendation"] = "wait"
            summary["recommendation_ru"] = "⚪ Неопределённость. Дождитесь более чёткого сигнала."

        return summary


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import json
    import sys

    logging.basicConfig(level=logging.INFO)

    symbol = sys.argv[1] if len(sys.argv) > 1 else "BTC"

    analyzer = MTFAnalyzer()

    # Полный анализ
    analysis = analyzer.analyze(symbol)
    print(json.dumps(analysis.to_dict(), indent=2, default=str))

    print("\n" + "=" * 60)
    print("SUMMARY:")
    print("=" * 60)

    # Краткая сводка
    summary = analyzer.get_summary(symbol)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
