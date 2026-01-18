"""Crypto sensors for Home Assistant MQTT Discovery.

This module registers crypto-related sensors that Home Assistant
will automatically discover when the add-on starts.

Sensors use dictionary format to support multiple trading pairs:
- sensor.crypto_inspect_prices: {"BTC/USDT": 100000, "ETH/USDT": 3500}
- sensor.crypto_inspect_changes: {"BTC/USDT": 2.5, "ETH/USDT": -1.2}
"""

import json
import logging
import os
from datetime import UTC, datetime
from decimal import Decimal

logger = logging.getLogger(__name__)


def get_symbols() -> list[str]:
    """Get trading symbols from environment."""
    symbols_env = os.environ.get("HA_SYMBOLS", "BTC/USDT,ETH/USDT")
    return [s.strip() for s in symbols_env.split(",") if s.strip()]


class CryptoSensorsManager:
    """
    Manages crypto sensors for Home Assistant.

    Creates aggregated sensors that contain data for all trading pairs
    in dictionary format, making it easy to use in HA templates.
    """

    DEVICE_ID = "crypto_inspect"
    DEVICE_NAME = "Crypto Inspect"

    # Sensor definitions
    SENSORS = {
        # === Price Sensors ===
        "prices": {
            "name": "Crypto Prices",
            "icon": "mdi:currency-usd",
            "unit": "USDT",
        },
        "changes_24h": {
            "name": "Crypto 24h Changes",
            "icon": "mdi:percent",
            "unit": "%",
        },
        "volumes_24h": {
            "name": "Crypto 24h Volumes",
            "icon": "mdi:chart-bar",
            "unit": "USDT",
        },
        "highs_24h": {
            "name": "Crypto 24h Highs",
            "icon": "mdi:arrow-up-bold",
            "unit": "USDT",
        },
        "lows_24h": {
            "name": "Crypto 24h Lows",
            "icon": "mdi:arrow-down-bold",
            "unit": "USDT",
        },
        # === Investor Sensors (Lazy Investor) ===
        "do_nothing_ok": {
            "name": "Do Nothing OK",
            "icon": "mdi:meditation",
        },
        "investor_phase": {
            "name": "Investor Phase",
            "icon": "mdi:chart-timeline-variant-shimmer",
        },
        "calm_indicator": {
            "name": "Calm Indicator",
            "icon": "mdi:emoticon-cool",
        },
        "red_flags": {
            "name": "Red Flags",
            "icon": "mdi:flag-variant",
        },
        "market_tension": {
            "name": "Market Tension",
            "icon": "mdi:gauge",
        },
        "price_context": {
            "name": "Price Context",
            "icon": "mdi:chart-box",
        },
        "dca_result": {
            "name": "DCA Result",
            "icon": "mdi:cash-check",
            "unit": "€",
        },
        "dca_signal": {
            "name": "DCA Signal",
            "icon": "mdi:cash-plus",
        },
        "weekly_insight": {
            "name": "Weekly Insight",
            "icon": "mdi:newspaper-variant",
        },
        "next_action_timer": {
            "name": "Next Action Timer",
            "icon": "mdi:timer-outline",
        },
        # === Market Sensors ===
        "fear_greed": {
            "name": "Fear & Greed Index",
            "icon": "mdi:emoticon-neutral",
        },
        "btc_dominance": {
            "name": "BTC Dominance",
            "icon": "mdi:crown",
            "unit": "%",
        },
        "derivatives": {
            "name": "Derivatives",
            "icon": "mdi:chart-timeline-variant",
        },
        # === Altseason & Stablecoins ===
        "altseason_index": {
            "name": "Altseason Index",
            "icon": "mdi:rocket-launch",
        },
        "altseason_status": {
            "name": "Altseason Status",
            "icon": "mdi:weather-sunny",
        },
        "stablecoin_total": {
            "name": "Stablecoin Total",
            "icon": "mdi:currency-usd-circle",
        },
        "stablecoin_flow": {
            "name": "Stablecoin Flow",
            "icon": "mdi:swap-horizontal",
        },
        "stablecoin_dominance": {
            "name": "Stablecoin Dominance",
            "icon": "mdi:chart-pie",
            "unit": "%",
        },
        # === Gas Tracker ===
        "eth_gas_slow": {
            "name": "ETH Gas Slow",
            "icon": "mdi:speedometer-slow",
            "unit": "Gwei",
        },
        "eth_gas_standard": {
            "name": "ETH Gas Standard",
            "icon": "mdi:speedometer-medium",
            "unit": "Gwei",
        },
        "eth_gas_fast": {
            "name": "ETH Gas Fast",
            "icon": "mdi:speedometer",
            "unit": "Gwei",
        },
        "eth_gas_status": {
            "name": "ETH Gas Status",
            "icon": "mdi:gas-station",
        },
        # === Whale Activity ===
        "whale_alerts_24h": {
            "name": "Whale Alerts 24h",
            "icon": "mdi:fish",
        },
        "whale_net_flow": {
            "name": "Whale Net Flow",
            "icon": "mdi:arrow-decision",
        },
        "whale_last_alert": {
            "name": "Whale Last Alert",
            "icon": "mdi:bell-ring",
        },
        # === Exchange Flow (Generic - Dictionary Format) ===
        "exchange_netflows": {
            "name": "Exchange Netflows",
            "icon": "mdi:bank-transfer",
        },
        "exchange_flow_signal": {
            "name": "Exchange Flow Signal",
            "icon": "mdi:trending-up",
        },
        # === Liquidations (Generic - Dictionary Format) ===
        "liq_levels": {
            "name": "Liquidation Levels",
            "icon": "mdi:arrow-expand-vertical",
        },
        "liq_risk_level": {
            "name": "Liquidation Risk",
            "icon": "mdi:alert-decagram",
        },
        # === Portfolio ===
        "portfolio_value": {
            "name": "Portfolio Value",
            "icon": "mdi:wallet",
            "unit": "USDT",
        },
        "portfolio_pnl": {
            "name": "Portfolio P&L",
            "icon": "mdi:chart-line",
            "unit": "%",
        },
        "portfolio_pnl_24h": {
            "name": "Portfolio 24h Change",
            "icon": "mdi:chart-areaspline",
            "unit": "%",
        },
        "portfolio_allocation": {
            "name": "Portfolio Allocation",
            "icon": "mdi:chart-donut",
        },
        # === Alerts ===
        "active_alerts_count": {
            "name": "Active Alerts",
            "icon": "mdi:bell-badge",
        },
        "triggered_alerts_24h": {
            "name": "Triggered Alerts 24h",
            "icon": "mdi:bell-check",
        },
        # === Divergences (Generic - Dictionary Format) ===
        "divergences": {
            "name": "Divergences",
            "icon": "mdi:call-split",
        },
        "divergences_active": {
            "name": "Active Divergences",
            "icon": "mdi:call-merge",
        },
        # === Signals ===
        "signals_win_rate": {
            "name": "Signals Win Rate",
            "icon": "mdi:trophy",
            "unit": "%",
        },
        "signals_today": {
            "name": "Signals Today",
            "icon": "mdi:signal",
        },
        "signals_last": {
            "name": "Last Signal",
            "icon": "mdi:traffic-light",
        },
        # === Bybit Exchange ===
        "bybit_balance": {
            "name": "Bybit Balance",
            "icon": "mdi:wallet",
            "unit": "USDT",
        },
        "bybit_pnl_24h": {
            "name": "Bybit P&L 24h",
            "icon": "mdi:chart-line",
            "unit": "%",
        },
        "bybit_pnl_7d": {
            "name": "Bybit P&L 7d",
            "icon": "mdi:chart-areaspline",
            "unit": "%",
        },
        "bybit_positions": {
            "name": "Bybit Positions",
            "icon": "mdi:format-list-bulleted",
        },
        "bybit_unrealized_pnl": {
            "name": "Bybit Unrealized P&L",
            "icon": "mdi:cash-clock",
            "unit": "USDT",
        },
        # === Bybit Earn ===
        "bybit_earn_balance": {
            "name": "Bybit Earn Balance",
            "icon": "mdi:piggy-bank",
            "unit": "USDT",
        },
        "bybit_earn_positions": {
            "name": "Bybit Earn Positions",
            "icon": "mdi:format-list-bulleted",
        },
        "bybit_earn_apy": {
            "name": "Bybit Earn APY",
            "icon": "mdi:percent",
            "unit": "%",
        },
        "bybit_total_portfolio": {
            "name": "Bybit Total Portfolio",
            "icon": "mdi:bank",
            "unit": "USDT",
        },
        # === DCA Calculator ===
        "dca_next_level": {
            "name": "DCA Next Level",
            "icon": "mdi:target",
            "unit": "USDT",
        },
        "dca_zone": {
            "name": "DCA Zone",
            "icon": "mdi:map-marker-radius",
        },
        "dca_risk_score": {
            "name": "DCA Risk Score",
            "icon": "mdi:gauge",
        },
        # === Correlation ===
        "btc_eth_correlation": {
            "name": "BTC/ETH Correlation",
            "icon": "mdi:link-variant",
        },
        "btc_sp500_correlation": {
            "name": "BTC/S&P500 Correlation",
            "icon": "mdi:chart-line-variant",
        },
        "correlation_status": {
            "name": "Correlation Status",
            "icon": "mdi:connection",
        },
        # === Volatility (Generic - Dictionary Format) ===
        "volatility_30d": {
            "name": "Volatility 30d",
            "icon": "mdi:chart-bell-curve",
        },
        "volatility_percentile": {
            "name": "Volatility Percentile",
            "icon": "mdi:percent-box",
        },
        "volatility_status": {
            "name": "Volatility Status",
            "icon": "mdi:pulse",
        },
        # === Token Unlocks ===
        "unlocks_next_7d": {
            "name": "Token Unlocks 7d",
            "icon": "mdi:lock-open-variant",
        },
        "unlock_next_event": {
            "name": "Next Unlock",
            "icon": "mdi:calendar-lock",
        },
        "unlock_risk_level": {
            "name": "Unlock Risk",
            "icon": "mdi:alert-circle",
        },
        # === Macro Calendar ===
        "next_macro_event": {
            "name": "Next Macro Event",
            "icon": "mdi:calendar-star",
        },
        "days_to_fomc": {
            "name": "Days to FOMC",
            "icon": "mdi:calendar-clock",
        },
        "macro_risk_week": {
            "name": "Macro Risk Week",
            "icon": "mdi:calendar-alert",
        },
        # === Arbitrage (Generic - Dictionary Format) ===
        "arb_spreads": {
            "name": "Arb Spreads",
            "icon": "mdi:swap-horizontal-bold",
        },
        "funding_arb_best": {
            "name": "Best Funding Arb",
            "icon": "mdi:cash-multiple",
        },
        "arb_opportunity": {
            "name": "Arb Opportunity",
            "icon": "mdi:lightning-bolt",
        },
        # === Profit Taking (Generic - Dictionary Format) ===
        "tp_levels": {
            "name": "Take Profit Levels",
            "icon": "mdi:target-variant",
        },
        "profit_action": {
            "name": "Profit Action",
            "icon": "mdi:cash-check",
        },
        "greed_level": {
            "name": "Greed Level",
            "icon": "mdi:emoticon-devil",
        },
        # === Traditional Finance ===
        "gold_price": {
            "name": "Gold Price",
            "icon": "mdi:gold",
            "unit": "USD",
        },
        "silver_price": {
            "name": "Silver Price",
            "icon": "mdi:circle-outline",
            "unit": "USD",
        },
        "platinum_price": {
            "name": "Platinum Price",
            "icon": "mdi:diamond-stone",
            "unit": "USD",
        },
        "sp500_price": {
            "name": "S&P 500",
            "icon": "mdi:chart-line",
            "unit": "USD",
        },
        "nasdaq_price": {
            "name": "NASDAQ",
            "icon": "mdi:chart-areaspline",
            "unit": "USD",
        },
        "dji_price": {
            "name": "Dow Jones",
            "icon": "mdi:chart-bar",
            "unit": "USD",
        },
        "dax_price": {
            "name": "DAX",
            "icon": "mdi:chart-timeline-variant",
            "unit": "EUR",
        },
        "eur_usd": {
            "name": "EUR/USD",
            "icon": "mdi:currency-eur",
        },
        "gbp_usd": {
            "name": "GBP/USD",
            "icon": "mdi:currency-gbp",
        },
        "dxy_index": {
            "name": "Dollar Index",
            "icon": "mdi:currency-usd",
        },
        "oil_brent": {
            "name": "Brent Oil",
            "icon": "mdi:barrel",
            "unit": "USD",
        },
        "oil_wti": {
            "name": "WTI Oil",
            "icon": "mdi:barrel",
            "unit": "USD",
        },
        "natural_gas": {
            "name": "Natural Gas",
            "icon": "mdi:fire",
            "unit": "USD",
        },
        # === AI Analysis ===
        "ai_daily_summary": {
            "name": "AI Daily Summary",
            "icon": "mdi:robot",
        },
        "ai_market_sentiment": {
            "name": "AI Market Sentiment",
            "icon": "mdi:brain",
        },
        "ai_recommendation": {
            "name": "AI Recommendation",
            "icon": "mdi:lightbulb",
        },
        "ai_last_analysis": {
            "name": "AI Last Analysis",
            "icon": "mdi:clock-outline",
        },
        "ai_provider": {
            "name": "AI Provider",
            "icon": "mdi:cog",
            "entity_category": "diagnostic",
        },
        # === Technical Indicators (Generic - Dictionary Format) ===
        "ta_rsi": {
            "name": "RSI Values",
            "icon": "mdi:chart-line",
        },
        "ta_macd_signal": {
            "name": "MACD Signals",
            "icon": "mdi:signal",
        },
        "ta_bb_position": {
            "name": "BB Positions",
            "icon": "mdi:chart-bell-curve",
        },
        "ta_trend": {
            "name": "Trends",
            "icon": "mdi:trending-up",
        },
        "ta_support": {
            "name": "Support Levels",
            "icon": "mdi:arrow-down-bold",
        },
        "ta_resistance": {
            "name": "Resistance Levels",
            "icon": "mdi:arrow-up-bold",
        },
        # === Multi-Timeframe Trends (Generic) ===
        "ta_trend_mtf": {
            "name": "MTF Trends",
            "icon": "mdi:clock-outline",
        },
        # === TA Confluence ===
        "ta_confluence": {
            "name": "TA Confluence Score",
            "icon": "mdi:check-all",
        },
        "ta_signal": {
            "name": "TA Signal",
            "icon": "mdi:traffic-light",
        },
        # === Risk Management ===
        "portfolio_sharpe": {
            "name": "Sharpe Ratio",
            "icon": "mdi:chart-areaspline",
        },
        "portfolio_sortino": {
            "name": "Sortino Ratio",
            "icon": "mdi:chart-line-variant",
        },
        "portfolio_max_drawdown": {
            "name": "Max Drawdown",
            "icon": "mdi:trending-down",
            "unit": "%",
        },
        "portfolio_current_drawdown": {
            "name": "Current Drawdown",
            "icon": "mdi:arrow-down",
            "unit": "%",
        },
        "portfolio_var_95": {
            "name": "VaR 95%",
            "icon": "mdi:alert",
            "unit": "%",
        },
        "risk_status": {
            "name": "Risk Status",
            "icon": "mdi:shield-alert",
        },
        # === Backtesting ===
        "backtest_dca_roi": {
            "name": "DCA Backtest ROI",
            "icon": "mdi:percent",
            "unit": "%",
        },
        "backtest_smart_dca_roi": {
            "name": "Smart DCA ROI",
            "icon": "mdi:brain",
            "unit": "%",
        },
        "backtest_lump_sum_roi": {
            "name": "Lump Sum ROI",
            "icon": "mdi:cash",
            "unit": "%",
        },
        "backtest_best_strategy": {
            "name": "Best Strategy",
            "icon": "mdi:trophy",
        },
        # === Smart Summary (UX) ===
        "market_pulse": {
            "name": "Market Pulse",
            "icon": "mdi:pulse",
        },
        "market_pulse_confidence": {
            "name": "Market Confidence",
            "icon": "mdi:percent",
            "unit": "%",
        },
        "portfolio_health": {
            "name": "Portfolio Health",
            "icon": "mdi:shield-check",
        },
        "portfolio_health_score": {
            "name": "Health Score",
            "icon": "mdi:counter",
            "unit": "%",
        },
        "today_action": {
            "name": "Today's Action",
            "icon": "mdi:clipboard-check",
        },
        "today_action_priority": {
            "name": "Action Priority",
            "icon": "mdi:alert-circle",
        },
        "weekly_outlook": {
            "name": "Weekly Outlook",
            "icon": "mdi:calendar-week",
        },
        # === Alerts & Notifications (UX) ===
        "pending_alerts_count": {
            "name": "Pending Alerts",
            "icon": "mdi:bell-badge",
        },
        "pending_alerts_critical": {
            "name": "Critical Alerts",
            "icon": "mdi:bell-alert",
        },
        "daily_digest_ready": {
            "name": "Daily Digest Ready",
            "icon": "mdi:newspaper",
        },
        "notification_mode": {
            "name": "Notification Mode",
            "icon": "mdi:bell-cog",
        },
        # === Briefings (UX) ===
        "morning_briefing": {
            "name": "Morning Briefing",
            "icon": "mdi:weather-sunny",
        },
        "evening_briefing": {
            "name": "Evening Briefing",
            "icon": "mdi:weather-night",
        },
        "briefing_last_sent": {
            "name": "Briefing Last Sent",
            "icon": "mdi:clock-check",
            "device_class": "timestamp",
        },
        # === Goal Tracking (UX) ===
        "goal_target": {
            "name": "Goal Target",
            "icon": "mdi:flag-checkered",
            "unit": "USDT",
        },
        "goal_progress": {
            "name": "Goal Progress",
            "icon": "mdi:progress-check",
            "unit": "%",
        },
        "goal_remaining": {
            "name": "Goal Remaining",
            "icon": "mdi:cash-minus",
            "unit": "USDT",
        },
        "goal_days_estimate": {
            "name": "Days to Goal",
            "icon": "mdi:calendar-clock",
        },
        "goal_status": {
            "name": "Goal Status",
            "icon": "mdi:trophy",
        },
        # === Diagnostic Sensors ===
        "sync_status": {
            "name": "Sync Status",
            "icon": "mdi:sync",
            "entity_category": "diagnostic",
        },
        "last_sync": {
            "name": "Last Sync",
            "icon": "mdi:clock-outline",
            "device_class": "timestamp",
            "entity_category": "diagnostic",
        },
        "candles_count": {
            "name": "Total Candles",
            "icon": "mdi:database",
            "unit": "candles",
            "entity_category": "diagnostic",
        },
    }

    def __init__(self, mqtt_client=None):
        self._mqtt = mqtt_client
        self._prices: dict[str, str] = {}
        self._changes: dict[str, str] = {}
        self._volumes: dict[str, str] = {}
        self._highs: dict[str, str] = {}
        self._lows: dict[str, str] = {}
        self._cache: dict[str, any] = {}  # General cache for sensor values

    @property
    def device_info(self) -> dict:
        """Device info for MQTT Discovery."""
        return {
            "identifiers": [self.DEVICE_ID],
            "name": self.DEVICE_NAME,
            "model": "Crypto Data Collector",
            "manufacturer": "Crypto Inspect Add-on",
            "sw_version": "0.2.1",
        }

    def _get_discovery_topic(self, sensor_id: str) -> str:
        """Get MQTT discovery config topic."""
        return f"homeassistant/sensor/{self.DEVICE_ID}/{sensor_id}/config"

    def _get_state_topic(self, sensor_id: str) -> str:
        """Get MQTT state topic."""
        return f"{self.DEVICE_ID}/{sensor_id}/state"

    def _get_attributes_topic(self, sensor_id: str) -> str:
        """Get MQTT attributes topic."""
        return f"{self.DEVICE_ID}/{sensor_id}/attributes"

    async def register_sensors(self) -> int:
        """
        Register all sensors via MQTT Discovery.

        Returns:
            Number of sensors registered.
        """
        if not self._mqtt:
            logger.warning("MQTT client not configured, skipping sensor registration")
            return 0

        count = 0
        symbols = get_symbols()

        for sensor_id, sensor_def in self.SENSORS.items():
            config = {
                "name": sensor_def["name"],
                "unique_id": f"{self.DEVICE_ID}_{sensor_id}",
                "state_topic": self._get_state_topic(sensor_id),
                "json_attributes_topic": self._get_attributes_topic(sensor_id),
                "device": self.device_info,
            }

            if "icon" in sensor_def:
                config["icon"] = sensor_def["icon"]
            if "unit" in sensor_def:
                config["unit_of_measurement"] = sensor_def["unit"]
            if "device_class" in sensor_def:
                config["device_class"] = sensor_def["device_class"]
            if "entity_category" in sensor_def:
                config["entity_category"] = sensor_def["entity_category"]

            topic = self._get_discovery_topic(sensor_id)

            try:
                await self._mqtt.publish(topic, json.dumps(config), retain=True)
                count += 1
                logger.info(f"Registered sensor: {sensor_def['name']}")
            except Exception as e:
                logger.error(f"Failed to register sensor {sensor_id}: {e}")

        # Publish initial attributes with symbol list
        await self._publish_attributes("prices", {"symbols": symbols, "count": len(symbols)})

        logger.info(f"Registered {count} MQTT sensors, tracking {len(symbols)} symbols")
        return count

    async def _publish_state(self, sensor_id: str, state: str | dict) -> bool:
        """Publish sensor state."""
        if not self._mqtt:
            return False

        topic = self._get_state_topic(sensor_id)
        payload = json.dumps(state) if isinstance(state, dict) else str(state)

        try:
            await self._mqtt.publish(topic, payload)
            return True
        except Exception as e:
            logger.error(f"Failed to publish state for {sensor_id}: {e}")
            return False

    async def _publish_attributes(self, sensor_id: str, attributes: dict) -> bool:
        """Publish sensor attributes."""
        if not self._mqtt:
            return False

        topic = self._get_attributes_topic(sensor_id)
        try:
            await self._mqtt.publish(topic, json.dumps(attributes))
            return True
        except Exception as e:
            logger.error(f"Failed to publish attributes for {sensor_id}: {e}")
            return False

    async def publish_sensor(self, sensor_id: str, value: any, attributes: dict | None = None) -> bool:
        """
        Publish a sensor value with optional attributes.

        This is the main public API for updating sensor values.
        Values are cached for later retrieval.

        Args:
            sensor_id: Sensor identifier
            value: Value to publish (will be converted to string/JSON)
            attributes: Optional attributes dict

        Returns:
            True if published successfully
        """
        # Cache the value
        self._cache[sensor_id] = value

        # Publish state
        result = await self._publish_state(sensor_id, value)

        # Publish attributes if provided
        if attributes and result:
            await self._publish_attributes(sensor_id, attributes)

        return result

    async def update_price(
        self,
        symbol: str,
        price: Decimal | float,
        change_24h: float | None = None,
        volume_24h: Decimal | float | None = None,
        high_24h: Decimal | float | None = None,
        low_24h: Decimal | float | None = None,
    ) -> None:
        """
        Update price data for a symbol.

        Args:
            symbol: Trading pair (e.g., "BTC/USDT")
            price: Current price
            change_24h: 24h price change percentage
            volume_24h: 24h trading volume
            high_24h: 24h high price
            low_24h: 24h low price
        """
        # Update internal state
        self._prices[symbol] = str(price)

        if change_24h is not None:
            self._changes[symbol] = f"{change_24h:.2f}"
        if volume_24h is not None:
            self._volumes[symbol] = str(volume_24h)
        if high_24h is not None:
            self._highs[symbol] = str(high_24h)
        if low_24h is not None:
            self._lows[symbol] = str(low_24h)

        # Publish all price data
        await self._publish_state("prices", self._prices)
        await self._publish_attributes(
            "prices",
            {
                "symbols": list(self._prices.keys()),
                "count": len(self._prices),
                "last_updated": datetime.now(UTC).isoformat(),
            },
        )

        # Publish other metrics if we have data
        if self._changes:
            await self._publish_state("changes_24h", self._changes)
        if self._volumes:
            await self._publish_state("volumes_24h", self._volumes)
        if self._highs:
            await self._publish_state("highs_24h", self._highs)
        if self._lows:
            await self._publish_state("lows_24h", self._lows)

    async def update_all_prices(self, prices_data: dict[str, dict]) -> None:
        """
        Update prices for all symbols at once.

        Args:
            prices_data: Dict of {symbol: {price, change_24h, volume_24h, high_24h, low_24h}}
        """
        for symbol, data in prices_data.items():
            self._prices[symbol] = str(data.get("price", 0))
            if "change_24h" in data:
                self._changes[symbol] = f"{data['change_24h']:.2f}"
            if "volume_24h" in data:
                self._volumes[symbol] = str(data["volume_24h"])
            if "high_24h" in data:
                self._highs[symbol] = str(data["high_24h"])
            if "low_24h" in data:
                self._lows[symbol] = str(data["low_24h"])

        # Publish all states
        await self._publish_state("prices", self._prices)
        await self._publish_state("changes_24h", self._changes)
        await self._publish_state("volumes_24h", self._volumes)
        await self._publish_state("highs_24h", self._highs)
        await self._publish_state("lows_24h", self._lows)

        await self._publish_attributes(
            "prices",
            {
                "symbols": list(self._prices.keys()),
                "count": len(self._prices),
                "last_updated": datetime.now(UTC).isoformat(),
            },
        )

    async def update_sync_status(
        self,
        status: str,
        success_count: int = 0,
        failure_count: int = 0,
        total_candles: int | None = None,
    ) -> None:
        """
        Update sync status sensors.

        Args:
            status: Current status ('running', 'completed', 'error')
            success_count: Number of successful operations
            failure_count: Number of failed operations
            total_candles: Total candles in database
        """
        # Sync status
        await self._publish_state("sync_status", status)
        await self._publish_attributes(
            "sync_status",
            {
                "success_count": success_count,
                "failure_count": failure_count,
                "total_operations": success_count + failure_count,
                "success_rate": (
                    f"{(success_count / (success_count + failure_count) * 100):.1f}%"
                    if (success_count + failure_count) > 0
                    else "N/A"
                ),
            },
        )

        # Last sync timestamp
        await self._publish_state("last_sync", datetime.now(UTC).isoformat())

        # Total candles
        if total_candles is not None:
            await self._publish_state("candles_count", str(total_candles))

    async def remove_sensors(self) -> None:
        """Remove all sensors by publishing empty configs."""
        if not self._mqtt:
            return

        for sensor_id in self.SENSORS:
            topic = self._get_discovery_topic(sensor_id)
            try:
                await self._mqtt.publish(topic, "", retain=True)
            except Exception as e:
                logger.error(f"Failed to remove sensor {sensor_id}: {e}")

        logger.info("Removed all MQTT sensors")

    async def update_investor_status(self, status_data: dict) -> None:
        """
        Update all investor-related sensors from InvestorStatus.

        Args:
            status_data: Dictionary from InvestorStatus.to_dict()
        """
        if not self._mqtt:
            logger.warning("MQTT not configured, skipping investor update")
            return

        # Do Nothing OK
        do_nothing = status_data.get("do_nothing_ok", {})
        await self._publish_state("do_nothing_ok", do_nothing.get("state", "N/A"))
        await self._publish_attributes(
            "do_nothing_ok",
            {
                "value": do_nothing.get("value", False),
                "reason": do_nothing.get("reason_ru", ""),
            },
        )

        # Investor Phase
        phase = status_data.get("phase", {})
        await self._publish_state("investor_phase", phase.get("name_ru", "N/A"))
        await self._publish_attributes(
            "investor_phase",
            {
                "value": phase.get("value", "unknown"),
                "confidence": phase.get("confidence", 0),
                "description": phase.get("description_ru", ""),
            },
        )

        # Calm Indicator
        calm = status_data.get("calm", {})
        await self._publish_state("calm_indicator", str(calm.get("score", 50)))
        await self._publish_attributes(
            "calm_indicator",
            {
                "level": calm.get("level", "neutral"),
                "message": calm.get("message_ru", ""),
            },
        )

        # Red Flags
        red_flags = status_data.get("red_flags", {})
        flags_count = red_flags.get("count", 0)
        state_emoji = "🟢" if flags_count == 0 else "🟡" if flags_count <= 2 else "🔴"
        await self._publish_state("red_flags", f"{state_emoji} {flags_count}")
        await self._publish_attributes(
            "red_flags",
            {
                "flags_count": flags_count,
                "flags_list": red_flags.get("flags_list", "✅ Нет флагов"),
                "flags": red_flags.get("flags", []),
            },
        )

        # Market Tension
        tension = status_data.get("tension", {})
        await self._publish_state("market_tension", tension.get("state", "N/A"))
        await self._publish_attributes(
            "market_tension",
            {
                "score": tension.get("score", 50),
                "level": tension.get("level_ru", "Норма"),
            },
        )

        # Price Context
        price_ctx = status_data.get("price_context", {})
        await self._publish_state("price_context", price_ctx.get("context_ru", "N/A"))
        await self._publish_attributes(
            "price_context",
            {
                "current_price": price_ctx.get("current_price", 0),
                "avg_6m": price_ctx.get("avg_6m", 0),
                "diff_percent": price_ctx.get("diff_percent", 0),
                "recommendation": price_ctx.get("recommendation_ru", ""),
            },
        )

        # DCA Result
        dca = status_data.get("dca", {})
        await self._publish_state("dca_result", str(dca.get("total_amount", 0)))
        await self._publish_attributes(
            "dca_result",
            {
                "btc_amount": dca.get("btc_amount", 0),
                "eth_amount": dca.get("eth_amount", 0),
                "alts_amount": dca.get("alts_amount", 0),
                "reason": dca.get("reason_ru", ""),
            },
        )

        # DCA Signal
        await self._publish_state("dca_signal", dca.get("state", "N/A"))
        await self._publish_attributes(
            "dca_signal",
            {
                "signal": dca.get("signal", "neutral"),
                "signal_ru": dca.get("signal_ru", "Нейтрально"),
                "next_dca": dca.get("next_dca", ""),
            },
        )

        # Weekly Insight
        insight = status_data.get("weekly_insight", {})
        await self._publish_state("weekly_insight", insight.get("summary_ru", "N/A"))
        await self._publish_attributes(
            "weekly_insight",
            {
                "btc_status": insight.get("btc_status", ""),
                "eth_vs_btc": insight.get("eth_vs_btc", ""),
                "alts_status": insight.get("alts_status", ""),
                "dominance_trend": insight.get("dominance_trend", ""),
                "summary": insight.get("summary", ""),
            },
        )

        # Next Action Timer
        await self._publish_state("next_action_timer", dca.get("next_dca", "N/A"))

        logger.info("Updated investor sensors via MQTT")

    async def update_market_data(
        self,
        fear_greed: int | None = None,
        btc_dominance: float | None = None,
        derivatives_data: dict | None = None,
    ) -> None:
        """
        Update market-related sensors.

        Args:
            fear_greed: Fear & Greed Index (0-100)
            btc_dominance: BTC dominance percentage
            derivatives_data: Derivatives metrics dict
        """
        if fear_greed is not None:
            # Determine emoji based on value
            if fear_greed <= 25:
                state = f"🔴 {fear_greed} (Extreme Fear)"
            elif fear_greed <= 45:
                state = f"🟠 {fear_greed} (Fear)"
            elif fear_greed <= 55:
                state = f"🟡 {fear_greed} (Neutral)"
            elif fear_greed <= 75:
                state = f"🟢 {fear_greed} (Greed)"
            else:
                state = f"🟢 {fear_greed} (Extreme Greed)"

            await self._publish_state("fear_greed", state)
            await self._publish_attributes(
                "fear_greed",
                {
                    "value": fear_greed,
                    "classification": self._get_fg_classification(fear_greed),
                },
            )

        if btc_dominance is not None:
            await self._publish_state("btc_dominance", f"{btc_dominance:.1f}")
            await self._publish_attributes(
                "btc_dominance",
                {
                    "value": btc_dominance,
                    "trend": "↗️" if btc_dominance >= 55 else "↘️" if btc_dominance <= 45 else "→",
                },
            )

        if derivatives_data:
            await self._publish_state("derivatives", "Active")
            await self._publish_attributes("derivatives", derivatives_data)

    def _get_fg_classification(self, value: int) -> str:
        """Get Fear & Greed classification."""
        if value <= 25:
            return "Extreme Fear"
        if value <= 45:
            return "Fear"
        if value <= 55:
            return "Neutral"
        if value <= 75:
            return "Greed"
        return "Extreme Greed"

    async def update_smart_summary(self, summary_data: dict) -> None:
        """
        Update smart summary sensors.

        Args:
            summary_data: Dict with market_pulse, portfolio_health, today_action, weekly_outlook
        """
        if not self._mqtt:
            return

        # Market Pulse
        if "market_pulse" in summary_data:
            pulse = summary_data["market_pulse"]
            await self._publish_state("market_pulse", pulse.get("sentiment_ru", "N/A"))
            await self._publish_attributes(
                "market_pulse",
                {
                    "sentiment_en": pulse.get("sentiment_en", ""),
                    "sentiment_ru": pulse.get("sentiment_ru", ""),
                    "confidence": pulse.get("confidence", 0),
                    "reason_en": pulse.get("reason_en", ""),
                    "reason_ru": pulse.get("reason_ru", ""),
                    "factors_en": pulse.get("factors_en", []),
                    "factors_ru": pulse.get("factors_ru", []),
                },
            )
            await self._publish_state("market_pulse_confidence", str(pulse.get("confidence", 0)))

        # Portfolio Health
        if "portfolio_health" in summary_data:
            health = summary_data["portfolio_health"]
            await self._publish_state("portfolio_health", health.get("status_ru", "N/A"))
            await self._publish_attributes(
                "portfolio_health",
                {
                    "status_en": health.get("status_en", ""),
                    "status_ru": health.get("status_ru", ""),
                    "score": health.get("score", 0),
                    "main_issue_en": health.get("main_issue_en", ""),
                    "main_issue_ru": health.get("main_issue_ru", ""),
                },
            )
            await self._publish_state("portfolio_health_score", str(health.get("score", 0)))

        # Today's Action
        if "today_action" in summary_data:
            action = summary_data["today_action"]
            await self._publish_state("today_action", action.get("action_ru", "N/A"))
            await self._publish_attributes(
                "today_action",
                {
                    "action_en": action.get("action_en", ""),
                    "action_ru": action.get("action_ru", ""),
                    "priority_en": action.get("priority_en", ""),
                    "priority_ru": action.get("priority_ru", ""),
                    "details_en": action.get("details_en", ""),
                    "details_ru": action.get("details_ru", ""),
                },
            )
            await self._publish_state("today_action_priority", action.get("priority_ru", "N/A"))

        # Weekly Outlook
        if "weekly_outlook" in summary_data:
            outlook = summary_data["weekly_outlook"]
            await self._publish_state("weekly_outlook", outlook.get("outlook_ru", "N/A"))
            await self._publish_attributes("weekly_outlook", outlook)

        logger.info("Updated smart summary sensors via MQTT")

    async def update_notification_status(self, status_data: dict) -> None:
        """
        Update notification-related sensors.

        Args:
            status_data: Dict from NotificationManager.format_sensor_attributes()
        """
        if not self._mqtt:
            return

        await self._publish_state("pending_alerts_count", str(status_data.get("pending_alerts_count", 0)))
        await self._publish_attributes(
            "pending_alerts_count",
            {
                "critical": status_data.get("pending_alerts_critical", 0),
                "important": status_data.get("pending_alerts_important", 0),
                "info": status_data.get("pending_alerts_info", 0),
            },
        )

        await self._publish_state("pending_alerts_critical", str(status_data.get("pending_alerts_critical", 0)))

        await self._publish_state("daily_digest_ready", status_data.get("digest_ready_ru", "Новых оповещений нет"))
        await self._publish_attributes(
            "daily_digest_ready",
            {
                "ready": status_data.get("daily_digest_ready", False),
                "ready_en": status_data.get("digest_ready_en", ""),
                "ready_ru": status_data.get("digest_ready_ru", ""),
                "last_digest": status_data.get("last_digest_time"),
            },
        )

        await self._publish_state("notification_mode", status_data.get("notification_mode_ru", "Умный режим"))
        await self._publish_attributes(
            "notification_mode",
            {
                "mode": status_data.get("notification_mode", "smart"),
                "mode_en": status_data.get("notification_mode_en", ""),
                "mode_ru": status_data.get("notification_mode_ru", ""),
            },
        )

        logger.info("Updated notification sensors via MQTT")

    async def update_briefing_status(self, briefing_data: dict) -> None:
        """
        Update briefing-related sensors.

        Args:
            briefing_data: Dict from BriefingService.format_sensor_attributes()
        """
        if not self._mqtt:
            return

        await self._publish_state(
            "morning_briefing", briefing_data.get("morning_briefing_status_ru", "Не сгенерирован")
        )
        await self._publish_attributes(
            "morning_briefing",
            {
                "available": briefing_data.get("morning_briefing_available", False),
                "status_en": briefing_data.get("morning_briefing_status_en", ""),
                "status_ru": briefing_data.get("morning_briefing_status_ru", ""),
                "last_sent": briefing_data.get("last_morning_briefing"),
            },
        )

        await self._publish_state(
            "evening_briefing", briefing_data.get("evening_briefing_status_ru", "Не сгенерирован")
        )
        await self._publish_attributes(
            "evening_briefing",
            {
                "available": briefing_data.get("evening_briefing_available", False),
                "status_en": briefing_data.get("evening_briefing_status_en", ""),
                "status_ru": briefing_data.get("evening_briefing_status_ru", ""),
                "last_sent": briefing_data.get("last_evening_briefing"),
            },
        )

        # Last briefing sent timestamp
        last_morning = briefing_data.get("last_morning_briefing")
        last_evening = briefing_data.get("last_evening_briefing")
        last_sent = last_evening or last_morning or None
        if last_sent:
            await self._publish_state("briefing_last_sent", last_sent)

        logger.info("Updated briefing sensors via MQTT")

    async def update_goal_status(self, goal_data: dict) -> None:
        """
        Update goal tracking sensors.

        Args:
            goal_data: Dict from GoalTracker.format_sensor_attributes()
        """
        if not self._mqtt:
            return

        await self._publish_state("goal_target", str(goal_data.get("goal_target", 0)))
        await self._publish_attributes(
            "goal_target",
            {
                "goal_name": goal_data.get("goal_name", ""),
                "goal_name_ru": goal_data.get("goal_name_ru", ""),
                "target_date": goal_data.get("target_date"),
                "start_date": goal_data.get("start_date"),
            },
        )

        progress = goal_data.get("goal_progress", 0)
        emoji = goal_data.get("goal_emoji", "🎯")
        await self._publish_state("goal_progress", f"{emoji} {progress:.1f}%")
        await self._publish_attributes(
            "goal_progress",
            {
                "percent": progress,
                "current": goal_data.get("goal_current", 0),
                "target": goal_data.get("goal_target", 0),
                "remaining": goal_data.get("goal_remaining", 0),
                "milestones_reached": goal_data.get("milestones_reached", []),
                "next_milestone": goal_data.get("next_milestone"),
            },
        )

        await self._publish_state("goal_remaining", str(goal_data.get("goal_remaining", 0)))

        days_estimate = goal_data.get("goal_days_estimate")
        if days_estimate is not None:
            await self._publish_state("goal_days_estimate", str(days_estimate))
        else:
            await self._publish_state("goal_days_estimate", "N/A")

        await self._publish_state("goal_status", goal_data.get("goal_status_ru", "В процессе"))
        await self._publish_attributes(
            "goal_status",
            {
                "status": goal_data.get("goal_status", ""),
                "status_en": goal_data.get("goal_status_en", ""),
                "status_ru": goal_data.get("goal_status_ru", ""),
                "milestone_message_en": goal_data.get("milestone_message", ""),
                "milestone_message_ru": goal_data.get("milestone_message_ru", ""),
            },
        )

        logger.info("Updated goal sensors via MQTT")


# Global instance
_sensors_manager: CryptoSensorsManager | None = None


def get_sensors_manager(mqtt_client=None) -> CryptoSensorsManager:
    """Get or create sensors manager."""
    global _sensors_manager
    if _sensors_manager is None or mqtt_client is not None:
        _sensors_manager = CryptoSensorsManager(mqtt_client)
    return _sensors_manager
