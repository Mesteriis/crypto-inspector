"""Home Assistant Integration Manager.

Main coordinator for all HA sensors. Replaces CryptoSensorsManager
with modular architecture and Pydantic validation.
"""

import logging
import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from core.constants import APP_VERSION, DEFAULT_SYMBOLS
from service.ha.core.base import BaseSensor
from service.ha.core.publisher import SupervisorPublisher
from service.ha.core.registry import SensorRegistry

logger = logging.getLogger(__name__)


# =============================================================================
# DYNAMIC CURRENCY LIST WITH BYBIT INTEGRATION
# =============================================================================


class DynamicCurrencyManager:
    """
    Dynamic currency list manager that combines:
    1. User-configured symbols (from env/config) OR defaults
    2. Symbols from Bybit balances (wallet + earn)

    Refreshes Bybit symbols at runtime, not just at startup.
    Automatically triggers historical data backfill for new symbols.
    """

    _instance: "DynamicCurrencyManager | None" = None

    def __init__(self):
        self._configured_symbols: list[str] = []
        self._bybit_symbols: set[str] = set()
        self._backfilled_symbols: set[str] = set()  # Track backfilled symbols
        self._last_bybit_refresh: datetime | None = None
        self._bybit_refresh_interval = timedelta(minutes=5)
        self._bybit_configured: bool | None = None  # Cached config check
        self._backfill_in_progress: set[str] = set()  # Prevent duplicate backfills

    @classmethod
    def get_instance(cls) -> "DynamicCurrencyManager":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_configured_symbols(self) -> list[str]:
        """Load user-configured symbols from env or defaults."""
        # Check environment variable first
        symbols_env = os.environ.get("HA_SYMBOLS", "")
        if symbols_env:
            symbols = [s.strip() for s in symbols_env.split(",") if s.strip()]
            # Normalize symbol format: BTCUSDT -> BTC/USDT
            normalized = []
            for s in symbols:
                if "/" in s:
                    # Already has slash, use as-is
                    normalized.append(s)
                elif s.endswith("USDT"):
                    # BTCUSDT -> BTC/USDT
                    normalized.append(s[:-4] + "/USDT")
                elif s.endswith("USDC"):
                    # BTCUSDC -> BTC/USDC
                    normalized.append(s[:-4] + "/USDC")
                elif s.endswith("BUSD"):
                    # BTCBUSD -> BTC/BUSD
                    normalized.append(s[:-4] + "/BUSD")
                else:
                    # Assume USDT pair
                    normalized.append(f"{s}/USDT")
            return normalized

        # Fallback to defaults
        return DEFAULT_SYMBOLS.copy()

    async def _refresh_bybit_symbols(self) -> None:
        """Fetch symbols from Bybit wallet and earn positions."""
        try:
            from service.exchange import get_bybit_portfolio

            portfolio = get_bybit_portfolio()

            # Cache the configured check
            if self._bybit_configured is None:
                self._bybit_configured = portfolio.is_configured

            if not self._bybit_configured:
                return

            account = await portfolio.get_account()

            new_symbols: set[str] = set()

            # Add symbols from wallet balances (non-zero balance)
            for balance in account.balances:
                if balance.wallet_balance > 0 or balance.usd_value > 1:  # Min $1 value
                    coin = balance.coin
                    if coin not in ("USDT", "USDC", "USD"):  # Skip stablecoins
                        new_symbols.add(f"{coin}/USDT")

            # Add symbols from earn positions
            for earn in account.earn_positions:
                coin = earn.coin
                if coin not in ("USDT", "USDC", "USD"):
                    new_symbols.add(f"{coin}/USDT")

            if new_symbols != self._bybit_symbols:
                added = new_symbols - self._bybit_symbols
                removed = self._bybit_symbols - new_symbols
                if added:
                    logger.info(f"Bybit symbols added: {added}")
                    # Trigger backfill for new symbols
                    await self._backfill_new_symbols(added)
                if removed:
                    logger.info(f"Bybit symbols removed: {removed}")
                self._bybit_symbols = new_symbols

            self._last_bybit_refresh = datetime.now(UTC)

        except Exception as e:
            logger.debug(f"Failed to refresh Bybit symbols: {e}")

    async def _backfill_new_symbols(self, symbols: set[str]) -> None:
        """Trigger historical data backfill for newly discovered symbols."""
        import asyncio

        for symbol in symbols:
            # Skip if already backfilled or in progress
            if symbol in self._backfilled_symbols or symbol in self._backfill_in_progress:
                continue

            self._backfill_in_progress.add(symbol)
            logger.info(f"Triggering historical backfill for new Bybit symbol: {symbol}")

            try:
                from service.backfill.crypto_backfill import CryptoBackfill

                backfill = CryptoBackfill()

                # Backfill key intervals for analysis
                intervals = [
                    ("4h", 1),  # 1 year of 4h data (for divergence/S-R)
                    ("1d", 2),  # 2 years of daily data
                    ("1h", 0.5),  # 6 months of hourly data
                    ("15m", 0.25),  # 3 months of 15m data
                ]

                total_candles = 0
                for interval, years in intervals:
                    try:
                        count = await backfill.backfill_symbol(
                            symbol=symbol,
                            interval=interval,
                            years=years,
                        )
                        total_candles += count
                        logger.info(f"Backfilled {count} {interval} candles for {symbol}")
                        await asyncio.sleep(0.5)  # Rate limiting
                    except Exception as e:
                        logger.warning(f"Failed to backfill {interval} for {symbol}: {e}")

                self._backfilled_symbols.add(symbol)
                logger.info(f"Backfill complete for {symbol}: {total_candles} total candles")

            except Exception as e:
                logger.error(f"Backfill failed for {symbol}: {e}")
            finally:
                self._backfill_in_progress.discard(symbol)

    def _needs_bybit_refresh(self) -> bool:
        """Check if Bybit symbols need refresh."""
        if self._last_bybit_refresh is None:
            return True
        return datetime.now(UTC) - self._last_bybit_refresh > self._bybit_refresh_interval

    async def get_symbols_async(self) -> list[str]:
        """Get combined currency list (async version for runtime refresh)."""
        # Refresh Bybit symbols if needed
        if self._needs_bybit_refresh():
            await self._refresh_bybit_symbols()

        return self._get_combined_symbols()

    def get_symbols_sync(self) -> list[str]:
        """Get combined currency list (sync version - uses cached Bybit data)."""
        return self._get_combined_symbols()

    def _get_combined_symbols(self) -> list[str]:
        """Combine configured and Bybit symbols."""
        configured = self._load_configured_symbols()

        # Merge: configured + bybit (deduped, maintaining order)
        combined: list[str] = list(configured)
        for sym in sorted(self._bybit_symbols):
            if sym not in combined:
                combined.append(sym)

        return combined

    def force_refresh(self) -> None:
        """Force Bybit refresh on next call."""
        self._last_bybit_refresh = None
        self._bybit_configured = None


