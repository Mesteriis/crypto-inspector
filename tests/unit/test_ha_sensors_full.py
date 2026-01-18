"""100% coverage tests for services/ha_sensors.py."""

import json
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.ha_sensors import (
    CryptoSensorsManager,
    get_sensors_manager,
    get_symbols,
)

# ═══════════════════════════════════════════════════════════════════════════
#                         get_symbols Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestGetSymbols:
    """Tests for get_symbols function."""

    def test_default_symbols(self):
        with patch.dict("os.environ", {}, clear=True):
            symbols = get_symbols()
            assert "BTC/USDT" in symbols
            assert "ETH/USDT" in symbols

    def test_custom_symbols_from_env(self):
        with patch.dict("os.environ", {"HA_SYMBOLS": "SOL/USDT,DOGE/USDT"}):
            symbols = get_symbols()
            assert symbols == ["SOL/USDT", "DOGE/USDT"]

    def test_single_symbol(self):
        with patch.dict("os.environ", {"HA_SYMBOLS": "BTC/USDT"}):
            symbols = get_symbols()
            assert symbols == ["BTC/USDT"]

    def test_strips_whitespace(self):
        with patch.dict("os.environ", {"HA_SYMBOLS": " BTC/USDT , ETH/USDT "}):
            symbols = get_symbols()
            assert symbols == ["BTC/USDT", "ETH/USDT"]

    def test_empty_values_filtered(self):
        with patch.dict("os.environ", {"HA_SYMBOLS": "BTC/USDT,,ETH/USDT,"}):
            symbols = get_symbols()
            assert symbols == ["BTC/USDT", "ETH/USDT"]


# ═══════════════════════════════════════════════════════════════════════════
#                    CryptoSensorsManager Init Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestCryptoSensorsManagerInit:
    """Tests for CryptoSensorsManager initialization."""

    def test_init_without_mqtt(self):
        manager = CryptoSensorsManager()
        assert manager._mqtt is None
        assert manager._prices == {}
        assert manager._changes == {}
        assert manager._volumes == {}
        assert manager._highs == {}
        assert manager._lows == {}
        assert manager._cache == {}

    def test_init_with_mqtt(self):
        mock_mqtt = MagicMock()
        manager = CryptoSensorsManager(mqtt_client=mock_mqtt)
        assert manager._mqtt is mock_mqtt

    def test_device_info(self):
        manager = CryptoSensorsManager()
        info = manager.device_info

        assert info["identifiers"] == ["crypto_inspect"]
        assert info["name"] == "Crypto Inspect"
        assert "model" in info
        assert "manufacturer" in info
        assert "sw_version" in info

    def test_sensors_dict_exists(self):
        """Test that SENSORS dict is properly defined."""
        assert len(CryptoSensorsManager.SENSORS) > 0
        # Check some key sensors exist
        assert "prices" in CryptoSensorsManager.SENSORS
        assert "fear_greed" in CryptoSensorsManager.SENSORS
        assert "sync_status" in CryptoSensorsManager.SENSORS


# ═══════════════════════════════════════════════════════════════════════════
#                    Topic Generation Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestTopicGeneration:
    """Tests for MQTT topic generation methods."""

    def test_get_discovery_topic(self):
        manager = CryptoSensorsManager()
        topic = manager._get_discovery_topic("prices")
        assert topic == "homeassistant/sensor/crypto_inspect/prices/config"

    def test_get_state_topic(self):
        manager = CryptoSensorsManager()
        topic = manager._get_state_topic("prices")
        assert topic == "crypto_inspect/prices/state"

    def test_get_attributes_topic(self):
        manager = CryptoSensorsManager()
        topic = manager._get_attributes_topic("prices")
        assert topic == "crypto_inspect/prices/attributes"


