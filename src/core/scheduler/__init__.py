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
        currency_list_monitor_job,
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

    # Currency List Monitor job - runs every 10 minutes
    sched.add_job(
        currency_list_monitor_job,
        trigger=CronTrigger(minute="*/10"),
        id="currency_list_monitor_job",
        name="Currency List Monitor Job",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    logger.info("Registered scheduled jobs (24 total)")


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

    # Run initial jobs to populate sensors (avoid 'unknown' state)
    await _run_startup_jobs()

    yield

    # Shutdown the scheduler
    sched.shutdown(wait=False)
    logger.info("Scheduler shutdown")


async def _run_startup_jobs() -> None:
    """
    Run critical jobs at startup to populate sensors.

    This prevents sensors from showing 'unknown' until scheduled run.
    First sets initial values based on feature flags, then runs enabled jobs.
    """
    import asyncio

    from core.config import settings

    logger.info("Initializing sensor values based on feature flags...")

    # Set initial values for all sensors first
    await _set_initial_sensor_values()

    logger.info("Running startup jobs for enabled features...")

    # Only run jobs for features that are enabled
    startup_jobs = []

    # Gas tracker - always enabled (no feature flag)
    from core.scheduler.jobs import gas_tracker_job

    startup_jobs.append(("gas_tracker", gas_tracker_job))

    # Investor analysis - always enabled
    from core.scheduler.jobs import investor_analysis_job

    startup_jobs.append(("investor_analysis", investor_analysis_job))

    # Volatility - always enabled
    from core.scheduler.jobs import volatility_job

    startup_jobs.append(("volatility", volatility_job))

    # Profit taking - always enabled
    from core.scheduler.jobs import profit_taking_job

    startup_jobs.append(("profit_taking", profit_taking_job))

    # Unlocks - always enabled
    from core.scheduler.jobs import unlocks_job

    startup_jobs.append(("unlocks", unlocks_job))

    # Run jobs sequentially with timeout
    for name, job_func in startup_jobs:
        try:
            await asyncio.wait_for(job_func(), timeout=30.0)
            logger.debug(f"Startup job '{name}' completed")
        except asyncio.TimeoutError:
            logger.warning(f"Startup job '{name}' timed out")
        except Exception as e:
            logger.warning(f"Startup job '{name}' failed: {e}")

    logger.info("Startup jobs completed")


async def _set_initial_sensor_values() -> None:
    """
    Set initial sensor values based on feature flags.

    This sets informative values for disabled features instead of 'unknown'.
    """
    from core.config import settings
    from service.ha import get_sensors_manager

    sensors = get_sensors_manager()
    disabled_text = "Disabled"
    disabled_dict = {}

    # AI sensors - depends on AI_ENABLED
    if not settings.AI_ENABLED:
        ai_sensors = [
            ("ai_daily_summary", "AI disabled"),
            ("ai_market_sentiment", "AI disabled"),
            ("ai_recommendation", "AI disabled"),
            ("ai_last_analysis", "N/A"),
            ("ai_provider", "None"),
            ("ai_trends", disabled_dict),
            ("ai_confidences", disabled_dict),
            ("ai_price_forecasts_24h", disabled_dict),
        ]
        for sensor_id, value in ai_sensors:
            try:
                await sensors.publish_sensor(sensor_id, value, {"status": "disabled"})
            except Exception:
                pass
        logger.debug("AI sensors set to disabled state")

    # Bybit sensors - depends on credentials
    if not settings.has_bybit_credentials():
        bybit_sensors = [
            ("bybit_balance", 0),
            ("bybit_pnl_24h", 0),
            ("bybit_pnl_7d", 0),
            ("bybit_positions", 0),
            ("bybit_unrealized_pnl", 0),
            ("bybit_earn_balance", 0),
            ("bybit_earn_positions", 0),
            ("bybit_earn_apy", 0),
            ("bybit_total_portfolio", 0),
        ]
        for sensor_id, value in bybit_sensors:
            try:
                await sensors.publish_sensor(sensor_id, value, {"status": "not_configured"})
            except Exception:
                pass
        logger.debug("Bybit sensors set to not configured state")

    # Goal sensors - depends on GOAL_ENABLED
    if not settings.GOAL_ENABLED:
        goal_sensors = [
            ("goal_progress", 0),
            ("goal_status", "Goal disabled"),
            ("goal_target", 0),
            ("goal_current", 0),
            ("goal_remaining", 0),
        ]
        for sensor_id, value in goal_sensors:
            try:
                await sensors.publish_sensor(sensor_id, value, {"status": "disabled"})
            except Exception:
                pass
        logger.debug("Goal sensors set to disabled state")

    # Set default values for sensors that are always enabled
    # These will be updated by startup jobs, but set reasonable defaults first
    default_sensors = [
        # Volatility
        ("volatility_30d", {}),
        ("volatility_percentile", 50),
        ("volatility_status", "Loading..."),
        # Unlocks
        ("unlock_next_event", "Loading..."),
        ("unlock_risk_level", "Loading..."),
        ("unlocks_next_7d", 0),
        # Profit taking
        ("tp_levels", {}),
        # Alerts
        ("active_alerts_count", 0),
        ("triggered_alerts_24h", 0),
        # Smart summary
        ("today_action", "Loading..."),
        ("today_action_priority", "low"),
        ("market_pulse", "Loading..."),
        ("weekly_outlook", "Loading..."),
        # Investor
        ("do_nothing_ok", True),
        ("investor_phase", "Loading..."),
        ("calm_indicator", 50),
        ("red_flags", "🟢 0"),
        # Technical
        ("divergences", {}),
        ("divergences_active", 0),
        # Gas
        ("gas_fast", 0),
        ("gas_standard", 0),
        ("gas_slow", 0),
        ("gas_status", "Loading..."),
    ]

    for sensor_id, value in default_sensors:
        try:
            await sensors.publish_sensor(sensor_id, value)
        except Exception:
            pass

    logger.info("Initial sensor values set based on feature configuration")
