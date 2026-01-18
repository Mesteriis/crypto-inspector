"""
Signal Accuracy Validation Tests.

Tests that validate technical indicator signals (RSI, MACD, BB) against
actual market outcomes across different market conditions.
"""

from tests.e2e.framework.data_loader import BacktestPeriod
from tests.e2e.framework.signal_validator import (
    SignalPrediction,
    SignalType,
)


class TestRSISignalAccuracy:
    """Tests for RSI signal accuracy."""

    def test_rsi_calculation_correct(self, sample_candles):
        """Test RSI calculation produces valid values."""
        from services.analysis.technical import TechnicalAnalyzer

        ta = TechnicalAnalyzer()
        closes = [c["close"] for c in sample_candles]

        rsi = ta.calc_rsi(closes)

        assert rsi is not None
        assert 0 <= rsi <= 100
        print(f"RSI value: {rsi:.2f}")

    def test_rsi_oversold_signals_accuracy(self, rsi_oversold_candles, data_loader, signal_validator):
        """Test accuracy of RSI oversold signals (< 30)."""
        candles = data_loader.load_from_list(rsi_oversold_candles)
        from services.analysis.technical import TechnicalAnalyzer

        ta = TechnicalAnalyzer()

        # Find points where RSI was oversold
        for idx in range(30, len(candles) - 7):
            closes = [c.close for c in candles[: idx + 1]]
            rsi = ta.calc_rsi(closes)

            if rsi and rsi < 30:
                signal_date = candles[idx].datetime

                period = BacktestPeriod(
                    name=f"RSI_Oversold_{idx}",
                    symbol="BTC/USDT",
                    signal_date=signal_date,
                    outcome_window_days=7,
                    candles=candles[: idx + 8],
                )

                prediction = SignalPrediction(
                    signal_type=SignalType.BUY,
                    confidence=100 - rsi,
                    timestamp=signal_date,
                    price_at_signal=period.signal_price or 0,
                    indicator_values={"rsi": rsi},
                )

                signal_validator.validate_prediction(period, prediction)

        report = signal_validator.generate_accuracy_report()

        print("\n=== RSI Oversold Signal Accuracy ===")
        print(f"Predictions: {report.total_predictions}")
        print(f"Correct: {report.correct_predictions}")
        print(f"Win rate: {report.win_rate * 100:.1f}%")
        print(f"Avg return on buy: {report.avg_return_on_buy:.2f}%")

    def test_rsi_overbought_signals_accuracy(self, bullish_candles, data_loader, signal_validator):
        """Test accuracy of RSI overbought signals (> 70)."""
        candles = data_loader.load_from_list(bullish_candles)
        from services.analysis.technical import TechnicalAnalyzer

        ta = TechnicalAnalyzer()

        overbought_count = 0

        for idx in range(50, len(candles) - 7):
            closes = [c.close for c in candles[: idx + 1]]
            rsi = ta.calc_rsi(closes)

            if rsi and rsi > 70 and overbought_count < 10:
                overbought_count += 1
                signal_date = candles[idx].datetime

                period = BacktestPeriod(
                    name=f"RSI_Overbought_{idx}",
                    symbol="BTC/USDT",
                    signal_date=signal_date,
                    outcome_window_days=7,
                    candles=candles[: idx + 8],
                )

                prediction = SignalPrediction(
                    signal_type=SignalType.SELL,
                    confidence=rsi,
                    timestamp=signal_date,
                    price_at_signal=period.signal_price or 0,
                    indicator_values={"rsi": rsi},
                )

                signal_validator.validate_prediction(period, prediction)

        report = signal_validator.generate_accuracy_report()

        print("\n=== RSI Overbought Signal Accuracy ===")
        print(f"Overbought signals found: {overbought_count}")
        print(f"Win rate: {report.win_rate * 100:.1f}%")


