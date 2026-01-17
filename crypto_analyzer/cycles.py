"""
Market Cycle Detector - Определение рыночного цикла

Фазы цикла Bitcoin:
1. Accumulation (Накопление) - после дна, низкий объём, боковик
2. Early Bull (Ранний бык) - рост после халвинга, выход из накопления
3. Bull Run (Бычий рынок) - экспоненциальный рост
4. Distribution (Распределение) - вершина, высокий объём, волатильность
5. Bear Market (Медвежий рынок) - падение, капитуляция
6. Capitulation (Капитуляция) - дно, максимальный страх

Индикаторы для определения:
- Halving cycle (3-5 лет)
- Расстояние от ATH/ATL
- MVRV (Market Value to Realized Value)
- Pi Cycle Top
- Rainbow Chart
- 200 Week MA Heatmap
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from analysis import TechnicalAnalyzer
from database import CryptoDatabase, get_database

logger = logging.getLogger(__name__)


class CyclePhase(Enum):
    """Фазы рыночного цикла"""

    ACCUMULATION = "accumulation"
    EARLY_BULL = "early_bull"
    BULL_RUN = "bull_run"
    EUPHORIA = "euphoria"
    DISTRIBUTION = "distribution"
    EARLY_BEAR = "early_bear"
    BEAR_MARKET = "bear_market"
    CAPITULATION = "capitulation"
    UNKNOWN = "unknown"


# Даты халвингов Bitcoin
HALVING_DATES = [
    datetime(2012, 11, 28),
    datetime(2016, 7, 9),
    datetime(2020, 5, 11),
    datetime(2024, 4, 20),  # Примерная дата
]

# Следующий халвинг (примерно каждые ~210,000 блоков / ~4 года)
NEXT_HALVING_ESTIMATE = datetime(2028, 4, 1)


@dataclass
class CycleInfo:
    """Информация о текущем цикле"""

    phase: CyclePhase
    phase_name_ru: str
    confidence: float  # 0-100%
    description_ru: str

    # Halving metrics
    days_since_halving: int | None = None
    days_to_next_halving: int | None = None
    halving_cycle_progress: float | None = None  # 0-100%

    # Price metrics
    ath: float | None = None
    atl: float | None = None
    distance_from_ath_pct: float | None = None
    distance_from_atl_pct: float | None = None

    # Cycle position
    cycle_position: float | None = None  # 0-100, где мы в цикле

    # Technical
    ma_200w: float | None = None
    ma_200w_position: str | None = None  # 'above', 'below'

    # Recommendations
    recommendation: str | None = None
    risk_level: str | None = None  # 'low', 'medium', 'high', 'extreme'

    def to_dict(self) -> dict:
        return {
            "phase": self.phase.value,
            "phase_name_ru": self.phase_name_ru,
            "confidence": self.confidence,
            "description_ru": self.description_ru,
            "halving": {
                "days_since": self.days_since_halving,
                "days_to_next": self.days_to_next_halving,
                "cycle_progress_pct": self.halving_cycle_progress,
            },
            "price": {
                "ath": self.ath,
                "atl": self.atl,
                "from_ath_pct": self.distance_from_ath_pct,
                "from_atl_pct": self.distance_from_atl_pct,
            },
            "cycle_position": self.cycle_position,
            "technical": {
                "ma_200w": self.ma_200w,
                "ma_200w_position": self.ma_200w_position,
            },
            "recommendation": self.recommendation,
            "risk_level": self.risk_level,
        }

    def get_summary(self) -> str:
        """Краткое резюме цикла"""
        emoji_map = {
            CyclePhase.ACCUMULATION: "🟢",
            CyclePhase.EARLY_BULL: "🟢",
            CyclePhase.BULL_RUN: "🟡",
            CyclePhase.EUPHORIA: "🔴",
            CyclePhase.DISTRIBUTION: "🔴",
            CyclePhase.EARLY_BEAR: "🟠",
            CyclePhase.BEAR_MARKET: "🔴",
            CyclePhase.CAPITULATION: "🟢",
            CyclePhase.UNKNOWN: "⚪",
        }

        emoji = emoji_map.get(self.phase, "⚪")

        summary = f"{emoji} **{self.phase_name_ru}**\n\n"
        summary += f"{self.description_ru}\n\n"

        if self.days_since_halving:
            summary += f"📅 {self.days_since_halving} дней после халвинга\n"
        if self.days_to_next_halving:
            summary += f"⏳ {self.days_to_next_halving} дней до следующего халвинга\n"

        if self.distance_from_ath_pct:
            summary += f"📉 {self.distance_from_ath_pct:.1f}% от ATH\n"
        if self.distance_from_atl_pct:
            summary += f"📈 +{self.distance_from_atl_pct:.1f}% от ATL\n"

        if self.recommendation:
            summary += f"\n💡 {self.recommendation}"

        return summary


class CycleDetector:
    """Детектор рыночного цикла"""

    # Фазы цикла на русском
    PHASE_NAMES_RU = {
        CyclePhase.ACCUMULATION: "Накопление",
        CyclePhase.EARLY_BULL: "Ранний бычий рынок",
        CyclePhase.BULL_RUN: "Бычий рынок",
        CyclePhase.EUPHORIA: "Эйфория",
        CyclePhase.DISTRIBUTION: "Распределение",
        CyclePhase.EARLY_BEAR: "Ранний медвежий рынок",
        CyclePhase.BEAR_MARKET: "Медвежий рынок",
        CyclePhase.CAPITULATION: "Капитуляция",
        CyclePhase.UNKNOWN: "Неопределённо",
    }

    def __init__(self, db: CryptoDatabase | None = None):
        self.db = db or get_database()
        self.ta = TechnicalAnalyzer(self.db)

    def detect_cycle(self, symbol: str = "BTC") -> CycleInfo:
        """
        Определить текущую фазу рыночного цикла

        Args:
            symbol: Символ (по умолчанию BTC, т.к. он определяет весь рынок)

        Returns:
            CycleInfo с детальной информацией о цикле
        """
        # Получаем данные
        candles_daily = self.db.get_ohlcv(symbol, "1d", limit=1460)  # ~4 года
        candles_weekly = self.db.get_ohlcv(symbol, "1w", limit=400)  # ~7.5 лет

        if len(candles_daily) < 365:
            return CycleInfo(
                phase=CyclePhase.UNKNOWN,
                phase_name_ru=self.PHASE_NAMES_RU[CyclePhase.UNKNOWN],
                confidence=0,
                description_ru="Недостаточно исторических данных для определения цикла",
            )

        current_price = candles_daily[-1]["close"]

        # === Halving Analysis ===
        halving_metrics = self._analyze_halving()

        # === Price Analysis ===
        price_metrics = self._analyze_price_position(candles_daily, current_price)

        # === Technical Analysis ===
        tech_metrics = self._analyze_technical(candles_daily, candles_weekly, current_price)

        # === Determine Phase ===
        phase, confidence = self._determine_phase(halving_metrics, price_metrics, tech_metrics)

        # === Build Description ===
        description = self._build_description(phase, halving_metrics, price_metrics, tech_metrics)

        # === Recommendation ===
        recommendation, risk_level = self._get_recommendation(phase, price_metrics, tech_metrics)

        return CycleInfo(
            phase=phase,
            phase_name_ru=self.PHASE_NAMES_RU[phase],
            confidence=confidence,
            description_ru=description,
            days_since_halving=halving_metrics.get("days_since"),
            days_to_next_halving=halving_metrics.get("days_to_next"),
            halving_cycle_progress=halving_metrics.get("cycle_progress"),
            ath=price_metrics.get("ath"),
            atl=price_metrics.get("atl"),
            distance_from_ath_pct=price_metrics.get("from_ath_pct"),
            distance_from_atl_pct=price_metrics.get("from_atl_pct"),
            cycle_position=self._calculate_cycle_position(phase, halving_metrics, price_metrics),
            ma_200w=tech_metrics.get("ma_200w"),
            ma_200w_position=tech_metrics.get("ma_200w_position"),
            recommendation=recommendation,
            risk_level=risk_level,
        )

    def _analyze_halving(self) -> dict:
        """Анализ позиции в халвинг-цикле"""
        now = datetime.now()

        # Находим последний халвинг
        last_halving = None
        for h in HALVING_DATES:
            if h <= now:
                last_halving = h

        if not last_halving:
            return {"days_since": None, "days_to_next": None, "cycle_progress": None}

        days_since = (now - last_halving).days

        # Следующий халвинг
        next_halving = None
        for h in HALVING_DATES:
            if h > now:
                next_halving = h
                break
        if not next_halving:
            next_halving = NEXT_HALVING_ESTIMATE

        days_to_next = (next_halving - now).days

        # Прогресс в текущем цикле (примерно 1460 дней между халвингами)
        cycle_length = (next_halving - last_halving).days
        cycle_progress = (days_since / cycle_length) * 100

        return {
            "days_since": days_since,
            "days_to_next": days_to_next,
            "cycle_progress": cycle_progress,
            "last_halving": last_halving,
            "next_halving": next_halving,
        }

    def _analyze_price_position(self, candles: list[dict], current_price: float) -> dict:
        """Анализ позиции цены относительно ATH/ATL"""
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]

        ath = max(highs)
        atl = min(lows)

        # Расстояние от ATH (отрицательное значение)
        from_ath_pct = ((current_price - ath) / ath) * 100

        # Расстояние от ATL (положительное значение)
        from_atl_pct = ((current_price - atl) / atl) * 100

        # Позиция в диапазоне ATL-ATH (0-100%)
        price_range_position = ((current_price - atl) / (ath - atl)) * 100 if ath != atl else 50

        return {
            "ath": ath,
            "atl": atl,
            "from_ath_pct": from_ath_pct,
            "from_atl_pct": from_atl_pct,
            "price_range_position": price_range_position,
        }

    def _analyze_technical(
        self, candles_daily: list[dict], candles_weekly: list[dict], current_price: float
    ) -> dict:
        """Технический анализ для определения цикла"""
        closes_daily = [c["close"] for c in candles_daily]

        # SMA 50, 200 Daily
        sma_50d = self.ta.calc_sma(closes_daily, 50)
        sma_200d = self.ta.calc_sma(closes_daily, 200)

        # SMA 200 Weekly (если есть данные)
        ma_200w = None
        if len(candles_weekly) >= 200:
            closes_weekly = [c["close"] for c in candles_weekly]
            ma_200w = self.ta.calc_sma(closes_weekly, 200)

        # RSI
        rsi = self.ta.calc_rsi(closes_daily, 14)

        # MACD
        macd, signal, hist = self.ta.calc_macd(closes_daily)

        return {
            "sma_50d": sma_50d,
            "sma_200d": sma_200d,
            "ma_200w": ma_200w,
            "ma_200w_position": "above" if ma_200w and current_price > ma_200w else "below",
            "rsi": rsi,
            "macd": macd,
            "macd_signal": signal,
            "macd_hist": hist,
            "golden_cross": sma_50d and sma_200d and sma_50d > sma_200d,
            "death_cross": sma_50d and sma_200d and sma_50d < sma_200d,
        }

    def _determine_phase(self, halving: dict, price: dict, tech: dict) -> tuple[CyclePhase, float]:
        """
        Определить фазу цикла на основе всех метрик

        Returns:
            (CyclePhase, confidence)
        """
        scores = {phase: 0 for phase in CyclePhase}

        days_since_halving = halving.get("days_since", 0)
        cycle_progress = halving.get("cycle_progress", 50)
        from_ath = price.get("from_ath_pct", 0)
        from_atl = price.get("from_atl_pct", 0)
        price_range = price.get("price_range_position", 50)
        rsi = tech.get("rsi", 50)
        golden_cross = tech.get("golden_cross", False)
        death_cross = tech.get("death_cross", False)
        above_200w = tech.get("ma_200w_position") == "above"

        # === ACCUMULATION ===
        # После дна, низкая позиция в диапазоне, ниже 200W MA
        if from_ath < -60 and price_range < 30 and not above_200w:
            scores[CyclePhase.ACCUMULATION] += 30
        if days_since_halving and (days_since_halving < 200 or days_since_halving > 1200):
            scores[CyclePhase.ACCUMULATION] += 15
        if rsi and 30 < rsi < 50:
            scores[CyclePhase.ACCUMULATION] += 10

        # === EARLY BULL ===
        # После халвинга, начало роста, пересечение 200W MA
        if 200 <= days_since_halving <= 500 if days_since_halving else False:
            scores[CyclePhase.EARLY_BULL] += 25
        if 20 < price_range < 50 and above_200w:
            scores[CyclePhase.EARLY_BULL] += 20
        if golden_cross:
            scores[CyclePhase.EARLY_BULL] += 15
        if rsi and 50 < rsi < 65:
            scores[CyclePhase.EARLY_BULL] += 10

        # === BULL RUN ===
        # Активный рост, высокий RSI, выше 200W MA
        if 500 <= days_since_halving <= 900 if days_since_halving else False:
            scores[CyclePhase.BULL_RUN] += 20
        if 50 < price_range < 80 and above_200w:
            scores[CyclePhase.BULL_RUN] += 20
        if golden_cross and rsi and rsi > 60:
            scores[CyclePhase.BULL_RUN] += 20
        if -30 < from_ath < -10:
            scores[CyclePhase.BULL_RUN] += 15

        # === EUPHORIA ===
        # Близко к ATH, экстремальный RSI
        if from_ath > -15 and price_range > 85:
            scores[CyclePhase.EUPHORIA] += 35
        if rsi and rsi > 75:
            scores[CyclePhase.EUPHORIA] += 25
        if 800 <= days_since_halving <= 1100 if days_since_halving else False:
            scores[CyclePhase.EUPHORIA] += 15

        # === DISTRIBUTION ===
        # После пика, начало распродаж
        if -30 < from_ath < -10 and rsi and rsi < 60:
            scores[CyclePhase.DISTRIBUTION] += 25
        if 70 < price_range < 90:
            scores[CyclePhase.DISTRIBUTION] += 15
        if tech.get("macd_hist") and tech["macd_hist"] < 0:
            scores[CyclePhase.DISTRIBUTION] += 15

        # === EARLY BEAR ===
        # Начало падения, пробой 200D MA
        if death_cross and from_ath < -30:
            scores[CyclePhase.EARLY_BEAR] += 30
        if -50 < from_ath < -25 and rsi and rsi < 50:
            scores[CyclePhase.EARLY_BEAR] += 20

        # === BEAR MARKET ===
        # Глубокое падение, ниже 200W MA
        if from_ath < -50 and not above_200w:
            scores[CyclePhase.BEAR_MARKET] += 30
        if death_cross and rsi and rsi < 40:
            scores[CyclePhase.BEAR_MARKET] += 20
        if 30 < price_range < 50:
            scores[CyclePhase.BEAR_MARKET] += 15

        # === CAPITULATION ===
        # Максимальное падение, экстремальный страх
        if from_ath < -70 and price_range < 20:
            scores[CyclePhase.CAPITULATION] += 35
        if rsi and rsi < 30:
            scores[CyclePhase.CAPITULATION] += 25
        if not above_200w and from_atl < 50:
            scores[CyclePhase.CAPITULATION] += 15

        # Находим фазу с максимальным score
        best_phase = max(scores, key=scores.get)
        best_score = scores[best_phase]

        # Confidence = score / max_possible (примерно 100)
        confidence = min(100, (best_score / 75) * 100)

        if best_score < 20:
            return CyclePhase.UNKNOWN, 0

        return best_phase, confidence

    def _build_description(self, phase: CyclePhase, halving: dict, price: dict, tech: dict) -> str:
        """Построить описание текущей фазы"""
        descriptions = {
            CyclePhase.ACCUMULATION: "Рынок находится в фазе накопления. Цена значительно ниже исторических максимумов. "
            "Умные деньги накапливают позиции. Хорошее время для долгосрочных инвестиций.",
            CyclePhase.EARLY_BULL: "Начало бычьего цикла. Рынок выходит из накопления после халвинга. "
            "Формируется восходящий тренд. Благоприятное время для входа.",
            CyclePhase.BULL_RUN: "Активная фаза бычьего рынка. Цена растёт, объёмы увеличиваются. "
            "Рекомендуется держать позиции, но следить за признаками перегрева.",
            CyclePhase.EUPHORIA: "Фаза эйфории! Рынок близок к историческим максимумам. "
            "Экстремальная жадность. Высокий риск коррекции. Рассмотрите фиксацию прибыли.",
            CyclePhase.DISTRIBUTION: "Фаза распределения. Крупные игроки начинают продавать. "
            "Высокая волатильность. Будьте осторожны с новыми покупками.",
            CyclePhase.EARLY_BEAR: "Начало медвежьего рынка. Тренд развернулся вниз. "
            "Рекомендуется сокращать позиции или хеджировать.",
            CyclePhase.BEAR_MARKET: "Медвежий рынок. Цена значительно упала от максимумов. "
            "Страх преобладает. Можно начинать постепенное накопление.",
            CyclePhase.CAPITULATION: "Фаза капитуляции. Максимальный страх, распродажи. "
            "Исторически - отличное время для долгосрочных покупок.",
            CyclePhase.UNKNOWN: "Недостаточно данных для определения фазы цикла.",
        }

        base_desc = descriptions.get(phase, "")

        # Добавляем конкретные цифры
        additions = []

        if price.get("from_ath_pct"):
            additions.append(
                f"Цена на {abs(price['from_ath_pct']):.0f}% ниже ATH (${price['ath']:,.0f})"
            )

        if halving.get("days_since"):
            additions.append(f"Прошло {halving['days_since']} дней после халвинга")

        if tech.get("golden_cross"):
            additions.append("Golden Cross активен")
        elif tech.get("death_cross"):
            additions.append("Death Cross активен")

        if additions:
            base_desc += "\n\n📊 " + " | ".join(additions)

        return base_desc

    def _get_recommendation(self, phase: CyclePhase, price: dict, tech: dict) -> tuple[str, str]:
        """Получить рекомендацию и уровень риска"""
        recommendations = {
            CyclePhase.ACCUMULATION: (
                "Отличное время для DCA (усреднения). Рассмотрите увеличение позиций.",
                "low",
            ),
            CyclePhase.EARLY_BULL: (
                "Хорошее время для покупок. Держите позиции, добавляйте на откатах.",
                "low",
            ),
            CyclePhase.BULL_RUN: (
                "Держите позиции. Фиксируйте часть прибыли по мере роста.",
                "medium",
            ),
            CyclePhase.EUPHORIA: (
                "⚠️ Высокий риск! Рассмотрите фиксацию 30-50% позиций.",
                "extreme",
            ),
            CyclePhase.DISTRIBUTION: (
                "Осторожно с новыми покупками. Рассмотрите защитные стратегии.",
                "high",
            ),
            CyclePhase.EARLY_BEAR: ("Сократите экспозицию. Избегайте плечей.", "high"),
            CyclePhase.BEAR_MARKET: ("Начинайте постепенное накопление через DCA.", "medium"),
            CyclePhase.CAPITULATION: (
                "💎 Потенциально лучшее время для покупок! Усиливайте DCA.",
                "low",
            ),
            CyclePhase.UNKNOWN: ("Недостаточно данных. Будьте осторожны.", "medium"),
        }

        return recommendations.get(phase, ("", "medium"))

    def _calculate_cycle_position(self, phase: CyclePhase, halving: dict, price: dict) -> float:
        """
        Рассчитать позицию в цикле (0-100)
        0 = дно цикла, 100 = вершина
        """
        # Используем комбинацию halving progress и price range
        halving_progress = halving.get("cycle_progress", 50)
        price_range = price.get("price_range_position", 50)

        # Взвешенная комбинация
        position = (halving_progress * 0.4) + (price_range * 0.6)

        return min(100, max(0, position))

    def get_cycle_timeline(self, symbol: str = "BTC") -> dict:
        """
        Получить временную шкалу цикла

        Returns:
            Dict с ключевыми датами и событиями
        """
        now = datetime.now()

        timeline = []

        # Прошлые халвинги
        for i, h in enumerate(HALVING_DATES):
            if h <= now:
                timeline.append(
                    {
                        "date": h.strftime("%Y-%m-%d"),
                        "event": f"Халвинг #{i+1}",
                        "type": "halving",
                        "status": "past",
                        "days_ago": (now - h).days,
                    }
                )

        # Следующий халвинг
        next_halving = None
        for h in HALVING_DATES:
            if h > now:
                next_halving = h
                break
        if not next_halving:
            next_halving = NEXT_HALVING_ESTIMATE

        timeline.append(
            {
                "date": next_halving.strftime("%Y-%m-%d"),
                "event": "Следующий халвинг",
                "type": "halving",
                "status": "future",
                "days_until": (next_halving - now).days,
            }
        )

        # Исторические пики (примерно 12-18 месяцев после халвинга)
        historical_peaks = [
            (datetime(2013, 11, 30), 1150),
            (datetime(2017, 12, 17), 19700),
            (datetime(2021, 11, 10), 69000),
        ]

        for peak_date, peak_price in historical_peaks:
            timeline.append(
                {
                    "date": peak_date.strftime("%Y-%m-%d"),
                    "event": f"ATH ${peak_price:,}",
                    "type": "peak",
                    "status": "past",
                }
            )

        # Сортируем по дате
        timeline.sort(key=lambda x: x["date"])

        return {
            "events": timeline,
            "average_cycle_length_days": 1460,  # ~4 года
            "average_peak_after_halving_days": 520,  # ~17 месяцев
        }


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import json

    logging.basicConfig(level=logging.INFO)

    detector = CycleDetector()

    print("\n" + "=" * 60)
    print("🔄 АНАЛИЗ РЫНОЧНОГО ЦИКЛА BITCOIN")
    print("=" * 60)

    cycle_info = detector.detect_cycle("BTC")

    print(cycle_info.get_summary())

    print("\n" + "=" * 60)
    print("📅 ВРЕМЕННАЯ ШКАЛА ЦИКЛА")
    print("=" * 60)

    timeline = detector.get_cycle_timeline()
    for event in timeline["events"]:
        status = "✅" if event["status"] == "past" else "⏳"
        print(f"{status} {event['date']}: {event['event']}")

    print(f"\n📊 Средняя длина цикла: {timeline['average_cycle_length_days']} дней")
    print(f"📊 Средний пик после халвинга: {timeline['average_peak_after_halving_days']} дней")

    print("\n" + "=" * 60)
    print("JSON OUTPUT:")
    print(json.dumps(cycle_info.to_dict(), indent=2, ensure_ascii=False))
