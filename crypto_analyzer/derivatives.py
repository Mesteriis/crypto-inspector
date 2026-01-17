"""
Derivatives Analysis - Анализ деривативов

Источники:
- Binance Futures API (бесплатно)
- Bybit Derivatives API (бесплатно)
- CoinGlass (частично бесплатно)

Метрики:
- Funding Rate
- Open Interest
- Long/Short Ratio
- Liquidations
- Top Trader Sentiment
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime

import aiohttp
from database import CryptoDatabase, get_database

logger = logging.getLogger(__name__)


# API Endpoints
BINANCE_FUTURES_URL = "https://fapi.binance.com/fapi/v1"
BYBIT_V5_URL = "https://api.bybit.com/v5"
COINGLASS_PUBLIC_URL = "https://open-api.coinglass.com/public/v2"


@dataclass
class DerivativesMetrics:
    """Структура метрик деривативов"""

    symbol: str
    timestamp: int

    # Funding Rate
    funding_rate: float | None = None  # В процентах (0.01 = 0.01%)
    funding_rate_annualized: float | None = None  # Годовая ставка
    funding_interpretation: str | None = None
    next_funding_time: int | None = None

    # Open Interest
    open_interest_usd: float | None = None
    open_interest_change_24h: float | None = None  # В процентах

    # Long/Short Ratio
    long_short_ratio: float | None = None  # > 1 = больше лонгов
    top_trader_long_short: float | None = None  # Топ трейдеры

    # Liquidations
    liquidations_long_24h: float | None = None  # В USD
    liquidations_short_24h: float | None = None
    liquidations_total_24h: float | None = None

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "funding": {
                "rate": self.funding_rate,
                "rate_annualized": self.funding_rate_annualized,
                "interpretation": self.funding_interpretation,
                "next_funding_ts": self.next_funding_time,
            },
            "open_interest": {
                "value_usd": self.open_interest_usd,
                "change_24h_pct": self.open_interest_change_24h,
            },
            "long_short": {
                "ratio": self.long_short_ratio,
                "top_traders_ratio": self.top_trader_long_short,
                "interpretation": self._interpret_ls_ratio(),
            },
            "liquidations": {
                "long_24h_usd": self.liquidations_long_24h,
                "short_24h_usd": self.liquidations_short_24h,
                "total_24h_usd": self.liquidations_total_24h,
                "dominant_side": self._get_dominant_liquidation(),
            },
        }

    def _interpret_ls_ratio(self) -> str:
        """Интерпретация Long/Short ratio"""
        if self.long_short_ratio is None:
            return "unknown"
        if self.long_short_ratio > 1.5:
            return "extreme_long"  # Много лонгов - риск short squeeze
        elif self.long_short_ratio > 1.1:
            return "long_bias"
        elif self.long_short_ratio < 0.67:
            return "extreme_short"  # Много шортов - риск long squeeze
        elif self.long_short_ratio < 0.9:
            return "short_bias"
        else:
            return "neutral"

    def _get_dominant_liquidation(self) -> str:
        """Определить доминирующую сторону ликвидаций"""
        if self.liquidations_long_24h is None or self.liquidations_short_24h is None:
            return "unknown"

        if self.liquidations_long_24h > self.liquidations_short_24h * 1.5:
            return "longs"  # Ликвидируются лонги - медвежий сигнал
        elif self.liquidations_short_24h > self.liquidations_long_24h * 1.5:
            return "shorts"  # Ликвидируются шорты - бычий сигнал
        else:
            return "balanced"

    def get_summary_ru(self) -> str:
        """Получить резюме на русском"""
        parts = []

        # Funding Rate
        if self.funding_rate is not None:
            fr_pct = self.funding_rate * 100
            if abs(fr_pct) < 0.005:
                fr_emoji = "⚪"
                fr_text = "нейтральный"
            elif fr_pct > 0.03:
                fr_emoji = "🔴"
                fr_text = f"высокий положительный ({fr_pct:.4f}%)"
            elif fr_pct > 0:
                fr_emoji = "🟡"
                fr_text = f"положительный ({fr_pct:.4f}%)"
            elif fr_pct < -0.03:
                fr_emoji = "🟢"
                fr_text = f"высокий отрицательный ({fr_pct:.4f}%)"
            else:
                fr_emoji = "🟡"
                fr_text = f"отрицательный ({fr_pct:.4f}%)"

            parts.append(f"{fr_emoji} Funding Rate: {fr_text}")

            if self.funding_rate_annualized:
                parts.append(f"   📊 Годовая ставка: {self.funding_rate_annualized:.1f}%")

        # Open Interest
        if self.open_interest_usd:
            oi_b = self.open_interest_usd / 1e9
            oi_text = f"💰 Open Interest: ${oi_b:.2f}B"
            if self.open_interest_change_24h:
                change = self.open_interest_change_24h
                change_emoji = "📈" if change > 0 else "📉"
                oi_text += f" ({change_emoji} {change:+.1f}% за 24ч)"
            parts.append(oi_text)

        # Long/Short Ratio
        if self.long_short_ratio:
            ls = self.long_short_ratio
            if ls > 1.5:
                ls_emoji = "🔴"
                ls_text = f"экстремально бычий ({ls:.2f})"
            elif ls > 1.1:
                ls_emoji = "🟡"
                ls_text = f"бычий ({ls:.2f})"
            elif ls < 0.67:
                ls_emoji = "🟢"
                ls_text = f"экстремально медвежий ({ls:.2f})"
            elif ls < 0.9:
                ls_emoji = "🟡"
                ls_text = f"медвежий ({ls:.2f})"
            else:
                ls_emoji = "⚪"
                ls_text = f"нейтральный ({ls:.2f})"

            parts.append(f"{ls_emoji} Long/Short: {ls_text}")

        # Liquidations
        if self.liquidations_total_24h:
            liq_m = self.liquidations_total_24h / 1e6
            dom = self._get_dominant_liquidation()
            if dom == "longs":
                liq_emoji = "🔴"
                liq_text = "больше лонгов"
            elif dom == "shorts":
                liq_emoji = "🟢"
                liq_text = "больше шортов"
            else:
                liq_emoji = "⚪"
                liq_text = "сбалансировано"

            parts.append(f"💥 Ликвидации 24ч: ${liq_m:.1f}M ({liq_emoji} {liq_text})")

        return "\n".join(parts) if parts else "Нет данных"

    def get_signal(self) -> tuple[str, str]:
        """
        Получить торговый сигнал на основе деривативов

        Returns:
            Tuple (signal, description_ru)
        """
        bullish_points = 0
        bearish_points = 0

        # Funding Rate analysis
        if self.funding_rate is not None:
            fr_pct = self.funding_rate * 100
            if fr_pct > 0.05:  # Очень высокий положительный - много лонгов платят шортам
                bearish_points += 2  # Контр-сигнал: возможен дамп
            elif fr_pct < -0.03:  # Отрицательный - шорты платят лонгам
                bullish_points += 2  # Контр-сигнал: возможен рост

        # Long/Short Ratio
        if self.long_short_ratio:
            if self.long_short_ratio > 1.5:  # Слишком много лонгов
                bearish_points += 1
            elif self.long_short_ratio < 0.67:  # Слишком много шортов
                bullish_points += 1

        # Liquidations
        dom = self._get_dominant_liquidation()
        if dom == "longs":
            bearish_points += 1
        elif dom == "shorts":
            bullish_points += 1

        # Open Interest change
        if self.open_interest_change_24h:
            if self.open_interest_change_24h > 10:  # Сильный рост OI
                # Зависит от направления цены, но в целом увеличивает волатильность
                pass
            elif self.open_interest_change_24h < -10:  # Сильное падение OI
                # Закрытие позиций, возможно окончание тренда
                pass

        if bullish_points > bearish_points + 1:
            return "bullish", "🟢 Деривативы указывают на потенциальный рост (шорты перегружены)"
        elif bearish_points > bullish_points + 1:
            return "bearish", "🔴 Деривативы указывают на риск падения (лонги перегружены)"
        else:
            return "neutral", "⚪ Деривативы нейтральны"


class DerivativesAnalyzer:
    """Анализатор деривативов"""

    # Маппинг символов для фьючерсов
    SYMBOL_MAP = {
        "BTC": {"binance": "BTCUSDT", "bybit": "BTCUSDT"},
        "ETH": {"binance": "ETHUSDT", "bybit": "ETHUSDT"},
        "SOL": {"binance": "SOLUSDT", "bybit": "SOLUSDT"},
    }

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

    async def fetch_binance_funding_rate(self, symbol: str) -> dict:
        """
        Получить funding rate с Binance Futures
        """
        session = await self._get_session()
        futures_symbol = self.SYMBOL_MAP.get(symbol.upper(), {}).get("binance", f"{symbol}USDT")

        try:
            # Текущий funding rate
            url = f"{BINANCE_FUTURES_URL}/premiumIndex"
            params = {"symbol": futures_symbol}

            async with session.get(url, params=params) as response:
                if response.status != 200:
                    return {}

                data = await response.json()

                funding_rate = float(data.get("lastFundingRate", 0))
                next_funding = int(data.get("nextFundingTime", 0))

                # Годовая ставка (funding каждые 8 часов, 3 раза в день, 365 дней)
                annualized = funding_rate * 3 * 365 * 100

                return {
                    "funding_rate": funding_rate,
                    "funding_rate_annualized": annualized,
                    "next_funding_time": next_funding,
                    "source": "binance",
                }

        except Exception as e:
            logger.error(f"Error fetching Binance funding rate: {e}")
            return {}

    async def fetch_binance_open_interest(self, symbol: str) -> dict:
        """
        Получить open interest с Binance Futures
        """
        session = await self._get_session()
        futures_symbol = self.SYMBOL_MAP.get(symbol.upper(), {}).get("binance", f"{symbol}USDT")

        try:
            url = f"{BINANCE_FUTURES_URL}/openInterest"
            params = {"symbol": futures_symbol}

            async with session.get(url, params=params) as response:
                if response.status != 200:
                    return {}

                data = await response.json()

                oi = float(data.get("openInterest", 0))

                # Получаем текущую цену для расчёта в USD
                price_url = f"{BINANCE_FUTURES_URL}/ticker/price"
                async with session.get(
                    price_url, params={"symbol": futures_symbol}
                ) as price_response:
                    if price_response.status == 200:
                        price_data = await price_response.json()
                        price = float(price_data.get("price", 0))
                        oi_usd = oi * price
                    else:
                        oi_usd = oi

                return {"open_interest": oi, "open_interest_usd": oi_usd, "source": "binance"}

        except Exception as e:
            logger.error(f"Error fetching Binance OI: {e}")
            return {}

    async def fetch_binance_long_short_ratio(self, symbol: str) -> dict:
        """
        Получить long/short ratio с Binance Futures
        """
        session = await self._get_session()
        futures_symbol = self.SYMBOL_MAP.get(symbol.upper(), {}).get("binance", f"{symbol}USDT")

        try:
            # Global Long/Short Account Ratio
            url = f"{BINANCE_FUTURES_URL}/globalLongShortAccountRatio"
            params = {"symbol": futures_symbol, "period": "1h", "limit": 1}

            async with session.get(url, params=params) as response:
                if response.status != 200:
                    return {}

                data = await response.json()

                if not data:
                    return {}

                latest = data[0]
                ls_ratio = float(latest.get("longShortRatio", 1))

                return {
                    "long_short_ratio": ls_ratio,
                    "long_account_pct": float(latest.get("longAccount", 50)),
                    "short_account_pct": float(latest.get("shortAccount", 50)),
                    "source": "binance",
                }

        except Exception as e:
            logger.error(f"Error fetching Binance L/S ratio: {e}")
            return {}

    async def fetch_binance_top_trader_sentiment(self, symbol: str) -> dict:
        """
        Получить sentiment топ трейдеров с Binance
        """
        session = await self._get_session()
        futures_symbol = self.SYMBOL_MAP.get(symbol.upper(), {}).get("binance", f"{symbol}USDT")

        try:
            url = f"{BINANCE_FUTURES_URL}/topLongShortPositionRatio"
            params = {"symbol": futures_symbol, "period": "1h", "limit": 1}

            async with session.get(url, params=params) as response:
                if response.status != 200:
                    return {}

                data = await response.json()

                if not data:
                    return {}

                latest = data[0]

                return {
                    "top_trader_ls_ratio": float(latest.get("longShortRatio", 1)),
                    "top_long_pct": float(latest.get("longAccount", 50)),
                    "top_short_pct": float(latest.get("shortAccount", 50)),
                    "source": "binance",
                }

        except Exception as e:
            logger.error(f"Error fetching Binance top trader sentiment: {e}")
            return {}

    async def analyze(self, symbol: str) -> DerivativesMetrics:
        """
        Полный анализ деривативов

        Args:
            symbol: Символ монеты

        Returns:
            DerivativesMetrics
        """
        metrics = DerivativesMetrics(
            symbol=symbol.upper(), timestamp=int(datetime.now().timestamp() * 1000)
        )

        # Параллельный сбор данных
        tasks = [
            self.fetch_binance_funding_rate(symbol),
            self.fetch_binance_open_interest(symbol),
            self.fetch_binance_long_short_ratio(symbol),
            self.fetch_binance_top_trader_sentiment(symbol),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Funding Rate
        fr_data = results[0] if not isinstance(results[0], Exception) else {}
        if fr_data:
            metrics.funding_rate = fr_data.get("funding_rate")
            metrics.funding_rate_annualized = fr_data.get("funding_rate_annualized")
            metrics.next_funding_time = fr_data.get("next_funding_time")

            # Интерпретация
            if metrics.funding_rate is not None:
                fr_pct = metrics.funding_rate * 100
                if fr_pct > 0.03:
                    metrics.funding_interpretation = "bullish_crowded"
                elif fr_pct < -0.02:
                    metrics.funding_interpretation = "bearish_crowded"
                else:
                    metrics.funding_interpretation = "neutral"

        # Open Interest
        oi_data = results[1] if not isinstance(results[1], Exception) else {}
        if oi_data:
            metrics.open_interest_usd = oi_data.get("open_interest_usd")

        # Long/Short Ratio
        ls_data = results[2] if not isinstance(results[2], Exception) else {}
        if ls_data:
            metrics.long_short_ratio = ls_data.get("long_short_ratio")

        # Top Trader Sentiment
        tt_data = results[3] if not isinstance(results[3], Exception) else {}
        if tt_data:
            metrics.top_trader_long_short = tt_data.get("top_trader_ls_ratio")

        return metrics

    def get_cached_or_fetch(self, symbol: str) -> dict | None:
        """
        Получить из кэша или запросить новые данные

        Returns:
            Dict с данными деривативов
        """
        # Проверяем кэш (TTL 5 минут для деривативов)
        cached = self.db.get_cache(symbol, "derivatives")
        if cached:
            return cached

        try:
            loop = asyncio.new_event_loop()
            metrics = loop.run_until_complete(self.analyze(symbol))
            loop.close()

            data = metrics.to_dict()

            # Сохраняем в кэш
            self.db.set_cache(symbol, "derivatives", data, ttl_minutes=5)

            return data
        except Exception as e:
            logger.error(f"Error fetching derivatives data: {e}")
            return None


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import json

    logging.basicConfig(level=logging.INFO)

    async def main():
        analyzer = DerivativesAnalyzer()

        try:
            for symbol in ["BTC", "ETH"]:
                print(f"\n{'='*60}")
                print(f"DERIVATIVES: {symbol}")
                print("=" * 60)

                metrics = await analyzer.analyze(symbol)

                print(json.dumps(metrics.to_dict(), indent=2, ensure_ascii=False))

                print("\nSUMMARY (RU):")
                print(metrics.get_summary_ru())

                signal, desc = metrics.get_signal()
                print(f"\nСИГНАЛ: {desc}")

        finally:
            await analyzer.close()

    asyncio.run(main())
