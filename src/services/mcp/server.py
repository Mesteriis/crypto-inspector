"""
MCP Server for Crypto Inspect.

Provides Model Context Protocol server for AI agent integration.
Uses FastMCP library for easy MCP server creation.
"""

import asyncio
import logging
from typing import Any

from fastmcp import FastMCP

from core.config import settings

logger = logging.getLogger(__name__)

# Create MCP server instance
mcp = FastMCP(
    name="crypto-inspect",
)


# ============================================================================
# REGISTER TOOLS
# ============================================================================


@mcp.tool()
async def get_crypto_prices() -> dict[str, Any]:
    """Get current cryptocurrency prices for all configured trading pairs."""
    from services.mcp.tools import get_crypto_prices as _get_crypto_prices

    return await _get_crypto_prices()


@mcp.tool()
async def get_crypto_analysis(symbol: str) -> dict[str, Any]:
    """Get full technical analysis for a cryptocurrency (RSI, MACD, patterns, score)."""
    from services.mcp.tools import get_crypto_analysis as _get_crypto_analysis

    return await _get_crypto_analysis(symbol)


@mcp.tool()
async def get_candlesticks(symbol: str, interval: str = "1h", limit: int = 100) -> dict[str, Any]:
    """Get historical candlestick (OHLCV) data for a trading pair."""
    from services.mcp.tools import get_candlesticks as _get_candlesticks

    return await _get_candlesticks(symbol, interval, limit)


@mcp.tool()
async def get_market_summary() -> dict[str, Any]:
    """Get comprehensive market summary (Fear/Greed, BTC dominance, altseason)."""
    from services.mcp.tools import get_market_summary as _get_market_summary

    return await _get_market_summary()


@mcp.tool()
async def get_fear_greed_index() -> dict[str, Any]:
    """Get current Fear & Greed Index (0-100)."""
    from services.mcp.tools import get_fear_greed_index as _get_fear_greed_index

    return await _get_fear_greed_index()


@mcp.tool()
async def get_btc_dominance() -> dict[str, Any]:
    """Get current BTC dominance percentage."""
    from services.mcp.tools import get_btc_dominance as _get_btc_dominance

    return await _get_btc_dominance()


@mcp.tool()
async def get_altseason_index() -> dict[str, Any]:
    """Get Altseason Index (Bitcoin Season vs Alt Season)."""
    from services.mcp.tools import get_altseason_index as _get_altseason_index

    return await _get_altseason_index()


@mcp.tool()
async def get_traditional_finance() -> dict[str, Any]:
    """Get traditional asset prices (Gold, Silver, S&P500, EUR/USD, Oil)."""
    from services.mcp.tools import get_traditional_finance as _get_traditional_finance

    return await _get_traditional_finance()


@mcp.tool()
async def get_whale_alerts() -> dict[str, Any]:
    """Get recent whale movement alerts (large BTC/ETH transfers)."""
    from services.mcp.tools import get_whale_alerts as _get_whale_alerts

    return await _get_whale_alerts()


@mcp.tool()
async def get_exchange_flow() -> dict[str, Any]:
    """Get exchange flow data (BTC/ETH inflows/outflows)."""
    from services.mcp.tools import get_exchange_flow as _get_exchange_flow

    return await _get_exchange_flow()


@mcp.tool()
async def get_funding_rates() -> dict[str, Any]:
    """Get perpetual futures funding rates."""
    from services.mcp.tools import get_funding_rates as _get_funding_rates

    return await _get_funding_rates()


@mcp.tool()
async def get_liquidation_levels(symbol: str = "BTC") -> dict[str, Any]:
    """Get liquidation level data for a symbol."""
    from services.mcp.tools import get_liquidation_levels as _get_liquidation_levels

    return await _get_liquidation_levels(symbol)


@mcp.tool()
async def get_correlations() -> dict[str, Any]:
    """Get crypto-to-traditional asset correlations."""
    from services.mcp.tools import get_correlations as _get_correlations

    return await _get_correlations()


@mcp.tool()
async def get_volatility() -> dict[str, Any]:
    """Get volatility metrics (30-day volatility, percentile)."""
    from services.mcp.tools import get_volatility as _get_volatility

    return await _get_volatility()


@mcp.tool()
async def get_macro_events() -> dict[str, Any]:
    """Get upcoming macro economic events (FOMC, CPI)."""
    from services.mcp.tools import get_macro_events as _get_macro_events

    return await _get_macro_events()


@mcp.tool()
async def get_token_unlocks() -> dict[str, Any]:
    """Get upcoming token unlock events."""
    from services.mcp.tools import get_token_unlocks as _get_token_unlocks

    return await _get_token_unlocks()


@mcp.tool()
async def get_investor_status() -> dict[str, Any]:
    """Get lazy investor status and recommendations."""
    from services.mcp.tools import get_investor_status as _get_investor_status

    return await _get_investor_status()


@mcp.tool()
async def get_dca_recommendation() -> dict[str, Any]:
    """Get DCA (Dollar Cost Averaging) recommendation."""
    from services.mcp.tools import get_dca_recommendation as _get_dca_recommendation

    return await _get_dca_recommendation()


