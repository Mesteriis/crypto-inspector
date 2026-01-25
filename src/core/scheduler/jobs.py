"""Scheduled jobs for the application.

This module contains all scheduled job functions that are registered
with the APScheduler.
"""

import asyncio
import logging
import os
import time
from datetime import UTC, datetime

from core.config import settings
from core.constants import (
    DEFAULT_SYMBOLS,
    AlertThresholds,
    PriceDefaults,
    SyncDefaults,
)

logger = logging.getLogger(__name__)


def get_symbols() -> list[str]:
    """Get trading symbols from environment (deprecated - use get_currency_list instead)."""
    symbols_env = os.environ.get("HA_SYMBOLS", "")
    if symbols_env:
        return [s.strip() for s in symbols_env.split(",") if s.strip()]
    return DEFAULT_SYMBOLS


def get_currency_list() -> list[str]:
    """Get the dynamic currency list (sync version).

    This is the single source of truth for currency selections across the application.
    For async contexts that need fresh Bybit data, use get_currency_list_async().

    Returns:
        List of currency symbols (e.g., ["BTC/USDT", "ETH/USDT"])
    """
    from service.ha import get_currency_list as get_dynamic_currency_list

    return get_dynamic_currency_list()


async def get_currency_list_async() -> list[str]:
    """Get the dynamic currency list with fresh Bybit data (async version).

    Use this in scheduler jobs and async contexts to get up-to-date
    symbols including any from Bybit wallet/earn positions.

    Returns:
        List of currency symbols (e.g., ["BTC/USDT", "ETH/USDT"])
    """
    from service.ha import get_currency_list_async as get_dynamic_currency_list_async

    return await get_dynamic_currency_list_async()


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
    from service.candlestick.fetcher import CandlestickFetcher
    from service.candlestick.models import CandleInterval

    try:
        # Convert string to enum
        interval = CandleInterval(interval_str)

        # Fetch candlesticks
        fetcher = CandlestickFetcher(timeout=settings.CANDLESTICK_FETCH_TIMEOUT)
        result = await fetcher.fetch(
            symbol=symbol,
            interval=interval,
            limit=SyncDefaults.CANDLES_LIMIT,  # Just get recent candles
        )

        if result.is_empty:
            logger.warning(f"No candlesticks returned for {symbol} {interval_str}")
            return False

        # Save to database using raw SQL to avoid circular imports
        from sqlalchemy import text

        from models.session import async_session_maker

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
                        "loaded_at": datetime.now(UTC),
                    },
                )
            await session.commit()
            logger.debug(f"Saved {len(result.candlesticks)} candlesticks for {symbol} {interval_str}")

        return True

    except Exception as e:
        logger.error(f"Error fetching {symbol} {interval_str}: {e}")

        # Retry logic
        if retry_count < settings.MAX_RETRIES:
            logger.info(
                f"Retrying {symbol} {interval_str} in {settings.RETRY_DELAY_SECONDS}s "
                f"(attempt {retry_count + 1}/{settings.MAX_RETRIES})"
            )
            await asyncio.sleep(settings.RETRY_DELAY_SECONDS)
            return await fetch_and_save_candlesticks(symbol, interval_str, retry_count + 1)

        logger.error(f"Failed to fetch {symbol} {interval_str} after {settings.MAX_RETRIES} retries")
        return False


