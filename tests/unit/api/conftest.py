"""
API Test Fixtures.

Provides FastAPI TestClient and mock services for API endpoint testing.
"""

import os
import sys
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

# Add src to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.insert(0, os.path.join(project_root, "src"))


@pytest.fixture
def app():
    """Create FastAPI app for testing."""
    from fastapi import FastAPI

    from api.router import api_router

    app = FastAPI()
    # Note: Routes already have /api prefix, don't add it again
    app.include_router(api_router)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    from fastapi.testclient import TestClient

    return TestClient(app)


# === Mock Data Fixtures ===


@pytest.fixture
def mock_price_data():
    """Sample price data for analysis endpoints."""
    return {
        "BTC/USDT": {
            "price": 100000.0,
            "change_24h": 2.5,
            "volume_24h": 50000000000.0,
            "high_24h": 102000.0,
            "low_24h": 98000.0,
        },
        "ETH/USDT": {
            "price": 3500.0,
            "change_24h": -1.2,
            "volume_24h": 20000000000.0,
            "high_24h": 3600.0,
            "low_24h": 3400.0,
        },
    }


@pytest.fixture
def mock_analysis_result():
    """Sample technical analysis result."""
    return {
        "symbol": "BTC/USDT",
        "timestamp": datetime.now().isoformat(),
        "indicators": {
            "rsi": {"value": 55.5, "signal": "neutral"},
            "macd": {"value": 150.0, "signal": "bullish", "histogram": 50.0},
            "bb": {"upper": 105000, "middle": 100000, "lower": 95000, "position": 0.5},
        },
        "trend": "uptrend",
        "score": 65,
        "recommendation": "hold",
    }


@pytest.fixture
def mock_investor_status():
    """Sample investor status data."""
    return {
        "do_nothing_ok": {"value": True, "reason_ru": "Всё спокойно", "state": "🟢 Да"},
        "phase": {"value": "accumulation", "name_ru": "Накопление", "confidence": 75},
        "calm": {"score": 70, "level": "calm", "message_ru": "Можно не волноваться"},
        "red_flags": {"count": 0, "flags": [], "flags_list": "✅ Нет флагов"},
        "tension": {"score": 30, "state": "🟢 Низкое", "level_ru": "Норма"},
        "dca": {"signal": "neutral", "state": "🟡 Нейтрально", "total_amount": 100},
    }


@pytest.fixture
def mock_bybit_account():
    """Sample Bybit account data."""
    return {
        "total_equity": 50000.0,
        "total_available": 45000.0,
        "total_margin_used": 5000.0,
        "total_unrealized_pnl": 250.0,
        "account_type": "UNIFIED",
        "balances": [
            {"coin": "USDT", "wallet_balance": 30000.0, "usd_value": 30000.0},
            {"coin": "BTC", "wallet_balance": 0.2, "usd_value": 20000.0},
        ],
        "positions": [],
        "earn_positions": [],
    }


@pytest.fixture
def mock_portfolio_status():
    """Sample portfolio status."""
    return {
        "total_value": 75000.0,
        "total_cost": 70000.0,
        "total_pnl": 5000.0,
        "total_pnl_percent": 7.14,
        "holdings": [
            {"symbol": "BTC", "amount": 0.5, "value": 50000.0, "pnl_percent": 10.0},
            {"symbol": "ETH", "amount": 5.0, "value": 17500.0, "pnl_percent": 5.0},
        ],
    }


@pytest.fixture
def mock_signal():
    """Sample signal data."""
    return {
        "id": "sig_123",
        "symbol": "BTC/USDT",
        "signal_type": "rsi_oversold",
        "direction": "long",
        "strength": 75,
        "price_at_signal": 95000.0,
        "timestamp": datetime.now().isoformat(),
        "outcome": None,
    }


@pytest.fixture
def mock_alert():
    """Sample alert data."""
    return {
        "id": "alert_123",
        "symbol": "BTC/USDT",
        "condition": "above",
        "target_price": 105000.0,
        "enabled": True,
        "triggered": False,
        "created_at": datetime.now().isoformat(),
    }


@pytest.fixture
def mock_candle_data():
    """Sample candlestick data."""
    now = datetime.now()
    return [
        {
            "timestamp": (now - timedelta(hours=i)).isoformat(),
            "open": 100000 + i * 100,
            "high": 100500 + i * 100,
            "low": 99500 + i * 100,
            "close": 100200 + i * 100,
            "volume": 1000000 + i * 10000,
        }
        for i in range(24)
    ]


@pytest.fixture
def mock_summary_data():
    """Sample smart summary data."""
    return {
        "market_pulse": {
            "sentiment_en": "Cautiously Bullish",
            "sentiment_ru": "Осторожно бычий",
            "confidence": 70,
            "reason_en": "RSI neutral, MACD bullish",
            "reason_ru": "RSI нейтральный, MACD бычий",
        },
        "portfolio_health": {
            "status_en": "Good",
            "status_ru": "Хорошо",
            "score": 75,
            "main_issue_en": "None",
            "main_issue_ru": "Нет проблем",
        },
        "today_action": {
            "action_en": "Hold positions",
            "action_ru": "Держать позиции",
            "priority_en": "Low",
            "priority_ru": "Низкий",
        },
    }


@pytest.fixture
def mock_briefing_data():
    """Sample briefing data."""
    return {
        "title": "Morning Briefing",
        "summary": "Market is stable, no major events.",
        "market_overview": {"btc_change": 1.5, "eth_change": -0.5},
        "key_events": [],
        "recommendation": "Continue DCA strategy",
    }


@pytest.fixture
def mock_goal_data():
    """Sample goal tracking data."""
    return {
        "goal_name": "First 100K",
        "goal_target": 100000.0,
        "goal_current": 75000.0,
        "goal_progress": 75.0,
        "goal_remaining": 25000.0,
        "goal_days_estimate": 180,
        "goal_status": "on_track",
        "milestones_reached": ["25K", "50K"],
        "next_milestone": "75K",
    }


@pytest.fixture
def mock_backtest_result():
    """Sample backtest result."""
    return {
        "strategy": "fixed_dca",
        "symbol": "BTC",
        "period_days": 365,
        "total_invested": 12000.0,
        "final_value": 15600.0,
        "total_return_pct": 30.0,
        "buys_count": 52,
        "avg_buy_price": 85000.0,
        "current_price": 100000.0,
    }


@pytest.fixture
def mock_risk_metrics():
    """Sample risk metrics."""
    return {
        "sharpe_ratio": 1.5,
        "sortino_ratio": 2.0,
        "max_drawdown": -15.0,
        "current_drawdown": -5.0,
        "var_95": -8.0,
        "volatility_30d": 45.0,
        "risk_status": "moderate",
    }


# === Mock Service Patches ===


@pytest.fixture
def mock_services(
    mock_analysis_result,
    mock_investor_status,
    mock_bybit_account,
    mock_portfolio_status,
    mock_signal,
    mock_candle_data,
    mock_summary_data,
    mock_briefing_data,
    mock_goal_data,
    mock_backtest_result,
    mock_risk_metrics,
):
    """Patch all services with mocks."""
    patches = {}

    # Analysis service
    patches["technical"] = patch(
        "service.analysis.technical.TechnicalAnalyzer.analyze",
        new_callable=AsyncMock,
        return_value=mock_analysis_result,
    )

    # Investor service
    patches["investor"] = patch(
        "service.analysis.investor.get_investor_status",
        new_callable=AsyncMock,
        return_value=mock_investor_status,
    )

    return patches
