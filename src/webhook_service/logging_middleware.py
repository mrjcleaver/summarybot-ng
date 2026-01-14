"""
FastAPI middleware for command logging in webhook service.
"""

import logging
import time
from typing import Callable, Optional, Dict, Any
from datetime import datetime

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ..logging import CommandLogger, CommandType, CommandStatus
from ..logging.models import CommandLog

logger = logging.getLogger(__name__)


class WebhookLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging webhook requests.

    Automatically logs all incoming webhook requests with:
    - Request parameters and headers
    - Response status and duration
    - Error details if applicable
    """

    def __init__(
        self,
        app: ASGIApp,
        command_logger: Optional[CommandLogger] = None
    ):
        """
        Initialize logging middleware.

        Args:
            app: FastAPI application
            command_logger: CommandLogger instance for audit logging
        """
        super().__init__(app)
        self.command_logger = command_logger

    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """
        Process request and log execution.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler

        Returns:
            HTTP response
        """
        # Skip logging if no logger configured or for health check endpoints
        if not self.command_logger or request.url.path in ["/health", "/metrics"]:
            return await call_next(request)

        # Extract request data
        guild_id = ""
        channel_id = ""
        parameters = {}

        # Try to extract guild_id and channel_id from request
        try:
            # For POST/PUT requests with JSON body
            if request.method in ["POST", "PUT", "PATCH"]:
                # Store body for later access by handler
                body = await request.body()
                request._body = body

                # Try to parse JSON
                try:
                    import json
                    body_data = json.loads(body.decode())
                    guild_id = body_data.get("guild_id", "")
                    channel_id = body_data.get("channel_id", "")

                    # Store sanitized parameters
                    parameters = {
                        "method": request.method,
                        "path": request.url.path,
                        "guild_id": guild_id,
                        "channel_id": channel_id,
                        "message_count": body_data.get("message_count", 0) if "messages" in body_data else None,
                        "options": body_data.get("options", {})
                    }
                except (json.JSONDecodeError, UnicodeDecodeError):
                    logger.debug("Could not parse request body as JSON")

            # For GET requests with query parameters
            elif request.method == "GET":
                query_params = dict(request.query_params)
                guild_id = query_params.get("guild_id", "")
                channel_id = query_params.get("channel_id", "")
                parameters = {
                    "method": request.method,
                    "path": request.url.path,
                    "query_params": query_params
                }

        except Exception as e:
            logger.warning(f"Failed to extract request parameters: {e}")

        # Extract execution context from headers
        execution_context = {
            "source_ip": request.client.host if request.client else "",
            "user_agent": request.headers.get("user-agent", ""),
            "request_id": request.headers.get("x-request-id", ""),
            "content_type": request.headers.get("content-type", ""),
            "method": request.method,
            "path": request.url.path
        }

        # Create log entry
        log_entry = await self.command_logger.log_command(
            command_type=CommandType.WEBHOOK_REQUEST,
            command_name=f"{request.method} {request.url.path}",
            user_id=None,  # Webhooks don't have user_id
            guild_id=guild_id,
            channel_id=channel_id,
            parameters=parameters,
            execution_context=execution_context
        )

        # Execute request
        start_time = time.time()
        error_occurred = False
        error_code = None
        error_message = None

        try:
            response = await call_next(request)

            # Determine status based on response code
            if response.status_code < 400:
                status = CommandStatus.SUCCESS
            elif response.status_code < 500:
                status = CommandStatus.FAILED
                error_occurred = True
                error_code = f"HTTP_{response.status_code}"
                error_message = f"Client error: {response.status_code}"
            else:
                status = CommandStatus.FAILED
                error_occurred = True
                error_code = f"HTTP_{response.status_code}"
                error_message = f"Server error: {response.status_code}"

            # Complete log entry
            duration_ms = int((time.time() - start_time) * 1000)

            result_summary = {
                "status_code": response.status_code,
                "duration_ms": duration_ms
            }

            if error_occurred:
                await self.command_logger.fail_log(
                    log_entry,
                    error_code=error_code,
                    error_message=error_message
                )
            else:
                await self.command_logger.complete_log(log_entry, result_summary)

            return response

        except Exception as e:
            # Log exception
            duration_ms = int((time.time() - start_time) * 1000)

            error_code = type(e).__name__
            error_message = str(e)

            await self.command_logger.fail_log(
                log_entry,
                error_code=error_code,
                error_message=error_message
            )

            # Re-raise to let FastAPI handle it
            raise


def create_logging_middleware(command_logger: Optional[CommandLogger] = None):
    """
    Factory function to create logging middleware.

    Args:
        command_logger: CommandLogger instance

    Returns:
        Middleware factory function
    """
    def middleware_factory(app: ASGIApp):
        return WebhookLoggingMiddleware(app, command_logger)

    return middleware_factory
