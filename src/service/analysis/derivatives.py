"""
Derivatives Analysis Module.

Fetches derivatives data from exchanges:
- Funding Rate (Binance Futures)
- Open Interest
- Long/Short Ratio
- Top Trader Sentiment
"""

import logging
from dataclasses import dataclass
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

# API URLs
BINANCE_FUTURES_URL = "https://fapi.binance.com/fapi/v1"


@dataclass
class FundingData:
    """Funding rate data."""

    symbol: str
    rate: float  # Current funding rate
    next_funding_time: int  # Timestamp
    mark_price: float
    index_price: float

    # Derived
    annualized_rate: float  # rate * 3 * 365
    interpretation: str

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "rate": self.rate,
            "rate_pct": round(self.rate * 100, 4),
            "annualized_pct": round(self.annualized_rate * 100, 2),
            "next_funding_time": self.next_funding_time,
            "mark_price": self.mark_price,
            "index_price": self.index_price,
            "interpretation": self.interpretation,
        }


@dataclass
class OpenInterestData:
    """Open interest data."""

    symbol: str
    open_interest: float  # In contracts
    open_interest_value: float  # In USD
    change_24h_pct: float | None = None

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "open_interest": self.open_interest,
            "open_interest_value_usd": self.open_interest_value,
            "change_24h_pct": self.change_24h_pct,
        }


@dataclass
class LongShortData:
    """Long/Short ratio data."""

    symbol: str
    long_short_ratio: float  # > 1 = more longs
    long_account_pct: float
    short_account_pct: float
    timestamp: int

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "ratio": self.long_short_ratio,
            "long_pct": self.long_account_pct,
            "short_pct": self.short_account_pct,
            "timestamp": self.timestamp,
        }


@dataclass
class TopTraderData:
    """Top trader sentiment data."""

    symbol: str
    long_short_ratio: float
    long_account: float
    short_account: float
    timestamp: int

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "ratio": self.long_short_ratio,
            "long_account": self.long_account,
            "short_account": self.short_account,
            "timestamp": self.timestamp,
        }


@dataclass
class DerivativesMetrics:
    """Combined derivatives metrics."""

    symbol: str
    funding: FundingData | None = None
    open_interest: OpenInterestData | None = None
    long_short: LongShortData | None = None
    top_traders: TopTraderData | None = None
    timestamp: int = 0

    # Overall signal
    signal: str = "neutral"
    score: float = 50.0

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "funding": self.funding.to_dict() if self.funding else None,
            "open_interest": self.open_interest.to_dict() if self.open_interest else None,
            "long_short": self.long_short.to_dict() if self.long_short else None,
            "top_traders": self.top_traders.to_dict() if self.top_traders else None,
            "signal": self.signal,
            "score": self.score,
        }


