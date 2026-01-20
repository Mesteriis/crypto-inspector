# Crypto Inspect - Home Assistant Add-on

Профессиональный криптовалютный анализатор для Home Assistant. Собирает рыночные данные, анализирует тренды, отслеживает портфель и отправляет сигналы прямо в вашу умную панель.

## Возможности

### 🔗 Интеграция с Bybit
- Синхронизация баланса и позиций
- Расчет P&L по периодам (24ч, 7д, 30д, YTD, всё время)
- Экспорт сделок в CSV (для налоговой)
- Отслеживание нереализованной прибыли

### 🤖 AI Анализ (NEW!)
- **ChatGPT** и **Ollama** интеграция
- Ежедневная AI-сводка рынка
- Анализ настроения и рекомендации
- Автоматический fallback между провайдерами

### 📈 Технический анализ (NEW!)
- **RSI, MACD, Bollinger Bands** как сенсоры HA
- Определение тренда и его силы
- Уровни поддержки/сопротивления
- Confluence Score для общей оценки

### ⚠️ Риск-менеджмент (NEW!)
- **Sharpe Ratio** и **Sortino Ratio**
- **Value at Risk (VaR)** 95% и 99%
- Отслеживание drawdown
- Стресс-тестирование портфеля

### 📊 DCA Backtesting (NEW!)
- Сравнение стратегий: Fixed DCA vs Smart DCA vs Lump Sum
- Smart DCA с Fear & Greed множителями
- Исторический анализ до 10 лет

### 📊 Анализ рынка
- **Fear & Greed Index** - индекс страха и жадности
- **BTC Dominance** - доминация биткоина
- **Altseason Index** - сезон альткоинов
- **Volatility Index** - волатильность рынка
- **Correlation Tracker** - корреляции BTC/ETH/S&P500

### 💰 Инструменты трейдера
- **DCA Calculator** - уровни для усреднения (Fibonacci)
- **Profit Taking Advisor** - когда фиксировать прибыль
- **Arbitrage Scanner** - арбитражные возможности
- **Liquidation Levels** - уровни ликвидаций
- **Token Unlocks** - разлоки токенов

### 📅 Макро-события
- FOMC (заседания ФРС)
- CPI (инфляция)
- NFP (рынок труда)
- Экономический календарь

### 🐋 On-Chain данные
- Whale Alerts - крупные переводы
- Exchange Flow - потоки на биржи
- Stablecoin Flow - потоки стейблкоинов
- Gas Tracker - цены на газ ETH

---

## Установка

### Как Home Assistant Add-on

1. Добавьте репозиторий в Supervisor:
   ```
   https://github.com/Mesteriis/crypto-inspector
   ```

2. Установите add-on "Crypto Inspect"

3. Настройте параметры в UI

4. Запустите add-on

### Standalone (для разработки)

```bash
git clone https://github.com/Mesteriis/crypto-inspector
cd crypto-inspector
make install
make run
```

---

## Конфигурация

### Основные настройки

| Параметр | Описание | По умолчанию |
|----------|----------|--------------|
| `api_port` | Порт API | `9999` |
| `database_type` | Тип БД | `sqlite` |
| `symbols` | Торговые пары | `["BTC/USDT", "ETH/USDT"]` |
| `log_level` | Уровень логов | `info` |

### Bybit API (поддерживает secrets)

```yaml
bybit_api_key: !secret bybit_api_key
bybit_api_secret: !secret bybit_api_secret
bybit_testnet: false
```

В `secrets.yaml`:
```yaml
bybit_api_key: "your_api_key_here"
bybit_api_secret: "your_api_secret_here"
```

### Анализ

| Параметр | Описание | По умолчанию |
|----------|----------|--------------|
| `analysis_enabled` | Включить анализ | `true` |
| `analysis_interval_hours` | Интервал анализа | `4` |
| `alert_on_strong_signals` | Алерты на сигналы | `true` |
| `alert_threshold_buy` | Порог покупки | `75` |
| `alert_threshold_sell` | Порог продажи | `25` |

### MCP Server (Model Context Protocol)

**Для интеграции с AI-агентами (Claude, Gemini, OpenAI)**

| Параметр | Описание | По умолчанию |
|----------|----------|--------------|
| `mcp_enabled` | Включить MCP сервер | `true` |
| `mcp_port` | Порт MCP сервера | `9998` |

Доступные MCP инструменты (tools):
- `get_crypto_prices` - Текущие цены криптовалют
- `get_crypto_analysis` - Технический анализ
- `get_candlesticks` - Исторические свечи
- `get_market_summary` - Обзор рынка
- `get_fear_greed_index` - Индекс страха/жадности
- `get_traditional_finance` - Золото, индексы, форекс
- `get_whale_alerts` - Алерты китов
- `get_funding_rates` - Ставки финансирования
- `get_liquidation_levels` - Уровни ликвидаций
- `get_investor_status` - Статус ленивого инвестора
- `get_bybit_portfolio` - Портфель Bybit
- и ещё 20+ инструментов

### Historical Data Backfill

**Автоматическая загрузка исторических данных при первом запуске**

| Параметр | Описание | По умолчанию |
|----------|----------|------------|
| `backfill_enabled` | Включить backfill | `true` |
| `backfill_crypto_years` | Годы истории крипты | `10` |
| `backfill_traditional_years` | Годы истории трад. активов | `1` |

### AI Анализ (ChatGPT / Ollama)

**Интеграция с AI для анализа рынка**

| Параметр | Описание | По умолчанию |
|----------|----------|------------|
| `ai_enabled` | Включить AI анализ | `false` |
| `ai_provider` | Провайдер (ollama/openai) | `ollama` |
| `openai_api_key` | API ключ OpenAI | `` |
| `openai_model` | Модель OpenAI | `gpt-4o-mini` |
| `ollama_host` | Хост Ollama | `http://localhost:11434` |
| `ollama_model` | Модель Ollama | `llama3.2` |
| `ai_analysis_interval_hours` | Интервал анализа (часы) | `24` |
| `ai_language` | Язык отчётов (ru/en) | `ru` |

**Пример конфигурации:**

```yaml
# Для OpenAI (ChatGPT)
ai_enabled: true
ai_provider: openai
openai_api_key: !secret openai_api_key
openai_model: gpt-4o-mini

# Для Ollama (локально)
ai_enabled: true
ai_provider: ollama
ollama_host: "http://192.168.1.100:11434"
ollama_model: "llama3.2"
```

---

## Сенсоры Home Assistant

### Цены и объемы

| Сенсор | Описание | Формат |
|--------|----------|--------|
| `sensor.crypto_inspect_prices` | Текущие цены | `{"BTC/USDT": "100000", "ETH/USDT": "3500"}` |
| `sensor.crypto_inspect_changes_24h` | Изменение за 24ч | `{"BTC/USDT": "2.50", "ETH/USDT": "-1.20"}` |
| `sensor.crypto_inspect_volumes_24h` | Объемы | `{"BTC/USDT": "1500000000"}` |
| `sensor.crypto_inspect_highs_24h` | Максимумы | `{"BTC/USDT": "102000"}` |
| `sensor.crypto_inspect_lows_24h` | Минимумы | `{"BTC/USDT": "98000"}` |

### Bybit Exchange

