"""
Altcoin Season Index Calculator.

Calculates the Altcoin Season Index based on:
- Top 50 altcoins performance vs BTC over 90 days
- Index 0-100: 75+ = Altseason, 25- = BTC Season

Data source: CoinGecko API with retry and backoff
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from core.http_client import get_coingecko_client

logger = logging.getLogger(__name__)


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
            "alts_outperforming": self.alts_outperforming,
            "total_analyzed": self.total_alts_analyzed,
            "btc_performance_90d": round(self.btc_performance_90d, 2),
            "avg_alt_performance_90d": round(self.avg_alt_performance_90d, 2),
            "top_performers": self.top_performers,
            "worst_performers": self.worst_performers,
            "summary": self._get_summary(),
            "summary_ru": self._get_summary_ru(),
        }

    def _get_summary(self) -> str:
        """Get English summary."""
        if self.total_alts_analyzed == 0:
            return "No data available"
        pct = round(self.alts_outperforming / self.total_alts_analyzed * 100)
        if self.status == SeasonStatus.ALTSEASON:
            return f"Altseason! {pct}% of alts outperforming BTC"
        if self.status == SeasonStatus.BTC_SEASON:
            return f"BTC Season - only {pct}% of alts beating BTC"
        return f"Neutral market - {pct}% of alts vs BTC"

    def _get_summary_ru(self) -> str:
        """Get Russian summary."""
        if self.total_alts_analyzed == 0:
            return "Нет данных"
        pct = round(self.alts_outperforming / self.total_alts_analyzed * 100)
        if self.status == SeasonStatus.ALTSEASON:
            return f"Альтсезон! {pct}% альтов обгоняют BTC"
        if self.status == SeasonStatus.BTC_SEASON:
            return f"Сезон BTC - только {pct}% альтов лучше BTC"
        return f"Нейтральный рынок - {pct}% альтов vs BTC"


class AltseasonAnalyzer:
    """
    Altcoin Season analyzer using CoinGecko markets endpoint.
    
    Uses resilient HTTP client with retry and backoff to avoid 429 errors.
    Single API call to get all coin data with 90d performance.
    """

    # Minimum number of altcoins required for valid analysis
    MIN_ALTCOINS_REQUIRED = 30

    async def close(self) -> None:
        """Close HTTP client (managed by global client)."""
        pass  # Client is managed globally

    async def analyze(self) -> AltseasonData:
        """
        Calculate Altcoin Season Index using market data.
        
        Uses price_change_percentage_30d as approximation for 90d performance.
        CoinGecko free tier doesn't support 90d directly.
        
        Returns:
            AltseasonData with index and analysis
            
        Raises:
            RuntimeError: If not enough altcoin data received
        """
        client = get_coingecko_client()

        # CoinGecko supports: 1h,24h,7d,14d,30d,200d,1y
        # Use 30d as approximation for quarterly performance
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": 100,
            "page": 1,
            "sparkline": "false",
            "price_change_percentage": "30d",  # 30d available, 90d not supported
        }

        data = await client.get("/coins/markets", params=params)
        
        if not data:
            raise RuntimeError("Failed to fetch market data from CoinGecko")

        # Find BTC
        btc_data = next((c for c in data if c["id"] == "bitcoin"), None)
        if not btc_data:
            raise RuntimeError("BTC data not found in CoinGecko response")
            
        # Use 30d performance as proxy for quarterly
        btc_perf = btc_data.get("price_change_percentage_30d_in_currency", 0) or 0

        # Filter altcoins (exclude BTC, stablecoins, wrapped)
        stablecoins = {"tether", "usd-coin", "dai", "binance-usd", "trueusd", "first-digital-usd"}
        wrapped = {"wrapped-bitcoin", "steth", "weth"}
        exclude = {"bitcoin"} | stablecoins | wrapped

        altcoins = [
            c
            for c in data
            if c["id"] not in exclude and c.get("price_change_percentage_30d_in_currency") is not None
        ]

        if len(altcoins) < self.MIN_ALTCOINS_REQUIRED:
            raise RuntimeError(
                f"Not enough altcoin data: got {len(altcoins)}, need {self.MIN_ALTCOINS_REQUIRED}"
            )

        # Calculate stats
        alts_beating_btc = sum(
            1 for c in altcoins if (c.get("price_change_percentage_30d_in_currency") or 0) > btc_perf
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
            key=lambda x: x.get("price_change_percentage_30d_in_currency") or 0,
            reverse=True,
        )

        avg_perf = sum(c.get("price_change_percentage_30d_in_currency") or 0 for c in altcoins) / total

        logger.info(f"Altseason analysis: index={index}, alts={total}, beating_btc={alts_beating_btc}")

        return AltseasonData(
            timestamp=datetime.now(),
            index=index,
            status=status,
            status_ru=status_ru,
            alts_outperforming=alts_beating_btc,
            total_alts_analyzed=total,
            btc_performance_90d=btc_perf,  # Actually 30d, but keeping field name for compatibility
            avg_alt_performance_90d=avg_perf,
            top_performers=[
                {
                    "coin": c["symbol"].upper(),
                    "name": c["name"],
                    "performance": round(c.get("price_change_percentage_30d_in_currency") or 0, 2),
                }
                for c in sorted_alts[:5]
            ],
            worst_performers=[
                {
                    "coin": c["symbol"].upper(),
                    "name": c["name"],
                    "performance": round(c.get("price_change_percentage_30d_in_currency") or 0, 2),
                }
                for c in sorted_alts[-5:]
            ],
        )


# Backward compatibility alias
AltseasonAnalyzerFast = AltseasonAnalyzer

# Global instance
_altseason_analyzer: AltseasonAnalyzer | None = None


def get_altseason_analyzer() -> AltseasonAnalyzer:
    """Get global altseason analyzer instance."""
    global _altseason_analyzer
    if _altseason_analyzer is None:
        _altseason_analyzer = AltseasonAnalyzer()
    return _altseason_analyzer
