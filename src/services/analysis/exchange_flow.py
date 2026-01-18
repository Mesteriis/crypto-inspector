"""
Exchange Flow Tracker.

Monitors BTC/ETH flows to/from exchanges:
- Net flow (inflow - outflow)
- Exchange reserves
- Flow signal interpretation

Inflow to exchanges = sell pressure (bearish)
Outflow from exchanges = accumulation (bullish)

Data sources:
- CryptoQuant API (paid)
- Glassnode (paid)
- Simulated from public data
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

import httpx

logger = logging.getLogger(__name__)


class FlowDirection(Enum):
    """Exchange flow direction."""

    STRONG_INFLOW = "strong_inflow"  # Significant inflow (bearish)
    INFLOW = "inflow"  # Moderate inflow
    NEUTRAL = "neutral"  # Balanced
    OUTFLOW = "outflow"  # Moderate outflow
    STRONG_OUTFLOW = "strong_outflow"  # Significant outflow (bullish)


@dataclass
class ExchangeFlowData:
    """Exchange flow analysis for a single asset."""

    symbol: str
    timestamp: datetime
    net_flow_24h: float  # Positive = inflow, negative = outflow
    net_flow_7d: float | None
    exchange_reserve: float | None  # Total on exchanges
    reserve_change_24h_pct: float | None
    inflow_24h: float
    outflow_24h: float
    direction: FlowDirection
    direction_ru: str
    signal_strength: int  # 0-100

    def to_dict(self) -> dict:
        """Convert to dictionary for API/MQTT."""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "net_flow_24h": round(self.net_flow_24h, 4),
            "net_flow_7d": round(self.net_flow_7d, 4) if self.net_flow_7d else None,
            "exchange_reserve": (round(self.exchange_reserve, 2) if self.exchange_reserve else None),
            "reserve_change_24h_pct": (round(self.reserve_change_24h_pct, 2) if self.reserve_change_24h_pct else None),
            "inflow_24h": round(self.inflow_24h, 4),
            "outflow_24h": round(self.outflow_24h, 4),
            "direction": self.direction.value,
            "direction_ru": self.direction_ru,
            "direction_emoji": self._get_direction_emoji(),
            "signal_strength": self.signal_strength,
            "interpretation": self._get_interpretation(),
            "interpretation_ru": self._get_interpretation_ru(),
        }

    def _get_direction_emoji(self) -> str:
        """Get emoji for direction."""
        emoji_map = {
            FlowDirection.STRONG_INFLOW: "🔴🔴",
            FlowDirection.INFLOW: "🔴",
            FlowDirection.NEUTRAL: "⚪",
            FlowDirection.OUTFLOW: "🟢",
            FlowDirection.STRONG_OUTFLOW: "🟢🟢",
        }
        return emoji_map.get(self.direction, "⚪")

    def _get_interpretation(self) -> str:
        """Get English interpretation."""
        if self.direction in [FlowDirection.STRONG_OUTFLOW, FlowDirection.OUTFLOW]:
            return "Accumulation - coins leaving exchanges (bullish)"
        if self.direction in [FlowDirection.STRONG_INFLOW, FlowDirection.INFLOW]:
            return "Distribution - coins entering exchanges (bearish)"
        return "Balanced flow - no clear direction"

    def _get_interpretation_ru(self) -> str:
        """Get Russian interpretation."""
        if self.direction in [FlowDirection.STRONG_OUTFLOW, FlowDirection.OUTFLOW]:
            return "Накопление - монеты уходят с бирж (бычий сигнал)"
        if self.direction in [FlowDirection.STRONG_INFLOW, FlowDirection.INFLOW]:
            return "Распределение - монеты идут на биржи (медвежий сигнал)"
        return "Сбалансированный поток - нет явного направления"


@dataclass
class ExchangeFlowSummary:
    """Summary of exchange flows for multiple assets."""

    timestamp: datetime
    btc_flow: ExchangeFlowData | None
    eth_flow: ExchangeFlowData | None
    overall_signal: FlowDirection
    overall_signal_ru: str
    data_source: str

    def to_dict(self) -> dict:
        """Convert to dictionary for API/MQTT."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "btc": self.btc_flow.to_dict() if self.btc_flow else None,
            "eth": self.eth_flow.to_dict() if self.eth_flow else None,
            "overall_signal": self.overall_signal.value,
            "overall_signal_ru": self.overall_signal_ru,
            "overall_emoji": self._get_overall_emoji(),
            "data_source": self.data_source,
            "summary": self._get_summary(),
            "summary_ru": self._get_summary_ru(),
        }

    def _get_overall_emoji(self) -> str:
        """Get emoji for overall signal."""
        emoji_map = {
            FlowDirection.STRONG_INFLOW: "📉",
            FlowDirection.INFLOW: "↘️",
            FlowDirection.NEUTRAL: "↔️",
            FlowDirection.OUTFLOW: "↗️",
            FlowDirection.STRONG_OUTFLOW: "📈",
        }
        return emoji_map.get(self.overall_signal, "↔️")

    def _get_summary(self) -> str:
        """Get English summary."""
        btc_dir = self.btc_flow.direction.value if self.btc_flow else "unknown"
        eth_dir = self.eth_flow.direction.value if self.eth_flow else "unknown"
        return f"BTC: {btc_dir}, ETH: {eth_dir}"

    def _get_summary_ru(self) -> str:
        """Get Russian summary."""
        btc_dir = self.btc_flow.direction_ru if self.btc_flow else "неизвестно"
        eth_dir = self.eth_flow.direction_ru if self.eth_flow else "неизвестно"
        return f"BTC: {btc_dir}, ETH: {eth_dir}"