# ═══════════════════════════════════════════════════════════════════════════
#                    register_sensors Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestRegisterSensors:
    """Tests for sensor registration."""

    @pytest.mark.asyncio
    async def test_register_sensors_no_mqtt(self):
        manager = CryptoSensorsManager(mqtt_client=None)
        count = await manager.register_sensors()
        assert count == 0

    @pytest.mark.asyncio
    async def test_register_sensors_success(self):
        mock_mqtt = AsyncMock()
        mock_mqtt.publish = AsyncMock()
        manager = CryptoSensorsManager(mqtt_client=mock_mqtt)

        with patch("services.ha_sensors.get_symbols", return_value=["BTC/USDT"]):
            count = await manager.register_sensors()

        assert count == len(CryptoSensorsManager.SENSORS)
        # Each sensor + initial attributes publish
        assert mock_mqtt.publish.call_count == count + 1

    @pytest.mark.asyncio
    async def test_register_sensors_with_all_options(self):
        """Test that sensors with all optional fields are registered correctly."""
        mock_mqtt = AsyncMock()
        mock_mqtt.publish = AsyncMock()
        manager = CryptoSensorsManager(mqtt_client=mock_mqtt)

        with patch("services.ha_sensors.get_symbols", return_value=["BTC/USDT"]):
            await manager.register_sensors()

        # Find a call for a sensor with unit
        found_unit_sensor = False
        found_device_class = False
        found_entity_category = False

        for call in mock_mqtt.publish.call_args_list:
            args = call[0]
            if "/config" in args[0] and args[1]:
                config = json.loads(args[1])
                if "unit_of_measurement" in config:
                    found_unit_sensor = True
                if "device_class" in config:
                    found_device_class = True
                if "entity_category" in config:
                    found_entity_category = True

        assert found_unit_sensor
        assert found_device_class
        assert found_entity_category

    @pytest.mark.asyncio
    async def test_register_sensors_mqtt_error(self):
        mock_mqtt = AsyncMock()
        mock_mqtt.publish = AsyncMock(side_effect=Exception("MQTT error"))
        manager = CryptoSensorsManager(mqtt_client=mock_mqtt)

        with patch("services.ha_sensors.get_symbols", return_value=["BTC/USDT"]):
            count = await manager.register_sensors()

        # All registrations should fail
        assert count == 0


# ═══════════════════════════════════════════════════════════════════════════
#                    Publish Methods Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestPublishMethods:
    """Tests for internal publish methods."""

    @pytest.mark.asyncio
    async def test_publish_state_no_mqtt(self):
        manager = CryptoSensorsManager(mqtt_client=None)
        result = await manager._publish_state("test", "value")
        assert result is False

    @pytest.mark.asyncio
    async def test_publish_state_string(self):
        mock_mqtt = AsyncMock()
        mock_mqtt.publish = AsyncMock()
        manager = CryptoSensorsManager(mqtt_client=mock_mqtt)

        result = await manager._publish_state("prices", "100000")

        assert result is True
        mock_mqtt.publish.assert_called_once_with("crypto_inspect/prices/state", "100000")

    @pytest.mark.asyncio
    async def test_publish_state_dict(self):
        mock_mqtt = AsyncMock()
        mock_mqtt.publish = AsyncMock()
        manager = CryptoSensorsManager(mqtt_client=mock_mqtt)

        data = {"BTC/USDT": "100000", "ETH/USDT": "3500"}
        result = await manager._publish_state("prices", data)

        assert result is True
        call_args = mock_mqtt.publish.call_args
        assert json.loads(call_args[0][1]) == data

    @pytest.mark.asyncio
    async def test_publish_state_error(self):
        mock_mqtt = AsyncMock()
        mock_mqtt.publish = AsyncMock(side_effect=Exception("Error"))
        manager = CryptoSensorsManager(mqtt_client=mock_mqtt)

        result = await manager._publish_state("test", "value")
        assert result is False

    @pytest.mark.asyncio
    async def test_publish_attributes_no_mqtt(self):
        manager = CryptoSensorsManager(mqtt_client=None)
        result = await manager._publish_attributes("test", {"key": "value"})
        assert result is False

    @pytest.mark.asyncio
    async def test_publish_attributes_success(self):
        mock_mqtt = AsyncMock()
        mock_mqtt.publish = AsyncMock()
        manager = CryptoSensorsManager(mqtt_client=mock_mqtt)

        attrs = {"count": 10, "symbols": ["BTC/USDT"]}
        result = await manager._publish_attributes("prices", attrs)

        assert result is True
        mock_mqtt.publish.assert_called_once_with("crypto_inspect/prices/attributes", json.dumps(attrs))

    @pytest.mark.asyncio
    async def test_publish_attributes_error(self):
        mock_mqtt = AsyncMock()
        mock_mqtt.publish = AsyncMock(side_effect=Exception("Error"))
        manager = CryptoSensorsManager(mqtt_client=mock_mqtt)

        result = await manager._publish_attributes("test", {})
        assert result is False

    @pytest.mark.asyncio
    async def test_publish_sensor_success(self):
        mock_mqtt = AsyncMock()
        mock_mqtt.publish = AsyncMock()
        manager = CryptoSensorsManager(mqtt_client=mock_mqtt)

        result = await manager.publish_sensor("fear_greed", 75, {"classification": "Greed"})

        assert result is True
        assert manager._cache["fear_greed"] == 75
        assert mock_mqtt.publish.call_count == 2  # state + attributes

    @pytest.mark.asyncio
    async def test_publish_sensor_without_attributes(self):
        mock_mqtt = AsyncMock()
        mock_mqtt.publish = AsyncMock()
        manager = CryptoSensorsManager(mqtt_client=mock_mqtt)

        result = await manager.publish_sensor("fear_greed", 50)

        assert result is True
        assert manager._cache["fear_greed"] == 50
        assert mock_mqtt.publish.call_count == 1  # only state

    @pytest.mark.asyncio
    async def test_publish_sensor_failure_no_attributes(self):
        mock_mqtt = AsyncMock()
        mock_mqtt.publish = AsyncMock(side_effect=Exception("Error"))
        manager = CryptoSensorsManager(mqtt_client=mock_mqtt)

        result = await manager.publish_sensor("test", "value", {"key": "val"})

        assert result is False
        # Value still cached
        assert manager._cache["test"] == "value"


