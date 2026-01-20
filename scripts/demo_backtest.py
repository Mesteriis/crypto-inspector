#!/usr/bin/env python3
"""
Simple ML Backtest Demo

This demonstrates the backtesting framework with mock models
to show the architecture working before fixing dependency issues.
"""

import asyncio
import json
import logging
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.constants import MLDefaults
from service.candlestick import CandleInterval, fetch_candlesticks
from service.ml.models import BacktestMetrics, ForecastResult, ModelComparison

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockForecaster:
    """Mock forecaster for demonstration purposes."""

    def __init__(self, model_name: str):
        self.model_name = model_name

    async def predict(self, prices: list[float], horizon: int = 6) -> ForecastResult:
        """Generate mock predictions."""
        if not prices:
            raise ValueError("Prices list cannot be empty")

        last_price = prices[-1]

        # Generate realistic-looking predictions
        predictions = []
        confidence_low = []
        confidence_high = []

        # Add some randomness but keep it reasonable
        trend = random.choice([-0.01, -0.005, 0, 0.005, 0.01])  # -1% to +1% trend

        for i in range(horizon):
            # Add trend + noise
            noise = random.uniform(-0.02, 0.02)  # ±2% noise
            pred_price = last_price * (1 + trend * (i + 1) + noise)
            predictions.append(pred_price)

            # Confidence intervals (±3%)
            confidence_range = pred_price * 0.03
            confidence_low.append(pred_price - confidence_range)
            confidence_high.append(pred_price + confidence_range)

        # Determine direction
        final_pred = predictions[-1]
        if final_pred > last_price * 1.01:
            direction = "up"
        elif final_pred < last_price * 0.99:
            direction = "down"
        else:
            direction = "neutral"

        # Random confidence between 60-90%
        confidence = random.uniform(60, 90)

        return ForecastResult(
            symbol="",  # Will be filled by caller
            interval="",  # Will be filled by caller
            model=self.model_name,
            predictions=predictions,
            confidence_low=confidence_low,
            confidence_high=confidence_high,
            direction=direction,
            confidence_pct=confidence,
            timestamp=datetime.now(),
            horizon=horizon,
        )

    def get_model_name(self) -> str:
        return self.model_name


class SimpleBacktester:
    """Simple backtester for demonstration."""

    def __init__(self):
        self.models = {
            "trend-following": MockForecaster("trend-following"),
            "mean-reversion": MockForecaster("mean-reversion"),
            "momentum": MockForecaster("momentum"),
        }

    async def run_backtest(
        self,
        symbol: str,
        interval: str,
        prices: list[float],
        model: str,
        train_ratio: float = 0.7,
    ) -> BacktestMetrics:
        """Run simple backtest."""
        # Split data
        n_train = int(len(prices) * train_ratio)
        train_data = prices[:n_train]
        test_data = prices[n_train:]

        if len(test_data) < MLDefaults.PREDICTION_HORIZON:
            raise ValueError("Insufficient test data")

        # Generate predictions and calculate errors
        predictions = []
        actuals = []

        # Walk-forward testing
        for i in range(0, len(test_data) - MLDefaults.PREDICTION_HORIZON, MLDefaults.PREDICTION_HORIZON):
            context = train_data + test_data[:i]
            context = context[-min(len(context), 100) :]  # Limit context

            future_prices = test_data[i : i + MLDefaults.PREDICTION_HORIZON]
            actual_final = future_prices[-1]
            actuals.append(actual_final)

            try:
                forecast = await self.models[model].predict(context, MLDefaults.PREDICTION_HORIZON)
                predicted_final = forecast.predictions[-1]
                predictions.append(predicted_final)
            except Exception:
                predictions.append(context[-1])  # Fallback

        # Calculate metrics
        if not predictions:
            raise RuntimeError("No predictions generated")

        # MAE
        mae = sum(abs(p - a) for p, a in zip(predictions, actuals)) / len(predictions)

        # RMSE
        rmse = (sum((p - a) ** 2 for p, a in zip(predictions, actuals)) / len(predictions)) ** 0.5

        # MAPE
        mape_values = []
        for p, a in zip(predictions, actuals):
            if a != 0:
                mape_values.append(abs((p - a) / a) * 100)
        mape = sum(mape_values) / len(mape_values) if mape_values else float("inf")

        # Direction accuracy
        pred_directions = [1 if predictions[i] > predictions[i - 1] else -1 for i in range(1, len(predictions))]
        actual_directions = [1 if actuals[i] > actuals[i - 1] else -1 for i in range(1, len(actuals))]

        if pred_directions and actual_directions:
            direction_acc = (
                sum(1 for p, a in zip(pred_directions, actual_directions) if p == a) / len(pred_directions) * 100
            )
        else:
            direction_acc = 0.0

        return BacktestMetrics(
            model=model,
            symbol=symbol,
            interval=interval,
            mae=mae,
            rmse=rmse,
            mape=mape,
            direction_accuracy=direction_acc,
            sample_size=len(predictions),
        )

    async def compare_models(self, symbol: str, interval: str, prices: list[float]) -> ModelComparison:
        """Compare all models."""
        comparison = ModelComparison(symbol=symbol, interval=interval)

        for model_name in self.models:
            try:
                metrics = await self.run_backtest(symbol, interval, prices, model_name)
                comparison.add_metrics(metrics)
                logger.info(f"{model_name}: MAE={metrics.mae:.2f}, DirAcc={metrics.direction_accuracy:.1f}%")
            except Exception as e:
                logger.error(f"Failed to test {model_name}: {e}")

        if comparison.metrics:
            best = min(comparison.metrics, key=lambda m: m.mae)
            comparison.best_model = best.model

        return comparison


