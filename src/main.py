import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.middleware import setup_exception_handlers
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

    from service.candlestick.buffer import get_candle_buffer, init_candle_buffer
    from service.candlestick.models import CandleInterval
    from service.candlestick.websocket import init_stream_manager

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
    from service.candlestick.buffer import stop_candle_buffer
    from service.candlestick.websocket import stop_stream_manager

    await stop_stream_manager()
    await stop_candle_buffer()
    logger.info("WebSocket streaming stopped")


async def start_mcp_server() -> None:
    """Start MCP server if enabled."""
    if not settings.MCP_ENABLED:
        logger.debug("MCP server disabled by configuration")
        return

    try:
        from service.mcp import start_mcp_server as _start_mcp_server

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
        from service.mcp import stop_mcp_server as _stop_mcp_server

        await _stop_mcp_server()
    except ImportError:
        pass  # MCP not available


async def run_initial_backfill() -> None:
    """Run initial data backfill if enabled."""
    if not settings.BACKFILL_ENABLED:
        logger.info("Data backfill disabled")
        return

    from service.backfill import get_backfill_manager

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

    # Log service configuration
    services_info = []
    if settings.API_ENABLED:
        services_info.append(f"API (port {settings.API_PORT})")
    if settings.MCP_ENABLED:
        services_info.append(f"MCP (port {settings.MCP_PORT})")
    if settings.STREAMING_ENABLED:
        services_info.append("WebSocket Streaming")

    if services_info:
        logger.info(f"Enabled services: {', '.join(services_info)}")
    else:
        logger.info("All optional services disabled")

    # Check HA Supervisor connection with retries
    from service.ha_integration import get_supervisor_client
    
    supervisor_client = get_supervisor_client()
    ha_connected = await supervisor_client.check_connection()
    
    if not ha_connected:
        if settings.API_ENABLED or settings.MCP_ENABLED:
            logger.info(
                "HA Supervisor not available, but API/MCP enabled - continuing in standalone mode"
            )
        else:
            logger.warning(
                "HA Supervisor not available and no API/MCP enabled. "
                "Application will run with limited functionality."
            )

    # Initialize HA entities only if connected
    if ha_connected:
        try:
            from service.ha_init import initialize_ha_entities

            await initialize_ha_entities()
        except ImportError:
            logger.warning("ha_init module not available, skipping entity initialization")
        except Exception as e:
            logger.error(f"Error initializing HA entities: {e}")

        # Register HA sensors
        from service.ha_integration import register_sensors

        await register_sensors()
    else:
        logger.info("Skipping HA entity initialization (not connected)")

    # Start WebSocket streaming
    await start_websocket_streaming()

    # Start MCP server (conditional)
    if settings.MCP_ENABLED:
        await start_mcp_server()
    else:
        logger.info("MCP server disabled by configuration")

    # Run initial backfill (background task)
    await run_initial_backfill()

    # Start scheduler
    async with scheduler_lifespan(app):
        yield

    # Stop services
    if settings.MCP_ENABLED:
        await stop_mcp_server()
    await stop_websocket_streaming()

    logger.info(f"{settings.APP_NAME} shutdown complete")


app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# Setup global exception handlers with HA notifications
setup_exception_handlers(app)

# Include API router only if API is enabled
if settings.API_ENABLED:
    app.include_router(api_router)
    logger.info(f"API server enabled on port {settings.API_PORT}")
else:
    logger.info("API server disabled by configuration")

# Static files for web UI
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def root():
    """Serve web UI."""
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": f"Welcome to {settings.APP_NAME}"}
