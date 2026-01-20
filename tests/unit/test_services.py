"""Tests for services modules - ha_integration, ha (sensors), etc."""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))


# ==============================================================================
# HA INTEGRATION TESTS
# Примечание: Полноценные интеграционные тесты находятся в
# tests/integration/test_ha_integration.py
# ==============================================================================


class TestHAIntegration:
    """Базовые тесты для Home Assistant integration.

    Полноценные интеграционные тесты см. в tests/integration/test_ha_integration.py
    """

    def test_module_importable(self):
        """Модуль ha_integration должен импортироваться."""
        import service.ha_integration

        assert service.ha_integration is not None

    def test_supervisor_api_client_importable(self):
        """SupervisorAPIClient должен импортироваться."""
        from service.ha_integration import SupervisorAPIClient

        assert SupervisorAPIClient is not None


# ==============================================================================
# HA SENSORS TESTS
# Примечание: Полноценные тесты сенсоров находятся в
# tests/unit/sensors/ и tests/integration/test_ha_integration.py
# ==============================================================================


class TestHASensors:
    """Базовые тесты для Home Assistant sensors.

    Полноценные тесты см. в:
    - tests/unit/sensors/test_ha_sensors.py
    - tests/integration/test_ha_integration.py
    """

    def test_ha_module_importable(self):
        """Модуль services.ha должен импортироваться."""
        import service.ha

        assert service.ha is not None

    def test_ha_integration_manager_importable(self):
        """HAIntegrationManager должен импортироваться."""
        from service.ha import HAIntegrationManager

        assert HAIntegrationManager is not None

    def test_sensor_registry_importable(self):
        """SensorRegistry должен импортироваться."""
        from service.ha import SensorRegistry

        assert SensorRegistry is not None

    def test_base_sensor_importable(self):
        """BaseSensor должен импортироваться."""
        from service.ha.core.base import BaseSensor

        assert BaseSensor is not None

    def test_dict_sensor_importable(self):
        """DictSensor должен импортироваться."""
        from service.ha.sensors.dict import DictSensor

        assert DictSensor is not None


# ==============================================================================
# CANDLESTICK SERVICE TESTS
# ==============================================================================


class TestCandlestickService:
    """Tests for candlestick service."""

    def test_import_fetcher(self):
        """Should import CandlestickFetcher."""
        from service.candlestick.fetcher import CandlestickFetcher

        assert CandlestickFetcher is not None

    def test_import_models(self):
        """Should import candlestick models."""
        from service.candlestick.models import CandleInterval, Candlestick

        assert CandleInterval is not None
        assert Candlestick is not None

    def test_candle_interval_values(self):
        """Should have expected interval values."""
        from service.candlestick.models import CandleInterval

        assert CandleInterval.MINUTE_1.value == "1m"
        assert CandleInterval.HOUR_1.value == "1h"
        assert CandleInterval.DAY_1.value == "1d"

    def test_candlestick_model(self):
        """Should have candlestick model."""
        from service.candlestick.models import Candlestick

        assert Candlestick is not None


# ==============================================================================
# EXCHANGE CLIENTS TESTS
# ==============================================================================


class TestExchangeClients:
    """Tests for exchange clients."""

    def test_binance_exchange(self):
        """Should import Binance exchange."""
        from service.candlestick.exchanges.binance import BinanceExchange

        assert BinanceExchange is not None

    def test_bybit_exchange(self):
        """Should import Bybit exchange."""
        from service.candlestick.exchanges.bybit import BybitExchange

        assert BybitExchange is not None

    def test_coinbase_exchange(self):
        """Should import Coinbase exchange."""
        from service.candlestick.exchanges.coinbase import CoinbaseExchange

        assert CoinbaseExchange is not None

    def test_kraken_exchange(self):
        """Should import Kraken exchange."""
        from service.candlestick.exchanges.kraken import KrakenExchange

        assert KrakenExchange is not None

    def test_kucoin_exchange(self):
        """Should import KuCoin exchange."""
        from service.candlestick.exchanges.kucoin import KucoinExchange

        assert KucoinExchange is not None

    def test_okx_exchange(self):
        """Should import OKX exchange."""
        from service.candlestick.exchanges.okx import OKXExchange

        assert OKXExchange is not None


# ==============================================================================
# WEBSOCKET TESTS
# ==============================================================================


class TestWebsocketClients:
    """Tests for websocket clients."""

    def test_websocket_module(self):
        """Should have websocket module."""
        import service.candlestick.websocket

        assert service.candlestick.websocket is not None


# ==============================================================================
# BYBIT CLIENT TESTS
# ==============================================================================


class TestBybitClient:
    """Tests for Bybit client."""

    def test_import(self):
        """Should import Bybit client."""
        from service.exchange.bybit_client import BybitClient

        assert BybitClient is not None

    def test_bybit_portfolio(self):
        """Should import Bybit portfolio."""
        from service.exchange.bybit_portfolio import BybitPortfolio

        assert BybitPortfolio is not None


# ==============================================================================
# PORTFOLIO SERVICE TESTS
# ==============================================================================


