"""Summary API schemas."""

from typing import Any

from pydantic import BaseModel


class MarketPulseResponse(BaseModel):
    """Market pulse response."""

    sentiment: str
    sentiment_en: str
    sentiment_ru: str
    confidence: int
    reason: str
    reason_ru: str
    factors: list[str]
    factors_ru: list[str]


class PortfolioHealthResponse(BaseModel):
    """Portfolio health response."""

    status: str
    status_en: str
    status_ru: str
    score: int
    main_issue: str
    main_issue_ru: str
    metrics: dict[str, Any] | None = None


class TodayActionResponse(BaseModel):
    """Today's action response."""

    action: str
    action_en: str
    action_ru: str
    priority: str
    priority_en: str
    priority_ru: str
    details: str
    details_ru: str


class WeeklyOutlookResponse(BaseModel):
    """Weekly outlook response."""

    outlook: str
    outlook_en: str
    outlook_ru: str
    confidence: int
    key_events: list[str]
    key_events_ru: list[str]
    risk_factors: list[str]
    risk_factors_ru: list[str]
    opportunities: list[str]
    opportunities_ru: list[str]


class FullSummaryResponse(BaseModel):
    """Full summary with all components."""

    market_pulse: MarketPulseResponse
    portfolio_health: PortfolioHealthResponse
    today_action: TodayActionResponse
    weekly_outlook: WeeklyOutlookResponse