def get_currency_list() -> list[str]:
    """Get the dynamic currency list.

    Combines:
    1. User-configured symbols (from HA_SYMBOLS env) OR defaults
    2. Symbols from Bybit wallet/earn positions (cached)

    This is the single source of truth for currency selections.
    For async contexts, use get_currency_list_async() for fresh Bybit data.

    Returns:
        List of currency symbols (e.g., ["BTC/USDT", "ETH/USDT"])
    """
    manager = DynamicCurrencyManager.get_instance()
    return manager.get_symbols_sync()


async def get_currency_list_async() -> list[str]:
    """Get the dynamic currency list with fresh Bybit data.

    Use this in async contexts (scheduler jobs, API handlers) to get
    up-to-date Bybit symbols.

    Returns:
        List of currency symbols (e.g., ["BTC/USDT", "ETH/USDT"])
    """
    manager = DynamicCurrencyManager.get_instance()
    return await manager.get_symbols_async()


def refresh_currency_list() -> None:
    """Force refresh of Bybit symbols on next call."""
    manager = DynamicCurrencyManager.get_instance()
    manager.force_refresh()


class HAIntegrationManager:
    """Main manager for Home Assistant integration.

    Replaces CryptoSensorsManager with:
    - Modular sensor architecture
    - Pydantic validation
    - Centralized registry
    - Backward-compatible API
    """

    DEVICE_ID = "crypto_inspect"
    DEVICE_NAME = "Crypto Inspect"

    def __init__(self, publisher: SupervisorPublisher | None = None):
        """Initialize manager.

        Args:
            publisher: Optional custom publisher. Uses default if not provided.
        """
        self.publisher = publisher or SupervisorPublisher()
        self._sensors: dict[str, BaseSensor] = {}
        self._prices: dict[str, str] = {}
        self._changes: dict[str, str] = {}
        self._volumes: dict[str, str] = {}
        self._highs: dict[str, str] = {}
        self._lows: dict[str, str] = {}
        self._cache: dict[str, Any] = {}

        # Ensure all sensors are registered
        SensorRegistry.ensure_initialized()
        self._initialize_sensors()

    def _initialize_sensors(self) -> None:
        """Create instances of all registered sensors."""
        for sensor_id, sensor_class in SensorRegistry.get_all().items():
            try:
                self._sensors[sensor_id] = sensor_class(self.publisher)
            except Exception as e:
                logger.error(f"Failed to initialize sensor {sensor_id}: {e}")

        logger.info(f"Initialized {len(self._sensors)} sensors")

    @property
    def device_info(self) -> dict:
        """Device info for Home Assistant."""
        return {
            "identifiers": [self.DEVICE_ID],
            "name": self.DEVICE_NAME,
            "manufacturer": "Crypto Inspect",
            "model": "Sensor Manager v2",
            "sw_version": APP_VERSION,
        }

    # === Registration Methods ===

    async def register_sensors(self) -> int:
        """Register all sensors in Home Assistant.

        Returns:
            Number of successfully registered sensors
        """
        if not self.publisher.is_available:
            logger.warning("Publisher not available, skipping registration")
            return 0

        count = 0
        for sensor_id, sensor in self._sensors.items():
            try:
                success = await self.publisher.create_sensor(
                    sensor_id=sensor_id,
                    registration_data=sensor.get_registration_data(),
                    initial_state="Загрузка...",
                )
                if success:
                    count += 1
            except Exception as e:
                logger.error(f"Failed to register {sensor_id}: {e}")

        logger.info(f"Registered {count}/{len(self._sensors)} sensors")
        return count

    async def remove_sensors(self) -> int:
        """Mark all sensors as unavailable.

        Returns:
            Number of sensors marked unavailable
        """
        count = 0
        for sensor_id in self._sensors:
            try:
                if await self.publisher.remove_sensor(sensor_id):
                    count += 1
            except Exception as e:
                logger.error(f"Failed to remove {sensor_id}: {e}")

        return count

    # === Generic Publishing Methods ===

    async def publish_sensor(
        self,
        sensor_id: str,
        value: Any,
        attributes: dict | None = None,
    ) -> bool:
        """Publish value to a sensor.

        Args:
            sensor_id: Sensor identifier
            value: Value to publish
            attributes: Optional additional attributes

        Returns:
            True if published successfully
        """
        # Update cache
        self._cache[sensor_id] = value

        if sensor_id not in self._sensors:
            logger.warning(f"Unknown sensor: {sensor_id}")
            # Fallback: publish directly without validation
            return await self.publisher.publish_sensor(sensor_id, str(value), attributes)

        return await self._sensors[sensor_id].publish(value, attributes)

    # === Price Update Methods (Backward Compatible) ===

    async def update_price(
        self,
        symbol: str,
        price: Decimal | float,
        change_24h: float | None = None,
        volume_24h: Decimal | float | None = None,
        high_24h: Decimal | float | None = None,
        low_24h: Decimal | float | None = None,
    ) -> None:
        """Update price data for a single symbol.

        Args:
            symbol: Trading pair (e.g., "BTC/USDT")
            price: Current price
            change_24h: Optional 24h change percentage
            volume_24h: Optional 24h volume
            high_24h: Optional 24h high
            low_24h: Optional 24h low
        """
        # Update caches
        self._prices[symbol] = str(price)

        if change_24h is not None:
            self._changes[symbol] = f"{change_24h:.2f}"

        if volume_24h is not None:
            self._volumes[symbol] = str(volume_24h)

        if high_24h is not None:
            self._highs[symbol] = str(high_24h)

        if low_24h is not None:
            self._lows[symbol] = str(low_24h)

        # Publish all price sensors
        timestamp = datetime.now(UTC).isoformat()
        base_attrs = {
            "last_updated": timestamp,
            "count": len(self._prices),
            "symbols": list(self._prices.keys()),
        }

        await self.publish_sensor("prices", self._prices, base_attrs)

        if self._changes:
            await self.publish_sensor("changes_24h", self._changes, base_attrs)

        if self._volumes:
            await self.publish_sensor("volumes_24h", self._volumes, base_attrs)

        if self._highs:
            await self.publish_sensor("highs_24h", self._highs, base_attrs)

        if self._lows:
            await self.publish_sensor("lows_24h", self._lows, base_attrs)

    async def update_all_prices(self, prices_data: dict[str, dict]) -> None:
        """Update all prices at once.

        Args:
            prices_data: Dict of symbol -> {price, change_24h, volume_24h, ...}
        """
        self._prices.clear()
        self._changes.clear()
        self._volumes.clear()
        self._highs.clear()
        self._lows.clear()

        for symbol, data in prices_data.items():
            if "price" in data:
                self._prices[symbol] = str(data["price"])
            if "change_24h" in data and data["change_24h"] is not None:
                self._changes[symbol] = f"{data['change_24h']:.2f}"
            if "volume_24h" in data and data["volume_24h"] is not None:
                self._volumes[symbol] = str(data["volume_24h"])
            if "high_24h" in data and data["high_24h"] is not None:
                self._highs[symbol] = str(data["high_24h"])
            if "low_24h" in data and data["low_24h"] is not None:
                self._lows[symbol] = str(data["low_24h"])

        timestamp = datetime.now(UTC).isoformat()
        base_attrs = {
            "last_updated": timestamp,
            "count": len(self._prices),
            "symbols": list(self._prices.keys()),
        }

        await self.publish_sensor("prices", self._prices, base_attrs)
        await self.publish_sensor("changes_24h", self._changes, base_attrs)
        await self.publish_sensor("volumes_24h", self._volumes, base_attrs)
        await self.publish_sensor("highs_24h", self._highs, base_attrs)
        await self.publish_sensor("lows_24h", self._lows, base_attrs)

    # === Investor Status Methods ===

    async def update_investor_status(self, status_data: dict) -> None:
        """Update lazy investor status sensors.

        Args:
            status_data: Dict from InvestorStatus.to_dict()
        """
        timestamp = datetime.now(UTC).isoformat()

        # do_nothing_ok - handle nested dict format from to_dict()
        do_nothing = status_data.get("do_nothing_ok", {})
        if isinstance(do_nothing, dict):
            do_nothing_val = do_nothing.get("value", False)
            do_nothing_attrs = {
                "state": do_nothing.get("state", ""),
                "reason": do_nothing.get("reason", ""),
                "reason_ru": do_nothing.get("reason_ru", ""),
                "last_updated": timestamp,
            }
        else:
            do_nothing_val = bool(do_nothing)
            do_nothing_attrs = {"last_updated": timestamp}
        await self.publish_sensor("do_nothing_ok", do_nothing_val, do_nothing_attrs)

        # investor_phase - handle nested dict format
        phase = status_data.get("phase", {})
        if isinstance(phase, dict):
            phase_val = phase.get("name_ru", phase.get("value", "unknown"))
            phase_attrs = {
                "value": phase.get("value", ""),
                "confidence": phase.get("confidence", 50),
                "description": phase.get("description", ""),
                "description_ru": phase.get("description_ru", ""),
                "last_updated": timestamp,
            }
        else:
            phase_val = str(phase)
            phase_attrs = {"last_updated": timestamp}
        await self.publish_sensor("investor_phase", phase_val, phase_attrs)

        # calm_indicator - handle nested dict format
        calm = status_data.get("calm", {})
        if isinstance(calm, dict):
            calm_val = calm.get("score", 50)
            calm_attrs = {
                "level": calm.get("level", ""),
                "message": calm.get("message", ""),
                "message_ru": calm.get("message_ru", ""),
                "last_updated": timestamp,
            }
        else:
            calm_val = int(calm) if calm else 50
            calm_attrs = {"last_updated": timestamp}
        await self.publish_sensor("calm_indicator", calm_val, calm_attrs)

        # red_flags - CountSensor expects int value
        flags_data = status_data.get("red_flags", {})
        if isinstance(flags_data, dict):
            flags_count = flags_data.get("count", 0)
            flags_list = flags_data.get("flags_list", "")
        else:
            flags_count = int(flags_data) if flags_data else 0
            flags_list = ""
        emoji = "🟢" if flags_count == 0 else ("🟡" if flags_count <= 2 else "🔴")
        await self.publish_sensor(
            "red_flags",
            flags_count,
            {
                "status_emoji": emoji,
                "count": flags_count,
                "flags_list": flags_list,
                "last_updated": timestamp,
            },
        )

        # market_tension - handle nested dict format
        tension = status_data.get("tension", {})
        if isinstance(tension, dict):
            tension_val = tension.get("level_ru", tension.get("level", "unknown"))
            tension_attrs = {
                "score": tension.get("score", 50),
                "state": tension.get("state", ""),
                "last_updated": timestamp,
            }
        else:
            tension_val = str(tension) if tension else "unknown"
            tension_attrs = {"last_updated": timestamp}
        await self.publish_sensor("market_tension", tension_val, tension_attrs)

        # price_context - handle nested dict format
        context = status_data.get("price_context", {})
        if isinstance(context, dict):
            context_val = context.get("context_ru", context.get("context", "unknown"))
            context_attrs = {
                "current_price": context.get("current_price", 0),
                "avg_6m": context.get("avg_6m", 0),
                "diff_percent": context.get("diff_percent", 0),
                "recommendation": context.get("recommendation", ""),
                "recommendation_ru": context.get("recommendation_ru", ""),
                "last_updated": timestamp,
            }
        else:
            context_val = str(context) if context else "unknown"
            context_attrs = {"last_updated": timestamp}
        await self.publish_sensor("price_context", context_val, context_attrs)

        # dca - handle nested dict format
        dca = status_data.get("dca", {})
        if isinstance(dca, dict):
            dca_signal = dca.get("signal_ru", dca.get("signal", "unknown"))
            dca_amount = dca.get("total_amount", 0)
            dca_attrs = {
                "signal": dca.get("signal", ""),
                "state": dca.get("state", ""),
                "btc_amount": dca.get("btc_amount", 0),
                "eth_amount": dca.get("eth_amount", 0),
                "reason": dca.get("reason", ""),
                "reason_ru": dca.get("reason_ru", ""),
                "next_dca": dca.get("next_dca", ""),
                "last_updated": timestamp,
            }
        else:
            dca_signal = str(dca) if dca else "unknown"
            dca_amount = 0
            dca_attrs = {"last_updated": timestamp}
        await self.publish_sensor("dca_result", dca_amount, dca_attrs)
        await self.publish_sensor("dca_signal", dca_signal, {"last_updated": timestamp})

        # weekly_insight - handle nested dict format
        insight = status_data.get("weekly_insight", {})
        if isinstance(insight, dict):
            insight_val = insight.get("summary_ru", insight.get("summary", ""))
            insight_attrs = {
                "btc_status": insight.get("btc_status", ""),
                "eth_vs_btc": insight.get("eth_vs_btc", ""),
                "alts_status": insight.get("alts_status", ""),
                "dominance_trend": insight.get("dominance_trend", ""),
                "last_updated": timestamp,
            }
        else:
            insight_val = str(insight) if insight else ""
            insight_attrs = {"last_updated": timestamp}
        await self.publish_sensor("weekly_insight", insight_val, insight_attrs)

    # === Market Data Methods ===

    async def update_market_data(
        self,
        fear_greed: int | None = None,
        btc_dominance: float | None = None,
        derivatives_data: dict | None = None,
    ) -> None:
        """Update market indicator sensors.

        Args:
            fear_greed: Fear & Greed Index (0-100)
            btc_dominance: BTC market dominance percentage
            derivatives_data: Derivatives market data
        """
        timestamp = datetime.now(UTC).isoformat()

        if fear_greed is not None:
            await self.publish_sensor(
                "fear_greed",
                fear_greed,
                {
                    "value": fear_greed,
                    "last_updated": timestamp,
                },
            )

        if btc_dominance is not None:
            await self.publish_sensor(
                "btc_dominance",
                btc_dominance,
                {
                    "last_updated": timestamp,
                },
            )

        if derivatives_data is not None:
            await self.publish_sensor(
                "derivatives",
                derivatives_data,
                {
                    "last_updated": timestamp,
                },
            )

    # === Sync Status Methods ===

    async def update_sync_status(
        self,
        status: str,
        success_count: int = 0,
        failure_count: int = 0,
        total_candles: int | None = None,
    ) -> None:
        """Update synchronization status sensors.

        Args:
            status: Current status (idle/running/completed/error)
            success_count: Number of successful syncs
            failure_count: Number of failed syncs
            total_candles: Total candles in database
        """
        timestamp = datetime.now(UTC).isoformat()

        await self.publish_sensor(
            "sync_status",
            status,
            {
                "success_count": success_count,
                "failure_count": failure_count,
                "last_updated": timestamp,
            },
        )

        await self.publish_sensor("last_sync", timestamp)

        if total_candles is not None:
            await self.publish_sensor("candles_count", total_candles)

    # === Smart Summary Methods ===

    async def update_smart_summary(self, summary_data: dict) -> None:
        """Update smart summary sensors.

        Args:
            summary_data: Dict with pulse, health, action, outlook
        """
        timestamp = datetime.now(UTC).isoformat()

        # Market pulse
        if "pulse" in summary_data:
            pulse = summary_data["pulse"]
            confidence = summary_data.get("pulse_confidence")
            await self.publish_sensor(
                "market_pulse",
                pulse,
                {
                    "confidence": confidence,
                    "pulse_ru": summary_data.get("pulse_ru", pulse),
                    "last_updated": timestamp,
                },
            )
            if confidence is not None:
                await self.publish_sensor("market_pulse_confidence", confidence)

        # Portfolio health
        if "health" in summary_data:
            health = summary_data["health"]
            score = summary_data.get("health_score")
            await self.publish_sensor(
                "portfolio_health",
                health,
                {
                    "score": score,
                    "health_ru": summary_data.get("health_ru", health),
                    "last_updated": timestamp,
                },
            )
            if score is not None:
                await self.publish_sensor("portfolio_health_score", score)

        # Today's action
        if "action" in summary_data:
            action = summary_data["action"]
            priority = summary_data.get("action_priority", "low")
            await self.publish_sensor(
                "today_action",
                action,
                {
                    "priority": priority,
                    "action_ru": summary_data.get("action_ru", action),
                    "last_updated": timestamp,
                },
            )
            await self.publish_sensor("today_action_priority", priority)

        # Weekly outlook
        if "outlook" in summary_data:
            outlook = summary_data["outlook"]
            await self.publish_sensor(
                "weekly_outlook",
                outlook,
                {
                    "outlook_ru": summary_data.get("outlook_ru", outlook),
                    "last_updated": timestamp,
                },
            )

    # === Notification Status Methods ===

    async def update_notification_status(self, status_data: dict) -> None:
        """Update notification sensors.

        Args:
            status_data: Dict with pending, critical, mode
        """
        timestamp = datetime.now(UTC).isoformat()

        if "pending_count" in status_data:
            await self.publish_sensor("pending_alerts_count", status_data["pending_count"])

        if "critical_count" in status_data:
            await self.publish_sensor("pending_alerts_critical", status_data["critical_count"])

        if "daily_digest_ready" in status_data:
            await self.publish_sensor("daily_digest_ready", status_data["daily_digest_ready"])

        if "mode" in status_data:
            await self.publish_sensor(
                "notification_mode",
                status_data["mode"],
                {
                    "last_updated": timestamp,
                },
            )

    # === ML/AI Methods ===

    async def update_ml_investor_sensors(self, ml_data: dict) -> None:
        """Update ML investor insight sensors.

        Args:
            ml_data: Dict with portfolio_health, market_confidence, etc.
        """
        timestamp = datetime.now(UTC).isoformat()

        if "portfolio_sentiment" in ml_data:
            await self.publish_sensor(
                "portfolio_health",
                ml_data["portfolio_sentiment"],
                {
                    "opportunity_signals": ml_data.get("opportunity_signals", 0),
                    "risk_signals": ml_data.get("risk_signals", 0),
                    "hold_signals": ml_data.get("hold_signals", 0),
                    "recommendation": ml_data.get("recommendation", ""),
                    "last_updated": timestamp,
                },
            )

    def _get_accuracy_rating(self, accuracy: float) -> str:
        """Get Russian accuracy rating label.

        Args:
            accuracy: Accuracy percentage (0-100)

        Returns:
            Russian rating label
        """
        if accuracy >= 80:
            return "отличная"
        elif accuracy >= 70:
            return "хорошая"
        elif accuracy >= 60:
            return "удовлетворительная"
        elif accuracy >= 50:
            return "средняя"
        else:
            return "низкая"

    async def update_ml_prediction_sensors(self, prediction_data: dict) -> None:
        """Update ML prediction sensors.

        Args:
            prediction_data: Dict with prediction statistics
        """
        timestamp = datetime.now(UTC).isoformat()

        # Latest predictions
        if "latest_predictions" in prediction_data:
            await self.publish_sensor(
                "ml_latest_predictions",
                prediction_data["latest_predictions"],
                {
                    "last_updated": timestamp,
                },
            )

        # Correct predictions count
        if "correct_predictions" in prediction_data:
            await self.publish_sensor(
                "ml_correct_predictions",
                prediction_data["correct_predictions"],
                {
                    "incorrect": prediction_data.get("incorrect_predictions", 0),
                    "total": prediction_data.get("total_predictions", 0),
                    "last_updated": timestamp,
                },
            )

        # Accuracy rate
        if "accuracy_percentage" in prediction_data:
            accuracy = prediction_data["accuracy_percentage"]
            rating = self._get_accuracy_rating(accuracy)
            await self.publish_sensor(
                "ml_accuracy_rate",
                accuracy,
                {
                    "rating": rating,
                    "rating_ru": rating,
                    "last_updated": timestamp,
                },
            )

    async def update_ai_trend_sensors(self) -> None:
        """Update AI trend analysis sensors."""
        try:
            from service.trend_analyzer import get_trend_analyzer

            analyzer = get_trend_analyzer()

            # Get symbols from multiple sources
            symbols = list(self._prices.keys()) if self._prices else []

            # Fallback: get from cache
            if not symbols:
                cached_prices = self._cache.get("prices", {})
                if isinstance(cached_prices, dict):
                    symbols = list(cached_prices.keys())

            # Fallback: get from currency list
            if not symbols:
                try:
                    from core.constants import DEFAULT_SYMBOLS

                    symbols = [s.split("/")[0] for s in DEFAULT_SYMBOLS]  # BTC/USDT -> BTC
                except Exception:
                    pass

            if not symbols:
                logger.debug("No symbols available for AI trend analysis")
                return

            ai_trends = {}
            ai_confidences = {}
            ai_forecasts = {}
            ai_details = {}

            for symbol in symbols:
                try:
                    result = await analyzer.analyze_trend(symbol)
                    if result:
                        # TrendAnalysis object - access attributes directly
                        ai_trends[symbol] = result.direction.value if hasattr(result, "direction") else "Neutral"
                        ai_confidences[symbol] = round(result.confidence, 1) if hasattr(result, "confidence") else 50
                        ai_forecasts[symbol] = (
                            round(result.predicted_price_24h, 2) if hasattr(result, "predicted_price_24h") else None
                        )
                        ai_details[symbol] = result.to_dict() if hasattr(result, "to_dict") else {}
                except Exception as e:
                    logger.debug(f"AI trend analysis failed for {symbol}: {e}")

            timestamp = datetime.now(UTC).isoformat()

            if ai_trends:
                await self.publish_sensor(
                    "ai_trends",
                    ai_trends,
                    {
                        "details": ai_details,
                        "last_updated": timestamp,
                    },
                )

            if ai_confidences:
                await self.publish_sensor(
                    "ai_confidences",
                    ai_confidences,
                    {
                        "last_updated": timestamp,
                    },
                )

            if ai_forecasts:
                await self.publish_sensor(
                    "ai_price_forecasts_24h",
                    ai_forecasts,
                    {
                        "last_updated": timestamp,
                    },
                )

            logger.info(f"AI trend sensors updated for {len(ai_trends)} symbols")

        except ImportError as e:
            logger.debug(f"Trend analyzer not available: {e}")
        except Exception as e:
            logger.error(f"Failed to update AI trend sensors: {e}")

    # === Backward-Compatible Internal Methods ===

    async def _publish_state(self, sensor_id: str, state: Any) -> bool:
        """Internal method to publish sensor state (backward compatible).

        Args:
            sensor_id: Sensor identifier
            state: State value (dict, list, or scalar)

        Returns:
            True if published successfully
        """
        self._cache[sensor_id] = state
        return await self.publish_sensor(sensor_id, state)

    async def _publish_attributes(self, sensor_id: str, attributes: dict) -> bool:
        """Internal method to publish sensor attributes (backward compatible).

        Args:
            sensor_id: Sensor identifier
            attributes: Attributes dictionary

        Returns:
            True if published successfully
        """
        return await self.publisher.update_attributes(sensor_id, attributes)

    def _get_fg_classification(self, value: int | float) -> str:
        """Get Fear & Greed classification label.

        Args:
            value: Fear & Greed index value (0-100)

        Returns:
            Classification label
        """
        if value <= 25:
            return "Extreme Fear"
        elif value <= 45:
            return "Fear"
        elif value <= 55:
            return "Neutral"
        elif value <= 75:
            return "Greed"
        else:
            return "Extreme Greed"

    # === Database Methods ===

    async def update_database_size(self) -> None:
        """Update database size sensor."""
        try:
            import os
            from pathlib import Path

            db_path = Path("data/crypto.db")
            if db_path.exists():
                size_bytes = os.path.getsize(db_path)
                size_mb = round(size_bytes / (1024 * 1024), 2)
                await self.publish_sensor("database_size", size_mb)
        except Exception as e:
            logger.debug(f"Could not get database size: {e}")


# Singleton instance
_manager: HAIntegrationManager | None = None


def get_ha_manager() -> HAIntegrationManager:
    """Get the singleton HAIntegrationManager instance.

    Returns:
        HAIntegrationManager instance
    """
    global _manager
    if _manager is None:
        _manager = HAIntegrationManager()
    return _manager


# Backward compatibility alias
def get_sensors_manager() -> HAIntegrationManager:
    """Backward-compatible alias for get_ha_manager."""
    return get_ha_manager()
