"""API middleware for error handling and request processing.

Provides:
- Global exception handlers with HA notifications
- Request logging middleware
- CORS configuration
"""

import asyncio
import logging
import time
from collections.abc import Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from core.exceptions import CryptoInspectError

logger = logging.getLogger(__name__)


def setup_exception_handlers(app: FastAPI) -> None:
    """Register exception handlers on FastAPI app.

    Args:
        app: FastAPI application instance
    """

    @app.exception_handler(CryptoInspectError)
    async def crypto_inspect_exception_handler(
        request: Request,
        exc: CryptoInspectError,
    ) -> JSONResponse:
        """Handle all CryptoInspect exceptions.

        - Logs the error with appropriate level
        - Sends HA notification if configured
        - Returns structured JSON response
        """
        # Log with configured level
        log_func = getattr(logger, exc.log_level, logger.error)
        log_func(
            f"{exc.__class__.__name__}: {exc.message}",
            extra={
                "context": exc.context,
                "path": request.url.path,
                "method": request.method,
            },
        )

        # Send HA notification asynchronously (don't block response)
        if exc.notify_ha:
            asyncio.create_task(_safe_ha_notification(exc))

        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict(),
        )

    @app.exception_handler(PydanticValidationError)
    async def pydantic_validation_handler(
        request: Request,
        exc: PydanticValidationError,
    ) -> JSONResponse:
        """Handle Pydantic validation errors.

        Converts Pydantic errors to our ValidationError format.
        """
        errors = exc.errors()
        message = "; ".join(f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}" for e in errors)

        logger.warning(
            f"Validation error: {message}",
            extra={"path": request.url.path},
        )

        return JSONResponse(
            status_code=400,
            content={
                "error": "ValidationError",
                "message": message,
                "details": errors,
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """Handle all unhandled exceptions.

        - Logs full traceback
        - ALWAYS sends HA notification (critical error)
        - Returns generic error response (no sensitive info)
        """
        logger.exception(
            f"Unhandled exception: {exc}",
            extra={
                "path": request.url.path,
                "method": request.method,
            },
        )

        # Critical error - always notify HA
        asyncio.create_task(
            _notify_critical_error(
                error_message=str(exc),
                context=f"Endpoint: {request.url.path}",
            )
        )

        return JSONResponse(
            status_code=500,
            content={
                "error": "InternalError",
                "message": "Internal server error",
                "message_ru": "Внутренняя ошибка сервера",
            },
        )


async def _safe_ha_notification(exc: CryptoInspectError) -> None:
    """Send HA notification safely (catches all errors).

    Args:
        exc: Exception to notify about
    """
    try:
        await exc.send_ha_notification()
    except Exception as e:
        logger.warning(f"Failed to send HA notification: {e}")


async def _notify_critical_error(error_message: str, context: str = "") -> None:
    """Send critical error notification to HA.

    Args:
        error_message: Error message
        context: Additional context
    """
    try:
        from service.ha_integration import notify_error

        await notify_error(error_message=error_message, context=context)
    except ImportError:
        logger.debug("HA integration not available")
    except Exception as e:
        logger.warning(f"Failed to send critical error notification: {e}")


class RequestLoggingMiddleware:
    """Middleware for request/response logging.

    Logs:
    - Request method and path
    - Response status code
    - Request duration
    """

    def __init__(self, app: FastAPI):
        self.app = app

    async def __call__(self, request: Request, call_next: Callable):
        start_time = time.time()

        response = await call_next(request)

        duration = time.time() - start_time

        # Log slow requests (> 1s)
        if duration > 1.0:
            logger.warning(
                f"Slow request: {request.method} {request.url.path} ({duration:.2f}s) -> {response.status_code}"
            )
        else:
            logger.debug(f"{request.method} {request.url.path} ({duration:.3f}s) -> {response.status_code}")

        return response
