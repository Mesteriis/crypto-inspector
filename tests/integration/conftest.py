"""
Фикстуры для интеграционных тестов.

Наследует базовые фикстуры из корневого conftest.py и добавляет
специфичные для интеграционного тестирования.
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

# Добавляем src в путь для импортов
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(project_root, "src"))

# Маркер для всех интеграционных тестов
pytestmark = [pytest.mark.integration]


# =============================================================================
# DATABASE FIXTURES
# =============================================================================


@pytest.fixture
def mock_db_connection():
    """Мок подключения к базе данных."""
    connection = MagicMock()
    connection.execute = AsyncMock()
    connection.fetch = AsyncMock(return_value=[])
    connection.fetchone = AsyncMock(return_value=None)
    connection.close = AsyncMock()
    return connection


@pytest.fixture
def mock_redis_connection():
    """Мок подключения к Redis."""
    connection = MagicMock()
    connection.get = AsyncMock(return_value=None)
    connection.set = AsyncMock(return_value=True)
    connection.delete = AsyncMock(return_value=True)
    connection.close = AsyncMock()
    return connection


# =============================================================================
# HA INTEGRATION FIXTURES
# =============================================================================


@pytest.fixture
def mock_mqtt_broker():
    """Мок MQTT брокера."""
    broker = MagicMock()
    broker.connect = MagicMock(return_value=True)
    broker.disconnect = MagicMock()
    broker.publish = MagicMock(return_value=MagicMock(rc=0))
    broker.subscribe = MagicMock()
    broker.is_connected = MagicMock(return_value=True)
    return broker


@pytest.fixture
def mock_supervisor_api():
    """Мок Supervisor API."""
    api = MagicMock()
    api.get_addon_info = AsyncMock(return_value={"state": "started"})
    api.get_addon_stats = AsyncMock(return_value={"cpu": 5, "memory": 256})
    return api
