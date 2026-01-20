#!/usr/bin/env python3
"""
Lazy Investor ML Integration

Transforms ML predictions from "trading signals" to "investment awareness triggers"
for passive investors who don't want to actively trade but want to stay informed.
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime

from service.analysis.scoring import ScoringEngine
from service.candlestick import CandleInterval, fetch_candlesticks
from service.ml.forecaster import PriceForecaster

from ...core.constants import MLDefaults

logger = logging.getLogger(__name__)


@dataclass
class InvestmentSignal:
    """Investment awareness signal for lazy investors."""

    symbol: str
    timestamp: datetime
    signal_type: str  # "opportunity", "risk_warning", "market_shift", "hold"
    confidence_level: str  # "high", "medium", "low"
    rationale: str
    suggested_action: str  # "monitor", "research", "consult", "ignore"
    timeframe: str  # "short_term", "medium_term", "long_term"


class LazyInvestorMLAdvisor:
    """Transforms ML predictions into lazy investor-friendly signals."""

    def __init__(self):
        self.forecaster = PriceForecaster()
        self.scoring_engine = ScoringEngine()
        self.investment_threshold = 0.6  # Only trigger for high-confidence signals

    async def generate_investment_signals(self, symbols: list[str]) -> list[InvestmentSignal]:
        """
        Generate investment awareness signals for lazy investors.

        Instead of "buy/sell" recommendations, provides:
        - Market condition awareness
        - Risk level assessment
        - Research triggers
        - Portfolio monitoring suggestions
        """
        signals = []

        for symbol in symbols:
            try:
                # Fetch recent data
                candles = await fetch_candlesticks(symbol=symbol, interval=CandleInterval.DAY_1, limit=100)

                if not candles:
                    continue

                prices = [float(candle.close_price) for candle in candles]

                # Get ML predictions with enhanced accuracy system
                predictions = await self._get_enhanced_predictions(symbol, prices)

                # Transform predictions into investment signals
                symbol_signals = await self._transform_to_signals(symbol, predictions, prices)
                signals.extend(symbol_signals)

            except Exception as e:
                logger.error(f"Failed to generate signals for {symbol}: {e}")
                continue

        return signals

    async def _get_enhanced_predictions(self, symbol: str, prices: list[float]) -> dict:
        """Get enhanced predictions using improved system."""
        # Use our enhanced accuracy forecaster
        # This would integrate with the enhanced_accuracy_system.py

        predictions = {}
        context_prices = prices[-min(len(prices), MLDefaults.CONTEXT_LENGTH) :]

        for model_name in self.forecaster.get_available_models():
            try:
                forecast = await self.forecaster.predict(
                    symbol=symbol,
                    interval="1d",
                    prices=context_prices,
                    model=model_name,
                    horizon=7,  # 7-day outlook for investment perspective
                )

                predictions[model_name] = {
                    "prediction": forecast.predictions[-1],
                    "confidence": forecast.confidence_pct,
                    "direction": forecast.direction,
                    "current_price": prices[-1],
                }

            except Exception as e:
                logger.debug(f"Model {model_name} failed for {symbol}: {e}")
                continue

        return predictions

    async def _transform_to_signals(
        self, symbol: str, predictions: dict, prices: list[float]
    ) -> list[InvestmentSignal]:
        """Transform raw predictions into investment awareness signals."""
        signals = []
        current_price = prices[-1]

        # Ensemble analysis
        if predictions:
            # Calculate consensus among models
            directions = [pred["direction"] for pred in predictions.values()]
            confidences = [pred["confidence"] for pred in predictions.values()]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0

            # Market consensus
            up_votes = directions.count("up")
            down_votes = directions.count("down")
            neutral_votes = directions.count("neutral")

            # Generate appropriate signals based on consensus and confidence
            if avg_confidence >= 70:  # High confidence threshold
                if up_votes > down_votes + neutral_votes:
                    # Strong bullish consensus
                    signals.append(
                        InvestmentSignal(
                            symbol=symbol,
                            timestamp=datetime.now(),
                            signal_type="opportunity",
                            confidence_level="high",
                            rationale=f"Strong bullish consensus ({up_votes}/{len(directions)} models) with {avg_confidence:.1f}% confidence",
                            suggested_action="research",
                            timeframe="medium_term",
                        )
                    )

                elif down_votes > up_votes + neutral_votes:
                    # Strong bearish consensus
                    signals.append(
                        InvestmentSignal(
                            symbol=symbol,
                            timestamp=datetime.now(),
                            signal_type="risk_warning",
                            confidence_level="high",
                            rationale=f"Strong bearish consensus ({down_votes}/{len(directions)} models) with {avg_confidence:.1f}% confidence",
                            suggested_action="review_portfolio",
                            timeframe="short_term",
                        )
                    )

            elif avg_confidence >= 50:  # Medium confidence
                # Market uncertainty - good time for dollar-cost averaging
                signals.append(
                    InvestmentSignal(
                        symbol=symbol,
                        timestamp=datetime.now(),
                        signal_type="market_shift",
                        confidence_level="medium",
                        rationale="Market uncertainty detected - good opportunity for DCA strategy",
                        suggested_action="monitor",
                        timeframe="long_term",
                    )
                )

            else:
                # Low confidence - hold and observe
                signals.append(
                    InvestmentSignal(
                        symbol=symbol,
                        timestamp=datetime.now(),
                        signal_type="hold",
                        confidence_level="low",
                        rationale="Low model confidence - market conditions unclear",
                        suggested_action="ignore",
                        timeframe="long_term",
                    )
                )

        # Technical analysis overlay
        tech_signals = await self._analyze_technical_conditions(symbol, prices)
        signals.extend(tech_signals)

        return signals

    async def _analyze_technical_conditions(self, symbol: str, prices: list[float]) -> list[InvestmentSignal]:
        """Analyze technical conditions for investment signals."""
        signals = []

        if len(prices) < 20:
            return signals

        # Simple technical indicators for lazy investors
        current_price = prices[-1]
        ma_20 = sum(prices[-20:]) / 20
        ma_50 = sum(prices[-50:]) / 50 if len(prices) >= 50 else ma_20

        # Moving average signals
        if current_price > ma_20 > ma_50:
            # Bullish trend
            signals.append(
                InvestmentSignal(
                    symbol=symbol,
                    timestamp=datetime.now(),
                    signal_type="opportunity",
                    confidence_level="medium",
                    rationale="Price above 20-day and 50-day moving averages - uptrend confirmed",
                    suggested_action="monitor",
                    timeframe="medium_term",
                )
            )

        elif current_price < ma_20 < ma_50:
            # Bearish trend
            signals.append(
                InvestmentSignal(
                    symbol=symbol,
                    timestamp=datetime.now(),
                    signal_type="risk_warning",
                    confidence_level="medium",
                    rationale="Price below 20-day and 50-day moving averages - downtrend confirmed",
                    suggested_action="review_holdings",
                    timeframe="short_term",
                )
            )

        # Volatility analysis
        recent_volatility = self._calculate_volatility(prices[-30:])
        if recent_volatility > 0.15:  # 15% volatility
            signals.append(
                InvestmentSignal(
                    symbol=symbol,
                    timestamp=datetime.now(),
                    signal_type="market_shift",
                    confidence_level="high",
                    rationale=f"High volatility detected ({recent_volatility:.1%}) - increased caution advised",
                    suggested_action="reduce_exposure",
                    timeframe="short_term",
                )
            )

        return signals

    def _calculate_volatility(self, prices: list[float]) -> float:
        """Calculate price volatility."""
        if len(prices) < 2:
            return 0

        returns = [(prices[i] - prices[i - 1]) / prices[i - 1] for i in range(1, len(prices))]
        return (sum(r**2 for r in returns) / len(returns)) ** 0.5

    async def get_portfolio_health_score(self, portfolio_symbols: list[str]) -> dict:
        """Generate overall portfolio health assessment."""
        signals = await self.generate_investment_signals(portfolio_symbols)

        # Categorize signals
        opportunity_count = len([s for s in signals if s.signal_type == "opportunity"])
        risk_count = len([s for s in signals if s.signal_type == "risk_warning"])
        hold_count = len([s for s in signals if s.signal_type == "hold"])
        total_signals = len(signals)

        # Portfolio sentiment
        if opportunity_count > risk_count * 2:
            sentiment = "bullish"
            recommendation = "Consider gradual accumulation"
        elif risk_count > opportunity_count * 2:
            sentiment = "bearish"
            recommendation = "Review holdings and consider rebalancing"
        else:
            sentiment = "neutral"
            recommendation = "Maintain current positions, monitor developments"

        return {
            "portfolio_sentiment": sentiment,
            "opportunity_signals": opportunity_count,
            "risk_signals": risk_count,
            "hold_signals": hold_count,
            "total_analyzed": total_signals,
            "recommendation": recommendation,
            "timestamp": datetime.now().isoformat(),
        }

    async def generate_daily_briefing(self, symbols: list[str]) -> str:
        """Generate human-readable daily investment briefing."""
        signals = await self.generate_investment_signals(symbols)
        portfolio_health = await self.get_portfolio_health_score(symbols)

        briefing = f"""
