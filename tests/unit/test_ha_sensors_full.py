"""100% coverage tests for services/ha module (new modular architecture)."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from service.ha import (
    HAIntegrationManager,
    SensorRegistry,
    get_currency_list,
    get_sensors_manager,
)

# ═══════════════════════════════════════════════════════════════════════════
#                         get_currency_list Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestGetCurrencyList:
    """Tests for get_currency_list function."""

    def test_default_symbols(self):
        with patch.dict("os.environ", {}, clear=True):
            symbols = get_currency_list()
            assert "BTC/USDT" in symbols
            assert "ETH/USDT" in symbols

    def test_custom_symbols_from_env(self):
        with patch.dict("os.environ", {"HA_SYMBOLS": "SOL/USDT,DOGE/USDT"}):
            symbols = get_currency_list()
            assert symbols == ["SOL/USDT", "DOGE/USDT"]

    def test_single_symbol(self):
        with patch.dict("os.environ", {"HA_SYMBOLS": "BTC/USDT"}):
            symbols = get_currency_list()
            assert symbols == ["BTC/USDT"]

    def test_strips_whitespace(self):
        with patch.dict("os.environ", {"HA_SYMBOLS": " BTC/USDT , ETH/USDT "}):
            symbols = get_currency_list()
            assert symbols == ["BTC/USDT", "ETH/USDT"]

    def test_empty_values_filtered(self):
        with patch.dict("os.environ", {"HA_SYMBOLS": "BTC/USDT,,ETH/USDT,"}):
            symbols = get_currency_list()
            assert symbols == ["BTC/USDT", "ETH/USDT"]


# ═══════════════════════════════════════════════════════════════════════════
#                    HAIntegrationManager Init Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestHAIntegrationManagerInit:
    """Tests for HAIntegrationManager initialization."""

    def test_init(self):
        manager = HAIntegrationManager()
        assert manager._cache == {}
        assert manager.publisher is not None

    def test_device_info(self):
        manager = HAIntegrationManager()
        info = manager.device_info

        assert info["identifiers"] == ["crypto_inspect"]
        assert info["name"] == "Crypto Inspect"
        assert "model" in info
        assert "manufacturer" in info
        assert "sw_version" in info


# ═══════════════════════════════════════════════════════════════════════════
#                    SensorRegistry Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestSensorRegistry:
    """Tests for SensorRegistry functionality."""

    def test_ensure_initialized(self):
        SensorRegistry.ensure_initialized()
        assert SensorRegistry.count() > 0

    def test_get_all_sensors(self):
        SensorRegistry.ensure_initialized()
        sensors = SensorRegistry.get_all()
        assert len(sensors) >= 130

    def test_get_sensor(self):
        SensorRegistry.ensure_initialized()
        sensor_class = SensorRegistry.get("prices")
        assert sensor_class is not None

    def test_get_nonexistent_sensor(self):
        SensorRegistry.ensure_initialized()
        with pytest.raises(KeyError):
            SensorRegistry.get("nonexistent_sensor_xyz")

    def test_is_registered(self):
        SensorRegistry.ensure_initialized()
        assert SensorRegistry.is_registered("prices")
        assert SensorRegistry.is_registered("fear_greed")
        assert not SensorRegistry.is_registered("nonexistent")

    def test_get_categories(self):
        SensorRegistry.ensure_initialized()
        categories = SensorRegistry.get_categories()
        assert len(categories) >= 15
        assert "price" in categories
        assert "market" in categories
        assert "investor" in categories

    def test_get_by_category(self):
        SensorRegistry.ensure_initialized()
        price_sensors = SensorRegistry.get_by_category("price")
        assert len(price_sensors) >= 5
        assert "prices" in price_sensors


# ═══════════════════════════════════════════════════════════════════════════
#                    register_sensors Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestRegisterSensors:
    """Tests for sensor registration."""

    @pytest.mark.asyncio
    async def test_register_sensors_success(self):
        manager = HAIntegrationManager()
        # Mock the publisher methods
        manager.publisher.create_sensor = AsyncMock(return_value=True)
        manager.publisher._client = MagicMock()
        manager.publisher._client.is_available = True

        count = await manager.register_sensors()

        assert count > 0
        assert manager.publisher.create_sensor.call_count > 0


# ═══════════════════════════════════════════════════════════════════════════
#                    Publish Methods Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestPublishMethods:
    """Tests for publish methods."""

    @pytest.mark.asyncio
    async def test_publish_sensor_success(self):
        manager = HAIntegrationManager()
        manager.publisher.publish_sensor = AsyncMock(return_value=True)

        result = await manager.publish_sensor("fear_greed", 75, {"classification": "Greed"})

        assert result is True
        assert manager._cache["fear_greed"] == 75

    @pytest.mark.asyncio
    async def test_publish_sensor_without_attributes(self):
        manager = HAIntegrationManager()
        manager.publisher.publish_sensor = AsyncMock(return_value=True)

        result = await manager.publish_sensor("fear_greed", 50)

        assert result is True
        assert manager._cache["fear_greed"] == 50

    @pytest.mark.asyncio
    async def test_publish_state_backward_compat(self):
        manager = HAIntegrationManager()
        manager.publisher.publish_sensor = AsyncMock(return_value=True)

        result = await manager._publish_state("test_sensor", "test_value")

        assert result is True
        assert manager._cache["test_sensor"] == "test_value"

    @pytest.mark.asyncio
    async def test_publish_attributes_backward_compat(self):
        manager = HAIntegrationManager()
        manager.publisher.update_attributes = AsyncMock(return_value=True)

        result = await manager._publish_attributes("test_sensor", {"key": "value"})

        assert result is True


# ═══════════════════════════════════════════════════════════════════════════
#                    update_price Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestUpdatePrice:
    """Tests for price update methods."""

    @pytest.mark.asyncio
    async def test_update_price_basic(self):
        manager = HAIntegrationManager()
        manager.publisher.publish_sensor = AsyncMock(return_value=True)

        await manager.update_price("BTC/USDT", Decimal("100000"))

        assert manager._prices["BTC/USDT"] == "100000"

    @pytest.mark.asyncio
    async def test_update_price_with_all_params(self):
        manager = HAIntegrationManager()
        manager.publisher.publish_sensor = AsyncMock(return_value=True)

        await manager.update_price(
            symbol="BTC/USDT",
            price=100000.50,
            change_24h=5.25,
            volume_24h=1000000000,
            high_24h=105000,
            low_24h=95000,
        )

        assert manager._prices["BTC/USDT"] == "100000.5"
        assert manager._changes["BTC/USDT"] == "5.25"
        assert manager._volumes["BTC/USDT"] == "1000000000"
        assert manager._highs["BTC/USDT"] == "105000"
        assert manager._lows["BTC/USDT"] == "95000"

    @pytest.mark.asyncio
    async def test_update_all_prices(self):
        manager = HAIntegrationManager()
        manager.publisher.publish_sensor = AsyncMock(return_value=True)

        prices_data = {
            "BTC/USDT": {
                "price": 100000,
                "change_24h": 5.0,
                "volume_24h": 1000000,
                "high_24h": 105000,
                "low_24h": 95000,
            },
            "ETH/USDT": {
                "price": 3500,
                "change_24h": -2.5,
            },
        }

        await manager.update_all_prices(prices_data)

        assert manager._prices["BTC/USDT"] == "100000"
        assert manager._prices["ETH/USDT"] == "3500"
        assert manager._changes["BTC/USDT"] == "5.00"
        assert manager._changes["ETH/USDT"] == "-2.50"


# ═══════════════════════════════════════════════════════════════════════════
#                    update_sync_status Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestUpdateSyncStatus:
    """Tests for sync status updates."""

    @pytest.mark.asyncio
    async def test_update_sync_status_basic(self):
        manager = HAIntegrationManager()
        manager.publisher.publish_sensor = AsyncMock(return_value=True)

        await manager.update_sync_status("running")

        manager.publisher.publish_sensor.assert_called()

    @pytest.mark.asyncio
    async def test_update_sync_status_with_counts(self):
        manager = HAIntegrationManager()
        manager.publisher.publish_sensor = AsyncMock(return_value=True)

        await manager.update_sync_status(status="completed", success_count=10, failure_count=2)

        # Check that publish was called multiple times
        assert manager.publisher.publish_sensor.call_count >= 1


# ═══════════════════════════════════════════════════════════════════════════
#                    remove_sensors Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestRemoveSensors:
    """Tests for sensor removal."""

    @pytest.mark.asyncio
    async def test_remove_sensors_success(self):
        manager = HAIntegrationManager()
        manager.publisher.remove_sensor = AsyncMock(return_value=True)

        await manager.remove_sensors()

        # Should call remove for each registered sensor
        assert manager.publisher.remove_sensor.call_count > 0


# ═══════════════════════════════════════════════════════════════════════════
#                    update_investor_status Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestUpdateInvestorStatus:
    """Tests for investor status updates."""

    @pytest.mark.asyncio
    async def test_update_investor_status_full(self):
        manager = HAIntegrationManager()
        manager.publisher.publish_sensor = AsyncMock(return_value=True)

        status_data = {
            "do_nothing_ok": {
                "state": "✅ Можно ничего не делать",
                "value": True,
                "reason_ru": "Рынок стабилен",
            },
            "phase": {
                "name_ru": "Накопление",
                "value": "accumulation",
                "confidence": 75,
            },
            "calm": {
                "score": 80,
                "level": "calm",
            },
            "red_flags": {
                "count": 0,
                "flags_list": "✅ Нет флагов",
            },
        }

        await manager.update_investor_status(status_data)

        # Should have multiple publish calls
        assert manager.publisher.publish_sensor.call_count >= 4


# ═══════════════════════════════════════════════════════════════════════════
#                    update_market_data Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestUpdateMarketData:
    """Tests for market data updates."""

    @pytest.mark.asyncio
    async def test_update_market_data_fear_greed(self):
        manager = HAIntegrationManager()
        manager.publisher.publish_sensor = AsyncMock(return_value=True)

        await manager.update_market_data(fear_greed=75)

        manager.publisher.publish_sensor.assert_called()

    @pytest.mark.asyncio
    async def test_update_market_data_btc_dominance(self):
        manager = HAIntegrationManager()
        manager.publisher.publish_sensor = AsyncMock(return_value=True)

        await manager.update_market_data(btc_dominance=52.5)

        manager.publisher.publish_sensor.assert_called()

    @pytest.mark.asyncio
    async def test_update_market_data_derivatives(self):
        manager = HAIntegrationManager()
        manager.publisher.publish_sensor = AsyncMock(return_value=True)

        derivatives = {"funding_rate": 0.01, "open_interest": 1000000}
        await manager.update_market_data(derivatives_data=derivatives)

        manager.publisher.publish_sensor.assert_called()


# ═══════════════════════════════════════════════════════════════════════════
#                    _get_fg_classification Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestGetFgClassification:
    """Tests for Fear & Greed classification."""

    def test_extreme_fear(self):
        manager = HAIntegrationManager()
        assert manager._get_fg_classification(10) == "Extreme Fear"
        assert manager._get_fg_classification(25) == "Extreme Fear"

    def test_fear(self):
        manager = HAIntegrationManager()
        assert manager._get_fg_classification(26) == "Fear"
        assert manager._get_fg_classification(45) == "Fear"

    def test_neutral(self):
        manager = HAIntegrationManager()
        assert manager._get_fg_classification(46) == "Neutral"
        assert manager._get_fg_classification(55) == "Neutral"

    def test_greed(self):
        manager = HAIntegrationManager()
        assert manager._get_fg_classification(56) == "Greed"
        assert manager._get_fg_classification(75) == "Greed"

    def test_extreme_greed(self):
        manager = HAIntegrationManager()
        assert manager._get_fg_classification(76) == "Extreme Greed"
        assert manager._get_fg_classification(100) == "Extreme Greed"


# ═══════════════════════════════════════════════════════════════════════════
#                    update_smart_summary Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestUpdateSmartSummary:
    """Tests for smart summary updates."""

    @pytest.mark.asyncio
    async def test_update_smart_summary_market_pulse(self):
        manager = HAIntegrationManager()
        manager.publisher.publish_sensor = AsyncMock(return_value=True)

        summary = {
            "pulse": "Bullish",
            "pulse_ru": "Бычий",
            "pulse_confidence": 80,
        }

        await manager.update_smart_summary(summary)
        assert manager.publisher.publish_sensor.call_count >= 1

    @pytest.mark.asyncio
    async def test_update_smart_summary_portfolio_health(self):
        manager = HAIntegrationManager()
        manager.publisher.publish_sensor = AsyncMock(return_value=True)

        summary = {
            "health": "Excellent",
            "health_ru": "Отлично",
            "health_score": 90,
        }

        await manager.update_smart_summary(summary)


# ═══════════════════════════════════════════════════════════════════════════
#                    get_sensors_manager Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestGetSensorsManager:
    """Tests for get_sensors_manager function."""

    def test_get_sensors_manager_singleton(self):
        import service.ha.core.manager as ha_manager

        ha_manager._ha_manager = None

        manager1 = get_sensors_manager()
        manager2 = get_sensors_manager()

        assert manager1 is manager2
        assert isinstance(manager1, HAIntegrationManager)

        ha_manager._ha_manager = None


# ═══════════════════════════════════════════════════════════════════════════
#                    Sensor Definitions Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestSensorDefinitions:
    """Tests for sensor definitions completeness."""

    def test_all_sensors_registered(self):
        SensorRegistry.ensure_initialized()
        assert SensorRegistry.count() >= 130

    def test_key_sensors_exist(self):
        """Verify critical sensors are defined."""
        SensorRegistry.ensure_initialized()
        critical_sensors = [
            "prices",
            "changes_24h",
            "fear_greed",
            "btc_dominance",
            "sync_status",
            "last_sync",
            "portfolio_value",
        ]
        for sensor in critical_sensors:
            assert SensorRegistry.is_registered(sensor), f"Critical sensor {sensor} missing"

    def test_category_sensors(self):
        """Verify each category has sensors."""
        SensorRegistry.ensure_initialized()
        categories = SensorRegistry.get_categories()

        for category in categories:
            sensors = SensorRegistry.get_by_category(category)
            assert len(sensors) > 0, f"Category {category} has no sensors"
