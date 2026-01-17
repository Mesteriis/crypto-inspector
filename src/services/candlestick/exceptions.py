"""Custom exceptions for the candlestick service."""


class CandlestickServiceError(Exception):
    """Base exception for candlestick service errors."""

    def __init__(self, message: str, exchange: str | None = None) -> None:
        self.message = message
        self.exchange = exchange
        super().__init__(self.message)


class ExchangeConnectionError(CandlestickServiceError):
    """Raised when unable to connect to an exchange."""

    def __init__(self, exchange: str, reason: str | None = None) -> None:
        message = f"Failed to connect to {exchange}"
        if reason:
            message += f": {reason}"
        super().__init__(message=message, exchange=exchange)


class ExchangeAPIError(CandlestickServiceError):
    """Raised when an exchange API returns an error response."""

    def __init__(
        self,
        exchange: str,
        status_code: int | None = None,
        error_message: str | None = None,
    ) -> None:
        self.status_code = status_code
        message = f"API error from {exchange}"
        if status_code:
            message += f" (status: {status_code})"
        if error_message:
            message += f": {error_message}"
        super().__init__(message=message, exchange=exchange)


class ExchangeRateLimitError(CandlestickServiceError):
    """Raised when an exchange rate limit is exceeded."""

    def __init__(self, exchange: str, retry_after: int | None = None) -> None:
        self.retry_after = retry_after
        message = f"Rate limit exceeded for {exchange}"
        if retry_after:
            message += f" (retry after {retry_after}s)"
        super().__init__(message=message, exchange=exchange)


class InvalidSymbolError(CandlestickServiceError):
    """Raised when an invalid trading symbol is requested."""

    def __init__(self, exchange: str, symbol: str) -> None:
        self.symbol = symbol
        message = f"Invalid symbol '{symbol}' for {exchange}"
        super().__init__(message=message, exchange=exchange)


class DataParsingError(CandlestickServiceError):
    """Raised when unable to parse candlestick data from exchange response."""

    def __init__(self, exchange: str, reason: str | None = None) -> None:
        message = f"Failed to parse candlestick data from {exchange}"
        if reason:
            message += f": {reason}"
        super().__init__(message=message, exchange=exchange)


class NoDataAvailableError(CandlestickServiceError):
    """Raised when no candlestick data is available for the requested parameters."""

    def __init__(
        self,
        exchange: str | None = None,
        symbol: str | None = None,
        reason: str | None = None,
    ) -> None:
        self.symbol = symbol
        if exchange:
            message = f"No data available from {exchange}"
        else:
            message = "No data available from any exchange"
        if symbol:
            message += f" for {symbol}"
        if reason:
            message += f": {reason}"
        super().__init__(message=message, exchange=exchange)


class AllExchangesFailedError(CandlestickServiceError):
    """Raised when all exchanges fail to provide data."""

    def __init__(self, errors: dict[str, Exception]) -> None:
        self.errors = errors
        exchange_errors = [f"{ex}: {str(err)}" for ex, err in errors.items()]
        message = "All exchanges failed to provide data:\n  " + "\n  ".join(exchange_errors)
        super().__init__(message=message, exchange=None)


class RequestTimeoutError(CandlestickServiceError):
    """Raised when a request times out."""

    def __init__(self, exchange: str, timeout_seconds: float) -> None:
        self.timeout_seconds = timeout_seconds
        message = f"Request to {exchange} timed out after {timeout_seconds}s"
        super().__init__(message=message, exchange=exchange)


class UnsupportedIntervalError(CandlestickServiceError):
    """Raised when an exchange doesn't support the requested interval."""

    def __init__(self, exchange: str, interval: str) -> None:
        self.interval = interval
        message = f"Interval '{interval}' is not supported by {exchange}"
        super().__init__(message=message, exchange=exchange)