| Сенсор | Описание |
|--------|----------|
| `sensor.crypto_inspect_bybit_balance` | Общий баланс (USDT) |
| `sensor.crypto_inspect_bybit_pnl_24h` | P&L за 24 часа (%) |
| `sensor.crypto_inspect_bybit_pnl_7d` | P&L за 7 дней (%) |
| `sensor.crypto_inspect_bybit_positions` | Количество позиций |
| `sensor.crypto_inspect_bybit_unrealized_pnl` | Нереализованная прибыль |

### Ленивый инвестор

| Сенсор | Описание |
|--------|----------|
| `sensor.crypto_inspect_do_nothing_ok` | Можно ничего не делать? |
| `sensor.crypto_inspect_investor_phase` | Фаза рынка |
| `sensor.crypto_inspect_calm_indicator` | Индикатор спокойствия (0-100) |
| `sensor.crypto_inspect_red_flags` | Красные флаги |
| `sensor.crypto_inspect_dca_signal` | Сигнал DCA |
| `sensor.crypto_inspect_dca_result` | Сумма для DCA (€) |

### Рыночные индикаторы

| Сенсор | Описание |
|--------|----------|
| `sensor.crypto_inspect_fear_greed` | Fear & Greed Index (0-100) |
| `sensor.crypto_inspect_btc_dominance` | Доминация BTC (%) |
| `sensor.crypto_inspect_altseason_index` | Индекс альтсезона |
| `sensor.crypto_inspect_altseason_status` | Статус альтсезона |

### Волатильность и корреляции

| Сенсор | Описание |
|--------|----------|
| `sensor.crypto_inspect_btc_volatility_30d` | Волатильность BTC 30д (%) |
| `sensor.crypto_inspect_volatility_status` | Статус волатильности |
| `sensor.crypto_inspect_btc_eth_correlation` | Корреляция BTC/ETH |
| `sensor.crypto_inspect_btc_sp500_correlation` | Корреляция BTC/S&P500 |

### DCA и Take Profit

| Сенсор | Описание |
|--------|----------|
| `sensor.crypto_inspect_tp_levels` | Уровни фиксации (словарь) |
| `sensor.crypto_inspect_profit_action` | Действие по прибыли |
| `sensor.crypto_inspect_greed_level` | Уровень жадности (0-100) |
| `sensor.crypto_inspect_dca_result` | Результат DCA (€) |
| `sensor.crypto_inspect_dca_signal` | Сигнал DCA (buy/wait/hold) |
| `sensor.crypto_inspect_dca_risk_score` | Риск-скор DCA (0-100) |

### Макро и события

| Сенсор | Описание |
|--------|----------|
| `sensor.crypto_inspect_next_macro_event` | Следующее макро-событие |
| `sensor.crypto_inspect_days_to_fomc` | Дней до FOMC |
| `sensor.crypto_inspect_macro_risk_week` | Риск недели (Low/Med/High) |
| `sensor.crypto_inspect_unlocks_next_7d` | Анлоков за 7 дней |
| `sensor.crypto_inspect_unlock_next_event` | Следующий анлок |

### On-Chain

| Сенсор | Описание |
|--------|----------|
| `sensor.crypto_inspect_whale_alerts_24h` | Китовых алертов за 24ч |
| `sensor.crypto_inspect_whale_net_flow` | Нетто-поток китов |
| `sensor.crypto_inspect_btc_exchange_netflow` | Поток BTC на биржи |
| `sensor.crypto_inspect_exchange_flow_signal` | Сигнал потока |
| `sensor.crypto_inspect_eth_gas_standard` | Газ ETH (Gwei) |

### Арбитраж

| Сенсор | Описание |
|--------|----------|
| `sensor.crypto_inspect_btc_arb_spread` | Спред арбитража BTC (%) |
| `sensor.crypto_inspect_funding_arb_best` | Лучший фандинг арбитраж |
| `sensor.crypto_inspect_arb_opportunity` | Возможность арбитража |

### AI Анализ

| Сенсор | Описание |
|--------|----------|
| `sensor.crypto_inspect_ai_daily_summary` | AI сводка рынка |
| `sensor.crypto_inspect_ai_market_sentiment` | AI оценка настроения |
| `sensor.crypto_inspect_ai_recommendation` | AI рекомендация |
| `sensor.crypto_inspect_ai_last_analysis` | Время анализа |
| `sensor.crypto_inspect_ai_provider` | Провайдер AI |

### Технический анализ

| Сенсор | Описание |
|--------|----------|
| `sensor.crypto_inspect_btc_rsi` | RSI (14) BTC |
| `sensor.crypto_inspect_btc_macd_signal` | MACD сигнал |
| `sensor.crypto_inspect_btc_bb_position` | Позиция в BB (%) |
| `sensor.crypto_inspect_btc_trend` | Тренд BTC |
| `sensor.crypto_inspect_btc_support` | Поддержка |
| `sensor.crypto_inspect_btc_resistance` | Сопротивление |
| `sensor.crypto_inspect_ta_confluence` | Confluence Score |

### Риск-менеджмент

| Сенсор | Описание |
|--------|----------|
| `sensor.crypto_inspect_portfolio_sharpe` | Sharpe Ratio |
| `sensor.crypto_inspect_portfolio_sortino` | Sortino Ratio |
| `sensor.crypto_inspect_portfolio_max_drawdown` | Макс. просадка (%) |
| `sensor.crypto_inspect_portfolio_var_95` | VaR 95% |
| `sensor.crypto_inspect_risk_status` | Статус риска |

### DCA Backtesting

| Сенсор | Описание |
|--------|----------|
| `sensor.crypto_inspect_backtest_dca_roi` | ROI Fixed DCA (%) |
| `sensor.crypto_inspect_backtest_smart_dca_roi` | ROI Smart DCA (%) |
| `sensor.crypto_inspect_backtest_lump_sum_roi` | ROI Lump Sum (%) |
| `sensor.crypto_inspect_backtest_best_strategy` | Лучшая стратегия |

### Ликвидации

| Сенсор | Описание |
|--------|----------|
| `sensor.crypto_inspect_btc_liq_long_nearest` | Ближайшая ликвидация лонгов |
| `sensor.crypto_inspect_btc_liq_short_nearest` | Ближайшая ликвидация шортов |
| `sensor.crypto_inspect_liq_risk_level` | Уровень риска ликвидаций |

### Традиционные финансы

#### Металлы

| Сенсор | Описание |
|--------|----------|
| `sensor.crypto_inspect_gold_price` | Золото (USD) |
| `sensor.crypto_inspect_silver_price` | Серебро (USD) |
| `sensor.crypto_inspect_platinum_price` | Платина (USD) |

#### Индексы

| Сенсор | Описание |
|--------|----------|
| `sensor.crypto_inspect_sp500_price` | S&P 500 |
| `sensor.crypto_inspect_nasdaq_price` | NASDAQ |
| `sensor.crypto_inspect_dji_price` | Dow Jones |
| `sensor.crypto_inspect_dax_price` | DAX (EUR) |

#### Форекс

| Сенсор | Описание |
|--------|----------|
| `sensor.crypto_inspect_eur_usd` | EUR/USD |
| `sensor.crypto_inspect_gbp_usd` | GBP/USD |
| `sensor.crypto_inspect_dxy_index` | Индекс доллара (DXY) |

#### Сырьё

| Сенсор | Описание |
|--------|----------|
| `sensor.crypto_inspect_oil_brent` | Нефть Brent (USD) |
| `sensor.crypto_inspect_oil_wti` | Нефть WTI (USD) |
| `sensor.crypto_inspect_natural_gas` | Природный газ (USD) |

