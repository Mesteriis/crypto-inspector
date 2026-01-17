"""
DeFi Tracker - Отслеживание стейкинга и DeFi

Функции:
- Мониторинг yields
- DefiLlama API интеграция
- Impermanent Loss калькулятор
- Risk alerts

Источники:
- DefiLlama API
- Direct protocol APIs (placeholder)
"""

import asyncio
import logging
import math
from dataclasses import dataclass, field
from datetime import datetime

import aiohttp
from database import CryptoDatabase, get_database

logger = logging.getLogger(__name__)


# API Endpoints
DEFILLAMA_URL = "https://yields.llama.fi"
DEFILLAMA_TVL_URL = "https://api.llama.fi"


@dataclass
class YieldPool:
    """DeFi пул с доходностью"""

    pool_id: str
    name: str
    symbol: str
    chain: str
    project: str

    # Доходность
    apy: float = 0.0
    apy_base: float = 0.0  # Базовая APY
    apy_reward: float = 0.0  # APY от наград

    # TVL
    tvl_usd: float = 0.0

    # Риски
    il_risk: str = "low"  # low, medium, high
    audit_score: int = 0  # 0-100

    # Метаданные
    stable_coin: bool = False
    exposure: list[str] = field(default_factory=list)  # Токены в пуле

    def to_dict(self) -> dict:
        return {
            "pool_id": self.pool_id,
            "name": self.name,
            "symbol": self.symbol,
            "chain": self.chain,
            "project": self.project,
            "apy": round(self.apy, 2),
            "apy_base": round(self.apy_base, 2),
            "apy_reward": round(self.apy_reward, 2),
            "tvl_usd": self.tvl_usd,
            "il_risk": self.il_risk,
            "audit_score": self.audit_score,
            "stable_coin": self.stable_coin,
            "exposure": self.exposure,
        }


@dataclass
class StakingPosition:
    """Позиция в стейкинге"""

    id: str
    pool_id: str
    pool_name: str
    chain: str

    # Позиция
    deposited_amount: float = 0.0
    deposited_usd: float = 0.0
    current_value_usd: float = 0.0

    # Награды
    rewards_earned: float = 0.0
    rewards_usd: float = 0.0

    # PnL
    pnl_usd: float = 0.0
    pnl_pct: float = 0.0

    # Impermanent Loss (для LP позиций)
    il_usd: float = 0.0
    il_pct: float = 0.0

    # Время
    entry_timestamp: int = 0
    days_staked: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "pool_id": self.pool_id,
            "pool_name": self.pool_name,
            "chain": self.chain,
            "deposited_amount": self.deposited_amount,
            "deposited_usd": self.deposited_usd,
            "current_value_usd": round(self.current_value_usd, 2),
            "rewards_earned": self.rewards_earned,
            "rewards_usd": round(self.rewards_usd, 2),
            "pnl_usd": round(self.pnl_usd, 2),
            "pnl_pct": round(self.pnl_pct, 2),
            "il_usd": round(self.il_usd, 2),
            "il_pct": round(self.il_pct, 2),
            "days_staked": self.days_staked,
        }


