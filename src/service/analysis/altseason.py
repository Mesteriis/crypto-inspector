"""
Altcoin Season Index Calculator.

Calculates the Altcoin Season Index based on:
- Top 50 altcoins performance vs BTC over 90 days
- Index 0-100: 75+ = Altseason, 25- = BTC Season

Data source: CoinGecko API (free, no API key required)
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

import httpx

logger = logging.getLogger(__name__)

COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"

# Top altcoins to track (excluding stablecoins and wrapped tokens)
TOP_ALTCOINS = [
    "ethereum",
    "binancecoin",
    "solana",
    "ripple",
    "cardano",
    "avalanche-2",
    "dogecoin",
    "polkadot",
    "chainlink",
    "tron",
    "polygon",
    "shiba-inu",
    "litecoin",
    "uniswap",
    "cosmos",
    "ethereum-classic",
    "stellar",
    "monero",
    "okb",
    "aptos",
    "near",
    "filecoin",
    "arbitrum",
    "optimism",
    "vechain",
    "aave",
    "maker",
    "the-graph",
    "fantom",
    "theta-token",
    "algorand",
    "flow",
    "axie-infinity",
    "decentraland",
    "the-sandbox",
    "eos",
    "neo",
    "kucoin-shares",
    "iota",
    "tezos",
    "pancakeswap-token",
    "curve-dao-token",
    "gala",
    "enjincoin",
    "chiliz",
    "zilliqa",
    "loopring",
    "1inch",
    "compound-governance-token",
    "yearn-finance",
]


class SeasonStatus(Enum):
    """Market season status."""

    BTC_SEASON = "btc_season"
    NEUTRAL = "neutral"
    ALTSEASON = "altseason"


@dataclass
class AltseasonData:
    """Altcoin season analysis result."""

    timestamp: datetime
    index: int  # 0-100
    status: SeasonStatus
    status_ru: str
    alts_outperforming: int  # Count of alts beating BTC
    total_alts_analyzed: int
    btc_performance_90d: float  # BTC 90-day change %
    avg_alt_performance_90d: float  # Average alt 90-day change %
    top_performers: list[dict]  # Top 5 performing alts
    worst_performers: list[dict]  # Worst 5 performing alts

    def to_dict(self) -> dict:
        """Convert to dictionary for API."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "index": self.index,
            "status": self.status.value,
            "status_ru": self.status_ru,
            "status_emoji": self._get_status_emoji(),
            "alts_outperforming": self.alts_outperforming,
            "total_analyzed": self.total_alts_analyzed,
            "btc_performance_90d": round(self.btc_performance_90d, 2),
            "avg_alt_performance_90d": round(self.avg_alt_performance_90d, 2),
            "top_performers": self.top_performers,
            "worst_performers": self.worst_performers,
            "summary": self._get_summary(),
            "summary_ru": self._get_summary_ru(),
        }

    def _get_status_emoji(self) -> str:
        """Get emoji for status."""
        if self.status == SeasonStatus.ALTSEASON:
            return "🚀"
        if self.status == SeasonStatus.BTC_SEASON:
            return "🟠"
        return "⚖️"

    def _get_summary(self) -> str:
        """Get English summary."""
        pct = round(self.alts_outperforming / self.total_alts_analyzed * 100)
        if self.status == SeasonStatus.ALTSEASON:
            return f"Altseason! {pct}% of alts outperforming BTC"
        if self.status == SeasonStatus.BTC_SEASON:
            return f"BTC Season - only {pct}% of alts beating BTC"
        return f"Neutral market - {pct}% of alts vs BTC"

    def _get_summary_ru(self) -> str:
        """Get Russian summary."""
        pct = round(self.alts_outperforming / self.total_alts_analyzed * 100)
        if self.status == SeasonStatus.ALTSEASON:
            return f"Альтсезон! {pct}% альтов обгоняют BTC"
        if self.status == SeasonStatus.BTC_SEASON:
            return f"Сезон BTC - только {pct}% альтов лучше BTC"
        return f"Нейтральный рынок - {pct}% альтов vs BTC"


