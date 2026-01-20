#!/usr/bin/env python3
"""
Final Working Backtest for 2024 Historical Data

This script runs a comprehensive backtest comparing all working ML models
on real historical cryptocurrency data to determine the best performing model.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from service.candlestick import CandleInterval, fetch_candlesticks
from service.ml.backtester import ForecastBacktester

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("final_backtest_2024.log"),
    ],
)

logger = logging.getLogger(__name__)


async def run_comprehensive_comparison():
    """Run comprehensive model comparison on historical data."""
    logger.info("=" * 80)
    logger.info("ЗАПУСК ФИНАЛЬНОГО БЭКТЕСТА 2024")
    logger.info("=" * 80)

    # Test configuration
    test_symbols = ["BTC/USDT", "ETH/USDT"]
    test_intervals = ["1d"]  # Start with daily for simplicity
    data_limit = 300  # Get more data for better testing

    results = {}

    # Initialize backtester
    backtester = ForecastBacktester()

    for symbol in test_symbols:
        results[symbol] = {}

        for interval in test_intervals:
            logger.info(f"\n📊 ТЕСТИРУЕМ {symbol} на интервале {interval}")
            logger.info("-" * 50)

            try:
                # Fetch historical data
                candles = await fetch_candlesticks(symbol=symbol, interval=CandleInterval(interval), limit=data_limit)

                if not candles or len(candles) < 100:
                    logger.warning(f"Недостаточно данных для {symbol} {interval}")
                    continue

                prices = [float(candle.close_price) for candle in candles]
                logger.info(f"Получено {len(prices)} свечей")
                logger.info(f"Период: {candles[0].timestamp} - {candles[-1].timestamp}")
                logger.info(f"Цены: {prices[0]:.2f} → {prices[-1]:.2f}")

                # Compare working models (excluding Chronos due to compatibility issues)
                working_models = ["statsforecast", "neuralprophet"]

                comparison = await backtester.compare_models(
                    symbol=symbol,
                    interval=interval,
                    prices=prices,
                    models=working_models,
                    train_ratio=0.6,
                    test_ratio=0.4,
                )

                # Store results
                results[symbol][interval] = {
                    "total_data_points": len(prices),
                    "period_start": candles[0].timestamp,
                    "period_end": candles[-1].timestamp,
                    "price_range": f"{prices[0]:.2f} → {prices[-1]:.2f}",
                    "models_tested": len(comparison.metrics),
                    "best_model": comparison.best_model,
                    "metrics": [metric.to_dict() for metric in comparison.metrics],
                }

                # Print detailed results
                logger.info(f"\n📈 РЕЗУЛЬТАТЫ ДЛЯ {symbol} {interval}:")
                logger.info(f"  Всего данных: {len(prices)} свечей")
                logger.info(f"  Тестовый период: {len(prices) * 0.4:.0f} свечей")

                for metric in comparison.metrics:
                    direction_emoji = "↗️" if metric.direction_accuracy > 50 else "↘️"
                    logger.info(
                        f"  {metric.model:20} "
                        f"MAE: {metric.mae:8.2f} | "
                        f"RMSE: {metric.rmse:8.2f} | "
                        f"Напр.точн: {metric.direction_accuracy:5.1f}% {direction_emoji}"
                    )

                if comparison.best_model:
                    best_metrics = next(m for m in comparison.metrics if m.model == comparison.best_model)
                    logger.info(f"\n🏆 ЛУЧШАЯ МОДЕЛЬ: {comparison.best_model}")
                    logger.info(f"   MAE: {best_metrics.mae:.2f}")
                    logger.info(f"   Точность направления: {best_metrics.direction_accuracy:.1f}%")

            except Exception as e:
                logger.error(f"Ошибка тестирования {symbol} {interval}: {e}")
                results[symbol][interval] = {"error": str(e)}

    # Save detailed results
    output_file = Path("ml_backtest_results_2024.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str, ensure_ascii=False)

    logger.info(f"\n💾 Результаты сохранены в: {output_file}")

    # Print final summary
    print_final_summary(results)

    return results


def print_final_summary(results: dict):
    """Print comprehensive summary of backtest results."""
    logger.info("\n" + "=" * 80)
    logger.info("ИТОГОВЫЕ РЕЗУЛЬТАТЫ БЭКТЕСТА 2024")
    logger.info("=" * 80)

    total_tests = 0
    successful_tests = 0
    model_performance = {}

    for symbol, symbol_data in results.items():
        logger.info(f"\n🔸 {symbol}:")
        logger.info("─" * 40)

        for interval, interval_data in symbol_data.items():
            total_tests += 1

            if "error" in interval_data:
                logger.info(f"  {interval}: ❌ ОШИБКА - {interval_data['error']}")
                continue

            successful_tests += 1
            logger.info(f"  {interval}: ✅ УСПЕШНО")
            logger.info(f"    Данные: {interval_data['total_data_points']} свечей")
            logger.info(f"    Период: {interval_data['price_range']}")
            logger.info(f"    Моделей протестировано: {interval_data['models_tested']}")

            if interval_data["best_model"]:
                logger.info(f"    🏆 Лучшая модель: {interval_data['best_model']}")

                # Track model performance across tests
                model = interval_data["best_model"]
                if model not in model_performance:
                    model_performance[model] = 0
                model_performance[model] += 1

    # Overall statistics
    logger.info("\n📊 ОБЩАЯ СТАТИСТИКА:")
    logger.info(f"  Всего тестов: {total_tests}")
    logger.info(f"  Успешных: {successful_tests}")
    logger.info(
        f"  Процент успеха: {(successful_tests/total_tests)*100:.1f}%" if total_tests > 0 else "  Процент успеха: 0%"
    )

    if model_performance:
        logger.info("\n🤖 ПРОИЗВОДИТЕЛЬНОСТЬ МОДЕЛЕЙ:")
        for model, wins in model_performance.items():
            win_rate = (wins / successful_tests) * 100
            logger.info(f"  {model:20} - Побед: {wins} ({win_rate:.1f}%)")

    # Recommendations
    if model_performance:
        best_model = max(model_performance.items(), key=lambda x: x[1])[0]
        logger.info("\n🎯 РЕКОМЕНДАЦИЯ:")
        logger.info(f"  Для дальнейшей интеграции рекомендуется использовать: {best_model}")
        logger.info(
            f"  Эта модель показала лучшие результаты в {model_performance[best_model]} из {successful_tests} тестов"
        )


async def main():
    """Main execution function."""
    try:
        # Run comprehensive backtest
        results = await run_comprehensive_comparison()

        logger.info("\n" + "=" * 80)
        logger.info("✅ БЭКТЕСТ 2024 ЗАВЕРШЕН УСПЕШНО!")
        logger.info("=" * 80)
        logger.info("Сгенерированные файлы:")
        logger.info("  - ml_backtest_results_2024.json (детальные результаты)")
        logger.info("  - final_backtest_2024.log (лог выполнения)")

        return results

    except Exception as e:
        logger.error(f"❌ Фатальная ошибка бэктеста: {e}")
        raise


if __name__ == "__main__":
    # Run the backtest
    results = asyncio.run(main())
