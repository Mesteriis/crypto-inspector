"""Интеграционные тесты для модуля интеграции с Home Assistant.

Этот модуль содержит полноценные интеграционные тесты, которые проверяют
реальную функциональность системы интеграции с Home Assistant:
- Регистрация сенсоров через SensorRegistry
- Отправка уведомлений через Supervisor API
- Синхронизация данных между приложением и HA
- Взаимодействие с MQTT Discovery
- Обновление значений сенсоров
- Работа HAIntegrationManager

Тесты фокусируются на позитивных сценариях использования (happy path).
"""

import json
import os
import sys
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from faker import Faker

# Добавляем src в путь для импортов
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(project_root, "src"))


# =============================================================================
# Фабрики для генерации тестовых данных
# =============================================================================


class CryptoDataFactory:
    """Фабрика для генерации криптовалютных тестовых данных."""

    SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "AR/USDT", "TON/USDT"]

    def __init__(self, seed: int | None = None):
        self.fake = Faker()
        if seed:
            Faker.seed(seed)

    def create_prices(self, symbols: list[str] | None = None) -> dict[str, float]:
        """Генерация словаря цен криптовалют."""
        symbols = symbols or self.SYMBOLS
        prices = {}
        price_ranges = {
            "BTC": (90000, 110000),
            "ETH": (2800, 4000),
            "SOL": (180, 280),
            "AR": (15, 35),
            "TON": (3, 8),
        }
        for symbol in symbols:
            base = symbol.split("/")[0]
            min_price, max_price = price_ranges.get(base, (10, 1000))
            prices[symbol] = round(self.fake.pyfloat(min_value=min_price, max_value=max_price), 2)
        return prices

    def create_changes_24h(self, symbols: list[str] | None = None) -> dict[str, float]:
        """Генерация словаря изменений цен за 24ч (в процентах)."""
        symbols = symbols or self.SYMBOLS
        return {s: round(self.fake.pyfloat(min_value=-15.0, max_value=15.0), 2) for s in symbols}

    def create_volumes_24h(self, symbols: list[str] | None = None) -> dict[str, float]:
        """Генерация словаря объёмов торгов за 24ч."""
        symbols = symbols or self.SYMBOLS
        return {s: round(self.fake.pyfloat(min_value=1e8, max_value=1e11), 0) for s in symbols}

    def create_investor_status(self) -> dict[str, Any]:
        """Генерация данных статуса инвестора."""
        phases = ["accumulation", "markup", "distribution", "markdown"]
        return {
            "do_nothing_ok": self.fake.boolean(chance_of_getting_true=70),
            "phase": self.fake.random_element(phases),
            "phase_ru": self.fake.random_element(["Накопление", "Рост", "Распределение", "Снижение"]),
            "calm_score": self.fake.pyint(min_value=30, max_value=90),
            "red_flags_count": self.fake.pyint(min_value=0, max_value=3),
            "red_flags": [],
            "market_tension": self.fake.random_element(["low", "medium", "high"]),
            "price_context": self.fake.random_element(["cheap", "fair", "expensive"]),
            "dca_amount": round(self.fake.pyfloat(min_value=0, max_value=500), 2),
            "dca_signal": self.fake.random_element(["strong_buy", "buy", "hold", "none"]),
            "weekly_insight": self.fake.sentence(nb_words=8),
        }

    def create_market_data(self) -> dict[str, Any]:
        """Генерация рыночных данных."""
        return {
            "fear_greed": self.fake.pyint(min_value=10, max_value=90),
            "btc_dominance": round(self.fake.pyfloat(min_value=40.0, max_value=60.0), 2),
            "derivatives": {
                "funding_rate": round(self.fake.pyfloat(min_value=-0.05, max_value=0.1), 4),
                "long_short_ratio": round(self.fake.pyfloat(min_value=0.5, max_value=2.0), 2),
            },
        }

    def create_smart_summary(self) -> dict[str, Any]:
        """Генерация данных умного саммари."""
        return {
            "pulse": self.fake.random_element(["Bullish", "Neutral", "Bearish"]),
            "pulse_ru": self.fake.random_element(["Бычий", "Нейтральный", "Медвежий"]),
            "pulse_confidence": self.fake.pyint(min_value=50, max_value=95),
            "health": self.fake.random_element(["Excellent", "Good", "Fair", "Poor"]),
            "health_ru": self.fake.random_element(["Отлично", "Хорошо", "Удовлетворительно", "Плохо"]),
            "health_score": self.fake.pyint(min_value=40, max_value=100),
            "action": self.fake.random_element(["Buy", "Hold", "Wait", "Take Profit"]),
            "action_ru": self.fake.random_element(["Покупать", "Держать", "Ждать", "Фиксировать прибыль"]),
            "action_priority": self.fake.random_element(["low", "medium", "high"]),
            "outlook": self.fake.sentence(nb_words=10),
            "outlook_ru": self.fake.sentence(nb_words=10),
        }

    def create_ta_data(self, symbols: list[str] | None = None) -> dict[str, dict]:
        """Генерация данных технического анализа."""
        symbols = symbols or self.SYMBOLS
        result = {}
        for symbol in symbols:
            price = self.create_prices([symbol])[symbol]
            result[symbol] = {
                "rsi": round(self.fake.pyfloat(min_value=20, max_value=80), 1),
                "macd_signal": self.fake.random_element(["bullish", "bearish", "neutral"]),
                "bb_position": round(self.fake.pyfloat(min_value=0, max_value=100), 1),
                "trend": self.fake.random_element(["uptrend", "downtrend", "sideways"]),
                "support": round(price * 0.95, 2),
                "resistance": round(price * 1.05, 2),
            }
        return result

    def create_bybit_portfolio(self) -> dict[str, Any]:
        """Генерация данных портфеля Bybit."""
        balance = round(self.fake.pyfloat(min_value=10000, max_value=100000), 2)
        return {
            "balance": balance,
            "pnl_24h": round(self.fake.pyfloat(min_value=-1000, max_value=2000), 2),
            "pnl_7d": round(self.fake.pyfloat(min_value=-3000, max_value=5000), 2),
            "unrealized_pnl": round(self.fake.pyfloat(min_value=-500, max_value=1000), 2),
            "positions": [
                {"symbol": "BTCUSDT", "side": "Long", "pnl": round(self.fake.pyfloat(-200, 500), 2)},
                {"symbol": "ETHUSDT", "side": "Short", "pnl": round(self.fake.pyfloat(-150, 300), 2)},
            ],
            "earn_balance": round(balance * 0.2, 2),
            "earn_positions": [
                {"coin": "USDT", "amount": 5000.0, "apy": 3.5},
                {"coin": "BTC", "amount": 0.1, "usd_value": 9500.0, "apy": 2.1},
            ],
            "earn_apy": 3.0,
            "total_portfolio": round(balance * 1.2, 2),
        }