async def candlestick_sync_job() -> None:
    """
    Main candlestick sync job.

    Runs every 5 minutes and fetches candlesticks for all configured
    symbols and appropriate intervals based on current time.
    Sends notifications to Home Assistant on completion.
    """
    from service.ha_integration import notify_error, notify_sync_complete

    start_time = time.time()
    now = datetime.now()
    current_time = now.strftime("%Y-%m-%d %H:%M:%S")

    logger.debug(f"[{current_time}] Starting candlestick sync job")

    # Get symbols and intervals to fetch
    symbols = await get_currency_list_async()  # Dynamic with Bybit
    intervals = get_intervals_to_fetch(now)

    logger.debug(f"Symbols: {symbols}")
    logger.debug(f"Intervals to fetch: {intervals}")

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

    # Update crypto history status sensor
    try:
        from service.backfill.crypto_backfill import get_crypto_backfill
        from service.ha import get_sensors_manager

        crypto_backfill = get_crypto_backfill()
        sensors = get_sensors_manager()
        history_status = await crypto_backfill.get_history_status()
        await sensors.publish_sensor("crypto_history_status", history_status)
    except Exception as e:
        logger.warning(f"Failed to update crypto history status: {e}")


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
    from service.analysis import (
        CycleDetector,
        DerivativesAnalyzer,
        OnChainAnalyzer,
        ScoringEngine,
    )
    from service.ha_integration import notify

    start_time = time.time()
    now = datetime.now()
    current_time = now.strftime("%Y-%m-%d %H:%M:%S")

    logger.info(f"[{current_time}] Starting market analysis job")

    symbols = await get_currency_list_async()  # Dynamic with Bybit
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
                            deriv_result.long_short.long_short_ratio if deriv_result.long_short else None
                        ),
                    }
                except Exception as e:
                    logger.warning(f"Derivatives fetch failed for {symbol}: {e}")

                # Cycle data for BTC
                cycle_data = None
                if symbol == "BTC":
                    current_price = PriceDefaults.PLACEHOLDER_BTC
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

                logger.info(f"{symbol}: Score={score.total_score:.0f}, Signal={score.signal}, Action={score.action}")

                # Alert on strong signals
                if score.action in ["strong_buy", "strong_sell"]:
                    await notify(
                        message=(
                            f"{symbol} {score.signal_ru}\nScore: {score.total_score:.0f}/100\n{score.recommendation_ru}"
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
    logger.info(f"[{current_time}] Market analysis completed in {duration:.1f}s, analyzed {len(results)} items")


async def investor_analysis_job() -> None:
    """
    Lazy Investor analysis job.

    Runs every hour to:
    - Calculate investor status (do nothing ok, market phase, etc.)
    - Update HA sensors for Home Assistant
    - Send alerts if critical conditions detected
    """
    from service.analysis import (
        CycleDetector,
        DerivativesAnalyzer,
        OnChainAnalyzer,
        get_investor_analyzer,
    )
    from service.ha import get_sensors_manager
    from service.ha_integration import notify

    start_time = time.time()
    now = datetime.now()
    current_time = now.strftime("%Y-%m-%d %H:%M:%S")

    logger.info(f"[{current_time}] Starting investor analysis job")

    analyzer = get_investor_analyzer()
    onchain = OnChainAnalyzer()
    derivatives = DerivativesAnalyzer()
    cycles = CycleDetector()
    sensors = get_sensors_manager()

    try:
        # Gather data
        fear_greed = None
        btc_dominance = None
        funding_rate = None
        long_short_ratio = None
        btc_price = None
        btc_price_avg_6m = None
        rsi = None
        cycle_phase = None
        days_since_halving = None

        # Fetch on-chain data
        try:
            onchain_data = await onchain.analyze()
            if onchain_data.fear_greed:
                fear_greed = onchain_data.fear_greed.value
            logger.info(f"On-chain: F&G={fear_greed}")
        except Exception as e:
            logger.warning(f"On-chain fetch failed: {e}")

        # Fetch BTC dominance from CoinGecko global
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get("https://api.coingecko.com/api/v3/global")
                if resp.status_code == 200:
                    data = resp.json()
                    btc_dominance = data.get("data", {}).get("market_cap_percentage", {}).get("btc")
                    if btc_dominance:
                        btc_dominance = round(btc_dominance, 2)
                        logger.info(f"BTC dominance: {btc_dominance}%")
        except Exception as e:
            logger.warning(f"BTC dominance fetch failed: {e}")

        # Fetch derivatives data
        try:
            deriv_data = await derivatives.analyze("BTC")
            if deriv_data.funding:
                funding_rate = deriv_data.funding.rate
                btc_price = deriv_data.funding.mark_price
            if deriv_data.long_short:
                long_short_ratio = deriv_data.long_short.long_short_ratio
            logger.info(f"Derivatives: funding={funding_rate}, L/S={long_short_ratio}, price={btc_price}")
        except Exception as e:
            logger.warning(f"Derivatives fetch failed: {e}")

        # Get cycle info
        try:
            if btc_price:
                cycle_info = cycles.detect_cycle(btc_price)
                cycle_phase = cycle_info.phase.value
                days_since_halving = cycle_info.days_since_halving
                logger.info(f"Cycle: phase={cycle_phase}, days_since_halving={days_since_halving}")
        except Exception as e:
            logger.warning(f"Cycle detection failed: {e}")

        # Calculate 6-month average (simplified - use historical data in production)
        if btc_price:
            btc_price_avg_6m = btc_price * 0.95  # Placeholder

        # Analyze investor status
        status = await analyzer.analyze(
            fear_greed=fear_greed,
            btc_price=btc_price,
            btc_price_avg_6m=btc_price_avg_6m,
            funding_rate=funding_rate,
            long_short_ratio=long_short_ratio,
            btc_dominance=btc_dominance,
            rsi=rsi,
            cycle_phase=cycle_phase,
            days_since_halving=days_since_halving,
        )

        logger.info(
            f"Investor status: do_nothing_ok={status.do_nothing_ok}, "
            f"phase={status.phase.value}, calm={status.calm_score}, "
            f"tension={status.tension_score}, red_flags={len(status.red_flags)}"
        )

        # Update HA sensors
        try:
            status_dict = status.to_dict()
            await sensors.update_investor_status(status_dict)

            # Also update market data sensors
            derivatives_dict = None
            if funding_rate is not None or long_short_ratio is not None:
                derivatives_dict = {
                    "funding_rate": funding_rate,
                    "long_short_ratio": long_short_ratio,
                }
            await sensors.update_market_data(
                fear_greed=fear_greed,
                btc_dominance=btc_dominance,
                derivatives_data=derivatives_dict,
            )

            # Update smart summary sensors
            phase_name = status._get_phase_name_ru()
            action = "Держать" if status.do_nothing_ok else "Внимание"
            priority = "low" if status.do_nothing_ok else "high"

            smart_summary = {
                "pulse": phase_name,
                "pulse_ru": phase_name,
                "action": action,
                "action_ru": action,
                "action_priority": priority,
                "outlook": f"Фаза: {phase_name}",
                "outlook_ru": f"Фаза: {phase_name}",
            }
            await sensors.update_smart_summary(smart_summary)

            logger.info("Updated HA sensors")
        except Exception as e:
            logger.warning(f"Failed to update HA sensors: {e}")

        # Check for alerts
        alert = analyzer.get_alert_if_needed(status)
        if alert:
            logger.warning(f"Alert triggered: {alert['title']} - {alert['message']}")
            try:
                await notify(
                    message=alert["message"],
                    title=alert["title"],
                    notification_id=alert["notification_id"],
                )
                logger.info(f"Sent alert notification: {alert['notification_id']}")
            except Exception as e:
                logger.error(f"Failed to send alert notification: {e}")

        # Send critical alerts for dangerous conditions
        if len(status.red_flags) >= AlertThresholds.RED_FLAGS_CRITICAL:
            try:
                flags_text = "\n".join([f"⚠️ {f.name_ru}" for f in status.red_flags])
                await notify(
                    message=f"Внимание! Множественные предупреждения:\n{flags_text}",
                    title="🚨 Crypto: Много красных флагов",
                    notification_id="crypto_multiple_flags",
                )
            except Exception as e:
                logger.error(f"Failed to send multi-flag alert: {e}")

        # Alert on phase transitions to extreme phases
        if status.phase.value in ["euphoria", "capitulation"]:
            try:
                phase_msg = f"Рынок в фазе: {status._get_phase_name_ru()}\n{status.phase_description_ru}"
                await notify(
                    message=phase_msg,
                    title=f"📉 Crypto: {status._get_phase_name_ru()}",
                    notification_id=f"crypto_phase_{status.phase.value}",
                )
            except Exception as e:
                logger.error(f"Failed to send phase alert: {e}")

    finally:
        await onchain.close()
        await derivatives.close()

    duration = time.time() - start_time
    logger.info(f"[{current_time}] Investor analysis completed in {duration:.1f}s")


async def altseason_job() -> None:
    """
    Altcoin Season Index job.

    Runs every 6 hours to fetch altcoin performance vs BTC
    and update HA sensors.
    
    Raises:
        RuntimeError: If not enough altcoin data received
    """
    from service.analysis.altseason import AltseasonAnalyzer
    from service.ha import get_sensors_manager

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"[{current_time}] Starting altseason analysis job")

    analyzer = AltseasonAnalyzer()
    sensors = get_sensors_manager()

    try:
        data = await analyzer.analyze()
        logger.info(f"Altseason: index={data.index}, status={data.status.value}, alts_analyzed={data.total_alts_analyzed}")

        # Update HA sensors
        await sensors.publish_sensor("altseason_index", data.index)
        await sensors.publish_sensor("altseason_status", data.status.value)

    except RuntimeError as e:
        # Data validation failed - job is considered failed
        logger.error(f"Altseason job FAILED (insufficient data): {e}")
        raise
    except Exception as e:
        logger.error(f"Altseason job FAILED: {e}")
        raise
    finally:
        await analyzer.close()


async def stablecoin_job() -> None:
    """
    Stablecoin Flow job.

    Runs every 4 hours to track stablecoin market caps
    and update HA sensors.
    
    Raises:
        RuntimeError: If not enough stablecoin data received
    """
    from service.analysis.stablecoins import StablecoinAnalyzer
    from service.ha import get_sensors_manager

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"[{current_time}] Starting stablecoin analysis job")

    analyzer = StablecoinAnalyzer()
    sensors = get_sensors_manager()

    try:
        data = await analyzer.analyze()
        logger.info(f"Stablecoins: total={data.total_market_cap / 1e9:.1f}B, flow_24h={data.change_24h_pct:.2f}%, count={len(data.stablecoins)}")

        # Update HA sensors
        await sensors.publish_sensor("stablecoin_total", round(data.total_market_cap / 1e9, 2))
        await sensors.publish_sensor("stablecoin_flow_24h", round(data.change_24h_pct, 2))
        await sensors.publish_sensor("stablecoin_dominance", round(data.dominance, 2))

    except RuntimeError as e:
        # Data validation failed - job is considered failed
        logger.error(f"Stablecoin job FAILED (insufficient data): {e}")
        raise
    except Exception as e:
        logger.error(f"Stablecoin job FAILED: {e}")
        raise
    finally:
        await analyzer.close()


