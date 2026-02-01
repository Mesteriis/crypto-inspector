"""
Unit Tests for Russian ML Sensors and Cleanup Job

Tests the Russian-language ML sensors and periodic cleanup functionality.
"""

import asyncio

# Add src to path
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from core.scheduler.ml_cleanup_job import MLPredictionCleanupJob
from service.ha import get_sensors_manager


class TestRussianMLSensors(unittest.IsolatedAsyncioTestCase):
    """Test suite for Russian ML sensors."""

    async def asyncSetUp(self):
        """Set up test fixtures."""
        # Mock Supervisor API client
        self.mock_client = AsyncMock()
        self.mock_client.is_available = True

        # Patch the get_supervisor_client function
        self.patcher = patch("service.ha_integration.get_supervisor_client", return_value=self.mock_client)
        self.patcher.start()

        self.sensor_manager = get_sensors_manager()
        # Mock the publisher's publish_sensor method
        self.sensor_manager.publisher.publish_sensor = AsyncMock(return_value=True)

    async def asyncTearDown(self):
        """Clean up after tests."""
        self.patcher.stop()

    async def test_russian_ml_investor_sensors(self):
        """Test Russian ML investor sensors creation."""
        ml_data = {
            "portfolio_sentiment": "бычий",
            "opportunity_signals": 3,
            "risk_signals": 1,
            "hold_signals": 8,
            "total_analyzed": 12,
            "recommendation": "Рассмотрите постепенное накопление",
            "last_analysis": "2026-01-18T22:00:00",
            "confidence_threshold": 70,
            "confidence_level": "высокий",
            "high_confidence_count": 5,
            "medium_confidence_count": 4,
            "low_confidence_count": 3,
            "action_required": True,
            "opportunity_status": "умеренный",
            "opportunity_symbols": ["SOL/USDT", "ADA/USDT"],
            "risk_level": "предупреждение",
            "risk_symbols": ["BTC/USDT"],
            "system_status": "операционный",
            "models_analyzed": 12,
            "average_accuracy": "50%",
        }

        await self.sensor_manager.update_ml_investor_sensors(ml_data)

        # Verify publish_sensor was called with portfolio_health
        self.sensor_manager.publisher.publish_sensor.assert_called()

        # Check that the call included the sentiment data
        calls = self.sensor_manager.publisher.publish_sensor.call_args_list
        sensor_ids_called = [call[0][0] for call in calls]
        self.assertIn("portfolio_health", sensor_ids_called)

    async def test_russian_ml_prediction_sensors(self):
        """Test Russian ML prediction sensors."""
        prediction_data = {
            "latest_predictions": {
                "BTC/USDT": {"prediction": "up", "confidence": 85},
                "ETH/USDT": {"prediction": "down", "confidence": 72},
            },
            "correct_predictions": 45,
            "incorrect_predictions": 23,
            "total_predictions": 68,
            "accuracy_percentage": 66.2,
            "last_update": "2026-01-18T22:00:00",
        }

        await self.sensor_manager.update_ml_prediction_sensors(prediction_data)

        # Verify publish_sensor was called for prediction sensors
        self.sensor_manager.publisher.publish_sensor.assert_called()

        calls = self.sensor_manager.publisher.publish_sensor.call_args_list
        sensor_ids_called = [call[0][0] for call in calls]

        # Check that prediction sensors were published
        self.assertIn("ml_latest_predictions", sensor_ids_called)
        self.assertIn("ml_correct_predictions", sensor_ids_called)
        self.assertIn("ml_accuracy_rate", sensor_ids_called)

    async def test_accuracy_rating_function(self):
        """Test accuracy rating function with Russian labels."""
        test_cases = [
            (85.5, "отличная"),
            (72.3, "хорошая"),
            (61.8, "удовлетворительная"),
            (55.0, "средняя"),
            (42.1, "низкая"),
        ]

        for accuracy, expected_rating in test_cases:
            with self.subTest(accuracy=accuracy):
                rating = self.sensor_manager._get_accuracy_rating(accuracy)
                self.assertEqual(rating, expected_rating)

    async def test_supervisor_api_unavailable(self):
        """Test behavior when Supervisor API is unavailable."""
        self.mock_client.is_available = False

        ml_data = {"portfolio_sentiment": "бычий"}
        prediction_data = {"correct_predictions": 10}

        # Should not crash when API unavailable
        try:
            await self.sensor_manager.update_ml_investor_sensors(ml_data)
            await self.sensor_manager.update_ml_prediction_sensors(prediction_data)
        except Exception:
            self.fail("Should handle Supervisor API unavailability gracefully")


