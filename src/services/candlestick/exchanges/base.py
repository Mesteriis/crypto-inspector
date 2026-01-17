"""Abstract base class for exchange adapters."""

import logging
from abc import ABC, abstractmethod
from typing import Any

import httpx

from services.candlestick.exceptions import (
    DataParsingError,
    ExchangeAPIError,
    ExchangeConnectionError,
    ExchangeRateLimitError,
    RequestTimeoutError,
)
from services.candlestick.models import CandleInterval, Candlestick

logger = logging.getLogger(__name__)


class BaseExchange(ABC):
    """
    Abstract base class for cryptocurrency exchange adapters.

    Each exchange adapter must implement the required abstract methods
    to provide candlestick data in a standardized format.
    """

    # Exchange identifier (must be overridden by subclasses)
    EXCHANGE_NAME: str = "base"

    # Base URL for API requests (must be overridden by subclasses)
    BASE_URL: str = ""

    # Default request timeout in seconds
    DEFAULT_TIMEOUT: float = 10.0

    # Mapping from CandleInterval to exchange-specific interval strings
    INTERVAL_MAP: dict[CandleInterval, str] = {}

    def __init__(self, timeout: float | None = None) -> None:
        """
        Initialize the exchange adapter.

        Args:
            timeout: Request timeout in seconds. Defaults to DEFAULT_TIMEOUT.
        """
        self.timeout = timeout or self.DEFAULT_TIMEOUT
        self._client: httpx.AsyncClient | None = None

    @property
    def name(self) -> str:
        """Return the exchange name."""
        return self.EXCHANGE_NAME

    async def get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                timeout=httpx.Timeout(self.timeout),
                headers=self._get_default_headers(),
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _get_default_headers(self) -> dict[str, str]:
        """Return default headers for API requests."""
        return {
            "Accept": "application/json",
            "User-Agent": "crypto-inspect/1.0",
        }

    def get_interval_string(self, interval: CandleInterval) -> str:
        """
        Convert a CandleInterval to the exchange-specific interval string.

        Args:
            interval: The standardized candle interval.

        Returns:
            Exchange-specific interval string.

        Raises:
            UnsupportedIntervalError: If the interval is not supported.
        """
        if interval not in self.INTERVAL_MAP:
            # Default to using the interval value directly
            return interval.value
        return self.INTERVAL_MAP[interval]

    def convert_symbol(self, symbol: str) -> str:
        """
        Convert a standardized symbol (e.g., BTC/USDT) to exchange format.

        Default implementation removes the slash. Override in subclasses
        if the exchange uses a different format.

        Args:
            symbol: Trading pair in standard format (e.g., "BTC/USDT").

        Returns:
            Exchange-specific symbol format.
        """
        return symbol.replace("/", "")

    @abstractmethod
    async def fetch_candlesticks(
        self,
        symbol: str,
        interval: CandleInterval,
        limit: int = 100,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> list[Candlestick]:
        """
        Fetch candlestick data from the exchange.

        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT").
            interval: Candlestick interval/granularity.
            limit: Maximum number of candlesticks to fetch.
            start_time: Start timestamp in milliseconds (inclusive).
            end_time: End timestamp in milliseconds (inclusive).

        Returns:
            List of Candlestick objects sorted by timestamp ascending.

        Raises:
            ExchangeConnectionError: If unable to connect to the exchange.
            ExchangeAPIError: If the API returns an error response.
            ExchangeRateLimitError: If rate limit is exceeded.
            InvalidSymbolError: If the symbol is not valid.
            DataParsingError: If unable to parse the response.
        """
        pass

    @abstractmethod
    def _parse_candlesticks(self, data: Any) -> list[Candlestick]:
        """
        Parse raw API response data into Candlestick objects.

        Args:
            data: Raw response data from the exchange API.

        Returns:
            List of Candlestick objects.

        Raises:
            DataParsingError: If unable to parse the data.
        """
        pass

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """
        Make an HTTP request to the exchange API.

        Args:
            method: HTTP method (GET, POST, etc.).
            endpoint: API endpoint path.
            params: Query parameters.

        Returns:
            Parsed JSON response data.

        Raises:
            ExchangeConnectionError: If unable to connect.
            ExchangeAPIError: If API returns an error.
            ExchangeRateLimitError: If rate limited.
            RequestTimeoutError: If request times out.
        """
        client = await self.get_client()

        try:
            logger.debug(
                f"[{self.EXCHANGE_NAME}] Making {method} request to {endpoint} "
                f"with params: {params}"
            )

            response = await client.request(method, endpoint, params=params)

            # Handle rate limiting
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                raise ExchangeRateLimitError(
                    exchange=self.EXCHANGE_NAME,
                    retry_after=int(retry_after) if retry_after else None,
                )

            # Handle other errors
            if response.status_code >= 400:
                error_msg = None
                try:
                    error_data = response.json()
                    error_msg = str(error_data)
                except Exception:
                    error_msg = response.text[:200] if response.text else None

                raise ExchangeAPIError(
                    exchange=self.EXCHANGE_NAME,
                    status_code=response.status_code,
                    error_message=error_msg,
                )

            return response.json()

        except httpx.TimeoutException as e:
            logger.warning(f"[{self.EXCHANGE_NAME}] Request timeout: {e}")
            raise RequestTimeoutError(
                exchange=self.EXCHANGE_NAME,
                timeout_seconds=self.timeout,
            ) from e

        except httpx.ConnectError as e:
            logger.warning(f"[{self.EXCHANGE_NAME}] Connection error: {e}")
            raise ExchangeConnectionError(
                exchange=self.EXCHANGE_NAME,
                reason=str(e),
            ) from e

        except (ExchangeAPIError, ExchangeRateLimitError, RequestTimeoutError):
            raise

        except Exception as e:
            logger.error(f"[{self.EXCHANGE_NAME}] Unexpected error: {e}")
            raise ExchangeConnectionError(
                exchange=self.EXCHANGE_NAME,
                reason=str(e),
            ) from e

    def _safe_parse(self, parse_func: callable, data: Any, field_name: str) -> Any:
        """
        Safely parse a field value with error handling.

        Args:
            parse_func: Function to parse the value.
            data: Data to parse.
            field_name: Name of the field (for error messages).

        Returns:
            Parsed value.

        Raises:
            DataParsingError: If parsing fails.
        """
        try:
            return parse_func(data)
        except Exception as e:
            raise DataParsingError(
                exchange=self.EXCHANGE_NAME,
                reason=f"Failed to parse {field_name}: {e}",
            ) from e
