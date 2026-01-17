"""
News Parser - Парсинг и анализ криптоновостей

Источники:
- CryptoPanic API (бесплатный план)
- CoinGecko News (через API)
- RSS feeds

Функции:
- Сбор новостей по монетам
- Фильтрация по watchlist
- Sentiment analysis (через Ollama)
- Breaking news detection
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import aiohttp
from config_loader import get_api_key
from database import CryptoDatabase, get_database

logger = logging.getLogger(__name__)


# API Endpoints
CRYPTOPANIC_URL = "https://cryptopanic.com/api/v1/posts/"
COINGECKO_NEWS_URL = "https://api.coingecko.com/api/v3/status_updates"


@dataclass
class NewsItem:
    """Одна новость"""

    id: str
    title: str
    source: str
    url: str
    published_at: int  # timestamp

    # Связанные монеты
    coins: list[str] = field(default_factory=list)

    # Sentiment
    sentiment: str = "neutral"  # 'positive', 'negative', 'neutral'
    sentiment_score: float = 0.0  # -1 to +1

    # Важность
    importance: str = "normal"  # 'breaking', 'important', 'normal'
    votes: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "source": self.source,
            "url": self.url,
            "published_at": self.published_at,
            "published_at_human": datetime.fromtimestamp(self.published_at).strftime(
                "%Y-%m-%d %H:%M"
            ),
            "coins": self.coins,
            "sentiment": self.sentiment,
            "sentiment_score": self.sentiment_score,
            "importance": self.importance,
        }


@dataclass
class NewsFeed:
    """Лента новостей"""

    timestamp: int

    # Новости
    items: list[NewsItem] = field(default_factory=list)
    total_count: int = 0

    # Статистика
    positive_count: int = 0
    negative_count: int = 0
    neutral_count: int = 0

    # Breaking news
    breaking_news: list[NewsItem] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "total_count": self.total_count,
            "statistics": {
                "positive": self.positive_count,
                "negative": self.negative_count,
                "neutral": self.neutral_count,
            },
            "overall_sentiment": self._get_overall_sentiment(),
            "breaking_news": [n.to_dict() for n in self.breaking_news],
            "recent_news": [n.to_dict() for n in self.items[:10]],
        }

    def _get_overall_sentiment(self) -> str:
        """Определить общий sentiment"""
        if self.positive_count > self.negative_count * 1.5:
            return "bullish"
        elif self.negative_count > self.positive_count * 1.5:
            return "bearish"
        else:
            return "neutral"

    def get_summary_ru(self) -> str:
        """Резюме на русском"""
        parts = [
            "📰 **Новости криптовалют**",
            f"Всего: {self.total_count} новостей",
            "",
            f"🟢 Позитивных: {self.positive_count}",
            f"🔴 Негативных: {self.negative_count}",
            f"⚪ Нейтральных: {self.neutral_count}",
            "",
        ]

        overall = self._get_overall_sentiment()
        if overall == "bullish":
            parts.append("📈 Общий фон: **позитивный**")
        elif overall == "bearish":
            parts.append("📉 Общий фон: **негативный**")
        else:
            parts.append("➡️ Общий фон: **нейтральный**")

        if self.breaking_news:
            parts.extend(["", "🚨 **Breaking News:**"])
            for news in self.breaking_news[:3]:
                parts.append(f"• {news.title}")

        return "\n".join(parts)


class NewsParser:
    """Парсер криптоновостей"""

    # Ключевые слова для определения sentiment
    POSITIVE_KEYWORDS = [
        "bullish",
        "surge",
        "rally",
        "growth",
        "adoption",
        "partnership",
        "approval",
        "launch",
        "breakthrough",
        "milestone",
        "record",
        "рост",
        "бычий",
        "одобрен",
        "партнёрство",
        "рекорд",
        "принят",
    ]

    NEGATIVE_KEYWORDS = [
        "bearish",
        "crash",
        "dump",
        "hack",
        "scam",
        "fraud",
        "ban",
        "investigation",
        "lawsuit",
        "delay",
        "cancel",
        "warning",
        "падение",
        "медвежий",
        "взлом",
        "мошенничество",
        "запрет",
        "иск",
    ]

    BREAKING_KEYWORDS = ["breaking", "just in", "urgent", "exclusive", "срочно", "важно"]

    def __init__(self, db: CryptoDatabase | None = None, cryptopanic_api_key: str = None):
        self.db = db or get_database()
        # API ключ из аргумента или из конфига
        self.api_key = cryptopanic_api_key or get_api_key("cryptopanic")
        self._session: aiohttp.ClientSession | None = None

        if self.api_key:
            logger.info("CryptoPanic API key configured")

    async def _get_session(self) -> aiohttp.ClientSession:
        """Получить HTTP сессию"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self):
        """Закрыть сессию"""
        if self._session and not self._session.closed:
            await self._session.close()

    def _analyze_sentiment_simple(self, text: str) -> tuple:
        """
        Простой анализ sentiment по ключевым словам

        Returns:
            (sentiment, score)
        """
        text_lower = text.lower()

        positive_count = sum(1 for kw in self.POSITIVE_KEYWORDS if kw in text_lower)
        negative_count = sum(1 for kw in self.NEGATIVE_KEYWORDS if kw in text_lower)

        if positive_count > negative_count:
            score = min(1.0, (positive_count - negative_count) * 0.2)
            return "positive", score
        elif negative_count > positive_count:
            score = max(-1.0, (positive_count - negative_count) * 0.2)
            return "negative", score
        else:
            return "neutral", 0.0

    def _is_breaking(self, text: str) -> bool:
        """Проверить, является ли новость breaking"""
        text_lower = text.lower()
        return any(kw in text_lower for kw in self.BREAKING_KEYWORDS)

    async def fetch_cryptopanic(
        self, currencies: list[str] = None, kind: str = "news", limit: int = 50
    ) -> list[NewsItem]:
        """
        Получить новости с CryptoPanic

        Args:
            currencies: Список валют (BTC, ETH)
            kind: Тип ('news', 'media', 'all')
            limit: Количество

        Returns:
            Список новостей
        """
        if not self.api_key:
            logger.info("CryptoPanic API key not configured")
            return []

        session = await self._get_session()

        params = {
            "auth_token": self.api_key,
            "kind": kind,
            "public": "true",
        }

        if currencies:
            params["currencies"] = ",".join(currencies)

        try:
            async with session.get(CRYPTOPANIC_URL, params=params) as response:
                if response.status != 200:
                    logger.error(f"CryptoPanic API error: {response.status}")
                    return []

                data = await response.json()

                items = []
                for post in data.get("results", [])[:limit]:
                    # Извлекаем монеты
                    coins = [c["code"] for c in post.get("currencies", [])]

                    # Анализируем sentiment
                    sentiment, score = self._analyze_sentiment_simple(post.get("title", ""))

                    # Votes
                    votes = post.get("votes", {})
                    if votes.get("positive", 0) > votes.get("negative", 0) * 2:
                        sentiment = "positive"
                        score = 0.5
                    elif votes.get("negative", 0) > votes.get("positive", 0) * 2:
                        sentiment = "negative"
                        score = -0.5

                    # Importance
                    importance = "normal"
                    if self._is_breaking(post.get("title", "")):
                        importance = "breaking"
                    elif votes.get("important", 0) > 5:
                        importance = "important"

                    item = NewsItem(
                        id=str(post.get("id")),
                        title=post.get("title", ""),
                        source=post.get("source", {}).get("title", "Unknown"),
                        url=post.get("url", ""),
                        published_at=int(
                            datetime.fromisoformat(
                                post.get("published_at", "").replace("Z", "+00:00")
                            ).timestamp()
                        )
                        if post.get("published_at")
                        else 0,
                        coins=coins,
                        sentiment=sentiment,
                        sentiment_score=score,
                        importance=importance,
                        votes=votes,
                    )
                    items.append(item)

                return items

        except Exception as e:
            logger.error(f"CryptoPanic error: {e}")
            return []

    async def fetch_coingecko_news(self, limit: int = 50) -> list[NewsItem]:
        """
        Получить новости с CoinGecko (status updates)
        """
        session = await self._get_session()

        try:
            async with session.get(COINGECKO_NEWS_URL) as response:
                if response.status != 200:
                    return []

                data = await response.json()

                items = []
                for update in data.get("status_updates", [])[:limit]:
                    sentiment, score = self._analyze_sentiment_simple(update.get("description", ""))

                    item = NewsItem(
                        id=f"cg_{update.get('created_at', '')}",
                        title=update.get("description", "")[:200],
                        source="CoinGecko",
                        url="https://www.coingecko.com/",
                        published_at=int(
                            datetime.fromisoformat(
                                update.get("created_at", "").replace("Z", "+00:00")
                            ).timestamp()
                        )
                        if update.get("created_at")
                        else 0,
                        coins=[update.get("project", {}).get("symbol", "").upper()],
                        sentiment=sentiment,
                        sentiment_score=score,
                    )
                    items.append(item)

                return items

        except Exception as e:
            logger.error(f"CoinGecko news error: {e}")
            return []

    async def get_news_feed(self, currencies: list[str] = None, hours: int = 24) -> NewsFeed:
        """
        Получить ленту новостей

        Args:
            currencies: Фильтр по валютам
            hours: За последние N часов

        Returns:
            NewsFeed
        """
        feed = NewsFeed(timestamp=int(datetime.now().timestamp() * 1000))

        # Собираем из всех источников
        tasks = [
            self.fetch_cryptopanic(currencies),
            self.fetch_coingecko_news(),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_news = []
        for result in results:
            if isinstance(result, list):
                all_news.extend(result)

        # Фильтруем по времени
        cutoff = int((datetime.now() - timedelta(hours=hours)).timestamp())
        all_news = [n for n in all_news if n.published_at >= cutoff]

        # Фильтруем по валютам если нужно
        if currencies:
            currencies_upper = [c.upper() for c in currencies]
            all_news = [
                n for n in all_news if not n.coins or any(c in currencies_upper for c in n.coins)
            ]

        # Сортируем по времени
        all_news.sort(key=lambda x: x.published_at, reverse=True)

        # Заполняем feed
        feed.items = all_news
        feed.total_count = len(all_news)

        feed.positive_count = sum(1 for n in all_news if n.sentiment == "positive")
        feed.negative_count = sum(1 for n in all_news if n.sentiment == "negative")
        feed.neutral_count = sum(1 for n in all_news if n.sentiment == "neutral")

        feed.breaking_news = [n for n in all_news if n.importance == "breaking"]

        return feed

    def filter_by_watchlist(self, news: list[NewsItem], watchlist: list[str]) -> list[NewsItem]:
        """
        Фильтровать новости по watchlist

        Args:
            news: Список новостей
            watchlist: Список отслеживаемых монет

        Returns:
            Отфильтрованный список
        """
        watchlist_upper = [c.upper() for c in watchlist]

        return [n for n in news if any(c in watchlist_upper for c in n.coins)]


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import json
    import os

    logging.basicConfig(level=logging.INFO)

    async def main():
        # API ключ из переменной окружения
        api_key = os.environ.get("CRYPTOPANIC_API_KEY")

        parser = NewsParser(cryptopanic_api_key=api_key)

        try:
            print("Fetching news...")
            feed = await parser.get_news_feed(currencies=["BTC", "ETH"], hours=24)

            print("\n" + "=" * 60)
            print("NEWS FEED")
            print("=" * 60)
            print(json.dumps(feed.to_dict(), indent=2, ensure_ascii=False))

            print("\n" + "=" * 60)
            print("SUMMARY (RU)")
            print("=" * 60)
            print(feed.get_summary_ru())

        finally:
            await parser.close()

    asyncio.run(main())
