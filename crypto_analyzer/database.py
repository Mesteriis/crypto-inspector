"""
Database Module - SQLite хранилище для крипто-данных

Таблицы:
- ohlcv: Свечные данные (4H, Daily, Weekly)
- coins: Конфигурация монет
- signals: История сигналов
- fingerprints: ML fingerprints для pattern matching
- cycle_events: События циклов (halving, ATH, ATL)
- whale_transactions: Крупные транзакции
- staking_positions: Позиции в стейкинге
"""

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# Настройка логирования
logger = logging.getLogger(__name__)

# Путь к базе данных
DB_PATH = Path(__file__).parent.parent.parent / "crypto_history.db"


class CryptoDatabase:
    """Класс для работы с SQLite базой данных криптовалют"""

    def __init__(self, db_path: Path | None = None):
        """
        Инициализация базы данных

        Args:
            db_path: Путь к файлу базы данных (по умолчанию crypto_history.db)
        """
        self.db_path = db_path or DB_PATH
        self._init_database()

    @contextmanager
    def _get_connection(self):
        """Context manager для подключения к БД"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Доступ к колонкам по имени
        try:
            yield conn
        finally:
            conn.close()

    def _init_database(self):
        """Создание всех таблиц при инициализации"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # =========================================================
            # OHLCV - Свечные данные
            # =========================================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ohlcv (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume REAL NOT NULL,
                    source TEXT DEFAULT 'binance',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, timeframe, timestamp)
                )
            """)

            # Индексы для быстрого поиска
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol_tf_ts
                ON ohlcv(symbol, timeframe, timestamp DESC)
            """)

            # =========================================================
            # COINS - Конфигурация монет
            # =========================================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS coins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    coingecko_id TEXT,
                    binance_symbol TEXT,
                    bybit_symbol TEXT,
                    has_options BOOLEAN DEFAULT 0,
                    has_onchain BOOLEAN DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1,
                    priority INTEGER DEFAULT 100,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # =========================================================
            # SIGNALS - История сигналов
            # =========================================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    signal_type TEXT NOT NULL,
                    signal_subtype TEXT,
                    timeframe TEXT DEFAULT '1d',
                    signal_date DATE NOT NULL,
                    price_at_signal REAL NOT NULL,
                    direction TEXT,  -- 'bullish', 'bearish', 'neutral'
                    strength INTEGER,  -- 1-10
                    description TEXT,
                    description_ru TEXT,
                    -- Результаты (заполняются позже)
                    result_1d REAL,
                    result_7d REAL,
                    result_30d REAL,
                    result_90d REAL,
                    -- Метаданные
                    metadata JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, signal_type, signal_date, timeframe)
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_signals_symbol_type
                ON signals(symbol, signal_type, signal_date DESC)
            """)

            # =========================================================
            # FINGERPRINTS - ML паттерны для similarity search
            # =========================================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fingerprints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    date DATE NOT NULL,
                    timeframe TEXT DEFAULT '1d',
                    -- Технические индикаторы (нормализованные)
                    rsi REAL,
                    price_vs_sma200 REAL,  -- % отклонения
                    price_vs_sma50 REAL,
                    macd_histogram REAL,
                    bb_position REAL,  -- 0-100 (нижняя-верхняя)
                    volume_sma_ratio REAL,
                    -- On-chain (если доступно)
                    mvrv REAL,
                    sopr REAL,
                    exchange_reserves_change REAL,
                    -- Sentiment
                    fear_greed REAL,
                    funding_rate REAL,
                    -- Cycle
                    days_since_halving INTEGER,
                    cycle_phase TEXT,
                    -- Результаты (для обучения)
                    outcome_7d REAL,
                    outcome_30d REAL,
                    outcome_90d REAL,
                    -- Метаданные
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, date, timeframe)
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_fingerprints_symbol_date
                ON fingerprints(symbol, date DESC)
            """)

            # =========================================================
            # CYCLE_EVENTS - События циклов
            # =========================================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cycle_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    event_type TEXT NOT NULL,  -- 'halving', 'ath', 'atl', 'golden_cross', 'death_cross'
                    event_date DATE NOT NULL,
                    price REAL,
                    description TEXT,
                    metadata JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, event_type, event_date)
                )
            """)

            # =========================================================
            # WHALE_TRANSACTIONS - Крупные транзакции
            # =========================================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS whale_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    tx_hash TEXT UNIQUE,
                    timestamp INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    amount_usd REAL,
                    from_address TEXT,
                    to_address TEXT,
                    from_type TEXT,  -- 'exchange', 'whale', 'unknown'
                    to_type TEXT,
                    exchange_name TEXT,
                    direction TEXT,  -- 'to_exchange', 'from_exchange', 'whale_to_whale'
                    source TEXT,  -- 'whale_alert', 'blockchain_com', etc
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_whale_tx_symbol_ts
                ON whale_transactions(symbol, timestamp DESC)
            """)

            # =========================================================
            # STAKING_POSITIONS - Позиции в стейкинге
            # =========================================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS staking_positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    protocol TEXT NOT NULL,
                    amount REAL NOT NULL,
                    entry_date DATE NOT NULL,
                    entry_price REAL,
                    current_apy REAL,
                    rewards_earned REAL DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1,
                    metadata JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # =========================================================
            # PORTFOLIO - Позиции в портфеле
            # =========================================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS portfolio (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    amount REAL NOT NULL,
                    avg_buy_price REAL NOT NULL,
                    first_buy_date DATE,
                    last_buy_date DATE,
                    notes TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol)
                )
            """)

            # =========================================================
            # PRICE_ALERTS - Ценовые алерты
            # =========================================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS price_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    alert_type TEXT NOT NULL,  -- 'above', 'below'
                    target_price REAL NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    triggered_at TIMESTAMP,
                    triggered_price REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # =========================================================
            # ANALYSIS_CACHE - Кэш анализа
            # =========================================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analysis_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    analysis_type TEXT NOT NULL,
                    timeframe TEXT DEFAULT '1d',
                    data JSON NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, analysis_type, timeframe)
                )
            """)

            conn.commit()
            logger.info(f"База данных инициализирована: {self.db_path}")

    # =========================================================================
    # OHLCV МЕТОДЫ
    # =========================================================================

    def insert_ohlcv(self, symbol: str, timeframe: str, candles: list[dict]) -> int:
        """
        Вставка свечных данных (с upsert)

        Args:
            symbol: Символ монеты (BTC, ETH)
            timeframe: Таймфрейм (4h, 1d, 1w)
            candles: Список свечей [{timestamp, open, high, low, close, volume}, ...]

        Returns:
            Количество вставленных/обновлённых записей
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            count = 0

            for candle in candles:
                cursor.execute(
                    """
                    INSERT INTO ohlcv (symbol, timeframe, timestamp, open, high, low, close, volume, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(symbol, timeframe, timestamp)
                    DO UPDATE SET
                        open = excluded.open,
                        high = excluded.high,
                        low = excluded.low,
                        close = excluded.close,
                        volume = excluded.volume,
                        source = excluded.source
                """,
                    (
                        symbol.upper(),
                        timeframe,
                        candle["timestamp"],
                        candle["open"],
                        candle["high"],
                        candle["low"],
                        candle["close"],
                        candle["volume"],
                        candle.get("source", "binance"),
                    ),
                )
                count += 1

            conn.commit()
            logger.debug(f"Вставлено {count} свечей для {symbol} ({timeframe})")
            return count

    def get_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 200,
        start_ts: int | None = None,
        end_ts: int | None = None,
    ) -> list[dict]:
        """
        Получение свечных данных

        Args:
            symbol: Символ монеты
            timeframe: Таймфрейм
            limit: Максимальное количество свечей
            start_ts: Начальный timestamp (опционально)
            end_ts: Конечный timestamp (опционально)

        Returns:
            Список свечей (от старых к новым)
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            query = """
                SELECT timestamp, open, high, low, close, volume
                FROM ohlcv
                WHERE symbol = ? AND timeframe = ?
            """
            params = [symbol.upper(), timeframe]

            if start_ts:
                query += " AND timestamp >= ?"
                params.append(start_ts)
            if end_ts:
                query += " AND timestamp <= ?"
                params.append(end_ts)

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            # Разворачиваем для хронологического порядка
            candles = [dict(row) for row in reversed(rows)]
            return candles

    def get_latest_timestamp(self, symbol: str, timeframe: str) -> int | None:
        """Получить timestamp последней свечи"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT MAX(timestamp) FROM ohlcv
                WHERE symbol = ? AND timeframe = ?
            """,
                (symbol.upper(), timeframe),
            )
            result = cursor.fetchone()
            return result[0] if result and result[0] else None

    def get_ohlcv_count(self, symbol: str, timeframe: str) -> int:
        """Получить количество свечей"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COUNT(*) FROM ohlcv
                WHERE symbol = ? AND timeframe = ?
            """,
                (symbol.upper(), timeframe),
            )
            return cursor.fetchone()[0]

    # =========================================================================
    # SIGNALS МЕТОДЫ
    # =========================================================================

    def insert_signal(
        self,
        symbol: str,
        signal_type: str,
        signal_date: str,
        price: float,
        direction: str = "neutral",
        strength: int = 5,
        description: str = "",
        description_ru: str = "",
        timeframe: str = "1d",
        signal_subtype: str = None,
        metadata: dict = None,
    ) -> int:
        """Вставка нового сигнала"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO signals
                (symbol, signal_type, signal_subtype, timeframe, signal_date,
                 price_at_signal, direction, strength, description, description_ru, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol, signal_type, signal_date, timeframe) DO UPDATE SET
                    price_at_signal = excluded.price_at_signal,
                    direction = excluded.direction,
                    strength = excluded.strength,
                    description = excluded.description,
                    description_ru = excluded.description_ru
            """,
                (
                    symbol.upper(),
                    signal_type,
                    signal_subtype,
                    timeframe,
                    signal_date,
                    price,
                    direction,
                    strength,
                    description,
                    description_ru,
                    json.dumps(metadata) if metadata else None,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def get_signal_history(self, symbol: str, signal_type: str, limit: int = 20) -> list[dict]:
        """Получить историю сигналов определённого типа"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM signals
                WHERE symbol = ? AND signal_type = ?
                ORDER BY signal_date DESC
                LIMIT ?
            """,
                (symbol.upper(), signal_type, limit),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_last_signal(self, symbol: str, signal_type: str) -> dict | None:
        """Получить последний сигнал"""
        signals = self.get_signal_history(symbol, signal_type, limit=1)
        return signals[0] if signals else None

    def update_signal_outcomes(self):
        """Обновить результаты сигналов (вызывать периодически)"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Получаем сигналы без результатов старше 1 дня
            cursor.execute("""
                SELECT id, symbol, signal_date, price_at_signal, timeframe
                FROM signals
                WHERE result_7d IS NULL
                  AND signal_date < date('now', '-1 day')
            """)
            signals_to_update = cursor.fetchall()

            for signal in signals_to_update:
                signal_id, symbol, signal_date, price_at_signal, timeframe = signal

                # Получаем цены через 1, 7, 30, 90 дней
                for days, column in [
                    (1, "result_1d"),
                    (7, "result_7d"),
                    (30, "result_30d"),
                    (90, "result_90d"),
                ]:
                    future_date = datetime.strptime(signal_date, "%Y-%m-%d") + timedelta(days=days)

                    if future_date <= datetime.now():
                        # Получаем цену на эту дату
                        cursor.execute(
                            """
                            SELECT close FROM ohlcv
                            WHERE symbol = ? AND timeframe = '1d'
                              AND date(timestamp/1000, 'unixepoch') = ?
                            LIMIT 1
                        """,
                            (symbol, future_date.strftime("%Y-%m-%d")),
                        )

                        result = cursor.fetchone()
                        if result and price_at_signal:
                            change_pct = ((result[0] - price_at_signal) / price_at_signal) * 100
                            cursor.execute(
                                f"""
                                UPDATE signals SET {column} = ? WHERE id = ?
                            """,
                                (round(change_pct, 2), signal_id),
                            )

            conn.commit()

    # =========================================================================
    # COINS МЕТОДЫ
    # =========================================================================

    def get_active_coins(self) -> list[dict]:
        """Получить список активных монет"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM coins WHERE is_active = 1
                ORDER BY priority ASC
            """)
            return [dict(row) for row in cursor.fetchall()]

    def add_coin(self, symbol: str, name: str, **kwargs) -> int:
        """Добавить монету"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO coins (symbol, name, coingecko_id, binance_symbol,
                                   bybit_symbol, has_options, has_onchain, priority)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol) DO UPDATE SET
                    name = excluded.name,
                    updated_at = CURRENT_TIMESTAMP
            """,
                (
                    symbol.upper(),
                    name,
                    kwargs.get("coingecko_id"),
                    kwargs.get("binance_symbol"),
                    kwargs.get("bybit_symbol"),
                    kwargs.get("has_options", False),
                    kwargs.get("has_onchain", False),
                    kwargs.get("priority", 100),
                ),
            )
            conn.commit()
            return cursor.lastrowid

    # =========================================================================
    # FINGERPRINTS МЕТОДЫ (для ML)
    # =========================================================================

    def insert_fingerprint(self, symbol: str, date: str, data: dict) -> int:
        """Вставка ML fingerprint"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO fingerprints
                (symbol, date, timeframe, rsi, price_vs_sma200, price_vs_sma50,
                 macd_histogram, bb_position, volume_sma_ratio, mvrv, sopr,
                 exchange_reserves_change, fear_greed, funding_rate,
                 days_since_halving, cycle_phase)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol, date, timeframe) DO UPDATE SET
                    rsi = excluded.rsi,
                    price_vs_sma200 = excluded.price_vs_sma200,
                    price_vs_sma50 = excluded.price_vs_sma50,
                    macd_histogram = excluded.macd_histogram,
                    bb_position = excluded.bb_position
            """,
                (
                    symbol.upper(),
                    date,
                    data.get("timeframe", "1d"),
                    data.get("rsi"),
                    data.get("price_vs_sma200"),
                    data.get("price_vs_sma50"),
                    data.get("macd_histogram"),
                    data.get("bb_position"),
                    data.get("volume_sma_ratio"),
                    data.get("mvrv"),
                    data.get("sopr"),
                    data.get("exchange_reserves_change"),
                    data.get("fear_greed"),
                    data.get("funding_rate"),
                    data.get("days_since_halving"),
                    data.get("cycle_phase"),
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def find_similar_fingerprints(
        self, symbol: str, current: dict, tolerance: dict = None, limit: int = 20
    ) -> list[dict]:
        """
        Поиск похожих исторических ситуаций

        Args:
            symbol: Символ монеты
            current: Текущий fingerprint
            tolerance: Допустимые отклонения для каждого параметра
            limit: Максимальное количество результатов
        """
        tolerance = tolerance or {"rsi": 10, "price_vs_sma200": 10, "fear_greed": 15, "mvrv": 0.3}

        with self._get_connection() as conn:
            cursor = conn.cursor()

            query = """
                SELECT *,
                       ABS(rsi - ?) + ABS(price_vs_sma200 - ?) + ABS(fear_greed - ?) as similarity
                FROM fingerprints
                WHERE symbol = ?
                  AND outcome_30d IS NOT NULL
            """
            params = [
                current.get("rsi", 50),
                current.get("price_vs_sma200", 0),
                current.get("fear_greed", 50),
                symbol.upper(),
            ]

            # Добавляем фильтры по tolerance
            if current.get("rsi"):
                query += " AND ABS(rsi - ?) < ?"
                params.extend([current["rsi"], tolerance["rsi"]])

            if current.get("cycle_phase"):
                query += " AND cycle_phase = ?"
                params.append(current["cycle_phase"])

            query += " ORDER BY similarity ASC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    # =========================================================================
    # PORTFOLIO МЕТОДЫ
    # =========================================================================

    def update_portfolio(self, symbol: str, amount: float, avg_price: float):
        """Обновить позицию в портфеле"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO portfolio (symbol, amount, avg_buy_price, first_buy_date, last_buy_date)
                VALUES (?, ?, ?, date('now'), date('now'))
                ON CONFLICT(symbol) DO UPDATE SET
                    amount = excluded.amount,
                    avg_buy_price = excluded.avg_buy_price,
                    last_buy_date = date('now'),
                    updated_at = CURRENT_TIMESTAMP
            """,
                (symbol.upper(), amount, avg_price),
            )
            conn.commit()

    def get_portfolio(self) -> list[dict]:
        """Получить весь портфель"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM portfolio WHERE is_active = 1
            """)
            return [dict(row) for row in cursor.fetchall()]

    # =========================================================================
    # WHALE МЕТОДЫ
    # =========================================================================

    def insert_whale_transaction(self, tx: dict) -> int:
        """Вставка транзакции кита"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR IGNORE INTO whale_transactions
                (symbol, tx_hash, timestamp, amount, amount_usd, from_address, to_address,
                 from_type, to_type, exchange_name, direction, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    tx["symbol"].upper(),
                    tx.get("tx_hash"),
                    tx["timestamp"],
                    tx["amount"],
                    tx.get("amount_usd"),
                    tx.get("from_address"),
                    tx.get("to_address"),
                    tx.get("from_type"),
                    tx.get("to_type"),
                    tx.get("exchange_name"),
                    tx.get("direction"),
                    tx.get("source", "whale_alert"),
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def get_whale_flow(self, symbol: str, hours: int = 24) -> dict:
        """Получить поток китов за период"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cutoff = int((datetime.now() - timedelta(hours=hours)).timestamp() * 1000)

            cursor.execute(
                """
                SELECT
                    SUM(CASE WHEN direction = 'to_exchange' THEN amount ELSE 0 END) as to_exchange,
                    SUM(CASE WHEN direction = 'from_exchange' THEN amount ELSE 0 END) as from_exchange,
                    COUNT(*) as tx_count
                FROM whale_transactions
                WHERE symbol = ? AND timestamp > ?
            """,
                (symbol.upper(), cutoff),
            )

            row = cursor.fetchone()
            to_exchange = row[0] or 0
            from_exchange = row[1] or 0

            return {
                "to_exchange": to_exchange,
                "from_exchange": from_exchange,
                "net_flow": to_exchange - from_exchange,
                "tx_count": row[2] or 0,
                "interpretation": "selling_pressure"
                if to_exchange > from_exchange
                else "accumulation",
            }

    # =========================================================================
    # CACHE МЕТОДЫ
    # =========================================================================

    def set_cache(
        self,
        symbol: str,
        analysis_type: str,
        data: Any,
        ttl_minutes: int = 60,
        timeframe: str = "1d",
    ):
        """Сохранить данные в кэш"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            expires_at = datetime.now() + timedelta(minutes=ttl_minutes)
            cursor.execute(
                """
                INSERT INTO analysis_cache (symbol, analysis_type, timeframe, data, expires_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(symbol, analysis_type, timeframe) DO UPDATE SET
                    data = excluded.data,
                    expires_at = excluded.expires_at,
                    created_at = CURRENT_TIMESTAMP
            """,
                (symbol.upper(), analysis_type, timeframe, json.dumps(data), expires_at),
            )
            conn.commit()

    def get_cache(self, symbol: str, analysis_type: str, timeframe: str = "1d") -> Any | None:
        """Получить данные из кэша (если не истёк)"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT data FROM analysis_cache
                WHERE symbol = ? AND analysis_type = ? AND timeframe = ?
                  AND expires_at > datetime('now')
            """,
                (symbol.upper(), analysis_type, timeframe),
            )
            row = cursor.fetchone()
            return json.loads(row[0]) if row else None

    def clear_expired_cache(self):
        """Очистить истёкший кэш"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM analysis_cache WHERE expires_at < datetime('now')")
            conn.commit()

    # =========================================================================
    # СТАТИСТИКА
    # =========================================================================

    def get_database_stats(self) -> dict:
        """Получить статистику базы данных"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            stats = {}

            # Количество записей в каждой таблице
            tables = [
                "ohlcv",
                "coins",
                "signals",
                "fingerprints",
                "whale_transactions",
                "portfolio",
            ]

            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                stats[f"{table}_count"] = cursor.fetchone()[0]

            # Размер файла
            stats["db_size_mb"] = round(self.db_path.stat().st_size / (1024 * 1024), 2)

            # Диапазон данных OHLCV
            cursor.execute("""
                SELECT symbol, timeframe,
                       MIN(date(timestamp/1000, 'unixepoch')) as from_date,
                       MAX(date(timestamp/1000, 'unixepoch')) as to_date,
                       COUNT(*) as candles
                FROM ohlcv
                GROUP BY symbol, timeframe
            """)
            stats["ohlcv_coverage"] = [dict(row) for row in cursor.fetchall()]

            return stats


# Singleton instance
_db_instance: CryptoDatabase | None = None


def get_database() -> CryptoDatabase:
    """Получить singleton экземпляр базы данных"""
    global _db_instance
    if _db_instance is None:
        _db_instance = CryptoDatabase()
    return _db_instance


if __name__ == "__main__":
    # Тест базы данных
    logging.basicConfig(level=logging.INFO)

    db = get_database()
    print(f"Database path: {db.db_path}")
    print(f"Stats: {json.dumps(db.get_database_stats(), indent=2)}")
