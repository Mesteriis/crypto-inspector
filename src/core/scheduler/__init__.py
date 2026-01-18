"""
APScheduler integration for FastAPI.

This module provides scheduler initialization and lifecycle management
integrated with FastAPI's lifespan events.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    """Get the global scheduler instance."""
    global scheduler
    if scheduler is None:
        scheduler = AsyncIOScheduler()
    return scheduler


def setup_scheduler() -> AsyncIOScheduler:
    """
    Initialize and configure the scheduler.

    Returns:
        Configured AsyncIOScheduler instance.
    """
    sched = get_scheduler()

    # Register all scheduled jobs
    _register_jobs(sched)

    return sched


def _register_jobs(sched: AsyncIOScheduler) -> None:
    """
    Register all scheduled jobs.

    Args:
        sched: The scheduler instance to register jobs with.
    """
    from core.scheduler.jobs import (
        altseason_job,
        arbitrage_job,
        bybit_sync_job,
        candlestick_sync_job,
        correlation_job,
        dca_job,
        divergence_job,
        exchange_flow_job,
        gas_tracker_job,
        investor_analysis_job,
        liquidation_job,
        macro_job,
        market_analysis_job,
        portfolio_job,
        price_alerts_job,
        profit_taking_job,
        signal_history_job,
        stablecoin_job,
        traditional_finance_job,
        unlocks_job,
        volatility_job,
        whale_monitor_job,
    )

    # Candlestick sync job - runs every 5 minutes at :00, :05, :10, etc.
    sched.add_job(
        candlestick_sync_job,
        trigger=CronTrigger(minute="*/5"),
        id="candlestick_sync_job",
        name="Candlestick Sync Job",
        replace_existing=True,
        max_instances=1,  # Prevent overlapping runs
        coalesce=True,  # Combine missed runs into one
    )

    # Market analysis job - runs every 4 hours
    sched.add_job(
        market_analysis_job,
        trigger=CronTrigger(hour="*/4", minute=5),  # Run at :05 past the hour
        id="market_analysis_job",
        name="Market Analysis Job",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    # Investor analysis job - runs every hour for lazy investor sensors
    sched.add_job(
        investor_analysis_job,
        trigger=CronTrigger(minute=10),  # Run at :10 past every hour
        id="investor_analysis_job",
        name="Investor Analysis Job",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    # Altseason Index job - runs every 6 hours
    sched.add_job(
        altseason_job,
        trigger=CronTrigger(hour="*/6", minute=15),
        id="altseason_job",
        name="Altseason Index Job",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    # Stablecoin Flow job - runs every 4 hours
    sched.add_job(
        stablecoin_job,
        trigger=CronTrigger(hour="*/4", minute=20),
        id="stablecoin_job",
        name="Stablecoin Flow Job",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    # Gas Tracker job - runs every 5 minutes
    sched.add_job(
        gas_tracker_job,
        trigger=CronTrigger(minute="*/5"),
        id="gas_tracker_job",
        name="Gas Tracker Job",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    # Whale Monitor job - runs every 15 minutes
    sched.add_job(
        whale_monitor_job,
        trigger=CronTrigger(minute="*/15"),
        id="whale_monitor_job",
        name="Whale Monitor Job",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    # Exchange Flow job - runs every 4 hours
    sched.add_job(
        exchange_flow_job,
        trigger=CronTrigger(hour="*/4", minute=25),
        id="exchange_flow_job",
        name="Exchange Flow Job",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    # Liquidation Levels job - runs every hour
    sched.add_job(
        liquidation_job,
        trigger=CronTrigger(minute=30),
        id="liquidation_job",
        name="Liquidation Levels Job",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    # Portfolio Tracker job - runs every 5 minutes
    sched.add_job(
        portfolio_job,
        trigger=CronTrigger(minute="*/5"),
        id="portfolio_job",
        name="Portfolio Tracker Job",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    # Divergence Detection job - runs every hour
    sched.add_job(
        divergence_job,
        trigger=CronTrigger(minute=35),
        id="divergence_job",
        name="Divergence Detection Job",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    # Signal History job - runs every hour
    sched.add_job(
        signal_history_job,
        trigger=CronTrigger(minute=40),
        id="signal_history_job",
        name="Signal History Job",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    # Price Alerts job - runs every minute
    sched.add_job(
        price_alerts_job,
        trigger=CronTrigger(minute="*"),
        id="price_alerts_job",
        name="Price Alerts Job",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    # === New Jobs: Bybit + Analysis ===

    # Bybit sync job - runs every 5 minutes
    sched.add_job(
        bybit_sync_job,
        trigger=CronTrigger(minute="*/5"),
        id="bybit_sync_job",
        name="Bybit Sync Job",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    # DCA Calculator job - runs every hour
    sched.add_job(
        dca_job,
        trigger=CronTrigger(minute=45),
        id="dca_job",
        name="DCA Calculator Job",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    # Correlation Tracker job - runs every 4 hours
    sched.add_job(
        correlation_job,
        trigger=CronTrigger(hour="*/4", minute=50),
        id="correlation_job",
        name="Correlation Tracker Job",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    # Volatility Index job - runs every hour
    sched.add_job(
        volatility_job,
        trigger=CronTrigger(minute=55),
        id="volatility_job",
        name="Volatility Index Job",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    # Token Unlocks job - runs every 6 hours
    sched.add_job(
        unlocks_job,
        trigger=CronTrigger(hour="*/6", minute=0),
        id="unlocks_job",
        name="Token Unlocks Job",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    # Macro Calendar job - runs every 12 hours
    sched.add_job(
        macro_job,
        trigger=CronTrigger(hour="0,12", minute=5),
        id="macro_job",
        name="Macro Calendar Job",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    # Arbitrage Scanner job - runs every 2 minutes
    sched.add_job(
        arbitrage_job,
        trigger=CronTrigger(minute="*/2"),
        id="arbitrage_job",
        name="Arbitrage Scanner Job",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    # Profit Taking Advisor job - runs every hour
    sched.add_job(
        profit_taking_job,
        trigger=CronTrigger(minute=15),
        id="profit_taking_job",
        name="Profit Taking Advisor Job",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    # Traditional Finance job - runs every 15 minutes
    sched.add_job(
        traditional_finance_job,
        trigger=CronTrigger(minute="*/15"),
        id="traditional_finance_job",
        name="Traditional Finance Job",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    logger.info("Registered scheduled jobs (23 total)")


@asynccontextmanager
async def scheduler_lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """
    FastAPI lifespan context manager for scheduler.

    Starts the scheduler on application startup and shuts it down
    on application shutdown.

    Args:
        app: FastAPI application instance.

    Yields:
        None
    """
    sched = setup_scheduler()

    # Start the scheduler
    sched.start()
    logger.info("Scheduler started")

    # Log all registered jobs
    jobs = sched.get_jobs()
    for job in jobs:
        logger.info(f"  Job registered: {job.name} (id={job.id}, trigger={job.trigger})")

    yield

    # Shutdown the scheduler
    sched.shutdown(wait=False)
    logger.info("Scheduler shutdown")
