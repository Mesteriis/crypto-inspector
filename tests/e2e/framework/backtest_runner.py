"""
Backtest Runner for E2E Testing.

Main orchestration class that runs analysis algorithms on historical data
and validates predictions against actual outcomes.
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from tests.e2e.framework.data_loader import BacktestPeriod, CandleData, HistoricalDataLoader
from tests.e2e.framework.signal_validator import (
    AccuracyReport,
    SignalPrediction,
    SignalType,
    SignalValidator,
    ValidationResult,
    pattern_to_signal_type,
    score_to_signal,
)

logger = logging.getLogger(__name__)


@dataclass
class BacktestConfig:
    """Configuration for backtest run."""

    symbol: str = "BTC/USDT"
    interval: str = "1d"
    start_date: datetime | None = None
    end_date: datetime | None = None
    signal_frequency_days: int = 7  # Generate signals every N days
    outcome_window_days: int = 7  # Days to measure outcome
    min_candles_for_analysis: int = 200  # Minimum candles needed for analysis


@dataclass
class BacktestRun:
    """Result of a complete backtest run."""

    config: BacktestConfig
    start_time: datetime
    end_time: datetime | None = None
    test_periods: list[BacktestPeriod] = field(default_factory=list)
    predictions: list[SignalPrediction] = field(default_factory=list)
    validations: list[ValidationResult] = field(default_factory=list)
    accuracy_report: AccuracyReport | None = None
    errors: list[str] = field(default_factory=list)

    @property
    def duration_seconds(self) -> float:
        """Duration of the backtest run."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0

    def to_dict(self) -> dict:
        """Convert to dictionary for reporting."""
        return {
            "config": {
                "symbol": self.config.symbol,
                "interval": self.config.interval,
                "signal_frequency_days": self.config.signal_frequency_days,
                "outcome_window_days": self.config.outcome_window_days,
            },
            "execution": {
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat() if self.end_time else None,
                "duration_seconds": self.duration_seconds,
                "test_periods_count": len(self.test_periods),
                "predictions_count": len(self.predictions),
            },
            "accuracy_report": self.accuracy_report.to_dict() if self.accuracy_report else None,
            "errors": self.errors,
        }


