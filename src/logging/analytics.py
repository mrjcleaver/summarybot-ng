"""
Analytics and reporting for command logs.
"""

from typing import Dict, List, Any
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
        """
        Initialize analytics service.

        Args:
            repository: Command log repository
        """
        self.repository = repository

    async def get_command_stats(
        self,
        guild_id: str,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get command execution statistics for a guild.

        Args:
            guild_id: Guild ID to analyze
            hours: Time period in hours

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
    ) -> List[Dict[str, Any]]:
        """
        Get user's command activity history.

        Args:
            user_id: User ID to analyze
            days: Time period in days

        Returns:
            List of command activity records
        """
        logs = await CommandLogQuery(self.repository) \
            .by_user(user_id) \
            .in_last_days(days) \
            .execute()

        return [
            {
                "command_name": log.command_name,
                "timestamp": log.started_at.isoformat(),
                "status": log.status.value,
                "duration_ms": log.duration_ms
            }
            for log in logs
        ]

    async def get_error_summary(
        self,
        guild_id: str,
        hours: int = 24
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get summary of errors by error code.

        Args:
            guild_id: Guild ID to analyze
            hours: Time period in hours

        Returns:
            Dict mapping error codes to error details
        """
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
                "timestamp": log.started_at.isoformat(),
                "message": log.error_message,
                "user_id": log.user_id
            })

        return dict(errors_by_code)
