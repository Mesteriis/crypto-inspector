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

    from services.candlestick.models import CandleInterval
    from services.candlestick.websocket import init_stream_manager

    # Parse interval
    interval_map = {i.value: i for i in CandleInterval}
    interval = interval_map.get(settings.STREAMING_INTERVAL, CandleInterval.MINUTE_1)

    async def on_candle(symbol: str, candle, is_closed: bool, source: str) -> None:
        """Handle received candle."""
        if is_closed:
            logger.info(
                f"[{source}] {symbol} candle closed: "
                f"O={candle.open_price} H={candle.high_price} "
                f"L={candle.low_price} C={candle.close_price} V={candle.volume}"
            )
            # TODO: Save to database when candle closes

    async def on_source_change(symbol: str, old_source, new_source) -> None:
        """Handle source change."""
        logger.warning(
            f"Stream source changed for {symbol}: {old_source.value} -> {new_source.value}"
        )

    await init_stream_manager(
        symbols=symbols,
        interval=interval,
        on_candle=on_candle,
        on_source_change=on_source_change,
    )
    logger.info(f"Started WebSocket streaming for {symbols}")


async def stop_websocket_streaming() -> None:
    """Stop WebSocket streaming."""
    from services.candlestick.websocket import stop_stream_manager

    await stop_stream_manager()
    logger.info("WebSocket streaming stopped")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Application lifespan manager."""
    logger.info(f"Starting {settings.APP_NAME}...")

    # Start WebSocket streaming
    await start_websocket_streaming()

    # Start scheduler
    async with scheduler_lifespan(app):
        yield

    # Stop WebSocket streaming
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
