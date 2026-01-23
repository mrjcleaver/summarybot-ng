"""
Error tracking service for capturing and storing operational errors.

This module provides a centralized way to capture, log, and store
operational errors for later inspection in the dashboard.
"""

import logging
import traceback
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from functools import wraps

from ..models.error_log import ErrorLog, ErrorType, ErrorSeverity

logger = logging.getLogger(__name__)

# Global error tracker instance
_error_tracker: Optional['ErrorTracker'] = None


class ErrorTracker:
    """Service for tracking operational errors."""

    def __init__(self, retention_days: int = 7):
        """Initialize error tracker.

        Args:
            retention_days: How many days to retain errors (default 7)
        """
        self.retention_days = retention_days
        self._pending_errors: List[ErrorLog] = []  # Buffer before DB is ready
        self._repository = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the error tracker with database connection."""
        if self._initialized:
            return

        try:
            from ..data import get_error_repository
            self._repository = await get_error_repository()
            self._initialized = True

            # Flush any pending errors
            for error in self._pending_errors:
                await self._save_error(error)
            self._pending_errors.clear()

            logger.info("ErrorTracker initialized")
        except Exception as e:
            logger.warning(f"ErrorTracker could not initialize repository: {e}")

    async def _save_error(self, error: ErrorLog) -> None:
        """Save error to repository."""
        if self._repository:
            try:
                await self._repository.save_error(error)
            except Exception as e:
                logger.error(f"Failed to save error to repository: {e}")
        else:
            # Buffer until initialized
            self._pending_errors.append(error)

    async def capture_error(
        self,
        error: Exception,
        error_type: ErrorType = ErrorType.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        guild_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        operation: str = "",
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> ErrorLog:
        """Capture and store an error.

        Args:
            error: The exception that occurred
            error_type: Category of error
            severity: Error severity
            guild_id: Discord guild involved
            channel_id: Discord channel involved
            operation: What was being attempted
            user_id: User who triggered the operation
            details: Additional context

        Returns:
            The created ErrorLog
        """
        error_log = ErrorLog(
            guild_id=guild_id,
            channel_id=channel_id,
            error_type=error_type,
            severity=severity,
            error_code=self._extract_error_code(error),
            message=str(error)[:500],
            details=details or {},
            operation=operation,
            user_id=user_id,
            stack_trace=traceback.format_exc()[:2000],
        )

        # Log to standard logging as well
        log_msg = f"[{error_type.value}] {operation}: {error}"
        if severity == ErrorSeverity.CRITICAL:
            logger.critical(log_msg)
        elif severity == ErrorSeverity.ERROR:
            logger.error(log_msg)
        elif severity == ErrorSeverity.WARNING:
            logger.warning(log_msg)
        else:
            logger.info(log_msg)

        await self._save_error(error_log)
        return error_log

    async def capture_discord_error(
        self,
        error: Exception,
        guild_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        operation: str = "",
        user_id: Optional[str] = None,
    ) -> ErrorLog:
        """Capture a Discord-specific error with automatic classification.

        Args:
            error: The Discord exception
            guild_id: Guild where error occurred
            channel_id: Channel involved
            operation: What was being attempted
            user_id: User who triggered it

        Returns:
            The created ErrorLog
        """
        error_log = ErrorLog.from_discord_error(
            error=error,
            guild_id=guild_id,
            channel_id=channel_id,
            operation=operation,
            user_id=user_id,
        )

        # Log to standard logging
        log_msg = f"[Discord:{error_log.error_code}] {operation}: {error}"
        if error_log.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_msg)
        elif error_log.severity == ErrorSeverity.ERROR:
            logger.error(log_msg)
        else:
            logger.warning(log_msg)

        await self._save_error(error_log)
        return error_log

    async def log_info(
        self,
        message: str,
        guild_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        operation: str = "",
        details: Optional[Dict[str, Any]] = None,
    ) -> ErrorLog:
        """Log an informational event (not an error)."""
        error_log = ErrorLog(
            guild_id=guild_id,
            channel_id=channel_id,
            error_type=ErrorType.UNKNOWN,
            severity=ErrorSeverity.INFO,
            message=message[:500],
            details=details or {},
            operation=operation,
        )

        logger.info(f"[INFO] {operation}: {message}")
        await self._save_error(error_log)
        return error_log

    async def cleanup_old_errors(self) -> int:
        """Delete errors older than retention period.

        Returns:
            Number of errors deleted
        """
        if not self._repository:
            return 0

        try:
            deleted = await self._repository.delete_old_errors(self.retention_days)
            if deleted > 0:
                logger.info(f"Cleaned up {deleted} old errors (>{self.retention_days} days)")
            return deleted
        except Exception as e:
            logger.error(f"Failed to cleanup old errors: {e}")
            return 0

    def _extract_error_code(self, error: Exception) -> Optional[str]:
        """Extract error code from exception."""
        # Discord.py specific
        if hasattr(error, 'status'):
            return str(error.status)
        if hasattr(error, 'code'):
            return str(error.code)
        return None


def get_error_tracker() -> ErrorTracker:
    """Get or create the global error tracker instance."""
    global _error_tracker
    if _error_tracker is None:
        retention_days = int(os.environ.get("ERROR_RETENTION_DAYS", "7"))
        _error_tracker = ErrorTracker(retention_days=retention_days)
    return _error_tracker


async def initialize_error_tracker() -> ErrorTracker:
    """Initialize and return the global error tracker."""
    tracker = get_error_tracker()
    await tracker.initialize()
    return tracker


# Convenience decorator for error tracking
def track_errors(
    operation: str,
    error_type: ErrorType = ErrorType.UNKNOWN,
    guild_id_arg: Optional[str] = None,
    channel_id_arg: Optional[str] = None,
):
    """Decorator to automatically track errors from a function.

    Args:
        operation: Description of the operation
        error_type: Type of errors to expect
        guild_id_arg: Name of argument containing guild_id
        channel_id_arg: Name of argument containing channel_id

    Example:
        @track_errors("fetch_messages", ErrorType.DISCORD_PERMISSION, "guild_id", "channel_id")
        async def fetch_messages(guild_id, channel_id):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                tracker = get_error_tracker()

                # Extract guild_id and channel_id from arguments
                guild_id = None
                channel_id = None

                if guild_id_arg:
                    guild_id = kwargs.get(guild_id_arg)
                if channel_id_arg:
                    channel_id = kwargs.get(channel_id_arg)

                await tracker.capture_error(
                    error=e,
                    error_type=error_type,
                    guild_id=guild_id,
                    channel_id=channel_id,
                    operation=operation,
                )
                raise  # Re-raise the exception

        return wrapper
    return decorator