# ═══════════════════════════════════════════════════════════════════════════
#                    update_price Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestUpdatePrice:
    """Tests for price update methods."""

    @pytest.mark.asyncio
    async def test_update_price_basic(self):
        mock_mqtt = AsyncMock()
        mock_mqtt.publish = AsyncMock()
        manager = CryptoSensorsManager(mqtt_client=mock_mqtt)

        await manager.update_price("BTC/USDT", Decimal("100000"))

        assert manager._prices["BTC/USDT"] == "100000"

    @pytest.mark.asyncio
    async def test_update_price_with_all_params(self):
        mock_mqtt = AsyncMock()
        mock_mqtt.publish = AsyncMock()
        manager = CryptoSensorsManager(mqtt_client=mock_mqtt)

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
    async def test_update_price_publishes_states(self):
        mock_mqtt = AsyncMock()
        mock_mqtt.publish = AsyncMock()
        manager = CryptoSensorsManager(mqtt_client=mock_mqtt)

        await manager.update_price("BTC/USDT", 100000, change_24h=5.0, volume_24h=1000000)

        # Should publish: prices state, prices attrs, changes state, volumes state
        assert mock_mqtt.publish.call_count >= 4

    @pytest.mark.asyncio
    async def test_update_price_decimal(self):
        mock_mqtt = AsyncMock()
        mock_mqtt.publish = AsyncMock()
        manager = CryptoSensorsManager(mqtt_client=mock_mqtt)

        await manager.update_price("ETH/USDT", Decimal("3500.123456"))

        assert manager._prices["ETH/USDT"] == "3500.123456"

    @pytest.mark.asyncio
    async def test_update_all_prices(self):
        mock_mqtt = AsyncMock()
        mock_mqtt.publish = AsyncMock()
        manager = CryptoSensorsManager(mqtt_client=mock_mqtt)

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
        assert manager._volumes["BTC/USDT"] == "1000000"
        assert manager._highs["BTC/USDT"] == "105000"
        assert manager._lows["BTC/USDT"] == "95000"


