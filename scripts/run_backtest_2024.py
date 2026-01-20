#!/usr/bin/env python3
"""
Backtest ML Models on 2024 Historical Data

This script runs comprehensive backtesting of all ML forecasting models
on real historical cryptocurrency data from 2024 to compare performance.
"""

import asyncio
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.constants import MLDefaults
from service.candlestick import CandleInterval, fetch_candlesticks
from service.ml.backtester import ForecastBacktester

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("backtest_2024.log"),
    ],
)

logger = logging.getLogger(__name__)


async def fetch_historical_data(symbol: str, interval: str, days: int = 365) -> list[float]:
    """Fetch historical candlestick data."""
    logger.info(f"Fetching {days} days of {interval} data for {symbol}")

    try:
        # Calculate start time
        end_time = int(datetime.now().timestamp() * 1000)
        start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)

        # Fetch candles
        candles = await fetch_candlesticks(
            symbol=symbol,
            interval=CandleInterval(interval),
            start_time=start_time,
            end_time=end_time,
        )

        if not candles:
            raise ValueError("No candle data received")

        # Extract closing prices
        prices = [float(candle.close_price) for candle in candles]
        logger.info(f"Fetched {len(prices)} candles")

        return prices

    except Exception as e:
        logger.error(f"Failed to fetch data: {e}")
        raise


async def run_comprehensive_backtest():
    """Run backtest comparing all models on 2024 data."""
    logger.info("=" * 80)
    logger.info("STARTING COMPREHENSIVE 2024 BACKTEST")
    logger.info("=" * 80)

    # Test configuration
    test_symbols = ["BTC/USDT", "ETH/USDT"]
    test_intervals = ["1h", "4h", "1d"]
    test_periods = [365]  # Days of historical data

    results = {}

    # Initialize backtester
    backtester = ForecastBacktester()

    for symbol in test_symbols:
        results[symbol] = {}

        for interval in test_intervals:
            results[symbol][interval] = {}

            for period in test_periods:
                logger.info(f"\n--- Testing {symbol} {interval} ({period} days) ---")

                try:
                    # Fetch data
                    prices = await fetch_historical_data(symbol, interval, period)

                    if len(prices) < MLDefaults.MIN_TRAINING_POINTS:
                        logger.warning(f"Insufficient data for {symbol} {interval}")
                        continue

                    # Compare all models
                    comparison = await backtester.compare_models(
                        symbol=symbol,
                        interval=interval,
                        prices=prices,
                        train_ratio=0.7,
                        test_ratio=0.3,
                    )

                    # Store results
                    results[symbol][interval][period] = comparison.to_dict()

                    # Print summary
                    logger.info(f"Results for {symbol} {interval}:")
                    for metric in comparison.metrics:
                        logger.info(
                            f"  {metric.model:20} MAE: {metric.mae:.4f} " f"Direction: {metric.direction_accuracy:.1f}%"
                        )

                    if comparison.best_model:
                        logger.info(f"  🏆 BEST MODEL: {comparison.best_model}")

                except Exception as e:
                    logger.error(f"Backtest failed for {symbol} {interval}: {e}")
                    results[symbol][interval][period] = {"error": str(e)}

    # Save results
    output_file = Path("backtest_results_2024.json")
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, default=str)

    logger.info(f"\nResults saved to: {output_file}")

    # Print final summary
    print_final_summary(results)

    return results


def print_final_summary(results: dict):
    """Print comprehensive summary of backtest results."""
    logger.info("\n" + "=" * 80)
    logger.info("FINAL BACKTEST SUMMARY")
    logger.info("=" * 80)

    for symbol, symbol_data in results.items():
        logger.info(f"\n{symbol}:")
        logger.info("-" * 40)

        for interval, interval_data in symbol_data.items():
            logger.info(f"  {interval}:")

            for period, period_data in interval_data.items():
                if "error" in period_data:
                    logger.info(f"    {period} days: ERROR - {period_data['error']}")
                    continue

                if "models" in period_data:
                    # Sort models by MAE
                    sorted_models = sorted(period_data["models"], key=lambda x: x["mae"])

                    for i, model in enumerate(sorted_models):
                        marker = "🏆" if i == 0 else "  "
                        logger.info(
                            f"    {marker} {model['model']:20} "
                            f"MAE: {model['mae']:.4f}  "
                            f"DirAcc: {model['direction_accuracy']:.1f}%"
                        )


async def run_walk_forward_test():
    """Run walk-forward validation for more robust testing."""
    logger.info("\n" + "=" * 80)
    logger.info("RUNNING WALK-FORWARD VALIDATION")
    logger.info("=" * 80)

    backtester = ForecastBacktester()

    # Test BTC 1d data with walk-forward
    symbol = "BTC/USDT"
    interval = "1d"

    try:
        prices = await fetch_historical_data(symbol, interval, 365)

        logger.info(f"Running walk-forward validation on {symbol} {interval}")
        logger.info(f"Data points: {len(prices)}")

        # Test each model
        models = ["chronos-bolt", "statsforecast", "neuralprophet"]

        wf_results = {}

        for model in models:
            try:
                logger.info(f"Testing {model}...")
                metrics = await backtester.walk_forward_validation(
                    symbol=symbol,
                    interval=interval,
                    prices=prices,
                    model=model,
                    window_size=180,  # 6 months rolling window
                    horizon=6,  # 6 day forecast
                )

                wf_results[model] = metrics.to_dict()
                logger.info(f"  MAE: {metrics.mae:.4f}")
                logger.info(f"  RMSE: {metrics.rmse:.4f}")
                logger.info(f"  Direction Accuracy: {metrics.direction_accuracy:.1f}%")

            except Exception as e:
                logger.error(f"Walk-forward test failed for {model}: {e}")
                wf_results[model] = {"error": str(e)}

        # Save walk-forward results
        with open("walk_forward_results.json", "w") as f:
            json.dump(wf_results, f, indent=2, default=str)

        logger.info("Walk-forward results saved to: walk_forward_results.json")

        return wf_results

    except Exception as e:
        logger.error(f"Walk-forward validation failed: {e}")
        return {}


async def main():
    """Main execution function."""
    try:
        # Run comprehensive backtest
        comprehensive_results = await run_comprehensive_backtest()

        # Run walk-forward validation
        wf_results = await run_walk_forward_test()

        logger.info("\n" + "=" * 80)
        logger.info("BACKTESTING COMPLETE!")
        logger.info("=" * 80)
        logger.info("Files generated:")
        logger.info("  - backtest_results_2024.json")
        logger.info("  - walk_forward_results.json")
        logger.info("  - backtest_2024.log")

        return {
            "comprehensive": comprehensive_results,
            "walk_forward": wf_results,
        }

    except Exception as e:
        logger.error(f"Backtesting failed: {e}")
        raise


if __name__ == "__main__":
    # Run the backtest
    results = asyncio.run(main())
