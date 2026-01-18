"""
Home Assistant Sensors for Lazy Investor ML System

Creates MQTT sensors that publish ML insights to Home Assistant
for passive investor monitoring and automation.
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class MLSensorData:
    """Data structure for ML sensor information."""

    name: str
    state: str
    attributes: dict
    device_class: str | None = None
    unit_of_measurement: str | None = None


class HALazyInvestorSensors:
    """Manages Home Assistant sensors for lazy investor ML insights."""

    def __init__(self):
        self.mqtt_client = None
        self.base_topic = "homeassistant/sensor/crypto_inspect"
        self.device_info = {
            "identifiers": ["crypto_inspect_ml"],
            "name": "Crypto Inspect ML Investor",
            "manufacturer": "Crypto Inspect",
            "model": "Lazy Investor v1.0",
            "sw_version": "1.0.0",
        }

    async def initialize_mqtt(self):
        """Initialize MQTT client for HA communication."""
        try:
            import aiomqtt

            # Connect to MQTT broker (typically HA Mosquitto addon)
            self.mqtt_client = aiomqtt.Client(
                hostname="localhost",
                port=1883,
                username="mqtt_user",  # Would come from config
                password="mqtt_password",
            )

            await self.mqtt_client.connect()
            logger.info("MQTT client connected for HA sensors")

        except ImportError:
            logger.warning("aiomqtt not available, using mock MQTT")
            self.mqtt_client = MockMQTTClient()
        except Exception as e:
            logger.error(f"MQTT initialization failed: {e}")
            self.mqtt_client = MockMQTTClient()

    async def create_investment_sensors(self) -> list[MLSensorData]:
        """Create all ML investment sensors for Home Assistant."""

        sensors = []

        # Portfolio Health Sensor
        portfolio_health = MLSensorData(
            name="ml_portfolio_health",
            state="neutral",
            attributes={
                "friendly_name": "ML Portfolio Health",
                "sentiment": "neutral",
                "opportunity_signals": 0,
                "risk_signals": 0,
                "hold_signals": 0,
                "total_analyzed": 0,
                "recommendation": "Maintain current positions",
                "last_updated": datetime.now().isoformat(),
            },
            device_class=None,
        )
        sensors.append(portfolio_health)

        # Market Confidence Sensor
        market_confidence = MLSensorData(
            name="ml_market_confidence",
            state="medium",
            attributes={
                "friendly_name": "ML Market Confidence",
                "level": "medium",
                "high_confidence_signals": 0,
                "medium_confidence_signals": 0,
                "low_confidence_signals": 0,
                "confidence_threshold": 70,
                "last_updated": datetime.now().isoformat(),
            },
            device_class=None,
        )
        sensors.append(market_confidence)

        # Investment Opportunity Sensor
        investment_opportunity = MLSensorData(
            name="ml_investment_opportunity",
            state="none",
            attributes={
                "friendly_name": "ML Investment Opportunity",
                "status": "none",
                "symbols_with_opportunities": [],
                "confidence_levels": {},
                "action_required": False,
                "last_updated": datetime.now().isoformat(),
            },
            device_class=None,
        )
        sensors.append(investment_opportunity)

        # Risk Warning Sensor
        risk_warning = MLSensorData(
            name="ml_risk_warning",
            state="clear",
            attributes={
                "friendly_name": "ML Risk Warning",
                "level": "clear",
                "symbols_with_risks": [],
                "risk_factors": [],
                "action_required": False,
                "last_updated": datetime.now().isoformat(),
            },
            device_class="problem",  # HA problem device class
        )
        sensors.append(risk_warning)

        # ML System Status Sensor
        system_status = MLSensorData(
            name="ml_system_status",
            state="operational",
            attributes={
                "friendly_name": "ML System Status",
                "status": "operational",
                "models_analyzed": 12,
                "average_accuracy": "50%",
                "last_analysis": datetime.now().isoformat(),
                "next_analysis": (datetime.now().replace(hour=23, minute=0, second=0)).isoformat(),
            },
            device_class="connectivity",
        )
        sensors.append(system_status)

        return sensors

    async def publish_sensor_discovery(self, sensor: MLSensorData):
        """Publish MQTT discovery message for HA sensor."""

        discovery_topic = f"{self.base_topic}/{sensor.name}/config"

        discovery_payload = {
            "name": sensor.attributes.get("friendly_name", sensor.name),
            "unique_id": f"crypto_inspect_{sensor.name}",
            "state_topic": f"{self.base_topic}/{sensor.name}/state",
            "json_attributes_topic": f"{self.base_topic}/{sensor.name}/attributes",
            "device": self.device_info,
        }

        # Add optional fields if present
        if sensor.device_class:
            discovery_payload["device_class"] = sensor.device_class

        if sensor.unit_of_measurement:
            discovery_payload["unit_of_measurement"] = sensor.unit_of_measurement

        # Publish discovery message
        if self.mqtt_client:
            try:
                await self.mqtt_client.publish(discovery_topic, json.dumps(discovery_payload), qos=1, retain=True)
                logger.info(f"Published discovery for sensor: {sensor.name}")
            except Exception as e:
                logger.error(f"Failed to publish discovery for {sensor.name}: {e}")

    async def update_sensor_state(self, sensor: MLSensorData):
        """Update sensor state and attributes."""

        state_topic = f"{self.base_topic}/{sensor.name}/state"
        attributes_topic = f"{self.base_topic}/{sensor.name}/attributes"

        if self.mqtt_client:
            try:
                # Publish state
                await self.mqtt_client.publish(state_topic, sensor.state, qos=1, retain=True)

                # Publish attributes
                await self.mqtt_client.publish(attributes_topic, json.dumps(sensor.attributes), qos=1, retain=True)

                logger.info(f"Updated sensor {sensor.name}: {sensor.state}")

            except Exception as e:
                logger.error(f"Failed to update sensor {sensor.name}: {e}")

    async def publish_all_sensors(self):
        """Publish all ML sensors to Home Assistant."""

        await self.initialize_mqtt()

        sensors = await self.create_investment_sensors()

        # Publish discovery messages first
        for sensor in sensors:
            await self.publish_sensor_discovery(sensor)

        # Small delay to ensure discovery is processed
        await asyncio.sleep(2)

        # Update sensor states
        for sensor in sensors:
            await self.update_sensor_state(sensor)

        logger.info(f"Published {len(sensors)} ML sensors to Home Assistant")

        return sensors

    async def update_with_ml_data(self, ml_insights: dict):
        """Update sensors with actual ML analysis data."""

        # Update portfolio health sensor
        health_sensor = MLSensorData(
            name="ml_portfolio_health",
            state=ml_insights.get("portfolio_sentiment", "neutral"),
            attributes={
                "friendly_name": "ML Portfolio Health",
                "sentiment": ml_insights.get("portfolio_sentiment", "neutral"),
                "opportunity_signals": ml_insights.get("opportunity_signals", 0),
                "risk_signals": ml_insights.get("risk_signals", 0),
                "hold_signals": ml_insights.get("hold_signals", 0),
                "total_analyzed": ml_insights.get("total_analyzed", 0),
                "recommendation": ml_insights.get("recommendation", "Maintain positions"),
                "last_updated": datetime.now().isoformat(),
            },
        )

        # Update market confidence sensor
        market_confidence_sensor = MLSensorData(
            name="ml_market_confidence",
            state=self._determine_confidence_level(ml_insights),
            attributes={
                "friendly_name": "ML Market Confidence",
                "level": self._determine_confidence_level(ml_insights),
                "high_confidence_signals": ml_insights.get("high_confidence_count", 0),
                "medium_confidence_signals": ml_insights.get("medium_confidence_count", 0),
                "low_confidence_signals": ml_insights.get("low_confidence_count", 0),
                "confidence_threshold": 70,
                "last_updated": datetime.now().isoformat(),
            },
        )

        # Update sensors
        await self.update_sensor_state(health_sensor)
        await self.update_sensor_state(market_confidence_sensor)

        logger.info("ML sensors updated with real analysis data")

    def _determine_confidence_level(self, insights: dict) -> str:
        """Determine overall confidence level from ML insights."""
        high_conf = insights.get("high_confidence_count", 0)
        med_conf = insights.get("medium_confidence_count", 0)
        total = insights.get("total_signals", 1)

        high_ratio = high_conf / total
        med_ratio = (high_conf + med_conf) / total

        if high_ratio > 0.5:
            return "high"
        elif med_ratio > 0.7:
            return "medium"
        else:
            return "low"


class MockMQTTClient:
    """Mock MQTT client for testing purposes."""

    async def connect(self):
        logger.info("Mock MQTT client connected")

    async def publish(self, topic: str, payload: str, qos: int = 0, retain: bool = False):
        logger.info(f"Mock publish to {topic}: {payload[:100]}...")

    async def disconnect(self):
        logger.info("Mock MQTT client disconnected")


# Example usage and testing
async def demo_ha_sensors():
    """Demonstrate HA sensor functionality."""

    print("🏠 HOME ASSISTANT ML SENSORS DEMO")
    print("=" * 50)

    # Create sensor manager
    sensor_manager = HALazyInvestorSensors()

    # Publish all sensors
    sensors = await sensor_manager.publish_all_sensors()

    print(f"✅ Published {len(sensors)} sensors:")
    for sensor in sensors:
        print(f"  • {sensor.attributes['friendly_name']} ({sensor.name})")

    # Simulate ML data update
    mock_ml_data = {
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

    await sensor_manager.update_with_ml_data(mock_ml_data)

    print("\n📊 Sensors updated with mock ML data")
    print("🎯 Ready for Home Assistant integration!")


if __name__ == "__main__":
    asyncio.run(demo_ha_sensors())
