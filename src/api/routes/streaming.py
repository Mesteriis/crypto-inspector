"""
Streaming API Routes.

Provides REST endpoints for WebSocket stream management:
- GET /api/streaming/status - Get stream status
- POST /api/streaming/retry - Retry primary connection
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/streaming", tags=["streaming"])


@router.get("/status")
async def get_stream_status() -> dict[str, Any]:
    """
    Get WebSocket streaming status.

    Returns:
        Stream status including active sources and connection states
    """
    from service.candlestick.buffer import get_candle_buffer
    from service.candlestick.websocket import get_stream_manager

    manager = get_stream_manager()
    buffer = get_candle_buffer()

    if not manager:
        return {
            "enabled": False,
            "message": "WebSocket streaming not initialized",
        }

    result = {
        "enabled": True,
        **manager.get_status(),
    }

    if buffer:
        result["buffer"] = buffer.stats

    return result


@router.post("/retry")
async def retry_primary(symbol: str | None = None) -> dict[str, Any]:
    """
    Retry connecting to primary source (Bybit).

    Args:
        symbol: Specific symbol to retry, or None for all symbols

    Returns:
        Confirmation message
    """
    from service.candlestick.websocket import get_stream_manager

    manager = get_stream_manager()
    if not manager:
        raise HTTPException(status_code=503, detail="Streaming not initialized")

    await manager.retry_primary(symbol)

    return {
        "status": "ok",
        "message": f"Retrying primary connection for {symbol or 'all symbols'}",
    }


@router.post("/start")
async def start_streaming() -> dict[str, Any]:
    """
    Start WebSocket streaming (if not already running).

    Returns:
        Confirmation message
    """
    from core.config import settings
    from service.candlestick.models import CandleInterval
    from service.candlestick.websocket import get_stream_manager, init_stream_manager

    manager = get_stream_manager()
    if manager:
        return {
            "status": "already_running",
            "message": "Streaming is already active",
            **manager.get_status(),
        }

    symbols = settings.get_streaming_symbols()
    if not symbols:
        raise HTTPException(status_code=400, detail="No symbols configured")

    interval_map = {i.value: i for i in CandleInterval}
    interval = interval_map.get(settings.STREAMING_INTERVAL, CandleInterval.MINUTE_1)

    await init_stream_manager(symbols=symbols, interval=interval)

    return {
        "status": "started",
        "message": f"Started streaming for {symbols}",
    }


@router.post("/stop")
async def stop_streaming() -> dict[str, Any]:
    """
    Stop WebSocket streaming.

    Returns:
        Confirmation message
    """
    from service.candlestick.websocket import get_stream_manager, stop_stream_manager

    manager = get_stream_manager()
    if not manager:
        return {
            "status": "not_running",
            "message": "Streaming is not active",
        }

    await stop_stream_manager()

    return {
        "status": "stopped",
        "message": "Streaming stopped",
    }
