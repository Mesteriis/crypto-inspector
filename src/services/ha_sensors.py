"""Crypto sensors for Home Assistant using Supervisor API.

This module manages crypto-related sensors that are created and updated
through Home Assistant Supervisor REST API.

Sensors use dictionary format to support multiple trading pairs:
- sensor.crypto_inspect_prices: {"BTC/USDT": 100000, "ETH/USDT": 3500}
- sensor.crypto_inspect_changes: {"BTC/USDT": 2.5, "ETH/USDT": -1.2}
"""

import json
import logging
import os
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from core.config import settings
from core.constants import APP_VERSION, DEFAULT_SYMBOLS
from services.ha_integration import get_supervisor_client

logger = logging.getLogger(__name__)


async def get_sensor_language() -> str:
    """Get current sensor language preference from input_select helper.
    
    Returns:
        'en' or 'ru' based on user selection
    """
    from services.ha_integration import get_supervisor_client
    
    client = get_supervisor_client()
    if not client.is_available:
        return "ru"  # Default to Russian
    
    try:
        # Get the state of the language selector
        http_client = await client._get_client()
        response = await http_client.get("/core/api/states/input_select.crypto_sensor_language")
        
        if response.status_code == 200:
            data = response.json()
            selected_option = data.get("state", "Russian")
            # Convert Russian/English to ru/en
            return "ru" if selected_option == "Russian" else "en"
        else:
            logger.debug(f"Language selector not found, using default Russian")
            return "ru"
    except Exception as e:
        logger.debug(f"Could not get sensor language, using default: {e}")
        return "ru"


def get_localized_sensor_name(sensor_config: dict, language: str) -> str:
    """Get localized sensor name based on language preference.
    
    Args:
        sensor_config: Sensor configuration dictionary
        language: Language code ('en' or 'ru')
    
    Returns:
        Localized sensor name
    """
    if language == "ru" and "name_ru" in sensor_config:
        return sensor_config["name_ru"]
    else:
        return sensor_config["name"]


def get_symbols() -> list[str]:
    """Get trading symbols from environment (deprecated - use get_currency_list instead)."""
    symbols_env = os.environ.get("HA_SYMBOLS", "BTC/USDT,ETH/USDT")
    return [s.strip() for s in symbols_env.split(",") if s.strip()]


def get_currency_list() -> list[str]:
    """Get the dynamic currency list from Home Assistant input_select helper.
    
    This is the single source of truth for currency selections across the application.
    Falls back to environment variable or defaults if helper is not available.
    
    Returns:
        List of currency symbols (e.g., ["BTC/USDT", "ETH/USDT"])
    """
    try:
        # Try to get from HA input_select helper
        supervisor_client = get_supervisor_client()
        if supervisor_client.is_available:
            # In a real implementation, we would fetch the current value from the helper
            # For now, we'll fall back to the environment/default approach
            # This would be implemented when we have the HA API integration
            pass
    except Exception:
        pass
    
    # Fallback to environment variable
    symbols_env = os.environ.get("HA_SYMBOLS", "")
    if symbols_env:
        return [s.strip() for s in symbols_env.split(",") if s.strip()]
    
    # Fallback to default symbols
    return DEFAULT_SYMBOLS.copy()


