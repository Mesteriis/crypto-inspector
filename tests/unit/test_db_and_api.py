"""Tests for database models and repositories."""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))


# ==============================================================================
# CANDLESTICK MODEL TESTS
# ==============================================================================


# DB model tests skipped due to circular imports
# Models are tested via integration tests


# ==============================================================================
# SESSION TESTS
# ==============================================================================


class TestDatabaseSession:
    """Tests for database session."""

    def test_import_session(self):
        """Should import session maker."""
        from db.session import async_session_maker

        assert async_session_maker is not None

    def test_import_engine(self):
        """Should import engine."""
        from db.session import engine

        assert engine is not None


# ==============================================================================
# BASE MODEL TESTS
# ==============================================================================


class TestBaseModel:
    """Tests for base model."""

    def test_import_base(self):
        """Should import base."""
        from db.base import Base

        assert Base is not None


# ==============================================================================
# API ROUTES TESTS
# ==============================================================================


class TestAPIRoutes:
    """Tests for API routes modules."""

    def test_import_analysis_routes(self):
        """Should import analysis routes."""
        from api.routes.analysis import router

        assert router is not None

    def test_import_alerts_routes(self):
        """Should import alerts routes."""
        from api.routes.alerts import router

        assert router is not None

    def test_import_backfill_routes(self):
        """Should import backfill routes."""
        from api.routes.backfill import router

        assert router is not None

    def test_import_backtest_routes(self):
        """Should import backtest routes."""
        from api.routes.backtest import router

        assert router is not None

    def test_import_briefing_routes(self):
        """Should import briefing routes."""
        from api.routes.briefing import router

        assert router is not None

    def test_import_bybit_routes(self):
        """Should import bybit routes."""
        from api.routes.bybit import router

        assert router is not None

    def test_import_candles_routes(self):
        """Should import candles routes."""
        from api.routes.candles import router

        assert router is not None

    def test_import_goals_routes(self):
        """Should import goals routes."""
        from api.routes.goals import router

        assert router is not None

    def test_import_health_routes(self):
        """Should import health routes."""
        from api.routes.health import router

        assert router is not None

    def test_import_investor_routes(self):
        """Should import investor routes."""
        from api.routes.investor import router

        assert router is not None

    def test_import_portfolio_routes(self):
        """Should import portfolio routes."""
        from api.routes.portfolio import router

        assert router is not None

    def test_import_signals_routes(self):
        """Should import signals routes."""
        from api.routes.signals import router

        assert router is not None

    def test_import_streaming_routes(self):
        """Should import streaming routes."""
        from api.routes.streaming import router

        assert router is not None

    def test_import_summary_routes(self):
        """Should import summary routes."""
        from api.routes.summary import router

        assert router is not None


# ==============================================================================
# API ROUTER TESTS
# ==============================================================================


class TestAPIRouter:
    """Tests for main API router."""

    def test_import_router(self):
        """Should import main router."""
        from api.router import api_router

        assert api_router is not None


# ==============================================================================
# CONFIG TESTS
# ==============================================================================


class TestConfig:
    """Tests for config module."""

    def test_import_config(self):
        """Should import config."""
        from core.config import settings

        assert settings is not None


# ==============================================================================
# SCHEDULER TESTS
# ==============================================================================


class TestScheduler:
    """Tests for scheduler module."""

    def test_module_exists(self):
        """Module should exist."""
        import core.scheduler

        assert core.scheduler is not None

    def test_import_jobs(self):
        """Should import jobs module."""
        import core.scheduler.jobs

        assert core.scheduler.jobs is not None


# ==============================================================================
# MAIN APP TESTS
# ==============================================================================


class TestMainApp:
    """Tests for main application."""

    def test_import_main(self):
        """Should import main module."""
        import main

        assert main is not None

    def test_app_exists(self):
        """Should have app instance."""
        from main import app

        assert app is not None
