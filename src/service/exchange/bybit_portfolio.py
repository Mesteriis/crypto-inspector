"""
Bybit Portfolio Service.

Tracks portfolio from Bybit exchange:
- Real-time balances and positions
- P&L calculations by period (24h, 7d, 30d, YTD, All-time)
- Sync with manual portfolio entries

Периоды P&L:
- 24h: За последние 24 часа
- 7d: За последние 7 дней
- 30d: За последний месяц
- ytd: С начала года
- all: За всё время
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from service.exchange.bybit_client import (
    AccountSummary,
    BybitClient,
    Position,
    Trade,
    get_bybit_client,
)

logger = logging.getLogger(__name__)


class PnlPeriod(Enum):
    """P&L calculation periods."""

    DAY = "24h"
    WEEK = "7d"
    MONTH = "30d"
    YTD = "ytd"
    ALL = "all"

    @property
    def name_ru(self) -> str:
        names = {
            PnlPeriod.DAY: "24 часа",
            PnlPeriod.WEEK: "7 дней",
            PnlPeriod.MONTH: "30 дней",
            PnlPeriod.YTD: "С начала года",
            PnlPeriod.ALL: "За всё время",
        }
        return names.get(self, self.value)


@dataclass
class PnlSummary:
    """P&L summary for a period."""

    period: PnlPeriod
    realized_pnl: float
    unrealized_pnl: float
    total_pnl: float
    fees_paid: float
    trades_count: int
    win_count: int
    loss_count: int
    start_time: datetime
    end_time: datetime
    best_trade: dict | None = None
    worst_trade: dict | None = None
    by_symbol: dict[str, float] = field(default_factory=dict)

    @property
    def win_rate(self) -> float:
        if self.trades_count == 0:
            return 0
        return (self.win_count / self.trades_count) * 100

    def to_dict(self) -> dict[str, Any]:
        return {
            "period": self.period.value,
            "period_ru": self.period.name_ru,
            "realized_pnl": round(self.realized_pnl, 2),
            "unrealized_pnl": round(self.unrealized_pnl, 2),
            "total_pnl": round(self.total_pnl, 2),
            "total_pnl_formatted": self._format_pnl(self.total_pnl),
            "pnl_emoji": "🟢" if self.total_pnl >= 0 else "🔴",
            "fees_paid": round(self.fees_paid, 2),
            "trades_count": self.trades_count,
            "win_count": self.win_count,
            "loss_count": self.loss_count,
            "win_rate": round(self.win_rate, 1),
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "best_trade": self.best_trade,
            "worst_trade": self.worst_trade,
            "by_symbol": {k: round(v, 2) for k, v in self.by_symbol.items()},
        }

    def _format_pnl(self, value: float) -> str:
        sign = "+" if value >= 0 else ""
        if abs(value) >= 1_000_000:
            return f"{sign}${value / 1_000_000:.2f}M"
        if abs(value) >= 1_000:
            return f"{sign}${value / 1_000:.1f}K"
        return f"{sign}${value:.2f}"


@dataclass
class BybitPortfolioStatus:
    """Complete Bybit portfolio status."""

    timestamp: datetime
    account: AccountSummary
    pnl_24h: PnlSummary | None
    pnl_7d: PnlSummary | None
    is_configured: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "is_configured": self.is_configured,
            "account": self.account.to_dict() if self.account else None,
            "pnl_24h": self.pnl_24h.to_dict() if self.pnl_24h else None,
            "pnl_7d": self.pnl_7d.to_dict() if self.pnl_7d else None,
            "summary": self._get_summary(),
            "summary_ru": self._get_summary_ru(),
            "earn_summary": self._get_earn_summary(),
            "earn_summary_ru": self._get_earn_summary_ru(),
        }

    def _get_summary(self) -> str:
        if not self.is_configured:
            return "Bybit not configured"
        total = self.account.total_portfolio_value if self.account else 0
        wallet = self.account.total_equity if self.account else 0
        earn = self.account.total_earn_value if self.account else 0
        pnl = self.pnl_24h.total_pnl if self.pnl_24h else 0
        sign = "+" if pnl >= 0 else ""
        return f"Bybit: ${total:,.2f} (Wallet: ${wallet:,.0f} + Earn: ${earn:,.0f}) {sign}${pnl:.2f} 24h"

    def _get_summary_ru(self) -> str:
        if not self.is_configured:
            return "Bybit не настроен"
        total = self.account.total_portfolio_value if self.account else 0
        wallet = self.account.total_equity if self.account else 0
        earn = self.account.total_earn_value if self.account else 0
        pnl = self.pnl_24h.total_pnl if self.pnl_24h else 0
        sign = "+" if pnl >= 0 else ""
        return f"Bybit: ${total:,.2f} (Кошелек: ${wallet:,.0f} + Earn: ${earn:,.0f}) {sign}${pnl:.2f} за 24ч"

    def _get_earn_summary(self) -> str:
        if not self.is_configured or not self.account:
            return "No earn positions"
        earn_count = len(self.account.earn_positions)
        earn_value = self.account.total_earn_value
        if earn_count == 0:
            return "No earn positions"
        return f"{earn_count} positions, ${earn_value:,.2f} total"

    def _get_earn_summary_ru(self) -> str:
        if not self.is_configured or not self.account:
            return "Нет позиций Earn"
        earn_count = len(self.account.earn_positions)
        earn_value = self.account.total_earn_value
        if earn_count == 0:
            return "Нет позиций Earn"
        return f"{earn_count} позиций, ${earn_value:,.2f} всего"


class BybitPortfolio:
    """
    Bybit portfolio tracking service.

    Fetches real data from Bybit and calculates P&L.
    """

    def __init__(self, client: BybitClient | None = None):
        self._client = client or get_bybit_client()
        self._cached_account: AccountSummary | None = None
        self._cached_positions: list[Position] = []
        self._cache_time: datetime | None = None
        self._cache_ttl = timedelta(seconds=60)

    @property
    def is_configured(self) -> bool:
        return self._client.is_configured

    async def close(self) -> None:
        """Close client connection."""
        await self._client.close()

    async def get_account(self, force_refresh: bool = False) -> AccountSummary:
        """
        Get account summary with balances and earn positions.

        Args:
            force_refresh: Force refresh from API

        Returns:
            AccountSummary with balances and earn positions
        """
        if not self.is_configured:
            return AccountSummary(
                total_equity=0,
                total_available=0,
                total_margin_used=0,
                total_unrealized_pnl=0,
                account_type="NOT_CONFIGURED",
            )

        # Check cache
        if not force_refresh and self._cached_account and self._cache_time:
            if datetime.now() - self._cache_time < self._cache_ttl:
                return self._cached_account

        try:
            account = await self._client.get_wallet_balance()
            positions = await self._client.get_positions()
            earn_positions = await self._client.get_all_earn_positions()

            account.positions = positions
            account.earn_positions = earn_positions
            self._cached_account = account
            self._cached_positions = positions
            self._cache_time = datetime.now()

            return account

        except Exception as e:
            logger.error(f"Failed to get Bybit account: {e}")
            if self._cached_account:
                return self._cached_account
            raise

    async def get_positions(self, force_refresh: bool = False) -> list[Position]:
        """Get open positions."""
        if not self.is_configured:
            return []

        if not force_refresh and self._cached_positions and self._cache_time:
            if datetime.now() - self._cache_time < self._cache_ttl:
                return self._cached_positions

        try:
            positions = await self._client.get_positions()
            self._cached_positions = positions
            self._cache_time = datetime.now()
            return positions
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            return self._cached_positions

    async def get_trades(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        symbol: str | None = None,
        limit: int = 100,
    ) -> list[Trade]:
        """Get trade history."""
        if not self.is_configured:
            return []

        try:
            return await self._client.get_trade_history(
                symbol=symbol,
                start_time=start_time,
                end_time=end_time,
                limit=limit,
            )
        except Exception as e:
            logger.error(f"Failed to get trades: {e}")
            return []

    async def calculate_pnl(self, period: PnlPeriod) -> PnlSummary:
        """
        Calculate P&L for a period.

        Args:
            period: Time period for calculation

        Returns:
            PnlSummary with detailed breakdown
        """
        now = datetime.now()
        end_time = now

        # Determine start time based on period
        if period == PnlPeriod.DAY:
            start_time = now - timedelta(days=1)
        elif period == PnlPeriod.WEEK:
            start_time = now - timedelta(days=7)
        elif period == PnlPeriod.MONTH:
            start_time = now - timedelta(days=30)
        elif period == PnlPeriod.YTD:
            start_time = datetime(now.year, 1, 1)
        else:  # ALL
            start_time = datetime(2020, 1, 1)  # Reasonable start

        if not self.is_configured:
            return PnlSummary(
                period=period,
                realized_pnl=0,
                unrealized_pnl=0,
                total_pnl=0,
                fees_paid=0,
                trades_count=0,
                win_count=0,
                loss_count=0,
                start_time=start_time,
                end_time=end_time,
            )

        try:
            # Get closed P&L records
            closed_pnl = await self._client.get_closed_pnl(
                start_time=start_time,
                end_time=end_time,
                limit=100,
            )

            # Get trades for fee calculation
            trades = await self._client.get_trade_history(
                start_time=start_time,
                end_time=end_time,
                limit=100,
            )

            # Get current unrealized P&L
            account = await self.get_account()
            unrealized_pnl = account.total_unrealized_pnl

            # Calculate realized P&L
            realized_pnl = sum(record.get("closed_pnl", 0) for record in closed_pnl)
            fees_paid = sum(trade.fee for trade in trades)

            # Count wins and losses
            win_count = sum(1 for r in closed_pnl if r.get("closed_pnl", 0) > 0)
            loss_count = sum(1 for r in closed_pnl if r.get("closed_pnl", 0) < 0)

            # P&L by symbol
            by_symbol: dict[str, float] = {}
            for record in closed_pnl:
                symbol = record.get("symbol", "UNKNOWN")
                pnl = record.get("closed_pnl", 0)
                by_symbol[symbol] = by_symbol.get(symbol, 0) + pnl

            # Best and worst trades
            best_trade = None
            worst_trade = None
            if closed_pnl:
                sorted_pnl = sorted(closed_pnl, key=lambda x: x.get("closed_pnl", 0))
                if sorted_pnl:
                    worst_trade = {
                        "symbol": sorted_pnl[0].get("symbol"),
                        "pnl": sorted_pnl[0].get("closed_pnl"),
                    }
                    best_trade = {
                        "symbol": sorted_pnl[-1].get("symbol"),
                        "pnl": sorted_pnl[-1].get("closed_pnl"),
                    }

            return PnlSummary(
                period=period,
                realized_pnl=realized_pnl,
                unrealized_pnl=unrealized_pnl,
                total_pnl=realized_pnl + unrealized_pnl,
                fees_paid=fees_paid,
                trades_count=len(closed_pnl),
                win_count=win_count,
                loss_count=loss_count,
                start_time=start_time,
                end_time=end_time,
                best_trade=best_trade,
                worst_trade=worst_trade,
                by_symbol=by_symbol,
            )

        except Exception as e:
            logger.error(f"Failed to calculate P&L: {e}")
            return PnlSummary(
                period=period,
                realized_pnl=0,
                unrealized_pnl=0,
                total_pnl=0,
                fees_paid=0,
                trades_count=0,
                win_count=0,
                loss_count=0,
                start_time=start_time,
                end_time=end_time,
            )

    async def get_full_status(self) -> BybitPortfolioStatus:
        """
        Get complete portfolio status.

        Returns:
            Full status with account and P&L
        """
        account = await self.get_account()
        pnl_24h = await self.calculate_pnl(PnlPeriod.DAY)
        pnl_7d = await self.calculate_pnl(PnlPeriod.WEEK)

        return BybitPortfolioStatus(
            timestamp=datetime.now(),
            account=account,
            pnl_24h=pnl_24h,
            pnl_7d=pnl_7d,
            is_configured=self.is_configured,
        )

    async def get_all_pnl_periods(self) -> dict[str, PnlSummary]:
        """Get P&L for all periods."""
        result = {}
        for period in PnlPeriod:
            result[period.value] = await self.calculate_pnl(period)
        return result


# Global instance
_bybit_portfolio: BybitPortfolio | None = None


def get_bybit_portfolio() -> BybitPortfolio:
    """Get global Bybit portfolio instance."""
    global _bybit_portfolio
    if _bybit_portfolio is None:
        _bybit_portfolio = BybitPortfolio()
    return _bybit_portfolio
