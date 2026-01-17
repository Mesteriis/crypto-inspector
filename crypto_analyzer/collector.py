"""
Data Collector - Сбор данных из криптобирж

Источники:
- Binance (основной)
- Bybit (резервный)
- CoinGecko (fallback)

Функции:
- Получение OHLCV свечей
- Backfill исторических данных
- Автоматический выбор источника
"""

import asyncio
import logging
from datetime import datetime, timedelta

import aiohttp
from database import CryptoDatabase, get_database

# Настройка логирования
logger = logging.getLogger(__name__)

# ============================================================================
# КОНСТАНТЫ
# ============================================================================

# Binance API
BINANCE_BASE_URL = "https://api.binance.com/api/v3"
BINANCE_KLINES_ENDPOINT = "/klines"

# Bybit API
BYBIT_BASE_URL = "https://api.bybit.com/v5/market"
BYBIT_KLINES_ENDPOINT = "/kline"

# CoinGecko API
COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"

# Маппинг таймфреймов
TIMEFRAME_MAP = {
    "4h": {
        "binance": "4h",
        "bybit": "240",
        "ms_interval": 4 * 60 * 60 * 1000,  # 4 часа в мс
    },
    "1d": {
        "binance": "1d",
        "bybit": "D",
        "ms_interval": 24 * 60 * 60 * 1000,  # 1 день в мс
    },
    "1w": {
        "binance": "1w",
        "bybit": "W",
        "ms_interval": 7 * 24 * 60 * 60 * 1000,  # 1 неделя в мс
    },
}

# Маппинг символов
SYMBOL_MAP = {
    "BTC": {"binance": "BTCUSDT", "bybit": "BTCUSDT", "coingecko": "bitcoin"},
    "ETH": {"binance": "ETHUSDT", "bybit": "ETHUSDT", "coingecko": "ethereum"},
    "SOL": {"binance": "SOLUSDT", "bybit": "SOLUSDT", "coingecko": "solana"},
    "ADA": {"binance": "ADAUSDT", "bybit": "ADAUSDT", "coingecko": "cardano"},
    "XRP": {"binance": "XRPUSDT", "bybit": "XRPUSDT", "coingecko": "ripple"},
    "DOT": {"binance": "DOTUSDT", "bybit": "DOTUSDT", "coingecko": "polkadot"},
    "AVAX": {"binance": "AVAXUSDT", "bybit": "AVAXUSDT", "coingecko": "avalanche-2"},
    "MATIC": {"binance": "MATICUSDT", "bybit": "MATICUSDT", "coingecko": "matic-network"},
    "LINK": {"binance": "LINKUSDT", "bybit": "LINKUSDT", "coingecko": "chainlink"},
    "DOGE": {"binance": "DOGEUSDT", "bybit": "DOGEUSDT", "coingecko": "dogecoin"},
}


