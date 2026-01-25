import asyncio
import logging
from typing import Any

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
async def health_check():
    return {"status": "healthy"}


@router.get("/api/debug/sensors")
async def get_all_sensor_states() -> dict[str, Any]:
    """Get all cached sensor states for debugging."""
    from service.ha import get_sensors_manager

    sensors = get_sensors_manager()
    return {
        "sensor_states": sensors._cache,
        "total": len(sensors._cache),
    }


@router.post("/api/jobs/run-all")
async def run_all_jobs() -> dict[str, Any]:
    """Run all scheduler jobs manually and return results."""
    from core.scheduler.jobs import (
        ai_analysis_job,
        altseason_job,
        arbitrage_job,
        bybit_sync_job,
        correlation_job,
        dca_job,
        divergence_job,
        exchange_flow_job,
        gas_tracker_job,
        investor_analysis_job,
        liquidation_job,
        macro_job,
        market_analysis_job,
        profit_taking_job,
        signal_history_job,
        stablecoin_job,
        traditional_backfill_job,
        traditional_finance_job,
        unlocks_job,
        volatility_job,
        whale_monitor_job,
    )

    jobs = [
        ("market_analysis", market_analysis_job),
        ("investor_analysis", investor_analysis_job),
        ("bybit_sync", bybit_sync_job),
        ("gas_tracker", gas_tracker_job),
        ("whale_monitor", whale_monitor_job),
        ("exchange_flow", exchange_flow_job),
        ("liquidation", liquidation_job),
        ("divergence", divergence_job),
        ("signal_history", signal_history_job),
        ("dca", dca_job),
        ("correlation", correlation_job),
        ("volatility", volatility_job),
        ("arbitrage", arbitrage_job),
        ("profit_taking", profit_taking_job),
        ("traditional_finance", traditional_finance_job),
        ("traditional_backfill", traditional_backfill_job),
        ("altseason", altseason_job),
        ("stablecoin", stablecoin_job),
        ("unlocks", unlocks_job),
        ("macro", macro_job),
        ("ai_analysis", ai_analysis_job),
    ]

    results = {}
    for name, job in jobs:
        try:
            logger.info(f"Running job: {name}")
            await job()
            results[name] = "OK"
        except Exception as e:
            logger.error(f"Job {name} failed: {e}")
            results[name] = f"FAILED: {str(e)[:100]}"
        # Small delay to avoid rate limiting
        await asyncio.sleep(0.5)

    return {
        "status": "completed",
        "jobs": results,
        "total": len(jobs),
        "success": sum(1 for v in results.values() if v == "OK"),
        "failed": sum(1 for v in results.values() if v.startswith("FAILED")),
    }
