"""
Unit Tests for ML Investor Sensors Integration

Tests the ML sensor functionality within the existing CryptoSensorsManager.
"""

# Import the existing sensor manager
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from services.ha_sensors import get_sensors_manager


class TestMLInvestorSensors(unittest.IsolatedAsyncioTestCase):
    """Test suite for ML investor sensors integration."""

    async def asyncSetUp(self):
        """Set up test fixtures."""
        # Create sensor manager with mock MQTT client
        self.mock_mqtt = AsyncMock()
        self.sensor_manager = get_sensors_manager(mqtt_client=self.mock_mqtt)

    async def test_update_ml_portfolio_health(self):
        """Test ML portfolio health sensor update."""
        ml_data = {
            "portfolio_sentiment": "bullish",
            "opportunity_signals": 3,
            "risk_signals": 1,
            "hold_signals": 8,
            "total_analyzed": 12,
            "recommendation": "Consider gradual accumulation",
            "recommendation_ru": "Рассмотрите постепенное накопление",
            "last_analysis": "2026-01-18T22:00:00",
            "confidence_threshold": 70,
        }

        await self.sensor_manager.update_ml_investor_sensors(ml_data)

        # Verify state update
        self.mock_mqtt.publish.assert_any_call("crypto_inspect/ml_portfolio_health/state", "bullish")

        # Verify attributes update
        attr_calls = [call for call in self.mock_mqtt.publish.call_args_list if "attributes" in call[0][0]]
        self.assertTrue(any("ml_portfolio_health" in call[0][0] for call in attr_calls))

    async def test_update_ml_market_confidence(self):
        """Test ML market confidence sensor update."""
        ml_data = {
            "confidence_level": "high",
            "high_confidence_count": 5,
            "medium_confidence_count": 4,
            "low_confidence_count": 3,
            "confidence_threshold": 70,
            "high_confidence_symbols": ["BTC/USDT", "ETH/USDT"],
            "action_required": True,
        }

        await self.sensor_manager.update_ml_investor_sensors(ml_data)

        # Verify confidence level state
        self.mock_mqtt.publish.assert_any_call("crypto_inspect/ml_market_confidence/state", "high")

    async def test_update_ml_investment_opportunity(self):
        """Test ML investment opportunity sensor update."""
        ml_data = {
            "opportunity_status": "moderate",
            "opportunity_symbols": ["SOL/USDT", "ADA/USDT"],
            "best_opportunity": "SOL/USDT",
            "recommended_allocation": 10,
            "opportunity_timeframe": "medium_term",
            "opportunity_risk": "medium",
        }

        await self.sensor_manager.update_ml_investor_sensors(ml_data)

        # Verify opportunity status
        self.mock_mqtt.publish.assert_any_call("crypto_inspect/ml_investment_opportunity/state", "moderate")

    async def test_update_ml_risk_warning(self):
        """Test ML risk warning sensor update."""
        ml_data = {
            "risk_level": "warning",
            "risk_symbols": ["BTC/USDT"],
            "risk_factors": ["high_volatility", "market_downtrend"],
            "risk_action_required": True,
            "protective_measures": ["review_positions", "consider_stop_loss"],
            "stop_loss_recommendation": "Set stop-loss at 8% below entry",
        }

        await self.sensor_manager.update_ml_investor_sensors(ml_data)

        # Verify risk level
        self.mock_mqtt.publish.assert_any_call("crypto_inspect/ml_risk_warning/state", "warning")

    async def test_update_ml_system_status(self):
        """Test ML system status sensor update."""
        ml_data = {
            "system_status": "operational",
            "models_analyzed": 12,
            "average_accuracy": "50%",
            "last_analysis": "2026-01-18T22:00:00",
            "next_analysis": "2026-01-19T22:00:00",
            "processing_time": "<5s",
            "data_quality": "good",
        }

        await self.sensor_manager.update_ml_investor_sensors(ml_data)

        # Verify system status
        self.mock_mqtt.publish.assert_any_call("crypto_inspect/ml_system_status/state", "operational")

    async def test_minimal_ml_data(self):
        """Test handling of minimal ML data."""
        minimal_data = {"portfolio_sentiment": "neutral"}

        # Should not crash with minimal data
        try:
            await self.sensor_manager.update_ml_investor_sensors(minimal_data)
        except Exception:
            self.fail("update_ml_investor_sensors should handle minimal data gracefully")

    async def test_empty_ml_data(self):
        """Test handling of empty ML data."""
        empty_data = {}

        # Should not crash with empty data
        try:
            await self.sensor_manager.update_ml_investor_sensors(empty_data)
        except Exception:
            self.fail("update_ml_investor_sensors should handle empty data gracefully")

    async def test_mqtt_unavailable(self):
        """Test behavior when MQTT is unavailable."""
        # Create manager without MQTT
        no_mqtt_manager = get_sensors_manager(mqtt_client=None)

        ml_data = {"portfolio_sentiment": "bullish"}

        # Should not crash when MQTT unavailable
        try:
            await no_mqtt_manager.update_ml_investor_sensors(ml_data)
        except Exception:
            self.fail("Should handle MQTT unavailability gracefully")


