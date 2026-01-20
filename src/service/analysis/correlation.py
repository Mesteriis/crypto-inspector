"""
Correlation Tracker.

Tracks correlations between:
- BTC/ETH
- BTC/S&P500
- BTC/Gold (XAU)
- BTC/DXY (Dollar Index)

Помогает определить:
- Корреляцию между активами
- Момент декорреляции (возможность диверсификации)
- Связь с традиционными рынками
"""

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import httpx

logger = logging.getLogger(__name__)

COINGECKO_API = "https://api.coingecko.com/api/v3"
YAHOO_FINANCE_API = "https://query1.finance.yahoo.com/v8/finance/chart"


class CorrelationStatus(Enum):
    """Correlation status classification."""

    STRONG_POSITIVE = "strong_positive"  # > 0.7
    POSITIVE = "positive"  # 0.3 to 0.7
    NEUTRAL = "neutral"  # -0.3 to 0.3
    NEGATIVE = "negative"  # -0.7 to -0.3
    STRONG_NEGATIVE = "strong_negative"  # < -0.7
    DIVERGING = "diverging"  # Breaking historical correlation

    @property
    def name_ru(self) -> str:
        names = {
            CorrelationStatus.STRONG_POSITIVE: "Сильная корреляция",
            CorrelationStatus.POSITIVE: "Положительная корреляция",
            CorrelationStatus.NEUTRAL: "Нейтрально",
            CorrelationStatus.NEGATIVE: "Отрицательная корреляция",
            CorrelationStatus.STRONG_NEGATIVE: "Сильная обратная",
            CorrelationStatus.DIVERGING: "Декорреляция",
        }
        return names.get(self, self.value)

    @property
    def emoji(self) -> str:
        emojis = {
            CorrelationStatus.STRONG_POSITIVE: "🔗",
            CorrelationStatus.POSITIVE: "📈",
            CorrelationStatus.NEUTRAL: "➡️",
            CorrelationStatus.NEGATIVE: "📉",
            CorrelationStatus.STRONG_NEGATIVE: "⚡",
            CorrelationStatus.DIVERGING: "🔀",
        }
        return emojis.get(self, "⚪")


@dataclass
class CorrelationPair:
    """Correlation between two assets."""

    asset1: str
    asset2: str
    correlation_30d: float
    correlation_90d: float
    status: CorrelationStatus
    is_diverging: bool
    historical_avg: float = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "pair": f"{self.asset1}/{self.asset2}",
            "asset1": self.asset1,
            "asset2": self.asset2,
            "correlation_30d": round(self.correlation_30d, 3),
            "correlation_90d": round(self.correlation_90d, 3),
            "status": self.status.value,
            "status_ru": self.status.name_ru,
            "status_emoji": self.status.emoji,
            "is_diverging": self.is_diverging,
            "historical_avg": round(self.historical_avg, 3),
            "interpretation": self._get_interpretation(),
            "interpretation_ru": self._get_interpretation_ru(),
        }

    def _get_interpretation(self) -> str:
        if self.is_diverging:
            return f"{self.asset1} breaking correlation with {self.asset2}"
        if self.status == CorrelationStatus.STRONG_POSITIVE:
            return f"{self.asset1} moves together with {self.asset2}"
        if self.status == CorrelationStatus.STRONG_NEGATIVE:
            return f"{self.asset1} moves opposite to {self.asset2}"
        return f"{self.asset1} has weak correlation with {self.asset2}"

    def _get_interpretation_ru(self) -> str:
        if self.is_diverging:
            return f"{self.asset1} теряет корреляцию с {self.asset2}"
        if self.status == CorrelationStatus.STRONG_POSITIVE:
            return f"{self.asset1} движется вместе с {self.asset2}"
        if self.status == CorrelationStatus.STRONG_NEGATIVE:
            return f"{self.asset1} движется противоположно {self.asset2}"
        return f"{self.asset1} слабо коррелирует с {self.asset2}"


