import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.router import api_router
from core.config import settings
from core.scheduler import scheduler_lifespan

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def start_websocket_streaming() -> None:
    """Start WebSocket streaming if enabled."""
    if not settings.STREAMING_ENABLED:
        logger.info("WebSocket streaming disabled")
        return

    symbols = settings.get_streaming_symbols()
    if not symbols:
        logger.warning("No streaming symbols configured")
        return

    from services.candlestick.buffer import get_candle_buffer, init_candle_buffer
    from services.candlestick.models import CandleInterval
    from services.candlestick.websocket import init_stream_manager

    # Initialize candle buffer for DB writes
    await init_candle_buffer()
    logger.info("Candle buffer initialized")

    # Parse interval
    interval_map = {i.value: i for i in CandleInterval}
    interval = interval_map.get(settings.STREAMING_INTERVAL, CandleInterval.MINUTE_1)
    interval_str = settings.STREAMING_INTERVAL

    async def on_candle(symbol: str, candle, is_closed: bool, source: str) -> None:
        """Handle received candle."""
        if is_closed:
            logger.info(
                f"[{source}] {symbol} candle closed: "
                f"O={candle.open_price} H={candle.high_price} "
                f"L={candle.low_price} C={candle.close_price} V={candle.volume}"
            )
            # Save closed candle to buffer
            buffer = get_candle_buffer()
            if buffer:
                await buffer.add(
                    symbol=symbol,
                    candle=candle,
                    exchange=source,
                    interval=interval_str,
                )

    async def on_source_change(symbol: str, old_source, new_source) -> None:
        """Handle source change."""
        logger.warning(f"Stream source changed for {symbol}: {old_source.value} -> {new_source.value}")

    await init_stream_manager(
        symbols=symbols,
        interval=interval,
        on_candle=on_candle,
        on_source_change=on_source_change,
    )
    logger.info(f"Started WebSocket streaming for {symbols}")


async def stop_websocket_streaming() -> None:
    """Stop WebSocket streaming."""
    from services.candlestick.buffer import stop_candle_buffer
    from services.candlestick.websocket import stop_stream_manager

    await stop_stream_manager()
    await stop_candle_buffer()
    logger.info("WebSocket streaming stopped")


async def start_mcp_server() -> None:
    """Start MCP server if enabled."""
    if not settings.MCP_ENABLED:
        logger.info("MCP server disabled")
        return

    try:
        from services.mcp import start_mcp_server as _start_mcp_server

        success = await _start_mcp_server()
        if success:
            logger.info(f"MCP server started on port {settings.MCP_PORT}")
        else:
            logger.warning("MCP server failed to start")
    except ImportError as e:
        logger.warning(f"MCP server not available (missing dependency): {e}")


async def stop_mcp_server() -> None:
    """Stop MCP server."""
    try:
        from services.mcp import stop_mcp_server as _stop_mcp_server

        await _stop_mcp_server()
    except ImportError:
        pass  # MCP not available


async def run_initial_backfill() -> None:
    """Run initial data backfill if enabled."""
    if not settings.BACKFILL_ENABLED:
        logger.info("Data backfill disabled")
        return

    from services.backfill import get_backfill_manager

    logger.info("Checking for initial data backfill...")
    manager = get_backfill_manager()

    # Run backfill in background to not block startup
    import asyncio

    asyncio.create_task(_run_backfill_background(manager))


async def _run_backfill_background(manager) -> None:
    """Run backfill in background."""
    try:
        await manager.check_and_backfill()
    except Exception as e:
        logger.error(f"Backfill error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Application lifespan manager."""
    logger.info(f"Starting {settings.APP_NAME}...")

    # Start WebSocket streaming
    await start_websocket_streaming()

    # Start MCP server
    await start_mcp_server()

    # Run initial backfill (background task)
    await run_initial_backfill()

    # Start scheduler
    async with scheduler_lifespan(app):
        yield

    # Stop services
    await stop_mcp_server()
    await stop_websocket_streaming()

    logger.info(f"{settings.APP_NAME} shutdown complete")


app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

app.include_router(api_router)


@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.APP_NAME}"}
