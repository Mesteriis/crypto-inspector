"""E2E testing framework components."""

from tests.e2e.framework.backtest_runner import BacktestConfig, BacktestRunner
from tests.e2e.framework.data_loader import HistoricalDataLoader
from tests.e2e.framework.signal_validator import SignalValidator, ValidationResult

__all__ = [
    "BacktestRunner",
    "BacktestConfig",
    "HistoricalDataLoader",
    "SignalValidator",
    "ValidationResult",
]
