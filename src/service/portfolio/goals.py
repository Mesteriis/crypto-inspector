"""
Goal Tracking Service.

Provides personal financial target tracking with visual progress,
milestone celebrations, and time-to-goal estimates.
All output is bilingual (English/Russian).
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

logger = logging.getLogger(__name__)


# =============================================================================
# Translation Dictionaries
# =============================================================================

STATUSES = {
    "not_started": {"en": "Not Started", "ru": "Не начата"},
    "in_progress": {"en": "In Progress", "ru": "В процессе"},
    "on_track": {"en": "On Track", "ru": "По плану"},
    "ahead": {"en": "Ahead of Schedule", "ru": "Опережает план"},
    "behind": {"en": "Behind Schedule", "ru": "Отстаёт от плана"},
    "achieved": {"en": "Achieved!", "ru": "Достигнута!"},
    "paused": {"en": "Paused", "ru": "Приостановлена"},
}

MILESTONES = {
    "10%": {"en": "10% - Great Start!", "ru": "10% - Отличное начало!"},
    "25%": {"en": "25% - Quarter Way!", "ru": "25% - Четверть пути!"},
    "50%": {"en": "50% - Halfway There!", "ru": "50% - На полпути!"},
    "75%": {"en": "75% - Almost There!", "ru": "75% - Почти готово!"},
    "90%": {"en": "90% - Final Stretch!", "ru": "90% - Финишная прямая!"},
    "100%": {"en": "100% - Goal Achieved!", "ru": "100% - Цель достигнута!"},
}

MILESTONE_MESSAGES = {
    "10%": {
        "en": "You've made a great start! Keep building momentum.",
        "ru": "Отличное начало! Продолжайте набирать обороты.",
    },
    "25%": {
        "en": "A quarter of the way there! You're making real progress.",
        "ru": "Четверть пути пройдена! Вы делаете реальный прогресс.",
    },
    "50%": {
        "en": "Halfway to your goal! This is a major milestone.",
        "ru": "Половина пути к цели! Это важная веха.",
    },
    "75%": {
        "en": "Three quarters complete! The finish line is in sight.",
        "ru": "Три четверти выполнено! Финиш уже виден.",
    },
    "90%": {
        "en": "90% done! You're in the final stretch now.",
        "ru": "90% выполнено! Вы на финишной прямой.",
    },
    "100%": {
        "en": "Congratulations! You've achieved your financial goal!",
        "ru": "Поздравляем! Вы достигли своей финансовой цели!",
    },
}

ENCOURAGEMENTS = {
    "start": {
        "en": "Every journey begins with a single step. You've taken yours!",
        "ru": "Каждый путь начинается с первого шага. Вы его сделали!",
    },
    "progress": {
        "en": "Consistency is key. Keep up the great work!",
        "ru": "Последовательность - ключ к успеху. Продолжайте в том же духе!",
    },
    "slow": {
        "en": "Progress might be slow, but you're still moving forward.",
        "ru": "Прогресс может быть медленным, но вы всё ещё двигаетесь вперёд.",
    },
    "fast": {
        "en": "Amazing pace! You're ahead of schedule!",
        "ru": "Потрясающий темп! Вы опережаете план!",
    },
    "achieved": {
        "en": "Goal achieved! Time to celebrate and set new targets!",
        "ru": "Цель достигнута! Время отпраздновать и поставить новые цели!",
    },
}

TIME_ESTIMATES = {
    "days": {"en": "days", "ru": "дней"},
    "weeks": {"en": "weeks", "ru": "недель"},
    "months": {"en": "months", "ru": "месяцев"},
    "years": {"en": "years", "ru": "лет"},
    "unknown": {"en": "Unknown", "ru": "Неизвестно"},
    "achieved": {"en": "Already achieved!", "ru": "Уже достигнуто!"},
    "never": {"en": "At current rate: not achievable", "ru": "При текущем темпе: недостижимо"},
}


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class Milestone:
    """Milestone data."""

    percentage: int
    label: str
    label_ru: str
    message: str
    message_ru: str
    reached: bool
    reached_at: datetime | None = None

    def to_dict(self, lang: str = "en") -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "percentage": self.percentage,
            "label": self.label if lang == "en" else self.label_ru,
            "label_en": self.label,
            "label_ru": self.label_ru,
            "message": self.message if lang == "en" else self.message_ru,
            "message_en": self.message,
            "message_ru": self.message_ru,
            "reached": self.reached,
            "reached_at": self.reached_at.isoformat() if self.reached_at else None,
        }


@dataclass
class PortfolioGoal:
    """Portfolio goal with progress tracking."""

    name: str
    name_ru: str
    target_value: Decimal
    current_value: Decimal
    start_value: Decimal
    progress_percent: float
    days_to_goal: int | None
    status: str
    status_en: str
    status_ru: str
    milestone_message: str
    milestone_message_ru: str
    milestones: list[Milestone]
    start_date: datetime
    target_date: datetime | None = None
    emoji: str = "🎯"

    def to_dict(self, lang: str = "en") -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name if lang == "en" else self.name_ru,
            "name_en": self.name,
            "name_ru": self.name_ru,
            "target_value": float(self.target_value),
            "current_value": float(self.current_value),
            "start_value": float(self.start_value),
            "remaining": float(self.target_value - self.current_value),
            "progress_percent": round(self.progress_percent, 1),
            "days_to_goal": self.days_to_goal,
            "status": self.status,
            "status_en": self.status_en,
            "status_ru": self.status_ru,
            "milestone_message": self.milestone_message if lang == "en" else self.milestone_message_ru,
            "milestone_message_en": self.milestone_message,
            "milestone_message_ru": self.milestone_message_ru,
            "milestones": [m.to_dict(lang) for m in self.milestones],
            "start_date": self.start_date.isoformat(),
            "target_date": self.target_date.isoformat() if self.target_date else None,
            "emoji": self.emoji,
        }


@dataclass
class GoalHistory:
    """Historical value entry for goal tracking."""

    timestamp: datetime
    value: Decimal
    note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "value": float(self.value),
            "note": self.note,
        }


# =============================================================================
# Goal Tracker Service
# =============================================================================


class GoalTracker:
    """
    Service for tracking portfolio goals and milestones.

    Features:
    - Progress calculation with visual indicators
    - Time-to-goal estimation based on historical rate
    - Milestone tracking (10%, 25%, 50%, 75%, 90%, 100%)
    - Encouragement messages based on progress
    - Bilingual output (EN/RU)
    """

    MILESTONE_PERCENTAGES = [10, 25, 50, 75, 90, 100]

    def __init__(
        self,
        goal_name: str = "Financial Freedom",
        goal_name_ru: str = "Финансовая свобода",
        target_value: Decimal = Decimal("100000"),
        start_value: Decimal = Decimal("0"),
        start_date: datetime | None = None,
        target_date: datetime | None = None,
    ):
        self.goal_name = goal_name
        self.goal_name_ru = goal_name_ru
        self.target_value = target_value
        self.start_value = start_value
        self.start_date = start_date or datetime.now(UTC)
        self.target_date = target_date

        self.history: list[GoalHistory] = []
        self.reached_milestones: set[int] = set()
        self._last_check: datetime | None = None

    def update_config(
        self,
        goal_name: str | None = None,
        goal_name_ru: str | None = None,
        target_value: Decimal | None = None,
    ) -> None:
        """Update goal configuration."""
        if goal_name:
            self.goal_name = goal_name
        if goal_name_ru:
            self.goal_name_ru = goal_name_ru
        if target_value:
            self.target_value = target_value

    def record_value(self, value: Decimal, note: str | None = None) -> None:
        """Record current portfolio value."""
        entry = GoalHistory(
            timestamp=datetime.now(UTC),
            value=value,
            note=note,
        )
        self.history.append(entry)

        # Keep history manageable (last 365 entries)
        if len(self.history) > 365:
            self.history = self.history[-365:]

    async def calculate_progress(self, current_value: Decimal) -> PortfolioGoal:
        """Calculate goal progress and generate report."""
        # Calculate progress percentage
        if self.target_value <= self.start_value:
            progress_percent = 100.0
        else:
            total_needed = float(self.target_value - self.start_value)
            current_progress = float(current_value - self.start_value)
            progress_percent = (current_progress / total_needed) * 100 if total_needed > 0 else 0

        progress_percent = max(0, min(100, progress_percent))

        # Determine status
        status, status_en, status_ru = self._determine_status(progress_percent, current_value)

        # Calculate time to goal
        days_to_goal = await self.estimate_time_to_goal(current_value)

        # Check milestones
        milestones = self._generate_milestones(progress_percent)
        await self.check_milestones(progress_percent)  # Side effect: updates reached_milestones

        # Get current milestone message
        milestone_msg, milestone_msg_ru = self._get_current_milestone_message(progress_percent)

        goal = PortfolioGoal(
            name=self.goal_name,
            name_ru=self.goal_name_ru,
            target_value=self.target_value,
            current_value=current_value,
            start_value=self.start_value,
            progress_percent=progress_percent,
            days_to_goal=days_to_goal,
            status=status,
            status_en=status_en,
            status_ru=status_ru,
            milestone_message=milestone_msg,
            milestone_message_ru=milestone_msg_ru,
            milestones=milestones,
            start_date=self.start_date,
            target_date=self.target_date,
            emoji=self._get_progress_emoji(progress_percent),
        )

        self._last_check = datetime.now(UTC)
        return goal

    async def estimate_time_to_goal(self, current_value: Decimal) -> int | None:
        """Estimate days to reach goal based on historical growth rate."""
        if current_value >= self.target_value:
            return 0

        if len(self.history) < 7:
            # Not enough history, use simple estimate if we have target date
            if self.target_date:
                days_remaining = (self.target_date - datetime.now(UTC)).days
                return max(0, days_remaining)
            return None

        # Calculate average daily growth from history
        recent_history = self.history[-30:]  # Last 30 entries
        if len(recent_history) < 2:
            return None

        first_entry = recent_history[0]
        last_entry = recent_history[-1]

        days_elapsed = (last_entry.timestamp - first_entry.timestamp).days
        if days_elapsed <= 0:
            return None

        value_change = float(last_entry.value - first_entry.value)
        daily_growth = value_change / days_elapsed

        if daily_growth <= 0:
            # Not growing, can't estimate
            return None

        remaining = float(self.target_value - current_value)
        days_needed = int(remaining / daily_growth)

        return max(1, days_needed)

    async def check_milestones(self, progress_percent: float) -> list[str]:
        """Check for newly reached milestones."""
        new_milestones = []

        for pct in self.MILESTONE_PERCENTAGES:
            if progress_percent >= pct and pct not in self.reached_milestones:
                self.reached_milestones.add(pct)
                new_milestones.append(f"{pct}%")
                logger.info(f"Goal milestone reached: {pct}%")

        return new_milestones

    def _determine_status(self, progress: float, current_value: Decimal) -> tuple[str, str, str]:
        """Determine goal status based on progress and expected pace."""
        if current_value >= self.target_value:
            return "achieved", STATUSES["achieved"]["en"], STATUSES["achieved"]["ru"]

        if progress == 0:
            return "not_started", STATUSES["not_started"]["en"], STATUSES["not_started"]["ru"]

        # If we have a target date, compare expected vs actual progress
        if self.target_date:
            days_total = (self.target_date - self.start_date).days
            days_elapsed = (datetime.now(UTC) - self.start_date).days

            if days_total > 0 and days_elapsed > 0:
                expected_progress = (days_elapsed / days_total) * 100

                if progress >= expected_progress + 10:
                    return "ahead", STATUSES["ahead"]["en"], STATUSES["ahead"]["ru"]
                elif progress >= expected_progress - 10:
                    return "on_track", STATUSES["on_track"]["en"], STATUSES["on_track"]["ru"]
                else:
                    return "behind", STATUSES["behind"]["en"], STATUSES["behind"]["ru"]

        return "in_progress", STATUSES["in_progress"]["en"], STATUSES["in_progress"]["ru"]

    def _generate_milestones(self, current_progress: float) -> list[Milestone]:
        """Generate milestone list with current status."""
        milestones = []

        for pct in self.MILESTONE_PERCENTAGES:
            key = f"{pct}%"
            reached = current_progress >= pct

            milestone = Milestone(
                percentage=pct,
                label=MILESTONES.get(key, {"en": key})["en"],
                label_ru=MILESTONES.get(key, {"ru": key})["ru"],
                message=MILESTONE_MESSAGES.get(key, {"en": ""})["en"],
                message_ru=MILESTONE_MESSAGES.get(key, {"ru": ""})["ru"],
                reached=reached,
                reached_at=None,  # Would need to track this separately
            )
            milestones.append(milestone)

        return milestones

    def _get_current_milestone_message(self, progress: float) -> tuple[str, str]:
        """Get encouragement message based on current progress."""
        if progress >= 100:
            return ENCOURAGEMENTS["achieved"]["en"], ENCOURAGEMENTS["achieved"]["ru"]

        if progress >= 75:
            key = "90%"
        elif progress >= 50:
            key = "75%"
        elif progress >= 25:
            key = "50%"
        elif progress >= 10:
            key = "25%"
        elif progress > 0:
            return ENCOURAGEMENTS["start"]["en"], ENCOURAGEMENTS["start"]["ru"]
        else:
            return ENCOURAGEMENTS["start"]["en"], ENCOURAGEMENTS["start"]["ru"]

        return MILESTONE_MESSAGES[key]["en"], MILESTONE_MESSAGES[key]["ru"]

    def _get_progress_emoji(self, progress: float) -> str:
        """Get emoji based on progress."""
        if progress >= 100:
            return "🏆"
        elif progress >= 75:
            return "🌟"
        elif progress >= 50:
            return "🚀"
        elif progress >= 25:
            return "📈"
        elif progress > 0:
            return "🌱"
        else:
            return "🎯"

    def format_time_estimate(self, days: int | None, lang: str = "en") -> str:
        """Format time estimate in human-readable form."""
        if days is None:
            return TIME_ESTIMATES["unknown"][lang]

        if days == 0:
            return TIME_ESTIMATES["achieved"][lang]

        if days < 0:
            return TIME_ESTIMATES["never"][lang]

        if days < 7:
            return f"{days} {TIME_ESTIMATES['days'][lang]}"
        elif days < 30:
            weeks = days // 7
            return f"{weeks} {TIME_ESTIMATES['weeks'][lang]}"
        elif days < 365:
            months = days // 30
            return f"{months} {TIME_ESTIMATES['months'][lang]}"
        else:
            years = days / 365
            return f"{years:.1f} {TIME_ESTIMATES['years'][lang]}"

    def format_sensor_attributes(self, current_value: Decimal) -> dict[str, Any]:
        """Format data for Home Assistant sensor attributes."""
        # Calculate basic progress
        if self.target_value <= self.start_value:
            progress_percent = 100.0
        else:
            total_needed = float(self.target_value - self.start_value)
            current_progress = float(current_value - self.start_value)
            progress_percent = (current_progress / total_needed) * 100 if total_needed > 0 else 0

        progress_percent = max(0, min(100, progress_percent))
        remaining = max(Decimal("0"), self.target_value - current_value)

        status, status_en, status_ru = self._determine_status(progress_percent, current_value)
        emoji = self._get_progress_emoji(progress_percent)

        # Get milestone message
        milestone_msg, milestone_msg_ru = self._get_current_milestone_message(progress_percent)

        return {
            "goal_name": self.goal_name,
            "goal_name_ru": self.goal_name_ru,
            "goal_target": float(self.target_value),
            "goal_current": float(current_value),
            "goal_remaining": float(remaining),
            "goal_progress": round(progress_percent, 1),
            "goal_status": status,
            "goal_status_en": status_en,
            "goal_status_ru": status_ru,
            "goal_emoji": emoji,
            "milestone_message": milestone_msg,
            "milestone_message_ru": milestone_msg_ru,
            "start_date": self.start_date.isoformat(),
            "target_date": self.target_date.isoformat() if self.target_date else None,
            "milestones_reached": list(self.reached_milestones),
            "next_milestone": self._get_next_milestone(progress_percent),
        }

    def _get_next_milestone(self, progress: float) -> int | None:
        """Get the next milestone percentage to reach."""
        for pct in self.MILESTONE_PERCENTAGES:
            if progress < pct:
                return pct
        return None


# =============================================================================
# Factory Function
# =============================================================================


def create_goal_tracker_from_config(config: dict[str, Any]) -> GoalTracker:
    """Create GoalTracker from configuration dictionary."""
    return GoalTracker(
        goal_name=config.get("goal_name", "Financial Freedom"),
        goal_name_ru=config.get("goal_name_ru", "Финансовая свобода"),
        target_value=Decimal(str(config.get("goal_target_value", 100000))),
        start_value=Decimal(str(config.get("goal_start_value", 0))),
        target_date=(datetime.fromisoformat(config["goal_target_date"]) if config.get("goal_target_date") else None),
    )
