"""Lazy Investor API schemas."""

from pydantic import BaseModel


class InvestmentSignalResponse(BaseModel):
    """Investment signal response."""

    symbol: str
    signal_type: str
    confidence_level: str
    rationale: str
    suggested_action: str
    timeframe: str
    timestamp: str


class PortfolioHealthResponse(BaseModel):
    """Portfolio health response for lazy investor."""

    portfolio_sentiment: str
    opportunity_signals: int
    risk_signals: int
    hold_signals: int
    total_analyzed: int
    recommendation: str
    timestamp: str


class DailyBriefingResponse(BaseModel):
    """Daily briefing response."""

    briefing_text: str
    portfolio_health: PortfolioHealthResponse
    signals: list[InvestmentSignalResponse]
