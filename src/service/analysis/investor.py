"""
Lazy Investor Analysis Module.

Provides high-level investment signals for passive investors:
- Do Nothing OK indicator
- Market phase detection
- Calm/stress indicator
- Red flags detection
- Market tension analysis
- Price context vs historical average
- DCA recommendations
- Weekly insights
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class MarketPhase(Enum):
    """Market phases for long-term investors."""

    ACCUMULATION = "accumulation"
    EARLY_GROWTH = "early_growth"
    GROWTH = "growth"
    LATE_GROWTH = "late_growth"
    EUPHORIA = "euphoria"
    DISTRIBUTION = "distribution"
    EARLY_DECLINE = "early_decline"
    CAPITULATION = "capitulation"


class RiskLevel(Enum):
    """Risk level classification."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


@dataclass
class RedFlag:
    """Single red flag indicator."""

    name: str
    name_ru: str
    severity: str  # warning, danger, critical
    description: str
    description_ru: str


@dataclass
class InvestorStatus:
    """Complete investor status snapshot."""

    timestamp: datetime = field(default_factory=datetime.now)

    # Do Nothing OK
    do_nothing_ok: bool = True
    do_nothing_reason: str = ""
    do_nothing_reason_ru: str = ""

    # Market Phase
    phase: MarketPhase = MarketPhase.GROWTH
    phase_confidence: int = 50
    phase_description: str = ""
    phase_description_ru: str = ""

    # Calm Indicator (0-100, higher = calmer)
    calm_score: int = 50
    calm_message: str = ""
    calm_message_ru: str = ""

    # Red Flags
    red_flags: list[RedFlag] = field(default_factory=list)

    # Market Tension (0-100, higher = more tension)
    tension_score: int = 50
    tension_level: str = "normal"
    tension_level_ru: str = "Норма"

    # Price Context
    current_price: float = 0
    avg_price_6m: float = 0
    price_diff_percent: float = 0
    price_context: str = ""
    price_context_ru: str = ""
    price_recommendation: str = ""
    price_recommendation_ru: str = ""

    # DCA Recommendation
    dca_signal: str = "neutral"
    dca_signal_ru: str = "Нейтрально"
    dca_total_amount: float = 0
    dca_btc_amount: float = 0
    dca_eth_amount: float = 0
    dca_alts_amount: float = 0
    dca_reason: str = ""
    dca_reason_ru: str = ""
    next_dca_date: str = ""

    # Weekly Insight
    weekly_summary: str = ""
    weekly_summary_ru: str = ""
    btc_status: str = ""
    eth_vs_btc: str = ""
    alts_status: str = ""
    dominance_trend: str = ""

    # Risk Level
    risk_level: RiskLevel = RiskLevel.MEDIUM

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "do_nothing_ok": {
                "value": self.do_nothing_ok,
                "state": "🟢 Всё ОК" if self.do_nothing_ok else "🔴 Внимание",
                "reason": self.do_nothing_reason,
                "reason_ru": self.do_nothing_reason_ru,
            },
            "phase": {
                "value": self.phase.value,
                "name": self.phase.name,
                "name_ru": self._get_phase_name_ru(),
                "confidence": self.phase_confidence,
                "description": self.phase_description,
                "description_ru": self.phase_description_ru,
            },
            "calm": {
                "score": self.calm_score,
                "level": self._get_calm_level(),
                "message": self.calm_message,
                "message_ru": self.calm_message_ru,
            },
            "red_flags": {
                "count": len(self.red_flags),
                "flags": [
                    {
                        "name": f.name,
                        "name_ru": f.name_ru,
                        "severity": f.severity,
                        "description": f.description,
                        "description_ru": f.description_ru,
                    }
                    for f in self.red_flags
                ],
                "flags_list": self._get_flags_list_ru(),
            },
            "tension": {
                "score": self.tension_score,
                "level": self.tension_level,
                "level_ru": self.tension_level_ru,
                "state": self._get_tension_state(),
            },
            "price_context": {
                "current_price": self.current_price,
                "avg_6m": self.avg_price_6m,
                "diff_percent": self.price_diff_percent,
                "context": self.price_context,
                "context_ru": self.price_context_ru,
                "recommendation": self.price_recommendation,
                "recommendation_ru": self.price_recommendation_ru,
            },
            "dca": {
                "signal": self.dca_signal,
                "signal_ru": self.dca_signal_ru,
                "state": self._get_dca_state(),
                "total_amount": self.dca_total_amount,
                "btc_amount": self.dca_btc_amount,
                "eth_amount": self.dca_eth_amount,
                "alts_amount": self.dca_alts_amount,
                "reason": self.dca_reason,
                "reason_ru": self.dca_reason_ru,
                "next_dca": self.next_dca_date,
            },
            "weekly_insight": {
                "summary": self.weekly_summary,
                "summary_ru": self.weekly_summary_ru,
                "btc_status": self.btc_status,
                "eth_vs_btc": self.eth_vs_btc,
                "alts_status": self.alts_status,
                "dominance_trend": self.dominance_trend,
            },
            "risk_level": {
                "value": self.risk_level.value,
                "name_ru": self._get_risk_name_ru(),
            },
        }

    def _get_phase_name_ru(self) -> str:
        """Get Russian name for market phase."""
        names = {
            MarketPhase.ACCUMULATION: "Накопление",
            MarketPhase.EARLY_GROWTH: "Ранний рост",
            MarketPhase.GROWTH: "Рост",
            MarketPhase.LATE_GROWTH: "Поздний рост",
            MarketPhase.EUPHORIA: "Эйфория",
            MarketPhase.DISTRIBUTION: "Распределение",
            MarketPhase.EARLY_DECLINE: "Ранний спад",
            MarketPhase.CAPITULATION: "Капитуляция",
        }
        return names.get(self.phase, "Неизвестно")

    def _get_calm_level(self) -> str:
        """Get calm level string."""
        if self.calm_score >= 80:
            return "very_calm"
        if self.calm_score >= 60:
            return "calm"
        if self.calm_score >= 40:
            return "neutral"
        if self.calm_score >= 20:
            return "anxious"
        return "panic"

    def _get_flags_list_ru(self) -> str:
        """Get formatted flags list in Russian."""
        if not self.red_flags:
            return "✅ Нет активных флагов"
        return "\n".join([f"⚠️ {f.name_ru}" for f in self.red_flags])

    def _get_tension_state(self) -> str:
        """Get tension state with emoji."""
        if self.tension_score <= 30:
            return "🟢 Низкая"
        if self.tension_score <= 60:
            return "🟡 Умеренная"
        return "🔴 Высокая"

    def _get_dca_state(self) -> str:
        """Get DCA state with emoji."""
        if self.dca_signal == "strong_buy":
            return "🟢 Отличное время"
        if self.dca_signal == "buy":
            return "🟢 Хорошее время"
        if self.dca_signal == "neutral":
            return "🟡 Нейтрально"
        if self.dca_signal == "wait":
            return "🟡 Лучше подождать"
        return "🔴 Не покупать"

    def _get_risk_name_ru(self) -> str:
        """Get Russian name for risk level."""
        names = {
            RiskLevel.LOW: "Низкий",
            RiskLevel.MEDIUM: "Средний",
            RiskLevel.HIGH: "Высокий",
            RiskLevel.EXTREME: "Экстремальный",
        }
        return names.get(self.risk_level, "Неизвестно")


