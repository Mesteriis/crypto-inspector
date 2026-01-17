"""
Whale Tracker - Отслеживание крупных транзакций

Источники:
- Blockchain.info API (BTC бесплатно)
- Etherscan API (ETH бесплатно с ограничениями)
- Whale Alert API (платный, но есть бесплатный план)

Функции:
- Мониторинг крупных транзакций
- Exchange inflow/outflow
- Whale wallet tracking
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime

import aiohttp
from config_loader import get_api_key
from database import CryptoDatabase, get_database

logger = logging.getLogger(__name__)


# API Endpoints
BLOCKCHAIN_INFO_URL = "https://blockchain.info"
ETHERSCAN_URL = "https://api.etherscan.io/api"
BLOCKCHAIR_URL = "https://api.blockchair.com"


# Известные адреса бирж (частичный список)
KNOWN_EXCHANGES = {
    # BTC addresses (частичный список крупнейших)
    "btc": {
        "binance": [
            "34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo",
            "3LYJfcfHPXYJreMsASk2jkn69LWEYKzexb",
            "bc1qm34lsc65zpw79lxes69zkqmk6ee3ewf0j77s3h",
        ],
        "coinbase": [
            "1FzWLkAahHooV3kzHE4A2hU3nxnBePD1Hk",
            "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
        ],
        "kraken": [
            "bc1q4s8wcf7n9k4hdkpt9z68qzwzqxe8j3q0e4qvnx",
        ],
        "bitfinex": [
            "bc1qgdjqv0av3q56jvd82tkdjpy7gdp9ut8tlqmgrpmv24sq90ecnvqqjwvw97",
        ],
    },
    # ETH addresses
    "eth": {
        "binance": [
            "0x28C6c06298d514Db089934071355E5743bf21d60",
            "0xDFd5293D8e347dFe59E90eFd55b2956a1343963d",
        ],
        "coinbase": [
            "0x71660c4005BA85c37ccec55d0C4493E66Fe775d3",
        ],
    },
}

# Пороги для whale транзакций (в базовых единицах)
WHALE_THRESHOLDS = {
    "BTC": 100,  # 100 BTC
    "ETH": 1000,  # 1000 ETH
    "SOL": 50000,  # 50,000 SOL
}


@dataclass
class WhaleTransaction:
    """Структура whale транзакции"""

    symbol: str
    tx_hash: str
    timestamp: int
    amount: float
    amount_usd: float | None = None

    from_address: str | None = None
    to_address: str | None = None
    from_type: str = "unknown"  # 'exchange', 'whale', 'unknown'
    to_type: str = "unknown"
    from_exchange: str | None = None
    to_exchange: str | None = None

    direction: str = "unknown"  # 'to_exchange', 'from_exchange', 'whale_to_whale'

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "tx_hash": self.tx_hash,
            "timestamp": self.timestamp,
            "amount": self.amount,
            "amount_usd": self.amount_usd,
            "from": {
                "address": self.from_address[:16] + "..." if self.from_address else None,
                "type": self.from_type,
                "exchange": self.from_exchange,
            },
            "to": {
                "address": self.to_address[:16] + "..." if self.to_address else None,
                "type": self.to_type,
                "exchange": self.to_exchange,
            },
            "direction": self.direction,
        }

    def get_description_ru(self) -> str:
        """Получить описание на русском"""
        amount_str = f"{self.amount:,.2f} {self.symbol}"
        if self.amount_usd:
            amount_str += f" (${self.amount_usd:,.0f})"

        if self.direction == "to_exchange":
            emoji = "🔴"
            action = f"переведено на {self.to_exchange or 'биржу'}"
        elif self.direction == "from_exchange":
            emoji = "🟢"
            action = f"выведено с {self.from_exchange or 'биржи'}"
        else:
            emoji = "🐋"
            action = "перемещение между кошельками"

        return f"{emoji} {amount_str} - {action}"


@dataclass
class WhaleActivity:
    """Агрегированная активность китов"""

    symbol: str
    period_hours: int
    timestamp: int

    # Транзакции
    transactions: list[WhaleTransaction] = field(default_factory=list)
    total_transactions: int = 0

    # Потоки
    inflow_to_exchanges: float = 0  # К биржам
    outflow_from_exchanges: float = 0  # С бирж
    net_flow: float = 0  # Чистый поток (+ = к биржам)

    inflow_usd: float = 0
    outflow_usd: float = 0
    net_flow_usd: float = 0

    # Whale to Whale
    whale_to_whale_volume: float = 0

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "period_hours": self.period_hours,
            "timestamp": self.timestamp,
            "summary": {
                "total_transactions": self.total_transactions,
                "inflow_to_exchanges": self.inflow_to_exchanges,
                "outflow_from_exchanges": self.outflow_from_exchanges,
                "net_flow": self.net_flow,
                "net_flow_usd": self.net_flow_usd,
                "whale_to_whale": self.whale_to_whale_volume,
            },
            "interpretation": self.get_interpretation(),
            "transactions": [tx.to_dict() for tx in self.transactions[:10]],  # Top 10
        }

    def get_interpretation(self) -> dict:
        """Интерпретация активности"""
        if self.net_flow > 0:
            direction = "selling_pressure"
            direction_ru = "Давление на продажу"
            emoji = "🔴"
        elif self.net_flow < 0:
            direction = "accumulation"
            direction_ru = "Накопление"
            emoji = "🟢"
        else:
            direction = "neutral"
            direction_ru = "Нейтрально"
            emoji = "⚪"

        # Интенсивность
        threshold = WHALE_THRESHOLDS.get(self.symbol, 100)
        total_flow = abs(self.net_flow)

        if total_flow > threshold * 10:
            intensity = "extreme"
            intensity_ru = "Экстремальная"
        elif total_flow > threshold * 5:
            intensity = "high"
            intensity_ru = "Высокая"
        elif total_flow > threshold * 2:
            intensity = "moderate"
            intensity_ru = "Умеренная"
        else:
            intensity = "low"
            intensity_ru = "Низкая"

        return {
            "direction": direction,
            "direction_ru": f"{emoji} {direction_ru}",
            "intensity": intensity,
            "intensity_ru": intensity_ru,
        }

    def get_summary_ru(self) -> str:
        """Получить резюме на русском"""
        interp = self.get_interpretation()

        parts = [
            f"🐋 **Активность китов {self.symbol} за {self.period_hours}ч**",
            "",
            f"📊 Всего транзакций: {self.total_transactions}",
            f"📥 На биржи: {self.inflow_to_exchanges:,.2f} {self.symbol}",
            f"📤 С бирж: {self.outflow_from_exchanges:,.2f} {self.symbol}",
            "",
            f"💎 Чистый поток: {self.net_flow:+,.2f} {self.symbol}",
        ]

        if self.net_flow_usd:
            parts.append(f"   (${self.net_flow_usd:+,.0f})")

        parts.extend(
            [
                "",
                f"**Интерпретация:** {interp['direction_ru']}",
                f"**Интенсивность:** {interp['intensity_ru']}",
            ]
        )

        return "\n".join(parts)


class WhaleTracker:
    """Трекер китов"""

    def __init__(self, db: CryptoDatabase | None = None):
        self.db = db or get_database()
        self._session: aiohttp.ClientSession | None = None

        # API ключи (загружаются из config/secrets)
        self.whale_alert_key = get_api_key("whale_alert")
        self.etherscan_key = get_api_key("etherscan")

        # Логируем статус API
        if self.whale_alert_key:
            logger.info("Whale Alert API key configured")
        if self.etherscan_key:
            logger.info("Etherscan API key configured")

    async def _get_session(self) -> aiohttp.ClientSession:
        """Получить HTTP сессию"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=60)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self):
        """Закрыть сессию"""
        if self._session and not self._session.closed:
            await self._session.close()

    def _identify_address(self, address: str, symbol: str) -> tuple:
        """
        Определить тип адреса

        Returns:
            (type, exchange_name)
        """
        symbol_lower = symbol.lower()
        exchanges = KNOWN_EXCHANGES.get(symbol_lower, {})

        for exchange_name, addresses in exchanges.items():
            if address in addresses:
                return "exchange", exchange_name

        return "whale", None

    async def fetch_btc_large_transactions(self, hours: int = 24) -> list[dict]:
        """
        Получить крупные BTC транзакции

        Note: Blockchain.info не предоставляет прямой API для крупных транзакций,
        поэтому используем Blockchair или другой источник.
        Для демонстрации возвращаем пустой список.
        """
        # В реальности нужен Whale Alert API или подписка на Blockchair
        # Возвращаем заглушку
        logger.info("BTC whale tracking requires Whale Alert API or similar service")
        return []

    async def fetch_eth_large_transactions(
        self, hours: int = 24, api_key: str | None = None
    ) -> list[dict]:
        """
        Получить крупные ETH транзакции через Etherscan

        Note: Etherscan имеет лимиты на бесплатном плане.
        """
        if not api_key:
            logger.info("ETH whale tracking requires Etherscan API key")
            return []

        session = await self._get_session()
        transactions = []

        try:
            # Получаем последние блоки
            params = {"module": "proxy", "action": "eth_blockNumber", "apikey": api_key}

            async with session.get(ETHERSCAN_URL, params=params) as response:
                if response.status != 200:
                    return []

                data = await response.json()
                current_block = int(data.get("result", "0"), 16)

            # Для простоты не реализуем полный поиск
            # В реальности нужно сканировать блоки или использовать специализированный API

        except Exception as e:
            logger.error(f"Error fetching ETH transactions: {e}")

        return transactions

    async def get_exchange_flow_estimate(self, symbol: str, hours: int = 24) -> dict:
        """
        Оценка потока на/с бирж (упрощённая версия)

        В реальности требуется:
        - Whale Alert API
        - Glassnode / CryptoQuant
        - Собственный node с индексацией

        Returns:
            Dict с оценочными данными
        """
        # Возвращаем заглушку - в реальности нужен специализированный API
        return {
            "symbol": symbol,
            "period_hours": hours,
            "note": "Требуется API ключ для Whale Alert или Glassnode",
            "inflow": 0,
            "outflow": 0,
            "net_flow": 0,
        }

    def get_from_database(self, symbol: str, hours: int = 24) -> WhaleActivity:
        """
        Получить данные о китах из БД

        Returns:
            WhaleActivity с данными из БД
        """
        whale_flow = self.db.get_whale_flow(symbol, hours)

        activity = WhaleActivity(
            symbol=symbol.upper(),
            period_hours=hours,
            timestamp=int(datetime.now().timestamp() * 1000),
            inflow_to_exchanges=whale_flow.get("to_exchange", 0),
            outflow_from_exchanges=whale_flow.get("from_exchange", 0),
            net_flow=whale_flow.get("net_flow", 0),
            total_transactions=whale_flow.get("tx_count", 0),
        )

        return activity

    async def analyze(self, symbol: str, hours: int = 24) -> WhaleActivity:
        """
        Анализ активности китов

        Args:
            symbol: Символ монеты
            hours: Период в часах

        Returns:
            WhaleActivity
        """
        # Сначала пробуем получить из БД
        db_activity = self.get_from_database(symbol, hours)

        # Если есть данные, возвращаем их
        if db_activity.total_transactions > 0:
            return db_activity

        # Иначе возвращаем пустую активность с пояснением
        return WhaleActivity(
            symbol=symbol.upper(),
            period_hours=hours,
            timestamp=int(datetime.now().timestamp() * 1000),
        )

    def record_whale_transaction(self, tx: WhaleTransaction):
        """Записать whale транзакцию в БД"""
        self.db.insert_whale_transaction(
            {
                "symbol": tx.symbol,
                "tx_hash": tx.tx_hash,
                "timestamp": tx.timestamp,
                "amount": tx.amount,
                "amount_usd": tx.amount_usd,
                "from_address": tx.from_address,
                "to_address": tx.to_address,
                "from_type": tx.from_type,
                "to_type": tx.to_type,
                "exchange_name": tx.to_exchange or tx.from_exchange,
                "direction": tx.direction,
            }
        )

    def get_alert_thresholds(self, symbol: str) -> dict:
        """
        Получить пороги для алертов

        Returns:
            Dict с порогами
        """
        base_threshold = WHALE_THRESHOLDS.get(symbol.upper(), 100)

        return {
            "symbol": symbol,
            "whale_threshold": base_threshold,
            "large_whale_threshold": base_threshold * 5,
            "mega_whale_threshold": base_threshold * 20,
            "exchange_flow_alert_threshold": base_threshold * 10,
        }


