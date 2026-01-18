"""
Stablecoin Flow Tracker.

Tracks stablecoin market caps and flows:
- USDT, USDC, DAI, BUSD total market cap
- 24h/7d changes indicating money flow
- Stablecoin dominance % of total crypto market

Inflow (rising stablecoin mcap) = bullish (dry powder ready)
Outflow (falling stablecoin mcap) = bearish or rotation into crypto
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

import httpx

logger = logging.getLogger(__name__)

COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"

# Major stablecoins to track
STABLECOINS = [
    "tether",  # USDT
    "usd-coin",  # USDC
    "dai",  # DAI
    "first-digital-usd",  # FDUSD
    "true-usd",  # TUSD
    "frax",  # FRAX
    "pax-dollar",  # USDP
    "usdd",  # USDD
    "gemini-dollar",  # GUSD
    "paypal-usd",  # PYUSD
]


class FlowSignal(Enum):
    """Stablecoin flow signal."""

    STRONG_INFLOW = "strong_inflow"  # >5% 7d increase
    INFLOW = "inflow"  # 1-5% 7d increase
    NEUTRAL = "neutral"  # -1% to 1%
    OUTFLOW = "outflow"  # 1-5% 7d decrease
    STRONG_OUTFLOW = "strong_outflow"  # >5% 7d decrease


@dataclass
class StablecoinData:
    """Individual stablecoin data."""

    id: str
    symbol: str
    name: str
    market_cap: float
    market_cap_change_24h: float
    market_cap_change_7d: float | None
    price: float  # Should be ~$1
    volume_24h: float


@dataclass
class StablecoinFlowData:
    """Stablecoin flow analysis result."""

    timestamp: datetime
    total_market_cap: float
    total_market_cap_formatted: str
    change_24h_pct: float
    change_7d_pct: float | None
    dominance: float  # % of total crypto market
    flow_signal: FlowSignal
    flow_signal_ru: str
    stablecoins: list[StablecoinData]
    usdt_dominance: float  # USDT % of stablecoins
    total_volume_24h: float

    def to_dict(self) -> dict:
        """Convert to dictionary for API/MQTT."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "total_market_cap": self.total_market_cap,
            "total_market_cap_formatted": self.total_market_cap_formatted,
            "change_24h_pct": round(self.change_24h_pct, 2),
            "change_7d_pct": round(self.change_7d_pct, 2) if self.change_7d_pct else None,
            "dominance": round(self.dominance, 2),
            "flow_signal": self.flow_signal.value,
            "flow_signal_ru": self.flow_signal_ru,
            "flow_emoji": self._get_flow_emoji(),
            "usdt_dominance": round(self.usdt_dominance, 2),
            "total_volume_24h": self.total_volume_24h,
            "stablecoins": [
                {
                    "symbol": s.symbol,
                    "name": s.name,
                    "market_cap": s.market_cap,
                    "market_cap_formatted": self._format_number(s.market_cap),
                    "change_24h": round(s.market_cap_change_24h, 2),
                    "peg": round(s.price, 4),
                }
                for s in self.stablecoins
            ],
            "summary": self._get_summary(),
            "summary_ru": self._get_summary_ru(),
        }

    def _get_flow_emoji(self) -> str:
        """Get emoji for flow signal."""
        emoji_map = {
            FlowSignal.STRONG_INFLOW: "🟢🟢",
            FlowSignal.INFLOW: "🟢",
            FlowSignal.NEUTRAL: "⚪",
            FlowSignal.OUTFLOW: "🔴",
            FlowSignal.STRONG_OUTFLOW: "🔴🔴",
        }
        return emoji_map.get(self.flow_signal, "⚪")

    def _format_number(self, num: float) -> str:
        """Format large number to B/M notation."""
        if num >= 1_000_000_000:
            return f"${num / 1_000_000_000:.1f}B"
        if num >= 1_000_000:
            return f"${num / 1_000_000:.1f}M"
        return f"${num:,.0f}"

    def _get_summary(self) -> str:
        """Get English summary."""
        direction = "rising" if self.change_24h_pct > 0 else "falling"
        return f"Stablecoins {direction} {abs(self.change_24h_pct):.1f}% (24h), {self.dominance:.1f}% dominance"

    def _get_summary_ru(self) -> str:
        """Get Russian summary."""
        if self.change_24h_pct > 0:
            direction = "растут"
        else:
            direction = "падают"
        return f"Стейблкоины {direction} на {abs(self.change_24h_pct):.1f}% (24ч), доминация {self.dominance:.1f}%"


