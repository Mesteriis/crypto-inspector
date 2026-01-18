"""
Volatility Index Tracker.

Tracks market volatility:
- Historical volatility (7d, 30d, 90d)
- Volatility percentile
- "Calm before storm" detection

Помогает определить:
- Текущий уровень волатильности
- Исторический контекст
- Потенциальные резкие движения
"""

import logging
import math
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

import httpx

logger = logging.getLogger(__name__)

COINGECKO_API = "https://api.coingecko.com/api/v3"


class VolatilityStatus(Enum):
    """Volatility status classification."""

    EXTREME_LOW = "extreme_low"  # < 10th percentile
    LOW = "low"  # 10-25th percentile
    NORMAL = "normal"  # 25-75th percentile
    HIGH = "high"  # 75-90th percentile
    EXTREME = "extreme"  # > 90th percentile

    @property
    def name_ru(self) -> str:
        names = {
            VolatilityStatus.EXTREME_LOW: "Экстремально низкая",
            VolatilityStatus.LOW: "Низкая",
            VolatilityStatus.NORMAL: "Нормальная",
            VolatilityStatus.HIGH: "Высокая",
            VolatilityStatus.EXTREME: "Экстремальная",
        }
        return names.get(self, self.value)

    @property
    def emoji(self) -> str:
        emojis = {
            VolatilityStatus.EXTREME_LOW: "😴",
            VolatilityStatus.LOW: "🟢",
            VolatilityStatus.NORMAL: "🟡",
            VolatilityStatus.HIGH: "🟠",
            VolatilityStatus.EXTREME: "🔴",
        }
        return emojis.get(self, "⚪")


@dataclass
class VolatilityData:
    """Volatility analysis data."""

    symbol: str
    timestamp: datetime
    volatility_7d: float  # Annualized %
    volatility_30d: float
    volatility_90d: float
    percentile: int  # 0-100
    status: VolatilityStatus
    bb_width: float  # Bollinger Band width
    is_calm_before_storm: bool
    avg_historical: float
    current_price: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "volatility_7d": round(self.volatility_7d, 2),
            "volatility_30d": round(self.volatility_30d, 2),
            "volatility_90d": round(self.volatility_90d, 2),
            "percentile": self.percentile,
            "status": self.status.value,
            "status_ru": self.status.name_ru,
            "status_emoji": self.status.emoji,
            "bb_width": round(self.bb_width, 4),
            "is_calm_before_storm": self.is_calm_before_storm,
            "avg_historical": round(self.avg_historical, 2),
            "current_price": round(self.current_price, 2),
            "interpretation": self._get_interpretation(),
            "interpretation_ru": self._get_interpretation_ru(),
        }

    def _get_interpretation(self) -> str:
        if self.is_calm_before_storm:
            return "WARNING: Volatility compression detected - expect big move"
        if self.status == VolatilityStatus.EXTREME:
            return "High volatility - use caution, consider reducing position size"
        if self.status == VolatilityStatus.EXTREME_LOW:
            return "Very low volatility - consolidation phase"
        return f"Volatility at {self.percentile}th percentile"

    def _get_interpretation_ru(self) -> str:
        if self.is_calm_before_storm:
            return "ВНИМАНИЕ: Сжатие волатильности - ожидайте резкое движение"
        if self.status == VolatilityStatus.EXTREME:
            return "Высокая волатильность - осторожность, уменьшите размер позиции"
        if self.status == VolatilityStatus.EXTREME_LOW:
            return "Очень низкая волатильность - фаза консолидации"
        return f"Волатильность на {self.percentile} перцентиле"


