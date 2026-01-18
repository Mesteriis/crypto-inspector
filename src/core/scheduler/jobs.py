"""Scheduled jobs for the application.

This module contains all scheduled job functions that are registered
with the APScheduler.
"""

import asyncio
import logging
import os
import time
from datetime import UTC, datetime

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
                        "loaded_at": datetime.now(UTC),
                    },
                )
            await session.commit()
            logger.info(f"Saved {len(result.candlesticks)} candlesticks for {symbol} {interval_str}")

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
                            deriv_result.long_short.long_short_ratio if deriv_result.long_short else None
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
                    f"{symbol}: Score={score.total_score:.0f}, " f"Signal={score.signal}, Action={score.action}"
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
    logger.info(f"[{current_time}] Market analysis completed in {duration:.1f}s, " f"analyzed {len(results)} items")


async def investor_analysis_job() -> None:
    """
    Lazy Investor analysis job.

    Runs every hour to:
    - Calculate investor status (do nothing ok, market phase, etc.)
    - Update MQTT sensors for Home Assistant
    - Send alerts if critical conditions detected
    """
    from services.analysis import (
        CycleDetector,
        DerivativesAnalyzer,
        OnChainAnalyzer,
        get_investor_analyzer,
    )
    from services.ha_integration import notify
    from services.ha_sensors import get_sensors_manager

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
            # Note: dominance is not available in OnChainMetrics, would need separate API
            logger.info(f"On-chain: F&G={fear_greed}")
        except Exception as e:
            logger.warning(f"On-chain fetch failed: {e}")

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

        # Update MQTT sensors
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
            logger.info("Updated MQTT sensors")
        except Exception as e:
            logger.warning(f"Failed to update MQTT sensors: {e}")

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
        if len(status.red_flags) >= 3:
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
                phase_msg = f"Рынок в фазе: {status._get_phase_name_ru()}\n" f"{status.phase_description_ru}"
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
    and update MQTT sensors.
    """
    from services.analysis.altseason import AltseasonAnalyzer
    from services.ha_sensors import get_sensors_manager

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"[{current_time}] Starting altseason analysis job")

    analyzer = AltseasonAnalyzer()
    sensors = get_sensors_manager()

    try:
        data = await analyzer.analyze()
        logger.info(f"Altseason: index={data.altseason_index}, status={data.status}")

        # Update MQTT sensors
        await sensors.publish_sensor("altseason_index", data.altseason_index)
        await sensors.publish_sensor("altseason_status", data.status)

    except Exception as e:
        logger.error(f"Altseason job failed: {e}")
    finally:
        await analyzer.close()


async def stablecoin_job() -> None:
    """
    Stablecoin Flow job.

    Runs every 4 hours to track stablecoin market caps
    and update MQTT sensors.
    """
    from services.analysis.stablecoins import StablecoinAnalyzer
    from services.ha_sensors import get_sensors_manager

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"[{current_time}] Starting stablecoin analysis job")

    analyzer = StablecoinAnalyzer()
    sensors = get_sensors_manager()

    try:
        data = await analyzer.analyze()
        logger.info(f"Stablecoins: total={data.total_market_cap/1e9:.1f}B, " f"flow_24h={data.flow_24h_percent:.2f}%")

        # Update MQTT sensors
        await sensors.publish_sensor("stablecoin_total", round(data.total_market_cap / 1e9, 2))
        await sensors.publish_sensor("stablecoin_flow_24h", round(data.flow_24h_percent, 2))
        await sensors.publish_sensor("stablecoin_dominance", round(data.dominance_percent, 2))

    except Exception as e:
        logger.error(f"Stablecoin job failed: {e}")
    finally:
        await analyzer.close()


async def gas_tracker_job() -> None:
    """
    ETH Gas Tracker job.

    Runs every 5 minutes to fetch current gas prices
    and update MQTT sensors.
    """
    from services.analysis.gas import GasTracker
    from services.ha_sensors import get_sensors_manager

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"[{current_time}] Starting gas tracker job")

    tracker = GasTracker()
    sensors = get_sensors_manager()

    try:
        data = await tracker.get_gas_prices()
        logger.info(
            f"Gas prices: slow={data.slow}, standard={data.standard}, " f"fast={data.fast}, status={data.status}"
        )

        # Update MQTT sensors
        await sensors.publish_sensor("eth_gas_slow", data.slow)
        await sensors.publish_sensor("eth_gas_standard", data.standard)
        await sensors.publish_sensor("eth_gas_fast", data.fast)
        await sensors.publish_sensor("eth_gas_status", data.status)

    except Exception as e:
        logger.error(f"Gas tracker job failed: {e}")
    finally:
        await tracker.close()


async def whale_monitor_job() -> None:
    """
    Whale Activity Monitor job.

    Runs every 15 minutes to fetch large transactions
    and update MQTT sensors.
    """
    from services.analysis.whales import WhaleTracker
    from services.ha_integration import notify
    from services.ha_sensors import get_sensors_manager

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"[{current_time}] Starting whale monitor job")

    tracker = WhaleTracker()
    sensors = get_sensors_manager()

    try:
        data = await tracker.analyze()
        logger.info(f"Whales: transactions_24h={data.transactions_24h}, net_flow=${data.net_flow_usd:,.0f}")

        # Update MQTT sensors
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
    and update MQTT sensors.
    """
    from services.analysis.exchange_flow import ExchangeFlowTracker
    from services.ha_integration import notify
    from services.ha_sensors import get_sensors_manager

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"[{current_time}] Starting exchange flow job")

    tracker = ExchangeFlowTracker()
    sensors = get_sensors_manager()

    try:
        data = await tracker.get_exchange_flow()
        logger.info(f"Exchange flow: netflow={data.btc_netflow}, signal={data.signal}")

        # Update MQTT sensors with dictionary format
        await sensors._publish_state("exchange_netflows", {"BTC": round(data.btc_netflow, 2)})
        await sensors.publish_sensor("exchange_flow_signal", data.signal)

        # Alert on significant outflows (bullish signal)
        if data.btc_netflow < -5000:
            await notify(
                message=f"BTC отток с бирж: {abs(data.btc_netflow):.0f} BTC\nСигнал: {data.signal}",
                title="📈 Сильный отток BTC с бирж",
                notification_id="exchange_outflow_alert",
            )

    except Exception as e:
        logger.error(f"Exchange flow job failed: {e}")
    finally:
        await tracker.close()


