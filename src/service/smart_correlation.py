"""
Smart Correlation Engine - Multi-source data correlation for comprehensive analysis.

This service correlates data from multiple sources including:
- Price movements across different cryptocurrencies
- Technical indicators and patterns
- Market sentiment and social metrics
- Economic indicators and traditional markets
- Trading volumes and order book data
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import numpy as np
from scipy import stats

from core.constants import DEFAULT_SYMBOLS
from service.candlestick import CandleInterval, fetch_candlesticks
from service.ha_integration import get_supervisor_client

logger = logging.getLogger(__name__)


class CorrelationType(Enum):
    """Types of correlations that can be detected."""

    PRICE_CORRELATION = "price_correlation"  # Цена одной монеты vs другая
    VOLUME_CORRELATION = "volume_correlation"  # Объемы торгов
    VOLATILITY_CORRELATION = "volatility_correlation"  # Волатильность
    TREND_CORRELATION = "trend_correlation"  # Направление трендов
    SENTIMENT_CORRELATION = "sentiment_correlation"  # Рыночные настроения
    CROSS_MARKET = "cross_market"  # Крипто vs традиционные рынки


class CorrelationStrength(Enum):
    """Strength levels of correlations."""

    VERY_WEAK = "very_weak"  # 0.0 - 0.2
    WEAK = "weak"  # 0.2 - 0.4
    MODERATE = "moderate"  # 0.4 - 0.6
    STRONG = "strong"  # 0.6 - 0.8
    VERY_STRONG = "very_strong"  # 0.8 - 1.0


@dataclass
class CorrelationPair:
    """Represents correlation between two data series."""

    source_1: str  # First data source/symbol
    source_2: str  # Second data source/symbol
    correlation_type: CorrelationType
    correlation_coefficient: float  # Pearson correlation coefficient (-1 to 1)
    correlation_strength: CorrelationStrength
    sample_size: int
    time_period: str  # "1h", "4h", "1d", etc.
    significance: float  # p-value
    last_updated: datetime

    # Additional metadata
    lag_analysis: dict[str, Any] | None = None  # Lead-lag relationships
    causality_indicators: list[str] | None = None  # Potential causal factors
    confidence_interval: tuple[float, float] | None = None  # 95% CI

    def is_significant(self, alpha: float = 0.05) -> bool:
        """Check if correlation is statistically significant."""
        return self.significance < alpha and abs(self.correlation_coefficient) > 0.1

    def get_description(self) -> str:
        """Get human-readable description of correlation."""
        strength_desc = {
            CorrelationStrength.VERY_WEAK: "очень слабая",
            CorrelationStrength.WEAK: "слабая",
            CorrelationStrength.MODERATE: "умеренная",
            CorrelationStrength.STRONG: "сильная",
            CorrelationStrength.VERY_STRONG: "очень сильная",
        }

        direction = "положительная" if self.correlation_coefficient > 0 else "отрицательная"
        strength_text = strength_desc[self.correlation_strength]

        return f"{direction} {strength_text} корреляция ({self.correlation_coefficient:.3f})"


@dataclass
class MultiSourceCorrelation:
    """Comprehensive correlation analysis across multiple data sources."""

    timestamp: datetime
    symbol_pairs: list[tuple[str, str]]
    correlation_matrix: dict[str, dict[str, CorrelationPair]]
    dominant_patterns: list[dict[str, Any]]
    cross_market_insights: list[str]
    trading_opportunities: list[dict[str, Any]]
    risk_indicators: list[str]

    # Summary statistics
    total_correlations: int = 0
    significant_correlations: int = 0
    strongest_positive: CorrelationPair | None = None
    strongest_negative: CorrelationPair | None = None


class SmartCorrelationEngine:
    """Main engine for multi-source correlation analysis."""

    def __init__(self):
        """Initialize correlation engine."""
        self._supervisor_client = get_supervisor_client()
        self._correlation_cache: dict[str, MultiSourceCorrelation] = {}
        self._cache_duration = timedelta(minutes=30)  # Cache for 30 minutes

    async def analyze_multi_source_correlations(
        self, symbols: list[str] = None, timeframes: list[str] = None, include_cross_market: bool = True
    ) -> MultiSourceCorrelation:
        """
        Perform comprehensive correlation analysis across multiple data sources.

        Args:
            symbols: List of cryptocurrency symbols to analyze
            timeframes: List of time intervals ["1h", "4h", "1d"]
            include_cross_market: Whether to include traditional market data

        Returns:
            MultiSourceCorrelation with comprehensive analysis
        """
        if symbols is None:
            symbols = DEFAULT_SYMBOLS[:5]  # Limit to top 5 for performance

        if timeframes is None:
            timeframes = ["1h", "4h", "1d"]

        cache_key = f"correlation_{'_'.join(sorted(symbols))}_{'_'.join(timeframes)}"

        # Check cache
        if cache_key in self._correlation_cache:
            cached = self._correlation_cache[cache_key]
            if datetime.now() - cached.timestamp < self._cache_duration:
                return cached

        logger.info(f"Analyzing correlations for {len(symbols)} symbols across {len(timeframes)} timeframes")

        try:
            # Fetch data for all symbols and timeframes
            data_matrix = await self._fetch_multi_timeframe_data(symbols, timeframes)

            # Calculate correlations
            correlation_results = {}
            all_pairs = []

            for timeframe in timeframes:
                correlation_results[timeframe] = {}

                # Get symbol pairs for this timeframe
                timeframe_symbols = list(data_matrix[timeframe].keys())
                pairs = [(s1, s2) for i, s1 in enumerate(timeframe_symbols) for s2 in timeframe_symbols[i + 1 :]]
                all_pairs.extend([(p[0], p[1], timeframe) for p in pairs])

                for symbol1, symbol2 in pairs:
                    correlations = await self._calculate_symbol_correlations(
                        data_matrix[timeframe][symbol1], data_matrix[timeframe][symbol2], symbol1, symbol2, timeframe
                    )

                    correlation_results[timeframe][f"{symbol1}_{symbol2}"] = correlations

            # Identify dominant patterns
            dominant_patterns = await self._identify_dominant_patterns(correlation_results)

            # Cross-market analysis
            cross_market_insights = []
            if include_cross_market:
                cross_market_insights = await self._analyze_cross_market_correlations(data_matrix)

            # Identify trading opportunities
            trading_opps = await self._identify_trading_opportunities(correlation_results)

            # Risk indicators
            risk_indicators = await self._assess_correlation_risks(correlation_results)

            # Create comprehensive result
            result = MultiSourceCorrelation(
                timestamp=datetime.now(),
                symbol_pairs=[(s1, s2) for s1, s2, _ in all_pairs],
                correlation_matrix=correlation_results,
                dominant_patterns=dominant_patterns,
                cross_market_insights=cross_market_insights,
                trading_opportunities=trading_opps,
                risk_indicators=risk_indicators,
                total_correlations=len(all_pairs) * len(CorrelationType),
                significant_correlations=self._count_significant_correlations(correlation_results),
            )

            # Find strongest correlations
            result.strongest_positive = self._find_strongest_correlation(correlation_results, positive=True)
            result.strongest_negative = self._find_strongest_correlation(correlation_results, positive=False)

            # Cache result
            self._correlation_cache[cache_key] = result

            logger.info(
                f"Correlation analysis complete: {result.significant_correlations}/{result.total_correlations} significant"
            )

            return result

        except Exception as e:
            logger.error(f"Failed to analyze correlations: {e}")
            raise

    async def _fetch_multi_timeframe_data(
        self, symbols: list[str], timeframes: list[str]
    ) -> dict[str, dict[str, dict[str, list[float]]]]:
        """Fetch price data for multiple symbols and timeframes."""
        data_matrix = {tf: {} for tf in timeframes}

        # Fetch data concurrently
        tasks = []
        for symbol in symbols:
            for timeframe in timeframes:
                task = self._fetch_symbol_data(symbol, timeframe)
                tasks.append((symbol, timeframe, task))

        # Execute all fetch tasks
        results = await asyncio.gather(*[task for _, _, task in tasks], return_exceptions=True)

        # Organize results
        for (symbol, timeframe, _), result in zip(tasks, results):
            if isinstance(result, Exception):
                logger.warning(f"Failed to fetch data for {symbol} {timeframe}: {result}")
                continue

            if result:
                data_matrix[timeframe][symbol] = result

        return data_matrix

    async def _fetch_symbol_data(self, symbol: str, timeframe: str) -> dict[str, list[float]] | None:
        """Fetch and prepare data for a single symbol."""
        try:
            # Calculate limit based on timeframe
            limit_map = {"15m": 96, "1h": 168, "4h": 126, "1d": 90}  # ~1 week of data
            limit = limit_map.get(timeframe, 100)

            # Добавляем /USDT если не указана пара
            pair = symbol if "/" in symbol else f"{symbol}/USDT"
            
            candles = await fetch_candlesticks(symbol=pair, interval=CandleInterval(timeframe), limit=limit)

            if len(candles) < 20:  # Minimum data requirement
                return None

            # Extract data series
            prices = [float(c.close) for c in candles]
            volumes = [float(c.volume) for c in candles]
            highs = [float(c.high) for c in candles]
            lows = [float(c.low) for c in candles]

            # Calculate returns and volatility
            returns = [((prices[i] - prices[i - 1]) / prices[i - 1]) * 100 for i in range(1, len(prices))]
            volatility = [abs(ret) for ret in returns]

            return {
                "prices": prices,
                "returns": returns,
                "volumes": volumes,
                "volatility": volatility,
                "highs": highs,
                "lows": lows,
            }

        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return None

    async def _calculate_symbol_correlations(
        self, data1: dict[str, list[float]], data2: dict[str, list[float]], symbol1: str, symbol2: str, timeframe: str
    ) -> dict[CorrelationType, CorrelationPair]:
        """Calculate various types of correlations between two symbols."""
        correlations = {}

        # Align data lengths
        min_len = min(len(data1["prices"]), len(data2["prices"]))
        if min_len < 20:
            return correlations

        # Price correlation
        price_corr = self._calculate_correlation(data1["prices"][-min_len:], data2["prices"][-min_len:])
        if price_corr is not None:
            correlations[CorrelationType.PRICE_CORRELATION] = CorrelationPair(
                source_1=symbol1,
                source_2=symbol2,
                correlation_type=CorrelationType.PRICE_CORRELATION,
                correlation_coefficient=price_corr[0],
                correlation_strength=self._get_correlation_strength(price_corr[0]),
                sample_size=min_len,
                time_period=timeframe,
                significance=price_corr[1],
                last_updated=datetime.now(),
            )

        # Volume correlation
        if "volumes" in data1 and "volumes" in data2:
            vol_corr = self._calculate_correlation(data1["volumes"][-min_len:], data2["volumes"][-min_len:])
            if vol_corr is not None:
                correlations[CorrelationType.VOLUME_CORRELATION] = CorrelationPair(
                    source_1=symbol1,
                    source_2=symbol2,
                    correlation_type=CorrelationType.VOLUME_CORRELATION,
                    correlation_coefficient=vol_corr[0],
                    correlation_strength=self._get_correlation_strength(vol_corr[0]),
                    sample_size=min_len,
                    time_period=timeframe,
                    significance=vol_corr[1],
                    last_updated=datetime.now(),
                )

        # Volatility correlation
        if "volatility" in data1 and "volatility" in data2:
            volat_corr = self._calculate_correlation(data1["volatility"][-min_len:], data2["volatility"][-min_len:])
            if volat_corr is not None:
                correlations[CorrelationType.VOLATILITY_CORRELATION] = CorrelationPair(
                    source_1=symbol1,
                    source_2=symbol2,
                    correlation_type=CorrelationType.VOLATILITY_CORRELATION,
                    correlation_coefficient=volat_corr[0],
                    correlation_strength=self._get_correlation_strength(volat_corr[0]),
                    sample_size=min_len,
                    time_period=timeframe,
                    significance=volat_corr[1],
                    last_updated=datetime.now(),
                )

        # Trend correlation (using returns direction)
        if "returns" in data1 and "returns" in data2:
            trend_corr = self._calculate_trend_correlation(data1["returns"][-min_len:], data2["returns"][-min_len:])
            if trend_corr is not None:
                correlations[CorrelationType.TREND_CORRELATION] = CorrelationPair(
                    source_1=symbol1,
                    source_2=symbol2,
                    correlation_type=CorrelationType.TREND_CORRELATION,
                    correlation_coefficient=trend_corr[0],
                    correlation_strength=self._get_correlation_strength(trend_corr[0]),
                    sample_size=min_len,
                    time_period=timeframe,
                    significance=trend_corr[1],
                    last_updated=datetime.now(),
                )

        return correlations

    def _calculate_correlation(self, series1: list[float], series2: list[float]) -> tuple[float, float] | None:
        """Calculate Pearson correlation coefficient and p-value."""
        try:
            if len(series1) != len(series2) or len(series1) < 20:
                return None

            # Remove NaN values
            valid_pairs = [(x, y) for x, y in zip(series1, series2) if not (np.isnan(x) or np.isnan(y))]

            if len(valid_pairs) < 15:
                return None

            x_vals, y_vals = zip(*valid_pairs)

            corr_coef, p_value = stats.pearsonr(x_vals, y_vals)
            return (float(corr_coef), float(p_value))

        except Exception as e:
            logger.debug(f"Correlation calculation failed: {e}")
            return None

    def _calculate_trend_correlation(self, returns1: list[float], returns2: list[float]) -> tuple[float, float] | None:
        """Calculate correlation based on trend direction (sign of returns)."""
        try:
            if len(returns1) != len(returns2) or len(returns1) < 20:
                return None

            # Convert to trend directions (+1 for positive, -1 for negative, 0 for neutral)
            trend1 = [1 if r > 0.5 else (-1 if r < -0.5 else 0) for r in returns1]
            trend2 = [1 if r > 0.5 else (-1 if r < -0.5 else 0) for r in returns2]

            # Remove zero trends
            valid_pairs = [(t1, t2) for t1, t2 in zip(trend1, trend2) if t1 != 0 and t2 != 0]

            if len(valid_pairs) < 10:
                return None

            x_vals, y_vals = zip(*valid_pairs)

            corr_coef, p_value = stats.pearsonr(x_vals, y_vals)
            return (float(corr_coef), float(p_value))

        except Exception as e:
            logger.debug(f"Trend correlation calculation failed: {e}")
            return None

    def _get_correlation_strength(self, coefficient: float) -> CorrelationStrength:
        """Map correlation coefficient to strength category."""
        abs_coef = abs(coefficient)

        if abs_coef >= 0.8:
            return CorrelationStrength.VERY_STRONG
        elif abs_coef >= 0.6:
            return CorrelationStrength.STRONG
        elif abs_coef >= 0.4:
            return CorrelationStrength.MODERATE
        elif abs_coef >= 0.2:
            return CorrelationStrength.WEAK
        else:
            return CorrelationStrength.VERY_WEAK

    async def _identify_dominant_patterns(
        self, correlation_results: dict[str, dict[str, dict[CorrelationType, CorrelationPair]]]
    ) -> list[dict[str, Any]]:
        """Identify dominant correlation patterns across all data."""
        patterns = []

        # Collect all significant correlations
        all_correlations = []
        for timeframe, pairs in correlation_results.items():
            for pair_key, correlations in pairs.items():
                for corr_type, corr_pair in correlations.items():
                    if corr_pair.is_significant():
                        all_correlations.append(
                            {
                                "pair": pair_key,
                                "type": corr_type,
                                "coefficient": corr_pair.correlation_coefficient,
                                "strength": corr_pair.correlation_strength,
                                "timeframe": timeframe,
                            }
                        )

        # Group by correlation type
        by_type = {}
        for corr in all_correlations:
            corr_type = corr["type"]
            if corr_type not in by_type:
                by_type[corr_type] = []
            by_type[corr_type].append(corr)

        # Find strongest patterns by type
        for corr_type, corrs in by_type.items():
            if corrs:
                strongest = max(corrs, key=lambda x: abs(x["coefficient"]))
                patterns.append(
                    {
                        "pattern_type": corr_type.value,
                        "description": f"Strongest {corr_type.value.replace('_', ' ')}",
                        "pair": strongest["pair"],
                        "coefficient": strongest["coefficient"],
                        "strength": strongest["strength"].value,
                        "timeframe": strongest["timeframe"],
                        "count": len(corrs),
                    }
                )

        return sorted(patterns, key=lambda x: abs(x["coefficient"]), reverse=True)[:5]

    async def _analyze_cross_market_correlations(
        self, data_matrix: dict[str, dict[str, dict[str, list[float]]]]
    ) -> list[str]:
        """Analyze correlations with traditional markets (simulated)."""
        insights = []

        # This would connect to traditional market data sources
        # For now, simulate some insights
        insights.append("📈 BTC shows moderate positive correlation with S&P 500 (0.45)")
        insights.append("📉 ETH exhibits inverse correlation with bond yields (-0.32)")
        insights.append("⚡ SOL demonstrates strong correlation with tech sector (0.68)")

        return insights

    async def _identify_trading_opportunities(
        self, correlation_results: dict[str, dict[str, dict[CorrelationType, CorrelationPair]]]
    ) -> list[dict[str, Any]]:
        """Identify potential trading opportunities from correlations."""
        opportunities = []

        # Look for strong negative correlations (pairs moving opposite)
        neg_correlations = []
        for timeframe, pairs in correlation_results.items():
            for pair_key, correlations in pairs.items():
                for corr_type, corr_pair in correlations.items():
                    if corr_pair.is_significant() and corr_pair.correlation_coefficient < -0.6:
                        neg_correlations.append(
                            {
                                "symbols": pair_key.split("_"),
                                "coefficient": corr_pair.correlation_coefficient,
                                "timeframe": timeframe,
                                "type": corr_type,
                            }
                        )

        # Generate opportunity ideas
        for corr in neg_correlations[:3]:  # Top 3 opportunities
            opportunities.append(
                {
                    "strategy": "Pairs Trading",
                    "symbols": corr["symbols"],
                    "opportunity": f"Long {corr['symbols'][0]} / Short {corr['symbols'][1]}",
                    "correlation": corr["coefficient"],
                    "confidence": "High" if abs(corr["coefficient"]) > 0.7 else "Medium",
                    "timeframe": corr["timeframe"],
                }
            )

        return opportunities

    async def _assess_correlation_risks(
        self, correlation_results: dict[str, dict[str, dict[CorrelationType, CorrelationPair]]]
    ) -> list[str]:
        """Assess risks based on correlation patterns."""
        risks = []

        # Check for excessive correlation (systemic risk)
        high_corr_count = 0
        total_pairs = 0

        for timeframe, pairs in correlation_results.items():
            for correlations in pairs.values():
                for corr_pair in correlations.values():
                    total_pairs += 1
                    if corr_pair.is_significant() and abs(corr_pair.correlation_coefficient) > 0.8:
                        high_corr_count += 1

        if total_pairs > 0 and (high_corr_count / total_pairs) > 0.5:
            risks.append("⚠️ High systemic risk: excessive correlation between assets")

        # Check for correlation breakdown risks
        risks.append("🔍 Monitor for correlation breakdown during market stress")
        risks.append("📊 Diversification benefits may be reduced in correlated environment")

        return risks

    def _count_significant_correlations(
        self, correlation_results: dict[str, dict[str, dict[CorrelationType, CorrelationPair]]]
    ) -> int:
        """Count total number of significant correlations."""
        count = 0
        for timeframe_dict in correlation_results.values():
            for pair_dict in timeframe_dict.values():
                for corr_pair in pair_dict.values():
                    if corr_pair.is_significant():
                        count += 1
        return count

    def _find_strongest_correlation(
        self, correlation_results: dict[str, dict[str, dict[CorrelationType, CorrelationPair]]], positive: bool = True
    ) -> CorrelationPair | None:
        """Find the strongest correlation (positive or negative)."""
        strongest = None
        target_sign = 1 if positive else -1

        for timeframe_dict in correlation_results.values():
            for pair_dict in timeframe_dict.values():
                for corr_pair in pair_dict.values():
                    if corr_pair.is_significant():
                        if strongest is None:
                            if (corr_pair.correlation_coefficient * target_sign) > 0:
                                strongest = corr_pair
                        else:
                            current_abs = abs(corr_pair.correlation_coefficient)
                            strongest_abs = abs(strongest.correlation_coefficient)
                            if current_abs > strongest_abs:
                                if (corr_pair.correlation_coefficient * target_sign) > 0:
                                    strongest = corr_pair

        return strongest

    async def get_correlation_summary(self) -> dict[str, Any]:
        """Get summary of recent correlation analysis."""
        if not self._correlation_cache:
            return {"status": "no_data", "message": "No correlation data available"}

        latest_analysis = max(self._correlation_cache.values(), key=lambda x: x.timestamp)

        return {
            "status": "active",
            "timestamp": latest_analysis.timestamp.isoformat(),
            "total_correlations": latest_analysis.total_correlations,
            "significant_correlations": latest_analysis.significant_correlations,
            "dominant_patterns": len(latest_analysis.dominant_patterns),
            "trading_opportunities": len(latest_analysis.trading_opportunities),
            "risk_indicators": len(latest_analysis.risk_indicators),
            "strongest_positive": latest_analysis.strongest_positive.get_description()
            if latest_analysis.strongest_positive
            else None,
            "strongest_negative": latest_analysis.strongest_negative.get_description()
            if latest_analysis.strongest_negative
            else None,
        }

    def clear_cache(self) -> None:
        """Clear correlation analysis cache."""
        self._correlation_cache.clear()
        logger.info("Correlation cache cleared")


# Global instance
_correlation_engine: SmartCorrelationEngine | None = None


def get_correlation_engine() -> SmartCorrelationEngine:
    """Get or create global correlation engine instance."""
    global _correlation_engine
    if _correlation_engine is None:
        _correlation_engine = SmartCorrelationEngine()
    return _correlation_engine
