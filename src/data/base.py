"""
Abstract repository interfaces for data access layer.

This module defines the repository pattern interfaces for all data operations.
Concrete implementations should inherit from these abstract base classes.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..models.summary import SummaryResult
from ..models.task import ScheduledTask, TaskResult
from ..models.feed import FeedConfig
from ..config.settings import GuildConfig


class SearchCriteria:
    """Search criteria for querying summaries."""

    def __init__(
        self,
        guild_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "created_at",
        order_direction: str = "DESC"
    ):
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.start_time = start_time
        self.end_time = end_time
        self.limit = limit
        self.offset = offset
        self.order_by = order_by
        self.order_direction = order_direction


class SummaryRepository(ABC):
    """Abstract repository for summary data operations."""

    @abstractmethod
    async def save_summary(self, summary: SummaryResult) -> str:
        """
        Save a summary to the database.

        Args:
            summary: The summary result to save

        Returns:
            The ID of the saved summary
        """
        pass

    @abstractmethod
    async def get_summary(self, summary_id: str) -> Optional[SummaryResult]:
        """
        Retrieve a summary by its ID.

        Args:
            summary_id: The unique identifier of the summary

        Returns:
            The summary result if found, None otherwise
        """
        pass

    @abstractmethod
    async def find_summaries(self, criteria: SearchCriteria) -> List[SummaryResult]:
        """
        Find summaries matching the given criteria.

        Args:
            criteria: Search criteria for filtering summaries

        Returns:
            List of matching summary results
        """
        pass

    @abstractmethod
    async def delete_summary(self, summary_id: str) -> bool:
        """
        Delete a summary from the database.

        Args:
            summary_id: The unique identifier of the summary to delete

        Returns:
            True if the summary was deleted, False otherwise
        """
        pass

    @abstractmethod
    async def count_summaries(self, criteria: SearchCriteria) -> int:
        """
        Count summaries matching the given criteria.

        Args:
            criteria: Search criteria for filtering summaries

        Returns:
            Number of matching summaries
        """
        pass

    @abstractmethod
    async def get_summaries_by_channel(
        self,
        channel_id: str,
        limit: int = 10
    ) -> List[SummaryResult]:
        """
        Get recent summaries for a specific channel.

        Args:
            channel_id: The channel ID to search for
            limit: Maximum number of summaries to return

        Returns:
            List of recent summary results for the channel
        """
        pass


class ConfigRepository(ABC):
    """Abstract repository for configuration data operations."""

    @abstractmethod
    async def save_guild_config(self, config: GuildConfig) -> None:
        """
        Save or update a guild configuration.

        Args:
            config: The guild configuration to save
        """
        pass

    @abstractmethod
    async def get_guild_config(self, guild_id: str) -> Optional[GuildConfig]:
        """
        Retrieve configuration for a specific guild.

        Args:
            guild_id: The unique identifier of the guild

        Returns:
            The guild configuration if found, None otherwise
        """
        pass

    @abstractmethod
    async def delete_guild_config(self, guild_id: str) -> bool:
        """
        Delete a guild configuration.

        Args:
            guild_id: The unique identifier of the guild

        Returns:
            True if the configuration was deleted, False otherwise
        """
        pass

    @abstractmethod
    async def get_all_guild_configs(self) -> List[GuildConfig]:
        """
        Retrieve all guild configurations.

        Returns:
            List of all guild configurations
        """
        pass


class TaskRepository(ABC):
    """Abstract repository for scheduled task data operations."""

    @abstractmethod
    async def save_task(self, task: ScheduledTask) -> str:
        """
        Save or update a scheduled task.

        Args:
            task: The scheduled task to save

        Returns:
            The ID of the saved task
        """
        pass

    @abstractmethod
    async def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """
        Retrieve a task by its ID.

        Args:
            task_id: The unique identifier of the task

        Returns:
            The scheduled task if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_tasks_by_guild(self, guild_id: str) -> List[ScheduledTask]:
        """
        Get all tasks for a specific guild.

        Args:
            guild_id: The unique identifier of the guild

        Returns:
            List of scheduled tasks for the guild
        """
        pass

    @abstractmethod
    async def get_active_tasks(self) -> List[ScheduledTask]:
        """
        Get all active tasks across all guilds.

        Returns:
            List of all active scheduled tasks
        """
        pass

    @abstractmethod
    async def delete_task(self, task_id: str) -> bool:
        """
        Delete a scheduled task.

        Args:
            task_id: The unique identifier of the task

        Returns:
            True if the task was deleted, False otherwise
        """
        pass

    @abstractmethod
    async def save_task_result(self, result: TaskResult) -> str:
        """
        Save a task execution result.

        Args:
            result: The task execution result to save

        Returns:
            The ID of the saved result
        """
        pass

    @abstractmethod
    async def get_task_results(
        self,
        task_id: str,
        limit: int = 10
    ) -> List[TaskResult]:
        """
        Get execution results for a specific task.

        Args:
            task_id: The unique identifier of the task
            limit: Maximum number of results to return

        Returns:
            List of task execution results
        """
        pass


