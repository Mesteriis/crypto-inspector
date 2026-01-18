#!/usr/bin/env python3
"""
Comprehensive ML Analysis Across All Default Cryptocurrencies

This script performs extended backtesting analysis across all default cryptocurrencies
in the system and stores prediction results and actual outcomes in the database
for later comparison and visualization.
"""

import asyncio
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import text

from core.constants import DEFAULT_SYMBOLS, MLDefaults
from db.models.ml_predictions import MLPredictionRecord
from db.repositories.ml_predictions import MLPredictionRepository
from db.session import async_session_maker
from services.candlestick import CandleInterval, fetch_candlesticks
from services.ml.backtester import ForecastBacktester
from services.ml.forecaster import PriceForecaster

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("comprehensive_ml_analysis.log"),
    ],
)

logger = logging.getLogger(__name__)


class ComprehensiveMLAnalyzer:
    """Analyzer for comprehensive ML testing across all cryptocurrencies."""

    def __init__(self):
        self.forecaster = PriceForecaster()
        self.backtester = ForecastBacktester()
        self.available_models = self.forecaster.get_available_models()
        logger.info(f"Available models: {self.available_models}")

    async def get_all_symbols(self) -> list[str]:
        """Get all cryptocurrency symbols to analyze."""
        # Start with default symbols
        symbols = DEFAULT_SYMBOLS.copy()

        # Add more popular cryptocurrencies
        additional_symbols = [
            "SOL/USDT",  # Solana
            "ADA/USDT",  # Cardano
            "DOT/USDT",  # Polkadot
            "AVAX/USDT",  # Avalanche
            "LINK/USDT",  # Chainlink
            "MATIC/USDT",  # Polygon
            "UNI/USDT",  # Uniswap
            "LTC/USDT",  # Litecoin
            "XRP/USDT",  # Ripple
            "DOGE/USDT",  # Dogecoin
        ]

        symbols.extend(additional_symbols)
        return symbols

    async def fetch_historical_data(self, symbol: str, interval: str, days: int = 730) -> list[float]:
        """Fetch historical price data for analysis."""
        logger.info(f"Fetching {days} days of {interval} data for {symbol}")

        try:
            end_time = int(datetime.now().timestamp() * 1000)
            start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)

            candles = await fetch_candlesticks(
                symbol=symbol,
                interval=CandleInterval(interval),
                start_time=start_time,
                end_time=end_time,
                limit=days + 100,  # Extra for safety
            )

            if not candles:
                logger.warning(f"No data available for {symbol} {interval}")
                return []

            prices = [float(candle.close_price) for candle in candles]
            logger.info(f"Fetched {len(prices)} candles for {symbol}")
            return prices

        except Exception as e:
            logger.error(f"Failed to fetch data for {symbol}: {e}")
            return []

    async def run_model_predictions(
        self,
        symbol: str,
        interval: str,
        prices: list[float],
        prediction_timestamp: int,
    ) -> dict[str, MLPredictionRecord]:
        """
        Run predictions for all available models and save to database.

        Returns:
            Dictionary mapping model names to saved prediction records
        """
        predictions = {}

        # Use last N points as context (where N = CONTEXT_LENGTH)
        context_length = min(len(prices), MLDefaults.CONTEXT_LENGTH)
        context_prices = prices[-context_length:]

        # Predict horizon (how many candles ahead)
        horizon = MLDefaults.PREDICTION_HORIZON

        async with async_session_maker() as session:
            repo = MLPredictionRepository(session)

            for model_name in self.available_models:
                try:
                    logger.info(f"Generating prediction for {symbol} using {model_name}")

                    # Generate forecast
                    forecast = await self.forecaster.predict(
                        symbol=symbol, interval=interval, prices=context_prices, model=model_name, horizon=horizon
                    )

                    # Save prediction to database
                    prediction_record = await repo.save_prediction(
                        symbol=symbol,
                        interval=interval,
                        model_name=model_name,
                        forecast=forecast,
                        context_prices=context_prices,
                        prediction_timestamp=prediction_timestamp,
                        prediction_horizon=horizon,
                    )

                    predictions[model_name] = prediction_record
                    logger.info(f"Saved prediction {prediction_record.id} for {model_name}")

                except Exception as e:
                    logger.error(f"Failed to generate/save prediction for {model_name}: {e}")
                    continue

        return predictions

    async def evaluate_predictions(
        self,
        symbol: str,
        interval: str,
        prediction_timestamp: int,
        actual_prices: list[float],
    ):
        """
        Evaluate predictions by comparing with actual realized prices.

        Args:
            symbol: Trading pair symbol
            interval: Time interval
            prediction_timestamp: When predictions were made
            actual_prices: Actual prices that occurred after prediction
        """
        if not actual_prices:
            logger.warning("No actual prices provided for evaluation")
            return

        # The actual price we want to compare against is the one that occurred
        # prediction_horizon candles after the prediction
        actual_price = actual_prices[-1] if len(actual_prices) >= 1 else actual_prices[0]
        actual_timestamp = int(datetime.now().timestamp() * 1000)  # Current time

        async with async_session_maker() as session:
            repo = MLPredictionRepository(session)

            # Get predictions made at the specified timestamp
            stmt = """
                SELECT id FROM ml_prediction_records
                WHERE symbol = :symbol
                AND interval = :interval
                AND prediction_timestamp = :prediction_timestamp
                AND actual_price IS NULL
            """

            result = await session.execute(
                text(stmt), {"symbol": symbol, "interval": interval, "prediction_timestamp": prediction_timestamp}
            )

            prediction_ids = [row[0] for row in result.fetchall()]

            if not prediction_ids:
                logger.warning(f"No unresolved predictions found for {symbol} at {prediction_timestamp}")
                return

            # Update each prediction with actual price
            for pred_id in prediction_ids:
                try:
                    await repo.update_actual_price(pred_id, actual_price, actual_timestamp)
                    logger.info(f"Updated prediction {pred_id} with actual price {actual_price}")
                except Exception as e:
                    logger.error(f"Failed to update prediction {pred_id}: {e}")

    async def calculate_performance_statistics(self, symbol: str, interval: str):
        """Calculate and update performance statistics for all models."""
        async with async_session_maker() as session:
            repo = MLPredictionRepository(session)

            for model_name in self.available_models:
                try:
                    logger.info(f"Calculating performance for {symbol} {interval} {model_name}")
                    await repo.calculate_model_performance(symbol, interval, model_name)
                except Exception as e:
                    logger.error(f"Failed to calculate performance for {model_name}: {e}")

    async def run_comprehensive_analysis(self):
        """Run complete analysis across all symbols and models."""
        logger.info("=" * 80)
        logger.info("ЗАПУСК КОМПЛЕКСНОГО ML АНАЛИЗА")
        logger.info("=" * 80)

        # Configuration
        symbols = await self.get_all_symbols()
        intervals = ["1d"]  # Start with daily for comprehensive analysis
        analysis_days = 730  # 2 years of historical data
        sliding_window_days = 180  # 6-month sliding window

        results_summary = {
            "analysis_started": datetime.now().isoformat(),
            "total_symbols": len(symbols),
            "symbols_processed": [],
            "total_predictions": 0,
            "models_analyzed": self.available_models,
        }

        for symbol in symbols:
            logger.info(f"\n🔮 АНАЛИЗИРУЕМ {symbol}")
            logger.info("-" * 50)

            symbol_results = {"symbol": symbol, "predictions_made": 0, "models_successful": [], "errors": []}

            for interval in intervals:
                try:
                    # Fetch historical data
                    prices = await self.fetch_historical_data(symbol, interval, analysis_days)

                    if len(prices) < sliding_window_days + MLDefaults.PREDICTION_HORIZON:
                        logger.warning(f"Insufficient data for {symbol} {interval}")
                        symbol_results["errors"].append(f"Insufficient data for {interval}")
                        continue

                    # Run sliding window analysis
                    window_size = sliding_window_days
                    step_size = 30  # Move 1 month each step
                    successful_predictions = 0

                    for i in range(0, len(prices) - window_size - MLDefaults.PREDICTION_HORIZON, step_size):
                        # Training data window
                        window_end = i + window_size
                        train_data = prices[i:window_end]

                        # Actual future prices for evaluation
                        future_prices = prices[window_end : window_end + MLDefaults.PREDICTION_HORIZON]

                        if len(future_prices) < MLDefaults.PREDICTION_HORIZON:
                            break

                        # Timestamp when prediction would have been made
                        prediction_timestamp = int(
                            (datetime.now() - timedelta(days=analysis_days - window_end)).timestamp() * 1000
                        )

                        # Generate and save predictions
                        predictions = await self.run_model_predictions(
                            symbol, interval, train_data, prediction_timestamp
                        )

                        if predictions:
                            successful_predictions += len(predictions)
                            symbol_results["models_successful"].extend(list(predictions.keys()))

                            # Evaluate predictions with actual prices
                            await self.evaluate_predictions(symbol, interval, prediction_timestamp, future_prices)

                    symbol_results["predictions_made"] += successful_predictions
                    logger.info(f"Completed {successful_predictions} predictions for {symbol} {interval}")

                    # Calculate performance statistics
                    await self.calculate_performance_statistics(symbol, interval)

                except Exception as e:
                    logger.error(f"Failed to analyze {symbol} {interval}: {e}")
                    symbol_results["errors"].append(str(e))

            # Record symbol results
            results_summary["symbols_processed"].append(symbol_results)
            results_summary["total_predictions"] += symbol_results["predictions_made"]

            if symbol_results["predictions_made"] > 0:
                logger.info(f"✅ {symbol}: {symbol_results['predictions_made']} predictions completed")
            else:
                logger.info(f"❌ {symbol}: No predictions completed")

        # Generate final summary
        await self.generate_analysis_summary(results_summary)

        return results_summary

    async def generate_analysis_summary(self, results_summary: dict):
        """Generate and save analysis summary with model rankings."""
        logger.info("\n" + "=" * 80)
        logger.info("ГЕНЕРАЦИЯ СВОДКИ АНАЛИЗА")
        logger.info("=" * 80)

        summary_data = {
            "analysis_completed": datetime.now().isoformat(),
            "total_symbols_analyzed": len(results_summary["symbols_processed"]),
            "total_predictions_generated": results_summary["total_predictions"],
            "models_analyzed": results_summary["models_analyzed"],
            "symbol_results": results_summary["symbols_processed"],
            "model_rankings": {},
        }

        # Get performance rankings for each symbol
        async with async_session_maker() as session:
            repo = MLPredictionRepository(session)

            for symbol_result in results_summary["symbols_processed"]:
                symbol = symbol_result["symbol"]
                if symbol_result["predictions_made"] > 0:
                    try:
                        rankings = await repo.get_model_rankings(symbol, "1d")
                        summary_data["model_rankings"][symbol] = rankings
                    except Exception as e:
                        logger.error(f"Failed to get rankings for {symbol}: {e}")

        # Save summary to file
        summary_file = Path("comprehensive_ml_analysis_summary.json")
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, indent=2, default=str, ensure_ascii=False)

        logger.info(f"💾 Сводка анализа сохранена в: {summary_file}")

        # Print key insights
        self.print_analysis_insights(summary_data)

    def print_analysis_insights(self, summary_data: dict):
        """Print key insights from the analysis."""
        logger.info("\n📊 КЛЮЧЕВЫЕ ВЫВОДЫ АНАЛИЗА:")
        logger.info(f"  Обработано символов: {summary_data['total_symbols_analyzed']}")
        logger.info(f"  Сгенерировано прогнозов: {summary_data['total_predictions_generated']}")
        logger.info(f"  Анализируемых моделей: {len(summary_data['models_analyzed'])}")

        # Model performance overview
        model_performance_count = {}
        for symbol, rankings in summary_data["model_rankings"].items():
            if rankings:
                best_model = rankings[0]["model_name"]
                model_performance_count[best_model] = model_performance_count.get(best_model, 0) + 1

        if model_performance_count:
            logger.info("\n🏆 РЕЙТИНГ МОДЕЛЕЙ ПО ЧИСЛУ ПОБЕД:")
            for model, wins in sorted(model_performance_count.items(), key=lambda x: x[1], reverse=True):
                logger.info(f"  {model:20} - {wins} побед")


async def main():
    """Main execution function."""
    try:
        analyzer = ComprehensiveMLAnalyzer()
        results = await analyzer.run_comprehensive_analysis()

        logger.info("\n" + "=" * 80)
        logger.info("✅ КОМПЛЕКСНЫЙ ML АНАЛИЗ ЗАВЕРШЕН!")
        logger.info("=" * 80)
        logger.info("Сгенерированные файлы:")
        logger.info("  - comprehensive_ml_analysis.log (полный лог)")
        logger.info("  - comprehensive_ml_analysis_summary.json (сводка результатов)")
        logger.info("\n📊 Данные сохранены в базу данных для последующей визуализации")

        return results

    except Exception as e:
        logger.error(f"Comprehensive analysis failed: {e}")
        raise


if __name__ == "__main__":
    results = asyncio.run(main())