@dataclass
class CorrelationAnalysis:
    """Complete correlation analysis."""

    timestamp: datetime
    btc_eth: CorrelationPair | None = None
    btc_sp500: CorrelationPair | None = None
    btc_gold: CorrelationPair | None = None
    btc_dxy: CorrelationPair | None = None
    overall_status: CorrelationStatus = CorrelationStatus.NEUTRAL
    pairs: list[CorrelationPair] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "btc_eth": self.btc_eth.to_dict() if self.btc_eth else None,
            "btc_sp500": self.btc_sp500.to_dict() if self.btc_sp500 else None,
            "btc_gold": self.btc_gold.to_dict() if self.btc_gold else None,
            "btc_dxy": self.btc_dxy.to_dict() if self.btc_dxy else None,
            "overall_status": self.overall_status.value,
            "overall_status_ru": self.overall_status.name_ru,
            "pairs": [p.to_dict() for p in self.pairs],
            "summary": self._get_summary(),
            "summary_ru": self._get_summary_ru(),
        }

    def _get_summary(self) -> str:
        if self.btc_eth and self.btc_eth.is_diverging:
            return "BTC/ETH correlation breaking down"
        if self.btc_sp500 and self.btc_sp500.correlation_30d > 0.7:
            return "BTC highly correlated with stocks"
        return "Normal correlation environment"

    def _get_summary_ru(self) -> str:
        if self.btc_eth and self.btc_eth.is_diverging:
            return "Корреляция BTC/ETH нарушается"
        if self.btc_sp500 and self.btc_sp500.correlation_30d > 0.7:
            return "BTC сильно коррелирует с акциями"
        return "Нормальная корреляционная среда"