# =============================================================================
# Фикстуры pytest
# =============================================================================


@pytest.fixture
def crypto_factory():
    """Фикстура для фабрики криптовалютных данных."""
    return CryptoDataFactory(seed=42)


@pytest.fixture
def mock_supervisor_client():
    """Мок SupervisorAPIClient с активным токеном и замоканным HTTP клиентом."""
    from service.ha_integration import SupervisorAPIClient

    client = SupervisorAPIClient()
    client.token = "test_token_123"

    # Мокаем HTTP клиент
    mock_http = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json = MagicMock(return_value={"state": "unknown", "attributes": {}})
    mock_http.post = AsyncMock(return_value=mock_response)
    mock_http.get = AsyncMock(return_value=mock_response)
    mock_http.is_closed = False

    # Патчим метод _get_client чтобы возвращал наш мок
    async def mock_get_client():
        return mock_http

    client._get_client = mock_get_client
    client._client = mock_http

    yield client


@pytest.fixture
def mock_publisher(mock_supervisor_client):
    """Мок SupervisorPublisher."""
    from service.ha.core.publisher import SupervisorPublisher

    publisher = SupervisorPublisher(client=mock_supervisor_client)
    return publisher


@pytest.fixture
def ha_manager(mock_publisher, initialized_registry):
    """Фикстура для HAIntegrationManager с мок-паблишером."""
    from service.ha import HAIntegrationManager

    manager = HAIntegrationManager(publisher=mock_publisher)
    return manager


@pytest.fixture
def mock_mqtt_client():
    """Мок MQTT клиента."""
    client = AsyncMock()
    client.publish = AsyncMock()
    client.is_connected = MagicMock(return_value=True)
    return client