# ═══════════════════════════════════════════════════════════════════════════
#                    update_sync_status Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestUpdateSyncStatus:
    """Tests for sync status updates."""

    @pytest.mark.asyncio
    async def test_update_sync_status_basic(self):
        mock_mqtt = AsyncMock()
        mock_mqtt.publish = AsyncMock()
        manager = CryptoSensorsManager(mqtt_client=mock_mqtt)

        await manager.update_sync_status("running")

        # Check state was published
        state_calls = [c for c in mock_mqtt.publish.call_args_list if "state" in c[0][0]]
        assert len(state_calls) >= 1

    @pytest.mark.asyncio
    async def test_update_sync_status_with_counts(self):
        mock_mqtt = AsyncMock()
        mock_mqtt.publish = AsyncMock()
        manager = CryptoSensorsManager(mqtt_client=mock_mqtt)

        await manager.update_sync_status(status="completed", success_count=10, failure_count=2)

        # Check attributes include success_rate
        attr_calls = [c for c in mock_mqtt.publish.call_args_list if "attributes" in c[0][0]]
        assert len(attr_calls) >= 1

        for call in attr_calls:
            if "sync_status" in call[0][0]:
                attrs = json.loads(call[0][1])
                assert "success_rate" in attrs
                assert attrs["success_count"] == 10
                assert attrs["failure_count"] == 2

    @pytest.mark.asyncio
    async def test_update_sync_status_zero_operations(self):
        mock_mqtt = AsyncMock()
        mock_mqtt.publish = AsyncMock()
        manager = CryptoSensorsManager(mqtt_client=mock_mqtt)

        await manager.update_sync_status(status="idle", success_count=0, failure_count=0)

        # Should have N/A for success_rate
        attr_calls = [
            c for c in mock_mqtt.publish.call_args_list if "sync_status" in c[0][0] and "attributes" in c[0][0]
        ]
        assert len(attr_calls) >= 1
        attrs = json.loads(attr_calls[0][0][1])
        assert attrs["success_rate"] == "N/A"

    @pytest.mark.asyncio
    async def test_update_sync_status_with_candles(self):
        mock_mqtt = AsyncMock()
        mock_mqtt.publish = AsyncMock()
        manager = CryptoSensorsManager(mqtt_client=mock_mqtt)

        await manager.update_sync_status(status="completed", success_count=5, failure_count=0, total_candles=10000)

        # Check candles_count was published
        state_calls = [c for c in mock_mqtt.publish.call_args_list if "candles_count" in c[0][0]]
        assert len(state_calls) >= 1


# ═══════════════════════════════════════════════════════════════════════════
#                    remove_sensors Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestRemoveSensors:
    """Tests for sensor removal."""

    @pytest.mark.asyncio
    async def test_remove_sensors_no_mqtt(self):
        manager = CryptoSensorsManager(mqtt_client=None)
        # Should not raise
        await manager.remove_sensors()

    @pytest.mark.asyncio
    async def test_remove_sensors_success(self):
        mock_mqtt = AsyncMock()
        mock_mqtt.publish = AsyncMock()
        manager = CryptoSensorsManager(mqtt_client=mock_mqtt)

        await manager.remove_sensors()

        # Should publish empty config for each sensor
        expected_calls = len(CryptoSensorsManager.SENSORS)
        assert mock_mqtt.publish.call_count == expected_calls

        # Each call should have empty payload and retain=True
        for call in mock_mqtt.publish.call_args_list:
            assert call[0][1] == ""
            assert call[1]["retain"] is True

    @pytest.mark.asyncio
    async def test_remove_sensors_partial_error(self):
        mock_mqtt = AsyncMock()
        call_count = 0

        async def publish_with_error(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 5:  # Error on 5th call
                raise Exception("Error")

        mock_mqtt.publish = publish_with_error
        manager = CryptoSensorsManager(mqtt_client=mock_mqtt)

        # Should not raise, continues removing other sensors
        await manager.remove_sensors()


# ═══════════════════════════════════════════════════════════════════════════
#                    update_investor_status Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestUpdateInvestorStatus:
    """Tests for investor status updates."""

    @pytest.mark.asyncio
    async def test_update_investor_status_no_mqtt(self):
        manager = CryptoSensorsManager(mqtt_client=None)
        # Should not raise
        await manager.update_investor_status({})

    @pytest.mark.asyncio
    async def test_update_investor_status_full(self):
        mock_mqtt = AsyncMock()
        mock_mqtt.publish = AsyncMock()
        manager = CryptoSensorsManager(mqtt_client=mock_mqtt)

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
                "description_ru": "Фаза накопления",
            },
            "calm": {
                "score": 80,
                "level": "calm",
                "message_ru": "Спокойно",
            },
            "red_flags": {
                "count": 0,
                "flags_list": "✅ Нет флагов",
                "flags": [],
            },
            "tension": {
                "state": "🟢 Низкое",
                "score": 20,
                "level_ru": "Низкое",
            },
            "price_context": {
                "context_ru": "Выше среднего",
                "current_price": 100000,
                "avg_6m": 80000,
                "diff_percent": 25,
                "recommendation_ru": "Осторожно",
            },
            "dca": {
                "total_amount": 500,
                "btc_amount": 300,
                "eth_amount": 150,
                "alts_amount": 50,
                "reason_ru": "По расписанию",
                "state": "🟢 Покупать",
                "signal": "buy",
                "signal_ru": "Покупать",
                "next_dca": "Через 7 дней",
            },
            "weekly_insight": {
                "summary_ru": "Бычий рынок",
                "btc_status": "bullish",
                "eth_vs_btc": "neutral",
                "alts_status": "bullish",
                "dominance_trend": "down",
                "summary": "Bull market",
            },
        }

        await manager.update_investor_status(status_data)

        # Should have many publish calls
        assert mock_mqtt.publish.call_count > 10

    @pytest.mark.asyncio
    async def test_update_investor_status_red_flags_variants(self):
        mock_mqtt = AsyncMock()
        mock_mqtt.publish = AsyncMock()
        manager = CryptoSensorsManager(mqtt_client=mock_mqtt)

        # Test 0 flags (green)
        await manager.update_investor_status({"red_flags": {"count": 0}})

        # Test 1-2 flags (yellow)
        mock_mqtt.publish.reset_mock()
        await manager.update_investor_status({"red_flags": {"count": 2}})

        # Test 3+ flags (red)
        mock_mqtt.publish.reset_mock()
        await manager.update_investor_status({"red_flags": {"count": 5}})


