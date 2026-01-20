"""
Profit Taking Advisor.

Provides guidance on when to take profits:
- Fibonacci extension levels
- Dynamic TP based on ATR
- "Greed meter" - scale out signals
- Portfolio rebalance suggestions

Помогает определить:
- Уровни фиксации прибыли
- Когда масштабировать позиции
- Сигналы о перегреве рынка
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import httpx

logger = logging.getLogger(__name__)

COINGECKO_API = "https://api.coingecko.com/api/v3"
BYBIT_API = "https://api.bybit.com"


class ProfitAction(Enum):
    """Recommended profit-taking action."""

    HOLD = "hold"  # Keep position
    SCALE_OUT_25 = "scale_out_25"  # Take 25% profits
    SCALE_OUT_50 = "scale_out_50"  # Take 50% profits
    TAKE_PROFIT = "take_profit"  # Close position

    @property
    def name_ru(self) -> str:
        names = {
            ProfitAction.HOLD: "Держать",
            ProfitAction.SCALE_OUT_25: "Зафиксировать 25%",
            ProfitAction.SCALE_OUT_50: "Зафиксировать 50%",
            ProfitAction.TAKE_PROFIT: "Фиксировать прибыль",
        }
        return names.get(self, self.value)

    @property
    def emoji(self) -> str:
        return {
            "hold": "🔒",
            "scale_out_25": "📊",
            "scale_out_50": "📉",
            "take_profit": "💰",
        }.get(self.value, "⚪")


class GreedLevel(Enum):
    """Market greed level."""

    LOW = "low"  # Safe to hold
    MODERATE = "moderate"  # Monitor closely
    HIGH = "high"  # Consider scaling out
    EXTREME = "extreme"  # Take profits

    @property
    def name_ru(self) -> str:
        names = {
            GreedLevel.LOW: "Низкая жадность",
            GreedLevel.MODERATE: "Умеренная жадность",
            GreedLevel.HIGH: "Высокая жадность",
            GreedLevel.EXTREME: "Экстремальная жадность",
        }
        return names.get(self, self.value)

    @property
    def emoji(self) -> str:
        return {
            "low": "🟢",
            "moderate": "🟡",
            "high": "🟠",
            "extreme": "🔴",
        }.get(self.value, "⚪")


@dataclass
class TakeProfitLevel:
    """Single take profit level."""

    level_num: int
    price: float
    distance_pct: float  # Distance from current price
    fib_extension: float  # Fibonacci extension level
    suggested_action: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level_num,
            "price": round(self.price, 2),
            "distance_pct": round(self.distance_pct, 2),
            "fib_extension": self.fib_extension,
            "action": self.suggested_action,
            "label": f"TP #{self.level_num}",
        }


@dataclass
class ProfitTakingAnalysis:
    """Profit taking analysis result."""

    symbol: str
    timestamp: datetime
    current_price: float
    action: ProfitAction
    greed_level: GreedLevel
    tp_levels: list[TakeProfitLevel] = field(default_factory=list)
    greed_score: int = 50  # 0-100
    distance_from_ath: float = 0
    atr_pct: float = 0  # ATR as % of price
    swing_high: float = 0
    swing_low: float = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "current_price": round(self.current_price, 2),
            "action": self.action.value,
            "action_ru": self.action.name_ru,
            "action_emoji": self.action.emoji,
            "greed_level": self.greed_level.value,
            "greed_level_ru": self.greed_level.name_ru,
            "greed_emoji": self.greed_level.emoji,
            "greed_score": self.greed_score,
            "tp_levels": [lvl.to_dict() for lvl in self.tp_levels],
            "tp_level_1": round(self.tp_levels[0].price, 2) if self.tp_levels else 0,
            "tp_level_2": round(self.tp_levels[1].price, 2) if len(self.tp_levels) > 1 else 0,
            "distance_from_ath": round(self.distance_from_ath, 2),
            "atr_pct": round(self.atr_pct, 2),
            "swing_high": round(self.swing_high, 2),
            "swing_low": round(self.swing_low, 2),
            "recommendation": self._get_recommendation(),
            "recommendation_ru": self._get_recommendation_ru(),
        }

    def _get_recommendation(self) -> str:
        if self.action == ProfitAction.TAKE_PROFIT:
            return (
                f"Strong sell signal. First TP at ${self.tp_levels[0].price:,.2f}"
                if self.tp_levels
                else "Take profits now"
            )
        if self.action == ProfitAction.SCALE_OUT_50:
            return "High greed - consider taking 50% off the table"
        if self.action == ProfitAction.SCALE_OUT_25:
            return "Moderate greed - consider taking 25% profits"
        return "No action needed - hold position"

    def _get_recommendation_ru(self) -> str:
        if self.action == ProfitAction.TAKE_PROFIT:
            return (
                f"Сильный сигнал продажи. Первая цель ${self.tp_levels[0].price:,.2f}"
                if self.tp_levels
                else "Фиксируйте прибыль"
            )
        if self.action == ProfitAction.SCALE_OUT_50:
            return "Высокая жадность - рассмотрите фиксацию 50%"
        if self.action == ProfitAction.SCALE_OUT_25:
            return "Умеренная жадность - рассмотрите фиксацию 25%"
        return "Действий не требуется - держите позицию"


class ProfitTakingAdvisor:
    """
    Profit taking advisory service.

    Calculates optimal profit taking levels and monitors greed.
    """

    # Fibonacci extension levels for TP
    FIB_EXTENSIONS = [1.618, 2.618, 4.236]

    def __init__(self, timeout: float = 30.0):
        self._client: httpx.AsyncClient | None = None
        self._timeout = timeout

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self._timeout,
                headers={"Accept": "application/json"},
            )
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def analyze(self, symbol: str = "BTC") -> ProfitTakingAnalysis:
        """
        Analyze profit taking levels for a symbol.

        Args:
            symbol: Cryptocurrency symbol

        Returns:
            ProfitTakingAnalysis with TP levels and recommendations
        """
        client = await self._get_client()

        # Fetch market data
        try:
            market_data = await self._fetch_market_data(client, symbol)
            current_price = market_data.get("current_price", 0)
            ath = market_data.get("ath", current_price * 1.5)
            high_24h = market_data.get("high_24h", current_price * 1.05)
            low_24h = market_data.get("low_24h", current_price * 0.95)
        except Exception as e:
            logger.error(f"Failed to fetch market data: {e}")
            return self._create_empty_result(symbol)

        if current_price <= 0:
            return self._create_empty_result(symbol)

        # Calculate swing points (simplified)
        swing_high = high_24h
        swing_low = low_24h
        swing_range = swing_high - swing_low

        # Calculate ATR as percentage
        atr_pct = (swing_range / current_price) * 100 if current_price > 0 else 0

        # Calculate Fibonacci extension TP levels
        tp_levels = []
        for i, fib in enumerate(self.FIB_EXTENSIONS):
            tp_price = swing_low + (swing_range * fib)
            distance = ((tp_price - current_price) / current_price) * 100

            # Suggested action at this level
            if i == 0:
                action = "Scale out 25%"
            elif i == 1:
                action = "Scale out 50%"
            else:
                action = "Close position"

            tp_levels.append(
                TakeProfitLevel(
                    level_num=i + 1,
                    price=tp_price,
                    distance_pct=distance,
                    fib_extension=fib,
                    suggested_action=action,
                )
            )

        # Calculate greed score
        greed_score = self._calculate_greed_score(current_price, ath, swing_high, swing_low)

        # Determine greed level
        greed_level = self._classify_greed(greed_score)

        # Determine recommended action
        action = self._determine_action(current_price, tp_levels, greed_level, ath)

        # Distance from ATH
        distance_from_ath = ((ath - current_price) / ath) * 100 if ath > 0 else 0

        return ProfitTakingAnalysis(
            symbol=symbol,
            timestamp=datetime.now(),
            current_price=current_price,
            action=action,
            greed_level=greed_level,
            tp_levels=tp_levels,
            greed_score=greed_score,
            distance_from_ath=distance_from_ath,
            atr_pct=atr_pct,
            swing_high=swing_high,
            swing_low=swing_low,
        )

    async def _fetch_market_data(self, client: httpx.AsyncClient, symbol: str) -> dict[str, float]:
        """Fetch market data from CoinGecko."""
        symbol_map = {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "SOL": "solana",
        }

        cg_id = symbol_map.get(symbol.upper(), symbol.lower())

        try:
            url = f"{COINGECKO_API}/coins/{cg_id}"
            params = {
                "localization": "false",
                "tickers": "false",
                "community_data": "false",
                "developer_data": "false",
            }

            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            market_data = data.get("market_data", {})

            return {
                "current_price": market_data.get("current_price", {}).get("usd", 0),
                "ath": market_data.get("ath", {}).get("usd", 0),
                "high_24h": market_data.get("high_24h", {}).get("usd", 0),
                "low_24h": market_data.get("low_24h", {}).get("usd", 0),
            }

        except Exception as e:
            logger.warning(f"CoinGecko fetch failed: {e}")

            # Fallback to Bybit
            try:
                bybit_symbol = f"{symbol.upper()}USDT"
                url = f"{BYBIT_API}/v5/market/tickers"
                params = {"category": "linear", "symbol": bybit_symbol}

                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                tickers = data.get("result", {}).get("list", [])
                if tickers:
                    ticker = tickers[0]
                    price = float(ticker.get("lastPrice", 0))
                    high = float(ticker.get("highPrice24h", price * 1.05))
                    low = float(ticker.get("lowPrice24h", price * 0.95))
                    return {
                        "current_price": price,
                        "ath": price * 1.5,  # Estimate
                        "high_24h": high,
                        "low_24h": low,
                    }
            except Exception as e2:
                logger.error(f"Bybit fallback failed: {e2}")

            return {}

    def _calculate_greed_score(
        self,
        current_price: float,
        ath: float,
        swing_high: float,
        swing_low: float,
    ) -> int:
        """
        Calculate greed score (0-100).

        Higher score = more greed in market.
        """
        if ath == 0 or swing_high == swing_low:
            return 50

        # Factor 1: Position vs ATH (0-40 points)
        ath_ratio = current_price / ath if ath > 0 else 0.5
        ath_score = min(40, int(ath_ratio * 40))

        # Factor 2: Position in swing range (0-30 points)
        swing_range = swing_high - swing_low
        position_in_swing = (current_price - swing_low) / swing_range if swing_range > 0 else 0.5
        swing_score = int(position_in_swing * 30)

        # Factor 3: Near ATH bonus (0-30 points)
        near_ath_score = 0
        if current_price > ath * 0.95:
            near_ath_score = 30
        elif current_price > ath * 0.90:
            near_ath_score = 20
        elif current_price > ath * 0.85:
            near_ath_score = 10

        return min(100, ath_score + swing_score + near_ath_score)

    def _classify_greed(self, score: int) -> GreedLevel:
        """Classify greed level based on score."""
        if score >= 80:
            return GreedLevel.EXTREME
        if score >= 60:
            return GreedLevel.HIGH
        if score >= 40:
            return GreedLevel.MODERATE
        return GreedLevel.LOW

    def _determine_action(
        self,
        current_price: float,
        tp_levels: list[TakeProfitLevel],
        greed_level: GreedLevel,
        ath: float,
    ) -> ProfitAction:
        """Determine recommended profit-taking action."""
        # Near ATH = always consider taking profits
        if ath > 0 and current_price >= ath * 0.95:
            return ProfitAction.TAKE_PROFIT

        # Based on greed level
        if greed_level == GreedLevel.EXTREME:
            return ProfitAction.TAKE_PROFIT
        if greed_level == GreedLevel.HIGH:
            return ProfitAction.SCALE_OUT_50
        if greed_level == GreedLevel.MODERATE:
            # Check if we hit first TP level
            if tp_levels and current_price >= tp_levels[0].price:
                return ProfitAction.SCALE_OUT_25

        return ProfitAction.HOLD

    def _create_empty_result(self, symbol: str) -> ProfitTakingAnalysis:
        """Create empty result on error."""
        return ProfitTakingAnalysis(
            symbol=symbol,
            timestamp=datetime.now(),
            current_price=0,
            action=ProfitAction.HOLD,
            greed_level=GreedLevel.LOW,
        )

    async def get_multi_symbol(self, symbols: list[str] | None = None) -> dict[str, ProfitTakingAnalysis]:
        """Get profit taking analysis for multiple symbols."""
        if symbols is None:
            symbols = ["BTC", "ETH"]

        result = {}
        for symbol in symbols:
            try:
                result[symbol] = await self.analyze(symbol)
            except Exception as e:
                logger.error(f"Analysis failed for {symbol}: {e}")
                result[symbol] = self._create_empty_result(symbol)

        return result


# Global instance
_profit_advisor: ProfitTakingAdvisor | None = None


def get_profit_advisor() -> ProfitTakingAdvisor:
    """Get global profit taking advisor instance."""
    global _profit_advisor
    if _profit_advisor is None:
        _profit_advisor = ProfitTakingAdvisor()
    return _profit_advisor