class AltseasonAnalyzer:
    """
    Analyzer for Altcoin Season Index.

    Uses CoinGecko API to fetch 90-day performance data.
    """

    def __init__(self, timeout: float = 30.0):
        self._client: httpx.AsyncClient | None = None
        self._timeout = timeout

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self._timeout,
                headers={"Accept": "application/json"},
            )
        return self._client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def analyze(self) -> AltseasonData:
        """
        Calculate Altcoin Season Index.

        Returns:
            AltseasonData with index and analysis
        """
        client = await self._get_client()

        # Fetch BTC performance
        btc_perf = await self._fetch_coin_performance(client, "bitcoin")

        # Fetch altcoin performances
        alt_performances = []
        for coin_id in TOP_ALTCOINS[:50]:  # Limit to 50
            try:
                perf = await self._fetch_coin_performance(client, coin_id)
                if perf is not None:
                    alt_performances.append({"id": coin_id, "performance": perf})
            except Exception as e:
                logger.warning(f"Failed to fetch {coin_id}: {e}")
                continue

        if not alt_performances:
            logger.error("No altcoin data fetched")
            return self._create_empty_result()

        # Calculate how many alts outperform BTC
        alts_beating_btc = sum(1 for alt in alt_performances if alt["performance"] > btc_perf)
        total_alts = len(alt_performances)

        # Calculate index (0-100)
        index = round((alts_beating_btc / total_alts) * 100)

        # Determine status
        if index >= 75:
            status = SeasonStatus.ALTSEASON
            status_ru = "Альтсезон"
        elif index <= 25:
            status = SeasonStatus.BTC_SEASON
            status_ru = "Сезон BTC"
        else:
            status = SeasonStatus.NEUTRAL
            status_ru = "Нейтрально"

        # Sort for top/worst performers
        sorted_alts = sorted(alt_performances, key=lambda x: x["performance"], reverse=True)

        avg_alt_perf = sum(a["performance"] for a in alt_performances) / total_alts

        return AltseasonData(
            timestamp=datetime.now(),
            index=index,
            status=status,
            status_ru=status_ru,
            alts_outperforming=alts_beating_btc,
            total_alts_analyzed=total_alts,
            btc_performance_90d=btc_perf,
            avg_alt_performance_90d=avg_alt_perf,
            top_performers=[{"coin": a["id"], "performance": round(a["performance"], 2)} for a in sorted_alts[:5]],
            worst_performers=[{"coin": a["id"], "performance": round(a["performance"], 2)} for a in sorted_alts[-5:]],
        )

    async def _fetch_coin_performance(self, client: httpx.AsyncClient, coin_id: str) -> float:
        """
        Fetch 90-day price performance for a coin.

        Args:
            client: HTTP client
            coin_id: CoinGecko coin ID

        Returns:
            90-day price change percentage
        """
        url = f"{COINGECKO_BASE_URL}/coins/{coin_id}/market_chart"
        params = {"vs_currency": "usd", "days": "90", "interval": "daily"}

        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            prices = data.get("prices", [])
            if len(prices) < 2:
                return 0.0

            start_price = prices[0][1]
            end_price = prices[-1][1]

            if start_price == 0:
                return 0.0

            return ((end_price - start_price) / start_price) * 100

        except Exception as e:
            logger.warning(f"Error fetching {coin_id} performance: {e}")
            raise

    def _create_empty_result(self) -> AltseasonData:
        """Create empty result when data fetch fails."""
        return AltseasonData(
            timestamp=datetime.now(),
            index=50,
            status=SeasonStatus.NEUTRAL,
            status_ru="Нет данных",
            alts_outperforming=0,
            total_alts_analyzed=0,
            btc_performance_90d=0,
            avg_alt_performance_90d=0,
            top_performers=[],
            worst_performers=[],
        )


