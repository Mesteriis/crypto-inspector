"""AI API schemas."""

from pydantic import BaseModel


class AnalyzeRequest(BaseModel):
    """Request for AI analysis."""

    analysis_type: str = "daily_summary"  # daily_summary, weekly_report, opportunity, dca, risk, sentiment
    symbol: str | None = None  # For opportunity analysis
    language: str = "en"  # en or ru


class AnalysisResponse(BaseModel):
    """AI analysis response."""

    type: str
    content: str
    sentiment: str | None = None
    recommendation: str | None = None
    provider: str | None = None
    model: str | None = None
    timestamp: str | None = None
    language: str = "en"


class AIStatusResponse(BaseModel):
    """AI service status."""

    enabled: bool
    available: bool
    provider: str | None = None
    model: str | None = None
    last_analysis: str | None = None
    analysis_count: int = 0