async def fetch_sample_data(symbol: str, interval: str, days: int = 90) -> list[float]:
    """Fetch sample historical data."""
    logger.info(f"Fetching {days} days of {interval} data for {symbol}")

    try:
        end_time = int(datetime.now().timestamp() * 1000)
        start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)

        candles = await fetch_candlesticks(
            symbol=symbol,
            interval=CandleInterval(interval),
            start_time=start_time,
            end_time=end_time,
        )

        if not candles:
            raise ValueError("No data received")

        prices = [float(candle.close_price) for candle in candles]
        logger.info(f"Fetched {len(prices)} candles")
        return prices

    except Exception as e:
        logger.error(f"Failed to fetch data: {e}")
        raise


async def main():
    """Run demonstration backtest."""
    logger.info("=" * 60)
    logger.info("ML BACKTESTING DEMO")
    logger.info("=" * 60)

    # Test configuration
    test_pairs = [("BTC/USDT", "1d"), ("ETH/USDT", "1d")]

    backtester = SimpleBacktester()
    results = {}

    for symbol, interval in test_pairs:
        logger.info(f"\n--- Testing {symbol} {interval} ---")

        try:
            # Fetch data
            prices = await fetch_sample_data(symbol, interval, days=180)

            if len(prices) < 50:
                logger.warning(f"Insufficient data for {symbol}")
                continue

            # Run comparison
            comparison = await backtester.compare_models(symbol, interval, prices)
            results[f"{symbol}_{interval}"] = comparison.to_dict()

            # Print results
            logger.info(f"\nResults for {symbol} {interval}:")
            for metric in comparison.metrics:
                logger.info(
                    f"  {metric.model:15} MAE: {metric.mae:>8.2f} " f"DirAcc: {metric.direction_accuracy:>6.1f}%"
                )

            if comparison.best_model:
                logger.info(f"  🏆 BEST: {comparison.best_model}")

        except Exception as e:
            logger.error(f"Failed to test {symbol} {interval}: {e}")
            results[f"{symbol}_{interval}"] = {"error": str(e)}

    # Save results
    output_file = Path("demo_backtest_results.json")
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, default=str)

    logger.info(f"\nDemo results saved to: {output_file}")
    logger.info("This demonstrates the backtesting framework architecture.")
    logger.info("Actual ML models will be integrated once dependency issues are resolved.")


if __name__ == "__main__":
    asyncio.run(main())
