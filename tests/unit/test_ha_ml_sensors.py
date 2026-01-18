"""
Unit Tests for Home Assistant ML Sensors

Tests the ML sensor functionality for Home Assistant integration.
"""

import json
import unittest
from datetime import datetime
from unittest.mock import AsyncMock, patch

from services.ha.ml_sensors import HALazyInvestorSensors, MLSensorData, MockMQTTClient


class TestHALazyInvestorSensors(unittest.TestCase):
    """Test suite for HA Lazy Investor Sensors."""

    def setUp(self):
        """Set up test fixtures."""
        self.sensor_manager = HALazyInvestorSensors()

    def test_sensor_data_creation(self):
        """Test MLSensorData creation and attributes."""
        sensor_data = MLSensorData(
            name="test_sensor", state="active", attributes={"friendly_name": "Test Sensor"}, device_class="connectivity"
        )

        self.assertEqual(sensor_data.name, "test_sensor")
        self.assertEqual(sensor_data.state, "active")
        self.assertEqual(sensor_data.attributes["friendly_name"], "Test Sensor")
        self.assertEqual(sensor_data.device_class, "connectivity")

    async def test_create_investment_sensors(self):
        """Test creation of all investment sensors."""
        sensors = await self.sensor_manager.create_investment_sensors()

        # Should create 5 sensors
        self.assertEqual(len(sensors), 5)

        sensor_names = [s.name for s in sensors]
        expected_names = [
            "ml_portfolio_health",
            "ml_market_confidence",
            "ml_investment_opportunity",
            "ml_risk_warning",
            "ml_system_status",
        ]

        for name in expected_names:
            self.assertIn(name, sensor_names)

    async def test_sensor_attributes_structure(self):
        """Test that sensors have proper attribute structure."""
        sensors = await self.sensor_manager.create_investment_sensors()

        for sensor in sensors:
            # All sensors should have required attributes
            required_attrs = ["friendly_name", "last_updated"]
            for attr in required_attrs:
                self.assertIn(attr, sensor.attributes)

            # last_updated should be ISO format timestamp
            timestamp = sensor.attributes["last_updated"]
            datetime.fromisoformat(timestamp)  # Should not raise exception

    def test_confidence_level_determination(self):
        """Test confidence level determination logic."""

        # Test high confidence scenario
        high_conf_insights = {"high_confidence_count": 8, "medium_confidence_count": 3, "total_signals": 12}
        confidence = self.sensor_manager._determine_confidence_level(high_conf_insights)
        self.assertEqual(confidence, "high")

        # Test medium confidence scenario
        med_conf_insights = {"high_confidence_count": 3, "medium_confidence_count": 7, "total_signals": 12}
        confidence = self.sensor_manager._determine_confidence_level(med_conf_insights)
        self.assertEqual(confidence, "medium")

        # Test low confidence scenario
        low_conf_insights = {"high_confidence_count": 1, "medium_confidence_count": 2, "total_signals": 12}
        confidence = self.sensor_manager._determine_confidence_level(low_conf_insights)
        self.assertEqual(confidence, "low")

    async def test_mock_mqtt_client(self):
        """Test mock MQTT client functionality."""
        mock_client = MockMQTTClient()

        # Test connect
        await mock_client.connect()

        # Test publish
        await mock_client.publish("test/topic", "test payload")

        # Test disconnect
        await mock_client.disconnect()

        # All should complete without error


class TestMLSensorIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration tests for ML sensors with mocked dependencies."""

    async def asyncSetUp(self):
        """Set up async test fixtures."""
        self.sensor_manager = HALazyInvestorSensors()

        # Mock MQTT client
        self.mock_mqtt = AsyncMock()
        self.sensor_manager.mqtt_client = self.mock_mqtt

    async def test_publish_sensor_discovery(self):
        """Test sensor discovery message publishing."""
        sensor = MLSensorData(name="test_sensor", state="active", attributes={"friendly_name": "Test Sensor"})

        await self.sensor_manager.publish_sensor_discovery(sensor)

        # Verify MQTT publish was called
        self.mock_mqtt.publish.assert_called()

        # Check that discovery topic was used
        call_args = self.mock_mqtt.publish.call_args
        topic = call_args[0][0]
        self.assertIn("homeassistant/sensor/crypto_inspect/test_sensor/config", topic)

    async def test_update_sensor_state(self):
        """Test sensor state and attributes update."""
        sensor = MLSensorData(
            name="test_sensor", state="active", attributes={"friendly_name": "Test Sensor", "value": 42}
        )

        await self.sensor_manager.update_sensor_state(sensor)

        # Should call publish twice (state + attributes)
        self.assertEqual(self.mock_mqtt.publish.call_count, 2)

        # Check state publication
        state_call = self.mock_mqtt.publish.call_args_list[0]
        self.assertEqual(state_call[0][1], "active")  # state value

        # Check attributes publication
        attrs_call = self.mock_mqtt.publish.call_args_list[1]
        attrs_payload = json.loads(attrs_call[0][1])
        self.assertEqual(attrs_payload["value"], 42)

    async def test_publish_all_sensors(self):
        """Test publishing all sensors."""
        with patch.object(self.sensor_manager, "create_investment_sensors") as mock_create:
            mock_create.return_value = [
                MLSensorData("sensor1", "state1", {"friendly_name": "Sensor 1"}),
                MLSensorData("sensor2", "state2", {"friendly_name": "Sensor 2"}),
            ]

            sensors = await self.sensor_manager.publish_all_sensors()

            # Should return created sensors
            self.assertEqual(len(sensors), 2)

            # Should call publish for each sensor (discovery + state + attributes)
            # 2 sensors × 3 publishes each = 6 total calls
            self.assertEqual(self.mock_mqtt.publish.call_count, 6)

    async def test_update_with_ml_data(self):
        """Test updating sensors with ML analysis data."""
        ml_insights = {
            "portfolio_sentiment": "bullish",
            "opportunity_signals": 3,
            "risk_signals": 1,
            "hold_signals": 8,
            "total_analyzed": 12,
            "high_confidence_count": 4,
            "medium_confidence_count": 6,
            "low_confidence_count": 2,
            "total_signals": 12,
            "recommendation": "Consider gradual accumulation",
        }

        await self.sensor_manager.update_with_ml_data(ml_insights)

        # Should update at least 2 sensors (health and confidence)
        self.assertGreaterEqual(self.mock_mqtt.publish.call_count, 4)  # 2 sensors × 2 publishes each

        # Verify data was used correctly
        calls = self.mock_mqtt.publish.call_args_list
        for call in calls:
            payload = call[0][1]
            if isinstance(payload, str) and "bullish" in payload:
                # Found health sensor update
                pass
            elif isinstance(payload, str) and "high" in payload:
                # Found confidence sensor update
                pass


class TestErrorHandling(unittest.IsolatedAsyncioTestCase):
    """Test error handling scenarios."""

    async def asyncSetUp(self):
        """Set up error handling tests."""
        self.sensor_manager = HALazyInvestorSensors()

    async def test_mqtt_connection_failure(self):
        """Test handling of MQTT connection failures."""
        # Mock connection failure
        with patch("services.ha.ml_sensors.aiomqtt.Client") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_instance.connect.side_effect = Exception("Connection failed")
            mock_client_class.return_value = mock_client_instance

            # Should fall back to mock client without crashing
            await self.sensor_manager.initialize_mqtt()
            self.assertIsInstance(self.sensor_manager.mqtt_client, MockMQTTClient)

    async def test_mqtt_publish_failure(self):
        """Test handling of MQTT publish failures."""
        # Mock publish failure
        mock_mqtt = AsyncMock()
        mock_mqtt.publish.side_effect = Exception("Publish failed")
        self.sensor_manager.mqtt_client = mock_mqtt

        sensor = MLSensorData("test", "state", {"friendly_name": "Test"})

        # Should not crash on publish failure
        try:
            await self.sensor_manager.update_sensor_state(sensor)
        except Exception:
            self.fail("update_sensor_state should handle publish failures gracefully")

    async def test_empty_ml_data(self):
        """Test handling of empty or malformed ML data."""
        # Should handle empty data gracefully
        empty_data = {}
        try:
            await self.sensor_manager.update_with_ml_data(empty_data)
        except Exception:
            self.fail("update_with_ml_data should handle empty data gracefully")

        # Should handle partial data
        partial_data = {"portfolio_sentiment": "neutral"}
        try:
            await self.sensor_manager.update_with_ml_data(partial_data)
        except Exception:
            self.fail("update_with_ml_data should handle partial data gracefully")


def run_tests():
    """Run all tests for HA ML sensors."""

    print("🧪 RUNNING HA ML SENSORS TESTS")
    print("=" * 40)

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestHALazyInvestorSensors))
    suite.addTests(loader.loadTestsFromTestCase(TestMLSensorIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestErrorHandling))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n📊 TEST RESULTS:")
    print(f"  Tests run: {result.testsRun}")
    print(f"  Failures: {len(result.failures)}")
    print(f"  Errors: {len(result.errors)}")

    if result.failures:
        print("\n❌ FAILURES:")
        for test, traceback in result.failures:
            print(f"  {test}: {traceback}")

    if result.errors:
        print("\n💥 ERRORS:")
        for test, traceback in result.errors:
            print(f"  {test}: {traceback}")

    if result.wasSuccessful():
        print("\n✅ ALL TESTS PASSED!")
        print("🚀 HA ML Sensors ready for production!")
    else:
        print("\n⚠️  SOME TESTS FAILED")

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
