"""Sensor categories auto-import.

This module imports all category modules to trigger
@register_sensor decorators for sensor registration.
"""

# Import all category modules to register sensors
from service.ha.categories import (
    ai,
    alerts,
    backtest,
    bybit,
    correlation,
    dca,
    diagnostic,
    economic,
    exchange,
    gas,
    investor,
    market,
    misc,
    ml,
    portfolio,
    price,
    risk,
    smart_summary,
    technical,
    traditional,
    volatility,
    whales,
)

__all__ = [
    "price",
    "investor",
    "market",
    "diagnostic",
    "portfolio",
    "gas",
    "whales",
    "exchange",
    "bybit",
    "dca",
    "correlation",
    "volatility",
    "traditional",
    "technical",
    "ai",
    "economic",
    "alerts",
    "smart_summary",
    "risk",
    "backtest",
    "misc",
    "ml",
]