class TestMACDSignalAccuracy:
    """Tests for MACD signal accuracy."""

    def test_macd_calculation_correct(self, sample_candles):
        """Test MACD calculation produces valid values."""
        from services.analysis.technical import TechnicalAnalyzer

        ta = TechnicalAnalyzer()
        closes = [c["close"] for c in sample_candles]

        macd_line, signal_line, histogram = ta.calc_macd(closes)

        print(f"MACD Line: {macd_line}")
        print(f"Signal Line: {signal_line}")
        print(f"Histogram: {histogram}")

        assert macd_line is not None or len(closes) < 35

    def test_macd_bullish_crossover_accuracy(self, bullish_candles, data_loader, signal_validator):
        """Test accuracy of MACD bullish crossover signals."""
        candles = data_loader.load_from_list(bullish_candles)
        from services.analysis.technical import TechnicalAnalyzer

        ta = TechnicalAnalyzer()
        crossover_count = 0

        for idx in range(50, len(candles) - 7):
            closes = [c.close for c in candles[: idx + 1]]
            prev_closes = [c.close for c in candles[:idx]]

            _, _, curr_hist = ta.calc_macd(closes)
            _, _, prev_hist = ta.calc_macd(prev_closes)

            # Bullish crossover: histogram goes from negative to positive
            if (
                curr_hist is not None
                and prev_hist is not None
                and prev_hist < 0
                and curr_hist > 0
                and crossover_count < 10
            ):
                crossover_count += 1
                signal_date = candles[idx].datetime

                period = BacktestPeriod(
                    name=f"MACD_Bullish_{idx}",
                    symbol="BTC/USDT",
                    signal_date=signal_date,
                    outcome_window_days=7,
                    candles=candles[: idx + 8],
                )

                prediction = SignalPrediction(
                    signal_type=SignalType.BUY,
                    confidence=70,
                    timestamp=signal_date,
                    price_at_signal=period.signal_price or 0,
                    indicator_values={"macd_histogram": curr_hist},
                )

                signal_validator.validate_prediction(period, prediction)

        report = signal_validator.generate_accuracy_report()

        print("\n=== MACD Bullish Crossover Accuracy ===")
        print(f"Crossovers found: {crossover_count}")
        print(f"Win rate: {report.win_rate * 100:.1f}%")
        print(f"Avg return: {report.avg_return_on_buy:.2f}%")

    def test_macd_bearish_crossover_accuracy(self, bearish_candles, data_loader, signal_validator):
        """Test accuracy of MACD bearish crossover signals."""
        candles = data_loader.load_from_list(bearish_candles)
        from services.analysis.technical import TechnicalAnalyzer

        ta = TechnicalAnalyzer()
        crossover_count = 0

        for idx in range(50, len(candles) - 7):
            closes = [c.close for c in candles[: idx + 1]]
            prev_closes = [c.close for c in candles[:idx]]

            _, _, curr_hist = ta.calc_macd(closes)
            _, _, prev_hist = ta.calc_macd(prev_closes)

            # Bearish crossover: histogram goes from positive to negative
            if (
                curr_hist is not None
                and prev_hist is not None
                and prev_hist > 0
                and curr_hist < 0
                and crossover_count < 10
            ):
                crossover_count += 1
                signal_date = candles[idx].datetime

                period = BacktestPeriod(
                    name=f"MACD_Bearish_{idx}",
                    symbol="BTC/USDT",
                    signal_date=signal_date,
                    outcome_window_days=7,
                    candles=candles[: idx + 8],
                )

                prediction = SignalPrediction(
                    signal_type=SignalType.SELL,
                    confidence=70,
                    timestamp=signal_date,
                    price_at_signal=period.signal_price or 0,
                    indicator_values={"macd_histogram": curr_hist},
                )

                signal_validator.validate_prediction(period, prediction)

        report = signal_validator.generate_accuracy_report()

        print("\n=== MACD Bearish Crossover Accuracy ===")
        print(f"Crossovers found: {crossover_count}")
        print(f"Win rate: {report.win_rate * 100:.1f}%")


