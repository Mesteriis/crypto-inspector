"""
Application constants.

Centralized location for all magic numbers and hardcoded values.
"""

from datetime import date

# =============================================================================
# VERSION
# =============================================================================

APP_VERSION = "0.2.17"

# =============================================================================
# RETRY CONFIGURATION
# =============================================================================

MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 10
RATE_LIMIT_DELAY_SECONDS = 0.5

# =============================================================================
# TIMEOUT DEFAULTS (seconds)
# =============================================================================


class Timeouts:
    """Default timeout values for various operations."""

    # HTTP clients
    DEFAULT = 30.0
    FAST = 15.0
    SLOW = 60.0
    VERY_SLOW = 120.0  # For AI/Ollama

    # Specific services
    CANDLESTICK_FETCH = 15.0
    DERIVATIVES = 15.0
    ONCHAIN = 15.0
    GAS_TRACKER = 15.0
    EXCHANGE_FLOW = 30.0
    LIQUIDATIONS = 30.0
    ALTSEASON = 30.0
    CORRELATION = 30.0
    DCA = 30.0
    PROFIT_TAKING = 30.0
    ARBITRAGE = 15.0

    # AI providers
    OPENAI = 60.0
    OLLAMA = 120.0


# =============================================================================
# PRICE DEFAULTS
# =============================================================================


class PriceDefaults:
    """Default price values for various assets."""

    # BTC cycle prices
    BTC_ATH = 109000.0  # All-time high (updated Dec 2024)
    BTC_CYCLE_LOW = 15500.0  # 2022 cycle low

    # Placeholder for unknown prices
    PLACEHOLDER_BTC = 100000.0


# =============================================================================
# TECHNICAL ANALYSIS
# =============================================================================


class TechnicalDefaults:
    """Default values for technical analysis."""

    # RSI
    RSI_PERIOD = 14
    RSI_OVERSOLD = 30
    RSI_OVERBOUGHT = 70

    # Moving Averages
    SMA_SHORT = 20
    SMA_MEDIUM = 50
    SMA_LONG = 200
    EMA_FAST = 12
    EMA_SLOW = 26

    # MACD
    MACD_FAST = 12
    MACD_SLOW = 26
    MACD_SIGNAL = 9

    # Bollinger Bands
    BB_PERIOD = 20
    BB_STD_DEV = 2.0
    BB_OVERSOLD_POSITION = 20
    BB_OVERBOUGHT_POSITION = 80

    # ATR
    ATR_PERIOD = 14

    # Support/Resistance
    SR_LOOKBACK = 50
    SR_THRESHOLD_PCT = 0.02

    # Minimum candles for analysis
    MIN_CANDLES = 26
    MIN_CANDLES_FOR_SMA200 = 200


# =============================================================================
# SCORING THRESHOLDS
# =============================================================================


class ScoringThresholds:
    """Thresholds for scoring engine."""

    # Overall score interpretation
    STRONG_BULLISH = 75
    BULLISH = 60
    SLIGHTLY_BULLISH = 55
    SLIGHTLY_BEARISH = 45
    BEARISH = 40
    STRONG_BEARISH = 25

    # Component score interpretation
    COMPONENT_BULLISH = 60
    COMPONENT_BEARISH = 40

    # Fear & Greed thresholds
    FG_EXTREME_FEAR = 25
    FG_FEAR = 45
    FG_GREED = 55
    FG_EXTREME_GREED = 75

    # Derivatives thresholds
    FUNDING_RATE_HIGH = 0.0005  # 0.05%
    FUNDING_RATE_LOW = -0.0002  # -0.02%
    LS_RATIO_HIGH = 1.5
    LS_RATIO_LOW = 0.67

    # On-chain thresholds
    MVRV_UNDERVALUED = 1.0
    MVRV_OVERVALUED = 3.5
    EXCHANGE_RESERVES_OUTFLOW = -5
    EXCHANGE_RESERVES_INFLOW = 5

    # Risk levels
    RISK_HIGH = 70
    RISK_MEDIUM = 40


# =============================================================================
# CYCLE DETECTION
# =============================================================================


