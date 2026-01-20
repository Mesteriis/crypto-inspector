"""Home Assistant инициализация и очистка.

Этот модуль обеспечивает:
1. Автоматическую очистку устаревших сенсоров при старте
2. Автоматическое создание input_helpers (input_number, input_select, input_boolean)
3. Валидацию и логирование процесса инициализации
"""

import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
import yaml

from services.ha_integration import get_supervisor_client
from services.ha_sensors import CryptoSensorsManager

logger = logging.getLogger(__name__)

# ============================================================================
# INPUT HELPERS DEFINITIONS
# ============================================================================


@dataclass
class InputNumberConfig:
    """Конфигурация input_number."""

    name: str
    min_value: float = 0
    max_value: float = 100
    step: float = 1
    initial: float | None = None
    unit: str | None = None
    icon: str = "mdi:numeric"
    mode: str = "box"


@dataclass
class InputSelectConfig:
    """Конфигурация input_select."""

    name: str
    options: list[str] = field(default_factory=list)
    initial: str | None = None
    icon: str = "mdi:format-list-bulleted"


@dataclass
class InputBooleanConfig:
    """Конфигурация input_boolean."""

    name: str
    initial: bool = False
    icon: str = "mdi:toggle-switch"


# Все input_number хелперы
INPUT_NUMBERS: dict[str, InputNumberConfig] = {
    # === DCA настройки ===
    "crypto_dca_weekly_amount": InputNumberConfig(
        name="DCA недельный бюджет",
        min_value=10,
        max_value=10000,
        step=10,
        initial=100,
        unit="€",
        icon="mdi:cash",
    ),
    "crypto_dca_btc_weight": InputNumberConfig(
        name="DCA вес BTC",
        min_value=0,
        max_value=100,
        step=5,
        initial=50,
        unit="%",
        icon="mdi:bitcoin",
        mode="slider",
    ),
    "crypto_dca_eth_weight": InputNumberConfig(
        name="DCA вес ETH",
        min_value=0,
        max_value=100,
        step=5,
        initial=30,
        unit="%",
        icon="mdi:ethereum",
        mode="slider",
    ),
    "crypto_dca_alt_weight": InputNumberConfig(
        name="DCA вес Alts",
        min_value=0,
        max_value=100,
        step=5,
        initial=20,
        unit="%",
        icon="mdi:currency-usd",
        mode="slider",
    ),
    # === RSI пороги ===
    "crypto_rsi_oversold": InputNumberConfig(
        name="RSI перепроданность",
        min_value=10,
        max_value=50,
        step=1,
        initial=30,
        icon="mdi:chart-line",
        mode="slider",
    ),
    "crypto_rsi_overbought": InputNumberConfig(
        name="RSI перекупленность",
        min_value=50,
        max_value=90,
        step=1,
        initial=70,
        icon="mdi:chart-line",
        mode="slider",
    ),
    # === Fear & Greed пороги ===
    "crypto_fg_extreme_fear": InputNumberConfig(
        name="F&G экстремальный страх",
        min_value=0,
        max_value=50,
        step=1,
        initial=20,
        icon="mdi:emoticon-cry",
        mode="slider",
    ),
    "crypto_fg_extreme_greed": InputNumberConfig(
        name="F&G экстремальная жадность",
        min_value=50,
        max_value=100,
        step=1,
        initial=80,
        icon="mdi:emoticon-happy",
        mode="slider",
    ),
    # === Whale Alert пороги ===
    "crypto_whale_btc_threshold": InputNumberConfig(
        name="Порог кита BTC",
        min_value=10,
        max_value=10000,
        step=10,
        initial=100,
        unit="BTC",
        icon="mdi:whale",
    ),
    "crypto_whale_eth_threshold": InputNumberConfig(
        name="Порог кита ETH",
        min_value=100,
        max_value=100000,
        step=100,
        initial=1000,
        unit="ETH",
        icon="mdi:whale",
    ),
    # === Ценовые алерты ===
    "crypto_btc_price_alert_low": InputNumberConfig(
        name="BTC алерт (низ)",
        min_value=1000,
        max_value=500000,
        step=1000,
        initial=80000,
        unit="USDT",
        icon="mdi:arrow-down-circle",
    ),
    "crypto_btc_price_alert_high": InputNumberConfig(
        name="BTC алерт (верх)",
        min_value=1000,
        max_value=500000,
        step=1000,
        initial=120000,
        unit="USDT",
        icon="mdi:arrow-up-circle",
    ),
    "crypto_eth_price_alert_low": InputNumberConfig(
        name="ETH алерт (низ)",
        min_value=100,
        max_value=50000,
        step=100,
        initial=2500,
        unit="USDT",
        icon="mdi:arrow-down-circle",
    ),
    "crypto_eth_price_alert_high": InputNumberConfig(
        name="ETH алерт (верх)",
        min_value=100,
        max_value=50000,
        step=100,
        initial=5000,
        unit="USDT",
        icon="mdi:arrow-up-circle",
    ),
    # === Конвертор валют ===
    "converter_amount": InputNumberConfig(
        name="Сумма конвертации",
        min_value=1,
        max_value=1000000,
        step=1,
        initial=100,
        icon="mdi:calculator",
    ),
    # === Очистка данных ===
    "crypto_cleanup_keep_days": InputNumberConfig(
        name="Хранить дней истории",
        min_value=1,
        max_value=365,
        step=1,
        initial=30,
        unit="days",
        icon="mdi:calendar-clock",
        mode="slider",
    ),
    "crypto_cleanup_min_candles": InputNumberConfig(
        name="Минимум свечей",
        min_value=100,
        max_value=10000,
        step=100,
        initial=1000,
        unit="candles",
        icon="mdi:candle",
        mode="box",
    ),
    # === Риск-менеджмент ===
    "crypto_max_drawdown_alert": InputNumberConfig(
        name="Алерт просадки",
        min_value=5,
        max_value=50,
        step=5,
        initial=20,
        unit="%",
        icon="mdi:trending-down",
        mode="slider",
    ),
    "crypto_position_size_max": InputNumberConfig(
        name="Макс. размер позиции",
        min_value=1,
        max_value=100,
        step=1,
        initial=10,
        unit="%",
        icon="mdi:resize",
        mode="slider",
    ),
}

