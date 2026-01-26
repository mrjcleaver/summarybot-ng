"""
Error logging models for operational error tracking.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from .base import BaseModel, generate_id, utc_now


class ErrorType(Enum):
    """Types of operational errors."""
    DISCORD_PERMISSION = "discord_permission"  # 403 Missing Access, etc.
    DISCORD_NOT_FOUND = "discord_not_found"    # Channel/Guild not found
    DISCORD_RATE_LIMIT = "discord_rate_limit"  # Rate limited
    DISCORD_CONNECTION = "discord_connection"  # Connection issues
    API_ERROR = "api_error"                    # External API failures
    DATABASE_ERROR = "database_error"          # Database operations
    SUMMARIZATION_ERROR = "summarization_error"  # LLM/summarization failures
    MODEL_FALLBACK = "model_fallback"          # Model unavailable, used fallback
    SCHEDULE_ERROR = "schedule_error"          # Scheduled task failures
    WEBHOOK_ERROR = "webhook_error"            # Webhook delivery failures
    AUTHENTICATION_ERROR = "authentication_error"  # Auth failures
    VALIDATION_ERROR = "validation_error"      # Input validation
    UNKNOWN = "unknown"                        # Catch-all


class ErrorSeverity(Enum):
    """Severity levels for errors."""
    INFO = "info"          # Informational, not a problem
    WARNING = "warning"    # Something to watch, not critical
    ERROR = "error"        # Operation failed but system continues
    CRITICAL = "critical"  # Serious issue requiring attention


@dataclass
class ErrorLog(BaseModel):
    """Operational error log entry.

    Attributes:
        id: Unique error identifier
        guild_id: Discord guild where error occurred (if applicable)
        channel_id: Discord channel involved (if applicable)
        error_type: Category of error
        severity: Error severity level
        error_code: Specific error code (e.g., "403", "MISSING_ACCESS")
        message: Human-readable error message
        details: Additional error details/context as JSON
        operation: What operation was being attempted
        user_id: User who triggered the operation (if applicable)
        stack_trace: Optional stack trace for debugging
        created_at: When the error occurred
        resolved_at: When the error was resolved (if applicable)
        resolution_notes: How the error was resolved
    """
    id: str = field(default_factory=generate_id)
    guild_id: Optional[str] = None
    channel_id: Optional[str] = None
    error_type: ErrorType = ErrorType.UNKNOWN
    severity: ErrorSeverity = ErrorSeverity.ERROR
    error_code: Optional[str] = None
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    operation: str = ""
    user_id: Optional[str] = None
    stack_trace: Optional[str] = None
    created_at: datetime = field(default_factory=utc_now)
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None

    def __post_init__(self):
        """Convert string enums if needed."""
        if isinstance(self.error_type, str):
            self.error_type = ErrorType(self.error_type)
        if isinstance(self.severity, str):
            self.severity = ErrorSeverity(self.severity)

    @property
    def is_resolved(self) -> bool:
        """Check if error has been resolved."""
        return self.resolved_at is not None

    def resolve(self, notes: Optional[str] = None) -> None:
        """Mark error as resolved."""
        self.resolved_at = utc_now()
        self.resolution_notes = notes

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "guild_id": self.guild_id,
            "channel_id": self.channel_id,
            "error_type": self.error_type.value if isinstance(self.error_type, ErrorType) else self.error_type,
            "severity": self.severity.value if isinstance(self.severity, ErrorSeverity) else self.severity,
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
            "operation": self.operation,
            "user_id": self.user_id,
            "stack_trace": self.stack_trace,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolution_notes": self.resolution_notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ErrorLog':
        """Create instance from dictionary."""
        # Handle datetime conversion
        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if isinstance(data.get("resolved_at"), str) and data["resolved_at"]:
            data["resolved_at"] = datetime.fromisoformat(data["resolved_at"])

        # Handle enum conversion
        if isinstance(data.get("error_type"), str):
            data["error_type"] = ErrorType(data["error_type"])
        if isinstance(data.get("severity"), str):
            data["severity"] = ErrorSeverity(data["severity"])

        return cls(**data)

    @classmethod
    def from_discord_error(
        cls,
        error: Exception,
        guild_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        operation: str = "",
        user_id: Optional[str] = None,
    ) -> 'ErrorLog':
        """Create error log from Discord exception.

        Args:
            error: The Discord exception
            guild_id: Guild where error occurred
            channel_id: Channel involved
            operation: What was being attempted
            user_id: User who triggered it

        Returns:
            ErrorLog instance
        """
        import traceback

        # Determine error type and extract details
        error_type = ErrorType.UNKNOWN
        severity = ErrorSeverity.ERROR
        error_code = None
        details = {}

        error_str = str(error)
        error_class = error.__class__.__name__

        # Discord.py specific error handling
        if hasattr(error, 'status'):
            status = error.status
            error_code = str(status)

            if status == 403:
                error_type = ErrorType.DISCORD_PERMISSION
                if "Missing Access" in error_str:
                    details["reason"] = "Bot lacks permission to access this channel"
                elif "Missing Permissions" in error_str:
                    details["reason"] = "Bot lacks required permissions"
            elif status == 404:
                error_type = ErrorType.DISCORD_NOT_FOUND
                details["reason"] = "Resource not found (channel/message deleted?)"
            elif status == 429:
                error_type = ErrorType.DISCORD_RATE_LIMIT
                severity = ErrorSeverity.WARNING
                details["reason"] = "Rate limited by Discord"
            elif status >= 500:
                error_type = ErrorType.DISCORD_CONNECTION
                details["reason"] = "Discord server error"

        elif "ConnectionClosed" in error_class or "ConnectionError" in error_class:
            error_type = ErrorType.DISCORD_CONNECTION
            details["reason"] = "Connection to Discord lost"

        return cls(
            guild_id=guild_id,
            channel_id=channel_id,
            error_type=error_type,
            severity=severity,
            error_code=error_code,
            message=error_str[:500],  # Limit message length
            details=details,
            operation=operation,
            user_id=user_id,
            stack_trace=traceback.format_exc()[:2000],  # Limit stack trace
        )


@dataclass
class ErrorSummary:
    """Summary of errors for a time period."""
    total_count: int = 0
    by_type: Dict[str, int] = field(default_factory=dict)
    by_severity: Dict[str, int] = field(default_factory=dict)
    by_guild: Dict[str, int] = field(default_factory=dict)
    recent_errors: List[ErrorLog] = field(default_factory=list)
    unresolved_count: int = 0