---

## Примеры Lovelace

### Зависимости (HACS)

Для полной функциональности рекомендуется установить:
- **apexcharts-card** - для свечных графиков
- **mushroom-cards** - для красивых карточек
- **mini-graph-card** - для мини-графиков

---

### Input Helpers (добавить в configuration.yaml)

```yaml
input_select:
  crypto_chart_coin:
    name: "Crypto Chart Coin"
    options:
      - BTC
      - ETH
      - SOL
      - TON
      - AR
    initial: BTC
    icon: mdi:bitcoin

  crypto_currency:
    name: "Display Currency"
    options:
      - EUR
      - USD
    initial: EUR
    icon: mdi:currency-eur

  crypto_main_coin:
    name: "Main Coin"
    options:
      - BTC
      - ETH
      - SOL
      - TON
      - AR
    initial: BTC

  crypto_compare_coin:
    name: "Compare Coin"
    options:
      - Нет
      - BTC
      - ETH
      - SOL
    initial: Нет

input_number:
  crypto_dca_weekly_amount:
    name: "DCA Weekly Amount"
    min: 10
    max: 1000
    step: 10
    initial: 100
    unit_of_measurement: "€"
    icon: mdi:cash
```

---

### Свечные графики (ApexCharts)

#### BTC 15-минутный график

```yaml
type: custom:apexcharts-card
header:
  show: true
  title: "{{ states('input_select.crypto_chart_coin') }}/USDT - 15m"
  show_states: false
chart_type: line
update_interval: 1min
span:
  end: now
graph_span: 24h
apex_config:
  chart:
    height: 350px
    type: candlestick
    animations:
      enabled: false
    toolbar:
      show: true
      tools:
        download: false
        selection: true
        zoom: true
        zoomin: true
        zoomout: true
        pan: true
        reset: true
  xaxis:
    type: datetime
    labels:
      datetimeFormatter:
        hour: HH:mm
  yaxis:
    tooltip:
      enabled: true
    labels:
      formatter: |
        EVAL:function(val) {
          return val ? val.toLocaleString('en-US', {maximumFractionDigits: 2}) : '';
        }
  plotOptions:
    candlestick:
      colors:
        upward: '#26a69a'
        downward: '#ef5350'
      wick:
        useFillColor: true
series:
  - entity: sensor.crypto_inspect_prices
    name: OHLC
    type: candlestick
    data_generator: |
      return fetch('/api/crypto_inspect/candles/' + hass.states['input_select.crypto_chart_coin'].state + '/chart?interval=15m&limit=96')
        .then(r => r.json())
        .then(data => data.ohlc || [])
        .catch(() => []);
```

#### BTC 1-часовой график

```yaml
type: custom:apexcharts-card
header:
  show: true
  title: "{{ states('input_select.crypto_chart_coin') }}/USDT - 1h"
  show_states: false
chart_type: line
update_interval: 5min
span:
  end: now
graph_span: 7d
apex_config:
  chart:
    height: 350px
    type: candlestick
    animations:
      enabled: false
    toolbar:
      show: true
  xaxis:
    type: datetime
    labels:
      datetimeFormatter:
        day: dd MMM
        hour: HH:mm
  yaxis:
    tooltip:
      enabled: true
  plotOptions:
    candlestick:
      colors:
        upward: '#26a69a'
        downward: '#ef5350'
      wick:
        useFillColor: true
series:
  - entity: sensor.crypto_inspect_prices
    name: OHLC
    type: candlestick
    data_generator: |
      return fetch('/api/crypto_inspect/candles/' + hass.states['input_select.crypto_chart_coin'].state + '/chart?interval=1h&limit=168')
        .then(r => r.json())
        .then(data => data.ohlc || [])
        .catch(() => []);
```

#### BTC 4-часовой график

```yaml
type: custom:apexcharts-card
header:
  show: true
  title: "{{ states('input_select.crypto_chart_coin') }}/USDT - 4h"
graph_span: 30d
apex_config:
  chart:
    height: 350px
    type: candlestick
  plotOptions:
    candlestick:
      colors:
        upward: '#26a69a'
        downward: '#ef5350'
series:
  - entity: sensor.crypto_inspect_prices
    type: candlestick
    data_generator: |
      return fetch('/api/crypto_inspect/candles/' + hass.states['input_select.crypto_chart_coin'].state + '/chart?interval=4h&limit=180')
        .then(r => r.json())
        .then(data => data.ohlc || [])
        .catch(() => []);
```

#### График объёмов

```yaml
type: custom:apexcharts-card
header:
  show: true
  title: "Volume - {{ states('input_select.crypto_chart_coin') }}"
chart_type: bar
update_interval: 5min
graph_span: 24h
apex_config:
  chart:
    height: 150px
    type: bar
  xaxis:
    type: datetime
  yaxis:
    labels:
      formatter: |
        EVAL:function(val) {
          if (val >= 1000000) return (val/1000000).toFixed(1) + 'M';
          if (val >= 1000) return (val/1000).toFixed(1) + 'K';
          return val.toFixed(0);
        }
  colors:
    - '#546E7A'
series:
  - entity: sensor.crypto_inspect_prices
    name: Volume
    type: column
    data_generator: |
      return fetch('/api/crypto_inspect/candles/' + hass.states['input_select.crypto_chart_coin'].state + '/chart?interval=1h&limit=24')
        .then(r => r.json())
        .then(data => data.volume || [])
        .catch(() => []);
```

---

### TradingView Charts (без HACS)

#### BTC 15-минутный

```yaml
type: iframe
url: "https://s.tradingview.com/widgetembed/?frameElementId=tradingview_btc_15m&symbol=BYBIT%3ABTCUSDT&interval=15&hidesidetoolbar=0&symboledit=0&saveimage=0&toolbarbg=1e222d&studies=MASimple%7C7%7C%7CMASimple%7C25&theme=dark&style=1&timezone=Etc%2FUTC&withdateranges=1&locale=ru"
aspect_ratio: "16:9"
```

#### BTC 1-часовой с индикаторами

```yaml
type: iframe
url: "https://s.tradingview.com/widgetembed/?frameElementId=tradingview_btc_1h&symbol=BYBIT%3ABTCUSDT&interval=60&hidesidetoolbar=0&symboledit=0&saveimage=0&toolbarbg=1e222d&studies=MASimple%7C7%7C%7CMASimple%7C25%7C%7CBollingerBands%4020%2C2&theme=dark&style=1&timezone=Etc%2FUTC&withdateranges=1&locale=ru"
aspect_ratio: "16:9"
```

#### Мульти-чарт (4 таймфрейма)

```yaml
type: vertical-stack
cards:
  - type: horizontal-stack
    cards:
      - type: iframe
        url: "https://s.tradingview.com/widgetembed/?symbol=BYBIT%3ABTCUSDT&interval=15&hidesidetoolbar=1&theme=dark&style=1&locale=ru"
        aspect_ratio: "4:3"
      - type: iframe
        url: "https://s.tradingview.com/widgetembed/?symbol=BYBIT%3ABTCUSDT&interval=60&hidesidetoolbar=1&theme=dark&style=1&locale=ru"
        aspect_ratio: "4:3"
  - type: horizontal-stack
    cards:
      - type: iframe
        url: "https://s.tradingview.com/widgetembed/?symbol=BYBIT%3ABTCUSDT&interval=240&hidesidetoolbar=1&theme=dark&style=1&locale=ru"
        aspect_ratio: "4:3"
      - type: iframe
        url: "https://s.tradingview.com/widgetembed/?symbol=BYBIT%3ABTCUSDT&interval=D&hidesidetoolbar=1&theme=dark&style=1&locale=ru"
        aspect_ratio: "4:3"
```