# ═══════════════════════════════════════════════════════════════════════════
#                    update_market_data Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestUpdateMarketData:
    """Tests for market data updates."""

    @pytest.mark.asyncio
    async def test_update_market_data_fear_greed_extreme_fear(self):
        mock_mqtt = AsyncMock()
        mock_mqtt.publish = AsyncMock()
        manager = CryptoSensorsManager(mqtt_client=mock_mqtt)

        await manager.update_market_data(fear_greed=10)

        state_calls = [c for c in mock_mqtt.publish.call_args_list if "fear_greed" in c[0][0] and "state" in c[0][0]]
        assert len(state_calls) == 1
        assert "Extreme Fear" in state_calls[0][0][1]

    @pytest.mark.asyncio
    async def test_update_market_data_fear_greed_fear(self):
        mock_mqtt = AsyncMock()
        mock_mqtt.publish = AsyncMock()
        manager = CryptoSensorsManager(mqtt_client=mock_mqtt)

        await manager.update_market_data(fear_greed=35)

        state_calls = [c for c in mock_mqtt.publish.call_args_list if "fear_greed" in c[0][0] and "state" in c[0][0]]
        assert "Fear" in state_calls[0][0][1]

    @pytest.mark.asyncio
    async def test_update_market_data_fear_greed_neutral(self):
        mock_mqtt = AsyncMock()
        mock_mqtt.publish = AsyncMock()
        manager = CryptoSensorsManager(mqtt_client=mock_mqtt)

        await manager.update_market_data(fear_greed=50)

        state_calls = [c for c in mock_mqtt.publish.call_args_list if "fear_greed" in c[0][0] and "state" in c[0][0]]
        assert "Neutral" in state_calls[0][0][1]

    @pytest.mark.asyncio
    async def test_update_market_data_fear_greed_greed(self):
        mock_mqtt = AsyncMock()
        mock_mqtt.publish = AsyncMock()
        manager = CryptoSensorsManager(mqtt_client=mock_mqtt)

        await manager.update_market_data(fear_greed=65)

        state_calls = [c for c in mock_mqtt.publish.call_args_list if "fear_greed" in c[0][0] and "state" in c[0][0]]
        assert "Greed" in state_calls[0][0][1]

    @pytest.mark.asyncio
    async def test_update_market_data_fear_greed_extreme_greed(self):
        mock_mqtt = AsyncMock()
        mock_mqtt.publish = AsyncMock()
        manager = CryptoSensorsManager(mqtt_client=mock_mqtt)

        await manager.update_market_data(fear_greed=85)

        state_calls = [c for c in mock_mqtt.publish.call_args_list if "fear_greed" in c[0][0] and "state" in c[0][0]]
        assert "Extreme Greed" in state_calls[0][0][1]

    @pytest.mark.asyncio
    async def test_update_market_data_btc_dominance_high(self):
        mock_mqtt = AsyncMock()
        mock_mqtt.publish = AsyncMock()
        manager = CryptoSensorsManager(mqtt_client=mock_mqtt)

        await manager.update_market_data(btc_dominance=60.5)

        attr_calls = [
            c for c in mock_mqtt.publish.call_args_list if "btc_dominance" in c[0][0] and "attributes" in c[0][0]
        ]
        attrs = json.loads(attr_calls[0][0][1])
        assert attrs["trend"] == "↗️"

    @pytest.mark.asyncio
    async def test_update_market_data_btc_dominance_low(self):
        mock_mqtt = AsyncMock()
        mock_mqtt.publish = AsyncMock()
        manager = CryptoSensorsManager(mqtt_client=mock_mqtt)

        await manager.update_market_data(btc_dominance=40.0)

        attr_calls = [
            c for c in mock_mqtt.publish.call_args_list if "btc_dominance" in c[0][0] and "attributes" in c[0][0]
        ]
        attrs = json.loads(attr_calls[0][0][1])
        assert attrs["trend"] == "↘️"

    @pytest.mark.asyncio
    async def test_update_market_data_btc_dominance_neutral(self):
        mock_mqtt = AsyncMock()
        mock_mqtt.publish = AsyncMock()
        manager = CryptoSensorsManager(mqtt_client=mock_mqtt)

        await manager.update_market_data(btc_dominance=50.0)

        attr_calls = [
            c for c in mock_mqtt.publish.call_args_list if "btc_dominance" in c[0][0] and "attributes" in c[0][0]
        ]
        attrs = json.loads(attr_calls[0][0][1])
        assert attrs["trend"] == "→"

    @pytest.mark.asyncio
    async def test_update_market_data_derivatives(self):
        mock_mqtt = AsyncMock()
        mock_mqtt.publish = AsyncMock()
        manager = CryptoSensorsManager(mqtt_client=mock_mqtt)

        derivatives = {"funding_rate": 0.01, "open_interest": 1000000}
        await manager.update_market_data(derivatives_data=derivatives)

        state_calls = [c for c in mock_mqtt.publish.call_args_list if "derivatives" in c[0][0] and "state" in c[0][0]]
        assert state_calls[0][0][1] == "Active"