async def liquidation_job() -> None:
    """
    Liquidation Levels job.

    Runs every hour to fetch liquidation clusters
    and update MQTT sensors.
    """
    from services.analysis.liquidations import LiquidationTracker
    from services.ha_integration import notify
    from services.ha_sensors import get_sensors_manager

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"[{current_time}] Starting liquidation analysis job")

    tracker = LiquidationTracker()
    sensors = get_sensors_manager()

    try:
        data = await tracker.get_liquidation_levels()
        logger.info(
            f"Liquidations: long_nearest={data.long_nearest}, "
            f"short_nearest={data.short_nearest}, risk={data.risk_level}"
        )

        # Update MQTT sensors with dictionary format
        await sensors._publish_state(
            "liq_levels",
            {
                "BTC": {
                    "long": data.long_nearest or 0,
                    "short": data.short_nearest or 0,
                }
            },
        )
        await sensors.publish_sensor("liq_risk_level", data.risk_level)

        # Alert on high risk
        if data.risk_level == "High":
            await notify(
                message=(
                    f"Высокий риск ликвидаций!\n"
                    f"Long: ${data.long_nearest:,.0f}\n"
                    f"Short: ${data.short_nearest:,.0f}"
                ),
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
    and MQTT sensors.
    """
    from services.ha_sensors import get_sensors_manager
    from services.portfolio import get_portfolio_manager

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"[{current_time}] Starting portfolio update job")

    portfolio = get_portfolio_manager()
    sensors = get_sensors_manager()

    try:
        # Check if portfolio has any holdings
        if not portfolio.get_holdings():
            logger.debug("No portfolio holdings configured, skipping")
            return

        status = await portfolio.calculate()
        logger.info(f"Portfolio: value={status.total_value:.2f}, pnl={status.total_pnl_percent:.2f}%")

        # Update MQTT sensors
        await sensors.publish_sensor("portfolio_value", round(status.total_value, 2))
        await sensors.publish_sensor("portfolio_pnl", round(status.total_pnl_percent, 2))
        await sensors.publish_sensor("portfolio_pnl_24h", round(status.change_24h_pct or 0, 2))
        await sensors.publish_sensor("portfolio_best", status.best_performer.symbol if status.best_performer else "N/A")
        await sensors.publish_sensor(
            "portfolio_worst", status.worst_performer.symbol if status.worst_performer else "N/A"
        )

    except Exception as e:
        logger.error(f"Portfolio job failed: {e}")


async def divergence_job() -> None:
    """
    Divergence Detection job.

    Runs every hour to detect RSI/MACD divergences
    and update MQTT sensors.
    """
    from services.analysis.divergences import DivergenceDetector
    from services.ha_integration import notify
    from services.ha_sensors import get_sensors_manager

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"[{current_time}] Starting divergence detection job")

    detector = DivergenceDetector()
    sensors = get_sensors_manager()
    symbols = get_symbols()
    base_symbols = [s.split("/")[0] for s in symbols]  # BTC/USDT -> BTC

    try:
        active_count = 0
        divergence_data = {}  # Dictionary for all symbols

        for symbol in base_symbols:
            divergences = await detector.detect_divergences(symbol)
            active_count += len(divergences)

            # Find most significant divergence for this symbol
            if divergences:
                # Prioritize by timeframe (4h, 1d are more significant)
                best = max(divergences, key=lambda d: d.timeframe in ["4h", "1d"])
                sensor_value = f"{best.divergence_type.capitalize()} {best.timeframe}"

                # Notify on significant divergences
                await notify(
                    message=(
                        f"{symbol}: {best.divergence_type} дивергенция на {best.timeframe}\n"
                        f"Индикатор: {best.indicator}\n"
                        f"Уверенность: {best.confidence:.0%}"
                    ),
                    title=f"📊 Дивергенция {symbol}",
                    notification_id=f"divergence_{symbol.lower()}_{best.timeframe}",
                )
            else:
                sensor_value = "None"

            # Add to dictionary
            divergence_data[symbol] = sensor_value
            logger.info(f"{symbol} divergences: {len(divergences)}")

        # Update with dictionary format
        await sensors._publish_state("divergences", divergence_data)
        await sensors.publish_sensor("divergences_active", active_count)

    except Exception as e:
        logger.error(f"Divergence job failed: {e}")


async def signal_history_job() -> None:
    """
    Signal History Update job.

    Runs every hour to update signal outcomes
    and recalculate win rates.
    """
    from services.analysis.signal_history import get_signal_tracker
    from services.ha_sensors import get_sensors_manager

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"[{current_time}] Starting signal history update job")

    tracker = get_signal_tracker()
    sensors = get_sensors_manager()

    try:
        # Update outcomes for pending signals
        await tracker.update_outcomes()

        # Get stats
        stats = await tracker.get_stats()
        logger.info(
            f"Signals: win_rate={stats.win_rate:.1f}%, "
            f"today={stats.signals_today}, last={stats.last_signal_description}"
        )

        # Update MQTT sensors
        await sensors.publish_sensor("signals_win_rate", round(stats.win_rate, 1))
        await sensors.publish_sensor("signals_today", stats.signals_today)
        await sensors.publish_sensor("signals_last", stats.last_signal_description or "Нет сигналов")

    except Exception as e:
        logger.error(f"Signal history job failed: {e}")


async def price_alerts_job() -> None:
    """
    Price Alerts Check job.

    Runs every minute to check price alerts
    and trigger notifications.
    """
    from services.alerts import get_alert_manager
    from services.ha_integration import notify
    from services.ha_sensors import get_sensors_manager

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
    and update MQTT sensors.
    """
    from services.exchange import get_bybit_portfolio
    from services.ha_sensors import get_sensors_manager

    logger.info("Starting Bybit sync job")

    portfolio = get_bybit_portfolio()
    sensors = get_sensors_manager()

    if not portfolio.is_configured:
        logger.debug("Bybit not configured, skipping")
        return

    try:
        account = await portfolio.get_account()
        pnl_24h = await portfolio.calculate_pnl(
            __import__("services.exchange.bybit_portfolio", fromlist=["PnlPeriod"]).PnlPeriod.DAY
        )
        pnl_7d = await portfolio.calculate_pnl(
            __import__("services.exchange.bybit_portfolio", fromlist=["PnlPeriod"]).PnlPeriod.WEEK
        )

        # Update MQTT sensors - Wallet
        await sensors.publish_sensor("bybit_balance", round(account.total_equity, 2))
        await sensors.publish_sensor("bybit_pnl_24h", round(pnl_24h.total_pnl, 2))
        await sensors.publish_sensor("bybit_pnl_7d", round(pnl_7d.total_pnl, 2))
        await sensors.publish_sensor("bybit_positions", len(account.positions))
        await sensors.publish_sensor("bybit_unrealized_pnl", round(account.total_unrealized_pnl, 2))

        # Update MQTT sensors - Earn (Flexible Savings + OnChain)
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
        await sensors.publish_sensor("bybit_total_portfolio", round(total_portfolio, 2))

        logger.info(
            f"Bybit sync: wallet=${account.total_equity:.2f}, earn=${earn_balance:.2f}, "
            f"total=${total_portfolio:.2f}, positions={len(account.positions)}, earn_positions={earn_count}"
        )

    except Exception as e:
        logger.error(f"Bybit sync job failed: {e}")


async def dca_job() -> None:
    """
    DCA Calculator job.

    Runs every hour to calculate optimal DCA levels
    and update MQTT sensors.
    """
    from services.analysis.dca import get_dca_calculator
    from services.ha_sensors import get_sensors_manager

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
    and update MQTT sensors.
    """
    from services.analysis.correlation import get_correlation_tracker
    from services.ha_sensors import get_sensors_manager

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
    and update MQTT sensors.
    """
    from services.analysis.volatility import get_volatility_tracker
    from services.ha_sensors import get_sensors_manager

    logger.info("Starting volatility tracker job")

    tracker = get_volatility_tracker()
    sensors = get_sensors_manager()

    try:
        data = await tracker.analyze("BTC")

        # Update with dictionary format for multi-currency support
        await sensors._publish_state("volatility_30d", {"BTC": round(data.volatility_30d, 2)})
        await sensors.publish_sensor("volatility_percentile", data.percentile)
        await sensors.publish_sensor("volatility_status", data.status.name_ru)

        logger.info(f"Volatility: {data.volatility_30d:.1f}%, percentile={data.percentile}")

    except Exception as e:
        logger.error(f"Volatility job failed: {e}")
    finally:
        await tracker.close()


async def unlocks_job() -> None:
    """
    Token Unlock Tracker job.

    Runs every 6 hours to track token unlock events
    and update MQTT sensors.
    """
    from services.analysis.unlocks import get_unlock_tracker
    from services.ha_integration import notify
    from services.ha_sensors import get_sensors_manager

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
    and update MQTT sensors.
    """
    from services.analysis.macro import get_macro_calendar
    from services.ha_integration import notify
    from services.ha_sensors import get_sensors_manager

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
    and update MQTT sensors.
    """
    from services.analysis.arbitrage import get_arbitrage_scanner
    from services.ha_integration import notify
    from services.ha_sensors import get_sensors_manager

    logger.debug("Running arbitrage scanner")

    scanner = get_arbitrage_scanner()
    sensors = get_sensors_manager()

    try:
        analysis = await scanner.analyze()

        # Use dictionary format for multi-currency support
        arb_spreads = {}
        if analysis.best_spread:
            arb_spreads["BTC"] = round(analysis.best_spread.spread_pct, 3)
        await sensors._publish_state("arb_spreads", arb_spreads)

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
    and update MQTT sensors.
    """
    from services.analysis.profit_taking import get_profit_advisor
    from services.ha_integration import notify
    from services.ha_sensors import get_sensors_manager

    logger.info("Starting profit taking advisor job")

    advisor = get_profit_advisor()
    sensors = get_sensors_manager()

    try:
        analysis = await advisor.analyze("BTC")

        # Use dictionary format for multi-currency support
        if analysis.tp_levels:
            tp_data = {}
            for i, level in enumerate(analysis.tp_levels[:2]):
                tp_data[f"level_{i+1}"] = round(level.price, 2)
            await sensors._publish_state("tp_levels", {"BTC": tp_data})

        await sensors.publish_sensor("profit_action", analysis.action.name_ru)
        await sensors.publish_sensor("greed_level", analysis.greed_level.name_ru)

        # Alert on scale out signals
        if analysis.action.value in ["scale_out_50", "take_profit"]:
            await notify(
                message=analysis._get_recommendation_ru(),
                title=f"💰 {analysis.action.name_ru}",
                notification_id="profit_taking_signal",
            )

        logger.info(f"Profit taking: action={analysis.action.value}, greed={analysis.greed_level.value}")

    except Exception as e:
        logger.error(f"Profit taking job failed: {e}")
    finally:
        await advisor.close()


async def traditional_finance_job() -> None:
    """
    Traditional Finance job.

    Runs every 15 minutes to fetch prices for:
    - Metals (Gold, Silver, Platinum)
    - Indices (S&P 500, NASDAQ, Dow Jones, DAX)
    - Forex (EUR/USD, GBP/USD, DXY)
    - Commodities (Oil Brent, WTI, Natural Gas)
    """
    from services.analysis.traditional import get_traditional_tracker
    from services.ha_sensors import get_sensors_manager

    logger.info("Starting traditional finance job")

    tracker = get_traditional_tracker()
    sensors = get_sensors_manager()

    try:
        status = await tracker.fetch_all()

        # Metals
        if status.gold:
            await sensors._publish_state("gold_price", round(status.gold.price, 2))
            await sensors._publish_attributes(
                "gold_price",
                {
                    "change_24h": status.gold.change_percent,
                    "high": status.gold.high_24h,
                    "low": status.gold.low_24h,
                },
            )
        if status.silver:
            await sensors._publish_state("silver_price", round(status.silver.price, 2))
            await sensors._publish_attributes(
                "silver_price",
                {
                    "change_24h": status.silver.change_percent,
                },
            )
        if status.platinum:
            await sensors._publish_state("platinum_price", round(status.platinum.price, 2))

        # Indices
        if status.sp500:
            await sensors._publish_state("sp500_price", round(status.sp500.price, 2))
            await sensors._publish_attributes(
                "sp500_price",
                {
                    "change_24h": status.sp500.change_percent,
                },
            )
        if status.nasdaq:
            await sensors._publish_state("nasdaq_price", round(status.nasdaq.price, 2))
            await sensors._publish_attributes(
                "nasdaq_price",
                {
                    "change_24h": status.nasdaq.change_percent,
                },
            )
        if status.dji:
            await sensors._publish_state("dji_price", round(status.dji.price, 2))
            await sensors._publish_attributes(
                "dji_price",
                {
                    "change_24h": status.dji.change_percent,
                },
            )
        if status.dax:
            await sensors._publish_state("dax_price", round(status.dax.price, 2))
            await sensors._publish_attributes(
                "dax_price",
                {
                    "change_24h": status.dax.change_percent,
                },
            )

        # Forex
        if status.eur_usd:
            await sensors._publish_state("eur_usd", round(status.eur_usd.price, 4))
            await sensors._publish_attributes(
                "eur_usd",
                {
                    "change_24h": status.eur_usd.change_percent,
                },
            )
        if status.gbp_usd:
            await sensors._publish_state("gbp_usd", round(status.gbp_usd.price, 4))
        if status.dxy:
            await sensors._publish_state("dxy_index", round(status.dxy.price, 2))
            await sensors._publish_attributes(
                "dxy_index",
                {
                    "change_24h": status.dxy.change_percent,
                },
            )

        # Commodities
        if status.oil_brent:
            await sensors._publish_state("oil_brent", round(status.oil_brent.price, 2))
            await sensors._publish_attributes(
                "oil_brent",
                {
                    "change_24h": status.oil_brent.change_percent,
                },
            )
        if status.oil_wti:
            await sensors._publish_state("oil_wti", round(status.oil_wti.price, 2))
        if status.natural_gas:
            await sensors._publish_state("natural_gas", round(status.natural_gas.price, 3))

        logger.info("Traditional finance data updated")

    except Exception as e:
        logger.error(f"Traditional finance job failed: {e}")
    finally:
        await tracker.close()