---

### Главная панель криптовалют

```yaml
type: vertical-stack
cards:
  # Заголовок с ценами
  - type: markdown
    content: |
      # 📊 Crypto Dashboard
      **BTC:** ${{ state_attr('sensor.crypto_inspect_prices', 'BTC/USDT') | default('N/A') }}
      **ETH:** ${{ state_attr('sensor.crypto_inspect_prices', 'ETH/USDT') | default('N/A') }}

  # Bybit баланс
  - type: entities
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

### Карточка Fear & Greed

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

### Карточка "Ленивый инвестор"

```yaml
type: vertical-stack
cards:
  - type: custom:mushroom-template-card
    primary: "{{ states('sensor.crypto_inspect_do_nothing_ok') }}"
    secondary: "{{ state_attr('sensor.crypto_inspect_do_nothing_ok', 'reason') }}"
    icon: mdi:meditation
    icon_color: |
      {% if state_attr('sensor.crypto_inspect_do_nothing_ok', 'value') %}
        green
      {% else %}
        orange
      {% endif %}

  - type: entities
    entities:
      - entity: sensor.crypto_inspect_investor_phase
        name: Фаза рынка
      - entity: sensor.crypto_inspect_calm_indicator
        name: Спокойствие
      - entity: sensor.crypto_inspect_red_flags
        name: Красные флаги
      - entity: sensor.crypto_inspect_dca_signal
        name: Сигнал DCA
```

### Панель волатильности

```yaml
type: custom:mushroom-chips-card
chips:
  - type: template
    content: "Vol: {{ states('sensor.crypto_inspect_btc_volatility_30d') }}%"
    icon: mdi:chart-bell-curve
    icon_color: |
      {% set status = states('sensor.crypto_inspect_volatility_status') %}
      {% if 'Low' in status %}green
      {% elif 'High' in status %}orange
      {% elif 'Extreme' in status %}red
      {% else %}blue{% endif %}
  - type: template
    content: "{{ states('sensor.crypto_inspect_volatility_status') }}"
```

### DCA Calculator

```yaml
type: vertical-stack
cards:
  - type: custom:mushroom-template-card
    primary: DCA Signal
    secondary: "{{ states('sensor.crypto_inspect_dca_signal') }}"
    icon: mdi:target
    icon_color: |
      {% set signal = states('sensor.crypto_inspect_dca_signal') %}
      {% if 'buy' in signal.lower() %}green
      {% elif 'wait' in signal.lower() %}yellow
      {% else %}red{% endif %}

  - type: entities
    title: 📈 DCA Info
    entities:
      - entity: sensor.crypto_inspect_dca_result
        name: Сумма DCA
      - entity: sensor.crypto_inspect_dca_risk_score
        name: Риск-скор
```

### Take Profit Advisor

```yaml
type: glance
title: 🎯 Take Profit
entities:
  - entity: sensor.crypto_inspect_tp_levels
    name: TP1
    attribute: btc_tp_level_1
  - entity: sensor.crypto_inspect_tp_levels
    name: TP2
    attribute: btc_tp_level_2
  - entity: sensor.crypto_inspect_profit_action
    name: Действие
  - entity: sensor.crypto_inspect_greed_level
    name: Жадность
```

### Макро-календарь

```yaml
type: entities
title: 📅 Macro Events
entities:
  - entity: sensor.crypto_inspect_next_macro_event
    name: Следующее событие
  - entity: sensor.crypto_inspect_days_to_fomc
    name: До FOMC
  - entity: sensor.crypto_inspect_macro_risk_week
    name: Риск недели
```

### Token Unlocks

```yaml
type: custom:mushroom-template-card
primary: Token Unlocks
secondary: |
  {{ states('sensor.crypto_inspect_unlocks_next_7d') }} за 7 дней
  Next: {{ states('sensor.crypto_inspect_unlock_next_event') }}
icon: mdi:lock-open-variant
icon_color: |
  {% set risk = states('sensor.crypto_inspect_unlock_risk_level') %}
  {% if 'Low' in risk %}green
  {% elif 'High' in risk %}red
  {% else %}orange{% endif %}
```

### Whale & Exchange Flow

```yaml
type: horizontal-stack
cards:
  - type: custom:mushroom-template-card
    primary: 🐋 Whales
    secondary: "{{ states('sensor.crypto_inspect_whale_alerts_24h') }} alerts"
    icon: mdi:fish

  - type: custom:mushroom-template-card
    primary: Exchange Flow
    secondary: "{{ states('sensor.crypto_inspect_exchange_flow_signal') }}"
    icon: mdi:bank-transfer
    icon_color: |
      {% set signal = states('sensor.crypto_inspect_exchange_flow_signal') %}
      {% if 'Bullish' in signal %}green
      {% elif 'Bearish' in signal %}red
      {% else %}grey{% endif %}
```

### Арбитраж Scanner

```yaml
type: entities
title: ⚡ Arbitrage
entities:
  - entity: sensor.crypto_inspect_btc_arb_spread
    name: BTC Spread
  - entity: sensor.crypto_inspect_funding_arb_best
    name: Best Funding
  - entity: sensor.crypto_inspect_arb_opportunity
    name: Opportunity
```

### ETH Gas Tracker

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
  - entity: sensor.crypto_inspect_eth_gas_status
    name: Status
```

### Liquidation Levels

```yaml
type: custom:mushroom-template-card
primary: Liquidation Risk
secondary: |
  Long: ${{ states('sensor.crypto_inspect_btc_liq_long_nearest') }}
  Short: ${{ states('sensor.crypto_inspect_btc_liq_short_nearest') }}
icon: mdi:alert-decagram
icon_color: |
  {% set risk = states('sensor.crypto_inspect_liq_risk_level') %}
  {% if 'Low' in risk %}green
  {% elif 'High' in risk %}red
  {% else %}orange{% endif %}
```

### Корреляции

```yaml
type: entities
title: 🔗 Correlations
entities:
  - entity: sensor.crypto_inspect_btc_eth_correlation
    name: BTC/ETH
  - entity: sensor.crypto_inspect_btc_sp500_correlation
    name: BTC/S&P500
  - entity: sensor.crypto_inspect_correlation_status
    name: Status
```

### Полная панель (Dashboard)

