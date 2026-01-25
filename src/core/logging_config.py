"""
Structured logging configuration with file rotation.

Log files:
- logs/app.log - main application log
- logs/errors.log - errors only (ERROR+)
- logs/jobs.log - scheduler jobs
- logs/services.log - services (analysis, exchange, etc.)
- logs/ha.log - Home Assistant integration

Rotation: 10MB max, 7 days retention
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path

# Log directory (project root / logs)
LOG_DIR = Path(__file__).parent.parent.parent / "logs"

# Rotation settings
MAX_BYTES = 10 * 1024 * 1024  # 10 MB
BACKUP_COUNT = 7  # 7 days of backups

# Log format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FORMAT_DETAILED = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"


class LoggerFilter(logging.Filter):
    """Filter logs by logger name prefix."""

    def __init__(self, prefixes: list[str], exclude: bool = False):
        super().__init__()
        self.prefixes = prefixes
        self.exclude = exclude

    def filter(self, record: logging.LogRecord) -> bool:
        matches = any(record.name.startswith(prefix) for prefix in self.prefixes)
        return not matches if self.exclude else matches


def setup_logging(
    level: str = "INFO",
    enable_file_logging: bool = True,
    enable_console: bool = True,
) -> None:
    """
    Configure application logging with rotation.

    Args:
        level: Root log level (DEBUG, INFO, WARNING, ERROR)
        enable_file_logging: Write logs to files
        enable_console: Output logs to console
    """
    # Create logs directory
    if enable_file_logging:
        LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Clear existing handlers
    root_logger.handlers.clear()

    formatter = logging.Formatter(LOG_FORMAT)
    detailed_formatter = logging.Formatter(LOG_FORMAT_DETAILED)

    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    if not enable_file_logging:
        return

    # === Main app log ===
    app_handler = RotatingFileHandler(
        LOG_DIR / "app.log",
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    app_handler.setLevel(logging.INFO)
    app_handler.setFormatter(formatter)
    root_logger.addHandler(app_handler)

    # === Errors log (ERROR+) ===
    error_handler = RotatingFileHandler(
        LOG_DIR / "errors.log",
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(error_handler)

    # === Jobs log ===
    jobs_handler = RotatingFileHandler(
        LOG_DIR / "jobs.log",
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    jobs_handler.setLevel(logging.DEBUG)
    jobs_handler.setFormatter(formatter)
    jobs_handler.addFilter(LoggerFilter([
        "core.scheduler",
        "apscheduler",
    ]))
    root_logger.addHandler(jobs_handler)

    # === Services log (analysis, exchange, etc.) ===
    services_handler = RotatingFileHandler(
        LOG_DIR / "services.log",
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    services_handler.setLevel(logging.DEBUG)
    services_handler.setFormatter(formatter)
    services_handler.addFilter(LoggerFilter([
        "service.analysis",
        "service.exchange",
        "service.candlestick",
        "service.backfill",
        "service.portfolio",
        "service.alerts",
        "service.investor",
        "service.ml",
        "service.ai",
        "service.mcp",
    ]))
    root_logger.addHandler(services_handler)

    # === Home Assistant log ===
    ha_handler = RotatingFileHandler(
        LOG_DIR / "ha.log",
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    ha_handler.setLevel(logging.DEBUG)
    ha_handler.setFormatter(formatter)
    ha_handler.addFilter(LoggerFilter([
        "service.ha",
        "service.ha_integration",
        "service.ha_init",
    ]))
    root_logger.addHandler(ha_handler)

    # === API log ===
    api_handler = RotatingFileHandler(
        LOG_DIR / "api.log",
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    api_handler.setLevel(logging.DEBUG)
    api_handler.setFormatter(formatter)
    api_handler.addFilter(LoggerFilter([
        "api.",
        "uvicorn",
        "fastapi",
    ]))
    root_logger.addHandler(api_handler)

    # Reduce noise from external libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("yfinance").setLevel(logging.WARNING)
    logging.getLogger("NP.plotly").setLevel(logging.ERROR)

    logging.info(f"Logging configured: level={level}, dir={LOG_DIR}")


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name."""
    return logging.getLogger(name)
