"""
Morning/Evening Briefing Service.

Generates comprehensive scheduled reports with market summaries,
portfolio status, and action recommendations.
All output is bilingual (English/Russian).
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class BriefingSection:
    """Single section of a briefing."""

    header: str
    header_ru: str
    content: str
    content_ru: str
    emoji: str
    priority: int = 0  # Lower = higher priority

    def to_dict(self, lang: str = "en") -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "header": self.header if lang == "en" else self.header_ru,
            "header_en": self.header,
            "header_ru": self.header_ru,
            "content": self.content if lang == "en" else self.content_ru,
            "content_en": self.content,
            "content_ru": self.content_ru,
            "emoji": self.emoji,
            "priority": self.priority,
        }


@dataclass
class Briefing:
    """Complete briefing with all sections."""

    type: str  # "morning" or "evening"
    title: str
    title_ru: str
    greeting: str
    greeting_ru: str
    sections: list[BriefingSection]
    timestamp: datetime
    summary_emoji: str = "📊"

    def to_dict(self, lang: str = "en") -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": self.type,
            "title": self.title if lang == "en" else self.title_ru,
            "title_en": self.title,
            "title_ru": self.title_ru,
            "greeting": self.greeting if lang == "en" else self.greeting_ru,
            "greeting_en": self.greeting,
            "greeting_ru": self.greeting_ru,
            "sections": [s.to_dict(lang) for s in self.sections],
            "timestamp": self.timestamp.isoformat(),
            "summary_emoji": self.summary_emoji,
        }

    def format_message(self, lang: str = "en") -> str:
        """Format briefing as a notification message."""
        lines = []

        # Greeting
        greeting = self.greeting if lang == "en" else self.greeting_ru
        lines.append(f"{self.summary_emoji} {greeting}")
        lines.append("")

        # Sections (sorted by priority)
        sorted_sections = sorted(self.sections, key=lambda s: s.priority)
        for section in sorted_sections:
            header = section.header if lang == "en" else section.header_ru
            content = section.content if lang == "en" else section.content_ru
            lines.append(f"{section.emoji} {header}")
            lines.append(content)
            lines.append("")

        return "\n".join(lines).strip()


# =============================================================================
# Translation Dictionaries
# =============================================================================

GREETINGS = {
    "morning": {
        "en": "Good morning! Here's your crypto briefing:",
        "ru": "Доброе утро! Вот ваш крипто-брифинг:",
    },
    "evening": {
        "en": "Good evening! Here's your daily summary:",
        "ru": "Добрый вечер! Вот ваша дневная сводка:",
    },
}

TITLES = {
    "morning": {
        "en": "Morning Crypto Briefing",
        "ru": "Утренний крипто-брифинг",
    },
    "evening": {
        "en": "Evening Crypto Summary",
        "ru": "Вечерняя крипто-сводка",
    },
}

SECTION_HEADERS = {
    "overnight": {
        "en": "Overnight Changes",
        "ru": "Изменения за ночь",
    },
    "market_status": {
        "en": "Market Status",
        "ru": "Состояние рынка",
    },
    "portfolio": {
        "en": "Portfolio Status",
        "ru": "Состояние портфеля",
    },
    "sentiment": {
        "en": "Market Sentiment",
        "ru": "Настроение рынка",
    },
    "whale_activity": {
        "en": "Whale Activity",
        "ru": "Активность китов",
    },
    "today_outlook": {
        "en": "Today's Outlook",
        "ru": "Прогноз на сегодня",
    },
    "recommended_action": {
        "en": "Recommended Action",
        "ru": "Рекомендуемые действия",
    },
    "upcoming_events": {
        "en": "Upcoming Events",
        "ru": "Предстоящие события",
    },
    "day_performance": {
        "en": "Today's Performance",
        "ru": "Результаты дня",
    },
    "key_events": {
        "en": "Key Events Today",
        "ru": "Ключевые события дня",
    },
    "tomorrow_preview": {
        "en": "Tomorrow's Preview",
        "ru": "Предпросмотр на завтра",
    },
    "weekly_progress": {
        "en": "Weekly Progress",
        "ru": "Недельный прогресс",
    },
    "risk_status": {
        "en": "Risk Status",
        "ru": "Состояние рисков",
    },
    "alerts_summary": {
        "en": "Alerts Summary",
        "ru": "Сводка оповещений",
    },
}

SENTIMENTS = {
    "bullish": {"en": "Bullish", "ru": "Бычий", "emoji": "🟢"},
    "neutral": {"en": "Neutral", "ru": "Нейтральный", "emoji": "🟡"},
    "bearish": {"en": "Bearish", "ru": "Медвежий", "emoji": "🔴"},
}

RISK_LEVELS = {
    "low": {"en": "Low Risk", "ru": "Низкий риск", "emoji": "🟢"},
    "medium": {"en": "Medium Risk", "ru": "Средний риск", "emoji": "🟡"},
    "high": {"en": "High Risk", "ru": "Высокий риск", "emoji": "🟠"},
    "critical": {"en": "Critical Risk", "ru": "Критический риск", "emoji": "🔴"},
}

ACTIONS = {
    "nothing": {"en": "No action needed", "ru": "Действий не требуется"},
    "consider_dca": {"en": "Consider DCA opportunity", "ru": "Рассмотрите возможность DCA"},
    "take_profits": {"en": "Consider taking profits", "ru": "Рассмотрите фиксацию прибыли"},
    "reduce_risk": {"en": "Consider reducing risk", "ru": "Рассмотрите снижение риска"},
    "rebalance": {"en": "Portfolio rebalancing suggested", "ru": "Рекомендуется ребалансировка"},
    "watch": {"en": "Monitor closely", "ru": "Внимательно наблюдайте"},
}


# =============================================================================
# Briefing Service
# =============================================================================


class BriefingService:
    """
    Service for generating morning and evening briefings.

    Morning Briefing Contents:
    - Overnight changes (prices, F&G, whales)
    - Today's outlook (events, risk level)
    - Recommended action
    - Portfolio status

    Evening Briefing Contents:
    - Day's performance summary
    - Key events that happened
    - Tomorrow's preview
    - Weekly progress (if Friday)
    """

    def __init__(self):
        self.last_morning_briefing: datetime | None = None
        self.last_evening_briefing: datetime | None = None
        self._cached_data: dict[str, Any] = {}

    def update_cache(self, data: dict[str, Any]) -> None:
        """Update cached market data for briefing generation."""
        self._cached_data.update(data)
        self._cached_data["_updated"] = datetime.utcnow()

    async def generate_morning_briefing(
        self,
        btc_price: Decimal | None = None,
        btc_change_24h: float | None = None,
        fear_greed: int | None = None,
        portfolio_value: Decimal | None = None,
        portfolio_change: float | None = None,
        whale_buys: int = 0,
        whale_sells: int = 0,
        upcoming_events: list[str] | None = None,
        risk_level: str = "medium",
        recommended_action: str = "nothing",
    ) -> Briefing:
        """Generate morning briefing."""
        sections = []

        # 1. Overnight Changes
        overnight_content = self._format_overnight_changes(btc_price, btc_change_24h, fear_greed, "en")
        overnight_content_ru = self._format_overnight_changes(btc_price, btc_change_24h, fear_greed, "ru")
        sections.append(
            BriefingSection(
                header=SECTION_HEADERS["overnight"]["en"],
                header_ru=SECTION_HEADERS["overnight"]["ru"],
                content=overnight_content,
                content_ru=overnight_content_ru,
                emoji="🌙",
                priority=1,
            )
        )

        # 2. Market Sentiment
        sentiment = self._determine_sentiment(btc_change_24h, fear_greed)
        sentiment_content = self._format_sentiment(sentiment, fear_greed, "en")
        sentiment_content_ru = self._format_sentiment(sentiment, fear_greed, "ru")
        sections.append(
            BriefingSection(
                header=SECTION_HEADERS["sentiment"]["en"],
                header_ru=SECTION_HEADERS["sentiment"]["ru"],
                content=sentiment_content,
                content_ru=sentiment_content_ru,
                emoji=SENTIMENTS.get(sentiment, SENTIMENTS["neutral"])["emoji"],
                priority=2,
            )
        )

        # 3. Portfolio Status
        if portfolio_value is not None:
            portfolio_content = self._format_portfolio(portfolio_value, portfolio_change, "en")
            portfolio_content_ru = self._format_portfolio(portfolio_value, portfolio_change, "ru")
            sections.append(
                BriefingSection(
                    header=SECTION_HEADERS["portfolio"]["en"],
                    header_ru=SECTION_HEADERS["portfolio"]["ru"],
                    content=portfolio_content,
                    content_ru=portfolio_content_ru,
                    emoji="💼",
                    priority=3,
                )
            )

        # 4. Whale Activity
        if whale_buys > 0 or whale_sells > 0:
            whale_content = self._format_whale_activity(whale_buys, whale_sells, "en")
            whale_content_ru = self._format_whale_activity(whale_buys, whale_sells, "ru")
            sections.append(
                BriefingSection(
                    header=SECTION_HEADERS["whale_activity"]["en"],
                    header_ru=SECTION_HEADERS["whale_activity"]["ru"],
                    content=whale_content,
                    content_ru=whale_content_ru,
                    emoji="🐋",
                    priority=4,
                )
            )

        # 5. Today's Outlook
        outlook_content = self._format_outlook(risk_level, upcoming_events, "en")
        outlook_content_ru = self._format_outlook(risk_level, upcoming_events, "ru")
        sections.append(
            BriefingSection(
                header=SECTION_HEADERS["today_outlook"]["en"],
                header_ru=SECTION_HEADERS["today_outlook"]["ru"],
                content=outlook_content,
                content_ru=outlook_content_ru,
                emoji="🔮",
                priority=5,
            )
        )

        # 6. Recommended Action
        action_content = ACTIONS.get(recommended_action, ACTIONS["nothing"])["en"]
        action_content_ru = ACTIONS.get(recommended_action, ACTIONS["nothing"])["ru"]

        if recommended_action == "consider_dca" and fear_greed and fear_greed < 30:
            action_content += f" (Fear & Greed at {fear_greed})"
            action_content_ru += f" (Страх и Жадность: {fear_greed})"

        sections.append(
            BriefingSection(
                header=SECTION_HEADERS["recommended_action"]["en"],
                header_ru=SECTION_HEADERS["recommended_action"]["ru"],
                content=action_content,
                content_ru=action_content_ru,
                emoji="✅",
                priority=6,
            )
        )

        briefing = Briefing(
            type="morning",
            title=TITLES["morning"]["en"],
            title_ru=TITLES["morning"]["ru"],
            greeting=GREETINGS["morning"]["en"],
            greeting_ru=GREETINGS["morning"]["ru"],
            sections=sections,
            timestamp=datetime.utcnow(),
            summary_emoji="☀️",
        )

        self.last_morning_briefing = datetime.utcnow()
        return briefing

    async def generate_evening_briefing(
        self,
        btc_price: Decimal | None = None,
        btc_change_24h: float | None = None,
        portfolio_value: Decimal | None = None,
        portfolio_change: float | None = None,
        day_high: Decimal | None = None,
        day_low: Decimal | None = None,
        volume_change: float | None = None,
        key_events: list[str] | None = None,
        tomorrow_events: list[str] | None = None,
        alerts_count: int = 0,
        risk_level: str = "medium",
        include_weekly: bool = False,
        weekly_change: float | None = None,
    ) -> Briefing:
        """Generate evening briefing."""
        sections = []

        # 1. Day's Performance
        perf_content = self._format_day_performance(btc_price, btc_change_24h, day_high, day_low, volume_change, "en")
        perf_content_ru = self._format_day_performance(
            btc_price, btc_change_24h, day_high, day_low, volume_change, "ru"
        )
        sections.append(
            BriefingSection(
                header=SECTION_HEADERS["day_performance"]["en"],
                header_ru=SECTION_HEADERS["day_performance"]["ru"],
                content=perf_content,
                content_ru=perf_content_ru,
                emoji="📈",
                priority=1,
            )
        )

        # 2. Portfolio Status
        if portfolio_value is not None:
            portfolio_content = self._format_portfolio(portfolio_value, portfolio_change, "en")
            portfolio_content_ru = self._format_portfolio(portfolio_value, portfolio_change, "ru")
            sections.append(
                BriefingSection(
                    header=SECTION_HEADERS["portfolio"]["en"],
                    header_ru=SECTION_HEADERS["portfolio"]["ru"],
                    content=portfolio_content,
                    content_ru=portfolio_content_ru,
                    emoji="💼",
                    priority=2,
                )
            )

        # 3. Key Events Today
        if key_events:
            events_content = self._format_events(key_events, "en")
            events_content_ru = self._format_events(key_events, "ru")
            sections.append(
                BriefingSection(
                    header=SECTION_HEADERS["key_events"]["en"],
                    header_ru=SECTION_HEADERS["key_events"]["ru"],
                    content=events_content,
                    content_ru=events_content_ru,
                    emoji="📌",
                    priority=3,
                )
            )

        # 4. Risk Status
        risk_content = self._format_risk_status(risk_level, "en")
        risk_content_ru = self._format_risk_status(risk_level, "ru")
        sections.append(
            BriefingSection(
                header=SECTION_HEADERS["risk_status"]["en"],
                header_ru=SECTION_HEADERS["risk_status"]["ru"],
                content=risk_content,
                content_ru=risk_content_ru,
                emoji=RISK_LEVELS.get(risk_level, RISK_LEVELS["medium"])["emoji"],
                priority=4,
            )
        )

        # 5. Alerts Summary
        if alerts_count > 0:
            alerts_content = f"{alerts_count} alerts triggered today"
            alerts_content_ru = f"{alerts_count} оповещений сработало сегодня"
            sections.append(
                BriefingSection(
                    header=SECTION_HEADERS["alerts_summary"]["en"],
                    header_ru=SECTION_HEADERS["alerts_summary"]["ru"],
                    content=alerts_content,
                    content_ru=alerts_content_ru,
                    emoji="🔔",
                    priority=5,
                )
            )

        # 6. Tomorrow's Preview
        if tomorrow_events:
            preview_content = self._format_tomorrow_preview(tomorrow_events, "en")
            preview_content_ru = self._format_tomorrow_preview(tomorrow_events, "ru")
            sections.append(
                BriefingSection(
                    header=SECTION_HEADERS["tomorrow_preview"]["en"],
                    header_ru=SECTION_HEADERS["tomorrow_preview"]["ru"],
                    content=preview_content,
                    content_ru=preview_content_ru,
                    emoji="📅",
                    priority=6,
                )
            )

        # 7. Weekly Progress (if Friday)
        if include_weekly and weekly_change is not None:
            weekly_content = self._format_weekly_progress(weekly_change, "en")
            weekly_content_ru = self._format_weekly_progress(weekly_change, "ru")
            sections.append(
                BriefingSection(
                    header=SECTION_HEADERS["weekly_progress"]["en"],
                    header_ru=SECTION_HEADERS["weekly_progress"]["ru"],
                    content=weekly_content,
                    content_ru=weekly_content_ru,
                    emoji="📊",
                    priority=7,
                )
            )

        briefing = Briefing(
            type="evening",
            title=TITLES["evening"]["en"],
            title_ru=TITLES["evening"]["ru"],
            greeting=GREETINGS["evening"]["en"],
            greeting_ru=GREETINGS["evening"]["ru"],
            sections=sections,
            timestamp=datetime.utcnow(),
            summary_emoji="🌙",
        )

        self.last_evening_briefing = datetime.utcnow()
        return briefing

    def _format_overnight_changes(
        self,
        btc_price: Decimal | None,
        change_24h: float | None,
        fear_greed: int | None,
        lang: str,
    ) -> str:
        """Format overnight changes section."""
        parts = []

        if btc_price is not None and change_24h is not None:
            change_emoji = "🟢" if change_24h >= 0 else "🔴"
            sign = "+" if change_24h >= 0 else ""

            if lang == "en":
                parts.append(f"BTC: ${btc_price:,.0f} ({sign}{change_24h:.1f}%) {change_emoji}")
            else:
                parts.append(f"BTC: ${btc_price:,.0f} ({sign}{change_24h:.1f}%) {change_emoji}")

        if fear_greed is not None:
            if lang == "en":
                fg_label = self._get_fear_greed_label(fear_greed, "en")
                parts.append(f"Fear & Greed: {fear_greed} ({fg_label})")
            else:
                fg_label = self._get_fear_greed_label(fear_greed, "ru")
                parts.append(f"Страх и Жадность: {fear_greed} ({fg_label})")

        if not parts:
            return "No data available" if lang == "en" else "Данные недоступны"

        return " | ".join(parts)

    def _format_sentiment(self, sentiment: str, fear_greed: int | None, lang: str) -> str:
        """Format market sentiment section."""
        sent_data = SENTIMENTS.get(sentiment, SENTIMENTS["neutral"])
        sent_label = sent_data[lang]

        if lang == "en":
            result = f"Market is currently {sent_label.lower()}"
            if fear_greed is not None:
                if fear_greed < 25:
                    result += " with extreme fear in the market"
                elif fear_greed > 75:
                    result += " with extreme greed in the market"
        else:
            result = f"Рынок сейчас {sent_label.lower()}"
            if fear_greed is not None:
                if fear_greed < 25:
                    result += " с экстремальным страхом"
                elif fear_greed > 75:
                    result += " с экстремальной жадностью"

        return result

    def _format_portfolio(
        self,
        value: Decimal,
        change: float | None,
        lang: str,
    ) -> str:
        """Format portfolio status section."""
        if lang == "en":
            result = f"Total value: ${value:,.2f}"
            if change is not None:
                sign = "+" if change >= 0 else ""
                emoji = "📈" if change >= 0 else "📉"
                result += f" ({sign}{change:.1f}%) {emoji}"
        else:
            result = f"Общая стоимость: ${value:,.2f}"
            if change is not None:
                sign = "+" if change >= 0 else ""
                emoji = "📈" if change >= 0 else "📉"
                result += f" ({sign}{change:.1f}%) {emoji}"

        return result

    def _format_whale_activity(self, buys: int, sells: int, lang: str) -> str:
        """Format whale activity section."""
        if lang == "en":
            parts = []
            if buys > 0:
                parts.append(f"{buys} large buy{'s' if buys > 1 else ''}")
            if sells > 0:
                parts.append(f"{sells} large sell{'s' if sells > 1 else ''}")

            if not parts:
                return "No significant whale activity"

            result = "Overnight: " + ", ".join(parts)
            if buys > sells:
                result += " (bullish signal)"
            elif sells > buys:
                result += " (bearish signal)"
            return result
        else:
            parts = []
            if buys > 0:
                parts.append(f"{buys} крупных покупок")
            if sells > 0:
                parts.append(f"{sells} крупных продаж")

            if not parts:
                return "Значительной активности китов нет"

            result = "За ночь: " + ", ".join(parts)
            if buys > sells:
                result += " (бычий сигнал)"
            elif sells > buys:
                result += " (медвежий сигнал)"
            return result

    def _format_outlook(
        self,
        risk_level: str,
        events: list[str] | None,
        lang: str,
    ) -> str:
        """Format today's outlook section."""
        risk_data = RISK_LEVELS.get(risk_level, RISK_LEVELS["medium"])
        risk_label = risk_data[lang]

        if lang == "en":
            result = f"Risk level: {risk_label}"
            if events:
                result += f"\nUpcoming: {', '.join(events[:3])}"
                if len(events) > 3:
                    result += f" (+{len(events) - 3} more)"
            else:
                result += "\nNo major events scheduled"
        else:
            result = f"Уровень риска: {risk_label}"
            if events:
                result += f"\nПредстоит: {', '.join(events[:3])}"
                if len(events) > 3:
                    result += f" (+{len(events) - 3} ещё)"
            else:
                result += "\nЗначимых событий не запланировано"

        return result

    def _format_day_performance(
        self,
        btc_price: Decimal | None,
        change_24h: float | None,
        day_high: Decimal | None,
        day_low: Decimal | None,
        volume_change: float | None,
        lang: str,
    ) -> str:
        """Format day's performance section."""
        parts = []

        if btc_price is not None:
            if lang == "en":
                parts.append(f"BTC closed at ${btc_price:,.0f}")
            else:
                parts.append(f"BTC закрылся на ${btc_price:,.0f}")

        if change_24h is not None:
            sign = "+" if change_24h >= 0 else ""
            emoji = "📈" if change_24h >= 0 else "📉"
            parts.append(f"({sign}{change_24h:.1f}%) {emoji}")

        if day_high is not None and day_low is not None:
            if lang == "en":
                parts.append(f"\nRange: ${day_low:,.0f} - ${day_high:,.0f}")
            else:
                parts.append(f"\nДиапазон: ${day_low:,.0f} - ${day_high:,.0f}")

        if volume_change is not None:
            sign = "+" if volume_change >= 0 else ""
            if lang == "en":
                parts.append(f"\nVolume: {sign}{volume_change:.0f}% vs average")
            else:
                parts.append(f"\nОбъём: {sign}{volume_change:.0f}% от среднего")

        if not parts:
            return "No data available" if lang == "en" else "Данные недоступны"

        return " ".join(parts)

    def _format_events(self, events: list[str], lang: str) -> str:
        """Format events list."""
        if not events:
            return "No major events" if lang == "en" else "Значимых событий нет"

        return "\n".join(f"• {event}" for event in events[:5])

    def _format_risk_status(self, risk_level: str, lang: str) -> str:
        """Format risk status section."""
        risk_data = RISK_LEVELS.get(risk_level, RISK_LEVELS["medium"])
        risk_label = risk_data[lang]
        emoji = risk_data["emoji"]

        if lang == "en":
            descriptions = {
                "low": "Market conditions are favorable",
                "medium": "Normal market conditions",
                "high": "Elevated caution recommended",
                "critical": "Consider reducing exposure",
            }
        else:
            descriptions = {
                "low": "Рыночные условия благоприятны",
                "medium": "Нормальные рыночные условия",
                "high": "Рекомендуется повышенная осторожность",
                "critical": "Рассмотрите снижение экспозиции",
            }

        desc = descriptions.get(risk_level, descriptions["medium"])
        return f"{emoji} {risk_label}: {desc}"

    def _format_tomorrow_preview(self, events: list[str], lang: str) -> str:
        """Format tomorrow's preview section."""
        if not events:
            if lang == "en":
                return "No major events scheduled for tomorrow"
            else:
                return "На завтра значимых событий не запланировано"

        if lang == "en":
            header = "Tomorrow's events:"
        else:
            header = "События на завтра:"

        return header + "\n" + "\n".join(f"• {event}" for event in events[:3])

    def _format_weekly_progress(self, weekly_change: float, lang: str) -> str:
        """Format weekly progress section."""
        sign = "+" if weekly_change >= 0 else ""
        emoji = "📈" if weekly_change >= 0 else "📉"

        if lang == "en":
            if weekly_change >= 5:
                status = "Great week!"
            elif weekly_change >= 0:
                status = "Positive week"
            elif weekly_change >= -5:
                status = "Slight decline"
            else:
                status = "Challenging week"

            return f"Weekly change: {sign}{weekly_change:.1f}% {emoji}\n{status}"
        else:
            if weekly_change >= 5:
                status = "Отличная неделя!"
            elif weekly_change >= 0:
                status = "Позитивная неделя"
            elif weekly_change >= -5:
                status = "Небольшое снижение"
            else:
                status = "Сложная неделя"

            return f"Изменение за неделю: {sign}{weekly_change:.1f}% {emoji}\n{status}"

    def _determine_sentiment(
        self,
        change_24h: float | None,
        fear_greed: int | None,
    ) -> str:
        """Determine overall market sentiment."""
        score = 0

        if change_24h is not None:
            if change_24h > 3:
                score += 2
            elif change_24h > 0:
                score += 1
            elif change_24h < -3:
                score -= 2
            elif change_24h < 0:
                score -= 1

        if fear_greed is not None:
            if fear_greed > 60:
                score += 1
            elif fear_greed < 40:
                score -= 1

        if score >= 2:
            return "bullish"
        elif score <= -2:
            return "bearish"
        else:
            return "neutral"

    def _get_fear_greed_label(self, value: int, lang: str) -> str:
        """Get Fear & Greed label for value."""
        labels = {
            "extreme_fear": {"en": "Extreme Fear", "ru": "Экстремальный страх"},
            "fear": {"en": "Fear", "ru": "Страх"},
            "neutral": {"en": "Neutral", "ru": "Нейтрально"},
            "greed": {"en": "Greed", "ru": "Жадность"},
            "extreme_greed": {"en": "Extreme Greed", "ru": "Экстремальная жадность"},
        }

        if value <= 20:
            key = "extreme_fear"
        elif value <= 40:
            key = "fear"
        elif value <= 60:
            key = "neutral"
        elif value <= 80:
            key = "greed"
        else:
            key = "extreme_greed"

        return labels[key][lang]

    def format_sensor_attributes(self) -> dict[str, Any]:
        """Format data for Home Assistant sensor attributes."""
        return {
            "morning_briefing_available": self.last_morning_briefing is not None,
            "evening_briefing_available": self.last_evening_briefing is not None,
            "last_morning_briefing": (self.last_morning_briefing.isoformat() if self.last_morning_briefing else None),
            "last_evening_briefing": (self.last_evening_briefing.isoformat() if self.last_evening_briefing else None),
            "morning_briefing_status_en": ("Ready" if self.last_morning_briefing else "Not generated"),
            "morning_briefing_status_ru": ("Готов" if self.last_morning_briefing else "Не сгенерирован"),
            "evening_briefing_status_en": ("Ready" if self.last_evening_briefing else "Not generated"),
            "evening_briefing_status_ru": ("Готов" if self.last_evening_briefing else "Не сгенерирован"),
        }
