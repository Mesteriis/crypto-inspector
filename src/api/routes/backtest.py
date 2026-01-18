"""
Backtest API Routes.

Endpoints for DCA backtesting:
- GET /api/backtest/dca - Run DCA backtest
- GET /api/backtest/compare - Compare strategies
- GET /api/backtest/risk - Risk analysis
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/backtest", tags=["Backtesting"])

# Global service instances (set from main.py)
_backtester = None
_risk_analyzer = None


def set_backtest_services(backtester, risk_analyzer):
    """Set service instances from main app."""
    global _backtester, _risk_analyzer
    _backtester = backtester
    _risk_analyzer = risk_analyzer


@router.get("/dca")
async def backtest_dca(
    symbol: str = Query(default="BTC/USDT", description="Trading pair"),
    amount: float = Query(default=100.0, ge=10, le=10000, description="Weekly amount"),
    years: int = Query(default=5, ge=1, le=10, description="Years to backtest"),
    strategy: str = Query(default="fixed", description="Strategy: fixed, smart, lump_sum"),
) -> dict[str, Any]:
    """
    Run DCA backtest.

    Strategies:
    - fixed: Regular weekly purchases
    - smart: Fear & Greed adjusted purchases
    - lump_sum: Single purchase at start
    """
    if not _backtester:
        raise HTTPException(status_code=503, detail="Backtest service not available")

    # Get candle data (mock for now - in production, fetch from DB)
    candles = await _get_historical_candles(symbol, years)

    if not candles:
        raise HTTPException(
            status_code=404,
            detail=f"No historical data available for {symbol}",
        )

    try:
        if strategy == "fixed":
            result = await _backtester.backtest_fixed_dca(symbol, candles, amount, "weekly", years)
        elif strategy == "smart":
            result = await _backtester.backtest_smart_dca(symbol, candles, amount, years)
        elif strategy == "lump_sum":
            total = amount * 52 * years
            result = await _backtester.backtest_lump_sum(symbol, candles, total, years)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown strategy: {strategy}")

        return result.to_dict()

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Backtest failed: {e}")
        raise HTTPException(status_code=500, detail="Backtest failed")


@router.get("/compare")
async def compare_strategies(
    symbol: str = Query(default="BTC/USDT", description="Trading pair"),
    amount: float = Query(default=100.0, ge=10, le=10000, description="Weekly amount"),
    years: int = Query(default=5, ge=1, le=10, description="Years to compare"),
) -> dict[str, Any]:
    """
    Compare all DCA strategies.

    Returns comparison of Fixed DCA, Smart DCA, and Lump Sum.
    """
    if not _backtester:
        raise HTTPException(status_code=503, detail="Backtest service not available")

    candles = await _get_historical_candles(symbol, years)

    if not candles:
        raise HTTPException(
            status_code=404,
            detail=f"No historical data available for {symbol}",
        )

    try:
        return await _backtester.compare_strategies(symbol, candles, amount, years)
    except Exception as e:
        logger.error(f"Strategy comparison failed: {e}")
        raise HTTPException(status_code=500, detail="Comparison failed")


@router.get("/risk")
async def get_risk_metrics(
    portfolio_value: float = Query(default=10000.0, description="Current portfolio value"),
) -> dict[str, Any]:
    """
    Get portfolio risk metrics.

    Returns Sharpe ratio, drawdown, VaR, etc.
    """
    if not _risk_analyzer:
        raise HTTPException(status_code=503, detail="Risk service not available")

    try:
        # Generate sample portfolio history for demo
        # In production, this would come from actual portfolio tracking
        import random

        portfolio_values = [portfolio_value]
        for i in range(90):
            change = random.uniform(-0.05, 0.06)
            portfolio_values.append(portfolio_values[-1] * (1 + change))

        metrics = await _risk_analyzer.calculate_risk_metrics(
            portfolio_values=portfolio_values,
            current_value=portfolio_value,
        )

        return metrics.to_dict()

    except Exception as e:
        logger.error(f"Risk calculation failed: {e}")
        raise HTTPException(status_code=500, detail="Risk calculation failed")


@router.get("/risk/stress-test")
async def stress_test(
    portfolio_value: float = Query(default=10000.0, description="Portfolio value"),
    scenario: str = Query(default="moderate", description="Scenario: 2022_crash, black_swan, moderate, flash_crash"),
) -> dict[str, Any]:
    """
    Run stress test simulation.

    Tests portfolio against historical crash scenarios.
    """
    if not _risk_analyzer:
        raise HTTPException(status_code=503, detail="Risk service not available")

    try:
        return await _risk_analyzer.stress_test(portfolio_value, scenario)
    except Exception as e:
        logger.error(f"Stress test failed: {e}")
        raise HTTPException(status_code=500, detail="Stress test failed")


@router.get("/risk/summary")
async def get_risk_summary() -> dict[str, Any]:
    """Get risk summary with recommendations."""
    if not _risk_analyzer:
        return {
            "status": "Service not available",
            "recommendations": ["Enable risk tracking in settings"],
        }

    return _risk_analyzer.get_risk_summary()


@router.get("/sensors")
async def get_backtest_sensors() -> dict[str, Any]:
    """Get backtest data formatted for HA sensors."""
    result = {
        "backtest_dca_roi": "N/A",
        "backtest_smart_dca_roi": "N/A",
        "backtest_lump_sum_roi": "N/A",
        "backtest_best_strategy": "N/A",
    }

    if _backtester:
        cached = _backtester.get_cached_result("BTC/USDT")
        if cached:
            result["backtest_dca_roi"] = f"{cached.total_return_pct:.1f}%"

    if _risk_analyzer and _risk_analyzer.last_metrics:
        m = _risk_analyzer.last_metrics
        result["portfolio_sharpe"] = f"{m.sharpe_ratio:.2f}"
        result["portfolio_max_drawdown"] = f"{m.max_drawdown:.1f}%"
        result["risk_status"] = m.risk_status

    return result


async def _get_historical_candles(symbol: str, years: int) -> list[dict]:
    """
    Get historical candle data.

    In production, this fetches from the database.
    For demo, generates synthetic data.
    """
    import random
    from datetime import datetime, timedelta

    # Generate synthetic daily candles for demo
    candles = []
    base_price = 50000 if "BTC" in symbol else 3000

    current_price = base_price * 0.3  # Start lower in the past
    start_date = datetime.now() - timedelta(days=years * 365)

    for i in range(years * 365):
        date = start_date + timedelta(days=i)

        # Random walk with slight upward bias
        change = random.uniform(-0.03, 0.035)
        current_price *= 1 + change

        # Add some volatility spikes
        if random.random() < 0.02:
            current_price *= random.uniform(0.9, 1.15)

        high = current_price * random.uniform(1.0, 1.02)
        low = current_price * random.uniform(0.98, 1.0)

        candles.append(
            {
                "timestamp": int(date.timestamp() * 1000),
                "open": current_price * random.uniform(0.99, 1.01),
                "high": high,
                "low": low,
                "close": current_price,
                "volume": random.uniform(1000, 10000) * base_price,
            }
        )

    return candles
