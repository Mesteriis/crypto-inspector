#!/usr/bin/env python3
"""
Extended 2-Year Backtest with Confidence Statistics

This script performs comprehensive backtesting on 2 years of historical data
to calculate model confidence coefficients and weighted confidence scores.
"""

import asyncio
import json
import logging
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from service.candlestick import CandleInterval, fetch_candlesticks
from service.ml.backtester import ForecastBacktester
from service.ml.forecaster import PriceForecaster

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("extended_backtest_2y.log"),
    ],
)

logger = logging.getLogger(__name__)


class ExtendedBacktestAnalyzer:
    """Analyzer for extended backtesting with confidence calculation."""

    def __init__(self):
        self.forecaster = PriceForecaster()
        self.backtester = ForecastBacktester()
        self.results = {}

    async def fetch_extended_data(self, symbol: str, interval: str, days: int = 730) -> list[float]:
        """Fetch extended historical data."""
        logger.info(f"Fetching {days} days of {interval} data for {symbol}")

        try:
            candles = await fetch_candlesticks(
                symbol=symbol,
                interval=CandleInterval(interval),
                limit=days + 100,  # Extra data for safety
            )

            if not candles:
                raise ValueError("No candle data received")

            prices = [float(candle.close_price) for candle in candles[-days:]]  # Take last N days
            logger.info(f"Fetched {len(prices)} candles from {candles[0].timestamp} to {candles[-1].timestamp}")

            return prices

        except Exception as e:
            logger.error(f"Failed to fetch extended data: {e}")
            raise

    async def run_sliding_window_backtests(self, symbol: str, interval: str, prices: list[float]) -> dict:
        """Run backtests on sliding windows to get comprehensive statistics."""
        logger.info(f"Running sliding window backtests for {symbol} {interval}")

        # Configuration
        window_size = 180  # 6 months sliding window
        step_size = 30  # Move 1 month each step
        horizon = 3  # Predict 3 candles ahead

        model_stats = defaultdict(list)
        total_windows = 0

        # Run sliding window tests
        for i in range(0, len(prices) - window_size - horizon, step_size):
            window_end = i + window_size
            train_data = prices[i:window_end]
            test_data = prices[window_end : window_end + horizon]

            if len(test_data) < horizon:
                break

            actual_price = test_data[-1]
            total_windows += 1

            # Test each model
            for model_name in ["statsforecast", "neuralprophet", "chronos-bolt"]:
                try:
                    forecast = await self.forecaster.predict(
                        symbol=symbol, interval=interval, prices=train_data, model=model_name, horizon=horizon
                    )

                    predicted_price = forecast.predictions[-1]
                    error = abs(predicted_price - actual_price)
                    direction_correct = (predicted_price > train_data[-1]) == (actual_price > train_data[-1])

                    model_stats[model_name].append(
                        {
                            "error": error,
                            "direction_correct": direction_correct,
                            "actual_price": actual_price,
                            "predicted_price": predicted_price,
                            "confidence": forecast.confidence_pct,
                            "window_start": i,
                            "window_end": window_end,
                        }
                    )

                except Exception as e:
                    logger.warning(f"Model {model_name} failed in window {i}: {e}")
                    continue

        logger.info(f"Completed {total_windows} sliding window tests")
        return dict(model_stats)

    def calculate_confidence_coefficients(self, model_stats: dict) -> dict:
        """Calculate confidence coefficients based on historical performance."""
        logger.info("Calculating confidence coefficients...")

        coefficients = {}

        for model_name, stats in model_stats.items():
            if not stats:
                coefficients[model_name] = {
                    "confidence_coefficient": 0.5,  # Default neutral
                    "accuracy": 0.0,
                    "mean_error": float("inf"),
                    "direction_accuracy": 0.0,
                    "sample_size": 0,
                }
                continue

            # Calculate metrics
            errors = [s["error"] for s in stats]
            directions_correct = [s["direction_correct"] for s in stats]
            confidences = [s["confidence"] for s in stats]

            mean_error = np.mean(errors)
            accuracy = np.mean([1 - (e / s["actual_price"]) for e, s in zip(errors, stats)])
            direction_accuracy = np.mean(directions_correct)
            mean_confidence = np.mean(confidences)

            # Calculate confidence coefficient (0-1 scale)
            # Higher accuracy and direction accuracy = higher coefficient
            # Lower error = higher coefficient
            error_score = 1 / (1 + mean_error / 1000)  # Normalize error
            accuracy_score = accuracy
            direction_score = direction_accuracy
            confidence_score = mean_confidence / 100  # Normalize to 0-1

            # Weighted combination
            confidence_coefficient = (
                0.3 * error_score + 0.3 * accuracy_score + 0.2 * direction_score + 0.2 * confidence_score
            )

            coefficients[model_name] = {
                "confidence_coefficient": float(confidence_coefficient),
                "accuracy": float(accuracy),
                "mean_error": float(mean_error),
                "direction_accuracy": float(direction_accuracy),
                "mean_confidence": float(mean_confidence),
                "sample_size": len(stats),
            }

            logger.info(
                f"{model_name:20} Coefficient: {confidence_coefficient:.3f} "
                f"(Accuracy: {accuracy:.3f}, Direction: {direction_accuracy:.3f})"
            )

        return coefficients

    def calculate_weighted_confidence(self, model_stats: dict, coefficients: dict) -> dict:
        """Calculate weighted confidence scores using confidence coefficients."""
        logger.info("Calculating weighted confidence scores...")

        weighted_results = {}

        for model_name, stats in model_stats.items():
            if not stats:
                continue

            coefficient = coefficients[model_name]["confidence_coefficient"]

            # Calculate weighted metrics
            weighted_errors = []
            weighted_directions = []
            weighted_confidences = []

            for stat in stats:
                weight = coefficient  # Could be adjusted based on recency, etc.
                weighted_errors.append(stat["error"] * weight)
                weighted_directions.append(stat["direction_correct"] * weight)
                weighted_confidences.append(stat["confidence"] * weight)

            weighted_results[model_name] = {
                "weighted_mean_error": float(np.mean(weighted_errors)),
                "weighted_accuracy": float(
                    np.mean([1 - (e / s["actual_price"]) for e, s in zip(weighted_errors, stats)])
                ),
                "weighted_direction_accuracy": float(np.mean(weighted_directions)),
                "weighted_mean_confidence": float(np.mean(weighted_confidences)),
                "effective_sample_size": len(stats) * coefficient,
            }

            logger.info(f"{model_name:20} Weighted Accuracy: {weighted_results[model_name]['weighted_accuracy']:.3f}")

        return weighted_results

    async def run_comprehensive_analysis(self):
        """Run complete 2-year analysis."""
        logger.info("=" * 80)
        logger.info("ЗАПУСК РАСШИРЕННОГО АНАЛИЗА НА 2 ГОДА")
        logger.info("=" * 80)

        symbols = ["BTC/USDT", "ETH/USDT"]
        interval = "1d"

        all_results = {}

        for symbol in symbols:
            logger.info(f"\n🔮 АНАЛИЗИРУЕМ {symbol}")
            logger.info("-" * 50)

            try:
                # Fetch 2 years of data
                prices = await self.fetch_extended_data(symbol, interval, days=730)
                logger.info(f"Получено {len(prices)} свечей за 2 года")

                # Run sliding window backtests
                model_stats = await self.run_sliding_window_backtests(symbol, interval, prices)

                # Calculate confidence coefficients
                coefficients = self.calculate_confidence_coefficients(model_stats)

                # Calculate weighted confidence
                weighted_confidence = self.calculate_weighted_confidence(model_stats, coefficients)

                # Store results
                all_results[symbol] = {
                    "symbol": symbol,
                    "interval": interval,
                    "total_data_points": len(prices),
                    "period_start": prices[0],
                    "period_end": prices[-1],
                    "model_statistics": model_stats,
                    "confidence_coefficients": coefficients,
                    "weighted_confidence": weighted_confidence,
                }

                # Print summary
                self.print_symbol_summary(symbol, coefficients, weighted_confidence)

            except Exception as e:
                logger.error(f"Analysis failed for {symbol}: {e}")
                all_results[symbol] = {"error": str(e)}

        # Save comprehensive results
        self.save_detailed_results(all_results)

        # Print final recommendations
        self.print_final_recommendations(all_results)

        return all_results

    def print_symbol_summary(self, symbol: str, coefficients: dict, weighted_confidence: dict):
        """Print detailed summary for a symbol."""
        logger.info(f"\n📊 РЕЗУЛЬТАТЫ ДЛЯ {symbol}:")

        for model_name in coefficients.keys():
            coeff = coefficients[model_name]
            weighted = weighted_confidence.get(model_name, {})

            logger.info(f"  {model_name:20}")
            logger.info(f"    Коэффициент доверия: {coeff['confidence_coefficient']:.3f}")
            logger.info(f"    Точность: {coeff['accuracy']:.3f}")
            logger.info(f"    Точность направления: {coeff['direction_accuracy']:.3f}")
            logger.info(f"    Средняя ошибка: ${coeff['mean_error']:.2f}")
            if weighted:
                logger.info(f"    Взвешенная точность: {weighted.get('weighted_accuracy', 0):.3f}")
                logger.info(f"    Взвешенная уверенность: {weighted.get('weighted_mean_confidence', 0):.1f}%")

    def print_final_recommendations(self, all_results: dict):
        """Print final recommendations based on analysis."""
        logger.info("\n" + "=" * 80)
        logger.info("ФИНАЛЬНЫЕ РЕКОМЕНДАЦИИ")
        logger.info("=" * 80)

        # Aggregate confidence coefficients across symbols
        model_scores = defaultdict(list)

        for symbol, data in all_results.items():
            if "confidence_coefficients" in data:
                for model, coeff in data["confidence_coefficients"].items():
                    model_scores[model].append(coeff["confidence_coefficient"])

        # Calculate average coefficients
        avg_coefficients = {}
        for model, scores in model_scores.items():
            avg_coefficients[model] = np.mean(scores)

        # Rank models
        ranked_models = sorted(avg_coefficients.items(), key=lambda x: x[1], reverse=True)

        logger.info("🏆 РЕЙТИНГ МОДЕЛЕЙ ПО ДОВЕРИЮ:")
        for i, (model, coeff) in enumerate(ranked_models, 1):
            emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
            logger.info(f"  {emoji} {model:20} {coeff:.3f}")

        # Recommendations
        best_model = ranked_models[0][0]
        logger.info(f"\n🎯 РЕКОМЕНДАЦИЯ: Использовать {best_model} как основную модель")
        logger.info(f"   Средний коэффициент доверия: {avg_coefficients[best_model]:.3f}")

        # Confidence bands
        logger.info("\n📊 ДИАПАЗОНЫ УВЕРЕННОСТИ:")
        for model, coeff in avg_coefficients.items():
            if coeff >= 0.8:
                level = "ОЧЕНЬ ВЫСОКАЯ"
            elif coeff >= 0.6:
                level = "ВЫСОКАЯ"
            elif coeff >= 0.4:
                level = "СРЕДНЯЯ"
            else:
                level = "НИЗКАЯ"
            logger.info(f"  {model:20} {level} ({coeff:.3f})")

    def save_detailed_results(self, results: dict):
        """Save detailed analysis results to JSON file."""
        output_file = Path("extended_backtest_2y_detailed.json")

        # Convert numpy arrays to lists for JSON serialization
        serializable_results = self.make_serializable(results)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(serializable_results, f, indent=2, default=str, ensure_ascii=False)

        logger.info(f"\n💾 Подробные результаты сохранены в: {output_file}")

        # Also save summary
        summary = self.create_summary_report(results)
        summary_file = Path("extended_backtest_2y_summary.json")
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, default=str, ensure_ascii=False)
        logger.info(f"💾 Резюме сохранено в: {summary_file}")

    def make_serializable(self, obj):
        """Convert numpy arrays and other non-serializable objects to serializable format."""
        if isinstance(obj, dict):
            return {k: self.make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.make_serializable(item) for item in obj]
        elif isinstance(obj, (np.integer, np.floating)):
            return obj.item()
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return obj

    def create_summary_report(self, results: dict) -> dict:
        """Create a summary report from detailed results."""
        summary = {
            "analysis_date": datetime.now().isoformat(),
            "period_days": 730,
            "symbols_analyzed": [],
            "model_rankings": {},
            "recommendations": {},
        }

        # Collect model rankings
        model_scores = defaultdict(list)

        for symbol, data in results.items():
            if "confidence_coefficients" in data:
                summary["symbols_analyzed"].append(symbol)
                for model, coeff in data["confidence_coefficients"].items():
                    model_scores[model].append(
                        {
                            "symbol": symbol,
                            "coefficient": coeff["confidence_coefficient"],
                            "accuracy": coeff["accuracy"],
                            "direction_accuracy": coeff["direction_accuracy"],
                        }
                    )

        # Calculate averages and rankings
        for model, scores in model_scores.items():
            avg_coeff = np.mean([s["coefficient"] for s in scores])
            avg_accuracy = np.mean([s["accuracy"] for s in scores])
            avg_direction = np.mean([s["direction_accuracy"] for s in scores])

            summary["model_rankings"][model] = {
                "average_confidence_coefficient": float(avg_coeff),
                "average_accuracy": float(avg_accuracy),
                "average_direction_accuracy": float(avg_direction),
                "tested_on_symbols": [s["symbol"] for s in scores],
            }

        # Sort by confidence coefficient
        ranked_models = sorted(
            summary["model_rankings"].items(), key=lambda x: x[1]["average_confidence_coefficient"], reverse=True
        )

        summary["recommendations"] = {
            "best_model": ranked_models[0][0] if ranked_models else None,
            "model_ranking": [model for model, _ in ranked_models],
            "confidence_thresholds": {"high": 0.7, "medium": 0.5, "low": 0.3},
        }

        return summary


async def main():
    """Main execution function."""
    try:
        analyzer = ExtendedBacktestAnalyzer()
        results = await analyzer.run_comprehensive_analysis()

        logger.info("\n" + "=" * 80)
        logger.info("✅ РАСШИРЕННЫЙ АНАЛИЗ 2 ГОДА ЗАВЕРШЕН!")
        logger.info("=" * 80)
        logger.info("Сгенерированные файлы:")
        logger.info("  - extended_backtest_2y_detailed.json (подробные данные)")
        logger.info("  - extended_backtest_2y_summary.json (резюме)")
        logger.info("  - extended_backtest_2y.log (полный лог)")

        return results

    except Exception as e:
        logger.error(f"Extended analysis failed: {e}")
        raise


if __name__ == "__main__":
    results = asyncio.run(main())
