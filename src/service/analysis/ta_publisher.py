"""
Technical Analysis Publisher.

Calculates and publishes technical indicators to Home Assistant sensors:
- RSI, MACD, Bollinger Bands
- Trend detection (uptrend/downtrend/sideways)
- Support/Resistance levels
- Multi-timeframe confluence
"""

import logging
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class TASignals:
    """Technical analysis signals for a symbol."""

    symbol: str
    timeframe: str
    timestamp: datetime

    # Indicators
    rsi: float | None = None
    macd_signal: str | None = None  # "Bullish", "Bearish", "Neutral"
    bb_position: float | None = None  # 0-100 (0=below lower, 100=above upper)

    # Trend
    trend: str = "sideways"  # "uptrend", "downtrend", "sideways"
    trend_strength: float = 0.0  # 0-100

    # Levels
    support: float | None = None
    resistance: float | None = None

    # Confluence
    confluence_score: int = 50  # 0-100 (0=very bearish, 100=very bullish)
    signal: str = "Neutral"  # "Strong Buy", "Buy", "Neutral", "Sell", "Strong Sell"

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "timestamp": self.timestamp.isoformat(),
            "rsi": self.rsi,
            "macd_signal": self.macd_signal,
            "bb_position": self.bb_position,
            "trend": self.trend,
            "trend_strength": self.trend_strength,
            "support": self.support,
            "resistance": self.resistance,
            "confluence_score": self.confluence_score,
            "signal": self.signal,
        }


