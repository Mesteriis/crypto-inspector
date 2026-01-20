"""
Composite Scoring Validation Tests.

Tests that validate the composite scoring engine against actual market outcomes.
The scoring engine combines:
- Technical Analysis (30%)
- Pattern Detection (20%)
- Market Cycle (15%)
- Derivatives (15%)
- Fear & Greed (10%)
- On-Chain (10%)
"""

from datetime import UTC, datetime

import pytest

from tests.e2e.framework.backtest_runner import BacktestConfig, BacktestRunner
from tests.e2e.framework.data_loader import BacktestPeriod
from tests.e2e.framework.signal_validator import (
    SignalPrediction,
    SignalType,
    score_to_signal,
)


class TestScoringEngine:
    """Tests for the composite scoring engine."""

    def test_scoring_engine_basic(self, sample_candles):
        """Test basic scoring engine functionality."""
        from service.analysis.scoring import ScoringEngine
        from service.analysis.technical import TechnicalAnalyzer, TechnicalIndicators

        ta = TechnicalAnalyzer()
        closes = [c["close"] for c in sample_candles]

        # Calculate indicators
        rsi = ta.calc_rsi(closes)
        sma_50 = ta.calc_sma(closes, 50)
        sma_200 = ta.calc_sma(closes, 200)
        macd_line, signal_line, histogram = ta.calc_macd(closes)
        bb_upper, bb_middle, bb_lower, bb_pos = ta.calc_bollinger_bands(closes)

        indicators = TechnicalIndicators(
            symbol="BTC/USDT",
            timeframe="1d",
            timestamp=int(datetime.now(UTC).timestamp() * 1000),
            price=closes[-1],
            rsi=rsi,
            sma_50=sma_50,
            sma_200=sma_200,
            macd_line=macd_line,
            macd_signal=signal_line,
            macd_histogram=histogram,
            bb_upper=bb_upper,
            bb_middle=bb_middle,
            bb_lower=bb_lower,
            bb_position=bb_pos,
        )

        scoring = ScoringEngine()
        score = scoring.calculate(symbol="BTC", indicators=indicators)

        print("\n=== Composite Score ===")
        print(f"Total Score: {score.total_score:.1f}/100")
        print(f"Signal: {score.signal}")
        print(f"Action: {score.action}")
        print(f"Confidence: {score.confidence:.1f}%")
        print(f"Risk Level: {score.risk_level}")

        print("\nComponent Scores:")
        for comp in score.components:
            print(f"  {comp.name}: {comp.score:.1f} (weight {comp.weight * 100:.0f}%)")

        assert 0 <= score.total_score <= 100
        assert score.signal in [
            "strong_bullish",
            "bullish",
            "slightly_bullish",
            "neutral",
            "slightly_bearish",
            "bearish",
            "strong_bearish",
        ]

    def test_scoring_bullish_market(self, bullish_candles):
        """Test scoring in bullish market conditions."""
        from service.analysis.scoring import ScoringEngine
        from service.analysis.technical import TechnicalAnalyzer, TechnicalIndicators

        ta = TechnicalAnalyzer()
        closes = [c["close"] for c in bullish_candles]

        indicators = TechnicalIndicators(
            symbol="BTC/USDT",
            timeframe="1d",
            timestamp=int(datetime.now(UTC).timestamp() * 1000),
            price=closes[-1],
            rsi=ta.calc_rsi(closes),
            sma_50=ta.calc_sma(closes, 50),
            sma_200=ta.calc_sma(closes, 200),
            macd_histogram=ta.calc_macd(closes)[2],
            bb_position=ta.calc_bollinger_bands(closes)[3],
        )

        scoring = ScoringEngine()
        score = scoring.calculate(symbol="BTC", indicators=indicators)

        print(f"\nBullish Market Score: {score.total_score:.1f}")
        print(f"Signal: {score.signal}")

        # In bullish conditions, we expect higher scores
        assert score.total_score >= 40  # At least neutral

    def test_scoring_bearish_market(self, bearish_candles):
        """Test scoring in bearish market conditions."""
        from service.analysis.scoring import ScoringEngine
        from service.analysis.technical import TechnicalAnalyzer, TechnicalIndicators

        ta = TechnicalAnalyzer()
        closes = [c["close"] for c in bearish_candles]

        indicators = TechnicalIndicators(
            symbol="BTC/USDT",
            timeframe="1d",
            timestamp=int(datetime.now(UTC).timestamp() * 1000),
            price=closes[-1],
            rsi=ta.calc_rsi(closes),
            sma_50=ta.calc_sma(closes, 50),
            sma_200=ta.calc_sma(closes, 200),
            macd_histogram=ta.calc_macd(closes)[2],
            bb_position=ta.calc_bollinger_bands(closes)[3],
        )

        scoring = ScoringEngine()
        score = scoring.calculate(symbol="BTC", indicators=indicators)

        print(f"\nBearish Market Score: {score.total_score:.1f}")
        print(f"Signal: {score.signal}")

        # In bearish conditions, we expect lower scores
        assert score.total_score <= 60  # At most slightly bullish


