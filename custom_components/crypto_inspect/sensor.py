"""Sensor platform for Crypto Inspect integration."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_LANGUAGE,
    DEFAULT_LANGUAGE,
    DEVICE_MANUFACTURER,
    DEVICE_MODEL,
    DEVICE_NAME,
    DOMAIN,
    SENSOR_TYPE_BOOL,
    SENSOR_TYPE_COUNT,
    SENSOR_TYPE_DICT,
    SENSOR_TYPE_PERCENT,
    SENSOR_TYPE_SCALAR,
    SENSOR_TYPE_STATUS,
    VALUE_TRANSLATIONS,
)
from .coordinator import CryptoInspectCoordinator

if TYPE_CHECKING:
    pass

_LOGGER = logging.getLogger(__name__)

# Sensor definitions with metadata
# Format: sensor_id -> {name, name_ru, icon, unit, device_class, type, category}
SENSOR_DEFINITIONS: dict[str, dict[str, Any]] = {
    # === PRICE ===
    "prices": {
        "name": "Crypto Prices",
        "name_ru": "Крипто цены",
        "icon": "mdi:currency-usd",
        "unit": "USDT",
        "type": SENSOR_TYPE_DICT,
        "category": "price",
    },
    "changes_24h": {
        "name": "24h Changes",
        "name_ru": "Изменение 24ч",
        "icon": "mdi:percent",
        "unit": PERCENTAGE,
        "type": SENSOR_TYPE_DICT,
        "category": "price",
    },
    "volumes_24h": {
        "name": "24h Volumes",
        "name_ru": "Объёмы 24ч",
        "icon": "mdi:chart-bar",
        "unit": "USDT",
        "type": SENSOR_TYPE_DICT,
        "category": "price",
    },
    "highs_24h": {
        "name": "24h Highs",
        "name_ru": "Максимумы 24ч",
        "icon": "mdi:arrow-up-bold",
        "unit": "USDT",
        "type": SENSOR_TYPE_DICT,
        "category": "price",
    },
    "lows_24h": {
        "name": "24h Lows",
        "name_ru": "Минимумы 24ч",
        "icon": "mdi:arrow-down-bold",
        "unit": "USDT",
        "type": SENSOR_TYPE_DICT,
        "category": "price",
    },
    # === MARKET ===
    "fear_greed": {
        "name": "Fear & Greed Index",
        "name_ru": "Индекс страха и жадности",
        "icon": "mdi:emoticon-neutral",
        "type": SENSOR_TYPE_SCALAR,
        "category": "market",
    },
    "btc_dominance": {
        "name": "BTC Dominance",
        "name_ru": "Доминация BTC",
        "icon": "mdi:crown",
        "unit": PERCENTAGE,
        "type": SENSOR_TYPE_PERCENT,
        "category": "market",
    },
    "derivatives": {
        "name": "Derivatives",
        "name_ru": "Деривативы",
        "icon": "mdi:chart-timeline-variant",
        "type": SENSOR_TYPE_DICT,
        "category": "market",
    },
    "altseason_index": {
        "name": "Altseason Index",
        "name_ru": "Индекс альтсезона",
        "icon": "mdi:rocket-launch",
        "type": SENSOR_TYPE_SCALAR,
        "category": "market",
    },
    "altseason_status": {
        "name": "Altseason Status",
        "name_ru": "Статус альтсезона",
        "icon": "mdi:weather-sunny",
        "type": SENSOR_TYPE_STATUS,
        "category": "market",
    },
    "stablecoin_total": {
        "name": "Stablecoin Volume",
        "name_ru": "Объём стейблкоинов",
        "icon": "mdi:currency-usd-circle",
        "type": SENSOR_TYPE_SCALAR,
        "category": "market",
    },
    "stablecoin_flow": {
        "name": "Stablecoin Flow",
        "name_ru": "Поток стейблкоинов",
        "icon": "mdi:swap-horizontal",
        "type": SENSOR_TYPE_STATUS,
        "category": "market",
    },
    "stablecoin_dominance": {
        "name": "Stablecoin Dominance",
        "name_ru": "Доминация стейблкоинов",
        "icon": "mdi:chart-pie",
        "unit": PERCENTAGE,
        "type": SENSOR_TYPE_PERCENT,
        "category": "market",
    },
    # === INVESTOR ===
    "do_nothing_ok": {
        "name": "Do Nothing OK",
        "name_ru": "Можно ничего не делать",
        "icon": "mdi:meditation",
        "type": SENSOR_TYPE_BOOL,
        "category": "investor",
    },
    "investor_phase": {
        "name": "Investor Phase",
        "name_ru": "Фаза рынка",
        "icon": "mdi:chart-timeline-variant-shimmer",
        "type": SENSOR_TYPE_STATUS,
        "category": "investor",
    },
    "calm_indicator": {
        "name": "Calm Indicator",
        "name_ru": "Индикатор спокойствия",
        "icon": "mdi:emoticon-cool",
        "type": SENSOR_TYPE_SCALAR,
        "category": "investor",
    },
    "red_flags": {
        "name": "Red Flags",
        "name_ru": "Красные флаги",
        "icon": "mdi:flag-variant",
        "type": SENSOR_TYPE_COUNT,
        "category": "investor",
    },
    "market_tension": {
        "name": "Market Tension",
        "name_ru": "Напряжённость рынка",
        "icon": "mdi:gauge",
        "type": SENSOR_TYPE_STATUS,
        "category": "investor",
    },
    "price_context": {
        "name": "Price Context",
        "name_ru": "Контекст цены",
        "icon": "mdi:chart-box",
        "type": SENSOR_TYPE_STATUS,
        "category": "investor",
    },
    "dca_result": {
        "name": "DCA Result",
        "name_ru": "Результат DCA",
        "icon": "mdi:cash-check",
        "unit": "EUR",
        "type": SENSOR_TYPE_SCALAR,
        "category": "investor",
    },
    "dca_signal": {
        "name": "DCA Signal",
        "name_ru": "Сигнал DCA",
        "icon": "mdi:cash-plus",
        "type": SENSOR_TYPE_STATUS,
        "category": "investor",
    },
    "weekly_insight": {
        "name": "Weekly Insight",
        "name_ru": "Недельный обзор",
        "icon": "mdi:newspaper-variant",
        "type": SENSOR_TYPE_STATUS,
        "category": "investor",
    },
    # === TECHNICAL ===
    "ta_rsi": {
        "name": "RSI",
        "name_ru": "RSI",
        "icon": "mdi:chart-line",
        "type": SENSOR_TYPE_DICT,
        "category": "technical",
    },
    "ta_macd_signal": {
        "name": "MACD Signal",
        "name_ru": "Сигнал MACD",
        "icon": "mdi:chart-bell-curve",
        "type": SENSOR_TYPE_DICT,
        "category": "technical",
    },
    "ta_bb_position": {
        "name": "Bollinger Position",
        "name_ru": "Позиция Боллинджера",
        "icon": "mdi:chart-line-variant",
        "type": SENSOR_TYPE_DICT,
        "category": "technical",
    },
    "ta_trend": {
        "name": "Trend",
        "name_ru": "Тренд",
        "icon": "mdi:trending-up",
        "type": SENSOR_TYPE_DICT,
        "category": "technical",
    },
    "ta_support": {
        "name": "Support Levels",
        "name_ru": "Уровни поддержки",
        "icon": "mdi:arrow-collapse-down",
        "type": SENSOR_TYPE_DICT,
        "category": "technical",
    },
    "ta_resistance": {
        "name": "Resistance Levels",
        "name_ru": "Уровни сопротивления",
        "icon": "mdi:arrow-collapse-up",
        "type": SENSOR_TYPE_DICT,
        "category": "technical",
    },
    "ta_confluence": {
        "name": "TA Confluence",
        "name_ru": "Конфлюенция ТА",
        "icon": "mdi:chart-scatter-plot",
        "type": SENSOR_TYPE_DICT,
        "category": "technical",
    },
    "divergences_active": {
        "name": "Active Divergences",
        "name_ru": "Активные дивергенции",
        "icon": "mdi:compare-horizontal",
        "type": SENSOR_TYPE_COUNT,
        "category": "technical",
    },
    # === VOLATILITY ===
    "volatility_30d": {
        "name": "30d Volatility",
        "name_ru": "Волатильность 30д",
        "icon": "mdi:chart-sankey",
        "type": SENSOR_TYPE_DICT,
        "category": "volatility",
    },
    "volatility_percentile": {
        "name": "Volatility Percentile",
        "name_ru": "Перцентиль волатильности",
        "icon": "mdi:percent-box",
        "unit": PERCENTAGE,
        "type": SENSOR_TYPE_PERCENT,
        "category": "volatility",
    },
    "volatility_status": {
        "name": "Volatility Status",
        "name_ru": "Статус волатильности",
        "icon": "mdi:speedometer",
        "type": SENSOR_TYPE_STATUS,
        "category": "volatility",
    },
    # === GAS ===
    "eth_gas_slow": {
        "name": "ETH Gas (Slow)",
        "name_ru": "Gas ETH (Медленный)",
        "icon": "mdi:gas-station",
        "unit": "Gwei",
        "type": SENSOR_TYPE_SCALAR,
        "category": "gas",
    },
    "eth_gas_standard": {
        "name": "ETH Gas (Standard)",
        "name_ru": "Gas ETH (Стандарт)",
        "icon": "mdi:gas-station",
        "unit": "Gwei",
        "type": SENSOR_TYPE_SCALAR,
        "category": "gas",
    },
    "eth_gas_fast": {
        "name": "ETH Gas (Fast)",
        "name_ru": "Gas ETH (Быстрый)",
        "icon": "mdi:gas-station",
        "unit": "Gwei",
        "type": SENSOR_TYPE_SCALAR,
        "category": "gas",
    },
    "eth_gas_status": {
        "name": "ETH Gas Status",
        "name_ru": "Статус Gas ETH",
        "icon": "mdi:gas-station-outline",
        "type": SENSOR_TYPE_STATUS,
        "category": "gas",
    },
    # === ML ===
    "ml_latest_predictions": {
        "name": "ML Predictions",
        "name_ru": "ML Прогнозы",
        "icon": "mdi:brain",
        "type": SENSOR_TYPE_DICT,
        "category": "ml",
    },
    "ml_system_status": {
        "name": "ML System Status",
        "name_ru": "Статус системы ML",
        "icon": "mdi:chip",
        "type": SENSOR_TYPE_STATUS,
        "category": "ml",
    },
    "ml_market_confidence": {
        "name": "ML Market Confidence",
        "name_ru": "ML Уверенность рынка",
        "icon": "mdi:chart-areaspline",
        "unit": PERCENTAGE,
        "type": SENSOR_TYPE_PERCENT,
        "category": "ml",
    },
    "ml_accuracy_rate": {
        "name": "ML Accuracy",
        "name_ru": "Точность ML",
        "icon": "mdi:target",
        "unit": PERCENTAGE,
        "type": SENSOR_TYPE_PERCENT,
        "category": "ml",
    },
    "ml_correct_predictions": {
        "name": "ML Correct Predictions",
        "name_ru": "ML Верные прогнозы",
        "icon": "mdi:check-circle",
        "type": SENSOR_TYPE_COUNT,
        "category": "ml",
    },
    # === PORTFOLIO ===
    "portfolio_value": {
        "name": "Portfolio Value",
        "name_ru": "Стоимость портфеля",
        "icon": "mdi:wallet",
        "unit": "USD",
        "device_class": SensorDeviceClass.MONETARY,
        "type": SENSOR_TYPE_SCALAR,
        "category": "portfolio",
    },
    "portfolio_pnl_percent": {
        "name": "Portfolio PnL",
        "name_ru": "PnL портфеля",
        "icon": "mdi:chart-line",
        "unit": PERCENTAGE,
        "type": SENSOR_TYPE_PERCENT,
        "category": "portfolio",
    },
    "portfolio_allocation": {
        "name": "Portfolio Allocation",
        "name_ru": "Распределение портфеля",
        "icon": "mdi:chart-pie",
        "type": SENSOR_TYPE_DICT,
        "category": "portfolio",
    },
    "portfolio_health": {
        "name": "Portfolio Health",
        "name_ru": "Здоровье портфеля",
        "icon": "mdi:heart-pulse",
        "type": SENSOR_TYPE_STATUS,
        "category": "portfolio",
    },
    "goal_progress_percent": {
        "name": "Goal Progress",
        "name_ru": "Прогресс цели",
        "icon": "mdi:flag-checkered",
        "unit": PERCENTAGE,
        "type": SENSOR_TYPE_PERCENT,
        "category": "portfolio",
    },
    # === RISK ===
    "sharpe_ratio": {
        "name": "Sharpe Ratio",
        "name_ru": "Коэф. Шарпа",
        "icon": "mdi:chart-bell-curve-cumulative",
        "type": SENSOR_TYPE_SCALAR,
        "category": "risk",
    },
    "sortino_ratio": {
        "name": "Sortino Ratio",
        "name_ru": "Коэф. Сортино",
        "icon": "mdi:chart-bell-curve",
        "type": SENSOR_TYPE_SCALAR,
        "category": "risk",
    },
    "max_drawdown_percent": {
        "name": "Max Drawdown",
        "name_ru": "Макс. просадка",
        "icon": "mdi:trending-down",
        "unit": PERCENTAGE,
        "type": SENSOR_TYPE_PERCENT,
        "category": "risk",
    },
    "value_at_risk": {
        "name": "Value at Risk",
        "name_ru": "VaR",
        "icon": "mdi:alert-circle",
        "unit": "USD",
        "type": SENSOR_TYPE_SCALAR,
        "category": "risk",
    },
    "portfolio_risk_level": {
        "name": "Risk Level",
        "name_ru": "Уровень риска",
        "icon": "mdi:shield-alert",
        "type": SENSOR_TYPE_STATUS,
        "category": "risk",
    },
    # === WHALES ===
    "whale_alerts_24h": {
        "name": "Whale Alerts 24h",
        "name_ru": "Киты 24ч",
        "icon": "mdi:fish",
        "type": SENSOR_TYPE_COUNT,
        "category": "whales",
    },
    "whale_net_flow": {
        "name": "Whale Net Flow",
        "name_ru": "Чистый поток китов",
        "icon": "mdi:swap-horizontal-bold",
        "type": SENSOR_TYPE_DICT,
        "category": "whales",
    },
    "whale_signal": {
        "name": "Whale Signal",
        "name_ru": "Сигнал китов",
        "icon": "mdi:fish",
        "type": SENSOR_TYPE_STATUS,
        "category": "whales",
    },
    # === EXCHANGE ===
    "exchange_netflows": {
        "name": "Exchange Netflows",
        "name_ru": "Потоки бирж",
        "icon": "mdi:bank-transfer",
        "type": SENSOR_TYPE_DICT,
        "category": "exchange",
    },
    # === DIAGNOSTIC ===
    "sync_status": {
        "name": "Sync Status",
        "name_ru": "Статус синхронизации",
        "icon": "mdi:sync",
        "type": SENSOR_TYPE_STATUS,
        "category": "diagnostic",
        "entity_category": "diagnostic",
    },
    "last_sync": {
        "name": "Last Sync",
        "name_ru": "Последняя синхронизация",
        "icon": "mdi:clock-check",
        "device_class": SensorDeviceClass.TIMESTAMP,
        "type": SENSOR_TYPE_SCALAR,
        "category": "diagnostic",
        "entity_category": "diagnostic",
    },
    "buffer_size": {
        "name": "Buffer Size",
        "name_ru": "Размер буфера",
        "icon": "mdi:database",
        "unit": "candles",
        "type": SENSOR_TYPE_COUNT,
        "category": "diagnostic",
        "entity_category": "diagnostic",
    },
    "candles_count": {
        "name": "Candles Count",
        "name_ru": "Количество свечей",
        "icon": "mdi:database-check",
        "unit": "candles",
        "type": SENSOR_TYPE_COUNT,
        "category": "diagnostic",
        "entity_category": "diagnostic",
    },
    # === TRADITIONAL ===
    "gold_price": {
        "name": "Gold Price",
        "name_ru": "Цена золота",
        "icon": "mdi:gold",
        "unit": "USD",
        "type": SENSOR_TYPE_SCALAR,
        "category": "traditional",
    },
    "sp500_index": {
        "name": "S&P 500",
        "name_ru": "S&P 500",
        "icon": "mdi:chart-line",
        "type": SENSOR_TYPE_SCALAR,
        "category": "traditional",
    },
    "vix_index": {
        "name": "VIX Index",
        "name_ru": "Индекс VIX",
        "icon": "mdi:chart-scatter-plot",
        "type": SENSOR_TYPE_SCALAR,
        "category": "traditional",
    },
    "usd_index": {
        "name": "USD Index",
        "name_ru": "Индекс USD",
        "icon": "mdi:currency-usd",
        "type": SENSOR_TYPE_SCALAR,
        "category": "traditional",
    },
    # === SMART SUMMARY ===
    "market_pulse": {
        "name": "Market Pulse",
        "name_ru": "Пульс рынка",
        "icon": "mdi:pulse",
        "type": SENSOR_TYPE_STATUS,
        "category": "smart_summary",
    },
    "market_pulse_confidence": {
        "name": "Pulse Confidence",
        "name_ru": "Уверенность пульса",
        "icon": "mdi:percent",
        "unit": PERCENTAGE,
        "type": SENSOR_TYPE_PERCENT,
        "category": "smart_summary",
    },
    "today_action": {
        "name": "Today's Action",
        "name_ru": "Действие на сегодня",
        "icon": "mdi:clipboard-check",
        "type": SENSOR_TYPE_STATUS,
        "category": "smart_summary",
    },
    "profit_action": {
        "name": "Profit Action",
        "name_ru": "Действие по прибыли",
        "icon": "mdi:cash-multiple",
        "type": SENSOR_TYPE_STATUS,
        "category": "smart_summary",
    },
    # === AI ===
    "ai_daily_summary": {
        "name": "AI Daily Summary",
        "name_ru": "AI Дневной обзор",
        "icon": "mdi:robot",
        "type": SENSOR_TYPE_STATUS,
        "category": "ai",
    },
    "ai_market_sentiment": {
        "name": "AI Market Sentiment",
        "name_ru": "AI Настроение рынка",
        "icon": "mdi:robot-outline",
        "type": SENSOR_TYPE_STATUS,
        "category": "ai",
    },
    "ai_recommendation": {
        "name": "AI Recommendation",
        "name_ru": "AI Рекомендация",
        "icon": "mdi:lightbulb-on",
        "type": SENSOR_TYPE_STATUS,
        "category": "ai",
    },
    "ai_trends": {
        "name": "AI Trends",
        "name_ru": "AI Тренды",
        "icon": "mdi:trending-up",
        "type": SENSOR_TYPE_DICT,
        "category": "ai",
    },
    "ai_confidences": {
        "name": "AI Confidences",
        "name_ru": "AI Уверенность",
        "icon": "mdi:gauge",
        "type": SENSOR_TYPE_DICT,
        "category": "ai",
    },
    "ai_price_forecasts_24h": {
        "name": "AI Price Forecasts 24h",
        "name_ru": "AI Прогнозы цен 24ч",
        "icon": "mdi:crystal-ball",
        "type": SENSOR_TYPE_DICT,
        "category": "ai",
    },
    # === BYBIT ===
    "bybit_portfolio_value": {
        "name": "Bybit Portfolio",
        "name_ru": "Портфель Bybit",
        "icon": "mdi:bank",
        "unit": "USD",
        "device_class": SensorDeviceClass.MONETARY,
        "type": SENSOR_TYPE_SCALAR,
        "category": "bybit",
    },
    "bybit_positions_count": {
        "name": "Bybit Positions",
        "name_ru": "Позиции Bybit",
        "icon": "mdi:format-list-numbered",
        "type": SENSOR_TYPE_COUNT,
        "category": "bybit",
    },
    "bybit_pnl": {
        "name": "Bybit PnL",
        "name_ru": "PnL Bybit",
        "icon": "mdi:chart-line",
        "unit": "USD",
        "type": SENSOR_TYPE_SCALAR,
        "category": "bybit",
    },
    "bybit_status": {
        "name": "Bybit Status",
        "name_ru": "Статус Bybit",
        "icon": "mdi:connection",
        "type": SENSOR_TYPE_STATUS,
        "category": "bybit",
    },
    # === ECONOMIC ===
    "economic_week_risk": {
        "name": "Economic Week Risk",
        "name_ru": "Экон. риск недели",
        "icon": "mdi:calendar-alert",
        "type": SENSOR_TYPE_STATUS,
        "category": "economic",
    },
    "fomc_days_to_meeting": {
        "name": "Days to FOMC",
        "name_ru": "Дней до FOMC",
        "icon": "mdi:calendar-clock",
        "unit": "days",
        "type": SENSOR_TYPE_COUNT,
        "category": "economic",
    },
    "macro_risk_level": {
        "name": "Macro Risk Level",
        "name_ru": "Макро уровень риска",
        "icon": "mdi:alert-octagon",
        "type": SENSOR_TYPE_STATUS,
        "category": "economic",
    },
    # === ALERTS ===
    "pending_alerts_count": {
        "name": "Pending Alerts",
        "name_ru": "Ожидающие оповещения",
        "icon": "mdi:bell-badge",
        "type": SENSOR_TYPE_COUNT,
        "category": "alerts",
    },
    "adaptive_volatilities": {
        "name": "Adaptive Volatilities",
        "name_ru": "Адаптивные волатильности",
        "icon": "mdi:tune-variant",
        "type": SENSOR_TYPE_DICT,
        "category": "alerts",
    },
    # === CORRELATION ===
    "correlation_btc_eth": {
        "name": "BTC-ETH Correlation",
        "name_ru": "Корреляция BTC-ETH",
        "icon": "mdi:link-variant",
        "type": SENSOR_TYPE_SCALAR,
        "category": "correlation",
    },
    "correlation_btc_sp500": {
        "name": "BTC-S&P500 Correlation",
        "name_ru": "Корреляция BTC-S&P500",
        "icon": "mdi:link-variant",
        "type": SENSOR_TYPE_SCALAR,
        "category": "correlation",
    },
    "dominant_pattern": {
        "name": "Dominant Pattern",
        "name_ru": "Доминирующий паттерн",
        "icon": "mdi:shape",
        "type": SENSOR_TYPE_STATUS,
        "category": "correlation",
    },
    # === BACKTEST ===
    "backtest_dca_roi": {
        "name": "Backtest DCA ROI",
        "name_ru": "Бэктест DCA ROI",
        "icon": "mdi:history",
        "unit": PERCENTAGE,
        "type": SENSOR_TYPE_PERCENT,
        "category": "backtest",
    },
    "backtest_best_strategy": {
        "name": "Best Strategy",
        "name_ru": "Лучшая стратегия",
        "icon": "mdi:trophy",
        "type": SENSOR_TYPE_STATUS,
        "category": "backtest",
    },
    # === LIQUIDATION ===
    "liquidation_levels": {
        "name": "Liquidation Levels",
        "name_ru": "Уровни ликвидаций",
        "icon": "mdi:skull-crossbones",
        "type": SENSOR_TYPE_DICT,
        "category": "misc",
    },
    "liquidation_risk": {
        "name": "Liquidation Risk",
        "name_ru": "Риск ликвидаций",
        "icon": "mdi:alert-decagram",
        "type": SENSOR_TYPE_STATUS,
        "category": "misc",
    },
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Crypto Inspect sensors from a config entry."""
    coordinator: CryptoInspectCoordinator = hass.data[DOMAIN][entry.entry_id]
    language = entry.data.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)

    entities: list[CryptoInspectSensor] = []

    # Create sensors from definitions
    for sensor_id, definition in SENSOR_DEFINITIONS.items():
        entities.append(
            CryptoInspectSensor(
                coordinator=coordinator,
                sensor_id=sensor_id,
                definition=definition,
                language=language,
            )
        )

    # Also create sensors from registry if available
    for sensor_id in coordinator.get_available_sensors():
        if sensor_id not in SENSOR_DEFINITIONS:
            # Dynamic sensor from registry
            metadata = coordinator.get_sensor_metadata(sensor_id)
            if metadata:
                entities.append(
                    CryptoInspectSensor(
                        coordinator=coordinator,
                        sensor_id=sensor_id,
                        definition=metadata,
                        language=language,
                    )
                )

    async_add_entities(entities)
    _LOGGER.info("Added %d Crypto Inspect sensors", len(entities))