class DerivativesAnalyzer:
    """Fetches and analyzes derivatives data."""

    SYMBOL_MAP = {
        "BTC": "BTCUSDT",
        "ETH": "ETHUSDT",
        "SOL": "SOLUSDT",
        "XRP": "XRPUSDT",
        "DOGE": "DOGEUSDT",
    }

    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers={"User-Agent": "CryptoInspect/1.0"},
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def _get_binance_symbol(self, symbol: str) -> str:
        """Convert symbol to Binance format."""
        return self.SYMBOL_MAP.get(symbol.upper(), f"{symbol.upper()}USDT")

    async def fetch_funding_rate(self, symbol: str) -> FundingData | None:
        """
        Fetch funding rate from Binance Futures.

        Args:
            symbol: Trading pair symbol

        Returns:
            FundingData or None on error
        """
        client = await self._get_client()
        binance_symbol = self._get_binance_symbol(symbol)

        try:
            response = await client.get(
                f"{BINANCE_FUTURES_URL}/premiumIndex",
                params={"symbol": binance_symbol},
            )
            response.raise_for_status()
            data = response.json()

            rate = float(data["lastFundingRate"])
            annualized = rate * 3 * 365  # 3 funding periods per day

            # Interpret funding rate
            if rate > 0.001:  # > 0.1%
                interpretation = "High positive - Many longs, potential squeeze"
            elif rate > 0.0003:
                interpretation = "Positive - Bullish sentiment"
            elif rate < -0.0005:
                interpretation = "Negative - Shorts pay, bullish signal"
            elif rate < -0.0001:
                interpretation = "Slightly negative - Some bearish sentiment"
            else:
                interpretation = "Neutral"

            return FundingData(
                symbol=symbol.upper(),
                rate=rate,
                next_funding_time=int(data["nextFundingTime"]),
                mark_price=float(data["markPrice"]),
                index_price=float(data["indexPrice"]),
                annualized_rate=annualized,
                interpretation=interpretation,
            )

        except httpx.HTTPError as e:
            logger.error(f"Funding rate API error for {symbol}: {e}")
            return None
        except Exception as e:
            logger.error(f"Funding rate parsing error for {symbol}: {e}")
            return None

    async def fetch_open_interest(self, symbol: str) -> OpenInterestData | None:
        """
        Fetch open interest from Binance Futures.

        Args:
            symbol: Trading pair symbol

        Returns:
            OpenInterestData or None on error
        """
        client = await self._get_client()
        binance_symbol = self._get_binance_symbol(symbol)

        try:
            response = await client.get(
                f"{BINANCE_FUTURES_URL}/openInterest",
                params={"symbol": binance_symbol},
            )
            response.raise_for_status()
            data = response.json()

            # Get current price for USD value calculation
            price_response = await client.get(
                f"{BINANCE_FUTURES_URL}/ticker/price",
                params={"symbol": binance_symbol},
            )
            price = float(price_response.json()["price"]) if price_response.status_code == 200 else 0

            oi = float(data["openInterest"])
            oi_value = oi * price

            return OpenInterestData(
                symbol=symbol.upper(),
                open_interest=oi,
                open_interest_value=oi_value,
            )

        except httpx.HTTPError as e:
            logger.error(f"Open interest API error for {symbol}: {e}")
            return None
        except Exception as e:
            logger.error(f"Open interest parsing error for {symbol}: {e}")
            return None

    async def fetch_long_short_ratio(self, symbol: str) -> LongShortData | None:
        """
        Fetch global long/short ratio from Binance Futures.

        Args:
            symbol: Trading pair symbol

        Returns:
            LongShortData or None on error
        """
        client = await self._get_client()
        binance_symbol = self._get_binance_symbol(symbol)

        try:
            response = await client.get(
                f"{BINANCE_FUTURES_URL}/globalLongShortAccountRatio",
                params={"symbol": binance_symbol, "period": "5m", "limit": 1},
            )
            response.raise_for_status()
            data = response.json()

            if not data:
                return None

            latest = data[0]

            return LongShortData(
                symbol=symbol.upper(),
                long_short_ratio=float(latest["longShortRatio"]),
                long_account_pct=float(latest["longAccount"]) * 100,
                short_account_pct=float(latest["shortAccount"]) * 100,
                timestamp=int(latest["timestamp"]),
            )

        except httpx.HTTPError as e:
            logger.error(f"Long/Short ratio API error for {symbol}: {e}")
            return None
        except Exception as e:
            logger.error(f"Long/Short ratio parsing error for {symbol}: {e}")
            return None

    async def fetch_top_trader_sentiment(self, symbol: str) -> TopTraderData | None:
        """
        Fetch top trader long/short ratio from Binance Futures.

        Args:
            symbol: Trading pair symbol

        Returns:
            TopTraderData or None on error
        """
        client = await self._get_client()
        binance_symbol = self._get_binance_symbol(symbol)

        try:
            response = await client.get(
                f"{BINANCE_FUTURES_URL}/topLongShortAccountRatio",
                params={"symbol": binance_symbol, "period": "5m", "limit": 1},
            )
            response.raise_for_status()
            data = response.json()

            if not data:
                return None

            latest = data[0]

            return TopTraderData(
                symbol=symbol.upper(),
                long_short_ratio=float(latest["longShortRatio"]),
                long_account=float(latest["longAccount"]) * 100,
                short_account=float(latest["shortAccount"]) * 100,
                timestamp=int(latest["timestamp"]),
            )

        except httpx.HTTPError as e:
            logger.error(f"Top trader API error for {symbol}: {e}")
            return None
        except Exception as e:
            logger.error(f"Top trader parsing error for {symbol}: {e}")
            return None

    async def analyze(self, symbol: str) -> DerivativesMetrics:
        """
        Fetch all derivatives metrics for a symbol.

        Args:
            symbol: Trading pair symbol

        Returns:
            DerivativesMetrics with all available data
        """
        import asyncio

        result = DerivativesMetrics(
            symbol=symbol.upper(),
            timestamp=int(datetime.now().timestamp() * 1000),
        )

        # Fetch all metrics concurrently
        funding_task = asyncio.create_task(self.fetch_funding_rate(symbol))
        oi_task = asyncio.create_task(self.fetch_open_interest(symbol))
        ls_task = asyncio.create_task(self.fetch_long_short_ratio(symbol))
        top_task = asyncio.create_task(self.fetch_top_trader_sentiment(symbol))

        result.funding = await funding_task
        result.open_interest = await oi_task
        result.long_short = await ls_task
        result.top_traders = await top_task

        # Calculate overall signal and score
        result.score, result.signal = self._calculate_signal(result)

        return result

    def _calculate_signal(self, metrics: DerivativesMetrics) -> tuple[float, str]:
        """
        Calculate overall signal from derivatives data.

        Derivatives are contrarian indicators - extreme positioning
        often precedes reversals.
        """
        score = 50.0

        # Funding rate (contrarian)
        if metrics.funding:
            rate = metrics.funding.rate
            if rate > 0.001:  # Very high positive
                score -= 15  # Bearish (too many longs)
            elif rate > 0.0003:
                score -= 5
            elif rate < -0.0005:  # Negative
                score += 15  # Bullish (shorts squeezable)
            elif rate < -0.0001:
                score += 5

        # Long/Short ratio (contrarian)
        if metrics.long_short:
            ratio = metrics.long_short.long_short_ratio
            if ratio > 2.0:  # Very long heavy
                score -= 10
            elif ratio > 1.5:
                score -= 5
            elif ratio < 0.5:  # Very short heavy
                score += 10
            elif ratio < 0.67:
                score += 5

        # Top trader sentiment (contrarian)
        if metrics.top_traders:
            ratio = metrics.top_traders.long_short_ratio
            if ratio > 2.0:
                score -= 5
            elif ratio < 0.5:
                score += 5

        score = max(0, min(100, score))

        if score >= 65:
            signal = "bullish"
        elif score <= 35:
            signal = "bearish"
        else:
            signal = "neutral"

        return round(score, 1), signal