```yaml
views:
  - title: Crypto
    icon: mdi:bitcoin
    cards:
      # Row 1: Overview
      - type: horizontal-stack
        cards:
          - type: custom:mushroom-template-card
            primary: BTC
            secondary: "${{ states('sensor.crypto_inspect_prices') | from_json | default({}) | selectattr('key', 'eq', 'BTC/USDT') | map(attribute='value') | first | default('N/A') }}"
            icon: mdi:bitcoin
            icon_color: orange

          - type: custom:mushroom-template-card
            primary: Fear & Greed
            secondary: "{{ states('sensor.crypto_inspect_fear_greed') }}"
            icon: mdi:emoticon-neutral

          - type: custom:mushroom-template-card
            primary: Bybit
            secondary: "${{ states('sensor.crypto_inspect_bybit_balance') }}"
            icon: mdi:wallet

      # Row 2: Investor Status
      - type: entities
        title: 🧘 Lazy Investor
        entities:
          - sensor.crypto_inspect_do_nothing_ok
          - sensor.crypto_inspect_investor_phase
          - sensor.crypto_inspect_dca_signal
          - sensor.crypto_inspect_red_flags

      # Row 3: Trading Tools
      - type: horizontal-stack
        cards:
          - type: entities
            title: DCA
            entities:
              - sensor.crypto_inspect_dca_signal
              - sensor.crypto_inspect_dca_result

          - type: entities
            title: Take Profit
            entities:
              - sensor.crypto_inspect_profit_action
              - sensor.crypto_inspect_tp_levels

      # Row 4: Market Data
      - type: entities
        title: 📊 Market
        entities:
          - sensor.crypto_inspect_btc_dominance
          - sensor.crypto_inspect_altseason_status
          - sensor.crypto_inspect_volatility_status
          - sensor.crypto_inspect_correlation_status

      # Row 5: Events & Risks
      - type: horizontal-stack
        cards:
          - type: entities
            title: Events
            entities:
              - sensor.crypto_inspect_next_macro_event
              - sensor.crypto_inspect_unlock_next_event

          - type: entities
            title: Risks
            entities:
              - sensor.crypto_inspect_macro_risk_week
              - sensor.crypto_inspect_liq_risk_level
```

---

### Статус инвестора (полный)

```yaml
type: grid
title: "🧘 Статус инвестора"
cards:
  - type: tile
    entity: sensor.crypto_inspect_do_nothing_ok
    name: "Действие"
    icon: mdi:meditation
    color: >
      {% set state = states('sensor.crypto_inspect_do_nothing_ok') %}
      {% if '🟢' in state %}green
      {% elif '🟡' in state %}amber
      {% else %}red{% endif %}
  - type: tile
    entity: sensor.crypto_inspect_investor_phase
    name: "Фаза рынка"
    icon: mdi:chart-timeline-variant-shimmer
    color: >
      {% set state = states('sensor.crypto_inspect_investor_phase') %}
      {% if 'Accumulation' in state %}green
      {% elif 'Growth' in state %}light-green
      {% elif 'Euphoria' in state %}red
      {% else %}grey{% endif %}
  - type: tile
    entity: sensor.crypto_inspect_calm_indicator
    name: "Спокойствие"
    icon: mdi:emoticon-cool
  - type: tile
    entity: sensor.crypto_inspect_next_action_timer
    name: "След. DCA"
    icon: mdi:timer-outline
  - type: markdown
    content: |
      ### {{ states('sensor.crypto_inspect_do_nothing_ok') }}
      {{ state_attr('sensor.crypto_inspect_do_nothing_ok', 'reason') | default('Нет данных') }}

      ---
      **Фаза:** {{ states('sensor.crypto_inspect_investor_phase') }}

      {{ state_attr('sensor.crypto_inspect_investor_phase', 'description') | default('') }}

      ---
      **{{ state_attr('sensor.crypto_inspect_calm_indicator', 'message') | default('') }}**
```

### Красные флаги и риски

```yaml
type: grid
title: "⚠️ Риски и контекст"
cards:
  - type: tile
    entity: sensor.crypto_inspect_red_flags
    name: "Флаги"
    icon: mdi:flag-variant
    color: >
      {% set count = state_attr('sensor.crypto_inspect_red_flags', 'flags_count') | default(0) | int %}
      {% if count == 0 %}green
      {% elif count <= 2 %}amber
      {% else %}red{% endif %}
  - type: tile
    entity: sensor.crypto_inspect_market_tension
    name: "Напряжённость"
    icon: mdi:gauge
    color: >
      {% set state = states('sensor.crypto_inspect_market_tension') %}
      {% if '🟢' in state %}green
      {% elif '🟡' in state %}amber
      {% else %}red{% endif %}
  - type: tile
    entity: sensor.crypto_inspect_price_context
    name: "Контекст цены"
    icon: mdi:chart-box
  - type: markdown
    content: |
      ### 🚩 Красные флаги
      {{ state_attr('sensor.crypto_inspect_red_flags', 'flags_list') | default('Проверка...') }}

      ---
      ### 📊 Контекст цены BTC
      **{{ states('sensor.crypto_inspect_price_context') }}**

      Текущая: ${{ state_attr('sensor.crypto_inspect_price_context', 'current_price') | default('N/A') }}
      Среднее 6м: ${{ state_attr('sensor.crypto_inspect_price_context', 'avg_6m') | default('N/A') }}
      Отклонение: {{ state_attr('sensor.crypto_inspect_price_context', 'diff_percent') | default(0) }}%

      *{{ state_attr('sensor.crypto_inspect_price_context', 'recommendation') | default('') }}*
```

### Портфель Bybit (подробный)

```yaml
type: grid
title: "💼 Портфель Bybit"
cards:
  - type: markdown
    content: |
      {% set balance = states('sensor.crypto_inspect_bybit_balance') | float(0) %}
      {% set pnl_24h = states('sensor.crypto_inspect_bybit_pnl_24h') | float(0) %}
      {% set pnl_7d = states('sensor.crypto_inspect_bybit_pnl_7d') | float(0) %}

      ### 💰 Всего: ${{ balance | int }}

      | Период | P&L |
      |--------|-----|
      | **24ч** | {{ '🟢' if pnl_24h >= 0 else '🔴' }} {{ pnl_24h | round(2) }}% |
      | **7д** | {{ '🟢' if pnl_7d >= 0 else '🔴' }} {{ pnl_7d | round(2) }}% |

      **Позиций:** {{ states('sensor.crypto_inspect_bybit_positions') }}
  - type: button
    name: "🔄 Обновить"
    icon: mdi:refresh
    tap_action:
      action: perform-action
      perform_action: homeassistant.update_entity
      target:
        entity_id: sensor.crypto_inspect_bybit_balance
```

### DCA Результат (полный)

```yaml
type: grid
title: "💵 DCA на эту неделю"
cards:
  - type: tile
    entity: sensor.crypto_inspect_dca_result
    name: "Сумма DCA"
    icon: mdi:cash-check
  - type: tile
    entity: sensor.crypto_inspect_dca_signal
    name: "Сигнал"
    icon: mdi:cash-plus
    color: >
      {% set state = states('sensor.crypto_inspect_dca_signal') %}
      {% if '🟢' in state %}green
      {% elif '🟡' in state %}amber
      {% else %}red{% endif %}
  - type: markdown
    content: |
      ### 💰 Распределение DCA
      | Актив | Сумма |
      |-------|------:|
      | **BTC** | €{{ state_attr('sensor.crypto_inspect_dca_result', 'btc_amount') | default(0) }} |
      | **ETH** | €{{ state_attr('sensor.crypto_inspect_dca_result', 'eth_amount') | default(0) }} |
      | **Alts** | €{{ state_attr('sensor.crypto_inspect_dca_result', 'alts_amount') | default(0) }} |
      | **Итого** | **€{{ states('sensor.crypto_inspect_dca_result') | default(0) }}** |

      {{ state_attr('sensor.crypto_inspect_dca_result', 'reason') | default('') }}

      📅 {{ states('sensor.crypto_inspect_next_action_timer') }}
```

### Обзор рынка (полный)

