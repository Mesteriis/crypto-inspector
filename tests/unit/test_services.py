"""Tests for services modules - ha_integration, ha_sensors, etc."""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))


# ==============================================================================
# HA INTEGRATION TESTS
# ==============================================================================


class TestHAIntegration:
    """Tests for Home Assistant integration."""

    def test_module_exists(self):
        """Module should be importable."""
        import services.ha_integration

        assert services.ha_integration is not None


# ==============================================================================
# HA SENSORS TESTS
# ==============================================================================


class TestHASensors:
    """Tests for Home Assistant sensors manager."""

    def test_module_exists(self):
        """Module should be importable."""
        import services.ha_sensors

        assert services.ha_sensors is not None


# ==============================================================================
# CANDLESTICK SERVICE TESTS
# ==============================================================================


class TestCandlestickService:
    """Tests for candlestick service."""

    def test_import_fetcher(self):
        """Should import CandlestickFetcher."""
        from services.candlestick.fetcher import CandlestickFetcher

        assert CandlestickFetcher is not None

    def test_import_models(self):
        """Should import candlestick models."""
        from services.candlestick.models import CandleInterval, Candlestick

        assert CandleInterval is not None
        assert Candlestick is not None

    def test_candle_interval_values(self):
        """Should have expected interval values."""
        from services.candlestick.models import CandleInterval

        assert CandleInterval.MINUTE_1.value == "1m"
        assert CandleInterval.HOUR_1.value == "1h"
        assert CandleInterval.DAY_1.value == "1d"

    def test_candlestick_model(self):
        """Should have candlestick model."""
        from services.candlestick.models import Candlestick

        assert Candlestick is not None


# ==============================================================================
# EXCHANGE CLIENTS TESTS
# ==============================================================================


class TestExchangeClients:
    """Tests for exchange clients."""

    def test_binance_exchange(self):
        """Should import Binance exchange."""
        from services.candlestick.exchanges.binance import BinanceExchange

        assert BinanceExchange is not None

    def test_bybit_exchange(self):
        """Should import Bybit exchange."""
        from services.candlestick.exchanges.bybit import BybitExchange

        assert BybitExchange is not None

    def test_coinbase_exchange(self):
        """Should import Coinbase exchange."""
        from services.candlestick.exchanges.coinbase import CoinbaseExchange

        assert CoinbaseExchange is not None

    def test_kraken_exchange(self):
        """Should import Kraken exchange."""
        from services.candlestick.exchanges.kraken import KrakenExchange

        assert KrakenExchange is not None

    def test_kucoin_exchange(self):
        """Should import KuCoin exchange."""
        import services.candlestick.exchanges.kucoin

        assert services.candlestick.exchanges.kucoin is not None

    def test_okx_exchange(self):
        """Should import OKX exchange."""
        from services.candlestick.exchanges.okx import OKXExchange

        assert OKXExchange is not None


# ==============================================================================
# WEBSOCKET TESTS
# ==============================================================================


class TestWebsocketClients:
    """Tests for websocket clients."""

    def test_websocket_module(self):
        """Should have websocket module."""
        import services.candlestick.websocket

        assert services.candlestick.websocket is not None


# ==============================================================================
# BYBIT CLIENT TESTS
# ==============================================================================


class TestBybitClient:
    """Tests for Bybit client."""

    def test_import(self):
        """Should import Bybit client."""
        from services.exchange.bybit_client import BybitClient

        assert BybitClient is not None

    def test_bybit_portfolio(self):
        """Should import Bybit portfolio."""
        from services.exchange.bybit_portfolio import BybitPortfolio

        assert BybitPortfolio is not None


# ==============================================================================
# PORTFOLIO SERVICE TESTS
# ==============================================================================


class TestPortfolioService:
    """Tests for portfolio service."""

    def test_import_portfolio_manager(self):
        """Should import portfolio manager."""
        from services.portfolio.portfolio import PortfolioManager

        assert PortfolioManager is not None

    def test_import_goals(self):
        """Should import goals."""
        from services.portfolio.goals import GoalTracker

        assert GoalTracker is not None


# ==============================================================================
# ALERTS SERVICE TESTS
# ==============================================================================


class TestAlertsService:
    """Tests for alerts service."""

    def test_import_alert_manager(self):
        """Should import alert manager."""
        from services.alerts.price_alerts import PriceAlertManager

        assert PriceAlertManager is not None

    def test_import_notification_manager(self):
        """Should import notification manager."""
        from services.alerts.notification_manager import NotificationManager

        assert NotificationManager is not None