class CorrelationTracker:
    """
    Correlation tracking service.

    Calculates rolling correlations between crypto and traditional assets.
    """

    def __init__(self, timeout: float = 30.0):
        self._client: httpx.AsyncClient | None = None
        self._timeout = timeout

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self._timeout,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "Mozilla/5.0",
                },
            )
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def analyze(self) -> CorrelationAnalysis:
        """
        Perform full correlation analysis.

        Returns:
            CorrelationAnalysis with all pairs
        """
        client = await self._get_client()

        # Fetch price data
        btc_prices = await self._fetch_crypto_prices(client, "bitcoin", 90)
        eth_prices = await self._fetch_crypto_prices(client, "ethereum", 90)
        sp500_prices = await self._fetch_yahoo_prices(client, "^GSPC", 90)
        gold_prices = await self._fetch_yahoo_prices(client, "GC=F", 90)
        dxy_prices = await self._fetch_yahoo_prices(client, "DX-Y.NYB", 90)

        pairs = []

        # BTC/ETH correlation
        btc_eth = None
        if btc_prices and eth_prices:
            btc_eth = self._calculate_correlation("BTC", "ETH", btc_prices, eth_prices, historical_avg=0.85)
            pairs.append(btc_eth)

        # BTC/S&P500 correlation
        btc_sp500 = None
        if btc_prices and sp500_prices:
            btc_sp500 = self._calculate_correlation("BTC", "S&P500", btc_prices, sp500_prices, historical_avg=0.4)
            pairs.append(btc_sp500)

        # BTC/Gold correlation
        btc_gold = None
        if btc_prices and gold_prices:
            btc_gold = self._calculate_correlation("BTC", "Gold", btc_prices, gold_prices, historical_avg=0.2)
            pairs.append(btc_gold)

        # BTC/DXY correlation (usually negative)
        btc_dxy = None
        if btc_prices and dxy_prices:
            btc_dxy = self._calculate_correlation("BTC", "DXY", btc_prices, dxy_prices, historical_avg=-0.3)
            pairs.append(btc_dxy)

        # Determine overall status
        overall_status = self._determine_overall_status(pairs)

        return CorrelationAnalysis(
            timestamp=datetime.now(),
            btc_eth=btc_eth,
            btc_sp500=btc_sp500,
            btc_gold=btc_gold,
            btc_dxy=btc_dxy,
            overall_status=overall_status,
            pairs=pairs,
        )

    async def _fetch_crypto_prices(self, client: httpx.AsyncClient, coin_id: str, days: int) -> list[float]:
        """Fetch crypto prices from CoinGecko."""
        try:
            url = f"{COINGECKO_API}/coins/{coin_id}/market_chart"
            params = {"vs_currency": "usd", "days": days}

            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            prices = [p[1] for p in data.get("prices", [])]
            return prices

        except Exception as e:
            logger.warning(f"Failed to fetch {coin_id} prices: {e}")
            return []

    async def _fetch_yahoo_prices(self, client: httpx.AsyncClient, symbol: str, days: int) -> list[float]:
        """Fetch prices from Yahoo Finance."""
        try:
            end_time = int(datetime.now().timestamp())
            start_time = int((datetime.now() - timedelta(days=days)).timestamp())

            url = f"{YAHOO_FINANCE_API}/{symbol}"
            params = {
                "period1": start_time,
                "period2": end_time,
                "interval": "1d",
            }

            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            result = data.get("chart", {}).get("result", [])
            if result:
                prices = result[0].get("indicators", {}).get("quote", [{}])[0].get("close", [])
                # Filter out None values
                return [p for p in prices if p is not None]

            return []

        except Exception as e:
            logger.warning(f"Failed to fetch {symbol} from Yahoo: {e}")
            return []

    def _calculate_correlation(
        self,
        asset1: str,
        asset2: str,
        prices1: list[float],
        prices2: list[float],
        historical_avg: float = 0,
    ) -> CorrelationPair:
        """Calculate correlation between two price series."""
        # Align series lengths
        min_len = min(len(prices1), len(prices2))
        if min_len < 10:
            return CorrelationPair(
                asset1=asset1,
                asset2=asset2,
                correlation_30d=0,
                correlation_90d=0,
                status=CorrelationStatus.NEUTRAL,
                is_diverging=False,
                historical_avg=historical_avg,
            )

        p1 = prices1[-min_len:]
        p2 = prices2[-min_len:]

        # Calculate returns
        returns1 = [(p1[i] - p1[i - 1]) / p1[i - 1] for i in range(1, len(p1)) if p1[i - 1] != 0]
        returns2 = [(p2[i] - p2[i - 1]) / p2[i - 1] for i in range(1, len(p2)) if p2[i - 1] != 0]

        # Ensure equal lengths
        min_ret_len = min(len(returns1), len(returns2))
        returns1 = returns1[:min_ret_len]
        returns2 = returns2[:min_ret_len]

        # 30-day correlation
        corr_30d = self._pearson_correlation(returns1[-30:], returns2[-30:])

        # 90-day correlation
        corr_90d = self._pearson_correlation(returns1, returns2)

        # Determine status
        status = self._classify_correlation(corr_30d)

        # Check for divergence (significant change from historical)
        is_diverging = abs(corr_30d - historical_avg) > 0.3

        return CorrelationPair(
            asset1=asset1,
            asset2=asset2,
            correlation_30d=corr_30d,
            correlation_90d=corr_90d,
            status=status,
            is_diverging=is_diverging,
            historical_avg=historical_avg,
        )

    def _pearson_correlation(self, x: list[float], y: list[float]) -> float:
        """Calculate Pearson correlation coefficient."""
        if len(x) != len(y) or len(x) < 2:
            return 0

        n = len(x)
        mean_x = sum(x) / n
        mean_y = sum(y) / n

        numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        sum_sq_x = sum((xi - mean_x) ** 2 for xi in x)
        sum_sq_y = sum((yi - mean_y) ** 2 for yi in y)

        denominator = math.sqrt(sum_sq_x * sum_sq_y)

        if denominator == 0:
            return 0

        return numerator / denominator

    def _classify_correlation(self, corr: float) -> CorrelationStatus:
        """Classify correlation value."""
        if corr > 0.7:
            return CorrelationStatus.STRONG_POSITIVE
        if corr > 0.3:
            return CorrelationStatus.POSITIVE
        if corr > -0.3:
            return CorrelationStatus.NEUTRAL
        if corr > -0.7:
            return CorrelationStatus.NEGATIVE
        return CorrelationStatus.STRONG_NEGATIVE

    def _determine_overall_status(self, pairs: list[CorrelationPair]) -> CorrelationStatus:
        """Determine overall correlation status."""
        if any(p.is_diverging for p in pairs):
            return CorrelationStatus.DIVERGING

        if pairs:
            avg_corr = sum(p.correlation_30d for p in pairs) / len(pairs)
            return self._classify_correlation(avg_corr)

        return CorrelationStatus.NEUTRAL


# Global instance
_correlation_tracker: CorrelationTracker | None = None


def get_correlation_tracker() -> CorrelationTracker:
    """Get global correlation tracker instance."""
    global _correlation_tracker
    if _correlation_tracker is None:
        _correlation_tracker = CorrelationTracker()
    return _correlation_tracker
