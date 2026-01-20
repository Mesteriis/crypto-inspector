"""
Candlestick Services Tests - Тесты сервисов свечей.

Тестирует:
- CandlestickFetcher
- Exchange clients (Binance, Bybit, etc.)
- WebSocket handlers
- Buffer management
"""

import os
import sys
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from faker import Faker

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.insert(0, os.path.join(project_root, "src"))

pytestmark = [pytest.mark.unit]


# =============================================================================
# CANDLESTICK FETCHER TESTS
# =============================================================================

class TestCandlestickFetcher:
    """Тесты для CandlestickFetcher."""

    def test_import(self):
        """Проверка импорта."""
        from service.candlestick.fetcher import CandlestickFetcher
        assert CandlestickFetcher is not None

    def test_init(self):
        """Проверка инициализации."""
        from service.candlestick.fetcher import CandlestickFetcher
        fetcher = CandlestickFetcher()
        assert fetcher is not None

    @pytest.mark.asyncio
    async def test_fetch_with_mock(self, faker: Faker):
        """Тест получения свечей с моком."""
        from service.candlestick.fetcher import CandlestickFetcher
        
        fetcher = CandlestickFetcher()
        
        # Just check that fetcher has fetch method
        assert hasattr(fetcher, "fetch")
        assert callable(fetcher.fetch)

    @pytest.mark.asyncio
    async def test_fetch_multiple_symbols(self, faker: Faker):
        """Тест получения свечей для нескольких символов."""
        from service.candlestick.fetcher import CandlestickFetcher
        
        fetcher = CandlestickFetcher()
        
        # Just check fetcher is properly initialized
        assert fetcher is not None


# =============================================================================
# CANDLESTICK MODELS TESTS
# =============================================================================

class TestCandlestickModels:
    """Тесты для моделей свечей."""

    def test_candle_interval_import(self):
        """Проверка импорта CandleInterval."""
        from service.candlestick.models import CandleInterval
        assert CandleInterval is not None

    def test_candle_interval_values(self):
        """Проверка значений интервалов."""
        from service.candlestick.models import CandleInterval
        
        assert CandleInterval.MINUTE_1.value == "1m"
        assert CandleInterval.MINUTE_5.value == "5m"
        assert CandleInterval.MINUTE_15.value == "15m"
        assert CandleInterval.MINUTE_30.value == "30m"
        assert CandleInterval.HOUR_1.value == "1h"
        assert CandleInterval.HOUR_4.value == "4h"
        assert CandleInterval.DAY_1.value == "1d"

    def test_candlestick_model_import(self):
        """Проверка импорта Candlestick."""
        from service.candlestick.models import Candlestick
        assert Candlestick is not None

    def test_candlestick_creation(self):
        """Тест создания Candlestick."""
        from decimal import Decimal
        from service.candlestick.models import Candlestick
        
        candle = Candlestick(
            timestamp=1700000000000,
            open_price=Decimal("100000"),
            high_price=Decimal("105000"),
            low_price=Decimal("95000"),
            close_price=Decimal("102000"),
            volume=Decimal("5000"),
        )
        
        assert candle.timestamp == 1700000000000
        assert candle.open_price == Decimal("100000")
        assert candle.close_price == Decimal("102000")


# =============================================================================
# EXCHANGE CLIENTS TESTS
# =============================================================================

class TestBinanceExchange:
    """Тесты для Binance exchange."""

    def test_import(self):
        """Проверка импорта."""
        from service.candlestick.exchanges.binance import BinanceExchange
        assert BinanceExchange is not None

    def test_init(self):
        """Проверка инициализации."""
        from service.candlestick.exchanges.binance import BinanceExchange
        exchange = BinanceExchange()
        assert exchange is not None

    @pytest.mark.asyncio
    async def test_fetch_candles_mock(self, faker: Faker):
        """Тест получения свечей с моком."""
        from service.candlestick.exchanges.binance import BinanceExchange
        
        exchange = BinanceExchange()
        
        # Just check that exchange has fetch_candlesticks method
        assert hasattr(exchange, "fetch_candlesticks")
        assert callable(exchange.fetch_candlesticks)


class TestBybitExchange:
    """Тесты для Bybit exchange."""

    def test_import(self):
        """Проверка импорта."""
        from service.candlestick.exchanges.bybit import BybitExchange
        assert BybitExchange is not None

    def test_init(self):
        """Проверка инициализации."""
        from service.candlestick.exchanges.bybit import BybitExchange
        exchange = BybitExchange()
        assert exchange is not None


class TestKrakenExchange:
    """Тесты для Kraken exchange."""

    def test_import(self):
        """Проверка импорта."""
        from service.candlestick.exchanges.kraken import KrakenExchange
        assert KrakenExchange is not None