# ═══════════════════════════════════════════════════════════════════════════
#                    _get_fg_classification Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestGetFgClassification:
    """Tests for Fear & Greed classification."""

    def test_extreme_fear(self):
        manager = CryptoSensorsManager()
        assert manager._get_fg_classification(10) == "Extreme Fear"
        assert manager._get_fg_classification(25) == "Extreme Fear"

    def test_fear(self):
        manager = CryptoSensorsManager()
        assert manager._get_fg_classification(26) == "Fear"
        assert manager._get_fg_classification(45) == "Fear"

    def test_neutral(self):
        manager = CryptoSensorsManager()
        assert manager._get_fg_classification(46) == "Neutral"
        assert manager._get_fg_classification(55) == "Neutral"

    def test_greed(self):
        manager = CryptoSensorsManager()
        assert manager._get_fg_classification(56) == "Greed"
        assert manager._get_fg_classification(75) == "Greed"

    def test_extreme_greed(self):
        manager = CryptoSensorsManager()
        assert manager._get_fg_classification(76) == "Extreme Greed"
        assert manager._get_fg_classification(100) == "Extreme Greed"


# ═══════════════════════════════════════════════════════════════════════════
#                    update_smart_summary Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestUpdateSmartSummary:
    """Tests for smart summary updates."""

    @pytest.mark.asyncio
    async def test_update_smart_summary_no_mqtt(self):
        manager = CryptoSensorsManager(mqtt_client=None)
        await manager.update_smart_summary({})
        # Should not raise

    @pytest.mark.asyncio
    async def test_update_smart_summary_market_pulse(self):
        mock_mqtt = AsyncMock()
        mock_mqtt.publish = AsyncMock()
        manager = CryptoSensorsManager(mqtt_client=mock_mqtt)

        summary = {
            "market_pulse": {
                "sentiment_ru": "Бычий",
                "sentiment_en": "Bullish",
                "confidence": 80,
                "reason_en": "Strong momentum",
                "reason_ru": "Сильный импульс",
                "factors_en": ["High volume"],
                "factors_ru": ["Высокий объем"],
            }
        }

        await manager.update_smart_summary(summary)
        assert mock_mqtt.publish.call_count >= 2

    @pytest.mark.asyncio
    async def test_update_smart_summary_portfolio_health(self):
        mock_mqtt = AsyncMock()
        mock_mqtt.publish = AsyncMock()
        manager = CryptoSensorsManager(mqtt_client=mock_mqtt)

        summary = {
            "portfolio_health": {
                "status_ru": "Отлично",
                "status_en": "Excellent",
                "score": 90,
                "main_issue_en": "None",
                "main_issue_ru": "Нет",
            }
        }

        await manager.update_smart_summary(summary)

    @pytest.mark.asyncio
    async def test_update_smart_summary_today_action(self):
        mock_mqtt = AsyncMock()
        mock_mqtt.publish = AsyncMock()
        manager = CryptoSensorsManager(mqtt_client=mock_mqtt)

        summary = {
            "today_action": {
                "action_ru": "Ничего не делать",
                "action_en": "Do nothing",
                "priority_ru": "Низкий",
                "priority_en": "Low",
                "details_ru": "Рынок стабилен",
                "details_en": "Market is stable",
            }
        }

        await manager.update_smart_summary(summary)

    @pytest.mark.asyncio
    async def test_update_smart_summary_weekly_outlook(self):
        mock_mqtt = AsyncMock()
        mock_mqtt.publish = AsyncMock()
        manager = CryptoSensorsManager(mqtt_client=mock_mqtt)

        summary = {
            "weekly_outlook": {
                "outlook_ru": "Позитивный",
                "outlook_en": "Positive",
            }
        }

        await manager.update_smart_summary(summary)


