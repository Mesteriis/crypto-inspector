"""
Divergence Detection Module.

Detects RSI and MACD divergences on multiple timeframes:
- Bullish divergence: Price makes lower low, indicator makes higher low
- Bearish divergence: Price makes higher high, indicator makes lower high

Timeframes: 1h, 4h, 1d
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class DivergenceType(Enum):
    """Type of divergence."""

    BULLISH = "bullish"  # Price lower low, indicator higher low
    BEARISH = "bearish"  # Price higher high, indicator lower high
    HIDDEN_BULLISH = "hidden_bullish"  # Price higher low, indicator lower low
    HIDDEN_BEARISH = "hidden_bearish"  # Price lower high, indicator higher high


class DivergenceStrength(Enum):
    """Strength of divergence signal."""

    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"


@dataclass
class Divergence:
    """Single detected divergence."""

    symbol: str
    timeframe: str  # "1h", "4h", "1d"
    indicator: str  # "rsi" or "macd"
    div_type: DivergenceType
    strength: DivergenceStrength
    detected_at: datetime
    price_point1: float  # First price point
    price_point2: float  # Second price point
    indicator_point1: float  # First indicator value
    indicator_point2: float  # Second indicator value
    current_price: float
    bars_apart: int  # Number of bars between points

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "indicator": self.indicator,
            "type": self.div_type.value,
            "type_ru": self._get_type_ru(),
            "strength": self.strength.value,
            "strength_ru": self._get_strength_ru(),
            "detected_at": self.detected_at.isoformat(),
            "price_points": [self.price_point1, self.price_point2],
            "indicator_points": [self.indicator_point1, self.indicator_point2],
            "current_price": self.current_price,
            "bars_apart": self.bars_apart,
            "signal_emoji": self._get_signal_emoji(),
            "description": self._get_description(),
            "description_ru": self._get_description_ru(),
        }

    def _get_type_ru(self) -> str:
        """Get Russian type name."""
        names = {
            DivergenceType.BULLISH: "Бычья",
            DivergenceType.BEARISH: "Медвежья",
            DivergenceType.HIDDEN_BULLISH: "Скрытая бычья",
            DivergenceType.HIDDEN_BEARISH: "Скрытая медвежья",
        }
        return names.get(self.div_type, "Неизвестно")

    def _get_strength_ru(self) -> str:
        """Get Russian strength."""
        names = {
            DivergenceStrength.WEAK: "Слабая",
            DivergenceStrength.MODERATE: "Умеренная",
            DivergenceStrength.STRONG: "Сильная",
        }
        return names.get(self.strength, "Неизвестно")

    def _get_signal_emoji(self) -> str:
        """Get emoji for signal."""
        if self.div_type in [DivergenceType.BULLISH, DivergenceType.HIDDEN_BULLISH]:
            return "🟢" if self.strength == DivergenceStrength.STRONG else "🟡"
        return "🔴" if self.strength == DivergenceStrength.STRONG else "🟠"

    def _get_description(self) -> str:
        """Get English description."""
        return (
            f"{self.div_type.value.replace('_', ' ').title()} {self.indicator.upper()} "
            f"divergence on {self.timeframe}"
        )

    def _get_description_ru(self) -> str:
        """Get Russian description."""
        return f"{self._get_type_ru()} дивергенция {self.indicator.upper()} на {self.timeframe}"


@dataclass
class DivergenceData:
    """Divergence analysis result for a symbol."""

    symbol: str
    timestamp: datetime
    divergences: list[Divergence] = field(default_factory=list)
    active_count: int = 0
    bullish_count: int = 0
    bearish_count: int = 0
    strongest_signal: Divergence | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "divergences": [d.to_dict() for d in self.divergences],
            "active_count": self.active_count,
            "bullish_count": self.bullish_count,
            "bearish_count": self.bearish_count,
            "strongest": self.strongest_signal.to_dict() if self.strongest_signal else None,
            "summary": self._get_summary(),
            "summary_ru": self._get_summary_ru(),
            "signal_state": self._get_signal_state(),
        }

    def _get_summary(self) -> str:
        """Get English summary."""
        if not self.divergences:
            return "No divergences detected"
        return f"{self.active_count} divergence(s): {self.bullish_count} bullish, {self.bearish_count} bearish"

    def _get_summary_ru(self) -> str:
        """Get Russian summary."""
        if not self.divergences:
            return "Дивергенций не обнаружено"
        return f"{self.active_count} дивергенция(й): {self.bullish_count} бычьих, {self.bearish_count} медвежьих"

    def _get_signal_state(self) -> str:
        """Get signal state for HA sensor."""
        if not self.divergences:
            return "None"
        if self.strongest_signal:
            return f"{self.strongest_signal.div_type.value.title()} {self.strongest_signal.timeframe}"
        return "Active"


class DivergenceDetector:
    """
    RSI and MACD divergence detector.

    Analyzes price action and indicators to find divergences.
    """

    def __init__(self, lookback_bars: int = 50):
        self._lookback = lookback_bars

    def detect(
        self,
        symbol: str,
        prices: list[float],  # Close prices, oldest first
        rsi_values: list[float] | None = None,
        macd_values: list[float] | None = None,  # MACD histogram
        timeframe: str = "1h",
    ) -> list[Divergence]:
        """
        Detect divergences in price data.

        Args:
            symbol: Trading symbol
            prices: List of close prices
            rsi_values: List of RSI values (same length as prices)
            macd_values: List of MACD histogram values
            timeframe: Timeframe string

        Returns:
            List of detected divergences
        """
        divergences = []

        if rsi_values and len(rsi_values) == len(prices):
            rsi_divs = self._find_divergences(symbol, prices, rsi_values, "rsi", timeframe)
            divergences.extend(rsi_divs)

        if macd_values and len(macd_values) == len(prices):
            macd_divs = self._find_divergences(symbol, prices, macd_values, "macd", timeframe)
            divergences.extend(macd_divs)

        return divergences

    def _find_divergences(
        self,
        symbol: str,
        prices: list[float],
        indicator: list[float],
        indicator_name: str,
        timeframe: str,
    ) -> list[Divergence]:
        """Find divergences between price and indicator."""
        divergences = []

        # Find local minima and maxima in recent data
        lookback = min(self._lookback, len(prices))
        recent_prices = prices[-lookback:]
        recent_indicator = indicator[-lookback:]

        # Find swing lows (for bullish divergence)
        price_lows = self._find_swing_lows(recent_prices)
        ind_lows = self._find_swing_lows(recent_indicator)

        # Find swing highs (for bearish divergence)
        price_highs = self._find_swing_highs(recent_prices)
        ind_highs = self._find_swing_highs(recent_indicator)

        # Check for bullish divergence (price lower low, indicator higher low)
        if len(price_lows) >= 2 and len(ind_lows) >= 2:
            p1_idx, p1_val = price_lows[-2]
            p2_idx, p2_val = price_lows[-1]
            i1_idx, i1_val = ind_lows[-2]
            i2_idx, i2_val = ind_lows[-1]

            # Price makes lower low
            if p2_val < p1_val:
                # Indicator makes higher low
                if i2_val > i1_val:
                    strength = self._calculate_strength(p1_val, p2_val, i1_val, i2_val)
                    divergences.append(
                        Divergence(
                            symbol=symbol,
                            timeframe=timeframe,
                            indicator=indicator_name,
                            div_type=DivergenceType.BULLISH,
                            strength=strength,
                            detected_at=datetime.now(),
                            price_point1=p1_val,
                            price_point2=p2_val,
                            indicator_point1=i1_val,
                            indicator_point2=i2_val,
                            current_price=recent_prices[-1],
                            bars_apart=p2_idx - p1_idx,
                        )
                    )

            # Check for hidden bullish (price higher low, indicator lower low)
            if p2_val > p1_val and i2_val < i1_val:
                strength = self._calculate_strength(p1_val, p2_val, i1_val, i2_val)
                divergences.append(
                    Divergence(
                        symbol=symbol,
                        timeframe=timeframe,
                        indicator=indicator_name,
                        div_type=DivergenceType.HIDDEN_BULLISH,
                        strength=strength,
                        detected_at=datetime.now(),
                        price_point1=p1_val,
                        price_point2=p2_val,
                        indicator_point1=i1_val,
                        indicator_point2=i2_val,
                        current_price=recent_prices[-1],
                        bars_apart=p2_idx - p1_idx,
                    )
                )

        # Check for bearish divergence (price higher high, indicator lower high)
        if len(price_highs) >= 2 and len(ind_highs) >= 2:
            p1_idx, p1_val = price_highs[-2]
            p2_idx, p2_val = price_highs[-1]
            i1_idx, i1_val = ind_highs[-2]
            i2_idx, i2_val = ind_highs[-1]

            # Price makes higher high
            if p2_val > p1_val:
                # Indicator makes lower high
                if i2_val < i1_val:
                    strength = self._calculate_strength(p1_val, p2_val, i1_val, i2_val)
                    divergences.append(
                        Divergence(
                            symbol=symbol,
                            timeframe=timeframe,
                            indicator=indicator_name,
                            div_type=DivergenceType.BEARISH,
                            strength=strength,
                            detected_at=datetime.now(),
                            price_point1=p1_val,
                            price_point2=p2_val,
                            indicator_point1=i1_val,
                            indicator_point2=i2_val,
                            current_price=recent_prices[-1],
                            bars_apart=p2_idx - p1_idx,
                        )
                    )

            # Check for hidden bearish (price lower high, indicator higher high)
            if p2_val < p1_val and i2_val > i1_val:
                strength = self._calculate_strength(p1_val, p2_val, i1_val, i2_val)
                divergences.append(
                    Divergence(
                        symbol=symbol,
                        timeframe=timeframe,
                        indicator=indicator_name,
                        div_type=DivergenceType.HIDDEN_BEARISH,
                        strength=strength,
                        detected_at=datetime.now(),
                        price_point1=p1_val,
                        price_point2=p2_val,
                        indicator_point1=i1_val,
                        indicator_point2=i2_val,
                        current_price=recent_prices[-1],
                        bars_apart=p2_idx - p1_idx,
                    )
                )

        return divergences

    def _find_swing_lows(self, data: list[float], window: int = 5) -> list[tuple[int, float]]:
        """Find swing lows in data."""
        lows = []
        for i in range(window, len(data) - window):
            is_low = True
            for j in range(i - window, i + window + 1):
                if j != i and data[j] < data[i]:
                    is_low = False
                    break
            if is_low:
                lows.append((i, data[i]))
        return lows

    def _find_swing_highs(self, data: list[float], window: int = 5) -> list[tuple[int, float]]:
        """Find swing highs in data."""
        highs = []
        for i in range(window, len(data) - window):
            is_high = True
            for j in range(i - window, i + window + 1):
                if j != i and data[j] > data[i]:
                    is_high = False
                    break
            if is_high:
                highs.append((i, data[i]))
        return highs

    def _calculate_strength(
        self,
        price1: float,
        price2: float,
        ind1: float,
        ind2: float,
    ) -> DivergenceStrength:
        """Calculate divergence strength based on magnitude."""
        # Calculate percentage differences
        price_diff = abs((price2 - price1) / price1 * 100)
        ind_diff = abs((ind2 - ind1) / (ind1 if ind1 != 0 else 1) * 100)

        # Combine for overall strength
        combined = (price_diff + ind_diff) / 2

        if combined >= 10:
            return DivergenceStrength.STRONG
        if combined >= 5:
            return DivergenceStrength.MODERATE
        return DivergenceStrength.WEAK

    def analyze_symbol(
        self,
        symbol: str,
        data_1h: dict[str, list[float]] | None = None,
        data_4h: dict[str, list[float]] | None = None,
        data_1d: dict[str, list[float]] | None = None,
    ) -> DivergenceData:
        """
        Analyze all timeframes for a symbol.

        Args:
            symbol: Trading symbol
            data_1h: Dict with 'prices', 'rsi', 'macd' for 1h
            data_4h: Dict with 'prices', 'rsi', 'macd' for 4h
            data_1d: Dict with 'prices', 'rsi', 'macd' for 1d

        Returns:
            DivergenceData with all detected divergences
        """
        all_divergences = []

        if data_1h:
            divs = self.detect(
                symbol,
                data_1h.get("prices", []),
                data_1h.get("rsi"),
                data_1h.get("macd"),
                "1h",
            )
            all_divergences.extend(divs)

        if data_4h:
            divs = self.detect(
                symbol,
                data_4h.get("prices", []),
                data_4h.get("rsi"),
                data_4h.get("macd"),
                "4h",
            )
            all_divergences.extend(divs)

        if data_1d:
            divs = self.detect(
                symbol,
                data_1d.get("prices", []),
                data_1d.get("rsi"),
                data_1d.get("macd"),
                "1d",
            )
            all_divergences.extend(divs)

        # Count by type
        bullish = [d for d in all_divergences if d.div_type in [DivergenceType.BULLISH, DivergenceType.HIDDEN_BULLISH]]
        bearish = [d for d in all_divergences if d.div_type in [DivergenceType.BEARISH, DivergenceType.HIDDEN_BEARISH]]

        # Find strongest signal (prefer higher timeframes)
        strongest = None
        if all_divergences:
            # Sort by timeframe priority (1d > 4h > 1h) and strength
            tf_priority = {"1d": 3, "4h": 2, "1h": 1}
            strength_priority = {
                DivergenceStrength.STRONG: 3,
                DivergenceStrength.MODERATE: 2,
                DivergenceStrength.WEAK: 1,
            }
            sorted_divs = sorted(
                all_divergences,
                key=lambda x: (
                    tf_priority.get(x.timeframe, 0),
                    strength_priority.get(x.strength, 0),
                ),
                reverse=True,
            )
            strongest = sorted_divs[0]

        return DivergenceData(
            symbol=symbol,
            timestamp=datetime.now(),
            divergences=all_divergences,
            active_count=len(all_divergences),
            bullish_count=len(bullish),
            bearish_count=len(bearish),
            strongest_signal=strongest,
        )


# Global instance
_divergence_detector: DivergenceDetector | None = None


def get_divergence_detector() -> DivergenceDetector:
    """Get global divergence detector instance."""
    global _divergence_detector
    if _divergence_detector is None:
        _divergence_detector = DivergenceDetector()
    return _divergence_detector