```yaml
type: grid
title: "📊 Обзор рынка"
cards:
  - type: tile
    entity: sensor.crypto_inspect_fear_greed
    name: "Fear & Greed"
    icon: mdi:emoticon-neutral
    color: >
      {% set val = states('sensor.crypto_inspect_fear_greed') | int(50) %}
      {% if val <= 25 %}red
      {% elif val <= 45 %}orange
      {% elif val <= 55 %}grey
      {% elif val <= 75 %}light-green
      {% else %}green{% endif %}
  - type: tile
    entity: sensor.crypto_inspect_btc_dominance
    name: "BTC Доминация"
    icon: mdi:crown
  - type: tile
    entity: sensor.crypto_inspect_altseason_status
    name: "Альтсезон"
    icon: mdi:rocket-launch
  - type: tile
    entity: sensor.crypto_inspect_volatility_status
    name: "Волатильность"
    icon: mdi:chart-bell-curve
  - type: markdown
    content: |
      ### 📈 Сводка рынка
      | Метрика | Значение |
      |---------|----------|
      | **F&G Index** | {{ states('sensor.crypto_inspect_fear_greed') | default(50) }}/100 |
      | **BTC Доминация** | {{ states('sensor.crypto_inspect_btc_dominance') | default('N/A') }}% |
      | **Волатильность** | {{ states('sensor.crypto_inspect_volatility_status') | default('N/A') }} |
      | **Корреляция** | {{ states('sensor.crypto_inspect_correlation_status') | default('N/A') }} |
```

### Цены криптовалют (таблица)

```yaml
type: markdown
content: |
  ### 💵 Топ монеты
  | Монета | Цена | 24h |
  |--------|-----:|----:|
  | **₿ BTC** | ${{ state_attr('sensor.crypto_inspect_prices', 'BTC/USDT') | default(0) }} | {{ state_attr('sensor.crypto_inspect_changes_24h', 'BTC/USDT') | default(0) }}% |
  | **Ξ ETH** | ${{ state_attr('sensor.crypto_inspect_prices', 'ETH/USDT') | default(0) }} | {{ state_attr('sensor.crypto_inspect_changes_24h', 'ETH/USDT') | default(0) }}% |
  | **◎ SOL** | ${{ state_attr('sensor.crypto_inspect_prices', 'SOL/USDT') | default(0) }} | {{ state_attr('sensor.crypto_inspect_changes_24h', 'SOL/USDT') | default(0) }}% |
```

### Деривативы (Funding & OI)

```yaml
type: grid
title: "📊 Деривативы"
cards:
  - type: tile
    entity: sensor.crypto_inspect_derivatives
    name: "Деривативы"
    icon: mdi:chart-timeline-variant-shimmer
  - type: markdown
    content: |
      ### 📈 Funding & Sentiment
      | Метрика | Значение |
      |---------|----------|
      | **Funding Rate** | {{ state_attr('sensor.crypto_inspect_derivatives', 'btc_funding') | default('N/A') }}% |
      | **BTC OI** | {{ state_attr('sensor.crypto_inspect_derivatives', 'btc_oi') | default('N/A') }} BTC |
      | **Long/Short** | {{ state_attr('sensor.crypto_inspect_derivatives', 'btc_long_pct') | default(50) }}% / {{ state_attr('sensor.crypto_inspect_derivatives', 'btc_short_pct') | default(50) }}% |

      **Сигнал:** {{ state_attr('sensor.crypto_inspect_derivatives', 'signal') | default('⚪ N/A') }}
```

### Графики истории (90 дней)

```yaml
type: history-graph
title: "BTC / ETH (USD)"
hours_to_show: 2160
entities:
  - entity: sensor.crypto_history_btc_usd
    name: "BTC"
  - entity: sensor.crypto_history_eth_usd
    name: "ETH"
```

```yaml
type: history-graph
title: "Fear & Greed / BTC Dominance"
hours_to_show: 2160
entities:
  - entity: sensor.crypto_history_fear_greed
    name: "Fear & Greed"
  - entity: sensor.crypto_history_btc_dominance
    name: "BTC Dom %"
```

```yaml
type: history-graph
title: "RSI (BTC / ETH)"
hours_to_show: 720
entities:
  - entity: sensor.crypto_history_btc_rsi
    name: "BTC RSI"
  - entity: sensor.crypto_history_eth_rsi
    name: "ETH RSI"
```

### Статистика BTC

```yaml
type: statistics-graph
title: "BTC USD (месяц)"
entities:
  - sensor.crypto_history_btc_usd
days_to_show: 30
stat_types:
  - mean
  - min
  - max
```

### Алерты и сигналы

```yaml
type: grid
title: "🚨 Алерты"
cards:
  - type: tile
    entity: binary_sensor.crypto_strong_buy_signal
    name: "Strong Buy"
    icon: mdi:arrow-up-bold-circle
    color: green
  - type: tile
    entity: binary_sensor.crypto_strong_sell_signal
    name: "Strong Sell"
    icon: mdi:arrow-down-bold-circle
    color: red
  - type: tile
    entity: binary_sensor.crypto_fg_extreme
    name: "F&G Extreme"
    icon: mdi:alert-circle
  - type: tile
    entity: binary_sensor.crypto_halving_soon
    name: "Халвинг"
    icon: mdi:timer-sand
  - type: tile
    entity: binary_sensor.crypto_btc_fees_high
    name: "Fees High"
    icon: mdi:currency-btc
    color: orange
  - type: tile
    entity: binary_sensor.crypto_exchange_flow_alert
    name: "Exchange Flow"
    icon: mdi:bank-transfer
```

### Киты (Whales)

```yaml
type: grid
title: "🐋 Киты"
cards:
  - type: tile
    entity: sensor.crypto_inspect_whale_alerts_24h
    name: "Whale Activity"
    icon: mdi:whale
  - type: markdown
    content: |
      ### 🐋 Whale Tracking
      | Параметр | Значение |
      |----------|----------|
      | **Алертов 24ч** | {{ states('sensor.crypto_inspect_whale_alerts_24h') }} |
      | **Нетто-поток** | {{ states('sensor.crypto_inspect_whale_net_flow') }} |
      | **Последний** | {{ states('sensor.crypto_inspect_whale_last_alert') }} |
```

### DCA Калькулятор (с вводом)

```yaml
type: grid
title: "💵 DCA Калькулятор"
cards:
  - type: tile
    entity: sensor.crypto_inspect_dca_signal
    name: "Сигнал DCA"
    icon: mdi:cash-plus
    color: >
      {% set signal = states('sensor.crypto_inspect_dca_signal') | default('') %}
      {% if '🟢' in signal %}green
      {% elif '🔴' in signal %}red
      {% elif '🟡' in signal %}orange
      {% else %}grey{% endif %}
  - type: tile
    entity: binary_sensor.crypto_dca_good_time
    name: "Хорошее время"
    icon: mdi:thumb-up
    color: green
  - type: tile
    entity: input_number.crypto_dca_weekly_amount
    name: "💵 Базовая сумма"
    icon: mdi:cash
    features:
      - type: numeric-input
        mode: box
  - type: markdown
    content: |
      ### 💰 DCA Рекомендация
      | Параметр | Значение |
      |----------|----------|
      | **F&G Index** | {{ state_attr('sensor.crypto_inspect_dca_signal', 'fear_greed') | default('N/A') }} |
      | **Множитель** | x{{ state_attr('sensor.crypto_inspect_dca_signal', 'multiplier') | default(1.0) }} |
      | **Рекомендуемая** | €{{ state_attr('sensor.crypto_inspect_dca_signal', 'recommended') | default(100) }} |

      **Распределение:**
      | Монета | Сумма |
      |--------|------:|
      | **BTC** | €{{ state_attr('sensor.crypto_inspect_dca_signal', 'alloc_btc') | default(0) }} |
      | **ETH** | €{{ state_attr('sensor.crypto_inspect_dca_signal', 'alloc_eth') | default(0) }} |
      | **Alts** | €{{ state_attr('sensor.crypto_inspect_dca_signal', 'alloc_alts') | default(0) }} |

      *{{ state_attr('sensor.crypto_inspect_dca_signal', 'reason') | default('') }}*

      📅 След. DCA: {{ state_attr('sensor.crypto_inspect_dca_signal', 'next_dca') | default('N/A') }}
```

