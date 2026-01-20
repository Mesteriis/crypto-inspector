# Changelog

## 0.2.17 - Documentation & Maintenance

### Documentation
- Comprehensive README.md with 1900+ lines of documentation
- Full DOCS.md with 2000+ lines for Home Assistant Add-on Store
- 30+ ready-to-use automation examples with bilingual support (RU/EN)
- Lovelace card examples for all sensor categories
- MCP Server integration guide for AI agents (Claude, Gemini, OpenAI)
- TradingView and ApexCharts integration examples
- Progressive disclosure dashboards (Summary → Detailed → Power User)

### Sensors
- 100+ MQTT sensors with automatic Home Assistant discovery
- Dictionary format for multi-currency data (prices, changes, RSI, etc.)
- Traditional finance sensors (Gold, S&P500, NASDAQ, EUR/USD, Oil)
- AI prediction sensors (trends, forecasts, confidence levels)
- Smart correlation and economic calendar sensors

## 0.2.1 - Bugfixes & Improvements

### Fixed
- Fixed `TestPeriod` → `BacktestPeriod` naming in e2e test framework
- Updated sw_version references in HA integration

### Changed
- Minor code cleanup and refactoring

## 0.2.0 - UX Enhancement Suite & Sensor Refactoring

### New Features
- **100+ MQTT Sensors** with automatic Home Assistant discovery
- **Lazy Investor Mode**: "Do Nothing OK" indicator, market phases, DCA signals
- **Smart Summary System**: Market Pulse, Today's Action, Portfolio Health
- **Briefing System**: Morning/Evening briefings with bilingual support (EN/RU)
- **Goal Tracking**: Financial goals with progress tracking and ETA
- **Alert System**: Smart notifications with priority levels and digest mode
- **AI Integration**: ChatGPT and Ollama support for market analysis
- **MCP Server**: Model Context Protocol for AI agent integration
- **Portfolio Analytics**: Sharpe, Sortino, VaR, drawdown metrics
- **Technical Analysis**: RSI, MACD, Bollinger Bands, MTF trends
- **On-Chain Data**: Whale tracking, exchange flows, liquidations
- **DCA Backtesting**: Compare Fixed DCA vs Smart DCA vs Lump Sum
- **Blueprints**: 12 ready-to-use Home Assistant automations

### Dashboard System
- **crypto_master.yaml**: Comprehensive 700+ line dashboard with all sensors
- **Progressive Dashboards**: Summary → Detailed → Power User views
- **Custom Cards**: Fear & Greed gauge, RSI indicators, risk dashboard
- **TradingView Charts**: Embedded chart integration

### Architecture Improvements
- Refactored currency-specific sensors to generic dictionary format
- Migrated all components from `crypto_analyzer/` to `src/services/`
- Added 15+ API routes for all features
- Scheduled jobs with APScheduler for data refresh

### Removed
- Deleted legacy `crypto_analyzer/` folder (fully migrated to `src/`)

## 0.1.0

- Initial release
- Candlestick data collection from multiple exchanges
- Support for Binance, Coinbase, Kraken, Bybit, KuCoin, OKX
- SQLite and PostgreSQL database support
- Home Assistant Ingress integration
- Configurable exchanges, symbols, and intervals
