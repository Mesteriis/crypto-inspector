"""Briefing API schemas."""

from pydantic import BaseModel


class BriefingSectionResponse(BaseModel):
    """Briefing section response."""

    header: str
    header_en: str
    header_ru: str
    content: str
    content_en: str
    content_ru: str
    emoji: str


class BriefingResponse(BaseModel):
    """Briefing response."""

    type: str
    title: str
    title_en: str
    title_ru: str
    greeting: str
    greeting_en: str
    greeting_ru: str
    sections: list[BriefingSectionResponse]
    message: str  # Formatted message
    message_ru: str


class DigestResponse(BaseModel):
    """Daily digest response."""

    type: str
    title: str
    title_ru: str
    summary: str
    summary_ru: str
    total_alerts: int
    critical_count: int
    important_count: int
    info_count: int
    message: str
    message_ru: str


class NotificationStatsResponse(BaseModel):
    """Notification statistics response."""

    pending_total: int
    pending_critical: int
    pending_important: int
    pending_info: int
    sent_today: int
    digest_ready: bool
    current_mode: str
    current_mode_en: str
    current_mode_ru: str
