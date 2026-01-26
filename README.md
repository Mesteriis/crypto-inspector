# Crypto Inspect

Профессиональный криптовалютный анализатор для Home Assistant. Собирает рыночные данные, анализирует тренды, отслеживает портфель и отправляет сигналы прямо в вашу умную панель.

**Version:** 1.0.0 (Stable)

## Возможности

- **150+ сенсоров** для Home Assistant
- **AI Analysis** - ChatGPT и Ollama интеграция
- **Технический анализ** - RSI, MACD, Bollinger Bands, Confluence Score
- **Риск-менеджмент** - Sharpe/Sortino Ratio, VaR, Drawdown
- **DCA Backtesting** - сравнение стратегий (Fixed DCA, Smart DCA, Lump Sum)
- **Bybit интеграция** - баланс, позиции, P&L, экспорт для налоговой
- **MCP Server** - интеграция с AI-агентами (Claude, Gemini, OpenAI)
- **On-Chain данные** - Whale Alerts, Exchange Flow, Gas Tracker
- **Макро-события** - FOMC, CPI, NFP календарь

---

## Установка

### Вариант 1: Home Assistant Add-on (рекомендуется)

1. Добавьте репозиторий в Supervisor:
   ```
   https://github.com/Mesteriis/crypto-inspector
   ```

2. Установите add-on "Crypto Inspect"

3. Настройте параметры в UI

4. Запустите add-on

### Вариант 2: Custom Component (для HACS или ручной установки)

Custom Component позволяет использовать Crypto Inspect как нативную интеграцию Home Assistant.

#### Автоматическая установка (HACS)

1. Откройте HACS в Home Assistant
2. Перейдите в "Integrations"
3. Нажмите меню (три точки) -> "Custom repositories"
4. Добавьте: `https://github.com/Mesteriis/crypto-inspector`
5. Категория: Integration
6. Найдите "Crypto Inspect" и установите
7. Перезапустите Home Assistant

#### Ручная установка

1. Скопируйте папку `custom_components/crypto_inspect/` в `/config/custom_components/`:
   ```bash
   cd /config/custom_components/
   git clone https://github.com/Mesteriis/crypto-inspector
   cp -r crypto-inspector/custom_components/crypto_inspect .
   rm -rf crypto-inspector
   ```

2. Перезапустите Home Assistant

3. Добавьте интеграцию:
   - Settings -> Devices & Services -> Add Integration
   - Найдите "Crypto Inspect"
   - Введите URL API сервера (по умолчанию: `http://localhost:9999`)

### Вариант 3: Standalone (Docker)

```bash
git clone https://github.com/Mesteriis/crypto-inspector
cd crypto-inspector
docker-compose up -d
```

### Вариант 4: Standalone (разработка)

```bash
git clone https://github.com/Mesteriis/crypto-inspector
cd crypto-inspector
uv sync
uv run python -m src.main
```

---

## Установка Blueprints

Blueprints предоставляют готовые автоматизации для уведомлений и алертов.

### Автоматическая установка

```bash
# SSH в Home Assistant
cd /config/blueprints/automation/
mkdir -p crypto_inspect
cd crypto_inspect

# Скачать blueprints
curl -sL https://github.com/Mesteriis/crypto-inspector/archive/main.tar.gz | tar xz --strip-components=2 crypto-inspector-main/ha/blueprints/
```

### Ручная установка

1. Скопируйте файлы из `ha/blueprints/` в `/config/blueprints/automation/crypto_inspect/`

2. Перезагрузите Home Assistant

3. Создайте автоматизации:
   - Settings -> Automations -> Create Automation
   - "Use a blueprint"
   - Выберите blueprint из `crypto_inspect`

### Доступные blueprints

| Blueprint | Описание |
|-----------|----------|
| `price_alert.yaml` | Ценовые алерты |
| `fear_greed_alert.yaml` | Алерты Fear & Greed Index |
| `dca_reminder.yaml` | Напоминания о DCA |
| `technical_signal.yaml` | Технические сигналы |
| `morning_briefing.yaml` | Утренний брифинг |
| `evening_briefing.yaml` | Вечерний брифинг |
| `whale_alert.yaml` | Алерты китов |
| `risk_alert.yaml` | Риск-алерты |
| `rsi_alert.yaml` | RSI алерты |
| `gas_price_alert.yaml` | Алерты цены газа ETH |
| `market_phase_change.yaml` | Смена фазы рынка |

---

## Конфигурация

### Основные настройки

| Параметр | Описание | По умолчанию |
|----------|----------|--------------|
| `api_port` | Порт API | `9999` |
| `database_type` | Тип БД (sqlite/postgres) | `sqlite` |
| `symbols` | Торговые пары | `["BTCUSDT", "ETHUSDT"]` |
| `log_level` | Уровень логов | `info` |

### Bybit API

```yaml
bybit_api_key: !secret bybit_api_key
bybit_api_secret: !secret bybit_api_secret
bybit_testnet: false
```

### AI Анализ

```yaml
ai_enabled: true
ai_provider: openai  # или ollama
openai_api_key: !secret openai_api_key
ollama_host: "http://localhost:11434"
ollama_model: "llama3.2"
```

### MCP Server

```yaml
mcp_enabled: true
mcp_port: 9998
```

---

## Сенсоры

### Цены и объемы

| Сенсор | Описание |
|--------|----------|
| `sensor.crypto_inspect_prices` | Текущие цены (dict) |
| `sensor.crypto_inspect_changes_24h` | Изменение за 24ч (dict) |
| `sensor.crypto_inspect_volumes_24h` | Объемы (dict) |

### Рыночные индикаторы

