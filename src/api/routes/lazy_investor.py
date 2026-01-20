"""
Lazy Investor API Routes

Endpoints for passive investors who want market awareness without active trading.
"""

from datetime import datetime

from fastapi import APIRouter, Query

from core.constants import DEFAULT_SYMBOLS
from schemas.api.lazy_investor import (
    DailyBriefingResponse,
    InvestmentSignalResponse,
    PortfolioHealthResponse,
)
from service.investor.lazy_investor_ml import LazyInvestorMLAdvisor

router = APIRouter(prefix="/lazy-investor", tags=["Lazy Investor"])


@router.get("/signals", response_model=list[InvestmentSignalResponse])
async def get_investment_signals(
    symbols: list[str] = Query(default=DEFAULT_SYMBOLS, description="Cryptocurrency symbols to analyze"),
):
    """
    Get investment awareness signals for lazy investors.

    Instead of buy/sell recommendations, provides:
    - Market condition awareness
    - Risk level assessment
    - Research triggers
    - Portfolio monitoring suggestions
    """
    advisor = LazyInvestorMLAdvisor()
    signals = await advisor.generate_investment_signals(symbols)

    return [
        InvestmentSignalResponse(
            symbol=s.symbol,
            signal_type=s.signal_type,
            confidence_level=s.confidence_level,
            rationale=s.rationale,
            suggested_action=s.suggested_action,
            timeframe=s.timeframe,
            timestamp=s.timestamp.isoformat(),
        )
        for s in signals
    ]


@router.get("/portfolio-health", response_model=PortfolioHealthResponse)
async def get_portfolio_health(
    symbols: list[str] = Query(default=DEFAULT_SYMBOLS, description="Portfolio symbols to analyze"),
):
    """Get overall portfolio health assessment for lazy investors."""
    advisor = LazyInvestorMLAdvisor()
    health = await advisor.get_portfolio_health_score(symbols)

    return PortfolioHealthResponse(**health)


@router.get("/daily-briefing", response_model=DailyBriefingResponse)
async def get_daily_briefing(
    symbols: list[str] = Query(default=DEFAULT_SYMBOLS, description="Portfolio symbols for briefing"),
):
    """
    Get daily investment briefing tailored for passive investors.

    Provides human-readable market insights without requiring active trading decisions.
    """
    advisor = LazyInvestorMLAdvisor()

    # Generate briefing and health assessment concurrently
    briefing_task = advisor.generate_daily_briefing(symbols)
    health_task = advisor.get_portfolio_health_score(symbols)

    briefing_text = await briefing_task
    health_data = await health_task

    # Get signals for completeness
    signals = await advisor.generate_investment_signals(symbols)
    signals_response = [
        InvestmentSignalResponse(
            symbol=s.symbol,
            signal_type=s.signal_type,
            confidence_level=s.confidence_level,
            rationale=s.rationale,
            suggested_action=s.suggested_action,
            timeframe=s.timeframe,
            timestamp=s.timestamp.isoformat(),
        )
        for s in signals
    ]

    return DailyBriefingResponse(
        briefing_text=briefing_text, portfolio_health=PortfolioHealthResponse(**health_data), signals=signals_response
    )


@router.get("/strategy-recommendation")
async def get_strategy_recommendation(
    risk_tolerance: str = Query(default="moderate", enum=["conservative", "moderate", "aggressive"]),
    investment_horizon: str = Query(default="long_term", enum=["short_term", "medium_term", "long_term"]),
):
    """
    Get personalized lazy investor strategy recommendation.

    Based on risk tolerance and investment horizon.
    """

    strategies = {
        "conservative": {
            "description": "Capital preservation focused",
            "allocation": "70% stablecoins/ETFs, 20% blue-chip crypto, 10% emerging projects",
            "approach": "Monthly rebalancing, ignore daily volatility",
            "signal_response": "Only act on high-confidence (>80%) risk warnings",
        },
        "moderate": {
            "description": "Balanced growth approach",
            "allocation": "50% established crypto, 30% stable positions, 20% opportunistic",
            "approach": "Quarterly rebalancing, dollar-cost averaging",
            "signal_response": "Monitor medium+ confidence signals, act on strong consensus",
        },
        "aggressive": {
            "description": "Growth-oriented with risk awareness",
            "allocation": "70% crypto exposure, 20% volatile pairs, 10% experimental",
            "approach": "Monthly portfolio review, tactical positioning",
            "signal_response": "Act on medium+ confidence opportunities, hedge against risks",
        },
    }

    strategy = strategies.get(risk_tolerance, strategies["moderate"])

    return {
        "risk_profile": risk_tolerance,
        "investment_horizon": investment_horizon,
        "recommended_strategy": strategy,
        "ml_integration": {
            "purpose": "Market awareness, not timing",
            "threshold": "Only high-confidence signals (>70%) trigger review",
            "frequency": "Weekly signal assessment, monthly portfolio review",
            "action_bias": "Conservative - preserve capital first, seek growth second",
        },
        "timestamp": datetime.now().isoformat(),
    }
