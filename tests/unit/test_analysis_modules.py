"""Tests for analysis modules."""

import os
import sys
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))


# ==============================================================================
# RISK ANALYZER TESTS
# ==============================================================================


class TestRiskMetrics:
    """Tests for RiskMetrics dataclass."""

    def test_default_values(self):
        """Should have sensible defaults."""
        from services.analysis.risk import RiskMetrics

        metrics = RiskMetrics()
        assert metrics.sharpe_ratio == 0.0
        assert metrics.sortino_ratio == 0.0
        assert metrics.risk_status == "Medium"

    def test_to_dict(self):
        """Should convert to dict with rounded values."""
        from services.analysis.risk import RiskMetrics

        metrics = RiskMetrics(
            sharpe_ratio=1.5678,
            sortino_ratio=2.3456,
            max_drawdown=-15.789,
            current_drawdown=-5.123,
            days_since_ath=10,
            var_95=-8.567,
            var_99=-12.345,
            volatility_30d=45.678,
            volatility_7d=55.432,
            beta_vs_btc=1.234,
            risk_status="High",
            calculated_at=datetime(2024, 1, 15, 10, 30),
            portfolio_value=50000.567,
        )

        result = metrics.to_dict()

        assert result["sharpe_ratio"] == 1.57
        assert result["sortino_ratio"] == 2.35
        assert result["max_drawdown"] == -15.79
        assert result["risk_status"] == "High"
        assert result["portfolio_value"] == 50000.57


class TestRiskAnalyzer:
    """Tests for RiskAnalyzer class."""

    def test_init(self):
        """Should initialize with empty state."""
        from services.analysis.risk import RiskAnalyzer

        analyzer = RiskAnalyzer()
        assert analyzer.last_metrics is None

    def test_add_portfolio_snapshot(self):
        """Should track portfolio history."""
        from services.analysis.risk import RiskAnalyzer

        analyzer = RiskAnalyzer()
        analyzer.add_portfolio_snapshot(50000)
        analyzer.add_portfolio_snapshot(51000)
        analyzer.add_portfolio_snapshot(49000)

        assert len(analyzer._portfolio_history) == 3

    def test_set_btc_returns(self):
        """Should store BTC returns for beta calc."""
        from services.analysis.risk import RiskAnalyzer

        analyzer = RiskAnalyzer()
        returns = [0.01, -0.02, 0.015, -0.005]
        analyzer.set_btc_returns(returns)

        assert analyzer._btc_returns == returns

    @pytest.mark.asyncio
    async def test_calculate_risk_metrics_insufficient_data(self):
        """Should return unknown risk with insufficient data."""
        from services.analysis.risk import RiskAnalyzer

        analyzer = RiskAnalyzer()
        # Only 5 values, need at least 7
        metrics = await analyzer.calculate_risk_metrics([100, 101, 102, 103, 104])

        assert metrics.risk_status == "Unknown"

    @pytest.mark.asyncio
    async def test_calculate_risk_metrics_with_data(self):
        """Should calculate metrics with sufficient data."""
        from services.analysis.risk import RiskAnalyzer

        analyzer = RiskAnalyzer()
        # Provide 30 days of data
        values = [50000 + i * 100 for i in range(35)]  # Uptrend

        with patch.object(analyzer, "_publish_to_ha", new_callable=AsyncMock):
            metrics = await analyzer.calculate_risk_metrics(values)

        assert metrics.sharpe_ratio != 0
        assert metrics.calculated_at is not None
        assert metrics.portfolio_value == values[-1]

    def test_calculate_returns(self):
        """Should calculate daily returns correctly."""
        from services.analysis.risk import RiskAnalyzer

        analyzer = RiskAnalyzer()
        values = [100, 110, 105, 115]

        returns = analyzer._calculate_returns(values)

        assert len(returns) == 3
        assert abs(returns[0] - 0.1) < 0.001  # 10% gain
        assert abs(returns[1] - (-0.0455)) < 0.01  # ~4.5% loss
        assert abs(returns[2] - 0.0952) < 0.01  # ~9.5% gain


# ==============================================================================
# BACKTEST SERVICE TESTS
# ==============================================================================


class TestBacktestService:
    """Tests for backtest service."""

    def test_import(self):
        """Should be importable."""
        from services.analysis.backtest import DCABacktester

        assert DCABacktester is not None

    def test_backtest_result_dataclass(self):
        """Should have backtest result dataclass."""
        from services.analysis.backtest import BacktestResult

        # BacktestResult is a dataclass with many fields
        assert BacktestResult is not None


# ==============================================================================
# CORRELATION SERVICE TESTS
# ==============================================================================


class TestCorrelationAnalyzer:
    """Tests for correlation analyzer."""

    def test_import(self):
        """Should be importable."""
        from services.analysis.correlation import CorrelationTracker

        assert CorrelationTracker is not None

    def test_correlation_result(self):
        """Should have correlation pair."""
        from services.analysis.correlation import CorrelationPair

        assert CorrelationPair is not None


# ==============================================================================
# ALTSEASON ANALYZER TESTS
# ==============================================================================


