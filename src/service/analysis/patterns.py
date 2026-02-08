"""
Pattern Detection Module.

Detects chart patterns:
- Golden Cross / Death Cross
- Double Top / Double Bottom
- RSI Overbought / Oversold
- Trend streaks
- Bollinger Breakouts
- Support/Resistance Breakouts
- Higher Highs / Lower Lows
"""

import logging
from dataclasses import dataclass
from enum import StrEnum

from service.analysis.technical import CandleDict, TechnicalAnalyzer

logger = logging.getLogger(__name__)


class PatternType(StrEnum):
    """Pattern types."""

    GOLDEN_CROSS = "golden_cross"
    DEATH_CROSS = "death_cross"
    DOUBLE_TOP = "double_top"
    DOUBLE_BOTTOM = "double_bottom"
    RSI_OVERSOLD = "rsi_oversold"
    RSI_OVERBOUGHT = "rsi_overbought"
    BULLISH_TREND = "bullish_trend"
    BEARISH_TREND = "bearish_trend"
    BB_BREAKOUT_UP = "bb_breakout_up"
    BB_BREAKOUT_DOWN = "bb_breakout_down"
    RESISTANCE_BREAK = "resistance_break"
    SUPPORT_BREAK = "support_break"
    HIGHER_HIGHS = "higher_highs"
    LOWER_LOWS = "lower_lows"


@dataclass
class DetectedPattern:
    """Detected chart pattern."""

    pattern_type: PatternType
    name: str
    name_ru: str
    direction: str  # 'bullish', 'bearish', 'neutral'
    strength: float  # 0-100
    confidence: float  # 0-100
    timestamp: int
    price: float
    description: str
    description_ru: str

    # Historical stats
    historical_win_rate: float | None = None
    historical_avg_return: float | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "type": self.pattern_type.value,
            "name": self.name,
            "name_ru": self.name_ru,
            "direction": self.direction,
            "strength": self.strength,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
            "price": self.price,
            "description": self.description,
            "description_ru": self.description_ru,
            "historical_win_rate": self.historical_win_rate,
            "historical_avg_return": self.historical_avg_return,
        }


# Pattern definitions with historical context
PATTERN_STATS = {
    PatternType.GOLDEN_CROSS: {
        "name": "Golden Cross",
        "name_ru": "Золотой крест",
        "direction": "bullish",
        "win_rate": 65,
        "avg_return": 12.5,
        "description": "SMA50 crossed above SMA200 - bullish signal",
        "description_ru": "SMA50 пересекла SMA200 снизу вверх - бычий сигнал",
    },
    PatternType.DEATH_CROSS: {
        "name": "Death Cross",
        "name_ru": "Крест смерти",
        "direction": "bearish",
        "win_rate": 60,
        "avg_return": -10.5,
        "description": "SMA50 crossed below SMA200 - bearish signal",
        "description_ru": "SMA50 пересекла SMA200 сверху вниз - медвежий сигнал",
    },
    PatternType.DOUBLE_TOP: {
        "name": "Double Top",
        "name_ru": "Двойная вершина",
        "direction": "bearish",
        "win_rate": 72,
        "avg_return": -8.0,
        "description": "Price failed to break above resistance twice",
        "description_ru": "Цена дважды не смогла пробить сопротивление",
    },
    PatternType.DOUBLE_BOTTOM: {
        "name": "Double Bottom",
        "name_ru": "Двойное дно",
        "direction": "bullish",
        "win_rate": 70,
        "avg_return": 9.0,
        "description": "Price bounced from support twice",
        "description_ru": "Цена дважды отскочила от поддержки",
    },
    PatternType.RSI_OVERSOLD: {
        "name": "RSI Oversold",
        "name_ru": "RSI перепродан",
        "direction": "bullish",
        "win_rate": 62,
        "avg_return": 5.5,
        "description": "RSI below 30 - potential bounce",
        "description_ru": "RSI ниже 30 - возможен отскок",
    },
    PatternType.RSI_OVERBOUGHT: {
        "name": "RSI Overbought",
        "name_ru": "RSI перекуплен",
        "direction": "bearish",
        "win_rate": 58,
        "avg_return": -4.5,
        "description": "RSI above 70 - potential correction",
        "description_ru": "RSI выше 70 - возможна коррекция",
    },
    PatternType.BULLISH_TREND: {
        "name": "Bullish Trend",
        "name_ru": "Бычий тренд",
        "direction": "bullish",
        "win_rate": 55,
        "avg_return": 3.0,
        "description": "Multiple consecutive up days",
        "description_ru": "Несколько дней роста подряд",
    },
    PatternType.BEARISH_TREND: {
        "name": "Bearish Trend",
        "name_ru": "Медвежий тренд",
        "direction": "bearish",
        "win_rate": 55,
        "avg_return": -3.0,
        "description": "Multiple consecutive down days",
        "description_ru": "Несколько дней падения подряд",
    },
    PatternType.BB_BREAKOUT_UP: {
        "name": "BB Breakout Up",
        "name_ru": "Пробой BB вверх",
        "direction": "bullish",
        "win_rate": 52,
        "avg_return": 2.5,
        "description": "Price broke above upper Bollinger Band",
        "description_ru": "Цена пробила верхнюю границу Боллинджера",
    },
    PatternType.BB_BREAKOUT_DOWN: {
        "name": "BB Breakout Down",
        "name_ru": "Пробой BB вниз",
        "direction": "bearish",
        "win_rate": 52,
        "avg_return": -2.5,
        "description": "Price broke below lower Bollinger Band",
        "description_ru": "Цена пробила нижнюю границу Боллинджера",
    },
    PatternType.HIGHER_HIGHS: {
        "name": "Higher Highs",
        "name_ru": "Растущие максимумы",
        "direction": "bullish",
        "win_rate": 60,
        "avg_return": 4.0,
        "description": "Sequence of higher highs - uptrend confirmation",
        "description_ru": "Серия растущих максимумов - подтверждение аптренда",
    },
    PatternType.LOWER_LOWS: {
        "name": "Lower Lows",
        "name_ru": "Падающие минимумы",
        "direction": "bearish",
        "win_rate": 60,
        "avg_return": -4.0,
        "description": "Sequence of lower lows - downtrend confirmation",
        "description_ru": "Серия падающих минимумов - подтверждение даунтренда",
    },
}


