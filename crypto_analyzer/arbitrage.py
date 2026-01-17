"""
Arbitrage Scanner - Поиск арбитражных возможностей

Типы арбитража:
- CEX price comparison (межбиржевой)
- Triangular arbitrage (внутри одной биржи)
- Spot-Futures basis (базис)
- Funding rate arbitrage

Источники:
- Binance
- Bybit
- OKX (placeholder)
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime

import aiohttp
from database import CryptoDatabase, get_database

logger = logging.getLogger(__name__)


# API Endpoints
BINANCE_SPOT_URL = "https://api.binance.com/api/v3"
BINANCE_FUTURES_URL = "https://fapi.binance.com/fapi/v1"
BYBIT_URL = "https://api.bybit.com/v5"


@dataclass
class ArbitrageOpportunity:
    """Арбитражная возможность"""

    type: str  # 'cex', 'triangular', 'basis', 'funding'
    symbol: str

    # Детали
    buy_exchange: str = ""
    sell_exchange: str = ""
    buy_price: float = 0.0
    sell_price: float = 0.0

    # Профит
    spread_pct: float = 0.0
    estimated_profit_pct: float = 0.0  # После комиссий

    # Дополнительно
    details: dict = field(default_factory=dict)

    # Метаданные
    timestamp: int = 0
    is_actionable: bool = False  # Можно ли реально использовать

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "symbol": self.symbol,
            "buy_exchange": self.buy_exchange,
            "sell_exchange": self.sell_exchange,
            "buy_price": self.buy_price,
            "sell_price": self.sell_price,
            "spread_pct": round(self.spread_pct, 4),
            "estimated_profit_pct": round(self.estimated_profit_pct, 4),
            "is_actionable": self.is_actionable,
            "details": self.details,
            "timestamp": self.timestamp,
        }

    def get_description_ru(self) -> str:
        """Описание на русском"""
        if self.type == "cex":
            return (
                f"💱 **Межбиржевой арбитраж: {self.symbol}**\n"
                f"Купить на {self.buy_exchange}: ${self.buy_price:,.2f}\n"
                f"Продать на {self.sell_exchange}: ${self.sell_price:,.2f}\n"
                f"Спред: {self.spread_pct:.2f}%\n"
                f"Профит после комиссий: ~{self.estimated_profit_pct:.2f}%"
            )
        elif self.type == "basis":
            return (
                f"📊 **Базисный арбитраж: {self.symbol}**\n"
                f"Spot: ${self.buy_price:,.2f}\n"
                f"Futures: ${self.sell_price:,.2f}\n"
                f"Базис: {self.spread_pct:.2f}%\n"
                f"Годовая доходность: ~{self.estimated_profit_pct:.2f}%"
            )
        elif self.type == "funding":
            funding = self.details.get("funding_rate", 0)
            return (
                f"💰 **Funding Rate арбитраж: {self.symbol}**\n"
                f"Funding Rate: {funding:.4f}%\n"
                f"Годовая доходность: ~{self.estimated_profit_pct:.2f}%\n"
                f"Стратегия: {self.details.get('strategy', 'N/A')}"
            )
        else:
            return f"🔄 Арбитраж {self.type}: {self.symbol} - {self.spread_pct:.2f}%"


@dataclass
class ArbitrageScan:
    """Результаты сканирования"""

    timestamp: int

    # Возможности по типам
    cex_opportunities: list[ArbitrageOpportunity] = field(default_factory=list)
    basis_opportunities: list[ArbitrageOpportunity] = field(default_factory=list)
    funding_opportunities: list[ArbitrageOpportunity] = field(default_factory=list)

    # Лучшие возможности
    best_opportunities: list[ArbitrageOpportunity] = field(default_factory=list)

    # Статистика
    total_scanned: int = 0
    actionable_count: int = 0

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "statistics": {
                "total_scanned": self.total_scanned,
                "actionable_count": self.actionable_count,
            },
            "best_opportunities": [o.to_dict() for o in self.best_opportunities[:10]],
            "by_type": {
                "cex": [o.to_dict() for o in self.cex_opportunities[:5]],
                "basis": [o.to_dict() for o in self.basis_opportunities[:5]],
                "funding": [o.to_dict() for o in self.funding_opportunities[:5]],
            },
        }

    def get_summary_ru(self) -> str:
        """Резюме на русском"""
        parts = [
            "🔍 **Arbitrage Scanner**",
            f"Проверено пар: {self.total_scanned}",
            f"Найдено возможностей: {self.actionable_count}",
            "",
        ]

        if self.best_opportunities:
            parts.append("**🏆 Лучшие возможности:**")
            for opp in self.best_opportunities[:5]:
                parts.append(f"• {opp.symbol}: {opp.spread_pct:.2f}% ({opp.type})")
        else:
            parts.append("❌ Значимых возможностей не найдено")

        return "\n".join(parts)


class ArbitrageScanner:
    """Сканер арбитражных возможностей"""

    # Пороги для "actionable" арбитража
    MIN_CEX_SPREAD = 0.3  # 0.3% минимум для межбиржевого
    MIN_BASIS_SPREAD = 0.1  # 0.1% для базиса
    MIN_FUNDING_ANNUAL = 10.0  # 10% годовых для funding

    # Комиссии (примерные)
    TRADING_FEE = 0.1  # 0.1% на сделку
    WITHDRAWAL_FEE_PCT = 0.1  # Примерно 0.1% на вывод

    def __init__(self, db: CryptoDatabase | None = None):
        self.db = db or get_database()
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Получить HTTP сессию"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self):
        """Закрыть сессию"""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _fetch_binance_spot_prices(self) -> dict[str, float]:
        """Получить спот цены с Binance"""
        session = await self._get_session()

        try:
            async with session.get(f"{BINANCE_SPOT_URL}/ticker/price") as response:
                if response.status != 200:
                    return {}

                data = await response.json()
                return {
                    item["symbol"]: float(item["price"])
                    for item in data
                    if item["symbol"].endswith("USDT")
                }

        except Exception as e:
            logger.error(f"Binance spot error: {e}")
            return {}

    async def _fetch_binance_futures_prices(self) -> dict[str, float]:
        """Получить фьючерсные цены с Binance"""
        session = await self._get_session()

        try:
            async with session.get(f"{BINANCE_FUTURES_URL}/ticker/price") as response:
                if response.status != 200:
                    return {}

                data = await response.json()
                return {item["symbol"]: float(item["price"]) for item in data}

        except Exception as e:
            logger.error(f"Binance futures error: {e}")
            return {}

    async def _fetch_binance_funding_rates(self) -> dict[str, float]:
        """Получить funding rates с Binance"""
        session = await self._get_session()

        try:
            async with session.get(f"{BINANCE_FUTURES_URL}/premiumIndex") as response:
                if response.status != 200:
                    return {}

                data = await response.json()
                return {item["symbol"]: float(item["lastFundingRate"]) for item in data}

        except Exception as e:
            logger.error(f"Binance funding error: {e}")
            return {}

    async def _fetch_bybit_spot_prices(self) -> dict[str, float]:
        """Получить спот цены с Bybit"""
        session = await self._get_session()

        try:
            url = f"{BYBIT_URL}/market/tickers"
            params = {"category": "spot"}

            async with session.get(url, params=params) as response:
                if response.status != 200:
                    return {}

                data = await response.json()

                if data.get("retCode") != 0:
                    return {}

                return {
                    item["symbol"]: float(item["lastPrice"])
                    for item in data.get("result", {}).get("list", [])
                    if item["symbol"].endswith("USDT")
                }

        except Exception as e:
            logger.error(f"Bybit spot error: {e}")
            return {}

    async def scan_cex_arbitrage(self, symbols: list[str] = None) -> list[ArbitrageOpportunity]:
        """
        Сканировать межбиржевой арбитраж

        Args:
            symbols: Список символов для проверки

        Returns:
            Список возможностей
        """
        # Получаем цены параллельно
        tasks = [
            self._fetch_binance_spot_prices(),
            self._fetch_bybit_spot_prices(),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        binance_prices = results[0] if not isinstance(results[0], Exception) else {}
        bybit_prices = results[1] if not isinstance(results[1], Exception) else {}

        opportunities = []

        # Находим общие символы
        common_symbols = set(binance_prices.keys()) & set(bybit_prices.keys())

        if symbols:
            symbols_upper = [f"{s.upper()}USDT" for s in symbols]
            common_symbols = common_symbols & set(symbols_upper)

        for symbol in common_symbols:
            binance_price = binance_prices[symbol]
            bybit_price = bybit_prices[symbol]

            if binance_price <= 0 or bybit_price <= 0:
                continue

            # Считаем спред
            if binance_price < bybit_price:
                spread_pct = (bybit_price - binance_price) / binance_price * 100
                buy_exchange = "Binance"
                sell_exchange = "Bybit"
                buy_price = binance_price
                sell_price = bybit_price
            else:
                spread_pct = (binance_price - bybit_price) / bybit_price * 100
                buy_exchange = "Bybit"
                sell_exchange = "Binance"
                buy_price = bybit_price
                sell_price = binance_price

            # Оцениваем профит после комиссий
            total_fees = self.TRADING_FEE * 2 + self.WITHDRAWAL_FEE_PCT
            estimated_profit = spread_pct - total_fees

            is_actionable = estimated_profit > self.MIN_CEX_SPREAD

            opp = ArbitrageOpportunity(
                type="cex",
                symbol=symbol.replace("USDT", ""),
                buy_exchange=buy_exchange,
                sell_exchange=sell_exchange,
                buy_price=buy_price,
                sell_price=sell_price,
                spread_pct=spread_pct,
                estimated_profit_pct=estimated_profit,
                timestamp=int(datetime.now().timestamp() * 1000),
                is_actionable=is_actionable,
            )

            if spread_pct > 0.1:  # Минимальный спред для включения
                opportunities.append(opp)

        # Сортируем по профиту
        opportunities.sort(key=lambda x: x.estimated_profit_pct, reverse=True)

        return opportunities

    async def scan_basis_arbitrage(self, symbols: list[str] = None) -> list[ArbitrageOpportunity]:
        """
        Сканировать базисный арбитраж (spot vs futures)

        Args:
            symbols: Список символов для проверки

        Returns:
            Список возможностей
        """
        # Получаем цены
        tasks = [
            self._fetch_binance_spot_prices(),
            self._fetch_binance_futures_prices(),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        spot_prices = results[0] if not isinstance(results[0], Exception) else {}
        futures_prices = results[1] if not isinstance(results[1], Exception) else {}

        opportunities = []

        # Находим общие символы
        common_symbols = set(spot_prices.keys()) & set(futures_prices.keys())

        if symbols:
            symbols_upper = [f"{s.upper()}USDT" for s in symbols]
            common_symbols = common_symbols & set(symbols_upper)

        for symbol in common_symbols:
            spot_price = spot_prices[symbol]
            futures_price = futures_prices[symbol]

            if spot_price <= 0 or futures_price <= 0:
                continue

            # Базис = (futures - spot) / spot * 100
            basis_pct = (futures_price - spot_price) / spot_price * 100

            # Годовая доходность (предполагаем квартальные фьючерсы ~ 90 дней)
            days_to_expiry = 30  # Примерно
            annual_yield = basis_pct * (365 / days_to_expiry)

            is_actionable = abs(basis_pct) > self.MIN_BASIS_SPREAD

            opp = ArbitrageOpportunity(
                type="basis",
                symbol=symbol.replace("USDT", ""),
                buy_exchange="Binance Spot",
                sell_exchange="Binance Futures",
                buy_price=spot_price if basis_pct > 0 else futures_price,
                sell_price=futures_price if basis_pct > 0 else spot_price,
                spread_pct=abs(basis_pct),
                estimated_profit_pct=abs(annual_yield),
                timestamp=int(datetime.now().timestamp() * 1000),
                is_actionable=is_actionable,
                details={
                    "basis_direction": "contango" if basis_pct > 0 else "backwardation",
                    "annual_yield_pct": annual_yield,
                },
            )

            if abs(basis_pct) > 0.05:
                opportunities.append(opp)

        opportunities.sort(key=lambda x: x.estimated_profit_pct, reverse=True)

        return opportunities

    async def scan_funding_arbitrage(self, symbols: list[str] = None) -> list[ArbitrageOpportunity]:
        """
        Сканировать funding rate арбитраж

        Args:
            symbols: Список символов для проверки

        Returns:
            Список возможностей
        """
        # Получаем funding rates и spot цены
        tasks = [
            self._fetch_binance_funding_rates(),
            self._fetch_binance_spot_prices(),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        funding_rates = results[0] if not isinstance(results[0], Exception) else {}
        spot_prices = results[1] if not isinstance(results[1], Exception) else {}

        opportunities = []

        for symbol, funding_rate in funding_rates.items():
            # Funding rate в процентах (уже в десятичном формате от API)
            funding_pct = funding_rate * 100

            # Годовая доходность (funding каждые 8 часов = 3 раза в день)
            annual_yield = funding_pct * 3 * 365

            # Фильтруем по списку если задан
            if symbols:
                symbol_base = symbol.replace("USDT", "")
                if symbol_base not in [s.upper() for s in symbols]:
                    continue

            spot_price = spot_prices.get(symbol, 0)

            # Определяем стратегию
            if funding_pct > 0:
                # Положительный funding - шортим perpetual, лонгим spot
                strategy = "Short perpetual + Long spot"
                strategy_ru = "Шорт перпетуал + Лонг спот"
            else:
                # Отрицательный funding - лонгим perpetual, шортим spot (сложнее)
                strategy = "Long perpetual + Short spot (requires margin)"
                strategy_ru = "Лонг перпетуал + Шорт спот (нужна маржа)"

            is_actionable = abs(annual_yield) > self.MIN_FUNDING_ANNUAL

            opp = ArbitrageOpportunity(
                type="funding",
                symbol=symbol.replace("USDT", ""),
                buy_exchange="Binance",
                sell_exchange="Binance",
                buy_price=spot_price,
                sell_price=spot_price,
                spread_pct=abs(funding_pct),
                estimated_profit_pct=abs(annual_yield),
                timestamp=int(datetime.now().timestamp() * 1000),
                is_actionable=is_actionable,
                details={
                    "funding_rate": funding_pct,
                    "annual_yield": annual_yield,
                    "strategy": strategy,
                    "strategy_ru": strategy_ru,
                    "funding_direction": "positive" if funding_pct > 0 else "negative",
                },
            )

            if abs(annual_yield) > 5:  # Минимум 5% годовых
                opportunities.append(opp)

        opportunities.sort(key=lambda x: x.estimated_profit_pct, reverse=True)

        return opportunities

    async def scan_all(self, symbols: list[str] = None) -> ArbitrageScan:
        """
        Полное сканирование всех типов арбитража

        Args:
            symbols: Список символов для проверки

        Returns:
            ArbitrageScan
        """
        scan = ArbitrageScan(timestamp=int(datetime.now().timestamp() * 1000))

        # Сканируем параллельно
        tasks = [
            self.scan_cex_arbitrage(symbols),
            self.scan_basis_arbitrage(symbols),
            self.scan_funding_arbitrage(symbols),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # CEX арбитраж
        if not isinstance(results[0], Exception):
            scan.cex_opportunities = results[0]

        # Базис
        if not isinstance(results[1], Exception):
            scan.basis_opportunities = results[1]

        # Funding
        if not isinstance(results[2], Exception):
            scan.funding_opportunities = results[2]

        # Собираем все возможности
        all_opportunities = (
            scan.cex_opportunities + scan.basis_opportunities + scan.funding_opportunities
        )

        # Статистика
        scan.total_scanned = len(all_opportunities)
        scan.actionable_count = sum(1 for o in all_opportunities if o.is_actionable)

        # Лучшие возможности (только actionable)
        actionable = [o for o in all_opportunities if o.is_actionable]
        actionable.sort(key=lambda x: x.estimated_profit_pct, reverse=True)
        scan.best_opportunities = actionable[:10]

        return scan


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import json

    logging.basicConfig(level=logging.INFO)

    async def main():
        scanner = ArbitrageScanner()

        try:
            print("Scanning arbitrage opportunities...")
            scan = await scanner.scan_all(symbols=["BTC", "ETH", "SOL"])

            print("\n" + "=" * 60)
            print("ARBITRAGE SCAN RESULTS")
            print("=" * 60)
            print(json.dumps(scan.to_dict(), indent=2, ensure_ascii=False))

            print("\n" + "=" * 60)
            print("SUMMARY (RU)")
            print("=" * 60)
            print(scan.get_summary_ru())

            # Детали лучших возможностей
            if scan.best_opportunities:
                print("\n" + "=" * 60)
                print("BEST OPPORTUNITIES DETAILS")
                print("=" * 60)
                for opp in scan.best_opportunities[:3]:
                    print(opp.get_description_ru())
                    print()

        finally:
            await scanner.close()

    asyncio.run(main())
