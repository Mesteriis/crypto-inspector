# Crypto Inspect - Sensor Usage Examples

This document provides practical examples for using all available sensors in Home Assistant dashboards, automations, and templates.

## 📊 Dictionary-Based Sensors (Multi-Coin Data)

These sensors return JSON dictionaries with coin symbols as keys.

### Prices Sensor
```yaml
# Get BTC price
{% set prices = states('sensor.crypto_inspect_prices') | from_json %}
Current BTC Price: ${{ '{:,.2f}'.format(prices.get('BTC/USDT', 0) | float) }}

# Get multiple coin prices
BTC: ${{ '{:,.0f}'.format(prices.get('BTC/USDT', 0) | float) }}
ETH: ${{ '{:,.0f}'.format(prices.get('ETH/USDT', 0) | float) }}
SOL: ${{ '{:,.0f}'.format(prices.get('SOL/USDT', 0) | float) }}
```

### 24h Changes Sensor
```yaml
{% set changes = states('sensor.crypto_inspect_changes_24h') | from_json %}
24h Changes:
BTC: {{ changes.get('BTC/USDT', '0') }}%
ETH: {{ changes.get('ETH/USDT', '0') }}%
SOL: {{ changes.get('SOL/USDT', '0') }}%
```

### Technical Analysis Sensors
```yaml
# RSI Values
{% set rsi = states('sensor.crypto_inspect_ta_rsi') | from_json %}
RSI:
BTC: {{ rsi.BTC | default('N/A') }}
ETH: {{ rsi.ETH | default('N/A') }}

# MACD Signal
{% set macd = states('sensor.crypto_inspect_ta_macd_signal') | from_json %}
MACD Signal:
BTC: {{ macd.BTC | default('N/A') }}
ETH: {{ macd.ETH | default('N/A') }}

# Trend Analysis
{% set trend = states('sensor.crypto_inspect_ta_trend') | from_json %}
Trends:
BTC: {{ trend.BTC | default('N/A') }}
ETH: {{ trend.ETH | default('N/A') }}

# Support/Resistance Levels
{% set support = states('sensor.crypto_inspect_ta_support') | from_json %}
{% set resistance = states('sensor.crypto_inspect_ta_resistance') | from_json %}
Support BTC: ${{ '{:,.0f}'.format(support.BTC | default(0)) }}
Resistance BTC: ${{ '{:,.0f}'.format(resistance.BTC | default(0)) }}
```

### Multi-Timeframe Trends
```yaml
{% set mtf = states('sensor.crypto_inspect_ta_trend_mtf') | from_json %}
{% set btc = mtf.BTC | default({}) %}
BTC Multi-Timeframe:
1H: {{ btc.get('1h', 'N/A') }}
4H: {{ btc.get('4h', 'N/A') }}
1D: {{ btc.get('1d', 'N/A') }}
```

### Divergences
```yaml
{% set div = states('sensor.crypto_inspect_divergences') | from_json %}
Divergences:
BTC: {{ div.BTC | default('None') }}
ETH: {{ div.ETH | default('None') }}
```

## 🎯 Single Value Sensors

### Market Sentiment & Phases
```yaml
# Market Phase
Current Phase: {{ states('sensor.crypto_inspect_investor_phase') }}
Confidence: {{ states('sensor.crypto_inspect_calm_indicator') }}%

# Fear & Greed Index
Fear & Greed: {{ states('sensor.crypto_inspect_fear_greed') }}
Value: {{ state_attr('sensor.crypto_inspect_fear_greed', 'value') }}

# Market Tension
Risk Level: {{ states('sensor.crypto_inspect_market_tension') }}
```

### DCA Signals
```yaml
# DCA Recommendation
Action: {{ states('sensor.crypto_inspect_dca_signal') }}
Result: {{ states('sensor.crypto_inspect_dca_result') }}
Risk Score: {{ states('sensor.crypto_inspect_dca_risk_score') }}
```

### Portfolio Management
```yaml
# Portfolio Value
Total Portfolio: ${{ states('sensor.crypto_inspect_bybit_total_portfolio') | float | round(2) }}
24h P&L: {{ states('sensor.crypto_inspect_bybit_pnl_24h') }}%

# Risk Metrics
Sharpe Ratio: {{ states('sensor.crypto_inspect_portfolio_sharpe') }}
Max Drawdown: {{ states('sensor.crypto_inspect_portfolio_max_drawdown') }}%
VaR 95%: {{ states('sensor.crypto_inspect_portfolio_var_95') }}
```