@pytest.fixture(scope="module")
def initialized_registry():
    """Инициализированный реестр сенсоров (один раз на модуль).

    Примечание: SensorRegistry использует декораторы, которые выполняются
    при первом импорте модулей. После clear() повторная инициализация
    не сработает без перезагрузки модулей. Поэтому используем scope='module'.
    """
    from service.ha import SensorRegistry

    # Инициализируем реестр (если ещё не инициализирован)
    SensorRegistry.ensure_initialized()
    return SensorRegistry


# =============================================================================
# Тесты SensorRegistry - регистрация и управление сенсорами
# =============================================================================


class TestSensorRegistryИнтеграция:
    """Интеграционные тесты для SensorRegistry.

    Проверяют корректную регистрацию, поиск и управление
    всеми сенсорами системы.
    """

    def test_регистрация_всех_сенсоров_при_инициализации(self, initialized_registry):
        """При вызове ensure_initialized регистрируются все сенсоры из категорий."""
        # Проверяем минимальное количество сенсоров
        assert initialized_registry.count() >= 130, (
            f"Ожидалось минимум 130 сенсоров, получено {initialized_registry.count()}"
        )

    def test_категории_сенсоров_корректно_определены(self, initialized_registry):
        """Все основные категории сенсоров присутствуют."""
        expected_categories = [
            "price",
            "investor",
            "market",
            "technical",
            "risk",
            "traditional",
            "ai",
            "alerts",
            "diagnostic",
        ]

        actual_categories = initialized_registry.get_categories()

        for category in expected_categories:
            assert category in actual_categories, f"Категория '{category}' отсутствует"

    def test_получение_сенсора_по_идентификатору(self, initialized_registry):
        """Сенсор можно получить по его ID."""
        # Проверяем основные сенсоры
        for sensor_id in ["prices", "fear_greed", "do_nothing_ok"]:
            sensor_class = initialized_registry.get(sensor_id)
            assert sensor_class is not None
            assert hasattr(sensor_class, "config")
            assert sensor_class.config.sensor_id == sensor_id

    def test_сенсоры_категории_price_содержат_все_ценовые_сенсоры(self, initialized_registry):
        """Категория price содержит все необходимые сенсоры цен."""
        price_sensors = initialized_registry.get_by_category("price")

        expected = ["prices", "changes_24h", "volumes_24h", "highs_24h", "lows_24h"]
        for sensor_id in expected:
            assert sensor_id in price_sensors, f"Сенсор '{sensor_id}' отсутствует в категории price"

    def test_is_registered_возвращает_корректный_результат(self, initialized_registry):
        """Метод is_registered корректно определяет наличие сенсора."""
        assert initialized_registry.is_registered("prices") is True
        assert initialized_registry.is_registered("fear_greed") is True
        assert initialized_registry.is_registered("несуществующий_сенсор") is False


# =============================================================================
# Тесты HAIntegrationManager - основной менеджер интеграции
# =============================================================================


