"""Diagnostic sensors - sync status, database info, system health."""

from service.ha.core.base import SensorConfig
from service.ha.core.registry import register_sensor
from service.ha.sensors.scalar import CountSensor, ScalarSensor, StatusSensor


@register_sensor(category="diagnostic")
class SyncStatusSensor(StatusSensor):
    """Data synchronization status."""

    config = SensorConfig(
        sensor_id="sync_status",
        name="Sync Status",
        name_ru="Статус синхронизации",
        icon="mdi:sync",
        entity_category="diagnostic",
        description="Status: idle/running/completed/error",
        description_ru="Статус: idle/running/completed/error",
    )


@register_sensor(category="diagnostic")
class LastSyncSensor(ScalarSensor):
    """Time of last synchronization."""

    config = SensorConfig(
        sensor_id="last_sync",
        name="Last Sync",
        name_ru="Последняя синхронизация",
        icon="mdi:clock-outline",
        device_class="timestamp",
        entity_category="diagnostic",
        description="Time of last synchronization",
        description_ru="Время последней синхронизации",
    )


@register_sensor(category="diagnostic")
class CandlesCountSensor(CountSensor):
    """Total candles in database."""

    config = SensorConfig(
        sensor_id="candles_count",
        name="Total Candles",
        name_ru="Всего свечей",
        icon="mdi:database",
        unit="candles",
        entity_category="diagnostic",
        description="Total number of candles in DB",
        description_ru="Общее количество свечей в БД",
    )


@register_sensor(category="diagnostic")
class DatabaseSizeSensor(ScalarSensor):
    """Database file size."""

    config = SensorConfig(
        sensor_id="database_size",
        name="Database Size",
        name_ru="Размер базы данных",
        icon="mdi:database-settings",
        unit="MB",
        entity_category="diagnostic",
        description="Size of database file",
        description_ru="Размер файла базы данных",
        value_type="float",
        min_value=0,
    )
