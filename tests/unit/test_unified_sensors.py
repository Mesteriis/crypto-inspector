"""100% coverage tests for service/unified_sensors.py."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from service.unified_sensors import (
    UnifiedSensorManager,
    get_unified_sensor_manager,
)

# ═══════════════════════════════════════════════════════════════════════════
#                      UnifiedSensorManager Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestUnifiedSensorManager:
    """Tests for UnifiedSensorManager class."""

    def test_init(self):
        """Test manager initialization."""
        mock_sensors_manager = MagicMock()
        manager = UnifiedSensorManager(mock_sensors_manager)

        assert manager.sensors_manager is mock_sensors_manager
        assert manager._consolidated_sensors_created is False

    def test_is_initialized_false(self):
        """Test is_initialized returns False initially."""
        mock_sensors_manager = MagicMock()
        manager = UnifiedSensorManager(mock_sensors_manager)

        assert manager.is_initialized() is False

    def test_is_initialized_true(self):
        """Test is_initialized returns True after creation."""
        mock_sensors_manager = MagicMock()
        manager = UnifiedSensorManager(mock_sensors_manager)
        manager._consolidated_sensors_created = True

        assert manager.is_initialized() is True

    def test_consolidated_sensors_list(self):
        """Test CONSOLIDATED_SENSORS class attribute."""
        expected = [
            "price_predictions",
            "ai_trend_directions",
            "technical_indicators",
            "market_volatility",
            "market_sentiment",
        ]
        assert UnifiedSensorManager.CONSOLIDATED_SENSORS == expected


class TestUnifiedSensorManagerCreateSensors:
    """Tests for sensor creation methods."""

    @pytest.mark.asyncio
    async def test_create_consolidated_sensors_success(self):
        """Test successful consolidated sensor creation."""
        mock_sensors_manager = MagicMock()
        manager = UnifiedSensorManager(mock_sensors_manager)

        await manager.create_consolidated_sensors()

        assert manager._consolidated_sensors_created is True

    @pytest.mark.asyncio
    async def test_create_consolidated_sensors_already_created(self):
        """Test that sensors are not recreated if already created."""
        mock_sensors_manager = MagicMock()
        manager = UnifiedSensorManager(mock_sensors_manager)
        manager._consolidated_sensors_created = True

        # Should return early without doing anything
        await manager.create_consolidated_sensors()

        assert manager._consolidated_sensors_created is True


class TestUnifiedSensorManagerUpdateSensors:
    """Tests for sensor update methods."""

    @pytest.mark.asyncio
    async def test_update_consolidated_sensors_creates_first(self):
        """Test that update creates sensors if not created."""
        mock_sensors_manager = MagicMock()
        mock_sensors_manager.publish_sensor = AsyncMock()
        manager = UnifiedSensorManager(mock_sensors_manager)

        with patch("service.unified_sensors.get_currency_list", return_value=["BTC/USDT"]):
            await manager.update_consolidated_sensors()

        assert manager._consolidated_sensors_created is True

    @pytest.mark.asyncio
    async def test_update_consolidated_sensors_success(self):
        """Test successful sensor update."""
        mock_sensors_manager = MagicMock()
        mock_sensors_manager.publish_sensor = AsyncMock()
        manager = UnifiedSensorManager(mock_sensors_manager)
        manager._consolidated_sensors_created = True

        with patch("service.unified_sensors.get_currency_list", return_value=["BTC/USDT", "ETH/USDT"]):
            await manager.update_consolidated_sensors()

        # 5 sensors updated via publish_sensor
        assert mock_sensors_manager.publish_sensor.call_count == 5

    @pytest.mark.asyncio
    async def test_update_consolidated_sensors_handles_error(self):
        """Test error handling during sensor update."""
        mock_sensors_manager = MagicMock()
        manager = UnifiedSensorManager(mock_sensors_manager)
        manager._consolidated_sensors_created = True

        with patch("service.unified_sensors.get_currency_list", side_effect=Exception("Test error")):
            # Should not raise
            await manager.update_consolidated_sensors()

    @pytest.mark.asyncio
    async def test_update_price_predictions(self):
        """Test price predictions update."""
        mock_sensors_manager = MagicMock()
        mock_sensors_manager.publish_sensor = AsyncMock()
        manager = UnifiedSensorManager(mock_sensors_manager)

        await manager._update_price_predictions(["BTC/USDT", "ETH/USDT"])

        mock_sensors_manager.publish_sensor.assert_called_once()
        call_args = mock_sensors_manager.publish_sensor.call_args
        assert call_args[0][0] == "price_predictions"
        assert call_args[0][1] == {}  # Empty dict (placeholders return None)

    @pytest.mark.asyncio
    async def test_update_price_predictions_handles_error(self):
        """Test error handling in price predictions update."""
        mock_sensors_manager = MagicMock()
        mock_sensors_manager.publish_sensor = AsyncMock(side_effect=Exception("Test error"))
        manager = UnifiedSensorManager(mock_sensors_manager)

        # Should not raise
        await manager._update_price_predictions(["BTC/USDT"])

    @pytest.mark.asyncio
    async def test_update_ai_trends(self):
        """Test AI trends update."""
        mock_sensors_manager = MagicMock()
        mock_sensors_manager.publish_sensor = AsyncMock()
        manager = UnifiedSensorManager(mock_sensors_manager)

        await manager._update_ai_trends(["BTC/USDT"])

        mock_sensors_manager.publish_sensor.assert_called_once()
        call_args = mock_sensors_manager.publish_sensor.call_args
        assert call_args[0][0] == "ai_trend_directions"

    @pytest.mark.asyncio
    async def test_update_ai_trends_handles_error(self):
        """Test error handling in AI trends update."""
        mock_sensors_manager = MagicMock()
        mock_sensors_manager.publish_sensor = AsyncMock(side_effect=Exception("Test"))
        manager = UnifiedSensorManager(mock_sensors_manager)

        await manager._update_ai_trends(["BTC/USDT"])

    @pytest.mark.asyncio
    async def test_update_technical_indicators(self):
        """Test technical indicators update."""
        mock_sensors_manager = MagicMock()
        mock_sensors_manager.publish_sensor = AsyncMock()
        manager = UnifiedSensorManager(mock_sensors_manager)

        await manager._update_technical_indicators(["BTC/USDT"])

        mock_sensors_manager.publish_sensor.assert_called_once()
        call_args = mock_sensors_manager.publish_sensor.call_args
        assert call_args[0][0] == "technical_indicators"

    @pytest.mark.asyncio
    async def test_update_technical_indicators_handles_error(self):
        """Test error handling in technical indicators update."""
        mock_sensors_manager = MagicMock()
        mock_sensors_manager.publish_sensor = AsyncMock(side_effect=Exception("Test"))
        manager = UnifiedSensorManager(mock_sensors_manager)

        await manager._update_technical_indicators(["BTC/USDT"])

    @pytest.mark.asyncio
    async def test_update_volatility_data(self):
        """Test volatility data update."""
        mock_sensors_manager = MagicMock()
        mock_sensors_manager.publish_sensor = AsyncMock()
        manager = UnifiedSensorManager(mock_sensors_manager)

        await manager._update_volatility_data(["BTC/USDT"])

        mock_sensors_manager.publish_sensor.assert_called_once()
        call_args = mock_sensors_manager.publish_sensor.call_args
        assert call_args[0][0] == "market_volatility"

    @pytest.mark.asyncio
    async def test_update_volatility_data_handles_error(self):
        """Test error handling in volatility update."""
        mock_sensors_manager = MagicMock()
        mock_sensors_manager.publish_sensor = AsyncMock(side_effect=Exception("Test"))
        manager = UnifiedSensorManager(mock_sensors_manager)

        await manager._update_volatility_data(["BTC/USDT"])

    @pytest.mark.asyncio
    async def test_update_market_sentiment(self):
        """Test market sentiment update."""
        mock_sensors_manager = MagicMock()
        mock_sensors_manager.publish_sensor = AsyncMock()
        manager = UnifiedSensorManager(mock_sensors_manager)

        await manager._update_market_sentiment(["BTC/USDT"])

        mock_sensors_manager.publish_sensor.assert_called_once()
        call_args = mock_sensors_manager.publish_sensor.call_args
        assert call_args[0][0] == "market_sentiment"

    @pytest.mark.asyncio
    async def test_update_market_sentiment_handles_error(self):
        """Test error handling in market sentiment update."""
        mock_sensors_manager = MagicMock()
        mock_sensors_manager.publish_sensor = AsyncMock(side_effect=Exception("Test"))
        manager = UnifiedSensorManager(mock_sensors_manager)

        await manager._update_market_sentiment(["BTC/USDT"])


class TestUnifiedSensorManagerDataGetters:
    """Tests for data getter methods."""

    @pytest.mark.asyncio
    async def test_get_price_prediction_returns_none(self):
        """Test price prediction getter returns None (placeholder)."""
        mock_sensors_manager = MagicMock()
        manager = UnifiedSensorManager(mock_sensors_manager)

        result = await manager._get_price_prediction("BTC/USDT")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_ai_trend_returns_none(self):
        """Test AI trend getter returns None (placeholder)."""
        mock_sensors_manager = MagicMock()
        manager = UnifiedSensorManager(mock_sensors_manager)

        result = await manager._get_ai_trend("BTC/USDT")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_technical_indicators_returns_none(self):
        """Test technical indicators getter returns None (placeholder)."""
        mock_sensors_manager = MagicMock()
        manager = UnifiedSensorManager(mock_sensors_manager)

        result = await manager._get_technical_indicators("BTC/USDT")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_volatility_returns_none(self):
        """Test volatility getter returns None (placeholder)."""
        mock_sensors_manager = MagicMock()
        manager = UnifiedSensorManager(mock_sensors_manager)

        result = await manager._get_volatility("BTC/USDT")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_market_sentiment_returns_none(self):
        """Test market sentiment getter returns None (placeholder)."""
        mock_sensors_manager = MagicMock()
        manager = UnifiedSensorManager(mock_sensors_manager)

        result = await manager._get_market_sentiment("BTC/USDT")

        assert result is None


class TestUnifiedSensorManagerCurrencyParsing:
    """Tests for currency symbol parsing."""

    @pytest.mark.asyncio
    async def test_parses_currency_pair_with_slash(self):
        """Test that BTC/USDT is parsed to BTC."""
        mock_sensors_manager = MagicMock()
        mock_sensors_manager.publish_sensor = AsyncMock()
        manager = UnifiedSensorManager(mock_sensors_manager)

        # We can verify parsing by checking the attributes dict keys
        with patch.object(manager, "_get_price_prediction", new_callable=AsyncMock, return_value=95000.0):
            await manager._update_price_predictions(["BTC/USDT"])

        call_args = mock_sensors_manager.publish_sensor.call_args
        predictions_data = call_args[0][1]  # Second argument is dict data
        assert "BTC" in predictions_data
        assert "USDT" not in predictions_data

    @pytest.mark.asyncio
    async def test_parses_currency_without_slash(self):
        """Test that BTC without slash stays as BTC."""
        mock_sensors_manager = MagicMock()
        mock_sensors_manager.publish_sensor = AsyncMock()
        manager = UnifiedSensorManager(mock_sensors_manager)

        with patch.object(manager, "_get_price_prediction", new_callable=AsyncMock, return_value=95000.0):
            await manager._update_price_predictions(["BTC"])

        call_args = mock_sensors_manager.publish_sensor.call_args
        predictions_data = call_args[0][1]
        assert "BTC" in predictions_data


class TestUnifiedSensorManagerErrorInLoop:
    """Tests for error handling within currency loops."""

    @pytest.mark.asyncio
    async def test_continues_on_currency_error_in_predictions(self):
        """Test that loop continues if one currency fails."""
        mock_sensors_manager = MagicMock()
        mock_sensors_manager.publish_sensor = AsyncMock()
        manager = UnifiedSensorManager(mock_sensors_manager)

        call_count = 0

        async def mock_get_prediction(currency):
            nonlocal call_count
            call_count += 1
            if currency == "BTC/USDT":
                raise Exception("BTC error")
            return 3200.0

        with patch.object(manager, "_get_price_prediction", side_effect=mock_get_prediction):
            await manager._update_price_predictions(["BTC/USDT", "ETH/USDT"])

        # Both currencies were processed
        assert call_count == 2
        # Only ETH should be in the data
        call_args = mock_sensors_manager.publish_sensor.call_args
        predictions_data = call_args[0][1]
        assert "ETH" in predictions_data
        assert "BTC" not in predictions_data

    @pytest.mark.asyncio
    async def test_continues_on_currency_error_in_ai_trends(self):
        """Test that AI trends loop continues if one currency fails."""
        mock_sensors_manager = MagicMock()
        mock_sensors_manager.publish_sensor = AsyncMock()
        manager = UnifiedSensorManager(mock_sensors_manager)

        call_count = 0

        async def mock_get_trend(currency):
            nonlocal call_count
            call_count += 1
            if currency == "BTC/USDT":
                raise Exception("BTC error")
            return "Bullish"

        with patch.object(manager, "_get_ai_trend", side_effect=mock_get_trend):
            await manager._update_ai_trends(["BTC/USDT", "ETH/USDT"])

        assert call_count == 2
        call_args = mock_sensors_manager.publish_sensor.call_args
        trends_data = call_args[0][1]
        assert "ETH" in trends_data
        assert "BTC" not in trends_data

    @pytest.mark.asyncio
    async def test_continues_on_currency_error_in_technical_indicators(self):
        """Test that technical indicators loop continues if one currency fails."""
        mock_sensors_manager = MagicMock()
        mock_sensors_manager.publish_sensor = AsyncMock()
        manager = UnifiedSensorManager(mock_sensors_manager)

        call_count = 0

        async def mock_get_indicators(currency):
            nonlocal call_count
            call_count += 1
            if currency == "BTC/USDT":
                raise Exception("BTC error")
            return {"rsi": 65}

        with patch.object(manager, "_get_technical_indicators", side_effect=mock_get_indicators):
            await manager._update_technical_indicators(["BTC/USDT", "ETH/USDT"])

        assert call_count == 2
        call_args = mock_sensors_manager.publish_sensor.call_args
        tech_data = call_args[0][1]
        assert "ETH" in tech_data
        assert "BTC" not in tech_data

    @pytest.mark.asyncio
    async def test_continues_on_currency_error_in_volatility(self):
        """Test that volatility loop continues if one currency fails."""
        mock_sensors_manager = MagicMock()
        mock_sensors_manager.publish_sensor = AsyncMock()
        manager = UnifiedSensorManager(mock_sensors_manager)

        call_count = 0

        async def mock_get_volatility(currency):
            nonlocal call_count
            call_count += 1
            if currency == "BTC/USDT":
                raise Exception("BTC error")
            return 2.5

        with patch.object(manager, "_get_volatility", side_effect=mock_get_volatility):
            await manager._update_volatility_data(["BTC/USDT", "ETH/USDT"])

        assert call_count == 2
        call_args = mock_sensors_manager.publish_sensor.call_args
        vol_data = call_args[0][1]
        assert "ETH" in vol_data
        assert "BTC" not in vol_data

    @pytest.mark.asyncio
    async def test_continues_on_currency_error_in_sentiment(self):
        """Test that sentiment loop continues if one currency fails."""
        mock_sensors_manager = MagicMock()
        mock_sensors_manager.publish_sensor = AsyncMock()
        manager = UnifiedSensorManager(mock_sensors_manager)

        call_count = 0

        async def mock_get_sentiment(currency):
            nonlocal call_count
            call_count += 1
            if currency == "BTC/USDT":
                raise Exception("BTC error")
            return 0.75

        with patch.object(manager, "_get_market_sentiment", side_effect=mock_get_sentiment):
            await manager._update_market_sentiment(["BTC/USDT", "ETH/USDT"])

        assert call_count == 2
        call_args = mock_sensors_manager.publish_sensor.call_args
        sentiment_data = call_args[0][1]
        assert "ETH" in sentiment_data
        assert "BTC" not in sentiment_data


# ═══════════════════════════════════════════════════════════════════════════
#                      Global Functions Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestGetUnifiedSensorManager:
    """Tests for get_unified_sensor_manager function."""

    def test_creates_new_instance(self):
        """Test that function creates new instance when none exists."""
        import service.unified_sensors as unified_mod

        unified_mod._unified_sensor_manager = None

        mock_sensors_manager = MagicMock()
        manager = get_unified_sensor_manager(mock_sensors_manager)

        assert manager is not None
        assert isinstance(manager, UnifiedSensorManager)

        # Cleanup
        unified_mod._unified_sensor_manager = None

    def test_returns_existing_instance(self):
        """Test that function returns existing instance (singleton)."""
        import service.unified_sensors as unified_mod

        unified_mod._unified_sensor_manager = None

        mock_sensors_manager = MagicMock()
        manager1 = get_unified_sensor_manager(mock_sensors_manager)
        manager2 = get_unified_sensor_manager()

        assert manager1 is manager2

        # Cleanup
        unified_mod._unified_sensor_manager = None

    def test_raises_if_no_manager_on_first_call(self):
        """Test that function raises ValueError if no manager provided on first call."""
        import service.unified_sensors as unified_mod

        unified_mod._unified_sensor_manager = None

        with pytest.raises(ValueError, match="sensors_manager required"):
            get_unified_sensor_manager()

        # Cleanup
        unified_mod._unified_sensor_manager = None
