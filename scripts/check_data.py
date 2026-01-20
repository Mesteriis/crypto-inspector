#!/usr/bin/env python3
"""
Check available historical data for backtesting
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from service.candlestick.fetcher import CandleInterval, fetch_candlesticks


async def check_data_availability():
    """Check how much historical data is available."""
    print("Проверка доступности исторических данных...")

    symbol = "BTC/USDT"
    intervals = ["1h", "4h", "1d"]

    for interval in intervals:
        try:
            print(f"\nПроверяем интервал {interval}...")
            candles = await fetch_candlesticks(
                symbol=symbol,
                interval=CandleInterval(interval),
                limit=1000,  # Максимальный лимит
            )
            print(f"  Получено свечей: {len(candles)}")
            if candles:
                print(f"  Первая свеча: {candles[0].timestamp}")
                print(f"  Последняя свеча: {candles[-1].timestamp}")
                print(f"  Цена открытия: {candles[0].open_price}")
                print(f"  Цена закрытия: {candles[-1].close_price}")
                print(f"  Объем: {candles[-1].volume}")
        except Exception as e:
            print(f"  Ошибка: {e}")


if __name__ == "__main__":
    asyncio.run(check_data_availability())
