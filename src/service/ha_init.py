"""Home Assistant инициализация и очистка.

Этот модуль обеспечивает:
1. Автоматическую очистку устаревших сенсоров при старте
2. Автоматическое создание input_helpers (input_number, input_select, input_boolean)
3. Валидацию и логирование процесса инициализации
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from service.ha import SensorRegistry
from service.ha_integration import get_supervisor_client

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
    которых нет в текущей конфигурации SensorRegistry.

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

    # Получаем список актуальных сенсоров из SensorRegistry
    SensorRegistry.ensure_initialized()
    valid_sensor_ids = set(SensorRegistry.get_all().keys())

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


async def validate_and_create_helpers() -> dict[str, int]:
    """
    Проверка наличия input_helpers.

    ПРИМЕЧАНИЕ: Home Assistant REST API не поддерживает создание input helpers.
    Пользователь должен создать их через UI или configuration.yaml.

    Returns:
        Статистика: {"created": 0, "existing": N, "failed": 0}
    """
    client = get_supervisor_client()

    if not client.is_available:
        logger.debug("Supervisor API недоступен, пропускаем проверку input helpers")
        return {"created": 0, "existing": 0, "failed": 0}

    stats = {"created": 0, "existing": 0, "failed": 0}
    missing_helpers: list[str] = []

    # Проверяем input_number
    for object_id in INPUT_NUMBERS:
        entity_id = f"input_number.{object_id}"
        if await entity_exists(client, entity_id):
            stats["existing"] += 1
        else:
            missing_helpers.append(entity_id)

    # Проверяем input_select
    for object_id in INPUT_SELECTS:
        entity_id = f"input_select.{object_id}"
        if await entity_exists(client, entity_id):
            stats["existing"] += 1
        else:
            missing_helpers.append(entity_id)

    # Проверяем input_boolean
    for object_id in INPUT_BOOLEANS:
        entity_id = f"input_boolean.{object_id}"
        if await entity_exists(client, entity_id):
            stats["existing"] += 1
        else:
            missing_helpers.append(entity_id)

    # Логируем результат
    if missing_helpers:
        logger.debug(
            f"Input helpers не найдены ({len(missing_helpers)}). "
            f"Создайте их через UI: Настройки → Устройства и службы → Вспомогательные"
        )
    else:
        logger.debug(f"Input helpers: все {stats['existing']} существуют")

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
        result["blueprints_invalid"] = blueprint_validation.get("invalid", 0) + blueprint_validation.get("missing", 0)
    except Exception as e:
        logger.debug(f"Ошибка при валидации blueprint-ов: {e}")

    # 5. Создание автоматизаций из blueprint-ов
    try:
        automation_stats = await create_automations_from_blueprints()
        result["automations_created"] = automation_stats.get("created", 0)
        result["automations_skipped"] = automation_stats.get("skipped", 0)
        result["automations_failed"] = automation_stats.get("failed", 0)
    except Exception as e:
        logger.error(f"Ошибка при создании автоматизаций: {e}")

    logger.info("=== Инициализация Home Assistant entities завершена ===")
    logger.debug(
        f"Результат: "
        f"helpers={result['helpers_existing']}, "
        f"blueprints={result['blueprints_valid']}/{result['blueprints_valid'] + result['blueprints_invalid']}"
    )

    return result


async def install_blueprints() -> dict[str, int]:
    """
    Установка blueprint-ов в Home Assistant.

    ПРИМЕЧАНИЕ: Add-on не может записывать файлы в /config (read-only filesystem).
    Blueprint-ы должны быть установлены вручную через UI или скопированы в
    /config/blueprints/automation/crypto_inspect/ вручную.

    Returns:
        Статистика: всегда {"installed": 0, "skipped": 0, "failed": 0}
    """
    stats = {"installed": 0, "skipped": 0, "failed": 0}

    # Add-on не может записывать в /config (read-only filesystem)
    # Blueprint-ы доступны в /blueprints директории add-on
    logger.debug(
        f"Blueprint-ы доступны в {BLUEPRINTS_SOURCE_DIR}. "
        f"Скопируйте их вручную в {BLUEPRINTS_TARGET_DIR}"
    )

    return stats


async def validate_blueprints() -> dict[str, Any]:
    """
    Проверка корректности установленных blueprint-ов.

    ПРИМЕЧАНИЕ: Blueprint-ы устанавливаются пользователем вручную.
    Эта функция только проверяет их наличие в целевой директории.

    Returns:
        Результаты валидации
    """
    results = {"total": len(REQUIRED_BLUEPRINTS), "valid": 0, "invalid": 0, "missing": 0, "details": {}}

    # Проверяем наличие blueprint-ов в целевой директории
    for blueprint_file in REQUIRED_BLUEPRINTS:
        target_path = BLUEPRINTS_TARGET_DIR / blueprint_file
        blueprint_name = blueprint_file.replace(".yaml", "")

        if target_path.exists():
            results["valid"] += 1
            results["details"][blueprint_name] = {"exists": True, "errors": []}
        else:
            results["missing"] += 1
            results["details"][blueprint_name] = {"exists": False, "errors": ["Файл не найден"]}

    # Логируем результат
    if results["missing"] > 0:
        logger.debug(
            f"Blueprint-ы не установлены ({results['missing']}/{results['total']}). "
            f"Скопируйте из {BLUEPRINTS_SOURCE_DIR} в {BLUEPRINTS_TARGET_DIR}"
        )
    else:
        logger.debug(f"Blueprint-ы: все {results['valid']} установлены")

    return results


async def create_automations_from_blueprints() -> dict[str, int]:
    """
    Создание автоматизаций на основе установленных blueprint-ов.

    ПРИМЕЧАНИЕ: Home Assistant REST API не поддерживает создание автоматизаций.
    Автоматизации создаются пользователем вручную через UI на основе blueprint-ов.

    Returns:
        Статистика: всегда {"created": 0, "skipped": 0, "failed": 0}
    """
    stats = {"created": 0, "skipped": 0, "failed": 0}

    # Home Assistant REST API не поддерживает создание автоматизаций
    # Пользователь должен создать их вручную через UI:
    # Настройки → Автоматизации → Создать из Blueprint → Crypto Inspect
    logger.debug(
        "Автоматизации создаются пользователем вручную через UI на основе blueprint-ов. "
        "Настройки → Автоматизации → Создать из Blueprint → Crypto Inspect"
    )

    return stats
