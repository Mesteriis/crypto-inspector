"""
Risk Management Service.

Advanced risk metrics for portfolio analysis:
- Sharpe Ratio
- Sortino Ratio
- Maximum Drawdown
- Value at Risk (VaR)
- Volatility analysis
"""

import logging
import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RiskMetrics:
    """Portfolio risk metrics."""

    # Ratios
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0

    # Drawdown
    max_drawdown: float = 0.0
    current_drawdown: float = 0.0
    days_since_ath: int = 0

    # Value at Risk
    var_95: float = 0.0  # 95% VaR (daily)
    var_99: float = 0.0  # 99% VaR (daily)

    # Volatility
    volatility_30d: float = 0.0
    volatility_7d: float = 0.0

    # Beta
    beta_vs_btc: float = 1.0

    # Overall
    risk_status: str = "Medium"  # Low, Medium, High, Critical

    # Timestamps
    calculated_at: datetime | None = None
    portfolio_value: float = 0.0

    def to_dict(self) -> dict:
        return {
            "sharpe_ratio": round(self.sharpe_ratio, 2),
            "sortino_ratio": round(self.sortino_ratio, 2),
            "max_drawdown": round(self.max_drawdown, 2),
            "current_drawdown": round(self.current_drawdown, 2),
            "days_since_ath": self.days_since_ath,
            "var_95": round(self.var_95, 2),
            "var_99": round(self.var_99, 2),
            "volatility_30d": round(self.volatility_30d, 2),
            "volatility_7d": round(self.volatility_7d, 2),
            "beta_vs_btc": round(self.beta_vs_btc, 2),
            "risk_status": self.risk_status,
            "calculated_at": self.calculated_at.isoformat() if self.calculated_at else None,
            "portfolio_value": round(self.portfolio_value, 2),
        }