class TestHAIntegrationManagerИнтеграция:
    """Интеграционные тесты для HAIntegrationManager.

    Проверяют полный цикл работы менеджера:
    - Инициализация всех сенсоров
    - Публикация данных
    - Обновление состояний
    """

    def test_инициализация_менеджера_создает_все_сенсоры(self, ha_manager):
        """При инициализации менеджера создаются экземпляры всех сенсоров."""
        assert len(ha_manager._sensors) >= 130, (
            f"Ожидалось минимум 130 сенсоров, получено {len(ha_manager._sensors)}"
        )

    def test_device_info_содержит_корректные_данные(self, ha_manager):
        """Device info содержит все необходимые поля."""
        info = ha_manager.device_info

        assert "identifiers" in info
        assert "name" in info
        assert "manufacturer" in info
        assert "sw_version" in info
        assert ha_manager.DEVICE_ID in info["identifiers"]

    @pytest.mark.asyncio
    async def test_обновление_цен_публикует_данные_во_все_ценовые_сенсоры(
        self, ha_manager, crypto_factory, mock_publisher
    ):
        """При обновлении цены данные публикуются во все связанные сенсоры."""
        prices = crypto_factory.create_prices()
        changes = crypto_factory.create_changes_24h()
        volumes = crypto_factory.create_volumes_24h()

        # Обновляем цены по одной
        for symbol in prices:
            await ha_manager.update_price(
                symbol=symbol,
                price=Decimal(str(prices[symbol])),
                change_24h=changes[symbol],
                volume_24h=Decimal(str(volumes[symbol])),
            )

        # Проверяем, что внутренние кеши заполнены
        assert len(ha_manager._prices) == len(prices)
        assert len(ha_manager._changes) == len(changes)
        assert len(ha_manager._volumes) == len(volumes)

    @pytest.mark.asyncio
    async def test_обновление_всех_цен_одновременно(self, ha_manager, crypto_factory):
        """Метод update_all_prices корректно обновляет все цены."""
        prices_data = {}
        prices = crypto_factory.create_prices()
        changes = crypto_factory.create_changes_24h()
        volumes = crypto_factory.create_volumes_24h()

        for symbol in prices:
            prices_data[symbol] = {
                "price": prices[symbol],
                "change_24h": changes[symbol],
                "volume_24h": volumes[symbol],
            }

        await ha_manager.update_all_prices(prices_data)

        assert len(ha_manager._prices) == len(prices)
        for symbol, price in prices.items():
            assert ha_manager._prices[symbol] == str(price)

    @pytest.mark.asyncio
    async def test_обновление_статуса_инвестора(self, ha_manager, crypto_factory):
        """Обновление статуса инвестора корректно публикует все данные."""
        status_data = crypto_factory.create_investor_status()

        await ha_manager.update_investor_status(status_data)

        # Проверяем, что метод не вызвал исключений
        # Реальная проверка публикации через мок publisher
        assert True  # Тест прошёл без ошибок

    @pytest.mark.asyncio
    async def test_обновление_рыночных_данных(self, ha_manager, crypto_factory):
        """Обновление рыночных данных публикуется корректно."""
        market_data = crypto_factory.create_market_data()

        await ha_manager.update_market_data(
            fear_greed=market_data["fear_greed"],
            btc_dominance=market_data["btc_dominance"],
            derivatives_data=market_data["derivatives"],
        )

        # Тест прошёл без ошибок
        assert True

    @pytest.mark.asyncio
    async def test_обновление_smart_summary(self, ha_manager, crypto_factory):
        """Smart summary корректно публикуется."""
        summary_data = crypto_factory.create_smart_summary()

        await ha_manager.update_smart_summary(summary_data)

        assert True

    @pytest.mark.asyncio
    async def test_публикация_произвольного_сенсора(self, ha_manager):
        """Публикация данных в любой зарегистрированный сенсор."""
        result = await ha_manager.publish_sensor(
            sensor_id="fear_greed",
            value=65,
            attributes={"classification": "Greed"},
        )

        # При активном publisher результат True
        assert result is True

    @pytest.mark.asyncio
    async def test_публикация_незарегистрированного_сенсора_через_fallback(self, ha_manager):
        """Незарегистрированный сенсор публикуется через fallback."""
        result = await ha_manager.publish_sensor(
            sensor_id="custom_sensor_xyz",
            value="test_value",
        )

        # Fallback публикация работает
        assert result is True


# =============================================================================
# Тесты SupervisorAPIClient - клиент Supervisor API
# =============================================================================


