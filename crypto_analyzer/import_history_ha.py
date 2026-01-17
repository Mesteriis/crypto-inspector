#!/usr/bin/env python3
"""
Import Crypto History via Home Assistant API
Использует recorder.import_statistics для импорта исторических данных

Использование:
    python3 import_history_ha.py [--days 90]
"""

import argparse
import json

# Конфигурация HA
import os
import time
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

# URL можно переопределить через переменную окружения
HA_URL = os.environ.get("HA_URL")
if not HA_URL:
    if os.path.exists("/var/run/supervisor"):
        HA_URL = "http://supervisor/core"
    else:
        # Для запуска снаружи HA - используем homeassistant.local или IP
        HA_URL = "http://homeassistant.local:8123"
HA_TOKEN_FILE = Path("/config/secrets.yaml")

# Маппинг: (sensor_id, coingecko_id, currency, display_name)
SENSORS_MAP = {
    "sensor.crypto_history_btc_usd": ("bitcoin", "USD", "Bitcoin"),
    "sensor.crypto_history_eth_usd": ("ethereum", "USD", "Ethereum"),
    "sensor.crypto_history_sol_usd": ("solana", "USD", "Solana"),
    "sensor.crypto_history_ton_usd": ("the-open-network", "USD", "TON"),
    "sensor.crypto_history_ar_usd": ("arweave", "USD", "Arweave"),
    "sensor.crypto_history_rndr_usd": ("render-token", "USD", "Render"),
    "sensor.crypto_history_fet_usd": ("fetch-ai", "USD", "Fetch.ai"),
    "sensor.crypto_history_tao_usd": ("bittensor", "USD", "Bittensor"),
    "sensor.crypto_history_btc_eur": ("bitcoin", "EUR", "Bitcoin"),
    "sensor.crypto_history_eth_eur": ("ethereum", "EUR", "Ethereum"),
}


def get_ha_token():
    """Получает токен: SUPERVISOR_TOKEN (HA OS) или Long-Lived Token из secrets.yaml"""
    import re

    # Для HA OS используем SUPERVISOR_TOKEN (автоматически доступен)
    token = os.environ.get("SUPERVISOR_TOKEN")
    if token:
        print("  🔐 Используем SUPERVISOR_TOKEN")
        return token

    # Для standalone или Docker пробуем HA_TOKEN переменную
    token = os.environ.get("HA_TOKEN")
    if token:
        print("  🔐 Используем HA_TOKEN env var")
        return token

    # Пробуем secrets.yaml
    secrets_paths = [
        Path("/config/secrets.yaml"),
        Path("/homeassistant/secrets.yaml"),
        Path(__file__).parent.parent.parent / "secrets.yaml",
    ]

    for path in secrets_paths:
        if path.exists():
            with open(path) as f:
                content = f.read()
                # Пробуем разные имена токенов
                for token_name in [
                    "ha_long_lived_token",
                    "mcp_long_live_token",
                    "ha_token",
                    "long_lived_token",
                ]:
                    match = re.search(rf'{token_name}:\s*["\']?([^"\'\n]+)["\']?', content)
                    if match:
                        print(f"  🔐 Используем {token_name} из secrets.yaml")
                        return match.group(1).strip()

    return None


def get_coingecko_history(coin_id: str, vs_currency: str, days: int = 90) -> list:
    """Загружает историю цен из CoinGecko"""
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency={vs_currency.lower()}&days={days}&interval=daily"

    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read())
            return data.get("prices", [])
    except Exception as e:
        print(f"  ❌ Ошибка загрузки {coin_id}: {e}")
        return []


def call_ha_service(token: str, domain: str, service: str, data: dict) -> bool:
    """Вызывает сервис Home Assistant"""
    url = f"{HA_URL}/api/services/{domain}/{service}"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    try:
        req = urllib.request.Request(
            url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST"
        )
        with urllib.request.urlopen(req, timeout=60) as response:
            return response.status == 200
    except urllib.error.HTTPError as e:
        print(f"  ❌ HTTP Error: {e.code} - {e.read().decode()}")
        return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def import_statistics(
    token: str, statistic_id: str, prices: list, unit: str, coin_name: str
) -> int:
    """Импортирует статистику через HA API (как внешний источник)"""
    # Формируем статистику в формате HA
    statistics = []

    # Берём только одну точку в день (убираем дубликаты)
    seen_days = set()
    for ts_ms, price in prices:
        dt = datetime.fromtimestamp(ts_ms / 1000, tz=UTC)
        day_key = dt.strftime("%Y-%m-%d")

        if day_key in seen_days:
            continue
        seen_days.add(day_key)

        # Округляем до начала часа
        dt_hour = dt.replace(minute=0, second=0, microsecond=0)

        statistics.append(
            {
                "start": dt_hour.isoformat(),
                "mean": price,
                "min": price,
                "max": price,
                "state": price,
            }
        )

    # Для импорта используем внешний источник (не recorder)
    # statistic_id формат: external_source:identifier
    external_id = f"coingecko:{statistic_id.replace('sensor.', '')}"

    data = {
        "statistic_id": external_id,
        "source": "coingecko",
        "name": f"{coin_name} Price ({unit})",
        "unit_of_measurement": unit,
        "has_mean": True,
        "has_sum": False,
        "stats": statistics,
    }

    success = call_ha_service(token, "recorder", "import_statistics", data)
    return len(statistics) if success else 0


def main():
    parser = argparse.ArgumentParser(description="Import crypto history to HA")
    parser.add_argument("--days", type=int, default=90, help="Days of history")
    args = parser.parse_args()

    print(f"📅 Загружаем историю за {args.days} дней")
    print()

    # Получаем токен
    token = get_ha_token()
    if not token:
        print("❌ HA Token не найден!")
        print("   Добавьте ha_long_lived_token в secrets.yaml")
        print("   или установите переменную SUPERVISOR_TOKEN")
        return

    print("🔑 Токен найден")
    print()

    total_imported = 0

    for entity_id, (coin_id, currency, display_name) in SENSORS_MAP.items():
        print(f"🪙 {display_name} ({currency}) → {entity_id}")

        # Загружаем данные
        prices = get_coingecko_history(coin_id, currency, args.days)
        if not prices:
            continue

        print(f"  📊 Загружено {len(prices)} точек")

        # Импортируем
        imported = import_statistics(token, entity_id, prices, currency, display_name)
        total_imported += imported

        if imported:
            print(f"  ✅ Импортировано: {imported}")
        else:
            print("  ⚠️ Ошибка импорта")

        # Пауза между запросами (CoinGecko rate limit: ~30 req/min для бесплатного API)
        time.sleep(3)
        print()

    print(f"🎉 Всего импортировано: {total_imported} точек")


if __name__ == "__main__":
    main()
