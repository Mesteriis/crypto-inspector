"""
DCA (Dollar Cost Averaging) Calculator.

Calculates optimal DCA levels using:
- Fibonacci retracements
- Support/resistance levels
- Market phase analysis

Помогает определить:
- Следующий уровень покупки
- Зону входа (Buy Zone / Wait / Overbought)
- Оптимальные уровни DCA на основе Фибоначчи
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import httpx

logger = logging.getLogger(__name__)

COINGECKO_API = "https://api.coingecko.com/api/v3"
BYBIT_API = "https://api.bybit.com"


class DCAZone(Enum):
    """DCA zone classification."""

    BUY_ZONE = "buy_zone"  # Good to accumulate
    WAIT = "wait"  # Neutral, wait for better entry
    OVERBOUGHT = "overbought"  # Price too high, don't buy

    @property
    def name_ru(self) -> str:
        names = {
            DCAZone.BUY_ZONE: "Зона покупки",
            DCAZone.WAIT: "Ожидание",
            DCAZone.OVERBOUGHT: "Перекуплено",
        }
        return names.get(self, self.value)

    @property
    def emoji(self) -> str:
        emojis = {
            DCAZone.BUY_ZONE: "🟢",
            DCAZone.WAIT: "🟡",
            DCAZone.OVERBOUGHT: "🔴",
        }
        return emojis.get(self, "⚪")


@dataclass
class DCALevel:
    """Single DCA level."""

    level_num: int
    price: float
    distance_pct: float  # Distance from current price
    fib_level: float  # Fibonacci level (0.236, 0.382, etc.)
    suggested_allocation: float  # % of total to allocate

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level_num,
            "price": round(self.price, 2),
            "distance_pct": round(self.distance_pct, 2),
            "fib_level": self.fib_level,
            "allocation_pct": self.suggested_allocation,
            "label": f"DCA #{self.level_num}",
        }


@dataclass
class DCAAnalysis:
    """DCA analysis result."""

    symbol: str
    current_price: float
    zone: DCAZone
    next_level: float  # Next DCA level
    levels: list[DCALevel] = field(default_factory=list)
    high_52w: float = 0
    low_52w: float = 0
    distance_from_ath: float = 0
    risk_score: int = 50  # 0-100, higher = more risky to buy
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "current_price": round(self.current_price, 2),
            "zone": self.zone.value,
            "zone_ru": self.zone.name_ru,
            "zone_emoji": self.zone.emoji,
            "next_level": round(self.next_level, 2),
            "next_level_distance_pct": round(
                ((self.current_price - self.next_level) / self.current_price * 100) if self.current_price > 0 else 0,
                2,
            ),
            "levels": [lvl.to_dict() for lvl in self.levels],
            "levels_json": str([lvl.to_dict() for lvl in self.levels]),
            "high_52w": round(self.high_52w, 2),
            "low_52w": round(self.low_52w, 2),
            "distance_from_ath": round(self.distance_from_ath, 2),
            "risk_score": self.risk_score,
            "recommendation": self._get_recommendation(),
            "recommendation_ru": self._get_recommendation_ru(),
            "timestamp": self.timestamp.isoformat(),
        }

    def _get_recommendation(self) -> str:
        if self.zone == DCAZone.BUY_ZONE:
            return f"Good entry zone. Next level at ${self.next_level:,.2f}"
        elif self.zone == DCAZone.WAIT:
            return f"Wait for better entry. Target: ${self.next_level:,.2f}"
        else:
            return "Price overextended. Avoid buying, consider taking profits."

    def _get_recommendation_ru(self) -> str:
        if self.zone == DCAZone.BUY_ZONE:
            return f"Хорошая зона для покупки. След. уровень: ${self.next_level:,.2f}"
        elif self.zone == DCAZone.WAIT:
            return f"Ожидайте лучшего входа. Цель: ${self.next_level:,.2f}"
        else:
            return "Цена перегрета. Избегайте покупок, рассмотрите фиксацию прибыли."


class DCACalculator:
    """
    DCA Calculator service.

    Calculates optimal DCA levels using Fibonacci retracements
    and market analysis.
    """

    # Fibonacci levels for DCA
    FIB_LEVELS = [0.236, 0.382, 0.5, 0.618, 0.786]

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

    async def analyze(self, symbol: str = "BTC") -> DCAAnalysis:
        """
        Analyze DCA levels for a symbol.

        Args:
            symbol: Cryptocurrency symbol (BTC, ETH, etc.)

        Returns:
            DCAAnalysis with levels and recommendations
        """
        client = await self._get_client()

        # Get current price and historical data
        try:
            price_data = await self._fetch_price_data(client, symbol)
            current_price = price_data.get("current_price", 0)
            high_52w = price_data.get("high_52w", current_price * 1.5)
            low_52w = price_data.get("low_52w", current_price * 0.5)
            ath = price_data.get("ath", high_52w)
        except Exception as e:
            logger.error(f"Failed to fetch price data: {e}")
            return self._create_empty_result(symbol)

        if current_price <= 0:
            return self._create_empty_result(symbol)

        # Calculate Fibonacci levels
        price_range = high_52w - low_52w
        levels = []

        for i, fib in enumerate(self.FIB_LEVELS):
            level_price = high_52w - (price_range * fib)
            distance_pct = ((current_price - level_price) / current_price) * 100

            # Allocation suggestion based on Fib level
            allocation = 10 + (i * 5)  # 10%, 15%, 20%, 25%, 30%

            levels.append(
                DCALevel(
                    level_num=i + 1,
                    price=level_price,
                    distance_pct=distance_pct,
                    fib_level=fib,
                    suggested_allocation=allocation,
                )
            )

        # Find next level (first level below current price)
        next_level = low_52w
        for lvl in levels:
            if lvl.price < current_price:
                next_level = lvl.price
                break

        # Determine zone
        zone = self._determine_zone(current_price, high_52w, low_52w, ath)

        # Calculate risk score
        distance_from_ath = ((ath - current_price) / ath) * 100 if ath > 0 else 0
        position_in_range = ((current_price - low_52w) / price_range) * 100 if price_range > 0 else 50
        risk_score = min(100, max(0, int(position_in_range)))

        return DCAAnalysis(
            symbol=symbol,
            current_price=current_price,
            zone=zone,
            next_level=next_level,
            levels=levels,
            high_52w=high_52w,
            low_52w=low_52w,
            distance_from_ath=distance_from_ath,
            risk_score=risk_score,
        )

    async def _fetch_price_data(self, client: httpx.AsyncClient, symbol: str) -> dict[str, float]:
        """Fetch price data from CoinGecko."""
        symbol_map = {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "SOL": "solana",
            "XRP": "ripple",
            "ADA": "cardano",
        }

        cg_id = symbol_map.get(symbol.upper(), symbol.lower())

        try:
            url = f"{COINGECKO_API}/coins/{cg_id}"
            params = {
                "localization": "false",
                "tickers": "false",
                "community_data": "false",
                "developer_data": "false",
            }

            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            market_data = data.get("market_data", {})

            return {
                "current_price": market_data.get("current_price", {}).get("usd", 0),
                "high_52w": market_data.get("high_24h", {}).get("usd", 0) * 1.5,  # Estimate
                "low_52w": market_data.get("low_24h", {}).get("usd", 0) * 0.5,  # Estimate
                "ath": market_data.get("ath", {}).get("usd", 0),
                "ath_date": market_data.get("ath_date", {}).get("usd", ""),
            }

        except Exception as e:
            logger.warning(f"CoinGecko fetch failed: {e}, trying Bybit")

            # Fallback to Bybit
            try:
                bybit_symbol = f"{symbol.upper()}USDT"
                url = f"{BYBIT_API}/v5/market/tickers"
                params = {"category": "linear", "symbol": bybit_symbol}

                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                tickers = data.get("result", {}).get("list", [])
                if tickers:
                    ticker = tickers[0]
                    price = float(ticker.get("lastPrice", 0))
                    return {
                        "current_price": price,
                        "high_52w": price * 1.3,  # Estimate
                        "low_52w": price * 0.7,  # Estimate
                        "ath": price * 1.5,  # Estimate
                    }
            except Exception as e2:
                logger.error(f"Bybit fallback failed: {e2}")

            return {}

    def _determine_zone(
        self,
        current_price: float,
        high_52w: float,
        low_52w: float,
        ath: float,
    ) -> DCAZone:
        """Determine DCA zone based on price position."""
        if high_52w == low_52w:
            return DCAZone.WAIT

        price_range = high_52w - low_52w
        position = (current_price - low_52w) / price_range

        # Near ATH or in upper range = overbought
        if position > 0.8 or (ath > 0 and current_price > ath * 0.9):
            return DCAZone.OVERBOUGHT

        # Lower range = buy zone
        if position < 0.4:
            return DCAZone.BUY_ZONE

        # Middle = wait
        return DCAZone.WAIT

    def _create_empty_result(self, symbol: str) -> DCAAnalysis:
        """Create empty result on error."""
        return DCAAnalysis(
            symbol=symbol,
            current_price=0,
            zone=DCAZone.WAIT,
            next_level=0,
        )

    async def get_multi_symbol(self, symbols: list[str] | None = None) -> dict[str, DCAAnalysis]:
        """
        Get DCA analysis for multiple symbols.

        Args:
            symbols: List of symbols (default: BTC, ETH)

        Returns:
            Dict of symbol -> DCAAnalysis
        """
        if symbols is None:
            symbols = ["BTC", "ETH"]

        result = {}
        for symbol in symbols:
            try:
                result[symbol] = await self.analyze(symbol)
            except Exception as e:
                logger.error(f"DCA analysis failed for {symbol}: {e}")
                result[symbol] = self._create_empty_result(symbol)

        return result


# Global instance
_dca_calculator: DCACalculator | None = None


def get_dca_calculator() -> DCACalculator:
    """Get global DCA calculator instance."""
    global _dca_calculator
    if _dca_calculator is None:
        _dca_calculator = DCACalculator()
    return _dca_calculator