### Market Indicators
```yaml
# Dominance & Altseason
BTC Dominance: {{ states('sensor.crypto_inspect_btc_dominance') }}%
Altseason Status: {{ states('sensor.crypto_inspect_altseason_status') }}

# Volatility
Volatility Status: {{ states('sensor.crypto_inspect_volatility_status') }}
30d Volatility: {{ states('sensor.crypto_inspect_volatility_30d') }}%

# Correlations
BTC/ETH Correlation: {{ states('sensor.crypto_inspect_btc_eth_correlation') }}
BTC/S&P500: {{ states('sensor.crypto_inspect_btc_sp500_correlation') }}
```

## ⚠️ Alert & Signal Sensors

### Pending Alerts
```yaml
Pending Alerts: {{ states('sensor.crypto_inspect_pending_alerts_count') }}
Critical Alerts: {{ states('sensor.crypto_inspect_pending_alerts_critical') }}
Active Alerts: {{ states('sensor.crypto_inspect_active_alerts_count') }}
```

### Trading Signals
```yaml
Today's Signals: {{ states('sensor.crypto_inspect_signals_today') }}
Win Rate: {{ states('sensor.crypto_inspect_signals_win_rate') }}%
Last Signal: {{ states('sensor.crypto_inspect_signals_last') }}
```

## 📰 Briefings & Insights

### Daily Briefings
```yaml
Morning Briefing: {{ states('sensor.crypto_inspect_morning_briefing') }}
Evening Briefing: {{ states('sensor.crypto_inspect_evening_briefing') }}
Last Sent: {{ states('sensor.crypto_inspect_briefing_last_sent') }}
```

### AI Analysis
```yaml
AI Sentiment: {{ states('sensor.crypto_inspect_investor_phase') }}
Weekly Insight: {{ states('sensor.crypto_inspect_weekly_insight') }}
Daily Summary: {{ states('sensor.crypto_inspect_dca_signal') }}
```

## 📈 Backtesting Results
```yaml
DCA ROI: {{ states('sensor.crypto_inspect_backtest_dca_roi') }}%
Smart DCA ROI: {{ states('sensor.crypto_inspect_backtest_smart_dca_roi') }}%
Lump Sum ROI: {{ states('sensor.crypto_inspect_backtest_lump_sum_roi') }}%
Best Strategy: {{ states('sensor.crypto_inspect_backtest_best_strategy') }}
```

## 💰 Exchange Data (Bybit)
```yaml
Balance: {{ states('sensor.crypto_inspect_bybit_balance') }}
Positions: {{ states('sensor.crypto_inspect_bybit_positions') }}
Earn Balance: {{ states('sensor.crypto_inspect_bybit_earn_balance') }}
Earn APY: {{ states('sensor.crypto_inspect_bybit_earn_apy') }}%
```

## 🌐 Traditional Markets
```yaml
Gold Price: {{ states('sensor.crypto_inspect_gold_price') }}
Silver Price: {{ states('sensor.crypto_inspect_silver_price') }}
S&P 500: {{ states('sensor.crypto_inspect_sp500_price') }}
NASDAQ: {{ states('sensor.crypto_inspect_nasdaq_price') }}
DXY: {{ states('sensor.crypto_inspect_dxy_index') }}
Oil (Brent): {{ states('sensor.crypto_inspect_oil_brent') }}
Natural Gas: {{ states('sensor.crypto_inspect_natural_gas') }}
EUR/USD: {{ states('sensor.crypto_inspect_eur_usd') }}
```

## 🐳 On-Chain & Derivatives
```yaml
Whale Net Flow: {{ states('sensor.crypto_inspect_whale_net_flow') }}
Exchange Flows: {{ states('sensor.crypto_inspect_exchange_netflows') }}
Liquidation Risk: {{ states('sensor.crypto_inspect_liq_risk_level') }}
Stablecoin Flow: {{ states('sensor.crypto_inspect_stablecoin_flow') }}
```