@dataclass
class DeFiSummary:
    """Сводка по DeFi"""

    timestamp: int

    # Топ пулы
    top_pools: list[YieldPool] = field(default_factory=list)

    # Позиции пользователя
    positions: list[StakingPosition] = field(default_factory=list)

    # Общая статистика
    total_deposited_usd: float = 0.0
    total_current_value_usd: float = 0.0
    total_rewards_usd: float = 0.0
    total_pnl_usd: float = 0.0
    total_pnl_pct: float = 0.0
    total_il_usd: float = 0.0

    # Риск-алерты
    risk_alerts: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "top_pools": [p.to_dict() for p in self.top_pools[:10]],
            "positions": [p.to_dict() for p in self.positions],
            "totals": {
                "deposited_usd": round(self.total_deposited_usd, 2),
                "current_value_usd": round(self.total_current_value_usd, 2),
                "rewards_usd": round(self.total_rewards_usd, 2),
                "pnl_usd": round(self.total_pnl_usd, 2),
                "pnl_pct": round(self.total_pnl_pct, 2),
                "il_usd": round(self.total_il_usd, 2),
            },
            "risk_alerts": self.risk_alerts,
        }

    def get_summary_ru(self) -> str:
        """Резюме на русском"""
        parts = [
            "🌾 **DeFi Portfolio Summary**",
            "",
        ]

        if self.positions:
            parts.extend(
                [
                    f"💰 Депозиты: **${self.total_deposited_usd:,.2f}**",
                    f"📊 Текущая стоимость: **${self.total_current_value_usd:,.2f}**",
                    f"🎁 Награды: **${self.total_rewards_usd:,.2f}**",
                ]
            )

            if self.total_pnl_usd >= 0:
                parts.append(
                    f"📈 PnL: **+${self.total_pnl_usd:,.2f}** (+{self.total_pnl_pct:.1f}%)"
                )
            else:
                parts.append(
                    f"📉 PnL: **-${abs(self.total_pnl_usd):,.2f}** ({self.total_pnl_pct:.1f}%)"
                )

            if self.total_il_usd != 0:
                parts.append(f"⚠️ Impermanent Loss: **${abs(self.total_il_usd):,.2f}**")
        else:
            parts.append("📭 Нет активных позиций")

        # Топ пулы
        if self.top_pools:
            parts.extend(["", "**🏆 Топ пулы по APY:**"])
            for pool in self.top_pools[:5]:
                parts.append(
                    f"• {pool.symbol} ({pool.chain}): **{pool.apy:.1f}%** APY | "
                    f"TVL: ${pool.tvl_usd / 1e6:.1f}M"
                )

        # Риск-алерты
        if self.risk_alerts:
            parts.extend(["", "🚨 **Алерты:**"])
            for alert in self.risk_alerts[:3]:
                parts.append(f"• {alert.get('message', 'N/A')}")

        return "\n".join(parts)


