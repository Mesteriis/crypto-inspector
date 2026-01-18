"""
Real unit tests for TechnicalAnalyzer.

Tests cover:
- SMA/EMA calculations
- RSI calculation
- MACD calculation
- Bollinger Bands
- ATR
- Support/Resistance detection
- Full analysis
"""

import pytest

from services.analysis.technical import TechnicalAnalyzer, TechnicalIndicators


class TestSMACalculation:
    """Tests for Simple Moving Average calculation."""

    def test_sma_with_exact_period(self):
        """SMA should calculate correctly with exact period length."""
        analyzer = TechnicalAnalyzer()
        prices = [10, 20, 30, 40, 50]
        result = analyzer.calc_sma(prices, 5)
        assert result == 30.0  # (10+20+30+40+50) / 5 = 30

    def test_sma_with_more_data(self):
        """SMA should use only last N prices."""
        analyzer = TechnicalAnalyzer()
        prices = [5, 10, 20, 30, 40, 50]
        result = analyzer.calc_sma(prices, 3)
        assert result == 40.0  # (30+40+50) / 3 = 40

    def test_sma_insufficient_data(self):
        """SMA should return None with insufficient data."""
        analyzer = TechnicalAnalyzer()
        prices = [10, 20]
        result = analyzer.calc_sma(prices, 5)
        assert result is None

    def test_sma_empty_list(self):
        """SMA should return None for empty list."""
        analyzer = TechnicalAnalyzer()
        result = analyzer.calc_sma([], 5)
        assert result is None


class TestEMACalculation:
    """Tests for Exponential Moving Average calculation."""

    def test_ema_basic(self):
        """EMA should calculate correctly."""
        analyzer = TechnicalAnalyzer()
        prices = [22, 22.5, 22.25, 22.5, 22.75, 23, 23.25, 23.5, 23.75, 24]
        result = analyzer.calc_ema(prices, 5)
        assert result is not None
        assert 23.0 < result < 24.0

    def test_ema_insufficient_data(self):
        """EMA should return None with insufficient data."""
        analyzer = TechnicalAnalyzer()
        prices = [10, 20]
        result = analyzer.calc_ema(prices, 5)
        assert result is None

    def test_ema_series(self):
        """EMA series should return correct length."""
        analyzer = TechnicalAnalyzer()
        prices = list(range(1, 21))  # 1 to 20
        result = analyzer.calc_ema_series(prices, 5)
        assert len(result) == 16  # 20 - 5 + 1


class TestRSICalculation:
    """Tests for Relative Strength Index calculation."""

    def test_rsi_all_gains(self):
        """RSI should be 100 when all prices go up."""
        analyzer = TechnicalAnalyzer()
        prices = list(range(1, 20))  # Constant increase
        result = analyzer.calc_rsi(prices, 14)
        assert result == 100

    def test_rsi_all_losses(self):
        """RSI should be close to 0 when all prices go down."""
        analyzer = TechnicalAnalyzer()
        prices = list(range(20, 1, -1))  # Constant decrease
        result = analyzer.calc_rsi(prices, 14)
        assert result is not None
        assert result < 5

    def test_rsi_mixed(self):
        """RSI should be between 0 and 100 for mixed prices."""
        analyzer = TechnicalAnalyzer()
        prices = [44, 44.5, 43.5, 44.25, 45, 44.5, 45.5, 46, 45.5, 46.25, 47, 46.5, 47.5, 48, 47.25, 48.5]
        result = analyzer.calc_rsi(prices, 14)
        assert result is not None
        assert 0 <= result <= 100

    def test_rsi_oversold(self):
        """RSI should detect oversold conditions."""
        analyzer = TechnicalAnalyzer()
        # Sharp decline
        prices = [100, 98, 95, 92, 88, 84, 80, 76, 72, 68, 65, 62, 60, 58, 56, 55]
        result = analyzer.calc_rsi(prices, 14)
        assert result is not None
        assert result < 35  # Oversold territory

    def test_rsi_insufficient_data(self):
        """RSI should return None with insufficient data."""
        analyzer = TechnicalAnalyzer()
        prices = [10, 20, 30]
        result = analyzer.calc_rsi(prices, 14)
        assert result is None


