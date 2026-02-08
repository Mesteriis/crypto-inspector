"""Smart Summary Service - Aggregated insights with bilingual support.

Provides easy-to-understand summary cards:
- Market Pulse: Overall market sentiment
- Portfolio Health: Portfolio risk status
- Today's Action: Recommended action for the day
- Weekly Outlook: Week ahead preview
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from service.analysis.dca import DCAZone, get_dca_calculator
from service.analysis.derivatives import DerivativesAnalyzer
from service.analysis.exchange_flow import FlowDirection, get_exchange_flow_analyzer
from service.analysis.macro import MacroRisk, get_macro_calendar
from service.analysis.onchain import OnChainAnalyzer
from service.analysis.risk import RiskAnalyzer
from service.analysis.unlocks import get_unlock_tracker

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# =============================================================================
# Bilingual Translations
# =============================================================================

SENTIMENTS = {
    "bullish": {"en": "Bullish", "ru": "Бычий"},
    "neutral": {"en": "Neutral", "ru": "Нейтральный"},
    "bearish": {"en": "Bearish", "ru": "Медвежий"},
}

HEALTH_STATUS = {
    "healthy": {"en": "Healthy", "ru": "Здоровый"},
    "warning": {"en": "Warning", "ru": "Внимание"},
    "critical": {"en": "Critical", "ru": "Критический"},
}

ACTIONS = {
    "nothing": {"en": "Nothing to do", "ru": "Ничего не делать"},
    "consider_dca": {"en": "Consider DCA", "ru": "Рассмотрите DCA"},
    "take_profits": {"en": "Take Profits", "ru": "Зафиксировать прибыль"},
    "reduce_risk": {"en": "Reduce Risk", "ru": "Снизить риск"},
    "wait": {"en": "Wait & Watch", "ru": "Ждать и наблюдать"},
    "accumulate": {"en": "Accumulate", "ru": "Накапливать"},
}

PRIORITIES = {
    "low": {"en": "Low", "ru": "Низкий"},
    "medium": {"en": "Medium", "ru": "Средний"},
    "high": {"en": "High", "ru": "Высокий"},
}

OUTLOOK = {
    "positive": {"en": "Positive", "ru": "Позитивный"},
    "neutral": {"en": "Neutral", "ru": "Нейтральный"},
    "negative": {"en": "Negative", "ru": "Негативный"},
    "uncertain": {"en": "Uncertain", "ru": "Неопределённый"},
}


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class MarketPulse:
    """Aggregated market sentiment indicator."""

    sentiment: str  # bullish / neutral / bearish
    sentiment_en: str
    sentiment_ru: str
    confidence: int  # 0-100
    reason: str
    reason_ru: str
    factors: list[str] = field(default_factory=list)
    factors_ru: list[str] = field(default_factory=list)
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict:
        return {
            "sentiment": self.sentiment,
            "sentiment_en": self.sentiment_en,
            "sentiment_ru": self.sentiment_ru,
            "confidence": self.confidence,
            "reason": self.reason,
            "reason_ru": self.reason_ru,
            "factors": self.factors,
            "factors_ru": self.factors_ru,
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class PortfolioHealth:
    """Portfolio health assessment."""

    status: str  # healthy / warning / critical
    status_en: str
    status_ru: str
    score: int  # 0-100
    main_issue: str
    main_issue_ru: str
    issues: list[str] = field(default_factory=list)
    issues_ru: list[str] = field(default_factory=list)
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "status_en": self.status_en,
            "status_ru": self.status_ru,
            "score": self.score,
            "main_issue": self.main_issue,
            "main_issue_ru": self.main_issue_ru,
            "issues": self.issues,
            "issues_ru": self.issues_ru,
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class TodayAction:
    """Recommended action for today."""

    action: str  # nothing / consider_dca / take_profits / reduce_risk
    action_en: str
    action_ru: str
    priority: str  # low / medium / high
    priority_en: str
    priority_ru: str
    details: str
    details_ru: str
    reasoning: list[str] = field(default_factory=list)
    reasoning_ru: list[str] = field(default_factory=list)
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "action_en": self.action_en,
            "action_ru": self.action_ru,
            "priority": self.priority,
            "priority_en": self.priority_en,
            "priority_ru": self.priority_ru,
            "details": self.details,
            "details_ru": self.details_ru,
            "reasoning": self.reasoning,
            "reasoning_ru": self.reasoning_ru,
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class WeeklyOutlook:
    """Weekly market outlook."""

    outlook: str  # positive / neutral / negative / uncertain
    outlook_en: str
    outlook_ru: str
    confidence: int = 50
    key_events: list[str] = field(default_factory=list)
    key_events_ru: list[str] = field(default_factory=list)
    risk_factors: list[str] = field(default_factory=list)
    risk_factors_ru: list[str] = field(default_factory=list)
    opportunities: list[str] = field(default_factory=list)
    opportunities_ru: list[str] = field(default_factory=list)
    risk_level: str = "medium"
    risk_level_en: str = "Medium"
    risk_level_ru: str = "Средний"
    summary: str = ""
    summary_ru: str = ""
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict:
        return {
            "outlook": self.outlook,
            "outlook_en": self.outlook_en,
            "outlook_ru": self.outlook_ru,
            "confidence": self.confidence,
            "key_events": self.key_events,
            "key_events_ru": self.key_events_ru,
            "risk_factors": self.risk_factors,
            "risk_factors_ru": self.risk_factors_ru,
            "opportunities": self.opportunities,
            "opportunities_ru": self.opportunities_ru,
            "risk_level": self.risk_level,
            "risk_level_en": self.risk_level_en,
            "risk_level_ru": self.risk_level_ru,
            "summary": self.summary,
            "summary_ru": self.summary_ru,
            "updated_at": self.updated_at.isoformat(),
        }


# =============================================================================
# Smart Summary Service
# =============================================================================


class SmartSummaryService:
    """
    Aggregates multiple data sources into easy-to-understand summaries.

    All outputs include bilingual support (English + Russian).
    """

    def __init__(self, db_session: "AsyncSession | None" = None):
        self.db = db_session
        self._cache: dict = {}
        self._cache_ttl = 300  # 5 minutes

        # Initialize service instances
        self._onchain_analyzer = OnChainAnalyzer()
        self._derivatives_analyzer = DerivativesAnalyzer()
        self._risk_analyzer = RiskAnalyzer()

    async def get_market_pulse(self) -> MarketPulse:
        """
        Calculate overall market sentiment from multiple indicators.

        Factors considered:
        - Fear & Greed Index
        - BTC trend direction
        - RSI levels
        - Exchange flows
        - Funding rates
        - Volume trends
        """
        # Collect market data (mock for now, will integrate with real services)
        factors_en = []
        factors_ru = []
        bullish_score = 0
        bearish_score = 0

        # Simulate data collection - in production, fetch from actual services
        fear_greed = await self._get_fear_greed()
        btc_trend = await self._get_btc_trend()
        rsi = await self._get_rsi("BTC")
        exchange_flow = await self._get_exchange_flow()
        funding = await self._get_funding_rate()

        # Analyze Fear & Greed
        if fear_greed < 25:
            bullish_score += 20  # Extreme fear = buying opportunity
            factors_en.append("Extreme fear (contrarian bullish)")
            factors_ru.append("Экстремальный страх (контрарный бычий)")
        elif fear_greed < 40:
            bullish_score += 10
            factors_en.append("Fear zone (cautiously bullish)")
            factors_ru.append("Зона страха (осторожно бычий)")
        elif fear_greed > 75:
            bearish_score += 20
            factors_en.append("Extreme greed (contrarian bearish)")
            factors_ru.append("Экстремальная жадность (контрарный медвежий)")
        elif fear_greed > 60:
            bearish_score += 10
            factors_en.append("Greed zone (cautiously bearish)")
            factors_ru.append("Зона жадности (осторожно медвежий)")

        # Analyze BTC Trend
        if btc_trend == "uptrend":
            bullish_score += 25
            factors_en.append("BTC in uptrend")
            factors_ru.append("BTC в восходящем тренде")
        elif btc_trend == "downtrend":
            bearish_score += 25
            factors_en.append("BTC in downtrend")
            factors_ru.append("BTC в нисходящем тренде")
        else:
            factors_en.append("BTC consolidating")
            factors_ru.append("BTC консолидируется")

        # Analyze RSI
        if rsi < 30:
            bullish_score += 15
            factors_en.append(f"RSI oversold ({rsi})")
            factors_ru.append(f"RSI перепродан ({rsi})")
        elif rsi > 70:
            bearish_score += 15
            factors_en.append(f"RSI overbought ({rsi})")
            factors_ru.append(f"RSI перекуплен ({rsi})")

        # Analyze Exchange Flow
        if exchange_flow == "bullish":
            bullish_score += 15
            factors_en.append("Outflow from exchanges (bullish)")
            factors_ru.append("Отток с бирж (бычий)")
        elif exchange_flow == "bearish":
            bearish_score += 15
            factors_en.append("Inflow to exchanges (bearish)")
            factors_ru.append("Приток на биржи (медвежий)")

        # Analyze Funding Rate
        if funding < -0.01:
            bullish_score += 10
            factors_en.append("Negative funding (shorts paying)")
            factors_ru.append("Отрицательный фандинг (шорты платят)")
        elif funding > 0.05:
            bearish_score += 10
            factors_en.append("High positive funding (longs overheated)")
            factors_ru.append("Высокий фандинг (лонги перегреты)")

        # Calculate sentiment
        total_score = bullish_score - bearish_score
        confidence = min(abs(total_score), 100)

        if total_score > 20:
            sentiment = "bullish"
            reason_en = "Multiple bullish signals aligned"
            reason_ru = "Несколько бычьих сигналов совпали"
        elif total_score < -20:
            sentiment = "bearish"
            reason_en = "Multiple bearish signals aligned"
            reason_ru = "Несколько медвежьих сигналов совпали"
        else:
            sentiment = "neutral"
            reason_en = "Mixed signals, no clear direction"
            reason_ru = "Смешанные сигналы, нет чёткого направления"

        return MarketPulse(
            sentiment=sentiment,
            sentiment_en=SENTIMENTS[sentiment]["en"],
            sentiment_ru=SENTIMENTS[sentiment]["ru"],
            confidence=confidence,
            reason=reason_en,
            reason_ru=reason_ru,
            factors=factors_en,
            factors_ru=factors_ru,
        )

    async def get_portfolio_health(self) -> PortfolioHealth:
        """
        Assess portfolio health based on risk metrics.

        Factors considered:
        - Current drawdown
        - Sharpe ratio
        - VaR exposure
        - Position concentration
        - Market correlation
        """
        issues_en = []
        issues_ru = []
        score = 100  # Start with perfect score, deduct for issues

        # Get risk metrics (mock data - integrate with RiskAnalyzer)
        drawdown = await self._get_current_drawdown()
        sharpe = await self._get_sharpe_ratio()
        var_95 = await self._get_var_95()

        # Check drawdown
        if drawdown > 20:
            score -= 30
            issues_en.append(f"High drawdown: {drawdown:.1f}%")
            issues_ru.append(f"Высокая просадка: {drawdown:.1f}%")
        elif drawdown > 10:
            score -= 15
            issues_en.append(f"Moderate drawdown: {drawdown:.1f}%")
            issues_ru.append(f"Умеренная просадка: {drawdown:.1f}%")

        # Check Sharpe ratio
        if sharpe < 0:
            score -= 25
            issues_en.append(f"Negative Sharpe ratio: {sharpe:.2f}")
            issues_ru.append(f"Отрицательный Sharpe: {sharpe:.2f}")
        elif sharpe < 1:
            score -= 10
            issues_en.append(f"Low Sharpe ratio: {sharpe:.2f}")
            issues_ru.append(f"Низкий Sharpe: {sharpe:.2f}")

        # Check VaR
        if var_95 > 15:
            score -= 20
            issues_en.append(f"High VaR 95%: {var_95:.1f}%")
            issues_ru.append(f"Высокий VaR 95%: {var_95:.1f}%")
        elif var_95 > 10:
            score -= 10
            issues_en.append(f"Elevated VaR 95%: {var_95:.1f}%")
            issues_ru.append(f"Повышенный VaR 95%: {var_95:.1f}%")

        # Determine status
        score = max(0, score)
        if score >= 70:
            status = "healthy"
            main_issue_en = "Portfolio is in good shape"
            main_issue_ru = "Портфель в хорошем состоянии"
        elif score >= 40:
            status = "warning"
            main_issue_en = issues_en[0] if issues_en else "Minor concerns detected"
            main_issue_ru = issues_ru[0] if issues_ru else "Обнаружены небольшие проблемы"
        else:
            status = "critical"
            main_issue_en = issues_en[0] if issues_en else "Multiple risk factors present"
            main_issue_ru = issues_ru[0] if issues_ru else "Присутствуют множественные факторы риска"

        return PortfolioHealth(
            status=status,
            status_en=HEALTH_STATUS[status]["en"],
            status_ru=HEALTH_STATUS[status]["ru"],
            score=score,
            main_issue=main_issue_en,
            main_issue_ru=main_issue_ru,
            issues=issues_en,
            issues_ru=issues_ru,
        )

    async def get_today_action(self) -> TodayAction:
        """
        Determine recommended action for today.

        Based on:
        - Market pulse sentiment
        - Portfolio health
        - DCA zone
        - Risk levels
        - Macro events
        """
        market_pulse = await self.get_market_pulse()
        portfolio_health = await self.get_portfolio_health()

        reasoning_en = []
        reasoning_ru = []

        # Get additional data
        dca_zone = await self._get_dca_zone()
        macro_risk = await self._get_macro_risk()
        fg_value = await self._get_fear_greed()

        # Decision logic
        action = "nothing"
        priority = "low"
        details_en = ""
        details_ru = ""

        # Critical portfolio health
        if portfolio_health.status == "critical":
            action = "reduce_risk"
            priority = "high"
            details_en = "Portfolio health is critical. Consider reducing exposure."
            details_ru = "Здоровье портфеля критическое. Рассмотрите снижение позиций."
            reasoning_en.append("Portfolio score below 40%")
            reasoning_ru.append("Оценка портфеля ниже 40%")

        # Extreme fear = buying opportunity
        elif fg_value < 20 and dca_zone == "buy":
            action = "consider_dca"
            priority = "high"
            details_en = "Extreme fear + Buy zone. Excellent DCA opportunity!"
            details_ru = "Экстремальный страх + Зона покупки. Отличная возможность для DCA!"
            reasoning_en.append(f"Fear & Greed at {fg_value}")
            reasoning_en.append("Price in buy zone")
            reasoning_ru.append(f"Fear & Greed на {fg_value}")
            reasoning_ru.append("Цена в зоне покупки")

        # Moderate fear
        elif fg_value < 35 and market_pulse.sentiment == "bullish":
            action = "consider_dca"
            priority = "medium"
            details_en = "Fear + Bullish signals. Good time to accumulate."
            details_ru = "Страх + Бычьи сигналы. Хорошее время для накопления."
            reasoning_en.append("Contrarian opportunity")
            reasoning_ru.append("Контрарная возможность")

        # Extreme greed = take profits
        elif fg_value > 80:
            action = "take_profits"
            priority = "high"
            details_en = "Extreme greed. Consider taking some profits."
            details_ru = "Экстремальная жадность. Рассмотрите фиксацию прибыли."
            reasoning_en.append(f"Fear & Greed at {fg_value}")
            reasoning_ru.append(f"Fear & Greed на {fg_value}")

        # High macro risk
        elif macro_risk == "high":
            action = "wait"
            priority = "medium"
            details_en = "High macro risk this week. Wait for clarity."
            details_ru = "Высокий макро-риск на этой неделе. Подождите ясности."
            reasoning_en.append("Important macro events ahead")
            reasoning_ru.append("Впереди важные макро-события")

        # Default: nothing to do
        else:
            action = "nothing"
            priority = "low"
            details_en = "Market is calm. No action needed."
            details_ru = "Рынок спокоен. Действий не требуется."
            reasoning_en.append("No significant signals")
            reasoning_ru.append("Нет значимых сигналов")

        return TodayAction(
            action=action,
            action_en=ACTIONS[action]["en"],
            action_ru=ACTIONS[action]["ru"],
            priority=priority,
            priority_en=PRIORITIES[priority]["en"],
            priority_ru=PRIORITIES[priority]["ru"],
            details=details_en,
            details_ru=details_ru,
            reasoning=reasoning_en,
            reasoning_ru=reasoning_ru,
        )

    async def get_weekly_outlook(self) -> WeeklyOutlook:
        """
        Generate weekly outlook based on upcoming events and trends.
        """
        events_en = []
        events_ru = []
        risk_factors_en = []
        risk_factors_ru = []
        opportunities_en = []
        opportunities_ru = []

        # Get upcoming events (mock data)
        macro_events = await self._get_upcoming_macro_events()
        unlocks = await self._get_upcoming_unlocks()

        # Add macro events
        for event in macro_events[:3]:
            events_en.append(event.get("name", ""))
            events_ru.append(event.get("name_ru", event.get("name", "")))

        # Add token unlocks
        if unlocks > 3:
            events_en.append(f"{unlocks} token unlocks this week")
            events_ru.append(f"{unlocks} анлоков токенов на этой неделе")

        # Determine outlook
        market_pulse = await self.get_market_pulse()
        macro_risk = await self._get_macro_risk()
        confidence = 50

        if macro_risk == "high":
            outlook = "uncertain"
            risk_level = "high"
            confidence = 40
            summary_en = "High-risk week ahead. Multiple macro events may cause volatility."
            summary_ru = "Впереди неделя высокого риска. Макро-события могут вызвать волатильность."
            risk_factors_en = ["Macro event volatility", "Market uncertainty"]
            risk_factors_ru = ["Волатильность макро-событий", "Рыночная неопределённость"]
            opportunities_en = ["Potential dip buying"]
            opportunities_ru = ["Потенциальная покупка на просадке"]
        elif market_pulse.sentiment == "bullish" and market_pulse.confidence > 60:
            outlook = "positive"
            risk_level = "low"
            confidence = 70
            summary_en = "Positive outlook. Bullish momentum likely to continue."
            summary_ru = "Позитивный прогноз. Бычий импульс вероятно продолжится."
            risk_factors_en = ["Overbought conditions possible"]
            risk_factors_ru = ["Возможна перекупленность"]
            opportunities_en = ["Trend continuation", "Alt rotation"]
            opportunities_ru = ["Продолжение тренда", "Ротация альтов"]
        elif market_pulse.sentiment == "bearish" and market_pulse.confidence > 60:
            outlook = "negative"
            risk_level = "medium"
            confidence = 60
            summary_en = "Cautious outlook. Bearish pressure may persist."
            summary_ru = "Осторожный прогноз. Медвежье давление может сохраниться."
            risk_factors_en = ["Continued selling pressure", "Support breakdown"]
            risk_factors_ru = ["Продолжение давления продаж", "Пробой поддержки"]
            opportunities_en = ["Accumulation zone entry"]
            opportunities_ru = ["Вход в зону накопления"]
        else:
            outlook = "neutral"
            risk_level = "medium"
            confidence = 50
            summary_en = "Mixed outlook. Watch key levels and events."
            summary_ru = "Смешанный прогноз. Следите за ключевыми уровнями и событиями."
            risk_factors_en = ["Low conviction environment"]
            risk_factors_ru = ["Среда с низкой уверенностью"]
            opportunities_en = ["Range trading", "Wait for breakout"]
            opportunities_ru = ["Торговля в диапазоне", "Ожидание пробоя"]

        return WeeklyOutlook(
            outlook=outlook,
            outlook_en=OUTLOOK[outlook]["en"],
            outlook_ru=OUTLOOK[outlook]["ru"],
            confidence=confidence,
            key_events=events_en,
            key_events_ru=events_ru,
            risk_factors=risk_factors_en,
            risk_factors_ru=risk_factors_ru,
            opportunities=opportunities_en,
            opportunities_ru=opportunities_ru,
            risk_level=risk_level,
            risk_level_en=PRIORITIES[risk_level]["en"],
            risk_level_ru=PRIORITIES[risk_level]["ru"],
            summary=summary_en,
            summary_ru=summary_ru,
        )

    # =========================================================================
    # Helper methods - integrated with real services
    # =========================================================================

    async def _get_fear_greed(self) -> int:
        """Get Fear & Greed Index value from OnChainAnalyzer."""
        try:
            fg_data = await self._onchain_analyzer.fetch_fear_greed()
            if fg_data:
                return fg_data.value
        except Exception as e:
            logger.warning(f"Failed to fetch Fear & Greed: {e}")
        return 45  # Default neutral value

    async def _get_btc_trend(self) -> str:
        """
        Get BTC trend direction from candlestick data.

        Analyzes SMA 20/50/200 to determine trend.
        """
        try:
            from service.analysis.technical import TechnicalAnalyzer
            from service.candlestick import fetch_candlesticks
            from service.candlestick.models import CandleInterval

            candles = await fetch_candlesticks(
                symbol="BTC",
                interval=CandleInterval.HOUR_4,
                limit=200,
            )

            if len(candles) >= 200:
                closes = [float(c.close_price) for c in candles]
                analyzer = TechnicalAnalyzer()

                sma_20 = analyzer.calc_sma(closes, 20)
                sma_50 = analyzer.calc_sma(closes, 50)
                sma_200 = analyzer.calc_sma(closes, 200)
                current_price = closes[-1]

                if sma_20 and sma_50 and sma_200:
                    # Strong uptrend: price > SMA20 > SMA50 > SMA200
                    if current_price > sma_20 > sma_50 > sma_200:
                        return "uptrend"
                    # Strong downtrend: price < SMA20 < SMA50 < SMA200
                    if current_price < sma_20 < sma_50 < sma_200:
                        return "downtrend"
        except Exception as e:
            logger.warning(f"Failed to analyze BTC trend: {e}")
        return "sideways"

    async def _get_rsi(self, symbol: str) -> float:
        """Get RSI value for symbol from TechnicalAnalyzer."""
        try:
            from service.analysis.technical import TechnicalAnalyzer
            from service.candlestick import fetch_candlesticks
            from service.candlestick.models import CandleInterval

            candles = await fetch_candlesticks(
                symbol=symbol,
                interval=CandleInterval.HOUR_4,
                limit=50,
            )

            if len(candles) >= 15:
                closes = [float(c.close_price) for c in candles]
                rsi = TechnicalAnalyzer.calc_rsi(closes, 14)
                if rsi is not None:
                    return rsi
        except Exception as e:
            logger.warning(f"Failed to calculate RSI for {symbol}: {e}")
        return 55.0  # Default neutral value

    async def _get_exchange_flow(self) -> str:
        """Get exchange flow signal from ExchangeFlowAnalyzer."""
        try:
            analyzer = get_exchange_flow_analyzer()
            flow_summary = await analyzer.analyze()

            if flow_summary.overall_signal in [
                FlowDirection.STRONG_OUTFLOW,
                FlowDirection.OUTFLOW,
            ]:
                return "bullish"
            if flow_summary.overall_signal in [
                FlowDirection.STRONG_INFLOW,
                FlowDirection.INFLOW,
            ]:
                return "bearish"
        except Exception as e:
            logger.warning(f"Failed to get exchange flow: {e}")
        return "neutral"

    async def _get_funding_rate(self) -> float:
        """Get BTC funding rate from DerivativesAnalyzer."""
        try:
            funding_data = await self._derivatives_analyzer.fetch_funding_rate("BTC")
            if funding_data:
                return funding_data.rate
        except Exception as e:
            logger.warning(f"Failed to fetch funding rate: {e}")
        return 0.01  # Default neutral value

    async def _get_current_drawdown(self) -> float:
        """Get current portfolio drawdown from RiskAnalyzer."""
        try:
            if self._risk_analyzer.last_metrics:
                return self._risk_analyzer.last_metrics.current_drawdown
        except Exception as e:
            logger.warning(f"Failed to get drawdown: {e}")
        return 5.0  # Default low drawdown

    async def _get_sharpe_ratio(self) -> float:
        """Get portfolio Sharpe ratio from RiskAnalyzer."""
        try:
            if self._risk_analyzer.last_metrics:
                return self._risk_analyzer.last_metrics.sharpe_ratio
        except Exception as e:
            logger.warning(f"Failed to get Sharpe ratio: {e}")
        return 1.5  # Default acceptable value

    async def _get_var_95(self) -> float:
        """Get portfolio VaR 95% from RiskAnalyzer."""
        try:
            if self._risk_analyzer.last_metrics:
                return self._risk_analyzer.last_metrics.var_95
        except Exception as e:
            logger.warning(f"Failed to get VaR: {e}")
        return 8.0  # Default moderate value

    async def _get_dca_zone(self) -> str:
        """Get current DCA zone from DCACalculator."""
        try:
            calculator = get_dca_calculator()
            analysis = await calculator.analyze("BTC")

            if analysis.zone == DCAZone.BUY_ZONE:
                return "buy"
            if analysis.zone == DCAZone.OVERBOUGHT:
                return "overbought"
        except Exception as e:
            logger.warning(f"Failed to get DCA zone: {e}")
        return "wait"

    async def _get_macro_risk(self) -> str:
        """Get macro risk level for the week from MacroCalendar."""
        try:
            calendar = get_macro_calendar()
            analysis = await calendar.analyze(days_ahead=7)

            if analysis.week_risk == MacroRisk.HIGH:
                return "high"
            if analysis.week_risk == MacroRisk.LOW:
                return "low"
        except Exception as e:
            logger.warning(f"Failed to get macro risk: {e}")
        return "medium"

    async def _get_upcoming_macro_events(self) -> list[dict]:
        """Get upcoming macro events from MacroCalendar."""
        try:
            calendar = get_macro_calendar()
            analysis = await calendar.analyze(days_ahead=14)

            events = []
            for event in analysis.events[:5]:
                events.append(
                    {
                        "name": event.name,
                        "name_ru": event.event_type.name_ru,
                        "date": event.date.strftime("%Y-%m-%d"),
                        "days_until": event.days_until,
                    }
                )
            return events
        except Exception as e:
            logger.warning(f"Failed to get macro events: {e}")
        return [
            {"name": "FOMC Meeting", "name_ru": "Заседание FOMC"},
            {"name": "CPI Data", "name_ru": "Данные CPI"},
        ]

    async def _get_upcoming_unlocks(self) -> int:
        """Get number of token unlocks this week from UnlockTracker."""
        try:
            tracker = get_unlock_tracker()
            analysis = await tracker.analyze()
            return analysis.next_7d_count
        except Exception as e:
            logger.warning(f"Failed to get unlock count: {e}")
        return 2  # Default value

    def format_sensor_attributes(self) -> dict:
        """
        Format summary data for Home Assistant sensors.

        Returns:
            Dict ready for HA sensor updates.
        """
        # Since we have async methods, we need to provide sync defaults
        # or cache the last computed values
        return {
            "market_pulse": {
                "sentiment": "neutral",
                "sentiment_en": "Neutral",
                "sentiment_ru": "Нейтральный",
                "confidence": 50,
            },
            "portfolio_health": {
                "status": "healthy",
                "status_en": "Healthy",
                "status_ru": "Здоровый",
                "score": 85,
            },
            "today_action": {
                "action": "nothing",
                "action_en": "No Action Needed",
                "action_ru": "Действий не требуется",
                "priority": "low",
            },
            "weekly_outlook": {
                "outlook": "neutral",
                "outlook_en": "Neutral",
                "outlook_ru": "Нейтральный",
                "risk_level": "medium",
            },
        }
