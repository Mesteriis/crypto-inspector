"""
Crypto Analyzer - Комплексная система технического анализа криптовалют

Компоненты:
- database: SQLite хранилище данных
- collector: Сбор данных из API (Binance, Bybit, CoinGecko)
- analysis: Технический анализ (SMA, EMA, RSI, MACD, BB)
- mtf_analysis: Multi-timeframe анализ
- patterns: Детектор паттернов
- cycles: Определение рыночных циклов
- onchain: On-chain метрики (MVRV, SOPR, NVT)
- derivatives: Фьючерсы и опционы
- whale_tracker: Отслеживание китов
- ml_predictor: ML прогнозы
- scoring: Комплексный скоринг
- ai_analyzer: AI интерпретация через Ollama
"""

__version__ = "1.0.0"
__author__ = "SHome"

from pathlib import Path

# Пути
BASE_DIR = Path(__file__).parent
CONFIG_DIR = BASE_DIR.parent.parent  # /config
DB_PATH = CONFIG_DIR / "crypto_history.db"
CONFIG_PATH = BASE_DIR / "config.yaml"

# Настройки по умолчанию
DEFAULT_COINS = ["BTC", "ETH", "SOL"]
DEFAULT_TIMEFRAMES = ["4h", "1d", "1w"]

# Halving dates для Bitcoin
HALVING_DATES = [
    "2012-11-28",
    "2016-07-09",
    "2020-05-11",
    "2024-04-20",
    "2028-04-15",  # estimated
]
