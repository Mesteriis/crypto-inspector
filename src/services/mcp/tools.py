"""
MCP Tools for Crypto Inspect.

Exposes all data endpoints as MCP tools for AI agents.
"""

import logging
import os
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import text

logger = logging.getLogger(__name__)


def get_symbols() -> list[str]:
    """Get configured symbols from environment (deprecated - use get_currency_list instead)."""
    symbols_env = os.environ.get("HA_SYMBOLS", "BTC/USDT,ETH/USDT")
    return [s.strip() for s in symbols_env.split(",") if s.strip()]


def get_currency_list() -> list[str]:
    """Get the dynamic currency list from Home Assistant input_select helper.

    This is the single source of truth for currency selections across the application.
    Returns coin symbols without exchange suffix (e.g., ["BTC", "ETH"]).

    Returns:
        List of currency symbols (e.g., ["BTC", "ETH"])
    """
    from services.ha_sensors import get_currency_list as get_dynamic_currency_list

    # Get full currency pairs and extract base symbols
    full_pairs = get_dynamic_currency_list()
    return [pair.split("/")[0] for pair in full_pairs if "/" in pair]


# ============================================================================
# CRYPTO PRICE TOOLS
# ============================================================================


async def get_crypto_prices() -> dict[str, Any]:
    """
    Get current cryptocurrency prices.

    Returns prices for all configured trading pairs including:
    - Current price
    - 24h change percentage
    - 24h high/low
    - 24h volume
    """
    from db.session import async_session_maker

    symbols = get_currency_list()
    result = {}

    try:
        async with async_session_maker() as session:
            for symbol in symbols:
                query = text("""
                    SELECT close_price, timestamp
                    FROM candlestick_records
                    WHERE symbol = :symbol AND interval = '1m'
                    ORDER BY timestamp DESC
                    LIMIT 1
                """)
                res = await session.execute(query, {"symbol": symbol})
                row = res.fetchone()

                if row:
                    result[symbol] = {
                        "price": float(row[0]),
                        "timestamp": row[1],
                        "updated_at": datetime.now(UTC).isoformat(),
                    }
    except Exception as e:
        logger.error(f"Error getting crypto prices: {e}")
        result["error"] = str(e)

    return {
        "prices": result,
        "symbols": symbols,
        "count": len(result),
    }


async def get_crypto_analysis(symbol: str) -> dict[str, Any]:
    """
    Get full technical analysis for a cryptocurrency.

    Args:
        symbol: Coin symbol (e.g., BTC, ETH, SOL)

    Returns:
        Technical analysis including:
        - RSI, MACD, Bollinger Bands
        - Support/resistance levels
        - Pattern detection
        - Composite score
    """
    from services.analysis import ScoringEngine

    symbol = symbol.upper()

    try:
        engine = ScoringEngine()
        analysis = await engine.analyze(symbol)
        return analysis.to_dict()
    except Exception as e:
        logger.error(f"Error getting analysis for {symbol}: {e}")
        return {"error": str(e), "symbol": symbol}


async def get_candlesticks(
    symbol: str,
    interval: str = "1h",
    limit: int = 100,
) -> dict[str, Any]:
    """
    Get historical candlestick (OHLCV) data.

    Args:
        symbol: Trading pair (e.g., BTC/USDT, ETH/USDT)
        interval: Candle interval (1m, 5m, 15m, 1h, 4h, 1d)
        limit: Number of candles to return (max 1000)

    Returns:
        List of candlesticks with open, high, low, close, volume
    """
    from db.session import async_session_maker

    if "/" not in symbol:
        symbol = f"{symbol}/USDT"

    limit = min(limit, 1000)

    try:
        async with async_session_maker() as session:
            query = text("""
                SELECT timestamp, open_price, high_price, low_price, close_price, volume
                FROM candlestick_records
                WHERE symbol = :symbol AND interval = :interval
                ORDER BY timestamp DESC
                LIMIT :limit
            """)
            result = await session.execute(query, {"symbol": symbol, "interval": interval, "limit": limit})
            rows = result.fetchall()

            candles = []
            for row in reversed(rows):  # Chronological order
                candles.append(
                    {
                        "timestamp": row[0],
                        "open": float(row[1]),
                        "high": float(row[2]),
                        "low": float(row[3]),
                        "close": float(row[4]),
                        "volume": float(row[5]) if row[5] else 0,
                    }
                )

            return {
                "symbol": symbol,
                "interval": interval,
                "candles": candles,
                "count": len(candles),
            }
    except Exception as e:
        logger.error(f"Error getting candlesticks: {e}")
        return {"error": str(e)}


