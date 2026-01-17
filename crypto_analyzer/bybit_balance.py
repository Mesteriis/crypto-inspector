#!/usr/bin/env python3
"""
Bybit Balance Fetcher - получает балансы с Bybit API v5
Включает: UNIFIED кошелёк + Earn (Flexible Savings)

Использование:
    python3 bybit_balance.py

Требует secrets.yaml с:
    bybit_api_key: "your_key"
    bybit_api_secret: "your_secret"
"""

import hashlib
import hmac
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

# Конфигурация
BYBIT_API_URL = "https://api.bybit.com"
RECV_WINDOW = "5000"

# Пути к secrets.yaml
SECRETS_PATHS = [
    Path("/config/secrets.yaml"),
    Path("/homeassistant/secrets.yaml"),
    Path(__file__).parent.parent.parent / "secrets.yaml",
]

# Маппинг символов Bybit -> CoinGecko ID
COINGECKO_IDS = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "USDT": "tether",
    "USDC": "usd-coin",
    "SOL": "solana",
    "AR": "arweave",
    "TON": "the-open-network",
    "NEAR": "near",
    "DOGE": "dogecoin",
    "ADA": "cardano",
    "DOT": "polkadot",
    "XRP": "ripple",
    "RNDR": "render-token",
    "FET": "fetch-ai",
    "TAO": "bittensor",
}

# Кэш цен
_price_cache = {}


def fetch_coingecko_prices():
    """Получает актуальные цены из CoinGecko"""
    global _price_cache

    ids = ",".join(COINGECKO_IDS.values())
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd"

    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))

            # Конвертируем обратно в символы Bybit
            for symbol, cg_id in COINGECKO_IDS.items():
                if cg_id in data:
                    _price_cache[symbol] = data[cg_id].get("usd", 0)

            # Стейблкоины всегда = 1
            _price_cache["USDT"] = 1
            _price_cache["USDC"] = 1

            return True
    except Exception:
        return False


def load_secrets():
    """Загружает API ключи из secrets.yaml"""
    import re

    for path in SECRETS_PATHS:
        if path.exists():
            with open(path) as f:
                content = f.read()
                api_key_match = re.search(r'bybit_api_key:\s*["\']?([^"\'\n]+)["\']?', content)
                api_secret_match = re.search(
                    r'bybit_api_secret:\s*["\']?([^"\'\n]+)["\']?', content
                )

                if api_key_match and api_secret_match:
                    return {
                        "api_key": api_key_match.group(1).strip(),
                        "api_secret": api_secret_match.group(1).strip(),
                    }

    return None


def generate_signature(
    api_secret: str, timestamp: str, api_key: str, recv_window: str, query_string: str
) -> str:
    """Генерирует HMAC-SHA256 подпись для Bybit API v5"""
    param_str = f"{timestamp}{api_key}{recv_window}{query_string}"
    return hmac.new(
        api_secret.encode("utf-8"), param_str.encode("utf-8"), hashlib.sha256
    ).hexdigest()


def api_call(api_key: str, api_secret: str, endpoint: str, params: dict = None) -> dict:
    """Универсальный вызов Bybit API"""
    timestamp = str(int(time.time() * 1000))
    query_string = urllib.parse.urlencode(params) if params else ""
    signature = generate_signature(api_secret, timestamp, api_key, RECV_WINDOW, query_string)

    headers = {
        "X-BAPI-API-KEY": api_key,
        "X-BAPI-SIGN": signature,
        "X-BAPI-SIGN-TYPE": "2",
        "X-BAPI-TIMESTAMP": timestamp,
        "X-BAPI-RECV-WINDOW": RECV_WINDOW,
        "Content-Type": "application/json",
    }

    url = f"{BYBIT_API_URL}{endpoint}"
    if query_string:
        url += f"?{query_string}"

    req = urllib.request.Request(url, headers=headers, method="GET")

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"retCode": -1, "retMsg": f"HTTP Error: {e.code}", "result": {}}
    except Exception as e:
        return {"retCode": -1, "retMsg": str(e), "result": {}}