class CycleConstants:
    """Constants for market cycle detection."""

    # Cycle length in days (~4 years)
    CYCLE_LENGTH_DAYS = 365 * 4  # 1460 days

    # Phase detection thresholds (% from ATH)
    ATH_EUPHORIA = 5
    ATH_BULL_RUN = 20
    ATH_ACCUMULATION = 80

    # Time thresholds (days since halving)
    HALVING_ACCUMULATION_END = 180
    HALVING_EARLY_BULL_END = 365
    HALVING_BULL_RUN_END = 540
    HALVING_DISTRIBUTION_END = 730
    HALVING_BEAR_END = 1095


# Bitcoin halving dates
HALVING_DATES = [
    date(2012, 11, 28),
    date(2016, 7, 9),
    date(2020, 5, 11),
    date(2024, 4, 20),
    date(2028, 4, 15),  # Estimated
    date(2032, 4, 15),  # Estimated
]

# Historical ATH data
BTC_ATH_HISTORY = [
    {"date": date(2013, 11, 30), "price": 1163},
    {"date": date(2017, 12, 17), "price": 19783},
    {"date": date(2021, 11, 10), "price": 69000},
    {"date": date(2024, 12, 5), "price": 109000},
]


# =============================================================================
# ALERTS AND NOTIFICATIONS
# =============================================================================


class AlertThresholds:
    """Thresholds for alerts and notifications."""

    # Whale activity
    WHALE_HIGH_ACTIVITY = 50  # transactions per 24h

    # Exchange flow
    EXCHANGE_SIGNIFICANT_OUTFLOW = -5000  # BTC

    # Red flags
    RED_FLAGS_CRITICAL = 3


# =============================================================================
# SYNC AND JOBS
# =============================================================================


class SyncDefaults:
    """Defaults for sync jobs."""

    # Candlestick fetch
    CANDLES_LIMIT = 10

    # Job notification
    NOTIFY_ON_HOURLY_SYNC = True
    NOTIFY_ON_DAILY_SYNC = True


# =============================================================================
# DEFAULT SYMBOLS
# =============================================================================

DEFAULT_SYMBOLS = ["BTC/USDT", "ETH/USDT"]
DEFAULT_SYMBOLS_STR = "BTC/USDT,ETH/USDT,SOL/USDT,TON/USDT,AR/USDT"


# =============================================================================
# ML FORECASTING
# =============================================================================


class MLDefaults:
    """Default values for ML forecasting."""

    # Prediction parameters
    PREDICTION_HORIZON = 3  # Candles forward (reduced for testing)
    CONTEXT_LENGTH = 100  # History for model (reduced for testing)
    MIN_TRAINING_POINTS = 50  # Minimum data points (reduced for testing)

    # Supported intervals
    SUPPORTED_INTERVALS = ["15m", "1h", "4h", "1d"]

    # Evaluation periods
    BACKTEST_TRAIN_DAYS = 270  # ~9 months training
    BACKTEST_VAL_DAYS = 90  # ~3 months validation
    BACKTEST_TEST_DAYS = 90  # ~3 months testing

    # Confidence intervals
    CONFIDENCE_LEVEL = 0.8  # 80% confidence


class MLModels:
    """ML model identifiers."""

    CHRONOS_BOLT = "chronos-bolt"  # amazon/chronos-bolt-tiny
    STATSFORECAST_ARIMA = "statsforecast"  # AutoARIMA
    NEURALPROPHET = "neuralprophet"  # NeuralProphet
    ENSEMBLE = "ensemble"  # Weighted average

    DEFAULT = CHRONOS_BOLT
    ALL = [CHRONOS_BOLT, STATSFORECAST_ARIMA, NEURALPROPHET]

    @classmethod
    def get_display_name(cls, model_id: str) -> str:
        """Get human-readable name for model."""
        names = {
            cls.CHRONOS_BOLT: "Amazon Chronos Bolt",
            cls.STATSFORECAST_ARIMA: "StatsForecast AutoARIMA",
            cls.NEURALPROPHET: "NeuralProphet",
            cls.ENSEMBLE: "Ensemble (Weighted Average)",
        }
        return names.get(model_id, model_id.title())