class PatternDetector:
    """Detects chart patterns from candlestick data."""

    def __init__(self):
        self.ta = TechnicalAnalyzer()

    def detect_all(
        self,
        symbol: str,
        candles: list[CandleDict],
        timeframe: str = "1d",
    ) -> list[DetectedPattern]:
        """
        Detect all patterns.

        Args:
            symbol: Coin symbol
            candles: List of candles
            timeframe: Timeframe

        Returns:
            List of detected patterns
        """
        if len(candles) < 50:
            logger.warning(f"Insufficient data for pattern detection: {len(candles)} candles")
            return []

        patterns = []

        # Calculate indicators
        closes = [float(c["close"]) for c in candles]
        current_price = closes[-1]
        current_ts = candles[-1]["timestamp"]

        # SMA calculations
        sma_50 = self.ta.calc_sma(closes, 50)
        sma_200 = self.ta.calc_sma(closes, 200) if len(closes) >= 200 else None
        prev_sma_50 = self.ta.calc_sma(closes[:-1], 50)
        prev_sma_200 = self.ta.calc_sma(closes[:-1], 200) if len(closes) >= 201 else None

        # 1. Golden/Death Cross
        if sma_50 and sma_200 and prev_sma_50 and prev_sma_200:
            if prev_sma_50 <= prev_sma_200 and sma_50 > sma_200:
                patterns.append(self._create_pattern(PatternType.GOLDEN_CROSS, current_price, current_ts, 80))
            elif prev_sma_50 >= prev_sma_200 and sma_50 < sma_200:
                patterns.append(self._create_pattern(PatternType.DEATH_CROSS, current_price, current_ts, 80))

        # 2. RSI Extremes
        rsi = self.ta.calc_rsi(closes)
        if rsi:
            if rsi < 30:
                strength = 100 - (rsi / 30 * 100)  # Lower RSI = stronger signal
                patterns.append(self._create_pattern(PatternType.RSI_OVERSOLD, current_price, current_ts, strength))
            elif rsi > 70:
                strength = ((rsi - 70) / 30) * 100  # Higher RSI = stronger signal
                patterns.append(self._create_pattern(PatternType.RSI_OVERBOUGHT, current_price, current_ts, strength))

        # 3. Bollinger Breakouts
        bb_upper, bb_middle, bb_lower, bb_pos = self.ta.calc_bollinger_bands(closes)
        if bb_upper and bb_lower:
            if current_price > bb_upper:
                patterns.append(self._create_pattern(PatternType.BB_BREAKOUT_UP, current_price, current_ts, 60))
            elif current_price < bb_lower:
                patterns.append(self._create_pattern(PatternType.BB_BREAKOUT_DOWN, current_price, current_ts, 60))

        # 4. Trend Streaks (5+ consecutive days)
        streak = self._count_streak(closes[-10:])
        if streak >= 5:
            patterns.append(
                self._create_pattern(PatternType.BULLISH_TREND, current_price, current_ts, min(100, streak * 15))
            )
        elif streak <= -5:
            patterns.append(
                self._create_pattern(PatternType.BEARISH_TREND, current_price, current_ts, min(100, abs(streak) * 15))
            )

        # 5. Higher Highs / Lower Lows
        highs = [float(c["high"]) for c in candles[-10:]]
        lows = [float(c["low"]) for c in candles[-10:]]

        hh_count = self._count_higher_highs(highs)
        ll_count = self._count_lower_lows(lows)

        if hh_count >= 3:
            patterns.append(
                self._create_pattern(PatternType.HIGHER_HIGHS, current_price, current_ts, min(100, hh_count * 20))
            )
        if ll_count >= 3:
            patterns.append(
                self._create_pattern(PatternType.LOWER_LOWS, current_price, current_ts, min(100, ll_count * 20))
            )

        # 6. Double Top / Double Bottom
        double_pattern = self._detect_double_pattern(candles[-30:])
        if double_pattern:
            patterns.append(self._create_pattern(double_pattern, current_price, current_ts, 70))

        return patterns

    def _create_pattern(
        self,
        pattern_type: PatternType,
        price: float,
        timestamp: int,
        strength: float,
    ) -> DetectedPattern:
        """Create a DetectedPattern from pattern type."""
        stats = PATTERN_STATS[pattern_type]

        return DetectedPattern(
            pattern_type=pattern_type,
            name=stats["name"],
            name_ru=stats["name_ru"],
            direction=stats["direction"],
            strength=strength,
            confidence=min(100, strength * 0.9),
            timestamp=timestamp,
            price=price,
            description=stats["description"],
            description_ru=stats["description_ru"],
            historical_win_rate=stats["win_rate"],
            historical_avg_return=stats["avg_return"],
        )

    def _count_streak(self, prices: list[float]) -> int:
        """Count consecutive up/down days."""
        if len(prices) < 2:
            return 0

        streak = 0
        for i in range(1, len(prices)):
            if prices[i] > prices[i - 1]:
                if streak >= 0:
                    streak += 1
                else:
                    streak = 1
            elif prices[i] < prices[i - 1]:
                if streak <= 0:
                    streak -= 1
                else:
                    streak = -1
            # Equal prices don't change streak

        return streak

    def _count_higher_highs(self, highs: list[float]) -> int:
        """Count sequence of higher highs."""
        count = 0
        for i in range(1, len(highs)):
            if highs[i] > highs[i - 1]:
                count += 1
            else:
                count = 0
        return count

    def _count_lower_lows(self, lows: list[float]) -> int:
        """Count sequence of lower lows."""
        count = 0
        for i in range(1, len(lows)):
            if lows[i] < lows[i - 1]:
                count += 1
            else:
                count = 0
        return count

    def _detect_double_pattern(self, candles: list[CandleDict]) -> PatternType | None:
        """
        Detect double top or double bottom pattern.

        Looks for two peaks/troughs at similar levels.
        """
        if len(candles) < 10:
            return None

        highs = [float(c["high"]) for c in candles]
        lows = [float(c["low"]) for c in candles]

        # Find local maxima for double top
        peaks = []
        for i in range(2, len(highs) - 2):
            if (
                highs[i] > highs[i - 1]
                and highs[i] > highs[i - 2]
                and highs[i] > highs[i + 1]
                and highs[i] > highs[i + 2]
            ):
                peaks.append((i, highs[i]))

        # Check for double top (two peaks at similar level)
        if len(peaks) >= 2:
            for i in range(len(peaks) - 1):
                for j in range(i + 1, len(peaks)):
                    if abs(peaks[i][1] - peaks[j][1]) / peaks[i][1] < 0.02:  # Within 2%
                        if peaks[j][0] - peaks[i][0] >= 5:  # At least 5 candles apart
                            return PatternType.DOUBLE_TOP

        # Find local minima for double bottom
        troughs = []
        for i in range(2, len(lows) - 2):
            if lows[i] < lows[i - 1] and lows[i] < lows[i - 2] and lows[i] < lows[i + 1] and lows[i] < lows[i + 2]:
                troughs.append((i, lows[i]))

        # Check for double bottom
        if len(troughs) >= 2:
            for i in range(len(troughs) - 1):
                for j in range(i + 1, len(troughs)):
                    if abs(troughs[i][1] - troughs[j][1]) / troughs[i][1] < 0.02:
                        if troughs[j][0] - troughs[i][0] >= 5:
                            return PatternType.DOUBLE_BOTTOM

        return None

    def get_summary(self, patterns: list[DetectedPattern]) -> dict:
        """
        Get pattern summary.

        Args:
            patterns: List of detected patterns

        Returns:
            Summary dictionary
        """
        bullish = [p for p in patterns if p.direction == "bullish"]
        bearish = [p for p in patterns if p.direction == "bearish"]

        total_bullish_strength = sum(p.strength for p in bullish)
        total_bearish_strength = sum(p.strength for p in bearish)

        if not patterns:
            overall = "neutral"
            score = 50
        elif total_bullish_strength > total_bearish_strength * 1.5:
            overall = "bullish"
            score = 60 + min(30, (total_bullish_strength - total_bearish_strength) / 5)
        elif total_bearish_strength > total_bullish_strength * 1.5:
            overall = "bearish"
            score = 40 - min(30, (total_bearish_strength - total_bullish_strength) / 5)
        else:
            overall = "neutral"
            score = 50

        return {
            "total_patterns": len(patterns),
            "bullish_count": len(bullish),
            "bearish_count": len(bearish),
            "bullish_patterns": [p.name for p in bullish],
            "bearish_patterns": [p.name for p in bearish],
            "overall": overall,
            "score": round(score, 1),
            "strongest_bullish": max(bullish, key=lambda p: p.strength).name if bullish else None,
            "strongest_bearish": max(bearish, key=lambda p: p.strength).name if bearish else None,
        }