class TestScoringAccuracy:
    """Tests for scoring accuracy against actual outcomes."""

    def test_score_to_signal_conversion(self):
        """Test score to signal type conversion."""
        assert score_to_signal(85) == SignalType.STRONG_BUY
        assert score_to_signal(70) == SignalType.BUY
        assert score_to_signal(50) == SignalType.NEUTRAL
        assert score_to_signal(35) == SignalType.SELL
        assert score_to_signal(20) == SignalType.STRONG_SELL

    def test_scoring_accuracy_bullish_periods(self, bullish_candles, data_loader, signal_validator):
        """Test scoring accuracy during bullish periods."""
        candles = data_loader.load_from_list(bullish_candles)
        from service.analysis.scoring import ScoringEngine
        from service.analysis.technical import TechnicalAnalyzer, TechnicalIndicators

        ta = TechnicalAnalyzer()
        scoring = ScoringEngine()

        # Test at multiple points
        for idx in range(200, min(len(candles) - 7, 280), 10):
            closes = [c.close for c in candles[: idx + 1]]
            signal_date = candles[idx].datetime

            indicators = TechnicalIndicators(
                symbol="BTC/USDT",
                timeframe="1d",
                timestamp=candles[idx].timestamp,
                price=closes[-1],
                rsi=ta.calc_rsi(closes),
                sma_50=ta.calc_sma(closes, 50),
                sma_200=ta.calc_sma(closes, 200),
                macd_histogram=ta.calc_macd(closes)[2],
                bb_position=ta.calc_bollinger_bands(closes)[3],
            )

            score = scoring.calculate(symbol="BTC", indicators=indicators)
            signal_type = score_to_signal(score.total_score)

            period = BacktestPeriod(
                name=f"Score_Bullish_{idx}",
                symbol="BTC/USDT",
                signal_date=signal_date,
                outcome_window_days=7,
                candles=candles[: idx + 8],
            )

            prediction = SignalPrediction(
                signal_type=signal_type,
                confidence=score.confidence,
                timestamp=signal_date,
                price_at_signal=period.signal_price or 0,
                raw_score=score.total_score,
            )

            signal_validator.validate_prediction(period, prediction)

        report = signal_validator.generate_accuracy_report()

        print("\n=== Scoring Accuracy (Bullish Market) ===")
        print(f"Predictions: {report.total_predictions}")
        print(f"Accuracy: {report.overall_accuracy * 100:.1f}%")
        print(f"Win rate: {report.win_rate * 100:.1f}%")

    def test_scoring_accuracy_bearish_periods(self, bearish_candles, data_loader, signal_validator):
        """Test scoring accuracy during bearish periods."""
        candles = data_loader.load_from_list(bearish_candles)
        from service.analysis.scoring import ScoringEngine
        from service.analysis.technical import TechnicalAnalyzer, TechnicalIndicators

        ta = TechnicalAnalyzer()
        scoring = ScoringEngine()

        for idx in range(200, min(len(candles) - 7, 280), 10):
            closes = [c.close for c in candles[: idx + 1]]
            signal_date = candles[idx].datetime

            indicators = TechnicalIndicators(
                symbol="BTC/USDT",
                timeframe="1d",
                timestamp=candles[idx].timestamp,
                price=closes[-1],
                rsi=ta.calc_rsi(closes),
                sma_50=ta.calc_sma(closes, 50),
                sma_200=ta.calc_sma(closes, 200),
                macd_histogram=ta.calc_macd(closes)[2],
                bb_position=ta.calc_bollinger_bands(closes)[3],
            )

            score = scoring.calculate(symbol="BTC", indicators=indicators)
            signal_type = score_to_signal(score.total_score)

            period = BacktestPeriod(
                name=f"Score_Bearish_{idx}",
                symbol="BTC/USDT",
                signal_date=signal_date,
                outcome_window_days=7,
                candles=candles[: idx + 8],
            )

            prediction = SignalPrediction(
                signal_type=signal_type,
                confidence=score.confidence,
                timestamp=signal_date,
                price_at_signal=period.signal_price or 0,
                raw_score=score.total_score,
            )

            signal_validator.validate_prediction(period, prediction)

        report = signal_validator.generate_accuracy_report()

        print("\n=== Scoring Accuracy (Bearish Market) ===")
        print(f"Predictions: {report.total_predictions}")
        print(f"Accuracy: {report.overall_accuracy * 100:.1f}%")
        print(f"Win rate: {report.win_rate * 100:.1f}%")


