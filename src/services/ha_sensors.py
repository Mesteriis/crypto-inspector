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

from core.constants import APP_VERSION

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
            "name": "Разблокировки 7д",
            "icon": "mdi:lock-open-variant",
            "description": "Разблокировки токенов за 7 дней",
        },
        "unlock_next_event": {
            "name": "Следующий анлок",
            "icon": "mdi:calendar-lock",
            "description": "Ближайшая разблокировка",
        },
        "unlock_risk_level": {
            "name": "Риск анлоков",
            "icon": "mdi:alert-circle",
            "description": "Уровень риска от разблокировок",
        },
        # === Макрокалендарь ===
        "next_macro_event": {
            "name": "Следующее макрособытие",
            "icon": "mdi:calendar-star",
            "description": "Ближайшее важное макрособытие",
        },
        "days_to_fomc": {
            "name": "Дней до FOMC",
            "icon": "mdi:calendar-clock",
            "description": "Дней до заседания ФРС",
        },
        "macro_risk_week": {
            "name": "Макрориск недели",
            "icon": "mdi:calendar-alert",
            "description": "Риск на неделе: низкий/средний/высокий",
        },
        # === Арбитраж (dict формат) ===
        "arb_spreads": {
            "name": "Спреды арбитража",
            "icon": "mdi:swap-horizontal-bold",
            "description": "Разница цен между биржами",
        },
        "funding_arb_best": {
            "name": "Лучший фандинг-арб",
            "icon": "mdi:cash-multiple",
            "description": "Лучшая возможность для фандинг-арбитража",
        },
        "arb_opportunity": {
            "name": "Возможность арбитража",
            "icon": "mdi:lightning-bolt",
            "description": "Есть ли арбитражная возможность",
        },
        # === Фиксация прибыли (dict формат) ===
        "tp_levels": {
            "name": "Уровни фиксации",
            "icon": "mdi:target-variant",
            "description": "Рекомендуемые уровни Take Profit",
        },
        "profit_action": {
            "name": "Действие по прибыли",
            "icon": "mdi:cash-check",
            "description": "Рекомендация: держать/фиксировать",
        },
        "greed_level": {
            "name": "Уровень жадности",
            "icon": "mdi:emoticon-devil",
            "description": "Насколько перекуплен рынок (0-100)",
        },
        # === Традиционные финансы ===
        "gold_price": {
            "name": "Золото",
            "icon": "mdi:gold",
            "unit": "USD",
            "description": "Цена золота XAU/USD",
        },
        "silver_price": {
            "name": "Серебро",
            "icon": "mdi:circle-outline",
            "unit": "USD",
            "description": "Цена серебра XAG/USD",
        },
        "platinum_price": {
            "name": "Платина",
            "icon": "mdi:diamond-stone",
            "unit": "USD",
            "description": "Цена платины",
        },
        "sp500_price": {
            "name": "Индекс S&P 500",
            "icon": "mdi:chart-line",
            "unit": "USD",
            "description": "Американский фондовый индекс S&P 500",
        },
        "nasdaq_price": {
            "name": "Индекс NASDAQ",
            "icon": "mdi:chart-areaspline",
            "unit": "USD",
            "description": "Индекс технологических компаний NASDAQ",
        },
        "dji_price": {
            "name": "Индекс Dow Jones",
            "icon": "mdi:chart-bar",
            "unit": "USD",
            "description": "Промышленный индекс Dow Jones",
        },
        "dax_price": {
            "name": "Индекс DAX",
            "icon": "mdi:chart-timeline-variant",
            "unit": "EUR",
            "description": "Немецкий фондовый индекс DAX",
        },
        "eur_usd": {
            "name": "Курс EUR/USD",
            "icon": "mdi:currency-eur",
            "description": "Курс евро к доллару",
        },
        "gbp_usd": {
            "name": "Курс GBP/USD",
            "icon": "mdi:currency-gbp",
            "description": "Курс фунта к доллару",
        },
        "dxy_index": {
            "name": "Индекс доллара",
            "icon": "mdi:currency-usd",
            "description": "Индекс DXY - сила доллара",
        },
        "oil_brent": {
            "name": "Нефть Brent",
            "icon": "mdi:barrel",
            "unit": "USD",
            "description": "Цена нефти Brent",
        },
        "oil_wti": {
            "name": "Нефть WTI",
            "icon": "mdi:barrel",
            "unit": "USD",
            "description": "Цена нефти WTI",
        },
        "natural_gas": {
            "name": "Природный газ",
            "icon": "mdi:fire",
            "unit": "USD",
            "description": "Цена природного газа",
        },
        # === AI анализ ===
        "ai_daily_summary": {
            "name": "AI дневная сводка",
            "icon": "mdi:robot",
            "description": "Ежедневная AI-сводка по рынку",
        },
        "ai_market_sentiment": {
            "name": "AI настроение",
            "icon": "mdi:brain",
            "description": "Оценка настроения рынка от AI",
        },
        "ai_recommendation": {
            "name": "AI рекомендация",
            "icon": "mdi:lightbulb",
            "description": "Рекомендация AI по действиям",
        },
        "ai_last_analysis": {
            "name": "AI последний анализ",
            "icon": "mdi:clock-outline",
            "description": "Время последнего AI-анализа",
        },
        "ai_provider": {
            "name": "AI провайдер",
            "icon": "mdi:cog",
            "entity_category": "diagnostic",
            "description": "Используемый AI-провайдер",
        },
        # === Технические индикаторы (dict формат) ===
        "ta_rsi": {
            "name": "RSI индикатор",
            "icon": "mdi:chart-line",
            "description": 'RSI(14) для всех монет. Формат: {"BTC": 65}',
        },
        "ta_macd_signal": {
            "name": "MACD сигналы",
            "icon": "mdi:signal",
            "description": 'MACD сигналы. Формат: {"BTC": "bullish"}',
        },
        "ta_bb_position": {
            "name": "Позиция BB",
            "icon": "mdi:chart-bell-curve",
            "description": 'Позиция в Bollinger Bands. Формат: {"BTC": 0.7}',
        },
        "ta_trend": {
            "name": "Тренды",
            "icon": "mdi:trending-up",
            "description": 'Направление тренда. Формат: {"BTC": "uptrend"}',
        },
        "ta_support": {
            "name": "Уровни поддержки",
            "icon": "mdi:arrow-down-bold",
            "description": 'Ближайшие уровни поддержки. Формат: {"BTC": 90000}',
        },
        "ta_resistance": {
            "name": "Уровни сопротивления",
            "icon": "mdi:arrow-up-bold",
            "description": 'Ближайшие уровни сопротивления. Формат: {"BTC": 100000}',
        },
        # === MTF тренды ===
        "ta_trend_mtf": {
            "name": "MTF тренды",
            "icon": "mdi:clock-outline",
            "description": "Тренды на разных таймфреймах",
        },
        # === TA Confluence ===
        "ta_confluence": {
            "name": "Конфлюенс TA",
            "icon": "mdi:check-all",
            "description": "Скор схождения индикаторов (0-100)",
        },
        "ta_signal": {
            "name": "TA сигнал",
            "icon": "mdi:traffic-light",
            "description": "Общий сигнал TA: buy/sell/hold",
        },
        # === Управление рисками ===
        "portfolio_sharpe": {
            "name": "Коэффициент Шарпа",
            "icon": "mdi:chart-areaspline",
            "description": "Соотношение доходности к риску",
        },
        "portfolio_sortino": {
            "name": "Коэффициент Сортино",
            "icon": "mdi:chart-line-variant",
            "description": "Оценка риска с учётом падений",
        },
        "portfolio_max_drawdown": {
            "name": "Макс. просадка",
            "icon": "mdi:trending-down",
            "unit": "%",
            "description": "Максимальная историческая просадка",
        },
        "portfolio_current_drawdown": {
            "name": "Текущая просадка",
            "icon": "mdi:arrow-down",
            "unit": "%",
            "description": "Текущая просадка от максимума",
        },
        "portfolio_var_95": {
            "name": "VaR 95%",
            "icon": "mdi:alert",
            "unit": "%",
            "description": "Стоимость под риском (95% доверия)",
        },
        "risk_status": {
            "name": "Статус риска",
            "icon": "mdi:shield-alert",
            "description": "Общий статус: низкий/средний/высокий",
        },
        # === Бэктест ===
        "backtest_dca_roi": {
            "name": "DCA бэктест ROI",
            "icon": "mdi:percent",
            "unit": "%",
            "description": "Доходность DCA стратегии в бэктесте",
        },
        "backtest_smart_dca_roi": {
            "name": "Smart DCA ROI",
            "icon": "mdi:brain",
            "unit": "%",
            "description": "Доходность умного DCA",
        },
        "backtest_lump_sum_roi": {
            "name": "Lump Sum ROI",
            "icon": "mdi:cash",
            "unit": "%",
            "description": "Доходность единоразовой покупки",
        },
        "backtest_best_strategy": {
            "name": "Лучшая стратегия",
            "icon": "mdi:trophy",
            "description": "Лучшая стратегия по бэктесту",
        },
        # === Умная сводка (UX) ===
        "market_pulse": {
            "name": "Пульс рынка",
            "icon": "mdi:pulse",
            "description": "Общее настроение рынка",
        },
        "market_pulse_confidence": {
            "name": "Уверенность пульса",
            "icon": "mdi:percent",
            "unit": "%",
            "description": "Уверенность в оценке рынка (%)",
        },
        "portfolio_health": {
            "name": "Здоровье портфеля",
            "icon": "mdi:shield-check",
            "description": "Общая оценка здоровья портфеля",
        },
        "portfolio_health_score": {
            "name": "Скор здоровья",
            "icon": "mdi:counter",
            "unit": "%",
            "description": "Оценка здоровья портфеля (0-100%)",
        },
        "today_action": {
            "name": "Действие сегодня",
            "icon": "mdi:clipboard-check",
            "description": "Рекомендуемое действие на сегодня",
        },
        "today_action_priority": {
            "name": "Приоритет действия",
            "icon": "mdi:alert-circle",
            "description": "Срочность: низкая/средняя/высокая",
        },
        "weekly_outlook": {
            "name": "Прогноз на неделю",
            "icon": "mdi:calendar-week",
            "description": "Краткий прогноз на неделю",
        },
        # === Алерты и уведомления (UX) ===
        "pending_alerts_count": {
            "name": "Ожидающие алерты",
            "icon": "mdi:bell-badge",
            "description": "Количество необработанных алертов",
        },
        "pending_alerts_critical": {
            "name": "Критические алерты",
            "icon": "mdi:bell-alert",
            "description": "Количество критических алертов",
        },
        "daily_digest_ready": {
            "name": "Дневной дайджест",
            "icon": "mdi:newspaper",
            "description": "Готов ли дневной дайджест",
        },
        "notification_mode": {
            "name": "Режим уведомлений",
            "icon": "mdi:bell-cog",
            "description": "Текущий режим: все/важные/тихий",
        },
        # === Брифинги (UX) ===
        "morning_briefing": {
            "name": "Утренний брифинг",
            "icon": "mdi:weather-sunny",
            "description": "Утренняя сводка по рынку",
        },
        "evening_briefing": {
            "name": "Вечерний брифинг",
            "icon": "mdi:weather-night",
            "description": "Вечерняя сводка по рынку",
        },
        "briefing_last_sent": {
            "name": "Последний брифинг",
            "icon": "mdi:clock-check",
            "device_class": "timestamp",
            "description": "Время последнего брифинга",
        },
        # === Отслеживание целей (UX) ===
        "goal_target": {
            "name": "Цель",
            "icon": "mdi:flag-checkered",
            "unit": "USDT",
            "description": "Целевая сумма портфеля",
        },
        "goal_progress": {
            "name": "Прогресс цели",
            "icon": "mdi:progress-check",
            "unit": "%",
            "description": "Процент достижения цели",
        },
        "goal_remaining": {
            "name": "Осталось до цели",
            "icon": "mdi:cash-minus",
            "unit": "USDT",
            "description": "Сколько осталось до цели",
        },
        "goal_days_estimate": {
            "name": "Дней до цели",
            "icon": "mdi:calendar-clock",
            "description": "Оценка дней до достижения",
        },
        "goal_status": {
            "name": "Статус цели",
            "icon": "mdi:trophy",
            "description": "Статус: в процессе/достигнута/отложена",
        },
        # === Диагностические сенсоры ===
        "sync_status": {
            "name": "Статус синхронизации",
            "icon": "mdi:sync",
            "entity_category": "diagnostic",
            "description": "Статус: idle/running/completed/error",
        },
        "last_sync": {
            "name": "Последняя синхронизация",
            "icon": "mdi:clock-outline",
            "device_class": "timestamp",
            "entity_category": "diagnostic",
            "description": "Время последней синхронизации",
        },
        "candles_count": {
            "name": "Всего свечей",
            "icon": "mdi:database",
            "unit": "свечей",
            "entity_category": "diagnostic",
            "description": "Общее количество свечей в БД",
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
            "sw_version": APP_VERSION,
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

    async def update_ml_investor_sensors(self, ml_data: dict) -> None:
        """
        Обновление ML-сенсоров для ленивого инвестора через Supervisor API.

        Args:
            ml_data: Словарь с результатами ML-анализа для пассивных инвесторов
        """
        from services.ha_integration import get_supervisor_client

        client = get_supervisor_client()
        if not client.is_available:
            logger.warning("Supervisor API недоступен, пропускаем обновление ML-сенсоров")
            return

        # Сенсор здоровья портфеля ML
        portfolio_sentiment = ml_data.get("portfolio_sentiment", "нейтральный")
        await client.create_sensor(
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
        await client.create_sensor(
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
        await client.create_sensor(
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
        await client.create_sensor(
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
        await client.create_sensor(
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
        await client.create_sensor(
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
        await client.create_sensor(
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
        await client.create_sensor(
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