class FeedRepository(ABC):
    """Abstract repository for RSS/Atom feed configuration operations."""

    @abstractmethod
    async def save_feed(self, feed: FeedConfig) -> str:
        """
        Save or update a feed configuration.

        Args:
            feed: The feed configuration to save

        Returns:
            The ID of the saved feed
        """
        pass

    @abstractmethod
    async def get_feed(self, feed_id: str) -> Optional[FeedConfig]:
        """
        Retrieve a feed by its ID.

        Args:
            feed_id: The unique identifier of the feed

        Returns:
            The feed configuration if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_feed_by_token(self, token: str) -> Optional[FeedConfig]:
        """
        Retrieve a feed by its authentication token.

        Args:
            token: The feed authentication token

        Returns:
            The feed configuration if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_feeds_by_guild(self, guild_id: str) -> List[FeedConfig]:
        """
        Get all feeds for a specific guild.

        Args:
            guild_id: The unique identifier of the guild

        Returns:
            List of feed configurations for the guild
        """
        pass

    @abstractmethod
    async def delete_feed(self, feed_id: str) -> bool:
        """
        Delete a feed configuration.

        Args:
            feed_id: The unique identifier of the feed

        Returns:
            True if the feed was deleted, False otherwise
        """
        pass

    @abstractmethod
    async def update_access_stats(self, feed_id: str) -> None:
        """
        Update access statistics for a feed.

        Args:
            feed_id: The unique identifier of the feed
        """
        pass


class DatabaseConnection(ABC):
    """Abstract database connection interface."""

    @abstractmethod
    async def connect(self) -> None:
        """Establish database connection."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close database connection."""
        pass

    @abstractmethod
    async def execute(self, query: str, params: Optional[tuple] = None) -> Any:
        """
        Execute a database query.

        Args:
            query: SQL query to execute
            params: Query parameters

        Returns:
            Query result
        """
        pass

    @abstractmethod
    async def fetch_one(self, query: str, params: Optional[tuple] = None) -> Optional[Dict[str, Any]]:
        """
        Fetch a single row from the database.

        Args:
            query: SQL query to execute
            params: Query parameters

        Returns:
            Single row as a dictionary, or None if no results
        """
        pass

    @abstractmethod
    async def fetch_all(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """
        Fetch all rows from the database.

        Args:
            query: SQL query to execute
            params: Query parameters

        Returns:
            List of rows as dictionaries
        """
        pass

    @abstractmethod
    async def begin_transaction(self) -> 'Transaction':
        """
        Begin a new database transaction.

        Returns:
            Transaction context manager
        """
        pass


class Transaction(ABC):
    """Abstract database transaction interface."""

    @abstractmethod
    async def commit(self) -> None:
        """Commit the transaction."""
        pass

    @abstractmethod
    async def rollback(self) -> None:
        """Rollback the transaction."""
        pass

    @abstractmethod
    async def __aenter__(self) -> 'Transaction':
        """Enter transaction context."""
        pass

    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit transaction context."""
        pass