class TestBollingerBandSignalAccuracy:
    """Tests for Bollinger Band signal accuracy."""

    def test_bb_lower_band_touch_accuracy(self, bearish_candles, data_loader, signal_validator):
        """Test accuracy when price touches lower BB."""
        candles = data_loader.load_from_list(bearish_candles)
        from services.analysis.technical import TechnicalAnalyzer

        ta = TechnicalAnalyzer()
        touch_count = 0

        for idx in range(30, len(candles) - 7):
            closes = [c.close for c in candles[: idx + 1]]
            upper, middle, lower, position = ta.calc_bollinger_bands(closes)

            # Price near or below lower band (position < 10)
            if position is not None and position < 10 and touch_count < 10:
                touch_count += 1
                signal_date = candles[idx].datetime

                period = BacktestPeriod(
                    name=f"BB_Lower_{idx}",
                    symbol="BTC/USDT",
                    signal_date=signal_date,
                    outcome_window_days=7,
                    candles=candles[: idx + 8],
                )

                prediction = SignalPrediction(
                    signal_type=SignalType.BUY,  # Mean reversion play
                    confidence=100 - position,
                    timestamp=signal_date,
                    price_at_signal=period.signal_price or 0,
                    indicator_values={"bb_position": position},
                )

                signal_validator.validate_prediction(period, prediction)

        report = signal_validator.generate_accuracy_report()

        print("\n=== BB Lower Band Touch Accuracy ===")
        print(f"Lower band touches: {touch_count}")
        print(f"Win rate: {report.win_rate * 100:.1f}%")

    def test_bb_upper_band_touch_accuracy(self, bullish_candles, data_loader, signal_validator):
        """Test accuracy when price touches upper BB."""
        candles = data_loader.load_from_list(bullish_candles)
        from services.analysis.technical import TechnicalAnalyzer

        ta = TechnicalAnalyzer()
        touch_count = 0

        for idx in range(30, len(candles) - 7):
            closes = [c.close for c in candles[: idx + 1]]
            upper, middle, lower, position = ta.calc_bollinger_bands(closes)

            # Price near or above upper band (position > 90)
            if position is not None and position > 90 and touch_count < 10:
                touch_count += 1
                signal_date = candles[idx].datetime

                period = BacktestPeriod(
                    name=f"BB_Upper_{idx}",
                    symbol="BTC/USDT",
                    signal_date=signal_date,
                    outcome_window_days=7,
                    candles=candles[: idx + 8],
                )

                prediction = SignalPrediction(
                    signal_type=SignalType.SELL,  # Mean reversion
                    confidence=position,
                    timestamp=signal_date,
                    price_at_signal=period.signal_price or 0,
                    indicator_values={"bb_position": position},
                )

                signal_validator.validate_prediction(period, prediction)

        report = signal_validator.generate_accuracy_report()

        print("\n=== BB Upper Band Touch Accuracy ===")
        print(f"Upper band touches: {touch_count}")
        print(f"Win rate: {report.win_rate * 100:.1f}%")


class TestCombinedSignalAccuracy:
    """Tests for signals that combine multiple indicators."""

    def test_confluence_signal_accuracy(self, bullish_candles, data_loader, signal_validator):
        """Test accuracy when multiple indicators agree."""
        candles = data_loader.load_from_list(bullish_candles)
        from services.analysis.technical import TechnicalAnalyzer

        ta = TechnicalAnalyzer()
        confluence_count = 0

        for idx in range(50, len(candles) - 7):
            closes = [c.close for c in candles[: idx + 1]]

            rsi = ta.calc_rsi(closes)
            _, _, histogram = ta.calc_macd(closes)
            _, _, _, bb_pos = ta.calc_bollinger_bands(closes)

            # Check for bullish confluence
            bullish_signals = 0
            if rsi and rsi < 40:
                bullish_signals += 1
            if histogram and histogram > 0:
                bullish_signals += 1
            if bb_pos and bb_pos < 30:
                bullish_signals += 1

            if bullish_signals >= 2 and confluence_count < 10:
                confluence_count += 1
                signal_date = candles[idx].datetime

                period = BacktestPeriod(
                    name=f"Confluence_Bullish_{idx}",
                    symbol="BTC/USDT",
                    signal_date=signal_date,
                    outcome_window_days=7,
                    candles=candles[: idx + 8],
                )

                # Higher confidence with more signals agreeing
                confidence = 50 + (bullish_signals * 15)

                prediction = SignalPrediction(
                    signal_type=SignalType.BUY,
                    confidence=confidence,
                    timestamp=signal_date,
                    price_at_signal=period.signal_price or 0,
                    indicator_values={
                        "rsi": rsi,
                        "macd_histogram": histogram,
                        "bb_position": bb_pos,
                        "confluence_count": bullish_signals,
                    },
                )

                signal_validator.validate_prediction(period, prediction)

        report = signal_validator.generate_accuracy_report()

        print("\n=== Confluence Signal Accuracy ===")
        print(f"Confluence signals found: {confluence_count}")
        print(f"Accuracy: {report.overall_accuracy * 100:.1f}%")
        print(f"Win rate: {report.win_rate * 100:.1f}%")
        print(f"Avg return: {report.avg_return_on_buy:.2f}%")


