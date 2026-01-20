"""
AI Market Analyzer.

Orchestrates AI analysis by collecting market data and generating insights.
"""

import logging
from dataclasses import dataclass
from datetime import datetime

from service.ai.prompts import (
    SYSTEM_PROMPT_ANALYST,
    SYSTEM_PROMPT_DCA,
    SYSTEM_PROMPT_RISK,
    MarketData,
    extract_recommendation_from_response,
    extract_sentiment_from_response,
    format_ai_response_for_ha,
    get_daily_summary_prompt,
    get_dca_recommendation_prompt,
    get_market_sentiment_prompt,
    get_opportunity_prompt,
    get_risk_assessment_prompt,
    get_weekly_report_prompt,
)
from service.ai.providers import AIService

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    """Result of AI analysis."""

    analysis_type: str
    content: str
    sentiment: str | None = None
    recommendation: str | None = None
    provider: str | None = None
    model: str | None = None
    timestamp: datetime | None = None
    language: str = "en"

    def to_dict(self) -> dict:
        return {
            "type": self.analysis_type,
            "content": self.content,
            "sentiment": self.sentiment,
            "recommendation": self.recommendation,
            "provider": self.provider,
            "model": self.model,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "language": self.language,
        }


class MarketAnalyzer:
    """
    AI-powered market analyzer.

    Collects data from various services and generates AI insights.
    """

    def __init__(self, ai_service: AIService):
        self.ai_service = ai_service
        self._last_analysis: AnalysisResult | None = None
        self._analysis_history: list[AnalysisResult] = []

    @property
    def last_analysis(self) -> AnalysisResult | None:
        return self._last_analysis

    @property
    def analysis_history(self) -> list[AnalysisResult]:
        return self._analysis_history[-50:]  # Keep last 50

    async def generate_daily_summary(
        self,
        market_data: MarketData,
        language: str = "en",
    ) -> AnalysisResult | None:
        """
        Generate daily market summary.

        Args:
            market_data: Current market data
            language: Response language ("en" or "ru")

        Returns:
            AnalysisResult or None if AI unavailable
        """
        prompt = get_daily_summary_prompt(market_data, language)

        response = await self.ai_service.generate(
            prompt=prompt,
            system=SYSTEM_PROMPT_ANALYST,
            temperature=0.7,
            max_tokens=500,
        )

        if not response:
            return None

        result = AnalysisResult(
            analysis_type="daily_summary",
            content=response.content,
            sentiment=extract_sentiment_from_response(response.content),
            recommendation=extract_recommendation_from_response(response.content),
            provider=response.provider,
            model=response.model,
            timestamp=datetime.now(),
            language=language,
        )

        self._last_analysis = result
        self._analysis_history.append(result)

        return result

    async def generate_weekly_report(
        self,
        market_data: MarketData,
        language: str = "en",
    ) -> AnalysisResult | None:
        """
        Generate weekly analysis report.

        Args:
            market_data: Current market data
            language: Response language

        Returns:
            AnalysisResult or None
        """
        prompt = get_weekly_report_prompt(market_data, language)

        response = await self.ai_service.generate(
            prompt=prompt,
            system=SYSTEM_PROMPT_ANALYST,
            temperature=0.7,
            max_tokens=800,
        )

        if not response:
            return None

        result = AnalysisResult(
            analysis_type="weekly_report",
            content=response.content,
            sentiment=extract_sentiment_from_response(response.content),
            recommendation=extract_recommendation_from_response(response.content),
            provider=response.provider,
            model=response.model,
            timestamp=datetime.now(),
            language=language,
        )

        self._last_analysis = result
        self._analysis_history.append(result)

        return result

    async def analyze_opportunity(
        self,
        symbol: str,
        market_data: MarketData,
        language: str = "en",
    ) -> AnalysisResult | None:
        """
        Analyze trading opportunity for a specific symbol.

        Args:
            symbol: Trading symbol (e.g., "BTC")
            market_data: Current market data
            language: Response language

        Returns:
            AnalysisResult or None
        """
        prompt = get_opportunity_prompt(symbol, market_data, language)

        response = await self.ai_service.generate(
            prompt=prompt,
            system=SYSTEM_PROMPT_ANALYST,
            temperature=0.5,
            max_tokens=400,
        )

        if not response:
            return None

        result = AnalysisResult(
            analysis_type=f"opportunity_{symbol.lower()}",
            content=response.content,
            sentiment=extract_sentiment_from_response(response.content),
            recommendation=extract_recommendation_from_response(response.content),
            provider=response.provider,
            model=response.model,
            timestamp=datetime.now(),
            language=language,
        )

        self._analysis_history.append(result)

        return result

    async def get_dca_recommendation(
        self,
        market_data: MarketData,
        base_amount: float = 100.0,
        language: str = "en",
    ) -> AnalysisResult | None:
        """
        Get DCA recommendation based on current market conditions.

        Args:
            market_data: Current market data
            base_amount: Base DCA amount
            language: Response language

        Returns:
            AnalysisResult or None
        """
        prompt = get_dca_recommendation_prompt(market_data, base_amount, language)

        response = await self.ai_service.generate(
            prompt=prompt,
            system=SYSTEM_PROMPT_DCA,
            temperature=0.3,
            max_tokens=300,
        )

        if not response:
            return None

        result = AnalysisResult(
            analysis_type="dca_recommendation",
            content=response.content,
            recommendation=extract_recommendation_from_response(response.content),
            provider=response.provider,
            model=response.model,
            timestamp=datetime.now(),
            language=language,
        )

        self._analysis_history.append(result)

        return result

    async def assess_risk(
        self,
        market_data: MarketData,
        portfolio_allocation: dict[str, float] | None = None,
        language: str = "en",
    ) -> AnalysisResult | None:
        """
        Assess portfolio risks.

        Args:
            market_data: Current market data
            portfolio_allocation: Portfolio allocation percentages
            language: Response language

        Returns:
            AnalysisResult or None
        """
        prompt = get_risk_assessment_prompt(market_data, portfolio_allocation, language)

        response = await self.ai_service.generate(
            prompt=prompt,
            system=SYSTEM_PROMPT_RISK,
            temperature=0.3,
            max_tokens=400,
        )

        if not response:
            return None

        result = AnalysisResult(
            analysis_type="risk_assessment",
            content=response.content,
            provider=response.provider,
            model=response.model,
            timestamp=datetime.now(),
            language=language,
        )

        self._analysis_history.append(result)

        return result

    async def get_sentiment(
        self,
        market_data: MarketData,
        language: str = "en",
    ) -> AnalysisResult | None:
        """
        Get market sentiment analysis.

        Args:
            market_data: Current market data
            language: Response language

        Returns:
            AnalysisResult with sentiment
        """
        prompt = get_market_sentiment_prompt(market_data, language)

        response = await self.ai_service.generate(
            prompt=prompt,
            system=SYSTEM_PROMPT_ANALYST,
            temperature=0.3,
            max_tokens=200,
        )

        if not response:
            return None

        sentiment = extract_sentiment_from_response(response.content)

        result = AnalysisResult(
            analysis_type="sentiment",
            content=response.content,
            sentiment=sentiment,
            provider=response.provider,
            model=response.model,
            timestamp=datetime.now(),
            language=language,
        )

        self._analysis_history.append(result)

        return result

    def get_summary_for_sensor(self, max_length: int = 255) -> str:
        """Get formatted summary for HA sensor."""
        if not self._last_analysis:
            return "No analysis available"

        return format_ai_response_for_ha(self._last_analysis.content, max_length=max_length)

    def get_sentiment_for_sensor(self) -> str:
        """Get sentiment for HA sensor."""
        if not self._last_analysis or not self._last_analysis.sentiment:
            return "Unknown"
        return self._last_analysis.sentiment

    def get_recommendation_for_sensor(self) -> str:
        """Get recommendation for HA sensor."""
        if not self._last_analysis or not self._last_analysis.recommendation:
            return "N/A"
        return self._last_analysis.recommendation

    def get_last_analysis_time(self) -> str:
        """Get last analysis timestamp for HA sensor."""
        if not self._last_analysis or not self._last_analysis.timestamp:
            return "Never"
        return self._last_analysis.timestamp.strftime("%Y-%m-%d %H:%M")


