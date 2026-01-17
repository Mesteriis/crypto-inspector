"""Scheduled jobs for the application.

This module contains all scheduled job functions that are registered
with the APScheduler.
"""

import asyncio
import logging
import os
import time
from datetime import datetime

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 10

# Get symbols from environment (set by HA add-on)
DEFAULT_SYMBOLS = ["BTC/USDT", "ETH/USDT"]


def get_symbols() -> list[str]:
    """Get trading symbols from environment or use defaults."""
    symbols_env = os.environ.get("HA_SYMBOLS", "")
    if symbols_env:
        return [s.strip() for s in symbols_env.split(",") if s.strip()]
    return DEFAULT_SYMBOLS


def get_intervals_to_fetch(now: datetime) -> list[str]:
    """
    Determine which intervals to fetch based on current time.

    Logic:
    - 1m, 3m, 5m: Always fetch (we run every 5 min)
    - 15m: When minute is divisible by 15 (0, 15, 30, 45)
    - 30m: When minute is divisible by 30 (0, 30)
    - 1h: When minute == 0
    - 2h: When minute == 0 and hour is even
    - 4h: When minute == 0 and hour % 4 == 0
    - 6h: When minute == 0 and hour % 6 == 0
    - 8h: When minute == 0 and hour % 8 == 0
    - 12h: When minute == 0 and hour % 12 == 0
    - 1d: When minute == 0 and hour == 0
    - 3d: When minute == 0 and hour == 0 and day % 3 == 1
    - 1w: When minute == 0 and hour == 0 and weekday == 0 (Monday)
    - 1M: When minute == 0 and hour == 0 and day == 1

    Args:
        now: Current datetime.

    Returns:
        List of interval strings to fetch.
    """
    minute = now.minute
    hour = now.hour
    day = now.day
    weekday = now.weekday()  # 0 = Monday

    intervals = []

    # Always fetch minute intervals
    intervals.extend(["1m", "3m", "5m"])

    # 15-minute intervals
    if minute % 15 == 0:
        intervals.append("15m")

    # 30-minute intervals
    if minute % 30 == 0:
        intervals.append("30m")

    # Hourly intervals (only at minute 0)
    if minute == 0:
        intervals.append("1h")

        if hour % 2 == 0:
            intervals.append("2h")
        if hour % 4 == 0:
            intervals.append("4h")
        if hour % 6 == 0:
            intervals.append("6h")
        if hour % 8 == 0:
            intervals.append("8h")
        if hour % 12 == 0:
            intervals.append("12h")

        # Daily intervals (only at midnight)
        if hour == 0:
            intervals.append("1d")

            # 3-day intervals
            if day % 3 == 1:
                intervals.append("3d")

            # Weekly (Monday)
            if weekday == 0:
                intervals.append("1w")

            # Monthly (1st of month)
            if day == 1:
                intervals.append("1M")

    return intervals


async def fetch_and_save_candlesticks(
    symbol: str,
    interval_str: str,
    retry_count: int = 0,
) -> bool:
    """
    Fetch candlesticks for a symbol/interval and save to database.

    Args:
        symbol: Trading pair symbol.
        interval_str: Interval string (e.g., "1h").
        retry_count: Current retry attempt.

    Returns:
        True if successful, False otherwise.
    """
    from db.repositories.candlestick import CandlestickRepository
    from db.session import async_session_maker
    from services.candlestick.fetcher import CandlestickFetcher
    from services.candlestick.models import CandleInterval

    try:
        # Convert string to enum
        interval = CandleInterval(interval_str)

        # Fetch candlesticks
        fetcher = CandlestickFetcher(timeout=15.0)
        result = await fetcher.fetch(
            symbol=symbol,
            interval=interval,
            limit=10,  # Just get recent candles
        )

        if result.is_empty:
            logger.warning(f"No candlesticks returned for {symbol} {interval_str}")
            return False

        # Save to database
        async with async_session_maker() as session:
            repo = CandlestickRepository(session)
            count = await repo.upsert_candlesticks(result)
            logger.info(f"Saved {count} candlesticks for {symbol} {interval_str}")

        return True

    except Exception as e:
        logger.error(f"Error fetching {symbol} {interval_str}: {e}")

        # Retry logic
        if retry_count < MAX_RETRIES:
            logger.info(
                f"Retrying {symbol} {interval_str} in {RETRY_DELAY_SECONDS}s "
                f"(attempt {retry_count + 1}/{MAX_RETRIES})"
            )
            await asyncio.sleep(RETRY_DELAY_SECONDS)
            return await fetch_and_save_candlesticks(symbol, interval_str, retry_count + 1)

        logger.error(f"Failed to fetch {symbol} {interval_str} after {MAX_RETRIES} retries")
        return False


async def candlestick_sync_job() -> None:
    """
    Main candlestick sync job.

    Runs every 5 minutes and fetches candlesticks for all configured
    symbols and appropriate intervals based on current time.
    Sends notifications to Home Assistant on completion.
    """
    from services.ha_integration import notify_error, notify_sync_complete

    start_time = time.time()
    now = datetime.now()
    current_time = now.strftime("%Y-%m-%d %H:%M:%S")

    logger.info(f"[{current_time}] Starting candlestick sync job")

    # Get symbols and intervals to fetch
    symbols = get_symbols()
    intervals = get_intervals_to_fetch(now)

    logger.info(f"Symbols: {symbols}")
    logger.info(f"Intervals to fetch: {intervals}")

    # Track results
    success_count = 0
    failure_count = 0

    # Fetch candlesticks for each symbol and interval
    for symbol in symbols:
        for interval in intervals:
            try:
                success = await fetch_and_save_candlesticks(symbol, interval)
                if success:
                    success_count += 1
                else:
                    failure_count += 1
            except Exception as e:
                logger.error(f"Unexpected error for {symbol} {interval}: {e}")
                failure_count += 1

            # Small delay between requests to avoid rate limiting
            await asyncio.sleep(0.5)

    # Calculate duration
    duration = time.time() - start_time

    # Summary
    total = success_count + failure_count
    logger.info(
        f"[{current_time}] Candlestick sync completed: "
        f"{success_count}/{total} successful, {failure_count} failed, "
        f"duration: {duration:.1f}s"
    )

    # Send notification to Home Assistant
    try:
        if failure_count > 0:
            # Notify about errors
            await notify_error(
                error_message=f"{failure_count} fetch operations failed",
                context=f"Sync job at {current_time}",
            )
        else:
            # Notify success (only for significant syncs, e.g., hourly)
            if "1h" in intervals or "1d" in intervals:
                await notify_sync_complete(
                    success_count=success_count,
                    failure_count=failure_count,
                    duration_seconds=duration,
                )
    except Exception as e:
        logger.warning(f"Failed to send HA notification: {e}")


async def hello_world_job() -> None:
    """Test job that prints 'Hello World' to the console."""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = f"[{current_time}] Hello World! (Scheduled job executed)"
    print(message)
    logger.info(message)
