# Changelog

## 1.0.0 - Stable Release
- **Date**: 2026-01-26
- **Status**: Stable (removed experimental flag)

### Highlights
- **150+ sensors** for Home Assistant covering crypto, traditional finance, and on-chain data
- **AI Analysis** with ChatGPT and Ollama integration
- **Technical Analysis** with RSI, MACD, Bollinger Bands, and confluence scoring
- **Risk Management** with Sharpe/Sortino ratios, VaR, and drawdown tracking
- **DCA Backtesting** comparing Fixed DCA, Smart DCA, and Lump Sum strategies
- **MCP Server** for AI agent integration (Claude, Gemini, OpenAI)
- **Bybit Integration** for portfolio tracking and P&L analysis
- **Lazy Investor Mode** with market phase detection and red flag alerts

### Features
- Market indicators: Fear & Greed, BTC Dominance, Altseason Index, Volatility
- Trading tools: DCA Calculator, Take Profit Advisor, Arbitrage Scanner
- On-chain data: Whale Alerts, Exchange Flow, Gas Tracker
- Macro events: FOMC, CPI, NFP calendar with risk assessment
- Traditional finance: Gold, Silver, S&P 500, NASDAQ, Forex, Oil

### Technical
- SQLite and PostgreSQL database support
- Docker and Home Assistant Add-on deployment
- Standalone mode for development
- Comprehensive API with 50+ endpoints

---

## 0.2.x - Development Phase

### 0.2.28 - Sensor Validation Fixes (2026-01-21)
- Fixed: `red_flags` now sends int value (CountSensor), emoji moved to attributes.
- Fixed: `greed_level` sends `greed_score` (0-100) instead of text (PercentSensor).
- Fixed: Gas sensor names corrected to `eth_gas_*` prefix.

### 0.2.27 - Fast Startup Fix (2026-01-21)
- Fixed: Removed heavy external API calls from startup to prevent slow boot.
- Changed: Startup now only sets placeholder values, data comes from scheduled jobs.

### 0.2.26 - Sensor Initialization (2026-01-20)
- Fixed: Divergence job now uses correct `DivergenceDetector.detect()` API.
- Feature: Run startup jobs immediately to populate sensors.
- Feature: Set informative initial values for disabled features.

### 0.2.25 - Sensor Registration Fix (2026-01-20)
- Fixed: Changed sensor registration to use `HAIntegrationManager.register_sensors()`.
- Result: All 152 sensors from SensorRegistry now registered (was 10).

### 0.2.24 - Test Coverage (2026-01-20)
- Fixed: NameError in `unified_sensors.py`.
- Tests: Added 100% test coverage for `unified_sensors.py` (39 tests).

### 0.2.23 - HA Init Graceful Degradation (2026-01-20)
- Fixed: Removed unsupported REST API calls for input_helpers and blueprints.
- Note: Input helpers and blueprints must be created manually via HA UI.

### 0.2.22 - HA Automation Fix (2026-01-20)
- Fixed: Removed automation creation via REST API (not supported by HA).

### 0.2.21 - Logging Improvements (2026-01-20)
- Logging: Changed candlestick fetch from INFO to DEBUG to reduce noise.
- Fixed: Resolved asyncio "Task exception was never retrieved" warnings.

### 0.2.20 - HA Connection Retry (2026-01-20)
- Feature: Added HA connection retry with graceful fallback to standalone mode.

### 0.2.17 - Documentation (2026-01-20)
- Documentation: Comprehensive README.md (1900+ lines) and DOCS.md (2000+ lines).
- Features: 30+ automation blueprints, Lovelace card examples, MCP Server guide.

### 0.2.16 - Localization (2026-01-20)
- Sensors: Complete bilingual localization (RU/EN) for all Home Assistant sensors.
- Configuration: Curated default list of 10 coins.

### 0.2.2 - Standalone Support (2026-01-18)
- Docker: Added standalone Dockerfile support for non-HA environments.
- Testing: Test suite expansion (325 tests), 45% coverage.
- Infrastructure: Migrated to s6-overlay v3.

### 0.2.0 - UX Enhancement Suite (2026-01-18)
- Sensors: 100+ sensors via Supervisor REST API with auto-discovery.
- Modules: Added Lazy Investor Mode, Smart Summary, and Briefing systems.
- Analysis: Integrated ChatGPT/Ollama, Portfolio Analytics, On-Chain data.

---

## 0.1.0 - Initial Release (2026-01-17)
- Core: Multi-exchange candlestick collection (Binance, Bybit, etc.).
- Storage: SQLite and PostgreSQL support.
- HA: Initial Home Assistant Ingress integration.
