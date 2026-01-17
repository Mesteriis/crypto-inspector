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

        # Save to database using raw SQL to avoid circular imports
        from sqlalchemy import text

        from db.session import async_session_maker

        async with async_session_maker() as session:
            for candle in result.candlesticks:
                stmt = text("""
                    INSERT INTO candlestick_records
                    (exchange, symbol, interval, timestamp, open_price, high_price,
                     low_price, close_price, volume, quote_volume, trades_count,
                     fetch_time_ms, is_complete, loaded_at)
                    VALUES (:exchange, :symbol, :interval, :timestamp, :open_price,
                            :high_price, :low_price, :close_price, :volume,
                            :quote_volume, :trades_count, :fetch_time_ms,
                            :is_complete, :loaded_at)
                    ON CONFLICT (exchange, symbol, interval, timestamp)
                    DO UPDATE SET
                        open_price = EXCLUDED.open_price,
                        high_price = EXCLUDED.high_price,
                        low_price = EXCLUDED.low_price,
                        close_price = EXCLUDED.close_price,
                        volume = EXCLUDED.volume,
                        is_complete = EXCLUDED.is_complete,
                        loaded_at = EXCLUDED.loaded_at
                """)
                await session.execute(
                    stmt,
                    {
                        "exchange": result.exchange,
                        "symbol": result.symbol,
                        "interval": result.interval.value,
                        "timestamp": candle.timestamp,
                        "open_price": float(candle.open_price),
                        "high_price": float(candle.high_price),
                        "low_price": float(candle.low_price),
                        "close_price": float(candle.close_price),
                        "volume": float(candle.volume),
                        "quote_volume": float(candle.quote_volume) if candle.quote_volume else None,
                        "trades_count": candle.trades_count,
                        "fetch_time_ms": result.fetch_time_ms,
                        "is_complete": True,
                        "loaded_at": datetime.utcnow(),
                    },
                )
            await session.commit()
            logger.info(
                f"Saved {len(result.candlesticks)} candlesticks for {symbol} {interval_str}"
            )

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


async def market_analysis_job() -> None:
    """
    Market analysis job.

    Runs every 4 hours to fetch on-chain metrics, derivatives data,
    and calculate composite scores. Sends alerts for significant signals.
    """
    from services.analysis import (
        CycleDetector,
        DerivativesAnalyzer,
        OnChainAnalyzer,
        ScoringEngine,
    )
    from services.ha_integration import notify

    start_time = time.time()
    now = datetime.now()
    current_time = now.strftime("%Y-%m-%d %H:%M:%S")

    logger.info(f"[{current_time}] Starting market analysis job")

    symbols = get_symbols()
    base_symbols = [s.split("/")[0] for s in symbols]  # BTC/USDT -> BTC

    results = {}
    onchain = OnChainAnalyzer()
    derivatives = DerivativesAnalyzer()
    scoring = ScoringEngine()
    cycles = CycleDetector()

    try:
        # Fetch Fear & Greed
        fg_value = None
        try:
            onchain_data = await onchain.analyze()
            if onchain_data.fear_greed:
                fg_value = onchain_data.fear_greed.value
                results["fear_greed"] = {
                    "value": fg_value,
                    "classification": onchain_data.fear_greed.classification,
                }
                logger.info(f"Fear & Greed: {fg_value} ({onchain_data.fear_greed.classification})")
        except Exception as e:
            logger.warning(f"On-chain fetch failed: {e}")

        # Analyze each symbol
        for symbol in base_symbols:
            try:
                # Fetch derivatives
                deriv_data = None
                try:
                    deriv_result = await derivatives.analyze(symbol)
                    deriv_data = {
                        "funding_rate": deriv_result.funding.rate if deriv_result.funding else None,
                        "long_short_ratio": (
                            deriv_result.long_short.long_short_ratio
                            if deriv_result.long_short
                            else None
                        ),
                    }
                except Exception as e:
                    logger.warning(f"Derivatives fetch failed for {symbol}: {e}")

                # Cycle data for BTC
                cycle_data = None
                if symbol == "BTC":
                    current_price = 100000  # Placeholder
                    if deriv_result and deriv_result.funding:
                        current_price = deriv_result.funding.mark_price
                    cycle_info = cycles.detect_cycle(current_price)
                    cycle_data = {
                        "phase": cycle_info.phase.value,
                        "phase_name_ru": cycle_info.phase_name_ru,
                        "days_since_halving": cycle_info.days_since_halving,
                        "distance_from_ath_pct": cycle_info.distance_from_ath_pct,
                    }

                # Calculate score
                score = scoring.calculate(
                    symbol=symbol,
                    fg_value=fg_value,
                    deriv_data=deriv_data,
                    cycle_data=cycle_data,
                )

                results[symbol] = {
                    "score": score.total_score,
                    "signal": score.signal,
                    "action": score.action,
                }

                logger.info(
                    f"{symbol}: Score={score.total_score:.0f}, "
                    f"Signal={score.signal}, Action={score.action}"
                )

                # Alert on strong signals
                if score.action in ["strong_buy", "strong_sell"]:
                    await notify(
                        message=(
                            f"{symbol} {score.signal_ru}\n"
                            f"Score: {score.total_score:.0f}/100\n"
                            f"{score.recommendation_ru}"
                        ),
                        title=f"Crypto Alert - {symbol}",
                        notification_id=f"crypto_alert_{symbol.lower()}",
                    )

            except Exception as e:
                logger.error(f"Analysis error for {symbol}: {e}")

            await asyncio.sleep(0.5)  # Rate limiting

    finally:
        await onchain.close()
        await derivatives.close()

    duration = time.time() - start_time
    logger.info(
        f"[{current_time}] Market analysis completed in {duration:.1f}s, "
        f"analyzed {len(results)} items"
    )
