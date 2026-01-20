"""
Macro Economic Calendar.

Tracks major economic events affecting crypto:
- FOMC meetings (Fed rate decisions)
- CPI releases
- Employment reports (NFP)
- GDP releases
- PCE inflation

Помогает отслеживать:
- Предстоящие макро-события
- Риск волатильности перед событиями
- Дни до следующего заседания FOMC
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Macro event types."""

    FOMC = "fomc"
    CPI = "cpi"
    NFP = "nfp"  # Non-Farm Payrolls
    GDP = "gdp"
    PCE = "pce"
    UNEMPLOYMENT = "unemployment"
    OTHER = "other"

    @property
    def name_ru(self) -> str:
        names = {
            EventType.FOMC: "Заседание ФРС",
            EventType.CPI: "Индекс потреб. цен",
            EventType.NFP: "Занятость (NFP)",
            EventType.GDP: "ВВП",
            EventType.PCE: "Инфляция PCE",
            EventType.UNEMPLOYMENT: "Безработица",
            EventType.OTHER: "Другое",
        }
        return names.get(self, self.value)

    @property
    def impact(self) -> str:
        """Event impact level on crypto."""
        high_impact = {EventType.FOMC, EventType.CPI, EventType.NFP}
        return "high" if self in high_impact else "medium"


class MacroRisk(Enum):
    """Macro risk level for the week."""

    LOW = "low"  # No major events
    MEDIUM = "medium"  # 1-2 events
    HIGH = "high"  # FOMC week or multiple events

    @property
    def name_ru(self) -> str:
        names = {
            MacroRisk.LOW: "Низкий",
            MacroRisk.MEDIUM: "Средний",
            MacroRisk.HIGH: "Высокий",
        }
        return names.get(self, self.value)

    @property
    def emoji(self) -> str:
        return {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(self.value, "⚪")


@dataclass
class MacroEvent:
    """Single macro economic event."""

    event_type: EventType
    name: str
    date: datetime
    description: str = ""
    previous: str = ""
    forecast: str = ""
    is_rate_decision: bool = False

    @property
    def days_until(self) -> int:
        return max(0, (self.date - datetime.now()).days)

    @property
    def is_upcoming(self) -> bool:
        return self.days_until <= 7

    @property
    def is_today(self) -> bool:
        return self.date.date() == datetime.now().date()

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.event_type.value,
            "type_ru": self.event_type.name_ru,
            "name": self.name,
            "date": self.date.isoformat(),
            "date_str": self.date.strftime("%Y-%m-%d"),
            "time_str": self.date.strftime("%H:%M") if self.date.hour > 0 else "TBD",
            "days_until": self.days_until,
            "description": self.description,
            "previous": self.previous,
            "forecast": self.forecast,
            "is_rate_decision": self.is_rate_decision,
            "is_upcoming": self.is_upcoming,
            "is_today": self.is_today,
            "impact": self.event_type.impact,
            "summary": f"{self.event_type.name_ru} через {self.days_until} дн.",
        }


@dataclass
class MacroAnalysis:
    """Macro calendar analysis."""

    timestamp: datetime
    events: list[MacroEvent] = field(default_factory=list)
    days_to_fomc: int = 99
    week_risk: MacroRisk = MacroRisk.LOW
    next_event: MacroEvent | None = None
    fomc_dates: list[datetime] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "events": [e.to_dict() for e in self.events],
            "events_count": len(self.events),
            "days_to_fomc": self.days_to_fomc,
            "week_risk": self.week_risk.value,
            "week_risk_ru": self.week_risk.name_ru,
            "week_risk_emoji": self.week_risk.emoji,
            "next_event": self.next_event.to_dict() if self.next_event else None,
            "summary": self._get_summary(),
            "summary_ru": self._get_summary_ru(),
        }

    def _get_summary(self) -> str:
        if self.next_event and self.next_event.is_today:
            return f"TODAY: {self.next_event.event_type.name_ru}"
        if self.days_to_fomc <= 7:
            return f"FOMC in {self.days_to_fomc} days - expect volatility"
        if self.next_event:
            return f"Next: {self.next_event.event_type.name_ru} in {self.next_event.days_until} days"
        return "No major events upcoming"

    def _get_summary_ru(self) -> str:
        if self.next_event and self.next_event.is_today:
            return f"СЕГОДНЯ: {self.next_event.event_type.name_ru}"
        if self.days_to_fomc <= 7:
            return f"FOMC через {self.days_to_fomc} дн. - ожидайте волатильность"
        if self.next_event:
            return f"След.: {self.next_event.event_type.name_ru} через {self.next_event.days_until} дн."
        return "Нет предстоящих событий"