# =============================================================================
# Helper to collect market data from services
# =============================================================================


async def collect_market_data(
    prices: dict | None = None,
    changes: dict | None = None,
    fear_greed: dict | None = None,
    btc_dominance: float | None = None,
    altseason: dict | None = None,
    technical: dict | None = None,
    volatility: dict | None = None,
    exchange_flow: dict | None = None,
    macro: dict | None = None,
    portfolio: dict | None = None,
) -> MarketData:
    """
    Collect market data from various sources into MarketData object.

    This is a helper to gather data from different services.
    """
    # Defaults
    btc_price = 0.0
    eth_price = 0.0
    btc_change = 0.0
    eth_change = 0.0

    if prices:
        btc_price = float(prices.get("BTC/USDT", prices.get("BTCUSDT", 0)))
        eth_price = float(prices.get("ETH/USDT", prices.get("ETHUSDT", 0)))

    if changes:
        btc_change = float(changes.get("BTC/USDT", changes.get("BTCUSDT", 0)))
        eth_change = float(changes.get("ETH/USDT", changes.get("ETHUSDT", 0)))

    fg_value = 50
    fg_label = "Neutral"
    if fear_greed:
        fg_value = int(fear_greed.get("value", 50))
        fg_label = fear_greed.get("label", "Neutral")

    alt_index = 50
    if altseason:
        alt_index = int(altseason.get("index", 50))

    # Technical data
    btc_rsi = None
    eth_rsi = None
    btc_trend = None
    btc_support = None
    btc_resistance = None

    if technical:
        btc_rsi = technical.get("btc_rsi")
        eth_rsi = technical.get("eth_rsi")
        btc_trend = technical.get("btc_trend")
        btc_support = technical.get("btc_support")
        btc_resistance = technical.get("btc_resistance")

    # Volatility
    vol_30d = None
    vol_status = None
    if volatility:
        vol_30d = volatility.get("volatility_30d")
        vol_status = volatility.get("status")

    # Exchange flow
    flow_signal = None
    whale_activity = None
    if exchange_flow:
        flow_signal = exchange_flow.get("signal")
        whale_activity = exchange_flow.get("whale_activity")

    # Macro
    next_event = None
    days_fomc = None
    if macro:
        next_event = macro.get("next_event")
        days_fomc = macro.get("days_to_fomc")

    # Portfolio
    port_value = None
    port_pnl = None
    if portfolio:
        port_value = portfolio.get("total_value")
        port_pnl = portfolio.get("pnl_24h")

    return MarketData(
        btc_price=btc_price,
        eth_price=eth_price,
        btc_change_24h=btc_change,
        eth_change_24h=eth_change,
        fear_greed=fg_value,
        fear_greed_label=fg_label,
        btc_dominance=btc_dominance or 50.0,
        altseason_index=alt_index,
        btc_rsi=btc_rsi,
        eth_rsi=eth_rsi,
        btc_trend=btc_trend,
        btc_support=btc_support,
        btc_resistance=btc_resistance,
        volatility_30d=vol_30d,
        volatility_status=vol_status,
        exchange_flow=flow_signal,
        whale_activity=whale_activity,
        next_macro_event=next_event,
        days_to_fomc=days_fomc,
        portfolio_value=port_value,
        portfolio_pnl_24h=port_pnl,
    )
