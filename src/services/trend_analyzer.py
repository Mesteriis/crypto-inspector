"""
AI Trend Analyzer - Advanced market trend prediction using machine learning.

This service combines multiple ML models, technical indicators, and sentiment analysis
to provide comprehensive trend predictions with confidence scoring.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import numpy as np
from scipy import stats

from core.constants import DEFAULT_SYMBOLS
from services.candlestick import CandleInterval, fetch_candlesticks
from services.ml.forecaster import PriceForecaster
from services.ml.models import ForecastResult
from services.technical import TechnicalAnalyzer

logger = logging.getLogger(__name__)


class TrendDirection(Enum):
    """Trend direction enumeration."""

    STRONGLY_BULLISH = "strongly_bullish"
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"
    STRONGLY_BEARISH = "strongly_bearish"


class TrendConfidence(Enum):
    """Trend confidence levels."""

    VERY_HIGH = "very_high"  # 90-100%
    HIGH = "high"  # 75-90%
    MODERATE = "moderate"  # 60-75%
    LOW = "low"  # 40-60%
    VERY_LOW = "very_low"  # 0-40%


@dataclass
class TrendAnalysis:
    """Comprehensive trend analysis result."""

    symbol: str
    interval: str
    timestamp: datetime

    # Primary trend assessment
    direction: TrendDirection
    confidence: float  # 0-100%
    confidence_level: TrendConfidence

    # Price predictions
    current_price: float
    predicted_price_24h: float
    predicted_price_7d: float
    price_change_24h_pct: float
    price_change_7d_pct: float

    # Technical indicators consensus
    technical_score: float  # -100 to +100
    technical_signals: dict[str, Any]

    # ML model ensemble results
    ml_predictions: list[ForecastResult]
    ml_consensus: str
    ml_confidence: float

    # Market context
    volatility: float  # Standard deviation of returns
    volume_trend: str  # increasing/decreasing/stable
    market_phase: str  # accumulation/distribution/manipulation/consolidation

    # Risk factors
    risk_level: str  # low/medium/high/extreme
    risk_factors: list[str]
    support_levels: list[float]
    resistance_levels: list[float]

    # Sentiment indicators (future expansion)
    sentiment_score: float | None = None
    news_sentiment: str | None = None

    # Metadata
    analysis_period: str = "24h"
    data_points_used: int = 0
    models_used: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "symbol": self.symbol,
            "interval": self.interval,
            "timestamp": self.timestamp.isoformat(),
            "direction": self.direction.value,
            "confidence": round(self.confidence, 1),
            "confidence_level": self.confidence_level.value,
            "current_price": round(self.current_price, 2),
            "predicted_price_24h": round(self.predicted_price_24h, 2),
            "predicted_price_7d": round(self.predicted_price_7d, 2),
            "price_change_24h_pct": round(self.price_change_24h_pct, 2),
            "price_change_7d_pct": round(self.price_change_7d_pct, 2),
            "technical_score": round(self.technical_score, 1),
            "technical_signals": self.technical_signals,
            "ml_consensus": self.ml_consensus,
            "ml_confidence": round(self.ml_confidence, 1),
            "volatility": round(self.volatility, 4),
            "volume_trend": self.volume_trend,
            "market_phase": self.market_phase,
            "risk_level": self.risk_level,
            "risk_factors": self.risk_factors,
            "support_levels": [round(level, 2) for level in self.support_levels[:3]],
            "resistance_levels": [round(level, 2) for level in self.resistance_levels[:3]],
            "sentiment_score": round(self.sentiment_score, 2) if self.sentiment_score else None,
            "news_sentiment": self.news_sentiment,
            "analysis_period": self.analysis_period,
            "data_points_used": self.data_points_used,
            "models_used": self.models_used,
        }


class AITrendAnalyzer:
    """Advanced AI-powered trend analyzer combining ML and technical analysis."""

    def __init__(self):
        """Initialize trend analyzer."""
        self.forecaster = PriceForecaster()
        self.tech_analyzer = TechnicalAnalyzer()
        self._cache: dict[str, TrendAnalysis] = {}

    async def analyze_trend(
        self, symbol: str, interval: str = "1h", lookback_days: int = 30, force_refresh: bool = False
    ) -> TrendAnalysis:
        """
        Perform comprehensive trend analysis for a symbol.

        Args:
            symbol: Trading pair symbol
            interval: Candlestick interval
            lookback_days: Historical data period to analyze
            force_refresh: Skip cache and force new analysis

        Returns:
            TrendAnalysis with comprehensive market assessment
        """
        cache_key = f"{symbol}_{interval}_{lookback_days}"

        # Check cache
        if not force_refresh and cache_key in self._cache:
            cached_analysis = self._cache[cache_key]
            # Refresh if older than 15 minutes
            if datetime.now() - cached_analysis.timestamp < timedelta(minutes=15):
                return cached_analysis

        logger.info(f"Analyzing trend for {symbol} {interval}")

        try:
            # Fetch historical data
            candles = await fetch_candlesticks(
                symbol=symbol,
                interval=CandleInterval(interval),
                limit=min(lookback_days * 24, 1000),  # Cap at 1000 candles
            )

            if len(candles) < 50:
                raise ValueError(f"Insufficient data for {symbol}: {len(candles)} candles")

            # Extract price data
            prices = [float(c.close) for c in candles]
            volumes = [float(c.volume) for c in candles]
            timestamps = [c.timestamp for c in candles]

            # Perform analyses
            tech_analysis = await self._analyze_technical_indicators(prices, volumes)
            ml_analysis = await self._analyze_ml_predictions(symbol, interval, prices)
            market_context = self._analyze_market_context(prices, volumes, timestamps)
            risk_assessment = self._assess_risk_factors(prices, tech_analysis, market_context)

            # Combine all signals for final trend assessment
            final_trend = self._synthesize_trend_analysis(
                symbol=symbol,
                interval=interval,
                current_price=prices[-1],
                tech_analysis=tech_analysis,
                ml_analysis=ml_analysis,
                market_context=market_context,
                risk_assessment=risk_assessment,
            )

            # Cache result
            self._cache[cache_key] = final_trend

            logger.info(
                f"Trend analysis complete for {symbol}: "
                f"{final_trend.direction.value} ({final_trend.confidence:.1f}% confidence)"
            )

            return final_trend

        except Exception as e:
            logger.error(f"Failed to analyze trend for {symbol}: {e}")
            raise

    async def _analyze_technical_indicators(self, prices: list[float], volumes: list[float]) -> dict[str, Any]:
        """Analyze technical indicators for trend signals."""
        try:
            # Calculate various technical indicators
            analysis = await self.tech_analyzer.analyze(prices, volumes)

            # Extract key signals
            signals = {
                "rsi": analysis.get("rsi", {}).get("value", 50),
                "rsi_signal": analysis.get("rsi", {}).get("signal", "neutral"),
                "macd_histogram": analysis.get("macd", {}).get("histogram", 0),
                "macd_signal": analysis.get("macd", {}).get("signal", "neutral"),
                "ema_20_50": analysis.get("moving_averages", {}).get("ema_cross", "neutral"),
                "bollinger_position": analysis.get("bollinger_bands", {}).get("price_position", 0.5),
                "support_resistance": analysis.get("support_resistance", {}),
                "volume_trend": analysis.get("volume_profile", {}).get("trend", "stable"),
            }

            # Calculate technical score (-100 to +100)
            score = self._calculate_technical_score(signals)
            signals["overall_score"] = score

            return signals

        except Exception as e:
            logger.warning(f"Technical analysis failed: {e}")
            return {"overall_score": 0, "error": str(e)}

    async def _analyze_ml_predictions(self, symbol: str, interval: str, prices: list[float]) -> dict[str, Any]:
        """Generate ML predictions for different time horizons."""
        try:
            # Get predictions for 24h and 7d horizons
            predictions_24h = await self.forecaster.predict(
                symbol=symbol, interval=interval, prices=prices, horizon=24 if interval == "1h" else 1
            )

            predictions_7d = await self.forecaster.predict(
                symbol=symbol, interval=interval, prices=prices, horizon=168 if interval == "1h" else 7
            )

            # Calculate consensus direction
            directions = [pred.direction for pred in [predictions_24h, predictions_7d]]
            bullish_count = directions.count("up")
            bearish_count = directions.count("down")

            if bullish_count > bearish_count:
                consensus = "bullish"
            elif bearish_count > bullish_count:
                consensus = "bearish"
            else:
                consensus = "neutral"

            # Average confidence
            avg_confidence = np.mean([pred.confidence_pct for pred in [predictions_24h, predictions_7d]])

            return {
                "predictions": [predictions_24h, predictions_7d],
                "consensus": consensus,
                "average_confidence": avg_confidence,
                "models_used": self.forecaster.get_available_models(),
            }

        except Exception as e:
            logger.warning(f"ML analysis failed: {e}")
            return {
                "predictions": [],
                "consensus": "neutral",
                "average_confidence": 0,
                "models_used": [],
                "error": str(e),
            }

    def _analyze_market_context(
        self, prices: list[float], volumes: list[float], timestamps: list[datetime]
    ) -> dict[str, Any]:
        """Analyze broader market context and conditions."""
        try:
            # Calculate returns
            returns = [((prices[i] - prices[i - 1]) / prices[i - 1]) * 100 for i in range(1, len(prices))]

            # Volatility (standard deviation of returns)
            volatility = np.std(returns) if len(returns) > 1 else 0

            # Volume trend analysis
            recent_volumes = volumes[-20:] if len(volumes) >= 20 else volumes
            volume_trend = self._analyze_volume_trend(recent_volumes)

            # Market phase detection
            market_phase = self._detect_market_phase(prices, volumes, returns)

            # Support/Resistance levels
            support_levels, resistance_levels = self._find_key_levels(prices)

            return {
                "volatility": volatility,
                "volume_trend": volume_trend,
                "market_phase": market_phase,
                "support_levels": support_levels,
                "resistance_levels": resistance_levels,
                "price_returns": returns[-1] if returns else 0,
            }

        except Exception as e:
            logger.warning(f"Market context analysis failed: {e}")
            return {
                "volatility": 0,
                "volume_trend": "stable",
                "market_phase": "unknown",
                "support_levels": [],
                "resistance_levels": [],
                "price_returns": 0,
                "error": str(e),
            }

    def _assess_risk_factors(
        self, prices: list[float], tech_analysis: dict[str, Any], market_context: dict[str, Any]
    ) -> dict[str, Any]:
        """Assess various risk factors."""
        risk_factors = []
        risk_score = 0

        # High volatility risk
        if market_context.get("volatility", 0) > 5:
            risk_factors.append("high_volatility")
            risk_score += 30

        # Overbought/Oversold conditions
        rsi = tech_analysis.get("rsi", 50)
        if rsi > 70:
            risk_factors.append("overbought")
            risk_score += 20
        elif rsi < 30:
            risk_factors.append("oversold")
            risk_score += 20

        # Volume divergence
        price_returns = market_context.get("price_returns", 0)
        if market_context.get("volume_trend") == "decreasing" and price_returns > 0:
            risk_factors.append("volume_divergence")
            risk_score += 25

        # Extreme price movements
        recent_returns = market_context.get("price_returns", 0)
        if abs(recent_returns) > 10:
            risk_factors.append("extreme_movement")
            risk_score += 35

        # Determine risk level
        if risk_score >= 70:
            risk_level = "extreme"
        elif risk_score >= 50:
            risk_level = "high"
        elif risk_score >= 30:
            risk_level = "medium"
        else:
            risk_level = "low"

        return {"risk_level": risk_level, "risk_score": risk_score, "risk_factors": risk_factors}

    def _synthesize_trend_analysis(
        self,
        symbol: str,
        interval: str,
        current_price: float,
        tech_analysis: dict[str, Any],
        ml_analysis: dict[str, Any],
        market_context: dict[str, Any],
        risk_assessment: dict[str, Any],
    ) -> TrendAnalysis:
        """Combine all analysis components into final trend assessment."""

        # Calculate weighted confidence score
        tech_confidence = self._normalize_score(tech_analysis.get("overall_score", 0), -100, 100)
        ml_confidence = ml_analysis.get("average_confidence", 50)
        risk_penalty = risk_assessment.get("risk_score", 0) * 0.5  # 50% penalty for high risk

        # Combined confidence (0-100)
        combined_confidence = (tech_confidence * 0.4 + ml_confidence * 0.6) - risk_penalty
        combined_confidence = max(0, min(100, combined_confidence))

        # Determine trend direction
        tech_score = tech_analysis.get("overall_score", 0)
        ml_consensus = ml_analysis.get("consensus", "neutral")

        # Weight technical analysis more heavily for direction
        if tech_score > 30 and ml_consensus in ["bullish", "up"]:
            direction = TrendDirection.BULLISH
        elif tech_score > 70 and ml_consensus == "bullish":
            direction = TrendDirection.STRONGLY_BULLISH
        elif tech_score < -30 and ml_consensus in ["bearish", "down"]:
            direction = TrendDirection.BEARISH
        elif tech_score < -70 and ml_consensus == "bearish":
            direction = TrendDirection.STRONGLY_BEARISH
        else:
            direction = TrendDirection.NEUTRAL

        # Map confidence to levels
        if combined_confidence >= 90:
            confidence_level = TrendConfidence.VERY_HIGH
        elif combined_confidence >= 75:
            confidence_level = TrendConfidence.HIGH
        elif combined_confidence >= 60:
            confidence_level = TrendConfidence.MODERATE
        elif combined_confidence >= 40:
            confidence_level = TrendConfidence.LOW
        else:
            confidence_level = TrendConfidence.VERY_LOW

        # Extract predictions
        predictions = ml_analysis.get("predictions", [])
        pred_24h = predictions[0] if len(predictions) > 0 else None
        pred_7d = predictions[1] if len(predictions) > 1 else None

        predicted_24h = pred_24h.predictions[-1] if pred_24h else current_price
        predicted_7d = pred_7d.predictions[-1] if pred_7d else current_price

        change_24h_pct = ((predicted_24h - current_price) / current_price) * 100
        change_7d_pct = ((predicted_7d - current_price) / current_price) * 100

        return TrendAnalysis(
            symbol=symbol,
            interval=interval,
            timestamp=datetime.now(),
            direction=direction,
            confidence=combined_confidence,
            confidence_level=confidence_level,
            current_price=current_price,
            predicted_price_24h=predicted_24h,
            predicted_price_7d=predicted_7d,
            price_change_24h_pct=change_24h_pct,
            price_change_7d_pct=change_7d_pct,
            technical_score=tech_score,
            technical_signals=tech_analysis,
            ml_predictions=predictions,
            ml_consensus=ml_consensus,
            ml_confidence=ml_confidence,
            volatility=market_context.get("volatility", 0),
            volume_trend=market_context.get("volume_trend", "stable"),
            market_phase=market_context.get("market_phase", "unknown"),
            risk_level=risk_assessment.get("risk_level", "low"),
            risk_factors=risk_assessment.get("risk_factors", []),
            support_levels=market_context.get("support_levels", []),
            resistance_levels=market_context.get("resistance_levels", []),
            data_points_used=len(tech_analysis.get("price_data", [])),
            models_used=ml_analysis.get("models_used", []),
        )

    def _calculate_technical_score(self, signals: dict[str, Any]) -> float:
        """Calculate composite technical score from various indicators."""
        score = 0

        # RSI contribution (-30 to +30)
        rsi = signals.get("rsi", 50)
        if rsi > 70:
            score -= 30  # Overbought
        elif rsi < 30:
            score += 30  # Oversold
        else:
            score += (50 - abs(rsi - 50)) * 0.6  # Neutral zone

        # MACD contribution (-20 to +20)
        macd_hist = signals.get("macd_histogram", 0)
        if macd_hist > 0:
            score += min(20, macd_hist * 100)  # Bullish momentum
        else:
            score += max(-20, macd_hist * 100)  # Bearish momentum

        # Moving average cross (-20 to +20)
        ema_signal = signals.get("ema_20_50", "neutral")
        if ema_signal == "bullish":
            score += 20
        elif ema_signal == "bearish":
            score -= 20

        # Bollinger Bands position (-15 to +15)
        bb_position = signals.get("bollinger_position", 0.5)
        if bb_position > 0.8:
            score -= 15  # Near upper band
        elif bb_position < 0.2:
            score += 15  # Near lower band

        # Volume trend (-15 to +15)
        vol_trend = signals.get("volume_trend", "stable")
        if vol_trend == "increasing":
            score *= 1.2  # Boost score with strong volume
        elif vol_trend == "decreasing":
            score *= 0.8  # Reduce score with weak volume

        return max(-100, min(100, score))

    def _analyze_volume_trend(self, volumes: list[float]) -> str:
        """Analyze volume trend direction."""
        if len(volumes) < 5:
            return "stable"

        # Simple linear regression slope
        x = np.arange(len(volumes))
        slope, _, _, _, _ = stats.linregress(x, volumes)

        if slope > 0.1:
            return "increasing"
        elif slope < -0.1:
            return "decreasing"
        else:
            return "stable"

    def _detect_market_phase(self, prices: list[float], volumes: list[float], returns: list[float]) -> str:
        """Detect current market phase."""
        if len(prices) < 20:
            return "unknown"

        # Calculate volatility and volume ratios
        recent_volatility = np.std(returns[-10:]) if len(returns) >= 10 else 0
        overall_volatility = np.std(returns) if len(returns) > 1 else 0

        recent_volume = np.mean(volumes[-10:]) if len(volumes) >= 10 else 0
        overall_volume = np.mean(volumes) if volumes else 0

        vol_ratio = recent_volatility / overall_volatility if overall_volatility > 0 else 1
        volume_ratio = recent_volume / overall_volume if overall_volume > 0 else 1

        # Phase determination logic
        if vol_ratio > 1.5 and volume_ratio > 1.2:
            return "accumulation"  # High volatility, high volume - buying pressure
        elif vol_ratio > 1.5 and volume_ratio < 0.8:
            return "distribution"  # High volatility, low volume - selling pressure
        elif vol_ratio < 0.7:
            return "consolidation"  # Low volatility - sideways movement
        else:
            return "manipulation"  # Unusual activity

    def _find_key_levels(self, prices: list[float]) -> tuple[list[float], list[float]]:
        """Find support and resistance levels using swing highs/lows."""
        if len(prices) < 20:
            return [], []

        support_levels = []
        resistance_levels = []

        # Simple approach: find local minima/maxima
        for i in range(5, len(prices) - 5):
            # Check for local minimum (support)
            if prices[i] <= min(prices[i - 5 : i]) and prices[i] <= min(prices[i + 1 : i + 6]):
                support_levels.append(prices[i])

            # Check for local maximum (resistance)
            if prices[i] >= max(prices[i - 5 : i]) and prices[i] >= max(prices[i + 1 : i + 6]):
                resistance_levels.append(prices[i])

        # Sort and return top 5 levels
        support_levels = sorted(set(support_levels))[-5:] if support_levels else []
        resistance_levels = sorted(set(resistance_levels))[:5] if resistance_levels else []

        return support_levels, resistance_levels

    def _normalize_score(self, score: float, min_val: float, max_val: float) -> float:
        """Normalize score to 0-100 range."""
        if max_val == min_val:
            return 50
        normalized = ((score - min_val) / (max_val - min_val)) * 100
        return max(0, min(100, normalized))

    async def get_multiple_trends(self, symbols: list[str] = None, interval: str = "1h") -> dict[str, TrendAnalysis]:
        """Get trend analysis for multiple symbols concurrently."""
        if symbols is None:
            symbols = DEFAULT_SYMBOLS

        tasks = [self.analyze_trend(symbol, interval) for symbol in symbols]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        trend_dict = {}
        for symbol, result in zip(symbols, results):
            if isinstance(result, TrendAnalysis):
                trend_dict[symbol] = result
            elif isinstance(result, Exception):
                logger.error(f"Failed to analyze {symbol}: {result}")

        return trend_dict

    def clear_cache(self) -> None:
        """Clear analysis cache."""
        self._cache.clear()
        logger.info("Trend analysis cache cleared")


# Global instance
_trend_analyzer: AITrendAnalyzer | None = None


def get_trend_analyzer() -> AITrendAnalyzer:
    """Get or create global trend analyzer instance."""
    global _trend_analyzer
    if _trend_analyzer is None:
        _trend_analyzer = AITrendAnalyzer()
    return _trend_analyzer