class CryptoInspectSensor(CoordinatorEntity[CryptoInspectCoordinator], SensorEntity):
    """Representation of a Crypto Inspect sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: CryptoInspectCoordinator,
        sensor_id: str,
        definition: dict[str, Any],
        language: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)

        self._sensor_id = sensor_id
        self._definition = definition
        self._language = language

        # Entity attributes
        self._attr_unique_id = f"crypto_inspect_{sensor_id}"

        # Use localized name based on language
        if language == "ru" and "name_ru" in definition:
            self._attr_name = definition["name_ru"]
        else:
            self._attr_name = definition.get("name", sensor_id)

        self._attr_icon = definition.get("icon", "mdi:help-circle")

        # Unit of measurement
        if unit := definition.get("unit"):
            self._attr_native_unit_of_measurement = unit

        # Device class
        if device_class := definition.get("device_class"):
            self._attr_device_class = device_class

        # State class for numeric values
        sensor_type = definition.get("type", SENSOR_TYPE_SCALAR)
        if sensor_type in (SENSOR_TYPE_SCALAR, SENSOR_TYPE_COUNT, SENSOR_TYPE_PERCENT):
            self._attr_state_class = SensorStateClass.MEASUREMENT

        # Entity category
        if entity_category := definition.get("entity_category"):
            self._attr_entity_category = entity_category

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, "crypto_inspect")},
            name=DEVICE_NAME,
            manufacturer=DEVICE_MANUFACTURER,
            model=DEVICE_MODEL,
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        value = self.coordinator.get_sensor_value(self._sensor_id)

        if value is None:
            return None

        sensor_type = self._definition.get("type", SENSOR_TYPE_SCALAR)

        # Handle dict type - convert to JSON string for HA state
        if sensor_type == SENSOR_TYPE_DICT and isinstance(value, dict):
            return json.dumps(value, ensure_ascii=False)

        # Translate status values
        if sensor_type == SENSOR_TYPE_STATUS and isinstance(value, str):
            return self._translate_value(value)

        # Handle bool type
        if sensor_type == SENSOR_TYPE_BOOL:
            if isinstance(value, bool):
                return self._translate_value("Yes" if value else "No")
            return self._translate_value(str(value))

        return value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        attrs = self.coordinator.get_sensor_attributes(self._sensor_id)

        # Add sensor metadata
        attrs["sensor_type"] = self._definition.get("type", SENSOR_TYPE_SCALAR)
        attrs["category"] = self._definition.get("category", "misc")

        # For dict sensors, add the raw data as attribute
        value = self.coordinator.get_sensor_value(self._sensor_id)
        if isinstance(value, dict):
            attrs["data"] = value

        return attrs

    def _translate_value(self, value: str) -> str:
        """Translate sensor value based on language setting."""
        if value in VALUE_TRANSLATIONS:
            return VALUE_TRANSLATIONS[value].get(self._language, value)
        return value

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
