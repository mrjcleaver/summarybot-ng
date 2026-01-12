# Command Logging System - Pseudocode Implementation

## Table of Contents
1. [Data Models](#1-data-models)
2. [Sanitizer Implementation](#2-sanitizer-implementation)
3. [Logger Core](#3-logger-core)
4. [Repository Layer](#4-repository-layer)
5. [Decorators and Middleware](#5-decorators-and-middleware)
6. [Integration Points](#6-integration-points)
7. [Query Interface](#7-query-interface)
8. [Cleanup and Maintenance](#8-cleanup-and-maintenance)

---

## 1. Data Models

### 1.1 CommandLog Model

```python
"""
File: src/logging/models.py
Purpose: Data models for command logging system
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from ..models.base import BaseModel, generate_id


class CommandType(Enum):
    """Types of commands that can be logged."""
    SLASH_COMMAND = "slash_command"
    SCHEDULED_TASK = "scheduled_task"
    WEBHOOK_REQUEST = "webhook_request"


class CommandStatus(Enum):
    """Execution status of a command."""
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class CommandLog(BaseModel):
    """
    Represents a logged command execution.

    This model captures all relevant information about a command execution
    including context, parameters, timing, and results.
    """

    # Identity and classification
    id: str = field(default_factory=generate_id)
    command_type: CommandType = CommandType.SLASH_COMMAND
    command_name: str = ""

    # Context
    user_id: Optional[str] = None  # Null for scheduled tasks
    guild_id: str = ""
    channel_id: str = ""

    # Execution data
    parameters: Dict[str, Any] = field(default_factory=dict)
    execution_context: Dict[str, Any] = field(default_factory=dict)

    # Results
    status: CommandStatus = CommandStatus.SUCCESS
    error_code: Optional[str] = None
    error_message: Optional[str] = None

    # Timing
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None

    # Output
    result_summary: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def mark_completed(self, result_summary: Dict[str, Any] = None) -> None:
        """Mark command execution as completed successfully."""
        self.completed_at = datetime.utcnow()
        self.duration_ms = int(
            (self.completed_at - self.started_at).total_seconds() * 1000
        )
        self.status = CommandStatus.SUCCESS
        if result_summary:
            self.result_summary = result_summary

    def mark_failed(self, error_code: str, error_message: str) -> None:
        """Mark command execution as failed."""
        self.completed_at = datetime.utcnow()
        self.duration_ms = int(
            (self.completed_at - self.started_at).total_seconds() * 1000
        )
        self.status = CommandStatus.FAILED
        self.error_code = error_code
        self.error_message = error_message

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            "id": self.id,
            "command_type": self.command_type.value,
            "command_name": self.command_name,
            "user_id": self.user_id,
            "guild_id": self.guild_id,
            "channel_id": self.channel_id,
            "parameters": json.dumps(self.parameters),
            "execution_context": json.dumps(self.execution_context),
            "status": self.status.value,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "result_summary": json.dumps(self.result_summary) if self.result_summary else None,
            "metadata": json.dumps(self.metadata)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CommandLog':
        """Create instance from database row."""
        import json
        from datetime import datetime

        return cls(
            id=data["id"],
            command_type=CommandType(data["command_type"]),
            command_name=data["command_name"],
            user_id=data.get("user_id"),
            guild_id=data["guild_id"],
            channel_id=data["channel_id"],
            parameters=json.loads(data["parameters"]) if data["parameters"] else {},
            execution_context=json.loads(data["execution_context"]) if data["execution_context"] else {},
            status=CommandStatus(data["status"]),
            error_code=data.get("error_code"),
            error_message=data.get("error_message"),
            started_at=datetime.fromisoformat(data["started_at"]),
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            duration_ms=data.get("duration_ms"),
            result_summary=json.loads(data["result_summary"]) if data.get("result_summary") else {},
            metadata=json.loads(data["metadata"]) if data["metadata"] else {}
        )


@dataclass
class LoggingConfig:
    """Configuration for command logging."""

    enabled: bool = True
    retention_days: int = 90
    async_writes: bool = True
    batch_size: int = 100
    sanitize_enabled: bool = True
    max_message_length: int = 200
    redact_patterns: List[str] = field(default_factory=lambda: [
        "token", "secret", "key", "password", "api_key"
    ])
```

---

## 2. Sanitizer Implementation

### 2.1 Log Sanitizer

```python
"""
File: src/logging/sanitizer.py
Purpose: Sanitize sensitive data before logging
"""

import re
import hashlib
import json
from typing import Any, Dict, List, Pattern
import logging

logger = logging.getLogger(__name__)


class LogSanitizer:
    """
    Sanitizes sensitive data in log entries.

    Responsibilities:
    - Redact API keys, tokens, passwords
    - Hash webhook signatures
    - Truncate message content
    - Mask PII (emails, IPs)
    """

    def __init__(self, config: LoggingConfig):
        self.config = config
        self._redact_patterns = self._compile_redact_patterns()

    def _compile_redact_patterns(self) -> List[Pattern]:
        """Compile regex patterns for redaction."""
        patterns = []
        for pattern_str in self.config.redact_patterns:
            try:
                # Case-insensitive pattern matching
                pattern = re.compile(pattern_str, re.IGNORECASE)
                patterns.append(pattern)
            except re.error as e:
                logger.warning(f"Invalid redact pattern '{pattern_str}': {e}")
        return patterns

    def sanitize_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize command parameters.

        Algorithm:
        1. Iterate through all key-value pairs
        2. Check if key matches redaction patterns
        3. Redact or sanitize based on data type
        4. Recursively sanitize nested dictionaries
        """
        if not self.config.sanitize_enabled:
            return parameters

        sanitized = {}

        for key, value in parameters.items():
            # Check if key matches redaction pattern
            if self._should_redact_key(key):
                sanitized[key] = "[REDACTED]"

            # Recursively sanitize nested dicts
            elif isinstance(value, dict):
                sanitized[key] = self.sanitize_parameters(value)

            # Sanitize lists
            elif isinstance(value, list):
                sanitized[key] = [
                    self.sanitize_parameters(item) if isinstance(item, dict) else item
                    for item in value
                ]

            # Truncate long strings
            elif isinstance(value, str) and len(value) > self.config.max_message_length:
                sanitized[key] = self._truncate_string(value)

            else:
                sanitized[key] = value

        return sanitized

    def _should_redact_key(self, key: str) -> bool:
        """Check if a key should be redacted."""
        for pattern in self._redact_patterns:
            if pattern.search(key):
                return True
        return False

    def _truncate_string(self, text: str) -> str:
        """Truncate long strings with ellipsis."""
        max_len = self.config.max_message_length
        if len(text) <= max_len:
            return text
        return text[:max_len] + "... [truncated]"

    def sanitize_error_message(self, error_message: str) -> str:
        """
        Sanitize error messages to remove sensitive data.

        Checks for:
        - File paths that might contain usernames
        - Connection strings
        - API endpoints with tokens
        """
        if not error_message:
            return error_message

        # Redact file paths
        sanitized = re.sub(
            r'/home/[^/]+/',
            '/home/[user]/',
            error_message
        )

        # Redact URLs with tokens
        sanitized = re.sub(
            r'(https?://[^?]+\?[^=]+=)[^&\s]+',
            r'\1[REDACTED]',
            sanitized
        )

        return self._truncate_string(sanitized)

    def hash_signature(self, signature: str) -> str:
        """Hash webhook signatures for verification without storage."""
        if not signature:
            return ""

        hash_obj = hashlib.sha256(signature.encode('utf-8'))
        return f"sha256:{hash_obj.hexdigest()[:16]}..."

    def mask_ip_address(self, ip_address: str) -> str:
        """Mask IP address for privacy."""
        if not ip_address:
            return ""

        # IPv4: 192.168.1.1 -> 192.168.*.**
        parts = ip_address.split('.')
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.*.***"

        # IPv6: Mask last 64 bits
        if ':' in ip_address:
            parts = ip_address.split(':')
            if len(parts) >= 4:
                return ':'.join(parts[:4]) + ':****:****:****:****'

        return "[MASKED_IP]"

    def sanitize_execution_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize execution context.

        Special handling:
        - IP addresses are masked
        - Signatures are hashed
        - User agents are preserved (useful for debugging)
        """
        sanitized = context.copy()

        if "source_ip" in sanitized:
            sanitized["source_ip"] = self.mask_ip_address(sanitized["source_ip"])

        if "signature" in sanitized:
            sanitized["signature_hash"] = self.hash_signature(sanitized["signature"])
            del sanitized["signature"]

        if "headers" in sanitized and isinstance(sanitized["headers"], dict):
            sanitized["headers"] = self._sanitize_headers(sanitized["headers"])

        return sanitized

    def _sanitize_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Sanitize HTTP headers."""
        sanitized = {}

        for key, value in headers.items():
            key_lower = key.lower()

            # Redact authorization headers
            if key_lower in ["authorization", "x-api-key", "x-auth-token"]:
                sanitized[key] = "[REDACTED]"

            # Hash signatures
            elif "signature" in key_lower:
                sanitized[f"{key}_hash"] = self.hash_signature(value)

            # Keep useful headers
            elif key_lower in ["user-agent", "content-type", "x-request-id"]:
                sanitized[key] = value

            else:
                sanitized[key] = value

        return sanitized
```

---

## 3. Logger Core

### 3.1 Command Logger

```python
"""
File: src/logging/logger.py
Purpose: Core command logging functionality
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from collections import deque

from .models import CommandLog, CommandType, CommandStatus, LoggingConfig
from .sanitizer import LogSanitizer
from .repository import CommandLogRepository

logger = logging.getLogger(__name__)


class CommandLogger:
    """
    Core command logging service.

    Features:
    - Async, non-blocking logging
    - Batch writes for performance
    - Automatic sanitization
    - Graceful degradation on errors
    """

    def __init__(
        self,
        repository: CommandLogRepository,
        config: LoggingConfig,
        sanitizer: Optional[LogSanitizer] = None
    ):
        self.repository = repository
        self.config = config
        self.sanitizer = sanitizer or LogSanitizer(config)

        # Async queue for batch processing
        self._log_queue: deque = deque(maxlen=config.batch_size * 10)
        self._flush_task: Optional[asyncio.Task] = None
        self._shutdown = False

    async def start(self) -> None:
        """Start the logging service."""
        if self.config.async_writes:
            self._flush_task = asyncio.create_task(self._flush_loop())
            logger.info("Command logger started with async writes")
        else:
            logger.info("Command logger started with sync writes")

    async def stop(self) -> None:
        """Stop the logging service and flush remaining logs."""
        self._shutdown = True

        if self._flush_task:
            await self._flush_task

        # Flush remaining logs
        await self._flush_queue()
        logger.info("Command logger stopped")

    async def _flush_loop(self) -> None:
        """Background task to flush logs periodically."""
        while not self._shutdown:
            try:
                await asyncio.sleep(self.config.flush_interval_seconds)
                await self._flush_queue()
            except Exception as e:
                logger.error(f"Error in flush loop: {e}")

    async def _flush_queue(self) -> None:
        """Flush queued logs to database."""
        if not self._log_queue:
            return

        # Batch write for performance
        batch = []
        while self._log_queue and len(batch) < self.config.batch_size:
            batch.append(self._log_queue.popleft())

        if batch:
            try:
                await self.repository.save_batch(batch)
                logger.debug(f"Flushed {len(batch)} log entries")
            except Exception as e:
                logger.error(f"Failed to flush logs: {e}")
                # Put logs back in queue for retry
                self._log_queue.extendleft(reversed(batch))

    async def log_command(
        self,
        command_type: CommandType,
        command_name: str,
        user_id: Optional[str],
        guild_id: str,
        channel_id: str,
        parameters: Dict[str, Any],
        execution_context: Dict[str, Any] = None
    ) -> CommandLog:
        """
        Create and queue a command log entry.

        Returns:
            CommandLog instance that can be updated with results
        """
        if not self.config.enabled:
            # Return dummy log that won't be persisted
            return CommandLog()

        # Sanitize sensitive data
        sanitized_params = self.sanitizer.sanitize_parameters(parameters)
        sanitized_context = self.sanitizer.sanitize_execution_context(
            execution_context or {}
        )

        # Create log entry
        log_entry = CommandLog(
            command_type=command_type,
            command_name=command_name,
            user_id=user_id,
            guild_id=guild_id,
            channel_id=channel_id,
            parameters=sanitized_params,
            execution_context=sanitized_context,
            started_at=datetime.utcnow()
        )

        # Queue for async write or write immediately
        if self.config.async_writes:
            self._log_queue.append(log_entry)
        else:
            try:
                await self.repository.save(log_entry)
            except Exception as e:
                logger.error(f"Failed to save log entry: {e}")

        return log_entry

    async def complete_log(
        self,
        log_entry: CommandLog,
        result_summary: Dict[str, Any] = None
    ) -> None:
        """
        Update log entry with completion status.

        Algorithm:
        1. Mark log as completed
        2. Sanitize result summary
        3. Update in database or queue
        """
        if not self.config.enabled:
            return

        log_entry.mark_completed(result_summary)

        # Sanitize result summary
        if log_entry.result_summary:
            log_entry.result_summary = self.sanitizer.sanitize_parameters(
                log_entry.result_summary
            )

        # Update in database
        try:
            await self.repository.update(log_entry)
        except Exception as e:
            logger.error(f"Failed to update log entry: {e}")

    async def fail_log(
        self,
        log_entry: CommandLog,
        error_code: str,
        error_message: str
    ) -> None:
        """Update log entry with failure status."""
        if not self.config.enabled:
            return

        # Sanitize error message
        sanitized_error = self.sanitizer.sanitize_error_message(error_message)
        log_entry.mark_failed(error_code, sanitized_error)

        # Update in database
        try:
            await self.repository.update(log_entry)
        except Exception as e:
            logger.error(f"Failed to update log entry: {e}")
```

---

## 4. Repository Layer

### 4.1 Command Log Repository

```python
"""
File: src/logging/repository.py
Purpose: Database operations for command logs
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from .models import CommandLog, CommandType, CommandStatus
from ..data.base import DatabaseConnection

logger = logging.getLogger(__name__)


class CommandLogRepository:
    """
    Repository for command log persistence.

    Responsibilities:
    - CRUD operations for command logs
    - Batch operations for performance
    - Query interface for log retrieval
    - Cleanup of expired logs
    """

    def __init__(self, connection: DatabaseConnection):
        self.connection = connection

    async def save(self, log_entry: CommandLog) -> str:
        """
        Save a single log entry.

        Algorithm:
        1. Convert log entry to dict
        2. Execute INSERT query
        3. Return log entry ID
        """
        query = """
        INSERT INTO command_logs (
            id, command_type, command_name, user_id, guild_id, channel_id,
            parameters, execution_context, status, error_code, error_message,
            started_at, completed_at, duration_ms, result_summary, metadata
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
        """

        data = log_entry.to_dict()
        params = (
            data["id"],
            data["command_type"],
            data["command_name"],
            data["user_id"],
            data["guild_id"],
            data["channel_id"],
            data["parameters"],
            data["execution_context"],
            data["status"],
            data["error_code"],
            data["error_message"],
            data["started_at"],
            data["completed_at"],
            data["duration_ms"],
            data["result_summary"],
            data["metadata"]
        )

        try:
            await self.connection.execute(query, params)
            return log_entry.id
        except Exception as e:
            logger.error(f"Failed to save command log: {e}")
            raise

    async def save_batch(self, log_entries: List[CommandLog]) -> List[str]:
        """
        Save multiple log entries in a single transaction.

        Performance optimization:
        - Single transaction for all entries
        - Batch INSERT statement
        - Returns list of saved IDs
        """
        if not log_entries:
            return []

        query = """
        INSERT INTO command_logs (
            id, command_type, command_name, user_id, guild_id, channel_id,
            parameters, execution_context, status, error_code, error_message,
            started_at, completed_at, duration_ms, result_summary, metadata
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        params_list = []
        for log_entry in log_entries:
            data = log_entry.to_dict()
            params_list.append((
                data["id"], data["command_type"], data["command_name"],
                data["user_id"], data["guild_id"], data["channel_id"],
                data["parameters"], data["execution_context"], data["status"],
                data["error_code"], data["error_message"], data["started_at"],
                data["completed_at"], data["duration_ms"], data["result_summary"],
                data["metadata"]
            ))

        try:
            async with self.connection.begin_transaction() as tx:
                for params in params_list:
                    await self.connection.execute(query, params)
                await tx.commit()

            return [entry.id for entry in log_entries]
        except Exception as e:
            logger.error(f"Failed to save batch of {len(log_entries)} logs: {e}")
            raise

    async def update(self, log_entry: CommandLog) -> bool:
        """
        Update an existing log entry.

        Typically used to update completion status and results.
        """
        query = """
        UPDATE command_logs
        SET status = ?, error_code = ?, error_message = ?,
            completed_at = ?, duration_ms = ?, result_summary = ?
        WHERE id = ?
        """

        data = log_entry.to_dict()
        params = (
            data["status"],
            data["error_code"],
            data["error_message"],
            data["completed_at"],
            data["duration_ms"],
            data["result_summary"],
            data["id"]
        )

        try:
            await self.connection.execute(query, params)
            return True
        except Exception as e:
            logger.error(f"Failed to update command log {log_entry.id}: {e}")
            return False

    async def get_by_id(self, log_id: str) -> Optional[CommandLog]:
        """Retrieve a single log entry by ID."""
        query = "SELECT * FROM command_logs WHERE id = ?"

        try:
            row = await self.connection.fetch_one(query, (log_id,))
            if row:
                return CommandLog.from_dict(row)
            return None
        except Exception as e:
            logger.error(f"Failed to get command log {log_id}: {e}")
            return None

    async def find(
        self,
        guild_id: Optional[str] = None,
        user_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        command_type: Optional[CommandType] = None,
        status: Optional[CommandStatus] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[CommandLog]:
        """
        Find command logs matching criteria.

        Algorithm:
        1. Build WHERE clause dynamically based on filters
        2. Add ORDER BY and LIMIT clauses
        3. Execute query and convert rows to CommandLog objects
        """
        where_clauses = []
        params = []

        if guild_id:
            where_clauses.append("guild_id = ?")
            params.append(guild_id)

        if user_id:
            where_clauses.append("user_id = ?")
            params.append(user_id)

        if channel_id:
            where_clauses.append("channel_id = ?")
            params.append(channel_id)

        if command_type:
            where_clauses.append("command_type = ?")
            params.append(command_type.value)

        if status:
            where_clauses.append("status = ?")
            params.append(status.value)

        if start_time:
            where_clauses.append("started_at >= ?")
            params.append(start_time.isoformat())

        if end_time:
            where_clauses.append("started_at <= ?")
            params.append(end_time.isoformat())

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        query = f"""
        SELECT * FROM command_logs
        WHERE {where_sql}
        ORDER BY started_at DESC
        LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        try:
            rows = await self.connection.fetch_all(query, tuple(params))
            return [CommandLog.from_dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to find command logs: {e}")
            return []

    async def count(
        self,
        guild_id: Optional[str] = None,
        user_id: Optional[str] = None,
        command_type: Optional[CommandType] = None,
        status: Optional[CommandStatus] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> int:
        """Count command logs matching criteria."""
        where_clauses = []
        params = []

        if guild_id:
            where_clauses.append("guild_id = ?")
            params.append(guild_id)

        if user_id:
            where_clauses.append("user_id = ?")
            params.append(user_id)

        if command_type:
            where_clauses.append("command_type = ?")
            params.append(command_type.value)

        if status:
            where_clauses.append("status = ?")
            params.append(status.value)

        if start_time:
            where_clauses.append("started_at >= ?")
            params.append(start_time.isoformat())

        if end_time:
            where_clauses.append("started_at <= ?")
            params.append(end_time.isoformat())

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        query = f"SELECT COUNT(*) as count FROM command_logs WHERE {where_sql}"

        try:
            row = await self.connection.fetch_one(query, tuple(params))
            return row["count"] if row else 0
        except Exception as e:
            logger.error(f"Failed to count command logs: {e}")
            return 0

    async def delete_older_than(self, cutoff_date: datetime) -> int:
        """
        Delete logs older than cutoff date.

        Used for retention policy enforcement.
        Returns number of deleted records.
        """
        query = "DELETE FROM command_logs WHERE started_at < ?"

        try:
            result = await self.connection.execute(
                query,
                (cutoff_date.isoformat(),)
            )
            return result.rowcount if hasattr(result, 'rowcount') else 0
        except Exception as e:
            logger.error(f"Failed to delete old command logs: {e}")
            return 0
```

---

## 5. Decorators and Middleware

### 5.1 Command Decorator

```python
"""
File: src/logging/decorators.py
Purpose: Decorators for automatic command logging
"""

import functools
import logging
from typing import Callable, Any
from datetime import datetime

from .models import CommandType
from .logger import CommandLogger

logger = logging.getLogger(__name__)


def log_command(
    command_type: CommandType,
    command_name: str = None
):
    """
    Decorator to automatically log command execution.

    Usage:
        @log_command(CommandType.SLASH_COMMAND)
        async def handle_summarize(interaction, **kwargs):
            # Command implementation
            pass

    Algorithm:
    1. Extract command context before execution
    2. Create log entry with start time
    3. Execute wrapped function
    4. Update log with result or error
    5. Ensure log is always updated even if exception
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs) -> Any:
            # Get command logger from handler instance
            if not hasattr(self, 'command_logger'):
                # No logger configured, execute without logging
                return await func(self, *args, **kwargs)

            command_logger: CommandLogger = self.command_logger

            # Extract context from function arguments
            # For Discord commands, first arg is interaction
            context = _extract_context(args, kwargs, command_type)

            # Determine command name
            cmd_name = command_name or func.__name__

            # Create log entry
            log_entry = await command_logger.log_command(
                command_type=command_type,
                command_name=cmd_name,
                user_id=context.get("user_id"),
                guild_id=context.get("guild_id"),
                channel_id=context.get("channel_id"),
                parameters=context.get("parameters", {}),
                execution_context=context.get("execution_context", {})
            )

            # Execute command
            try:
                result = await func(self, *args, **kwargs)

                # Extract result summary
                result_summary = _extract_result_summary(result, command_type)

                # Mark log as completed
                await command_logger.complete_log(log_entry, result_summary)

                return result

            except Exception as e:
                # Mark log as failed
                error_code = getattr(e, 'error_code', 'UNKNOWN_ERROR')
                error_message = str(e)

                await command_logger.fail_log(
                    log_entry,
                    error_code=error_code,
                    error_message=error_message
                )

                # Re-raise exception
                raise

        return wrapper

    return decorator


def _extract_context(args, kwargs, command_type: CommandType) -> dict:
    """
    Extract logging context from function arguments.

    Different command types have different argument structures:
    - Discord commands: interaction object
    - Scheduled tasks: task object
    - Webhooks: request object
    """
    context = {
        "user_id": None,
        "guild_id": "",
        "channel_id": "",
        "parameters": {},
        "execution_context": {}
    }

    if command_type == CommandType.SLASH_COMMAND:
        # First arg should be interaction
        if args and hasattr(args[0], 'user'):
            interaction = args[0]
            context["user_id"] = str(interaction.user.id)
            context["guild_id"] = str(interaction.guild_id) if interaction.guild else ""
            context["channel_id"] = str(interaction.channel_id)
            context["parameters"] = dict(kwargs)
            context["execution_context"] = {
                "interaction_id": str(interaction.id),
                "command_name": interaction.command.name if interaction.command else ""
            }

    elif command_type == CommandType.SCHEDULED_TASK:
        # First arg should be task
        if args:
            task = args[0]
            context["user_id"] = None  # Scheduled tasks have no user
            context["guild_id"] = getattr(task, 'guild_id', '')
            context["channel_id"] = getattr(task, 'channel_id', '')
            context["parameters"] = {
                "task_id": getattr(task, 'id', ''),
                "schedule_type": getattr(task, 'schedule_type', '').value if hasattr(getattr(task, 'schedule_type', ''), 'value') else ''
            }
            context["execution_context"] = {
                "scheduled_time": getattr(task, 'next_run', None),
                "task_name": getattr(task, 'name', '')
            }

    elif command_type == CommandType.WEBHOOK_REQUEST:
        # Extract from request object or kwargs
        if "request" in kwargs:
            request = kwargs["request"]
            context["guild_id"] = request.get("guild_id", "")
            context["channel_id"] = request.get("channel_id", "")
            context["parameters"] = request.get("parameters", {})

            # Get execution context from headers/metadata
            if "headers" in kwargs:
                headers = kwargs["headers"]
                context["execution_context"] = {
                    "source_ip": headers.get("x-forwarded-for", ""),
                    "user_agent": headers.get("user-agent", ""),
                    "signature": headers.get("x-signature", "")
                }

    return context


def _extract_result_summary(result: Any, command_type: CommandType) -> dict:
    """
    Extract summary from command result.

    Different commands return different result types.
    Extract relevant metrics for logging.
    """
    summary = {}

    if result is None:
        return summary

    if command_type == CommandType.SLASH_COMMAND:
        # For summarize commands
        if hasattr(result, 'message_count'):
            summary["messages_processed"] = result.message_count
        if hasattr(result, 'summary_text'):
            summary["summary_length"] = len(result.summary_text)
        if hasattr(result, 'key_points'):
            summary["key_points_count"] = len(result.key_points)

    elif command_type == CommandType.SCHEDULED_TASK:
        if isinstance(result, dict):
            summary["messages_processed"] = result.get("message_count", 0)
            summary["destinations_delivered"] = result.get("deliveries", 0)

    return summary
```

### 5.2 Webhook Middleware

```python
"""
File: src/logging/middleware.py
Purpose: FastAPI middleware for webhook logging
"""

import time
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from .models import CommandType
from .logger import CommandLogger

logger = logging.getLogger(__name__)


class WebhookLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all webhook requests.

    Captures:
    - Request path and method
    - Request headers (sanitized)
    - Request timing
    - Response status
    """

    def __init__(self, app, command_logger: CommandLogger):
        super().__init__(app)
        self.command_logger = command_logger

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and log execution.

        Algorithm:
        1. Extract request context
        2. Create log entry
        3. Execute request handler
        4. Update log with response
        5. Return response
        """
        # Skip logging for health checks and static files
        if request.url.path in ["/health", "/metrics"]:
            return await call_next(request)

        # Extract request body for logging (limited)
        try:
            body = await request.body()
            request_data = await request.json() if body else {}
        except:
            request_data = {}

        # Create log entry
        log_entry = await self.command_logger.log_command(
            command_type=CommandType.WEBHOOK_REQUEST,
            command_name=f"{request.method} {request.url.path}",
            user_id=None,
            guild_id=request_data.get("guild_id", ""),
            channel_id=request_data.get("channel_id", ""),
            parameters=request_data,
            execution_context={
                "method": request.method,
                "path": request.url.path,
                "source_ip": request.client.host if request.client else "",
                "user_agent": request.headers.get("user-agent", ""),
                "signature": request.headers.get("x-signature", "")
            }
        )

        # Execute request
        start_time = time.time()
        try:
            response = await call_next(request)

            # Mark as completed
            duration_ms = int((time.time() - start_time) * 1000)
            await self.command_logger.complete_log(
                log_entry,
                result_summary={
                    "status_code": response.status_code,
                    "duration_ms": duration_ms
                }
            )

            return response

        except Exception as e:
            # Mark as failed
            await self.command_logger.fail_log(
                log_entry,
                error_code="WEBHOOK_ERROR",
                error_message=str(e)
            )
            raise
```

---

## 6. Integration Points

### 6.1 Discord Command Handler Integration

```python
"""
File: src/command_handlers/base.py (modifications)
Purpose: Integrate logging into base command handler
"""

# Add to BaseCommandHandler __init__:
def __init__(
    self,
    summarization_engine,
    permission_manager=None,
    command_logger: Optional[CommandLogger] = None,
    rate_limit_enabled: bool = True
):
    # ... existing code ...
    self.command_logger = command_logger

# Modify handle_command to use decorator:
@log_command(CommandType.SLASH_COMMAND)
async def handle_command(self, interaction: discord.Interaction, **kwargs) -> None:
    """
    Main command handler with error handling, rate limiting, and logging.

    Logging is now handled by decorator - captures:
    - Command invocation
    - Parameters
    - Execution time
    - Success/failure status
    """
    # ... existing implementation ...
```

### 6.2 Scheduled Task Integration

```python
"""
File: src/scheduling/executor.py (modifications)
Purpose: Add logging to scheduled task execution
"""

class TaskExecutor:
    def __init__(
        self,
        # ... existing params ...
        command_logger: Optional[CommandLogger] = None
    ):
        # ... existing code ...
        self.command_logger = command_logger

    @log_command(CommandType.SCHEDULED_TASK)
    async def execute_task(self, task: SummaryTask) -> Dict[str, Any]:
        """
        Execute a scheduled summary task.

        Logging decorator captures:
        - Task ID and configuration
        - Execution timing
        - Result metrics
        - Any errors
        """
        # ... existing implementation ...

        result = {
            "message_count": len(processed_messages),
            "deliveries": len(task.destinations),
            "summary_id": summary_result.id
        }

        return result
```

### 6.3 Webhook Endpoint Integration

```python
"""
File: src/webhook_service/server.py (modifications)
Purpose: Add logging middleware to webhook service
"""

from ..logging.middleware import WebhookLoggingMiddleware
from ..logging.logger import CommandLogger

def create_webhook_app(
    summarization_engine,
    config: BotConfig,
    command_logger: CommandLogger
) -> FastAPI:
    """Create FastAPI app with logging middleware."""

    app = FastAPI(title="Summary Bot Webhook API")

    # Add logging middleware
    app.add_middleware(
        WebhookLoggingMiddleware,
        command_logger=command_logger
    )

    # ... rest of app setup ...

    return app
```

---

## 7. Query Interface

### 7.1 Query Builder

```python
"""
File: src/logging/query.py
Purpose: Fluent query interface for command logs
"""

from typing import Optional, List
from datetime import datetime, timedelta

from .models import CommandLog, CommandType, CommandStatus
from .repository import CommandLogRepository


class CommandLogQuery:
    """
    Fluent query builder for command logs.

    Usage:
        logs = await CommandLogQuery(repository) \
            .by_guild("123456") \
            .in_last_hours(24) \
            .status(CommandStatus.FAILED) \
            .limit(50) \
            .execute()
    """

    def __init__(self, repository: CommandLogRepository):
        self.repository = repository
        self._guild_id: Optional[str] = None
        self._user_id: Optional[str] = None
        self._channel_id: Optional[str] = None
        self._command_type: Optional[CommandType] = None
        self._status: Optional[CommandStatus] = None
        self._start_time: Optional[datetime] = None
        self._end_time: Optional[datetime] = None
        self._limit: int = 100
        self._offset: int = 0

    def by_guild(self, guild_id: str) -> 'CommandLogQuery':
        """Filter by guild ID."""
        self._guild_id = guild_id
        return self

    def by_user(self, user_id: str) -> 'CommandLogQuery':
        """Filter by user ID."""
        self._user_id = user_id
        return self

    def by_channel(self, channel_id: str) -> 'CommandLogQuery':
        """Filter by channel ID."""
        self._channel_id = channel_id
        return self

    def of_type(self, command_type: CommandType) -> 'CommandLogQuery':
        """Filter by command type."""
        self._command_type = command_type
        return self

    def with_status(self, status: CommandStatus) -> 'CommandLogQuery':
        """Filter by execution status."""
        self._status = status
        return self

    def in_time_range(
        self,
        start: datetime,
        end: datetime
    ) -> 'CommandLogQuery':
        """Filter by time range."""
        self._start_time = start
        self._end_time = end
        return self

    def in_last_hours(self, hours: int) -> 'CommandLogQuery':
        """Filter to last N hours."""
        self._end_time = datetime.utcnow()
        self._start_time = self._end_time - timedelta(hours=hours)
        return self

    def in_last_days(self, days: int) -> 'CommandLogQuery':
        """Filter to last N days."""
        self._end_time = datetime.utcnow()
        self._start_time = self._end_time - timedelta(days=days)
        return self

    def limit(self, limit: int) -> 'CommandLogQuery':
        """Set result limit."""
        self._limit = limit
        return self

    def offset(self, offset: int) -> 'CommandLogQuery':
        """Set result offset for pagination."""
        self._offset = offset
        return self

    def page(self, page_num: int, page_size: int = 50) -> 'CommandLogQuery':
        """Set pagination by page number."""
        self._limit = page_size
        self._offset = (page_num - 1) * page_size
        return self

    async def execute(self) -> List[CommandLog]:
        """Execute query and return results."""
        return await self.repository.find(
            guild_id=self._guild_id,
            user_id=self._user_id,
            channel_id=self._channel_id,
            command_type=self._command_type,
            status=self._status,
            start_time=self._start_time,
            end_time=self._end_time,
            limit=self._limit,
            offset=self._offset
        )

    async def count(self) -> int:
        """Count matching records without fetching."""
        return await self.repository.count(
            guild_id=self._guild_id,
            user_id=self._user_id,
            command_type=self._command_type,
            status=self._status,
            start_time=self._start_time,
            end_time=self._end_time
        )

    async def first(self) -> Optional[CommandLog]:
        """Get first matching result."""
        results = await self.limit(1).execute()
        return results[0] if results else None
```

### 7.2 Analytics Helper

```python
"""
File: src/logging/analytics.py
Purpose: Analytics and reporting on command logs
"""

from typing import Dict, List
from datetime import datetime, timedelta
from collections import defaultdict

from .query import CommandLogQuery
from .models import CommandType, CommandStatus
from .repository import CommandLogRepository


class CommandAnalytics:
    """
    Analytics and reporting for command logs.

    Provides aggregated statistics and insights.
    """

    def __init__(self, repository: CommandLogRepository):
        self.repository = repository

    async def get_command_stats(
        self,
        guild_id: str,
        hours: int = 24
    ) -> Dict[str, any]:
        """
        Get command execution statistics for a guild.

        Returns:
            Dict with counts, success rates, avg duration, etc.
        """
        query = CommandLogQuery(self.repository) \
            .by_guild(guild_id) \
            .in_last_hours(hours)

        # Get all logs
        logs = await query.execute()

        if not logs:
            return {
                "total_commands": 0,
                "success_count": 0,
                "failed_count": 0,
                "success_rate": 0.0,
                "avg_duration_ms": 0,
                "by_type": {},
                "by_status": {}
            }

        # Calculate statistics
        total = len(logs)
        success_count = sum(1 for log in logs if log.status == CommandStatus.SUCCESS)
        failed_count = sum(1 for log in logs if log.status == CommandStatus.FAILED)

        # Average duration (only completed commands)
        durations = [log.duration_ms for log in logs if log.duration_ms is not None]
        avg_duration = sum(durations) / len(durations) if durations else 0

        # Group by type
        by_type = defaultdict(int)
        for log in logs:
            by_type[log.command_type.value] += 1

        # Group by status
        by_status = defaultdict(int)
        for log in logs:
            by_status[log.status.value] += 1

        return {
            "total_commands": total,
            "success_count": success_count,
            "failed_count": failed_count,
            "success_rate": (success_count / total * 100) if total > 0 else 0.0,
            "avg_duration_ms": avg_duration,
            "by_type": dict(by_type),
            "by_status": dict(by_status)
        }

    async def get_user_activity(
        self,
        user_id: str,
        days: int = 7
    ) -> List[Dict[str, any]]:
        """Get user's command activity history."""
        logs = await CommandLogQuery(self.repository) \
            .by_user(user_id) \
            .in_last_days(days) \
            .execute()

        return [
            {
                "command_name": log.command_name,
                "timestamp": log.started_at,
                "status": log.status.value,
                "duration_ms": log.duration_ms
            }
            for log in logs
        ]

    async def get_error_summary(
        self,
        guild_id: str,
        hours: int = 24
    ) -> Dict[str, List[Dict]]:
        """Get summary of errors by error code."""
        logs = await CommandLogQuery(self.repository) \
            .by_guild(guild_id) \
            .with_status(CommandStatus.FAILED) \
            .in_last_hours(hours) \
            .execute()

        errors_by_code = defaultdict(list)
        for log in logs:
            error_code = log.error_code or "UNKNOWN"
            errors_by_code[error_code].append({
                "command": log.command_name,
                "timestamp": log.started_at,
                "message": log.error_message,
                "user_id": log.user_id
            })

        return dict(errors_by_code)
```

---

## 8. Cleanup and Maintenance

### 8.1 Retention Policy Enforcer

```python
"""
File: src/logging/cleanup.py
Purpose: Automatic cleanup of expired logs
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from .repository import CommandLogRepository
from .models import LoggingConfig

logger = logging.getLogger(__name__)


class LogCleanupService:
    """
    Service for cleaning up expired command logs.

    Enforces retention policy by deleting old logs.
    """

    def __init__(
        self,
        repository: CommandLogRepository,
        config: LoggingConfig
    ):
        self.repository = repository
        self.config = config

    async def cleanup_expired_logs(self) -> int:
        """
        Delete logs older than retention period.

        Algorithm:
        1. Calculate cutoff date
        2. Delete logs older than cutoff
        3. Return count of deleted records
        4. Log cleanup summary
        """
        if not self.config.enabled:
            return 0

        cutoff_date = datetime.utcnow() - timedelta(days=self.config.retention_days)

        logger.info(f"Starting log cleanup. Deleting logs older than {cutoff_date}")

        try:
            deleted_count = await self.repository.delete_older_than(cutoff_date)

            logger.info(f"Log cleanup completed. Deleted {deleted_count} records")

            return deleted_count

        except Exception as e:
            logger.error(f"Log cleanup failed: {e}")
            return 0

    async def cleanup_by_guild(
        self,
        guild_id: str,
        retention_days: Optional[int] = None
    ) -> int:
        """
        Clean up logs for a specific guild.

        Allows per-guild retention policies.
        """
        days = retention_days or self.config.retention_days
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        query = """
        DELETE FROM command_logs
        WHERE guild_id = ? AND started_at < ?
        """

        try:
            result = await self.repository.connection.execute(
                query,
                (guild_id, cutoff_date.isoformat())
            )
            return result.rowcount if hasattr(result, 'rowcount') else 0
        except Exception as e:
            logger.error(f"Guild cleanup failed for {guild_id}: {e}")
            return 0
```

### 8.2 Scheduled Cleanup Task

```python
"""
File: src/logging/scheduled_cleanup.py
Purpose: Schedule automatic log cleanup
"""

import asyncio
import logging
from typing import Optional
from datetime import time

from .cleanup import LogCleanupService

logger = logging.getLogger(__name__)


class ScheduledCleanup:
    """
    Schedule automatic log cleanup.

    Runs cleanup at specified time each day.
    """

    def __init__(
        self,
        cleanup_service: LogCleanupService,
        cleanup_time: time = time(hour=2, minute=0)
    ):
        self.cleanup_service = cleanup_service
        self.cleanup_time = cleanup_time
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        """Start scheduled cleanup."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._cleanup_loop())
        logger.info(f"Scheduled log cleanup started (runs daily at {self.cleanup_time})")

    async def stop(self) -> None:
        """Stop scheduled cleanup."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Scheduled log cleanup stopped")

    async def _cleanup_loop(self) -> None:
        """Background task for periodic cleanup."""
        while self._running:
            try:
                # Calculate time until next cleanup
                now = datetime.utcnow()
                next_run = now.replace(
                    hour=self.cleanup_time.hour,
                    minute=self.cleanup_time.minute,
                    second=0,
                    microsecond=0
                )

                # If time has passed today, schedule for tomorrow
                if next_run <= now:
                    next_run += timedelta(days=1)

                # Wait until next cleanup time
                wait_seconds = (next_run - now).total_seconds()
                logger.debug(f"Next log cleanup in {wait_seconds:.0f} seconds")

                await asyncio.sleep(wait_seconds)

                # Run cleanup
                deleted = await self.cleanup_service.cleanup_expired_logs()
                logger.info(f"Scheduled cleanup removed {deleted} log entries")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                # Wait before retrying
                await asyncio.sleep(3600)  # 1 hour
```

---

## 9. Database Migration

### 9.1 Schema Migration

```sql
-- File: src/data/migrations/002_command_logs.sql
-- Purpose: Add command_logs table to database

-- ============================================================================
-- COMMAND LOGS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS command_logs (
    -- Identity
    id TEXT PRIMARY KEY,
    command_type TEXT NOT NULL CHECK(command_type IN ('slash_command', 'scheduled_task', 'webhook_request')),
    command_name TEXT NOT NULL,

    -- Context
    user_id TEXT,  -- NULL for scheduled tasks
    guild_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,

    -- Execution data
    parameters TEXT NOT NULL DEFAULT '{}',  -- JSON
    execution_context TEXT NOT NULL DEFAULT '{}',  -- JSON

    -- Results
    status TEXT NOT NULL CHECK(status IN ('success', 'failed', 'timeout', 'cancelled')),
    error_code TEXT,
    error_message TEXT,

    -- Timing
    started_at TEXT NOT NULL,
    completed_at TEXT,
    duration_ms INTEGER CHECK(duration_ms >= 0),

    -- Output
    result_summary TEXT,  -- JSON
    metadata TEXT NOT NULL DEFAULT '{}',  -- JSON

    -- Constraints
    CHECK(completed_at IS NULL OR completed_at >= started_at)
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- Query by guild and time (most common)
CREATE INDEX idx_command_logs_guild_time
    ON command_logs(guild_id, started_at DESC);

-- Query by user and time
CREATE INDEX idx_command_logs_user_time
    ON command_logs(user_id, started_at DESC)
    WHERE user_id IS NOT NULL;

-- Query by channel and time
CREATE INDEX idx_command_logs_channel_time
    ON command_logs(channel_id, started_at DESC);

-- Query by type and status (analytics)
CREATE INDEX idx_command_logs_type_status
    ON command_logs(command_type, status);

-- Query by time only (cleanup)
CREATE INDEX idx_command_logs_started_at
    ON command_logs(started_at DESC);

-- Composite index for failed commands in guild
CREATE INDEX idx_command_logs_guild_status_time
    ON command_logs(guild_id, status, started_at DESC)
    WHERE status = 'failed';

-- ============================================================================
-- SCHEMA VERSION UPDATE
-- ============================================================================
INSERT INTO schema_version (version, applied_at, description)
VALUES (2, datetime('now'), 'Add command_logs table for audit trail');
```

---

## 10. Usage Examples

### 10.1 Setup and Initialization

```python
"""
Example: Setting up command logging in main.py
"""

from src.logging.logger import CommandLogger
from src.logging.repository import CommandLogRepository
from src.logging.models import LoggingConfig
from src.logging.cleanup import LogCleanupService
from src.logging.scheduled_cleanup import ScheduledCleanup
from src.data.sqlite import SQLiteConnection

async def initialize_command_logging(db_connection):
    """Initialize command logging system."""

    # Load configuration
    config = LoggingConfig.from_env()

    # Create repository
    repository = CommandLogRepository(db_connection)

    # Create logger
    command_logger = CommandLogger(repository, config)

    # Start logger
    await command_logger.start()

    # Setup cleanup service
    cleanup_service = LogCleanupService(repository, config)
    scheduled_cleanup = ScheduledCleanup(cleanup_service)

    # Start scheduled cleanup
    if config.auto_cleanup:
        await scheduled_cleanup.start()

    return command_logger, scheduled_cleanup


# In main application startup:
async def main():
    db_connection = await create_db_connection()
    command_logger, cleanup_task = await initialize_command_logging(db_connection)

    # Pass command_logger to handlers
    summarize_handler = SummarizeCommandHandler(
        summarization_engine=engine,
        command_logger=command_logger
    )

    # ... rest of app initialization
```

### 10.2 Querying Logs

```python
"""
Example: Querying command logs
"""

from src.logging.query import CommandLogQuery
from src.logging.analytics import CommandAnalytics

# Get failed commands in last 24 hours
failed_commands = await CommandLogQuery(repository) \
    .by_guild("123456789") \
    .with_status(CommandStatus.FAILED) \
    .in_last_hours(24) \
    .execute()

# Get user activity
user_logs = await CommandLogQuery(repository) \
    .by_user("987654321") \
    .in_last_days(7) \
    .limit(100) \
    .execute()

# Get analytics
analytics = CommandAnalytics(repository)
stats = await analytics.get_command_stats("123456789", hours=24)

print(f"Success rate: {stats['success_rate']:.1f}%")
print(f"Average duration: {stats['avg_duration_ms']:.0f}ms")
```

---

**Document Version:** 1.0
**Last Updated:** 2024-01-15
**Author:** SPARC Specification Agent
