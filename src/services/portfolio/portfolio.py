"""
Portfolio Tracking Service.

Tracks cryptocurrency portfolio:
- Holdings with cost basis
- Current value and P&L calculations
- Allocation percentages
- 24h/7d performance

Supports configuration via:
- Environment variables
- API endpoints
- HA addon options
"""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

import httpx

logger = logging.getLogger(__name__)

COINGECKO_API = "https://api.coingecko.com/api/v3"


class PerformanceStatus(Enum):
    """Portfolio performance status."""

    STRONG_PROFIT = "strong_profit"  # >20% profit
    PROFIT = "profit"  # 5-20% profit
    SLIGHT_PROFIT = "slight_profit"  # 0-5% profit
    SLIGHT_LOSS = "slight_loss"  # 0-5% loss
    LOSS = "loss"  # 5-20% loss
    STRONG_LOSS = "strong_loss"  # >20% loss


@dataclass
class Holding:
    """Single portfolio holding."""

    symbol: str
    amount: float
    avg_price: float  # Cost basis per unit
    current_price: float = 0
    current_value: float = 0
    cost_basis: float = 0
    pnl_absolute: float = 0
    pnl_percent: float = 0
    change_24h_pct: float = 0
    allocation_pct: float = 0

    def calculate(self) -> None:
        """Calculate derived values."""
        self.cost_basis = self.amount * self.avg_price
        self.current_value = self.amount * self.current_price
        self.pnl_absolute = self.current_value - self.cost_basis
        self.pnl_percent = ((self.current_price - self.avg_price) / self.avg_price * 100) if self.avg_price > 0 else 0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "amount": self.amount,
            "avg_price": self.avg_price,
            "current_price": round(self.current_price, 2),
            "current_value": round(self.current_value, 2),
            "cost_basis": round(self.cost_basis, 2),
            "pnl_absolute": round(self.pnl_absolute, 2),
            "pnl_percent": round(self.pnl_percent, 2),
            "pnl_emoji": "🟢" if self.pnl_percent >= 0 else "🔴",
            "change_24h_pct": round(self.change_24h_pct, 2),
            "allocation_pct": round(self.allocation_pct, 2),
        }


@dataclass
class PortfolioData:
    """Complete portfolio data."""

    timestamp: datetime
    total_value: float
    total_cost_basis: float
    total_pnl_absolute: float
    total_pnl_percent: float
    change_24h_pct: float
    change_7d_pct: float | None
    status: PerformanceStatus
    status_ru: str
    holdings: list[Holding] = field(default_factory=list)
    best_performer: Holding | None = None
    worst_performer: Holding | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for API/MQTT."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "total_value": round(self.total_value, 2),
            "total_value_formatted": self._format_currency(self.total_value),
            "total_cost_basis": round(self.total_cost_basis, 2),
            "total_pnl_absolute": round(self.total_pnl_absolute, 2),
            "total_pnl_formatted": self._format_pnl(self.total_pnl_absolute),
            "total_pnl_percent": round(self.total_pnl_percent, 2),
            "change_24h_pct": round(self.change_24h_pct, 2),
            "change_7d_pct": round(self.change_7d_pct, 2) if self.change_7d_pct else None,
            "status": self.status.value,
            "status_ru": self.status_ru,
            "status_emoji": self._get_status_emoji(),
            "holdings": [h.to_dict() for h in self.holdings],
            "allocation": {h.symbol: round(h.allocation_pct, 2) for h in self.holdings},
            "best_performer": (
                {
                    "symbol": self.best_performer.symbol,
                    "pnl_percent": round(self.best_performer.pnl_percent, 2),
                }
                if self.best_performer
                else None
            ),
            "worst_performer": (
                {
                    "symbol": self.worst_performer.symbol,
                    "pnl_percent": round(self.worst_performer.pnl_percent, 2),
                }
                if self.worst_performer
                else None
            ),
            "summary": self._get_summary(),
            "summary_ru": self._get_summary_ru(),
        }

    def _format_currency(self, value: float) -> str:
        """Format currency value."""
        if value >= 1_000_000:
            return f"${value / 1_000_000:.2f}M"
        if value >= 1_000:
            return f"${value / 1_000:.1f}K"
        return f"${value:.2f}"

    def _format_pnl(self, value: float) -> str:
        """Format P&L value with sign."""
        sign = "+" if value >= 0 else ""
        return f"{sign}{self._format_currency(value)}"

    def _get_status_emoji(self) -> str:
        """Get emoji for status."""
        emoji_map = {
            PerformanceStatus.STRONG_PROFIT: "🚀",
            PerformanceStatus.PROFIT: "📈",
            PerformanceStatus.SLIGHT_PROFIT: "🟢",
            PerformanceStatus.SLIGHT_LOSS: "🟡",
            PerformanceStatus.LOSS: "📉",
            PerformanceStatus.STRONG_LOSS: "💀",
        }
        return emoji_map.get(self.status, "⚪")

    def _get_summary(self) -> str:
        """Get English summary."""
        sign = "+" if self.total_pnl_percent >= 0 else ""
        return f"Portfolio: {self._format_currency(self.total_value)} ({sign}{self.total_pnl_percent:.1f}%)"

    def _get_summary_ru(self) -> str:
        """Get Russian summary."""
        sign = "+" if self.total_pnl_percent >= 0 else ""
        return f"Портфель: {self._format_currency(self.total_value)} ({sign}{self.total_pnl_percent:.1f}%)"