class RiskAnalyzer:
    """
    Risk analysis calculator.

    Calculates portfolio risk metrics using historical data.
    """

    # Risk-free rate (approximate annual rate for calculations)
    RISK_FREE_RATE = 0.04  # 4% annual

    def __init__(self, mqtt_client=None):
        self._mqtt = mqtt_client
        self._last_metrics: RiskMetrics | None = None
        self._portfolio_history: list[dict] = []
        self._btc_returns: list[float] = []

    @property
    def last_metrics(self) -> RiskMetrics | None:
        return self._last_metrics

    def add_portfolio_snapshot(
        self,
        value: float,
        timestamp: datetime | None = None,
    ) -> None:
        """
        Add portfolio value snapshot for tracking.

        Args:
            value: Portfolio value in USDT
            timestamp: Snapshot timestamp
        """
        self._portfolio_history.append(
            {
                "value": value,
                "timestamp": timestamp or datetime.now(),
            }
        )

        # Keep last 365 days
        cutoff = datetime.now() - timedelta(days=365)
        self._portfolio_history = [s for s in self._portfolio_history if s["timestamp"] > cutoff]

    def set_btc_returns(self, returns: list[float]) -> None:
        """Set BTC daily returns for beta calculation."""
        self._btc_returns = returns

    async def calculate_risk_metrics(
        self,
        portfolio_values: list[float] | None = None,
        current_value: float | None = None,
    ) -> RiskMetrics:
        """
        Calculate comprehensive risk metrics.

        Args:
            portfolio_values: Historical portfolio values (oldest first)
            current_value: Current portfolio value

        Returns:
            RiskMetrics object
        """
        # Use provided values or internal history
        if portfolio_values:
            values = portfolio_values
        else:
            values = [s["value"] for s in self._portfolio_history]

        if len(values) < 7:
            logger.warning("Insufficient data for risk calculation")
            return RiskMetrics(
                risk_status="Unknown",
                calculated_at=datetime.now(),
                portfolio_value=current_value or 0,
            )

        current = current_value or values[-1]

        # Calculate returns
        returns = self._calculate_returns(values)

        # Calculate metrics
        sharpe = self._calculate_sharpe_ratio(returns)
        sortino = self._calculate_sortino_ratio(returns)
        max_dd, current_dd, days_ath = self._calculate_drawdown(values)
        var_95, var_99 = self._calculate_var(returns)
        vol_30d = self._calculate_volatility(returns[-30:]) if len(returns) >= 30 else 0
        vol_7d = self._calculate_volatility(returns[-7:]) if len(returns) >= 7 else 0
        beta = self._calculate_beta(returns)
        risk_status = self._determine_risk_status(max_dd, current_dd, vol_30d, var_95)

        metrics = RiskMetrics(
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            max_drawdown=max_dd,
            current_drawdown=current_dd,
            days_since_ath=days_ath,
            var_95=var_95,
            var_99=var_99,
            volatility_30d=vol_30d,
            volatility_7d=vol_7d,
            beta_vs_btc=beta,
            risk_status=risk_status,
            calculated_at=datetime.now(),
            portfolio_value=current,
        )

        self._last_metrics = metrics

        # Publish to HA
        await self._publish_to_ha(metrics)

        return metrics

    def _calculate_returns(self, values: list[float]) -> list[float]:
        """Calculate daily returns from values."""
        if len(values) < 2:
            return []

        returns = []
        for i in range(1, len(values)):
            if values[i - 1] != 0:
                ret = (values[i] - values[i - 1]) / values[i - 1]
                returns.append(ret)

        return returns

    def _calculate_sharpe_ratio(self, returns: list[float]) -> float:
        """
        Calculate Sharpe Ratio.

        Sharpe = (Mean Return - Risk Free Rate) / Std Dev of Returns
        Annualized.
        """
        if len(returns) < 7:
            return 0.0

        mean_return = sum(returns) / len(returns)
        std_dev = self._std_dev(returns)

        if std_dev == 0:
            return 0.0

        # Annualize (assuming daily returns)
        daily_rf = self.RISK_FREE_RATE / 365
        excess_return = mean_return - daily_rf

        # Annualize Sharpe
        sharpe = (excess_return / std_dev) * math.sqrt(365)

        return sharpe

    def _calculate_sortino_ratio(self, returns: list[float]) -> float:
        """
        Calculate Sortino Ratio.

        Similar to Sharpe but only uses downside deviation.
        """
        if len(returns) < 7:
            return 0.0

        mean_return = sum(returns) / len(returns)

        # Downside deviation (only negative returns)
        negative_returns = [r for r in returns if r < 0]
        if not negative_returns:
            return 3.0  # No negative returns = very good

        downside_dev = self._std_dev(negative_returns)

        if downside_dev == 0:
            return 0.0

        daily_rf = self.RISK_FREE_RATE / 365
        excess_return = mean_return - daily_rf

        sortino = (excess_return / downside_dev) * math.sqrt(365)

        return sortino

    def _calculate_drawdown(self, values: list[float]) -> tuple[float, float, int]:
        """
        Calculate maximum and current drawdown.

        Returns:
            (max_drawdown_pct, current_drawdown_pct, days_since_ath)
        """
        if len(values) < 2:
            return 0.0, 0.0, 0

        peak = values[0]
        peak_idx = 0
        max_drawdown = 0.0

        for i, value in enumerate(values):
            if value > peak:
                peak = value
                peak_idx = i

            if peak > 0:
                drawdown = (peak - value) / peak * 100
                max_drawdown = max(max_drawdown, drawdown)

        # Current drawdown
        current_value = values[-1]
        current_drawdown = (peak - current_value) / peak * 100 if peak > 0 else 0

        # Days since ATH
        days_since_ath = len(values) - 1 - peak_idx

        return max_drawdown, current_drawdown, days_since_ath

    def _calculate_var(self, returns: list[float]) -> tuple[float, float]:
        """
        Calculate Value at Risk (VaR) using historical simulation.

        Returns:
            (var_95, var_99) as percentages
        """
        if len(returns) < 30:
            return 0.0, 0.0

        sorted_returns = sorted(returns)

        # 95% VaR (5th percentile)
        idx_95 = int(len(sorted_returns) * 0.05)
        var_95 = abs(sorted_returns[idx_95]) * 100

        # 99% VaR (1st percentile)
        idx_99 = int(len(sorted_returns) * 0.01)
        var_99 = abs(sorted_returns[max(0, idx_99)]) * 100

        return var_95, var_99

    def _calculate_volatility(self, returns: list[float]) -> float:
        """Calculate annualized volatility."""
        if len(returns) < 2:
            return 0.0

        std_dev = self._std_dev(returns)
        # Annualize
        annual_vol = std_dev * math.sqrt(365) * 100

        return annual_vol

    def _calculate_beta(self, portfolio_returns: list[float]) -> float:
        """
        Calculate beta vs BTC.

        Beta = Cov(Portfolio, BTC) / Var(BTC)
        """
        if len(self._btc_returns) < 30 or len(portfolio_returns) < 30:
            return 1.0

        # Align lengths
        min_len = min(len(portfolio_returns), len(self._btc_returns))
        port_ret = portfolio_returns[-min_len:]
        btc_ret = self._btc_returns[-min_len:]

        # Calculate covariance
        mean_port = sum(port_ret) / len(port_ret)
        mean_btc = sum(btc_ret) / len(btc_ret)

        covariance = sum((p - mean_port) * (b - mean_btc) for p, b in zip(port_ret, btc_ret)) / len(port_ret)

        # BTC variance
        btc_variance = sum((b - mean_btc) ** 2 for b in btc_ret) / len(btc_ret)

        if btc_variance == 0:
            return 1.0

        beta = covariance / btc_variance

        return beta

    def _std_dev(self, values: list[float]) -> float:
        """Calculate standard deviation."""
        if len(values) < 2:
            return 0.0

        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)

        return math.sqrt(variance)

    def _determine_risk_status(
        self,
        max_drawdown: float,
        current_drawdown: float,
        volatility: float,
        var_95: float,
    ) -> str:
        """
        Determine overall risk status.

        Returns: Low, Medium, High, or Critical
        """
        score = 0

        # Drawdown scoring
        if current_drawdown > 30:
            score += 3
        elif current_drawdown > 20:
            score += 2
        elif current_drawdown > 10:
            score += 1

        # Volatility scoring
        if volatility > 100:
            score += 3
        elif volatility > 60:
            score += 2
        elif volatility > 40:
            score += 1

        # VaR scoring
        if var_95 > 10:
            score += 2
        elif var_95 > 5:
            score += 1

        # Determine status
        if score >= 7:
            return "Critical"
        elif score >= 4:
            return "High"
        elif score >= 2:
            return "Medium"
        else:
            return "Low"

    async def stress_test(
        self,
        portfolio_value: float,
        scenario: str = "2022_crash",
    ) -> dict[str, Any]:
        """
        Perform stress test simulation.

        Scenarios:
        - 2022_crash: -75% drawdown like 2022
        - black_swan: -50% sudden drop
        - moderate: -30% correction
        """
        scenarios = {
            "2022_crash": {
                "name": "2022 Crypto Crash",
                "drawdown": -75,
                "duration_days": 365,
                "description": "Extended bear market like 2022",
            },
            "black_swan": {
                "name": "Black Swan Event",
                "drawdown": -50,
                "duration_days": 7,
                "description": "Sudden market collapse",
            },
            "moderate": {
                "name": "Moderate Correction",
                "drawdown": -30,
                "duration_days": 30,
                "description": "Standard correction",
            },
            "flash_crash": {
                "name": "Flash Crash",
                "drawdown": -20,
                "duration_days": 1,
                "description": "Brief sharp decline",
            },
        }

        if scenario not in scenarios:
            scenario = "moderate"

        s = scenarios[scenario]
        projected_value = portfolio_value * (1 + s["drawdown"] / 100)
        loss_amount = portfolio_value - projected_value

        return {
            "scenario": s["name"],
            "description": s["description"],
            "drawdown_pct": s["drawdown"],
            "duration_days": s["duration_days"],
            "current_value": round(portfolio_value, 2),
            "projected_value": round(projected_value, 2),
            "potential_loss": round(loss_amount, 2),
            "survival_probability": self._estimate_survival(s["drawdown"]),
        }

    def _estimate_survival(self, drawdown: float) -> str:
        """Estimate portfolio survival probability."""
        if drawdown > -30:
            return "High"
        elif drawdown > -50:
            return "Medium"
        else:
            return "Low - Consider hedging"

    async def _publish_to_ha(self, metrics: RiskMetrics) -> None:
        """Publish risk metrics to Home Assistant."""
        if not self._mqtt:
            return

        try:
            await self._publish_sensor("portfolio_sharpe", metrics.sharpe_ratio)
            await self._publish_sensor("portfolio_sortino", metrics.sortino_ratio)
            await self._publish_sensor("portfolio_max_drawdown", metrics.max_drawdown)
            await self._publish_sensor("portfolio_current_drawdown", metrics.current_drawdown)
            await self._publish_sensor("portfolio_var_95", metrics.var_95)
            await self._publish_sensor("risk_status", metrics.risk_status)

            logger.info(f"Published risk metrics - Status: {metrics.risk_status}")

        except Exception as e:
            logger.error(f"Failed to publish risk metrics: {e}")

    async def _publish_sensor(self, sensor_id: str, value: Any) -> None:
        """Publish single sensor value."""
        if self._mqtt and value is not None:
            topic = f"crypto_inspect/{sensor_id}/state"
            payload = str(round(value, 2)) if isinstance(value, float) else str(value)
            await self._mqtt.publish(topic, payload)

    def get_risk_summary(self) -> dict[str, Any]:
        """Get risk summary for display."""
        if not self._last_metrics:
            return {
                "status": "Not calculated",
                "recommendation": "Add portfolio snapshots to enable risk tracking",
            }

        m = self._last_metrics
        recommendations = []

        if m.current_drawdown > 20:
            recommendations.append("Consider reducing position sizes")
        if m.volatility_30d > 60:
            recommendations.append("High volatility - use stop losses")
        if m.var_95 > 8:
            recommendations.append("High daily risk exposure")
        if m.sharpe_ratio < 0.5:
            recommendations.append("Risk-adjusted returns are low")

        return {
            "status": m.risk_status,
            "sharpe": round(m.sharpe_ratio, 2),
            "current_drawdown": f"{m.current_drawdown:.1f}%",
            "max_drawdown": f"{m.max_drawdown:.1f}%",
            "daily_var_95": f"{m.var_95:.1f}%",
            "recommendations": recommendations or ["Portfolio risk is acceptable"],
        }
