#!/usr/bin/env python3
"""
Quick ML Backtest with Fixed Parameters

This script runs a simplified backtest to verify the ML models work correctly.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.candlestick import CandleInterval, fetch_candlesticks
from services.ml.backtester import ForecastBacktester
from services.ml.forecaster import PriceForecaster

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)


async def run_simple_test():
    """Run a simple test with minimal data requirements."""
    logger.info("ЗАПУСК УПРОЩЕННОГО БЭКТЕСТА")
    logger.info("=" * 50)

    # Initialize components
    forecaster = PriceForecaster()
    backtester = ForecastBacktester()

    # Test with smaller dataset
    symbol = "BTC/USDT"
    interval = "1d"

    logger.info(f"Тестируем {symbol} на интервале {interval}")

    try:
        # Fetch data (request more to have enough for testing)
        candles = await fetch_candlesticks(
            symbol=symbol,
            interval=CandleInterval(interval),
            limit=200,  # Increase limit for better testing
        )

        if not candles:
            logger.error("Не удалось получить данные")
            return

        prices = [float(candle.close_price) for candle in candles]
        logger.info(f"Получено {len(prices)} цен закрытия")
        logger.info(f"Цены: {prices[0]:.2f} -> {prices[-1]:.2f}")

        # Test direct prediction first
        logger.info("\n--- ТЕСТИРУЕМ ПРЯМОЕ ПРЕДСКАЗАНИЕ ---")
        try:
            forecast = await forecaster.predict(
                symbol=symbol,
                interval=interval,
                prices=prices[-100:],  # Use last 100 points
                model="statsforecast",
                horizon=3,
            )
            logger.info("✅ Предсказание успешно!")
            logger.info(f"  Текущая цена: {prices[-1]:.2f}")
            logger.info(f"  Прогноз (+3 свечи): {forecast.predictions[-1]:.2f}")
            logger.info(f"  Все прогнозы: {[f'{p:.2f}' for p in forecast.predictions]}")
        except Exception as e:
            logger.error(f"❌ Ошибка прямого предсказания: {e}")

        # Test backtest with adjusted parameters
        logger.info("\n--- ТЕСТИРУЕМ БЭКТЕСТ ---")
        try:
            # Use smaller ratios to ensure we have enough data
            metrics = await backtester.run_backtest(
                symbol=symbol,
                interval=interval,
                prices=prices,
                model="statsforecast",
                train_ratio=0.6,  # Reduced from 0.7
                val_ratio=0.0,  # No validation
                test_ratio=0.4,  # Increased from 0.3
            )
            logger.info("✅ Бэктест успешен!")
            logger.info(f"  MAE: {metrics.mae:.4f}")
            logger.info(f"  RMSE: {metrics.rmse:.4f}")
            logger.info(f"  Direction Accuracy: {metrics.direction_accuracy:.1f}%")
            logger.info(f"  Sample Size: {metrics.sample_size}")

        except Exception as e:
            logger.error(f"❌ Ошибка бэктеста: {e}")

        # Test model comparison
        logger.info("\n--- СРАВНЕНИЕ МОДЕЛЕЙ ---")
        try:
            comparison = await backtester.compare_models(
                symbol=symbol,
                interval=interval,
                prices=prices,
                models=["statsforecast", "neuralprophet"],  # Exclude problematic chronos
                train_ratio=0.6,
                test_ratio=0.4,
            )

            logger.info("✅ Сравнение моделей завершено!")
            logger.info(f"  Лучшая модель: {comparison.best_model}")

            for metric in comparison.metrics:
                logger.info(
                    f"  {metric.model:20} MAE: {metric.mae:.4f} " f"Direction: {metric.direction_accuracy:.1f}%"
                )

        except Exception as e:
            logger.error(f"❌ Ошибка сравнения моделей: {e}")

    except Exception as e:
        logger.error(f"Общая ошибка: {e}")
        raise


async def main():
    """Main execution."""
    try:
        await run_simple_test()
        logger.info("\n" + "=" * 50)
        logger.info("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО!")
        logger.info("=" * 50)

    except Exception as e:
        logger.error(f"Фатальная ошибка: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