class DeFiTracker:
    """Трекер DeFi позиций и yields"""

    # Минимальный TVL для рекомендаций (в USD)
    MIN_TVL = 1_000_000  # $1M

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

    async def fetch_top_yields(
        self, chains: list[str] = None, min_tvl: float = None, limit: int = 50
    ) -> list[YieldPool]:
        """
        Получить топ yields с DefiLlama

        Args:
            chains: Фильтр по чейнам
            min_tvl: Минимальный TVL
            limit: Максимум пулов

        Returns:
            Список пулов
        """
        session = await self._get_session()
        min_tvl = min_tvl or self.MIN_TVL

        try:
            async with session.get(f"{DEFILLAMA_URL}/pools") as response:
                if response.status != 200:
                    logger.error(f"DefiLlama API error: {response.status}")
                    return []

                data = await response.json()

                pools = []
                for item in data.get("data", []):
                    tvl = item.get("tvlUsd", 0) or 0
                    apy = item.get("apy", 0) or 0

                    # Фильтры
                    if tvl < min_tvl:
                        continue
                    if apy <= 0 or apy > 1000:  # Фильтруем нереальные APY
                        continue
                    if chains and item.get("chain") not in chains:
                        continue

                    # Определяем риск IL
                    il_risk = "low"
                    exposure = item.get("exposure", "").split("-") if item.get("exposure") else []
                    if len(exposure) > 1:
                        # LP пул - есть риск IL
                        il_risk = "medium"
                        if any(t not in ["USDC", "USDT", "DAI", "BUSD"] for t in exposure):
                            il_risk = "high"

                    pool = YieldPool(
                        pool_id=item.get("pool", ""),
                        name=item.get("poolMeta", item.get("symbol", "")),
                        symbol=item.get("symbol", ""),
                        chain=item.get("chain", ""),
                        project=item.get("project", ""),
                        apy=apy,
                        apy_base=item.get("apyBase", 0) or 0,
                        apy_reward=item.get("apyReward", 0) or 0,
                        tvl_usd=tvl,
                        il_risk=il_risk,
                        stable_coin=item.get("stablecoin", False),
                        exposure=exposure,
                    )
                    pools.append(pool)

                # Сортируем по APY
                pools.sort(key=lambda x: x.apy, reverse=True)

                return pools[:limit]

        except Exception as e:
            logger.error(f"DefiLlama error: {e}")
            return []

    async def fetch_protocol_tvl(self, protocol: str) -> dict | None:
        """
        Получить TVL протокола

        Args:
            protocol: Slug протокола (например, 'aave')

        Returns:
            Данные TVL
        """
        session = await self._get_session()

        try:
            url = f"{DEFILLAMA_TVL_URL}/protocol/{protocol}"
            async with session.get(url) as response:
                if response.status != 200:
                    return None

                data = await response.json()

                return {
                    "name": data.get("name"),
                    "tvl": data.get("tvl"),
                    "chain_tvls": data.get("chainTvls", {}),
                    "change_1d": data.get("change_1d"),
                    "change_7d": data.get("change_7d"),
                }

        except Exception as e:
            logger.error(f"Protocol TVL error: {e}")
            return None

    @staticmethod
    def calculate_impermanent_loss(initial_price_ratio: float, current_price_ratio: float) -> float:
        """
        Рассчитать Impermanent Loss для LP позиции

        Формула: IL = 2 * sqrt(price_ratio) / (1 + price_ratio) - 1

        Args:
            initial_price_ratio: Начальное соотношение цен token0/token1
            current_price_ratio: Текущее соотношение цен

        Returns:
            IL в процентах (отрицательное число)
        """
        if initial_price_ratio <= 0:
            return 0.0

        # Относительное изменение цены
        price_change = current_price_ratio / initial_price_ratio

        # Формула IL
        il = 2 * math.sqrt(price_change) / (1 + price_change) - 1

        return il * 100  # В процентах

    def get_position_from_db(self, position_id: str) -> StakingPosition | None:
        """Получить позицию из БД"""
        # Placeholder - в реальности читаем из таблицы staking_positions
        return None

    def save_position_to_db(self, position: StakingPosition):
        """Сохранить позицию в БД"""
        # Placeholder - в реальности пишем в таблицу staking_positions
        pass

    async def get_user_positions(self) -> list[StakingPosition]:
        """
        Получить позиции пользователя из БД

        Returns:
            Список позиций
        """
        # Placeholder - в реальности читаем из БД
        return []

    def check_risk_alerts(
        self, positions: list[StakingPosition], pools: list[YieldPool]
    ) -> list[dict]:
        """
        Проверить риск-алерты

        Args:
            positions: Позиции пользователя
            pools: Данные по пулам

        Returns:
            Список алертов
        """
        alerts = []

        pool_map = {p.pool_id: p for p in pools}

        for pos in positions:
            pool = pool_map.get(pos.pool_id)

            # Высокий IL
            if pos.il_pct < -5:
                alerts.append(
                    {
                        "type": "high_il",
                        "severity": "warning",
                        "position_id": pos.id,
                        "message": f"⚠️ Высокий IL в {pos.pool_name}: {pos.il_pct:.1f}%",
                    }
                )

            # Падение TVL
            if pool and pool.tvl_usd < self.MIN_TVL / 2:
                alerts.append(
                    {
                        "type": "low_tvl",
                        "severity": "warning",
                        "position_id": pos.id,
                        "message": f"⚠️ Низкий TVL в {pos.pool_name}: ${pool.tvl_usd / 1e6:.1f}M",
                    }
                )

            # Большой убыток
            if pos.pnl_pct < -10:
                alerts.append(
                    {
                        "type": "high_loss",
                        "severity": "critical",
                        "position_id": pos.id,
                        "message": f"🚨 Убыток в {pos.pool_name}: {pos.pnl_pct:.1f}%",
                    }
                )

        return alerts

    async def get_summary(self, chains: list[str] = None) -> DeFiSummary:
        """
        Получить полную сводку по DeFi

        Args:
            chains: Фильтр по чейнам

        Returns:
            DeFiSummary
        """
        summary = DeFiSummary(timestamp=int(datetime.now().timestamp() * 1000))

        # Получаем топ пулы
        summary.top_pools = await self.fetch_top_yields(chains=chains, limit=20)

        # Получаем позиции пользователя
        summary.positions = await self.get_user_positions()

        # Считаем тотали
        if summary.positions:
            summary.total_deposited_usd = sum(p.deposited_usd for p in summary.positions)
            summary.total_current_value_usd = sum(p.current_value_usd for p in summary.positions)
            summary.total_rewards_usd = sum(p.rewards_usd for p in summary.positions)
            summary.total_pnl_usd = (
                summary.total_current_value_usd
                - summary.total_deposited_usd
                + summary.total_rewards_usd
            )

            if summary.total_deposited_usd > 0:
                summary.total_pnl_pct = summary.total_pnl_usd / summary.total_deposited_usd * 100

            summary.total_il_usd = sum(p.il_usd for p in summary.positions)

        # Проверяем риски
        summary.risk_alerts = self.check_risk_alerts(summary.positions, summary.top_pools)

        return summary

    async def find_best_yields(
        self, amount_usd: float, risk_tolerance: str = "medium", chains: list[str] = None
    ) -> list[dict]:
        """
        Найти лучшие возможности для инвестирования

        Args:
            amount_usd: Сумма в USD
            risk_tolerance: Уровень риска (low, medium, high)
            chains: Предпочитаемые чейны

        Returns:
            Список рекомендаций
        """
        pools = await self.fetch_top_yields(chains=chains, limit=100)

        recommendations = []

        for pool in pools:
            # Фильтруем по риску
            if risk_tolerance == "low":
                if pool.il_risk != "low" or not pool.stable_coin:
                    continue
            elif risk_tolerance == "medium":
                if pool.il_risk == "high":
                    continue

            # Считаем ожидаемый доход
            expected_yearly = amount_usd * (pool.apy / 100)
            expected_monthly = expected_yearly / 12

            recommendations.append(
                {
                    "pool": pool.to_dict(),
                    "expected_yearly_usd": round(expected_yearly, 2),
                    "expected_monthly_usd": round(expected_monthly, 2),
                    "risk_level": pool.il_risk,
                    "recommendation": self._get_recommendation(pool, risk_tolerance),
                }
            )

        # Сортируем по APY
        recommendations.sort(key=lambda x: x["pool"]["apy"], reverse=True)

        return recommendations[:10]

    def _get_recommendation(self, pool: YieldPool, risk_tolerance: str) -> str:
        """Сгенерировать рекомендацию"""
        if pool.stable_coin:
            return "✅ Стейблкоин пул - низкий риск IL"
        elif pool.il_risk == "low":
            return "✅ Низкий риск - подходит для консервативной стратегии"
        elif pool.il_risk == "medium":
            if risk_tolerance in ["medium", "high"]:
                return "⚡ Умеренный риск - хороший баланс риск/доходность"
            else:
                return "⚠️ Есть риск IL - не подходит для консервативной стратегии"
        else:
            if risk_tolerance == "high":
                return "🔥 Высокий риск, высокая доходность - для опытных"
            else:
                return "⚠️ Высокий риск IL - рекомендуется осторожность"


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import json

    logging.basicConfig(level=logging.INFO)

    async def main():
        tracker = DeFiTracker()

        try:
            print("Fetching DeFi data...")

            # Сводка
            summary = await tracker.get_summary(chains=["Ethereum", "Arbitrum", "Optimism"])

            print("\n" + "=" * 60)
            print("DEFI SUMMARY")
            print("=" * 60)
            print(json.dumps(summary.to_dict(), indent=2, ensure_ascii=False))

            print("\n" + "=" * 60)
            print("SUMMARY (RU)")
            print("=" * 60)
            print(summary.get_summary_ru())

            # Лучшие возможности
            print("\n" + "=" * 60)
            print("BEST YIELDS FOR $10,000")
            print("=" * 60)
            best = await tracker.find_best_yields(
                amount_usd=10000, risk_tolerance="medium", chains=["Ethereum", "Arbitrum"]
            )
            for rec in best[:5]:
                print(f"\n{rec['pool']['symbol']} ({rec['pool']['chain']})")
                print(f"  APY: {rec['pool']['apy']:.1f}%")
                print(f"  Expected yearly: ${rec['expected_yearly_usd']:,.2f}")
                print(f"  {rec['recommendation']}")

            # IL Calculator demo
            print("\n" + "=" * 60)
            print("IMPERMANENT LOSS CALCULATOR")
            print("=" * 60)

            # Пример: ETH/USDC пул, ETH вырос на 50%
            il = DeFiTracker.calculate_impermanent_loss(1.0, 1.5)
            print(f"ETH вырос на 50%: IL = {il:.2f}%")

            # ETH вырос на 100%
            il = DeFiTracker.calculate_impermanent_loss(1.0, 2.0)
            print(f"ETH вырос на 100%: IL = {il:.2f}%")

            # ETH упал на 50%
            il = DeFiTracker.calculate_impermanent_loss(1.0, 0.5)
            print(f"ETH упал на 50%: IL = {il:.2f}%")

        finally:
            await tracker.close()

    asyncio.run(main())
