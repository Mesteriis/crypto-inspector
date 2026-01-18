"""
Arbitrage Scanner.

Scans for arbitrage opportunities:
- Price spreads between exchanges
- Funding rate arbitrage
- Spot-futures basis

Помогает находить:
- Спреды цен между биржами
- Арбитраж фандинга
- Базис спот-фьючерс
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import httpx

logger = logging.getLogger(__name__)

BYBIT_API = "https://api.bybit.com"
BINANCE_API = "https://api.binance.com"
OKX_API = "https://www.okx.com"


class ArbitrageOpportunity(Enum):
    """Arbitrage opportunity level."""

    NONE = "none"  # < 0.1% spread
    LOW = "low"  # 0.1-0.3% spread
    GOOD = "good"  # 0.3-0.5% spread
    EXCELLENT = "excellent"  # > 0.5% spread

    @property
    def name_ru(self) -> str:
        names = {
            ArbitrageOpportunity.NONE: "Нет",
            ArbitrageOpportunity.LOW: "Низкая",
            ArbitrageOpportunity.GOOD: "Хорошая",
            ArbitrageOpportunity.EXCELLENT: "Отличная",
        }
        return names.get(self, self.value)

    @property
    def emoji(self) -> str:
        return {
            "none": "⚪",
            "low": "🟡",
            "good": "🟢",
            "excellent": "💰",
        }.get(self.value, "⚪")


@dataclass
class PriceSpread:
    """Price spread between exchanges."""

    symbol: str
    exchange_low: str
    exchange_high: str
    price_low: float
    price_high: float
    spread_pct: float
    spread_usd: float
    opportunity: ArbitrageOpportunity

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "exchange_low": self.exchange_low,
            "exchange_high": self.exchange_high,
            "price_low": round(self.price_low, 2),
            "price_high": round(self.price_high, 2),
            "spread_pct": round(self.spread_pct, 3),
            "spread_usd": round(self.spread_usd, 2),
            "opportunity": self.opportunity.value,
            "opportunity_ru": self.opportunity.name_ru,
            "opportunity_emoji": self.opportunity.emoji,
            "description": f"Buy on {self.exchange_low}, sell on {self.exchange_high}",
            "description_ru": f"Купить на {self.exchange_low}, продать на {self.exchange_high}",
        }


@dataclass
class FundingArbitrage:
    """Funding rate arbitrage opportunity."""

    symbol: str
    exchange: str
    funding_rate: float
    annualized_rate: float
    direction: str  # "long" or "short"
    next_funding_time: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "exchange": self.exchange,
            "funding_rate": round(self.funding_rate * 100, 4),
            "funding_rate_str": f"{self.funding_rate * 100:.4f}%",
            "annualized_rate": round(self.annualized_rate, 2),
            "annualized_str": f"{self.annualized_rate:.1f}%",
            "direction": self.direction,
            "direction_ru": "Шорт (получать)" if self.direction == "short" else "Лонг (платить)",
            "next_funding": self.next_funding_time.isoformat() if self.next_funding_time else None,
            "strategy": self._strategy_text(),
        }

    def _strategy_text(self) -> str:
        """Get strategy description."""
        if self.direction == "short":
            return "Short perp, long spot"
        return "Long perp, short spot"


@dataclass
class ArbitrageAnalysis:
    """Complete arbitrage analysis."""

    timestamp: datetime
    spreads: list[PriceSpread] = field(default_factory=list)
    funding_arbs: list[FundingArbitrage] = field(default_factory=list)
    best_spread: PriceSpread | None = None
    best_funding: FundingArbitrage | None = None
    overall_opportunity: ArbitrageOpportunity = ArbitrageOpportunity.NONE

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "spreads": [s.to_dict() for s in self.spreads],
            "funding_arbs": [f.to_dict() for f in self.funding_arbs],
            "best_spread": self.best_spread.to_dict() if self.best_spread else None,
            "best_funding": self.best_funding.to_dict() if self.best_funding else None,
            "overall_opportunity": self.overall_opportunity.value,
            "overall_opportunity_ru": self.overall_opportunity.name_ru,
            "overall_opportunity_emoji": self.overall_opportunity.emoji,
            "summary": self._get_summary(),
            "summary_ru": self._get_summary_ru(),
        }

    def _get_summary(self) -> str:
        if self.best_spread and self.best_spread.spread_pct > 0.3:
            return f"{self.best_spread.symbol}: {self.best_spread.spread_pct:.2f}% spread"
        if self.best_funding and abs(self.best_funding.annualized_rate) > 20:
            return f"{self.best_funding.symbol}: {self.best_funding.annualized_rate:.1f}% APR funding"
        return "No significant opportunities"

    def _get_summary_ru(self) -> str:
        if self.best_spread and self.best_spread.spread_pct > 0.3:
            return f"{self.best_spread.symbol}: {self.best_spread.spread_pct:.2f}% спред"
        if self.best_funding and abs(self.best_funding.annualized_rate) > 20:
            return f"{self.best_funding.symbol}: {self.best_funding.annualized_rate:.1f}% годовых фандинг"
        return "Нет значимых возможностей"


class ArbitrageScanner:
    """
    Arbitrage scanning service.

    Scans multiple exchanges for price spreads and funding arbitrage.
    """

    SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

    def __init__(self, timeout: float = 15.0):
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

    async def analyze(self) -> ArbitrageAnalysis:
        """
        Perform full arbitrage analysis.

        Returns:
            ArbitrageAnalysis with opportunities
        """
        client = await self._get_client()

        # Fetch prices from all exchanges
        bybit_prices = await self._fetch_bybit_prices(client)
        binance_prices = await self._fetch_binance_prices(client)
        okx_prices = await self._fetch_okx_prices(client)

        # Calculate spreads
        spreads = self._calculate_spreads(bybit_prices, binance_prices, okx_prices)

        # Fetch funding rates
        funding_arbs = await self._fetch_funding_arbitrage(client)

        # Find best opportunities
        best_spread = max(spreads, key=lambda x: x.spread_pct) if spreads else None
        best_funding = max(funding_arbs, key=lambda x: abs(x.annualized_rate)) if funding_arbs else None

        # Determine overall opportunity
        overall = ArbitrageOpportunity.NONE
        if best_spread and best_spread.spread_pct > 0.5:
            overall = ArbitrageOpportunity.EXCELLENT
        elif best_spread and best_spread.spread_pct > 0.3:
            overall = ArbitrageOpportunity.GOOD
        elif best_spread and best_spread.spread_pct > 0.1:
            overall = ArbitrageOpportunity.LOW
        elif best_funding and abs(best_funding.annualized_rate) > 50:
            overall = ArbitrageOpportunity.GOOD

        return ArbitrageAnalysis(
            timestamp=datetime.now(),
            spreads=spreads,
            funding_arbs=funding_arbs,
            best_spread=best_spread,
            best_funding=best_funding,
            overall_opportunity=overall,
        )

    async def _fetch_bybit_prices(self, client: httpx.AsyncClient) -> dict[str, float]:
        """Fetch prices from Bybit."""
        try:
            url = f"{BYBIT_API}/v5/market/tickers"
            params = {"category": "linear"}

            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            prices = {}
            for ticker in data.get("result", {}).get("list", []):
                symbol = ticker.get("symbol", "")
                if symbol in self.SYMBOLS:
                    prices[symbol] = float(ticker.get("lastPrice", 0))

            return prices

        except Exception as e:
            logger.warning(f"Failed to fetch Bybit prices: {e}")
            return {}

    async def _fetch_binance_prices(self, client: httpx.AsyncClient) -> dict[str, float]:
        """Fetch prices from Binance."""
        try:
            url = f"{BINANCE_API}/api/v3/ticker/price"

            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

            prices = {}
            for ticker in data:
                symbol = ticker.get("symbol", "")
                if symbol in self.SYMBOLS:
                    prices[symbol] = float(ticker.get("price", 0))

            return prices

        except Exception as e:
            logger.warning(f"Failed to fetch Binance prices: {e}")
            return {}

    async def _fetch_okx_prices(self, client: httpx.AsyncClient) -> dict[str, float]:
        """Fetch prices from OKX."""
        try:
            url = f"{OKX_API}/api/v5/market/tickers"
            params = {"instType": "SPOT"}

            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            prices = {}
            # OKX uses different symbol format (BTC-USDT)
            symbol_map = {
                "BTC-USDT": "BTCUSDT",
                "ETH-USDT": "ETHUSDT",
                "SOL-USDT": "SOLUSDT",
            }

            for ticker in data.get("data", []):
                okx_symbol = ticker.get("instId", "")
                if okx_symbol in symbol_map:
                    prices[symbol_map[okx_symbol]] = float(ticker.get("last", 0))

            return prices

        except Exception as e:
            logger.warning(f"Failed to fetch OKX prices: {e}")
            return {}

    def _calculate_spreads(
        self,
        bybit: dict[str, float],
        binance: dict[str, float],
        okx: dict[str, float],
    ) -> list[PriceSpread]:
        """Calculate price spreads between exchanges."""
        spreads = []

        for symbol in self.SYMBOLS:
            prices = {}
            if symbol in bybit and bybit[symbol] > 0:
                prices["Bybit"] = bybit[symbol]
            if symbol in binance and binance[symbol] > 0:
                prices["Binance"] = binance[symbol]
            if symbol in okx and okx[symbol] > 0:
                prices["OKX"] = okx[symbol]

            if len(prices) < 2:
                continue

            # Find min and max
            min_exchange = min(prices, key=prices.get)
            max_exchange = max(prices, key=prices.get)
            min_price = prices[min_exchange]
            max_price = prices[max_exchange]

            if min_price == 0:
                continue

            spread_pct = ((max_price - min_price) / min_price) * 100
            spread_usd = max_price - min_price

            # Classify opportunity
            if spread_pct >= 0.5:
                opportunity = ArbitrageOpportunity.EXCELLENT
            elif spread_pct >= 0.3:
                opportunity = ArbitrageOpportunity.GOOD
            elif spread_pct >= 0.1:
                opportunity = ArbitrageOpportunity.LOW
            else:
                opportunity = ArbitrageOpportunity.NONE

            spreads.append(
                PriceSpread(
                    symbol=symbol,
                    exchange_low=min_exchange,
                    exchange_high=max_exchange,
                    price_low=min_price,
                    price_high=max_price,
                    spread_pct=spread_pct,
                    spread_usd=spread_usd,
                    opportunity=opportunity,
                )
            )

        return spreads

    async def _fetch_funding_arbitrage(self, client: httpx.AsyncClient) -> list[FundingArbitrage]:
        """Fetch funding rates for arbitrage analysis."""
        arbs = []

        try:
            # Bybit funding rates
            url = f"{BYBIT_API}/v5/market/tickers"
            params = {"category": "linear"}

            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            for ticker in data.get("result", {}).get("list", []):
                symbol = ticker.get("symbol", "")
                if symbol not in self.SYMBOLS:
                    continue

                funding_rate = float(ticker.get("fundingRate", 0))
                if abs(funding_rate) < 0.0001:  # Filter out tiny rates
                    continue

                # Annualize (3 funding periods per day, 365 days)
                annualized = funding_rate * 3 * 365 * 100

                arbs.append(
                    FundingArbitrage(
                        symbol=symbol,
                        exchange="Bybit",
                        funding_rate=funding_rate,
                        annualized_rate=annualized,
                        direction="short" if funding_rate > 0 else "long",
                    )
                )

        except Exception as e:
            logger.warning(f"Failed to fetch funding rates: {e}")

        return arbs


# Global instance
_arbitrage_scanner: ArbitrageScanner | None = None


def get_arbitrage_scanner() -> ArbitrageScanner:
    """Get global arbitrage scanner instance."""
    global _arbitrage_scanner
    if _arbitrage_scanner is None:
        _arbitrage_scanner = ArbitrageScanner()
    return _arbitrage_scanner