class CryptoSensorsManager:
    """
    Manages crypto sensors for Home Assistant using Supervisor API.

    Creates and updates aggregated sensors that contain data for all trading pairs
    in dictionary format, making it easy to use in HA templates.
    """

    DEVICE_ID = "crypto_inspect"
    DEVICE_NAME = "Crypto Inspect"
    ENTITY_PREFIX = "sensor.crypto_inspect_"

    # Sensor definitions (English names with Russian translations)
    SENSORS = {
        # === Цены (dict формат: ключ=монета, значение=цена) ===
        "prices": {
            "name": "Crypto Prices",
            "name_ru": "Крипто цены",
            "icon": "mdi:currency-usd",
            "unit": "USDT",
            "description": 'Current prices of all coins. Format: {"BTC": 95000, "ETH": 3200}',
            "description_ru": 'Текущие цены всех монет. Формат: {"BTC": 95000, "ETH": 3200}',
        },
        "changes_24h": {
            "name": "24h Change",
            "name_ru": "Изменение 24ч",
            "icon": "mdi:percent",
            "unit": "%",
            "description": 'Price change over 24 hours (%). Format: {"BTC": 2.5}',
            "description_ru": 'Изменение цены за 24 часа (%). Формат: {"BTC": 2.5}',
        },
        "volumes_24h": {
            "name": "24h Volumes",
            "name_ru": "Объёмы 24ч",
            "icon": "mdi:chart-bar",
            "unit": "USDT",
            "description": 'Trading volume over 24 hours. Format: {"BTC": 50000000000}',
            "description_ru": 'Объём торгов за 24 часа. Формат: {"BTC": 50000000000}',
        },
        "highs_24h": {
            "name": "24h Highs",
            "name_ru": "Максимумы 24ч",
            "icon": "mdi:arrow-up-bold",
            "unit": "USDT",
            "description": 'Highest price over 24 hours. Format: {"BTC": 96000}',
            "description_ru": 'Максимальная цена за 24 часа. Формат: {"BTC": 96000}',
        },
        "lows_24h": {
            "name": "24h Lows",
            "name_ru": "Минимумы 24ч",
            "icon": "mdi:arrow-down-bold",
            "unit": "USDT",
            "description": 'Lowest price over 24 hours. Format: {"BTC": 94000}',
            "description_ru": 'Минимальная цена за 24 часа. Формат: {"BTC": 94000}',
        },
        # === Ленивый инвестор ===
        "do_nothing_ok": {
            "name": "Do Nothing OK",
            "name_ru": "Можно ничего не делать",
            "icon": "mdi:meditation",
            "description": "Yes/No - whether you can just hold now",
            "description_ru": "Да/Нет - можно ли сейчас просто держать",
        },
        "investor_phase": {
            "name": "Investor Phase",
            "name_ru": "Фаза рынка",
            "icon": "mdi:chart-timeline-variant-shimmer",
            "description": "Phase: Accumulation/Growth/Euphoria/Correction/Capitulation",
            "description_ru": "Фаза: Накопление/Рост/Эйфория/Коррекция/Капитуляция",
        },
        "calm_indicator": {
            "name": "Calm Indicator",
            "name_ru": "Индикатор спокойствия",
            "icon": "mdi:emoticon-cool",
            "description": "How calm the market is (0-100)",
            "description_ru": "Насколько спокоен рынок (0-100)",
        },
        "red_flags": {
            "name": "Red Flags",
            "name_ru": "Красные флаги",
            "icon": "mdi:flag-variant",
            "description": "Number of warning signals",
            "description_ru": "Количество предупреждающих сигналов",
        },
        "market_tension": {
            "name": "Market Tension",
            "name_ru": "Напряжённость рынка",
            "icon": "mdi:gauge",
            "description": "Level of market tension",
            "description_ru": "Уровень напряжённости рынка",
        },
        "price_context": {
            "name": "Price Context",
            "name_ru": "Контекст цены",
            "icon": "mdi:chart-box",
            "description": "Current price position relative to ATH/ATL",
            "description_ru": "Позиция текущей цены относительно ATH/ATL",
        },
        "dca_result": {
            "name": "DCA Result",
            "name_ru": "Результат DCA",
            "icon": "mdi:cash-check",
            "unit": "€",
            "description": "Recommended amount for DCA",
            "description_ru": "Рекомендуемая сумма для DCA",
        },
        "dca_signal": {
            "name": "DCA Signal",
            "name_ru": "Сигнал DCA",
            "icon": "mdi:cash-plus",
            "description": "Buy signal: Buy/Wait/Do not buy",
            "description_ru": "Сигнал для покупки: Покупать/Ждать/Не покупать",
        },
        "weekly_insight": {
            "name": "Weekly Insight",
            "name_ru": "Недельный обзор",
            "icon": "mdi:newspaper-variant",
            "description": "Brief market overview for the week",
            "description_ru": "Краткий обзор рынка за неделю",
        },
        "next_action_timer": {
            "name": "Next Action Timer",
            "name_ru": "Таймер действия",
            "icon": "mdi:timer-outline",
            "description": "Time until next check",
            "description_ru": "Время до следующей проверки",
        },
        # === Рыночные индикаторы ===
        "fear_greed": {
            "name": "Fear & Greed Index",
            "name_ru": "Индекс страха и жадности",
            "icon": "mdi:emoticon-neutral",
            "description": "Fear & Greed Index (0-100). 0=fear, 100=greed",
            "description_ru": "Fear & Greed Index (0-100). 0=страх, 100=жадность",
        },
        "btc_dominance": {
            "name": "BTC Dominance",
            "name_ru": "Доминация BTC",
            "icon": "mdi:crown",
            "unit": "%",
            "description": "Bitcoin share in the market (%)",
            "description_ru": "Доля Bitcoin на рынке (%)",
        },
        "derivatives": {
            "name": "Derivatives",
            "name_ru": "Деривативы",
            "icon": "mdi:chart-timeline-variant",
            "description": "Futures and options data",
            "description_ru": "Данные по фьючерсам и опционам",
        },
        # === Альтсезон и стейблкоины ===
        "altseason_index": {
            "name": "Altseason Index",
            "name_ru": "Индекс альтсезона",
            "icon": "mdi:rocket-launch",
            "description": "Altcoin season index (0-100)",
            "description_ru": "Индекс альткоин сезона (0-100)",
        },
        "altseason_status": {
            "name": "Altseason Status",
            "name_ru": "Статус альтсезона",
            "icon": "mdi:weather-sunny",
            "description": "Bitcoin season / Altseason / Neutral",
            "description_ru": "Биткоин сезон / Альтсезон / Нейтрально",
        },
        "stablecoin_total": {
            "name": "Stablecoin Volume",
            "name_ru": "Объём стейблкоинов",
            "icon": "mdi:currency-usd-circle",
            "description": "Total stablecoin volume in the market",
            "description_ru": "Общий объём стейблкоинов на рынке",
        },
        "stablecoin_flow": {
            "name": "Stablecoin Flow",
            "name_ru": "Поток стейблкоинов",
            "icon": "mdi:swap-horizontal",
            "description": "Inflow/outflow of stablecoins to exchanges",
            "description_ru": "Приток/отток стейблкоинов на биржи",
        },
        "stablecoin_dominance": {
            "name": "Stablecoin Dominance",
            "name_ru": "Доминация стейблкоинов",
            "icon": "mdi:chart-pie",
            "unit": "%",
            "description": "Share of stablecoins in the market (%)",
            "description_ru": "Доля стейблкоинов на рынке (%)",
        },
        # === Gas Tracker ===
        "eth_gas_slow": {
            "name": "ETH Gas Slow",
            "name_ru": "ETH Gas медленный",
            "icon": "mdi:speedometer-slow",
            "unit": "Gwei",
            "description": "Gas price for slow transactions",
            "description_ru": "Цена газа для медленных транзакций",
        },
        "eth_gas_standard": {
            "name": "ETH Gas Standard",
            "name_ru": "ETH Gas стандартный",
            "icon": "mdi:speedometer-medium",
            "unit": "Gwei",
            "description": "Gas price for standard transactions",
            "description_ru": "Цена газа для стандартных транзакций",
        },
        "eth_gas_fast": {
            "name": "ETH Gas Fast",
            "name_ru": "ETH Gas быстрый",
            "icon": "mdi:speedometer",
            "unit": "Gwei",
            "description": "Gas price for fast transactions",
            "description_ru": "Цена газа для быстрых транзакций",
        },
        "eth_gas_status": {
            "name": "ETH Gas Status",
            "name_ru": "Статус ETH Gas",
            "icon": "mdi:gas-station",
            "description": "Current network status: low/medium/high",
            "description_ru": "Текущий статус сети: низкий/средний/высокий",
        },
        # === Активность китов ===
        "whale_alerts_24h": {
            "name": "Whale Alerts 24h",
            "name_ru": "Алерты китов 24ч",
            "icon": "mdi:fish",
            "description": "Number of large transactions in 24h",
            "description_ru": "Количество крупных транзакций за 24ч",
        },
        "whale_net_flow": {
            "name": "Whale Net Flow",
            "name_ru": "Нетто-поток китов",
            "icon": "mdi:arrow-decision",
            "description": "Net inflow/outflow from large wallets",
            "description_ru": "Чистый приток/отток от крупных кошельков",
        },
        "whale_last_alert": {
            "name": "Last Whale Alert",
            "name_ru": "Последний алерт кита",
            "icon": "mdi:bell-ring",
            "description": "Last large transaction",
            "description_ru": "Последняя крупная транзакция",
        },
        # === Потоки на биржи (dict формат) ===
        "exchange_netflows": {
            "name": "Exchange Netflows",
            "name_ru": "Потоки на биржи",
            "icon": "mdi:bank-transfer",
            "description": 'Net flows to exchanges. Format: {"BTC": -500, "ETH": 200}',
            "description_ru": 'Нетто-потоки на биржи. Формат: {"BTC": -500, "ETH": 200}',
        },
        "exchange_flow_signal": {
            "name": "Flow Signal",
            "name_ru": "Сигнал потоков",
            "icon": "mdi:trending-up",
            "description": "Signal: accumulation/distribution/neutral",
            "description_ru": "Сигнал: накопление/распределение/нейтрально",
        },
        # === Ликвидации (dict формат) ===
        "liq_levels": {
            "name": "Liquidation Levels",
            "name_ru": "Уровни ликвидаций",
            "icon": "mdi:arrow-expand-vertical",
            "description": "Price levels of mass liquidations",
            "description_ru": "Ценовые уровни массовых ликвидаций",
        },
        "liq_risk_level": {
            "name": "Liquidation Risk",
            "name_ru": "Риск ликвидаций",
            "icon": "mdi:alert-decagram",
            "description": "Risk level: low/medium/high",
            "description_ru": "Уровень риска: низкий/средний/высокий",
        },
        # === Портфель ===
        "portfolio_value": {
            "name": "Portfolio Value",
            "name_ru": "Стоимость портфеля",
            "icon": "mdi:wallet",
            "unit": "USDT",
            "description": "Total portfolio value",
            "description_ru": "Общая стоимость портфеля",
        },
        "portfolio_pnl": {
            "name": "Portfolio P&L",
            "name_ru": "Прибыль/Убыток",
            "icon": "mdi:chart-line",
            "unit": "%",
            "description": "Total portfolio profit/loss (%)",
            "description_ru": "Общий P&L портфеля (%)",
        },
        "portfolio_pnl_24h": {
            "name": "Portfolio 24h Change",
            "name_ru": "Портфель изм. 24ч",
            "icon": "mdi:chart-areaspline",
            "unit": "%",
            "description": "Portfolio change over 24 hours (%)",
            "description_ru": "Изменение портфеля за 24 часа (%)",
        },
        "portfolio_allocation": {
            "name": "Portfolio Allocation",
            "name_ru": "Распределение",
            "icon": "mdi:chart-donut",
            "description": "Asset allocation in portfolio",
            "description_ru": "Распределение активов в портфеле",
        },
        # === Алерты ===
        "active_alerts_count": {
            "name": "Active Alerts Count",
            "name_ru": "Активные алерты",
            "icon": "mdi:bell-badge",
            "description": "Number of active notifications",
            "description_ru": "Количество активных оповещений",
        },
        "triggered_alerts_24h": {
            "name": "Triggered Alerts 24h",
            "name_ru": "Сработавшие алерты 24ч",
            "icon": "mdi:bell-check",
            "description": "Alerts in the last 24 hours",
            "description_ru": "Алерты за последние 24 часа",
        },
        # === Дивергенции (dict формат) ===
        "divergences": {
            "name": "Divergences",
            "name_ru": "Дивергенции",
            "icon": "mdi:call-split",
            "description": "Price and indicator divergences",
            "description_ru": "Расхождения цены и индикаторов",
        },
        "divergences_active": {
            "name": "Active Divergences",
            "name_ru": "Активные дивергенции",
            "icon": "mdi:call-merge",
            "description": "Number of active divergences",
            "description_ru": "Количество активных дивергенций",
        },
        # === Сигналы ===
        "signals_win_rate": {
            "name": "Signals Win Rate",
            "name_ru": "Винрейт сигналов",
            "icon": "mdi:trophy",
            "unit": "%",
            "description": "Percentage of successful signals",
            "description_ru": "Процент успешных сигналов",
        },
        "signals_today": {
            "name": "Today's Signals",
            "name_ru": "Сигналы сегодня",
            "icon": "mdi:signal",
            "description": "Number of signals today",
            "description_ru": "Количество сигналов за сегодня",
        },
        "signals_last": {
            "name": "Last Signal",
            "name_ru": "Последний сигнал",
            "icon": "mdi:traffic-light",
            "description": "Last trading signal",
            "description_ru": "Последний торговый сигнал",
        },
        # === Bybit биржа ===
        "bybit_balance": {
            "name": "Bybit Balance",
            "name_ru": "Баланс Bybit",
            "icon": "mdi:wallet",
            "unit": "USDT",
            "description": "Bybit trading account balance",
            "description_ru": "Баланс торгового счёта Bybit",
        },
        "bybit_pnl_24h": {
            "name": "Bybit P&L 24h",
            "name_ru": "Bybit P&L 24ч",
            "icon": "mdi:chart-line",
            "unit": "%",
            "description": "Profit/loss over 24 hours",
            "description_ru": "Прибыль/убыток за 24 часа",
        },
        "bybit_pnl_7d": {
            "name": "Bybit P&L 7d",
            "name_ru": "Bybit P&L 7д",
            "icon": "mdi:chart-areaspline",
            "unit": "%",
            "description": "Profit/loss over 7 days",
            "description_ru": "Прибыль/убыток за 7 дней",
        },
        "bybit_positions": {
            "name": "Bybit Positions",
            "name_ru": "Позиции Bybit",
            "icon": "mdi:format-list-bulleted",
            "description": "Open positions on Bybit",
            "description_ru": "Открытые позиции на Bybit",
        },
        "bybit_unrealized_pnl": {
            "name": "Unrealized P&L",
            "name_ru": "Нереализованный P&L",
            "icon": "mdi:cash-clock",
            "unit": "USDT",
            "description": "Unrealized profit/loss",
            "description_ru": "Нереализованная прибыль/убыток",
        },
        # === Bybit Earn ===
        "bybit_earn_balance": {
            "name": "Bybit Earn Balance",
            "name_ru": "Баланс Bybit Earn",
            "icon": "mdi:piggy-bank",
            "unit": "USDT",
            "description": "Balance in Bybit Earn",
            "description_ru": "Баланс в Bybit Earn",
        },
        "bybit_earn_positions": {
            "name": "Earn Positions",
            "name_ru": "Позиции Earn",
            "icon": "mdi:format-list-bulleted",
            "description": "Active Earn positions",
            "description_ru": "Активные Earn позиции",
        },
        "bybit_earn_apy": {
            "name": "Earn APY",
            "name_ru": "APY Earn",
            "icon": "mdi:percent",
            "unit": "%",
            "description": "Average Earn yield",
            "description_ru": "Средняя доходность Earn",
        },
        "bybit_total_portfolio": {
            "name": "Bybit Portfolio",
            "name_ru": "Портфель Bybit",
            "icon": "mdi:bank",
            "unit": "USDT",
            "description": "Total value on Bybit",
            "description_ru": "Общая стоимость на Bybit",
        },
        # === DCA калькулятор ===
        "dca_next_level": {
            "name": "DCA Next Level",
            "name_ru": "Следующий уровень DCA",
            "icon": "mdi:target",
            "unit": "USDT",
            "description": "Price for next DCA purchase",
            "description_ru": "Цена для следующей покупки DCA",
        },
        "dca_zone": {
            "name": "DCA Zone",
            "name_ru": "Зона DCA",
            "icon": "mdi:map-marker-radius",
            "description": "Current zone: buy/accumulate/wait",
            "description_ru": "Текущая зона: покупка/накопление/ожидание",
        },
        "dca_risk_score": {
            "name": "DCA Risk Score",
            "name_ru": "Риск-скор DCA",
            "icon": "mdi:gauge",
            "description": "Risk assessment for DCA (0-100)",
            "description_ru": "Оценка риска для DCA (0-100)",
        },
        # === Корреляция ===
        "btc_eth_correlation": {
            "name": "BTC/ETH Correlation",
            "name_ru": "Корреляция BTC/ETH",
            "icon": "mdi:link-variant",
            "description": "Correlation coefficient between BTC and ETH",
            "description_ru": "Коэффициент корреляции BTC и ETH",
        },
        "btc_sp500_correlation": {
            "name": "BTC/S&P500 Correlation",
            "name_ru": "Корреляция BTC/S&P500",
            "icon": "mdi:chart-line-variant",
            "description": "Correlation between crypto and stock market",
            "description_ru": "Корреляция крипты с фондовым рынком",
        },
        "correlation_status": {
            "name": "Correlation Status",
            "name_ru": "Статус корреляции",
            "icon": "mdi:connection",
            "description": "Overall correlation status",
            "description_ru": "Общий статус корреляций",
        },
        # === Волатильность (dict формат) ===
        "volatility_30d": {
            "name": "30d Volatility",
            "name_ru": "Волатильность 30д",
            "icon": "mdi:chart-bell-curve",
            "description": '30-day volatility. Format: {"BTC": 45}',
            "description_ru": '30-дневная волатильность. Формат: {"BTC": 45}',
        },
        "volatility_percentile": {
            "name": "Volatility Percentile",
            "name_ru": "Перцентиль волатильности",
            "icon": "mdi:percent-box",
            "description": "Position in historical distribution",
            "description_ru": "Позиция в историческом распределении",
        },
        "volatility_status": {
            "name": "Volatility Status",
            "name_ru": "Статус волатильности",
            "icon": "mdi:pulse",
            "description": "Low/medium/high volatility",
            "description_ru": "Низкая/средняя/высокая волатильность",
        },
        "unlocks_next_7d": {
            "name": "Unlocks Next 7d",
            "name_ru": "Разблокировки 7д",
            "icon": "mdi:lock-open-variant",
            "description": "Token unlocks in next 7 days",
            "description_ru": "Разблокировки токенов за 7 дней",
        },
        "unlock_next_event": {
            "name": "Next Unlock Event",
            "name_ru": "Следующий анлок",
            "icon": "mdi:calendar-lock",
            "description": "Next token unlock event",
            "description_ru": "Ближайшая разблокировка",
        },
        "unlock_risk_level": {
            "name": "Unlock Risk Level",
            "name_ru": "Риск анлоков",
            "icon": "mdi:alert-circle",
            "description": "Risk level from unlocks",
            "description_ru": "Уровень риска от разблокировок",
        },
        # === Макрокалендарь ===
        "next_macro_event": {
            "name": "Next Macro Event",
            "name_ru": "Следующее макрособытие",
            "icon": "mdi:calendar-star",
            "description": "Next important macroeconomic event",
            "description_ru": "Ближайшее важное макрособытие",
        },
        "days_to_fomc": {
            "name": "Days to FOMC",
            "name_ru": "Дней до FOMC",
            "icon": "mdi:calendar-clock",
            "description": "Days until Fed meeting",
            "description_ru": "Дней до заседания ФРС",
        },
        "macro_risk_week": {
            "name": "Macro Risk Week",
            "name_ru": "Макрориск недели",
            "icon": "mdi:calendar-alert",
            "description": "Weekly risk: low/medium/high",
            "description_ru": "Риск на неделе: низкий/средний/высокий",
        },
        # === Арбитраж (dict формат) ===
        "arb_spreads": {
            "name": "Arbitrage Spreads",
            "name_ru": "Спреды арбитража",
            "icon": "mdi:swap-horizontal-bold",
            "description": "Price differences between exchanges",
            "description_ru": "Разница цен между биржами",
        },
        "funding_arb_best": {
            "name": "Best Funding Arbitrage",
            "name_ru": "Лучший фандинг-арб",
            "icon": "mdi:cash-multiple",
            "description": "Best funding arbitrage opportunity",
            "description_ru": "Лучшая возможность для фандинг-арбитража",
        },
        "arb_opportunity": {
            "name": "Arbitrage Opportunity",
            "name_ru": "Возможность арбитража",
            "icon": "mdi:lightning-bolt",
            "description": "Is there an arbitrage opportunity",
            "description_ru": "Есть ли арбитражная возможность",
        },
        # === Фиксация прибыли (dict формат) ===
        "tp_levels": {
            "name": "Take Profit Levels",
            "name_ru": "Уровни фиксации",
            "icon": "mdi:target-variant",
            "description": "Recommended Take Profit levels",
            "description_ru": "Рекомендуемые уровни Take Profit",
        },
        "profit_action": {
            "name": "Profit Action",
            "name_ru": "Действие по прибыли",
            "icon": "mdi:cash-check",
            "description": "Recommendation: hold/take profit",
            "description_ru": "Рекомендация: держать/фиксировать",
        },
        "greed_level": {
            "name": "Greed Level",
            "name_ru": "Уровень жадности",
            "icon": "mdi:emoticon-devil",
            "description": "How overbought the market is (0-100)",
            "description_ru": "Насколько перекуплен рынок (0-100)",
        },
        # === Традиционные финансы ===
        "gold_price": {
            "name": "Gold Price",
            "name_ru": "Золото",
            "icon": "mdi:gold",
            "unit": "USD",
            "description": "Gold price XAU/USD",
            "description_ru": "Цена золота XAU/USD",
        },
        "silver_price": {
            "name": "Silver Price",
            "name_ru": "Серебро",
            "icon": "mdi:circle-outline",
            "unit": "USD",
            "description": "Silver price XAG/USD",
            "description_ru": "Цена серебра XAG/USD",
        },
        "platinum_price": {
            "name": "Platinum Price",
            "name_ru": "Платина",
            "icon": "mdi:diamond-stone",
            "unit": "USD",
            "description": "Platinum price",
            "description_ru": "Цена платины",
        },
        "sp500_price": {
            "name": "S&P 500 Index",
            "name_ru": "Индекс S&P 500",
            "icon": "mdi:chart-line",
            "unit": "USD",
            "description": "American stock index S&P 500",
            "description_ru": "Американский фондовый индекс S&P 500",
        },
        "nasdaq_price": {
            "name": "NASDAQ Index",
            "name_ru": "Индекс NASDAQ",
            "icon": "mdi:chart-areaspline",
            "unit": "USD",
            "description": "Technology companies index NASDAQ",
            "description_ru": "Индекс технологических компаний NASDAQ",
        },
        "dji_price": {
            "name": "Dow Jones Index",
            "name_ru": "Индекс Dow Jones",
            "icon": "mdi:chart-bar",
            "unit": "USD",
            "description": "Industrial index Dow Jones",
            "description_ru": "Промышленный индекс Dow Jones",
        },
        "dax_price": {
            "name": "DAX Index",
            "name_ru": "Индекс DAX",
            "icon": "mdi:chart-timeline-variant",
            "unit": "EUR",
            "description": "German stock index DAX",
            "description_ru": "Немецкий фондовый индекс DAX",
        },
        "eur_usd": {
            "name": "EUR/USD Rate",
            "name_ru": "Курс EUR/USD",
            "icon": "mdi:currency-eur",
            "description": "Euro to dollar exchange rate",
            "description_ru": "Курс евро к доллару",
        },
        "gbp_usd": {
            "name": "GBP/USD Rate",
            "name_ru": "Курс GBP/USD",
            "icon": "mdi:currency-gbp",
            "description": "Pound to dollar exchange rate",
            "description_ru": "Курс фунта к доллару",
        },
        "dxy_index": {
            "name": "Dollar Index",
            "name_ru": "Индекс доллара",
            "icon": "mdi:currency-usd",
            "description": "DXY Index - dollar strength",
            "description_ru": "Индекс DXY - сила доллара",
        },
        "oil_brent": {
            "name": "Brent Oil",
            "name_ru": "Нефть Brent",
            "icon": "mdi:barrel",
            "unit": "USD",
            "description": "Brent oil price",
            "description_ru": "Цена нефти Brent",
        },
        "oil_wti": {
            "name": "WTI Oil",
            "name_ru": "Нефть WTI",
            "icon": "mdi:barrel",
            "unit": "USD",
            "description": "WTI oil price",
            "description_ru": "Цена нефти WTI",
        },
        "natural_gas": {
            "name": "Natural Gas",
            "name_ru": "Природный газ",
            "icon": "mdi:fire",
            "unit": "USD",
            "description": "Natural gas price",
            "description_ru": "Цена природного газа",
        },
        # === AI анализ ===
        "ai_daily_summary": {
            "name": "AI Daily Summary",
            "name_ru": "AI дневная сводка",
            "icon": "mdi:robot",
            "description": "Daily AI market summary",
            "description_ru": "Ежедневная AI-сводка по рынку",
        },
        "ai_market_sentiment": {
            "name": "AI Market Sentiment",
            "name_ru": "AI настроение",
            "icon": "mdi:brain",
            "description": "AI assessment of market sentiment",
            "description_ru": "Оценка настроения рынка от AI",
        },
        "ai_recommendation": {
            "name": "AI Recommendation",
            "name_ru": "AI рекомендация",
            "icon": "mdi:lightbulb",
            "description": "AI recommendation for actions",
            "description_ru": "Рекомендация AI по действиям",
        },
        "ai_last_analysis": {
            "name": "AI Last Analysis",
            "name_ru": "AI последний анализ",
            "icon": "mdi:clock-outline",
            "description": "Time of last AI analysis",
            "description_ru": "Время последнего AI-анализа",
        },
        "ai_provider": {
            "name": "AI Provider",
            "name_ru": "AI провайдер",
            "icon": "mdi:cog",
            "entity_category": "diagnostic",
            "description": "Used AI provider",
            "description_ru": "Используемый AI-провайдер",
        },
        # === Технические индикаторы (dict формат) ===
        "ta_rsi": {
            "name": "RSI Indicator",
            "name_ru": "RSI индикатор",
            "icon": "mdi:chart-line",
            "description": 'RSI(14) for all coins. Format: {"BTC": 65}',
            "description_ru": 'RSI(14) для всех монет. Формат: {"BTC": 65}',
        },
        "ta_macd_signal": {
            "name": "MACD Signals",
            "name_ru": "MACD сигналы",
            "icon": "mdi:signal",
            "description": 'MACD signals. Format: {"BTC": "bullish"}',
            "description_ru": 'MACD сигналы. Формат: {"BTC": "bullish"}',
        },
        "ta_bb_position": {
            "name": "BB Position",
            "name_ru": "Позиция BB",
            "icon": "mdi:chart-bell-curve",
            "description": 'Position in Bollinger Bands. Format: {"BTC": 0.7}',
            "description_ru": 'Позиция в Bollinger Bands. Формат: {"BTC": 0.7}',
        },
        "ta_trend": {
            "name": "Trends",
            "name_ru": "Тренды",
            "icon": "mdi:trending-up",
            "description": 'Trend direction. Format: {"BTC": "uptrend"}',
            "description_ru": 'Направление тренда. Формат: {"BTC": "uptrend"}',
        },
        "ta_support": {
            "name": "Support Levels",
            "name_ru": "Уровни поддержки",
            "icon": "mdi:arrow-down-bold",
            "description": 'Nearest support levels. Format: {"BTC": 90000}',
            "description_ru": 'Ближайшие уровни поддержки. Формат: {"BTC": 90000}',
        },
        "ta_resistance": {
            "name": "Resistance Levels",
            "name_ru": "Уровни сопротивления",
            "icon": "mdi:arrow-up-bold",
            "description": 'Nearest resistance levels. Format: {"BTC": 100000}',
            "description_ru": 'Ближайшие уровни сопротивления. Формат: {"BTC": 100000}',
        },
        # === MTF тренды ===
        "ta_trend_mtf": {
            "name": "MTF Trends",
            "name_ru": "MTF тренды",
            "icon": "mdi:clock-outline",
            "description": "Trends across different timeframes",
            "description_ru": "Тренды на разных таймфреймах",
        },
        # === TA Confluence ===
        "ta_confluence": {
            "name": "TA Confluence",
            "name_ru": "Конфлюенс TA",
            "icon": "mdi:check-all",
            "description": "Indicator convergence score (0-100)",
            "description_ru": "Скор схождения индикаторов (0-100)",
        },
        "ta_signal": {
            "name": "TA Signal",
            "name_ru": "TA сигнал",
            "icon": "mdi:traffic-light",
            "description": "Overall TA signal: buy/sell/hold",
            "description_ru": "Общий сигнал TA: buy/sell/hold",
        },
        # === Управление рисками ===
        "portfolio_sharpe": {
            "name": "Sharpe Ratio",
            "name_ru": "Коэффициент Шарпа",
            "icon": "mdi:chart-areaspline",
            "description": "Return to risk ratio",
            "description_ru": "Соотношение доходности к риску",
        },
        "portfolio_sortino": {
            "name": "Sortino Ratio",
            "name_ru": "Коэффициент Сортино",
            "icon": "mdi:chart-line-variant",
            "description": "Risk assessment considering drawdowns",
            "description_ru": "Оценка риска с учётом падений",
        },
        "portfolio_max_drawdown": {
            "name": "Max Drawdown",
            "name_ru": "Макс. просадка",
            "icon": "mdi:trending-down",
            "unit": "%",
            "description": "Maximum historical drawdown",
            "description_ru": "Максимальная историческая просадка",
        },
        "portfolio_current_drawdown": {
            "name": "Current Drawdown",
            "name_ru": "Текущая просадка",
            "icon": "mdi:arrow-down",
            "unit": "%",
            "description": "Current drawdown from peak",
            "description_ru": "Текущая просадка от максимума",
        },
        "portfolio_var_95": {
            "name": "VaR 95%",
            "name_ru": "VaR 95%",
            "icon": "mdi:alert",
            "unit": "%",
            "description": "Value at Risk (95% confidence)",
            "description_ru": "Стоимость под риском (95% доверия)",
        },
        "risk_status": {
            "name": "Risk Status",
            "name_ru": "Статус риска",
            "icon": "mdi:shield-alert",
            "description": "Overall status: low/medium/high",
            "description_ru": "Общий статус: низкий/средний/высокий",
        },
        # === Бэктест ===
        "backtest_dca_roi": {
            "name": "Backtest DCA ROI",
            "name_ru": "DCA бэктест ROI",
            "icon": "mdi:percent",
            "unit": "%",
            "description": "ROI of DCA strategy in backtest",
            "description_ru": "Доходность DCA стратегии в бэктесте",
        },
        "backtest_smart_dca_roi": {
            "name": "Backtest Smart DCA ROI",
            "name_ru": "Smart DCA ROI",
            "icon": "mdi:brain",
            "unit": "%",
            "description": "ROI of smart DCA",
            "description_ru": "Доходность умного DCA",
        },
        "backtest_lump_sum_roi": {
            "name": "Backtest Lump Sum ROI",
            "name_ru": "Lump Sum ROI",
            "icon": "mdi:cash",
            "unit": "%",
            "description": "ROI of lump sum purchase",
            "description_ru": "Доходность единоразовой покупки",
        },
        "backtest_best_strategy": {
            "name": "Best Backtest Strategy",
            "name_ru": "Лучшая стратегия",
            "icon": "mdi:trophy",
            "description": "Best strategy according to backtest",
            "description_ru": "Лучшая стратегия по бэктесту",
        },
        # === Умная сводка (UX) ===
        "market_pulse": {
            "name": "Market Pulse",
            "name_ru": "Пульс рынка",
            "icon": "mdi:pulse",
            "description": "Overall market sentiment",
            "description_ru": "Общее настроение рынка",
        },
        "market_pulse_confidence": {
            "name": "Market Pulse Confidence",
            "name_ru": "Уверенность пульса",
            "icon": "mdi:percent",
            "unit": "%",
            "description": "Confidence in market assessment (%)",
            "description_ru": "Уверенность в оценке рынка (%)",
        },
        "portfolio_health": {
            "name": "Portfolio Health",
            "name_ru": "Здоровье портфеля",
            "icon": "mdi:shield-check",
            "description": "Overall portfolio health assessment",
            "description_ru": "Общая оценка здоровья портфеля",
        },
        "portfolio_health_score": {
            "name": "Portfolio Health Score",
            "name_ru": "Скор здоровья",
            "icon": "mdi:counter",
            "unit": "%",
            "description": "Portfolio health assessment (0-100%)",
            "description_ru": "Оценка здоровья портфеля (0-100%)",
        },
        "today_action": {
            "name": "Today's Action",
            "name_ru": "Действие сегодня",
            "icon": "mdi:clipboard-check",
            "description": "Recommended action for today",
            "description_ru": "Рекомендуемое действие на сегодня",
        },
        "today_action_priority": {
            "name": "Action Priority",
            "name_ru": "Приоритет действия",
            "icon": "mdi:alert-circle",
            "description": "Urgency: low/medium/high",
            "description_ru": "Срочность: низкая/средняя/высокая",
        },
        "weekly_outlook": {
            "name": "Weekly Outlook",
            "name_ru": "Прогноз на неделю",
            "icon": "mdi:calendar-week",
            "description": "Brief forecast for the week",
            "description_ru": "Краткий прогноз на неделю",
        },
        # === Алерты и уведомления (UX) ===
        "pending_alerts_count": {
            "name": "Pending Alerts Count",
            "name_ru": "Ожидающие алерты",
            "icon": "mdi:bell-badge",
            "description": "Number of unprocessed alerts",
            "description_ru": "Количество необработанных алертов",
        },
        "pending_alerts_critical": {
            "name": "Critical Alerts Count",
            "name_ru": "Критические алерты",
            "icon": "mdi:bell-alert",
            "description": "Number of critical alerts",
            "description_ru": "Количество критических алертов",
        },
        "daily_digest_ready": {
            "name": "Daily Digest Ready",
            "name_ru": "Дневной дайджест",
            "icon": "mdi:newspaper",
            "description": "Is daily digest ready",
            "description_ru": "Готов ли дневной дайджест",
        },
        "notification_mode": {
            "name": "Notification Mode",
            "name_ru": "Режим уведомлений",
            "icon": "mdi:bell-cog",
            "description": "Current mode: all/important/quiet",
            "description_ru": "Текущий режим: все/важные/тихий",
        },
        # === Брифинги (UX) ===
        "morning_briefing": {
            "name": "Morning Briefing",
            "name_ru": "Утренний брифинг",
            "icon": "mdi:weather-sunny",
            "description": "Morning market summary",
            "description_ru": "Утренняя сводка по рынку",
        },
        "evening_briefing": {
            "name": "Evening Briefing",
            "name_ru": "Вечерний брифинг",
            "icon": "mdi:weather-night",
            "description": "Evening market summary",
            "description_ru": "Вечерняя сводка по рынку",
        },
        "briefing_last_sent": {
            "name": "Last Briefing Sent",
            "name_ru": "Последний брифинг",
            "icon": "mdi:clock-check",
            "device_class": "timestamp",
            "description": "Time of last briefing",
            "description_ru": "Время последнего брифинга",
        },
        # === Отслеживание целей (UX) ===
        "goal_target": {
            "name": "Goal Target",
            "name_ru": "Цель",
            "icon": "mdi:flag-checkered",
            "unit": "USDT",
            "description": "Target portfolio amount",
            "description_ru": "Целевая сумма портфеля",
        },
        "goal_progress": {
            "name": "Goal Progress",
            "name_ru": "Прогресс цели",
            "icon": "mdi:progress-check",
            "unit": "%",
            "description": "Goal achievement percentage",
            "description_ru": "Процент достижения цели",
        },
        "goal_remaining": {
            "name": "Goal Remaining",
            "name_ru": "Осталось до цели",
            "icon": "mdi:cash-minus",
            "unit": "USDT",
            "description": "Amount remaining to reach goal",
            "description_ru": "Сколько осталось до цели",
        },
        "goal_days_estimate": {
            "name": "Days to Goal",
            "name_ru": "Дней до цели",
            "icon": "mdi:calendar-clock",
            "description": "Estimated days to achievement",
            "description_ru": "Оценка дней до достижения",
        },
        "goal_status": {
            "name": "Goal Status",
            "name_ru": "Статус цели",
            "icon": "mdi:trophy",
            "description": "Status: in progress/reached/postponed",
            "description_ru": "Статус: в процессе/достигнута/отложена",
        },
        # === Диагностические сенсоры ===
        "sync_status": {
            "name": "Sync Status",
            "name_ru": "Статус синхронизации",
            "icon": "mdi:sync",
            "entity_category": "diagnostic",
            "description": "Status: idle/running/completed/error",
            "description_ru": "Статус: idle/running/completed/error",
        },
        "last_sync": {
            "name": "Last Sync",
            "name_ru": "Последняя синхронизация",
            "icon": "mdi:clock-outline",
            "device_class": "timestamp",
            "entity_category": "diagnostic",
            "description": "Time of last synchronization",
            "description_ru": "Время последней синхронизации",
        },
        "candles_count": {
            "name": "Total Candles",
            "name_ru": "Всего свечей",
            "icon": "mdi:database",
            "unit": "candles",
            "entity_category": "diagnostic",
            "description": "Total number of candles in DB",
            "description_ru": "Общее количество свечей в БД",
        },
        "database_size": {
            "name": "Database Size",
            "name_ru": "Размер базы данных",
            "icon": "mdi:database-settings",
            "unit": "MB",
            "entity_category": "diagnostic",
            "description": "Size of database file",
            "description_ru": "Размер файла базы данных",
        },
        # === AI Аналитика (словарный формат) ===
        "ai_trends": {
            "name": "AI Trends",
            "name_ru": "AI Тренды",
            "icon": "mdi:brain",
            "entity_category": "diagnostic",
            "description": 'AI-predicted trends for all currencies. Format: {"BTC": "Bullish", "ETH": "Neutral"}',
            "description_ru": 'AI-предсказанные тренды для всех валют. Формат: {"BTC": "Bullish", "ETH": "Neutral"}',
        },
        "ai_confidences": {
            "name": "AI Confidences",
            "name_ru": "AI Уверенности",
            "icon": "mdi:percent",
            "unit": "%",
            "entity_category": "diagnostic",
            "description": 'AI prediction confidences for all currencies. Format: {"BTC": 85, "ETH": 78}',
            "description_ru": 'Уровни уверенности AI-предсказаний для всех валют. Формат: {"BTC": 85, "ETH": 78}',
        },
        "ai_price_forecasts_24h": {
            "name": "AI 24h Price Forecasts",
            "name_ru": "AI Прогнозы цен 24ч",
            "icon": "mdi:chart-line",
            "unit": "USDT",
            "entity_category": "diagnostic",
            "description": 'AI-predicted prices in 24 hours for all currencies. Format: {"BTC": 95000, "ETH": 3200}',
            "description_ru": 'AI-прогнозы цен через 24 часа для всех валют. Формат: {"BTC": 95000, "ETH": 3200}',
        },
        # === Адаптивные уведомления ===
        "adaptive_notifications_status": {
            "name": "Adaptive Notifications",
            "name_ru": "Адаптивные уведомления",
            "icon": "mdi:bell-ring",
            "entity_category": "diagnostic",
            "description": "Status of adaptive notification system",
            "description_ru": "Статус системы адаптивных уведомлений",
        },
        "adaptive_volatilities": {
            "name": "Adaptive Volatilities",
            "name_ru": "Адаптивные уровни волатильности",
            "icon": "mdi:wave",
            "entity_category": "diagnostic",
            "description": 'Current volatility levels for all currencies. Format: {"BTC": "High", "ETH": "Medium"}',
            "description_ru": 'Текущие уровни волатильности для всех валют. Формат: {"BTC": "High", "ETH": "Medium"}',
        },
        "adaptive_notification_count_24h": {
            "name": "Notifications 24h",
            "name_ru": "Уведомлений за 24ч",
            "icon": "mdi:counter",
            "unit": "alerts",
            "entity_category": "diagnostic",
            "description": "Number of notifications sent in last 24 hours",
            "description_ru": "Количество отправленных уведомлений за последние 24 часа",
        },
        "adaptive_adaptation_factors": {
            "name": "Adaptive Adaptation Factors",
            "name_ru": "Адаптивные факторы адаптации",
            "icon": "mdi:scale-balance",
            "unit": "x",
            "entity_category": "diagnostic",
            "description": 'Current adaptation factors for all currencies. Format: {"BTC": 1.5, "ETH": 1.2}',
            "description_ru": 'Текущие факторы адаптации для всех валют. Формат: {"BTC": 1.5, "ETH": 1.2}',
        },
        # === Умная корреляция ===
        "correlation_analysis_status": {
            "name": "Correlation Analysis",
            "name_ru": "Анализ корреляций",
            "icon": "mdi:vector-link",
            "entity_category": "diagnostic",
            "description": "Status of smart correlation analysis",
            "description_ru": "Статус анализа умных корреляций",
        },
        "correlation_significant_count": {
            "name": "Significant Correlations",
            "name_ru": "Значимые корреляции",
            "icon": "mdi:link",
            "unit": "pairs",
            "entity_category": "diagnostic",
            "description": "Number of statistically significant correlations detected",
            "description_ru": "Количество статистически значимых корреляций",
        },
        "correlation_strongest_positive": {
            "name": "Strongest Positive Corr",
            "name_ru": "Сильнейшая положительная корреляция",
            "icon": "mdi:trending-up",
            "entity_category": "diagnostic",
            "description": "Strongest positive correlation found",
            "description_ru": "Самая сильная положительная корреляция",
        },
        "correlation_strongest_negative": {
            "name": "Strongest Negative Corr",
            "name_ru": "Сильнейшая отрицательная корреляция",
            "icon": "mdi:trending-down",
            "entity_category": "diagnostic",
            "description": "Strongest negative correlation found",
            "description_ru": "Самая сильная отрицательная корреляция",
        },
        "correlation_dominant_patterns": {
            "name": "Dominant Patterns",
            "name_ru": "Доминирующие паттерны",
            "icon": "mdi:pattern",
            "unit": "patterns",
            "entity_category": "diagnostic",
            "description": "Number of dominant correlation patterns identified",
            "description_ru": "Количество выявленных доминирующих паттернов",
        },
        # === Экономический календарь ===
        "economic_calendar_status": {
            "name": "Economic Calendar",
            "name_ru": "Экономический календарь",
            "icon": "mdi:calendar-clock",
            "entity_category": "diagnostic",
            "description": "Status of economic events and news tracking",
            "description_ru": "Статус отслеживания экономических событий и новостей",
        },
        "economic_upcoming_events_24h": {
            "name": "Upcoming Events 24h",
            "name_ru": "Предстоящие события 24ч",
            "icon": "mdi:clock-alert",
            "unit": "events",
            "entity_category": "diagnostic",
            "description": "Number of important economic events in next 24 hours",
            "description_ru": "Количество важных экономических событий в ближайшие 24 часа",
        },
        "economic_important_events": {
            "name": "Important Events",
            "name_ru": "Важные события",
            "icon": "mdi:alert-circle",
            "unit": "events",
            "entity_category": "diagnostic",
            "description": "Number of currently tracked important events",
            "description_ru": "Количество отслеживаемых важных событий",
        },
        "economic_breaking_news": {
            "name": "Breaking News",
            "name_ru": "Срочные новости",
            "icon": "mdi:flash-alert",
            "unit": "news",
            "entity_category": "diagnostic",
            "description": "Number of breaking cryptocurrency news",
            "description_ru": "Количество срочных новостей о криптовалютах",
        },
        "economic_sentiment_score": {
            "name": "Market Sentiment",
            "name_ru": "Рыночные настроения",
            "icon": "mdi:emoticon",
            "entity_category": "diagnostic",
            "description": "Overall market sentiment from news and events",
            "description_ru": "Общие рыночные настроения из новостей и событий",
        },
    }

    def __init__(self):
        self._prices: dict[str, str] = {}
        self._changes: dict[str, str] = {}
        self._volumes: dict[str, str] = {}
        self._highs: dict[str, str] = {}
        self._lows: dict[str, str] = {}
        self._cache: dict[str, any] = {}  # General cache for sensor values
        self._supervisor_client = get_supervisor_client()

    @property
    def device_info(self) -> dict:
        """Device info for sensor attributes."""
        return {
            "identifiers": [self.DEVICE_ID],
            "name": self.DEVICE_NAME,
            "model": "Crypto Data Collector",
            "manufacturer": "Crypto Inspect Add-on",
            "sw_version": APP_VERSION,
        }

    def _get_entity_id(self, sensor_id: str) -> str:
        """Get full entity ID for Supervisor API."""
        return f"{self.ENTITY_PREFIX}{sensor_id}"

    async def register_sensor(self, sensor_id: str, sensor_config: dict) -> bool:
        """
        Register a single sensor via Supervisor API.
        
        Args:
            sensor_id: Unique identifier for the sensor
            sensor_config: Configuration dictionary containing:
                - name: Display name
                - name_ru: Russian display name
                - icon: Material Design icon
                - unit: Optional unit of measurement
                - description: English description
                - description_ru: Russian description
                
        Returns:
            True if registered successfully
        """
        if not self._supervisor_client.is_available:
            logger.warning("Supervisor API not available, skipping sensor registration")
            return False
            
        try:
            success = await self._supervisor_client.create_sensor(
                sensor_id=sensor_id,
                state="unknown",
                friendly_name=sensor_config["name"],
                icon=sensor_config.get("icon", "mdi:information"),
                unit=sensor_config.get("unit"),
                device_class=sensor_config.get("device_class"),
                attributes={
                    "device": self.device_info,
                    "description": sensor_config.get("description", ""),
                    "description_ru": sensor_config.get("description_ru", ""),
                    "name_ru": sensor_config.get("name_ru", ""),
                },
            )
            
            if success:
                logger.info(f"Registered sensor: {sensor_config['name']} (ID: {sensor_id})")
                return True
            else:
                logger.error(f"Failed to register sensor {sensor_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error registering sensor {sensor_id}: {e}")
            return False
    
    async def register_sensors(self) -> int:
        """
        Register all sensors via Supervisor API.

        Returns:
            Number of sensors registered.
        """
        if not self._supervisor_client.is_available:
            logger.warning("Supervisor API not available, skipping sensor registration")
            return 0

        count = 0
        symbols = get_symbols()

        for sensor_id, sensor_def in self.SENSORS.items():
            # Create sensor with initial empty state
            success = await self._supervisor_client.create_sensor(
                sensor_id=sensor_id,
                state="unknown",
                friendly_name=sensor_def["name"],
                icon=sensor_def.get("icon", "mdi:information"),
                unit=sensor_def.get("unit"),
                device_class=sensor_def.get("device_class"),
                attributes={
                    "device": self.device_info,
                    "description": sensor_def.get("description", ""),
                    "description_ru": sensor_def.get("description_ru", ""),
                    "name_ru": sensor_def.get("name_ru", ""),
                },
            )
            
            if success:
                count += 1
                logger.info(f"Registered sensor: {sensor_def['name']}")
            else:
                logger.error(f"Failed to register sensor {sensor_id}")

        # Update prices sensor with initial attributes
        await self._update_sensor_attributes("prices", {"symbols": symbols, "count": len(symbols)})

        logger.info(f"Registered {count} sensors via Supervisor API, tracking {len(symbols)} symbols")
        return count

    async def _update_sensor_state(self, sensor_id: str, state: str | dict) -> bool:
        """Update sensor state via Supervisor API."""
        if not self._supervisor_client.is_available:
            return False

        payload = json.dumps(state) if isinstance(state, dict) else str(state)
        
        try:
            success = await self._supervisor_client.update_sensor(sensor_id, payload)
            if success:
                logger.debug(f"Updated state for {sensor_id}: {payload}")
            return success
        except Exception as e:
            logger.error(f"Failed to update state for {sensor_id}: {e}")
            return False

    async def _update_sensor_attributes(self, sensor_id: str, attributes: dict) -> bool:
        """Update sensor attributes via Supervisor API."""
        if not self._supervisor_client.is_available:
            return False

        try:
            # We need to get current state first to preserve it
            entity_id = self._get_entity_id(sensor_id)
            success = await self._supervisor_client.set_state(entity_id, "unknown", attributes)
            if success:
                logger.debug(f"Updated attributes for {sensor_id}")
            return success
        except Exception as e:
            logger.error(f"Failed to update attributes for {sensor_id}: {e}")
            return False

    async def _publish_state(self, sensor_id: str, state: any) -> bool:
        """
        Internal method to publish sensor state.
        
        Args:
            sensor_id: Sensor identifier
            state: State value (dict, list, or scalar)
            
        Returns:
            True if published successfully
        """
        # Cache the value
        self._cache[sensor_id] = state
        
        # Update via Supervisor API
        return await self._update_sensor_state(sensor_id, state)
    
    async def _publish_attributes(self, sensor_id: str, attributes: dict) -> bool:
        """
        Internal method to publish sensor attributes.
        
        Args:
            sensor_id: Sensor identifier
            attributes: Attributes dictionary
            
        Returns:
            True if published successfully
        """
        return await self._update_sensor_attributes(sensor_id, attributes)
    
    async def publish_sensor(self, sensor_id: str, value: any, attributes: dict | None = None) -> bool:
        """
        Update a sensor value with optional attributes via Supervisor API.

        This is the main public API for updating sensor values.
        Values are cached for later retrieval.

        Args:
            sensor_id: Sensor identifier
            value: Value to publish (will be converted to string/JSON)
            attributes: Optional attributes dict

        Returns:
            True if updated successfully
        """
        # Cache the value
        self._cache[sensor_id] = value

        # Update state
        result = await self._update_sensor_state(sensor_id, value)

        # Update attributes if provided
        if attributes and result:
            await self._update_sensor_attributes(sensor_id, attributes)

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
        Update price data for a symbol via Supervisor API.

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

        # Update all price data via Supervisor API
        await self._update_sensor_state("prices", self._prices)
        await self._update_sensor_attributes(
            "prices",
            {
                "symbols": list(self._prices.keys()),
                "count": len(self._prices),
                "last_updated": datetime.now(UTC).isoformat(),
            },
        )

        # Update other metrics if we have data
        if self._changes:
            await self._update_sensor_state("changes_24h", self._changes)
        if self._volumes:
            await self._update_sensor_state("volumes_24h", self._volumes)
        if self._highs:
            await self._update_sensor_state("highs_24h", self._highs)
        if self._lows:
            await self._update_sensor_state("lows_24h", self._lows)

    async def update_all_prices(self, prices_data: dict[str, dict]) -> None:
        """
        Update prices for all symbols at once via Supervisor API.

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

        # Update all states via Supervisor API
        await self._update_sensor_state("prices", self._prices)
        await self._update_sensor_state("changes_24h", self._changes)
        await self._update_sensor_state("volumes_24h", self._volumes)
        await self._update_sensor_state("highs_24h", self._highs)
        await self._update_sensor_state("lows_24h", self._lows)

        await self._update_sensor_attributes(
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
        Update sync status sensors via Supervisor API.

        Args:
            status: Current status ('running', 'completed', 'error')
            success_count: Number of successful operations
            failure_count: Number of failed operations
            total_candles: Total candles in database
        """
        # Sync status
        await self._update_sensor_state("sync_status", status)
        await self._update_sensor_attributes(
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
        await self._update_sensor_state("last_sync", datetime.now(UTC).isoformat())

        # Total candles
        if total_candles is not None:
            await self._update_sensor_state("candles_count", str(total_candles))

    async def remove_sensors(self) -> None:
        """Remove all sensors by setting their states to 'unavailable'."""
        if not self._supervisor_client.is_available:
            return

        for sensor_id in self.SENSORS:
            try:
                entity_id = self._get_entity_id(sensor_id)
                # Set state to unavailable to effectively "remove" the sensor
                await self._supervisor_client.set_state(entity_id, "unavailable")
            except Exception as e:
                logger.error(f"Failed to remove sensor {sensor_id}: {e}")

        logger.info("Marked all sensors as unavailable")

    async def update_investor_status(self, status_data: dict) -> None:
        """
        Update all investor-related sensors from InvestorStatus via Supervisor API.

        Args:
            status_data: Dictionary from InvestorStatus.to_dict()
        """
        if not self._supervisor_client.is_available:
            logger.warning("Supervisor API not available, skipping investor update")
            return

        # Do Nothing OK
        do_nothing = status_data.get("do_nothing_ok", {})
        await self._update_sensor_state("do_nothing_ok", do_nothing.get("state", "N/A"))
        await self._update_sensor_attributes(
            "do_nothing_ok",
            {
                "value": do_nothing.get("value", False),
                "reason": do_nothing.get("reason_ru", ""),
            },
        )

        # Investor Phase
        phase = status_data.get("phase", {})
        await self._update_sensor_state("investor_phase", phase.get("name_ru", "N/A"))
        await self._update_sensor_attributes(
            "investor_phase",
            {
                "value": phase.get("value", "unknown"),
                "confidence": phase.get("confidence", 0),
                "description": phase.get("description_ru", ""),
            },
        )

        # Calm Indicator
        calm = status_data.get("calm", {})
        await self._update_sensor_state("calm_indicator", str(calm.get("score", 50)))
        await self._update_sensor_attributes(
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
        await self._update_sensor_state("red_flags", f"{state_emoji} {flags_count}")
        await self._update_sensor_attributes(
            "red_flags",
            {
                "flags_count": flags_count,
                "flags_list": red_flags.get("flags_list", "✅ Нет флагов"),
                "flags": red_flags.get("flags", []),
            },
        )

        # Market Tension
        tension = status_data.get("tension", {})
        await self._update_sensor_state("market_tension", tension.get("state", "N/A"))
        await self._update_sensor_attributes(
            "market_tension",
            {
                "score": tension.get("score", 50),
                "level": tension.get("level_ru", "Норма"),
            },
        )

        # Price Context
        price_ctx = status_data.get("price_context", {})
        await self._update_sensor_state("price_context", price_ctx.get("context_ru", "N/A"))
        await self._update_sensor_attributes(
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
        await self._update_sensor_state("dca_result", str(dca.get("total_amount", 0)))
        await self._update_sensor_attributes(
            "dca_result",
            {
                "btc_amount": dca.get("btc_amount", 0),
                "eth_amount": dca.get("eth_amount", 0),
                "alts_amount": dca.get("alts_amount", 0),
                "reason": dca.get("reason_ru", ""),
            },
        )

        # DCA Signal
        await self._update_sensor_state("dca_signal", dca.get("state", "N/A"))
        await self._update_sensor_attributes(
            "dca_signal",
            {
                "signal": dca.get("signal", "neutral"),
                "signal_ru": dca.get("signal_ru", "Нейтрально"),
                "next_dca": dca.get("next_dca", ""),
            },
        )

        # Weekly Insight
        insight = status_data.get("weekly_insight", {})
        await self._update_sensor_state("weekly_insight", insight.get("summary_ru", "N/A"))
        await self._update_sensor_attributes(
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
        await self._update_sensor_state("next_action_timer", dca.get("next_dca", "N/A"))

        logger.info("Updated investor sensors via Supervisor API")

    async def update_market_data(
        self,
        fear_greed: int | None = None,
        btc_dominance: float | None = None,
        derivatives_data: dict | None = None,
    ) -> None:
        """
        Update market-related sensors via Supervisor API.

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

            await self._update_sensor_state("fear_greed", state)
            await self._update_sensor_attributes(
                "fear_greed",
                {
                    "value": fear_greed,
                    "classification": self._get_fg_classification(fear_greed),
                },
            )

        if btc_dominance is not None:
            await self._update_sensor_state("btc_dominance", f"{btc_dominance:.1f}")
            await self._update_sensor_attributes(
                "btc_dominance",
                {
                    "value": btc_dominance,
                    "trend": "↗️" if btc_dominance >= 55 else "↘️" if btc_dominance <= 45 else "→",
                },
            )

        if derivatives_data:
            await self._update_sensor_state("derivatives", "Active")
            await self._update_sensor_attributes("derivatives", derivatives_data)

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
        Update smart summary sensors via Supervisor API.

        Args:
            summary_data: Dict with market_pulse, portfolio_health, today_action, weekly_outlook
        """
        if not self._supervisor_client.is_available:
            return

        # Market Pulse
        if "market_pulse" in summary_data:
            pulse = summary_data["market_pulse"]
            await self._update_sensor_state("market_pulse", pulse.get("sentiment_ru", "N/A"))
            await self._update_sensor_attributes(
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
            await self._update_sensor_state("market_pulse_confidence", str(pulse.get("confidence", 0)))

        # Portfolio Health
        if "portfolio_health" in summary_data:
            health = summary_data["portfolio_health"]
            await self._update_sensor_state("portfolio_health", health.get("status_ru", "N/A"))
            await self._update_sensor_attributes(
                "portfolio_health",
                {
                    "status_en": health.get("status_en", ""),
                    "status_ru": health.get("status_ru", ""),
                    "score": health.get("score", 0),
                    "main_issue_en": health.get("main_issue_en", ""),
                    "main_issue_ru": health.get("main_issue_ru", ""),
                },
            )
            await self._update_sensor_state("portfolio_health_score", str(health.get("score", 0)))

        # Today's Action
        if "today_action" in summary_data:
            action = summary_data["today_action"]
            await self._update_sensor_state("today_action", action.get("action_ru", "N/A"))
            await self._update_sensor_attributes(
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
            await self._update_sensor_state("today_action_priority", action.get("priority_ru", "N/A"))

        # Weekly Outlook
        if "weekly_outlook" in summary_data:
            outlook = summary_data["weekly_outlook"]
            await self._update_sensor_state("weekly_outlook", outlook.get("outlook_ru", "N/A"))
            await self._update_sensor_attributes("weekly_outlook", outlook)

        logger.info("Updated smart summary sensors via Supervisor API")

    async def update_notification_status(self, status_data: dict) -> None:
        """
        Update notification-related sensors via Supervisor API.

        Args:
            status_data: Dict from NotificationManager.format_sensor_attributes()
        """
        if not self._supervisor_client.is_available:
            return

        await self._update_sensor_state("pending_alerts_count", str(status_data.get("pending_alerts_count", 0)))
        await self._update_sensor_attributes(
            "pending_alerts_count",
            {
                "critical": status_data.get("pending_alerts_critical", 0),
                "important": status_data.get("pending_alerts_important", 0),
                "info": status_data.get("pending_alerts_info", 0),
            },
        )

        await self._update_sensor_state("pending_alerts_critical", str(status_data.get("pending_alerts_critical", 0)))

        await self._update_sensor_state("daily_digest_ready", status_data.get("digest_ready_ru", "Новых оповещений нет"))
        await self._update_sensor_attributes(
            "daily_digest_ready",
            {
                "ready": status_data.get("daily_digest_ready", False),
                "ready_en": status_data.get("digest_ready_en", ""),
                "ready_ru": status_data.get("digest_ready_ru", ""),
                "last_digest": status_data.get("last_digest_time"),
            },
        )

        await self._update_sensor_state("notification_mode", status_data.get("notification_mode_ru", "Умный режим"))
        await self._update_sensor_attributes(
            "notification_mode",
            {
                "mode": status_data.get("notification_mode", "smart"),
                "mode_en": status_data.get("notification_mode_en", ""),
                "mode_ru": status_data.get("notification_mode_ru", ""),
            },
        )

        logger.info("Updated notification sensors via Supervisor API")

    async def update_briefing_status(self, briefing_data: dict) -> None:
        """
        Update briefing-related sensors via Supervisor API.

        Args:
            briefing_data: Dict from BriefingService.format_sensor_attributes()
        """
        if not self._supervisor_client.is_available:
            return

        await self._update_sensor_state(
            "morning_briefing", briefing_data.get("morning_briefing_status_ru", "Не сгенерирован")
        )
        await self._update_sensor_attributes(
            "morning_briefing",
            {
                "available": briefing_data.get("morning_briefing_available", False),
                "status_en": briefing_data.get("morning_briefing_status_en", ""),
                "status_ru": briefing_data.get("morning_briefing_status_ru", ""),
                "last_sent": briefing_data.get("last_morning_briefing"),
            },
        )

        await self._update_sensor_state(
            "evening_briefing", briefing_data.get("evening_briefing_status_ru", "Не сгенерирован")
        )
        await self._update_sensor_attributes(
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
            await self._update_sensor_state("briefing_last_sent", last_sent)

        logger.info("Updated briefing sensors via Supervisor API")

    async def update_ml_investor_sensors(self, ml_data: dict) -> None:
        """
        Обновление ML-сенсоров для ленивого инвестора через Supervisor API.

        Args:
            ml_data: Словарь с результатами ML-анализа для пассивных инвесторов
        """
        if not self._supervisor_client.is_available:
            logger.warning("Supervisor API недоступен, пропускаем обновление ML-сенсоров")
            return

        # Сенсор здоровья портфеля ML
        portfolio_sentiment = ml_data.get("portfolio_sentiment", "нейтральный")
        await self._supervisor_client.create_sensor(
            sensor_id="ml_portfolio_health",
            state=portfolio_sentiment,
            friendly_name="ML Portfolio Health",
            icon="mdi:heart-pulse",
            attributes={
                "sentiment": portfolio_sentiment,
                "opportunity_signals": ml_data.get("opportunity_signals", 0),
                "risk_signals": ml_data.get("risk_signals", 0),
                "hold_signals": ml_data.get("hold_signals", 0),
                "total_analyzed": ml_data.get("total_analyzed", 0),
                "recommendation": ml_data.get("recommendation", "Maintain current positions"),
                "last_analysis": ml_data.get("last_analysis", "N/A"),
                "confidence_threshold": ml_data.get("confidence_threshold", 70),
            },
        )

        # Сенсор уверенности рынка ML
        confidence_level = ml_data.get("confidence_level", "средний")
        await self._supervisor_client.create_sensor(
            sensor_id="ml_market_confidence",
            state=confidence_level,
            friendly_name="ML Market Confidence",
            icon="mdi:chart-bell-curve-cumulative",
            attributes={
                "level": confidence_level,
                "high_confidence_count": ml_data.get("high_confidence_count", 0),
                "medium_confidence_count": ml_data.get("medium_confidence_count", 0),
                "low_confidence_count": ml_data.get("low_confidence_count", 0),
                "confidence_threshold": ml_data.get("confidence_threshold", 70),
                "high_confidence_symbols": ml_data.get("high_confidence_symbols", []),
                "action_required": ml_data.get("action_required", False),
            },
        )

        # Сенсор инвестиционных возможностей ML
        opportunity_status = ml_data.get("opportunity_status", "нет")
        await self._supervisor_client.create_sensor(
            sensor_id="ml_investment_opportunity",
            state=opportunity_status,
            friendly_name="ML Investment Opportunity",
            icon="mdi:trending-up",
            attributes={
                "status": opportunity_status,
                "opportunity_symbols": ml_data.get("opportunity_symbols", []),
                "best_opportunity": ml_data.get("best_opportunity", "N/A"),
                "recommended_allocation": ml_data.get("recommended_allocation", 0),
                "timeframe": ml_data.get("opportunity_timeframe", "short_term"),
                "risk_level": ml_data.get("opportunity_risk", "low"),
            },
        )

        # Сенсор предупреждений о рисках ML
        risk_level = ml_data.get("risk_level", "чисто")
        await self._supervisor_client.create_sensor(
            sensor_id="ml_risk_warning",
            state=risk_level,
            friendly_name="ML Risk Warning",
            icon="mdi:alert-circle",
            attributes={
                "level": risk_level,
                "risk_symbols": ml_data.get("risk_symbols", []),
                "risk_factors": ml_data.get("risk_factors", []),
                "action_required": ml_data.get("risk_action_required", False),
                "protective_measures": ml_data.get("protective_measures", []),
                "stop_loss_recommendation": ml_data.get("stop_loss_recommendation", "N/A"),
            },
        )

        # Сенсор статуса ML-системы
        system_status = ml_data.get("system_status", "операционный")
        await self._supervisor_client.create_sensor(
            sensor_id="ml_system_status",
            state=system_status,
            friendly_name="ML System Status",
            icon="mdi:server-network",
            attributes={
                "status": system_status,
                "models_analyzed": ml_data.get("models_analyzed", 12),
                "average_accuracy": ml_data.get("average_accuracy", "50%"),
                "last_analysis": ml_data.get("last_analysis", "N/A"),
                "next_analysis": ml_data.get("next_analysis", "N/A"),
                "processing_time": ml_data.get("processing_time", "<5s"),
                "data_quality": ml_data.get("data_quality", "good"),
            },
        )

        logger.info("Обновлены ML-сенсоры ленивого инвестора через Supervisor API")

    async def update_ml_prediction_sensors(self, prediction_data: dict) -> None:
        """
        Обновление сенсоров ML-предсказаний и точности через Supervisor API.

        Args:
            prediction_data: Данные о последних предсказаниях и точности
        """
        from services.ha_integration import get_supervisor_client

        client = get_supervisor_client()
        if not client.is_available:
            logger.warning("Supervisor API недоступен, пропускаем обновление сенсоров предсказаний")
            return

        # Сенсор последних ML-предсказаний
        latest_predictions = prediction_data.get("latest_predictions", {})
        await self._supervisor_client.create_sensor(
            sensor_id="ml_latest_predictions",
            state=str(len(latest_predictions)),
            friendly_name="ML Latest Predictions",
            icon="mdi:history",
            unit="predictions",
            attributes={
                "latest_predictions": latest_predictions,
                "last_update": prediction_data.get("last_update", "N/A"),
                "total_count": len(latest_predictions),
                "correct_predictions": prediction_data.get("correct_predictions", 0),
                "incorrect_predictions": prediction_data.get("incorrect_predictions", 0),
                "accuracy_percentage": prediction_data.get("accuracy_percentage", 0),
            },
        )

        # Сенсор счетчика верных предсказаний
        correct_count = prediction_data.get("correct_predictions", 0)
        await self._supervisor_client.create_sensor(
            sensor_id="ml_correct_predictions",
            state=str(correct_count),
            friendly_name="ML Correct Predictions",
            icon="mdi:check-circle",
            unit="count",
            attributes={
                "correct_count": correct_count,
                "total_predictions": prediction_data.get("total_predictions", 0),
                "accuracy_percentage": prediction_data.get("accuracy_percentage", 0),
                "last_update": prediction_data.get("last_update", "N/A"),
            },
        )

        # Сенсор точности ML-моделей
        accuracy_rate = prediction_data.get("accuracy_percentage", 0)
        accuracy_text = f"{accuracy_rate}%"
        await self._supervisor_client.create_sensor(
            sensor_id="ml_accuracy_rate",
            state=accuracy_text,
            friendly_name="ML Accuracy Rate",
            icon="mdi:target",
            unit="%",
            attributes={
                "accuracy_percentage": accuracy_rate,
                "rating": self._get_accuracy_rating(accuracy_rate),
                "total_predictions": prediction_data.get("total_predictions", 0),
                "correct": prediction_data.get("correct_predictions", 0),
                "incorrect": prediction_data.get("incorrect_predictions", 0),
                "last_update": prediction_data.get("last_update", "N/A"),
            },
        )

        logger.info("Обновлены сенсоры ML-предсказаний и точности")

    def _get_accuracy_rating(self, accuracy: float) -> str:
        """Получение текстовой оценки точности."""
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

    async def update_goal_status(self, goal_data: dict) -> None:
        """
        Update goal tracking sensors via Supervisor API.

        Args:
            goal_data: Dict from GoalTracker.format_sensor_attributes()
        """
        if not self._supervisor_client.is_available:
            return

        await self._update_sensor_state("goal_target", str(goal_data.get("goal_target", 0)))
        await self._update_sensor_attributes(
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
        await self._update_sensor_state("goal_progress", f"{emoji} {progress:.1f}%")
        await self._update_sensor_attributes(
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

        await self._update_sensor_state("goal_remaining", str(goal_data.get("goal_remaining", 0)))

        days_estimate = goal_data.get("goal_days_estimate")
        if days_estimate is not None:
            await self._update_sensor_state("goal_days_estimate", str(days_estimate))
        else:
            await self._update_sensor_state("goal_days_estimate", "N/A")

        await self._update_sensor_state("goal_status", goal_data.get("goal_status_ru", "В процессе"))
        await self._update_sensor_attributes(
            "goal_status",
            {
                "status": goal_data.get("goal_status", ""),
                "status_en": goal_data.get("goal_status_en", ""),
                "status_ru": goal_data.get("goal_status_ru", ""),
                "milestone_message_en": goal_data.get("milestone_message", ""),
                "milestone_message_ru": goal_data.get("milestone_message_ru", ""),
            },
        )

        logger.info("Updated goal sensors via Supervisor API")

    async def update_economic_calendar_sensors(self) -> None:
        """Update economic calendar sensors."""
        if not self._supervisor_client.is_available:
            return
        
        try:
            from services.economic_calendar import get_economic_calendar, EventImpact
            
            calendar = get_economic_calendar()
            
            # Initialize if needed
            if not calendar._last_update:
                await calendar.initialize_events()
            
            # Get calendar summary
            summary = await calendar.get_calendar_summary()
            
            # Update status
            await self._update_sensor_state("economic_calendar_status", "Active")
            
            # Update event counts
            await self._update_sensor_state(
                "economic_upcoming_events_24h",
                str(summary["upcoming_events_24h"])
            )
            await self._update_sensor_state(
                "economic_important_events",
                str(summary["important_events"])
            )
            await self._update_sensor_state(
                "economic_breaking_news",
                str(summary["breaking_news"])
            )
            
            # Update sentiment score
            sentiment_data = await calendar.get_sentiment_analysis()
            sentiment_score = sentiment_data["average_sentiment"]
            
            # Map sentiment score to readable format
            if sentiment_score >= 0.5:
                sentiment_state = f"🟢 Very Positive ({sentiment_score:+.2f})"
            elif sentiment_score >= 0.1:
                sentiment_state = f"🔵 Positive ({sentiment_score:+.2f})"
            elif sentiment_score <= -0.5:
                sentiment_state = f"🔴 Very Negative ({sentiment_score:+.2f})"
            elif sentiment_score <= -0.1:
                sentiment_state = f"🟠 Negative ({sentiment_score:+.2f})"
            else:
                sentiment_state = f"⚪ Neutral ({sentiment_score:+.2f})"
            
            await self._update_sensor_state("economic_sentiment_score", sentiment_state)
            
            # Update attributes with detailed information
            attributes = {
                "upcoming_events_48h": summary["upcoming_events_48h"],
                "recent_events_24h": summary["recent_events_24h"],
                "high_impact_events": summary["high_impact_events"],
                "critical_events": summary["critical_events"],
                "relevant_news_24h": summary["relevant_news_24h"],
                "next_event": summary["next_event"],
                "sentiment_details": {
                    "label": sentiment_data["sentiment_label"],
                    "positive_news": sentiment_data["positive_news"],
                    "negative_news": sentiment_data["negative_news"],
                    "neutral_news": sentiment_data["neutral_news"]
                },
                "last_update": summary["last_update"]
            }
            
            await self._update_sensor_attributes("economic_calendar_status", attributes)
            
            # Log significant events
            if summary["upcoming_events_24h"] > 0:
                logger.info(f"Economic calendar: {summary['upcoming_events_24h']} events in next 24h")
            if summary["breaking_news"] > 0:
                logger.info(f"Breaking news: {summary['breaking_news']} articles")
            
        except ImportError:
            logger.warning("Economic calendar not available, skipping sensor updates")
            await self._update_sensor_state("economic_calendar_status", "Not Available")
        except Exception as e:
            logger.error(f"Failed to update economic calendar sensors: {e}")
            await self._update_sensor_state("economic_calendar_status", "Error")
    
    async def update_correlation_sensors(self) -> None:
        """Update smart correlation analysis sensors."""
        if not self._supervisor_client.is_available:
            return
        
        try:
            from services.smart_correlation import get_correlation_engine
            
            correlation_engine = get_correlation_engine()
            
            # Get correlation summary
            summary = await correlation_engine.get_correlation_summary()
            
            if summary["status"] == "no_data":
                await self._update_sensor_state("correlation_analysis_status", "No Data")
                await self._update_sensor_state("correlation_significant_count", "0")
                await self._update_sensor_state("correlation_dominant_patterns", "0")
                await self._update_sensor_state("correlation_strongest_positive", "N/A")
                await self._update_sensor_state("correlation_strongest_negative", "N/A")
                return
            
            # Update status
            await self._update_sensor_state("correlation_analysis_status", "Active")
            
            # Update counts
            await self._update_sensor_state(
                "correlation_significant_count", 
                str(summary["significant_correlations"])
            )
            await self._update_sensor_state(
                "correlation_dominant_patterns",
                str(summary.get("dominant_patterns", 0))
            )
            
            # Update strongest correlations
            pos_corr = summary.get("strongest_positive", "N/A")
            neg_corr = summary.get("strongest_negative", "N/A")
            
            await self._update_sensor_state("correlation_strongest_positive", pos_corr)
            await self._update_sensor_state("correlation_strongest_negative", neg_corr)
            
            # Update attributes with detailed information
            attributes = {
                "total_correlations": summary.get("total_correlations", 0),
                "trading_opportunities": summary.get("trading_opportunities", 0),
                "risk_indicators": summary.get("risk_indicators", 0),
                "last_analysis": summary.get("timestamp", "N/A"),
                "analysis_details": {
                    "positive_correlation": pos_corr,
                    "negative_correlation": neg_corr
                }
            }
            
            await self._update_sensor_attributes("correlation_analysis_status", attributes)
            
            logger.info(
                f"Updated correlation sensors: "
                f"{summary['significant_correlations']} significant correlations, "
                f"{summary.get('dominant_patterns', 0)} patterns"
            )
            
        except ImportError:
            logger.warning("Smart correlation engine not available, skipping sensor updates")
            await self._update_sensor_state("correlation_analysis_status", "Not Available")
        except Exception as e:
            logger.error(f"Failed to update correlation sensors: {e}")
            await self._update_sensor_state("correlation_analysis_status", "Error")
    
    async def update_adaptive_notification_sensors(self) -> None:
        """Update adaptive notification system sensors."""
        if not self._supervisor_client.is_available:
            return
        
        try:
            from services.adaptive_notifications import get_adaptive_notifications, MarketVolatility
            
            notification_manager = get_adaptive_notifications()
            
            # Update volatility profiles
            await notification_manager.update_volatility_profiles()
            
            # Update status sensor
            status_state = "active" if notification_manager.rules else "inactive"
            await self._update_sensor_state("adaptive_notifications_status", status_state)
            
            # Update volatility sensors
            volatility_status = notification_manager.get_volatility_status()
            
            # Initialize consolidated data structures
            volatility_states = {}
            adaptation_factors = {}
            detailed_data = {}
            
            for symbol, profile in volatility_status.items():
                coin_id = "btc" if "BTC" in symbol else "eth"
                
                # Collect data for consolidated sensors
                volatility_level = profile["volatility_level"]
                level_mapping = {
                    "very_low": "🟢 Very Low",
                    "low": "🟡 Low", 
                    "moderate": "🔵 Moderate",
                    "high": "🟠 High",
                    "very_high": "🔴 Very High"
                }
                volatility_states[coin_id.upper()] = level_mapping.get(volatility_level, "Unknown")
                
                adaptation_factors[coin_id.upper()] = round(profile["adaptation_factor"], 1)
                
                # Store detailed data for attributes
                detailed_data[coin_id.upper()] = {
                    "current_volatility": f"{profile['current_volatility']:.2f}%",
                    "price_change_24h": f"{profile['price_change_24h']:+.2f}%",
                    "price_change_1h": f"{profile['price_change_1h']:+.2f}%",
                    "last_update": profile["last_update"]
                }
            
            # Update consolidated sensors
            await self._publish_state("adaptive_volatilities", volatility_states)
            await self._publish_state("adaptive_adaptation_factors", adaptation_factors)
            await self._publish_attributes("adaptive_volatilities", detailed_data)
            
            # Update notification count sensor
            stats = await notification_manager.get_notification_stats()
            await self._update_sensor_state("adaptive_notification_count_24h", str(stats["recent_24h"]))
            
            # Update notification count attributes
            count_attributes = {
                "total_sent": stats["total_sent"],
                "by_priority": stats["by_priority"],
                "by_symbol": stats["by_symbol"],
                "last_notification": stats["last_notification"]
            }
            await self._update_sensor_attributes("adaptive_notification_count_24h", count_attributes)
            
            logger.info("Updated adaptive notification sensors")
            
        except ImportError:
            logger.warning("Adaptive notifications not available, skipping sensor updates")
        except Exception as e:
            logger.error(f"Failed to update adaptive notification sensors: {e}")
    
    async def update_ai_trend_sensors(self) -> None:
        """Update AI trend analysis sensors for major cryptocurrencies."""
        if not self._supervisor_client.is_available:
            return
        
        try:
            from services.trend_analyzer import get_trend_analyzer, TrendDirection, TrendConfidence
            
            analyzer = get_trend_analyzer()
            symbols = ["BTC/USDT", "ETH/USDT"]
            
            # Initialize consolidated data structures
            ai_trends = {}
            ai_confidences = {}
            ai_forecasts = {}
            ai_details = {}
            
            for symbol in symbols:
                try:
                    # Analyze trend
                    analysis = await analyzer.analyze_trend(symbol, "1h", lookback_days=30)
                    
                    # Map trend direction to readable format
                    direction_map = {
                        TrendDirection.STRONGLY_BULLISH: "🚀 Strong Bullish",
                        TrendDirection.BULLISH: "📈 Bullish",
                        TrendDirection.NEUTRAL: "⏸️ Neutral",
                        TrendDirection.BEARISH: "📉 Bearish",
                        TrendDirection.STRONGLY_BEARISH: "💥 Strong Bearish"
                    }
                    
                    # Get coin identifier
                    coin_id = "btc" if "BTC" in symbol else "eth"
                    coin_key = coin_id.upper()
                    
                    # Collect data for consolidated sensors
                    trend_state = direction_map.get(analysis.direction, "Unknown")
                    ai_trends[coin_key] = trend_state
                    ai_confidences[coin_key] = round(analysis.confidence, 1)
                    ai_forecasts[coin_key] = round(analysis.predicted_price_24h, 2)
                    
                    # Store detailed analysis
                    ai_details[coin_key] = {
                        "confidence_level": analysis.confidence_level.value,
                        "technical_score": analysis.technical_score,
                        "ml_consensus": analysis.ml_consensus,
                        "ml_confidence": analysis.ml_confidence,
                        "volatility": analysis.volatility,
                        "volume_trend": analysis.volume_trend,
                        "market_phase": analysis.market_phase,
                        "risk_level": analysis.risk_level,
                        "risk_factors": analysis.risk_factors,
                        "support_levels": analysis.support_levels[:3],
                        "resistance_levels": analysis.resistance_levels[:3],
                        "price_change_24h_pct": analysis.price_change_24h_pct,
                        "price_change_7d_pct": analysis.price_change_7d_pct,
                        "models_used": analysis.models_used,
                        "last_analysis": analysis.timestamp.isoformat()
                    }
                    
                    logger.info(f"Updated AI sensors for {symbol}: {trend_state} ({analysis.confidence:.1f}% confidence)")
                    
                except Exception as e:
                    logger.error(f"Failed to update AI sensors for {symbol}: {e}")
                    # Set error states in consolidated data
                    coin_id = "btc" if "BTC" in symbol else "eth"
                    coin_key = coin_id.upper()
                    ai_trends[coin_key] = "Error"
                    ai_confidences[coin_key] = 0
                    ai_forecasts[coin_key] = 0
        
            # Update consolidated AI sensors
            await self._publish_state("ai_trends", ai_trends)
            await self._publish_state("ai_confidences", ai_confidences)
            await self._publish_state("ai_price_forecasts_24h", ai_forecasts)
            await self._publish_attributes("ai_trends", ai_details)
            
        except ImportError:
            logger.warning("Trend analyzer not available, skipping AI sensor updates")
            # Set error states for consolidated sensors
            await self._publish_state("ai_trends", {"BTC": "Error", "ETH": "Error"})
            await self._publish_state("ai_confidences", {"BTC": 0, "ETH": 0})
            await self._publish_state("ai_price_forecasts_24h", {"BTC": 0, "ETH": 0})
        except Exception as e:
            logger.error(f"Failed to update AI trend sensors: {e}")
            # Set error states for consolidated sensors
            await self._publish_state("ai_trends", {"BTC": "Error", "ETH": "Error"})
            await self._publish_state("ai_confidences", {"BTC": 0, "ETH": 0})
            await self._publish_state("ai_price_forecasts_24h", {"BTC": 0, "ETH": 0})
    
    async def update_database_size(self) -> None:
        """Update database size sensor."""
        if not self._supervisor_client.is_available:
            return
        
        try:
            # Get database file size
            db_path = Path(settings.db_path)
            if db_path.exists():
                size_bytes = db_path.stat().st_size
                size_mb = round(size_bytes / (1024 * 1024), 2)
                await self._update_sensor_state("database_size", str(size_mb))
                logger.debug(f"Database size: {size_mb} MB")
            else:
                await self._update_sensor_state("database_size", "0")
                logger.warning("Database file not found")
        except Exception as e:
            logger.error(f"Failed to get database size: {e}")
            await self._update_sensor_state("database_size", "error")
    
    async def cleanup_historical_data(self, keep_days: int = 30, min_candles: int = 1000) -> dict:
        """
        Cleanup historical candle data.
        
        Args:
            keep_days: Days of history to keep
            min_candles: Minimum candles to preserve per symbol
            
        Returns:
            Dict with cleanup statistics
        """
        if not self._supervisor_client.is_available:
            return {"error": "Supervisor API not available"}
        
        try:
            from datetime import datetime, timedelta, UTC
            from sqlalchemy import text
            from src.core.db import get_db_session
            
            cutoff_date = datetime.now(UTC) - timedelta(days=keep_days)
            deleted_count = 0
            symbols_affected = []
            
            # Get current candles count before cleanup
            async with get_db_session() as session:
                result = await session.execute(text("SELECT COUNT(*) FROM candles"))
                total_before = result.scalar_one()
            
            # Delete old candles (keeping minimum per symbol)
            async with get_db_session() as session:
                # First, get symbols that have old data
                result = await session.execute(
                    text("""
                        SELECT symbol, COUNT(*) as candle_count
                        FROM candles 
                        WHERE timestamp < :cutoff_date
                        GROUP BY symbol
                        HAVING COUNT(*) > :min_candles
                    """),
                    {"cutoff_date": cutoff_date, "min_candles": min_candles}
                )
                
                for row in result:
                    symbol = row.symbol
                    # Delete oldest candles, keeping min_candles
                    result = await session.execute(
                        text("""
                            DELETE FROM candles 
                            WHERE symbol = :symbol 
                            AND timestamp < :cutoff_date
                            AND id NOT IN (
                                SELECT id FROM candles 
                                WHERE symbol = :symbol 
                                ORDER BY timestamp DESC 
                                LIMIT :min_candles
                            )
                        """),
                        {"symbol": symbol, "cutoff_date": cutoff_date, "min_candles": min_candles}
                    )
                    deleted = result.rowcount
                    if deleted > 0:
                        deleted_count += deleted
                        symbols_affected.append(symbol)
                        logger.info(f"Cleaned {deleted} candles for {symbol}")
                
                await session.commit()
            
            # Get count after cleanup
            async with get_db_session() as session:
                result = await session.execute(text("SELECT COUNT(*) FROM candles"))
                total_after = result.scalar_one()
            
            # Update sensors
            stats = {
                "deleted_candles": deleted_count,
                "symbols_affected": len(symbols_affected),
                "symbols_list": symbols_affected,
                "total_before": total_before,
                "total_after": total_after,
                "space_freed_mb": round((total_before - total_after) * 0.001, 2),  # Rough estimate
                "keep_days": keep_days,
                "min_candles": min_candles,
                "cleanup_timestamp": datetime.now(UTC).isoformat()
            }
            
            # Update database size sensor
            await self.update_database_size()
            
            logger.info(f"Cleanup completed: {deleted_count} candles removed from {len(symbols_affected)} symbols")
            return stats
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return {"error": str(e)}
    
    async def cleanup_database(self) -> dict:
        """
        Perform full database maintenance.
        Includes VACUUM and ANALYZE operations.
        """
        if not self._supervisor_client.is_available:
            return {"error": "Supervisor API not available"}
        
        try:
            from sqlalchemy import text
            from src.core.db import get_db_session
            
            logger.info("Starting database maintenance...")
            
            # Get size before maintenance
            db_path = Path(settings.db_path)
            size_before = db_path.stat().st_size if db_path.exists() else 0
            
            # Perform VACUUM and ANALYZE
            async with get_db_session() as session:
                await session.execute(text("VACUUM"))
                await session.execute(text("ANALYZE"))
                await session.commit()
            
            # Get size after maintenance
            size_after = db_path.stat().st_size if db_path.exists() else 0
            space_saved = size_before - size_after
            
            stats = {
                "operation": "vacuum_analyze",
                "size_before_mb": round(size_before / (1024 * 1024), 2),
                "size_after_mb": round(size_after / (1024 * 1024), 2),
                "space_saved_mb": round(space_saved / (1024 * 1024), 2),
                "maintenance_timestamp": datetime.now(UTC).isoformat()
            }
            
            # Update database size sensor
            await self.update_database_size()
            
            logger.info(f"Database maintenance completed. Saved {stats['space_saved_mb']} MB")
            return stats
            
        except Exception as e:
            logger.error(f"Database maintenance failed: {e}")
            return {"error": str(e)}

# Global instance
_sensors_manager: CryptoSensorsManager | None = None


def get_sensors_manager() -> CryptoSensorsManager:
    """Get or create sensors manager."""
    global _sensors_manager
    if _sensors_manager is None:
        _sensors_manager = CryptoSensorsManager()
    return _sensors_manager
