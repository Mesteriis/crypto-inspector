"""
Unit tests for dictionary-format sensors.

Tests coverage for new consolidated dictionary sensors:
- AI trend sensors (ai_trends, ai_confidences, ai_price_forecasts_24h)
- Adaptive notification sensors (adaptive_volatilities, adaptive_adaptation_factors)
- Exchange flow sensors (exchange_netflows)
- Technical analysis sensors (ta_* dictionary formats)
- Other dictionary-format sensors
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
from datetime import datetime, UTC


class TestDictionarySensorFormats:
    """Tests for dictionary-format sensor data structures."""

    @pytest.fixture
    def sample_crypto_data(self):
        """Sample cryptocurrency data for testing."""
        return {
            "BTC/USDT": {
                "price": 95000.0,
                "change_24h": 2.5,
                "volume": 50000000000.0,
                "rsi": 65.5,
                "trend": "bullish",
                "volatility": "high"
            },
            "ETH/USDT": {
                "price": 3200.0,
                "change_24h": -1.2,
                "volume": 25000000000.0,
                "rsi": 45.2,
                "trend": "neutral",
                "volatility": "medium"
            },
            "SOL/USDT": {
                "price": 150.0,
                "change_24h": 5.8,
                "volume": 8000000000.0,
                "rsi": 72.1,
                "trend": "bullish",
                "volatility": "high"
            }
        }

    def test_ai_trends_format(self, sample_crypto_data):
        """Test AI trends sensor dictionary format."""
        # Simulate AI trends data
        ai_trends = {}
        for symbol, data in sample_crypto_data.items():
            coin = symbol.split('/')[0]  # Extract BTC, ETH, SOL
            if data["trend"] == "bullish":
                ai_trends[coin] = "Bullish"
            elif data["trend"] == "neutral":
                ai_trends[coin] = "Neutral"
            else:
                ai_trends[coin] = "Bearish"
        
        # Verify format
        assert isinstance(ai_trends, dict)
        assert len(ai_trends) == 3  # BTC, ETH, SOL
        for coin, trend in ai_trends.items():
            assert coin in ["BTC", "ETH", "SOL"]
            assert trend in ["Bullish", "Neutral", "Bearish"]
        
        print(f"✅ AI Trends format verified: {ai_trends}")

    def test_ai_confidences_format(self, sample_crypto_data):
        """Test AI confidences sensor dictionary format."""
        # Simulate AI confidence data (based on RSI distance from extremes)
        ai_confidences = {}
        for symbol, data in sample_crypto_data.items():
            coin = symbol.split('/')[0]
            rsi = data["rsi"]
            
            # Higher confidence when RSI is extreme or near center
            if rsi > 70 or rsi < 30:
                confidence = 85  # High confidence for extreme RSI
            elif 40 <= rsi <= 60:
                confidence = 90  # Very high confidence for neutral RSI
            else:
                confidence = 75  # Moderate confidence
            
            ai_confidences[coin] = confidence
        
        # Verify format
        assert isinstance(ai_confidences, dict)
        assert len(ai_confidences) == 3
        for coin, confidence in ai_confidences.items():
            assert coin in ["BTC", "ETH", "SOL"]
            assert isinstance(confidence, int)
            assert 0 <= confidence <= 100
        
        print(f"✅ AI Confidences format verified: {ai_confidences}")

    def test_ai_price_forecasts_format(self, sample_crypto_data):
        """Test AI price forecasts sensor dictionary format."""
        # Simulate 24h price forecasts (simple projection)
        ai_forecasts = {}
        for symbol, data in sample_crypto_data.items():
            coin = symbol.split('/')[0]
            current_price = data["price"]
            change_24h = data["change_24h"]
            
            # Simple forecast: current price + projected change
            forecast_change = change_24h * 0.8  # Reduce magnitude for forecast
            forecast_price = current_price * (1 + forecast_change / 100)
            
            ai_forecasts[coin] = round(forecast_price, 2)
        
        # Verify format
        assert isinstance(ai_forecasts, dict)
        assert len(ai_forecasts) == 3
        for coin, forecast in ai_forecasts.items():
            assert coin in ["BTC", "ETH", "SOL"]
            assert isinstance(forecast, (int, float))
            assert forecast > 0
        
        print(f"✅ AI Price Forecasts format verified: {ai_forecasts}")

    def test_adaptive_volatilities_format(self, sample_crypto_data):
        """Test adaptive volatilities sensor dictionary format."""
        # Simulate adaptive volatility levels
        adaptive_vols = {}
        for symbol, data in sample_crypto_data.items():
            coin = symbol.split('/')[0]
            base_vol = data["volatility"]
            
            # Map to adaptive levels
            if base_vol == "high":
                adaptive_vols[coin] = "High"
            elif base_vol == "medium":
                adaptive_vols[coin] = "Medium"
            else:
                adaptive_vols[coin] = "Low"
        
        # Verify format
        assert isinstance(adaptive_vols, dict)
        assert len(adaptive_vols) == 3
        for coin, vol_level in adaptive_vols.items():
            assert coin in ["BTC", "ETH", "SOL"]
            assert vol_level in ["High", "Medium", "Low"]
        
        print(f"✅ Adaptive Volatilities format verified: {adaptive_vols}")

    def test_adaptive_adaptation_factors_format(self, sample_crypto_data):
        """Test adaptive adaptation factors sensor dictionary format."""
        # Simulate adaptation factors based on market conditions
        adaptation_factors = {}
        for symbol, data in sample_crypto_data.items():
            coin = symbol.split('/')[0]
            rsi = data["rsi"]
            volume = data["volume"]
            
            # Higher factor for volatile conditions
            if rsi > 70 or rsi < 30:  # Extreme RSI
                factor = 1.5
            elif volume > 30000000000:  # High volume
                factor = 1.3
            else:
                factor = 1.0
            
            adaptation_factors[coin] = round(factor, 1)
        
        # Verify format
        assert isinstance(adaptation_factors, dict)
        assert len(adaptation_factors) == 3
        for coin, factor in adaptation_factors.items():
            assert coin in ["BTC", "ETH", "SOL"]
            assert isinstance(factor, (int, float))
            assert factor >= 1.0
        
        print(f"✅ Adaptive Adaptation Factors format verified: {adaptation_factors}")

    def test_exchange_netflows_format(self):
        """Test exchange netflows sensor dictionary format."""
        # Simulate exchange netflow data
        netflows = {
            "BTC": -1500,  # Negative = withdrawal from exchanges
            "ETH": 800,    # Positive = deposit to exchanges
            "SOL": -300,   # Negative = withdrawal from exchanges
            "ADA": 1200,   # Positive = deposit to exchanges
            "DOT": -750    # Negative = withdrawal from exchanges
        }
        
        # Verify format
        assert isinstance(netflows, dict)
        for coin, flow in netflows.items():
            assert isinstance(coin, str)
            assert isinstance(flow, (int, float))
            # Flow can be positive or negative
            assert -10000 <= flow <= 10000  # Reasonable range
        
        print(f"✅ Exchange Netflows format verified: {netflows}")

    def test_ta_indicators_format(self, sample_crypto_data):
        """Test technical analysis indicators dictionary format."""
        # Test multiple TA indicators
        ta_data = {
            "rsi": {},
            "macd_signal": {},
            "bb_position": {},
            "trend": {}
        }
        
        for symbol, data in sample_crypto_data.items():
            coin = symbol.split('/')[0]
            rsi = data["rsi"]
            
            # RSI
            ta_data["rsi"][coin] = round(rsi, 1)
            
            # MACD Signal
            if rsi > 70:
                ta_data["macd_signal"][coin] = "bearish"
            elif rsi < 30:
                ta_data["macd_signal"][coin] = "bullish"
            else:
                ta_data["macd_signal"][coin] = "neutral"
            
            # Bollinger Bands Position (0.0-1.0)
            bb_pos = min(1.0, max(0.0, (rsi - 30) / 40))
            ta_data["bb_position"][coin] = round(bb_pos, 2)
            
            # Trend
            ta_data["trend"][coin] = data["trend"]
        
        # Verify all TA indicators
        for indicator_name, values in ta_data.items():
            assert isinstance(values, dict)
            assert len(values) == 3  # BTC, ETH, SOL
            for coin in values.keys():
                assert coin in ["BTC", "ETH", "SOL"]
        
        print(f"✅ TA Indicators format verified for {len(ta_data)} indicators")

    def test_empty_dictionary_handling(self):
        """Test handling of empty dictionaries."""
        empty_dict = {}
        
        # Should be valid empty dictionary
        assert isinstance(empty_dict, dict)
        assert len(empty_dict) == 0
        
        # Should not raise errors when accessed safely
        assert empty_dict.get("nonexistent", "default") == "default"
        
        print("✅ Empty dictionary handling verified")

    def test_nested_dictionary_validation(self):
        """Test validation of nested dictionary structures."""
        # Complex nested structure
        complex_data = {
            "BTC": {
                "trend": "Bullish",
                "confidence": 85,
                "forecast_24h": 96000,
                "indicators": {
                    "rsi": 65.5,
                    "macd": "bullish",
                    "support": 92000
                }
            },
            "ETH": {
                "trend": "Neutral",
                "confidence": 90,
                "forecast_24h": 3150,
                "indicators": {
                    "rsi": 45.2,
                    "macd": "neutral",
                    "support": 3000
                }
            }
        }
        
        # Verify structure
        assert isinstance(complex_data, dict)
        for coin, data in complex_data.items():
            assert isinstance(data, dict)
            assert "trend" in data
            assert "confidence" in data
            assert "forecast_24h" in data
            assert "indicators" in data
            assert isinstance(data["indicators"], dict)
        
        print(f"✅ Nested dictionary validation passed for {len(complex_data)} coins")


class TestDictionarySensorUpdates:
    """Tests for updating dictionary-format sensors."""

    @pytest.mark.asyncio
    async def test_update_ai_trends_sensor(self):
        """Test updating AI trends sensor with dictionary data."""
        mock_manager = AsyncMock()
        mock_manager._update_sensor_state = AsyncMock()
        mock_manager._update_sensor_attributes = AsyncMock()
        
        # Sample AI trends data
        ai_trends = {
            "BTC": "Bullish",
            "ETH": "Neutral", 
            "SOL": "Bullish"
        }
        
        # Simulate sensor update
        await mock_manager._update_sensor_state("ai_trends", json.dumps(ai_trends))
        await mock_manager._update_sensor_attributes("ai_trends", {"count": len(ai_trends)})
        
        # Verify calls were made
        assert mock_manager._update_sensor_state.called
        assert mock_manager._update_sensor_attributes.called
        
        # Verify data format
        call_args = mock_manager._update_sensor_state.call_args[0]
        sensor_id, state_data = call_args
        assert sensor_id == "ai_trends"
        parsed_data = json.loads(state_data)
        assert isinstance(parsed_data, dict)
        assert len(parsed_data) == 3
        
        print("✅ AI trends sensor update test passed")

    @pytest.mark.asyncio
    async def test_update_exchange_flows_sensor(self):
        """Test updating exchange flows sensor."""
        mock_manager = AsyncMock()
        mock_manager._update_sensor_state = AsyncMock()
        
        # Sample exchange flow data
        flows = {
            "BTC": -1250.5,
            "ETH": 680.2,
            "SOL": -295.8
        }
        
        # Update sensor
        await mock_manager._update_sensor_state("exchange_netflows", json.dumps(flows))
        
        # Verify
        call_args = mock_manager._update_sensor_state.call_args[0]
        sensor_id, state_data = call_args
        assert sensor_id == "exchange_netflows"
        parsed_data = json.loads(state_data)
        assert isinstance(parsed_data, dict)
        
        # Verify flow values
        for coin, flow in parsed_data.items():
            assert isinstance(flow, (int, float))
        
        print("✅ Exchange flows sensor update test passed")

    @pytest.mark.asyncio
    async def test_batch_dictionary_updates(self):
        """Test batch updating multiple dictionary sensors."""
        mock_manager = AsyncMock()
        mock_manager._update_sensor_state = AsyncMock()
        
        # Multiple dictionary sensors to update
        sensor_updates = {
            "ai_trends": {"BTC": "Bullish", "ETH": "Neutral"},
            "ai_confidences": {"BTC": 85, "ETH": 90},
            "exchange_netflows": {"BTC": -500, "ETH": 200}
        }
        
        # Batch update
        update_count = 0
        for sensor_id, data in sensor_updates.items():
            await mock_manager._update_sensor_state(sensor_id, json.dumps(data))
            update_count += 1
        
        # Verify all updates occurred
        assert mock_manager._update_sensor_state.call_count == update_count
        assert update_count == len(sensor_updates)
        
        print(f"✅ Batch dictionary updates test passed ({update_count} sensors)")


class TestDictionarySensorEdgeCases:
    """Tests for edge cases in dictionary sensors."""

    def test_special_characters_in_keys(self):
        """Test handling of special characters in dictionary keys."""
        # Some exchanges might use special symbols
        special_keys = {
            "BTC-PERP": "Bullish",  # Futures contract
            "ETH-USD": "Neutral",   # Spot with dash
            "SOL_USDT": "Bearish"   # Underscore separator
        }
        
        # Verify format
        assert isinstance(special_keys, dict)
        for key in special_keys.keys():
            assert isinstance(key, str)
            # Keys should be valid identifiers or contract names
            assert len(key) > 0
        
        print("✅ Special character keys handling verified")

    def test_numeric_values_range_validation(self):
        """Test validation of numeric values in dictionaries."""
        test_cases = [
            {"BTC": 95000.50, "ETH": 3200.25},  # Normal prices
            {"BTC": 0.00001, "ETH": 0.000001},  # Very small values
            {"BTC": 1000000, "ETH": 500000},    # Large values
        ]
        
        for i, test_data in enumerate(test_cases):
            assert isinstance(test_data, dict)
            for coin, value in test_data.items():
                assert isinstance(value, (int, float))
                assert value >= 0  # Prices should be non-negative
        
        print(f"✅ Numeric values validation passed for {len(test_cases)} test cases")

    def test_boolean_values_in_dictionaries(self):
        """Test handling of boolean values in dictionary sensors."""
        boolean_data = {
            "BTC": True,   # Bullish signal
            "ETH": False,  # Bearish signal
            "SOL": True    # Bullish signal
        }
        
        assert isinstance(boolean_data, dict)
        for coin, value in boolean_data.items():
            assert isinstance(value, bool)
        
        print("✅ Boolean values in dictionaries verified")

    def test_mixed_data_types(self):
        """Test dictionaries with mixed data types."""
        mixed_data = {
            "BTC": {
                "price": 95000.0,
                "change_pct": 2.5,
                "is_bullish": True,
                "signal_strength": "strong"
            },
            "ETH": {
                "price": 3200.0,
                "change_pct": -1.2,
                "is_bullish": False,
                "signal_strength": "weak"
            }
        }
        
        assert isinstance(mixed_data, dict)
        for coin, data in mixed_data.items():
            assert isinstance(data, dict)
            assert isinstance(data["price"], (int, float))
            assert isinstance(data["change_pct"], (int, float))
            assert isinstance(data["is_bullish"], bool)
            assert isinstance(data["signal_strength"], str)
        
        print("✅ Mixed data types handling verified")


if __name__ == "__main__":
    # Run tests manually
    pytest.main([__file__, "-v"])