class LazyInvestorAnalyzer:
    """
    Analyzer for passive/lazy investors.

    Combines multiple data sources to provide simple, actionable signals.
    """

    def __init__(self):
        self._last_status: InvestorStatus | None = None
        self._dca_weekly_budget: float = 100.0  # Default €100/week
        self._dca_weights = {"btc": 0.5, "eth": 0.3, "alts": 0.2}

    def set_dca_config(
        self,
        weekly_budget: float = 100.0,
        btc_weight: float = 0.5,
        eth_weight: float = 0.3,
        alts_weight: float = 0.2,
    ) -> None:
        """Configure DCA parameters."""
        self._dca_weekly_budget = weekly_budget
        total = btc_weight + eth_weight + alts_weight
        self._dca_weights = {
            "btc": btc_weight / total,
            "eth": eth_weight / total,
            "alts": alts_weight / total,
        }

    async def analyze(
        self,
        fear_greed: int | None = None,
        btc_price: float | None = None,
        btc_price_avg_6m: float | None = None,
        funding_rate: float | None = None,
        long_short_ratio: float | None = None,
        btc_dominance: float | None = None,
        rsi: float | None = None,
        cycle_phase: str | None = None,
        days_since_halving: int | None = None,
    ) -> InvestorStatus:
        """
        Analyze market and generate investor status.

        Args:
            fear_greed: Fear & Greed Index (0-100)
            btc_price: Current BTC price
            btc_price_avg_6m: 6-month average BTC price
            funding_rate: Funding rate (decimal, e.g., 0.0001)
            long_short_ratio: Long/Short ratio
            btc_dominance: BTC dominance percentage
            rsi: RSI value
            cycle_phase: Current cycle phase string
            days_since_halving: Days since last halving

        Returns:
            Complete investor status
        """
        status = InvestorStatus()

        # Detect red flags
        status.red_flags = self._detect_red_flags(
            fear_greed=fear_greed,
            funding_rate=funding_rate,
            long_short_ratio=long_short_ratio,
            rsi=rsi,
        )

        # Calculate tension score
        status.tension_score = self._calculate_tension(
            fear_greed=fear_greed,
            funding_rate=funding_rate,
            long_short_ratio=long_short_ratio,
            red_flags_count=len(status.red_flags),
        )
        status.tension_level, status.tension_level_ru = self._get_tension_level(status.tension_score)

        # Calculate calm score (inverse of tension + fear_greed factor)
        status.calm_score = self._calculate_calm(
            tension=status.tension_score,
            fear_greed=fear_greed,
        )
        status.calm_message, status.calm_message_ru = self._get_calm_message(status.calm_score)

        # Determine market phase
        status.phase, status.phase_confidence = self._determine_phase(
            fear_greed=fear_greed,
            rsi=rsi,
            cycle_phase=cycle_phase,
            days_since_halving=days_since_halving,
            btc_dominance=btc_dominance,
        )
        status.phase_description, status.phase_description_ru = self._get_phase_description(status.phase)

        # Price context
        if btc_price and btc_price_avg_6m:
            status.current_price = btc_price
            status.avg_price_6m = btc_price_avg_6m
            status.price_diff_percent = round(((btc_price - btc_price_avg_6m) / btc_price_avg_6m) * 100, 1)
            status.price_context, status.price_context_ru = self._get_price_context(status.price_diff_percent)
            status.price_recommendation, status.price_recommendation_ru = self._get_price_recommendation(
                status.price_diff_percent
            )

        # DCA calculation
        self._calculate_dca(status, fear_greed, rsi, status.price_diff_percent)

        # Risk level
        status.risk_level = self._determine_risk_level(
            tension=status.tension_score,
            red_flags_count=len(status.red_flags),
            phase=status.phase,
        )

        # Do Nothing OK determination
        status.do_nothing_ok = self._should_do_nothing(status)
        status.do_nothing_reason, status.do_nothing_reason_ru = self._get_do_nothing_reason(status)

        # Weekly insight
        self._generate_weekly_insight(
            status,
            btc_dominance=btc_dominance,
            fear_greed=fear_greed,
        )

        self._last_status = status
        return status

    def _detect_red_flags(
        self,
        fear_greed: int | None,
        funding_rate: float | None,
        long_short_ratio: float | None,
        rsi: float | None,
    ) -> list[RedFlag]:
        """Detect active red flags."""
        flags = []

        # Extreme Fear
        if fear_greed is not None and fear_greed <= 15:
            flags.append(
                RedFlag(
                    name="Extreme Fear",
                    name_ru="Экстремальный страх",
                    severity="warning",
                    description="Market is in extreme fear mode",
                    description_ru="Рынок в режиме экстремального страха",
                )
            )

        # Extreme Greed
        if fear_greed is not None and fear_greed >= 85:
            flags.append(
                RedFlag(
                    name="Extreme Greed",
                    name_ru="Экстремальная жадность",
                    severity="danger",
                    description="Market is overheated, correction likely",
                    description_ru="Рынок перегрет, вероятна коррекция",
                )
            )

        # High Funding Rate
        if funding_rate is not None and abs(funding_rate) > 0.001:
            if funding_rate > 0:
                flags.append(
                    RedFlag(
                        name="High Positive Funding",
                        name_ru="Высокий положительный фандинг",
                        severity="warning",
                        description="Longs paying shorts, overlevered longs",
                        description_ru="Лонги платят шортам, переизбыток лонгов",
                    )
                )
            else:
                flags.append(
                    RedFlag(
                        name="High Negative Funding",
                        name_ru="Высокий отрицательный фандинг",
                        severity="warning",
                        description="Shorts paying longs, overlevered shorts",
                        description_ru="Шорты платят лонгам, переизбыток шортов",
                    )
                )

        # Extreme Long/Short Ratio
        if long_short_ratio is not None:
            if long_short_ratio > 2.0:
                flags.append(
                    RedFlag(
                        name="Extreme Long Bias",
                        name_ru="Экстремальный перекос в лонги",
                        severity="danger",
                        description="Too many longs, squeeze risk",
                        description_ru="Слишком много лонгов, риск сквиза",
                    )
                )
            elif long_short_ratio < 0.5:
                flags.append(
                    RedFlag(
                        name="Extreme Short Bias",
                        name_ru="Экстремальный перекос в шорты",
                        severity="warning",
                        description="Too many shorts, short squeeze possible",
                        description_ru="Слишком много шортов, возможен шорт-сквиз",
                    )
                )

        # Overbought RSI
        if rsi is not None and rsi >= 80:
            flags.append(
                RedFlag(
                    name="RSI Overbought",
                    name_ru="RSI перекуплен",
                    severity="warning",
                    description="Market is overbought",
                    description_ru="Рынок перекуплен",
                )
            )

        # Oversold RSI
        if rsi is not None and rsi <= 20:
            flags.append(
                RedFlag(
                    name="RSI Oversold",
                    name_ru="RSI перепродан",
                    severity="warning",
                    description="Market is oversold",
                    description_ru="Рынок перепродан",
                )
            )

        return flags

    def _calculate_tension(
        self,
        fear_greed: int | None,
        funding_rate: float | None,
        long_short_ratio: float | None,
        red_flags_count: int,
    ) -> int:
        """Calculate market tension score (0-100)."""
        score = 50  # Baseline

        # Fear & Greed contribution
        if fear_greed is not None:
            # Extreme values increase tension
            if fear_greed <= 25 or fear_greed >= 75:
                score += 20
            elif fear_greed <= 35 or fear_greed >= 65:
                score += 10

        # Funding rate contribution
        if funding_rate is not None:
            if abs(funding_rate) > 0.001:
                score += 15
            elif abs(funding_rate) > 0.0005:
                score += 5

        # Long/Short ratio contribution
        if long_short_ratio is not None:
            if long_short_ratio > 1.5 or long_short_ratio < 0.7:
                score += 15
            elif long_short_ratio > 1.2 or long_short_ratio < 0.8:
                score += 5

        # Red flags contribution
        score += red_flags_count * 10

        return min(100, max(0, score))

    def _get_tension_level(self, score: int) -> tuple[str, str]:
        """Get tension level description."""
        if score <= 30:
            return "low", "Низкая"
        if score <= 50:
            return "normal", "Норма"
        if score <= 70:
            return "elevated", "Повышенная"
        return "high", "Высокая"

    def _calculate_calm(
        self,
        tension: int,
        fear_greed: int | None,
    ) -> int:
        """Calculate calm score (0-100, higher = calmer)."""
        # Start with inverse of tension
        score = 100 - tension

        # Adjust based on Fear & Greed
        if fear_greed is not None:
            # Neutral F&G (40-60) is calming
            if 40 <= fear_greed <= 60:
                score += 10
            # Extreme values reduce calm
            elif fear_greed <= 20 or fear_greed >= 80:
                score -= 15

        return min(100, max(0, score))

    def _get_calm_message(self, score: int) -> tuple[str, str]:
        """Get calm indicator message."""
        if score >= 80:
            return (
                "Markets are calm, stick to your plan",
                "Рынки спокойны, придерживайтесь плана",
            )
        if score >= 60:
            return (
                "Slight volatility, stay focused",
                "Небольшая волатильность, сохраняйте фокус",
            )
        if score >= 40:
            return (
                "Moderate activity, don't panic",
                "Умеренная активность, не паникуйте",
            )
        if score >= 20:
            return (
                "High volatility, be cautious",
                "Высокая волатильность, будьте осторожны",
            )
        return (
            "Extreme volatility, protect your capital",
            "Экстремальная волатильность, защитите капитал",
        )

    def _determine_phase(
        self,
        fear_greed: int | None,
        rsi: float | None,
        cycle_phase: str | None,
        days_since_halving: int | None,
        btc_dominance: float | None,
    ) -> tuple[MarketPhase, int]:
        """Determine current market phase."""
        confidence = 50

        # If we have cycle phase from cycles.py, use it
        if cycle_phase:
            phase_map = {
                "accumulation": MarketPhase.ACCUMULATION,
                "early_bull": MarketPhase.EARLY_GROWTH,
                "bull_market": MarketPhase.GROWTH,
                "late_bull": MarketPhase.LATE_GROWTH,
                "distribution": MarketPhase.DISTRIBUTION,
                "early_bear": MarketPhase.EARLY_DECLINE,
                "bear_market": MarketPhase.CAPITULATION,
                "capitulation": MarketPhase.CAPITULATION,
            }
            if cycle_phase.lower() in phase_map:
                return phase_map[cycle_phase.lower()], 70

        # Otherwise, estimate from available data
        phase = MarketPhase.GROWTH  # Default

        if fear_greed is not None:
            if fear_greed >= 80:
                phase = MarketPhase.EUPHORIA
                confidence = 75
            elif fear_greed >= 65:
                phase = MarketPhase.LATE_GROWTH
                confidence = 60
            elif fear_greed <= 20:
                phase = MarketPhase.CAPITULATION
                confidence = 70
            elif fear_greed <= 35:
                phase = MarketPhase.ACCUMULATION
                confidence = 60

        # Halving cycle adjustment
        if days_since_halving is not None:
            if days_since_halving < 180:
                # Shortly after halving - usually accumulation
                if phase == MarketPhase.GROWTH:
                    phase = MarketPhase.EARLY_GROWTH
                    confidence += 10
            elif 180 <= days_since_halving < 365:
                # 6-12 months after - growth phase
                if phase in [MarketPhase.ACCUMULATION, MarketPhase.GROWTH]:
                    phase = MarketPhase.GROWTH
                    confidence += 10
            elif 365 <= days_since_halving < 550:
                # 12-18 months after - often peak
                if phase == MarketPhase.GROWTH:
                    phase = MarketPhase.LATE_GROWTH
                    confidence += 5

        return phase, min(100, confidence)

    def _get_phase_description(self, phase: MarketPhase) -> tuple[str, str]:
        """Get phase description."""
        descriptions = {
            MarketPhase.ACCUMULATION: (
                "Smart money accumulating, good entry point",
                "Умные деньги накапливают, хорошая точка входа",
            ),
            MarketPhase.EARLY_GROWTH: (
                "Market starting to recover, early adopters buying",
                "Рынок начинает восстанавливаться, ранние инвесторы покупают",
            ),
            MarketPhase.GROWTH: (
                "Healthy growth phase, DCA is effective",
                "Фаза здорового роста, DCA эффективен",
            ),
            MarketPhase.LATE_GROWTH: (
                "Late cycle growth, consider reducing exposure",
                "Поздний рост цикла, рассмотрите снижение позиции",
            ),
            MarketPhase.EUPHORIA: (
                "Market euphoria, extreme caution advised",
                "Эйфория на рынке, рекомендуется крайняя осторожность",
            ),
            MarketPhase.DISTRIBUTION: (
                "Distribution phase, smart money exiting",
                "Фаза распределения, умные деньги выходят",
            ),
            MarketPhase.EARLY_DECLINE: (
                "Early decline, protect profits",
                "Начало спада, защитите прибыль",
            ),
            MarketPhase.CAPITULATION: (
                "Capitulation, potential buying opportunity",
                "Капитуляция, потенциальная возможность для покупки",
            ),
        }
        return descriptions.get(phase, ("Unknown phase", "Неизвестная фаза"))

    def _get_price_context(self, diff_percent: float) -> tuple[str, str]:
        """Get price context description."""
        if diff_percent <= -30:
            return "Far below average", "Значительно ниже среднего"
        if diff_percent <= -15:
            return "Below average", "Ниже среднего"
        if diff_percent <= -5:
            return "Slightly below average", "Немного ниже среднего"
        if diff_percent <= 5:
            return "Near average", "Около среднего"
        if diff_percent <= 15:
            return "Slightly above average", "Немного выше среднего"
        if diff_percent <= 30:
            return "Above average", "Выше среднего"
        return "Far above average", "Значительно выше среднего"

    def _get_price_recommendation(self, diff_percent: float) -> tuple[str, str]:
        """Get price-based recommendation."""
        if diff_percent <= -20:
            return (
                "Consider increasing DCA amount",
                "Рассмотрите увеличение DCA суммы",
            )
        if diff_percent <= -10:
            return "Good time for regular DCA", "Хорошее время для обычного DCA"
        if diff_percent <= 10:
            return "Continue regular DCA", "Продолжайте обычный DCA"
        if diff_percent <= 25:
            return (
                "Consider reducing DCA amount",
                "Рассмотрите уменьшение DCA суммы",
            )
        return "Consider pausing DCA", "Рассмотрите паузу в DCA"

    def _calculate_dca(
        self,
        status: InvestorStatus,
        fear_greed: int | None,
        rsi: float | None,
        price_diff: float,
    ) -> None:
        """Calculate DCA recommendation."""
        multiplier = 1.0

        # Fear & Greed adjustment
        if fear_greed is not None:
            if fear_greed <= 25:
                multiplier *= 1.5  # Buy more in fear
                status.dca_signal = "strong_buy"
                status.dca_signal_ru = "Отличное время покупать"
            elif fear_greed <= 40:
                multiplier *= 1.2
                status.dca_signal = "buy"
                status.dca_signal_ru = "Хорошее время покупать"
            elif fear_greed >= 80:
                multiplier *= 0.5  # Buy less in greed
                status.dca_signal = "wait"
                status.dca_signal_ru = "Лучше подождать"
            elif fear_greed >= 70:
                multiplier *= 0.8
                status.dca_signal = "neutral"
                status.dca_signal_ru = "Нейтрально"
            else:
                status.dca_signal = "neutral"
                status.dca_signal_ru = "Нейтрально"

        # Price context adjustment
        if price_diff <= -20:
            multiplier *= 1.3
        elif price_diff <= -10:
            multiplier *= 1.1
        elif price_diff >= 30:
            multiplier *= 0.6
        elif price_diff >= 15:
            multiplier *= 0.8

        # Calculate amounts
        base_amount = self._dca_weekly_budget * multiplier
        status.dca_total_amount = round(base_amount, 2)
        status.dca_btc_amount = round(base_amount * self._dca_weights["btc"], 2)
        status.dca_eth_amount = round(base_amount * self._dca_weights["eth"], 2)
        status.dca_alts_amount = round(base_amount * self._dca_weights["alts"], 2)

        # Generate reason
        reasons = []
        if fear_greed is not None:
            if fear_greed <= 25:
                reasons.append("Extreme fear = opportunity")
            elif fear_greed >= 80:
                reasons.append("Extreme greed = caution")

        if price_diff <= -15:
            reasons.append("Price below 6m average")
        elif price_diff >= 25:
            reasons.append("Price above 6m average")

        status.dca_reason = ", ".join(reasons) if reasons else "Regular DCA"
        status.dca_reason_ru = self._translate_dca_reason(status.dca_reason)

        # Next DCA date (assuming weekly)
        from datetime import timedelta

        next_monday = datetime.now() + timedelta(days=(7 - datetime.now().weekday()))
        status.next_dca_date = next_monday.strftime("%Y-%m-%d")

    def _translate_dca_reason(self, reason: str) -> str:
        """Translate DCA reason to Russian."""
        translations = {
            "Extreme fear = opportunity": "Экстремальный страх = возможность",
            "Extreme greed = caution": "Экстремальная жадность = осторожность",
            "Price below 6m average": "Цена ниже 6м среднего",
            "Price above 6m average": "Цена выше 6м среднего",
            "Regular DCA": "Обычный DCA",
        }
        parts = reason.split(", ")
        translated = [translations.get(p, p) for p in parts]
        return ", ".join(translated)

    def _determine_risk_level(
        self,
        tension: int,
        red_flags_count: int,
        phase: MarketPhase,
    ) -> RiskLevel:
        """Determine overall risk level."""
        risk_score = 0

        # Tension contribution
        risk_score += tension // 20

        # Red flags contribution
        risk_score += red_flags_count * 2

        # Phase contribution
        high_risk_phases = [
            MarketPhase.EUPHORIA,
            MarketPhase.DISTRIBUTION,
            MarketPhase.EARLY_DECLINE,
        ]
        if phase in high_risk_phases:
            risk_score += 3
        elif phase == MarketPhase.CAPITULATION:
            risk_score += 2  # High risk but also opportunity

        if risk_score <= 3:
            return RiskLevel.LOW
        if risk_score <= 6:
            return RiskLevel.MEDIUM
        if risk_score <= 9:
            return RiskLevel.HIGH
        return RiskLevel.EXTREME

    def _should_do_nothing(self, status: InvestorStatus) -> bool:
        """Determine if investor should do nothing."""
        # Do nothing is OK if:
        # 1. No critical red flags
        # 2. Not in extreme phases
        # 3. Tension is not extreme

        critical_flags = [f for f in status.red_flags if f.severity == "critical"]
        if critical_flags:
            return False

        extreme_phases = [MarketPhase.EUPHORIA, MarketPhase.CAPITULATION]
        if status.phase in extreme_phases:
            return False

        if status.tension_score >= 80:
            return False

        return True

    def _get_do_nothing_reason(self, status: InvestorStatus) -> tuple[str, str]:
        """Get reason for do nothing recommendation."""
        if status.do_nothing_ok:
            return (
                "Markets stable, continue your strategy",
                "Рынки стабильны, продолжайте свою стратегию",
            )

        reasons = []
        if status.red_flags:
            critical = [f for f in status.red_flags if f.severity in ["critical", "danger"]]
            if critical:
                reasons.append(f"{len(critical)} serious warnings")

        if status.phase == MarketPhase.EUPHORIA:
            reasons.append("Market euphoria")
        elif status.phase == MarketPhase.CAPITULATION:
            reasons.append("Market capitulation")

        if status.tension_score >= 80:
            reasons.append("High market tension")

        reason_en = ", ".join(reasons) if reasons else "Review your positions"
        reason_ru = self._translate_do_nothing_reason(reason_en)
        return reason_en, reason_ru

    def _translate_do_nothing_reason(self, reason: str) -> str:
        """Translate do nothing reason."""
        translations = {
            "serious warnings": "серьёзных предупреждений",
            "Market euphoria": "Рыночная эйфория",
            "Market capitulation": "Рыночная капитуляция",
            "High market tension": "Высокая рыночная напряжённость",
            "Review your positions": "Пересмотрите свои позиции",
        }
        result = reason
        for en, ru in translations.items():
            result = result.replace(en, ru)
        return result

    def _generate_weekly_insight(
        self,
        status: InvestorStatus,
        btc_dominance: float | None,
        fear_greed: int | None,
    ) -> None:
        """Generate weekly market insight."""
        insights = []

        # BTC status
        if status.phase in [MarketPhase.GROWTH, MarketPhase.EARLY_GROWTH]:
            status.btc_status = "📈 Bullish"
            insights.append("BTC in growth phase")
        elif status.phase in [MarketPhase.LATE_GROWTH, MarketPhase.EUPHORIA]:
            status.btc_status = "⚠️ Overextended"
            insights.append("BTC may be overextended")
        elif status.phase in [MarketPhase.ACCUMULATION, MarketPhase.CAPITULATION]:
            status.btc_status = "🔵 Accumulation Zone"
            insights.append("BTC in accumulation zone")
        else:
            status.btc_status = "📉 Bearish"
            insights.append("BTC showing weakness")

        # ETH vs BTC
        if btc_dominance is not None:
            if btc_dominance >= 55:
                status.eth_vs_btc = "BTC доминирует"
                insights.append("ETH underperforming BTC")
            elif btc_dominance <= 45:
                status.eth_vs_btc = "ALT Season близко"
                insights.append("Altcoin season approaching")
            else:
                status.eth_vs_btc = "Баланс"

        # Alts status
        if btc_dominance is not None and btc_dominance <= 50:
            status.alts_status = "🚀 Сильные"
        elif btc_dominance is not None and btc_dominance >= 58:
            status.alts_status = "😴 Слабые"
        else:
            status.alts_status = "➡️ Нейтрально"

        # Dominance trend
        if btc_dominance is not None:
            if btc_dominance >= 55:
                status.dominance_trend = f"↗️ {btc_dominance:.1f}%"
            elif btc_dominance <= 45:
                status.dominance_trend = f"↘️ {btc_dominance:.1f}%"
            else:
                status.dominance_trend = f"→ {btc_dominance:.1f}%"

        # Summary
        status.weekly_summary = "; ".join(insights) if insights else "Market stable"
        status.weekly_summary_ru = self._translate_weekly_summary(status.weekly_summary)

    def _translate_weekly_summary(self, summary: str) -> str:
        """Translate weekly summary."""
        translations = {
            "BTC in growth phase": "BTC в фазе роста",
            "BTC may be overextended": "BTC может быть перекуплен",
            "BTC in accumulation zone": "BTC в зоне накопления",
            "BTC showing weakness": "BTC показывает слабость",
            "ETH underperforming BTC": "ETH слабее BTC",
            "Altcoin season approaching": "Приближается альтсезон",
            "Market stable": "Рынок стабилен",
        }
        result = summary
        for en, ru in translations.items():
            result = result.replace(en, ru)
        return result

    def get_alert_if_needed(self, status: InvestorStatus) -> dict | None:
        """
        Check if alert should be sent.

        Returns alert dict if needed, None otherwise.
        """
        # Check for critical situations
        critical_flags = [f for f in status.red_flags if f.severity == "critical"]
        danger_flags = [f for f in status.red_flags if f.severity == "danger"]

        if critical_flags:
            return {
                "level": "critical",
                "title": "🚨 Crypto Critical Alert",
                "message": f"Critical: {', '.join([f.name_ru for f in critical_flags])}",
                "notification_id": "crypto_critical",
            }

        if len(danger_flags) >= 2:
            return {
                "level": "danger",
                "title": "⚠️ Crypto Danger Alert",
                "message": f"Multiple warnings: {', '.join([f.name_ru for f in danger_flags])}",
                "notification_id": "crypto_danger",
            }

        if status.phase == MarketPhase.EUPHORIA and status.tension_score >= 70:
            return {
                "level": "warning",
                "title": "📈 Market Euphoria Alert",
                "message": "Рынок в состоянии эйфории. Рассмотрите фиксацию прибыли.",
                "notification_id": "crypto_euphoria",
            }

        if status.phase == MarketPhase.CAPITULATION and status.calm_score >= 60:
            return {
                "level": "info",
                "title": "💎 Potential Buying Opportunity",
                "message": "Капитуляция на рынке. Возможность для долгосрочной покупки.",
                "notification_id": "crypto_opportunity",
            }

        return None


# Global instance
_investor_analyzer: LazyInvestorAnalyzer | None = None


def get_investor_analyzer() -> LazyInvestorAnalyzer:
    """Get global investor analyzer instance."""
    global _investor_analyzer
    if _investor_analyzer is None:
        _investor_analyzer = LazyInvestorAnalyzer()
    return _investor_analyzer