class DataCollector:
    """Сборщик данных из криптобирж"""

    def __init__(self, db: CryptoDatabase | None = None):
        self.db = db or get_database()
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Получить или создать HTTP сессию"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "application/json",
            }
            self._session = aiohttp.ClientSession(timeout=timeout, headers=headers)
        return self._session

    async def close(self):
        """Закрыть сессию"""
        if self._session and not self._session.closed:
            await self._session.close()

    # ========================================================================
    # BINANCE
    # ========================================================================

    async def fetch_binance_klines(
        self,
        symbol: str,
        timeframe: str,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int = 1000,
    ) -> list[dict]:
        """
        Получить свечи с Binance

        Args:
            symbol: Символ (BTC, ETH)
            timeframe: Таймфрейм (4h, 1d, 1w)
            start_time: Начальный timestamp в мс
            end_time: Конечный timestamp в мс
            limit: Максимум свечей (до 1000)

        Returns:
            Список свечей
        """
        session = await self._get_session()

        binance_symbol = SYMBOL_MAP.get(symbol.upper(), {}).get("binance", f"{symbol}USDT")
        binance_interval = TIMEFRAME_MAP.get(timeframe, {}).get("binance", timeframe)

        params = {"symbol": binance_symbol, "interval": binance_interval, "limit": limit}

        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time

        url = f"{BINANCE_BASE_URL}{BINANCE_KLINES_ENDPOINT}"

        try:
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Binance API error: {response.status} - {error_text}")
                    return []

                data = await response.json()

                candles = []
                for item in data:
                    candles.append(
                        {
                            "timestamp": item[0],  # Open time
                            "open": float(item[1]),
                            "high": float(item[2]),
                            "low": float(item[3]),
                            "close": float(item[4]),
                            "volume": float(item[5]),
                            "source": "binance",
                        }
                    )

                return candles

        except TimeoutError:
            logger.error(f"Binance timeout for {symbol}")
            return []
        except Exception as e:
            logger.error(f"Binance error for {symbol}: {e}")
            return []

    # ========================================================================
    # BYBIT
    # ========================================================================

    async def fetch_bybit_klines(
        self,
        symbol: str,
        timeframe: str,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int = 1000,
    ) -> list[dict]:
        """
        Получить свечи с Bybit

        Args:
            symbol: Символ (BTC, ETH)
            timeframe: Таймфрейм (4h, 1d, 1w)
            start_time: Начальный timestamp в мс
            end_time: Конечный timestamp в мс
            limit: Максимум свечей (до 1000)

        Returns:
            Список свечей
        """
        session = await self._get_session()

        bybit_symbol = SYMBOL_MAP.get(symbol.upper(), {}).get("bybit", f"{symbol}USDT")
        bybit_interval = TIMEFRAME_MAP.get(timeframe, {}).get("bybit", timeframe)

        params = {
            "category": "spot",
            "symbol": bybit_symbol,
            "interval": bybit_interval,
            "limit": limit,
        }

        if start_time:
            params["start"] = start_time
        if end_time:
            params["end"] = end_time

        url = f"{BYBIT_BASE_URL}{BYBIT_KLINES_ENDPOINT}"

        try:
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Bybit API error: {response.status} - {error_text}")
                    return []

                data = await response.json()

                if data.get("retCode") != 0:
                    logger.error(f"Bybit API error: {data.get('retMsg')}")
                    return []

                candles = []
                for item in data.get("result", {}).get("list", []):
                    candles.append(
                        {
                            "timestamp": int(item[0]),
                            "open": float(item[1]),
                            "high": float(item[2]),
                            "low": float(item[3]),
                            "close": float(item[4]),
                            "volume": float(item[5]),
                            "source": "bybit",
                        }
                    )

                # Bybit возвращает в обратном порядке
                candles.reverse()
                return candles

        except TimeoutError:
            logger.error(f"Bybit timeout for {symbol}")
            return []
        except Exception as e:
            logger.error(f"Bybit error for {symbol}: {e}")
            return []

    # ========================================================================
    # COINGECKO (Fallback)
    # ========================================================================

    async def fetch_coingecko_ohlc(self, symbol: str, days: int = 30) -> list[dict]:
        """
        Получить OHLC с CoinGecko (ограниченные данные)

        Args:
            symbol: Символ (BTC, ETH)
            days: Количество дней (1/7/14/30/90/180/365/max)

        Returns:
            Список свечей
        """
        session = await self._get_session()

        coin_id = SYMBOL_MAP.get(symbol.upper(), {}).get("coingecko", symbol.lower())

        url = f"{COINGECKO_BASE_URL}/coins/{coin_id}/ohlc"
        params = {"vs_currency": "usd", "days": days}

        try:
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"CoinGecko API error: {response.status} - {error_text}")
                    return []

                data = await response.json()

                candles = []
                for item in data:
                    candles.append(
                        {
                            "timestamp": item[0],
                            "open": float(item[1]),
                            "high": float(item[2]),
                            "low": float(item[3]),
                            "close": float(item[4]),
                            "volume": 0,  # CoinGecko OHLC не включает volume
                            "source": "coingecko",
                        }
                    )

                return candles

        except Exception as e:
            logger.error(f"CoinGecko error for {symbol}: {e}")
            return []

    # ========================================================================
    # ОСНОВНЫЕ МЕТОДЫ
    # ========================================================================

    async def fetch_klines(
        self,
        symbol: str,
        timeframe: str,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int = 1000,
        source: str = "auto",
    ) -> tuple[list[dict], str]:
        """
        Получить свечи с автоматическим fallback

        Args:
            symbol: Символ монеты
            timeframe: Таймфрейм
            start_time: Начальный timestamp
            end_time: Конечный timestamp
            limit: Максимум свечей
            source: Источник ('binance', 'bybit', 'coingecko', 'auto')

        Returns:
            Tuple (список свечей, использованный источник)
        """
        sources = ["binance", "bybit"] if source == "auto" else [source]

        for src in sources:
            if src == "binance":
                candles = await self.fetch_binance_klines(
                    symbol, timeframe, start_time, end_time, limit
                )
            elif src == "bybit":
                candles = await self.fetch_bybit_klines(
                    symbol, timeframe, start_time, end_time, limit
                )
            elif src == "coingecko":
                # CoinGecko только для daily данных
                days = min(limit, 365)
                candles = await self.fetch_coingecko_ohlc(symbol, days)
            else:
                continue

            if candles:
                logger.info(f"Получено {len(candles)} свечей {symbol}/{timeframe} с {src}")
                return candles, src

            logger.warning(f"Нет данных с {src} для {symbol}/{timeframe}, пробуем следующий...")
            await asyncio.sleep(1)  # Пауза перед следующим источником

        logger.error(f"Не удалось получить данные для {symbol}/{timeframe}")
        return [], "none"

    async def update_symbol(self, symbol: str, timeframe: str = "1d") -> int:
        """
        Обновить данные для символа (инкрементально)

        Args:
            symbol: Символ монеты
            timeframe: Таймфрейм

        Returns:
            Количество новых свечей
        """
        # Получаем последний timestamp из БД
        last_ts = self.db.get_latest_timestamp(symbol, timeframe)

        if last_ts:
            # Начинаем с последней свечи + 1 интервал
            ms_interval = TIMEFRAME_MAP.get(timeframe, {}).get("ms_interval", 86400000)
            start_time = last_ts + ms_interval
        else:
            # Первый запуск - берём данные за последние 30 дней
            start_time = int((datetime.now() - timedelta(days=30)).timestamp() * 1000)

        candles, source = await self.fetch_klines(symbol, timeframe, start_time=start_time)

        if candles:
            count = self.db.insert_ohlcv(symbol, timeframe, candles)
            logger.info(f"Обновлено {count} свечей для {symbol}/{timeframe}")
            return count

        return 0

    async def backfill_symbol(
        self, symbol: str, timeframe: str = "1d", years: int = 5, progress_callback=None
    ) -> int:
        """
        Загрузить историческиеdata для символа

        Args:
            symbol: Символ монеты
            timeframe: Таймфрейм
            years: Количество лет истории
            progress_callback: Callback для отображения прогресса

        Returns:
            Общее количество загруженных свечей
        """
        logger.info(f"Начинаем backfill {symbol}/{timeframe} за {years} лет...")

        ms_interval = TIMEFRAME_MAP.get(timeframe, {}).get("ms_interval", 86400000)

        # Определяем начальную дату
        start_date = datetime.now() - timedelta(days=years * 365)
        start_time = int(start_date.timestamp() * 1000)
        end_time = int(datetime.now().timestamp() * 1000)

        total_candles = 0
        current_start = start_time
        batch_num = 0

        while current_start < end_time:
            batch_num += 1

            candles, source = await self.fetch_klines(
                symbol, timeframe, start_time=current_start, limit=1000
            )

            if not candles:
                logger.warning(
                    f"Нет данных для {symbol} начиная с {datetime.fromtimestamp(current_start/1000)}"
                )
                break

            count = self.db.insert_ohlcv(symbol, timeframe, candles)
            total_candles += count

            # Следующий batch начинается после последней свечи
            current_start = candles[-1]["timestamp"] + ms_interval

            if progress_callback:
                progress = min(
                    100, int((current_start - start_time) / (end_time - start_time) * 100)
                )
                progress_callback(symbol, timeframe, progress, total_candles)

            logger.debug(f"Batch {batch_num}: загружено {count} свечей, всего {total_candles}")

            # Rate limiting
            await asyncio.sleep(0.5)

        logger.info(f"Backfill завершён: {symbol}/{timeframe} - {total_candles} свечей")
        return total_candles

    async def backfill_all(
        self,
        symbols: list[str] = None,
        timeframes: list[str] = None,
        years_map: dict[str, int] = None,
    ) -> dict[str, int]:
        """
        Загрузить историческиеdata для всех символов

        Args:
            symbols: Список символов (по умолчанию основные)
            timeframes: Список таймфреймов
            years_map: Сколько лет загружать для каждого символа

        Returns:
            Словарь {symbol: количество_свечей}
        """
        symbols = symbols or ["BTC", "ETH", "SOL"]
        timeframes = timeframes or ["1d", "1w"]
        years_map = years_map or {
            "BTC": 10,  # Bitcoin с 2015
            "ETH": 8,  # Ethereum с 2017
            "default": 5,  # Остальные за 5 лет
        }

        results = {}

        for symbol in symbols:
            years = years_map.get(symbol, years_map.get("default", 5))
            symbol_total = 0

            for timeframe in timeframes:
                count = await self.backfill_symbol(symbol, timeframe, years)
                symbol_total += count

            results[symbol] = symbol_total
            logger.info(f"✅ {symbol}: загружено {symbol_total} свечей")

        return results

    async def update_all(
        self, symbols: list[str] = None, timeframes: list[str] = None
    ) -> dict[str, int]:
        """
        Обновить данные для всех символов

        Args:
            symbols: Список символов
            timeframes: Список таймфреймов

        Returns:
            Словарь {symbol: количество_новых_свечей}
        """
        symbols = symbols or ["BTC", "ETH", "SOL", "ADA", "XRP", "DOT"]
        timeframes = timeframes or ["4h", "1d", "1w"]

        results = {}

        for symbol in symbols:
            symbol_total = 0

            for timeframe in timeframes:
                count = await self.update_symbol(symbol, timeframe)
                symbol_total += count
                await asyncio.sleep(0.2)  # Rate limiting

            results[symbol] = symbol_total

        total = sum(results.values())
        logger.info(f"Обновление завершено: {total} новых свечей")

        return results


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================


async def run_backfill(symbols: list[str] = None):
    """Запустить начальную загрузку данных"""
    collector = DataCollector()

    try:
        results = await collector.backfill_all(symbols=symbols)
        print("\n📊 Результаты backfill:")
        for symbol, count in results.items():
            print(f"  {symbol}: {count} свечей")
    finally:
        await collector.close()


async def run_update():
    """Запустить обновление данных"""
    collector = DataCollector()

    try:
        results = await collector.update_all()
        print(f"\n📊 Обновлено: {sum(results.values())} свечей")
    finally:
        await collector.close()


def print_progress(symbol: str, timeframe: str, progress: int, total: int):
    """Callback для отображения прогресса"""
    print(f"\r{symbol}/{timeframe}: {progress}% ({total} свечей)", end="", flush=True)


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "backfill":
            symbols = sys.argv[2:] if len(sys.argv) > 2 else None
            asyncio.run(run_backfill(symbols))

        elif command == "update":
            asyncio.run(run_update())

        else:
            print(f"Неизвестная команда: {command}")
            print("Использование:")
            print("  python collector.py backfill [BTC ETH SOL]")
            print("  python collector.py update")
    else:
        # По умолчанию - обновление
        asyncio.run(run_update())