class TAPublisher:
    """
    Technical Analysis Publisher.

    Calculates TA indicators and publishes to HA sensors using
    generic dictionary-based sensors for multi-currency support.
    """

    def __init__(self):
        self._cache: dict[str, TASignals] = {}
        # Aggregated data for dictionary-based sensors
        self._rsi_values: dict[str, float] = {}
        self._macd_signals: dict[str, str] = {}
        self._bb_positions: dict[str, float] = {}
        self._trends: dict[str, str] = {}
        self._supports: dict[str, float] = {}
        self._resistances: dict[str, float] = {}
        self._mtf_trends: dict[str, dict] = {}

    async def calculate_and_publish(
        self,
        symbol: str,
        candles: list[dict],
        timeframe: str = "4h",
    ) -> TASignals | None:
        """
        Calculate technical indicators and publish to HA.

        Args:
            symbol: Trading pair (e.g., "BTC/USDT")
            candles: List of candle dicts with open, high, low, close, volume
            timeframe: Timeframe string

        Returns:
            TASignals object
        """
        if len(candles) < 200:
            logger.warning(f"Insufficient candles for {symbol}: {len(candles)}")
            return None

        try:
            # Extract closes for calculations
            closes = [float(c.get("close", 0)) for c in candles]
            highs = [float(c.get("high", 0)) for c in candles]
            lows = [float(c.get("low", 0)) for c in candles]

            # Calculate indicators
            rsi = self._calculate_rsi(closes)
            macd_signal = self._get_macd_signal(closes)
            bb_position = self._calculate_bb_position(closes)
            trend, trend_strength = self._detect_trend(closes)
            support, resistance = self._find_levels(closes, highs, lows)
            confluence = self._calculate_confluence(rsi, macd_signal, bb_position, trend)
            signal = self._get_signal(confluence)

            signals = TASignals(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=datetime.now(),
                rsi=rsi,
                macd_signal=macd_signal,
                bb_position=bb_position,
                trend=trend,
                trend_strength=trend_strength,
                support=support,
                resistance=resistance,
                confluence_score=confluence,
                signal=signal,
            )

            self._cache[symbol] = signals

            # Publish to HA
            await self._publish_to_ha(symbol, signals)

            return signals

        except Exception as e:
            logger.error(f"TA calculation failed for {symbol}: {e}")
            return None

    def _calculate_rsi(self, closes: list[float], period: int = 14) -> float | None:
        """Calculate RSI."""
        if len(closes) < period + 1:
            return None

        changes = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
        gains = [max(0, c) for c in changes[-period:]]
        losses = [abs(min(0, c)) for c in changes[-period:]]

        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return round(rsi, 1)

    def _get_macd_signal(self, closes: list[float]) -> str:
        """Get MACD signal direction."""
        if len(closes) < 35:
            return "Neutral"

        # Calculate EMAs
        ema_12 = self._ema(closes, 12)
        ema_26 = self._ema(closes, 26)

        if ema_12 is None or ema_26 is None:
            return "Neutral"

        macd = ema_12 - ema_26

        # Calculate signal line (9-period EMA of MACD)
        macd_values = []
        for i in range(26, len(closes)):
            e12 = self._ema(closes[: i + 1], 12)
            e26 = self._ema(closes[: i + 1], 26)
            if e12 and e26:
                macd_values.append(e12 - e26)

        if len(macd_values) < 9:
            return "Neutral"

        signal_line = self._ema(macd_values, 9)
        if signal_line is None:
            return "Neutral"

        histogram = macd - signal_line

        # Simple signal based on histogram
        if histogram > 0 and macd > 0:
            return "Bullish"
        elif histogram < 0 and macd < 0:
            return "Bearish"
        else:
            return "Neutral"

    def _ema(self, prices: list[float], period: int) -> float | None:
        """Calculate EMA."""
        if len(prices) < period:
            return None

        multiplier = 2 / (period + 1)
        ema = prices[0]

        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))

        return ema

    def _calculate_bb_position(self, closes: list[float], period: int = 20) -> float | None:
        """Calculate position within Bollinger Bands (0-100)."""
        if len(closes) < period:
            return None

        sma = sum(closes[-period:]) / period
        variance = sum((p - sma) ** 2 for p in closes[-period:]) / period
        std = variance**0.5

        upper = sma + 2 * std
        lower = sma - 2 * std

        current = closes[-1]

        if upper == lower:
            return 50.0

        # Position as percentage (0 = at lower, 100 = at upper)
        position = ((current - lower) / (upper - lower)) * 100
        return round(max(0, min(100, position)), 1)

    def _detect_trend(self, closes: list[float]) -> tuple[str, float]:
        """
        Detect trend direction and strength.

        Returns:
            (trend_direction, trend_strength)
        """
        if len(closes) < 50:
            return "sideways", 0.0

        # Use SMA crossover for trend
        sma_20 = sum(closes[-20:]) / 20
        sma_50 = sum(closes[-50:]) / 50

        current = closes[-1]
        prev_20 = sum(closes[-40:-20]) / 20 if len(closes) >= 40 else sma_20

        # Calculate price momentum
        price_change = (current - closes[-20]) / closes[-20] * 100 if closes[-20] != 0 else 0

        # Determine trend
        if current > sma_20 > sma_50 and sma_20 > prev_20:
            trend = "uptrend"
            strength = min(100, abs(price_change) * 5)
        elif current < sma_20 < sma_50 and sma_20 < prev_20:
            trend = "downtrend"
            strength = min(100, abs(price_change) * 5)
        else:
            trend = "sideways"
            strength = 0.0

        return trend, round(strength, 1)

    def _find_levels(
        self,
        closes: list[float],
        highs: list[float],
        lows: list[float],
    ) -> tuple[float | None, float | None]:
        """Find support and resistance levels."""
        if len(closes) < 50:
            return None, None

        current = closes[-1]

        # Simple approach: recent swing highs/lows
        recent_highs = highs[-50:]
        recent_lows = lows[-50:]

        # Find resistance (nearest high above current price)
        resistance_candidates = [h for h in recent_highs if h > current]
        resistance = min(resistance_candidates) if resistance_candidates else None

        # Find support (nearest low below current price)
        support_candidates = [l for l in recent_lows if l < current]
        support = max(support_candidates) if support_candidates else None

        return support, resistance

    def _calculate_confluence(
        self,
        rsi: float | None,
        macd_signal: str,
        bb_position: float | None,
        trend: str,
    ) -> int:
        """Calculate TA confluence score (0-100)."""
        score = 50  # Start neutral

        # RSI contribution (-20 to +20)
        if rsi is not None:
            if rsi < 30:
                score += 15  # Oversold = bullish
            elif rsi < 40:
                score += 8
            elif rsi > 70:
                score -= 15  # Overbought = bearish
            elif rsi > 60:
                score -= 8

        # MACD contribution (-15 to +15)
        if macd_signal == "Bullish":
            score += 15
        elif macd_signal == "Bearish":
            score -= 15

        # BB contribution (-10 to +10)
        if bb_position is not None:
            if bb_position < 20:
                score += 10  # Near lower band = bullish
            elif bb_position > 80:
                score -= 10  # Near upper band = bearish

        # Trend contribution (-15 to +15)
        if trend == "uptrend":
            score += 15
        elif trend == "downtrend":
            score -= 15

        return max(0, min(100, score))

    def _get_signal(self, confluence: int) -> str:
        """Convert confluence score to signal."""
        if confluence >= 75:
            return "Strong Buy"
        elif confluence >= 60:
            return "Buy"
        elif confluence <= 25:
            return "Strong Sell"
        elif confluence <= 40:
            return "Sell"
        else:
            return "Neutral"

    async def _publish_to_ha(self, symbol: str, signals: TASignals) -> None:
        """Publish TA data to Home Assistant sensors (via Supervisor API)."""
        # Extract currency code (e.g., "BTC/USDT" -> "BTC")
        currency = symbol.replace("/USDT", "").replace("USDT", "")

        # Update aggregated data for SensorManager
        if signals.rsi is not None:
            self._rsi_values[currency] = signals.rsi
        if signals.macd_signal:
            self._macd_signals[currency] = signals.macd_signal
        if signals.bb_position is not None:
            self._bb_positions[currency] = signals.bb_position
        if signals.trend:
            self._trends[currency] = signals.trend
        if signals.support is not None:
            self._supports[currency] = signals.support
        if signals.resistance is not None:
            self._resistances[currency] = signals.resistance

    def get_cached_signals(self, symbol: str) -> TASignals | None:
        """Get cached signals for a symbol."""
        return self._cache.get(symbol)

    def get_all_signals(self) -> dict[str, dict]:
        """Get all cached signals."""
        return {symbol: signals.to_dict() for symbol, signals in self._cache.items()}

    async def publish_multi_timeframe(
        self,
        symbol: str,
        candles_1h: list[dict] | None = None,
        candles_4h: list[dict] | None = None,
        candles_1d: list[dict] | None = None,
    ) -> None:
        """
        Calculate and publish multi-timeframe trends using generic dictionary format.

        Args:
            symbol: Trading pair
            candles_1h: 1-hour candles
            candles_4h: 4-hour candles
            candles_1d: Daily candles
        """
        currency = symbol.replace("/USDT", "").replace("USDT", "")

        if currency not in self._mtf_trends:
            self._mtf_trends[currency] = {}

        if candles_1h and len(candles_1h) >= 50:
            closes = [float(c.get("close", 0)) for c in candles_1h]
            trend, _ = self._detect_trend(closes)
            self._mtf_trends[currency]["1h"] = trend

        if candles_4h and len(candles_4h) >= 50:
            closes = [float(c.get("close", 0)) for c in candles_4h]
            trend, _ = self._detect_trend(closes)
            self._mtf_trends[currency]["4h"] = trend

        if candles_1d and len(candles_1d) >= 50:
            closes = [float(c.get("close", 0)) for c in candles_1d]
            trend, _ = self._detect_trend(closes)
            self._mtf_trends[currency]["1d"] = trend

        # Publish aggregated MTF trends
        await self._publish_dict_sensor("ta_trend_mtf", self._mtf_trends)
