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
    from core.scheduler.jobs import hello_world_job

    # Hello World test job - runs every 5 minutes at :00, :05, :10, etc.
    sched.add_job(
        hello_world_job,
        trigger=CronTrigger(minute="*/5"),  # Every 5 minutes, aligned to clock
        id="hello_world_job",
        name="Hello World Test Job",
        replace_existing=True,
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
