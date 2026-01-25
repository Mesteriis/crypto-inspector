"""
Unified Sensor Consolidation Service.

Replaces individual currency-specific sensors with consolidated dictionary format sensors.
"""

import logging
from typing import Any

from service.ha import HAIntegrationManager, get_currency_list

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

    # These sensors are already registered in SensorRegistry via category modules
    CONSOLIDATED_SENSORS = [
        "price_predictions",
        "ai_trend_directions", 
        "technical_indicators",
        "market_volatility",
        "market_sentiment",
    ]

    def __init__(self, sensors_manager: HAIntegrationManager):
        self.sensors_manager = sensors_manager
        self._consolidated_sensors_created = False

    async def create_consolidated_sensors(self) -> None:
        """Mark consolidated sensors as ready.
        
        Note: Actual sensor registration happens via SensorRegistry during startup.
        This method just marks them as initialized.
        """
        if self._consolidated_sensors_created:
            logger.debug("Consolidated sensors already created")
            return

        try:
            logger.info("Creating consolidated dictionary format sensors")
            # Sensors are pre-registered via @register_sensor decorator
            # Just mark as created
            self._consolidated_sensors_created = True
            logger.info("Consolidated sensors created successfully")

        except Exception as e:
            logger.error(f"Error creating consolidated sensors: {e}")

    async def update_consolidated_sensors(self) -> None:
        """Update all consolidated sensors with current data."""
        if not self._consolidated_sensors_created:
            await self.create_consolidated_sensors()

        try:
            # get_currency_list is synchronous
            currencies = get_currency_list()
            logger.debug(f"Updating consolidated sensors for {len(currencies)} currencies")

            # Update each consolidated sensor using publish_sensor
            await self._update_price_predictions(currencies)
            await self._update_ai_trends(currencies)
            await self._update_technical_indicators(currencies)
            await self._update_volatility_data(currencies)
            await self._update_market_sentiment(currencies)

        except Exception as e:
            logger.error(f"Error updating consolidated sensors: {e}")

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

            # Update sensor using publish_sensor
            await self.sensors_manager.publish_sensor(
                "price_predictions", 
                predictions_data
            )

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

            await self.sensors_manager.publish_sensor(
                "ai_trend_directions",
                trends_data
            )

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

            await self.sensors_manager.publish_sensor(
                "technical_indicators",
                tech_data
            )

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

            await self.sensors_manager.publish_sensor(
                "market_volatility",
                volatility_data
            )

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

            await self.sensors_manager.publish_sensor(
                "market_sentiment",
                sentiment_data
            )

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
        except Exception:  # pragma: no cover
            return None

    async def _get_ai_trend(self, currency: str) -> str | None:
        """Get AI trend for a currency (placeholder implementation)."""
        # This would integrate with actual AI trend analysis
        # For now, return placeholder data
        try:
            # In real implementation, this would call trend analysis services
            # return await trend_service.get_latest_trend(currency)
            return None  # Placeholder
        except Exception:  # pragma: no cover
            return None

    async def _get_technical_indicators(self, currency: str) -> dict[str, Any] | None:
        """Get technical indicators for a currency (placeholder implementation)."""
        # This would integrate with actual technical analysis
        # For now, return placeholder data
        try:
            # In real implementation, this would call technical analysis services
            # return await technical_service.get_indicators(currency)
            return None  # Placeholder
        except Exception:  # pragma: no cover
            return None

    async def _get_volatility(self, currency: str) -> float | None:
        """Get volatility for a currency (placeholder implementation)."""
        # This would integrate with actual volatility calculation
        # For now, return placeholder data
        try:
            # In real implementation, this would calculate volatility from price data
            # return await volatility_service.calculate(currency)
            return None  # Placeholder
        except Exception:  # pragma: no cover
            return None

    async def _get_market_sentiment(self, currency: str) -> float | None:
        """Get market sentiment for a currency (placeholder implementation)."""
        # This would integrate with actual sentiment analysis
        # For now, return placeholder data
        try:
            # In real implementation, this would analyze market sentiment
            # return await sentiment_service.analyze(currency)
            return None  # Placeholder
        except Exception:  # pragma: no cover
            return None

    def is_initialized(self) -> bool:
        """Check if consolidated sensors have been created."""
        return self._consolidated_sensors_created


# Global instance management
_unified_sensor_manager = None


def get_unified_sensor_manager(sensors_manager: HAIntegrationManager = None) -> UnifiedSensorManager:
    """Get singleton unified sensor manager instance."""
    global _unified_sensor_manager
    if _unified_sensor_manager is None:
        if sensors_manager is None:
            raise ValueError("sensors_manager required for first initialization")
        _unified_sensor_manager = UnifiedSensorManager(sensors_manager)
    return _unified_sensor_manager
