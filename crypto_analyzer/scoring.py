"""
Scoring Engine - Комплексный скоринг всех факторов

Объединяет данные из всех модулей в единый score 0-100:
- Technical Analysis (30%)
- MTF Confluence (20%)
- Market Cycle (15%)
- Derivatives (15%)
- Fear & Greed (10%)
- ML Prediction (10%)

Score интерпретация:
- 80-100: Сильный бычий сигнал
- 60-79: Умеренно бычий
- 40-59: Нейтрально
- 20-39: Умеренно медвежий
- 0-19: Сильный медвежий сигнал
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime

from analysis import TechnicalAnalyzer
from cycles import CycleDetector
from database import CryptoDatabase, get_database
from mtf_analysis import MTFAnalyzer

logger = logging.getLogger(__name__)


@dataclass
class ComponentScore:
    """Оценка одного компонента"""

    name: str
    name_ru: str
    score: float  # 0-100
    weight: float  # 0-1
    weighted_score: float = 0
    details: dict = field(default_factory=dict)
    signal: str = "neutral"  # 'bullish', 'bearish', 'neutral'


@dataclass
class CompositeScore:
    """Комплексная оценка"""

    symbol: str
    timestamp: int

    # Финальный score
    total_score: float = 50.0
    signal: str = "neutral"
    signal_ru: str = "Нейтрально"

    # Компоненты
    components: list[ComponentScore] = field(default_factory=list)

    # Рекомендация
    recommendation: str = ""
    recommendation_ru: str = ""
    action: str = "hold"  # 'strong_buy', 'buy', 'hold', 'sell', 'strong_sell'

    # Риск
    risk_score: float = 50.0  # 0=low risk, 100=high risk
    risk_level: str = "medium"

    # Уверенность
    confidence: float = 50.0

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "score": {
                "total": round(self.total_score, 1),
                "signal": self.signal,
                "signal_ru": self.signal_ru,
            },
            "components": [
                {
                    "name": c.name,
                    "name_ru": c.name_ru,
                    "score": round(c.score, 1),
                    "weight": c.weight,
                    "weighted": round(c.weighted_score, 1),
                    "signal": c.signal,
                    "details": c.details,
                }
                for c in self.components
            ],
            "recommendation": {
                "text": self.recommendation,
                "text_ru": self.recommendation_ru,
                "action": self.action,
            },
            "risk": {
                "score": round(self.risk_score, 1),
                "level": self.risk_level,
            },
            "confidence": round(self.confidence, 1),
        }

    def get_summary_ru(self) -> str:
        """Получить резюме на русском"""
        # Эмодзи для score
        if self.total_score >= 80:
            score_emoji = "🟢🟢🟢"
        elif self.total_score >= 60:
            score_emoji = "🟢🟢"
        elif self.total_score >= 55:
            score_emoji = "🟢"
        elif self.total_score <= 20:
            score_emoji = "🔴🔴🔴"
        elif self.total_score <= 40:
            score_emoji = "🔴🔴"
        elif self.total_score <= 45:
            score_emoji = "🔴"
        else:
            score_emoji = "⚪"

        parts = [
            f"📊 **Комплексная оценка: {self.symbol}**",
            "",
            f"{score_emoji} **Score: {self.total_score:.0f}/100** ({self.signal_ru})",
            "",
            "**Компоненты:**",
        ]

        for c in self.components:
            c_emoji = "🟢" if c.score >= 60 else "🔴" if c.score <= 40 else "⚪"
            parts.append(f"  {c_emoji} {c.name_ru}: {c.score:.0f} (вес {c.weight*100:.0f}%)")

        parts.extend(
            [
                "",
                f"**Риск:** {self.risk_level} ({self.risk_score:.0f}/100)",
                f"**Уверенность:** {self.confidence:.0f}%",
                "",
                f"💡 **Рекомендация:** {self.recommendation_ru}",
            ]
        )

        return "\n".join(parts)


class ScoringEngine:
    """Движок комплексного скоринга"""

    # Веса компонентов
    WEIGHTS = {
        "technical": 0.30,
        "mtf": 0.20,
        "cycle": 0.15,
        "derivatives": 0.15,
        "fear_greed": 0.10,
        "ml": 0.10,
    }

    def __init__(self, db: CryptoDatabase | None = None):
        self.db = db or get_database()
        self.ta = TechnicalAnalyzer(self.db)
        self.mtf = MTFAnalyzer(self.db)
        self.cycles = CycleDetector(self.db)

    def score_technical(self, symbol: str) -> ComponentScore:
        """
        Оценка технического анализа

        Returns:
            ComponentScore
        """
        indicators = self.ta.analyze(symbol, "1d")

        if not indicators:
            return ComponentScore(
                name="technical",
                name_ru="Технический анализ",
                score=50,
                weight=self.WEIGHTS["technical"],
                signal="neutral",
            )

        score = 50.0
        details = {}

        # RSI (вес 25%)
        if indicators.rsi:
            rsi = indicators.rsi
            details["rsi"] = rsi
            if rsi < 30:
                score += 12.5  # Перепроданность = бычий сигнал
            elif rsi < 45:
                score += 6
            elif rsi > 70:
                score -= 12.5  # Перекупленность = медвежий
            elif rsi > 55:
                score -= 6

        # SMA200 (вес 25%)
        if indicators.sma_200 and indicators.price:
            above_sma200 = indicators.price > indicators.sma_200
            details["above_sma200"] = above_sma200
            score += 12.5 if above_sma200 else -12.5

        # Golden/Death Cross (вес 20%)
        if indicators.sma_50 and indicators.sma_200:
            golden_cross = indicators.sma_50 > indicators.sma_200
            details["golden_cross"] = golden_cross
            score += 10 if golden_cross else -10

        # MACD (вес 15%)
        if indicators.macd_histogram is not None:
            details["macd_positive"] = indicators.macd_histogram > 0
            score += 7.5 if indicators.macd_histogram > 0 else -7.5

        # Bollinger Position (вес 15%)
        if indicators.bb_position is not None:
            details["bb_position"] = indicators.bb_position
            if indicators.bb_position < 20:
                score += 7.5  # У нижней границы
            elif indicators.bb_position > 80:
                score -= 7.5  # У верхней границы

        score = max(0, min(100, score))

        return ComponentScore(
            name="technical",
            name_ru="Технический анализ",
            score=score,
            weight=self.WEIGHTS["technical"],
            weighted_score=score * self.WEIGHTS["technical"],
            details=details,
            signal="bullish" if score >= 60 else "bearish" if score <= 40 else "neutral",
        )

    def score_mtf(self, symbol: str) -> ComponentScore:
        """
        Оценка Multi-Timeframe

        Returns:
            ComponentScore
        """
        try:
            analysis = self.mtf.analyze(symbol)
            score = analysis.confluence_score

            details = {
                "4h": analysis.tf_4h.trend if analysis.tf_4h else "unknown",
                "daily": analysis.tf_daily.trend if analysis.tf_daily else "unknown",
                "weekly": analysis.tf_weekly.trend if analysis.tf_weekly else "unknown",
                "has_divergence": analysis.has_divergence,
            }

            # Штраф за дивергенцию
            if analysis.has_divergence:
                score = score * 0.9  # -10%

            return ComponentScore(
                name="mtf",
                name_ru="Multi-Timeframe",
                score=score,
                weight=self.WEIGHTS["mtf"],
                weighted_score=score * self.WEIGHTS["mtf"],
                details=details,
                signal=analysis.confluence_signal,
            )
        except Exception as e:
            logger.error(f"MTF scoring error: {e}")
            return ComponentScore(
                name="mtf",
                name_ru="Multi-Timeframe",
                score=50,
                weight=self.WEIGHTS["mtf"],
                signal="neutral",
            )

    def score_cycle(self, symbol: str) -> ComponentScore:
        """
        Оценка рыночного цикла

        Returns:
            ComponentScore
        """
        # Цикл только для BTC
        if symbol.upper() != "BTC":
            return ComponentScore(
                name="cycle",
                name_ru="Рыночный цикл",
                score=50,
                weight=self.WEIGHTS["cycle"],
                weighted_score=50 * self.WEIGHTS["cycle"],
                details={"note": "Только для BTC"},
                signal="neutral",
            )

        try:
            cycle = self.cycles.detect_cycle("BTC")

            # Преобразуем фазу в score
            phase_scores = {
                "capitulation": 85,  # Отличное время для покупки
                "accumulation": 75,
                "early_bull": 70,
                "bull_run": 60,
                "euphoria": 30,  # Высокий риск
                "distribution": 35,
                "early_bear": 40,
                "bear_market": 45,
                "unknown": 50,
            }

            score = phase_scores.get(cycle.phase.value, 50)

            details = {
                "phase": cycle.phase.value,
                "phase_ru": cycle.phase_name_ru,
                "days_since_halving": cycle.days_since_halving,
                "from_ath_pct": cycle.distance_from_ath_pct,
                "risk_level": cycle.risk_level,
            }

            signal = "bullish" if score >= 60 else "bearish" if score <= 40 else "neutral"

            return ComponentScore(
                name="cycle",
                name_ru="Рыночный цикл",
                score=score,
                weight=self.WEIGHTS["cycle"],
                weighted_score=score * self.WEIGHTS["cycle"],
                details=details,
                signal=signal,
            )
        except Exception as e:
            logger.error(f"Cycle scoring error: {e}")
            return ComponentScore(
                name="cycle",
                name_ru="Рыночный цикл",
                score=50,
                weight=self.WEIGHTS["cycle"],
                signal="neutral",
            )

    def score_derivatives(self, symbol: str) -> ComponentScore:
        """
        Оценка деривативов

        Returns:
            ComponentScore
        """
        # Получаем из кэша или используем default
        cached = self.db.get_cache(symbol, "derivatives")

        if not cached:
            return ComponentScore(
                name="derivatives",
                name_ru="Деривативы",
                score=50,
                weight=self.WEIGHTS["derivatives"],
                weighted_score=50 * self.WEIGHTS["derivatives"],
                details={"note": "Нет данных"},
                signal="neutral",
            )

        score = 50.0
        details = {}

        funding = cached.get("funding", {})
        ls = cached.get("long_short", {})

        # Funding Rate (контр-индикатор)
        fr = funding.get("rate")
        if fr is not None:
            fr_pct = fr * 100
            details["funding_rate"] = fr_pct

            if fr_pct > 0.05:  # Высокий positive = много лонгов
                score -= 15  # Медвежий контр-сигнал
            elif fr_pct < -0.02:  # Negative = шорты платят
                score += 15  # Бычий контр-сигнал

        # Long/Short Ratio (контр-индикатор)
        ratio = ls.get("ratio")
        if ratio:
            details["ls_ratio"] = ratio

            if ratio > 1.5:  # Много лонгов
                score -= 10
            elif ratio < 0.67:  # Много шортов
                score += 10

        score = max(0, min(100, score))

        return ComponentScore(
            name="derivatives",
            name_ru="Деривативы",
            score=score,
            weight=self.WEIGHTS["derivatives"],
            weighted_score=score * self.WEIGHTS["derivatives"],
            details=details,
            signal="bullish" if score >= 60 else "bearish" if score <= 40 else "neutral",
        )

    def score_fear_greed(self) -> ComponentScore:
        """
        Оценка Fear & Greed Index

        Returns:
            ComponentScore
        """
        cached = self.db.get_cache("BTC", "onchain")

        fg_value = None
        if cached:
            fg_value = cached.get("fear_greed", {}).get("value")

        if fg_value is None:
            return ComponentScore(
                name="fear_greed",
                name_ru="Fear & Greed",
                score=50,
                weight=self.WEIGHTS["fear_greed"],
                weighted_score=50 * self.WEIGHTS["fear_greed"],
                details={"note": "Нет данных"},
                signal="neutral",
            )

        # F&G - контр-индикатор
        # Extreme Fear (0-25) = бычий сигнал
        # Extreme Greed (75-100) = медвежий сигнал

        if fg_value < 25:
            score = 80  # Extreme Fear = время покупать
        elif fg_value < 45:
            score = 65  # Fear
        elif fg_value > 75:
            score = 20  # Extreme Greed = время продавать
        elif fg_value > 55:
            score = 35  # Greed
        else:
            score = 50  # Neutral

        details = {
            "value": fg_value,
            "interpretation": "extreme_fear"
            if fg_value < 25
            else "fear"
            if fg_value < 45
            else "extreme_greed"
            if fg_value > 75
            else "greed"
            if fg_value > 55
            else "neutral",
        }

        return ComponentScore(
            name="fear_greed",
            name_ru="Fear & Greed",
            score=score,
            weight=self.WEIGHTS["fear_greed"],
            weighted_score=score * self.WEIGHTS["fear_greed"],
            details=details,
            signal="bullish" if score >= 60 else "bearish" if score <= 40 else "neutral",
        )

    def score_ml(self, symbol: str) -> ComponentScore:
        """
        Оценка ML предсказания

        Returns:
            ComponentScore
        """
        # ML требует исторических данных, возвращаем нейтральный если нет
        return ComponentScore(
            name="ml",
            name_ru="ML Прогноз",
            score=50,
            weight=self.WEIGHTS["ml"],
            weighted_score=50 * self.WEIGHTS["ml"],
            details={"note": "Требуется обучение"},
            signal="neutral",
        )

    def calculate(self, symbol: str) -> CompositeScore:
        """
        Рассчитать комплексный score

        Args:
            symbol: Символ монеты

        Returns:
            CompositeScore
        """
        result = CompositeScore(
            symbol=symbol.upper(), timestamp=int(datetime.now().timestamp() * 1000)
        )

        # Собираем все компоненты
        components = [
            self.score_technical(symbol),
            self.score_mtf(symbol),
            self.score_cycle(symbol),
            self.score_derivatives(symbol),
            self.score_fear_greed(),
            self.score_ml(symbol),
        ]

        result.components = components

        # Рассчитываем итоговый score
        total_weighted = sum(c.weighted_score for c in components)
        total_weight = sum(c.weight for c in components)

        result.total_score = total_weighted / total_weight if total_weight > 0 else 50

        # Определяем сигнал
        if result.total_score >= 75:
            result.signal = "strong_bullish"
            result.signal_ru = "🟢🟢🟢 Сильный бычий"
            result.action = "strong_buy"
        elif result.total_score >= 60:
            result.signal = "bullish"
            result.signal_ru = "🟢🟢 Бычий"
            result.action = "buy"
        elif result.total_score >= 55:
            result.signal = "slightly_bullish"
            result.signal_ru = "🟢 Умеренно бычий"
            result.action = "buy"
        elif result.total_score <= 25:
            result.signal = "strong_bearish"
            result.signal_ru = "🔴🔴🔴 Сильный медвежий"
            result.action = "strong_sell"
        elif result.total_score <= 40:
            result.signal = "bearish"
            result.signal_ru = "🔴🔴 Медвежий"
            result.action = "sell"
        elif result.total_score <= 45:
            result.signal = "slightly_bearish"
            result.signal_ru = "🔴 Умеренно медвежий"
            result.action = "sell"
        else:
            result.signal = "neutral"
            result.signal_ru = "⚪ Нейтрально"
            result.action = "hold"

        # Рекомендации
        result.recommendation_ru = self._generate_recommendation(result)

        # Риск (инвертированный score для бычьих сигналов)
        cycle_component = next((c for c in components if c.name == "cycle"), None)
        if cycle_component and cycle_component.details.get("risk_level"):
            risk_map = {"low": 25, "medium": 50, "high": 75, "extreme": 90}
            result.risk_score = risk_map.get(cycle_component.details["risk_level"], 50)
            result.risk_level = cycle_component.details["risk_level"]
        else:
            result.risk_score = 100 - result.total_score
            result.risk_level = (
                "high" if result.risk_score > 70 else "medium" if result.risk_score > 40 else "low"
            )

        # Уверенность (на основе согласованности компонентов)
        signals = [c.signal for c in components if c.signal != "neutral"]
        if signals:
            bullish_count = sum(1 for s in signals if "bullish" in s)
            bearish_count = sum(1 for s in signals if "bearish" in s)
            result.confidence = (max(bullish_count, bearish_count) / len(signals)) * 100
        else:
            result.confidence = 50

        return result

    def _generate_recommendation(self, score: CompositeScore) -> str:
        """Сгенерировать рекомендацию"""
        if score.action == "strong_buy":
            return "Отличное время для покупки. Все факторы указывают на рост."
        elif score.action == "buy":
            return "Хорошее время для покупки. Рассмотрите DCA или добавление позиции."
        elif score.action == "strong_sell":
            return "Рассмотрите фиксацию прибыли. Высокий риск коррекции."
        elif score.action == "sell":
            return "Осторожность. Рассмотрите сокращение позиции."
        else:
            return "Неопределённость. Дождитесь более чёткого сигнала."


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import json

    logging.basicConfig(level=logging.INFO)

    engine = ScoringEngine()

    for symbol in ["BTC", "ETH"]:
        print(f"\n{'='*60}")
        print(f"COMPOSITE SCORE: {symbol}")
        print("=" * 60)

        score = engine.calculate(symbol)

        print(json.dumps(score.to_dict(), indent=2, ensure_ascii=False))

        print("\nSUMMARY (RU):")
        print(score.get_summary_ru())
