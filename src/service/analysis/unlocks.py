"""
Token Unlock Tracker.

Tracks major token unlock events:
- ARB, APT, OP, SUI, SEI, TIA, JUP, W, STRK
- Alert before large unlocks

Помогает отслеживать:
- Предстоящие разлоки токенов
- Потенциальное давление продаж
- Риск удержания позиций перед разлоком
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class UnlockRisk(Enum):
    """Unlock risk level."""

    LOW = "low"  # < $10M or > 30 days
    MEDIUM = "medium"  # $10-50M or 7-30 days
    HIGH = "high"  # > $50M in < 7 days

    @property
    def name_ru(self) -> str:
        names = {
            UnlockRisk.LOW: "Низкий",
            UnlockRisk.MEDIUM: "Средний",
            UnlockRisk.HIGH: "Высокий",
        }
        return names.get(self, self.value)

    @property
    def emoji(self) -> str:
        emojis = {
            UnlockRisk.LOW: "🟢",
            UnlockRisk.MEDIUM: "🟡",
            UnlockRisk.HIGH: "🔴",
        }
        return emojis.get(self, "⚪")


@dataclass
class TokenUnlock:
    """Single token unlock event."""

    token: str
    unlock_date: datetime
    amount: float
    value_usd: float
    percent_of_supply: float
    unlock_type: str  # cliff, linear, team, etc.
    source: str

    @property
    def days_until(self) -> int:
        return max(0, (self.unlock_date - datetime.now()).days)

    @property
    def is_upcoming(self) -> bool:
        return self.days_until <= 7

    @property
    def risk(self) -> UnlockRisk:
        if self.value_usd >= 50_000_000 and self.days_until <= 7:
            return UnlockRisk.HIGH
        if self.value_usd >= 10_000_000 and self.days_until <= 30:
            return UnlockRisk.MEDIUM
        return UnlockRisk.LOW

    def to_dict(self) -> dict[str, Any]:
        return {
            "token": self.token,
            "unlock_date": self.unlock_date.isoformat(),
            "unlock_date_str": self.unlock_date.strftime("%Y-%m-%d"),
            "days_until": self.days_until,
            "amount": self.amount,
            "amount_formatted": self._format_amount(self.amount),
            "value_usd": self.value_usd,
            "value_formatted": self._format_usd(self.value_usd),
            "percent_of_supply": round(self.percent_of_supply, 2),
            "unlock_type": self.unlock_type,
            "source": self.source,
            "risk": self.risk.value,
            "risk_ru": self.risk.name_ru,
            "risk_emoji": self.risk.emoji,
            "is_upcoming": self.is_upcoming,
            "summary": f"{self.token}: {self._format_usd(self.value_usd)} in {self.days_until} days",
            "summary_ru": f"{self.token}: {self._format_usd(self.value_usd)} через {self.days_until} дн.",
        }

    def _format_amount(self, amount: float) -> str:
        if amount >= 1_000_000_000:
            return f"{amount / 1_000_000_000:.2f}B"
        if amount >= 1_000_000:
            return f"{amount / 1_000_000:.2f}M"
        if amount >= 1_000:
            return f"{amount / 1_000:.1f}K"
        return f"{amount:.0f}"

    def _format_usd(self, value: float) -> str:
        if value >= 1_000_000_000:
            return f"${value / 1_000_000_000:.2f}B"
        if value >= 1_000_000:
            return f"${value / 1_000_000:.1f}M"
        if value >= 1_000:
            return f"${value / 1_000:.0f}K"
        return f"${value:.0f}"


@dataclass
class UnlockAnalysis:
    """Token unlock analysis."""

    timestamp: datetime
    unlocks: list[TokenUnlock] = field(default_factory=list)
    next_7d_count: int = 0
    next_7d_value: float = 0
    highest_risk: UnlockRisk = UnlockRisk.LOW
    next_event: TokenUnlock | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "unlocks": [u.to_dict() for u in self.unlocks],
            "total_count": len(self.unlocks),
            "next_7d_count": self.next_7d_count,
            "next_7d_value": self.next_7d_value,
            "next_7d_value_formatted": self._format_usd(self.next_7d_value),
            "highest_risk": self.highest_risk.value,
            "highest_risk_ru": self.highest_risk.name_ru,
            "highest_risk_emoji": self.highest_risk.emoji,
            "next_event": self.next_event.to_dict() if self.next_event else None,
            "summary": self._get_summary(),
            "summary_ru": self._get_summary_ru(),
        }

    def _format_usd(self, value: float) -> str:
        if value >= 1_000_000_000:
            return f"${value / 1_000_000_000:.2f}B"
        if value >= 1_000_000:
            return f"${value / 1_000_000:.1f}M"
        return f"${value / 1_000:.0f}K"

    def _get_summary(self) -> str:
        if self.next_event:
            return f"Next: {self.next_event.token} in {self.next_event.days_until} days"
        return "No upcoming unlocks"

    def _get_summary_ru(self) -> str:
        if self.next_event:
            return f"След.: {self.next_event.token} через {self.next_event.days_until} дн."
        return "Нет предстоящих разлоков"


class UnlockTracker:
    """
    Token unlock tracking service.

    Tracks scheduled token unlocks for major altcoins.
    Uses a combination of known schedules and API data.
    """

    # Known unlock schedules (manually maintained)
    # Format: token -> list of (date, amount, percent, type)
    # These are examples - in production would fetch from API
    UNLOCK_SCHEDULES: dict[str, list[dict]] = {
        "ARB": [
            {
                "date": "2025-03-16",
                "amount": 92_650_000,
                "percent": 0.93,
                "value_usd": 80_000_000,
                "type": "Team & Investors",
            },
        ],
        "APT": [
            {
                "date": "2025-02-12",
                "amount": 11_310_000,
                "percent": 0.89,
                "value_usd": 120_000_000,
                "type": "Investors",
            },
        ],
        "OP": [
            {
                "date": "2025-01-31",
                "amount": 31_340_000,
                "percent": 1.43,
                "value_usd": 55_000_000,
                "type": "Core Contributors",
            },
        ],
        "SUI": [
            {
                "date": "2025-02-01",
                "amount": 64_190_000,
                "percent": 0.64,
                "value_usd": 250_000_000,
                "type": "Investors & Team",
            },
        ],
        "SEI": [
            {
                "date": "2025-02-15",
                "amount": 55_560_000,
                "percent": 1.32,
                "value_usd": 25_000_000,
                "type": "Ecosystem",
            },
        ],
        "TIA": [
            {
                "date": "2025-02-28",
                "amount": 8_330_000,
                "percent": 1.67,
                "value_usd": 35_000_000,
                "type": "R&D",
            },
        ],
        "JUP": [
            {
                "date": "2025-02-17",
                "amount": 127_000_000,
                "percent": 1.27,
                "value_usd": 95_000_000,
                "type": "Ecosystem",
            },
        ],
        "STRK": [
            {
                "date": "2025-02-15",
                "amount": 64_000_000,
                "percent": 0.64,
                "value_usd": 30_000_000,
                "type": "Early Contributors",
            },
        ],
    }

    def __init__(self):
        pass

    async def analyze(self) -> UnlockAnalysis:
        """
        Analyze upcoming token unlocks.

        Returns:
            UnlockAnalysis with all upcoming unlocks
        """
        unlocks = self._get_scheduled_unlocks()

        # Sort by date
        unlocks.sort(key=lambda x: x.unlock_date)

        # Filter to upcoming (next 90 days)
        cutoff = datetime.now() + timedelta(days=90)
        unlocks = [u for u in unlocks if u.unlock_date <= cutoff]

        # Calculate stats
        next_7d = [u for u in unlocks if u.days_until <= 7]
        next_7d_count = len(next_7d)
        next_7d_value = sum(u.value_usd for u in next_7d)

        # Highest risk
        highest_risk = UnlockRisk.LOW
        for unlock in unlocks:
            if unlock.risk == UnlockRisk.HIGH:
                highest_risk = UnlockRisk.HIGH
                break
            if unlock.risk == UnlockRisk.MEDIUM and highest_risk != UnlockRisk.HIGH:
                highest_risk = UnlockRisk.MEDIUM

        # Next event
        next_event = unlocks[0] if unlocks else None

        return UnlockAnalysis(
            timestamp=datetime.now(),
            unlocks=unlocks,
            next_7d_count=next_7d_count,
            next_7d_value=next_7d_value,
            highest_risk=highest_risk,
            next_event=next_event,
        )

    def _get_scheduled_unlocks(self) -> list[TokenUnlock]:
        """Get all scheduled unlocks from known data."""
        unlocks = []

        for token, schedules in self.UNLOCK_SCHEDULES.items():
            for schedule in schedules:
                try:
                    unlock_date = datetime.strptime(schedule["date"], "%Y-%m-%d")

                    # Skip past unlocks
                    if unlock_date < datetime.now():
                        continue

                    unlocks.append(
                        TokenUnlock(
                            token=token,
                            unlock_date=unlock_date,
                            amount=schedule["amount"],
                            value_usd=schedule["value_usd"],
                            percent_of_supply=schedule["percent"],
                            unlock_type=schedule["type"],
                            source="schedule",
                        )
                    )
                except Exception as e:
                    logger.warning(f"Failed to parse unlock for {token}: {e}")

        return unlocks

    async def get_by_token(self, token: str) -> list[TokenUnlock]:
        """Get unlocks for a specific token."""
        analysis = await self.analyze()
        return [u for u in analysis.unlocks if u.token.upper() == token.upper()]

    async def get_high_risk(self) -> list[TokenUnlock]:
        """Get high-risk upcoming unlocks."""
        analysis = await self.analyze()
        return [u for u in analysis.unlocks if u.risk == UnlockRisk.HIGH]


# Global instance
_unlock_tracker: UnlockTracker | None = None


def get_unlock_tracker() -> UnlockTracker:
    """Get global unlock tracker instance."""
    global _unlock_tracker
    if _unlock_tracker is None:
        _unlock_tracker = UnlockTracker()
    return _unlock_tracker