class TestAltseasonAnalyzer:
    """Tests for altseason analyzer."""

    def test_import(self):
        """Should be importable."""
        from services.analysis.altseason import AltseasonAnalyzer

        assert AltseasonAnalyzer is not None

    def test_altseason_data(self):
        """Should have altseason data class."""
        from services.analysis.altseason import AltseasonData

        # AltseasonData is a dataclass
        assert AltseasonData is not None


# ==============================================================================
# STABLECOIN ANALYZER TESTS
# ==============================================================================


class TestStablecoinAnalyzer:
    """Tests for stablecoin analyzer."""

    def test_import(self):
        """Should be importable."""
        from services.analysis.stablecoins import StablecoinAnalyzer

        assert StablecoinAnalyzer is not None

    def test_stablecoin_data(self):
        """Should have stablecoin data class."""
        from services.analysis.stablecoins import StablecoinData

        assert StablecoinData is not None


# ==============================================================================
# GAS TRACKER TESTS
# ==============================================================================


class TestGasTracker:
    """Tests for gas tracker."""

    def test_import(self):
        """Should be importable."""
        from services.analysis.gas import GasTracker

        assert GasTracker is not None

    def test_gas_prices_data(self):
        """Should have gas data class."""
        from services.analysis.gas import GasData

        assert GasData is not None


# ==============================================================================
# WHALE TRACKER TESTS
# ==============================================================================


class TestWhaleTracker:
    """Tests for whale tracker."""

    def test_import(self):
        """Should be importable."""
        from services.analysis.whales import WhaleTracker

        assert WhaleTracker is not None


# ==============================================================================
# LIQUIDATION TRACKER TESTS
# ==============================================================================


class TestLiquidationTracker:
    """Tests for liquidation tracker."""

    def test_import(self):
        """Should be importable."""
        from services.analysis.liquidations import LiquidationTracker

        assert LiquidationTracker is not None


# ==============================================================================
# DIVERGENCE DETECTOR TESTS
# ==============================================================================


class TestDivergenceDetector:
    """Tests for divergence detector."""

    def test_import(self):
        """Should be importable."""
        from services.analysis.divergences import DivergenceDetector

        assert DivergenceDetector is not None


# ==============================================================================
# DCA ANALYZER TESTS
# ==============================================================================


class TestDCAAnalyzer:
    """Tests for DCA analyzer."""

    def test_import(self):
        """Should be importable."""
        from services.analysis.dca import DCACalculator

        assert DCACalculator is not None


# ==============================================================================
# VOLATILITY ANALYZER TESTS
# ==============================================================================


class TestVolatilityAnalyzer:
    """Tests for volatility analyzer."""

    def test_import(self):
        """Should be importable."""
        from services.analysis.volatility import VolatilityTracker

        assert VolatilityTracker is not None


# ==============================================================================
# MACRO ANALYZER TESTS
# ==============================================================================


class TestMacroAnalyzer:
    """Tests for macro/traditional finance analyzer."""

    def test_import(self):
        """Should be importable."""
        from services.analysis.traditional import TraditionalFinanceTracker

        assert TraditionalFinanceTracker is not None


# ==============================================================================
# PROFIT TAKING ANALYZER TESTS
# ==============================================================================


class TestProfitTakingAnalyzer:
    """Tests for profit taking analyzer."""

    def test_import(self):
        """Should be importable."""
        from services.analysis.profit_taking import ProfitTakingAdvisor

        assert ProfitTakingAdvisor is not None


# ==============================================================================
# ARBITRAGE ANALYZER TESTS
# ==============================================================================


class TestArbitrageAnalyzer:
    """Tests for arbitrage analyzer."""

    def test_import(self):
        """Should be importable."""
        from services.analysis.arbitrage import ArbitrageScanner

        assert ArbitrageScanner is not None


# ==============================================================================
# TRADITIONAL ASSETS ANALYZER TESTS
# ==============================================================================


class TestTraditionalAnalyzer:
    """Tests for traditional assets analyzer."""

    def test_import(self):
        """Should be importable."""
        from services.analysis.traditional import TraditionalFinanceStatus

        assert TraditionalFinanceStatus is not None


# ==============================================================================
# TOKEN UNLOCKS TRACKER TESTS
# ==============================================================================


class TestUnlocksTracker:
    """Tests for token unlocks tracker."""

    def test_import(self):
        """Should be importable."""
        from services.analysis.unlocks import UnlockTracker

        assert UnlockTracker is not None


# ==============================================================================
# TA PUBLISHER TESTS
# ==============================================================================


class TestTAPublisher:
    """Tests for TA publisher."""

    def test_import(self):
        """Should be importable."""
        from services.analysis.ta_publisher import TAPublisher

        assert TAPublisher is not None


# ==============================================================================
# EXCHANGE FLOW TRACKER TESTS
# ==============================================================================


class TestExchangeFlowTracker:
    """Tests for exchange flow tracker."""

    def test_import(self):
        """Should be importable."""
        from services.analysis.exchange_flow import ExchangeFlowAnalyzer

        assert ExchangeFlowAnalyzer is not None