# Все input_select хелперы
INPUT_SELECTS: dict[str, InputSelectConfig] = {
    "crypto_chart_coin": InputSelectConfig(
        name="Монета для графика",
        options=["BTC", "ETH", "SOL", "TON", "AR"],
        initial="BTC",
        icon="mdi:bitcoin",
    ),
    "crypto_main_coin": InputSelectConfig(
        name="Основная монета",
        options=["BTC", "ETH", "SOL", "TON", "AR"],
        initial="BTC",
        icon="mdi:star",
    ),
    "crypto_compare_coin": InputSelectConfig(
        name="Монета для сравнения",
        options=["Нет", "BTC", "ETH", "SOL", "TON", "AR"],
        initial="Нет",
        icon="mdi:compare",
    ),
    "crypto_currency": InputSelectConfig(
        name="Валюта отображения",
        options=["EUR", "USD", "RUB", "USDT"],
        initial="EUR",
        icon="mdi:currency-eur",
    ),
    "crypto_ta_coin": InputSelectConfig(
        name="Монета для TA",
        options=["BTC", "ETH", "SOL", "TON", "AR"],
        initial="BTC",
        icon="mdi:chart-line",
    ),
    "crypto_ta_timeframe": InputSelectConfig(
        name="Таймфрейм TA",
        options=["15m", "1h", "4h", "1d", "1w"],
        initial="1h",
        icon="mdi:clock-outline",
    ),
    "crypto_notification_language": InputSelectConfig(
        name="Язык уведомлений",
        options=["Russian", "English"],
        initial="Russian",
        icon="mdi:translate",
    ),
    "crypto_sensor_language": InputSelectConfig(
        name="Язык сенсоров",
        options=["Russian", "English"],
        initial="Russian",
        icon="mdi:translate-variant",
    ),
    "crypto_notification_mode": InputSelectConfig(
        name="Режим уведомлений",
        options=["all", "smart", "digest_only", "critical_only", "silent"],
        initial="smart",
        icon="mdi:bell-cog",
    ),
    "converter_currency": InputSelectConfig(
        name="Исходная валюта",
        options=["EUR", "USD", "RUB", "UAH", "BTC", "ETH", "USDT"],
        initial="EUR",
        icon="mdi:swap-horizontal",
    ),
    "crypto_currency_list": InputSelectConfig(
        name="Список криптовалют",
        options=["BTC/USDT", "ETH/USDT", "SOL/USDT", "TON/USDT", "AR/USDT"],
        initial="BTC/USDT,ETH/USDT,SOL/USDT,TON/USDT,AR/USDT",
        icon="mdi:bitcoin",
    ),
}

