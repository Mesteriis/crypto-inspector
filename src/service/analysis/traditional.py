"""
Traditional Finance Tracker.

Отслеживает классические активы:
- Золото (XAU/USD)
- Серебро (XAG/USD)
- S&P 500
- EUR/USD
- DXY (Dollar Index)
- Нефть (Brent, WTI)

Источник: Yahoo Finance API (yfinance)
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum

import httpx

logger = logging.getLogger(__name__)


class AssetClass(Enum):
    """Класс актива."""

    METAL = "metal"
    INDEX = "index"
    FOREX = "forex"
    COMMODITY = "commodity"


@dataclass
class TraditionalAsset:
    """Традиционный актив."""

    symbol: str
    name: str
    name_ru: str
    asset_class: AssetClass
    price: float = 0.0
    change_24h: float = 0.0
    change_percent: float = 0.0
    high_24h: float = 0.0
    low_24h: float = 0.0
    volume: float = 0.0
    last_updated: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Yahoo Finance ticker
    yahoo_ticker: str = ""

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "name_ru": self.name_ru,
            "asset_class": self.asset_class.value,
            "price": round(self.price, 2),
            "change_24h": round(self.change_24h, 2),
            "change_percent": round(self.change_percent, 2),
            "high_24h": round(self.high_24h, 2),
            "low_24h": round(self.low_24h, 2),
            "volume": self.volume,
            "last_updated": self.last_updated.isoformat(),
        }


@dataclass
class TraditionalFinanceStatus:
    """Полный статус традиционных финансов."""

    # Металлы
    gold: TraditionalAsset | None = None
    silver: TraditionalAsset | None = None
    platinum: TraditionalAsset | None = None

    # Индексы
    sp500: TraditionalAsset | None = None
    nasdaq: TraditionalAsset | None = None
    dji: TraditionalAsset | None = None  # Dow Jones
    dax: TraditionalAsset | None = None  # German DAX
    vix: TraditionalAsset | None = None  # VIX Volatility Index

    # Форекс
    eur_usd: TraditionalAsset | None = None
    gbp_usd: TraditionalAsset | None = None
    usd_jpy: TraditionalAsset | None = None
    dxy: TraditionalAsset | None = None  # Dollar Index

    # Commodities
    oil_brent: TraditionalAsset | None = None
    oil_wti: TraditionalAsset | None = None
    natural_gas: TraditionalAsset | None = None

    # Treasury Bonds
    treasury_2y: TraditionalAsset | None = None
    treasury_10y: TraditionalAsset | None = None

    # Метаданные
    last_updated: datetime = field(default_factory=lambda: datetime.now(UTC))
    status: str = "ok"
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "metals": {
                "gold": self.gold.to_dict() if self.gold else None,
                "silver": self.silver.to_dict() if self.silver else None,
                "platinum": self.platinum.to_dict() if self.platinum else None,
            },
            "indices": {
                "sp500": self.sp500.to_dict() if self.sp500 else None,
                "nasdaq": self.nasdaq.to_dict() if self.nasdaq else None,
                "dji": self.dji.to_dict() if self.dji else None,
                "dax": self.dax.to_dict() if self.dax else None,
                "vix": self.vix.to_dict() if self.vix else None,
            },
            "forex": {
                "eur_usd": self.eur_usd.to_dict() if self.eur_usd else None,
                "gbp_usd": self.gbp_usd.to_dict() if self.gbp_usd else None,
                "usd_jpy": self.usd_jpy.to_dict() if self.usd_jpy else None,
                "dxy": self.dxy.to_dict() if self.dxy else None,
            },
            "commodities": {
                "oil_brent": self.oil_brent.to_dict() if self.oil_brent else None,
                "oil_wti": self.oil_wti.to_dict() if self.oil_wti else None,
                "natural_gas": self.natural_gas.to_dict() if self.natural_gas else None,
            },
            "treasury": {
                "treasury_2y": self.treasury_2y.to_dict() if self.treasury_2y else None,
                "treasury_10y": self.treasury_10y.to_dict() if self.treasury_10y else None,
            },
            "last_updated": self.last_updated.isoformat(),
            "status": self.status,
            "error": self.error,
        }


# Конфигурация активов
ASSETS_CONFIG = {
    # Металлы
    "gold": {
        "yahoo": "GC=F",
        "name": "Gold",
        "name_ru": "Золото",
        "class": AssetClass.METAL,
    },
    "silver": {
        "yahoo": "SI=F",
        "name": "Silver",
        "name_ru": "Серебро",
        "class": AssetClass.METAL,
    },
    "platinum": {
        "yahoo": "PL=F",
        "name": "Platinum",
        "name_ru": "Платина",
        "class": AssetClass.METAL,
    },
    # Индексы
    "sp500": {
        "yahoo": "^GSPC",
        "name": "S&P 500",
        "name_ru": "S&P 500",
        "class": AssetClass.INDEX,
    },
    "nasdaq": {
        "yahoo": "^IXIC",
        "name": "NASDAQ",
        "name_ru": "NASDAQ",
        "class": AssetClass.INDEX,
    },
    "dji": {
        "yahoo": "^DJI",
        "name": "Dow Jones",
        "name_ru": "Dow Jones",
        "class": AssetClass.INDEX,
    },
    "dax": {
        "yahoo": "^GDAXI",
        "name": "DAX",
        "name_ru": "DAX",
        "class": AssetClass.INDEX,
    },
    "vix": {
        "yahoo": "^VIX",
        "name": "VIX",
        "name_ru": "Индекс VIX",
        "class": AssetClass.INDEX,
    },
    # Форекс
    "eur_usd": {
        "yahoo": "EURUSD=X",
        "name": "EUR/USD",
        "name_ru": "Евро/Доллар",
        "class": AssetClass.FOREX,
    },
    "gbp_usd": {
        "yahoo": "GBPUSD=X",
        "name": "GBP/USD",
        "name_ru": "Фунт/Доллар",
        "class": AssetClass.FOREX,
    },
    "usd_jpy": {
        "yahoo": "USDJPY=X",
        "name": "USD/JPY",
        "name_ru": "Доллар/Йена",
        "class": AssetClass.FOREX,
    },
    "dxy": {
        "yahoo": "DX-Y.NYB",
        "name": "Dollar Index",
        "name_ru": "Индекс доллара",
        "class": AssetClass.FOREX,
    },
    # Commodities
    "oil_brent": {
        "yahoo": "BZ=F",
        "name": "Brent Oil",
        "name_ru": "Нефть Brent",
        "class": AssetClass.COMMODITY,
    },
    "oil_wti": {
        "yahoo": "CL=F",
        "name": "WTI Oil",
        "name_ru": "Нефть WTI",
        "class": AssetClass.COMMODITY,
    },
    "natural_gas": {
        "yahoo": "NG=F",
        "name": "Natural Gas",
        "name_ru": "Природный газ",
        "class": AssetClass.COMMODITY,
    },
    # Treasury Bonds
    "treasury_2y": {
        "yahoo": "^IRX",  # 13-week T-Bill rate (proxy for short-term)
        "name": "2Y Treasury",
        "name_ru": "Облигации 2г",
        "class": AssetClass.INDEX,
    },
    "treasury_10y": {
        "yahoo": "^TNX",  # 10-year Treasury yield
        "name": "10Y Treasury",
        "name_ru": "Облигации 10л",
        "class": AssetClass.INDEX,
    },
}


class TraditionalFinanceTracker:
    """
    Трекер традиционных финансов.

    Использует Yahoo Finance API для получения данных.
    """

    # Yahoo Finance API (через query1/query2)
    YAHOO_API_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

    def __init__(self):
        self._cache: dict[str, TraditionalAsset] = {}
        self._last_update: datetime | None = None
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            )
        return self._client

    async def fetch_asset(self, asset_id: str) -> TraditionalAsset | None:
        """
        Получить данные по одному активу.

        Args:
            asset_id: ID актива (gold, silver, sp500 и т.д.)

        Returns:
            TraditionalAsset или None при ошибке
        """
        if asset_id not in ASSETS_CONFIG:
            logger.warning(f"Unknown asset: {asset_id}")
            return None

        config = ASSETS_CONFIG[asset_id]
        yahoo_ticker = config["yahoo"]

        try:
            client = await self._get_client()

            # Yahoo Finance API
            url = self.YAHOO_API_URL.format(symbol=yahoo_ticker)
            params = {
                "interval": "1d",
                "range": "2d",
            }

            response = await client.get(url, params=params)

            if response.status_code != 200:
                logger.error(f"Yahoo API error for {asset_id}: {response.status_code}")
                return None

            data = response.json()

            # Парсим ответ Yahoo Finance
            result = data.get("chart", {}).get("result", [])
            if not result:
                logger.warning(f"No data for {asset_id}")
                return None

            quote = result[0]
            meta = quote.get("meta", {})
            indicators = quote.get("indicators", {}).get("quote", [{}])[0]

            # Текущая цена
            price = meta.get("regularMarketPrice", 0)
            prev_close = meta.get("previousClose", price)

            # Изменение
            change = price - prev_close if prev_close else 0
            change_pct = (change / prev_close * 100) if prev_close else 0

            # High/Low
            highs = indicators.get("high", [])
            lows = indicators.get("low", [])
            volumes = indicators.get("volume", [])

            high_24h = max(highs) if highs else price
            low_24h = min([l for l in lows if l]) if lows else price
            volume = volumes[-1] if volumes else 0

            asset = TraditionalAsset(
                symbol=asset_id.upper(),
                name=config["name"],
                name_ru=config["name_ru"],
                asset_class=config["class"],
                price=price,
                change_24h=change,
                change_percent=change_pct,
                high_24h=high_24h,
                low_24h=low_24h,
                volume=volume or 0,
                yahoo_ticker=yahoo_ticker,
                last_updated=datetime.now(UTC),
            )

            self._cache[asset_id] = asset
            return asset

        except Exception as e:
            logger.error(f"Error fetching {asset_id}: {e}")
            return self._cache.get(asset_id)

    async def fetch_all(self) -> TraditionalFinanceStatus:
        """
        Получить данные по всем активам.

        Returns:
            TraditionalFinanceStatus со всеми данными
        """
        status = TraditionalFinanceStatus()

        try:
            # Металлы
            status.gold = await self.fetch_asset("gold")
            status.silver = await self.fetch_asset("silver")
            status.platinum = await self.fetch_asset("platinum")

            # Индексы
            status.sp500 = await self.fetch_asset("sp500")
            status.nasdaq = await self.fetch_asset("nasdaq")
            status.dji = await self.fetch_asset("dji")
            status.dax = await self.fetch_asset("dax")
            status.vix = await self.fetch_asset("vix")

            # Форекс
            status.eur_usd = await self.fetch_asset("eur_usd")
            status.gbp_usd = await self.fetch_asset("gbp_usd")
            status.usd_jpy = await self.fetch_asset("usd_jpy")
            status.dxy = await self.fetch_asset("dxy")

            # Commodities
            status.oil_brent = await self.fetch_asset("oil_brent")
            status.oil_wti = await self.fetch_asset("oil_wti")
            status.natural_gas = await self.fetch_asset("natural_gas")

            # Treasury Bonds
            status.treasury_2y = await self.fetch_asset("treasury_2y")
            status.treasury_10y = await self.fetch_asset("treasury_10y")

            status.last_updated = datetime.now(UTC)
            status.status = "ok"
            self._last_update = datetime.now(UTC)

            logger.info("Traditional finance data updated")

        except Exception as e:
            logger.error(f"Error fetching traditional finance: {e}")
            status.status = "error"
            status.error = str(e)

        return status

    async def get_metals(self) -> dict:
        """Получить только металлы."""
        result = {}
        for asset_id in ["gold", "silver", "platinum"]:
            asset = await self.fetch_asset(asset_id)
            if asset:
                result[asset_id] = asset.to_dict()
        return result

    async def get_indices(self) -> dict:
        """Получить только индексы."""
        result = {}
        for asset_id in ["sp500", "nasdaq", "dji", "dax", "vix"]:
            asset = await self.fetch_asset(asset_id)
            if asset:
                result[asset_id] = asset.to_dict()
        return result

    async def get_forex(self) -> dict:
        """Получить только форекс."""
        result = {}
        for asset_id in ["eur_usd", "gbp_usd", "usd_jpy", "dxy"]:
            asset = await self.fetch_asset(asset_id)
            if asset:
                result[asset_id] = asset.to_dict()
        return result

    async def get_commodities(self) -> dict:
        """Получить только commodities."""
        result = {}
        for asset_id in ["oil_brent", "oil_wti", "natural_gas"]:
            asset = await self.fetch_asset(asset_id)
            if asset:
                result[asset_id] = asset.to_dict()
        return result

    def get_cached(self, asset_id: str) -> TraditionalAsset | None:
        """Получить закэшированные данные."""
        return self._cache.get(asset_id)

    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


# Global instance
_tracker: TraditionalFinanceTracker | None = None


def get_traditional_tracker() -> TraditionalFinanceTracker:
    """Get or create tracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = TraditionalFinanceTracker()
    return _tracker