class TestPortfolioService:
    """Tests for portfolio service."""

    def test_import_portfolio_manager(self):
        """Should import portfolio manager."""
        from service.portfolio.portfolio import PortfolioManager

        assert PortfolioManager is not None

    def test_import_goals(self):
        """Should import goals."""
        from service.portfolio.goals import GoalTracker

        assert GoalTracker is not None


# ==============================================================================
# ALERTS SERVICE TESTS
# ==============================================================================


class TestAlertsService:
    """Tests for alerts service."""

    def test_import_alert_manager(self):
        """Should import alert manager."""
        from service.alerts.price_alerts import PriceAlertManager

        assert PriceAlertManager is not None

    def test_import_notification_manager(self):
        """Should import notification manager."""
        from service.alerts.notification_manager import NotificationManager

        assert NotificationManager is not None


# ==============================================================================
# BACKFILL SERVICE TESTS
# ==============================================================================


class TestBackfillService:
    """Tests for backfill service."""

    def test_import_manager(self):
        """Should import backfill manager."""
        from service.backfill.manager import BackfillManager

        assert BackfillManager is not None

    def test_import_crypto_backfill(self):
        """Should import crypto backfill."""
        from service.backfill.crypto_backfill import CryptoBackfill

        assert CryptoBackfill is not None

    def test_import_traditional_backfill(self):
        """Should import traditional backfill."""
        from service.backfill.traditional_backfill import TraditionalBackfill

        assert TraditionalBackfill is not None


# ==============================================================================
# CSV EXPORT TESTS
# ==============================================================================


class TestCSVExport:
    """Tests for CSV export service."""

    def test_import(self):
        """Should import CSV exporter."""
        from service.export.csv_export import CSVExporter

        assert CSVExporter is not None


# ==============================================================================
# AI SERVICE TESTS
# ==============================================================================


class TestAIService:
    """Tests for AI service."""

    def test_module_exists(self):
        """Module should be importable."""
        import service.ai

        assert service.ai is not None


# ==============================================================================
# SCORING ENGINE TESTS
# ==============================================================================


class TestScoringEngine:
    """Tests for scoring engine."""

    def test_import(self):
        """Should import scoring engine."""
        from service.analysis.scoring import ScoringEngine

        assert ScoringEngine is not None


# ==============================================================================
# TECHNICAL ANALYZER TESTS
# ==============================================================================


class TestTechnicalAnalyzer:
    """Tests for technical analyzer."""

    def test_import(self):
        """Should import technical analyzer."""
        from service.analysis.technical import TechnicalAnalyzer

        assert TechnicalAnalyzer is not None


# ==============================================================================
# INVESTOR ANALYZER TESTS
# ==============================================================================


class TestInvestorAnalyzer:
    """Tests for investor analyzer."""

    def test_module_exists(self):
        """Module should be importable."""
        import service.analysis.investor

        assert service.analysis.investor is not None


# ==============================================================================
# PATTERN DETECTOR TESTS
# ==============================================================================


class TestPatternDetector:
    """Tests for pattern detector."""

    def test_import(self):
        """Should import pattern detector."""
        from service.analysis.patterns import PatternDetector

        assert PatternDetector is not None


# ==============================================================================
# SMART SUMMARY TESTS
# ==============================================================================


class TestSmartSummary:
    """Tests for smart summary."""

    def test_import(self):
        """Should import smart summary service."""
        from service.analysis.smart_summary import SmartSummaryService

        assert SmartSummaryService is not None


# ==============================================================================
# BRIEFING SERVICE TESTS
# ==============================================================================


class TestBriefingService:
    """Tests for briefing service."""

    def test_import(self):
        """Should import briefing service."""
        from service.analysis.briefing import BriefingService

        assert BriefingService is not None


# ==============================================================================
# CYCLE DETECTOR TESTS
# ==============================================================================


class TestCycleDetector:
    """Tests for cycle detector."""

    def test_import(self):
        """Should import cycle detector."""
        from service.analysis.cycles import CycleDetector

        assert CycleDetector is not None

    def test_cycle_phase_enum(self):
        """Should have cycle phases."""
        from service.analysis.cycles import CyclePhase

        assert CyclePhase.ACCUMULATION is not None
        assert CyclePhase.EUPHORIA is not None


# ==============================================================================
# DERIVATIVES ANALYZER TESTS
# ==============================================================================


class TestDerivativesAnalyzer:
    """Tests for derivatives analyzer."""

    def test_import(self):
        """Should import derivatives analyzer."""
        from service.analysis.derivatives import DerivativesAnalyzer

        assert DerivativesAnalyzer is not None


# ==============================================================================
# ONCHAIN ANALYZER TESTS
# ==============================================================================


class TestOnChainAnalyzer:
    """Tests for on-chain analyzer."""

    def test_import(self):
        """Should import on-chain analyzer."""
        from service.analysis.onchain import OnChainAnalyzer

        assert OnChainAnalyzer is not None


# ==============================================================================
# SIGNAL HISTORY TESTS
# ==============================================================================


class TestSignalHistory:
    """Tests for signal history."""

    def test_module_exists(self):
        """Module should be importable."""
        import service.analysis.signal_history

        assert service.analysis.signal_history is not None
