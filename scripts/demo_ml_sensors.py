#!/usr/bin/env python3
"""
Demo Script for ML Investor Sensors in Home Assistant

Shows how to use the newly integrated ML sensors with real data.
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.ha_sensors import get_sensors_manager


async def demo_ml_sensors():
    """Demonstrate ML investor sensors functionality."""

    print("🤖 ML INVESTOR SENSORS DEMO")
    print("=" * 50)

    # Create sensor manager with mock MQTT (for demo)
    sensor_manager = get_sensors_manager(mqtt_client=None)

    # Sample ML analysis data (simulating real ML output)
    sample_ml_data = {
        # Portfolio Health Section
        "portfolio_sentiment": "bullish",
        "opportunity_signals": 4,
        "risk_signals": 2,
        "hold_signals": 6,
        "total_analyzed": 12,
        "recommendation": "Consider gradual accumulation of strong projects",
        "recommendation_ru": "Рассмотрите постепенное накопление сильных проектов",
        "last_analysis": datetime.now().isoformat(),
        "confidence_threshold": 70,
        # Market Confidence Section
        "confidence_level": "high",
        "high_confidence_count": 6,
        "medium_confidence_count": 4,
        "low_confidence_count": 2,
        "high_confidence_symbols": ["BTC/USDT", "ETH/USDT", "SOL/USDT", "ADA/USDT"],
        "action_required": True,
        # Investment Opportunity Section
        "opportunity_status": "moderate",
        "opportunity_symbols": ["SOL/USDT", "ADA/USDT", "DOT/USDT"],
        "best_opportunity": "SOL/USDT",
        "recommended_allocation": 15,
        "opportunity_timeframe": "medium_term",
        "opportunity_risk": "medium",
        # Risk Warning Section
        "risk_level": "warning",
        "risk_symbols": ["BTC/USDT", "ETH/USDT"],
        "risk_factors": ["high_volatility", "market_correction_risk", "macro_uncertainty"],
        "risk_action_required": True,
        "protective_measures": ["review_stop_losses", "diversify_portfolio", "reduce_leverage"],
        "stop_loss_recommendation": "Consider tightening stop-loss levels by 2-3%",
        # System Status Section
        "system_status": "operational",
        "models_analyzed": 12,
        "average_accuracy": "50%",
        "next_analysis": (datetime.now().replace(hour=23, minute=0, second=0)).isoformat(),
        "processing_time": "<5s",
        "data_quality": "good",
    }

    print("📊 SAMPLE ML DATA:")
    print(f"  Portfolio Sentiment: {sample_ml_data['portfolio_sentiment']}")
    print(f"  Opportunities Found: {sample_ml_data['opportunity_signals']}")
    print(f"  Risk Signals: {sample_ml_data['risk_signals']}")
    print(f"  Confidence Level: {sample_ml_data['confidence_level']}")
    print(f"  Action Required: {sample_ml_data['action_required']}")
    print()

    # Update sensors (this would normally publish to MQTT)
    print("📡 UPDATING ML SENSORS:")
    try:
        await sensor_manager.update_ml_investor_sensors(sample_ml_data)
        print("  ✅ ML sensors updated successfully")
    except Exception as e:
        print(f"  ❌ Error updating sensors: {e}")
        return

    # Show what sensors would be created
    print("\n🏠 HOME ASSISTANT SENSORS CREATED:")
    sensors_info = [
        {
            "name": "sensor.ml_portfolio_health",
            "state": sample_ml_data["portfolio_sentiment"],
            "description": "Overall portfolio sentiment from ML analysis",
        },
        {
            "name": "sensor.ml_market_confidence",
            "state": sample_ml_data["confidence_level"],
            "description": "Market confidence level based on ML predictions",
        },
        {
            "name": "sensor.ml_investment_opportunity",
            "state": sample_ml_data["opportunity_status"],
            "description": "Investment opportunities detected by ML",
        },
        {
            "name": "sensor.ml_risk_warning",
            "state": sample_ml_data["risk_level"],
            "description": "Risk warnings from ML analysis",
        },
        {
            "name": "sensor.ml_system_status",
            "state": sample_ml_data["system_status"],
            "description": "ML system operational status",
        },
    ]

    for sensor in sensors_info:
        print(f"  • {sensor['name']}: {sensor['state']}")
        print(f"    {sensor['description']}")

    # Show example HA automation triggers
    print("\n⚡ HOME ASSISTANT AUTOMATION EXAMPLES:")

    print("""
# Automation: Send notification when high-confidence opportunities arise
automation:
  - alias: "ML High Confidence Opportunity Alert"
    trigger:
      - platform: state
        entity_id: sensor.ml_market_confidence
        to: "high"
      - platform: numeric_state
        entity_id: sensor.ml_portfolio_health.opportunity_signals
        above: 3
    condition:
      - condition: state
        entity_id: sensor.ml_system_status
        state: "operational"
    action:
      - service: notify.mobile_app
        data:
          message: "📈 ML detected high-confidence investment opportunities!"
          data:
            actions:
              - action: "VIEW_DETAILS"
                title: "View Details"
""")

    print("""
# Automation: Risk management alert
automation:
  - alias: "ML Risk Warning Alert"
    trigger:
      - platform: state
        entity_id: sensor.ml_risk_warning
        to: "warning"
    action:
      - service: notify.mobile_app
        data:
          message: "⚠️ ML detected potential risks in your portfolio"
          data:
            actions:
              - action: "REVIEW_POSITIONS"
                title: "Review Positions"
""")

    # Save sample data for reference
    sample_file = Path("ml_sensor_sample_data.json")
    with open(sample_file, "w") as f:
        json.dump(sample_ml_data, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Sample data saved to: {sample_file}")
    print("\n🎯 ML SENSORS DEMO COMPLETE!")
    print("🚀 Ready for Home Assistant integration!")


def show_ha_configuration():
    """Show Home Assistant configuration example."""

    print("\n🏠 HOME ASSISTANT CONFIGURATION:")
    print("=" * 40)

    config_example = """
# Add to your Home Assistant configuration.yaml

# MQTT Broker Configuration (if not already configured)
mqtt:
  broker: localhost
  port: 1883
  username: !secret mqtt_username
  password: !secret mqtt_password

# MQTT Discovery is enabled by default
# The sensors will auto-discover when published

# Example Lovelace Dashboard Cards:

# Portfolio Health Card
type: entities
title: ML Portfolio Insights
entities:
  - entity: sensor.ml_portfolio_health
    name: Portfolio Sentiment
  - entity: sensor.ml_market_confidence
    name: Market Confidence
  - entity: sensor.ml_investment_opportunity
    name: Opportunities
  - entity: sensor.ml_risk_warning
    name: Risk Level
  - entity: sensor.ml_system_status
    name: ML System

# Conditional Card based on ML signals
type: conditional
conditions:
  - entity: sensor.ml_market_confidence
    state: "high"
card:
  type: markdown
  content: >
    **🚀 High Confidence Market Conditions Detected!**
    Consider reviewing your investment strategy.
"""

    print(config_example)


if __name__ == "__main__":
    print("Starting ML Investor Sensors Demo...\n")

    # Run demo
    asyncio.run(demo_ml_sensors())

    # Show configuration
    show_ha_configuration()

    print("\n✨ DEMO COMPLETE!")
    print("The ML sensors are now integrated into your Home Assistant system.")
