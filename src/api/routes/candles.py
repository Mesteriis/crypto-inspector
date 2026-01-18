"""
Candlestick Data API Routes.

Provides REST endpoints for candlestick (OHLC) data:
- GET /api/candles/{symbol} - Get candlesticks for a symbol
- GET /api/candles/{symbol}/chart - Get chart-ready data for ApexCharts
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from db.session import async_session_maker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/candles", tags=["candles"])


@router.get("/available")
async def get_available_symbols() -> dict[str, Any]:
    """
    Get list of available symbols and intervals in the database.

    Returns:
        Available symbols and intervals
    """
    try:
        async with async_session_maker() as session:
            # Get unique symbols
            symbols_result = await session.execute(
                text("SELECT DISTINCT symbol FROM candlestick_records ORDER BY symbol")
            )
            symbols = [row[0] for row in symbols_result.fetchall()]

            # Get unique intervals
            intervals_result = await session.execute(
                text("SELECT DISTINCT interval FROM candlestick_records ORDER BY interval")
            )
            intervals = [row[0] for row in intervals_result.fetchall()]

            # Get count per symbol/interval
            stats_result = await session.execute(
                text("""
                    SELECT symbol, interval, COUNT(*) as count,
                           MIN(timestamp) as oldest,
                           MAX(timestamp) as newest
                    FROM candlestick_records
                    GROUP BY symbol, interval
                    ORDER BY symbol, interval
                """)
            )

            stats = []
            for row in stats_result.fetchall():
                stats.append(
                    {
                        "symbol": row[0],
                        "interval": row[1],
                        "count": row[2],
                        "oldest": datetime.fromtimestamp(row[3] / 1000).isoformat() if row[3] else None,
                        "newest": datetime.fromtimestamp(row[4] / 1000).isoformat() if row[4] else None,
                    }
                )

            return {
                "symbols": symbols,
                "intervals": intervals,
                "stats": stats,
            }

    except Exception as e:
        logger.error(f"Error fetching available data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}")
async def get_candles(
    symbol: str,
    interval: str = Query(default="1h", description="Candle interval (1m, 15m, 1h, 4h, 1d)"),
    limit: int = Query(default=100, ge=1, le=1000, description="Number of candles"),
    exchange: str = Query(default=None, description="Exchange filter (bybit, binance)"),
) -> dict[str, Any]:
    """
    Get candlestick data for a symbol.

    Args:
        symbol: Trading pair (e.g., BTC/USDT)
        interval: Candle interval
        limit: Number of candles to return
        exchange: Optional exchange filter

    Returns:
        Candlestick data with OHLCV
    """
    # Normalize symbol format
    if "/" not in symbol:
        symbol = f"{symbol}/USDT"

    try:
        async with async_session_maker() as session:
            query = """
                SELECT
                    timestamp, open_price, high_price, low_price, close_price,
                    volume, quote_volume, exchange
                FROM candlestick_records
                WHERE symbol = :symbol AND interval = :interval
            """
            params: dict[str, Any] = {"symbol": symbol, "interval": interval}

            if exchange:
                query += " AND exchange = :exchange"
                params["exchange"] = exchange

            query += " ORDER BY timestamp DESC LIMIT :limit"
            params["limit"] = limit

            result = await session.execute(text(query), params)
            rows = result.fetchall()

            candles = []
            for row in rows:
                candles.append(
                    {
                        "timestamp": row[0],
                        "open": float(row[1]),
                        "high": float(row[2]),
                        "low": float(row[3]),
                        "close": float(row[4]),
                        "volume": float(row[5]) if row[5] else 0,
                        "quote_volume": float(row[6]) if row[6] else None,
                        "exchange": row[7],
                    }
                )

            # Reverse to chronological order
            candles.reverse()

            return {
                "symbol": symbol,
                "interval": interval,
                "count": len(candles),
                "candles": candles,
            }

    except Exception as e:
        logger.error(f"Error fetching candles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}/chart")
async def get_chart_data(
    symbol: str,
    interval: str = Query(default="1h", description="Candle interval"),
    limit: int = Query(default=100, ge=1, le=500, description="Number of candles"),
    include_indicators: bool = Query(default=True, description="Include MA/EMA/BB"),
) -> dict[str, Any]:
    """
    Get chart-ready data for ApexCharts candlestick visualization.

    Returns data formatted for ApexCharts:
    - ohlc: [[timestamp, open, high, low, close], ...]
    - volume: [[timestamp, volume], ...]
    - indicators: MA, EMA, Bollinger Bands (optional)
    """
    if "/" not in symbol:
        symbol = f"{symbol}/USDT"

    try:
        async with async_session_maker() as session:
            query = """
                SELECT
                    timestamp, open_price, high_price, low_price, close_price,
                    volume, exchange
                FROM candlestick_records
                WHERE symbol = :symbol AND interval = :interval
                ORDER BY timestamp DESC
                LIMIT :limit
            """
            result = await session.execute(
                text(query),
                {"symbol": symbol, "interval": interval, "limit": limit},
            )
            rows = result.fetchall()

            if not rows:
                return {
                    "symbol": symbol,
                    "interval": interval,
                    "count": 0,
                    "ohlc": [],
                    "volume": [],
                    "indicators": {},
                }

            # Reverse to chronological order
            rows = list(reversed(rows))

            # Format for ApexCharts
            ohlc = []
            volume = []
            closes = []

            for row in rows:
                ts = row[0]  # Already in milliseconds
                ohlc.append(
                    {
                        "x": ts,
                        "y": [float(row[1]), float(row[2]), float(row[3]), float(row[4])],
                    }
                )
                volume.append(
                    {
                        "x": ts,
                        "y": float(row[5]) if row[5] else 0,
                    }
                )
                closes.append(float(row[4]))

            response = {
                "symbol": symbol,
                "interval": interval,
                "count": len(ohlc),
                "exchange": rows[0][6] if rows else None,
                "ohlc": ohlc,
                "volume": volume,
            }

            # Calculate indicators if requested
            if include_indicators and len(closes) >= 20:
                response["indicators"] = calculate_indicators(
                    closes=closes,
                    timestamps=[row[0] for row in rows],
                )

            return response

    except Exception as e:
        logger.error(f"Error fetching chart data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def calculate_indicators(
    closes: list[float],
    timestamps: list[int],
) -> dict[str, Any]:
    """
    Calculate technical indicators for chart overlay.

    Args:
        closes: List of closing prices
        timestamps: List of timestamps

    Returns:
        Dictionary with MA, EMA, Bollinger Bands data
    """
    import statistics

    indicators = {}

    # Simple Moving Averages
    for period in [7, 14, 20, 28]:
        if len(closes) >= period:
            ma_values = []
            for i in range(len(closes)):
                if i >= period - 1:
                    ma = sum(closes[i - period + 1 : i + 1]) / period
                    ma_values.append({"x": timestamps[i], "y": round(ma, 2)})
            indicators[f"ma{period}"] = ma_values

    # Exponential Moving Averages
    for period in [7, 14, 28]:
        if len(closes) >= period:
            ema_values = []
            multiplier = 2 / (period + 1)
            ema = sum(closes[:period]) / period  # Initial SMA

            for i in range(len(closes)):
                if i < period - 1:
                    continue
                if i == period - 1:
                    ema_values.append({"x": timestamps[i], "y": round(ema, 2)})
                else:
                    ema = (closes[i] - ema) * multiplier + ema
                    ema_values.append({"x": timestamps[i], "y": round(ema, 2)})
            indicators[f"ema{period}"] = ema_values

    # Bollinger Bands (20, 2)
    bb_period = 20
    if len(closes) >= bb_period:
        upper_band = []
        middle_band = []
        lower_band = []

        for i in range(bb_period - 1, len(closes)):
            window = closes[i - bb_period + 1 : i + 1]
            sma = sum(window) / bb_period
            std = statistics.stdev(window)

            upper_band.append({"x": timestamps[i], "y": round(sma + 2 * std, 2)})
            middle_band.append({"x": timestamps[i], "y": round(sma, 2)})
            lower_band.append({"x": timestamps[i], "y": round(sma - 2 * std, 2)})

        indicators["bb_upper"] = upper_band
        indicators["bb_middle"] = middle_band
        indicators["bb_lower"] = lower_band

    return indicators
