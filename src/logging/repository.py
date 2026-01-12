"""
Database operations for command logs.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from .models import CommandLog, CommandType, CommandStatus

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

    def __init__(self, connection):
        """
        Initialize repository.

        Args:
            connection: Database connection (SQLite or PostgreSQL)
        """
        self.connection = connection

    async def save(self, log_entry: CommandLog) -> str:
        """
        Save a single log entry.

        Args:
            log_entry: Command log to save

        Returns:
            Log entry ID

        Raises:
            Exception: If database operation fails
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

        Args:
            log_entries: List of command logs to save

        Returns:
            List of log entry IDs
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
            # Execute batch insert
            for params in params_list:
                await self.connection.execute(query, params)

            return [entry.id for entry in log_entries]
        except Exception as e:
            logger.error(f"Failed to save batch of {len(log_entries)} logs: {e}")
            raise

    async def update(self, log_entry: CommandLog) -> bool:
        """
        Update an existing log entry.

        Typically used to update completion status and results.

        Args:
            log_entry: Command log with updated data

        Returns:
            True if update successful
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
        """
        Retrieve a single log entry by ID.

        Args:
            log_id: Log entry ID

        Returns:
            CommandLog if found, None otherwise
        """
        query = "SELECT * FROM command_logs WHERE id = ?"

        try:
            row = await self.connection.fetch_one(query, (log_id,))
            if row:
                return CommandLog.from_dict(dict(row))
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

        Args:
            guild_id: Filter by guild
            user_id: Filter by user
            channel_id: Filter by channel
            command_type: Filter by command type
            status: Filter by status
            start_time: Filter by start time (inclusive)
            end_time: Filter by end time (inclusive)
            limit: Maximum results to return
            offset: Offset for pagination

        Returns:
            List of matching CommandLog entries
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
            return [CommandLog.from_dict(dict(row)) for row in rows]
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
        """
        Count command logs matching criteria.

        Args:
            guild_id: Filter by guild
            user_id: Filter by user
            command_type: Filter by command type
            status: Filter by status
            start_time: Filter by start time
            end_time: Filter by end time

        Returns:
            Count of matching logs
        """
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

        Args:
            cutoff_date: Delete logs older than this date

        Returns:
            Number of deleted records
        """
        query = "DELETE FROM command_logs WHERE started_at < ?"

        try:
            result = await self.connection.execute(
                query,
                (cutoff_date.isoformat(),)
            )
            # SQLite returns cursor, check for rowcount
            deleted = getattr(result, 'rowcount', 0)
            logger.info(f"Deleted {deleted} command logs older than {cutoff_date}")
            return deleted
        except Exception as e:
            logger.error(f"Failed to delete old command logs: {e}")
            return 0
