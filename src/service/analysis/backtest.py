"""
DCA Backtesting Service.

Backtests different investment strategies:
- Fixed DCA (regular purchases)
- Smart DCA (Fear & Greed adjusted)
- Lump Sum
- Comparison analysis
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    """Result of a backtest simulation."""

    strategy: str
    symbol: str
    start_date: datetime
    end_date: datetime

    # Investment
    total_invested: float
    current_value: float
    total_coins: float

    # Returns
    total_return_pct: float
    annualized_return: float

    # Risk metrics
    max_drawdown: float
    sharpe_ratio: float

    # Stats
    buy_count: int
    avg_buy_price: float

    # Monthly breakdown
    best_month: dict = field(default_factory=dict)
    worst_month: dict = field(default_factory=dict)

    # Details
    trades: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "strategy": self.strategy,
            "symbol": self.symbol,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "total_invested": round(self.total_invested, 2),
            "current_value": round(self.current_value, 2),
            "total_coins": round(self.total_coins, 8),
            "total_return_pct": round(self.total_return_pct, 2),
            "annualized_return": round(self.annualized_return, 2),
            "max_drawdown": round(self.max_drawdown, 2),
            "sharpe_ratio": round(self.sharpe_ratio, 2),
            "buy_count": self.buy_count,
            "avg_buy_price": round(self.avg_buy_price, 2),
            "best_month": self.best_month,
            "worst_month": self.worst_month,
        }


class DCABacktester:
    """
    DCA Strategy Backtester.

    Tests different investment strategies using historical data.
    """

    # Fear & Greed multipliers for Smart DCA
    FG_MULTIPLIERS = {
        "extreme_fear": 2.0,  # F&G 0-19
        "fear": 1.5,  # F&G 20-39
        "neutral": 1.0,  # F&G 40-59
        "greed": 0.5,  # F&G 60-79
        "extreme_greed": 0.25,  # F&G 80-100
    }

    def __init__(self):
        self._cache: dict[str, BacktestResult] = {}
        self._historical_fg: list[dict] = []  # Historical Fear & Greed data

    def set_fear_greed_history(self, data: list[dict]) -> None:
        """
        Set historical Fear & Greed data.

        Args:
            data: List of {"date": datetime, "value": int}
        """
        self._historical_fg = data

    def _get_fg_for_date(self, date: datetime) -> int:
        """Get Fear & Greed value for a specific date."""
        for fg in self._historical_fg:
            if fg.get("date") and fg["date"].date() == date.date():
                return fg.get("value", 50)
        return 50  # Default to neutral

    def _get_fg_multiplier(self, fg_value: int) -> float:
        """Get DCA multiplier based on Fear & Greed."""
        if fg_value < 20:
            return self.FG_MULTIPLIERS["extreme_fear"]
        elif fg_value < 40:
            return self.FG_MULTIPLIERS["fear"]
        elif fg_value < 60:
            return self.FG_MULTIPLIERS["neutral"]
        elif fg_value < 80:
            return self.FG_MULTIPLIERS["greed"]
        else:
            return self.FG_MULTIPLIERS["extreme_greed"]

    async def backtest_fixed_dca(
        self,
        symbol: str,
        candles: list[dict],
        amount: float = 100.0,
        frequency: str = "weekly",
        years: int = 5,
    ) -> BacktestResult:
        """
        Backtest fixed DCA strategy.

        Args:
            symbol: Trading pair
            candles: Historical candle data (daily)
            amount: Fixed investment amount per period
            frequency: "daily", "weekly", "monthly"
            years: Number of years to backtest

        Returns:
            BacktestResult
        """
        if not candles:
            raise ValueError("No candle data provided")

        # Calculate days between purchases
        freq_days = {"daily": 1, "weekly": 7, "monthly": 30}
        interval = freq_days.get(frequency, 7)

        # Filter candles for the period
        end_date = datetime.now()
        start_date = end_date - timedelta(days=years * 365)

        filtered = [c for c in candles if datetime.fromtimestamp(c.get("timestamp", 0) / 1000) >= start_date]

        if not filtered:
            raise ValueError("No data in the specified period")

        # Simulate DCA
        trades = []
        total_invested = 0.0
        total_coins = 0.0
        portfolio_values = []

        for i, candle in enumerate(filtered):
            if i % interval == 0:
                price = float(candle.get("close", 0))
                if price > 0:
                    coins = amount / price
                    total_coins += coins
                    total_invested += amount
                    trades.append(
                        {
                            "date": datetime.fromtimestamp(candle.get("timestamp", 0) / 1000).isoformat(),
                            "price": price,
                            "amount": amount,
                            "coins": coins,
                        }
                    )

            # Track portfolio value
            current_price = float(candle.get("close", 0))
            portfolio_values.append(total_coins * current_price)

        # Calculate metrics
        final_price = float(filtered[-1].get("close", 0))
        current_value = total_coins * final_price
        avg_buy_price = total_invested / total_coins if total_coins > 0 else 0

        return self._create_result(
            strategy="Fixed DCA",
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            total_invested=total_invested,
            current_value=current_value,
            total_coins=total_coins,
            avg_buy_price=avg_buy_price,
            portfolio_values=portfolio_values,
            trades=trades,
        )

    async def backtest_smart_dca(
        self,
        symbol: str,
        candles: list[dict],
        base_amount: float = 100.0,
        years: int = 5,
    ) -> BacktestResult:
        """
        Backtest Smart DCA strategy (Fear & Greed adjusted).

        Invests more during fear, less during greed.
        """
        if not candles:
            raise ValueError("No candle data provided")

        end_date = datetime.now()
        start_date = end_date - timedelta(days=years * 365)

        filtered = [c for c in candles if datetime.fromtimestamp(c.get("timestamp", 0) / 1000) >= start_date]

        if not filtered:
            raise ValueError("No data in the specified period")

        # Weekly DCA with F&G multiplier
        trades = []
        total_invested = 0.0
        total_coins = 0.0
        portfolio_values = []

        for i, candle in enumerate(filtered):
            if i % 7 == 0:  # Weekly
                price = float(candle.get("close", 0))
                if price > 0:
                    candle_date = datetime.fromtimestamp(candle.get("timestamp", 0) / 1000)
                    fg_value = self._get_fg_for_date(candle_date)
                    multiplier = self._get_fg_multiplier(fg_value)

                    adjusted_amount = base_amount * multiplier
                    coins = adjusted_amount / price

                    total_coins += coins
                    total_invested += adjusted_amount

                    trades.append(
                        {
                            "date": candle_date.isoformat(),
                            "price": price,
                            "amount": adjusted_amount,
                            "coins": coins,
                            "fear_greed": fg_value,
                            "multiplier": multiplier,
                        }
                    )

            current_price = float(candle.get("close", 0))
            portfolio_values.append(total_coins * current_price)

        final_price = float(filtered[-1].get("close", 0))
        current_value = total_coins * final_price
        avg_buy_price = total_invested / total_coins if total_coins > 0 else 0

        return self._create_result(
            strategy="Smart DCA",
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            total_invested=total_invested,
            current_value=current_value,
            total_coins=total_coins,
            avg_buy_price=avg_buy_price,
            portfolio_values=portfolio_values,
            trades=trades,
        )

    async def backtest_lump_sum(
        self,
        symbol: str,
        candles: list[dict],
        total_amount: float = 10000.0,
        years: int = 5,
    ) -> BacktestResult:
        """
        Backtest lump sum investment (invest all at start).
        """
        if not candles:
            raise ValueError("No candle data provided")

        end_date = datetime.now()
        start_date = end_date - timedelta(days=years * 365)

        filtered = [c for c in candles if datetime.fromtimestamp(c.get("timestamp", 0) / 1000) >= start_date]

        if not filtered:
            raise ValueError("No data in the specified period")

        # Buy everything at start
        entry_price = float(filtered[0].get("close", 0))
        total_coins = total_amount / entry_price if entry_price > 0 else 0

        trades = [
            {
                "date": start_date.isoformat(),
                "price": entry_price,
                "amount": total_amount,
                "coins": total_coins,
            }
        ]

        # Track portfolio value
        portfolio_values = [total_coins * float(c.get("close", 0)) for c in filtered]

        final_price = float(filtered[-1].get("close", 0))
        current_value = total_coins * final_price

        return self._create_result(
            strategy="Lump Sum",
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            total_invested=total_amount,
            current_value=current_value,
            total_coins=total_coins,
            avg_buy_price=entry_price,
            portfolio_values=portfolio_values,
            trades=trades,
        )

    async def compare_strategies(
        self,
        symbol: str,
        candles: list[dict],
        amount: float = 100.0,
        years: int = 5,
    ) -> dict[str, Any]:
        """
        Compare all strategies.

        Returns comparison data for all strategies.
        """
        # Calculate equivalent lump sum
        weeks_in_period = years * 52
        lump_sum_amount = amount * weeks_in_period

        results = {}

        try:
            results["fixed_dca"] = await self.backtest_fixed_dca(symbol, candles, amount, "weekly", years)
        except Exception as e:
            logger.error(f"Fixed DCA backtest failed: {e}")

        try:
            results["smart_dca"] = await self.backtest_smart_dca(symbol, candles, amount, years)
        except Exception as e:
            logger.error(f"Smart DCA backtest failed: {e}")

        try:
            results["lump_sum"] = await self.backtest_lump_sum(symbol, candles, lump_sum_amount, years)
        except Exception as e:
            logger.error(f"Lump sum backtest failed: {e}")

        # Determine best strategy
        best_strategy = None
        best_return = float("-inf")

        for name, result in results.items():
            if result and result.total_return_pct > best_return:
                best_return = result.total_return_pct
                best_strategy = name

        # Cache results
        self._cache[symbol] = results.get("smart_dca") or results.get("fixed_dca")

        # Publish to HA
        await self._publish_to_ha(results, best_strategy)

        return {
            "symbol": symbol,
            "period_years": years,
            "weekly_amount": amount,
            "best_strategy": best_strategy,
            "strategies": {name: result.to_dict() if result else None for name, result in results.items()},
        }

    def _create_result(
        self,
        strategy: str,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        total_invested: float,
        current_value: float,
        total_coins: float,
        avg_buy_price: float,
        portfolio_values: list[float],
        trades: list[dict],
    ) -> BacktestResult:
        """Create BacktestResult with calculated metrics."""
        # Calculate return
        total_return = (current_value - total_invested) / total_invested * 100 if total_invested > 0 else 0

        # Annualized return
        days = (end_date - start_date).days
        years = days / 365
        if years > 0 and total_invested > 0:
            annualized = ((current_value / total_invested) ** (1 / years) - 1) * 100
        else:
            annualized = 0

        # Max drawdown
        max_dd = self._calculate_max_drawdown(portfolio_values)

        # Sharpe ratio (simplified)
        sharpe = self._calculate_sharpe(portfolio_values)

        # Best/worst month
        best_month, worst_month = self._find_best_worst_months(trades)

        return BacktestResult(
            strategy=strategy,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            total_invested=total_invested,
            current_value=current_value,
            total_coins=total_coins,
            total_return_pct=total_return,
            annualized_return=annualized,
            max_drawdown=max_dd,
            sharpe_ratio=sharpe,
            buy_count=len(trades),
            avg_buy_price=avg_buy_price,
            best_month=best_month,
            worst_month=worst_month,
            trades=trades[-10:],  # Keep last 10 trades
        )

    def _calculate_max_drawdown(self, values: list[float]) -> float:
        """Calculate maximum drawdown percentage."""
        if len(values) < 2:
            return 0.0

        peak = values[0]
        max_dd = 0.0

        for value in values:
            if value > peak:
                peak = value
            if peak > 0:
                dd = (peak - value) / peak * 100
                max_dd = max(max_dd, dd)

        return max_dd

    def _calculate_sharpe(self, values: list[float]) -> float:
        """Calculate simplified Sharpe ratio."""
        if len(values) < 30:
            return 0.0

        returns = []
        for i in range(1, len(values)):
            if values[i - 1] > 0:
                returns.append((values[i] - values[i - 1]) / values[i - 1])

        if not returns:
            return 0.0

        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        std_dev = variance**0.5

        if std_dev == 0:
            return 0.0

        # Annualized (assuming daily values)
        risk_free = 0.04 / 365
        sharpe = ((mean_return - risk_free) / std_dev) * (365**0.5)

        return sharpe

    def _find_best_worst_months(self, trades: list[dict]) -> tuple[dict, dict]:
        """Find best and worst months based on entry prices."""
        if not trades:
            return {}, {}

        monthly_data = {}

        for trade in trades:
            date_str = trade.get("date", "")[:7]  # YYYY-MM
            if date_str not in monthly_data:
                monthly_data[date_str] = {"prices": [], "amount": 0}

            monthly_data[date_str]["prices"].append(trade.get("price", 0))
            monthly_data[date_str]["amount"] += trade.get("amount", 0)

        best_month = {}
        worst_month = {}
        best_avg = float("inf")
        worst_avg = 0

        for month, data in monthly_data.items():
            if data["prices"]:
                avg = sum(data["prices"]) / len(data["prices"])
                if avg < best_avg:
                    best_avg = avg
                    best_month = {"month": month, "avg_price": round(avg, 2)}
                if avg > worst_avg:
                    worst_avg = avg
                    worst_month = {"month": month, "avg_price": round(avg, 2)}

        return best_month, worst_month

    async def _publish_to_ha(
        self,
        results: dict[str, BacktestResult],
        best_strategy: str | None,
    ) -> None:
        """Publish backtest results to Home Assistant (via Supervisor API)."""
        # Sensor publishing handled by SensorManager
        pass

    def get_cached_result(self, symbol: str) -> BacktestResult | None:
        """Get cached backtest result."""
        return self._cache.get(symbol)
