"""Home Assistant инициализация и очистка.

Этот модуль обеспечивает:
1. Автоматическую очистку устаревших сенсоров при старте
2. Автоматическое создание input_helpers (input_number, input_select, input_boolean)
3. Валидацию и логирование процесса инициализации
"""

import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

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
}

# Префикс для сенсоров нашего аддона
SENSOR_PREFIX = "sensor.crypto_inspect_"


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

    Returns:
        Статистика инициализации.
    """
    logger.info("=== Начинаем инициализацию Home Assistant entities ===")

    result = {
        "sensors_removed": 0,
        "helpers_created": 0,
        "helpers_existing": 0,
        "helpers_failed": 0,
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

    logger.info("=== Инициализация Home Assistant entities завершена ===")
    logger.info(
        f"Результат: удалено сенсоров={result['sensors_removed']}, "
        f"helpers создано={result['helpers_created']}, "
        f"helpers существует={result['helpers_existing']}, "
        f"helpers ошибок={result['helpers_failed']}"
    )

    return result


async def get_missing_helpers_yaml() -> str:
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
