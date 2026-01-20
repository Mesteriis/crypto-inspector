"""Goals API schemas."""

from pydantic import BaseModel


class MilestoneResponse(BaseModel):
    """Milestone response."""

    percentage: int
    label: str
    label_ru: str
    message: str
    message_ru: str
    reached: bool
    reached_at: str | None = None


class GoalProgressResponse(BaseModel):
    """Goal progress response."""

    name: str
    name_en: str
    name_ru: str
    target_value: float
    current_value: float
    remaining: float
    progress_percent: float
    days_to_goal: int | None
    status: str
    status_en: str
    status_ru: str
    milestone_message: str
    milestone_message_ru: str
    milestones: list[MilestoneResponse]
    emoji: str


class GoalConfigResponse(BaseModel):
    """Goal configuration response."""

    enabled: bool
    name: str
    name_ru: str
    target_value: float
    start_date: str | None = None
    target_date: str | None = None


class GoalUpdateRequest(BaseModel):
    """Goal update request."""

    name: str | None = None
    name_ru: str | None = None
    target_value: float | None = None
    target_date: str | None = None