@mcp.tool()
async def get_profit_taking_levels(symbol: str = "BTC") -> dict[str, Any]:
    """Get profit taking level recommendations for a symbol."""
    from services.mcp.tools import get_profit_taking_levels as _get_profit_taking_levels

    return await _get_profit_taking_levels(symbol)


@mcp.tool()
async def get_signals(hours: int = 24) -> dict[str, Any]:
    """Get recent trading signals."""
    from services.mcp.tools import get_signals as _get_signals

    return await _get_signals(hours)


@mcp.tool()
async def get_bybit_portfolio() -> dict[str, Any]:
    """Get Bybit exchange portfolio (if configured)."""
    from services.mcp.tools import get_bybit_portfolio as _get_bybit_portfolio

    return await _get_bybit_portfolio()


@mcp.tool()
async def get_backfill_status() -> dict[str, Any]:
    """Get historical data backfill status."""
    from services.mcp.tools import get_backfill_status as _get_backfill_status

    return await _get_backfill_status()


# ============================================================================
# REGISTER RESOURCES
# ============================================================================


@mcp.resource("crypto://prices")
async def resource_crypto_prices() -> str:
    """Current cryptocurrency prices."""
    import json

    from services.mcp.tools import get_crypto_prices as _get_crypto_prices

    data = await _get_crypto_prices()
    return json.dumps(data, indent=2)


@mcp.resource("crypto://analysis/{symbol}")
async def resource_crypto_analysis(symbol: str) -> str:
    """Technical analysis for a cryptocurrency."""
    import json

    from services.mcp.tools import get_crypto_analysis as _get_crypto_analysis

    data = await _get_crypto_analysis(symbol)
    return json.dumps(data, indent=2)


@mcp.resource("crypto://candles/{symbol}/{interval}")
async def resource_candlesticks(symbol: str, interval: str) -> str:
    """Historical candlestick data."""
    import json

    from services.mcp.tools import get_candlesticks as _get_candlesticks

    data = await _get_candlesticks(symbol, interval, 100)
    return json.dumps(data, indent=2)


@mcp.resource("finance://metals")
async def resource_metals() -> str:
    """Traditional finance metals (Gold, Silver, Platinum)."""
    import json

    from services.analysis.traditional import get_traditional_tracker

    tracker = get_traditional_tracker()
    data = await tracker.get_metals()
    return json.dumps(data, indent=2)


@mcp.resource("finance://indices")
async def resource_indices() -> str:
    """Stock market indices (S&P500, NASDAQ, Dow Jones, DAX)."""
    import json

    from services.analysis.traditional import get_traditional_tracker

    tracker = get_traditional_tracker()
    data = await tracker.get_indices()
    return json.dumps(data, indent=2)


@mcp.resource("finance://forex")
async def resource_forex() -> str:
    """Forex pairs (EUR/USD, GBP/USD, DXY)."""
    import json

    from services.analysis.traditional import get_traditional_tracker

    tracker = get_traditional_tracker()
    data = await tracker.get_forex()
    return json.dumps(data, indent=2)


@mcp.resource("finance://commodities")
async def resource_commodities() -> str:
    """Commodities (Oil Brent, WTI, Natural Gas)."""
    import json

    from services.analysis.traditional import get_traditional_tracker

    tracker = get_traditional_tracker()
    data = await tracker.get_commodities()
    return json.dumps(data, indent=2)


@mcp.resource("market://summary")
async def resource_market_summary() -> str:
    """Market summary with Fear/Greed, dominance, altseason."""
    import json

    from services.mcp.tools import get_market_summary as _get_market_summary

    data = await _get_market_summary()
    return json.dumps(data, indent=2)


# ============================================================================
# SERVER MANAGEMENT
# ============================================================================

_mcp_task: asyncio.Task | None = None


def get_mcp_server() -> FastMCP:
    """Get the MCP server instance."""
    return mcp


async def start_mcp_server() -> bool:
    """
    Start the MCP server.

    Returns:
        True if started successfully
    """
    global _mcp_task

    if not settings.MCP_ENABLED:
        logger.info("MCP server disabled in config")
        return False

    try:
        logger.info(f"Starting MCP server on {settings.MCP_HOST}:{settings.MCP_PORT}")

        # Run MCP server in background task
        _mcp_task = asyncio.create_task(
            mcp.run_http_async(
                host=settings.MCP_HOST,
                port=settings.MCP_PORT,
                transport="sse",
                show_banner=False,
            )
        )

        logger.info(f"MCP server started on port {settings.MCP_PORT}")
        return True

    except Exception as e:
        logger.error(f"Failed to start MCP server: {e}")
        return False


async def stop_mcp_server() -> None:
    """Stop the MCP server."""
    global _mcp_task

    if _mcp_task:
        _mcp_task.cancel()
        try:
            await _mcp_task
        except asyncio.CancelledError:
            pass
        _mcp_task = None
        logger.info("MCP server stopped")