class MacroCalendar:
    """
    Macro economic calendar service.

    Tracks scheduled economic events and their impact on crypto.
    """

    # 2025 FOMC Meeting dates (actual dates)
    FOMC_DATES_2025 = [
        datetime(2025, 1, 28, 19, 0),  # Jan 28-29
        datetime(2025, 3, 18, 19, 0),  # Mar 18-19
        datetime(2025, 5, 6, 19, 0),  # May 6-7
        datetime(2025, 6, 17, 19, 0),  # Jun 17-18
        datetime(2025, 7, 29, 19, 0),  # Jul 29-30
        datetime(2025, 9, 16, 19, 0),  # Sep 16-17
        datetime(2025, 11, 4, 19, 0),  # Nov 4-5
        datetime(2025, 12, 16, 19, 0),  # Dec 16-17
    ]

    # Monthly CPI dates (usually around 12-14th of month)
    CPI_DATES_2025 = [
        datetime(2025, 1, 15, 13, 30),
        datetime(2025, 2, 12, 13, 30),
        datetime(2025, 3, 12, 13, 30),
        datetime(2025, 4, 10, 13, 30),
        datetime(2025, 5, 13, 13, 30),
        datetime(2025, 6, 11, 13, 30),
        datetime(2025, 7, 10, 13, 30),
        datetime(2025, 8, 12, 13, 30),
        datetime(2025, 9, 10, 13, 30),
        datetime(2025, 10, 14, 13, 30),
        datetime(2025, 11, 12, 13, 30),
        datetime(2025, 12, 10, 13, 30),
    ]

    # NFP dates (first Friday of month)
    NFP_DATES_2025 = [
        datetime(2025, 1, 10, 13, 30),
        datetime(2025, 2, 7, 13, 30),
        datetime(2025, 3, 7, 13, 30),
        datetime(2025, 4, 4, 13, 30),
        datetime(2025, 5, 2, 13, 30),
        datetime(2025, 6, 6, 13, 30),
        datetime(2025, 7, 3, 13, 30),
        datetime(2025, 8, 1, 13, 30),
        datetime(2025, 9, 5, 13, 30),
        datetime(2025, 10, 3, 13, 30),
        datetime(2025, 11, 7, 13, 30),
        datetime(2025, 12, 5, 13, 30),
    ]

    def __init__(self):
        pass

    async def analyze(self, days_ahead: int = 30) -> MacroAnalysis:
        """
        Analyze upcoming macro events.

        Args:
            days_ahead: How many days to look ahead

        Returns:
            MacroAnalysis with upcoming events
        """
        now = datetime.now()
        cutoff = now + timedelta(days=days_ahead)

        events = self._get_all_events(now, cutoff)

        # Sort by date
        events.sort(key=lambda x: x.date)

        # Calculate days to FOMC
        days_to_fomc = 99
        for date in self.FOMC_DATES_2025:
            if date > now:
                days_to_fomc = (date - now).days
                break

        # Calculate week risk
        week_events = [e for e in events if e.days_until <= 7]
        week_risk = self._calculate_week_risk(week_events, days_to_fomc)

        # Next event
        next_event = events[0] if events else None

        return MacroAnalysis(
            timestamp=now,
            events=events,
            days_to_fomc=days_to_fomc,
            week_risk=week_risk,
            next_event=next_event,
            fomc_dates=[d for d in self.FOMC_DATES_2025 if d > now],
        )

    def _get_all_events(self, start: datetime, end: datetime) -> list[MacroEvent]:
        """Get all macro events in date range."""
        events = []

        # FOMC meetings
        for date in self.FOMC_DATES_2025:
            if start <= date <= end:
                events.append(
                    MacroEvent(
                        event_type=EventType.FOMC,
                        name="FOMC Meeting",
                        date=date,
                        description="Federal Reserve rate decision",
                        is_rate_decision=True,
                    )
                )

        # CPI releases
        for date in self.CPI_DATES_2025:
            if start <= date <= end:
                events.append(
                    MacroEvent(
                        event_type=EventType.CPI,
                        name="CPI Release",
                        date=date,
                        description="Consumer Price Index (inflation)",
                    )
                )

        # NFP releases
        for date in self.NFP_DATES_2025:
            if start <= date <= end:
                events.append(
                    MacroEvent(
                        event_type=EventType.NFP,
                        name="Non-Farm Payrolls",
                        date=date,
                        description="Employment report",
                    )
                )

        return events

    def _calculate_week_risk(self, week_events: list[MacroEvent], days_to_fomc: int) -> MacroRisk:
        """Calculate risk level for the week."""
        # FOMC week is always high risk
        if days_to_fomc <= 7:
            return MacroRisk.HIGH

        # Check for high-impact events
        high_impact_count = sum(1 for e in week_events if e.event_type.impact == "high")

        if high_impact_count >= 2:
            return MacroRisk.HIGH
        if high_impact_count >= 1 or len(week_events) >= 2:
            return MacroRisk.MEDIUM

        return MacroRisk.LOW

    async def get_fomc_countdown(self) -> dict[str, Any]:
        """Get FOMC meeting countdown."""
        now = datetime.now()

        next_fomc = None
        for date in self.FOMC_DATES_2025:
            if date > now:
                next_fomc = date
                break

        if next_fomc:
            days = (next_fomc - now).days
            return {
                "next_fomc": next_fomc.isoformat(),
                "next_fomc_str": next_fomc.strftime("%Y-%m-%d"),
                "days_until": days,
                "is_this_week": days <= 7,
                "message": f"FOMC через {days} дней" if days > 0 else "FOMC сегодня!",
            }

        return {
            "next_fomc": None,
            "days_until": 99,
            "message": "Нет данных о FOMC",
        }


# Global instance
_macro_calendar: MacroCalendar | None = None


def get_macro_calendar() -> MacroCalendar:
    """Get global macro calendar instance."""
    global _macro_calendar
    if _macro_calendar is None:
        _macro_calendar = MacroCalendar()
    return _macro_calendar
