#!/usr/bin/env python3
"""
Backfill Crypto History - загружает исторические данные в статистику Home Assistant

Использование:
    python3 backfill_history.py [--days 90]

ВАЖНО: Запускать когда HA остановлен или сделать бэкап базы!
"""

import argparse
import json
import sqlite3
import urllib.request
from datetime import datetime
from pathlib import Path

# Пути к базе данных HA
DB_PATHS = [
    Path("/config/home-assistant_v2.db"),
    Path("/homeassistant/home-assistant_v2.db"),
    Path(__file__).parent.parent.parent / "home-assistant_v2.db",
]

# Маппинг сенсоров на CoinGecko ID
SENSORS_MAP = {
    "sensor.crypto_history_btc_usd": "bitcoin",
    "sensor.crypto_history_eth_usd": "ethereum",
    "sensor.crypto_history_sol_usd": "solana",
    "sensor.crypto_history_ton_usd": "the-open-network",
    "sensor.crypto_history_ar_usd": "arweave",
    "sensor.crypto_history_rndr_usd": "render-token",
    "sensor.crypto_history_fet_usd": "fetch-ai",
    "sensor.crypto_history_tao_usd": "bittensor",
}


def find_db():
    """Находит базу данных HA"""
    for path in DB_PATHS:
        if path.exists():
            return path
    return None


def get_coingecko_history(coin_id: str, days: int = 90) -> list:
    """Загружает историю цен из CoinGecko"""
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days={days}&interval=daily"

    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read())
            # Возвращает список [timestamp_ms, price]
            return data.get("prices", [])
    except Exception as e:
        print(f"  Ошибка загрузки {coin_id}: {e}")
        return []


def get_statistic_id(conn, entity_id: str) -> int:
    """Получает или создаёт statistic_id для entity"""
    cursor = conn.cursor()

    # Ищем существующий
    cursor.execute("SELECT id FROM statistics_meta WHERE statistic_id = ?", (entity_id,))
    row = cursor.fetchone()

    if row:
        return row[0]

    # Создаём новый
    cursor.execute(
        """
        INSERT INTO statistics_meta (statistic_id, source, unit_of_measurement, has_mean, has_sum, name)
        VALUES (?, 'recorder', 'USD', 1, 0, ?)
    """,
        (entity_id, entity_id.replace("sensor.", "").replace("_", " ").title()),
    )

    conn.commit()
    return cursor.lastrowid


def insert_statistics(conn, metadata_id: int, prices: list, existing_timestamps: set):
    """Вставляет статистику в базу"""
    cursor = conn.cursor()
    inserted = 0

    for ts_ms, price in prices:
        # Округляем до начала часа
        ts = datetime.fromtimestamp(ts_ms / 1000)
        ts_hour = ts.replace(minute=0, second=0, microsecond=0)
        ts_unix = ts_hour.timestamp()

        # Пропускаем если уже есть
        if ts_unix in existing_timestamps:
            continue

        try:
            cursor.execute(
                """
                INSERT INTO statistics (created_ts, start_ts, mean, min, max, state, sum, metadata_id)
                VALUES (?, ?, ?, ?, ?, ?, NULL, ?)
            """,
                (ts_unix, ts_unix, price, price, price, price, metadata_id),
            )
            inserted += 1
            existing_timestamps.add(ts_unix)
        except sqlite3.IntegrityError:
            pass  # Уже существует

    conn.commit()
    return inserted


def get_existing_timestamps(conn, metadata_id: int) -> set:
    """Получает существующие timestamps для избежания дубликатов"""
    cursor = conn.cursor()
    cursor.execute("SELECT start_ts FROM statistics WHERE metadata_id = ?", (metadata_id,))
    return {row[0] for row in cursor.fetchall()}


def main():
    parser = argparse.ArgumentParser(description="Backfill crypto history to HA")
    parser.add_argument("--days", type=int, default=90, help="Days of history to load")
    args = parser.parse_args()

    # Находим базу
    db_path = find_db()
    if not db_path:
        print("❌ База данных HA не найдена!")
        return

    print(f"📁 База данных: {db_path}")
    print(f"📅 Загружаем историю за {args.days} дней")
    print()

    # Подключаемся с таймаутом для работы с занятой базой
    conn = sqlite3.connect(db_path, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")

    total_inserted = 0

    for entity_id, coin_id in SENSORS_MAP.items():
        print(f"🪙 {coin_id.upper()} ({entity_id})")

        # Загружаем данные
        prices = get_coingecko_history(coin_id, args.days)
        if not prices:
            print("  ⚠️ Нет данных")
            continue

        print(f"  📊 Загружено {len(prices)} точек")

        # Получаем metadata_id
        metadata_id = get_statistic_id(conn, entity_id)
        print(f"  🔑 metadata_id: {metadata_id}")

        # Получаем существующие timestamps
        existing = get_existing_timestamps(conn, metadata_id)
        print(f"  📈 Уже в базе: {len(existing)} точек")

        # Вставляем
        inserted = insert_statistics(conn, metadata_id, prices, existing)
        total_inserted += inserted
        print(f"  ✅ Добавлено: {inserted} точек")
        print()

    conn.close()

    print(f"🎉 Всего добавлено: {total_inserted} точек")
    print()
    print("⚠️  Перезапустите Home Assistant чтобы увидеть изменения!")


if __name__ == "__main__":
    main()
