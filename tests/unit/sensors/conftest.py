"""
Pytest fixtures for HA Sensors tests.
"""

import os
import sys
from unittest.mock import MagicMock

import pytest

# Add src to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.insert(0, os.path.join(project_root, "src"))


@pytest.fixture
def mock_mqtt_client():
    """Create a mock MQTT client."""
    client = MagicMock()
    client.publish = MagicMock()
    client.is_connected = MagicMock(return_value=True)
    return client


@pytest.fixture
def sensors_manager(mock_mqtt_client):
    """Create a HAIntegrationManager instance with mock publisher."""
    from service.ha import HAIntegrationManager

    manager = HAIntegrationManager()
    return manager


@pytest.fixture
def sample_price_data():
    """Sample price data for testing."""
    return {
        "BTC/USDT": 100000.50,
        "ETH/USDT": 3500.25,
        "SOL/USDT": 250.75,
    }


@pytest.fixture
def sample_change_data():
    """Sample 24h change data for testing."""
    return {
        "BTC/USDT": 2.5,
        "ETH/USDT": -1.2,
        "SOL/USDT": 5.8,
    }


@pytest.fixture
def sample_investor_data():
    """Sample investor analysis data."""
    return {
        "do_nothing_ok": True,
        "phase": "accumulation",
        "calm_indicator": 75,
        "red_flags": [],
        "market_tension": "low",
        "dca_signal": "buy",
    }


@pytest.fixture
def sample_bybit_data():
    """Sample Bybit portfolio data."""
    return {
        "balance": 50000.00,
        "pnl_24h": 250.50,
        "pnl_7d": 1500.00,
        "unrealized_pnl": -125.00,
        "positions": [
            {"symbol": "BTCUSDT", "side": "Long", "pnl": 200.00},
            {"symbol": "ETHUSDT", "side": "Short", "pnl": -50.00},
        ],
        "earn_balance": 10000.00,
        "earn_positions": [
            {"coin": "USDT", "amount": 5000.00, "apy": 3.5},
            {"coin": "BTC", "amount": 0.1, "usd_value": 5000.00, "apy": 2.1},
        ],
        "total_portfolio": 60000.00,
    }


@pytest.fixture
def sample_market_data():
    """Sample market data."""
    return {
        "fear_greed": {"value": 65, "classification": "Greed"},
        "btc_dominance": 52.5,
        "altseason_index": 35,
        "stablecoin_total": 150_000_000_000,
    }


@pytest.fixture
def sample_ta_data():
    """Sample technical analysis data."""
    return {
        "BTC/USDT": {
            "rsi": 55.5,
            "macd_signal": "bullish",
            "bb_position": 65.0,
            "trend": "uptrend",
            "support": 95000,
            "resistance": 105000,
        },
        "ETH/USDT": {
            "rsi": 48.2,
            "macd_signal": "neutral",
            "bb_position": 50.0,
            "trend": "sideways",
            "support": 3200,
            "resistance": 3800,
        },
    }


@pytest.fixture
def all_sensor_keys():
    """Get all sensor keys from the registry."""
    from service.ha import SensorRegistry

    SensorRegistry.ensure_initialized()
    return list(SensorRegistry.get_all().keys())