class BacktestRunner:
    """
    Main backtest orchestrator.

    Runs analysis algorithms on historical data and validates predictions.
    """

    def __init__(self, config: BacktestConfig | None = None):
        self.config = config or BacktestConfig()
        self.data_loader = HistoricalDataLoader()
        self.validator = SignalValidator()
        self._candles: list[CandleData] = []

    async def load_historical_data(
        self,
        from_database: bool = True,
    ) -> list[CandleData]:
        """
        Load historical data for backtesting.

        Args:
            from_database: If True, load from database; otherwise use synthetic

        Returns:
            List of CandleData
        """
        if from_database:
            self._candles = await self.data_loader.load_from_database(
                symbol=self.config.symbol,
                interval=self.config.interval,
                start_date=self.config.start_date,
                end_date=self.config.end_date,
                limit=5000,  # Load up to 5000 candles
            )
        else:
            # Use synthetic data for testing
            self._candles = self.data_loader.generate_synthetic_bullish_period(
                base_price=50000,
                days=365,
            )

        logger.info(f"Loaded {len(self._candles)} candles for backtesting")
        return self._candles

    def generate_test_periods(self) -> list[BacktestPeriod]:
        """
        Generate test periods from loaded candles.

        Creates test periods at regular intervals throughout the data.
        """
        if len(self._candles) < self.config.min_candles_for_analysis:
            logger.warning(f"Insufficient candles: {len(self._candles)}")
            return []

        test_periods = []
        freq = self.config.signal_frequency_days

        # Start after we have enough candles for analysis
        start_idx = self.config.min_candles_for_analysis

        # Need enough candles after signal for outcome measurement
        end_idx = len(self._candles) - self.config.outcome_window_days

        idx = start_idx
        period_num = 1

        while idx < end_idx:
            signal_candle = self._candles[idx]
            signal_date = signal_candle.datetime

            # Create test period with all candles up to and including outcome window
            outcome_idx = min(idx + self.config.outcome_window_days + 1, len(self._candles))

            period = BacktestPeriod(
                name=f"Period_{period_num}_{signal_date.strftime('%Y%m%d')}",
                symbol=self.config.symbol,
                signal_date=signal_date,
                outcome_window_days=self.config.outcome_window_days,
                candles=self._candles[:outcome_idx],
            )

            test_periods.append(period)
            idx += freq
            period_num += 1

        logger.info(f"Generated {len(test_periods)} test periods")
        return test_periods

    def analyze_technical(self, candles: list[dict]) -> dict[str, Any]:
        """
        Run technical analysis on candles.

        Args:
            candles: List of candle dicts

        Returns:
            Dictionary with RSI, MACD, BB, trend info
        """
        # Import analysis services
        from services.analysis.technical import TechnicalAnalyzer

        if len(candles) < 50:
            return {}

        ta = TechnicalAnalyzer()
        closes = [float(c["close"]) for c in candles]

        result = {
            "rsi": ta.calc_rsi(closes),
            "sma_50": ta.calc_sma(closes, 50),
            "sma_200": ta.calc_sma(closes, 200) if len(closes) >= 200 else None,
        }

        # MACD
        macd_line, signal_line, histogram = ta.calc_macd(closes)
        result["macd"] = {
            "line": macd_line,
            "signal": signal_line,
            "histogram": histogram,
        }

        # Bollinger Bands
        bb_upper, bb_middle, bb_lower, bb_pos = ta.calc_bollinger_bands(closes)
        result["bollinger"] = {
            "upper": bb_upper,
            "middle": bb_middle,
            "lower": bb_lower,
            "position": bb_pos,
        }

        return result

    def detect_patterns(self, symbol: str, candles: list[dict]) -> list[dict]:
        """
        Detect chart patterns in candles.

        Args:
            symbol: Trading symbol
            candles: List of candle dicts

        Returns:
            List of detected patterns
        """
        from services.analysis.patterns import PatternDetector

        if len(candles) < 50:
            return []

        detector = PatternDetector()
        patterns = detector.detect_all(symbol, candles)

        return [p.to_dict() for p in patterns]

    def calculate_score(
        self,
        symbol: str,
        indicators: dict | None = None,
        patterns: list[dict] | None = None,
    ) -> dict:
        """
        Calculate composite score.

        Args:
            symbol: Trading symbol
            indicators: Technical indicator values
            patterns: Detected patterns

        Returns:
            Composite score data
        """
        from services.analysis.scoring import ScoringEngine
        from services.analysis.technical import TechnicalIndicators

        scoring = ScoringEngine()

        # Build TechnicalIndicators if we have data
        tech_indicators = None
        if indicators:
            tech_indicators = TechnicalIndicators(
                symbol=symbol,
                timeframe="1d",
                timestamp=0,
                price=0,
                rsi=indicators.get("rsi"),
                sma_50=indicators.get("sma_50"),
                sma_200=indicators.get("sma_200"),
                macd_line=indicators.get("macd", {}).get("line"),
                macd_signal=indicators.get("macd", {}).get("signal"),
                macd_histogram=indicators.get("macd", {}).get("histogram"),
                bb_upper=indicators.get("bollinger", {}).get("upper"),
                bb_middle=indicators.get("bollinger", {}).get("middle"),
                bb_lower=indicators.get("bollinger", {}).get("lower"),
                bb_position=indicators.get("bollinger", {}).get("position"),
            )

        # Build pattern summary
        pattern_summary = None
        if patterns:
            bullish = [p for p in patterns if p.get("direction") == "bullish"]
            bearish = [p for p in patterns if p.get("direction") == "bearish"]
            pattern_summary = {
                "bullish_count": len(bullish),
                "bearish_count": len(bearish),
                "bullish_patterns": [p.get("name") for p in bullish],
                "bearish_patterns": [p.get("name") for p in bearish],
                "total_patterns": len(patterns),
                "score": 50 + (len(bullish) - len(bearish)) * 10,
            }

        score = scoring.calculate(
            symbol=symbol,
            indicators=tech_indicators,
            pattern_summary=pattern_summary,
        )

        return score.to_dict()

    def generate_prediction(
        self,
        test_period: BacktestPeriod,
    ) -> SignalPrediction:
        """
        Generate a prediction for a test period.

        Args:
            test_period: The test period to analyze

        Returns:
            SignalPrediction
        """
        candles = test_period.input_candles
        symbol = test_period.symbol

        # Run analysis
        indicators = self.analyze_technical(candles)
        patterns = self.detect_patterns(symbol, candles)
        score_data = self.calculate_score(symbol, indicators, patterns)

        # Extract values for prediction
        raw_score = score_data.get("score", {}).get("total", 50)
        signal_type = score_to_signal(raw_score)
        confidence = score_data.get("confidence", 50)

        # Get pattern info
        pattern_name = None
        if patterns:
            # Use strongest pattern
            strongest = max(patterns, key=lambda p: p.get("strength", 0))
            pattern_name = strongest.get("name")

        prediction = SignalPrediction(
            signal_type=signal_type,
            confidence=confidence,
            timestamp=test_period.signal_date,
            price_at_signal=test_period.signal_price or 0,
            indicator_values={
                "rsi": indicators.get("rsi"),
                "macd_histogram": indicators.get("macd", {}).get("histogram"),
                "bb_position": indicators.get("bollinger", {}).get("position"),
            },
            pattern_detected=pattern_name,
            raw_score=raw_score,
        )

        return prediction

    async def run_backtest(
        self,
        from_database: bool = True,
    ) -> BacktestRun:
        """
        Run complete backtest.

        Args:
            from_database: If True, load data from database

        Returns:
            BacktestRun with all results
        """
        run = BacktestRun(
            config=self.config,
            start_time=datetime.now(UTC),
        )

        try:
            # Load data
            await self.load_historical_data(from_database=from_database)

            if len(self._candles) < self.config.min_candles_for_analysis:
                run.errors.append(
                    f"Insufficient data: {len(self._candles)} candles, need {self.config.min_candles_for_analysis}"
                )
                run.end_time = datetime.now(UTC)
                return run

            # Generate test periods
            run.test_periods = self.generate_test_periods()

            if not run.test_periods:
                run.errors.append("No test periods generated")
                run.end_time = datetime.now(UTC)
                return run

            # Generate predictions and validate
            self.validator.clear_results()

            for period in run.test_periods:
                try:
                    prediction = self.generate_prediction(period)
                    run.predictions.append(prediction)

                    validation = self.validator.validate_prediction(period, prediction)
                    run.validations.append(validation)

                except Exception as e:
                    logger.error(f"Error processing period {period.name}: {e}")
                    run.errors.append(f"Period {period.name}: {str(e)}")

            # Generate accuracy report
            run.accuracy_report = self.validator.generate_accuracy_report()

        except Exception as e:
            logger.error(f"Backtest failed: {e}")
            run.errors.append(str(e))

        run.end_time = datetime.now(UTC)
        return run

    async def run_pattern_validation(
        self,
        pattern_type: str,
        from_database: bool = True,
    ) -> AccuracyReport:
        """
        Validate a specific pattern type.

        Args:
            pattern_type: Pattern type to validate (e.g., "golden_cross")
            from_database: Load data from database

        Returns:
            AccuracyReport for the pattern
        """
        await self.load_historical_data(from_database=from_database)

        self.validator.clear_results()
        test_periods = self.generate_test_periods()

        for period in test_periods:
            candles = period.input_candles
            patterns = self.detect_patterns(self.config.symbol, candles)

            # Find the specific pattern
            target_pattern = None
            for p in patterns:
                if p.get("type") == pattern_type:
                    target_pattern = p
                    break

            if target_pattern:
                signal_type = pattern_to_signal_type(target_pattern.get("direction", "neutral"))

                prediction = SignalPrediction(
                    signal_type=signal_type,
                    confidence=target_pattern.get("confidence", 50),
                    timestamp=period.signal_date,
                    price_at_signal=period.signal_price or 0,
                    pattern_detected=target_pattern.get("name"),
                )

                self.validator.validate_prediction(period, prediction)

        return self.validator.generate_accuracy_report()

    async def run_indicator_validation(
        self,
        indicator: str,
        from_database: bool = True,
    ) -> AccuracyReport:
        """
        Validate signals from a specific indicator.

        Args:
            indicator: Indicator to validate ("rsi", "macd", "bb")
            from_database: Load data from database

        Returns:
            AccuracyReport for the indicator
        """
        await self.load_historical_data(from_database=from_database)

        self.validator.clear_results()
        test_periods = self.generate_test_periods()

        for period in test_periods:
            candles = period.input_candles
            indicators = self.analyze_technical(candles)

            signal_type = SignalType.NEUTRAL
            confidence = 50

            if indicator == "rsi":
                rsi = indicators.get("rsi")
                if rsi is not None:
                    if rsi < 30:
                        signal_type = SignalType.BUY
                        confidence = 100 - rsi
                    elif rsi > 70:
                        signal_type = SignalType.SELL
                        confidence = rsi

            elif indicator == "macd":
                histogram = indicators.get("macd", {}).get("histogram")
                if histogram is not None:
                    if histogram > 0:
                        signal_type = SignalType.BUY
                        confidence = min(80, 50 + abs(histogram) * 100)
                    else:
                        signal_type = SignalType.SELL
                        confidence = min(80, 50 + abs(histogram) * 100)

            elif indicator == "bb":
                bb_pos = indicators.get("bollinger", {}).get("position")
                if bb_pos is not None:
                    if bb_pos < 20:
                        signal_type = SignalType.BUY
                        confidence = 100 - bb_pos
                    elif bb_pos > 80:
                        signal_type = SignalType.SELL
                        confidence = bb_pos

            prediction = SignalPrediction(
                signal_type=signal_type,
                confidence=confidence,
                timestamp=period.signal_date,
                price_at_signal=period.signal_price or 0,
                indicator_values={indicator: indicators.get(indicator)},
            )

            self.validator.validate_prediction(period, prediction)

        return self.validator.generate_accuracy_report()