class TestSignalAccuracyReport:
    """Generate comprehensive signal accuracy reports."""

    def test_generate_comprehensive_report(self, sample_candles, data_loader, signal_validator):
        """Generate a comprehensive report across all indicators."""
        candles = data_loader.load_from_list(sample_candles)
        from services.analysis.technical import TechnicalAnalyzer

        ta = TechnicalAnalyzer()

        # Test every 10 days
        for idx in range(50, min(len(candles) - 7, 250), 10):
            closes = [c.close for c in candles[: idx + 1]]

            rsi = ta.calc_rsi(closes)
            _, _, histogram = ta.calc_macd(closes)
            _, _, _, bb_pos = ta.calc_bollinger_bands(closes)

            signal_date = candles[idx].datetime

            period = BacktestPeriod(
                name=f"Comprehensive_{idx}",
                symbol="BTC/USDT",
                signal_date=signal_date,
                outcome_window_days=7,
                candles=candles[: idx + 8],
            )

            # Determine signal from indicators
            score = 50
            if rsi:
                if rsi < 30:
                    score += 15
                elif rsi > 70:
                    score -= 15
            if histogram:
                if histogram > 0:
                    score += 10
                else:
                    score -= 10
            if bb_pos:
                if bb_pos < 20:
                    score += 10
                elif bb_pos > 80:
                    score -= 10

            if score >= 65:
                signal_type = SignalType.BUY
            elif score <= 35:
                signal_type = SignalType.SELL
            else:
                signal_type = SignalType.NEUTRAL

            prediction = SignalPrediction(
                signal_type=signal_type,
                confidence=abs(score - 50) + 50,
                timestamp=signal_date,
                price_at_signal=period.signal_price or 0,
                indicator_values={
                    "rsi": rsi,
                    "macd_histogram": histogram,
                    "bb_position": bb_pos,
                },
                raw_score=score,
            )

            signal_validator.validate_prediction(period, prediction)

        report = signal_validator.generate_accuracy_report()

        print("\n" + "=" * 50)
        print("COMPREHENSIVE SIGNAL ACCURACY REPORT")
        print("=" * 50)
        print(f"\nTotal predictions: {report.total_predictions}")
        print(f"Correct predictions: {report.correct_predictions}")
        print(f"Profitable predictions: {report.profitable_predictions}")
        print(f"\nOverall accuracy: {report.overall_accuracy * 100:.1f}%")
        print(f"Overall profitability: {report.overall_profitability * 100:.1f}%")
        print(f"Win rate: {report.win_rate * 100:.1f}%")

        print("\nBy Signal Type:")
        for signal, count in report.signal_counts.items():
            accuracy = report.signal_accuracy.get(signal, 0)
            profit = report.signal_profitability.get(signal, 0)
            print(f"  {signal}: {count} signals, {accuracy * 100:.1f}% accurate, {profit * 100:.1f}% profitable")

        print(f"\nAvg return on BUY: {report.avg_return_on_buy:.2f}%")
        print(f"Avg return on SELL: {report.avg_return_on_sell:.2f}%")
        print("=" * 50)

        # Assert minimum standards
        assert report.total_predictions > 0
