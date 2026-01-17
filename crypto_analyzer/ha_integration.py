#!/usr/bin/env python3
"""
Home Assistant Integration - записывает результаты анализа в JSON файл
для чтения template sensors

Использование:
    python3 ha_integration.py [--coin BTC] [--timeframe 30m]

Результат записывается в /config/crypto_analysis.json
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Добавляем путь к модулям
sys.path.insert(0, str(Path(__file__).parent))

from run_analysis import CryptoAnalyzerRunner

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


# Путь для результата - определяем динамически
# Приоритет: /config (HA OS), /homeassistant (HA Core), текущая директория
def get_output_path():
    """Определяет путь для записи результата"""
    possible_paths = [
        Path("/config/crypto_analysis.json"),
        Path("/homeassistant/crypto_analysis.json"),
        Path(__file__).parent.parent.parent / "crypto_analysis.json",  # Относительно скрипта
    ]
    for p in possible_paths:
        if p.parent.exists():
            return p
    return possible_paths[0]  # По умолчанию /config


OUTPUT_PATH = get_output_path()

# Список монет для анализа (по умолчанию)
DEFAULT_COINS = ["BTC", "ETH", "SOL", "TON", "AR"]
DEFAULT_TIMEFRAMES = ["30m", "1h", "4h", "1d"]


def parse_args():
    """Парсинг аргументов командной строки"""
    parser = argparse.ArgumentParser(description="Crypto Analyzer for Home Assistant")
    parser.add_argument("--coin", type=str, help="Specific coin to analyze (e.g., BTC)")
    parser.add_argument("--coins", type=str, help="Comma-separated list of coins")
    parser.add_argument("--timeframe", type=str, help="Specific timeframe (e.g., 30m, 1h, 4h, 1d)")
    parser.add_argument("--timeframes", type=str, help="Comma-separated list of timeframes")
    return parser.parse_args()


async def main():
    """Главная функция"""
    args = parse_args()

    # Определяем монеты для анализа
    if args.coin:
        coins = [args.coin.upper()]
    elif args.coins:
        coins = [c.strip().upper() for c in args.coins.split(",")]
    else:
        coins = DEFAULT_COINS

    # Определяем таймфреймы
    if args.timeframe:
        timeframes = [args.timeframe.lower()]
    elif args.timeframes:
        timeframes = [t.strip().lower() for t in args.timeframes.split(",")]
    else:
        timeframes = DEFAULT_TIMEFRAMES

    runner = CryptoAnalyzerRunner()

    try:
        # Пробуем обновить данные (игнорируем ошибки - используем существующие)
        try:
            await runner.update_data(coins, timeframes)
        except Exception as e:
            logger.warning(f"Update failed, using cached data: {e}")

        # Получаем анализ в формате HA (работает с существующими данными)
        ha_data = runner.get_ha_sensors_data(coins)

        # Добавляем метаданные
        result = {
            "timestamp": datetime.now().isoformat(),
            "status": "ok",
            "data": ha_data.get("sensors", {}),
            "raw": {},
        }

        # Упрощаем raw данные для JSON
        for coin, coin_data in ha_data.get("raw", {}).get("coins", {}).items():
            if isinstance(coin_data, dict) and "error" not in coin_data:
                result["raw"][coin.lower()] = {
                    "price": coin_data.get("price"),
                    "mtf": coin_data.get("mtf"),
                    "technical": coin_data.get("technical"),
                    "patterns": coin_data.get("patterns"),
                    "cycle": coin_data.get("cycle"),
                    "levels": coin_data.get("levels"),
                    "recommendation": coin_data.get("recommendation"),
                }

        # Записываем результат
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2, default=str)

        print(json.dumps({"status": "ok", "file": str(OUTPUT_PATH)}, ensure_ascii=False))

    except Exception as e:
        logger.error(f"Ошибка: {e}")
        error_result = {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e),
            "data": {},
            "raw": {},
        }
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(error_result, f, ensure_ascii=False, indent=2)
        print(json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False))
        sys.exit(1)
    finally:
        await runner.close_all()


if __name__ == "__main__":
    asyncio.run(main())