async def gas_tracker_job() -> None:
    """
    ETH Gas Tracker job.

    Runs every 5 minutes to fetch current gas prices
    and update HA sensors.
    """
    from service.analysis.gas import GasTracker
    from service.ha import get_sensors_manager

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.debug(f"[{current_time}] Starting gas tracker job")

    tracker = GasTracker()
    sensors = get_sensors_manager()

    try:
        data = await tracker.get_gas_prices()
        logger.debug(f"Gas prices: slow={data.slow}, standard={data.standard}, fast={data.fast}, status={data.status}")

        # Update HA sensors
        await sensors.publish_sensor("eth_gas_slow", data.slow)
        await sensors.publish_sensor("eth_gas_standard", data.standard)
        await sensors.publish_sensor("eth_gas_fast", data.fast)
        # Convert enum to string value
        status_value = data.status.value if hasattr(data.status, 'value') else str(data.status)
        await sensors.publish_sensor("eth_gas_status", status_value)

    except Exception as e:
        logger.error(f"Gas tracker job failed: {e}")
    finally:
        await tracker.close()


async def whale_monitor_job() -> None:
    """
    Whale Activity Monitor job.

    Runs every 15 minutes to fetch large transactions
    and update HA sensors.
    """
    from service.analysis.whales import WhaleTracker
    from service.ha import get_sensors_manager
    from service.ha_integration import notify

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"[{current_time}] Starting whale monitor job")

    tracker = WhaleTracker()
    sensors = get_sensors_manager()

    try:
        data = await tracker.analyze()
        logger.info(f"Whales: transactions_24h={data.transactions_24h}, net_flow=${data.net_flow_usd:,.0f}")

        # Update HA sensors
        await sensors.publish_sensor("whale_alerts_24h", data.transactions_24h)
        await sensors.publish_sensor("whale_net_flow", data._format_usd(data.net_flow_usd))
        await sensors.publish_sensor("whale_signal", data.signal.value)

        # Alert on significant whale activity
        if data.transactions_24h > 50:
            await notify(
                message=(
                    f"Активность китов: {data.transactions_24h} транзакций за 24ч\n"
                    f"{data._format_usd(data.net_flow_usd)}"
                ),
                title="🐋 Высокая активность китов",
                notification_id="whale_high_activity",
            )

    except Exception as e:
        logger.error(f"Whale monitor job failed: {e}")
    finally:
        await tracker.close()


async def exchange_flow_job() -> None:
    """
    Exchange Flow job.

    Runs every 4 hours to track BTC/ETH exchange flows
    and update HA sensors for all currencies.
    """
    from service.analysis.exchange_flow import get_exchange_flow_analyzer
    from service.ha import get_sensors_manager
    from service.ha_integration import notify

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"[{current_time}] Starting exchange flow job")

    analyzer = get_exchange_flow_analyzer()
    sensors = get_sensors_manager()

    try:
        data = await analyzer.analyze()
        logger.info(f"Exchange flow: signal={data.overall_signal.value}")

        # Update HA sensors with dictionary format for ALL currencies
        netflows: dict[str, float] = {}
        if data.btc_flow:
            netflows["BTC"] = round(data.btc_flow.net_flow_24h, 2)
        if data.eth_flow:
            netflows["ETH"] = round(data.eth_flow.net_flow_24h, 2)

        await sensors.publish_sensor("exchange_netflows", netflows)
        await sensors.publish_sensor("exchange_flow_signal", data.overall_signal.value)

        # Alert on significant outflows (bullish signal)
        btc_flow = data.btc_flow
        if btc_flow and btc_flow.net_flow_24h < -5000:
            await notify(
                message=f"BTC отток с бирж: {abs(btc_flow.net_flow_24h):.0f} BTC\nСигнал: {data.overall_signal.value}",
                title="📈 Сильный отток BTC с бирж",
                notification_id="exchange_outflow_alert",
            )

    except Exception as e:
        logger.error(f"Exchange flow job failed: {e}")
    finally:
        await analyzer.close()


async def liquidation_job() -> None:
    """
    Liquidation Levels job.

    Runs every hour to fetch liquidation clusters
    and update HA sensors for all crypto symbols.
    """
    from service.analysis.liquidations import LiquidationTracker
    from service.ha import get_sensors_manager
    from service.ha_integration import notify

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"[{current_time}] Starting liquidation analysis job")

    tracker = LiquidationTracker()
    sensors = get_sensors_manager()

    symbols = await get_currency_list_async()  # Dynamic with Bybit
    base_symbols = [s.split("/")[0] for s in symbols]  # BTC/USDT -> BTC

    try:
        liq_levels_dict: dict[str, dict[str, float]] = {}
        highest_risk = "low"
        risk_order = {"low": 0, "medium": 1, "high": 2, "extreme": 3}

        for symbol in base_symbols:
            try:
                data = await tracker.analyze(symbol)

                liq_levels_dict[symbol] = {
                    "long": data.nearest_long_liq or 0,
                    "short": data.nearest_short_liq or 0,
                }

                # Track highest risk across all symbols
                if risk_order.get(data.risk_level.value, 0) > risk_order.get(highest_risk, 0):
                    highest_risk = data.risk_level.value

                logger.debug(
                    f"{symbol} liquidations: long={data.nearest_long_liq}, "
                    f"short={data.nearest_short_liq}, risk={data.risk_level.value}"
                )

            except Exception as e:
                logger.warning(f"Liquidation analysis failed for {symbol}: {e}")
                liq_levels_dict[symbol] = {"long": 0, "short": 0}

            await asyncio.sleep(0.5)  # Rate limiting

        # Update HA sensors with dictionary format for ALL symbols
        await sensors.publish_sensor("liq_levels", liq_levels_dict)
        await sensors.publish_sensor("liq_risk_level", highest_risk)

        logger.info(f"Liquidations updated for {len(liq_levels_dict)} symbols, highest risk: {highest_risk}")

        # Alert on high risk
        if highest_risk in ["high", "extreme"]:
            await notify(
                message=f"Высокий риск ликвидаций на рынке! Уровень: {highest_risk}",
                title="⚠️ Высокий риск ликвидаций",
                notification_id="liquidation_high_risk",
            )

    except Exception as e:
        logger.error(f"Liquidation job failed: {e}")
    finally:
        await tracker.close()


