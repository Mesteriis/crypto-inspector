#!/usr/bin/env python3
"""
Test Chronos T5 Model Integration
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from service.ml.chronos_forecaster import ChronosBoltForecaster


async def test_chronos_integration():
    """Test Chronos model integration."""
    print("🔍 ТЕСТИРУЕМ ИНТЕГРАЦИЮ CHRONOS T5")
    print("=" * 50)

    try:
        # Create forecaster
        print("Создаем Chronos форекастер...")
        forecaster = ChronosBoltForecaster()
        print("✅ Форекастер создан успешно!")

        # Test data
        test_prices = [45000, 46000, 47000, 46500, 47200, 48000, 47800, 48500, 49000, 48800]
        print(f"Тестовые данные: {test_prices}")

        # Make prediction
        print("Генерируем прогноз...")
        result = await forecaster.predict(test_prices, horizon=3)

        print("✅ Прогноз успешно сгенерирован!")
        print(f"Прогнозируемые цены: {[f'{p:.2f}' for p in result.predictions]}")
        print(f"Направление: {result.direction}")
        print(f"Уверенность: {result.confidence_pct:.1f}%")
        print(f"Доверительный интервал: [{result.confidence_low[0]:.2f}, {result.confidence_high[0]:.2f}]")

        return True

    except Exception as e:
        print(f"❌ Ошибка интеграции: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_chronos_integration())
    if success:
        print("\n🎉 CHRONOS T5 ИНТЕГРИРОВАН УСПЕШНО!")
    else:
        print("\n💥 ИНТЕГРАЦИЯ НЕ УДАЛАСЬ")