def get_wallet_balance(api_key: str, api_secret: str) -> dict:
    """Получает баланс UNIFIED кошелька"""
    return api_call(api_key, api_secret, "/v5/account/wallet-balance", {"accountType": "UNIFIED"})


def get_earn_positions(api_key: str, api_secret: str) -> dict:
    """Получает позиции в Earn (Flexible Savings)"""
    return api_call(api_key, api_secret, "/v5/earn/position", {"category": "FlexibleSaving"})


def get_coin_price(symbol: str) -> float:
    """Получает цену монеты из кэша CoinGecko"""
    symbol = symbol.upper()
    if symbol in _price_cache:
        return _price_cache[symbol]
    # Стейблкоины
    if symbol in ("USDT", "USDC", "DAI", "BUSD"):
        return 1.0
    return 0


def parse_all_balances(wallet_response: dict, earn_response: dict) -> dict:
    """Объединяет балансы из кошелька и Earn"""
    result = {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "total_usd": 0.0,
        "balances": {},
        "earn_balances": {},
        "wallet_balances": {},
        "account_type": "UNIFIED",
    }

    # Парсим кошелёк
    if wallet_response.get("retCode") == 0:
        for account in wallet_response.get("result", {}).get("list", []):
            result["account_type"] = account.get("accountType", "UNIFIED")
            for coin in account.get("coin", []):
                symbol = coin.get("coin", "")
                qty = float(coin.get("walletBalance", 0) or 0)
                usd_value = float(coin.get("usdValue", 0) or 0)

                if qty > 0.00000001:
                    result["wallet_balances"][symbol] = {
                        "qty": round(qty, 8),
                        "usd": round(usd_value, 2),
                    }

    # Парсим Earn
    if earn_response.get("retCode") == 0:
        for position in earn_response.get("result", {}).get("list", []):
            symbol = position.get("coin", "")
            qty = float(position.get("amount", 0) or 0)

            if qty > 0.00000001:
                # Получаем цену для расчёта USD
                price = get_coin_price(symbol)
                usd_value = qty * price

                result["earn_balances"][symbol] = {
                    "qty": round(qty, 8),
                    "usd": round(usd_value, 2),
                    "pnl": round(float(position.get("totalPnl", 0) or 0), 6),
                    "claimable": round(float(position.get("claimableYield", 0) or 0), 6),
                }

    # Объединяем балансы
    all_symbols = set(result["wallet_balances"].keys()) | set(result["earn_balances"].keys())

    for symbol in all_symbols:
        wallet = result["wallet_balances"].get(symbol, {"qty": 0, "usd": 0})
        earn = result["earn_balances"].get(symbol, {"qty": 0, "usd": 0})

        total_qty = wallet["qty"] + earn["qty"]
        total_usd = wallet["usd"] + earn["usd"]

        result["balances"][symbol] = {
            "qty": round(total_qty, 8),
            "usd": round(total_usd, 2),
            "in_wallet": round(wallet["qty"], 8),
            "in_earn": round(earn["qty"], 8),
        }

        result["total_usd"] += total_usd

    result["total_usd"] = round(result["total_usd"], 2)
    result["coins_count"] = len(result["balances"])

    # Убираем детальные балансы из вывода для краткости
    del result["wallet_balances"]
    del result["earn_balances"]

    return result


def main():
    """Главная функция"""
    secrets = load_secrets()

    if not secrets:
        error_result = {
            "status": "error",
            "error": "API keys not found in secrets.yaml",
            "timestamp": datetime.now().isoformat(),
            "total_usd": 0,
            "balances": {},
            "coins_count": 0,
        }
        print(json.dumps(error_result, ensure_ascii=False))
        return

    # Загружаем актуальные цены из CoinGecko
    fetch_coingecko_prices()

    # Получаем балансы из обоих источников
    wallet_response = get_wallet_balance(secrets["api_key"], secrets["api_secret"])
    earn_response = get_earn_positions(secrets["api_key"], secrets["api_secret"])

    # Объединяем результаты
    result = parse_all_balances(wallet_response, earn_response)

    # Выводим JSON
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