async def portfolio_job() -> None:
    """
    Portfolio Tracker job.

    Runs every 5 minutes to update portfolio values
    and HA sensors.
    """
    from service.ha import get_sensors_manager
    from service.portfolio import get_portfolio_manager

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.debug(f"[{current_time}] Starting portfolio update job")

    portfolio = get_portfolio_manager()
    sensors = get_sensors_manager()

    try:
        # Check if portfolio has any holdings
        if not portfolio.get_holdings():
            logger.debug("No portfolio holdings configured, skipping")
            return

        status = await portfolio.calculate()
        logger.info(f"Portfolio: value={status.total_value:.2f}, pnl={status.total_pnl_percent:.2f}%")

        # Update HA sensors
        await sensors.publish_sensor("portfolio_value", round(status.total_value, 2))
        await sensors.publish_sensor("portfolio_pnl", round(status.total_pnl_percent, 2))
        await sensors.publish_sensor("portfolio_pnl_24h", round(status.change_24h_pct or 0, 2))
        await sensors.publish_sensor("portfolio_best", status.best_performer.symbol if status.best_performer else "—")
        await sensors.publish_sensor(
            "portfolio_worst", status.worst_performer.symbol if status.worst_performer else "—"
        )

    except Exception as e:
        logger.error(f"Portfolio job failed: {e}")


async def divergence_job() -> None:
    """
    Divergence Detection job.

    Runs every hour to detect RSI/MACD divergences,
    calculate support/resistance levels, technical indicators and update HA sensors.
    """
    from service.analysis.divergences import DivergenceDetector
    from service.analysis.technical import TechnicalAnalyzer
    from service.candlestick import fetch_candlesticks
    from service.candlestick.models import CandleInterval
    from service.ha import get_sensors_manager
    from service.ha_integration import notify

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"[{current_time}] Starting divergence detection job")

    detector = DivergenceDetector()
    ta = TechnicalAnalyzer()
    sensors = get_sensors_manager()
    symbols = await get_currency_list_async()  # Dynamic with Bybit
    base_symbols = [s.split("/")[0] for s in symbols]  # BTC/USDT -> BTC

    try:
        active_count = 0
        divergence_data = {}  # Dictionary for all symbols
        support_data: dict[str, float | None] = {}  # Support levels
        resistance_data: dict[str, float | None] = {}  # Resistance levels
        
        # TA indicators dictionaries
        rsi_data: dict[str, float | None] = {}
        macd_data: dict[str, str] = {}
        trend_data: dict[str, str] = {}
        bb_position_data: dict[str, str] = {}
        prices_data: dict[str, float] = {}
        changes_data: dict[str, float] = {}
        signal_data: dict[str, str] = {}

        for symbol in base_symbols:
            try:
                # Fetch candle data for 4h timeframe (most useful for divergences)
                candles = await fetch_candlesticks(
                    symbol=f"{symbol}/USDT",
                    interval=CandleInterval.HOUR_4,
                    limit=100,
                )

                if len(candles) < 50:
                    divergence_data[symbol] = "Insufficient data"
                    support_data[symbol] = None
                    resistance_data[symbol] = None
                    rsi_data[symbol] = None
                    macd_data[symbol] = "—"
                    trend_data[symbol] = "—"
                    bb_position_data[symbol] = "—"
                    signal_data[symbol] = "—"
                    continue

                # Convert to list of close prices and calculate indicators
                closes = [float(c.close_price) for c in candles]
                highs = [float(c.high_price) for c in candles]
                lows = [float(c.low_price) for c in candles]
                rsi_values = []
                macd_values = []

                # Calculate RSI and MACD for each candle (rolling window)
                for i in range(14, len(closes)):
                    rsi = ta.calc_rsi(closes[: i + 1])
                    if rsi is not None:
                        rsi_values.append(rsi)

                for i in range(35, len(closes)):  # MACD needs 26+9 bars
                    _, _, hist = ta.calc_macd(closes[: i + 1])
                    if hist is not None:
                        macd_values.append(hist)
                
                # Get current price and calculate change
                current_price = closes[-1]
                price_24h_ago = closes[-6] if len(closes) >= 6 else closes[0]  # 4h * 6 = 24h
                change_24h = ((current_price - price_24h_ago) / price_24h_ago) * 100 if price_24h_ago else 0
                
                prices_data[symbol] = current_price
                changes_data[symbol] = round(change_24h, 2)
                
                # Current RSI
                current_rsi = ta.calc_rsi(closes)
                rsi_data[symbol] = round(current_rsi, 1) if current_rsi else None
                
                # Current MACD signal
                macd_line, signal_line, _ = ta.calc_macd(closes)
                if macd_line is not None and signal_line is not None:
                    if macd_line > signal_line:
                        macd_data[symbol] = "Bullish"
                    elif macd_line < signal_line:
                        macd_data[symbol] = "Bearish"
                    else:
                        macd_data[symbol] = "Neutral"
                else:
                    macd_data[symbol] = "—"
                
                # Trend direction based on SMA
                sma_20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else None
                sma_50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else None
                if sma_20 and sma_50:
                    if current_price > sma_20 > sma_50:
                        trend_data[symbol] = "Uptrend"
                    elif current_price < sma_20 < sma_50:
                        trend_data[symbol] = "Downtrend"
                    else:
                        trend_data[symbol] = "Sideways"
                else:
                    trend_data[symbol] = "—"
                
                # Bollinger Band position
                # calc_bollinger_bands returns tuple (upper, middle, lower, position)
                bb_result = ta.calc_bollinger_bands(closes)
                if bb_result and bb_result[0] is not None:
                    bb_upper, bb_middle, bb_lower, _ = bb_result
                    
                    if current_price >= bb_upper:
                        bb_position_data[symbol] = "Above Upper"
                    elif current_price <= bb_lower:
                        bb_position_data[symbol] = "Below Lower"
                    elif current_price > bb_middle:
                        bb_position_data[symbol] = "Upper Half"
                    else:
                        bb_position_data[symbol] = "Lower Half"
                else:
                    bb_position_data[symbol] = "—"
                
                # Generate trading signal
                signal = "HOLD"
                if current_rsi and current_rsi < 30 and macd_data[symbol] == "Bullish":
                    signal = "BUY"
                elif current_rsi and current_rsi > 70 and macd_data[symbol] == "Bearish":
                    signal = "SELL"
                signal_data[symbol] = signal

                # Align arrays for divergence detection
                min_len = min(len(closes) - 35, len(rsi_values), len(macd_values))
                if min_len < 20:
                    divergence_data[symbol] = "Insufficient data"
                    support_data[symbol] = None
                    resistance_data[symbol] = None
                    continue

                aligned_prices = closes[-min_len:]
                aligned_rsi = rsi_values[-min_len:]
                aligned_macd = macd_values[-min_len:]

                # Detect divergences
                divergences = detector.detect(
                    symbol=symbol,
                    prices=aligned_prices,
                    rsi_values=aligned_rsi,
                    macd_values=aligned_macd,
                    timeframe="4h",
                )
                active_count += len(divergences)

                # Find most significant divergence for this symbol
                if divergences:
                    # Prioritize by strength using mapping
                    strength_order = {"weak": 1, "moderate": 2, "strong": 3}
                    best = max(divergences, key=lambda d: strength_order.get(d.strength.value, 0))
                    sensor_value = f"{best.div_type.value} {best.timeframe}"

                    # Notify on significant divergences (MODERATE or STRONG)
                    if best.strength.value in ("moderate", "strong"):
                        await notify(
                            message=(
                                f"{symbol}: {best.div_type.value} дивергенция на {best.timeframe}\n"
                                f"Индикатор: {best.indicator}\n"
                                f"Сила: {best.strength.value}"
                            ),
                            title=f"Дивергенция {symbol}",
                            notification_id=f"divergence_{symbol.lower()}_{best.timeframe}",
                        )
                else:
                    sensor_value = "Нет"

                # Add to dictionary
                divergence_data[symbol] = sensor_value

                # Calculate support/resistance levels
                candle_dicts = [
                    {
                        "open": float(c.open_price),
                        "high": float(c.high_price),
                        "low": float(c.low_price),
                        "close": float(c.close_price),
                    }
                    for c in candles
                ]
                sr = ta.find_support_resistance(candle_dicts)
                support_data[symbol] = sr.nearest_support["level"] if sr.nearest_support else None
                resistance_data[symbol] = sr.nearest_resistance["level"] if sr.nearest_resistance else None

                logger.debug(
                    f"{symbol}: divergences={len(divergences)}, RSI={rsi_data[symbol]}, "
                    f"MACD={macd_data[symbol]}, trend={trend_data[symbol]}"
                )

            except Exception as e:
                logger.warning(f"Failed to analyze {symbol}: {e}")
                divergence_data[symbol] = "—"
                support_data[symbol] = None
                resistance_data[symbol] = None
                rsi_data[symbol] = None
                macd_data[symbol] = "—"
                trend_data[symbol] = "—"
                bb_position_data[symbol] = "—"
                signal_data[symbol] = "—"

        # Update divergence sensors
        await sensors.publish_sensor("divergences", divergence_data)
        await sensors.publish_sensor("divergences_active", active_count)

        # Update support/resistance levels
        await sensors.publish_sensor("ta_support", support_data)
        await sensors.publish_sensor("ta_resistance", resistance_data)
        
        # Update TA indicator sensors
        await sensors.publish_sensor("ta_rsi", rsi_data)
        await sensors.publish_sensor("ta_macd_signal", macd_data)
        await sensors.publish_sensor("ta_trend", trend_data)
        await sensors.publish_sensor("ta_bb_position", bb_position_data)
        await sensors.publish_sensor("ta_signal", signal_data)
        
        # Update price sensors
        await sensors.publish_sensor("prices", prices_data)
        await sensors.publish_sensor("changes_24h", changes_data)

        logger.info(
            f"Divergence job complete: {active_count} divergences, "
            f"TA indicators for {len(rsi_data)} symbols"
        )

    except Exception as e:
        logger.error(f"Divergence job failed: {e}")