class VolatilityTracker:
    """
    Volatility tracking service.

    Calculates historical volatility and percentile rankings.
    """

    # Historical volatility benchmarks (approximate annualized %)
    HISTORICAL_RANGES = {
        "BTC": {"low": 40, "avg": 65, "high": 100},
        "ETH": {"low": 50, "avg": 80, "high": 120},
    }

    def __init__(self, timeout: float = 30.0):
        self._client: httpx.AsyncClient | None = None
        self._timeout = timeout

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self._timeout,
                headers={"Accept": "application/json"},
            )
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def analyze(self, symbol: str = "BTC") -> VolatilityData:
        """
        Analyze volatility for a symbol.

        Args:
            symbol: Cryptocurrency symbol

        Returns:
            VolatilityData with volatility metrics
        """
        client = await self._get_client()

        # Fetch price data
        prices = await self._fetch_prices(client, symbol, 90)

        if len(prices) < 7:
            return self._create_empty_result(symbol)

        # Calculate returns
        returns = [(prices[i] - prices[i - 1]) / prices[i - 1] for i in range(1, len(prices)) if prices[i - 1] != 0]

        # Calculate volatility for different periods
        vol_7d = self._calculate_volatility(returns[-7:])
        vol_30d = self._calculate_volatility(returns[-30:]) if len(returns) >= 30 else vol_7d
        vol_90d = self._calculate_volatility(returns) if len(returns) >= 90 else vol_30d

        # Calculate Bollinger Band width (proxy for volatility)
        bb_width = self._calculate_bb_width(prices[-20:])

        # Determine percentile based on historical data
        percentile = self._calculate_percentile(vol_30d, symbol)

        # Determine status
        status = self._classify_volatility(percentile)

        # Check for "calm before storm"
        is_calm = self._detect_calm_before_storm(returns, bb_width, symbol)

        # Historical average
        hist_ranges = self.HISTORICAL_RANGES.get(symbol.upper(), {"avg": 70})
        avg_historical = hist_ranges["avg"]

        return VolatilityData(
            symbol=symbol,
            timestamp=datetime.now(),
            volatility_7d=vol_7d,
            volatility_30d=vol_30d,
            volatility_90d=vol_90d,
            percentile=percentile,
            status=status,
            bb_width=bb_width,
            is_calm_before_storm=is_calm,
            avg_historical=avg_historical,
            current_price=prices[-1] if prices else 0,
        )

    async def _fetch_prices(self, client: httpx.AsyncClient, symbol: str, days: int) -> list[float]:
        """Fetch daily closing prices."""
        symbol_map = {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "SOL": "solana",
        }

        cg_id = symbol_map.get(symbol.upper(), symbol.lower())

        try:
            url = f"{COINGECKO_API}/coins/{cg_id}/market_chart"
            params = {"vs_currency": "usd", "days": days}

            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            prices = [p[1] for p in data.get("prices", [])]
            return prices

        except Exception as e:
            logger.error(f"Failed to fetch prices for {symbol}: {e}")
            return []

    def _calculate_volatility(self, returns: list[float]) -> float:
        """
        Calculate annualized volatility from returns.

        Returns volatility as percentage.
        """
        if len(returns) < 2:
            return 0

        # Standard deviation of returns
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
        std_dev = math.sqrt(variance)

        # Annualize (assuming daily returns, 365 days)
        annualized_vol = std_dev * math.sqrt(365) * 100

        return annualized_vol

    def _calculate_bb_width(self, prices: list[float]) -> float:
        """Calculate Bollinger Band width as volatility proxy."""
        if len(prices) < 20:
            return 0

        # 20-period SMA
        sma = sum(prices) / len(prices)

        # Standard deviation
        variance = sum((p - sma) ** 2 for p in prices) / len(prices)
        std_dev = math.sqrt(variance)

        # BB width = (Upper - Lower) / Middle
        upper = sma + 2 * std_dev
        lower = sma - 2 * std_dev

        if sma == 0:
            return 0

        bb_width = (upper - lower) / sma

        return bb_width

    def _calculate_percentile(self, volatility: float, symbol: str) -> int:
        """Calculate volatility percentile based on historical ranges."""
        hist = self.HISTORICAL_RANGES.get(symbol.upper(), {"low": 40, "avg": 70, "high": 100})

        low = hist["low"]
        avg = hist["avg"]
        high = hist["high"]

        if volatility <= low:
            # Map to 0-25
            return int((volatility / low) * 25)
        elif volatility <= avg:
            # Map to 25-50
            return int(25 + ((volatility - low) / (avg - low)) * 25)
        elif volatility <= high:
            # Map to 50-75
            return int(50 + ((volatility - avg) / (high - avg)) * 25)
        else:
            # Map to 75-100
            extra = min((volatility - high) / high, 1)
            return int(75 + extra * 25)

    def _classify_volatility(self, percentile: int) -> VolatilityStatus:
        """Classify volatility based on percentile."""
        if percentile < 10:
            return VolatilityStatus.EXTREME_LOW
        if percentile < 25:
            return VolatilityStatus.LOW
        if percentile < 75:
            return VolatilityStatus.NORMAL
        if percentile < 90:
            return VolatilityStatus.HIGH
        return VolatilityStatus.EXTREME

    def _detect_calm_before_storm(self, returns: list[float], bb_width: float, symbol: str) -> bool:
        """
        Detect potential "calm before storm" scenario.

        This occurs when:
        1. Current volatility is very low
        2. BB width is compressed
        3. Historical patterns suggest incoming move
        """
        if len(returns) < 7:
            return False

        # Recent volatility
        recent_vol = self._calculate_volatility(returns[-7:])

        # Historical thresholds
        hist = self.HISTORICAL_RANGES.get(symbol.upper(), {"low": 40})
        low_threshold = hist["low"] * 0.7  # 30% below historical low

        # Conditions for calm before storm:
        # 1. Very low recent volatility
        # 2. Narrow BB width
        if recent_vol < low_threshold and bb_width < 0.05:
            return True

        return False

    def _create_empty_result(self, symbol: str) -> VolatilityData:
        """Create empty result on error."""
        return VolatilityData(
            symbol=symbol,
            timestamp=datetime.now(),
            volatility_7d=0,
            volatility_30d=0,
            volatility_90d=0,
            percentile=50,
            status=VolatilityStatus.NORMAL,
            bb_width=0,
            is_calm_before_storm=False,
            avg_historical=70,
            current_price=0,
        )

    async def get_multi_symbol(self, symbols: list[str] | None = None) -> dict[str, VolatilityData]:
        """Get volatility for multiple symbols."""
        if symbols is None:
            symbols = ["BTC", "ETH"]

        result = {}
        for symbol in symbols:
            try:
                result[symbol] = await self.analyze(symbol)
            except Exception as e:
                logger.error(f"Volatility analysis failed for {symbol}: {e}")
                result[symbol] = self._create_empty_result(symbol)

        return result


# Global instance
_volatility_tracker: VolatilityTracker | None = None


def get_volatility_tracker() -> VolatilityTracker:
    """Get global volatility tracker instance."""
    global _volatility_tracker
    if _volatility_tracker is None:
        _volatility_tracker = VolatilityTracker()
    return _volatility_tracker
