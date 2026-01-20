"""
Unified Sensor Consolidation Service.

Replaces individual currency-specific sensors with consolidated dictionary format sensors.
"""

import logging
from typing import Any

from services.ha_sensors import CryptoSensorsManager, get_currency_list

logger = logging.getLogger(__name__)


class UnifiedSensorManager:
    """
    Manages consolidated sensors that return dictionary format data.

    Instead of separate sensors like:
    - btc_price_prediction_model1
    - eth_price_prediction_model1
    - sol_price_prediction_model1

    Creates unified sensors like:
    - price_predictions: {"BTC": 95000, "ETH": 3200, "SOL": 150}
    - ai_trend_directions: {"BTC": "Bullish", "ETH": "Neutral", "SOL": "Bearish"}
    """

    def __init__(self, sensors_manager: CryptoSensorsManager):
        self.sensors_manager = sensors_manager
        self._consolidated_sensors_created = False

    async def create_consolidated_sensors(self) -> None:
        """Create unified dictionary format sensors."""
        if self._consolidated_sensors_created:
            logger.debug("Consolidated sensors already created")
            return

        try:
            logger.info("Creating consolidated dictionary format sensors")

            # Create consolidated sensors
            await self._create_price_predictions_sensor()
            await self._create_ai_trend_sensor()
            await self._create_technical_indicators_sensor()
            await self._create_volatility_sensor()
            await self._create_market_sentiment_sensor()

            self._consolidated_sensors_created = True
            logger.info("Consolidated sensors created successfully")

        except Exception as e:
            logger.error(f"Error creating consolidated sensors: {e}")

    async def update_consolidated_sensors(self) -> None:
        """Update all consolidated sensors with current data."""
        if not self._consolidated_sensors_created:
            await self.create_consolidated_sensors()

        try:
            currencies = await get_currency_list()
            logger.debug(f"Updating consolidated sensors for {len(currencies)} currencies")

            # Update each consolidated sensor
            await self._update_price_predictions(currencies)
            await self._update_ai_trends(currencies)
            await self._update_technical_indicators(currencies)
            await self._update_volatility_data(currencies)
            await self._update_market_sentiment(currencies)

        except Exception as e:
            logger.error(f"Error updating consolidated sensors: {e}")

    async def _create_price_predictions_sensor(self) -> None:
        """Create consolidated price predictions sensor."""
        sensor_config = {
            "name": "Price Predictions",
            "name_ru": "Предсказания цен",
            "icon": "mdi:chart-line",
            "unit": "USDT",
            "description": 'AI price predictions for all currencies. Format: {"BTC": 95000, "ETH": 3200}',
            "description_ru": 'AI предсказания цен для всех валют. Формат: {"BTC": 95000, "ETH": 3200}',
        }

        await self.sensors_manager.register_sensor("price_predictions", sensor_config)

    async def _create_ai_trend_sensor(self) -> None:
        """Create consolidated AI trend sensor."""
        sensor_config = {
            "name": "AI Trend Directions",
            "name_ru": "AI направления трендов",
            "icon": "mdi:trending-up",
            "description": 'AI trend analysis for all currencies. Format: {"BTC": "Bullish", "ETH": "Neutral"}',
            "description_ru": 'AI анализ трендов для всех валют. Формат: {"BTC": "Bullish", "ETH": "Neutral"}',
        }

        await self.sensors_manager.register_sensor("ai_trend_directions", sensor_config)

    async def _create_technical_indicators_sensor(self) -> None:
        """Create consolidated technical indicators sensor."""
        sensor_config = {
            "name": "Technical Indicators",
            "name_ru": "Технические индикаторы",
            "icon": "mdi:chart-bell-curve",
            "description": 'Key technical indicators for all currencies. Format: {"BTC": {"rsi": 65, "macd": 1.2}}',
            "description_ru": 'Ключевые технические индикаторы для всех валют. Формат: {"BTC": {"rsi": 65, "macd": 1.2}}',
        }

        await self.sensors_manager.register_sensor("technical_indicators", sensor_config)

    async def _create_volatility_sensor(self) -> None:
        """Create consolidated volatility sensor."""
        sensor_config = {
            "name": "Market Volatility",
            "name_ru": "Рыночная волатильность",
            "icon": "mdi:wave",
            "unit": "%",
            "description": 'Volatility measurements for all currencies. Format: {"BTC": 2.5, "ETH": 3.1}',
            "description_ru": 'Измерения волатильности для всех валют. Формат: {"BTC": 2.5, "ETH": 3.1}',
        }

        await self.sensors_manager.register_sensor("market_volatility", sensor_config)

    async def _create_market_sentiment_sensor(self) -> None:
        """Create consolidated market sentiment sensor."""
        sensor_config = {
            "name": "Market Sentiment",
            "name_ru": "Рыночное настроение",
            "icon": "mdi:emoticon",
            "description": 'Sentiment analysis for all currencies. Format: {"BTC": 0.75, "ETH": 0.62}',
            "description_ru": 'Анализ настроения для всех валют. Формат: {"BTC": 0.75, "ETH": 0.62}',
        }

        await self.sensors_manager.register_sensor("market_sentiment", sensor_config)

    async def _update_price_predictions(self, currencies: list[str]) -> None:
        """Update consolidated price predictions sensor."""
        try:
            predictions_data = {}

            # Get predictions for each currency (this would integrate with existing prediction services)
            for currency in currencies:
                try:
                    # Extract base symbol (BTC from BTC/USDT)
                    base_symbol = currency.split("/")[0] if "/" in currency else currency

                    # Get prediction data (placeholder - would integrate with actual prediction services)
                    prediction = await self._get_price_prediction(currency)
                    if prediction is not None:
                        predictions_data[base_symbol] = prediction

                except Exception as e:
                    logger.debug(f"Could not get prediction for {currency}: {e}")
                    continue

            # Update sensor
            await self.sensors_manager._update_sensor_state("price_predictions", str(len(predictions_data)))
            await self.sensors_manager._update_sensor_attributes("price_predictions", predictions_data)

        except Exception as e:
            logger.error(f"Error updating price predictions sensor: {e}")

    async def _update_ai_trends(self, currencies: list[str]) -> None:
        """Update consolidated AI trends sensor."""
        try:
            trends_data = {}

            for currency in currencies:
                try:
                    base_symbol = currency.split("/")[0] if "/" in currency else currency
                    trend = await self._get_ai_trend(currency)
                    if trend:
                        trends_data[base_symbol] = trend

                except Exception as e:
                    logger.debug(f"Could not get AI trend for {currency}: {e}")
                    continue

            await self.sensors_manager._update_sensor_state("ai_trend_directions", str(len(trends_data)))
            await self.sensors_manager._update_sensor_attributes("ai_trend_directions", trends_data)

        except Exception as e:
            logger.error(f"Error updating AI trends sensor: {e}")

    async def _update_technical_indicators(self, currencies: list[str]) -> None:
        """Update consolidated technical indicators sensor."""
        try:
            tech_data = {}

            for currency in currencies:
                try:
                    base_symbol = currency.split("/")[0] if "/" in currency else currency
                    indicators = await self._get_technical_indicators(currency)
                    if indicators:
                        tech_data[base_symbol] = indicators

                except Exception as e:
                    logger.debug(f"Could not get technical indicators for {currency}: {e}")
                    continue

            await self.sensors_manager._update_sensor_state("technical_indicators", str(len(tech_data)))
            await self.sensors_manager._update_sensor_attributes("technical_indicators", tech_data)

        except Exception as e:
            logger.error(f"Error updating technical indicators sensor: {e}")

    async def _update_volatility_data(self, currencies: list[str]) -> None:
        """Update consolidated volatility sensor."""
        try:
            volatility_data = {}

            for currency in currencies:
                try:
                    base_symbol = currency.split("/")[0] if "/" in currency else currency
                    volatility = await self._get_volatility(currency)
                    if volatility is not None:
                        volatility_data[base_symbol] = volatility

                except Exception as e:
                    logger.debug(f"Could not get volatility for {currency}: {e}")
                    continue

            await self.sensors_manager._update_sensor_state("market_volatility", str(len(volatility_data)))
            await self.sensors_manager._update_sensor_attributes("market_volatility", volatility_data)

        except Exception as e:
            logger.error(f"Error updating volatility sensor: {e}")

    async def _update_market_sentiment(self, currencies: list[str]) -> None:
        """Update consolidated market sentiment sensor."""
        try:
            sentiment_data = {}

            for currency in currencies:
                try:
                    base_symbol = currency.split("/")[0] if "/" in currency else currency
                    sentiment = await self._get_market_sentiment(currency)
                    if sentiment is not None:
                        sentiment_data[base_symbol] = sentiment

                except Exception as e:
                    logger.debug(f"Could not get sentiment for {currency}: {e}")
                    continue

            await self.sensors_manager._update_sensor_state("market_sentiment", str(len(sentiment_data)))
            await self.sensors_manager._update_sensor_attributes("market_sentiment", sentiment_data)

        except Exception as e:
            logger.error(f"Error updating market sentiment sensor: {e}")

    async def _get_price_prediction(self, currency: str) -> float | None:
        """Get price prediction for a currency (placeholder implementation)."""
        # This would integrate with actual prediction services
        # For now, return placeholder data
        try:
            # In real implementation, this would call prediction services
            # return await prediction_service.get_latest_prediction(currency)
            return None  # Placeholder
        except Exception:
            return None

    async def _get_ai_trend(self, currency: str) -> str | None:
        """Get AI trend for a currency (placeholder implementation)."""
        # This would integrate with actual AI trend analysis
        # For now, return placeholder data
        try:
            # In real implementation, this would call trend analysis services
            # return await trend_service.get_latest_trend(currency)
            return None  # Placeholder
        except Exception:
            return None

    async def _get_technical_indicators(self, currency: str) -> dict[str, Any] | None:
        """Get technical indicators for a currency (placeholder implementation)."""
        # This would integrate with actual technical analysis
        # For now, return placeholder data
        try:
            # In real implementation, this would call technical analysis services
            # return await technical_service.get_indicators(currency)
            return None  # Placeholder
        except Exception:
            return None

    async def _get_volatility(self, currency: str) -> float | None:
        """Get volatility for a currency (placeholder implementation)."""
        # This would integrate with actual volatility calculation
        # For now, return placeholder data
        try:
            # In real implementation, this would calculate volatility from price data
            # return await volatility_service.calculate(currency)
            return None  # Placeholder
        except Exception:
            return None

    async def _get_market_sentiment(self, currency: str) -> float | None:
        """Get market sentiment for a currency (placeholder implementation)."""
        # This would integrate with actual sentiment analysis
        # For now, return placeholder data
        try:
            # In real implementation, this would analyze market sentiment
            # return await sentiment_service.analyze(currency)
            return None  # Placeholder
        except Exception:
            return None

    def is_initialized(self) -> bool:
        """Check if consolidated sensors have been created."""
        return self._consolidated_sensors_created


# Global instance management
_unified_sensor_manager = None


def get_unified_sensor_manager(sensors_manager: CryptoSensorsManager = None) -> UnifiedSensorManager:
    """Get singleton unified sensor manager instance."""
    global _unified_sensor_manager
    if _unified_sensor_manager is None:
        if sensors_manager is None:
            raise ValueError("sensors_manager required for first initialization")
        _unified_sensor_manager = UnifiedSensorManager(sensors_manager)
    return _unified_sensor_manager