class TestMACDCalculation:
    """Tests for MACD calculation."""

    def test_macd_basic(self):
        """MACD should return three values."""
        analyzer = TechnicalAnalyzer()
        prices = list(range(1, 50))  # 49 prices
        macd_line, signal_line, histogram = analyzer.calc_macd(prices)

        assert macd_line is not None
        assert signal_line is not None
        assert histogram is not None

    def test_macd_uptrend(self):
        """MACD should be positive in uptrend."""
        analyzer = TechnicalAnalyzer()
        # Strong uptrend
        prices = [i * 1.02 for i in range(30, 80)]
        macd_line, signal_line, histogram = analyzer.calc_macd(prices)

        assert macd_line is not None
        assert macd_line > 0

    def test_macd_insufficient_data(self):
        """MACD should return None tuple with insufficient data."""
        analyzer = TechnicalAnalyzer()
        prices = [10, 20, 30]
        macd_line, signal_line, histogram = analyzer.calc_macd(prices)

        assert macd_line is None
        assert signal_line is None
        assert histogram is None


class TestBollingerBands:
    """Tests for Bollinger Bands calculation."""

    def test_bb_basic(self):
        """Bollinger Bands should return four values."""
        analyzer = TechnicalAnalyzer()
        prices = [100 + i * 0.5 for i in range(30)]
        upper, middle, lower, position = analyzer.calc_bollinger_bands(prices)

        assert upper is not None
        assert middle is not None
        assert lower is not None
        assert position is not None
        assert upper > middle > lower

    def test_bb_position_in_range(self):
        """BB position should be between 0 and 100."""
        analyzer = TechnicalAnalyzer()
        prices = [100 + i * 0.5 for i in range(30)]
        _, _, _, position = analyzer.calc_bollinger_bands(prices)

        assert 0 <= position <= 100

    def test_bb_insufficient_data(self):
        """BB should return None tuple with insufficient data."""
        analyzer = TechnicalAnalyzer()
        prices = [10, 20, 30]
        upper, middle, lower, position = analyzer.calc_bollinger_bands(prices)

        assert upper is None
        assert middle is None
        assert lower is None
        assert position is None


class TestATRCalculation:
    """Tests for Average True Range calculation."""

    def test_atr_basic(self):
        """ATR should calculate correctly."""
        analyzer = TechnicalAnalyzer()
        candles = [
            {"high": 102, "low": 98, "close": 100},
            {"high": 104, "low": 99, "close": 103},
            {"high": 105, "low": 101, "close": 102},
            {"high": 106, "low": 100, "close": 105},
            {"high": 108, "low": 103, "close": 107},
            {"high": 110, "low": 105, "close": 108},
            {"high": 109, "low": 104, "close": 106},
            {"high": 108, "low": 102, "close": 104},
            {"high": 107, "low": 101, "close": 105},
            {"high": 109, "low": 103, "close": 108},
            {"high": 111, "low": 106, "close": 110},
            {"high": 113, "low": 108, "close": 112},
            {"high": 115, "low": 110, "close": 114},
            {"high": 116, "low": 112, "close": 115},
            {"high": 118, "low": 113, "close": 117},
            {"high": 120, "low": 115, "close": 119},
        ]
        result = analyzer.calc_atr(candles, 14)
        assert result is not None
        assert result > 0

    def test_atr_insufficient_data(self):
        """ATR should return None with insufficient data."""
        analyzer = TechnicalAnalyzer()
        candles = [
            {"high": 102, "low": 98, "close": 100},
            {"high": 104, "low": 99, "close": 103},
        ]
        result = analyzer.calc_atr(candles, 14)
        assert result is None


class TestSupportResistance:
    """Tests for Support/Resistance detection."""

    def test_find_sr_levels(self):
        """Should find support and resistance levels."""
        analyzer = TechnicalAnalyzer()

        # Create candles with clear levels
        candles = []
        base_price = 100
        for i in range(60):
            if i % 10 < 5:
                # Oscillate between 95-100
                price = 95 + (i % 5)
            else:
                # Oscillate between 100-105
                price = 100 + (i % 5)
            candles.append(
                {
                    "timestamp": i * 1000,
                    "high": price + 2,
                    "low": price - 2,
                    "close": price,
                }
            )

        result = analyzer.find_support_resistance(candles)

        assert result is not None
        assert result.current_price == candles[-1]["close"]

    def test_psychological_levels(self):
        """Should find psychological levels."""
        analyzer = TechnicalAnalyzer()

        result = analyzer.find_psychological_levels(95000)

        assert "resistance" in result
        assert "support" in result
        assert len(result["resistance"]) > 0
        assert len(result["support"]) > 0