class PortfolioManager:
    """
    Portfolio management service.

    Tracks holdings and calculates portfolio metrics.
    """

    def __init__(self, timeout: float = 30.0):
        self._client: httpx.AsyncClient | None = None
        self._timeout = timeout
        self._holdings: dict[str, Holding] = {}
        self._load_from_env()

    def _load_from_env(self) -> None:
        """Load portfolio configuration from environment."""
        portfolio_json = os.environ.get("PORTFOLIO_CONFIG", "")
        if portfolio_json:
            try:
                config = json.loads(portfolio_json)
                for item in config:
                    symbol = item.get("symbol", "").upper()
                    if symbol:
                        self._holdings[symbol] = Holding(
                            symbol=symbol,
                            amount=float(item.get("amount", 0)),
                            avg_price=float(item.get("avg_price", 0)),
                        )
                logger.info(f"Loaded {len(self._holdings)} holdings from env")
            except Exception as e:
                logger.warning(f"Failed to load portfolio from env: {e}")

        # Also check for individual env vars
        # Format: PORTFOLIO_BTC=0.5:45000 (amount:avg_price)
        for key, value in os.environ.items():
            if key.startswith("PORTFOLIO_") and key != "PORTFOLIO_CONFIG":
                symbol = key.replace("PORTFOLIO_", "").upper()
                try:
                    parts = value.split(":")
                    if len(parts) == 2:
                        amount = float(parts[0])
                        avg_price = float(parts[1])
                        self._holdings[symbol] = Holding(
                            symbol=symbol,
                            amount=amount,
                            avg_price=avg_price,
                        )
                except Exception as e:
                    logger.warning(f"Failed to parse {key}: {e}")

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

    def add_holding(self, symbol: str, amount: float, avg_price: float) -> Holding:
        """Add or update a holding."""
        symbol = symbol.upper()
        if symbol in self._holdings:
            # Update existing - recalculate average price
            existing = self._holdings[symbol]
            total_cost = (existing.amount * existing.avg_price) + (amount * avg_price)
            total_amount = existing.amount + amount
            new_avg = total_cost / total_amount if total_amount > 0 else 0

            existing.amount = total_amount
            existing.avg_price = new_avg
            return existing
        else:
            holding = Holding(symbol=symbol, amount=amount, avg_price=avg_price)
            self._holdings[symbol] = holding
            return holding

    def remove_holding(self, symbol: str) -> bool:
        """Remove a holding."""
        symbol = symbol.upper()
        if symbol in self._holdings:
            del self._holdings[symbol]
            return True
        return False

    def get_holdings(self) -> list[Holding]:
        """Get all holdings."""
        return list(self._holdings.values())

    async def calculate(self) -> PortfolioData:
        """
        Calculate current portfolio status.

        Fetches current prices and calculates all metrics.
        """
        if not self._holdings:
            return self._create_empty_result()

        client = await self._get_client()

        # Fetch current prices
        prices = await self._fetch_prices(client, list(self._holdings.keys()))

        # Update holdings with current prices
        total_value = 0
        total_cost = 0
        weighted_change_24h = 0

        for symbol, holding in self._holdings.items():
            price_data = prices.get(symbol, {})
            holding.current_price = price_data.get("price", holding.avg_price)
            holding.change_24h_pct = price_data.get("change_24h", 0)
            holding.calculate()

            total_value += holding.current_value
            total_cost += holding.cost_basis

        # Calculate allocations
        for holding in self._holdings.values():
            holding.allocation_pct = (holding.current_value / total_value * 100) if total_value > 0 else 0
            weighted_change_24h += holding.change_24h_pct * (holding.allocation_pct / 100)

        # Calculate P&L
        total_pnl = total_value - total_cost
        total_pnl_pct = ((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0

        # Find best/worst performers
        sorted_holdings = sorted(self._holdings.values(), key=lambda x: x.pnl_percent, reverse=True)
        best = sorted_holdings[0] if sorted_holdings else None
        worst = sorted_holdings[-1] if sorted_holdings else None

        # Determine status
        status, status_ru = self._calculate_status(total_pnl_pct)

        return PortfolioData(
            timestamp=datetime.now(),
            total_value=total_value,
            total_cost_basis=total_cost,
            total_pnl_absolute=total_pnl,
            total_pnl_percent=total_pnl_pct,
            change_24h_pct=weighted_change_24h,
            change_7d_pct=None,  # Would need historical tracking
            status=status,
            status_ru=status_ru,
            holdings=list(self._holdings.values()),
            best_performer=best,
            worst_performer=worst,
        )

    async def _fetch_prices(self, client: httpx.AsyncClient, symbols: list[str]) -> dict[str, dict]:
        """Fetch current prices from CoinGecko."""
        # Map symbols to CoinGecko IDs
        symbol_to_id = {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "SOL": "solana",
            "XRP": "ripple",
            "ADA": "cardano",
            "DOGE": "dogecoin",
            "DOT": "polkadot",
            "LINK": "chainlink",
            "AVAX": "avalanche-2",
            "MATIC": "polygon",
            "UNI": "uniswap",
            "ATOM": "cosmos",
            "LTC": "litecoin",
            "TON": "the-open-network",
            "AR": "arweave",
        }

        ids = [symbol_to_id.get(s, s.lower()) for s in symbols]
        ids_str = ",".join(ids)

        try:
            url = f"{COINGECKO_API}/simple/price"
            params = {
                "ids": ids_str,
                "vs_currencies": "usd",
                "include_24hr_change": "true",
            }

            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            result = {}
            for symbol in symbols:
                cg_id = symbol_to_id.get(symbol, symbol.lower())
                if cg_id in data:
                    result[symbol] = {
                        "price": data[cg_id].get("usd", 0),
                        "change_24h": data[cg_id].get("usd_24h_change", 0),
                    }

            return result

        except Exception as e:
            logger.warning(f"Failed to fetch prices: {e}")
            return {}

    def _calculate_status(self, pnl_pct: float) -> tuple[PerformanceStatus, str]:
        """Calculate performance status."""
        if pnl_pct >= 20:
            return PerformanceStatus.STRONG_PROFIT, "Отличный профит"
        if pnl_pct >= 5:
            return PerformanceStatus.PROFIT, "В профите"
        if pnl_pct >= 0:
            return PerformanceStatus.SLIGHT_PROFIT, "Небольшой профит"
        if pnl_pct >= -5:
            return PerformanceStatus.SLIGHT_LOSS, "Небольшой убыток"
        if pnl_pct >= -20:
            return PerformanceStatus.LOSS, "В убытке"
        return PerformanceStatus.STRONG_LOSS, "Сильный убыток"

    def _create_empty_result(self) -> PortfolioData:
        """Create empty result when no holdings."""
        return PortfolioData(
            timestamp=datetime.now(),
            total_value=0,
            total_cost_basis=0,
            total_pnl_absolute=0,
            total_pnl_percent=0,
            change_24h_pct=0,
            change_7d_pct=None,
            status=PerformanceStatus.SLIGHT_PROFIT,
            status_ru="Нет позиций",
            holdings=[],
            best_performer=None,
            worst_performer=None,
        )


# Global instance
_portfolio_manager: PortfolioManager | None = None


def get_portfolio_manager() -> PortfolioManager:
    """Get global portfolio manager instance."""
    global _portfolio_manager
    if _portfolio_manager is None:
        _portfolio_manager = PortfolioManager()
    return _portfolio_manager