class StablecoinAnalyzer:
    """
    Analyzer for stablecoin flows.

    Tracks major stablecoins and calculates flow signals.
    """

    def __init__(self, timeout: float = 30.0):
        self._client: httpx.AsyncClient | None = None
        self._timeout = timeout
        self._prev_total_mcap: float | None = None

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

    async def analyze(self) -> StablecoinFlowData:
        """
        Analyze stablecoin market caps and flows.

        Returns:
            StablecoinFlowData with analysis
        """
        client = await self._get_client()

        # Fetch stablecoin data
        stablecoins = await self._fetch_stablecoin_data(client)

        # Fetch total crypto market cap for dominance calculation
        total_crypto_mcap = await self._fetch_total_market_cap(client)

        if not stablecoins:
            return self._create_empty_result()

        # Calculate totals
        total_stable_mcap = sum(s.market_cap for s in stablecoins)
        total_volume = sum(s.volume_24h for s in stablecoins)

        # Calculate 24h change (weighted by market cap)
        weighted_change_24h = sum(
            s.market_cap_change_24h * (s.market_cap / total_stable_mcap) for s in stablecoins if total_stable_mcap > 0
        )

        # Calculate 7d change if available
        change_7d = None
        stables_with_7d = [s for s in stablecoins if s.market_cap_change_7d is not None]
        if stables_with_7d:
            total_7d_mcap = sum(s.market_cap for s in stables_with_7d)
            if total_7d_mcap > 0:
                change_7d = sum((s.market_cap_change_7d or 0) * (s.market_cap / total_7d_mcap) for s in stables_with_7d)

        # Calculate dominance
        dominance = (total_stable_mcap / total_crypto_mcap * 100) if total_crypto_mcap > 0 else 0

        # USDT dominance within stablecoins
        usdt = next((s for s in stablecoins if s.symbol.upper() == "USDT"), None)
        usdt_dominance = (usdt.market_cap / total_stable_mcap * 100) if usdt and total_stable_mcap > 0 else 0

        # Determine flow signal based on 7d change
        flow_signal, flow_signal_ru = self._calculate_flow_signal(change_7d or weighted_change_24h)

        # Format total market cap
        total_formatted = self._format_large_number(total_stable_mcap)

        return StablecoinFlowData(
            timestamp=datetime.now(),
            total_market_cap=total_stable_mcap,
            total_market_cap_formatted=total_formatted,
            change_24h_pct=weighted_change_24h,
            change_7d_pct=change_7d,
            dominance=dominance,
            flow_signal=flow_signal,
            flow_signal_ru=flow_signal_ru,
            stablecoins=sorted(stablecoins, key=lambda x: x.market_cap, reverse=True),
            usdt_dominance=usdt_dominance,
            total_volume_24h=total_volume,
        )

    async def _fetch_stablecoin_data(self, client: httpx.AsyncClient) -> list[StablecoinData]:
        """Fetch stablecoin market data."""
        ids = ",".join(STABLECOINS)
        url = f"{COINGECKO_BASE_URL}/coins/markets"
        params = {
            "vs_currency": "usd",
            "ids": ids,
            "order": "market_cap_desc",
            "sparkline": "false",
            "price_change_percentage": "24h,7d",
        }

        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            stablecoins = []
            for coin in data:
                stablecoins.append(
                    StablecoinData(
                        id=coin["id"],
                        symbol=coin["symbol"].upper(),
                        name=coin["name"],
                        market_cap=coin.get("market_cap", 0) or 0,
                        market_cap_change_24h=coin.get("market_cap_change_percentage_24h", 0) or 0,
                        market_cap_change_7d=coin.get("price_change_percentage_7d_in_currency"),
                        price=coin.get("current_price", 1) or 1,
                        volume_24h=coin.get("total_volume", 0) or 0,
                    )
                )

            return stablecoins

        except Exception as e:
            logger.error(f"Failed to fetch stablecoin data: {e}")
            return []

    async def _fetch_total_market_cap(self, client: httpx.AsyncClient) -> float:
        """Fetch total crypto market cap."""
        url = f"{COINGECKO_BASE_URL}/global"

        try:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

            return data.get("data", {}).get("total_market_cap", {}).get("usd", 0)

        except Exception as e:
            logger.warning(f"Failed to fetch total market cap: {e}")
            return 0

    def _calculate_flow_signal(self, change_pct: float) -> tuple[FlowSignal, str]:
        """Calculate flow signal based on percentage change."""
        if change_pct >= 5:
            return FlowSignal.STRONG_INFLOW, "Сильный приток"
        if change_pct >= 1:
            return FlowSignal.INFLOW, "Приток"
        if change_pct <= -5:
            return FlowSignal.STRONG_OUTFLOW, "Сильный отток"
        if change_pct <= -1:
            return FlowSignal.OUTFLOW, "Отток"
        return FlowSignal.NEUTRAL, "Нейтрально"

    def _format_large_number(self, num: float) -> str:
        """Format large number to readable string."""
        if num >= 1_000_000_000_000:
            return f"${num / 1_000_000_000_000:.2f}T"
        if num >= 1_000_000_000:
            return f"${num / 1_000_000_000:.1f}B"
        if num >= 1_000_000:
            return f"${num / 1_000_000:.1f}M"
        return f"${num:,.0f}"

    def _create_empty_result(self) -> StablecoinFlowData:
        """Create empty result when data fetch fails."""
        return StablecoinFlowData(
            timestamp=datetime.now(),
            total_market_cap=0,
            total_market_cap_formatted="$0",
            change_24h_pct=0,
            change_7d_pct=None,
            dominance=0,
            flow_signal=FlowSignal.NEUTRAL,
            flow_signal_ru="Нет данных",
            stablecoins=[],
            usdt_dominance=0,
            total_volume_24h=0,
        )


# Global instance
_stablecoin_analyzer: StablecoinAnalyzer | None = None


def get_stablecoin_analyzer() -> StablecoinAnalyzer:
    """Get global stablecoin analyzer instance."""
    global _stablecoin_analyzer
    if _stablecoin_analyzer is None:
        _stablecoin_analyzer = StablecoinAnalyzer()
    return _stablecoin_analyzer