# ============================================================================
# Helper functions
# ============================================================================


def create_mock_whale_activity(symbol: str, hours: int = 24) -> WhaleActivity:
    """
    Создать моковые данные для тестирования

    Returns:
        WhaleActivity с тестовыми данными
    """
    import random

    now = int(datetime.now().timestamp() * 1000)

    # Генерируем случайные транзакции
    transactions = []
    for i in range(random.randint(3, 8)):
        direction = random.choice(["to_exchange", "from_exchange", "whale_to_whale"])
        amount = random.uniform(100, 1000) if symbol == "BTC" else random.uniform(1000, 10000)

        tx = WhaleTransaction(
            symbol=symbol,
            tx_hash=f"mock_tx_{i}",
            timestamp=now - random.randint(0, hours * 3600 * 1000),
            amount=amount,
            amount_usd=amount * (95000 if symbol == "BTC" else 3500),
            direction=direction,
            from_type="whale" if direction != "from_exchange" else "exchange",
            to_type="exchange" if direction == "to_exchange" else "whale",
            from_exchange="binance" if direction == "from_exchange" else None,
            to_exchange="coinbase" if direction == "to_exchange" else None,
        )
        transactions.append(tx)

    # Агрегируем
    inflow = sum(tx.amount for tx in transactions if tx.direction == "to_exchange")
    outflow = sum(tx.amount for tx in transactions if tx.direction == "from_exchange")
    w2w = sum(tx.amount for tx in transactions if tx.direction == "whale_to_whale")

    price = 95000 if symbol == "BTC" else 3500

    return WhaleActivity(
        symbol=symbol,
        period_hours=hours,
        timestamp=now,
        transactions=transactions,
        total_transactions=len(transactions),
        inflow_to_exchanges=inflow,
        outflow_from_exchanges=outflow,
        net_flow=inflow - outflow,
        inflow_usd=inflow * price,
        outflow_usd=outflow * price,
        net_flow_usd=(inflow - outflow) * price,
        whale_to_whale_volume=w2w,
    )


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import json

    logging.basicConfig(level=logging.INFO)

    async def main():
        tracker = WhaleTracker()

        try:
            for symbol in ["BTC", "ETH"]:
                print(f"\n{'='*60}")
                print(f"WHALE ACTIVITY: {symbol}")
                print("=" * 60)

                # Реальный анализ (скорее всего пустой без API)
                activity = await tracker.analyze(symbol, hours=24)

                # Если нет данных, используем моковые для демонстрации
                if activity.total_transactions == 0:
                    print("\n[Используем тестовые данные для демонстрации]")
                    activity = create_mock_whale_activity(symbol)

                print(json.dumps(activity.to_dict(), indent=2, ensure_ascii=False))

                print("\nSUMMARY (RU):")
                print(activity.get_summary_ru())

                print("\nALERT THRESHOLDS:")
                print(json.dumps(tracker.get_alert_thresholds(symbol), indent=2))

        finally:
            await tracker.close()

    asyncio.run(main())