## ⚙️ System Status
```yaml
Sync Status: {{ states('sensor.crypto_inspect_sync_status') }}
Last Sync: {{ states('sensor.crypto_inspect_last_sync') }}
Total Candles: {{ states('sensor.crypto_inspect_candles_count') }}
Notification Mode: {{ states('sensor.crypto_inspect_notification_mode') }}
```

## 🎯 Practical Dashboard Examples

### Mushroom Template Card Example
```yaml
type: custom:mushroom-template-card
primary: "BTC Price"
secondary: |
  {% set prices = states('sensor.crypto_inspect_prices') | from_json %}
  ${{ '{:,.0f}'.format(prices.get('BTC/USDT', 0) | float) }}
icon: mdi:bitcoin
icon_color: orange
```

### Conditional Card Based on Market Phase
```yaml
type: conditional
conditions:
  - entity: sensor.crypto_inspect_investor_phase
    state: "Accumulation"
card:
  type: markdown
  content: "🟢 Good time to accumulate!"
```

### Risk-Based Color Coding
```yaml
type: custom:mushroom-template-card
primary: "Risk Status"
secondary: "{{ states('sensor.crypto_inspect_market_tension') }}"
icon: mdi:shield-alert
icon_color: |
  {% set risk = states('sensor.crypto_inspect_market_tension') %}
  {% if risk == 'Low' %}green
  {% elif risk == 'Medium' %}orange
  {% else %}red{% endif %}
```

### Multi-Sensor Dashboard Row
```yaml
type: horizontal-stack
cards:
  - type: custom:mushroom-entity-card
    entity: sensor.crypto_inspect_fear_greed
    name: F&G

  - type: custom:mushroom-template-card
    primary: "BTC"
    secondary: |
      {% set prices = states('sensor.crypto_inspect_prices') | from_json %}
      ${{ '{:,.0f}'.format(prices.get('BTC/USDT', 0) | float) }}

  - type: custom:mushroom-entity-card
    entity: sensor.crypto_inspect_dca_signal
    name: DCA
```

## 🔄 Automation Triggers

### Price Alert Automation
```yaml
automation:
  - alias: "Price Drop Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.crypto_inspect_prices
        attribute: "BTC/USDT"
        below: 30000
    action:
      - service: notify.mobile_app
        data:
          message: "BTC dropped below $30,000!"
```

### Market Phase Change Notification
```yaml
automation:
  - alias: "Market Phase Change"
    trigger:
      - platform: state
        entity_id: sensor.crypto_inspect_investor_phase
    action:
      - service: notify.mobile_app
        data:
          message: "Market phase changed to {{ trigger.to_state.state }}"
```

## 📊 Advanced Template Examples

### Portfolio Health Dashboard
```yaml
type: markdown
content: |
  ## Portfolio Overview

  **Total Value:** ${{ states('sensor.crypto_inspect_bybit_total_portfolio') | float | round(2) }}
  **24h Change:** {{ states('sensor.crypto_inspect_bybit_pnl_24h') }}%
  **Risk Level:** {{ states('sensor.crypto_inspect_market_tension') }}

  **DCA Signal:** {{ states('sensor.crypto_inspect_dca_signal') }}
  **Market Phase:** {{ states('sensor.crypto_inspect_investor_phase') }}

  **Fear & Greed:** {{ state_attr('sensor.crypto_inspect_fear_greed', 'value') }}/100
```

### Technical Analysis Summary
```yaml
type: markdown
content: |
  ## Technical Analysis

  {% set rsi = states('sensor.crypto_inspect_ta_rsi') | from_json %}
  {% set trend = states('sensor.crypto_inspect_ta_trend') | from_json %}
  {% set macd = states('sensor.crypto_inspect_ta_macd_signal') | from_json %}

  **BTC Analysis:**
  - RSI: {{ rsi.BTC | default('N/A') }}
  - Trend: {{ trend.BTC | default('N/A') }}
  - MACD: {{ macd.BTC | default('N/A') }}

  **ETH Analysis:**
  - RSI: {{ rsi.ETH | default('N/A') }}
  - Trend: {{ trend.ETH | default('N/A') }}
  - MACD: {{ macd.ETH | default('N/A') }}
```

---

*Last Updated: Generated from current sensor implementation*
*Total Sensors Covered: 195+*