# ═══════════════════════════════════════════════════════════════════════════
#                    update_notification_status Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestUpdateNotificationStatus:
    """Tests for notification status updates."""

    @pytest.mark.asyncio
    async def test_update_notification_status_no_mqtt(self):
        manager = CryptoSensorsManager(mqtt_client=None)
        await manager.update_notification_status({})

    @pytest.mark.asyncio
    async def test_update_notification_status_full(self):
        mock_mqtt = AsyncMock()
        mock_mqtt.publish = AsyncMock()
        manager = CryptoSensorsManager(mqtt_client=mock_mqtt)

        status = {
            "pending_alerts_count": 5,
            "pending_alerts_critical": 2,
            "pending_alerts_important": 2,
            "pending_alerts_info": 1,
            "daily_digest_ready": True,
            "digest_ready_en": "Ready",
            "digest_ready_ru": "Готов",
            "last_digest_time": "2024-01-15T10:00:00",
            "notification_mode": "smart",
            "notification_mode_en": "Smart mode",
            "notification_mode_ru": "Умный режим",
        }

        await manager.update_notification_status(status)
        assert mock_mqtt.publish.call_count >= 6


# ═══════════════════════════════════════════════════════════════════════════
#                    update_briefing_status Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestUpdateBriefingStatus:
    """Tests for briefing status updates."""

    @pytest.mark.asyncio
    async def test_update_briefing_status_no_mqtt(self):
        manager = CryptoSensorsManager(mqtt_client=None)
        await manager.update_briefing_status({})

    @pytest.mark.asyncio
    async def test_update_briefing_status_full(self):
        mock_mqtt = AsyncMock()
        mock_mqtt.publish = AsyncMock()
        manager = CryptoSensorsManager(mqtt_client=mock_mqtt)

        briefing = {
            "morning_briefing_available": True,
            "morning_briefing_status_en": "Ready",
            "morning_briefing_status_ru": "Готов",
            "last_morning_briefing": "2024-01-15T08:00:00",
            "evening_briefing_available": True,
            "evening_briefing_status_en": "Ready",
            "evening_briefing_status_ru": "Готов",
            "last_evening_briefing": "2024-01-15T20:00:00",
        }

        await manager.update_briefing_status(briefing)
        assert mock_mqtt.publish.call_count >= 4

    @pytest.mark.asyncio
    async def test_update_briefing_status_only_morning(self):
        mock_mqtt = AsyncMock()
        mock_mqtt.publish = AsyncMock()
        manager = CryptoSensorsManager(mqtt_client=mock_mqtt)

        briefing = {
            "last_morning_briefing": "2024-01-15T08:00:00",
        }

        await manager.update_briefing_status(briefing)

    @pytest.mark.asyncio
    async def test_update_briefing_status_no_last_sent(self):
        mock_mqtt = AsyncMock()
        mock_mqtt.publish = AsyncMock()
        manager = CryptoSensorsManager(mqtt_client=mock_mqtt)

        briefing = {
            "morning_briefing_available": False,
            "evening_briefing_available": False,
        }

        await manager.update_briefing_status(briefing)