# Alternative: Use CoinGecko simple endpoint for faster calculation
class AltseasonAnalyzerFast:
    """
    Fast Altcoin Season analyzer using market data endpoint.

    Uses single API call to get all coin data.
    """

    def __init__(self, timeout: float = 30.0):
        self._client: httpx.AsyncClient | None = None
        self._timeout = timeout

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self._timeout,
                headers={"Accept": "application/json"},
            )
        return self._client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def analyze(self) -> AltseasonData:
        """
        Calculate Altcoin Season Index using market data.

        Uses price_change_percentage_90d from markets endpoint.
        """
        client = await self._get_client()

        url = f"{COINGECKO_BASE_URL}/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": 100,
            "page": 1,
            "sparkline": "false",
            "price_change_percentage": "90d",
        }

        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            # Find BTC
            btc_data = next((c for c in data if c["id"] == "bitcoin"), None)
            btc_perf = btc_data.get("price_change_percentage_90d_in_currency", 0) if btc_data else 0

            # Filter altcoins (exclude BTC, stablecoins, wrapped)
            stablecoins = {"tether", "usd-coin", "dai", "binance-usd", "trueusd"}
            wrapped = {"wrapped-bitcoin", "steth", "weth"}
            exclude = {"bitcoin"} | stablecoins | wrapped

            altcoins = [
                c
                for c in data
                if c["id"] not in exclude and c.get("price_change_percentage_90d_in_currency") is not None
            ]

            if not altcoins:
                return self._create_empty_result(btc_perf)

            # Calculate stats
            alts_beating_btc = sum(
                1 for c in altcoins if c.get("price_change_percentage_90d_in_currency", 0) > btc_perf
            )
            total = len(altcoins)
            index = round((alts_beating_btc / total) * 100)

            # Status
            if index >= 75:
                status = SeasonStatus.ALTSEASON
                status_ru = "Альтсезон"
            elif index <= 25:
                status = SeasonStatus.BTC_SEASON
                status_ru = "Сезон BTC"
            else:
                status = SeasonStatus.NEUTRAL
                status_ru = "Нейтрально"

            # Sort for top/worst
            sorted_alts = sorted(
                altcoins,
                key=lambda x: x.get("price_change_percentage_90d_in_currency", 0),
                reverse=True,
            )

            avg_perf = sum(c.get("price_change_percentage_90d_in_currency", 0) for c in altcoins) / total

            return AltseasonData(
                timestamp=datetime.now(),
                index=index,
                status=status,
                status_ru=status_ru,
                alts_outperforming=alts_beating_btc,
                total_alts_analyzed=total,
                btc_performance_90d=btc_perf,
                avg_alt_performance_90d=avg_perf,
                top_performers=[
                    {
                        "coin": c["symbol"].upper(),
                        "name": c["name"],
                        "performance": round(c.get("price_change_percentage_90d_in_currency", 0), 2),
                    }
                    for c in sorted_alts[:5]
                ],
                worst_performers=[
                    {
                        "coin": c["symbol"].upper(),
                        "name": c["name"],
                        "performance": round(c.get("price_change_percentage_90d_in_currency", 0), 2),
                    }
                    for c in sorted_alts[-5:]
                ],
            )

        except Exception as e:
            logger.error(f"Altseason analysis failed: {e}")
            return self._create_empty_result(0)

    def _create_empty_result(self, btc_perf: float = 0) -> AltseasonData:
        """Create empty result."""
        return AltseasonData(
            timestamp=datetime.now(),
            index=50,
            status=SeasonStatus.NEUTRAL,
            status_ru="Нет данных",
            alts_outperforming=0,
            total_alts_analyzed=0,
            btc_performance_90d=btc_perf,
            avg_alt_performance_90d=0,
            top_performers=[],
            worst_performers=[],
        )


# Global instance
_altseason_analyzer: AltseasonAnalyzerFast | None = None


def get_altseason_analyzer() -> AltseasonAnalyzerFast:
    """Get global altseason analyzer instance."""
    global _altseason_analyzer
    if _altseason_analyzer is None:
        _altseason_analyzer = AltseasonAnalyzerFast()
    return _altseason_analyzer