# ============================================================================
# MARKET OVERVIEW TOOLS
# ============================================================================


async def get_market_summary() -> dict[str, Any]:
    """
    Get comprehensive market summary.

    Returns overview of:
    - All configured symbols with current prices
    - Fear & Greed Index
    - BTC dominance
    - Altseason status
    - Market phase
    """
    from services.analysis import OnChainAnalyzer
    from services.analysis.altseason import get_altseason_tracker

    try:
        onchain = OnChainAnalyzer()
        altseason = get_altseason_tracker()

        fear_greed = await onchain.get_fear_greed_index()
        btc_dom = await onchain.get_btc_dominance()
        alt_status = await altseason.get_status()

        return {
            "fear_greed": fear_greed,
            "btc_dominance": btc_dom,
            "altseason": alt_status.to_dict() if alt_status else None,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting market summary: {e}")
        return {"error": str(e)}


async def get_fear_greed_index() -> dict[str, Any]:
    """
    Get current Fear & Greed Index.

    Returns:
        Value (0-100), classification, and trend
        - 0-25: Extreme Fear
        - 25-45: Fear
        - 45-55: Neutral
        - 55-75: Greed
        - 75-100: Extreme Greed
    """
    from services.analysis import OnChainAnalyzer

    try:
        onchain = OnChainAnalyzer()
        result = await onchain.get_fear_greed_index()
        return result
    except Exception as e:
        logger.error(f"Error getting fear/greed: {e}")
        return {"error": str(e)}


async def get_btc_dominance() -> dict[str, Any]:
    """
    Get current BTC dominance percentage.

    Returns:
        BTC market cap as percentage of total crypto market cap
    """
    from services.analysis import OnChainAnalyzer

    try:
        onchain = OnChainAnalyzer()
        result = await onchain.get_btc_dominance()
        return {"btc_dominance": result}
    except Exception as e:
        logger.error(f"Error getting BTC dominance: {e}")
        return {"error": str(e)}


async def get_altseason_index() -> dict[str, Any]:
    """
    Get Altseason Index status.

    Returns:
        - Index value (0-100)
        - Status: Bitcoin Season / Alt Season / Neutral
        - Top performing altcoins
    """
    from services.analysis.altseason import get_altseason_tracker

    try:
        tracker = get_altseason_tracker()
        status = await tracker.get_status()
        return status.to_dict() if status else {"error": "No data"}
    except Exception as e:
        logger.error(f"Error getting altseason: {e}")
        return {"error": str(e)}


# ============================================================================
# TRADITIONAL FINANCE TOOLS
# ============================================================================


async def get_traditional_finance() -> dict[str, Any]:
    """
    Get traditional finance asset prices.

    Returns data for:
    - Metals: Gold, Silver, Platinum
    - Indices: S&P 500, NASDAQ, Dow Jones, DAX
    - Forex: EUR/USD, GBP/USD, DXY
    - Commodities: Brent Oil, WTI Oil, Natural Gas
    """
    from services.analysis.traditional import get_traditional_tracker

    try:
        tracker = get_traditional_tracker()
        status = await tracker.fetch_all()
        return status.to_dict()
    except Exception as e:
        logger.error(f"Error getting traditional finance: {e}")
        return {"error": str(e)}


# ============================================================================
# ON-CHAIN DATA TOOLS
# ============================================================================


async def get_whale_alerts() -> dict[str, Any]:
    """
    Get recent whale movement alerts.

    Returns:
        - Large BTC/ETH transfers (>100 BTC, >1000 ETH)
        - Exchange inflows/outflows
        - Net flow direction
    """
    from services.analysis.whales import get_whale_monitor

    try:
        monitor = get_whale_monitor()
        alerts = await monitor.get_recent_alerts(hours=24)
        return {
            "alerts": [a.to_dict() for a in alerts],
            "count": len(alerts),
            "period": "24h",
        }
    except Exception as e:
        logger.error(f"Error getting whale alerts: {e}")
        return {"error": str(e)}


async def get_exchange_flow() -> dict[str, Any]:
    """
    Get exchange flow data (inflows/outflows).

    Returns:
        - BTC/ETH exchange netflow
        - Signal interpretation (bullish/bearish)
        - Historical trend
    """
    from services.analysis.exchange_flow import get_exchange_flow_tracker

    try:
        tracker = get_exchange_flow_tracker()
        status = await tracker.get_status()
        return status.to_dict() if status else {"error": "No data"}
    except Exception as e:
        logger.error(f"Error getting exchange flow: {e}")
        return {"error": str(e)}


# ============================================================================
# DERIVATIVES DATA TOOLS
# ============================================================================


async def get_funding_rates() -> dict[str, Any]:
    """
    Get perpetual futures funding rates.

    Returns:
        - Current funding rates for major pairs
        - Interpretation (bullish/bearish)
        - Historical average
    """
    from services.analysis import DerivativesAnalyzer

    try:
        analyzer = DerivativesAnalyzer()
        result = await analyzer.get_funding_rates()
        return result
    except Exception as e:
        logger.error(f"Error getting funding rates: {e}")
        return {"error": str(e)}


async def get_liquidation_levels(symbol: str = "BTC") -> dict[str, Any]:
    """
    Get liquidation level heatmap data.

    Args:
        symbol: Coin symbol (BTC, ETH)

    Returns:
        - Nearest long liquidation levels
        - Nearest short liquidation levels
        - Risk assessment
    """
    from services.analysis.liquidations import get_liquidation_tracker

    try:
        tracker = get_liquidation_tracker()
        levels = await tracker.get_levels(symbol.upper())
        return levels.to_dict() if levels else {"error": "No data"}
    except Exception as e:
        logger.error(f"Error getting liquidation levels: {e}")
        return {"error": str(e)}


# ============================================================================
# CORRELATION & VOLATILITY TOOLS
# ============================================================================


async def get_correlations() -> dict[str, Any]:
    """
    Get crypto-to-traditional asset correlations.

    Returns:
        - BTC/ETH correlation
        - BTC/S&P500 correlation
        - BTC/Gold correlation
        - BTC/DXY correlation
    """
    from services.analysis.correlation import get_correlation_tracker

    try:
        tracker = get_correlation_tracker()
        status = await tracker.get_status()
        return status.to_dict() if status else {"error": "No data"}
    except Exception as e:
        logger.error(f"Error getting correlations: {e}")
        return {"error": str(e)}


async def get_volatility() -> dict[str, Any]:
    """
    Get volatility metrics.

    Returns:
        - BTC 30-day volatility
        - Volatility percentile (vs history)
        - Status: Low/Normal/High/Extreme
    """
    from services.analysis.volatility import get_volatility_tracker

    try:
        tracker = get_volatility_tracker()
        status = await tracker.get_status()
        return status.to_dict() if status else {"error": "No data"}
    except Exception as e:
        logger.error(f"Error getting volatility: {e}")
        return {"error": str(e)}


# ============================================================================
# MACRO & EVENTS TOOLS
# ============================================================================


async def get_macro_events() -> dict[str, Any]:
    """
    Get upcoming macro economic events.

    Returns:
        - Next FOMC meeting
        - CPI/PPI releases
        - Week risk level
    """
    from services.analysis.macro import get_macro_calendar

    try:
        calendar = get_macro_calendar()
        analysis = await calendar.analyze()
        return analysis.to_dict() if analysis else {"error": "No data"}
    except Exception as e:
        logger.error(f"Error getting macro events: {e}")
        return {"error": str(e)}


async def get_token_unlocks() -> dict[str, Any]:
    """
    Get upcoming token unlock events.

    Returns:
        - Unlocks in next 7 days
        - Unlock amounts and valuations
        - Risk assessment
    """
    from services.analysis.unlocks import get_unlocks_tracker

    try:
        tracker = get_unlocks_tracker()
        unlocks = await tracker.get_upcoming(days=7)
        return {
            "unlocks": [u.to_dict() for u in unlocks] if unlocks else [],
            "count": len(unlocks) if unlocks else 0,
        }
    except Exception as e:
        logger.error(f"Error getting token unlocks: {e}")
        return {"error": str(e)}


# ============================================================================
# INVESTOR TOOLS
# ============================================================================


async def get_investor_status() -> dict[str, Any]:
    """
    Get lazy investor status and recommendations.

    Returns:
        - "Do Nothing OK" indicator
        - Market phase
        - Calm indicator (0-100)
        - Red flags
        - DCA recommendation
    """
    from services.analysis import get_investor_analyzer

    try:
        analyzer = get_investor_analyzer()
        status = analyzer.analyze_simple(fear_greed=None)
        return status.to_dict()
    except Exception as e:
        logger.error(f"Error getting investor status: {e}")
        return {"error": str(e)}


async def get_dca_recommendation() -> dict[str, Any]:
    """
    Get DCA (Dollar Cost Averaging) recommendation.

    Returns:
        - Current DCA zone (Buy/Wait/Overbought)
        - Next DCA level
        - Recommended allocation
    """
    from services.analysis.dca import get_dca_calculator

    try:
        calculator = get_dca_calculator()
        result = await calculator.calculate()
        return result.to_dict() if result else {"error": "No data"}
    except Exception as e:
        logger.error(f"Error getting DCA recommendation: {e}")
        return {"error": str(e)}


async def get_profit_taking_levels(symbol: str = "BTC") -> dict[str, Any]:
    """
    Get profit taking level recommendations.

    Args:
        symbol: Coin symbol (BTC, ETH)

    Returns:
        - Take profit levels (TP1, TP2)
        - Recommended action (Hold/Scale Out/Take Profit)
        - Greed level
    """
    from services.analysis.profit_taking import get_profit_advisor

    try:
        advisor = get_profit_advisor()
        analysis = await advisor.analyze(symbol.upper())
        return analysis.to_dict() if analysis else {"error": "No data"}
    except Exception as e:
        logger.error(f"Error getting profit taking levels: {e}")
        return {"error": str(e)}


# ============================================================================
# SIGNALS TOOLS
# ============================================================================


async def get_signals(hours: int = 24) -> dict[str, Any]:
    """
    Get recent trading signals.

    Args:
        hours: Look back period in hours

    Returns:
        - List of signals with type, source, confidence
        - Signal statistics
    """
    from services.analysis.signal_history import get_signal_manager

    try:
        manager = get_signal_manager()
        since = datetime.now(UTC) - timedelta(hours=hours)
        signals = manager.get_signals(since=since, limit=100)

        return {
            "signals": [s.to_dict() for s in signals],
            "count": len(signals),
            "period_hours": hours,
        }
    except Exception as e:
        logger.error(f"Error getting signals: {e}")
        return {"error": str(e)}


# ============================================================================
# BYBIT PORTFOLIO TOOLS
# ============================================================================


async def get_bybit_portfolio() -> dict[str, Any]:
    """
    Get Bybit exchange portfolio (if configured).

    Returns:
        - Account balance
        - Open positions
        - P&L by period
        - Recent trades
    """
    from services.exchange import get_bybit_portfolio

    try:
        portfolio = get_bybit_portfolio()

        if not portfolio.is_configured:
            return {"error": "Bybit API not configured", "is_configured": False}

        summary = await portfolio.get_account_summary()

        result = {"is_configured": True}
        if summary:
            result.update(summary.to_dict())
        return result
    except Exception as e:
        logger.error(f"Error getting Bybit portfolio: {e}")
        return {"error": str(e)}


# ============================================================================
# BACKFILL STATUS TOOLS
# ============================================================================


async def get_backfill_status() -> dict[str, Any]:
    """
    Get historical data backfill status.

    Returns:
        - Current status (idle/running/completed/error)
        - Progress percentage
        - Total candles/records loaded
    """
    from services.backfill import get_backfill_manager

    try:
        manager = get_backfill_manager()
        return manager.progress.to_dict()
    except Exception as e:
        logger.error(f"Error getting backfill status: {e}")
        return {"error": str(e)}


# Export all tools
ALL_TOOLS = {
    # Crypto
    "get_crypto_prices": get_crypto_prices,
    "get_crypto_analysis": get_crypto_analysis,
    "get_candlesticks": get_candlesticks,
    # Market
    "get_market_summary": get_market_summary,
    "get_fear_greed_index": get_fear_greed_index,
    "get_btc_dominance": get_btc_dominance,
    "get_altseason_index": get_altseason_index,
    # Traditional
    "get_traditional_finance": get_traditional_finance,
    # On-Chain
    "get_whale_alerts": get_whale_alerts,
    "get_exchange_flow": get_exchange_flow,
    # Derivatives
    "get_funding_rates": get_funding_rates,
    "get_liquidation_levels": get_liquidation_levels,
    # Correlation & Volatility
    "get_correlations": get_correlations,
    "get_volatility": get_volatility,
    # Macro
    "get_macro_events": get_macro_events,
    "get_token_unlocks": get_token_unlocks,
    # Investor
    "get_investor_status": get_investor_status,
    "get_dca_recommendation": get_dca_recommendation,
    "get_profit_taking_levels": get_profit_taking_levels,
    # Signals
    "get_signals": get_signals,
    # Bybit
    "get_bybit_portfolio": get_bybit_portfolio,
    # Backfill
    "get_backfill_status": get_backfill_status,
}
