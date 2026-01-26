# Crypto Inspect - Documentation

## Обзор

Crypto Inspect - это профессиональный криптовалютный анализатор, интегрированный с Home Assistant. Add-on собирает рыночные данные, анализирует тренды, отслеживает ваш портфель на Bybit и отправляет все данные в виде сенсоров.

**Version:** 1.0.0 (Stable)

## Быстрый старт

1. Установите add-on или custom component
2. Настройте Bybit API ключи (опционально)
3. Запустите add-on
4. Сенсоры появятся автоматически в Home Assistant
5. Настройте input helpers и blueprints (см. ниже)

---

## Варианты установки

### Вариант 1: Home Assistant Add-on (рекомендуется)

Самый простой способ - использовать как Home Assistant Add-on.

1. Добавьте репозиторий в Supervisor:
   ```
   https://github.com/Mesteriis/crypto-inspector
   ```

2. Установите add-on "Crypto Inspect"

3. Настройте параметры в UI

4. Запустите add-on

### Вариант 2: Custom Component

Custom Component позволяет использовать Crypto Inspect как нативную интеграцию Home Assistant. Полезно если:
- Вы не используете Home Assistant OS/Supervised
- Хотите запустить API сервер отдельно (на другом сервере)
- Используете Home Assistant Container

#### Установка через HACS

1. Откройте HACS в Home Assistant
2. Перейдите в "Integrations"
3. Нажмите меню (три точки) -> "Custom repositories"
4. Добавьте URL: `https://github.com/Mesteriis/crypto-inspector`
5. Выберите категорию: Integration
6. Найдите "Crypto Inspect" и установите
7. Перезапустите Home Assistant

#### Ручная установка Custom Component

1. Скачайте или клонируйте репозиторий:
   ```bash
   git clone https://github.com/Mesteriis/crypto-inspector
   ```

2. Скопируйте папку `custom_components/crypto_inspect/` в `/config/custom_components/`:
   ```bash
   cp -r crypto-inspector/custom_components/crypto_inspect /config/custom_components/
   ```

3. Структура должна быть:
   ```
   /config/custom_components/crypto_inspect/
   ├── __init__.py
   ├── config_flow.py
   ├── const.py
   ├── coordinator.py
   ├── manifest.json
   ├── sensor.py
   ├── strings.json
   └── translations/
       ├── en.json
       └── ru.json
   ```

4. Перезапустите Home Assistant

5. Добавьте интеграцию:
   - Settings -> Devices & Services -> Add Integration
   - Найдите "Crypto Inspect"
   - Введите URL API сервера

#### Настройка Custom Component

При добавлении интеграции нужно указать:

| Параметр | Описание | По умолчанию |
|----------|----------|--------------|
| Host | URL API сервера | `http://localhost:9999` |
| Update interval | Интервал обновления (сек) | `60` |

**Примеры URL:**
- Add-on в том же HA: `http://localhost:9999`
- Add-on по IP: `http://192.168.1.100:9999`
- Docker контейнер: `http://crypto-inspect:9999`
- Удалённый сервер: `http://myserver.local:9999`

### Вариант 3: Standalone (Docker)

Запустите API сервер отдельно без Home Assistant Add-on:

```bash
git clone https://github.com/Mesteriis/crypto-inspector
cd crypto-inspector
docker-compose up -d
```

Затем подключите Custom Component к этому серверу.

### Вариант 4: Standalone (разработка)

Для локальной разработки с использованием `uv`:

```bash
git clone https://github.com/Mesteriis/crypto-inspector
cd crypto-inspector
uv sync
uv run python -m src.main
```

API сервер будет доступен на `http://localhost:9999`.

---

## Ручная настройка Input Helpers и Blueprints

Home Assistant не поддерживает автоматическое создание input helpers и blueprints через REST API.
Ниже инструкции по ручной настройке.

### 📁 Установка Blueprints

