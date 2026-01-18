"""
Smart Notification Manager Service.

Provides intelligent alert prioritization with daily digests and weekly summaries.
All output is bilingual (English/Russian).
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# =============================================================================
# Enums and Constants
# =============================================================================


class AlertPriority(Enum):
    """Alert priority levels."""

    CRITICAL = "critical"  # Immediate push notification
    IMPORTANT = "important"  # Daily digest
    INFO = "info"  # Weekly summary


class AlertCategory(Enum):
    """Alert categories for grouping."""

    PRICE = "price"
    RISK = "risk"
    OPPORTUNITY = "opportunity"
    WHALE = "whale"
    PORTFOLIO = "portfolio"
    GOAL = "goal"
    SYSTEM = "system"
    INFO = "info"


class NotificationMode(Enum):
    """Notification delivery modes."""

    ALL = "all"  # Send all notifications immediately
    SMART = "smart"  # Use priority-based filtering
    DIGEST_ONLY = "digest_only"  # Only daily digests
    CRITICAL_ONLY = "critical_only"  # Only critical alerts
    SILENT = "silent"  # No notifications


# =============================================================================
# Translation Dictionaries
# =============================================================================

PRIORITIES = {
    "critical": {"en": "Critical", "ru": "Критический"},
    "important": {"en": "Important", "ru": "Важный"},
    "info": {"en": "Informational", "ru": "Информационный"},
}

CATEGORIES = {
    "price": {"en": "Price Alert", "ru": "Ценовое оповещение"},
    "risk": {"en": "Risk Alert", "ru": "Оповещение о риске"},
    "opportunity": {"en": "Opportunity", "ru": "Возможность"},
    "whale": {"en": "Whale Activity", "ru": "Активность китов"},
    "portfolio": {"en": "Portfolio", "ru": "Портфель"},
    "goal": {"en": "Goal Progress", "ru": "Прогресс цели"},
    "system": {"en": "System", "ru": "Система"},
    "info": {"en": "Information", "ru": "Информация"},
}

MODES = {
    "all": {"en": "All Notifications", "ru": "Все уведомления"},
    "smart": {"en": "Smart Mode", "ru": "Умный режим"},
    "digest_only": {"en": "Digest Only", "ru": "Только дайджест"},
    "critical_only": {"en": "Critical Only", "ru": "Только критические"},
    "silent": {"en": "Silent", "ru": "Без звука"},
}

DIGEST_HEADERS = {
    "morning": {
        "en": "Good morning! Here's your crypto digest:",
        "ru": "Доброе утро! Вот ваш крипто-дайджест:",
    },
    "evening": {
        "en": "Good evening! Here's your daily summary:",
        "ru": "Добрый вечер! Вот ваша дневная сводка:",
    },
    "daily": {
        "en": "Daily Crypto Digest",
        "ru": "Ежедневный крипто-дайджест",
    },
    "weekly": {
        "en": "Weekly Crypto Summary",
        "ru": "Еженедельная крипто-сводка",
    },
}


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class SmartAlert:
    """Smart alert with bilingual support."""

    id: str
    title: str
    title_ru: str
    message: str
    message_ru: str
    priority: AlertPriority
    category: AlertCategory
    timestamp: datetime = field(default_factory=datetime.utcnow)
    value: Decimal | None = None
    symbol: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    sent: bool = False

    def to_dict(self, lang: str = "en") -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "id": self.id,
            "title": self.title if lang == "en" else self.title_ru,
            "title_en": self.title,
            "title_ru": self.title_ru,
            "message": self.message if lang == "en" else self.message_ru,
            "message_en": self.message,
            "message_ru": self.message_ru,
            "priority": self.priority.value,
            "priority_en": PRIORITIES[self.priority.value]["en"],
            "priority_ru": PRIORITIES[self.priority.value]["ru"],
            "category": self.category.value,
            "category_en": CATEGORIES[self.category.value]["en"],
            "category_ru": CATEGORIES[self.category.value]["ru"],
            "timestamp": self.timestamp.isoformat(),
            "value": float(self.value) if self.value else None,
            "symbol": self.symbol,
            "sent": self.sent,
        }


@dataclass
class DigestSection:
    """Section of a digest with bilingual content."""

    category: AlertCategory
    title: str
    title_ru: str
    alerts: list[SmartAlert]
    emoji: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "category": self.category.value,
            "title": self.title,
            "title_ru": self.title_ru,
            "emoji": self.emoji,
            "alert_count": len(self.alerts),
            "alerts": [a.to_dict() for a in self.alerts],
        }


@dataclass
class Digest:
    """Daily or weekly digest with bilingual support."""

    type: str  # "daily" or "weekly"
    title: str
    title_ru: str
    summary: str
    summary_ru: str
    sections: list[DigestSection]
    timestamp: datetime
    total_alerts: int
    critical_count: int
    important_count: int
    info_count: int

    def to_dict(self, lang: str = "en") -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": self.type,
            "title": self.title if lang == "en" else self.title_ru,
            "title_en": self.title,
            "title_ru": self.title_ru,
            "summary": self.summary if lang == "en" else self.summary_ru,
            "summary_en": self.summary,
            "summary_ru": self.summary_ru,
            "sections": [s.to_dict() for s in self.sections],
            "timestamp": self.timestamp.isoformat(),
            "total_alerts": self.total_alerts,
            "critical_count": self.critical_count,
            "important_count": self.important_count,
            "info_count": self.info_count,
        }

    def format_message(self, lang: str = "en") -> str:
        """Format digest as a notification message."""
        lines = []

        # Header
        title = self.title if lang == "en" else self.title_ru
        lines.append(f"📊 {title}")
        lines.append("")

        # Summary
        summary = self.summary if lang == "en" else self.summary_ru
        lines.append(summary)
        lines.append("")

        # Sections
        for section in self.sections:
            if not section.alerts:
                continue

            section_title = section.title if lang == "en" else section.title_ru
            lines.append(f"{section.emoji} {section_title} ({len(section.alerts)})")

            for alert in section.alerts[:3]:  # Limit to 3 per section
                msg = alert.message if lang == "en" else alert.message_ru
                lines.append(f"  • {msg}")

            if len(section.alerts) > 3:
                more = len(section.alerts) - 3
                more_text = f"... and {more} more" if lang == "en" else f"... и ещё {more}"
                lines.append(f"  {more_text}")

            lines.append("")

        return "\n".join(lines)


@dataclass
class NotificationStats:
    """Statistics for notifications."""

    pending_total: int
    pending_critical: int
    pending_important: int
    pending_info: int
    sent_today: int
    digest_ready: bool
    last_digest_time: datetime | None
    current_mode: NotificationMode

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pending_total": self.pending_total,
            "pending_critical": self.pending_critical,
            "pending_important": self.pending_important,
            "pending_info": self.pending_info,
            "sent_today": self.sent_today,
            "digest_ready": self.digest_ready,
            "last_digest_time": self.last_digest_time.isoformat() if self.last_digest_time else None,
            "current_mode": self.current_mode.value,
            "current_mode_en": MODES[self.current_mode.value]["en"],
            "current_mode_ru": MODES[self.current_mode.value]["ru"],
        }


# =============================================================================
# Category Emoji Mapping
# =============================================================================

CATEGORY_EMOJI = {
    AlertCategory.PRICE: "💰",
    AlertCategory.RISK: "⚠️",
    AlertCategory.OPPORTUNITY: "🎯",
    AlertCategory.WHALE: "🐋",
    AlertCategory.PORTFOLIO: "📁",
    AlertCategory.GOAL: "🏆",
    AlertCategory.SYSTEM: "⚙️",
    AlertCategory.INFO: "ℹ️",
}


# =============================================================================
# Notification Manager Service
# =============================================================================


class NotificationManager:
    """
    Smart notification manager with priority-based filtering.

    Features:
    - Priority-based alert filtering (Critical/Important/Info)
    - Daily digest aggregation
    - Weekly summary generation
    - Notification mode control
    - Bilingual output (EN/RU)
    """

    def __init__(self):
        self.pending_alerts: list[SmartAlert] = []
        self.sent_alerts: list[SmartAlert] = []
        self.mode = NotificationMode.SMART
        self.last_digest_time: datetime | None = None
        self.last_weekly_time: datetime | None = None
        self._alert_counter = 0

    def _generate_alert_id(self) -> str:
        """Generate unique alert ID."""
        self._alert_counter += 1
        return f"alert_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{self._alert_counter}"

    def set_mode(self, mode: NotificationMode) -> None:
        """Set notification mode."""
        self.mode = mode
        logger.info(f"Notification mode set to: {mode.value}")

    def create_alert(
        self,
        title: str,
        title_ru: str,
        message: str,
        message_ru: str,
        priority: AlertPriority,
        category: AlertCategory,
        value: Decimal | None = None,
        symbol: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SmartAlert:
        """Create a new smart alert."""
        alert = SmartAlert(
            id=self._generate_alert_id(),
            title=title,
            title_ru=title_ru,
            message=message,
            message_ru=message_ru,
            priority=priority,
            category=category,
            value=value,
            symbol=symbol,
            metadata=metadata or {},
        )
        return alert

    async def add_alert(self, alert: SmartAlert) -> bool:
        """
        Add alert and determine if it should be sent immediately.

        Returns True if alert should be sent now, False if added to digest.
        """
        self.pending_alerts.append(alert)

        should_send = await self.should_notify_now(alert)

        if should_send:
            alert.sent = True
            self.sent_alerts.append(alert)
            self.pending_alerts.remove(alert)

        return should_send

    async def should_notify_now(self, alert: SmartAlert) -> bool:
        """Determine if alert should be sent immediately based on mode and priority."""
        if self.mode == NotificationMode.SILENT:
            return False

        if self.mode == NotificationMode.ALL:
            return True

        if self.mode == NotificationMode.CRITICAL_ONLY:
            return alert.priority == AlertPriority.CRITICAL

        if self.mode == NotificationMode.DIGEST_ONLY:
            return False

        # Smart mode - only critical alerts sent immediately
        if self.mode == NotificationMode.SMART:
            return alert.priority == AlertPriority.CRITICAL

        return False

    async def add_to_digest(self, alert: SmartAlert) -> None:
        """Add alert directly to digest (skip immediate notification check)."""
        alert.sent = False
        self.pending_alerts.append(alert)

    def get_pending_by_priority(self, priority: AlertPriority) -> list[SmartAlert]:
        """Get pending alerts by priority level."""
        return [a for a in self.pending_alerts if a.priority == priority and not a.sent]

    def get_pending_by_category(self, category: AlertCategory) -> list[SmartAlert]:
        """Get pending alerts by category."""
        return [a for a in self.pending_alerts if a.category == category and not a.sent]

    async def get_daily_digest(self) -> Digest:
        """Generate daily digest from pending alerts."""
        unsent_alerts = [a for a in self.pending_alerts if not a.sent]

        # Count by priority
        critical_count = len([a for a in unsent_alerts if a.priority == AlertPriority.CRITICAL])
        important_count = len([a for a in unsent_alerts if a.priority == AlertPriority.IMPORTANT])
        info_count = len([a for a in unsent_alerts if a.priority == AlertPriority.INFO])

        # Group by category
        sections = []
        for category in AlertCategory:
            category_alerts = [a for a in unsent_alerts if a.category == category]
            if category_alerts:
                # Sort by priority (critical first) and timestamp
                category_alerts.sort(
                    key=lambda x: (
                        0
                        if x.priority == AlertPriority.CRITICAL
                        else 1
                        if x.priority == AlertPriority.IMPORTANT
                        else 2,
                        x.timestamp,
                    )
                )

                sections.append(
                    DigestSection(
                        category=category,
                        title=CATEGORIES[category.value]["en"],
                        title_ru=CATEGORIES[category.value]["ru"],
                        alerts=category_alerts,
                        emoji=CATEGORY_EMOJI.get(category, "📌"),
                    )
                )

        # Generate summary
        summary_en = self._generate_summary(unsent_alerts, "en")
        summary_ru = self._generate_summary(unsent_alerts, "ru")

        digest = Digest(
            type="daily",
            title=DIGEST_HEADERS["daily"]["en"],
            title_ru=DIGEST_HEADERS["daily"]["ru"],
            summary=summary_en,
            summary_ru=summary_ru,
            sections=sections,
            timestamp=datetime.utcnow(),
            total_alerts=len(unsent_alerts),
            critical_count=critical_count,
            important_count=important_count,
            info_count=info_count,
        )

        return digest

    async def get_weekly_summary(self) -> Digest:
        """Generate weekly summary from all alerts (sent and pending)."""
        # Get alerts from last 7 days
        week_ago = datetime.utcnow() - timedelta(days=7)
        weekly_alerts = [a for a in (self.sent_alerts + self.pending_alerts) if a.timestamp >= week_ago]

        # Count by priority
        critical_count = len([a for a in weekly_alerts if a.priority == AlertPriority.CRITICAL])
        important_count = len([a for a in weekly_alerts if a.priority == AlertPriority.IMPORTANT])
        info_count = len([a for a in weekly_alerts if a.priority == AlertPriority.INFO])

        # Group by category
        sections = []
        for category in AlertCategory:
            category_alerts = [a for a in weekly_alerts if a.category == category]
            if category_alerts:
                category_alerts.sort(key=lambda x: x.timestamp, reverse=True)

                sections.append(
                    DigestSection(
                        category=category,
                        title=CATEGORIES[category.value]["en"],
                        title_ru=CATEGORIES[category.value]["ru"],
                        alerts=category_alerts[:10],  # Limit to 10 per category
                        emoji=CATEGORY_EMOJI.get(category, "📌"),
                    )
                )

        # Generate summary
        summary_en = self._generate_weekly_summary(weekly_alerts, "en")
        summary_ru = self._generate_weekly_summary(weekly_alerts, "ru")

        digest = Digest(
            type="weekly",
            title=DIGEST_HEADERS["weekly"]["en"],
            title_ru=DIGEST_HEADERS["weekly"]["ru"],
            summary=summary_en,
            summary_ru=summary_ru,
            sections=sections,
            timestamp=datetime.utcnow(),
            total_alerts=len(weekly_alerts),
            critical_count=critical_count,
            important_count=important_count,
            info_count=info_count,
        )

        return digest

    def _generate_summary(self, alerts: list[SmartAlert], lang: str) -> str:
        """Generate daily summary text."""
        if not alerts:
            return "No new alerts today." if lang == "en" else "Новых оповещений сегодня нет."

        critical = len([a for a in alerts if a.priority == AlertPriority.CRITICAL])
        important = len([a for a in alerts if a.priority == AlertPriority.IMPORTANT])

        if lang == "en":
            parts = []
            if critical > 0:
                parts.append(f"{critical} critical")
            if important > 0:
                parts.append(f"{important} important")

            total = len(alerts)
            if parts:
                return f"{total} alerts: {', '.join(parts)}."
            return f"{total} informational updates."
        else:
            parts = []
            if critical > 0:
                parts.append(f"{critical} критических")
            if important > 0:
                parts.append(f"{important} важных")

            total = len(alerts)
            if parts:
                return f"{total} оповещений: {', '.join(parts)}."
            return f"{total} информационных обновлений."

    def _generate_weekly_summary(self, alerts: list[SmartAlert], lang: str) -> str:
        """Generate weekly summary text."""
        if not alerts:
            return (
                "Quiet week with no significant alerts."
                if lang == "en"
                else "Спокойная неделя без значимых оповещений."
            )

        # Count categories
        category_counts = {}
        for alert in alerts:
            cat = alert.category.value
            category_counts[cat] = category_counts.get(cat, 0) + 1

        # Find top category
        top_cat = max(category_counts, key=category_counts.get)
        top_count = category_counts[top_cat]

        if lang == "en":
            cat_name = CATEGORIES[top_cat]["en"]
            return f"This week: {len(alerts)} alerts. Most active: {cat_name} ({top_count})."
        else:
            cat_name = CATEGORIES[top_cat]["ru"]
            return f"За неделю: {len(alerts)} оповещений. Самое активное: {cat_name} ({top_count})."

    async def mark_digest_sent(self) -> None:
        """Mark daily digest as sent and clear pending alerts."""
        now = datetime.utcnow()

        for alert in self.pending_alerts:
            alert.sent = True
            self.sent_alerts.append(alert)

        self.pending_alerts = []
        self.last_digest_time = now

    async def mark_weekly_sent(self) -> None:
        """Mark weekly summary as sent."""
        self.last_weekly_time = datetime.utcnow()

        # Clean up old sent alerts (keep 14 days)
        cutoff = datetime.utcnow() - timedelta(days=14)
        self.sent_alerts = [a for a in self.sent_alerts if a.timestamp >= cutoff]

    def get_stats(self) -> NotificationStats:
        """Get notification statistics."""
        unsent = [a for a in self.pending_alerts if not a.sent]
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        sent_today = len([a for a in self.sent_alerts if a.timestamp >= today_start])

        return NotificationStats(
            pending_total=len(unsent),
            pending_critical=len([a for a in unsent if a.priority == AlertPriority.CRITICAL]),
            pending_important=len([a for a in unsent if a.priority == AlertPriority.IMPORTANT]),
            pending_info=len([a for a in unsent if a.priority == AlertPriority.INFO]),
            sent_today=sent_today,
            digest_ready=len(unsent) > 0,
            last_digest_time=self.last_digest_time,
            current_mode=self.mode,
        )

    def format_sensor_attributes(self) -> dict[str, Any]:
        """Format data for Home Assistant sensor attributes."""
        stats = self.get_stats()

        return {
            "pending_alerts_count": stats.pending_total,
            "pending_alerts_critical": stats.pending_critical,
            "pending_alerts_important": stats.pending_important,
            "pending_alerts_info": stats.pending_info,
            "sent_today": stats.sent_today,
            "daily_digest_ready": stats.digest_ready,
            "digest_ready_en": "Ready" if stats.digest_ready else "No new alerts",
            "digest_ready_ru": "Готов" if stats.digest_ready else "Новых оповещений нет",
            "last_digest_time": stats.last_digest_time.isoformat() if stats.last_digest_time else None,
            "notification_mode": stats.current_mode.value,
            "notification_mode_en": MODES[stats.current_mode.value]["en"],
            "notification_mode_ru": MODES[stats.current_mode.value]["ru"],
        }


# =============================================================================
# Alert Factory Functions
# =============================================================================


def create_price_alert(
    symbol: str,
    current_price: Decimal,
    target_price: Decimal,
    direction: str,  # "above" or "below"
) -> SmartAlert:
    """Create a price alert."""
    manager = NotificationManager()

    if direction == "above":
        title = f"{symbol} above ${target_price:,.2f}"
        title_ru = f"{symbol} выше ${target_price:,.2f}"
        message = f"{symbol} reached ${current_price:,.2f}, crossing above ${target_price:,.2f}"
        message_ru = f"{symbol} достиг ${current_price:,.2f}, пересёк ${target_price:,.2f} вверх"
    else:
        title = f"{symbol} below ${target_price:,.2f}"
        title_ru = f"{symbol} ниже ${target_price:,.2f}"
        message = f"{symbol} dropped to ${current_price:,.2f}, crossing below ${target_price:,.2f}"
        message_ru = f"{symbol} упал до ${current_price:,.2f}, пересёк ${target_price:,.2f} вниз"

    return manager.create_alert(
        title=title,
        title_ru=title_ru,
        message=message,
        message_ru=message_ru,
        priority=AlertPriority.IMPORTANT,
        category=AlertCategory.PRICE,
        value=current_price,
        symbol=symbol,
    )


def create_risk_alert(
    risk_type: str,
    risk_level: str,  # "low", "medium", "high", "critical"
    details: str,
    details_ru: str,
) -> SmartAlert:
    """Create a risk alert."""
    manager = NotificationManager()

    priority = (
        AlertPriority.CRITICAL
        if risk_level == "critical"
        else AlertPriority.IMPORTANT
        if risk_level == "high"
        else AlertPriority.INFO
    )

    titles = {
        "drawdown": ("Drawdown Alert", "Оповещение о просадке"),
        "volatility": ("Volatility Alert", "Оповещение о волатильности"),
        "exposure": ("Exposure Alert", "Оповещение о экспозиции"),
        "correlation": ("Correlation Alert", "Оповещение о корреляции"),
    }

    title, title_ru = titles.get(risk_type, ("Risk Alert", "Оповещение о риске"))

    return manager.create_alert(
        title=title,
        title_ru=title_ru,
        message=details,
        message_ru=details_ru,
        priority=priority,
        category=AlertCategory.RISK,
    )


def create_opportunity_alert(
    opp_type: str,
    message: str,
    message_ru: str,
    value: Decimal | None = None,
    symbol: str | None = None,
) -> SmartAlert:
    """Create an opportunity alert."""
    manager = NotificationManager()

    titles = {
        "dca": ("DCA Opportunity", "Возможность DCA"),
        "oversold": ("Oversold Signal", "Сигнал перепроданности"),
        "fear": ("Fear & Greed Signal", "Сигнал страха и жадности"),
        "whale": ("Whale Accumulation", "Накопление китами"),
    }

    title, title_ru = titles.get(opp_type, ("Opportunity", "Возможность"))

    return manager.create_alert(
        title=title,
        title_ru=title_ru,
        message=message,
        message_ru=message_ru,
        priority=AlertPriority.IMPORTANT,
        category=AlertCategory.OPPORTUNITY,
        value=value,
        symbol=symbol,
    )


def create_whale_alert(
    symbol: str,
    amount: Decimal,
    direction: str,  # "buy" or "sell"
    exchange: str | None = None,
) -> SmartAlert:
    """Create a whale activity alert."""
    manager = NotificationManager()

    if direction == "buy":
        title = f"Whale Buy: {symbol}"
        title_ru = f"Покупка кита: {symbol}"
        message = f"Large {symbol} purchase detected: ${amount:,.0f}"
        message_ru = f"Обнаружена крупная покупка {symbol}: ${amount:,.0f}"
    else:
        title = f"Whale Sell: {symbol}"
        title_ru = f"Продажа кита: {symbol}"
        message = f"Large {symbol} sale detected: ${amount:,.0f}"
        message_ru = f"Обнаружена крупная продажа {symbol}: ${amount:,.0f}"

    if exchange:
        message += f" on {exchange}"
        message_ru += f" на {exchange}"

    return manager.create_alert(
        title=title,
        title_ru=title_ru,
        message=message,
        message_ru=message_ru,
        priority=AlertPriority.IMPORTANT,
        category=AlertCategory.WHALE,
        value=amount,
        symbol=symbol,
        metadata={"exchange": exchange, "direction": direction},
    )


def create_goal_alert(
    milestone: str,  # "25%", "50%", "75%", "100%"
    goal_name: str,
    goal_name_ru: str,
    current_value: Decimal,
    target_value: Decimal,
) -> SmartAlert:
    """Create a goal milestone alert."""
    manager = NotificationManager()

    progress = (float(current_value) / float(target_value)) * 100

    messages = {
        "25%": (
            f"You've reached 25% of your '{goal_name}' goal! Current: ${current_value:,.2f}",
            f"Вы достигли 25% цели '{goal_name_ru}'! Текущее: ${current_value:,.2f}",
        ),
        "50%": (
            f"Halfway there! 50% of '{goal_name}' achieved! Current: ${current_value:,.2f}",
            f"На полпути! 50% цели '{goal_name_ru}' достигнуто! Текущее: ${current_value:,.2f}",
        ),
        "75%": (
            f"Almost there! 75% of '{goal_name}' complete! Current: ${current_value:,.2f}",
            f"Почти готово! 75% цели '{goal_name_ru}' выполнено! Текущее: ${current_value:,.2f}",
        ),
        "100%": (
            f"Congratulations! You've achieved your '{goal_name}' goal! ${current_value:,.2f}",
            f"Поздравляем! Вы достигли цели '{goal_name_ru}'! ${current_value:,.2f}",
        ),
    }

    message, message_ru = messages.get(milestone, (f"Goal milestone: {milestone}", f"Этап цели: {milestone}"))

    return manager.create_alert(
        title=f"Goal: {milestone} milestone!",
        title_ru=f"Цель: этап {milestone}!",
        message=message,
        message_ru=message_ru,
        priority=AlertPriority.IMPORTANT,
        category=AlertCategory.GOAL,
        value=current_value,
        metadata={"milestone": milestone, "progress": progress},
    )
