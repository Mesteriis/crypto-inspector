"""
Economic Calendar - Market events and news integration system.

This service tracks economic events, news, and market-moving announcements
that can significantly impact cryptocurrency markets.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from core.constants import DEFAULT_SYMBOLS
from service.ha_integration import get_supervisor_client

logger = logging.getLogger(__name__)


class EventImpact(Enum):
    """Impact levels of economic events."""

    LOW = "low"  # Minimal market impact
    MEDIUM = "medium"  # Moderate market impact
    HIGH = "high"  # Significant market impact
    CRITICAL = "critical"  # Major market impact


class EventType(Enum):
    """Types of market events."""

    ECONOMIC_DATA = "economic_data"  # GDP, inflation, employment data
    CENTRAL_BANK = "central_bank"  # Fed, ECB meetings and decisions
    POLITICAL = "political"  # Elections, policy changes
    REGULATORY = "regulatory"  # New regulations, bans
    CORPORATE = "corporate"  # Major company announcements
    TECH_UPGRADE = "tech_upgrade"  # Blockchain upgrades, halvings
    MARKET_EVENT = "market_event"  # Major market movements, crashes
    NEWS_SENTIMENT = "news_sentiment"  # Media sentiment analysis


@dataclass
class EconomicEvent:
    """Represents an economic or market event."""

    event_id: str
    title: str
    description: str
    event_type: EventType
    impact: EventImpact
    timestamp: datetime
    source: str  # News source/provider
    symbols_affected: list[str]  # Which cryptocurrencies might be affected
    predicted_impact: str | None = None  # Predicted market reaction
    actual_impact: str | None = None  # Actual market reaction (filled after event)
    sentiment_score: float | None = None  # -1 to 1 sentiment score
    relevance_score: float = 0.0  # 0-100 relevance to crypto markets
    is_important: bool = False
    notified: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "event_id": self.event_id,
            "title": self.title,
            "description": self.description,
            "event_type": self.event_type.value,
            "impact": self.impact.value,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "symbols_affected": self.symbols_affected,
            "predicted_impact": self.predicted_impact,
            "actual_impact": self.actual_impact,
            "sentiment_score": self.sentiment_score,
            "relevance_score": self.relevance_score,
            "is_important": self.is_important,
        }

    def is_upcoming(self, hours_ahead: int = 24) -> bool:
        """Check if event is upcoming within specified hours."""
        now = datetime.now()
        future_limit = now + timedelta(hours=hours_ahead)
        return now <= self.timestamp <= future_limit

    def is_recent(self, hours_back: int = 24) -> bool:
        """Check if event happened recently."""
        now = datetime.now()
        past_limit = now - timedelta(hours=hours_back)
        return past_limit <= self.timestamp <= now


@dataclass
class NewsArticle:
    """Represents a news article affecting crypto markets."""

    article_id: str
    title: str
    summary: str
    url: str
    published_at: datetime
    source: str
    symbols_mentioned: list[str]
    sentiment: float  # -1 (very negative) to 1 (very positive)
    relevance: float  # 0-100 relevance to crypto
    market_impact: str | None = None
    is_breaking: bool = False


class EconomicCalendar:
    """Main economic calendar service."""

    def __init__(self):
        """Initialize economic calendar."""
        self._supervisor_client = get_supervisor_client()
        self._events: list[EconomicEvent] = []
        self._news: list[NewsArticle] = []
        self._cache_duration = timedelta(minutes=30)
        self._last_update: datetime | None = None

        # Event sources (simulated for now)
        self._news_sources = ["CryptoPanic", "CoinDesk", "CoinTelegraph", "Reuters Crypto", "Bloomberg Crypto"]

        self._economic_sources = ["Federal Reserve", "ECB", "BoE", "BOJ", "SNB"]

    async def initialize_events(self) -> None:
        """Initialize with upcoming economic events."""
        logger.info("Initializing economic calendar events")

        # Simulate upcoming events (in real implementation, fetch from APIs)
        upcoming_events = await self._generate_sample_events()
        self._events.extend(upcoming_events)

        # Fetch recent news
        await self._fetch_news()

        self._last_update = datetime.now()
        logger.info(f"Initialized {len(self._events)} events and {len(self._news)} news articles")

    async def _generate_sample_events(self) -> list[EconomicEvent]:
        """Generate sample economic events (placeholder for real data)."""
        now = datetime.now()
        events = []

        # Federal Reserve meeting (high impact)
        events.append(
            EconomicEvent(
                event_id="fed_meeting_001",
                title="FOMC Interest Rate Decision",
                description="Federal Reserve announces interest rate decision and monetary policy stance",
                event_type=EventType.CENTRAL_BANK,
                impact=EventImpact.HIGH,
                timestamp=now + timedelta(days=2, hours=14),
                source="Federal Reserve",
                symbols_affected=["BTC/USDT", "ETH/USDT", "USDT"],
                predicted_impact="Rate hikes typically strengthen USD, putting downward pressure on crypto",
                sentiment_score=-0.3,  # Slightly negative for crypto
                relevance_score=95.0,
                is_important=True,
            )
        )

        # CPI Release (medium impact)
        events.append(
            EconomicEvent(
                event_id="cpi_release_001",
                title="US Consumer Price Index",
                description="Monthly inflation data release affecting monetary policy expectations",
                event_type=EventType.ECONOMIC_DATA,
                impact=EventImpact.MEDIUM,
                timestamp=now + timedelta(days=1, hours=13),
                source="Bureau of Labor Statistics",
                symbols_affected=["BTC/USDT", "ETH/USDT"],
                predicted_impact="Higher than expected CPI may lead to hawkish Fed expectations",
                sentiment_score=-0.2,
                relevance_score=85.0,
                is_important=True,
            )
        )

        # Bitcoin Halving countdown (high impact for BTC)
        events.append(
            EconomicEvent(
                event_id="btc_halving_001",
                title="Bitcoin Halving Countdown",
                description="Approximately 30 days until next Bitcoin halving event",
                event_type=EventType.TECH_UPGRADE,
                impact=EventImpact.HIGH,
                timestamp=now + timedelta(days=30),
                source="Blockchain Data",
                symbols_affected=["BTC/USDT"],
                predicted_impact="Historically leads to increased price volatility and potential bull run",
                sentiment_score=0.7,
                relevance_score=100.0,
                is_important=True,
            )
        )

        # Regulatory announcement (high impact)
        events.append(
            EconomicEvent(
                event_id="regulation_001",
                title="SEC Crypto Regulation Update",
                description="Potential new regulatory framework for cryptocurrency exchanges",
                event_type=EventType.REGULATORY,
                impact=EventImpact.HIGH,
                timestamp=now + timedelta(days=5),
                source="SEC.gov",
                symbols_affected=DEFAULT_SYMBOLS,
                predicted_impact="Clear regulations could boost institutional adoption",
                sentiment_score=0.4,
                relevance_score=90.0,
                is_important=True,
            )
        )

        return events

    async def _fetch_news(self) -> None:
        """Fetch recent cryptocurrency news (placeholder)."""
        now = datetime.now()

        # Sample news articles
        self._news.extend(
            [
                NewsArticle(
                    article_id="news_001",
                    title="Bitcoin ETF Approval Rumors Circulate",
                    summary="Reports suggest SEC may approve spot Bitcoin ETFs sooner than expected",
                    url="https://example.com/bitcoin-etf-rumors",
                    published_at=now - timedelta(hours=2),
                    source="CryptoPanic",
                    symbols_mentioned=["BTC/USDT"],
                    sentiment=0.8,
                    relevance=95.0,
                    is_breaking=True,
                    market_impact="Positive for Bitcoin price",
                ),
                NewsArticle(
                    article_id="news_002",
                    title="Ethereum Layer 2 Adoption Surpasses 50%",
                    summary="Major increase in Ethereum Layer 2 network usage shows growing scalability",
                    url="https://example.com/eth-layer2-adoption",
                    published_at=now - timedelta(hours=4),
                    source="CoinDesk",
                    symbols_mentioned=["ETH/USDT"],
                    sentiment=0.6,
                    relevance=85.0,
                    market_impact="Bullish for Ethereum ecosystem",
                ),
                NewsArticle(
                    article_id="news_003",
                    title="China Announces Digital Yuan Pilot Expansion",
                    summary="People's Bank of China expands digital currency pilot program to more cities",
                    url="https://example.com/digital-yuan-expansion",
                    published_at=now - timedelta(hours=6),
                    source="Reuters",
                    symbols_mentioned=["BTC/USDT", "ETH/USDT"],
                    sentiment=-0.2,
                    relevance=75.0,
                    market_impact="Potentially bearish for decentralized cryptocurrencies",
                ),
            ]
        )

    async def get_upcoming_events(self, hours_ahead: int = 48) -> list[EconomicEvent]:
        """Get upcoming economic events."""
        return [event for event in self._events if event.is_upcoming(hours_ahead)]

    async def get_recent_events(self, hours_back: int = 24) -> list[EconomicEvent]:
        """Get recently occurred events."""
        return [event for event in self._events if event.is_recent(hours_back)]

    async def get_important_events(self) -> list[EconomicEvent]:
        """Get events marked as important."""
        return [event for event in self._events if event.is_important]

    async def get_relevant_news(self, hours_back: int = 24) -> list[NewsArticle]:
        """Get recent relevant news articles."""
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        return [article for article in self._news if article.published_at >= cutoff_time]

    async def get_breaking_news(self) -> list[NewsArticle]:
        """Get breaking news articles."""
        return [article for article in self._news if article.is_breaking]

    async def get_events_by_symbol(self, symbol: str) -> list[EconomicEvent]:
        """Get events affecting a specific symbol."""
        return [event for event in self._events if symbol in event.symbols_affected]

    async def get_events_by_type(self, event_type: EventType) -> list[EconomicEvent]:
        """Get events of specific type."""
        return [event for event in self._events if event.event_type == event_type]

    async def get_events_by_impact(self, impact: EventImpact) -> list[EconomicEvent]:
        """Get events with specific impact level."""
        return [event for event in self._events if event.impact == impact]

    async def update_event_actual_impact(self, event_id: str, actual_impact: str) -> bool:
        """Update actual impact of an event after it occurs."""
        for event in self._events:
            if event.event_id == event_id:
                event.actual_impact = actual_impact
                logger.info(f"Updated actual impact for event {event_id}: {actual_impact}")
                return True
        return False

    async def get_calendar_summary(self) -> dict[str, Any]:
        """Get summary of current calendar status."""
        datetime.now()

        upcoming_24h = await self.get_upcoming_events(24)
        upcoming_48h = await self.get_upcoming_events(48)
        recent_events = await self.get_recent_events(24)
        important_events = await self.get_important_events()
        breaking_news = await self.get_breaking_news()
        relevant_news = await self.get_relevant_news(24)

        return {
            "status": "active",
            "last_update": self._last_update.isoformat() if self._last_update else None,
            "upcoming_events_24h": len(upcoming_24h),
            "upcoming_events_48h": len(upcoming_48h),
            "recent_events_24h": len(recent_events),
            "important_events": len(important_events),
            "breaking_news": len(breaking_news),
            "relevant_news_24h": len(relevant_news),
            "high_impact_events": len(await self.get_events_by_impact(EventImpact.HIGH)),
            "critical_events": len(await self.get_events_by_impact(EventImpact.CRITICAL)),
            "next_event": upcoming_24h[0].title if upcoming_24h else "No upcoming events",
        }

    async def search_events(self, query: str) -> list[EconomicEvent]:
        """Search events by title or description."""
        query = query.lower()
        results = []

        for event in self._events:
            if query in event.title.lower() or query in event.description.lower():
                results.append(event)

        return results

    async def get_sentiment_analysis(self) -> dict[str, Any]:
        """Get overall sentiment from news and events."""
        recent_news = await self.get_relevant_news(48)
        upcoming_events = await self.get_upcoming_events(48)

        # Calculate average sentiment
        news_sentiments = [article.sentiment for article in recent_news if article.sentiment is not None]
        event_sentiments = [event.sentiment_score for event in upcoming_events if event.sentiment_score is not None]

        all_sentiments = news_sentiments + event_sentiments

        if all_sentiments:
            avg_sentiment = sum(all_sentiments) / len(all_sentiments)
            sentiment_label = self._classify_sentiment(avg_sentiment)
        else:
            avg_sentiment = 0.0
            sentiment_label = "neutral"

        return {
            "average_sentiment": round(avg_sentiment, 3),
            "sentiment_label": sentiment_label,
            "news_articles_analyzed": len(recent_news),
            "events_analyzed": len(upcoming_events),
            "positive_news": len([s for s in news_sentiments if s > 0.1]),
            "negative_news": len([s for s in news_sentiments if s < -0.1]),
            "neutral_news": len([s for s in news_sentiments if -0.1 <= s <= 0.1]),
        }

    def _classify_sentiment(self, score: float) -> str:
        """Classify sentiment score into labels."""
        if score >= 0.5:
            return "very_positive"
        elif score >= 0.1:
            return "positive"
        elif score <= -0.5:
            return "very_negative"
        elif score <= -0.1:
            return "negative"
        else:
            return "neutral"

    async def add_custom_event(self, event: EconomicEvent) -> bool:
        """Add a custom economic event."""
        try:
            self._events.append(event)
            logger.info(f"Added custom event: {event.title}")
            return True
        except Exception as e:
            logger.error(f"Failed to add custom event: {e}")
            return False

    async def remove_event(self, event_id: str) -> bool:
        """Remove an event by ID."""
        try:
            self._events = [event for event in self._events if event.event_id != event_id]
            logger.info(f"Removed event: {event_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove event {event_id}: {e}")
            return False

    def clear_old_data(self, days_old: int = 7) -> None:
        """Clear old events and news."""
        cutoff_date = datetime.now() - timedelta(days=days_old)

        self._events = [event for event in self._events if event.timestamp >= cutoff_date]
        self._news = [news for news in self._news if news.published_at >= cutoff_date]

        logger.info(f"Cleared data older than {days_old} days")


# Global instance
_economic_calendar: EconomicCalendar | None = None


def get_economic_calendar() -> EconomicCalendar:
    """Get or create global economic calendar instance."""
    global _economic_calendar
    if _economic_calendar is None:
        _economic_calendar = EconomicCalendar()
    return _economic_calendar