🌅 DAILY INVESTMENT BRIEFING
📅 {datetime.now().strftime('%Y-%m-%d')}
📊 Portfolio Health: {portfolio_health['portfolio_sentiment'].upper()}
💡 Recommendation: {portfolio_health['recommendation']}

🔔 KEY SIGNALS TODAY:
"""

        # Group signals by type
        opportunities = [s for s in signals if s.signal_type == "opportunity"]
        risks = [s for s in signals if s.signal_type == "risk_warning"]
        market_shifts = [s for s in signals if s.signal_type == "market_shift"]

        if opportunities:
            briefing += f"\n✅ OPPORTUNITIES ({len(opportunities)}):\n"
            for signal in opportunities[:3]:  # Top 3
                briefing += f"  • {signal.symbol}: {signal.rationale}\n"

        if risks:
            briefing += f"\n⚠️  RISK WARNINGS ({len(risks)}):\n"
            for signal in risks[:3]:  # Top 3
                briefing += f"  • {signal.symbol}: {signal.rationale}\n"

        if market_shifts:
            briefing += f"\n🔄 MARKET SHIFTS ({len(market_shifts)}):\n"
            for signal in market_shifts[:2]:
                briefing += f"  • {signal.symbol}: {signal.rationale}\n"

        briefing += f"""
📈 PORTFOLIO METRICS:
• Opportunities: {portfolio_health['opportunity_signals']}
• Risk Warnings: {portfolio_health['risk_signals']}
• Hold Signals: {portfolio_health['hold_signals']}
• Total Assets Monitored: {portfolio_health['total_analyzed']}

🎯 LAZY INVESTOR STRATEGY:
• Don't panic sell on negative signals
• Don't chase every positive signal
• Focus on long-term trends (30+ day outlook)
• Use volatility as opportunity for dollar-cost averaging
• Review portfolio monthly, not daily
"""

        return briefing.strip()


# Example usage
async def main():
    advisor = LazyInvestorMLAdvisor()

    # Example portfolio
    portfolio = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]

    # Generate daily briefing
    briefing = await advisor.generate_daily_briefing(portfolio)
    print(briefing)

    # Get portfolio health
    health = await advisor.get_portfolio_health_score(portfolio)
    print(f"\nPortfolio Health: {json.dumps(health, indent=2)}")


if __name__ == "__main__":
    asyncio.run(main())
