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
        ai_analysis_job,
        altseason_job,
        arbitrage_job,
        backtest_job,
        briefing_job,
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
        ml_prediction_job,
        portfolio_job,
        price_alerts_job,
        profit_taking_job,
        signal_history_job,
        stablecoin_job,
        traditional_backfill_job,
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

    # Traditional Backfill job - runs once a day at 03:00
    sched.add_job(
        traditional_backfill_job,
        trigger=CronTrigger(hour=3, minute=0),
        id="traditional_backfill_job",
        name="Traditional Backfill Job",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    # AI Analysis job - runs based on AI_ANALYSIS_INTERVAL_HOURS (default: every 24 hours at 08:00)
    sched.add_job(
        ai_analysis_job,
        trigger=CronTrigger(hour=8, minute=0),  # Run at 8:00 AM daily
        id="ai_analysis_job",
        name="AI Analysis Job",
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

    # Briefing job - runs at 7:00 (morning) and 20:00 (evening)
    sched.add_job(
        briefing_job,
        trigger=CronTrigger(hour="7,20", minute=0),
        id="briefing_job",
        name="Briefing Job",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    # Backtest job - runs every Sunday at 2:00 AM
    sched.add_job(
        backtest_job,
        trigger=CronTrigger(day_of_week="sun", hour=2, minute=0),
        id="backtest_job",
        name="Weekly Backtest Job",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    # ML Prediction job - runs every hour to update ML sensors independently
    sched.add_job(
        ml_prediction_job,
        trigger=CronTrigger(minute=20),
        id="ml_prediction_job",
        name="ML Prediction Job",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    logger.info("Registered scheduled jobs (27 total)")


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
    Initialize sensors at startup.

    Sets initial placeholder values immediately, then runs critical jobs
    to populate sensors with real data.
    """
    import asyncio

    from core.config import settings

    logger.info("Initializing sensor values...")

    # Set initial values for all sensors (no external API calls)
    await _set_initial_sensor_values()

    logger.info("Sensor initialization completed")

    # Run critical jobs in background to populate sensors with real data
    # This doesn't block startup but ensures sensors get data quickly
    _startup_task = asyncio.create_task(_run_critical_startup_jobs())
    # Store task reference to prevent garbage collection
    asyncio.get_event_loop().__dict__.setdefault("_crypto_inspect_tasks", []).append(_startup_task)


async def _run_critical_startup_jobs() -> None:
    """
    Run critical jobs to populate sensors with real data after startup.

    Runs in background to not block application startup.
    """
    import asyncio

    from core.config import settings

    logger.info("Starting critical startup jobs to populate sensor data...")

    # Small delay to ensure HA connection is established
    await asyncio.sleep(2)

    try:
        from core.scheduler.jobs import (
            ai_analysis_job,
            altseason_job,
            backtest_job,
            briefing_job,
            bybit_sync_job,
            correlation_job,
            currency_list_monitor_job,
            divergence_job,
            exchange_flow_job,
            gas_tracker_job,
            investor_analysis_job,
            liquidation_job,
            macro_job,
            ml_prediction_job,
            portfolio_job,
            profit_taking_job,
            stablecoin_job,
            traditional_finance_job,
            volatility_job,
        )

        jobs_to_run = []

        # Currency list and unified sensors - most critical
        jobs_to_run.append(("currency_list_monitor", currency_list_monitor_job))

        # Always run investor analysis to populate market data
        jobs_to_run.append(("investor_analysis", investor_analysis_job))

        # Run Bybit sync if configured
        if settings.has_bybit_credentials():
            jobs_to_run.append(("bybit_sync", bybit_sync_job))

        # Always run gas tracker - it's fast
        jobs_to_run.append(("gas_tracker", gas_tracker_job))

        # Altseason index
        jobs_to_run.append(("altseason", altseason_job))

        # Technical analysis (RSI, MACD, trends)
        jobs_to_run.append(("divergence", divergence_job))

        # Correlation analysis
        jobs_to_run.append(("correlation", correlation_job))

        # Volatility tracker - updates volatility_30d, adaptive_volatilities
        jobs_to_run.append(("volatility", volatility_job))

        # Liquidation levels
        jobs_to_run.append(("liquidation", liquidation_job))

        # Exchange flow (netflows)
        jobs_to_run.append(("exchange_flow", exchange_flow_job))

        # Stablecoin flow
        jobs_to_run.append(("stablecoin", stablecoin_job))

        # Macro calendar
        jobs_to_run.append(("macro", macro_job))

        # Traditional finance (gold, indices, forex)
        jobs_to_run.append(("traditional_finance", traditional_finance_job))

        # AI analysis if enabled
        if settings.AI_ENABLED:
            jobs_to_run.append(("ai_analysis", ai_analysis_job))

        # Briefing sensors
        jobs_to_run.append(("briefing", briefing_job))

        # Portfolio tracker - always run to update portfolio values
        jobs_to_run.append(("portfolio", portfolio_job))

        # ML predictions - critical for ml_* and price_predictions sensors
        jobs_to_run.append(("ml_prediction", ml_prediction_job))

        # Profit taking - updates tp_levels and greed_level
        jobs_to_run.append(("profit_taking", profit_taking_job))

        # Backtest - updates backtest_* sensors (normally weekly, but run at startup)
        jobs_to_run.append(("backtest", backtest_job))

        for name, job in jobs_to_run:
            try:
                logger.info(f"Startup job: Running {name}...")
                await job()
                logger.info(f"Startup job: {name} completed")
            except Exception as e:
                logger.warning(f"Startup job {name} failed: {e}")
            # Small delay between jobs
            await asyncio.sleep(1)

        logger.info("Critical startup jobs completed")

    except Exception as e:
        logger.error(f"Error running critical startup jobs: {e}")


async def _set_initial_sensor_values() -> None:
    """
    Set initial sensor values based on feature flags.

    This sets informative values for disabled features instead of 'unknown'.
    """
    from core.config import settings
    from service.ha import get_currency_list, get_sensors_manager

    sensors = get_sensors_manager()
    disabled_dict: dict = {}

    # Get real currency list
    try:
        currency_list = get_currency_list()
        logger.info(f"Loaded currency list: {currency_list}")
    except Exception as e:
        logger.warning(f"Failed to get currency list: {e}")
        currency_list = []

    # AI sensors - depends on AI_ENABLED
    if not settings.AI_ENABLED:
        ai_sensors = [
            ("ai_daily_summary", "AI отключен"),
            ("ai_market_sentiment", "AI отключен"),
            ("ai_recommendation", "AI отключен"),
            ("ai_last_analysis", "—"),
            ("ai_provider", "—"),
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
    else:
        # AI enabled - set initial values
        provider_name = settings.AI_PROVIDER or "ollama"
        ai_sensors = [
            ("ai_daily_summary", "Ожидание анализа..."),
            ("ai_market_sentiment", "Ожидание анализа..."),
            ("ai_recommendation", "Ожидание анализа..."),
            ("ai_last_analysis", "—"),
            ("ai_provider", provider_name),
            ("ai_trends", {}),
            ("ai_confidences", {}),
            ("ai_price_forecasts_24h", {}),
        ]
        for sensor_id, value in ai_sensors:
            try:
                await sensors.publish_sensor(sensor_id, value, {"status": "enabled"})
            except Exception:
                pass
        logger.debug("AI sensors set to enabled state")

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
            ("goal_status", "Цель отключена"),
            ("goal_target", 0),
            ("goal_remaining", 0),
            ("goal_days_estimate", 0),
        ]
        for sensor_id, value in goal_sensors:
            try:
                await sensors.publish_sensor(sensor_id, value, {"status": "disabled"})
            except Exception:
                pass
        logger.debug("Goal sensors set to disabled state")
    else:
        # Goal enabled - set initial values
        goal_sensors = [
            ("goal_progress", 0),
            ("goal_status", "Отслеживание..."),
            ("goal_target", settings.GOAL_TARGET_VALUE),
            ("goal_remaining", settings.GOAL_TARGET_VALUE),
            ("goal_days_estimate", 0),
        ]
        for sensor_id, value in goal_sensors:
            try:
                await sensors.publish_sensor(sensor_id, value, {"status": "enabled"})
            except Exception:
                pass
        logger.debug("Goal sensors set to enabled state")

    # Set default values for ALL sensors to avoid "unknown" state
    # These will be updated by scheduled jobs
    default_sensors = [
        # === System ===
        ("ready", True),
        ("version", settings.VERSION if hasattr(settings, "VERSION") else "—"),
        ("api_status", "running"),
        ("database_status", "connected"),
        ("scheduler_status", "running"),
        ("last_sync", "—"),
        ("sync_status", "idle"),
        ("candles_count", 0),
        ("database_size", 0),
        ("crypto_history_status", {}),
        # === Market Overview ===
        ("fear_greed", 50),
        ("fear_greed_alert", "—"),
        ("btc_dominance", 0),
        ("prices", {}),
        ("changes_24h", {}),
        ("volumes_24h", {}),
        ("highs_24h", {}),
        ("lows_24h", {}),
        ("price_alert", "—"),
        ("price_context", {}),
        ("crypto_currency_list", currency_list),
        # === Volatility ===
        ("volatility_30d", {}),
        ("volatility_percentile", 50),
        ("volatility_status", "Загрузка..."),
        ("vix_index", 0),
        # === Market Pulse ===
        ("market_pulse", "Загрузка..."),
        ("market_pulse_confidence", 0),
        ("market_tension", 0),
        # === Altseason ===
        ("altseason_index", 0),
        ("altseason_status", "Загрузка..."),
        # === Stablecoins ===
        ("stablecoin_total", 0),
        ("stablecoin_dominance", 0),
        ("stablecoin_flow", "Загрузка..."),
        ("stablecoin_flow_24h", 0),
        # === Whales ===
        ("whale_alerts_24h", 0),
        ("whale_last_alert", "—"),
        ("whale_net_flow", 0),
        ("whale_signal", "—"),
        # === Exchange Flow ===
        ("exchange_flow_signal", "Загрузка..."),
        ("exchange_netflows", {}),
        # === Liquidation ===
        ("liq_levels", {}),
        ("liq_risk_level", "Загрузка..."),
        # === Unlocks ===
        ("unlock_next_event", "Загрузка..."),
        ("unlock_risk_level", "Загрузка..."),
        ("unlocks_next_7d", 0),
        ("unlocks_next_event", "—"),
        # === Profit taking ===
        ("tp_levels", {}),
        ("greed_level", 0),
        ("profit_action", "Загрузка..."),
        ("stop_loss_recommendation", {}),
        ("success_rate", 0),
        # === Alerts ===
        ("active_alerts_count", 0),
        ("triggered_alerts_24h", 0),
        ("pending_alerts_count", 0),
        ("pending_alerts_critical", 0),
        # === Smart summary ===
        ("today_action", "Загрузка..."),
        ("today_action_priority", "low"),
        ("next_action_timer", "—"),
        ("weekly_outlook", "Загрузка..."),
        ("weekly_insight", "—"),
        # === Investor ===
        ("do_nothing_ok", True),
        ("investor_phase", "Загрузка..."),
        ("calm_indicator", 50),
        ("red_flags", 0),
        ("risk_status", "Загрузка..."),
        # === Technical Analysis ===
        ("divergences", {}),
        ("divergences_active", 0),
        ("ta_rsi", {}),
        ("ta_macd_signal", {}),
        ("ta_trend", {}),
        ("ta_trend_mtf", {}),
        ("ta_support", {}),
        ("ta_resistance", {}),
        ("ta_confluence", 0),
        ("ta_signal", {}),
        ("ta_bb_position", {}),
        # === Signals ===
        ("signals_today", 0),
        ("signals_last", "—"),
        ("signals_win_rate", 0),
        # === Gas ===
        ("eth_gas_fast", 0),
        ("eth_gas_standard", 0),
        ("eth_gas_slow", 0),
        ("eth_gas_status", "Загрузка..."),
        # === Correlation ===
        ("btc_eth_correlation", 0),
        ("btc_sp500_correlation", 0),
        ("correlation_status", "Загрузка..."),
        ("correlation_analysis_status", "Загрузка..."),
        ("correlation_significant_count", 0),
        ("correlation_strongest_positive", "—"),
        ("correlation_strongest_negative", "—"),
        ("correlation_dominant_patterns", {}),
        # === DCA ===
        ("dca_signal", "Загрузка..."),
        ("dca_zone", "Загрузка..."),
        ("dca_next_level", 0),
        ("dca_risk_score", 50),
        ("dca_result", 0),
        # === Arbitrage ===
        ("arb_opportunity", "Нет"),
        ("arb_spreads", {}),
        ("funding_arb_best", "—"),
        # === Macro ===
        ("days_to_fomc", 0),
        ("macro_risk_week", "Загрузка..."),
        ("next_macro_event", "—"),
        # === Derivatives ===
        ("derivatives", {}),
        # === Traditional Finance ===
        ("sp500_price", 0),
        ("nasdaq_price", 0),
        ("dji_price", 0),
        ("dax_price", 0),
        ("gold_price", 0),
        ("silver_price", 0),
        ("platinum_price", 0),
        ("oil_wti", 0),
        ("oil_brent", 0),
        ("natural_gas", 0),
        ("dxy_index", 0),
        ("eur_usd", 0),
        ("gbp_usd", 0),
        ("treasury_yield_2y", 0),
        ("treasury_yield_10y", 0),
        # === Portfolio (advanced) ===
        ("portfolio_value", 0),
        ("portfolio_pnl", 0),
        ("portfolio_pnl_24h", 0),
        ("portfolio_health", "Загрузка..."),
        ("portfolio_health_score", 0),
        ("portfolio_allocation", {}),
        ("portfolio_sharpe", 0),
        ("portfolio_sortino", 0),
        ("portfolio_var_95", 0),
        ("portfolio_max_drawdown", 0),
        ("portfolio_current_drawdown", 0),
        # === Briefings ===
        ("morning_briefing", "Ожидание..."),
        ("evening_briefing", "Ожидание..."),
        ("daily_digest_ready", False),
        ("briefing_last_sent", "—"),
        # === Backtest ===
        ("backtest_dca_roi", 0),
        ("backtest_lump_sum_roi", 0),
        ("backtest_smart_dca_roi", 0),
        ("backtest_best_strategy", "—"),
        # === ML ===
        ("ml_system_status", "Загрузка..."),
        ("ml_accuracy_rate", 0),
        ("ml_correct_predictions", 0),
        ("ml_latest_predictions", {}),
        ("ml_market_confidence", 0),
        ("ml_portfolio_health", "Загрузка..."),
        ("ml_risk_warning", "—"),
        ("ml_investment_opportunity", "Загрузка..."),
        # === Economic Calendar ===
        ("economic_calendar_status", "Загрузка..."),
        ("economic_upcoming_events_24h", 0),
        ("economic_important_events", 0),
        ("economic_sentiment_score", 0),
        ("economic_breaking_news", "—"),
        # === Adaptive Notifications ===
        ("adaptive_notifications_status", "Загрузка..."),
        ("adaptive_notification_count_24h", 0),
        ("adaptive_volatilities", {}),
        ("adaptive_adaptation_factors", {}),
        ("notification_mode", settings.NOTIFICATION_MODE),
        ("notification_service", f"Active ({settings.NOTIFICATION_MODE})"),
    ]

    for sensor_id, value in default_sensors:
        try:
            await sensors.publish_sensor(sensor_id, value)
        except Exception:
            pass

    # Load crypto history status from database (fast, no external API calls)
    try:
        from service.backfill.crypto_backfill import get_crypto_backfill

        crypto_backfill = get_crypto_backfill()
        history_status = await crypto_backfill.get_history_status()
        if history_status:
            await sensors.publish_sensor("crypto_history_status", history_status)
            logger.debug(f"Loaded crypto history status for {len(history_status)} symbols")
    except Exception as e:
        logger.debug(f"Could not load crypto history status: {e}")

    logger.info("Initial sensor values set based on feature configuration")