async def signal_history_job() -> None:
    """
    Signal History Update job.

    Runs every hour to update signal outcomes
    and recalculate win rates.
    """
    from service.analysis.signal_history import get_signal_manager
    from service.ha import get_sensors_manager

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"[{current_time}] Starting signal history update job")

    tracker = get_signal_manager()
    sensors = get_sensors_manager()

    try:
        # Get stats (update_outcomes is not async, get_stats is sync)
        stats = tracker.get_stats()
        logger.info(
            f"Signals: total={stats.total_signals}, "
            f"win_rate_24h={stats.win_rate_24h:.1f}%"
        )

        # Update HA sensors
        await sensors.publish_sensor("signals_win_rate", round(stats.win_rate_24h, 1))
        await sensors.publish_sensor("signals_today", stats.signals_24h)

    except Exception as e:
        logger.error(f"Signal history job failed: {e}")


async def price_alerts_job() -> None:
    """
    Price Alerts Check job.

    Runs every minute to check price alerts
    and trigger notifications.
    """
    from service.alerts import get_alert_manager
    from service.ha import get_sensors_manager
    from service.ha_integration import notify

    logger.debug("Checking price alerts")

    alerts_manager = get_alert_manager()
    sensors = get_sensors_manager()

    try:
        # Get current prices from cache
        prices = {}
        for symbol in ["BTC", "ETH", "SOL", "TON", "AR"]:
            cached = sensors._cache.get(f"price_{symbol.lower()}")
            if cached:
                prices[symbol] = cached

        if not prices:
            logger.debug("No cached prices available for alerts")
            return

        # Check all alerts against prices
        triggered = await alerts_manager.check_prices(prices)

        # Update sensors with summary
        summary = alerts_manager.get_summary()
        await sensors.publish_sensor("active_alerts_count", summary.active_alerts)
        await sensors.publish_sensor("triggered_alerts_24h", summary.triggered_24h)

        # Send notifications for triggered alerts
        for alert, price in triggered:
            notification = alerts_manager.generate_notification(alert, price)
            await notify(
                message=notification["message"],
                title=notification["title"],
                notification_id=notification["notification_id"],
            )
            logger.info(f"Price alert triggered: {alert.symbol} at {price}")

    except Exception as e:
        logger.error(f"Price alerts job failed: {e}")


async def bybit_sync_job() -> None:
    """
    Bybit sync job.

    Runs every 5 minutes to sync Bybit account data
    and update HA sensors.
    """
    from service.exchange import get_bybit_portfolio
    from service.ha import get_sensors_manager

    logger.info("Starting Bybit sync job")

    portfolio = get_bybit_portfolio()
    sensors = get_sensors_manager()

    if not portfolio.is_configured:
        logger.debug("Bybit not configured, skipping")
        return

    try:
        account = await portfolio.get_account()
        from service.exchange.bybit_portfolio import PnlPeriod
        pnl_24h = await portfolio.calculate_pnl(PnlPeriod.DAY)
        pnl_7d = await portfolio.calculate_pnl(PnlPeriod.WEEK)

        # Calculate Earn PnL (total accumulated from all earn positions)
        earn_total_pnl = sum(p.total_pnl for p in account.earn_positions)
        earn_claimable = sum(p.claimable_yield for p in account.earn_positions)

        # Update HA sensors - Wallet
        await sensors.publish_sensor("bybit_balance", round(account.total_equity, 2))
        # Include earn PnL in total PnL
        await sensors.publish_sensor("bybit_pnl_24h", round(pnl_24h.total_pnl, 2))
        await sensors.publish_sensor("bybit_pnl_7d", round(pnl_7d.total_pnl, 2))
        await sensors.publish_sensor("bybit_positions", len(account.positions))
        await sensors.publish_sensor("bybit_unrealized_pnl", round(account.total_unrealized_pnl, 2))

        # Update HA sensors - Earn (Flexible Savings + OnChain)
        earn_balance = sum(p.usd_value for p in account.earn_positions)
        earn_count = len(account.earn_positions)
        avg_apy = sum(p.estimated_apy for p in account.earn_positions) / earn_count if earn_count > 0 else 0
        total_portfolio = account.total_equity + earn_balance

        await sensors.publish_sensor("bybit_earn_balance", round(earn_balance, 2))
        await sensors.publish_sensor(
            "bybit_earn_positions",
            earn_count,
            attributes={
                "positions": [p.to_dict() for p in account.earn_positions],
                "coins": [p.coin for p in account.earn_positions],
            },
        )
        await sensors.publish_sensor("bybit_earn_apy", round(avg_apy, 2))
        await sensors.publish_sensor("bybit_earn_pnl", round(earn_total_pnl, 2))
        await sensors.publish_sensor("bybit_earn_claimable", round(earn_claimable, 6))
        await sensors.publish_sensor("bybit_total_portfolio", round(total_portfolio, 2))

        logger.info(
            f"Bybit sync: wallet=${account.total_equity:.2f}, earn=${earn_balance:.2f}, "
            f"total=${total_portfolio:.2f}, earn_pnl=${earn_total_pnl:.2f}, "
            f"positions={len(account.positions)}, earn_positions={earn_count}"
        )

    except Exception as e:
        logger.error(f"Bybit sync job failed: {e}")