**Исходные файлы:** `/addon_configs/local_crypto_inspect/blueprints/` или в репозитории: [`blueprints/`](https://github.com/Mesteriis/crypto-inspector/tree/main/blueprints)

**Куда копировать:** `/config/blueprints/automation/crypto_inspect/`

**Список blueprint-ов:**

| Файл | Описание |
|------|----------|
| `price_alert.yaml` | Ценовые алерты |
| `fear_greed_alert.yaml` | Алерты Fear & Greed Index |
| `dca_reminder.yaml` | Напоминания о DCA |
| `technical_signal.yaml` | Технические сигналы |
| `morning_briefing.yaml` | Утренний брифинг |
| `evening_briefing.yaml` | Вечерний брифинг |
| `daily_digest.yaml` | Ежедневный дайджест |
| `weekly_summary.yaml` | Недельный обзор |
| `whale_alert.yaml` | Алерты китов |
| `risk_alert.yaml` | Риск-алерты |
| `rsi_alert.yaml` | RSI алерты |
| `drawdown_alert.yaml` | Алерты просадки |
| `gas_price_alert.yaml` | Алерты цены газа |
| `goal_milestone.yaml` | Достижение целей |
| `portfolio_milestone.yaml` | Milestone портфеля |
| `ai_report.yaml` | AI отчёт |
| `market_phase_change.yaml` | Смена фазы рынка |
| `adaptive_notifications.yaml` | Адаптивные уведомления |

**Создание автоматизации из blueprint:**
1. Настройки → Автоматизации → Создать автоматизацию
2. Выберите "Использовать blueprint"
3. Выберите нужный blueprint из папки `crypto_inspect`
4. Заполните параметры и сохраните

---

### ⚙️ Настройка Input Helpers

Добавьте в `configuration.yaml` или создайте через UI (Настройки → Устройства и службы → Вспомогательные):

```yaml
# /config/configuration.yaml

# ============================================
# CRYPTO INSPECT - INPUT HELPERS
# ============================================

input_number:
  # DCA настройки
  crypto_dca_weekly_amount:
    name: "DCA недельный бюджет"
    min: 10
    max: 10000
    step: 10
    initial: 100
    unit_of_measurement: "€"
    icon: mdi:cash
  crypto_dca_btc_weight:
    name: "DCA вес BTC"
    min: 0
    max: 100
    step: 5
    initial: 50
    unit_of_measurement: "%"
    icon: mdi:bitcoin
    mode: slider
  crypto_dca_eth_weight:
    name: "DCA вес ETH"
    min: 0
    max: 100
    step: 5
    initial: 30
    unit_of_measurement: "%"
    icon: mdi:ethereum
    mode: slider
  crypto_dca_alt_weight:
    name: "DCA вес Alts"
    min: 0
    max: 100
    step: 5
    initial: 20
    unit_of_measurement: "%"
    icon: mdi:currency-usd
    mode: slider

  # RSI пороги
  crypto_rsi_oversold:
    name: "RSI перепроданность"
    min: 10
    max: 50
    step: 1
    initial: 30
    icon: mdi:chart-line
    mode: slider
  crypto_rsi_overbought:
    name: "RSI перекупленность"
    min: 50
    max: 90
    step: 1
    initial: 70
    icon: mdi:chart-line
    mode: slider

  # Fear & Greed пороги
  crypto_fg_extreme_fear:
    name: "F&G экстремальный страх"
    min: 0
    max: 50
    step: 1
    initial: 20
    icon: mdi:emoticon-cry
    mode: slider
  crypto_fg_extreme_greed:
    name: "F&G экстремальная жадность"
    min: 50
    max: 100
    step: 1
    initial: 80
    icon: mdi:emoticon-happy
    mode: slider

  # Whale Alert пороги
  crypto_whale_btc_threshold:
    name: "Порог кита BTC"
    min: 10
    max: 10000
    step: 10
    initial: 100
    unit_of_measurement: "BTC"
    icon: mdi:whale
  crypto_whale_eth_threshold:
    name: "Порог кита ETH"
    min: 100
    max: 100000
    step: 100
    initial: 1000
    unit_of_measurement: "ETH"
    icon: mdi:whale

  # Ценовые алерты
  crypto_btc_price_alert_low:
    name: "BTC алерт (низ)"
    min: 1000
    max: 500000
    step: 1000
    initial: 80000
    unit_of_measurement: "USDT"
    icon: mdi:arrow-down-circle
  crypto_btc_price_alert_high:
    name: "BTC алерт (верх)"
    min: 1000
    max: 500000
    step: 1000
    initial: 120000
    unit_of_measurement: "USDT"
    icon: mdi:arrow-up-circle
  crypto_eth_price_alert_low:
    name: "ETH алерт (низ)"
    min: 100
    max: 50000
    step: 100
    initial: 2500
    unit_of_measurement: "USDT"
    icon: mdi:arrow-down-circle
  crypto_eth_price_alert_high:
    name: "ETH алерт (верх)"
    min: 100
    max: 50000
    step: 100
    initial: 5000
    unit_of_measurement: "USDT"
    icon: mdi:arrow-up-circle

  # Конвертор валют
  converter_amount:
    name: "Сумма конвертации"
    min: 1
    max: 1000000
    step: 1
    initial: 100
    icon: mdi:calculator

  # Очистка данных
  crypto_cleanup_keep_days:
    name: "Хранить данные (дней)"
    min: 1
    max: 365
    step: 1
    initial: 30
    unit_of_measurement: "дн."
    icon: mdi:calendar-range
  crypto_cleanup_min_candles:
    name: "Мин. свечей для хранения"
    min: 100
    max: 10000
    step: 100
    initial: 1000
    icon: mdi:database

  # Риск-менеджмент
  crypto_max_drawdown_alert:
    name: "Макс. просадка для алерта"
    min: 5
    max: 50
    step: 1
    initial: 20
    unit_of_measurement: "%"
    icon: mdi:trending-down
    mode: slider
  crypto_position_size_max:
    name: "Макс. размер позиции"
    min: 1
    max: 100
    step: 1
    initial: 10
    unit_of_measurement: "%"
    icon: mdi:resize
    mode: slider

input_select:
  crypto_chart_coin:
    name: "Монета для графика"
    options:
      - BTC
      - ETH
      - SOL
      - TON
      - AR
    initial: BTC
    icon: mdi:bitcoin
  crypto_main_coin:
    name: "Основная монета"
    options:
      - BTC
      - ETH
      - SOL
      - TON
      - AR
    initial: BTC
    icon: mdi:star
  crypto_compare_coin:
    name: "Монета для сравнения"
    options:
      - Нет
      - BTC
      - ETH
      - SOL
      - TON
      - AR
    initial: Нет
    icon: mdi:compare
  crypto_currency:
    name: "Валюта отображения"
    options:
      - EUR
      - USD
      - RUB
      - USDT
    initial: EUR
    icon: mdi:currency-eur
  crypto_ta_coin:
    name: "Монета для TA"
    options:
      - BTC
      - ETH
      - SOL
      - TON
      - AR
    initial: BTC
    icon: mdi:chart-line
  crypto_ta_timeframe:
    name: "Таймфрейм TA"
    options:
      - 15m
      - 1h
      - 4h
      - 1d
      - 1w
    initial: 1h
    icon: mdi:clock-outline
  crypto_notification_language:
    name: "Язык уведомлений"
    options:
      - Russian
      - English
    initial: Russian
    icon: mdi:translate
  crypto_sensor_language:
    name: "Язык сенсоров"
    options:
      - Russian
      - English
    initial: Russian
    icon: mdi:translate-variant
  crypto_notification_mode:
    name: "Режим уведомлений"
    options:
      - all
      - smart
      - digest_only
      - critical_only
      - silent
    initial: smart
    icon: mdi:bell-cog
  converter_currency:
    name: "Исходная валюта"
    options:
      - EUR
      - USD
      - RUB
      - UAH
      - BTC
      - ETH
      - USDT
    initial: EUR
    icon: mdi:swap-horizontal

input_boolean:
  crypto_alerts_enabled:
    name: "Алерты включены"
    initial: true
    icon: mdi:bell
  crypto_dca_reminders_enabled:
    name: "DCA напоминания"
    initial: true
    icon: mdi:calendar-check
  crypto_whale_alerts_enabled:
    name: "Whale алерты"
    initial: true
    icon: mdi:whale
  crypto_morning_briefing_enabled:
    name: "Утренний брифинг"
    initial: true
    icon: mdi:weather-sunny
  crypto_evening_briefing_enabled:
    name: "Вечерний брифинг"
    initial: true
    icon: mdi:weather-night
  crypto_ai_analysis_enabled:
    name: "AI анализ"
    initial: false
    icon: mdi:robot
  crypto_risk_alerts_enabled:
    name: "Риск-алерты"
    initial: true
    icon: mdi:shield-alert
  crypto_technical_signals_enabled:
    name: "Технические сигналы"
    initial: true
    icon: mdi:chart-line
  crypto_cleanup_history_trigger:
    name: "Очистить историю"
    initial: false
    icon: mdi:delete-clock
  crypto_cleanup_database_trigger:
    name: "Очистить базу данных"
    initial: false
    icon: mdi:database-remove
```

После добавления перезагрузите Home Assistant: **Инструменты разработчика → Перезагрузить YAML → Input Numbers / Input Selects / Input Booleans**

## Конфигурация

### Основные параметры

```yaml
api_port: 9999              # Порт API
database_type: sqlite       # sqlite или postgres
symbols:                    # Торговые пары для отслеживания
  - BTC/USDT
  - ETH/USDT
log_level: info            # debug, info, warning, error
```

### Bybit Integration

Для синхронизации с Bybit добавьте API ключи:

```yaml
bybit_api_key: !secret bybit_api_key
bybit_api_secret: !secret bybit_api_secret
bybit_testnet: false
```

В файле `secrets.yaml`:
```yaml
bybit_api_key: "your_api_key"
bybit_api_secret: "your_api_secret"
```

**Важно:** В настройках Bybit API включите:
- Read-only access
- Wallet - Read
- Position - Read
- Order - Read

### Параметры анализа

```yaml
analysis_enabled: true          # Включить анализ
analysis_interval_hours: 4      # Интервал анализа (часы)
alert_on_strong_signals: true   # Уведомления о сигналах
alert_threshold_buy: 75         # Порог сигнала покупки (0-100)
alert_threshold_sell: 25        # Порог сигнала продажи (0-100)
```

### AI анализ (ChatGPT / Ollama)

Интеграция с AI для анализа рынка. Поддерживаются OpenAI (ChatGPT) и Ollama (локальный).

```yaml
ai_enabled: false               # Включить AI анализ
ai_provider: "ollama"           # ollama | openai
openai_api_key: ""              # API ключ OpenAI (если provider=openai)
openai_model: "gpt-4o-mini"     # Модель OpenAI
ollama_host: "http://192.168.1.2:11434"  # Хост Ollama
ollama_model: "llama3.2"        # Модель Ollama
ai_analysis_interval_hours: 24  # Интервал AI анализа (часы)
ai_language: "ru"               # Язык отчётов (ru | en)
```

**Приоритет провайдеров:** Если указан `openai_api_key`, то OpenAI будет основным провайдером, Ollama - фолбэк. Если OpenAI недоступен, система автоматически переключится на Ollama.

**AI возможности:**
- Ежедневная сводка рынка
- Анализ настроения (sentiment)
- Рекомендации по позициям
- Анализ конкретного символа

---

## Сенсоры

После запуска add-on автоматически создает сенсоры в Home Assistant. Все сенсоры имеют префикс `sensor.crypto_inspect_`.

### Цены и объемы

Все ценовые сенсоры используют **словарный формат**: ключ = код монеты, значение = данные.

| Сенсор | Описание | Пример значения |
|--------|----------|-----------------|
| `prices` | Текущие цены всех монет | `{"BTC": 95000, "ETH": 3200}` |
| `changes_24h` | Изменение за 24ч (%) | `{"BTC": 2.5, "ETH": -1.2}` |
| `volumes_24h` | Объемы торгов | `{"BTC": 50000000000}` |
| `highs_24h` | Максимумы 24ч | `{"BTC": 96000}` |
| `lows_24h` | Минимумы 24ч | `{"BTC": 94000}` |

### Bybit Account

| Сенсор | Описание |
|--------|----------|
| `bybit_balance` | Баланс торгового счёта (USDT) |
| `bybit_pnl_24h` | P&L за 24 часа (%) |
| `bybit_pnl_7d` | P&L за 7 дней (%) |
| `bybit_positions` | Открытые позиции |
| `bybit_unrealized_pnl` | Нереализованный P&L (USDT) |
| `bybit_earn_balance` | Баланс Bybit Earn |
| `bybit_total_portfolio` | Общий портфель Bybit |

### Ленивый Инвестор

Система анализа для долгосрочных инвесторов.

| Сенсор | Описание |
|--------|----------|
| `do_nothing_ok` | Можно ли ничего не делать? (Да/Нет) |
| `investor_phase` | Фаза рынка (Накопление/Рост/Эйфория/Коррекция/Капитуляция) |
| `calm_indicator` | Индикатор спокойствия (0-100) |
| `red_flags` | Количество красных флагов |
| `market_tension` | Напряжённость рынка |
| `price_context` | Контекст цены (относительно ATH/ATL) |
| `dca_signal` | Сигнал DCA (Покупать/Ждать/Не покупать) |
| `dca_result` | Рекомендуемая сумма DCA (€) |
| `weekly_insight` | Недельный обзор |

### Рыночные индикаторы

| Сенсор | Описание |
|--------|----------|
| `fear_greed` | Индекс страха и жадности (0-100) |
| `btc_dominance` | Доминация Bitcoin (%) |
| `market_pulse` | Пульс рынка (Бычий/Медвежий/Нейтрально) |
| `altseason_index` | Индекс альтсезона (0-100) |
| `altseason_status` | Статус (Биткоин сезон/Альтсезон/Нейтрально) |
| `derivatives` | Данные по деривативам |

### DCA Calculator

Расчет уровней для усреднения позиции.

| Сенсор | Описание |
|--------|----------|
| `dca_next_level` | Следующий уровень для покупки (USDT) |
| `dca_zone` | Зона (покупка/накопление/ожидание) |
| `dca_risk_score` | Оценка риска (0-100) |

### Фиксация прибыли (Take Profit)

Рекомендации по фиксации прибыли.

| Сенсор | Описание |
|--------|----------|
| `tp_levels` | Уровни фиксации (dict: `{"BTC": [95000, 100000]}`) |
| `profit_action` | Рекомендация (держать/фиксировать) |
| `greed_level` | Уровень жадности рынка (0-100) |

### Волатильность и корреляции

| Сенсор | Описание |
|--------|----------|
| `volatility_30d` | 30-дневная волатильность (dict: `{"BTC": 45}`) |
| `volatility_percentile` | Перцентиль волатильности |
| `volatility_status` | Статус (низкая/средняя/высокая) |
| `btc_eth_correlation` | Корреляция BTC/ETH |
| `btc_sp500_correlation` | Корреляция BTC/S&P500 |
| `correlation_status` | Статус корреляций |

### Макро-события

| Сенсор | Описание |
|--------|----------|
| `next_macro_event` | Следующее макрособытие |
| `days_to_fomc` | Дней до заседания FOMC |
| `macro_risk_week` | Макрориск недели (низкий/средний/высокий) |

### Разблокировка токенов

| Сенсор | Описание |
|--------|----------|
| `unlocks_next_7d` | Разблокировки за 7 дней |
| `unlock_next_event` | Ближайшая разблокировка |
| `unlock_risk_level` | Риск анлоков |

### On-Chain данные и киты

| Сенсор | Описание |
|--------|----------|
| `whale_alerts_24h` | Алерты китов за 24ч |
| `whale_net_flow` | Нетто-поток китов |
| `whale_last_alert` | Последний алерт |
| `exchange_netflows` | Потоки на биржи (dict: `{"BTC": -500}`) |
| `exchange_flow_signal` | Сигнал потоков |

### ETH Gas

| Сенсор | Описание |
|--------|----------|
| `eth_gas_slow` | Медленная скорость (Gwei) |
| `eth_gas_standard` | Стандартная скорость (Gwei) |
| `eth_gas_fast` | Быстрая скорость (Gwei) |
| `eth_gas_status` | Статус газа (низкий/средний/высокий) |

### Арбитраж

| Сенсор | Описание |
|--------|----------|
| `arb_spreads` | Спреды арбитража |
| `funding_arb_best` | Лучший фандинг-арбитраж |
| `arb_opportunity` | Возможность арбитража |

### AI Анализ

| Сенсор | Описание |
|--------|----------|
| `ai_daily_summary` | Ежедневная AI-сводка рынка |
| `ai_market_sentiment` | AI оценка настроения |
| `ai_recommendation` | AI рекомендация (Buy/Hold/Sell) |
| `ai_last_analysis` | Время последнего AI-анализа |
| `ai_provider` | Используемый AI провайдер |
| `ai_trends` | AI-предсказанные тренды для всех валют (dict) |
| `ai_confidences` | Уровни уверенности AI-предсказаний (dict) |
| `ai_price_forecasts_24h` | AI-прогнозы цен через 24 часа (dict) |

### Адаптивные уведомления

| Сенсор | Описание |
|--------|----------|
| `adaptive_notifications_status` | Статус системы адаптивных уведомлений |
| `adaptive_volatilities` | Текущие уровни волатильности для всех валют (dict) |
| `adaptive_notification_count_24h` | Количество отправленных уведомлений за 24 часа |
| `adaptive_adaptation_factors` | Текущие факторы адаптации для всех валют (dict) |

### Умная корреляция

| Сенсор | Описание |
|--------|----------|
| `correlation_analysis_status` | Статус анализа умных корреляций |
| `correlation_significant_count` | Количество статистически значимых корреляций |
| `correlation_strongest_positive` | Самая сильная положительная корреляция |
| `correlation_strongest_negative` | Самая сильная отрицательная корреляция |
| `correlation_dominant_patterns` | Количество выявленных доминирующих паттернов |

### Экономический календарь

| Сенсор | Описание |
|--------|----------|
| `economic_calendar_status` | Статус отслеживания экономических событий и новостей |
| `economic_upcoming_events_24h` | Количество важных экономических событий в ближайшие 24 часа |
| `economic_important_events` | Количество отслеживаемых важных событий |
| `economic_breaking_news` | Количество срочных новостей о криптовалютах |
| `economic_sentiment_score` | Общие рыночные настроения из новостей и событий |

### Технический анализ (TA)

Все индикаторы используют **словарный формат**: ключ = монета, значение = данные.

| Сенсор | Описание | Пример |
|--------|----------|--------|
| `ta_rsi` | RSI(14) | `{"BTC": 65, "ETH": 45}` |
| `ta_macd_signal` | MACD сигналы | `{"BTC": "bullish"}` |
| `ta_bb_position` | Позиция Bollinger Bands | `{"BTC": 0.7}` |
| `ta_trend` | Направление тренда | `{"BTC": "uptrend"}` |
| `ta_support` | Уровни поддержки | `{"BTC": 90000}` |
| `ta_resistance` | Уровни сопротивления | `{"BTC": 100000}` |
| `ta_trend_mtf` | MTF тренды | - |
| `ta_confluence` | Конфлюенс скор (0-100) | - |
| `ta_signal` | TA сигнал (buy/sell/hold) | - |

### Риск-менеджмент

| Сенсор | Описание |
|--------|----------|
| `portfolio_sharpe` | Коэффициент Шарпа |
| `portfolio_sortino` | Коэффициент Сортино |
| `portfolio_max_drawdown` | Максимальная просадка (%) |
| `portfolio_current_drawdown` | Текущая просадка (%) |
| `portfolio_var_95` | VaR 95% |
| `risk_status` | Статус риска (низкий/средний/высокий/критический) |

### DCA Бэктест

| Сенсор | Описание |
|--------|----------|
| `backtest_dca_roi` | ROI DCA стратегии (%) |
| `backtest_smart_dca_roi` | ROI умного DCA (%) |
| `backtest_lump_sum_roi` | ROI единовременной покупки (%) |
| `backtest_best_strategy` | Лучшая стратегия |

### Ликвидации

| Сенсор | Описание |
|--------|----------|
| `liq_levels` | Уровни ликвидаций |
| `liq_risk_level` | Риск ликвидаций |

### Традиционные финансы

Данные по классическим активам (металлы, индексы, форекс, сырьё).

| Сенсор | Описание |
|--------|----------|
| `gold_price` | Золото (USD) |
| `silver_price` | Серебро (USD) |
| `platinum_price` | Платина (USD) |
| `sp500_price` | Индекс S&P 500 |
| `nasdaq_price` | Индекс NASDAQ |
| `dji_price` | Индекс Dow Jones |
| `dax_price` | Индекс DAX (EUR) |
| `eur_usd` | Курс EUR/USD |
| `gbp_usd` | Курс GBP/USD |
| `dxy_index` | Индекс доллара (DXY) |
| `oil_brent` | Нефть Brent (USD) |
| `oil_wti` | Нефть WTI (USD) |
| `natural_gas` | Природный газ (USD) |

### Диагностические сенсоры

| Сенсор | Описание |
|--------|----------|
| `sync_status` | Статус синхронизации данных |
| `last_sync` | Время последней синхронизации |
| `candles_count` | Общее количество свечей в БД |
| `database_size` | Размер файла базы данных (MB) |

### UX/Уведомления

| Сенсор | Описание |
|--------|----------|
| `pending_alerts_count` | Количество необработанных алертов |
| `pending_alerts_critical` | Количество критических алертов |
| `daily_digest_ready` | Готов ли дневной дайджест |
| `notification_mode` | Текущий режим уведомлений (all/important/quiet) |

### Брифинги

| Сенсор | Описание |
|--------|----------|
| `morning_briefing` | Утренняя сводка по рынку |
| `evening_briefing` | Вечерняя сводка по рынку |
| `briefing_last_sent` | Время последнего брифинга |

### Отслеживание целей

| Сенсор | Описание |
|--------|----------|
| `goal_target` | Целевая сумма портфеля (USDT) |
| `goal_progress` | Процент достижения цели (%) |
| `goal_remaining` | Сколько осталось до цели (USDT) |
| `goal_days_estimate` | Оценка дней до достижения цели |
| `goal_status` | Статус цели (in progress/reached/postponed) |

---

## Примеры Lovelace

### Карточка Bybit Account

```yaml
type: entities
title: 💰 Bybit Account
entities:
  - entity: sensor.crypto_inspect_bybit_balance
    name: Баланс
  - entity: sensor.crypto_inspect_bybit_pnl_24h
    name: P&L 24ч
  - entity: sensor.crypto_inspect_bybit_pnl_7d
    name: P&L 7д
  - entity: sensor.crypto_inspect_bybit_positions
    name: Позиции
```

### Карточка Fear & Greed с цветом

```yaml
type: custom:mushroom-template-card
primary: Fear & Greed Index
secondary: "{{ states('sensor.crypto_inspect_fear_greed') }}"
icon: mdi:emoticon-neutral
icon_color: |
  {% set val = state_attr('sensor.crypto_inspect_fear_greed', 'value') | int(50) %}
  {% if val <= 25 %}red
  {% elif val <= 45 %}orange
  {% elif val <= 55 %}yellow
  {% elif val <= 75 %}green
  {% else %}light-green{% endif %}
```

### Карточка Ленивого инвестора

```yaml
type: vertical-stack
cards:
  - type: custom:mushroom-template-card
    primary: "{{ states('sensor.crypto_inspect_do_nothing_ok') }}"
    secondary: "{{ state_attr('sensor.crypto_inspect_do_nothing_ok', 'reason') }}"
    icon: mdi:meditation
    icon_color: |
      {% if state_attr('sensor.crypto_inspect_do_nothing_ok', 'value') %}green{% else %}orange{% endif %}

  - type: entities
    entities:
      - entity: sensor.crypto_inspect_investor_phase
      - entity: sensor.crypto_inspect_calm_indicator
      - entity: sensor.crypto_inspect_red_flags
      - entity: sensor.crypto_inspect_dca_signal
```

### DCA Zones

```yaml
type: custom:mushroom-template-card
primary: DCA Zone
secondary: |
  {{ states('sensor.crypto_inspect_dca_signal') }}
  Next: {{ states('sensor.crypto_inspect_dca_result') }}
icon: mdi:target
icon_color: |
  {% set signal = states('sensor.crypto_inspect_dca_signal') %}
  {% if 'buy' in signal.lower() %}green
  {% elif 'wait' in signal.lower() %}yellow
  {% else %}red{% endif %}
```

### Take Profit

```yaml
type: glance
title: 🎯 Take Profit
entities:
  - entity: sensor.crypto_inspect_tp_levels
    name: Levels
    attribute: btc_tp_level_1
  - entity: sensor.crypto_inspect_tp_levels
    name: TP2
    attribute: btc_tp_level_2
  - entity: sensor.crypto_inspect_profit_action
    name: Action
  - entity: sensor.crypto_inspect_greed_level
    name: Greed
```

### Macro Events

```yaml
type: entities
title: 📅 Upcoming Events
entities:
  - entity: sensor.crypto_inspect_next_macro_event
    name: Next Event
  - entity: sensor.crypto_inspect_days_to_fomc
    name: Days to FOMC
  - entity: sensor.crypto_inspect_macro_risk_week
    name: Week Risk
  - entity: sensor.crypto_inspect_unlock_next_event
    name: Next Unlock
```

### Gas Tracker

```yaml
type: glance
title: ⛽ ETH Gas
entities:
  - entity: sensor.crypto_inspect_eth_gas_slow
    name: Slow
  - entity: sensor.crypto_inspect_eth_gas_standard
    name: Standard
  - entity: sensor.crypto_inspect_eth_gas_fast
    name: Fast
```

### Whale Activity

```yaml
type: horizontal-stack
cards:
  - type: custom:mushroom-template-card
    primary: 🐋 Whales 24h
    secondary: "{{ states('sensor.crypto_inspect_whale_alerts_24h') }}"
    icon: mdi:fish

  - type: custom:mushroom-template-card
    primary: Exchange Flow
    secondary: "{{ states('sensor.crypto_inspect_exchange_flow_signal') }}"
    icon: mdi:bank-transfer
```

### Arbitrage Scanner

```yaml
type: entities
title: ⚡ Arbitrage
entities:
  - entity: sensor.crypto_inspect_btc_arb_spread
    name: BTC Spread %
  - entity: sensor.crypto_inspect_funding_arb_best
    name: Best Funding
  - entity: sensor.crypto_inspect_arb_opportunity
    name: Opportunity
```

### Традиционные финансы

```yaml
type: glance
title: "🥇 Металлы"
entities:
  - entity: sensor.crypto_inspect_gold_price
    name: "Золото"
    icon: mdi:gold
  - entity: sensor.crypto_inspect_silver_price
    name: "Серебро"
  - entity: sensor.crypto_inspect_platinum_price
    name: "Платина"
```

```yaml
type: entities
title: "📈 Индексы"
entities:
  - entity: sensor.crypto_inspect_sp500_price
    name: "S&P 500"
  - entity: sensor.crypto_inspect_nasdaq_price
    name: "NASDAQ"
  - entity: sensor.crypto_inspect_dji_price
    name: "Dow Jones"
  - entity: sensor.crypto_inspect_dax_price
    name: "DAX"
```

```yaml
type: glance
title: "💱 Форекс"
entities:
  - entity: sensor.crypto_inspect_eur_usd
    name: "EUR/USD"
  - entity: sensor.crypto_inspect_gbp_usd
    name: "GBP/USD"
  - entity: sensor.crypto_inspect_dxy_index
    name: "DXY"
```

```yaml
type: entities
title: "🛢️ Сырьё"
entities:
  - entity: sensor.crypto_inspect_oil_brent
    name: "Нефть Brent"
    icon: mdi:barrel
  - entity: sensor.crypto_inspect_oil_wti
    name: "Нефть WTI"
  - entity: sensor.crypto_inspect_natural_gas
    name: "Газ"
    icon: mdi:fire
```

---

## Автоматизации / Automations

Полный набор автоматизаций с поддержкой русского и английского языков.

---

### 🌐 Настройка языка (configuration.yaml)

```yaml
input_select:
  crypto_notification_language:
    name: "Crypto Notification Language"
    options:
      - Russian
      - English
    initial: Russian
    icon: mdi:translate
```

---

### 📊 Ценовые алерты

#### BTC достиг целевой цены

```yaml
automation:
  - alias: "BTC Price Target Alert"
    trigger:
      - platform: template
        value_template: "{{ states('sensor.crypto_inspect_prices') | from_json | default({}) | selectattr('key', 'eq', 'BTC/USDT') | map(attribute='value') | first | float(0) > 110000 }}"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "🚀 BTC Price Alert"
          message: >-
            {% if is_state('input_select.crypto_notification_language', 'Russian') %}
            Bitcoin превысил $110,000!
            {% else %}
            Bitcoin exceeded $110,000!
            {% endif %}
```

#### Значительное падение цены (>5% за 24ч)

```yaml
automation:
  - alias: "Major Price Drop Alert"
    trigger:
      - platform: template
        value_template: "{{ states('sensor.crypto_inspect_changes_24h') | from_json | default({}) | selectattr('key', 'eq', 'BTC/USDT') | map(attribute='value') | first | float(0) < -5 }}"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "📉 Price Drop Alert"
          message: >-
            {% if is_state('input_select.crypto_notification_language', 'Russian') %}
            BTC упал более чем на 5% за 24 часа. Возможность для DCA?
            {% else %}
            BTC dropped more than 5% in 24 hours. DCA opportunity?
            {% endif %}
```

---

### 😱 Fear & Greed Index

#### Экстремальный страх (зона покупки)

```yaml
automation:
  - alias: "Extreme Fear Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.crypto_inspect_fear_greed
        below: 20
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "😱 Extreme Fear"
          message: >-
            {% set fg = states('sensor.crypto_inspect_fear_greed') %}
            {% if is_state('input_select.crypto_notification_language', 'Russian') %}
            Fear & Greed Index: {{ fg }}. Исторически хорошее время для покупки!
            {% else %}
            Fear & Greed Index: {{ fg }}. Historically a good time to buy!
            {% endif %}
```

#### Экстремальная жадность (зона осторожности)

```yaml
automation:
  - alias: "Extreme Greed Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.crypto_inspect_fear_greed
        above: 80
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "🤑 Extreme Greed"
          message: >-
            {% set fg = states('sensor.crypto_inspect_fear_greed') %}
            {% if is_state('input_select.crypto_notification_language', 'Russian') %}
            Fear & Greed Index: {{ fg }}. Рынок перегрет, рассмотрите фиксацию прибыли.
            {% else %}
            Fear & Greed Index: {{ fg }}. Market overheated, consider taking profits.
            {% endif %}
```

---

### 💰 DCA (усреднение позиции)

#### Вход в зону покупки

```yaml
automation:
  - alias: "DCA Buy Zone Alert"
    trigger:
      - platform: state
        entity_id: sensor.crypto_inspect_dca_zone
        to: "Buy Zone"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "💰 DCA Opportunity"
          message: >-
            {% set level = states('sensor.crypto_inspect_dca_next_level') %}
            {% if is_state('input_select.crypto_notification_language', 'Russian') %}
            Рынок в зоне покупки! Уровень: ${{ level }}
            {% else %}
            Market in buy zone! Level: ${{ level }}
            {% endif %}
```

#### Еженедельное напоминание о DCA

```yaml
automation:
  - alias: "Weekly DCA Reminder"
    trigger:
      - platform: time
        at: "09:00:00"
    condition:
      - condition: time
        weekday:
          - mon
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "📅 Weekly DCA"
          message: >-
            {% set zone = states('sensor.crypto_inspect_dca_zone') %}
            {% set signal = states('sensor.crypto_inspect_dca_signal') %}
            {% set amount = states('sensor.crypto_inspect_dca_result') %}
            {% if is_state('input_select.crypto_notification_language', 'Russian') %}
            Понедельник - день DCA!
            Зона: {{ zone }}
            Рекомендация: {{ signal }}
            Сумма: €{{ amount }}
            {% else %}
            Monday - DCA day!
            Zone: {{ zone }}
            Recommendation: {{ signal }}
            Amount: €{{ amount }}
            {% endif %}
```

#### Сигнал "Ленивого инвестора" изменился

```yaml
automation:
  - alias: "Lazy Investor Signal Change"
    trigger:
      - platform: state
        entity_id: sensor.crypto_inspect_do_nothing_ok
    condition:
      - condition: template
        value_template: "{{ trigger.from_state.state != trigger.to_state.state }}"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "🧘 Investor Status"
          message: >-
            {% set status = states('sensor.crypto_inspect_do_nothing_ok') %}
            {% set reason = state_attr('sensor.crypto_inspect_do_nothing_ok', 'reason') %}
            {% if is_state('input_select.crypto_notification_language', 'Russian') %}
            Статус изменился: {{ status }}
            Причина: {{ reason }}
            {% else %}
            Status changed: {{ status }}
            Reason: {{ reason }}
            {% endif %}
```

---

### 🎯 Take Profit

#### Достигнут уровень TP1

```yaml
automation:
  - alias: "Take Profit Level 1 Alert"
    trigger:
      - platform: state
        entity_id: sensor.crypto_inspect_profit_action
        to: "Scale Out"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "🎯 Take Profit Signal"
          message: >-
            {% set tp1 = states('sensor.crypto_inspect_btc_tp_level_1') %}
            {% set tp2 = states('sensor.crypto_inspect_btc_tp_level_2') %}
            {% if is_state('input_select.crypto_notification_language', 'Russian') %}
            Рекомендация: частичная фиксация прибыли!
            TP1: ${{ tp1 }} | TP2: ${{ tp2 }}
            {% else %}
            Recommendation: partial profit taking!
            TP1: ${{ tp1 }} | TP2: ${{ tp2 }}
            {% endif %}
```

#### Полная фиксация прибыли

```yaml
automation:
  - alias: "Full Take Profit Alert"
    trigger:
      - platform: state
        entity_id: sensor.crypto_inspect_profit_action
        to: "Take Profit"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "💰 Full TP Signal"
          message: >-
            {% if is_state('input_select.crypto_notification_language', 'Russian') %}
            Рынок перегрет! Рассмотрите полную фиксацию прибыли.
            {% else %}
            Market overheated! Consider full profit taking.
            {% endif %}
          data:
            priority: high
            ttl: 0
```

---

### 📈 Волатильность

#### Экстремальная волатильность

```yaml
automation:
  - alias: "Extreme Volatility Alert"
    trigger:
      - platform: state
        entity_id: sensor.crypto_inspect_volatility_status
        to: "Extreme"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "⚠️ Extreme Volatility"
          message: >-
            {% set vol = states('sensor.crypto_inspect_btc_volatility_30d') %}
            {% if is_state('input_select.crypto_notification_language', 'Russian') %}
            Волатильность {{ vol }}%! Будьте осторожны с позициями.
            {% else %}
            Volatility {{ vol }}%! Be careful with your positions.
            {% endif %}
```

#### Низкая волатильность (затишье перед бурей)

```yaml
automation:
  - alias: "Low Volatility Alert"
    trigger:
      - platform: state
        entity_id: sensor.crypto_inspect_volatility_status
        to: "Low"
        for:
          hours: 24
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "🌊 Calm Before Storm?"
          message: >-
            {% if is_state('input_select.crypto_notification_language', 'Russian') %}
            Волатильность аномально низкая уже 24ч. Возможен сильный импульс.
            {% else %}
            Volatility abnormally low for 24h. Strong move possible.
            {% endif %}
```

---

### 🐋 On-Chain данные

#### Whale Alert

```yaml
automation:
  - alias: "Whale Movement Alert"
    trigger:
      - platform: state
        entity_id: sensor.crypto_inspect_whale_last_alert
    condition:
      - condition: template
        value_template: "{{ trigger.to_state.state != 'unknown' and trigger.to_state.state != trigger.from_state.state }}"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "🐋 Whale Alert"
          message: >-
            {% set alert = states('sensor.crypto_inspect_whale_last_alert') %}
            {% if is_state('input_select.crypto_notification_language', 'Russian') %}
            Движение кита: {{ alert }}
            {% else %}
            Whale movement: {{ alert }}
            {% endif %}
```

#### Bullish Exchange Flow (отток с бирж)

```yaml
automation:
  - alias: "Bullish Exchange Flow"
    trigger:
      - platform: state
        entity_id: sensor.crypto_inspect_exchange_flow_signal
        to: "Bullish"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "🟢 Bullish Exchange Flow"
          message: >-
            {% set netflow = states('sensor.crypto_inspect_btc_exchange_netflow') %}
            {% if is_state('input_select.crypto_notification_language', 'Russian') %}
            BTC выводят с бирж. Netflow: {{ netflow }} BTC
            {% else %}
            BTC being withdrawn from exchanges. Netflow: {{ netflow }} BTC
            {% endif %}
```

#### Bearish Exchange Flow (приток на биржи)

```yaml
automation:
  - alias: "Bearish Exchange Flow"
    trigger:
      - platform: state
        entity_id: sensor.crypto_inspect_exchange_flow_signal
        to: "Bearish"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "🔴 Bearish Exchange Flow"
          message: >-
            {% set netflow = states('sensor.crypto_inspect_btc_exchange_netflow') %}
            {% if is_state('input_select.crypto_notification_language', 'Russian') %}
            BTC заводят на биржи - возможна распродажа. Netflow: {{ netflow }} BTC
            {% else %}
            BTC flowing to exchanges - possible selloff. Netflow: {{ netflow }} BTC
            {% endif %}
```

---

### ⛽ ETH Gas Tracker

#### Низкий газ (оптимальное время для транзакций)

```yaml
automation:
  - alias: "Low Gas Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.crypto_inspect_eth_gas_standard
        below: 20
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "⛽ Low Gas!"
          message: >-
            {% set gas = states('sensor.crypto_inspect_eth_gas_standard') %}
            {% if is_state('input_select.crypto_notification_language', 'Russian') %}
            ETH Gas всего {{ gas }} Gwei. Отличное время для транзакций!
            {% else %}
            ETH Gas only {{ gas }} Gwei. Great time for transactions!
            {% endif %}
```

#### Высокий газ (предупреждение)

```yaml
automation:
  - alias: "High Gas Warning"
    trigger:
      - platform: numeric_state
        entity_id: sensor.crypto_inspect_eth_gas_standard
        above: 100
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "⛽ High Gas Warning"
          message: >-
            {% set gas = states('sensor.crypto_inspect_eth_gas_standard') %}
            {% if is_state('input_select.crypto_notification_language', 'Russian') %}
            ETH Gas {{ gas }} Gwei. Отложите некритичные транзакции.
            {% else %}
            ETH Gas {{ gas }} Gwei. Delay non-critical transactions.
            {% endif %}
```

---

### 📅 Макро-события

#### Напоминание о FOMC

```yaml
automation:
  - alias: "FOMC Reminder"
    trigger:
      - platform: numeric_state
        entity_id: sensor.crypto_inspect_days_to_fomc
        below: 2
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "📅 FOMC Alert"
          message: >-
            {% set days = states('sensor.crypto_inspect_days_to_fomc') %}
            {% if is_state('input_select.crypto_notification_language', 'Russian') %}
            FOMC через {{ days }} дня! Ожидайте повышенную волатильность.
            {% else %}
            FOMC in {{ days }} days! Expect increased volatility.
            {% endif %}
```

#### Высокий риск недели

```yaml
automation:
  - alias: "High Risk Week Alert"
    trigger:
      - platform: state
        entity_id: sensor.crypto_inspect_macro_risk_week
        to: "High"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "⚠️ High Risk Week"
          message: >-
            {% set event = states('sensor.crypto_inspect_next_macro_event') %}
            {% if is_state('input_select.crypto_notification_language', 'Russian') %}
            На этой неделе много важных макро-событий. Следующее: {{ event }}
            {% else %}
            Many important macro events this week. Next: {{ event }}
            {% endif %}
```

#### Token Unlock предупреждение

```yaml
automation:
  - alias: "Token Unlock Warning"
    trigger:
      - platform: numeric_state
        entity_id: sensor.crypto_inspect_unlocks_next_7d
        above: 5
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "🔓 Token Unlocks"
          message: >-
            {% set count = states('sensor.crypto_inspect_unlocks_next_7d') %}
            {% set next = states('sensor.crypto_inspect_unlock_next_event') %}
            {% if is_state('input_select.crypto_notification_language', 'Russian') %}
            {{ count }} анлоков за 7 дней! Следующий: {{ next }}
            {% else %}
            {{ count }} unlocks in 7 days! Next: {{ next }}
            {% endif %}
```

---

### 🌊 Altseason

#### Начало альтсезона

```yaml
automation:
  - alias: "Altseason Started"
    trigger:
      - platform: state
        entity_id: sensor.crypto_inspect_altseason_status
        to: "Altseason"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "🌊 Altseason!"
          message: >-
            {% set index = states('sensor.crypto_inspect_altseason_index') %}
            {% if is_state('input_select.crypto_notification_language', 'Russian') %}
            Альтсезон начался! Index: {{ index }}. Время для альткоинов.
            {% else %}
            Altseason started! Index: {{ index }}. Time for altcoins.
            {% endif %}
```

#### Bitcoin Season (время для BTC)

```yaml
automation:
  - alias: "Bitcoin Season"
    trigger:
      - platform: state
        entity_id: sensor.crypto_inspect_altseason_status
        to: "Bitcoin Season"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "₿ Bitcoin Season"
          message: >-
            {% set dom = states('sensor.crypto_inspect_btc_dominance') %}
            {% if is_state('input_select.crypto_notification_language', 'Russian') %}
            Деньги перетекают в Bitcoin. BTC Dominance: {{ dom }}%
            {% else %}
            Money flowing to Bitcoin. BTC Dominance: {{ dom }}%
            {% endif %}
```

---

### ⚡ Ликвидации

#### Высокий риск ликвидаций

```yaml
automation:
  - alias: "Liquidation Risk Warning"
    trigger:
      - platform: state
        entity_id: sensor.crypto_inspect_liq_risk_level
        to: "High"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "⚡ Liquidation Risk"
          message: >-
            {% set long_liq = states('sensor.crypto_inspect_btc_liq_long_nearest') %}
            {% set short_liq = states('sensor.crypto_inspect_btc_liq_short_nearest') %}
            {% if is_state('input_select.crypto_notification_language', 'Russian') %}
            Высокий риск ликвидаций!
            Long: ${{ long_liq }} | Short: ${{ short_liq }}
            {% else %}
            High liquidation risk!
            Long: ${{ long_liq }} | Short: ${{ short_liq }}
            {% endif %}
```

---

### 💱 Funding Rate

#### Экстремальный положительный фандинг

```yaml
automation:
  - alias: "High Positive Funding Alert"
    trigger:
      - platform: template
        value_template: "{{ state_attr('sensor.crypto_inspect_funding_rates', 'btc_rate') | float(0) > 0.05 }}"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "💱 High Funding Rate"
          message: >-
            {% if is_state('input_select.crypto_notification_language', 'Russian') %}
            BTC funding rate очень высокий! Лонги перегреты, возможна коррекция.
            {% else %}
            BTC funding rate very high! Longs overheated, correction possible.
            {% endif %}
```

#### Отрицательный фандинг (возможность для лонга)

```yaml
automation:
  - alias: "Negative Funding Alert"
    trigger:
      - platform: template
        value_template: "{{ state_attr('sensor.crypto_inspect_funding_rates', 'btc_rate') | float(0) < -0.01 }}"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "💱 Negative Funding"
          message: >-
            {% if is_state('input_select.crypto_notification_language', 'Russian') %}
            BTC funding отрицательный! Шорты платят лонгам - возможен рост.
            {% else %}
            BTC funding negative! Shorts paying longs - growth possible.
            {% endif %}
```

---

### ⚖️ Арбитраж

#### Арбитражная возможность

```yaml
automation:
  - alias: "Arbitrage Opportunity Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.crypto_inspect_btc_arb_spread
        above: 0.5
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "⚖️ Arbitrage Opportunity"
          message: >-
            {% set spread = states('sensor.crypto_inspect_btc_arb_spread') %}
            {% set opp = states('sensor.crypto_inspect_arb_opportunity') %}
            {% if is_state('input_select.crypto_notification_language', 'Russian') %}
            BTC spread {{ spread }}%! Возможность: {{ opp }}
            {% else %}
            BTC spread {{ spread }}%! Opportunity: {{ opp }}
            {% endif %}
```

---

### 🔗 Корреляции

#### BTC декоррелировался от S&P500

```yaml
automation:
  - alias: "BTC SP500 Decorrelation"
    trigger:
      - platform: numeric_state
        entity_id: sensor.crypto_inspect_btc_sp500_correlation
        below: 0.3
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "🔗 Decorrelation Alert"
          message: >-
            {% set corr = states('sensor.crypto_inspect_btc_sp500_correlation') %}
            {% if is_state('input_select.crypto_notification_language', 'Russian') %}
            BTC декоррелировался от S&P500 ({{ corr }}). Крипта движется независимо!
            {% else %}
            BTC decorrelated from S&P500 ({{ corr }}). Crypto moving independently!
            {% endif %}
```

---

### 💼 Bybit Portfolio

#### Значительная прибыль за 24ч

```yaml
automation:
  - alias: "Bybit Profit Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.crypto_inspect_bybit_pnl_24h
        above: 5
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "💰 Bybit Profit!"
          message: >-
            {% set pnl = states('sensor.crypto_inspect_bybit_pnl_24h') %}
            {% set balance = states('sensor.crypto_inspect_bybit_balance') %}
            {% if is_state('input_select.crypto_notification_language', 'Russian') %}
            P&L за 24ч: +{{ pnl }}%! Баланс: ${{ balance }}
            {% else %}
            P&L 24h: +{{ pnl }}%! Balance: ${{ balance }}
            {% endif %}
```

#### Значительный убыток за 24ч

```yaml
automation:
  - alias: "Bybit Loss Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.crypto_inspect_bybit_pnl_24h
        below: -5
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "📉 Bybit Loss Alert"
          message: >-
            {% set pnl = states('sensor.crypto_inspect_bybit_pnl_24h') %}
            {% if is_state('input_select.crypto_notification_language', 'Russian') %}
            P&L за 24ч: {{ pnl }}%! Проверьте позиции.
            {% else %}
            P&L 24h: {{ pnl }}%! Check your positions.
            {% endif %}
          data:
            priority: high
```

#### Баланс достиг цели

```yaml
automation:
  - alias: "Bybit Balance Target"
    trigger:
      - platform: numeric_state
        entity_id: sensor.crypto_inspect_bybit_balance
        above: 10000
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "🎉 Balance Target!"
          message: >-
            {% set balance = states('sensor.crypto_inspect_bybit_balance') | int %}
            {% if is_state('input_select.crypto_notification_language', 'Russian') %}
            Баланс Bybit достиг ${{ balance }}!
            {% else %}
            Bybit balance reached ${{ balance }}!
            {% endif %}
```

---

### 🚩 Красные флаги

#### Множество красных флагов

```yaml
automation:
  - alias: "Multiple Red Flags Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.crypto_inspect_red_flags
        above: 3
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "🚩 Multiple Red Flags!"
          message: >-
            {% set count = states('sensor.crypto_inspect_red_flags') %}
            {% set flags = state_attr('sensor.crypto_inspect_red_flags', 'flags_list') %}
            {% if is_state('input_select.crypto_notification_language', 'Russian') %}
            {{ count }} красных флагов!
            {{ flags }}
            {% else %}
            {{ count }} red flags detected!
            {{ flags }}
            {% endif %}
          data:
            priority: high
```

---

### 🥇 Традиционные финансы

#### Золото достигло рекорда

```yaml
automation:
  - alias: "Gold Record High"
    trigger:
      - platform: numeric_state
        entity_id: sensor.crypto_inspect_gold_price
        above: 2500
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "🥇 Gold ATH!"
          message: >-
            {% set price = states('sensor.crypto_inspect_gold_price') %}
            {% if is_state('input_select.crypto_notification_language', 'Russian') %}
            Золото выше ${{ price }}!
            {% else %}
            Gold above ${{ price }}!
            {% endif %}
```

#### DXY (доллар) укрепляется

```yaml
automation:
  - alias: "DXY Strength Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.crypto_inspect_dxy_index
        above: 105
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "💵 Strong Dollar"
          message: >-
            {% set dxy = states('sensor.crypto_inspect_dxy_index') %}
            {% if is_state('input_select.crypto_notification_language', 'Russian') %}
            DXY: {{ dxy }}. Сильный доллар - давление на рисковые активы.
            {% else %}
            DXY: {{ dxy }}. Strong dollar - pressure on risk assets.
            {% endif %}
```

#### S&P500 падение

```yaml
automation:
  - alias: "SP500 Drop Alert"
    trigger:
      - platform: template
        value_template: "{{ state_attr('sensor.crypto_inspect_sp500_price', 'change_percent') | float(0) < -2 }}"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "📉 S&P500 Drop"
          message: >-
            {% if is_state('input_select.crypto_notification_language', 'Russian') %}
            S&P500 падает более чем на 2%! Возможно давление на крипту.
            {% else %}
            S&P500 dropping more than 2%! Possible pressure on crypto.
            {% endif %}
```

---

### 📱 Утренний отчёт

```yaml
automation:
  - alias: "Morning Crypto Report"
    trigger:
      - platform: time
        at: "08:00:00"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "☀️ Crypto Morning"
          message: >-
            {% set fg = states('sensor.crypto_inspect_fear_greed') %}
            {% set vol = states('sensor.crypto_inspect_volatility_status') %}
            {% set dca = states('sensor.crypto_inspect_dca_zone') %}
            {% set balance = states('sensor.crypto_inspect_bybit_balance') %}
            {% if is_state('input_select.crypto_notification_language', 'Russian') %}
            📊 F&G: {{ fg }}
            📈 Волатильность: {{ vol }}
            💰 DCA: {{ dca }}
            {% if balance != 'unknown' %}💼 Bybit: ${{ balance | int }}{% endif %}
            {% else %}
            📊 F&G: {{ fg }}
            📈 Volatility: {{ vol }}
            💰 DCA: {{ dca }}
            {% if balance != 'unknown' %}💼 Bybit: ${{ balance | int }}{% endif %}
            {% endif %}
```

---

### 🌙 Вечерний обзор

```yaml
automation:
  - alias: "Evening Market Review"
    trigger:
      - platform: time
        at: "21:00:00"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "🌙 Evening Review"
          message: >-
            {% set whales = states('sensor.crypto_inspect_whale_alerts_24h') %}
            {% set event = states('sensor.crypto_inspect_next_macro_event') %}
            {% set flags = states('sensor.crypto_inspect_red_flags') %}
            {% if is_state('input_select.crypto_notification_language', 'Russian') %}
            🐋 Whale алертов: {{ whales }}
            📅 Следующее событие: {{ event }}
            🚩 Красных флагов: {{ flags }}
            {% else %}
            🐋 Whale alerts: {{ whales }}
            📅 Next event: {{ event }}
            🚩 Red flags: {{ flags }}
            {% endif %}
```

---

### 🎛️ Смена фазы рынка

```yaml
automation:
  - alias: "Market Phase Change"
    trigger:
      - platform: state
        entity_id: sensor.crypto_inspect_investor_phase
    condition:
      - condition: template
        value_template: "{{ trigger.from_state.state != trigger.to_state.state and trigger.from_state.state != 'unknown' }}"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "🎛️ Market Phase Changed"
          message: >-
            {% set phase = trigger.to_state.state %}
            {% set desc = state_attr('sensor.crypto_inspect_investor_phase', 'description') %}
            {% if is_state('input_select.crypto_notification_language', 'Russian') %}
            Новая фаза: {{ phase }}
            {{ desc }}
            {% else %}
            New phase: {{ phase }}
            {{ desc }}
            {% endif %}
```

---

### 📲 Actionable Notifications (iOS)

Для iOS можно добавить кнопки действий:

```yaml
automation:
  - alias: "DCA Actionable Alert"
    trigger:
      - platform: state
        entity_id: sensor.crypto_inspect_dca_zone
        to: "Buy Zone"
    action:
      - service: notify.mobile_app_iphone
        data:
          title: "💰 DCA Opportunity"
          message: >-
            {% if is_state('input_select.crypto_notification_language', 'Russian') %}
            Войти в позицию?
            {% else %}
            Enter position?
            {% endif %}
          data:
            actions:
              - action: "OPEN_BYBIT"
                title: >-
                  {% if is_state('input_select.crypto_notification_language', 'Russian') %}
                  Открыть Bybit
                  {% else %}
                  Open Bybit
                  {% endif %}
                uri: "bybit://"
              - action: "DISMISS"
                title: >-
                  {% if is_state('input_select.crypto_notification_language', 'Russian') %}
                  Позже
                  {% else %}
                  Later
                  {% endif %}
```

---

### 🔔 TTS оповещения (голосовые)

```yaml
automation:
  - alias: "Voice Alert Extreme Fear"
    trigger:
      - platform: numeric_state
        entity_id: sensor.crypto_inspect_fear_greed
        below: 15
    action:
      - service: tts.google_translate_say
        data:
          entity_id: media_player.living_room_speaker
          message: >-
            {% set fg = states('sensor.crypto_inspect_fear_greed') %}
            {% if is_state('input_select.crypto_notification_language', 'Russian') %}
            Внимание! Экстремальный страх на крипторынке. Fear and Greed index {{ fg }}. Возможно хорошее время для покупки.
            {% else %}
            Attention! Extreme fear in crypto market. Fear and Greed index {{ fg }}. Possibly a good time to buy.
            {% endif %}
```

---

## CSV Export (Bybit)

Add-on позволяет экспортировать данные в CSV для налоговой отчетности.

### Endpoints

- `http://homeassistant.local:9999/api/bybit/export/trades` - История сделок
- `http://homeassistant.local:9999/api/bybit/export/pnl` - P&L по активам
- `http://homeassistant.local:9999/api/bybit/export/tax` - Формат для налоговой

### Параметры

```
?start_date=2024-01-01&end_date=2024-12-31
```

---

## Troubleshooting

### Сенсоры не появляются

1. Перезапустите add-on
2. Проверьте что add-on запущен (зеленый статус)
3. Посмотрите логи: Settings → Add-ons → Crypto Inspect → Logs

### Bybit не подключается

1. Проверьте API ключи в настройках
2. Убедитесь что ваш IP разрешен в Bybit API Management
3. Для реального аккаунта: `bybit_testnet: false`
4. Проверьте права API (Read-only достаточно)

### Данные не обновляются

1. Проверьте `sensor.crypto_inspect_sync_status`
2. Проверьте интернет на хосте Home Assistant
3. Некоторые данные обновляются раз в несколько часов (корреляции, макро)

### Ошибки в логах

- `Supervisor API error` - Проверьте что add-on запущен в режиме Supervisor
- `Bybit API error` - Проверьте API ключи
- `Rate limit` - Слишком частые запросы, подождите

---

## MCP Server (Model Context Protocol)

Crypto Inspect включает MCP сервер для интеграции с AI-агентами (Claude Desktop, Gemini, OpenAI Agents и др.).

### Конфигурация

```yaml
mcp_enabled: true    # Включить MCP сервер
mcp_port: 9998       # Порт MCP сервера
```

MCP сервер запускается автоматически на отдельном порту и предоставляет все данные через стандартный протокол MCP.

### Подключение к Claude Desktop

Добавьте в `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "crypto-inspect": {
      "command": "curl",
      "args": ["http://homeassistant.local:9998/sse"]
    }
  }
}
```

### Доступные инструменты (Tools)

#### Криптовалюты

| Tool | Описание | Параметры |
|------|----------|-----------||
| `get_crypto_prices` | Текущие цены криптовалют | - |
| `get_crypto_analysis` | Технический анализ символа | `symbol: str` |
| `get_candlesticks` | Исторические свечи | `symbol: str, interval: str, limit: int` |
| `get_market_summary` | Обзор рынка | - |
| `get_btc_dominance` | Доминация Bitcoin | - |
| `get_altseason_index` | Индекс альтсезона | - |

#### Индикаторы и аналитика

| Tool | Описание | Параметры |
|------|----------|-----------||
| `get_fear_greed_index` | Индекс страха и жадности | - |
| `get_volatility` | Волатильность рынка | - |
| `get_correlations` | Корреляции между активами | - |
| `get_dca_recommendation` | Рекомендации по DCA | - |
| `get_profit_taking_levels` | Уровни фиксации прибыли | `symbol: str` |

#### Деривативы

| Tool | Описание | Параметры |
|------|----------|-----------||
| `get_funding_rates` | Ставки финансирования | - |
| `get_liquidation_levels` | Уровни ликвидаций | `symbol: str` |
| `get_arbitrage_opportunities` | Арбитражные возможности | - |

#### On-Chain данные

| Tool | Описание | Параметры |
|------|----------|-----------||
| `get_whale_alerts` | Крупные переводы | - |
| `get_exchange_flow` | Потоки на биржи | - |
| `get_gas_tracker` | ETH Gas Tracker | - |

#### Традиционные финансы

| Tool | Описание | Параметры |
|------|----------|-----------||
| `get_traditional_finance` | Все традиционные активы | - |
| `get_metals_prices` | Золото, серебро, платина | - |
| `get_indices_prices` | S&P500, NASDAQ, DAX | - |
| `get_forex_prices` | EUR/USD, GBP/USD, DXY | - |
| `get_commodities_prices` | Нефть, газ | - |

#### Макро и события

| Tool | Описание | Параметры |
|------|----------|-----------||
| `get_macro_events` | Макроэкономические события | - |
| `get_token_unlocks` | Token Unlock расписание | - |

#### Портфель и статус

| Tool | Описание | Параметры |
|------|----------|-----------||
| `get_investor_status` | Статус "ленивого инвестора" | - |
| `get_bybit_portfolio` | Портфель Bybit (если настроен) | - |
| `get_signals` | Последние торговые сигналы | `hours: int` |

### Доступные ресурсы (Resources)

| Resource URI | Описание |
|--------------|----------|
| `crypto://prices` | Текущие цены всех пар |
| `crypto://analysis/{symbol}` | Анализ по символу |
| `crypto://candles/{symbol}/{interval}` | Свечные данные |
| `finance://metals` | Цены металлов |
| `finance://indices` | Цены индексов |
| `finance://forex` | Курсы валют |
| `finance://commodities` | Цены сырья |

### Пример использования в Claude

```
Пользователь: Какая сейчас ситуация на крипторынке?

Claude: [использует get_market_summary, get_fear_greed_index, get_btc_dominance]

Биткоин торгуется на уровне $100,000, Fear & Greed Index показывает 72 (Жадность).
Доминация BTC составляет 54.3%, что указывает на...
```

---

## Historical Data Backfill

При первом запуске Crypto Inspect автоматически загружает исторические данные.

### Конфигурация

```yaml
backfill_enabled: true           # Включить backfill
backfill_crypto_years: 10        # Лет истории для крипты
backfill_traditional_years: 1    # Лет истории для традиционных активов
backfill_intervals: "1d,4h,1h"   # Интервалы для загрузки
```

### Как это работает

1. При первом запуске система проверяет наличие маркерного файла `/data/backfill_completed`
2. Если файл отсутствует, запускается фоновая загрузка данных:
   - **Криптовалюты**: до 10 лет истории для всех настроенных пар
   - **Традиционные активы**: 1 год истории (Gold, S&P500, EUR/USD и др.)
3. Данные загружаются в фоне, не блокируя основной функционал
4. После завершения создается маркерный файл

### API для мониторинга

| Endpoint | Описание |
|----------|----------|
| `GET /api/backfill/status` | Статус загрузки |
| `POST /api/backfill/trigger` | Запустить backfill вручную |
| `GET /api/backfill/gaps` | Найти пропуски в данных |

### Пример ответа `/api/backfill/status`

```json
{
  "is_running": false,
  "completed": true,
  "crypto_symbols": ["BTC/USDT", "ETH/USDT"],
  "crypto_years": 10,
  "traditional_symbols": ["GC=F", "^GSPC"],
  "traditional_years": 1,
  "last_run": "2025-01-15T12:00:00Z"
}
```

---

## UX Enhancement Suite

### Smart Summary / Умная сводка

Агрегированные сенсоры для быстрого понимания рынка.

| Сенсор | Описание / Description |
|--------|------------------------|
| `market_pulse` | Настроение рынка (Бычий/Нейтральный/Медвежий) / Market sentiment |
| `market_pulse_confidence` | Уверенность оценки (%) / Confidence level |
| `portfolio_health` | Здоровье портфеля / Portfolio health status |
| `portfolio_health_score` | Оценка здоровья (0-100) / Health score |
| `today_action` | Рекомендуемое действие на сегодня / Today's action |
| `today_action_priority` | Приоритет действия / Action priority |
| `weekly_outlook` | Недельный прогноз / Weekly outlook |

### Notifications / Уведомления

Умная система приоритетных уведомлений с дайджестами.

| Сенсор | Описание |
|--------|----------|
| `pending_alerts_count` | Количество ожидающих оповещений |
| `pending_alerts_critical` | Критических оповещений |
| `daily_digest_ready` | Готов ли дайджест |
| `notification_mode` | Режим уведомлений |

**Режимы уведомлений:**
- `all` - Все сразу
- `smart` - Только критические сразу, остальное в дайджест
- `digest_only` - Только дайджест
- `critical_only` - Только критические
- `silent` - Без уведомлений

### Briefings / Брифинги

Утренние и вечерние отчёты.

| Сенсор | Описание |
|--------|----------|
| `morning_briefing` | Статус утреннего брифинга |
| `evening_briefing` | Статус вечернего брифинга |
| `briefing_last_sent` | Время последнего брифинга |

### Goal Tracking / Отслеживание целей

Личные финансовые цели с визуальным прогрессом.

| Сенсор | Описание |
|--------|----------|
| `goal_target` | Целевая сумма (USDT) |
| `goal_progress` | Прогресс (%) |
| `goal_remaining` | Осталось до цели (USDT) |
| `goal_days_estimate` | Оценка дней до цели |
| `goal_status` | Статус цели |

**Конфигурация:**

```yaml
# config.yaml
goal_enabled: true
goal_target_value: 100000
goal_name: "Financial Freedom"
goal_name_ru: "Финансовая свобода"
```

**Этапы (milestones):** 10%, 25%, 50%, 75%, 90%, 100%

### Progressive Disclosure Dashboards

Три уровня дашбордов:

1. **Summary** (`dashboards/views/summary.yaml`) - 4 плитки, 2 секунды на понимание
2. **Detailed** (`dashboards/views/detailed.yaml`) - Расширенные секции с контекстом
3. **Power User** (`dashboards/views/power_user.yaml`) - Все технические данные

### UX Blueprints

| Blueprint | Описание |
|-----------|----------|
| `daily_digest.yaml` | Ежедневный дайджест оповещений |
| `morning_briefing.yaml` | Утренний брифинг |
| `evening_briefing.yaml` | Вечерний брифинг |
| `goal_milestone.yaml` | Уведомления о достижении этапов |

### UX API Endpoints

| Endpoint | Описание |
|----------|----------|
| `GET /api/summary/market-pulse` | Market Pulse сентимент |
| `GET /api/summary/portfolio-health` | Здоровье портфеля |
| `GET /api/summary/today-action` | Действие на сегодня |
| `GET /api/summary/full` | Полная сводка |
| `GET /api/briefing/morning` | Утренний брифинг |
| `GET /api/briefing/evening` | Вечерний брифинг |
| `GET /api/briefing/notifications/digest` | Дневной дайджест |
| `POST /api/briefing/notifications/mode` | Установить режим |
| `GET /api/goals/progress` | Прогресс цели |
| `GET /api/goals/milestones` | Достигнутые этапы |
| `POST /api/goals/record` | Записать значение |

### Пример карточки Market Pulse

```yaml
type: custom:mushroom-template-card
primary: "{{ states('sensor.crypto_inspect_market_pulse') }}"
secondary: "{{ state_attr('sensor.crypto_inspect_market_pulse', 'reason_ru') }}"
icon: mdi:pulse
icon_color: |-
  {% set sentiment = states('sensor.crypto_inspect_market_pulse') %}
  {% if 'Бычий' in sentiment %}green
  {% elif 'Медвежий' in sentiment %}red
  {% else %}orange{% endif %}
```

### Пример карточки Goal Progress

```yaml
type: vertical-stack
cards:
  - type: custom:mushroom-template-card
    primary: "{{ state_attr('sensor.crypto_inspect_goal_target', 'goal_name_ru') }}"
    secondary: "{{ states('sensor.crypto_inspect_goal_progress') }} • Осталось: ${{ states('sensor.crypto_inspect_goal_remaining') }}"
    icon: mdi:trophy
    icon_color: amber

  - type: gauge
    entity: sensor.crypto_inspect_goal_progress
    name: Прогресс к цели
    min: 0
    max: 100
    severity:
      green: 75
      yellow: 25
      red: 0
```

---

## API Reference

Add-on предоставляет REST API на порту 9999.

### Основные

| Endpoint | Описание |
|----------|----------|
| `GET /health` | Статус сервиса |
| `GET /api/bybit/balance` | Bybit баланс |
| `GET /api/bybit/positions` | Bybit позиции |
| `GET /api/bybit/pnl?period=7d` | P&L за период |
| `GET /api/analysis/{symbol}` | Анализ символа |
| `GET /api/market/summary` | Обзор рынка |
| `GET /api/investor/status` | Статус инвестора |
| `GET /api/candles/{symbol}` | Данные свечей |

### AI Анализ

| Endpoint | Описание |
|----------|----------|
| `GET /api/ai/summary` | Последняя AI сводка |
| `POST /api/ai/analyze` | Запустить AI анализ |
| `GET /api/ai/analyze/{symbol}` | AI анализ символа |
| `GET /api/ai/status` | Статус AI сервиса |

### Технический анализ

| Endpoint | Описание |
|----------|----------|
| `GET /api/ta/{symbol}` | Технические индикаторы |
| `GET /api/ta/{symbol}/signals` | Торговые сигналы |
| `GET /api/ta/confluence` | Confluence скор |

### Риск-менеджмент

| Endpoint | Описание |
|----------|----------|
| `GET /api/risk/portfolio` | Риск-метрики портфеля |
| `GET /api/risk/stress-test` | Стресс-тест портфеля |

### DCA Backtesting

| Endpoint | Описание |
|----------|----------|
| `GET /api/backtest/dca?symbol=BTC&years=5` | DCA бэктест |
| `GET /api/backtest/smart-dca?symbol=BTC&years=5` | Smart DCA бэктест |
| `GET /api/backtest/compare?symbol=BTC` | Сравнение стратегий |

---

## Примеры Lovelace - Advanced Analytics

### AI Insights карточка

```yaml
type: markdown
title: "🤖 AI Анализ"
content: |
  ### {{ states('sensor.crypto_inspect_ai_market_sentiment') }}

  **Рекомендация:** {{ states('sensor.crypto_inspect_ai_recommendation') }}

  {{ states('sensor.crypto_inspect_ai_daily_summary') }}

  ---
  *Обновлено: {{ states('sensor.crypto_inspect_ai_last_analysis') }}*
  *Провайдер: {{ states('sensor.crypto_inspect_ai_provider') }}*
```

### Технический анализ BTC

```yaml
type: grid
title: "📈 BTC Technical"
cards:
  - type: tile
    entity: sensor.crypto_inspect_btc_rsi
    name: "RSI"
    icon: mdi:chart-line
    color: |
      {% set rsi = states('sensor.crypto_inspect_btc_rsi') | int(50) %}
      {% if rsi > 70 %}red
      {% elif rsi < 30 %}green
      {% else %}blue{% endif %}
  - type: tile
    entity: sensor.crypto_inspect_btc_trend
    name: "Тренд"
    icon: mdi:trending-up
    color: |
      {% set trend = states('sensor.crypto_inspect_btc_trend') %}
      {% if 'Up' in trend %}green
      {% elif 'Down' in trend %}red
      {% else %}grey{% endif %}
  - type: tile
    entity: sensor.crypto_inspect_btc_macd_signal
    name: "MACD"
    icon: mdi:signal
  - type: tile
    entity: sensor.crypto_inspect_ta_confluence
    name: "Confluence"
    icon: mdi:check-all
```

### RSI с зонами

```yaml
type: custom:apexcharts-card
header:
  show: true
  title: "BTC RSI"
chart_type: radialBar
series:
  - entity: sensor.crypto_inspect_btc_rsi
    name: RSI
apex_config:
  plotOptions:
    radialBar:
      startAngle: -135
      endAngle: 135
      dataLabels:
        name:
          show: true
        value:
          fontSize: '24px'
      track:
        background: '#333'
  colors:
    - |
      EVAL:function(value) {
        if (value > 70) return '#ef5350';
        if (value < 30) return '#26a69a';
        return '#42a5f5';
      }
```

### Риск-менеджмент

```yaml
type: entities
title: "⚠️ Риск-метрики"
entities:
  - entity: sensor.crypto_inspect_portfolio_sharpe
    name: "Sharpe Ratio"
    icon: mdi:chart-areaspline
  - entity: sensor.crypto_inspect_portfolio_sortino
    name: "Sortino Ratio"
    icon: mdi:chart-line-variant
  - entity: sensor.crypto_inspect_portfolio_max_drawdown
    name: "Макс. просадка"
    icon: mdi:trending-down
  - entity: sensor.crypto_inspect_portfolio_var_95
    name: "VaR 95%"
    icon: mdi:alert
  - entity: sensor.crypto_inspect_risk_status
    name: "Статус риска"
    icon: mdi:shield-alert
```

### DCA Backtest результаты

```yaml
type: markdown
title: "📊 DCA Backtest"
content: |
  ### Сравнение стратегий ({{ states('sensor.crypto_inspect_backtest_period') }})

  | Стратегия | ROI |
  |----------|-----|
  | **Fixed DCA** | {{ states('sensor.crypto_inspect_backtest_dca_roi') }}% |
  | **Smart DCA** | {{ states('sensor.crypto_inspect_backtest_smart_dca_roi') }}% |
  | **Lump Sum** | {{ states('sensor.crypto_inspect_backtest_lump_sum_roi') }}% |

  🏆 **Лучшая:** {{ states('sensor.crypto_inspect_backtest_best_strategy') }}
```

### Поддержка/Сопротивление

```yaml
type: glance
title: "🚧 Уровни BTC"
entities:
  - entity: sensor.crypto_inspect_btc_support
    name: "Поддержка"
    icon: mdi:arrow-down-bold
  - entity: sensor.crypto_inspect_btc_resistance
    name: "Сопротивление"
    icon: mdi:arrow-up-bold
```

---

## Поддержка

Если у вас возникли проблемы:

1. Проверьте логи add-on
2. Создайте issue на GitHub с логами и описанием проблемы

GitHub: https://github.com/Mesteriis/crypto-inspector

---

## Blueprint Автоматизации

Gotovye Blueprint-ы для быстрой настройки автоматизаций.

### Установка

1. Скопируйте файлы из `/blueprints/` в `config/blueprints/automation/crypto_inspect/`
2. Перезагрузите Home Assistant
3. Создайте автоматизацию из Blueprint: Settings → Automations → “+ Create Automation” → “Use Blueprint”

### Доступные Blueprint-ы

| Blueprint | Описание |
|-----------|----------|
| `price_alert.yaml` | Алерт при достижении цены |
| `fear_greed_alert.yaml` | Алерт Fear & Greed Index |
| `dca_reminder.yaml` | Еженедельное напоминание DCA |
| `technical_signal.yaml` | Алерт технического сигнала |
| `risk_alert.yaml` | Предупреждение о риске портфеля |
| `ai_report.yaml` | Ежедневный AI отчёт |
| `whale_alert.yaml` | Алерт китов |
| `portfolio_milestone.yaml` | Достижение цели портфеля |

### Пример использования Price Alert

После импорта blueprint, создайте автоматизацию:

1. Выберите символ (BTC, ETH, SOL)
2. Укажите условие (above/below)
3. Укажите целевую цену
4. Выберите сервис уведомлений

### Пример DCA Reminder

Настраиваемые параметры:
- День недели (Пн-Вс)
- Время напоминания
- Базовая сумма DCA
- Сервис уведомлений

Blueprint автоматически учитывает Fear & Greed Index для расчёта Smart DCA множителя.
