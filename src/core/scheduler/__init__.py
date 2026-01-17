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
    from core.scheduler.jobs import candlestick_sync_job, market_analysis_job

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

    logger.info("Registered scheduled jobs")


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
