#!/usr/bin/env python3
"""
Debug Chronos Output Format
"""

import numpy as np
import torch
from chronos import ChronosPipeline


def debug_chronos_output():
    print("🔍 ОТЛАДКА ФОРМАТА ВЫХОДНЫХ ДАННЫХ CHRONOS")
    print("=" * 50)

    # Загрузим модель
    print("Загружаем модель...")
    pipeline = ChronosPipeline.from_pretrained("amazon/chronos-t5-tiny", device_map="cpu")
    print("✅ Модель загружена")

    # Тестовые данные
    test_data = torch.tensor(
        [[45000, 46000, 47000, 46500, 47200, 48000, 47800, 48500, 49000, 48800]], dtype=torch.float32
    )
    print(f"Входные данные shape: {test_data.shape}")
    print(f"Входные данные: {test_data}")

    # Сделаем предсказание
    print("\nГенерируем прогноз...")
    forecast = pipeline.predict(test_data, prediction_length=3, num_samples=20)
    print(f"Выходной тензор shape: {forecast.shape}")
    print(f"Тип выходного тензора: {type(forecast)}")

    # Исследуем структуру
    print("\nАтрибуты тензора:")
    print(f"  ndim: {forecast.ndim}")
    print(f"  dtype: {forecast.dtype}")

    # Попробуем разные способы извлечения данных
    print("\nПопытки извлечения медианы:")

    try:
        # Метод 1: стандартный
        median1 = forecast.median(dim=1).values[0]
        print(f"  Метод 1 (median(dim=1)): {median1}")
    except Exception as e:
        print(f"  Метод 1 ОШИБКА: {e}")

    try:
        # Метод 2: индексирование
        median2 = forecast[0].median(dim=0).values
        print(f"  Метод 2 ([0].median(dim=0)): {median2}")
    except Exception as e:
        print(f"  Метод 2 ОШИБКА: {e}")

    try:
        # Метод 3: reshape
        reshaped = forecast.reshape(-1, forecast.shape[-1])
        median3 = reshaped.median(dim=0).values
        print(f"  Метод 3 (reshape): {median3}")
    except Exception as e:
        print(f"  Метод 3 ОШИБКА: {e}")

    # Проверим содержимое тензора
    print("\nСодержимое тензора (первые 2 сэмпла):")
    print(f"forecast[0, :2, :]: {forecast[0, :2, :]}")

    # Попробуем конвертировать в numpy
    try:
        numpy_forecast = forecast.numpy()
        print(f"\nNumpy conversion shape: {numpy_forecast.shape}")
        median_np = np.median(numpy_forecast, axis=1)[0]
        print(f"Numpy median: {median_np}")
        return median_np.tolist()
    except Exception as e:
        print(f"Numpy conversion ОШИБКА: {e}")
        return None


if __name__ == "__main__":
    result = debug_chronos_output()
    if result:
        print(f"\n🎉 УДАЛОСЬ ИЗВЛЕЧЬ ДАННЫЕ: {result}")
    else:
        print("\n💥 НЕ УДАЛОСЬ ИЗВЛЕЧЬ ДАННЫЕ")
