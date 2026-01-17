"""
Config Loader - Загрузка конфигурации и API ключей

Приоритет загрузки API ключей:
1. Environment variables (WHALE_ALERT_API_KEY, etc.)
2. Home Assistant secrets.yaml
3. Значения из config.yaml
"""

import logging
import os
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Пути
BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config.yaml"
HA_CONFIG_DIR = Path("/config")
SECRETS_FILE = HA_CONFIG_DIR / "secrets.yaml"

# Маппинг API ключей: config_key -> (env_var, secrets_key)
API_KEY_MAPPING = {
    "whale_alert": ("WHALE_ALERT_API_KEY", "whale_alert_api_key"),
    "etherscan": ("ETHERSCAN_API_KEY", "etherscan_api_key"),
    "cryptopanic": ("CRYPTOPANIC_API_KEY", "cryptopanic_api_key"),
    "glassnode": ("GLASSNODE_API_KEY", "glassnode_api_key"),
    "lunarcrush": ("LUNARCRUSH_API_KEY", "lunarcrush_api_key"),
    "coinglass": ("COINGLASS_API_KEY", "coinglass_api_key"),
    "santiment": ("SANTIMENT_API_KEY", "santiment_api_key"),
}


class ConfigLoader:
    """Загрузчик конфигурации"""

    def __init__(self):
        self._config: dict | None = None
        self._secrets: dict | None = None
        self._api_keys: dict | None = None

    def _load_yaml(self, path: Path) -> dict:
        """Загрузить YAML файл"""
        try:
            if path.exists():
                with open(path, encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning(f"Не удалось загрузить {path}: {e}")
        return {}

    @property
    def config(self) -> dict:
        """Получить конфигурацию"""
        if self._config is None:
            self._config = self._load_yaml(CONFIG_FILE)
        return self._config

    @property
    def secrets(self) -> dict:
        """Получить секреты Home Assistant"""
        if self._secrets is None:
            self._secrets = self._load_yaml(SECRETS_FILE)
        return self._secrets

    def get_api_key(self, key_name: str) -> str | None:
        """
        Получить API ключ с приоритетом:
        1. Environment variable
        2. HA secrets.yaml
        3. config.yaml

        Args:
            key_name: Имя ключа (whale_alert, etherscan, etc.)

        Returns:
            API ключ или None
        """
        if key_name not in API_KEY_MAPPING:
            # Попробовать напрямую из config
            return self.config.get("api_keys", {}).get(key_name)

        env_var, secrets_key = API_KEY_MAPPING[key_name]

        # 1. Environment variable
        env_value = os.environ.get(env_var)
        if env_value and not env_value.startswith("YOUR_"):
            return env_value

        # 2. HA secrets.yaml
        secrets_value = self.secrets.get(secrets_key)
        if secrets_value and not secrets_value.startswith("YOUR_"):
            return secrets_value

        # 3. config.yaml
        config_value = self.config.get("api_keys", {}).get(key_name)
        if config_value and not config_value.startswith("YOUR_"):
            return config_value

        return None

    @property
    def api_keys(self) -> dict[str, str | None]:
        """Получить все API ключи"""
        if self._api_keys is None:
            self._api_keys = {key: self.get_api_key(key) for key in API_KEY_MAPPING.keys()}
        return self._api_keys

    def get(self, path: str, default: Any = None) -> Any:
        """
        Получить значение из конфигурации по пути

        Args:
            path: Путь через точку (например: 'technical_analysis.rsi_period')
            default: Значение по умолчанию

        Returns:
            Значение или default
        """
        value = self.config
        for key in path.split("."):
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return default
            if value is None:
                return default
        return value

    def get_coins(self, include_custom: bool = True) -> list:
        """
        Получить список монет для отслеживания

        Args:
            include_custom: Включать пользовательские монеты

        Returns:
            Список символов монет
        """
        coins = []

        # Primary coins
        primary = self.config.get("coins", {}).get("primary", [])
        for coin in primary:
            if isinstance(coin, dict):
                coins.append(coin.get("symbol"))
            elif isinstance(coin, str):
                coins.append(coin)

        # Secondary coins
        secondary = self.config.get("coins", {}).get("secondary", [])
        for coin in secondary:
            if isinstance(coin, dict):
                coins.append(coin.get("symbol"))
            elif isinstance(coin, str):
                coins.append(coin)

        return [c for c in coins if c]

    def get_ollama_url(self) -> str:
        """Получить URL Ollama"""
        ollama = self.config.get("ollama", {})
        host = ollama.get("host", "192.168.1.2")
        port = ollama.get("port", 11434)
        return f"http://{host}:{port}"

    def get_ollama_model(self) -> str:
        """Получить модель Ollama"""
        return self.config.get("ollama", {}).get("model", "llama3.2")

    def has_api_key(self, key_name: str) -> bool:
        """Проверить наличие API ключа"""
        key = self.get_api_key(key_name)
        return key is not None and len(key) > 10


# Singleton instance
_config_loader: ConfigLoader | None = None


def get_config() -> ConfigLoader:
    """Получить singleton экземпляр ConfigLoader"""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader


# Удобные функции
def get_api_key(key_name: str) -> str | None:
    """Получить API ключ"""
    return get_config().get_api_key(key_name)


def has_api_key(key_name: str) -> bool:
    """Проверить наличие API ключа"""
    return get_config().has_api_key(key_name)


# ============================================================================
# CLI - проверка конфигурации
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    config = get_config()

    print("=" * 60)
    print("CRYPTO ANALYZER - CONFIG CHECK")
    print("=" * 60)

    print("\n📁 Config files:")
    print(f"  Config: {CONFIG_FILE} ({'✅' if CONFIG_FILE.exists() else '❌'})")
    print(f"  Secrets: {SECRETS_FILE} ({'✅' if SECRETS_FILE.exists() else '❌'})")

    print("\n🔑 API Keys Status:")
    for key_name, (env_var, secrets_key) in API_KEY_MAPPING.items():
        has_key = config.has_api_key(key_name)
        status = "✅ Настроен" if has_key else "❌ Не настроен"
        print(f"  {key_name:15} {status}")
        if not has_key:
            print(f"    → env: {env_var}")
            print(f"    → secrets: {secrets_key}")

    print("\n🪙 Coins to track:")
    coins = config.get_coins()
    print(f"  {', '.join(coins)}")

    print("\n🤖 Ollama:")
    print(f"  URL: {config.get_ollama_url()}")
    print(f"  Model: {config.get_ollama_model()}")

    print("\n📊 Technical Analysis Settings:")
    print(f"  RSI Period: {config.get('technical_analysis.rsi_period', 14)}")
    print(f"  RSI Oversold: {config.get('technical_analysis.rsi_oversold', 30)}")
    print(f"  RSI Overbought: {config.get('technical_analysis.rsi_overbought', 70)}")

    print()
