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

    # CoinGecko ID mapping
    COINGECKO_IDS = {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "SOL": "solana",
        "TON": "the-open-network",
        "AR": "arweave",
        "RENDER": "render-token",
        "TAO": "bittensor",
        "FET": "fetch-ai",
        "NEAR": "near",
        "INJ": "injective-protocol",
    }

    def __init__(self, sensors_manager: HAIntegrationManager):
        self.sensors_manager = sensors_manager
        self._consolidated_sensors_created = False
        self._cache: dict[str, Any] = {}

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

            # Fetch all market data in one call
            await self._fetch_market_data(currencies)

            # Update each consolidated sensor using publish_sensor
            await self._update_price_predictions(currencies)
            await self._update_ai_trends(currencies)
            await self._update_technical_indicators(currencies)
            await self._update_volatility_data(currencies)
            await self._update_market_sentiment(currencies)

        except Exception as e:
            logger.error(f"Error updating consolidated sensors: {e}")

    async def _fetch_market_data(self, currencies: list[str]) -> None:
        """Fetch market data for all currencies from CoinGecko."""
        import httpx

        try:
            # Build list of CoinGecko IDs
            ids = []
            for currency in currencies:
                base = currency.split("/")[0] if "/" in currency else currency
                cg_id = self.COINGECKO_IDS.get(base, base.lower())
                ids.append(cg_id)

            ids_str = ",".join(ids)
            url = f"https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids={ids_str}&order=market_cap_desc&sparkline=false&price_change_percentage=24h"

            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    
                    # Build cache with data by symbol
                    for coin in data:
                        symbol = coin.get("symbol", "").upper()
                        self._cache[symbol] = {
                            "price": coin.get("current_price"),
                            "high_24h": coin.get("high_24h"),
                            "low_24h": coin.get("low_24h"),
                            "volume_24h": coin.get("total_volume"),
                            "change_24h": coin.get("price_change_percentage_24h"),
                            "market_cap": coin.get("market_cap"),
                            "ath": coin.get("ath"),
                            "ath_change_pct": coin.get("ath_change_percentage"),
                        }
                    logger.debug(f"Fetched market data for {len(data)} coins")
                else:
                    logger.warning(f"CoinGecko API returned {resp.status_code}")

        except Exception as e:
            logger.warning(f"Failed to fetch market data: {e}")

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
        """Get price prediction for a currency."""
        # This requires ML/AI backend - return None if not available
        # In future: integrate with ML prediction service
        return None

    async def _get_ai_trend(self, currency: str) -> str | None:
        """Get AI trend for a currency."""
        # Calculate trend from price change
        base = currency.split("/")[0] if "/" in currency else currency
        data = self._cache.get(base)
        if not data:
            return None

        change = data.get("change_24h")
        if change is None:
            return None

        # Simple trend classification
        if change > 5:
            return "Strong Bullish"
        elif change > 2:
            return "Bullish"
        elif change > -2:
            return "Neutral"
        elif change > -5:
            return "Bearish"
        else:
            return "Strong Bearish"

    async def _get_technical_indicators(self, currency: str) -> dict[str, Any] | None:
        """Get technical indicators for a currency."""
        base = currency.split("/")[0] if "/" in currency else currency
        data = self._cache.get(base)
        if not data:
            return None

        price = data.get("price")
        high = data.get("high_24h")
        low = data.get("low_24h")
        ath = data.get("ath")

        if not all([price, high, low]):
            return None

        # Calculate simple indicators
        range_24h = high - low
        position_in_range = (price - low) / range_24h if range_24h > 0 else 0.5
        distance_from_ath = data.get("ath_change_pct", 0)

        return {
            "price": round(price, 2),
            "high_24h": round(high, 2),
            "low_24h": round(low, 2),
            "range_position": round(position_in_range * 100, 1),  # 0-100%
            "ath_distance": round(distance_from_ath, 1),
        }

    async def _get_volatility(self, currency: str) -> float | None:
        """Get volatility for a currency."""
        base = currency.split("/")[0] if "/" in currency else currency
        data = self._cache.get(base)
        if not data:
            return None

        high = data.get("high_24h")
        low = data.get("low_24h")
        price = data.get("price")

        if not all([high, low, price]) or price == 0:
            return None

        # 24h volatility as % of price
        volatility = ((high - low) / price) * 100
        return round(volatility, 2)

    async def _get_market_sentiment(self, currency: str) -> str | None:
        """Get market sentiment for a currency."""
        base = currency.split("/")[0] if "/" in currency else currency
        data = self._cache.get(base)
        if not data:
            return None

        change = data.get("change_24h")
        ath_dist = data.get("ath_change_pct", -50)

        if change is None:
            return None

        # Composite sentiment from change and ATH distance
        if change > 3 and ath_dist > -20:
            return "Greedy"
        elif change > 0:
            return "Optimistic"
        elif change > -3:
            return "Cautious"
        else:
            return "Fearful"

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