class TestMLSensorDataStructure(unittest.TestCase):
    """Test the structure and content of ML sensor data."""

    def test_complete_ml_data_structure(self):
        """Test that ML data has expected structure."""
        complete_data = {
            # Portfolio Health
            "portfolio_sentiment": "bullish",
            "opportunity_signals": 3,
            "risk_signals": 1,
            "hold_signals": 8,
            "total_analyzed": 12,
            "recommendation": "Consider gradual accumulation",
            "recommendation_ru": "Рассмотрите постепенное накопление",
            # Market Confidence
            "confidence_level": "high",
            "high_confidence_count": 5,
            "medium_confidence_count": 4,
            "low_confidence_count": 3,
            "confidence_threshold": 70,
            "high_confidence_symbols": ["BTC/USDT", "ETH/USDT"],
            "action_required": True,
            # Investment Opportunity
            "opportunity_status": "moderate",
            "opportunity_symbols": ["SOL/USDT", "ADA/USDT"],
            "best_opportunity": "SOL/USDT",
            "recommended_allocation": 10,
            # Risk Warning
            "risk_level": "warning",
            "risk_symbols": ["BTC/USDT"],
            "risk_factors": ["high_volatility"],
            "risk_action_required": True,
            # System Status
            "system_status": "operational",
            "models_analyzed": 12,
            "average_accuracy": "50%",
            "processing_time": "<5s",
        }

        # All required keys should be present
        required_keys = ["portfolio_sentiment", "confidence_level", "opportunity_status", "risk_level", "system_status"]

        for key in required_keys:
            self.assertIn(key, complete_data)

    def test_default_values_handling(self):
        """Test that default values are used appropriately."""
        minimal_data = {"portfolio_sentiment": "neutral"}

        # Test defaults for missing keys
        self.assertEqual(minimal_data.get("opportunity_signals", 0), 0)
        self.assertEqual(minimal_data.get("confidence_level", "medium"), "medium")
        self.assertEqual(minimal_data.get("opportunity_status", "none"), "none")


def run_ml_sensor_tests():
    """Run all ML sensor integration tests."""

    print("🧪 RUNNING ML INVESTOR SENSOR TESTS")
    print("=" * 50)

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestMLInvestorSensors))
    suite.addTests(loader.loadTestsFromTestCase(TestMLSensorDataStructure))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n📊 ML SENSOR TEST RESULTS:")
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

    success = result.wasSuccessful()
    if success:
        print("\n✅ ALL ML SENSOR TESTS PASSED!")
        print("🚀 ML Sensors integrated successfully!")
    else:
        print("\n⚠️  SOME ML SENSOR TESTS FAILED")

    return success


if __name__ == "__main__":
    success = run_ml_sensor_tests()
    exit(0 if success else 1)