# ═══════════════════════════════════════════════════════════════════════════
#                    update_goal_status Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestUpdateGoalStatus:
    """Tests for goal status updates."""

    @pytest.mark.asyncio
    async def test_update_goal_status_no_mqtt(self):
        manager = CryptoSensorsManager(mqtt_client=None)
        await manager.update_goal_status({})

    @pytest.mark.asyncio
    async def test_update_goal_status_full(self):
        mock_mqtt = AsyncMock()
        mock_mqtt.publish = AsyncMock()
        manager = CryptoSensorsManager(mqtt_client=mock_mqtt)

        goal = {
            "goal_target": 100000,
            "goal_name": "Retirement Fund",
            "goal_name_ru": "Пенсионный фонд",
            "target_date": "2030-01-01",
            "start_date": "2024-01-01",
            "goal_progress": 25.5,
            "goal_emoji": "🎯",
            "goal_current": 25500,
            "goal_remaining": 74500,
            "milestones_reached": ["10%", "25%"],
            "next_milestone": "50%",
            "goal_days_estimate": 365,
            "goal_status": "on_track",
            "goal_status_en": "On Track",
            "goal_status_ru": "По плану",
            "milestone_message": "Great progress!",
            "milestone_message_ru": "Отличный прогресс!",
        }

        await manager.update_goal_status(goal)
        assert mock_mqtt.publish.call_count >= 8

    @pytest.mark.asyncio
    async def test_update_goal_status_no_days_estimate(self):
        mock_mqtt = AsyncMock()
        mock_mqtt.publish = AsyncMock()
        manager = CryptoSensorsManager(mqtt_client=mock_mqtt)

        goal = {
            "goal_target": 100000,
            "goal_progress": 10.0,
            "goal_days_estimate": None,
        }

        await manager.update_goal_status(goal)

        # Check N/A was published
        state_calls = [
            c for c in mock_mqtt.publish.call_args_list if "goal_days_estimate" in c[0][0] and "state" in c[0][0]
        ]
        assert state_calls[0][0][1] == "N/A"


# ═══════════════════════════════════════════════════════════════════════════
#                    get_sensors_manager Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestGetSensorsManager:
    """Tests for get_sensors_manager function."""

    def test_get_sensors_manager_singleton(self):
        import services.ha_sensors as ha_sensors

        ha_sensors._sensors_manager = None

        manager1 = get_sensors_manager()
        manager2 = get_sensors_manager()

        assert manager1 is manager2
        assert isinstance(manager1, CryptoSensorsManager)

        ha_sensors._sensors_manager = None

    def test_get_sensors_manager_with_mqtt(self):
        import services.ha_sensors as ha_sensors

        ha_sensors._sensors_manager = None

        mock_mqtt = MagicMock()
        manager = get_sensors_manager(mqtt_client=mock_mqtt)

        assert manager._mqtt is mock_mqtt

        ha_sensors._sensors_manager = None

    def test_get_sensors_manager_replaces_with_new_mqtt(self):
        import services.ha_sensors as ha_sensors

        ha_sensors._sensors_manager = None

        manager1 = get_sensors_manager()
        assert manager1._mqtt is None

        mock_mqtt = MagicMock()
        manager2 = get_sensors_manager(mqtt_client=mock_mqtt)

        assert manager2._mqtt is mock_mqtt

        ha_sensors._sensors_manager = None


# ═══════════════════════════════════════════════════════════════════════════
#                    Sensor Definitions Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestSensorDefinitions:
    """Tests for sensor definitions completeness."""

    def test_all_sensors_have_name(self):
        for sensor_id, sensor_def in CryptoSensorsManager.SENSORS.items():
            assert "name" in sensor_def, f"Sensor {sensor_id} missing 'name'"

    def test_all_sensors_have_icon(self):
        for sensor_id, sensor_def in CryptoSensorsManager.SENSORS.items():
            assert "icon" in sensor_def, f"Sensor {sensor_id} missing 'icon'"

    def test_icon_format(self):
        for sensor_id, sensor_def in CryptoSensorsManager.SENSORS.items():
            icon = sensor_def["icon"]
            assert icon.startswith("mdi:"), f"Sensor {sensor_id} icon should start with 'mdi:'"

    def test_key_sensors_exist(self):
        """Verify critical sensors are defined."""
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
            assert sensor in CryptoSensorsManager.SENSORS, f"Critical sensor {sensor} missing"

    def test_diagnostic_sensors_have_entity_category(self):
        """Verify diagnostic sensors have proper entity_category."""
        diagnostic_sensors = ["sync_status", "last_sync", "candles_count", "ai_provider"]
        for sensor_id in diagnostic_sensors:
            if sensor_id in CryptoSensorsManager.SENSORS:
                sensor_def = CryptoSensorsManager.SENSORS[sensor_id]
                assert sensor_def.get("entity_category") == "diagnostic", f"{sensor_id} should be diagnostic"