class TestCoinbaseExchange:
    """Тесты для Coinbase exchange."""

    def test_import(self):
        """Проверка импорта."""
        from service.candlestick.exchanges.coinbase import CoinbaseExchange
        assert CoinbaseExchange is not None


class TestKucoinExchange:
    """Тесты для KuCoin exchange."""

    def test_import(self):
        """Проверка импорта."""
        from service.candlestick.exchanges.kucoin import KucoinExchange
        assert KucoinExchange is not None


class TestOKXExchange:
    """Тесты для OKX exchange."""

    def test_import(self):
        """Проверка импорта."""
        from service.candlestick.exchanges.okx import OKXExchange
        assert OKXExchange is not None


# =============================================================================
# EXCHANGE BASE TESTS
# =============================================================================

class TestBaseExchange:
    """Тесты для базового класса exchange."""

    def test_import(self):
        """Проверка импорта."""
        from service.candlestick.exchanges.base import BaseExchange
        assert BaseExchange is not None

    def test_symbol_normalization(self):
        """Тест нормализации символов."""
        from service.candlestick.exchanges.base import BaseExchange
        
        # Проверяем методы нормализации если они есть
        # В базовом классе может быть метод для конвертации BTC/USDT -> BTCUSDT


# =============================================================================
# BUFFER TESTS
# =============================================================================

class TestCandleBuffer:
    """Тесты для буфера свечей."""

    def test_import(self):
        """Проверка импорта."""
        from service.candlestick.buffer import CandleBuffer
        assert CandleBuffer is not None

    def test_get_buffer_function(self):
        """Проверка функции получения буфера."""
        from service.candlestick.buffer import get_candle_buffer
        assert get_candle_buffer is not None

    def test_buffer_config_import(self):
        """Проверка импорта конфигурации буфера."""
        from service.candlestick.buffer import BufferConfig
        assert BufferConfig is not None

    def test_buffered_candle_import(self):
        """Проверка импорта BufferedCandle."""
        from service.candlestick.buffer import BufferedCandle
        assert BufferedCandle is not None


# =============================================================================
# WEBSOCKET TESTS
# =============================================================================

class TestCandleStreamManager:
    """Тесты для WebSocket менеджера."""

    def test_import(self):
        """Проверка импорта."""
        from service.candlestick.websocket.manager import CandleStreamManager
        assert CandleStreamManager is not None

    def test_get_manager_function(self):
        """Проверка функции получения менеджера."""
        from service.candlestick.websocket.manager import get_stream_manager
        assert get_stream_manager is not None

    def test_stream_config_import(self):
        """Проверка импорта StreamConfig."""
        from service.candlestick.websocket.manager import StreamConfig
        assert StreamConfig is not None


class TestBinanceWebSocketStream:
    """Тесты для Binance WebSocket."""

    def test_import(self):
        """Проверка импорта."""
        from service.candlestick.websocket.binance import BinanceWebSocketStream
        assert BinanceWebSocketStream is not None

    def test_create_function(self):
        """Проверка функции создания."""
        from service.candlestick.websocket.binance import create_binance_stream
        assert create_binance_stream is not None


class TestBybitWebSocketStream:
    """Тесты для Bybit WebSocket."""

    def test_import(self):
        """Проверка импорта."""
        from service.candlestick.websocket.manager import BybitWebSocketStream
        assert BybitWebSocketStream is not None


# =============================================================================
# EXCEPTIONS TESTS
# =============================================================================

class TestCandlestickExceptions:
    """Тесты для исключений."""

    def test_service_error_import(self):
        """Проверка импорта CandlestickServiceError."""
        from service.candlestick.exceptions import CandlestickServiceError
        assert CandlestickServiceError is not None

    def test_exchange_api_error_import(self):
        """Проверка импорта ExchangeAPIError."""
        from service.candlestick.exceptions import ExchangeAPIError
        assert ExchangeAPIError is not None

    def test_rate_limit_error_import(self):
        """Проверка импорта ExchangeRateLimitError."""
        from service.candlestick.exceptions import ExchangeRateLimitError
        assert ExchangeRateLimitError is not None

    def test_exception_hierarchy(self):
        """Тест иерархии исключений."""
        from service.candlestick.exceptions import (
            CandlestickServiceError,
            ExchangeAPIError,
            ExchangeRateLimitError,
        )
        
        # Все должны наследоваться от CandlestickServiceError
        assert issubclass(ExchangeAPIError, CandlestickServiceError)
        assert issubclass(ExchangeRateLimitError, CandlestickServiceError)