| Сенсор | Описание |
|--------|----------|
| `sensor.crypto_inspect_fear_greed` | Fear & Greed Index (0-100) |
| `sensor.crypto_inspect_btc_dominance` | Доминация BTC (%) |
| `sensor.crypto_inspect_altseason_index` | Индекс альтсезона |
| `sensor.crypto_inspect_volatility_status` | Статус волатильности |

### Ленивый инвестор

| Сенсор | Описание |
|--------|----------|
| `sensor.crypto_inspect_do_nothing_ok` | Можно ничего не делать? |
| `sensor.crypto_inspect_investor_phase` | Фаза рынка |
| `sensor.crypto_inspect_dca_signal` | Сигнал DCA |
| `sensor.crypto_inspect_red_flags` | Красные флаги |

### Технический анализ

| Сенсор | Описание |
|--------|----------|
| `sensor.crypto_inspect_btc_rsi` | RSI (14) BTC |
| `sensor.crypto_inspect_btc_macd_signal` | MACD сигнал |
| `sensor.crypto_inspect_btc_trend` | Тренд BTC |
| `sensor.crypto_inspect_ta_confluence` | Confluence Score |

### Bybit

| Сенсор | Описание |
|--------|----------|
| `sensor.crypto_inspect_bybit_balance` | Баланс (USDT) |
| `sensor.crypto_inspect_bybit_pnl_24h` | P&L за 24ч (%) |
| `sensor.crypto_inspect_bybit_positions` | Количество позиций |

### Традиционные финансы

| Сенсор | Описание |
|--------|----------|
| `sensor.crypto_inspect_gold_price` | Золото (USD) |
| `sensor.crypto_inspect_sp500_price` | S&P 500 |
| `sensor.crypto_inspect_eur_usd` | EUR/USD |
| `sensor.crypto_inspect_dxy_index` | Индекс доллара |

> **Полный список 150+ сенсоров см. в [DOCS.md](DOCS.md)**

---

## Input Helpers

Добавьте в `configuration.yaml`:

```yaml
input_number:
  crypto_dca_weekly_amount:
    name: "DCA Weekly Amount"
    min: 10
    max: 10000
    step: 10
    initial: 100
    unit_of_measurement: "EUR"
    icon: mdi:cash

input_select:
  crypto_chart_coin:
    name: "Crypto Chart Coin"
    options: [BTC, ETH, SOL, TON]
    initial: BTC
    icon: mdi:bitcoin

  crypto_notification_language:
    name: "Notification Language"
    options: [Russian, English]
    initial: Russian
    icon: mdi:translate
```

---

## API Endpoints

| Endpoint | Описание |
|----------|----------|
| `/api/market/summary` | Обзор рынка |
| `/api/market/fear-greed` | Fear & Greed Index |
| `/api/analysis/{symbol}` | Полный анализ символа |
| `/api/investor/status` | Статус ленивого инвестора |
| `/api/investor/dca` | DCA рекомендации |
| `/api/bybit/balance` | Баланс Bybit |
| `/api/bybit/positions` | Позиции Bybit |
| `/api/candles/{symbol}` | Исторические свечи |
| `/api/candles/{symbol}/chart` | Данные для графика |

---

## MCP Server

Crypto Inspect включает MCP (Model Context Protocol) сервер для интеграции с AI-агентами.

**Порт:** 9998 (по умолчанию)

### Подключение к Claude Desktop

```json
{
  "mcpServers": {
    "crypto-inspect": {
      "command": "nc",
      "args": ["localhost", "9998"]
    }
  }
}
```

### Доступные инструменты

- `get_crypto_prices` - Текущие цены
- `get_crypto_analysis` - Технический анализ
- `get_market_summary` - Обзор рынка
- `get_fear_greed_index` - Fear & Greed Index
- `get_traditional_finance` - Традиционные рынки
- `get_whale_alerts` - Алерты китов
- `get_investor_status` - Статус ленивого инвестора
- `get_bybit_portfolio` - Портфель Bybit

---

## Примеры Lovelace

### Fear & Greed карточка

```yaml
type: custom:mushroom-template-card
primary: Fear & Greed Index
secondary: "{{ states('sensor.crypto_inspect_fear_greed') }}"
icon: mdi:emoticon-neutral
icon_color: |
  {% set val = states('sensor.crypto_inspect_fear_greed') | int(50) %}
  {% if val <= 25 %}red
  {% elif val <= 45 %}orange
  {% elif val <= 55 %}yellow
  {% elif val <= 75 %}green
  {% else %}light-green{% endif %}
```

### DCA сигнал

```yaml
type: entities
title: DCA Signal
entities:
  - entity: sensor.crypto_inspect_dca_signal
    name: Сигнал
  - entity: sensor.crypto_inspect_dca_result
    name: Сумма
  - entity: sensor.crypto_inspect_dca_risk_score
    name: Риск-скор
```

> **Больше примеров см. в [DOCS.md](DOCS.md#примеры-lovelace)**

---

## Troubleshooting

### Сенсоры не появляются

1. Перезапустите add-on
2. Проверьте логи: Settings -> Add-ons -> Crypto Inspect -> Logs
3. Убедитесь что add-on работает (зеленый статус)

### Bybit не подключается

1. Проверьте API ключи
2. Убедитесь что IP разрешен в Bybit API settings
3. `bybit_testnet: false` для реального аккаунта

### Custom Component не видит API

1. Проверьте что add-on или standalone сервер запущен
2. Убедитесь в правильности URL (`http://localhost:9999` или IP add-on)
3. Проверьте firewall/network

---

## Документация

- [DOCS.md](DOCS.md) - Полная документация
- [CHANGELOG.md](CHANGELOG.md) - История изменений

## Поддержка

- GitHub Issues: [crypto-inspector/issues](https://github.com/Mesteriis/crypto-inspector/issues)

## Лицензия

MIT License
