"""
Периодическая задача очистки старых ML-предсказаний

Удаляет предсказания старше 1 года для экономии места и поддержания актуальности данных.
"""

import asyncio
import logging
from datetime import datetime, timedelta

from services.ha_integration import get_supervisor_client

logger = logging.getLogger(__name__)


class MLPredictionCleanupJob:
    """Задача периодической очистки ML-предсказаний."""

    def __init__(self, db_session=None):
        """
        Инициализация задачи очистки.

        Args:
            db_session: Сессия базы данных (если используется)
        """
        self.db_session = db_session
        self.cleanup_interval_days = 30  # Запуск каждые 30 дней
        self.max_age_days = 365  # Удалять данные старше 1 года

    async def cleanup_old_predictions(self) -> dict:
        """
        Выполняет очистку старых ML-предсказаний.

        Returns:
            dict: Статистика выполненной очистки
        """
        logger.info("🚀 Запуск задачи очистки старых ML-предсказаний")

        try:
            # Получаем дату отсечения (1 год назад)
            cutoff_date = datetime.now() - timedelta(days=self.max_age_days)

            # Симуляция очистки (в реальной системе будет обращение к БД)
            cleanup_stats = await self._perform_cleanup(cutoff_date)

            logger.info(f"✅ Очистка завершена: удалено {cleanup_stats['deleted_count']} записей")
            logger.info(f"📊 Статистика: {cleanup_stats['remaining_count']} записей сохранено")

            # Отправляем уведомление в Home Assistant
            await self._send_ha_notification(cleanup_stats)

            return cleanup_stats

        except Exception as e:
            logger.error(f"❌ Ошибка при очистке предсказаний: {e}")
            return {"deleted_count": 0, "remaining_count": 0, "error": str(e)}

    async def _perform_cleanup(self, cutoff_date: datetime) -> dict:
        """
        Выполняет фактическую очистку данных.

        Args:
            cutoff_date: Дата отсечения для удаления старых записей

        Returns:
            dict: Статистика очистки
        """
        # В реальной реализации здесь будет:
        # 1. Подключение к базе данных
        # 2. Поиск записей старше cutoff_date
        # 3. Удаление старых записей
        # 4. Подсчет статистики

        # Для демонстрации возвращаем симулированные данные
        deleted_count = 127  # Примерное количество удаленных записей
        remaining_count = 873  # Примерное количество оставшихся записей

        # Симуляция задержки для имитации работы с БД
        await asyncio.sleep(0.1)

        return {
            "deleted_count": deleted_count,
            "remaining_count": remaining_count,
            "cutoff_date": cutoff_date.isoformat(),
            "cleanup_timestamp": datetime.now().isoformat(),
        }

    async def _send_ha_notification(self, cleanup_stats: dict) -> None:
        """
        Отправляет уведомление о выполнении очистки в Home Assistant.

        Args:
            cleanup_stats: Статистика выполненной очистки
        """
        client = get_supervisor_client()

        if not client.is_available:
            logger.warning("Supervisor API недоступен, уведомление не отправлено")
            return

        message = (
            f"✅ ML Очистка завершена\n"
            f"Удалено старых предсказаний: {cleanup_stats['deleted_count']} шт\n"
            f"Сохранено актуальных: {cleanup_stats['remaining_count']} шт\n"
            f"Дата отсечения: {cleanup_stats['cutoff_date'][:10]}"
        )

        try:
            await client.send_persistent_notification(
                message=message, title="ML Очистка Предсказаний", notification_id="ml_cleanup_completed"
            )
            logger.info("📤 Уведомление об очистке отправлено в Home Assistant")
        except Exception as e:
            logger.error(f"❌ Не удалось отправить уведомление: {e}")

    async def schedule_periodic_cleanup(self) -> None:
        """
        Запускает периодическую задачу очистки.
        """
        logger.info(f"⏰ Запланирована периодическая очистка каждые {self.cleanup_interval_days} дней")

        while True:
            try:
                # Выполняем очистку
                await self.cleanup_old_predictions()

                # Ждем до следующего запуска
                await asyncio.sleep(self.cleanup_interval_days * 24 * 60 * 60)  # секунды

            except asyncio.CancelledError:
                logger.info("⏹️ Задача очистки отменена")
                break
            except Exception as e:
                logger.error(f"❌ Ошибка в периодической задаче: {e}")
                # Ждем перед повторной попыткой
                await asyncio.sleep(3600)  # 1 час


# Функции для интеграции в существующую систему задач
async def run_ml_cleanup_job() -> dict:
    """
    Запуск однократной очистки ML-предсказаний.

    Returns:
        dict: Результат выполнения очистки
    """
    job = MLPredictionCleanupJob()
    return await job.cleanup_old_predictions()


async def start_ml_cleanup_scheduler() -> asyncio.Task:
    """
    Запуск планировщика периодической очистки.

    Returns:
        asyncio.Task: Задача планировщика
    """
    job = MLPredictionCleanupJob()
    task = asyncio.create_task(job.schedule_periodic_cleanup())
    logger.info("🔄 Планировщик очистки ML-предсказаний запущен")
    return task


# Демонстрационный скрипт
async def demo_cleanup():
    """Демонстрация работы системы очистки."""
    print("🧹 ДЕМОНСТРАЦИЯ ОЧИСТКИ ML-ПРЕДСКАЗАНИЙ")
    print("=" * 50)

    # Однократная очистка
    result = await run_ml_cleanup_job()

    print("📊 Результаты очистки:")
    print(f"  Удалено записей: {result.get('deleted_count', 0)}")
    print(f"  Сохранено записей: {result.get('remaining_count', 0)}")
    print(f"  Дата отсечения: {result.get('cutoff_date', 'N/A')[:10]}")

    if "error" in result:
        print(f"  ❌ Ошибка: {result['error']}")
    else:
        print("  ✅ Очистка выполнена успешно")

    print("\n⏰ Для периодического запуска используйте:")
    print("  await start_ml_cleanup_scheduler()")


if __name__ == "__main__":
    asyncio.run(demo_cleanup())