---

### Традиционные финансы (Dashboard)

#### Металлы

```yaml
type: glance
title: "🥇 Металлы"
entities:
  - entity: sensor.crypto_inspect_gold_price
    name: "Золото"
    icon: mdi:gold
  - entity: sensor.crypto_inspect_silver_price
    name: "Серебро"
    icon: mdi:circle-outline
  - entity: sensor.crypto_inspect_platinum_price
    name: "Платина"
    icon: mdi:diamond-stone
```

#### Индексы

```yaml
type: entities
title: "📈 Индексы"
entities:
  - entity: sensor.crypto_inspect_sp500_price
    name: "S&P 500"
    icon: mdi:chart-line
  - entity: sensor.crypto_inspect_nasdaq_price
    name: "NASDAQ"
    icon: mdi:chart-areaspline
  - entity: sensor.crypto_inspect_dji_price
    name: "Dow Jones"
    icon: mdi:chart-bar
  - entity: sensor.crypto_inspect_dax_price
    name: "DAX"
    icon: mdi:chart-timeline-variant
```

#### Форекс

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

#### Сырьё (нефть, газ)

```yaml
type: entities
title: "🛢️ Сырьё"
entities:
  - entity: sensor.crypto_inspect_oil_brent
    name: "Нефть Brent"
    icon: mdi:barrel
  - entity: sensor.crypto_inspect_oil_wti
    name: "Нефть WTI"
    icon: mdi:barrel
  - entity: sensor.crypto_inspect_natural_gas
    name: "Природный газ"
    icon: mdi:fire
```

#### Полная панель финансов

```yaml
type: grid
title: "💰 Финансы"
cards:
  - type: tile
    entity: sensor.crypto_inspect_gold_price
    name: "Золото"
    icon: mdi:gold
    color: amber
  - type: tile
    entity: sensor.crypto_inspect_silver_price
    name: "Серебро"
    icon: mdi:circle-outline
    color: grey
  - type: tile
    entity: sensor.crypto_inspect_sp500_price
    name: "S&P 500"
    icon: mdi:chart-line
  - type: tile
    entity: sensor.crypto_inspect_nasdaq_price
    name: "NASDAQ"
    icon: mdi:chart-areaspline
  - type: tile
    entity: sensor.crypto_inspect_eur_usd
    name: "EUR/USD"
    icon: mdi:currency-eur
  - type: tile
    entity: sensor.crypto_inspect_dxy_index
    name: "DXY"
    icon: mdi:currency-usd
  - type: tile
    entity: sensor.crypto_inspect_oil_brent
    name: "Нефть"
    icon: mdi:barrel
    color: black
```

#### Металлы с изменением

```yaml
type: markdown
content: |
  ### 🥇 Металлы
  | Актив | Цена | 24h |
  |-------|-------|-----|
  | **Золото** | ${{ states('sensor.crypto_inspect_gold_price') }} | {{ state_attr('sensor.crypto_inspect_gold_price', 'change_24h') | default(0) | round(2) }}% |
  | **Серебро** | ${{ states('sensor.crypto_inspect_silver_price') }} | {{ state_attr('sensor.crypto_inspect_silver_price', 'change_24h') | default(0) | round(2) }}% |
  | **Платина** | ${{ states('sensor.crypto_inspect_platinum_price') }} | - |
```

#### Индексы с изменением

```yaml
type: markdown
content: |
  ### 📈 Индексы
  | Индекс | Цена | 24h |
  |--------|-------|-----|
  | **S&P 500** | {{ states('sensor.crypto_inspect_sp500_price') | int }} | {{ state_attr('sensor.crypto_inspect_sp500_price', 'change_24h') | default(0) | round(2) }}% |
  | **NASDAQ** | {{ states('sensor.crypto_inspect_nasdaq_price') | int }} | {{ state_attr('sensor.crypto_inspect_nasdaq_price', 'change_24h') | default(0) | round(2) }}% |
  | **Dow Jones** | {{ states('sensor.crypto_inspect_dji_price') | int }} | {{ state_attr('sensor.crypto_inspect_dji_price', 'change_24h') | default(0) | round(2) }}% |
  | **DAX** | {{ states('sensor.crypto_inspect_dax_price') | int }} | {{ state_attr('sensor.crypto_inspect_dax_price', 'change_24h') | default(0) | round(2) }}% |
```

#### Сырьё с изменением

```yaml
type: markdown
content: |
  ### 🛢️ Сырьё
  | Актив | Цена | 24h |
  |-------|-------|-----|
  | **Brent** | ${{ states('sensor.crypto_inspect_oil_brent') }} | {{ state_attr('sensor.crypto_inspect_oil_brent', 'change_24h') | default(0) | round(2) }}% |
  | **WTI** | ${{ states('sensor.crypto_inspect_oil_wti') }} | - |
  | **Газ** | ${{ states('sensor.crypto_inspect_natural_gas') }} | - |
```

#### Форекс панель

```yaml
type: horizontal-stack
cards:
  - type: custom:mushroom-template-card
    primary: "EUR/USD"
    secondary: "{{ states('sensor.crypto_inspect_eur_usd') }}"
    icon: mdi:currency-eur
    icon_color: blue
  - type: custom:mushroom-template-card
    primary: "GBP/USD"
    secondary: "{{ states('sensor.crypto_inspect_gbp_usd') }}"
    icon: mdi:currency-gbp
    icon_color: purple
  - type: custom:mushroom-template-card
    primary: "DXY"
    secondary: "{{ states('sensor.crypto_inspect_dxy_index') }}"
    icon: mdi:currency-usd
    icon_color: green
```

#### BTC vs Золото (сравнение)

```yaml
type: markdown
content: |
  ### ₿ BTC vs 🥇 Gold
  | Актив | Цена | 24h |
  |-------|-------|-----|
  | **Bitcoin** | ${{ state_attr('sensor.crypto_inspect_prices', 'BTC/USDT') | default(0) }} | {{ state_attr('sensor.crypto_inspect_changes_24h', 'BTC/USDT') | default(0) }}% |
  | **Gold** | ${{ states('sensor.crypto_inspect_gold_price') }} | {{ state_attr('sensor.crypto_inspect_gold_price', 'change_24h') | default(0) | round(2) }}% |

  **Корреляция:** {{ states('sensor.crypto_inspect_btc_sp500_correlation') | default('N/A') }}
```

---

## Автоматизации

