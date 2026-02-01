"""Exception hierarchy for crypto-inspect.

Provides structured exceptions with:
- Automatic Home Assistant notifications for critical errors
- HTTP status code mapping
- Bilingual error messages
- Contextual information for debugging
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class CryptoInspectError(Exception):
    """Base exception for all crypto-inspect errors.

    Features:
    - Optional automatic HA notification
    - HTTP status code for API responses
    - Contextual information
    - Bilingual messages

    Attributes:
        message: Error message (English)
        message_ru: Error message (Russian)
        context: Additional context for debugging
        notify_ha: Whether to send notification to Home Assistant
        status_code: HTTP status code for API responses
        log_level: Logging level for this exception
    """

    notify_ha: bool = False
    status_code: int = 500
    log_level: str = "error"

    def __init__(
        self,
        message: str,
        message_ru: str | None = None,
        context: str = "",
        notify_ha: bool | None = None,
        details: dict[str, Any] | None = None,
    ):
        """Initialize exception.

        Args:
            message: Error message in English
            message_ru: Error message in Russian (optional)
            context: Additional context (e.g., function name, symbol)
            notify_ha: Override class-level notify_ha setting
            details: Additional details for debugging
        """
        self.message = message
        self.message_ru = message_ru or message
        self.context = context
        self.details = details or {}

        if notify_ha is not None:
            self.notify_ha = notify_ha

        super().__init__(message)

    async def send_ha_notification(self) -> bool:
        """Send notification to Home Assistant.

        Sends a persistent notification to HA if notify_ha is True.
        Uses notify_error from ha_integration.

        Returns:
            True if notification was sent successfully
        """
        if not self.notify_ha:
            return False

        try:
            from service.ha_integration import notify_error

            return await notify_error(
                error_message=self.message,
                context=self.context,
            )
        except ImportError:
            logger.warning("HA integration not available for error notification")
            return False
        except Exception as e:
            logger.warning(f"Failed to send HA notification: {e}")
            return False

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for API response.

        Returns:
            Dictionary with error details
        """
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "message_ru": self.message_ru,
            "context": self.context,
            "details": self.details,
        }

    def __str__(self) -> str:
        if self.context:
            return f"{self.message} (context: {self.context})"
        return self.message


# =============================================================================
# Validation Errors (4xx)
# =============================================================================


class ValidationError(CryptoInspectError):
    """Input validation error.

    Used for invalid request parameters, malformed data, etc.
    Does NOT trigger HA notification by default.
    """

    notify_ha = False
    status_code = 400
    log_level = "warning"


class NotFoundError(CryptoInspectError):
    """Resource not found error.

    Used when requested entity doesn't exist.
    """

    notify_ha = False
    status_code = 404
    log_level = "warning"


class AuthenticationError(CryptoInspectError):
    """Authentication/authorization error.

    Used for invalid API keys, unauthorized access, etc.
    Triggers HA notification for security awareness.
    """

    notify_ha = True
    status_code = 401
    log_level = "warning"


class ConflictError(CryptoInspectError):
    """Resource conflict error.

    Used when operation conflicts with current state.
    """

    notify_ha = False
    status_code = 409
    log_level = "warning"


# =============================================================================
# Service Errors (5xx) - Trigger HA Notifications
# =============================================================================


class ServiceError(CryptoInspectError):
    """Base service layer error.

    All service errors trigger HA notifications by default.
    """

    notify_ha = True
    status_code = 500
    log_level = "error"


class ExternalAPIError(ServiceError):
    """External API call failed.

    Used when calls to external services (exchanges, data providers) fail.

    Attributes:
        api_name: Name of the external API
        original_error: Original exception from API call
    """

    def __init__(
        self,
        message: str,
        api_name: str = "",
        original_error: Exception | None = None,
        **kwargs,
    ):
        self.api_name = api_name
        self.original_error = original_error
        context = kwargs.pop("context", api_name)
        super().__init__(message, context=context, **kwargs)


class DatabaseError(ServiceError):
    """Database operation failed.

    Used for connection errors, query failures, etc.
    """

    def __init__(
        self,
        message: str,
        operation: str = "",
        **kwargs,
    ):
        self.operation = operation
        context = kwargs.pop("context", operation)
        super().__init__(message, context=context, **kwargs)


class ConfigurationError(ServiceError):
    """Configuration error.

    Used when required configuration is missing or invalid.
    """

    status_code = 503

    def __init__(
        self,
        message: str,
        setting_name: str = "",
        **kwargs,
    ):
        self.setting_name = setting_name
        context = kwargs.pop("context", f"setting: {setting_name}")
        super().__init__(message, context=context, **kwargs)


class ServiceUnavailableError(ServiceError):
    """Service temporarily unavailable.

    Used when a required service is not accessible.
    """

    status_code = 503


# =============================================================================
# Domain-Specific Errors
# =============================================================================


class ExchangeError(ExternalAPIError):
    """Exchange-related error.

    Specialized error for cryptocurrency exchange operations.
    """

    def __init__(
        self,
        message: str,
        exchange: str = "",
        symbol: str = "",
        **kwargs,
    ):
        self.exchange = exchange
        self.symbol = symbol
        api_name = f"{exchange}:{symbol}" if symbol else exchange
        super().__init__(message, api_name=api_name, **kwargs)


class AnalysisError(ServiceError):
    """Analysis computation error.

    Used when market analysis fails.
    """

    def __init__(
        self,
        message: str,
        symbol: str = "",
        analysis_type: str = "",
        **kwargs,
    ):
        self.symbol = symbol
        self.analysis_type = analysis_type
        context = f"{analysis_type}:{symbol}" if symbol else analysis_type
        super().__init__(message, context=context, **kwargs)


class HAIntegrationError(ServiceError):
    """Home Assistant integration error.

    Used when HA communication fails.
    Note: This error does NOT trigger additional HA notification
    to avoid infinite loops.
    """

    notify_ha = False  # Avoid infinite loop

    def __init__(
        self,
        message: str,
        entity_id: str = "",
        **kwargs,
    ):
        self.entity_id = entity_id
        context = kwargs.pop("context", entity_id)
        super().__init__(message, context=context, **kwargs)
