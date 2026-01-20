"""API request and response schemas."""

from schemas.api.ai import AIStatusResponse, AnalysisResponse, AnalyzeRequest
from schemas.api.alerts import CreateAlertRequest
from schemas.api.backfill import TriggerBackfillRequest
from schemas.api.briefing import (
    BriefingResponse,
    BriefingSectionResponse,
    DigestResponse,
    NotificationStatsResponse,
)
from schemas.api.goals import (
    GoalConfigResponse,
    GoalProgressResponse,
    GoalUpdateRequest,
    MilestoneResponse,
)
from schemas.api.lazy_investor import (
    DailyBriefingResponse,
    InvestmentSignalResponse,
)
from schemas.api.lazy_investor import (
    PortfolioHealthResponse as LazyPortfolioHealthResponse,
)
from schemas.api.portfolio import HoldingRequest
from schemas.api.signals import RecordSignalRequest
from schemas.api.summary import (
    FullSummaryResponse,
    MarketPulseResponse,
    PortfolioHealthResponse,
    TodayActionResponse,
    WeeklyOutlookResponse,
)

__all__ = [
    # AI
    "AnalyzeRequest",
    "AnalysisResponse",
    "AIStatusResponse",
    # Alerts
    "CreateAlertRequest",
    # Portfolio
    "HoldingRequest",
    # Goals
    "MilestoneResponse",
    "GoalProgressResponse",
    "GoalConfigResponse",
    "GoalUpdateRequest",
    # Signals
    "RecordSignalRequest",
    # Briefing
    "BriefingSectionResponse",
    "BriefingResponse",
    "DigestResponse",
    "NotificationStatsResponse",
    # Summary
    "MarketPulseResponse",
    "PortfolioHealthResponse",
    "TodayActionResponse",
    "WeeklyOutlookResponse",
    "FullSummaryResponse",
    # Lazy Investor
    "InvestmentSignalResponse",
    "LazyPortfolioHealthResponse",
    "DailyBriefingResponse",
    # Backfill
    "TriggerBackfillRequest",
]