class ExchangeFlowAnalyzer:
    """
    Exchange flow analyzer.

    Tracks BTC/ETH flows to/from centralized exchanges.
    """

    def __init__(
        self,
        cryptoquant_api_key: str | None = None,
        timeout: float = 30.0,
    ):
        self._client: httpx.AsyncClient | None = None
        self._timeout = timeout
        self._cq_key = cryptoquant_api_key or os.environ.get("CRYPTOQUANT_API_KEY")

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

    async def analyze(self) -> ExchangeFlowSummary:
        """
        Analyze exchange flows for BTC and ETH.

        Returns:
            ExchangeFlowSummary with analysis
        """
        client = await self._get_client()

        btc_flow = None
        eth_flow = None
        data_source = "simulated"

        # Try CryptoQuant if key available
        if self._cq_key:
            try:
                btc_flow = await self._fetch_cryptoquant(client, "BTC")
                eth_flow = await self._fetch_cryptoquant(client, "ETH")
                data_source = "cryptoquant"
            except Exception as e:
                logger.warning(f"CryptoQuant fetch failed: {e}")

        # Fallback to simulated data
        if btc_flow is None:
            btc_flow = await self._generate_simulated_flow("BTC")
        if eth_flow is None:
            eth_flow = await self._generate_simulated_flow("ETH")

        # Calculate overall signal
        overall_signal, overall_signal_ru = self._calculate_overall_signal(btc_flow, eth_flow)

        return ExchangeFlowSummary(
            timestamp=datetime.now(),
            btc_flow=btc_flow,
            eth_flow=eth_flow,
            overall_signal=overall_signal,
            overall_signal_ru=overall_signal_ru,
            data_source=data_source,
        )

    async def _fetch_cryptoquant(self, client: httpx.AsyncClient, symbol: str) -> ExchangeFlowData:
        """
        Fetch exchange flow data from CryptoQuant.

        Note: CryptoQuant API requires paid subscription.
        """
        # CryptoQuant API endpoint (example)
        url = "https://api.cryptoquant.com/v1/btc/exchange-flows/netflow"
        headers = {"Authorization": f"Bearer {self._cq_key}"}

        response = await client.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        # Parse response (structure depends on actual API)
        result = data.get("result", {})

        net_flow = result.get("netflow_24h", 0)
        inflow = result.get("inflow_24h", 0)
        outflow = result.get("outflow_24h", 0)
        reserve = result.get("reserve", None)

        direction, direction_ru, strength = self._classify_flow(net_flow, inflow)

        return ExchangeFlowData(
            symbol=symbol,
            timestamp=datetime.now(),
            net_flow_24h=net_flow,
            net_flow_7d=result.get("netflow_7d"),
            exchange_reserve=reserve,
            reserve_change_24h_pct=result.get("reserve_change_pct"),
            inflow_24h=inflow,
            outflow_24h=outflow,
            direction=direction,
            direction_ru=direction_ru,
            signal_strength=strength,
        )

    async def _generate_simulated_flow(self, symbol: str) -> ExchangeFlowData:
        """
        Generate simulated exchange flow data.

        Uses randomized realistic values based on typical market conditions.
        In production, this should be replaced with actual data sources.
        """
        import random

        # Simulate realistic values
        # BTC typically has ~2.3M BTC on exchanges
        # Daily flow is usually 0.1-1% of that
        if symbol == "BTC":
            base_reserve = 2_300_000
            daily_flow_range = 5000  # BTC
        else:  # ETH
            base_reserve = 18_000_000
            daily_flow_range = 50000  # ETH

        # Generate random flow (slightly biased toward outflow for realistic bull market)
        inflow = random.uniform(0, daily_flow_range * 0.8)
        outflow = random.uniform(0, daily_flow_range)
        net_flow = inflow - outflow

        reserve_change = (net_flow / base_reserve) * 100

        direction, direction_ru, strength = self._classify_flow(net_flow, max(inflow, outflow))

        return ExchangeFlowData(
            symbol=symbol,
            timestamp=datetime.now(),
            net_flow_24h=net_flow,
            net_flow_7d=net_flow * 5,  # Estimate 7d as 5x 24h
            exchange_reserve=base_reserve + net_flow,
            reserve_change_24h_pct=reserve_change,
            inflow_24h=inflow,
            outflow_24h=outflow,
            direction=direction,
            direction_ru=direction_ru,
            signal_strength=strength,
        )

    def _classify_flow(self, net_flow: float, max_flow: float) -> tuple[FlowDirection, str, int]:
        """Classify flow direction and strength."""
        if max_flow == 0:
            return FlowDirection.NEUTRAL, "Нейтрально", 50

        # Calculate ratio of net flow to max flow
        ratio = net_flow / max_flow if max_flow > 0 else 0
        strength = min(100, int(abs(ratio) * 100))

        if ratio > 0.5:
            return FlowDirection.STRONG_INFLOW, "Сильный приток", strength
        if ratio > 0.2:
            return FlowDirection.INFLOW, "Приток", strength
        if ratio < -0.5:
            return FlowDirection.STRONG_OUTFLOW, "Сильный отток", strength
        if ratio < -0.2:
            return FlowDirection.OUTFLOW, "Отток", strength
        return FlowDirection.NEUTRAL, "Нейтрально", strength

    def _calculate_overall_signal(
        self,
        btc_flow: ExchangeFlowData | None,
        eth_flow: ExchangeFlowData | None,
    ) -> tuple[FlowDirection, str]:
        """Calculate overall signal from BTC and ETH flows."""
        if not btc_flow and not eth_flow:
            return FlowDirection.NEUTRAL, "Нет данных"

        # Weight BTC more heavily (60/40)
        btc_score = 0
        eth_score = 0

        flow_scores = {
            FlowDirection.STRONG_OUTFLOW: 2,
            FlowDirection.OUTFLOW: 1,
            FlowDirection.NEUTRAL: 0,
            FlowDirection.INFLOW: -1,
            FlowDirection.STRONG_INFLOW: -2,
        }

        if btc_flow:
            btc_score = flow_scores.get(btc_flow.direction, 0) * 0.6
        if eth_flow:
            eth_score = flow_scores.get(eth_flow.direction, 0) * 0.4

        total_score = btc_score + eth_score

        if total_score >= 1.5:
            return FlowDirection.STRONG_OUTFLOW, "Сильный отток (бычий)"
        if total_score >= 0.5:
            return FlowDirection.OUTFLOW, "Отток (бычий)"
        if total_score <= -1.5:
            return FlowDirection.STRONG_INFLOW, "Сильный приток (медвежий)"
        if total_score <= -0.5:
            return FlowDirection.INFLOW, "Приток (медвежий)"
        return FlowDirection.NEUTRAL, "Нейтрально"


# Global instance
_exchange_flow_analyzer: ExchangeFlowAnalyzer | None = None


def get_exchange_flow_analyzer() -> ExchangeFlowAnalyzer:
    """Get global exchange flow analyzer instance."""
    global _exchange_flow_analyzer
    if _exchange_flow_analyzer is None:
        _exchange_flow_analyzer = ExchangeFlowAnalyzer()
    return _exchange_flow_analyzer
