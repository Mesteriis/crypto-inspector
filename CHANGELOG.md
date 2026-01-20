# Changelog

## 0.2.24 - Unified Sensors Fix & Test Coverage
- **Date**: 2026-01-20
- **Fixed**: NameError in `unified_sensors.py` - `CryptoSensorsManager` replaced with `HAIntegrationManager`.
- **Tests**: Added 100% test coverage for `unified_sensors.py` (39 tests).
- **Policy**: Added `unified_sensors.py` to critical HA files requiring 100% coverage.

## 0.2.23 - HA Init Graceful Degradation
- **Date**: 2026-01-20
- **Fixed**: Removed input_helpers creation via REST API (not supported by HA).
- **Fixed**: Removed blueprint file copying (read-only filesystem in add-on).
- **Logging**: Changed all HA init warnings to DEBUG level.
- **Note**: Input helpers and blueprints must be created manually via HA UI.

## 0.2.22 - HA Automation Fix
- **Date**: 2026-01-20
- **Fixed**: Removed automation creation via REST API (not supported by HA).
- **Note**: Automations should be created manually via UI: Settings → Automations → Create from Blueprint → Crypto Inspect.

## 0.2.21 - Logging Improvements
- **Date**: 2026-01-20
- **Logging**: Changed candlestick fetch operations from INFO to DEBUG level to reduce log noise.
- **Fixed**: Resolved "Task exception was never retrieved" asyncio warnings in fetcher.
- **Fixed**: Changed expected API 404 errors (derivatives) from ERROR to DEBUG.
- **Logging**: Set httpx, httpcore, apscheduler loggers to WARNING level.

## 0.2.20 - HA Connection Retry
- **Date**: 2026-01-20
- **Feature**: Added HA connection retry with graceful fallback to standalone mode.

## 0.2.19 - Python Environment Fix
- **Date**: 2026-01-20
- **Fixed**: Use system-wide Python install, lower requirement to Python 3.11.
- **Fixed**: Install dependencies system-wide instead of venv.

## 0.2.18 - Docker Build Fixes
- **Date**: 2026-01-20
- **Fixed**: Use venv python explicitly in run script.
- **Fixed**: Add python3 to runtime image, fix import paths.
- **Fixed**: Add uv.lock to repository for Docker builds.

## 0.2.17 - Documentation & Maintenance
- **Date**: 2026-01-20
- **Documentation**: Comprehensive README.md (1900+ lines) and DOCS.md (2000+ lines).
- **Features**: 30+ automation blueprints, Lovelace card examples, MCP Server guide.
- **Sensors**: Refactored to Supervisor REST API (removed MQTT dependency).
- **Architecture**: Consolidated all configurations into `pyproject.toml`.

## 0.2.16 - Enhanced Dashboard & Localization
- **Date**: 2026-01-20
- **Sensors**: Complete bilingual localization (RU/EN) for all Home Assistant sensors.
- **Configuration**: Curated default list of 10 coins (Majors, L1, AI infrastructure).
- **UI**: Enhanced sensor dashboard coverage and improved documentation.

## 0.2.2 - Standalone Support & Infrastructure
- **Date**: 2026-01-18
- **Docker**: Added standalone Dockerfile support for non-HA environments.
- **Testing**: Massive test suite expansion (added 325 tests), increasing coverage to 45%.
- **Infrastructure**: Migrated to s6-overlay v3 for better process management.
- **CI/CD**: Improved release workflows for both standalone and HA Add-on builds.
- **GitHub**: Added GitHub Pages with a card gallery for dashboard visualization.

## 0.2.1 - Bugfixes & Polish
- **Date**: 2026-01-18
- **Fixed**: Resolved `datetime.utcnow()` deprecation warnings and import issues.
- **Refactoring**: Cleaned up `PYTHONPATH` imports and improved API compatibility.
- **Assets**: Added custom icons for the application.
- **Workflows**: Initial setup of linting and formatting with Ruff.

## 0.2.0 - UX Enhancement Suite
- **Date**: 2026-01-18
- **Sensors**: 100+ sensors via Supervisor REST API with auto-discovery.
- **Modules**: Added Lazy Investor Mode, Smart Summary, and Briefing systems.
- **Analysis**: Integrated ChatGPT/Ollama, Portfolio Analytics, and On-Chain data.
- **Dashboard**: Added `crypto_master.yaml` and progressive disclosure views.
- **Architecture**: Migrated legacy `crypto_analyzer/` to modern `src/services/` structure.

## 0.1.0 - Initial Release
- **Date**: 2026-01-17
- **Core**: Multi-exchange candlestick collection (Binance, Bybit, etc.).
- **Storage**: SQLite and PostgreSQL support.
- **HA**: Initial Home Assistant Ingress integration and basic config.
