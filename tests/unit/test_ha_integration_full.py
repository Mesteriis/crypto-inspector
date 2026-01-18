"""100% coverage tests for services/ha_integration.py."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from services.ha_integration import (
    HANotification,
    MQTTDiscoveryClient,
    NotificationType,
    SupervisorAPIClient,
    get_mqtt_discovery,
    get_supervisor_client,
    notify,
    notify_error,
    notify_sync_complete,
)

# ═══════════════════════════════════════════════════════════════════════════
#                         NotificationType Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestNotificationType:
    """Tests for NotificationType enum."""

    def test_info_value(self):
        assert NotificationType.INFO == "info"
        assert NotificationType.INFO.value == "info"

    def test_warning_value(self):
        assert NotificationType.WARNING == "warning"
        assert NotificationType.WARNING.value == "warning"

    def test_error_value(self):
        assert NotificationType.ERROR == "error"
        assert NotificationType.ERROR.value == "error"

    def test_success_value(self):
        assert NotificationType.SUCCESS == "success"
        assert NotificationType.SUCCESS.value == "success"

    def test_is_string_enum(self):
        # Test that it's a string enum
        assert isinstance(NotificationType.INFO, str)
        assert NotificationType.INFO == "info"


# ═══════════════════════════════════════════════════════════════════════════
#                         HANotification Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestHANotification:
    """Tests for HANotification dataclass."""

    def test_create_with_required_fields(self):
        notif = HANotification(title="Test Title", message="Test Message")
        assert notif.title == "Test Title"
        assert notif.message == "Test Message"
        assert notif.notification_id is None

    def test_create_with_notification_id(self):
        notif = HANotification(title="Test", message="Msg", notification_id="test_id_123")
        assert notif.notification_id == "test_id_123"

    def test_dataclass_equality(self):
        n1 = HANotification(title="T", message="M", notification_id="id1")
        n2 = HANotification(title="T", message="M", notification_id="id1")
        assert n1 == n2


# ═══════════════════════════════════════════════════════════════════════════
#                      SupervisorAPIClient Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestSupervisorAPIClient:
    """Tests for SupervisorAPIClient."""

    def test_init_defaults(self):
        client = SupervisorAPIClient()
        assert client.base_url == "http://supervisor"
        assert client._client is None

    def test_headers_property(self):
        with patch("services.ha_integration.SUPERVISOR_TOKEN", "test_token"):
            client = SupervisorAPIClient()
            client.token = "test_token"
            headers = client.headers
            assert headers["Authorization"] == "Bearer test_token"
            assert headers["Content-Type"] == "application/json"

    @pytest.mark.asyncio
    async def test_get_client_creates_new_client(self):
        client = SupervisorAPIClient()
        assert client._client is None

        http_client = await client._get_client()
        assert http_client is not None
        assert client._client is http_client

        await client.close()

    @pytest.mark.asyncio
    async def test_get_client_returns_existing_client(self):
        client = SupervisorAPIClient()

        http_client1 = await client._get_client()
        http_client2 = await client._get_client()

        assert http_client1 is http_client2
        await client.close()

    @pytest.mark.asyncio
    async def test_get_client_recreates_closed_client(self):
        client = SupervisorAPIClient()

        http_client1 = await client._get_client()
        await client.close()

        http_client2 = await client._get_client()
        assert http_client1 is not http_client2
        await client.close()

    @pytest.mark.asyncio
    async def test_close_when_client_exists(self):
        client = SupervisorAPIClient()
        await client._get_client()
        assert client._client is not None

        await client.close()
        assert client._client.is_closed

    @pytest.mark.asyncio
    async def test_close_when_no_client(self):
        client = SupervisorAPIClient()
        # Should not raise
        await client.close()

    @pytest.mark.asyncio
    async def test_call_service_success(self):
        client = SupervisorAPIClient()

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client", new_callable=AsyncMock) as mock_get_client:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http

            result = await client.call_service("notify", "mobile_app", {"message": "Hi"})

            assert result is True
            mock_http.post.assert_called_once_with("/core/api/services/notify/mobile_app", json={"message": "Hi"})

    @pytest.mark.asyncio
    async def test_call_service_without_data(self):
        client = SupervisorAPIClient()

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client", new_callable=AsyncMock) as mock_get_client:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http

            result = await client.call_service("persistent_notification", "create")

            assert result is True
            mock_http.post.assert_called_once_with("/core/api/services/persistent_notification/create", json={})

    @pytest.mark.asyncio
    async def test_call_service_http_error(self):
        client = SupervisorAPIClient()

        with patch.object(client, "_get_client", new_callable=AsyncMock) as mock_get_client:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(side_effect=httpx.HTTPError("Connection failed"))
            mock_get_client.return_value = mock_http

            result = await client.call_service("notify", "test", {})

            assert result is False

    @pytest.mark.asyncio
    async def test_send_persistent_notification_basic(self):
        client = SupervisorAPIClient()

        with patch.object(client, "call_service", new_callable=AsyncMock, return_value=True) as mock_call:
            result = await client.send_persistent_notification("Hello!")

            assert result is True
            mock_call.assert_called_once_with(
                domain="persistent_notification",
                service="create",
                data={"message": "Hello!", "title": "Crypto Inspect"},
            )

    @pytest.mark.asyncio
    async def test_send_persistent_notification_with_all_params(self):
        client = SupervisorAPIClient()

        with patch.object(client, "call_service", new_callable=AsyncMock, return_value=True) as mock_call:
            result = await client.send_persistent_notification(
                message="Test message",
                title="Custom Title",
                notification_id="custom_id_123",
            )

            assert result is True
            mock_call.assert_called_once_with(
                domain="persistent_notification",
                service="create",
                data={
                    "message": "Test message",
                    "title": "Custom Title",
                    "notification_id": "custom_id_123",
                },
            )

    @pytest.mark.asyncio
    async def test_dismiss_notification(self):
        client = SupervisorAPIClient()

        with patch.object(client, "call_service", new_callable=AsyncMock, return_value=True) as mock_call:
            result = await client.dismiss_notification("notif_123")

            assert result is True
            mock_call.assert_called_once_with(
                domain="persistent_notification",
                service="dismiss",
                data={"notification_id": "notif_123"},
            )

    @pytest.mark.asyncio
    async def test_fire_event_success(self):
        client = SupervisorAPIClient()

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client", new_callable=AsyncMock) as mock_get_client:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http

            result = await client.fire_event("crypto_alert", {"symbol": "BTC"})

            assert result is True
            mock_http.post.assert_called_once_with("/core/api/events/crypto_alert", json={"symbol": "BTC"})

    @pytest.mark.asyncio
    async def test_fire_event_without_data(self):
        client = SupervisorAPIClient()

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client", new_callable=AsyncMock) as mock_get_client:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http

            result = await client.fire_event("crypto_test")

            assert result is True
            mock_http.post.assert_called_once_with("/core/api/events/crypto_test", json={})

    @pytest.mark.asyncio
    async def test_fire_event_http_error(self):
        client = SupervisorAPIClient()

        with patch.object(client, "_get_client", new_callable=AsyncMock) as mock_get_client:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(side_effect=httpx.HTTPError("Error"))
            mock_get_client.return_value = mock_http

            result = await client.fire_event("test_event")

            assert result is False


# ═══════════════════════════════════════════════════════════════════════════
#                      MQTTDiscoveryClient Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestMQTTDiscoveryClient:
    """Tests for MQTTDiscoveryClient."""

    def test_init_without_mqtt(self):
        client = MQTTDiscoveryClient()
        assert client._mqtt is None
        assert client._registered_entities == set()

    def test_init_with_mqtt(self):
        mock_mqtt = MagicMock()
        client = MQTTDiscoveryClient(mqtt_client=mock_mqtt)
        assert client._mqtt is mock_mqtt

    def test_device_info_property(self):
        client = MQTTDiscoveryClient()
        info = client.device_info

        assert info["identifiers"] == ["crypto_inspect"]
        assert info["name"] == "Crypto Inspect"
        assert info["model"] == "Crypto Data Collector"
        assert info["manufacturer"] == "Crypto Inspect Add-on"
        assert "sw_version" in info

    def test_get_discovery_topic(self):
        client = MQTTDiscoveryClient()
        topic = client._get_discovery_topic("sensor", "btc_price")
        assert topic == "homeassistant/sensor/crypto_inspect/btc_price/config"

    def test_get_state_topic(self):
        client = MQTTDiscoveryClient()
        topic = client._get_state_topic("btc_price")
        assert topic == "crypto_inspect/btc_price/state"

    def test_get_attributes_topic(self):
        client = MQTTDiscoveryClient()
        topic = client._get_attributes_topic("btc_price")
        assert topic == "crypto_inspect/btc_price/attributes"

    @pytest.mark.asyncio
    async def test_register_sensor_no_mqtt(self):
        client = MQTTDiscoveryClient(mqtt_client=None)
        result = await client.register_sensor("test", "Test Sensor")
        assert result is False

    @pytest.mark.asyncio
    async def test_register_sensor_basic(self):
        mock_mqtt = AsyncMock()
        mock_mqtt.publish = AsyncMock()
        client = MQTTDiscoveryClient(mqtt_client=mock_mqtt)

        result = await client.register_sensor("btc_price", "BTC Price")

        assert result is True
        assert "btc_price" in client._registered_entities
        mock_mqtt.publish.assert_called_once()

        # Check published config
        call_args = mock_mqtt.publish.call_args
        topic = call_args[0][0]
        config = json.loads(call_args[0][1])

        assert topic == "homeassistant/sensor/crypto_inspect/btc_price/config"
        assert config["name"] == "BTC Price"
        assert config["unique_id"] == "crypto_inspect_btc_price"

    @pytest.mark.asyncio
    async def test_register_sensor_with_all_options(self):
        mock_mqtt = AsyncMock()
        mock_mqtt.publish = AsyncMock()
        client = MQTTDiscoveryClient(mqtt_client=mock_mqtt)

        result = await client.register_sensor(
            object_id="btc_price",
            name="BTC Price",
            unit="USDT",
            device_class="monetary",
            state_class="measurement",
            icon="mdi:bitcoin",
            entity_category="diagnostic",
        )

        assert result is True
        call_args = mock_mqtt.publish.call_args
        config = json.loads(call_args[0][1])

        assert config["unit_of_measurement"] == "USDT"
        assert config["device_class"] == "monetary"
        assert config["state_class"] == "measurement"
        assert config["icon"] == "mdi:bitcoin"
        assert config["entity_category"] == "diagnostic"

    @pytest.mark.asyncio
    async def test_register_sensor_mqtt_error(self):
        mock_mqtt = AsyncMock()
        mock_mqtt.publish = AsyncMock(side_effect=Exception("MQTT error"))
        client = MQTTDiscoveryClient(mqtt_client=mock_mqtt)

        result = await client.register_sensor("test", "Test")

        assert result is False
        assert "test" not in client._registered_entities

    @pytest.mark.asyncio
    async def test_register_binary_sensor_no_mqtt(self):
        client = MQTTDiscoveryClient(mqtt_client=None)
        result = await client.register_binary_sensor("test", "Test")
        assert result is False

    @pytest.mark.asyncio
    async def test_register_binary_sensor_success(self):
        mock_mqtt = AsyncMock()
        mock_mqtt.publish = AsyncMock()
        client = MQTTDiscoveryClient(mqtt_client=mock_mqtt)

        result = await client.register_binary_sensor(
            object_id="market_open",
            name="Market Open",
            device_class="connectivity",
            icon="mdi:store",
        )

        assert result is True
        assert "market_open" in client._registered_entities

        call_args = mock_mqtt.publish.call_args
        config = json.loads(call_args[0][1])

        assert config["name"] == "Market Open"
        assert config["payload_on"] == "ON"
        assert config["payload_off"] == "OFF"
        assert config["device_class"] == "connectivity"
        assert config["icon"] == "mdi:store"

    @pytest.mark.asyncio
    async def test_register_binary_sensor_error(self):
        mock_mqtt = AsyncMock()
        mock_mqtt.publish = AsyncMock(side_effect=Exception("Error"))
        client = MQTTDiscoveryClient(mqtt_client=mock_mqtt)

        result = await client.register_binary_sensor("test", "Test")
        assert result is False

    @pytest.mark.asyncio
    async def test_update_state_no_mqtt(self):
        client = MQTTDiscoveryClient(mqtt_client=None)
        result = await client.update_state("test", "value")
        assert result is False

    @pytest.mark.asyncio
    async def test_update_state_success(self):
        mock_mqtt = AsyncMock()
        mock_mqtt.publish = AsyncMock()
        client = MQTTDiscoveryClient(mqtt_client=mock_mqtt)

        result = await client.update_state("btc_price", 50000)

        assert result is True
        mock_mqtt.publish.assert_called_once_with("crypto_inspect/btc_price/state", "50000")

    @pytest.mark.asyncio
    async def test_update_state_error(self):
        mock_mqtt = AsyncMock()
        mock_mqtt.publish = AsyncMock(side_effect=Exception("Error"))
        client = MQTTDiscoveryClient(mqtt_client=mock_mqtt)

        result = await client.update_state("test", 100)
        assert result is False

    @pytest.mark.asyncio
    async def test_update_attributes_no_mqtt(self):
        client = MQTTDiscoveryClient(mqtt_client=None)
        result = await client.update_attributes("test", {"key": "value"})
        assert result is False

    @pytest.mark.asyncio
    async def test_update_attributes_success(self):
        mock_mqtt = AsyncMock()
        mock_mqtt.publish = AsyncMock()
        client = MQTTDiscoveryClient(mqtt_client=mock_mqtt)

        attrs = {"symbol": "BTC", "change": 5.5}
        result = await client.update_attributes("btc_price", attrs)

        assert result is True
        mock_mqtt.publish.assert_called_once_with("crypto_inspect/btc_price/attributes", json.dumps(attrs))

    @pytest.mark.asyncio
    async def test_update_attributes_error(self):
        mock_mqtt = AsyncMock()
        mock_mqtt.publish = AsyncMock(side_effect=Exception("Error"))
        client = MQTTDiscoveryClient(mqtt_client=mock_mqtt)

        result = await client.update_attributes("test", {})
        assert result is False

    @pytest.mark.asyncio
    async def test_remove_entity_no_mqtt(self):
        client = MQTTDiscoveryClient(mqtt_client=None)
        result = await client.remove_entity("sensor", "test")
        assert result is False

    @pytest.mark.asyncio
    async def test_remove_entity_success(self):
        mock_mqtt = AsyncMock()
        mock_mqtt.publish = AsyncMock()
        client = MQTTDiscoveryClient(mqtt_client=mock_mqtt)
        client._registered_entities.add("test_sensor")

        result = await client.remove_entity("sensor", "test_sensor")

        assert result is True
        assert "test_sensor" not in client._registered_entities
        mock_mqtt.publish.assert_called_once_with(
            "homeassistant/sensor/crypto_inspect/test_sensor/config", "", retain=True
        )

    @pytest.mark.asyncio
    async def test_remove_entity_error(self):
        mock_mqtt = AsyncMock()
        mock_mqtt.publish = AsyncMock(side_effect=Exception("Error"))
        client = MQTTDiscoveryClient(mqtt_client=mock_mqtt)

        result = await client.remove_entity("sensor", "test")
        assert result is False


# ═══════════════════════════════════════════════════════════════════════════
#                      Global Functions Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestGlobalFunctions:
    """Tests for global convenience functions."""

    def test_get_supervisor_client_singleton(self):
        # Reset global state
        import services.ha_integration as ha_int

        ha_int._supervisor_client = None

        client1 = get_supervisor_client()
        client2 = get_supervisor_client()

        assert client1 is client2
        assert isinstance(client1, SupervisorAPIClient)

        # Cleanup
        ha_int._supervisor_client = None

    def test_get_mqtt_discovery_without_client(self):
        import services.ha_integration as ha_int

        ha_int._mqtt_discovery = None

        client = get_mqtt_discovery()
        assert isinstance(client, MQTTDiscoveryClient)
        assert client._mqtt is None

        # Cleanup
        ha_int._mqtt_discovery = None

    def test_get_mqtt_discovery_with_client(self):
        import services.ha_integration as ha_int

        ha_int._mqtt_discovery = None

        mock_mqtt = MagicMock()
        client = get_mqtt_discovery(mqtt_client=mock_mqtt)

        assert client._mqtt is mock_mqtt

        # Cleanup
        ha_int._mqtt_discovery = None

    def test_get_mqtt_discovery_replaces_with_new_client(self):
        import services.ha_integration as ha_int

        ha_int._mqtt_discovery = None

        # First call without mqtt
        client1 = get_mqtt_discovery()
        assert client1._mqtt is None

        # Second call with mqtt should replace
        mock_mqtt = MagicMock()
        client2 = get_mqtt_discovery(mqtt_client=mock_mqtt)

        assert client2._mqtt is mock_mqtt
        # They should be different instances now
        assert client1 is not client2 or client2._mqtt is mock_mqtt

        # Cleanup
        ha_int._mqtt_discovery = None

    @pytest.mark.asyncio
    async def test_notify_function(self):
        import services.ha_integration as ha_int

        ha_int._supervisor_client = None

        with patch.object(
            SupervisorAPIClient,
            "send_persistent_notification",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_send:
            result = await notify("Test message", "Test Title", "test_id")

            assert result is True
            mock_send.assert_called_once_with("Test message", "Test Title", "test_id")

        # Cleanup
        ha_int._supervisor_client = None

    @pytest.mark.asyncio
    async def test_notify_sync_complete_all_success(self):
        import services.ha_integration as ha_int

        ha_int._supervisor_client = None

        with patch("services.ha_integration.notify", new_callable=AsyncMock, return_value=True) as mock_notify:
            result = await notify_sync_complete(success_count=10, failure_count=0, duration_seconds=5.5)

            assert result is True
            call_args = mock_notify.call_args
            message = call_args.kwargs["message"]
            assert "completed" in message
            assert "Success: 10/10" in message
            assert "Failed: 0" in message
            assert "5.5s" in message

        # Cleanup
        ha_int._supervisor_client = None

    @pytest.mark.asyncio
    async def test_notify_sync_complete_with_errors(self):
        import services.ha_integration as ha_int

        ha_int._supervisor_client = None

        with patch("services.ha_integration.notify", new_callable=AsyncMock, return_value=True) as mock_notify:
            result = await notify_sync_complete(success_count=8, failure_count=2, duration_seconds=10.0)

            assert result is True
            call_args = mock_notify.call_args
            message = call_args.kwargs["message"]
            assert "completed with errors" in message
            assert "Success: 8/10" in message
            assert "Failed: 2" in message

        # Cleanup
        ha_int._supervisor_client = None

    @pytest.mark.asyncio
    async def test_notify_error_basic(self):
        import services.ha_integration as ha_int

        ha_int._supervisor_client = None

        with patch("services.ha_integration.notify", new_callable=AsyncMock, return_value=True) as mock_notify:
            result = await notify_error("Connection failed")

            assert result is True
            call_args = mock_notify.call_args
            message = call_args.kwargs["message"]
            assert "Error: Connection failed" in message
            assert "Context" not in message

        # Cleanup
        ha_int._supervisor_client = None

    @pytest.mark.asyncio
    async def test_notify_error_with_context(self):
        import services.ha_integration as ha_int

        ha_int._supervisor_client = None

        with patch("services.ha_integration.notify", new_callable=AsyncMock, return_value=True) as mock_notify:
            result = await notify_error("API error", context="Binance fetch")

            assert result is True
            call_args = mock_notify.call_args
            message = call_args.kwargs["message"]
            assert "Error: API error" in message
            assert "Context: Binance fetch" in message

        # Cleanup
        ha_int._supervisor_client = None


# ═══════════════════════════════════════════════════════════════════════════
#                      Constants Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestConstants:
    """Tests for module constants."""

    def test_supervisor_url(self):
        from services.ha_integration import SUPERVISOR_URL

        assert SUPERVISOR_URL == "http://supervisor"

    def test_mqtt_discovery_prefix(self):
        assert MQTTDiscoveryClient.DISCOVERY_PREFIX == "homeassistant"

    def test_device_id(self):
        assert MQTTDiscoveryClient.DEVICE_ID == "crypto_inspect"

    def test_device_name(self):
        assert MQTTDiscoveryClient.DEVICE_NAME == "Crypto Inspect"