async def dca_job() -> None:
    """
    DCA Calculator job.

    Runs every hour to calculate optimal DCA levels
    and update HA sensors.
    """
    from service.analysis.dca import get_dca_calculator
    from service.ha import get_sensors_manager

    logger.info("Starting DCA calculator job")

    calculator = get_dca_calculator()
    sensors = get_sensors_manager()

    try:
        analysis = await calculator.analyze("BTC")

        await sensors.publish_sensor("dca_next_level", round(analysis.next_level, 2))
        await sensors.publish_sensor("dca_zone", analysis.zone.name_ru)
        await sensors.publish_sensor("dca_risk_score", analysis.risk_score)

        logger.info(f"DCA: zone={analysis.zone.value}, next_level=${analysis.next_level:.2f}")

    except Exception as e:
        logger.error(f"DCA job failed: {e}")
    finally:
        await calculator.close()


async def correlation_job() -> None:
    """
    Correlation Tracker job.

    Runs every 4 hours to calculate asset correlations
    and update HA sensors.
    """
    from service.analysis.correlation import get_correlation_tracker
    from service.ha import get_sensors_manager

    logger.info("Starting correlation tracker job")

    tracker = get_correlation_tracker()
    sensors = get_sensors_manager()

    try:
        analysis = await tracker.analyze()

        if analysis.btc_eth:
            await sensors.publish_sensor("btc_eth_correlation", round(analysis.btc_eth.correlation_30d, 3))
        if analysis.btc_sp500:
            await sensors.publish_sensor("btc_sp500_correlation", round(analysis.btc_sp500.correlation_30d, 3))
        await sensors.publish_sensor("correlation_status", analysis.overall_status.name_ru)

        logger.info(f"Correlation: status={analysis.overall_status.value}")

    except Exception as e:
        logger.error(f"Correlation job failed: {e}")
    finally:
        await tracker.close()


async def volatility_job() -> None:
    """
    Volatility Tracker job.

    Runs every hour to track market volatility
    and update HA sensors for all currencies.
    """
    from service.analysis.volatility import get_volatility_tracker
    from service.ha import get_sensors_manager

    logger.info("Starting volatility tracker job")

    tracker = get_volatility_tracker()
    sensors = get_sensors_manager()
    symbols = await get_currency_list_async()
    base_symbols = [s.split("/")[0] for s in symbols]

    try:
        volatility_data: dict[str, float] = {}
        highest_percentile = 0
        overall_status = "Низкая"

        for symbol in base_symbols:
            try:
                # Map symbol to CoinGecko ID
                coin_id_map = {
                    "BTC": "bitcoin",
                    "ETH": "ethereum",
                    "SOL": "solana",
                    "TON": "the-open-network",
                    "AR": "arweave",
                    "RENDER": "render-token",
                    "TAO": "bittensor",
                    "FET": "fetch-ai",
                    "NEAR": "near",
                    "INJ": "injective-protocol",
                }
                coin_id = coin_id_map.get(symbol, symbol.lower())
                data = await tracker.analyze(coin_id)
                volatility_data[symbol] = round(data.volatility_30d, 2)
                
                if data.percentile > highest_percentile:
                    highest_percentile = data.percentile
                    overall_status = data.status.name_ru

            except Exception as e:
                logger.warning(f"Volatility analysis failed for {symbol}: {e}")
                volatility_data[symbol] = 0

            await asyncio.sleep(0.3)  # Rate limiting

        await sensors.publish_sensor("volatility_30d", volatility_data)
        await sensors.publish_sensor("volatility_percentile", highest_percentile)
        await sensors.publish_sensor("volatility_status", overall_status)

        logger.info(f"Volatility updated for {len(volatility_data)} symbols")

    except Exception as e:
        logger.error(f"Volatility job failed: {e}")
    finally:
        await tracker.close()


async def unlocks_job() -> None:
    """
    Token Unlock Tracker job.

    Runs every 6 hours to track token unlock events
    and update HA sensors.
    """
    from service.analysis.unlocks import get_unlock_tracker
    from service.ha import get_sensors_manager
    from service.ha_integration import notify

    logger.info("Starting unlock tracker job")

    tracker = get_unlock_tracker()
    sensors = get_sensors_manager()

    try:
        analysis = await tracker.analyze()

        await sensors.publish_sensor("unlocks_next_7d", analysis.next_7d_count)
        await sensors.publish_sensor(
            "unlock_next_event",
            analysis.next_event.to_dict()["summary_ru"] if analysis.next_event else "Нет данных",
        )
        await sensors.publish_sensor("unlock_risk_level", analysis.highest_risk.name_ru)

        # Alert on high-risk unlocks
        high_risk = [u for u in analysis.unlocks if u.risk.value == "high" and u.days_until <= 3]
        for unlock in high_risk:
            await notify(
                message=f"{unlock.token}: разлок {unlock._format_usd(unlock.value_usd)} через {unlock.days_until} дн.",
                title=f"⚠️ Крупный разлок {unlock.token}",
                notification_id=f"unlock_{unlock.token}",
            )

        logger.info(f"Unlocks: {analysis.next_7d_count} in next 7 days")

    except Exception as e:
        logger.error(f"Unlocks job failed: {e}")


async def macro_job() -> None:
    """
    Macro Calendar job.

    Runs every 12 hours to track economic events
    and update HA sensors.
    """
    from service.analysis.macro import get_macro_calendar
    from service.ha import get_sensors_manager
    from service.ha_integration import notify

    logger.info("Starting macro calendar job")

    calendar = get_macro_calendar()
    sensors = get_sensors_manager()

    try:
        analysis = await calendar.analyze()

        await sensors.publish_sensor(
            "next_macro_event",
            analysis.next_event.to_dict()["summary"] if analysis.next_event else "Нет событий",
        )
        await sensors.publish_sensor("days_to_fomc", analysis.days_to_fomc)
        await sensors.publish_sensor("macro_risk_week", analysis.week_risk.name_ru)

        # Alert before FOMC
        if analysis.days_to_fomc <= 2:
            await notify(
                message=f"Заседание FOMC через {analysis.days_to_fomc} дней. Ожидайте волатильность.",
                title="📅 FOMC Meeting Soon",
                notification_id="fomc_reminder",
            )

        logger.info(f"Macro: days_to_fomc={analysis.days_to_fomc}, risk={analysis.week_risk.value}")

    except Exception as e:
        logger.error(f"Macro job failed: {e}")


