"""
Main fetcher module for concurrent candlestick data fetching.

This module implements a race/future approach where requests are sent to multiple
exchanges concurrently, and the first successful response wins while other
requests are cancelled.
"""

import asyncio
import logging
import time
from collections.abc import Sequence

from service.candlestick.exceptions import AllExchangesFailedError, CandlestickServiceError
from service.candlestick.exchanges.base import BaseExchange
from service.candlestick.exchanges.binance import BinanceExchange
from service.candlestick.exchanges.bybit import BybitExchange
from service.candlestick.exchanges.coinbase import CoinbaseExchange
from service.candlestick.exchanges.kraken import KrakenExchange
from service.candlestick.exchanges.kucoin import KucoinExchange
from service.candlestick.exchanges.okx import OKXExchange
from service.candlestick.models import CandleInterval, Candlestick, FetchResult

logger = logging.getLogger(__name__)

# Default list of exchanges to query (in priority order)
DEFAULT_EXCHANGES: list[type[BaseExchange]] = [
    BinanceExchange,
    OKXExchange,
    BybitExchange,
    CoinbaseExchange,
    KrakenExchange,
    KucoinExchange,
]


class CandlestickFetcher:
    """
    Concurrent candlestick data fetcher using race/future pattern.

    Fetches candlestick data from multiple exchanges simultaneously and returns
    the first successful result while cancelling remaining requests.
    """

    def __init__(
        self,
        exchanges: Sequence[type[BaseExchange]] | None = None,
        timeout: float = 10.0,
    ) -> None:
        """
        Initialize the fetcher.

        Args:
            exchanges: List of exchange classes to use. Defaults to DEFAULT_EXCHANGES.
            timeout: Request timeout in seconds for each exchange.
        """
        self.exchange_classes = list(exchanges or DEFAULT_EXCHANGES)
        self.timeout = timeout
        self._exchange_instances: list[BaseExchange] = []

    def _create_exchanges(self) -> list[BaseExchange]:
        """Create exchange instances."""
        return [cls(timeout=self.timeout) for cls in self.exchange_classes]

    async def _fetch_from_exchange(
        self,
        exchange: BaseExchange,
        symbol: str,
        interval: CandleInterval,
        limit: int,
        start_time: int | None,
        end_time: int | None,
    ) -> FetchResult:
        """
        Fetch candlesticks from a single exchange.

        Args:
            exchange: Exchange instance to fetch from.
            symbol: Trading pair symbol.
            interval: Candlestick interval.
            limit: Number of candlesticks to fetch.
            start_time: Start timestamp in milliseconds.
            end_time: End timestamp in milliseconds.

        Returns:
            FetchResult containing candlesticks and metadata.
        """
        start = time.perf_counter()

        try:
            logger.info(f"[{exchange.name}] Starting fetch for {symbol} {interval.value}")

            candlesticks = await exchange.fetch_candlesticks(
                symbol=symbol,
                interval=interval,
                limit=limit,
                start_time=start_time,
                end_time=end_time,
            )

            elapsed_ms = (time.perf_counter() - start) * 1000

            logger.info(
                f"[{exchange.name}] Successfully fetched {len(candlesticks)} candlesticks in {elapsed_ms:.2f}ms"
            )

            return FetchResult(
                candlesticks=candlesticks,
                exchange=exchange.name,
                symbol=symbol,
                interval=interval,
                fetch_time_ms=elapsed_ms,
            )

        except CandlestickServiceError:
            raise
        except Exception as e:
            logger.warning(f"[{exchange.name}] Fetch failed: {e}")
            raise

    async def fetch(
        self,
        symbol: str,
        interval: CandleInterval,
        limit: int = 100,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> FetchResult:
        """
        Fetch candlesticks using race/future approach.

        Sends requests to all configured exchanges concurrently and returns
        the first successful result. Remaining requests are cancelled.

        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT").
            interval: Candlestick interval/granularity.
            limit: Number of candlesticks to fetch (1-1000).
            start_time: Start timestamp in milliseconds (optional).
            end_time: End timestamp in milliseconds (optional).

        Returns:
            FetchResult containing candlesticks from the first responding exchange.

        Raises:
            AllExchangesFailedError: If all exchanges fail to provide data.
        """
        exchanges = self._create_exchanges()
        errors: dict[str, Exception] = {}
        pending_tasks: set[asyncio.Task] = set()

        try:
            # Create tasks for all exchanges
            for exchange in exchanges:
                task = asyncio.create_task(
                    self._fetch_from_exchange(
                        exchange=exchange,
                        symbol=symbol,
                        interval=interval,
                        limit=limit,
                        start_time=start_time,
                        end_time=end_time,
                    ),
                    name=f"fetch_{exchange.name}",
                )
                pending_tasks.add(task)

            logger.info(f"Racing {len(pending_tasks)} exchanges for {symbol} {interval.value}")

            # Wait for first successful result or all failures
            while pending_tasks:
                done, pending_tasks = await asyncio.wait(
                    pending_tasks,
                    return_when=asyncio.FIRST_COMPLETED,
                )

                for task in done:
                    exchange_name = task.get_name().replace("fetch_", "")

                    try:
                        result = task.result()

                        # Validate we got actual data
                        if result.candlesticks:
                            logger.info(
                                f"First successful response from {result.exchange} "
                                f"with {len(result.candlesticks)} candlesticks"
                            )

                            # Cancel remaining tasks
                            for pending_task in pending_tasks:
                                pending_task.cancel()

                            return result
                        else:
                            # Empty result, treat as failure
                            logger.warning(f"[{exchange_name}] Returned empty result")
                            errors[exchange_name] = Exception("Empty result")

                    except asyncio.CancelledError:
                        logger.debug(f"[{exchange_name}] Task cancelled")
                    except Exception as e:
                        logger.warning(f"[{exchange_name}] Failed: {e}")
                        errors[exchange_name] = e

            # All exchanges failed
            raise AllExchangesFailedError(errors=errors)

        finally:
            # Clean up: cancel any remaining tasks and close exchange connections
            for task in pending_tasks:
                if not task.done():
                    task.cancel()

            # Wait for cancellations to complete
            if pending_tasks:
                await asyncio.gather(*pending_tasks, return_exceptions=True)

            # Close all exchange connections
            for exchange in exchanges:
                try:
                    await exchange.close()
                except Exception as e:
                    logger.debug(f"Error closing {exchange.name}: {e}")

    async def fetch_with_fallback(
        self,
        symbol: str,
        interval: CandleInterval,
        limit: int = 100,
        start_time: int | None = None,
        end_time: int | None = None,
        required_count: int | None = None,
    ) -> FetchResult:
        """
        Fetch candlesticks with validation and fallback.

        Similar to fetch(), but validates that the result meets requirements.
        If the first result doesn't have enough candlesticks, continues
        waiting for other exchanges.

        Args:
            symbol: Trading pair symbol.
            interval: Candlestick interval.
            limit: Number of candlesticks to fetch.
            start_time: Start timestamp in milliseconds.
            end_time: End timestamp in milliseconds.
            required_count: Minimum required candlesticks (optional).

        Returns:
            FetchResult meeting the requirements.

        Raises:
            AllExchangesFailedError: If no exchange meets requirements.
        """
        exchanges = self._create_exchanges()
        errors: dict[str, Exception] = {}
        best_result: FetchResult | None = None
        pending_tasks: set[asyncio.Task] = set()

        min_count = required_count or (limit // 2)  # At least half requested

        try:
            # Create tasks for all exchanges
            for exchange in exchanges:
                task = asyncio.create_task(
                    self._fetch_from_exchange(
                        exchange=exchange,
                        symbol=symbol,
                        interval=interval,
                        limit=limit,
                        start_time=start_time,
                        end_time=end_time,
                    ),
                    name=f"fetch_{exchange.name}",
                )
                pending_tasks.add(task)

            # Wait for results
            while pending_tasks:
                done, pending_tasks = await asyncio.wait(
                    pending_tasks,
                    return_when=asyncio.FIRST_COMPLETED,
                )

                for task in done:
                    exchange_name = task.get_name().replace("fetch_", "")

                    try:
                        result = task.result()

                        # Check if result meets requirements
                        if len(result.candlesticks) >= min_count:
                            logger.info(
                                f"Sufficient data from {result.exchange}: {len(result.candlesticks)} candlesticks"
                            )

                            # Cancel remaining tasks
                            for pending_task in pending_tasks:
                                pending_task.cancel()

                            return result

                        # Keep track of best result so far
                        if best_result is None or len(result.candlesticks) > len(best_result.candlesticks):
                            best_result = result
                            logger.info(
                                f"Best result so far from {result.exchange}: {len(result.candlesticks)} candlesticks"
                            )

                    except asyncio.CancelledError:
                        pass
                    except Exception as e:
                        logger.warning(f"[{exchange_name}] Failed: {e}")
                        errors[exchange_name] = e

            # Return best result if we have any
            if best_result is not None:
                logger.warning(
                    f"Returning best available result from {best_result.exchange} "
                    f"with {len(best_result.candlesticks)} candlesticks "
                    f"(requested: {limit})"
                )
                return best_result

            # All failed
            raise AllExchangesFailedError(errors=errors)

        finally:
            # Clean up
            for task in pending_tasks:
                if not task.done():
                    task.cancel()

            if pending_tasks:
                await asyncio.gather(*pending_tasks, return_exceptions=True)

            for exchange in exchanges:
                try:
                    await exchange.close()
                except Exception:
                    pass


# Module-level fetcher instance for convenience
_default_fetcher: CandlestickFetcher | None = None


def get_fetcher(
    exchanges: Sequence[type[BaseExchange]] | None = None,
    timeout: float = 10.0,
) -> CandlestickFetcher:
    """
    Get or create a CandlestickFetcher instance.

    Args:
        exchanges: List of exchange classes (uses default if None).
        timeout: Request timeout in seconds.

    Returns:
        CandlestickFetcher instance.
    """
    global _default_fetcher

    if exchanges is not None or _default_fetcher is None:
        _default_fetcher = CandlestickFetcher(exchanges=exchanges, timeout=timeout)

    return _default_fetcher


async def fetch_candlesticks(
    symbol: str,
    interval: CandleInterval,
    limit: int = 100,
    start_time: int | None = None,
    end_time: int | None = None,
    timeout: float = 10.0,
    exchanges: Sequence[type[BaseExchange]] | None = None,
) -> list[Candlestick]:
    """
    Fetch candlestick data from the first responding exchange.

    This is the main entry point for the candlestick service. It sends requests
    to multiple exchanges concurrently and returns data from the first one
    that responds successfully.

    Args:
        symbol: Trading pair symbol (e.g., "BTC/USDT", "ETH/USDT").
        interval: Candlestick interval/granularity (e.g., CandleInterval.HOUR_1).
        limit: Number of candlesticks to fetch (1-1000, default 100).
        start_time: Start timestamp in milliseconds (optional).
        end_time: End timestamp in milliseconds (optional).
        timeout: Request timeout in seconds (default 10.0).
        exchanges: List of exchange classes to use (optional, uses default if None).

    Returns:
        List of Candlestick objects sorted by timestamp ascending.

    Raises:
        AllExchangesFailedError: If all exchanges fail to provide data.

    Example:
        >>> from service.candlestick import fetch_candlesticks, CandleInterval
        >>>
        >>> # Fetch last 100 hourly candles for BTC/USDT
        >>> candles = await fetch_candlesticks(
        ...     symbol="BTC/USDT",
        ...     interval=CandleInterval.HOUR_1,
        ...     limit=100,
        ... )
        >>>
        >>> for candle in candles[:5]:
        ...     print(f"{candle.timestamp}: O={candle.open_price} C={candle.close_price}")
    """
    fetcher = CandlestickFetcher(exchanges=exchanges, timeout=timeout)
    result = await fetcher.fetch(
        symbol=symbol,
        interval=interval,
        limit=limit,
        start_time=start_time,
        end_time=end_time,
    )
    return result.candlesticks


async def fetch_candlesticks_with_source(
    symbol: str,
    interval: CandleInterval,
    limit: int = 100,
    start_time: int | None = None,
    end_time: int | None = None,
    timeout: float = 10.0,
    exchanges: Sequence[type[BaseExchange]] | None = None,
) -> FetchResult:
    """
    Fetch candlestick data with source information.

    Similar to fetch_candlesticks(), but returns a FetchResult that includes
    metadata about the source exchange and fetch time.

    Args:
        symbol: Trading pair symbol.
        interval: Candlestick interval.
        limit: Number of candlesticks to fetch.
        start_time: Start timestamp in milliseconds.
        end_time: End timestamp in milliseconds.
        timeout: Request timeout in seconds.
        exchanges: List of exchange classes to use.

    Returns:
        FetchResult containing candlesticks and metadata.

    Example:
        >>> result = await fetch_candlesticks_with_source(
        ...     symbol="ETH/USDT",
        ...     interval=CandleInterval.DAY_1,
        ... )
        >>> print(f"Got {result.count} candles from {result.exchange}")
        >>> print(f"Fetch time: {result.fetch_time_ms:.2f}ms")
    """
    fetcher = CandlestickFetcher(exchanges=exchanges, timeout=timeout)
    return await fetcher.fetch(
        symbol=symbol,
        interval=interval,
        limit=limit,
        start_time=start_time,
        end_time=end_time,
    )