# ==============================================================================
# BACKFILL SERVICE TESTS
# ==============================================================================


class TestBackfillService:
    """Tests for backfill service."""

    def test_import_manager(self):
        """Should import backfill manager."""
        from services.backfill.manager import BackfillManager

        assert BackfillManager is not None

    def test_import_crypto_backfill(self):
        """Should import crypto backfill."""
        from services.backfill.crypto_backfill import CryptoBackfill

        assert CryptoBackfill is not None

    def test_import_traditional_backfill(self):
        """Should import traditional backfill."""
        from services.backfill.traditional_backfill import TraditionalBackfill

        assert TraditionalBackfill is not None


# ==============================================================================
# CSV EXPORT TESTS
# ==============================================================================


class TestCSVExport:
    """Tests for CSV export service."""

    def test_import(self):
        """Should import CSV exporter."""
        from services.export.csv_export import CSVExporter

        assert CSVExporter is not None


# ==============================================================================
# AI SERVICE TESTS
# ==============================================================================


class TestAIService:
    """Tests for AI service."""

    def test_module_exists(self):
        """Module should be importable."""
        import services.ai

        assert services.ai is not None


# ==============================================================================
# SCORING ENGINE TESTS
# ==============================================================================


class TestScoringEngine:
    """Tests for scoring engine."""

    def test_import(self):
        """Should import scoring engine."""
        from services.analysis.scoring import ScoringEngine

        assert ScoringEngine is not None


# ==============================================================================
# TECHNICAL ANALYZER TESTS
# ==============================================================================


class TestTechnicalAnalyzer:
    """Tests for technical analyzer."""

    def test_import(self):
        """Should import technical analyzer."""
        from services.analysis.technical import TechnicalAnalyzer

        assert TechnicalAnalyzer is not None


# ==============================================================================
# INVESTOR ANALYZER TESTS
# ==============================================================================


class TestInvestorAnalyzer:
    """Tests for investor analyzer."""

    def test_module_exists(self):
        """Module should be importable."""
        import services.analysis.investor

        assert services.analysis.investor is not None


# ==============================================================================
# PATTERN DETECTOR TESTS
# ==============================================================================


class TestPatternDetector:
    """Tests for pattern detector."""

    def test_import(self):
        """Should import pattern detector."""
        from services.analysis.patterns import PatternDetector

        assert PatternDetector is not None


# ==============================================================================
# SMART SUMMARY TESTS
# ==============================================================================


class TestSmartSummary:
    """Tests for smart summary."""

    def test_import(self):
        """Should import smart summary service."""
        from services.analysis.smart_summary import SmartSummaryService

        assert SmartSummaryService is not None


# ==============================================================================
# BRIEFING SERVICE TESTS
# ==============================================================================


class TestBriefingService:
    """Tests for briefing service."""

    def test_import(self):
        """Should import briefing service."""
        from services.analysis.briefing import BriefingService

        assert BriefingService is not None


# ==============================================================================
# CYCLE DETECTOR TESTS
# ==============================================================================


class TestCycleDetector:
    """Tests for cycle detector."""

    def test_import(self):
        """Should import cycle detector."""
        from services.analysis.cycles import CycleDetector

        assert CycleDetector is not None

    def test_cycle_phase_enum(self):
        """Should have cycle phases."""
        from services.analysis.cycles import CyclePhase

        assert CyclePhase.ACCUMULATION is not None
        assert CyclePhase.EUPHORIA is not None


# ==============================================================================
# DERIVATIVES ANALYZER TESTS
# ==============================================================================


class TestDerivativesAnalyzer:
    """Tests for derivatives analyzer."""

    def test_import(self):
        """Should import derivatives analyzer."""
        from services.analysis.derivatives import DerivativesAnalyzer

        assert DerivativesAnalyzer is not None


# ==============================================================================
# ONCHAIN ANALYZER TESTS
# ==============================================================================


class TestOnChainAnalyzer:
    """Tests for on-chain analyzer."""

    def test_import(self):
        """Should import on-chain analyzer."""
        from services.analysis.onchain import OnChainAnalyzer

        assert OnChainAnalyzer is not None


# ==============================================================================
# SIGNAL HISTORY TESTS
# ==============================================================================


class TestSignalHistory:
    """Tests for signal history."""

    def test_module_exists(self):
        """Module should be importable."""
        import services.analysis.signal_history

        assert services.analysis.signal_history is not None