async def arbitrage_job() -> None:
    """
    Arbitrage Scanner job.

    Runs every 2 minutes to scan for arbitrage opportunities
    and update HA sensors for all currencies.
    """
    from service.analysis.arbitrage import get_arbitrage_scanner
    from service.ha import get_sensors_manager
    from service.ha_integration import notify

    logger.debug("Running arbitrage scanner")

    scanner = get_arbitrage_scanner()
    sensors = get_sensors_manager()

    try:
        analysis = await scanner.analyze()

        # Build dict of spreads for all symbols from analysis
        arb_spreads: dict[str, float] = {}
        for spread in analysis.spreads:
            # Convert BTCUSDT -> BTC
            coin = spread.symbol.replace("USDT", "")
            arb_spreads[coin] = round(spread.spread_pct, 3)

        await sensors.publish_sensor("arb_spreads", arb_spreads)

        # Best funding arb
        if analysis.best_funding:
            await sensors.publish_sensor(
                "funding_arb_best",
                f"{analysis.best_funding.symbol}: {analysis.best_funding.annualized_rate:.1f}% APR",
            )
        else:
            await sensors.publish_sensor("funding_arb_best", "Нет")

        await sensors.publish_sensor("arb_opportunity", analysis.overall_opportunity.name_ru)

        # Alert on good opportunities
        if analysis.overall_opportunity.value in ["good", "excellent"]:
            await notify(
                message=analysis._get_summary_ru(),
                title="💰 Арбитражная возможность",
                notification_id="arb_opportunity",
            )

    except Exception as e:
        logger.error(f"Arbitrage job failed: {e}")
    finally:
        await scanner.close()


async def profit_taking_job() -> None:
    """
    Profit Taking Advisor job.

    Runs every hour to calculate take profit levels
    and update HA sensors for all currencies.
    """
    from service.analysis.profit_taking import get_profit_advisor
    from service.ha import get_sensors_manager
    from service.ha_integration import notify

    logger.info("Starting profit taking advisor job")

    advisor = get_profit_advisor()
    sensors = get_sensors_manager()
    symbols = await get_currency_list_async()
    base_symbols = [s.split("/")[0] for s in symbols]

    try:
        tp_levels_data: dict[str, dict[str, float]] = {}
        best_action = None
        max_greed = 0

        for symbol in base_symbols:
            try:
                analysis = await advisor.analyze(symbol)

                # Build TP levels for this symbol
                if analysis.tp_levels:
                    tp_data = {}
                    for i, level in enumerate(analysis.tp_levels[:2]):
                        tp_data[f"level_{i + 1}"] = round(level.price, 2)
                    tp_levels_data[symbol] = tp_data

                # Track highest greed for overall action
                if analysis.greed_score > max_greed:
                    max_greed = analysis.greed_score
                    best_action = analysis

            except Exception as e:
                logger.warning(f"Profit taking analysis failed for {symbol}: {e}")

            await asyncio.sleep(0.3)  # Rate limiting

        await sensors.publish_sensor("tp_levels", tp_levels_data)

        # Use the analysis with highest greed for overall metrics
        if best_action:
            await sensors.publish_sensor("profit_action", best_action.action.name_ru)
            await sensors.publish_sensor("greed_level", best_action.greed_score)

            # Alert on scale out signals
            if best_action.action.value in ["scale_out_50", "take_profit"]:
                await notify(
                    message=best_action._get_recommendation_ru(),
                    title=f"💰 {best_action.action.name_ru}",
                    notification_id="profit_taking_signal",
                )

            logger.info(f"Profit taking: action={best_action.action.value}, greed={best_action.greed_level.value}")

        logger.info(f"TP levels updated for {len(tp_levels_data)} symbols")

    except Exception as e:
        logger.error(f"Profit taking job failed: {e}")
    finally:
        await advisor.close()


async def currency_list_monitor_job() -> None:
    """
    Currency List Monitor job.

    Runs every 10 minutes to check for changes in the dynamic currency list.
    Handles automatic cleanup of removed currencies and loading of new currencies.
    Updates notification systems and consolidated sensors.
    """
    from service.currency_manager import get_currency_manager
    from service.ha import get_sensors_manager
    from service.unified_sensors import get_unified_sensor_manager

    logger.info("Starting currency list monitor job")

    try:
        # Get managers
        currency_manager = get_currency_manager()
        sensors_manager = get_sensors_manager()
        unified_manager = get_unified_sensor_manager(sensors_manager)

        # Initialize currency manager if needed
        if not hasattr(currency_manager, "_initialized"):
            await currency_manager.initialize()
            currency_manager._initialized = True

        # Check for currency list changes
        await currency_manager.check_for_changes()

        # Update consolidated sensors
        await unified_manager.update_consolidated_sensors()
        
        # Update crypto_currency_list sensor with current list
        current_currencies = await get_currency_list_async()
        await sensors_manager.publish_sensor("crypto_currency_list", current_currencies)
        logger.debug(f"Updated crypto_currency_list sensor: {current_currencies}")

        logger.info("Currency list monitor job completed")

    except Exception as e:
        logger.error(f"Currency list monitor job failed: {e}")


async def traditional_finance_job() -> None:
    """
    Traditional Finance job.

    Runs every 15 minutes to fetch prices for:
    - Metals (Gold, Silver, Platinum)
    - Indices (S&P 500, NASDAQ, Dow Jones, DAX)
    - Forex (EUR/USD, GBP/USD, DXY)
    - Commodities (Oil Brent, WTI, Natural Gas)
    """
    from service.analysis.traditional import get_traditional_tracker
    from service.backfill.traditional_backfill import get_traditional_backfill
    from service.ha import get_sensors_manager

    logger.info("Starting traditional finance job")

    tracker = get_traditional_tracker()
    backfill = get_traditional_backfill()
    sensors = get_sensors_manager()

    try:
        status = await tracker.fetch_all()

        # Metals
        if status.gold:
            await sensors.publish_sensor("gold_price", round(status.gold.price, 2))
            await sensors._publish_attributes(
                "gold_price",
                {
                    "change_24h": status.gold.change_percent,
                    "high": status.gold.high_24h,
                    "low": status.gold.low_24h,
                },
            )
        if status.silver:
            await sensors.publish_sensor("silver_price", round(status.silver.price, 2))
            await sensors._publish_attributes(
                "silver_price",
                {
                    "change_24h": status.silver.change_percent,
                },
            )
        if status.platinum:
            await sensors.publish_sensor("platinum_price", round(status.platinum.price, 2))

        # Indices
        if status.sp500:
            await sensors.publish_sensor("sp500_price", round(status.sp500.price, 2))
            await sensors._publish_attributes(
                "sp500_price",
                {
                    "change_24h": status.sp500.change_percent,
                },
            )
        if status.nasdaq:
            await sensors.publish_sensor("nasdaq_price", round(status.nasdaq.price, 2))
            await sensors._publish_attributes(
                "nasdaq_price",
                {
                    "change_24h": status.nasdaq.change_percent,
                },
            )
        if status.dji:
            await sensors.publish_sensor("dji_price", round(status.dji.price, 2))
            await sensors._publish_attributes(
                "dji_price",
                {
                    "change_24h": status.dji.change_percent,
                },
            )
        if status.dax:
            await sensors.publish_sensor("dax_price", round(status.dax.price, 2))
            await sensors._publish_attributes(
                "dax_price",
                {
                    "change_24h": status.dax.change_percent,
                },
            )

        # Forex
        if status.eur_usd:
            await sensors.publish_sensor("eur_usd", round(status.eur_usd.price, 4))
            await sensors._publish_attributes(
                "eur_usd",
                {
                    "change_24h": status.eur_usd.change_percent,
                },
            )
        if status.gbp_usd:
            await sensors.publish_sensor("gbp_usd", round(status.gbp_usd.price, 4))
        if status.dxy:
            await sensors.publish_sensor("dxy_index", round(status.dxy.price, 2))
            await sensors._publish_attributes(
                "dxy_index",
                {
                    "change_24h": status.dxy.change_percent,
                },
            )

        # Commodities
        if status.oil_brent:
            await sensors.publish_sensor("oil_brent", round(status.oil_brent.price, 2))
            await sensors._publish_attributes(
                "oil_brent",
                {
                    "change_24h": status.oil_brent.change_percent,
                },
            )
        if status.oil_wti:
            await sensors.publish_sensor("oil_wti", round(status.oil_wti.price, 2))
        if status.natural_gas:
            await sensors.publish_sensor("natural_gas", round(status.natural_gas.price, 3))

        # History status - dict {symbol: {start: ts, stop: ts}}
        try:
            history_status = await backfill.get_history_status()
            await sensors.publish_sensor("traditional_history_status", history_status)
        except Exception as e:
            logger.warning(f"Failed to get traditional history status: {e}")

        logger.info("Traditional finance data updated")

    except Exception as e:
        logger.error(f"Traditional finance job failed: {e}")
    finally:
        await tracker.close()