class TestFullAnalysis:
    """Tests for full technical analysis."""

    @pytest.fixture
    def sample_candles(self):
        """Generate sample candle data."""
        candles = []
        base_price = 50000
        for i in range(250):
            change = (i % 7 - 3) * 100
            price = base_price + change + i * 10
            candles.append(
                {
                    "timestamp": 1700000000000 + i * 86400000,
                    "open": price - 50,
                    "high": price + 100,
                    "low": price - 100,
                    "close": price,
                    "volume": 1000 + i * 10,
                }
            )
        return candles

    def test_analyze_returns_indicators(self, sample_candles):
        """analyze() should return TechnicalIndicators."""
        analyzer = TechnicalAnalyzer()
        result = analyzer.analyze("BTC", "1d", sample_candles)

        assert result is not None
        assert isinstance(result, TechnicalIndicators)
        assert result.symbol == "BTC"
        assert result.timeframe == "1d"

    def test_analyze_calculates_all_indicators(self, sample_candles):
        """analyze() should calculate all available indicators."""
        analyzer = TechnicalAnalyzer()
        result = analyzer.analyze("BTC", "1d", sample_candles)

        assert result.sma_20 is not None
        assert result.sma_50 is not None
        assert result.sma_200 is not None
        assert result.ema_12 is not None
        assert result.ema_26 is not None
        assert result.rsi is not None
        assert result.macd_line is not None
        assert result.bb_upper is not None
        assert result.atr is not None

    def test_analyze_insufficient_data(self):
        """analyze() should return None with insufficient data."""
        analyzer = TechnicalAnalyzer()
        candles = [{"timestamp": 1, "close": 100, "high": 101, "low": 99, "volume": 100}]
        result = analyzer.analyze("BTC", "1d", candles)

        assert result is None

    def test_get_signal_summary(self, sample_candles):
        """get_signal_summary() should return interpretation."""
        analyzer = TechnicalAnalyzer()
        indicators = analyzer.analyze("BTC", "1d", sample_candles)

        signals = analyzer.get_signal_summary(indicators)

        assert "overall" in signals
        assert "score" in signals
        assert "details" in signals
        assert signals["overall"] in ["bullish", "slightly_bullish", "neutral", "slightly_bearish", "bearish"]
        assert 0 <= signals["score"] <= 100

    def test_analyze_full(self, sample_candles):
        """analyze_full() should return complete analysis."""
        analyzer = TechnicalAnalyzer()
        result = analyzer.analyze_full("BTC", "1d", sample_candles)

        assert "symbol" in result
        assert "indicators" in result
        assert "signals" in result
        assert "support_resistance" in result

    def test_to_dict(self, sample_candles):
        """TechnicalIndicators.to_dict() should serialize correctly."""
        analyzer = TechnicalAnalyzer()
        indicators = analyzer.analyze("BTC", "1d", sample_candles)

        result = indicators.to_dict()

        assert isinstance(result, dict)
        assert "symbol" in result
        assert "rsi" in result
        assert "sma_20" in result


class TestEdgeCases:
    """Tests for edge cases."""

    def test_zero_prices(self):
        """Should handle zero prices gracefully."""
        analyzer = TechnicalAnalyzer()
        prices = [0, 0, 0, 0, 0]
        result = analyzer.calc_sma(prices, 5)
        assert result == 0

    def test_negative_prices(self):
        """Should handle negative prices (shouldn't happen but be safe)."""
        analyzer = TechnicalAnalyzer()
        prices = [-10, -5, 0, 5, 10]
        result = analyzer.calc_sma(prices, 5)
        assert result == 0

    def test_very_large_prices(self):
        """Should handle very large prices."""
        analyzer = TechnicalAnalyzer()
        prices = [1e10, 1.1e10, 1.2e10, 1.3e10, 1.4e10]
        result = analyzer.calc_sma(prices, 5)
        assert result == 1.2e10

    def test_constant_prices(self):
        """RSI should handle constant prices."""
        analyzer = TechnicalAnalyzer()
        prices = [100] * 20
        result = analyzer.calc_rsi(prices, 14)
        # When all changes are 0, RSI is undefined, implementation may return 100 or 50
        assert result is not None
