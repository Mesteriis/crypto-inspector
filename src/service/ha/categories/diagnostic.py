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


@register_sensor(category="diagnostic")
class DatabaseStatusSensor(StatusSensor):
    """Database connection status."""

    config = SensorConfig(
        sensor_id="database_status",
        name="Database Status",
        name_ru="Статус базы данных",
        icon="mdi:database-check",
        entity_category="diagnostic",
        description="Database connection status",
        description_ru="Статус подключения к базе данных",
    )


@register_sensor(category="diagnostic")
class ApiStatusSensor(StatusSensor):
    """API server status."""

    config = SensorConfig(
        sensor_id="api_status",
        name="API Status",
        name_ru="Статус API",
        icon="mdi:api",
        entity_category="diagnostic",
        description="API server status",
        description_ru="Статус API сервера",
    )


@register_sensor(category="diagnostic")
class SchedulerStatusSensor(StatusSensor):
    """Scheduler status."""

    config = SensorConfig(
        sensor_id="scheduler_status",
        name="Scheduler Status",
        name_ru="Статус планировщика",
        icon="mdi:clock-check",
        entity_category="diagnostic",
        description="Background scheduler status",
        description_ru="Статус фонового планировщика",
    )


@register_sensor(category="diagnostic")
class VersionSensor(StatusSensor):
    """System version."""

    config = SensorConfig(
        sensor_id="version",
        name="Version",
        name_ru="Версия",
        icon="mdi:tag",
        entity_category="diagnostic",
        description="Crypto Inspect version",
        description_ru="Версия Crypto Inspect",
    )


@register_sensor(category="diagnostic")
class NotificationServiceSensor(StatusSensor):
    """Notification service status."""

    config = SensorConfig(
        sensor_id="notification_service",
        name="Notification Service",
        name_ru="Служба уведомлений",
        icon="mdi:bell-cog",
        entity_category="diagnostic",
        description="Notification service status",
        description_ru="Статус службы уведомлений",
    )


@register_sensor(category="diagnostic")
class CryptoCurrencyListSensor(StatusSensor):
    """List of tracked cryptocurrencies."""

    config = SensorConfig(
        sensor_id="crypto_currency_list",
        name="Tracked Currencies",
        name_ru="Отслеживаемые валюты",
        icon="mdi:format-list-bulleted",
        entity_category="diagnostic",
        description="List of tracked cryptocurrencies",
        description_ru="Список отслеживаемых криптовалют",
    )
