#!/usr/bin/env python
"""Run all scheduler jobs and verify sensor population."""

import asyncio
import logging
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def run_all_jobs():
    """Run all jobs sequentially and check results."""
    from core.scheduler.jobs import (
        currency_list_monitor_job,
        investor_analysis_job,
        divergence_job,
        gas_tracker_job,
        altseason_job,
        stablecoin_job,
        correlation_job,
        volatility_job,
        whale_monitor_job,
        exchange_flow_job,
        liquidation_job,
        dca_job,
        profit_taking_job,
        arbitrage_job,
        unlocks_job,
        macro_job,
        portfolio_job,
        bybit_sync_job,
        traditional_finance_job,
        market_analysis_job,
        ml_prediction_job,
        backtest_job,
        signal_history_job,
        briefing_job,
    )
    
    jobs = [
        ("currency_list_monitor_job", currency_list_monitor_job),
        ("investor_analysis_job", investor_analysis_job),
        ("market_analysis_job", market_analysis_job),
        ("divergence_job", divergence_job),
        ("gas_tracker_job", gas_tracker_job),
        ("altseason_job", altseason_job),
        ("stablecoin_job", stablecoin_job),
        ("correlation_job", correlation_job),
        ("volatility_job", volatility_job),
        ("whale_monitor_job", whale_monitor_job),
        ("exchange_flow_job", exchange_flow_job),
        ("liquidation_job", liquidation_job),
        ("dca_job", dca_job),
        ("profit_taking_job", profit_taking_job),
        ("arbitrage_job", arbitrage_job),
        ("unlocks_job", unlocks_job),
        ("macro_job", macro_job),
        ("portfolio_job", portfolio_job),
        ("bybit_sync_job", bybit_sync_job),
        ("traditional_finance_job", traditional_finance_job),
        ("ml_prediction_job", ml_prediction_job),
        ("backtest_job", backtest_job),
        ("signal_history_job", signal_history_job),
        ("briefing_job", briefing_job),
    ]
    
    success = 0
    failed = 0
    
    for name, job in jobs:
        logger.info(f"\n{'='*60}")
        logger.info(f"Running: {name}")
        logger.info('='*60)
        try:
            await job()
            success += 1
            logger.info(f"✓ {name} completed")
        except Exception as e:
            failed += 1
            logger.error(f"✗ {name} FAILED: {e}")
    
    logger.info(f"\n{'='*60}")
    logger.info(f"SUMMARY: {success} success, {failed} failed")
    logger.info('='*60)
    
    # Query sensor states
    await check_sensors()


async def check_sensors():
    """Check sensor states in database."""
    from models.session import async_session_maker
    from sqlalchemy import text
    
    async with async_session_maker() as session:
        # Non-empty sensors
        result = await session.execute(text("""
            SELECT COUNT(*) 
            FROM sensor_states 
            WHERE value NOT IN ('{}', '[]', '—', '0', '$0', 'null', '')
        """))
        non_empty = result.scalar()
        
        # Total sensors
        result = await session.execute(text("SELECT COUNT(*) FROM sensor_states"))
        total = result.scalar()
        
        # Empty sensors
        result = await session.execute(text("""
            SELECT unique_id, name, value, updated_at 
            FROM sensor_states 
            WHERE value IN ('{}', '[]', '—', '0', '$0', 'null', '')
            ORDER BY name
        """))
        empty_sensors = result.fetchall()
        
        logger.info(f"\n{'='*60}")
        logger.info(f"SENSOR STATUS: {non_empty}/{total} populated")
        logger.info(f"Empty sensors: {len(empty_sensors)}")
        logger.info('='*60)
        
        if empty_sensors:
            logger.info("\nEmpty sensors:")
            for s in empty_sensors[:30]:  # First 30
                logger.info(f"  - {s.name}: '{s.value}'")
            if len(empty_sensors) > 30:
                logger.info(f"  ... and {len(empty_sensors) - 30} more")


if __name__ == "__main__":
    asyncio.run(run_all_jobs())