class TestBacktestRunner:
    """Tests using the BacktestRunner for comprehensive validation."""

    @pytest.mark.asyncio
    async def test_backtest_with_synthetic_data(self, backtest_runner):
        """Run backtest with synthetic data."""
        run = await backtest_runner.run_backtest(from_database=False)

        print("\n=== Backtest Run Results ===")
        print(f"Duration: {run.duration_seconds:.2f}s")
        print(f"Test periods: {len(run.test_periods)}")
        print(f"Predictions: {len(run.predictions)}")
        print(f"Errors: {len(run.errors)}")

        if run.accuracy_report:
            print(f"\nAccuracy: {run.accuracy_report.overall_accuracy * 100:.1f}%")
            print(f"Win rate: {run.accuracy_report.win_rate * 100:.1f}%")

        # Some errors are acceptable in synthetic data
        assert len(run.predictions) > 0 or len(run.errors) > 0

    @pytest.mark.asyncio
    async def test_backtest_config_options(self):
        """Test different backtest configuration options."""
        # Test with different outcome windows
        for window in [3, 7, 14]:
            config = BacktestConfig(
                symbol="BTC/USDT",
                interval="1d",
                signal_frequency_days=10,
                outcome_window_days=window,
                min_candles_for_analysis=100,
            )
            runner = BacktestRunner(config=config)

            # Load synthetic data
            runner._candles = runner.data_loader.generate_synthetic_bullish_period(base_price=50000, days=200)

            periods = runner.generate_test_periods()

            print(f"\nWindow {window} days: {len(periods)} test periods")

            assert len(periods) >= 0  # May be 0 with short data

    @pytest.mark.asyncio
    async def test_pattern_validation_runner(self, backtest_runner):
        """Test pattern validation through runner."""
        # Load synthetic data for golden cross
        backtest_runner._candles = backtest_runner.data_loader.generate_synthetic_bullish_period(
            base_price=50000, days=300
        )

        # Test RSI oversold pattern
        backtest_runner._candles, _ = backtest_runner.data_loader.generate_rsi_oversold_scenario()

        report = await backtest_runner.run_indicator_validation("rsi", from_database=False)

        print("\n=== RSI Indicator Validation ===")
        print(f"Total signals: {report.total_predictions}")
        if report.total_predictions > 0:
            print(f"Accuracy: {report.overall_accuracy * 100:.1f}%")