# Все input_boolean хелперы
INPUT_BOOLEANS: dict[str, InputBooleanConfig] = {
    "crypto_alerts_enabled": InputBooleanConfig(
        name="Алерты включены",
        initial=True,
        icon="mdi:bell",
    ),
    "crypto_dca_reminders_enabled": InputBooleanConfig(
        name="DCA напоминания",
        initial=True,
        icon="mdi:calendar-check",
    ),
    "crypto_whale_alerts_enabled": InputBooleanConfig(
        name="Whale алерты",
        initial=True,
        icon="mdi:whale",
    ),
    "crypto_morning_briefing_enabled": InputBooleanConfig(
        name="Утренний брифинг",
        initial=True,
        icon="mdi:weather-sunny",
    ),
    "crypto_evening_briefing_enabled": InputBooleanConfig(
        name="Вечерний брифинг",
        initial=True,
        icon="mdi:weather-night",
    ),
    "crypto_ai_analysis_enabled": InputBooleanConfig(
        name="AI анализ",
        initial=False,
        icon="mdi:robot",
    ),
    "crypto_risk_alerts_enabled": InputBooleanConfig(
        name="Риск-алерты",
        initial=True,
        icon="mdi:shield-alert",
    ),
    "crypto_technical_signals_enabled": InputBooleanConfig(
        name="Технические сигналы",
        initial=True,
        icon="mdi:chart-line",
    ),
    "crypto_cleanup_history_trigger": InputBooleanConfig(
        name="Очистить историю",
        initial=False,
        icon="mdi:delete-clock",
    ),
    "crypto_cleanup_database_trigger": InputBooleanConfig(
        name="Очистить базу данных",
        initial=False,
        icon="mdi:database-remove",
    ),
}

# Префикс для сенсоров нашего аддона
SENSOR_PREFIX = "sensor.crypto_inspect_"

# Директории blueprint-ов
BLUEPRINTS_SOURCE_DIR = Path("/blueprints")
BLUEPRINTS_TARGET_DIR = Path("/config/blueprints/automation/crypto_inspect")

# Список обязательных blueprint-ов
REQUIRED_BLUEPRINTS = [
    "price_alert.yaml",
    "fear_greed_alert.yaml",
    "dca_reminder.yaml",
    "technical_signal.yaml",
    "morning_briefing.yaml",
    "evening_briefing.yaml",
    "daily_digest.yaml",
    "goal_milestone.yaml",
    "portfolio_milestone.yaml",
    "ai_report.yaml",
    "whale_alert.yaml",
    "risk_alert.yaml",
]