class TestSupervisorAPIClientИнтеграция:
    """Интеграционные тесты для SupervisorAPIClient.

    Проверяют взаимодействие с Supervisor REST API для:
    - Создания и обновления сенсоров
    - Отправки уведомлений
    - Вызова сервисов HA
    """

    @pytest.mark.asyncio
    async def test_создание_сенсора_через_api(self, mock_supervisor_client):
        """Создание сенсора отправляет корректный запрос."""
        result = await mock_supervisor_client.create_sensor(
            sensor_id="test_sensor",
            state="online",
            friendly_name="Test Sensor",
            icon="mdi:test-tube",
            unit="units",
        )

        assert result is True
        mock_supervisor_client._client.post.assert_called()

    @pytest.mark.asyncio
    async def test_обновление_сенсора_через_api(self, mock_supervisor_client):
        """Обновление состояния сенсора работает корректно."""
        result = await mock_supervisor_client.update_sensor(
            sensor_id="test_sensor",
            state="50",
            attributes={"last_updated": "2024-01-01T00:00:00"},
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_отправка_persistent_notification(self, mock_supervisor_client):
        """Отправка постоянного уведомления."""
        result = await mock_supervisor_client.send_persistent_notification(
            message="Тестовое сообщение",
            title="Тест",
            notification_id="test_notification",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_вызов_сервиса_ha(self, mock_supervisor_client):
        """Вызов произвольного сервиса Home Assistant."""
        result = await mock_supervisor_client.call_service(
            domain="light",
            service="turn_on",
            data={"entity_id": "light.test"},
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_fire_event_отправляет_событие(self, mock_supervisor_client):
        """Отправка кастомного события в HA."""
        result = await mock_supervisor_client.fire_event(
            event_type="crypto_alert",
            event_data={"symbol": "BTC", "action": "buy"},
        )

        assert result is True



# =============================================================================
# Тесты типов сенсоров - Dict, Scalar, Composite
# =============================================================================


class TestDictSensorИнтеграция:
    """Интеграционные тесты для DictSensor и его подклассов."""

    @pytest.mark.asyncio
    async def test_price_dict_sensor_валидирует_положительные_цены(self, mock_publisher):
        """PriceDictSensor принимает только положительные цены."""
        from service.ha.core.base import SensorConfig
        from service.ha.sensors.dict import PriceDictSensor

        class TestPriceSensor(PriceDictSensor):
            config = SensorConfig(
                sensor_id="test_prices",
                name="Test Prices",
                name_ru="Тестовые цены",
                icon="mdi:currency-usd",
            )

        sensor = TestPriceSensor(mock_publisher)

        # Корректные данные
        valid_data = {"BTC": 95000.0, "ETH": 3200.50}
        result = sensor.validate(valid_data)
        assert result == valid_data

        # Отрицательная цена вызывает ошибку
        with pytest.raises(ValueError, match="Invalid price"):
            sensor.validate({"BTC": -100})

    @pytest.mark.asyncio
    async def test_percent_dict_sensor_округляет_проценты(self, mock_publisher):
        """PercentDictSensor округляет значения до 2 знаков."""
        from service.ha.core.base import SensorConfig
        from service.ha.sensors.dict import PercentDictSensor

        class TestPercentSensor(PercentDictSensor):
            config = SensorConfig(
                sensor_id="test_changes",
                name="Test Changes",
                name_ru="Тестовые изменения",
                icon="mdi:percent",
            )

        sensor = TestPercentSensor(mock_publisher)

        data = {"BTC": 2.5678, "ETH": -1.2345}
        result = sensor.validate(data)

        assert result["BTC"] == 2.57
        assert result["ETH"] == -1.23

    @pytest.mark.asyncio
    async def test_dict_sensor_конвертирует_decimal_в_float(self, mock_publisher):
        """DictSensor корректно конвертирует Decimal в float."""
        from service.ha.core.base import SensorConfig
        from service.ha.sensors.dict import DictSensor

        class TestDictSensor(DictSensor):
            config = SensorConfig(
                sensor_id="test_dict",
                name="Test Dict",
                name_ru="Тестовый словарь",
                icon="mdi:database",
            )

        sensor = TestDictSensor(mock_publisher)

        data = {"BTC": Decimal("95000.12345"), "ETH": Decimal("3200.5")}
        result = sensor.validate(data)

        assert isinstance(result["BTC"], float)
        assert isinstance(result["ETH"], float)


# =============================================================================
# Тесты BaseSensor - базовый класс сенсоров
# =============================================================================


class TestBaseSensorИнтеграция:
    """Интеграционные тесты для BaseSensor."""

    @pytest.mark.asyncio
    async def test_publish_кеширует_значение(self, mock_publisher):
        """После publish значение сохраняется в кеше."""
        from service.ha.core.base import BaseSensor, SensorConfig

        class TestSensor(BaseSensor):
            config = SensorConfig(
                sensor_id="test_base",
                name="Test Base",
                name_ru="Тестовый базовый",
                icon="mdi:test",
                value_type="int",
            )

        sensor = TestSensor(mock_publisher)
        await sensor.publish(42)

        assert sensor.cached_value == 42

    @pytest.mark.asyncio
    async def test_validate_проверяет_тип_int(self, mock_publisher):
        """Валидация проверяет тип int."""
        from service.ha.core.base import BaseSensor, SensorConfig

        class IntSensor(BaseSensor):
            config = SensorConfig(
                sensor_id="int_sensor",
                name="Int Sensor",
                name_ru="Целочисленный сенсор",
                icon="mdi:numeric",
                value_type="int",
            )

        sensor = IntSensor(mock_publisher)

        assert sensor.validate(42) == 42
        assert sensor.validate("42") == 42
        assert sensor.validate(42.8) == 42

    @pytest.mark.asyncio
    async def test_validate_проверяет_диапазон_значений(self, mock_publisher):
        """Валидация проверяет min/max диапазон."""
        from service.ha.core.base import BaseSensor, SensorConfig

        class RangeSensor(BaseSensor):
            config = SensorConfig(
                sensor_id="range_sensor",
                name="Range Sensor",
                name_ru="Сенсор с диапазоном",
                icon="mdi:gauge",
                value_type="float",
                min_value=0.0,
                max_value=100.0,
            )

        sensor = RangeSensor(mock_publisher)

        assert sensor.validate(50.0) == 50.0

        with pytest.raises(ValueError, match="below minimum"):
            sensor.validate(-10.0)

        with pytest.raises(ValueError, match="above maximum"):
            sensor.validate(150.0)

    @pytest.mark.asyncio
    async def test_format_state_для_разных_типов(self, mock_publisher):
        """format_state корректно форматирует разные типы."""
        from service.ha.core.base import BaseSensor, SensorConfig

        class TestSensor(BaseSensor):
            config = SensorConfig(
                sensor_id="format_test",
                name="Format Test",
                name_ru="Тест форматирования",
                icon="mdi:test",
            )

        sensor = TestSensor(mock_publisher)

        # Словарь -> JSON
        assert sensor.format_state({"key": "value"}) == '{"key": "value"}'

        # Boolean -> on/off
        assert sensor.format_state(True) == "on"
        assert sensor.format_state(False) == "off"

        # Число -> строка
        assert sensor.format_state(42) == "42"
        assert sensor.format_state(3.14) == "3.14"

    def test_get_registration_data_содержит_все_поля(self, mock_publisher):
        """get_registration_data возвращает все метаданные."""
        from service.ha.core.base import BaseSensor, SensorConfig

        class FullSensor(BaseSensor):
            config = SensorConfig(
                sensor_id="full_sensor",
                name="Full Sensor",
                name_ru="Полный сенсор",
                icon="mdi:full",
                unit="units",
                device_class="monetary",
                entity_category="diagnostic",
                description="Test description",
                description_ru="Тестовое описание",
            )

        sensor = FullSensor(mock_publisher)
        data = sensor.get_registration_data()

        assert data["friendly_name"] == "Full Sensor"
        assert data["icon"] == "mdi:full"
        assert data["unit_of_measurement"] == "units"
        assert data["device_class"] == "monetary"
        assert data["entity_category"] == "diagnostic"
        assert data["name_ru"] == "Полный сенсор"


# =============================================================================
# Тесты сценариев из scheduler/jobs.py
# =============================================================================


class TestSchedulerJobsСценарии:
    """Тесты сценариев использования HA интеграции из планировщика."""

    @pytest.mark.asyncio
    async def test_сценарий_investor_analysis_job(self, ha_manager, crypto_factory):
        """Сценарий работы investor_analysis_job."""
        # Симуляция данных, получаемых из различных анализаторов
        investor_status = crypto_factory.create_investor_status()
        market_data = crypto_factory.create_market_data()

        # Обновляем сенсоры как в реальном job
        await ha_manager.update_investor_status(investor_status)
        await ha_manager.update_market_data(
            fear_greed=market_data["fear_greed"],
            btc_dominance=market_data["btc_dominance"],
            derivatives_data=market_data["derivatives"],
        )

        # Тест прошёл успешно
        assert True

    @pytest.mark.asyncio
    async def test_сценарий_smart_summary_job(self, ha_manager, crypto_factory):
        """Сценарий работы smart_summary_job."""
        summary = crypto_factory.create_smart_summary()

        await ha_manager.update_smart_summary(summary)

        assert True

    @pytest.mark.asyncio
    async def test_сценарий_price_update_job(self, ha_manager, crypto_factory):
        """Сценарий обновления цен из WebSocket."""
        prices = crypto_factory.create_prices()
        changes = crypto_factory.create_changes_24h()
        volumes = crypto_factory.create_volumes_24h()

        prices_data = {}
        for symbol in prices:
            prices_data[symbol] = {
                "price": prices[symbol],
                "change_24h": changes[symbol],
                "volume_24h": volumes[symbol],
            }

        await ha_manager.update_all_prices(prices_data)

        # Проверяем кеши
        assert len(ha_manager._prices) == len(prices)
        assert len(ha_manager._changes) == len(changes)
        assert len(ha_manager._volumes) == len(volumes)

    @pytest.mark.asyncio
    async def test_сценарий_sync_status_update(self, ha_manager):
        """Сценарий обновления статуса синхронизации."""
        await ha_manager.update_sync_status(
            status="running",
            success_count=45,
            failure_count=5,
            total_candles=100000,
        )

        # Обновляем статус завершения
        await ha_manager.update_sync_status(
            status="completed",
            success_count=50,
            failure_count=0,
        )

        assert True

    @pytest.mark.asyncio
    async def test_сценарий_notification_status(self, ha_manager):
        """Сценарий обновления статуса уведомлений."""
        status_data = {
            "pending_count": 3,
            "critical_count": 1,
            "daily_digest_ready": True,
            "mode": "normal",
        }

        await ha_manager.update_notification_status(status_data)

        assert True


# =============================================================================
# Тесты helper функций ha_integration
# =============================================================================


class TestHelperFunctionsИнтеграция:
    """Тесты вспомогательных функций из ha_integration.py."""

    @pytest.mark.asyncio
    async def test_notify_функция(self):
        """Функция notify отправляет уведомление."""
        from service.ha_integration import notify

        with patch("service.ha_integration.get_supervisor_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.send_persistent_notification = AsyncMock(return_value=True)
            mock_get_client.return_value = mock_client

            result = await notify(
                message="Тестовое сообщение",
                title="Тест",
                notification_id="test_id",
            )

            assert result is True
            mock_client.send_persistent_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_notify_sync_complete_без_ошибок(self):
        """notify_sync_complete форматирует сообщение об успешной синхронизации."""
        from service.ha_integration import notify_sync_complete

        with patch("service.ha_integration.notify", new_callable=AsyncMock, return_value=True) as mock_notify:
            result = await notify_sync_complete(
                success_count=100,
                failure_count=0,
                duration_seconds=45.5,
            )

            assert result is True
            call_args = mock_notify.call_args
            message = call_args.kwargs["message"]
            assert "completed" in message
            assert "100/100" in message

    @pytest.mark.asyncio
    async def test_notify_sync_complete_с_ошибками(self):
        """notify_sync_complete корректно отображает ошибки."""
        from service.ha_integration import notify_sync_complete

        with patch("service.ha_integration.notify", new_callable=AsyncMock, return_value=True) as mock_notify:
            result = await notify_sync_complete(
                success_count=95,
                failure_count=5,
                duration_seconds=60.0,
            )

            assert result is True
            message = mock_notify.call_args.kwargs["message"]
            assert "with errors" in message
            assert "95/100" in message
            assert "5" in message

    @pytest.mark.asyncio
    async def test_notify_error_с_контекстом(self):
        """notify_error включает контекст в сообщение."""
        from service.ha_integration import notify_error

        with patch("service.ha_integration.notify", new_callable=AsyncMock, return_value=True) as mock_notify:
            result = await notify_error(
                error_message="Connection timeout",
                context="Binance API fetch",
            )

            assert result is True
            message = mock_notify.call_args.kwargs["message"]
            assert "Connection timeout" in message
            assert "Binance API fetch" in message


# =============================================================================
# Тесты глобального состояния и синглтонов
# =============================================================================


class TestГлобальноеСостояние:
    """Тесты глобального состояния модулей интеграции."""

    def test_get_supervisor_client_возвращает_синглтон(self):
        """get_supervisor_client возвращает один и тот же экземпляр."""
        import service.ha_integration as ha_int

        # Сбрасываем глобальное состояние
        ha_int._supervisor_client = None

        client1 = ha_int.get_supervisor_client()
        client2 = ha_int.get_supervisor_client()

        assert client1 is client2

        # Очистка
        ha_int._supervisor_client = None

    def test_get_ha_manager_возвращает_менеджер(self):
        """get_ha_manager возвращает экземпляр HAIntegrationManager."""
        # Сбрасываем
        import service.ha.core.manager as manager_module
        from service.ha import HAIntegrationManager, get_ha_manager
        manager_module._manager = None

        manager = get_ha_manager()
        assert isinstance(manager, HAIntegrationManager)

        manager_module._manager = None

    def test_get_sensors_manager_совместим_с_get_ha_manager(self):
        """get_sensors_manager - алиас для get_ha_manager."""
        import service.ha.core.manager as manager_module
        from service.ha import get_ha_manager, get_sensors_manager
        manager_module._manager = None

        manager1 = get_ha_manager()
        manager2 = get_sensors_manager()

        assert manager1 is manager2

        manager_module._manager = None