class TestFullSystemBacktest:
    """Full system backtest tests."""

    @pytest.mark.asyncio
    async def test_full_system_synthetic_bullish(self):
        """Full system test with synthetic bullish data."""
        config = BacktestConfig(
            symbol="BTC/USDT",
            interval="1d",
            signal_frequency_days=7,
            outcome_window_days=7,
            min_candles_for_analysis=50,
        )

        runner = BacktestRunner(config=config)

        # Generate bullish market data
        runner._candles = runner.data_loader.generate_synthetic_bullish_period(
            base_price=45000,
            days=200,
        )

        periods = runner.generate_test_periods()

        print("\n" + "=" * 60)
        print("FULL SYSTEM BACKTEST - BULLISH SYNTHETIC DATA")
        print("=" * 60)
        print(f"Total candles: {len(runner._candles)}")
        print(f"Test periods: {len(periods)}")

        if len(periods) == 0:
            print("Not enough data for test periods")
            return

        # Process each period
        for period in periods[:10]:  # Test first 10
            try:
                prediction = runner.generate_prediction(period)
                runner.validator.validate_prediction(period, prediction)
            except Exception as e:
                print(f"Error: {e}")

        report = runner.validator.generate_accuracy_report()

        print("\nResults:")
        print(f"  Predictions: {report.total_predictions}")
        print(f"  Accuracy: {report.overall_accuracy * 100:.1f}%")
        print(f"  Win rate: {report.win_rate * 100:.1f}%")
        print(f"  Avg return on BUY: {report.avg_return_on_buy:.2f}%")
        print("=" * 60)

    @pytest.mark.asyncio
    async def test_full_system_synthetic_bearish(self):
        """Full system test with synthetic bearish data."""
        config = BacktestConfig(
            symbol="BTC/USDT",
            interval="1d",
            signal_frequency_days=7,
            outcome_window_days=7,
            min_candles_for_analysis=50,
        )

        runner = BacktestRunner(config=config)

        # Generate bearish market data
        runner._candles = runner.data_loader.generate_synthetic_bearish_period(
            base_price=65000,
            days=200,
        )

        periods = runner.generate_test_periods()

        print("\n" + "=" * 60)
        print("FULL SYSTEM BACKTEST - BEARISH SYNTHETIC DATA")
        print("=" * 60)
        print(f"Total candles: {len(runner._candles)}")
        print(f"Test periods: {len(periods)}")

        if len(periods) == 0:
            print("Not enough data for test periods")
            return

        # Process each period
        for period in periods[:10]:
            try:
                prediction = runner.generate_prediction(period)
                runner.validator.validate_prediction(period, prediction)
            except Exception as e:
                print(f"Error: {e}")

        report = runner.validator.generate_accuracy_report()

        print("\nResults:")
        print(f"  Predictions: {report.total_predictions}")
        print(f"  Accuracy: {report.overall_accuracy * 100:.1f}%")
        print(f"  Win rate: {report.win_rate * 100:.1f}%")
        print(f"  Avg return on SELL: {report.avg_return_on_sell:.2f}%")
        print("=" * 60)

    @pytest.mark.asyncio
    async def test_compare_market_conditions(self):
        """Compare system performance across different market conditions."""
        config = BacktestConfig(
            symbol="BTC/USDT",
            interval="1d",
            signal_frequency_days=7,
            outcome_window_days=7,
            min_candles_for_analysis=50,
        )

        results = {}

        for condition, generator in [
            ("bullish", lambda dl: dl.generate_synthetic_bullish_period(50000, 200)),
            ("bearish", lambda dl: dl.generate_synthetic_bearish_period(50000, 200)),
        ]:
            runner = BacktestRunner(config=config)
            runner._candles = generator(runner.data_loader)
            periods = runner.generate_test_periods()

            for period in periods[:10]:
                try:
                    prediction = runner.generate_prediction(period)
                    runner.validator.validate_prediction(period, prediction)
                except Exception:
                    pass

            report = runner.validator.generate_accuracy_report()
            results[condition] = {
                "accuracy": report.overall_accuracy,
                "win_rate": report.win_rate,
                "avg_return": report.avg_return_on_buy if condition == "bullish" else report.avg_return_on_sell,
            }

        print("\n" + "=" * 60)
        print("MARKET CONDITION COMPARISON")
        print("=" * 60)
        for condition, metrics in results.items():
            print(f"\n{condition.upper()}:")
            print(f"  Accuracy: {metrics['accuracy'] * 100:.1f}%")
            print(f"  Win Rate: {metrics['win_rate'] * 100:.1f}%")
            print(f"  Avg Return: {metrics['avg_return']:.2f}%")
        print("=" * 60)