class TestMLCleanupJob(unittest.IsolatedAsyncioTestCase):
    """Test suite for ML prediction cleanup job."""

    async def asyncSetUp(self):
        """Set up cleanup job tests."""
        self.cleanup_job = MLPredictionCleanupJob()

        # Mock Supervisor client
        self.mock_client = AsyncMock()
        self.mock_client.is_available = True

        # Patch get_supervisor_client
        self.client_patcher = patch("service.ha_integration.get_supervisor_client", return_value=self.mock_client)
        self.client_patcher.start()

    async def asyncTearDown(self):
        """Clean up patches."""
        self.client_patcher.stop()

    async def test_cleanup_statistics(self):
        """Test cleanup returns proper statistics."""
        result = await self.cleanup_job.cleanup_old_predictions()

        # Should return statistics dictionary
        self.assertIsInstance(result, dict)
        self.assertIn("deleted_count", result)
        self.assertIn("remaining_count", result)
        self.assertIn("cutoff_date", result)

        # Counts should be reasonable
        self.assertGreaterEqual(result["deleted_count"], 0)
        self.assertGreaterEqual(result["remaining_count"], 0)

    async def test_cleanup_notification_availability_check(self):
        """Test that cleanup checks client availability before sending notifications."""
        # Test when client is available
        self.mock_client.is_available = True
        result = await self.cleanup_job.cleanup_old_predictions()

        # Should not have error about client unavailability
        self.assertNotIn("error", result)

        # Test when client is unavailable
        self.mock_client.is_available = False
        result = await self.cleanup_job.cleanup_old_predictions()

        # Should handle gracefully
        self.assertIn("deleted_count", result)

    async def test_cleanup_error_handling(self):
        """Test cleanup handles errors gracefully."""
        # Mock error in cleanup process
        with patch.object(self.cleanup_job, "_perform_cleanup", side_effect=Exception("Database error")):
            result = await self.cleanup_job.cleanup_old_predictions()

            # Should return error information
            self.assertIn("error", result)
            self.assertEqual(result["deleted_count"], 0)
            self.assertEqual(result["remaining_count"], 0)

    async def test_periodic_scheduler_logic(self):
        """Test periodic cleanup scheduler logic (limited test)."""
        # Test single iteration of scheduler
        with patch.object(asyncio, "sleep") as mock_sleep:
            # Cancel after first iteration
            mock_sleep.side_effect = asyncio.CancelledError()

            try:
                await self.cleanup_job.schedule_periodic_cleanup()
            except asyncio.CancelledError:
                pass  # Expected

            # Scheduler loop should have been entered
            # (actual notification sending tested separately)


def run_russian_ml_tests():
    """Run all Russian ML tests."""

    print("🇷🇺 ЗАПУСК ТЕСТОВ РУССКИХ ML-СЕНСОРОВ")
    print("=" * 50)

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestRussianMLSensors))
    suite.addTests(loader.loadTestsFromTestCase(TestMLCleanupJob))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n📊 РЕЗУЛЬТАТЫ ТЕСТОВ:")
    print(f"  Всего тестов: {result.testsRun}")
    print(f"  Провалов: {len(result.failures)}")
    print(f"  Ошибок: {len(result.errors)}")

    if result.failures:
        print("\n❌ ПРОВАЛЕННЫЕ ТЕСТЫ:")
        for test, traceback in result.failures:
            print(f"  {test}: {traceback}")

    if result.errors:
        print("\n💥 ОШИБКИ:")
        for test, traceback in result.errors:
            print(f"  {test}: {traceback}")

    success = result.wasSuccessful()
    if success:
        print("\n✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        print("🚀 Русские ML-сенсоры и задача очистки готовы!")
    else:
        print("\n⚠️  НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ")

    return success


if __name__ == "__main__":
    success = run_russian_ml_tests()
    exit(0 if success else 1)
