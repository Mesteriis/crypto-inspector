"""
Scoring Engine - Composite scoring from multiple factors.

Combines data from all analysis modules into a single score 0-100:
- Technical Analysis (30%)
- Pattern Detection (20%)
- Market Cycle (15%)
- Derivatives (15%)
- Fear & Greed (10%)
- On-Chain (10%)

Score interpretation:
- 80-100: Strong bullish signal
- 60-79: Moderately bullish
- 40-59: Neutral
- 20-39: Moderately bearish
- 0-19: Strong bearish signal
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime

from service.analysis.technical import TechnicalIndicators

logger = logging.getLogger(__name__)


@dataclass
class ComponentScore:
    """Score for a single component."""

    name: str
    name_ru: str
    score: float  # 0-100
    weight: float  # 0-1
    weighted_score: float = 0
    details: dict = field(default_factory=dict)
    signal: str = "neutral"  # 'bullish', 'bearish', 'neutral'

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "name_ru": self.name_ru,
            "score": round(self.score, 1),
            "weight": self.weight,
            "weighted": round(self.weighted_score, 1),
            "signal": self.signal,
            "details": self.details,
        }


@dataclass
class CompositeScore:
    """Composite score from all components."""

    symbol: str
    timestamp: int

    # Final score
    total_score: float = 50.0
    signal: str = "neutral"
    signal_ru: str = "Neutral"

    # Components
    components: list[ComponentScore] = field(default_factory=list)

    # Recommendation
    recommendation: str = ""
    recommendation_ru: str = ""
    action: str = "hold"  # 'strong_buy', 'buy', 'hold', 'sell', 'strong_sell'

    # Risk
    risk_score: float = 50.0  # 0=low risk, 100=high risk
    risk_level: str = "medium"

    # Confidence
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
            "components": [c.to_dict() for c in self.components],
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

    def get_summary(self) -> str:
        """Get text summary."""
        if self.total_score >= 80:
            score_emoji = "+++"
        elif self.total_score >= 60:
            score_emoji = "++"
        elif self.total_score >= 55:
            score_emoji = "+"
        elif self.total_score <= 20:
            score_emoji = "---"
        elif self.total_score <= 40:
            score_emoji = "--"
        elif self.total_score <= 45:
            score_emoji = "-"
        else:
            score_emoji = "o"

        parts = [
            f"Composite Score: {self.symbol}",
            "",
            f"{score_emoji} Score: {self.total_score:.0f}/100 ({self.signal_ru})",
            "",
            "Components:",
        ]

        for c in self.components:
            c_mark = "+" if c.score >= 60 else "-" if c.score <= 40 else "o"
            parts.append(f"  {c_mark} {c.name}: {c.score:.0f} (weight {c.weight * 100:.0f}%)")

        parts.extend(
            [
                "",
                f"Risk: {self.risk_level} ({self.risk_score:.0f}/100)",
                f"Confidence: {self.confidence:.0f}%",
                "",
                f"Recommendation: {self.recommendation_ru}",
            ]
        )

        return "\n".join(parts)


class ScoringEngine:
    """Engine for composite scoring."""

    # Component weights
    WEIGHTS = {
        "technical": 0.30,
        "patterns": 0.20,
        "cycle": 0.15,
        "derivatives": 0.15,
        "fear_greed": 0.10,
        "onchain": 0.10,
    }

    def score_technical(self, indicators: TechnicalIndicators | None) -> ComponentScore:
        """
        Score from technical analysis.

        Returns:
            ComponentScore
        """
        if not indicators:
            return ComponentScore(
                name="technical",
                name_ru="Technical Analysis",
                score=50,
                weight=self.WEIGHTS["technical"],
                weighted_score=50 * self.WEIGHTS["technical"],
                signal="neutral",
            )

        score = 50.0
        details = {}

        # RSI (25% weight)
        if indicators.rsi:
            rsi = indicators.rsi
            details["rsi"] = rsi
            if rsi < 30:
                score += 12.5  # Oversold = bullish signal
            elif rsi < 45:
                score += 6
            elif rsi > 70:
                score -= 12.5  # Overbought = bearish
            elif rsi > 55:
                score -= 6

        # SMA200 (25% weight)
        if indicators.sma_200 and indicators.price:
            above_sma200 = indicators.price > indicators.sma_200
            details["above_sma200"] = above_sma200
            score += 12.5 if above_sma200 else -12.5

        # Golden/Death Cross (20% weight)
        if indicators.sma_50 and indicators.sma_200:
            golden_cross = indicators.sma_50 > indicators.sma_200
            details["golden_cross"] = golden_cross
            score += 10 if golden_cross else -10

        # MACD (15% weight)
        if indicators.macd_histogram is not None:
            details["macd_positive"] = indicators.macd_histogram > 0
            score += 7.5 if indicators.macd_histogram > 0 else -7.5

        # Bollinger Position (15% weight)
        if indicators.bb_position is not None:
            details["bb_position"] = indicators.bb_position
            if indicators.bb_position < 20:
                score += 7.5  # Near lower band
            elif indicators.bb_position > 80:
                score -= 7.5  # Near upper band

        score = max(0, min(100, score))

        return ComponentScore(
            name="technical",
            name_ru="Technical Analysis",
            score=score,
            weight=self.WEIGHTS["technical"],
            weighted_score=score * self.WEIGHTS["technical"],
            details=details,
            signal="bullish" if score >= 60 else "bearish" if score <= 40 else "neutral",
        )

    def score_patterns(self, pattern_summary: dict | None) -> ComponentScore:
        """
        Score from pattern detection.

        Args:
            pattern_summary: Summary from PatternDetector.get_summary()

        Returns:
            ComponentScore
        """
        if not pattern_summary:
            return ComponentScore(
                name="patterns",
                name_ru="Chart Patterns",
                score=50,
                weight=self.WEIGHTS["patterns"],
                weighted_score=50 * self.WEIGHTS["patterns"],
                signal="neutral",
            )

        score = pattern_summary.get("score", 50)
        bullish = pattern_summary.get("bullish_count", 0)
        bearish = pattern_summary.get("bearish_count", 0)

        details = {
            "bullish_patterns": pattern_summary.get("bullish_patterns", []),
            "bearish_patterns": pattern_summary.get("bearish_patterns", []),
            "total": pattern_summary.get("total_patterns", 0),
        }

        return ComponentScore(
            name="patterns",
            name_ru="Chart Patterns",
            score=score,
            weight=self.WEIGHTS["patterns"],
            weighted_score=score * self.WEIGHTS["patterns"],
            details=details,
            signal="bullish" if bullish > bearish else "bearish" if bearish > bullish else "neutral",
        )

    def score_cycle(self, cycle_data: dict | None) -> ComponentScore:
        """
        Score from market cycle analysis.

        Args:
            cycle_data: Cycle information

        Returns:
            ComponentScore
        """
        if not cycle_data:
            return ComponentScore(
                name="cycle",
                name_ru="Market Cycle",
                score=50,
                weight=self.WEIGHTS["cycle"],
                weighted_score=50 * self.WEIGHTS["cycle"],
                signal="neutral",
            )

        phase = cycle_data.get("phase", "unknown")

        # Phase to score mapping
        phase_scores = {
            "capitulation": 85,  # Great time to buy
            "accumulation": 75,
            "early_bull": 70,
            "bull_run": 60,
            "euphoria": 30,  # High risk
            "distribution": 35,
            "early_bear": 40,
            "bear_market": 45,
            "unknown": 50,
        }

        score = phase_scores.get(phase, 50)

        details = {
            "phase": phase,
            "phase_ru": cycle_data.get("phase_name_ru", phase),
            "days_since_halving": cycle_data.get("days_since_halving"),
            "from_ath_pct": cycle_data.get("distance_from_ath_pct"),
        }

        signal = "bullish" if score >= 60 else "bearish" if score <= 40 else "neutral"

        return ComponentScore(
            name="cycle",
            name_ru="Market Cycle",
            score=score,
            weight=self.WEIGHTS["cycle"],
            weighted_score=score * self.WEIGHTS["cycle"],
            details=details,
            signal=signal,
        )

    def score_fear_greed(self, fg_value: int | None) -> ComponentScore:
        """
        Score from Fear & Greed Index.

        Args:
            fg_value: Fear & Greed value 0-100

        Returns:
            ComponentScore
        """
        if fg_value is None:
            return ComponentScore(
                name="fear_greed",
                name_ru="Fear & Greed",
                score=50,
                weight=self.WEIGHTS["fear_greed"],
                weighted_score=50 * self.WEIGHTS["fear_greed"],
                signal="neutral",
            )

        # F&G is a contrarian indicator
        # Extreme Fear (0-25) = bullish signal (buy when others are fearful)
        # Extreme Greed (75-100) = bearish signal (sell when others are greedy)

        if fg_value < 25:
            score = 80  # Extreme Fear = time to buy
            interpretation = "extreme_fear"
        elif fg_value < 45:
            score = 65  # Fear
            interpretation = "fear"
        elif fg_value > 75:
            score = 20  # Extreme Greed = time to sell
            interpretation = "extreme_greed"
        elif fg_value > 55:
            score = 35  # Greed
            interpretation = "greed"
        else:
            score = 50  # Neutral
            interpretation = "neutral"

        details = {
            "value": fg_value,
            "interpretation": interpretation,
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

    def score_derivatives(self, deriv_data: dict | None) -> ComponentScore:
        """
        Score from derivatives data.

        Args:
            deriv_data: Derivatives information (funding rate, OI, L/S ratio)

        Returns:
            ComponentScore
        """
        if not deriv_data:
            return ComponentScore(
                name="derivatives",
                name_ru="Derivatives",
                score=50,
                weight=self.WEIGHTS["derivatives"],
                weighted_score=50 * self.WEIGHTS["derivatives"],
                signal="neutral",
            )

        score = 50.0
        details = {}

        # Funding Rate (contrarian indicator)
        funding_rate = deriv_data.get("funding_rate")
        if funding_rate is not None:
            fr_pct = funding_rate * 100
            details["funding_rate"] = fr_pct

            if fr_pct > 0.05:  # High positive = many longs
                score -= 15  # Bearish contrarian signal
            elif fr_pct < -0.02:  # Negative = shorts pay
                score += 15  # Bullish contrarian signal

        # Long/Short Ratio (contrarian indicator)
        ls_ratio = deriv_data.get("long_short_ratio")
        if ls_ratio:
            details["ls_ratio"] = ls_ratio

            if ls_ratio > 1.5:  # Many longs
                score -= 10
            elif ls_ratio < 0.67:  # Many shorts
                score += 10

        # Open Interest change
        oi_change = deriv_data.get("oi_change_24h")
        if oi_change:
            details["oi_change_24h"] = oi_change

        score = max(0, min(100, score))

        return ComponentScore(
            name="derivatives",
            name_ru="Derivatives",
            score=score,
            weight=self.WEIGHTS["derivatives"],
            weighted_score=score * self.WEIGHTS["derivatives"],
            details=details,
            signal="bullish" if score >= 60 else "bearish" if score <= 40 else "neutral",
        )

    def score_onchain(self, onchain_data: dict | None) -> ComponentScore:
        """
        Score from on-chain metrics.

        Args:
            onchain_data: On-chain information

        Returns:
            ComponentScore
        """
        if not onchain_data:
            return ComponentScore(
                name="onchain",
                name_ru="On-Chain",
                score=50,
                weight=self.WEIGHTS["onchain"],
                weighted_score=50 * self.WEIGHTS["onchain"],
                signal="neutral",
            )

        score = 50.0
        details = {}

        # MVRV ratio
        mvrv = onchain_data.get("mvrv")
        if mvrv:
            details["mvrv"] = mvrv
            if mvrv < 1.0:
                score += 15  # Undervalued
            elif mvrv > 3.5:
                score -= 15  # Overvalued

        # Exchange reserves change
        reserves_change = onchain_data.get("exchange_reserves_change")
        if reserves_change:
            details["exchange_reserves_change"] = reserves_change
            if reserves_change < -5:  # Outflow
                score += 10  # Bullish
            elif reserves_change > 5:  # Inflow
                score -= 10  # Bearish

        score = max(0, min(100, score))

        return ComponentScore(
            name="onchain",
            name_ru="On-Chain",
            score=score,
            weight=self.WEIGHTS["onchain"],
            weighted_score=score * self.WEIGHTS["onchain"],
            details=details,
            signal="bullish" if score >= 60 else "bearish" if score <= 40 else "neutral",
        )

    def calculate(
        self,
        symbol: str,
        indicators: TechnicalIndicators | None = None,
        pattern_summary: dict | None = None,
        cycle_data: dict | None = None,
        fg_value: int | None = None,
        deriv_data: dict | None = None,
        onchain_data: dict | None = None,
    ) -> CompositeScore:
        """
        Calculate composite score.

        Args:
            symbol: Coin symbol
            indicators: Technical indicators
            pattern_summary: Pattern detection summary
            cycle_data: Market cycle data
            fg_value: Fear & Greed value
            deriv_data: Derivatives data
            onchain_data: On-chain data

        Returns:
            CompositeScore
        """
        result = CompositeScore(
            symbol=symbol.upper(),
            timestamp=int(datetime.now().timestamp() * 1000),
        )

        # Collect all components
        components = [
            self.score_technical(indicators),
            self.score_patterns(pattern_summary),
            self.score_cycle(cycle_data),
            self.score_derivatives(deriv_data),
            self.score_fear_greed(fg_value),
            self.score_onchain(onchain_data),
        ]

        result.components = components

        # Calculate total score
        total_weighted = sum(c.weighted_score for c in components)
        total_weight = sum(c.weight for c in components)

        result.total_score = total_weighted / total_weight if total_weight > 0 else 50

        # Determine signal
        if result.total_score >= 75:
            result.signal = "strong_bullish"
            result.signal_ru = "Strong Bullish"
            result.action = "strong_buy"
        elif result.total_score >= 60:
            result.signal = "bullish"
            result.signal_ru = "Bullish"
            result.action = "buy"
        elif result.total_score >= 55:
            result.signal = "slightly_bullish"
            result.signal_ru = "Slightly Bullish"
            result.action = "buy"
        elif result.total_score <= 25:
            result.signal = "strong_bearish"
            result.signal_ru = "Strong Bearish"
            result.action = "strong_sell"
        elif result.total_score <= 40:
            result.signal = "bearish"
            result.signal_ru = "Bearish"
            result.action = "sell"
        elif result.total_score <= 45:
            result.signal = "slightly_bearish"
            result.signal_ru = "Slightly Bearish"
            result.action = "sell"
        else:
            result.signal = "neutral"
            result.signal_ru = "Neutral"
            result.action = "hold"

        # Generate recommendation
        result.recommendation_ru = self._generate_recommendation(result)
        result.recommendation = result.recommendation_ru

        # Risk level
        result.risk_score = 100 - result.total_score
        if result.risk_score > 70:
            result.risk_level = "high"
        elif result.risk_score > 40:
            result.risk_level = "medium"
        else:
            result.risk_level = "low"

        # Confidence based on component agreement
        signals = [c.signal for c in components if c.signal != "neutral"]
        if signals:
            bullish_count = sum(1 for s in signals if "bullish" in s)
            bearish_count = sum(1 for s in signals if "bearish" in s)
            result.confidence = (max(bullish_count, bearish_count) / len(signals)) * 100
        else:
            result.confidence = 50

        return result

    def _generate_recommendation(self, score: CompositeScore) -> str:
        """Generate recommendation text."""
        if score.action == "strong_buy":
            return "Excellent time to buy. All factors point to growth."
        elif score.action == "buy":
            return "Good time to buy. Consider DCA or adding to position."
        elif score.action == "strong_sell":
            return "Consider taking profits. High correction risk."
        elif score.action == "sell":
            return "Caution advised. Consider reducing position."
        else:
            return "Uncertainty. Wait for clearer signal."
