"""
On-Chain Metrics - Метрики из блокчейна

Источники:
- CoinGlass (бесплатно, ограничено)
- Blockchain.com API (BTC)
- Etherscan API (ETH)
- Alternative.me (Fear & Greed)

Метрики:
- Fear & Greed Index
- Exchange Reserves (приблизительно)
- Active Addresses (BTC/ETH)
- Hash Rate (BTC)
- Transaction count
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime

import aiohttp
from config_loader import get_api_key
from database import CryptoDatabase, get_database

logger = logging.getLogger(__name__)


# API Endpoints
ALTERNATIVE_ME_FG_URL = "https://api.alternative.me/fng/?limit=30"
BLOCKCHAIN_INFO_URL = "https://api.blockchain.info"
COINGLASS_URL = "https://open-api.coinglass.com/public/v2"
MEMPOOL_SPACE_URL = "https://mempool.space/api/v1"


@dataclass
class OnChainMetrics:
    """Структура on-chain метрик"""

    symbol: str
    timestamp: int

    # Fear & Greed
    fear_greed_value: int | None = None
    fear_greed_classification: str | None = None
    fear_greed_trend: str | None = None  # 'increasing', 'decreasing', 'stable'

    # Bitcoin specific
    btc_hash_rate: float | None = None  # TH/s
    btc_difficulty: float | None = None
    btc_mempool_size: int | None = None  # tx count
    btc_avg_fee: float | None = None  # sat/vB

    # General
    active_addresses_24h: int | None = None
    transaction_count_24h: int | None = None

    # Exchange flow (если доступно)
    exchange_inflow: float | None = None
    exchange_outflow: float | None = None
    exchange_net_flow: float | None = None

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "fear_greed": {
                "value": self.fear_greed_value,
                "classification": self.fear_greed_classification,
                "trend": self.fear_greed_trend,
            },
            "bitcoin": {
                "hash_rate_th": self.btc_hash_rate,
                "difficulty": self.btc_difficulty,
                "mempool_tx_count": self.btc_mempool_size,
                "avg_fee_sat_vb": self.btc_avg_fee,
            },
            "network": {
                "active_addresses_24h": self.active_addresses_24h,
                "transaction_count_24h": self.transaction_count_24h,
            },
            "exchange_flow": {
                "inflow": self.exchange_inflow,
                "outflow": self.exchange_outflow,
                "net_flow": self.exchange_net_flow,
                "interpretation": self._interpret_flow(),
            },
        }

    def _interpret_flow(self) -> str:
        """Интерпретация exchange flow"""
        if self.exchange_net_flow is None:
            return "unknown"
        if self.exchange_net_flow > 1000:  # Большой приток на биржи
            return "selling_pressure"
        elif self.exchange_net_flow < -1000:  # Большой отток с бирж
            return "accumulation"
        else:
            return "neutral"

    def get_summary_ru(self) -> str:
        """Получить резюме на русском"""
        parts = []

        if self.fear_greed_value:
            fg_emoji = (
                "😱"
                if self.fear_greed_value < 25
                else "😰"
                if self.fear_greed_value < 45
                else "😐"
                if self.fear_greed_value < 55
                else "😊"
                if self.fear_greed_value < 75
                else "🤑"
            )
            parts.append(
                f"{fg_emoji} Fear & Greed: {self.fear_greed_value} ({self.fear_greed_classification})"
            )

        if self.btc_mempool_size:
            congestion = (
                "🟢 низкая"
                if self.btc_mempool_size < 50000
                else "🟡 средняя"
                if self.btc_mempool_size < 100000
                else "🔴 высокая"
            )
            parts.append(f"📦 Mempool: {self.btc_mempool_size:,} tx ({congestion} загрузка)")

        if self.btc_avg_fee:
            parts.append(f"💰 Средняя комиссия: {self.btc_avg_fee:.0f} sat/vB")

        flow = self._interpret_flow()
        if flow == "selling_pressure":
            parts.append("🔴 Приток на биржи (давление на продажу)")
        elif flow == "accumulation":
            parts.append("🟢 Отток с бирж (накопление)")

        return "\n".join(parts) if parts else "Нет данных"


class OnChainAnalyzer:
    """Анализатор on-chain метрик"""

    def __init__(self, db: CryptoDatabase | None = None):
        self.db = db or get_database()
        self._session: aiohttp.ClientSession | None = None

        # API ключи (загружаются из config/secrets)
        self.glassnode_key = get_api_key("glassnode")
        self.etherscan_key = get_api_key("etherscan")
        self.coinglass_key = get_api_key("coinglass")

        # Логируем доступные API
        available_apis = []
        if self.glassnode_key:
            available_apis.append("Glassnode")
        if self.etherscan_key:
            available_apis.append("Etherscan")
        if self.coinglass_key:
            available_apis.append("CoinGlass")

        if available_apis:
            logger.info(f"On-chain APIs configured: {', '.join(available_apis)}")

    async def _get_session(self) -> aiohttp.ClientSession:
        """Получить HTTP сессию"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self):
        """Закрыть сессию"""
        if self._session and not self._session.closed:
            await self._session.close()

    async def fetch_fear_greed(self) -> dict:
        """
        Получить Fear & Greed Index от Alternative.me

        Returns:
            Dict с индексом и историей
        """
        session = await self._get_session()

        try:
            async with session.get(ALTERNATIVE_ME_FG_URL) as response:
                if response.status != 200:
                    logger.error(f"Fear&Greed API error: {response.status}")
                    return {}

                data = await response.json()

                if not data.get("data"):
                    return {}

                current = data["data"][0]
                history = data["data"][:7]  # Последние 7 дней

                # Определяем тренд
                if len(history) >= 3:
                    recent_avg = sum(int(h["value"]) for h in history[:3]) / 3
                    older_avg = sum(int(h["value"]) for h in history[3:7]) / max(
                        1, len(history[3:7])
                    )

                    if recent_avg > older_avg + 5:
                        trend = "increasing"
                    elif recent_avg < older_avg - 5:
                        trend = "decreasing"
                    else:
                        trend = "stable"
                else:
                    trend = "unknown"

                return {
                    "value": int(current["value"]),
                    "classification": current["value_classification"],
                    "trend": trend,
                    "history": [
                        {"value": int(h["value"]), "date": h["timestamp"]} for h in history
                    ],
                }

        except Exception as e:
            logger.error(f"Error fetching Fear&Greed: {e}")
            return {}

    async def fetch_btc_mempool(self) -> dict:
        """
        Получить данные mempool BTC от mempool.space

        Returns:
            Dict с mempool данными
        """
        session = await self._get_session()

        try:
            # Mempool stats
            async with session.get(f"{MEMPOOL_SPACE_URL}/fees/mempool-blocks") as response:
                if response.status != 200:
                    return {}

                blocks = await response.json()

                total_tx = sum(b.get("nTx", 0) for b in blocks)
                avg_fee = sum(b.get("medianFee", 0) for b in blocks) / max(1, len(blocks))

                return {
                    "mempool_size": total_tx,
                    "avg_fee_sat_vb": avg_fee,
                    "blocks_pending": len(blocks),
                }

        except Exception as e:
            logger.error(f"Error fetching BTC mempool: {e}")
            return {}

    async def fetch_btc_hashrate(self) -> dict:
        """
        Получить hash rate BTC

        Returns:
            Dict с hash rate данными
        """
        session = await self._get_session()

        try:
            url = f"{BLOCKCHAIN_INFO_URL}/q/hashrate"
            async with session.get(url) as response:
                if response.status != 200:
                    return {}

                # Blockchain.info возвращает GH/s
                hashrate_ghs = float(await response.text())
                hashrate_ths = hashrate_ghs / 1000  # Convert to TH/s
                hashrate_ehs = hashrate_ths / 1_000_000  # Convert to EH/s

                return {
                    "hash_rate_ths": hashrate_ths,
                    "hash_rate_ehs": hashrate_ehs,
                }

        except Exception as e:
            logger.error(f"Error fetching BTC hashrate: {e}")
            return {}

    async def fetch_btc_difficulty(self) -> dict:
        """
        Получить сложность майнинга BTC

        Returns:
            Dict с difficulty данными
        """
        session = await self._get_session()

        try:
            url = f"{BLOCKCHAIN_INFO_URL}/q/getdifficulty"
            async with session.get(url) as response:
                if response.status != 200:
                    return {}

                difficulty = float(await response.text())

                return {
                    "difficulty": difficulty,
                    "difficulty_t": difficulty / 1e12,  # В триллионах
                }

        except Exception as e:
            logger.error(f"Error fetching BTC difficulty: {e}")
            return {}

    async def analyze(self, symbol: str = "BTC") -> OnChainMetrics:
        """
        Полный on-chain анализ

        Args:
            symbol: Символ (пока только BTC полностью поддерживается)

        Returns:
            OnChainMetrics
        """
        metrics = OnChainMetrics(
            symbol=symbol.upper(), timestamp=int(datetime.now().timestamp() * 1000)
        )

        # Параллельный сбор данных
        tasks = [
            self.fetch_fear_greed(),
            self.fetch_btc_mempool(),
            self.fetch_btc_hashrate(),
            self.fetch_btc_difficulty(),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Fear & Greed
        fg_data = results[0] if not isinstance(results[0], Exception) else {}
        if fg_data:
            metrics.fear_greed_value = fg_data.get("value")
            metrics.fear_greed_classification = fg_data.get("classification")
            metrics.fear_greed_trend = fg_data.get("trend")

        # Mempool
        mempool_data = results[1] if not isinstance(results[1], Exception) else {}
        if mempool_data:
            metrics.btc_mempool_size = mempool_data.get("mempool_size")
            metrics.btc_avg_fee = mempool_data.get("avg_fee_sat_vb")

        # Hash rate
        hashrate_data = results[2] if not isinstance(results[2], Exception) else {}
        if hashrate_data:
            metrics.btc_hash_rate = hashrate_data.get("hash_rate_ths")

        # Difficulty
        diff_data = results[3] if not isinstance(results[3], Exception) else {}
        if diff_data:
            metrics.btc_difficulty = diff_data.get("difficulty")

        return metrics

    def get_cached_or_fetch(self, symbol: str = "BTC") -> dict | None:
        """
        Получить из кэша или запросить новые данные

        Returns:
            Dict с on-chain данными
        """
        # Проверяем кэш (TTL 15 минут)
        cached = self.db.get_cache(symbol, "onchain")
        if cached:
            return cached

        # Запрашиваем новые данные (синхронно для простоты)
        try:
            loop = asyncio.new_event_loop()
            metrics = loop.run_until_complete(self.analyze(symbol))
            loop.close()

            data = metrics.to_dict()

            # Сохраняем в кэш
            self.db.set_cache(symbol, "onchain", data, ttl_minutes=15)

            return data
        except Exception as e:
            logger.error(f"Error fetching on-chain data: {e}")
            return None


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import json

    logging.basicConfig(level=logging.INFO)

    async def main():
        analyzer = OnChainAnalyzer()

        try:
            print("Fetching on-chain metrics...")
            metrics = await analyzer.analyze("BTC")

            print("\n" + "=" * 60)
            print("ON-CHAIN METRICS")
            print("=" * 60)
            print(json.dumps(metrics.to_dict(), indent=2, ensure_ascii=False))

            print("\n" + "=" * 60)
            print("SUMMARY (RU)")
            print("=" * 60)
            print(metrics.get_summary_ru())

        finally:
            await analyzer.close()

    asyncio.run(main())