> 📖 **Полный список из 30+ автоматизаций смотрите в [DOCS.md](DOCS.md#автоматизации)**

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

### 💰 DCA - вход в зону покупки

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
            {% set signal = states('sensor.crypto_inspect_dca_signal') %}
            {% set amount = states('sensor.crypto_inspect_dca_result') %}
            {% if is_state('input_select.crypto_notification_language', 'Russian') %}
            Рынок в зоне покупки! Сигнал: {{ signal }}, Сумма: €{{ amount }}
            {% else %}
            Market in buy zone! Signal: {{ signal }}, Amount: €{{ amount }}
            {% endif %}
```

### 😱 Экстремальный страх (зона покупки)

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

### 🤑 Экстремальная жадность (зона риска)

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
            {% if is_state('input_select.crypto_notification_language', 'Russian') %}
            Рынок перегрет! Рассмотрите фиксацию прибыли.
            {% else %}
            Market overheated! Consider taking profits.
            {% endif %}
```

### 🐋 Whale Alert

```yaml
automation:
  - alias: "Whale Movement Alert"
    trigger:
      - platform: state
        entity_id: sensor.crypto_inspect_whale_last_alert
    condition:
      - condition: template
        value_template: "{{ trigger.to_state.state != 'unknown' }}"
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

### ⚠️ Экстремальная волатильность

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
            Волатильность {{ vol }}%! Будьте осторожны.
            {% else %}
            Volatility {{ vol }}%! Be careful.
            {% endif %}
```

### 📅 FOMC напоминание

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
            FOMC через {{ days }} дня! Ожидайте волатильность.
            {% else %}
            FOMC in {{ days }} days! Expect volatility.
            {% endif %}
```

### ⛽ Низкий Gas (время для транзакций)

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
            ETH Gas {{ gas }} Gwei. Отличное время для транзакций!
            {% else %}
            ETH Gas {{ gas }} Gwei. Great time for transactions!
            {% endif %}
```

### 🌊 Начало альтсезона

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
            {% if is_state('input_select.crypto_notification_language', 'Russian') %}
            Альтсезон начался! Время для альткоинов.
            {% else %}
            Altseason started! Time for altcoins.
            {% endif %}
```

### 💼 Bybit P&L алерт

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
            {% if is_state('input_select.crypto_notification_language', 'Russian') %}
            P&L за 24ч: +{{ pnl }}%!
            {% else %}
            P&L 24h: +{{ pnl }}%!
            {% endif %}
```

### 🚩 Множество красных флагов

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
            {{ count }} флагов! {{ flags }}
            {% else %}
            {{ count }} flags! {{ flags }}
            {% endif %}
          data:
            priority: high
```

### ☀️ Утренний отчёт

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
            {% set dca = states('sensor.crypto_inspect_dca_signal') %}
            {% set balance = states('sensor.crypto_inspect_bybit_balance') %}
            {% if is_state('input_select.crypto_notification_language', 'Russian') %}
            F&G: {{ fg }} | Волатильность: {{ vol }} | DCA: {{ dca }}
            {% if balance != 'unknown' %}Bybit: ${{ balance | int }}{% endif %}
            {% else %}
            F&G: {{ fg }} | Volatility: {{ vol }} | DCA: {{ dca }}
            {% if balance != 'unknown' %}Bybit: ${{ balance | int }}{% endif %}
            {% endif %}
```

### 📅 Еженедельное DCA напоминание

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
            {% set signal = states('sensor.crypto_inspect_dca_signal') %}
            {% set amount = states('sensor.crypto_inspect_dca_result') %}
            {% if is_state('input_select.crypto_notification_language', 'Russian') %}
            Понедельник - день DCA!
            Сигнал: {{ signal }} | Сумма: €{{ amount }}
            {% else %}
            Monday - DCA day!
            Signal: {{ signal }} | Amount: €{{ amount }}
            {% endif %}
```

---

### Дополнительные автоматизации в [DOCS.md](DOCS.md)

- 🎯 **Take Profit** - уровни фиксации прибыли
- ⚡ **Ликвидации** - предупреждения о рисках
- 💱 **Funding Rate** - экстремальный фандинг
- ⚖️ **Арбитраж** - возможности арбитража
- 🔗 **Корреляции** - декорреляция BTC/S&P500
- 🔓 **Token Unlocks** - предупреждения об анлоках
- 🟢 **Exchange Flow** - потоки на биржи
- 🥇 **Традиционные финансы** - золото, DXY, S&P500
- 📱 **Actionable уведомления** - iOS с кнопками
- 🔔 **TTS** - голосовые оповещения
- 🌙 **Вечерний обзор** - сводка за день
- 🎛️ **Смена фазы** - изменение фазы рынка

---

## API Endpoints

### Bybit

| Endpoint | Метод | Описание |
|----------|-------|----------|
| `/api/bybit/status` | GET | Статус подключения |
| `/api/bybit/balance` | GET | Баланс аккаунта |
| `/api/bybit/positions` | GET | Открытые позиции |
| `/api/bybit/pnl?period=7d` | GET | P&L за период |
| `/api/bybit/trades?limit=100` | GET | История сделок |
| `/api/bybit/export/trades` | GET | CSV экспорт сделок |
| `/api/bybit/export/pnl` | GET | CSV экспорт P&L |
| `/api/bybit/export/tax` | GET | CSV для налоговой |

### Анализ

| Endpoint | Метод | Описание |
|----------|-------|----------|
| `/api/analysis/{symbol}` | GET | Полный анализ символа |
| `/api/analysis/{symbol}/score` | GET | Торговый скор |
| `/api/market/summary` | GET | Обзор рынка |
| `/api/market/fear-greed` | GET | Fear & Greed Index |

### Инвестор

| Endpoint | Метод | Описание |
|----------|-------|----------|
| `/api/investor/status` | GET | Полный статус |
| `/api/investor/dca` | GET | DCA рекомендации |
| `/api/investor/red-flags` | GET | Красные флаги |
| `/api/investor/phase` | GET | Фаза рынка |

### Портфель

| Endpoint | Метод | Описание |
|----------|-------|----------|
| `/api/portfolio` | GET | Портфель |
| `/api/portfolio/holdings` | GET | Активы |
| `/api/portfolio/summary` | GET | Сводка |

### Сигналы

| Endpoint | Метод | Описание |
|----------|-------|----------|
| `/api/signals` | GET | Список сигналов |
| `/api/signals/stats` | GET | Статистика |
| `/api/signals/summary` | GET | Сводка |

### Свечи

| Endpoint | Метод | Описание |
|----------|-------|----------|
| `/api/candles/available` | GET | Доступные символы |
| `/api/candles/{symbol}` | GET | Данные свечей |
| `/api/candles/{symbol}/chart` | GET | Данные для графика |

---

## Troubleshooting

### Сенсоры не появляются

1. Перезапустите add-on
2. Проверьте логи: `Settings → Add-ons → Crypto Inspect → Logs`
3. Убедитесь что add-on работает (зеленый статус)

### Bybit не подключается

1. Проверьте API ключи в настройках
2. Убедитесь что IP разрешен в Bybit API settings
3. Проверьте `bybit_testnet: false` для реального аккаунта

### Данные не обновляются

1. Проверьте `sensor.crypto_inspect_sync_status`
2. Проверьте интернет-соединение
3. Посмотрите логи на ошибки API

---

## Поддержка

- GitHub Issues: [crypto-inspector/issues](https://github.com/Mesteriis/crypto-inspector/issues)
- Документация: [DOCS.md](DOCS.md)

---

## Лицензия

MIT License