async def traditional_backfill_job() -> None:
    """
    Traditional assets daily backfill job.

    Runs once a day to update historical data for traditional assets.
    Uses Yahoo Finance with Stooq fallback.
    """
    from service.backfill.traditional_backfill import TRADITIONAL_ASSETS, get_traditional_backfill

    logger.info("Starting traditional backfill job")

    backfill = get_traditional_backfill()
    success_count = 0
    failure_count = 0

    for symbol in TRADITIONAL_ASSETS.keys():
        try:
            count = await backfill.backfill_asset(symbol, years=1)
            if count > 0:
                success_count += 1
                logger.info(f"Traditional backfill {symbol}: {count} records")
            else:
                failure_count += 1
                logger.warning(f"Traditional backfill {symbol}: no data")
        except Exception as e:
            failure_count += 1
            logger.error(f"Traditional backfill {symbol} failed: {e}")

        # Rate limiting
        await asyncio.sleep(3.0)

    logger.info(
        f"Traditional backfill completed: {success_count} success, {failure_count} failed"
    )


async def ai_analysis_job() -> None:
    """
    AI Market Analysis job.

    Runs periodically (default: every 24 hours) to generate AI-powered
    market analysis using Ollama or OpenAI.
    """
    from service.ai.analyzer import MarketAnalyzer, collect_market_data
    from service.ai.providers import create_ai_service
    from service.ha import get_sensors_manager
    from service.ha_integration import notify

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"[{current_time}] Starting AI analysis job")

    # Check if AI is enabled
    if not settings.AI_ENABLED:
        logger.info("AI analysis is disabled, skipping job")
        return

    sensors = get_sensors_manager()

    # Create AI service
    ai_service = create_ai_service(
        ai_enabled=settings.AI_ENABLED,
        ai_provider=settings.AI_PROVIDER,
        openai_api_key=settings.OPENAI_API_KEY,
        ollama_host=settings.OLLAMA_HOST,
        ollama_model=settings.OLLAMA_MODEL,
    )

    # Check if service is available
    is_available = await ai_service.is_available()
    if not is_available:
        logger.warning(f"AI service not available (provider: {settings.AI_PROVIDER})")
        await sensors.publish_sensor("ai_daily_summary", "AI недоступен")
        await sensors.publish_sensor("ai_market_sentiment", "Unavailable")
        await sensors.publish_sensor("ai_provider", settings.AI_PROVIDER)
        return

    analyzer = MarketAnalyzer(ai_service)

    try:
        # Collect market data from various services
        from service.analysis import OnChainAnalyzer, DerivativesAnalyzer

        onchain = OnChainAnalyzer()
        derivatives = DerivativesAnalyzer()

        # Gather data
        fear_greed_data = None
        deriv_data = None
        btc_price = None
        btc_change = 0.0

        try:
            onchain_data = await onchain.analyze()
            if onchain_data.fear_greed:
                fear_greed_data = {
                    "value": onchain_data.fear_greed.value,
                    "label": onchain_data.fear_greed.classification,
                }
        except Exception as e:
            logger.warning(f"Failed to get on-chain data for AI: {e}")

        try:
            btc_deriv = await derivatives.analyze("BTC")
            if btc_deriv.funding:
                btc_price = btc_deriv.funding.mark_price
            deriv_data = {
                "funding_rate": btc_deriv.funding.rate if btc_deriv.funding else None,
                "long_short_ratio": btc_deriv.long_short.long_short_ratio if btc_deriv.long_short else None,
            }
        except Exception as e:
            logger.warning(f"Failed to get derivatives data for AI: {e}")

        await onchain.close()
        await derivatives.close()

        # Collect market data
        market_data = await collect_market_data(
            prices={"BTC/USDT": btc_price or 0},
            changes={"BTC/USDT": btc_change},
            fear_greed=fear_greed_data,
        )

        # Generate daily summary
        language = settings.AI_LANGUAGE
        result = await analyzer.generate_daily_summary(market_data, language=language)

        if result:
            # Update sensors
            await sensors.publish_sensor("ai_daily_summary", analyzer.get_summary_for_sensor())
            await sensors.publish_sensor("ai_market_sentiment", analyzer.get_sentiment_for_sensor())
            await sensors.publish_sensor("ai_recommendation", analyzer.get_recommendation_for_sensor())
            await sensors.publish_sensor("ai_last_analysis", analyzer.get_last_analysis_time())
            await sensors.publish_sensor("ai_provider", f"{result.provider}/{result.model}")

            logger.info(
                f"AI analysis completed: sentiment={result.sentiment}, "
                f"provider={result.provider}, model={result.model}"
            )

            # Send notification with AI summary
            if result.recommendation and result.recommendation not in ["N/A", "HOLD"]:
                await notify(
                    message=analyzer.get_summary_for_sensor(max_length=500),
                    title=f"🤖 AI: {result.sentiment or 'Analysis'}",
                    notification_id="ai_daily_summary",
                )
        else:
            logger.warning("AI analysis returned no result")
            await sensors.publish_sensor("ai_daily_summary", "Анализ недоступен")

    except Exception as e:
        logger.error(f"AI analysis job failed: {e}")
        await sensors.publish_sensor("ai_daily_summary", f"Ошибка: {str(e)[:50]}")
    finally:
        await ai_service.close()