# Дефолтные параметры для автоматизаций
DEFAULT_AUTOMATION_CONFIGS = {
    "price_alert.yaml": {
        "symbol": "BTC",
        "condition": "below",
        "target_price": 80000,
        "notify_device": None,  # Будет определено динамически
    },
    "fear_greed_alert.yaml": {"threshold": 20, "condition": "below", "notify_device": None},
    "dca_reminder.yaml": {"day_of_week": "mon", "time": "09:00:00", "notify_device": None},
    "technical_signal.yaml": {"symbol": "BTC", "indicators": ["rsi", "macd"], "notify_device": None},
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


async def get_all_entity_ids(client) -> list[str]:
    """
    Получить список всех entity_id из Home Assistant.

    Returns:
        Список entity_id.
    """
    if not client.is_available:
        logger.debug("Supervisor API недоступен")
        return []

    http_client = await client._get_client()
    url = "/core/api/states"

    try:
        response = await http_client.get(url)
        response.raise_for_status()
        states = response.json()
        return [s.get("entity_id", "") for s in states if s.get("entity_id")]
    except httpx.HTTPError as e:
        logger.error(f"Не удалось получить states: {e}")
        return []


async def entity_exists(client, entity_id: str) -> bool:
    """
    Проверить существует ли entity.

    Args:
        client: SupervisorAPIClient
        entity_id: Полный entity_id

    Returns:
        True если существует.
    """
    if not client.is_available:
        return False

    http_client = await client._get_client()
    url = f"/core/api/states/{entity_id}"

    try:
        response = await http_client.get(url)
        return response.status_code == 200
    except httpx.HTTPError:
        return False


async def delete_entity(client, entity_id: str) -> bool:
    """
    Удалить entity из Home Assistant.

    Args:
        client: SupervisorAPIClient
        entity_id: Полный entity_id

    Returns:
        True если успешно.
    """
    if not client.is_available:
        return False

    http_client = await client._get_client()
    url = f"/core/api/states/{entity_id}"

    try:
        response = await http_client.delete(url)
        if response.status_code in (200, 204, 404):
            logger.debug(f"Удалена entity: {entity_id}")
            return True
        return False
    except httpx.HTTPError as e:
        logger.error(f"Не удалось удалить {entity_id}: {e}")
        return False


# ============================================================================
# CLEANUP FUNCTIONS
# ============================================================================


async def cleanup_old_sensors() -> int:
    """
    Очистка устаревших сенсоров.

    Находит и удаляет сенсоры с префиксом crypto_inspect_,
    которых нет в текущей конфигурации SENSORS.

    Returns:
        Количество удалённых сенсоров.
    """
    client = get_supervisor_client()

    if not client.is_available:
        logger.warning("Supervisor API недоступен, пропускаем очистку сенсоров")
        return 0

    logger.info("Начинаем очистку устаревших сенсоров...")

    # Получаем текущие entity_id
    all_entities = await get_all_entity_ids(client)

    # Фильтруем по нашему префиксу
    our_sensors = [e for e in all_entities if e.startswith(SENSOR_PREFIX)]

    # Получаем список актуальных сенсоров из SENSORS
    valid_sensor_ids = set(CryptoSensorsManager.SENSORS.keys())
    # Добавляем встроенные сенсоры из ha_integration
    valid_sensor_ids.update(
        [
            "status",
            "prices",
            "changes_24h",
            "volumes_24h",
            "fear_greed",
            "market_pulse",
            "btc_dominance",
            "do_nothing_ok",
            "investor_phase",
            "calm_indicator",
            "red_flags",
            "ta_rsi",
            "ta_trend",
            "buffer_size",
            "candles_total",
            "sync_status",
            # Старые имена для обратной совместимости
            "btc_price",
            "eth_price",
        ]
    )

    # Находим устаревшие сенсоры
    removed_count = 0
    for entity_id in our_sensors:
        sensor_id = entity_id.replace(SENSOR_PREFIX, "")
        if sensor_id not in valid_sensor_ids:
            logger.info(f"Удаляем устаревший сенсор: {entity_id}")
            if await delete_entity(client, entity_id):
                removed_count += 1

    if removed_count > 0:
        logger.info(f"Очистка завершена: удалено {removed_count} устаревших сенсоров")
    else:
        logger.info("Устаревших сенсоров не найдено")

    return removed_count


# ============================================================================
# INPUT HELPER CREATION
# ============================================================================


async def create_input_number(client, object_id: str, config: InputNumberConfig) -> bool:
    """
    Создать input_number helper.

    Args:
        client: SupervisorAPIClient
        object_id: ID без префикса
        config: Конфигурация

    Returns:
        True если успешно создан или уже существует.
    """
    entity_id = f"input_number.{object_id}"

    if await entity_exists(client, entity_id):
        logger.debug(f"input_number {object_id} уже существует")
        return True

    # Пробуем создать через helpers API
    http_client = await client._get_client()
    helpers_url = "/core/api/config/input_number"

    data = {
        "name": config.name,
        "min": config.min_value,
        "max": config.max_value,
        "step": config.step,
        "mode": config.mode,
        "icon": config.icon,
    }
    if config.initial is not None:
        data["initial"] = config.initial
    if config.unit:
        data["unit_of_measurement"] = config.unit

    try:
        response = await http_client.post(helpers_url, json=data)
        if response.status_code in (200, 201):
            logger.info(f"Создан input_number: {object_id}")
            return True
        else:
            logger.warning(
                f"input_number {object_id} не создан автоматически (код {response.status_code}). "
                f"Добавьте в configuration.yaml"
            )
            return False
    except httpx.HTTPError as e:
        logger.warning(f"Не удалось создать input_number {object_id}: {e}")
        return False


async def create_input_select(client, object_id: str, config: InputSelectConfig) -> bool:
    """
    Создать input_select helper.

    Args:
        client: SupervisorAPIClient
        object_id: ID без префикса
        config: Конфигурация

    Returns:
        True если успешно создан или уже существует.
    """
    entity_id = f"input_select.{object_id}"

    if await entity_exists(client, entity_id):
        logger.debug(f"input_select {object_id} уже существует")
        return True

    http_client = await client._get_client()
    helpers_url = "/core/api/config/input_select"

    data = {
        "name": config.name,
        "options": config.options,
        "icon": config.icon,
    }
    if config.initial:
        data["initial"] = config.initial

    try:
        response = await http_client.post(helpers_url, json=data)
        if response.status_code in (200, 201):
            logger.info(f"Создан input_select: {object_id}")
            return True
        else:
            logger.warning(f"input_select {object_id} не создан автоматически. " f"Добавьте в configuration.yaml")
            return False
    except httpx.HTTPError as e:
        logger.warning(f"Не удалось создать input_select {object_id}: {e}")
        return False


async def create_input_boolean(client, object_id: str, config: InputBooleanConfig) -> bool:
    """
    Создать input_boolean helper.

    Args:
        client: SupervisorAPIClient
        object_id: ID без префикса
        config: Конфигурация

    Returns:
        True если успешно создан или уже существует.
    """
    entity_id = f"input_boolean.{object_id}"

    if await entity_exists(client, entity_id):
        logger.debug(f"input_boolean {object_id} уже существует")
        return True

    http_client = await client._get_client()
    helpers_url = "/core/api/config/input_boolean"

    data = {
        "name": config.name,
        "icon": config.icon,
        "initial": config.initial,
    }

    try:
        response = await http_client.post(helpers_url, json=data)
        if response.status_code in (200, 201):
            logger.info(f"Создан input_boolean: {object_id}")
            return True
        else:
            logger.warning(f"input_boolean {object_id} не создан автоматически. " f"Добавьте в configuration.yaml")
            return False
    except httpx.HTTPError as e:
        logger.warning(f"Не удалось создать input_boolean {object_id}: {e}")
        return False


async def validate_and_create_helpers() -> dict[str, int]:
    """
    Валидация и создание всех input_helpers.

    Returns:
        Статистика: {"created": N, "existing": N, "failed": N}
    """
    client = get_supervisor_client()

    if not client.is_available:
        logger.warning("Supervisor API недоступен, пропускаем создание input helpers")
        return {"created": 0, "existing": 0, "failed": 0}

    logger.info("Проверяем и создаём input helpers...")

    stats = {"created": 0, "existing": 0, "failed": 0}

    # input_number
    for object_id, config in INPUT_NUMBERS.items():
        entity_id = f"input_number.{object_id}"
        if await entity_exists(client, entity_id):
            stats["existing"] += 1
        elif await create_input_number(client, object_id, config):
            stats["created"] += 1
        else:
            stats["failed"] += 1

    # input_select
    for object_id, config in INPUT_SELECTS.items():
        entity_id = f"input_select.{object_id}"
        if await entity_exists(client, entity_id):
            stats["existing"] += 1
        elif await create_input_select(client, object_id, config):
            stats["created"] += 1
        else:
            stats["failed"] += 1

    # input_boolean
    for object_id, config in INPUT_BOOLEANS.items():
        entity_id = f"input_boolean.{object_id}"
        if await entity_exists(client, entity_id):
            stats["existing"] += 1
        elif await create_input_boolean(client, object_id, config):
            stats["created"] += 1
        else:
            stats["failed"] += 1

    logger.info(
        f"Input helpers: создано {stats['created']}, " f"существует {stats['existing']}, " f"ошибок {stats['failed']}"
    )

    return stats


# ============================================================================
# MAIN INITIALIZATION
# ============================================================================


async def initialize_ha_entities() -> dict[str, Any]:
    """
    Главная функция инициализации Home Assistant entities.

    Выполняет:
    1. Очистку устаревших сенсоров
    2. Создание/валидацию input helpers
    3. Установку blueprint-ов
    4. Валидацию blueprint-ов
    5. Создание автоматизаций из blueprint-ов

    Returns:
        Статистика инициализации.
    """
    logger.info("=== Начинаем инициализацию Home Assistant entities ===")

    result = {
        "sensors_removed": 0,
        "helpers_created": 0,
        "helpers_existing": 0,
        "helpers_failed": 0,
        "blueprints_installed": 0,
        "blueprints_skipped": 0,
        "blueprints_failed": 0,
        "blueprints_valid": 0,
        "blueprints_invalid": 0,
        "automations_created": 0,
        "automations_skipped": 0,
        "automations_failed": 0,
    }

    # 1. Очистка устаревших сенсоров
    try:
        result["sensors_removed"] = await cleanup_old_sensors()
    except Exception as e:
        logger.error(f"Ошибка при очистке сенсоров: {e}")

    # 2. Создание input helpers
    try:
        helpers_stats = await validate_and_create_helpers()
        result["helpers_created"] = helpers_stats.get("created", 0)
        result["helpers_existing"] = helpers_stats.get("existing", 0)
        result["helpers_failed"] = helpers_stats.get("failed", 0)
    except Exception as e:
        logger.error(f"Ошибка при создании input helpers: {e}")

    # 3. Установка blueprint-ов
    try:
        blueprint_install_stats = await install_blueprints()
        result["blueprints_installed"] = blueprint_install_stats.get("installed", 0)
        result["blueprints_skipped"] = blueprint_install_stats.get("skipped", 0)
        result["blueprints_failed"] = blueprint_install_stats.get("failed", 0)
    except Exception as e:
        logger.error(f"Ошибка при установке blueprint-ов: {e}")

    # 4. Валидация blueprint-ов
    try:
        blueprint_validation = await validate_blueprints()
        result["blueprints_valid"] = blueprint_validation.get("valid", 0)
        result["blueprints_invalid"] = blueprint_validation.get("invalid", 0)
        # Логируем детали валидации только при наличии проблем
        invalid_details = {
            name: details
            for name, details in blueprint_validation.get("details", {}).items()
            if details.get("errors") and "OK" not in details["errors"]
        }
        if invalid_details:
            logger.warning(f"Невалидные blueprint-ы: {list(invalid_details.keys())}")
    except Exception as e:
        logger.error(f"Ошибка при валидации blueprint-ов: {e}")

    # 5. Создание автоматизаций из blueprint-ов
    try:
        automation_stats = await create_automations_from_blueprints()
        result["automations_created"] = automation_stats.get("created", 0)
        result["automations_skipped"] = automation_stats.get("skipped", 0)
        result["automations_failed"] = automation_stats.get("failed", 0)
    except Exception as e:
        logger.error(f"Ошибка при создании автоматизаций: {e}")

    logger.info("=== Инициализация Home Assistant entities завершена ===")
    logger.info(
        f"Результат: "
        f"сенсоров удалено={result['sensors_removed']}, "
        f"helpers создано={result['helpers_created']}, "
        f"helpers существует={result['helpers_existing']}, "
        f"helpers ошибок={result['helpers_failed']}, "
        f"blueprints установлено={result['blueprints_installed']}, "
        f"blueprints пропущено={result['blueprints_skipped']}, "
        f"blueprints ошибок={result['blueprints_failed']}, "
        f"blueprints валидных={result['blueprints_valid']}, "
        f"blueprints невалидных={result['blueprints_invalid']}, "
        f"автоматизаций создано={result['automations_created']}, "
        f"автоматизаций пропущено={result['automations_skipped']}, "
        f"автоматизаций ошибок={result['automations_failed']}"
    )

    return result


async def install_blueprints() -> dict[str, int]:
    """
    Автоматическая установка blueprint-ов в Home Assistant.

    Копирует файлы blueprint-ов из исходной директории в
    конфигурационную директорию Home Assistant.

    Returns:
        Статистика установки: {"installed": N, "skipped": N, "failed": N}
    """
    stats = {"installed": 0, "skipped": 0, "failed": 0}

    # Проверяем доступность Supervisor API
    client = get_supervisor_client()
    if not client.is_available:
        logger.warning("Supervisor API недоступен, пропускаем установку blueprint-ов")
        return stats

    logger.info("Начинаем установку blueprint-ов...")

    # Создаем целевую директорию если она не существует
    try:
        BLUEPRINTS_TARGET_DIR.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Директория blueprint-ов создана: {BLUEPRINTS_TARGET_DIR}")
    except Exception as e:
        logger.error(f"Не удалось создать директорию blueprint-ов: {e}")
        stats["failed"] = len(REQUIRED_BLUEPRINTS)
        return stats

    # Копируем каждый blueprint
    for blueprint_file in REQUIRED_BLUEPRINTS:
        source_path = BLUEPRINTS_SOURCE_DIR / blueprint_file
        target_path = BLUEPRINTS_TARGET_DIR / blueprint_file

        # Проверяем существование исходного файла
        if not source_path.exists():
            logger.warning(f"Исходный файл blueprint не найден: {source_path}")
            stats["failed"] += 1
            continue

        # Проверяем нужно ли обновить
        if target_path.exists():
            try:
                source_mtime = source_path.stat().st_mtime
                target_mtime = target_path.stat().st_mtime
                if source_mtime <= target_mtime:
                    logger.debug(f"Blueprint уже актуален: {blueprint_file}")
                    stats["skipped"] += 1
                    continue
            except Exception:
                pass  # Если не можем проверить время, копируем заново

        # Копируем файл
        try:
            shutil.copy2(source_path, target_path)
            logger.info(f"Установлен blueprint: {blueprint_file}")
            stats["installed"] += 1
        except Exception as e:
            logger.error(f"Не удалось скопировать blueprint {blueprint_file}: {e}")
            stats["failed"] += 1

    logger.info(
        f"Установка blueprint-ов завершена: "
        f"установлено={stats['installed']}, "
        f"пропущено={stats['skipped']}, "
        f"ошибок={stats['failed']}"
    )

    return stats


async def validate_blueprints() -> dict[str, Any]:
    """
    Проверка корректности установленных blueprint-ов.

    Проверяет:
    1. Существование файлов
    2. Корректность YAML формата
    3. Наличие обязательных полей blueprint
    4. Совместимость с текущей версией

    Returns:
        Результаты валидации
    """
    results = {"total": len(REQUIRED_BLUEPRINTS), "valid": 0, "invalid": 0, "missing": 0, "details": {}}

    logger.info("Начинаем валидацию blueprint-ов...")

    for blueprint_file in REQUIRED_BLUEPRINTS:
        target_path = BLUEPRINTS_TARGET_DIR / blueprint_file
        blueprint_name = blueprint_file.replace(".yaml", "")

        result = {"exists": False, "valid_format": False, "has_blueprint_section": False, "errors": []}

        # Проверяем существование файла
        if not target_path.exists():
            result["errors"].append("Файл не найден")
            results["missing"] += 1
            results["details"][blueprint_name] = result
            continue

        result["exists"] = True

        # Проверяем формат YAML
        try:
            with open(target_path, encoding="utf-8") as f:
                content = yaml.safe_load(f)
            result["valid_format"] = True
        except yaml.YAMLError as e:
            result["errors"].append(f"Ошибка YAML: {str(e)}")
            results["invalid"] += 1
            results["details"][blueprint_name] = result
            continue
        except Exception as e:
            result["errors"].append(f"Ошибка чтения файла: {str(e)}")
            results["invalid"] += 1
            results["details"][blueprint_name] = result
            continue

        # Проверяем наличие секции blueprint
        if not isinstance(content, dict) or "blueprint" not in content:
            result["errors"].append("Отсутствует секция 'blueprint'")
            results["invalid"] += 1
            results["details"][blueprint_name] = result
            continue

        blueprint_section = content["blueprint"]
        result["has_blueprint_section"] = True

        # Проверяем обязательные поля в секции blueprint
        required_fields = ["name", "domain"]
        for field in required_fields:
            if field not in blueprint_section:
                result["errors"].append(f"Отсутствует обязательное поле: {field}")

        # Проверяем что domain = automation
        if blueprint_section.get("domain") != "automation":
            result["errors"].append("Неверный домен (должен быть 'automation')")

        # Если есть ошибки, помечаем как невалидный
        if result["errors"]:
            results["invalid"] += 1
        else:
            results["valid"] += 1
            result["errors"] = ["OK"]

        results["details"][blueprint_name] = result

    logger.info(
        f"Валидация завершена: "
        f"валидных={results['valid']}, "
        f"невалидных={results['invalid']}, "
        f"отсутствующих={results['missing']}"
    )

    return results


async def create_automations_from_blueprints() -> dict[str, int]:
    """
    Создание автоматизаций на основе установленных blueprint-ов.

    Использует дефолтные параметры для создания базовых автоматизаций.

    Returns:
        Статистика создания: {"created": N, "skipped": N, "failed": N}
    """
    stats = {"created": 0, "skipped": 0, "failed": 0}

    client = get_supervisor_client()
    if not client.is_available:
        logger.warning("Supervisor API недоступен, пропускаем создание автоматизаций")
        return stats

    logger.info("Начинаем создание автоматизаций из blueprint-ов...")

    # Получаем список мобильных устройств для уведомлений
    mobile_devices = await _get_mobile_devices(client)
    if not mobile_devices:
        logger.warning("Мобильные устройства не найдены, некоторые автоматизации могут не работать")

    # Создаем автоматизации для каждого blueprint с дефолтными параметрами
    for blueprint_file, default_config in DEFAULT_AUTOMATION_CONFIGS.items():
        blueprint_name = blueprint_file.replace(".yaml", "")
        automation_id = f"crypto_inspect_{blueprint_name}_default"

        # Проверяем существует ли уже такая автоматизация
        if await _automation_exists(client, automation_id):
            logger.debug(f"Автоматизация уже существует: {automation_id}")
            stats["skipped"] += 1
            continue

        # Обновляем конфигурацию с реальными данными
        config = default_config.copy()
        if config.get("notify_device") is None and mobile_devices:
            config["notify_device"] = mobile_devices[0]  # Используем первое доступное устройство

        # Создаем автоматизацию
        success = await _create_automation_from_blueprint(client, automation_id, blueprint_name, config)

        if success:
            logger.info(f"Создана автоматизация: {automation_id}")
            stats["created"] += 1
        else:
            logger.error(f"Не удалось создать автоматизацию: {automation_id}")
            stats["failed"] += 1

    logger.info(
        f"Создание автоматизаций завершено: "
        f"создано={stats['created']}, "
        f"пропущено={stats['skipped']}, "
        f"ошибок={stats['failed']}"
    )

    return stats


async def _get_mobile_devices(client) -> list[str]:
    """Получить список мобильных устройств."""
    try:
        http_client = await client._get_client()
        response = await http_client.get("/core/api/devices")
        response.raise_for_status()

        devices = response.json()
        mobile_devices = []

        for device in devices:
            if device.get("disabled_by") is None:  # Не отключенное устройство
                integrations = device.get("config_entries", [])
                # Ищем устройства с мобильной интеграцией
                for config_entry in integrations:
                    # Здесь можно добавить более точную проверку интеграции
                    if "mobile_app" in str(config_entry).lower():
                        mobile_devices.append(device["id"])
                        break

        return mobile_devices
    except Exception as e:
        logger.error(f"Ошибка получения списка мобильных устройств: {e}")
        return []


async def _automation_exists(client, automation_id: str) -> bool:
    """Проверить существует ли автоматизация."""
    try:
        http_client = await client._get_client()
        response = await http_client.get(f"/core/api/automations/{automation_id}")
        return response.status_code == 200
    except Exception:
        return False


async def _create_automation_from_blueprint(client, automation_id: str, blueprint_name: str, config: dict) -> bool:
    """Создать автоматизацию на основе blueprint."""
    try:
        http_client = await client._get_client()

        # Формируем конфигурацию автоматизации
        automation_config = {
            "alias": f"Crypto Inspect - {blueprint_name.title()} (Auto)",
            "description": f"Автоматически созданная автоматизация из blueprint: {blueprint_name}",
            "mode": "single",
            "use_blueprint": {"path": f"crypto_inspect/{blueprint_name}.yaml", "input": config},
        }

        # Отправляем запрос на создание
        response = await http_client.post("/core/api/automations", json=automation_config)

        return response.status_code in (200, 201)

    except Exception as e:
        logger.error(f"Ошибка создания автоматизации {automation_id}: {e}")
        return False

    """
    Генерирует YAML-конфигурацию для отсутствующих input helpers.

    Полезно если автоматическое создание не сработало.

    Returns:
        YAML строка для configuration.yaml
    """
    client = get_supervisor_client()
    yaml_parts = []

    # input_number
    missing_numbers = []
    for object_id, config in INPUT_NUMBERS.items():
        entity_id = f"input_number.{object_id}"
        if not await entity_exists(client, entity_id):
            lines = [f"  {object_id}:"]
            lines.append(f'    name: "{config.name}"')
            lines.append(f"    min: {config.min_value}")
            lines.append(f"    max: {config.max_value}")
            lines.append(f"    step: {config.step}")
            if config.initial is not None:
                lines.append(f"    initial: {config.initial}")
            if config.unit:
                lines.append(f'    unit_of_measurement: "{config.unit}"')
            lines.append(f"    icon: {config.icon}")
            missing_numbers.append("\n".join(lines))

    if missing_numbers:
        yaml_parts.append("input_number:")
        yaml_parts.extend(missing_numbers)

    # input_select
    missing_selects = []
    for object_id, config in INPUT_SELECTS.items():
        entity_id = f"input_select.{object_id}"
        if not await entity_exists(client, entity_id):
            lines = [f"  {object_id}:"]
            lines.append(f'    name: "{config.name}"')
            lines.append("    options:")
            for opt in config.options:
                lines.append(f"      - {opt}")
            if config.initial:
                lines.append(f"    initial: {config.initial}")
            lines.append(f"    icon: {config.icon}")
            missing_selects.append("\n".join(lines))

    if missing_selects:
        yaml_parts.append("\ninput_select:")
        yaml_parts.extend(missing_selects)

    # input_boolean
    missing_booleans = []
    for object_id, config in INPUT_BOOLEANS.items():
        entity_id = f"input_boolean.{object_id}"
        if not await entity_exists(client, entity_id):
            lines = [f"  {object_id}:"]
            lines.append(f'    name: "{config.name}"')
            lines.append(f"    initial: {'true' if config.initial else 'false'}")
            lines.append(f"    icon: {config.icon}")
            missing_booleans.append("\n".join(lines))

    if missing_booleans:
        yaml_parts.append("\ninput_boolean:")
        yaml_parts.extend(missing_booleans)

    return "\n".join(yaml_parts)
