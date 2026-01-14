"""
Integration tests for command logging system.
"""

import pytest
import pytest_asyncio
import tempfile
import os
from datetime import datetime, timedelta
import aiosqlite

from src.logging.logger import CommandLogger
from src.logging.repository import CommandLogRepository
from src.logging.models import CommandLog, CommandType, CommandStatus, LoggingConfig
from src.logging.query import CommandLogQuery
from src.logging.analytics import CommandAnalytics
from src.logging.cleanup import LogCleanupService


@pytest_asyncio.fixture
async def test_db():
    """Create a temporary test database."""
    # Create temp database
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    # Initialize database
    async with aiosqlite.connect(path) as db:
        # Create schema
        await db.execute("""
            CREATE TABLE command_logs (
                id TEXT PRIMARY KEY,
                command_type TEXT NOT NULL,
                command_name TEXT NOT NULL,
                user_id TEXT,
                guild_id TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                parameters TEXT NOT NULL DEFAULT '{}',
                execution_context TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL,
                error_code TEXT,
                error_message TEXT,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                duration_ms INTEGER,
                result_summary TEXT,
                metadata TEXT NOT NULL DEFAULT '{}'
            )
        """)
        await db.commit()

    yield path

    # Cleanup
    try:
        os.unlink(path)
    except:
        pass


@pytest_asyncio.fixture
async def repository(test_db):
    """Create repository with test database."""
    conn = await aiosqlite.connect(test_db)
    repo = CommandLogRepository(conn)
    yield repo
    await conn.close()


@pytest_asyncio.fixture
async def command_logger(repository):
    """Create command logger with test repository."""
    config = LoggingConfig(
        enabled=True,
        async_writes=False,  # Synchronous for testing
        sanitize_enabled=True
    )
    return CommandLogger(repository=repository, config=config)


@pytest.mark.asyncio
class TestCommandLoggingIntegration:
    """Integration tests for command logging."""

    async def test_log_and_retrieve_command(self, command_logger, repository):
        """Test logging a command and retrieving it."""
        # Log a command
        log_entry = await command_logger.log_command(
            command_type=CommandType.SLASH_COMMAND,
            command_name="test_command",
            user_id="user-123",
            guild_id="guild-456",
            channel_id="channel-789",
            parameters={"count": 100, "format": "detailed"}
        )

        # Complete the log
        await command_logger.complete_log(log_entry, {"messages_processed": 50})

        # Retrieve from repository
        retrieved = await repository.get_by_id(log_entry.id)

        assert retrieved is not None
        assert retrieved.command_name == "test_command"
        assert retrieved.user_id == "user-123"
        assert retrieved.status == CommandStatus.SUCCESS
        assert retrieved.result_summary["messages_processed"] == 50

    async def test_log_with_sensitive_data_sanitization(self, command_logger, repository):
        """Test that sensitive data is sanitized."""
        log_entry = await command_logger.log_command(
            command_type=CommandType.WEBHOOK_REQUEST,
            command_name="POST /api/summary",
            user_id=None,
            guild_id="guild-456",
            channel_id="channel-789",
            parameters={
                "api_key": "sk-secret123456",
                "count": 100
            },
            execution_context={
                "source_ip": "192.168.1.100"
            }
        )

        # Retrieve and verify sanitization
        retrieved = await repository.get_by_id(log_entry.id)

        assert retrieved.parameters["api_key"] == "[REDACTED]"
        assert retrieved.parameters["count"] == 100
        assert retrieved.execution_context["source_ip"] == "192.168.*.*"

    async def test_log_failure(self, command_logger, repository):
        """Test logging a failed command."""
        log_entry = await command_logger.log_command(
            command_type=CommandType.SLASH_COMMAND,
            command_name="summarize",
            user_id="user-123",
            guild_id="guild-456",
            channel_id="channel-789",
            parameters={}
        )

        # Mark as failed
        await command_logger.fail_log(
            log_entry,
            error_code="API_ERROR",
            error_message="API request failed with status 500"
        )

        # Retrieve and verify
        retrieved = await repository.get_by_id(log_entry.id)

        assert retrieved.status == CommandStatus.FAILED
        assert retrieved.error_code == "API_ERROR"
        assert "API request failed" in retrieved.error_message
        assert retrieved.duration_ms is not None

    async def test_query_by_guild(self, command_logger, repository):
        """Test querying logs by guild."""
        # Create multiple logs
        for i in range(5):
            await command_logger.log_command(
                command_type=CommandType.SLASH_COMMAND,
                command_name=f"command_{i}",
                user_id=f"user-{i}",
                guild_id="guild-123",
                channel_id="channel-789",
                parameters={}
            )

        # Different guild
        await command_logger.log_command(
            command_type=CommandType.SLASH_COMMAND,
            command_name="other_command",
            user_id="user-999",
            guild_id="guild-999",
            channel_id="channel-999",
            parameters={}
        )

        # Query logs for guild-123
        logs = await CommandLogQuery(repository).by_guild("guild-123").execute()

        assert len(logs) == 5
        assert all(log.guild_id == "guild-123" for log in logs)

    async def test_query_by_status(self, command_logger, repository):
        """Test querying logs by status."""
        # Create successful log
        log1 = await command_logger.log_command(
            command_type=CommandType.SLASH_COMMAND,
            command_name="success_cmd",
            user_id="user-123",
            guild_id="guild-456",
            channel_id="channel-789",
            parameters={}
        )
        await command_logger.complete_log(log1, {})

        # Create failed log
        log2 = await command_logger.log_command(
            command_type=CommandType.SLASH_COMMAND,
            command_name="fail_cmd",
            user_id="user-123",
            guild_id="guild-456",
            channel_id="channel-789",
            parameters={}
        )
        await command_logger.fail_log(log2, "ERROR", "Test error")

        # Query failed logs
        failed_logs = await CommandLogQuery(repository)\
            .by_guild("guild-456")\
            .with_status(CommandStatus.FAILED)\
            .execute()

        assert len(failed_logs) == 1
        assert failed_logs[0].command_name == "fail_cmd"

    async def test_analytics_command_stats(self, command_logger, repository):
        """Test command analytics."""
        # Create successful logs
        for i in range(3):
            log = await command_logger.log_command(
                command_type=CommandType.SLASH_COMMAND,
                command_name="summarize",
                user_id=f"user-{i}",
                guild_id="guild-123",
                channel_id="channel-789",
                parameters={}
            )
            await command_logger.complete_log(log, {})

        # Create failed log
        log = await command_logger.log_command(
            command_type=CommandType.SLASH_COMMAND,
            command_name="summarize",
            user_id="user-999",
            guild_id="guild-123",
            channel_id="channel-789",
            parameters={}
        )
        await command_logger.fail_log(log, "ERROR", "Test error")

        # Get analytics
        analytics = CommandAnalytics(repository)
        stats = await analytics.get_command_stats("guild-123", hours=24)

        assert stats["total_commands"] == 4
        assert stats["success_count"] == 3
        assert stats["failed_count"] == 1
        assert stats["success_rate"] == 75.0

    async def test_cleanup_old_logs(self, command_logger, repository):
        """Test cleanup of old logs."""
        config = LoggingConfig(retention_days=7)

        # Create old log
        old_log = CommandLog(
            command_type=CommandType.SLASH_COMMAND,
            command_name="old_command",
            user_id="user-123",
            guild_id="guild-456",
            channel_id="channel-789",
            started_at=datetime.utcnow() - timedelta(days=10)
        )
        await repository.save(old_log)

        # Create recent log
        recent_log = await command_logger.log_command(
            command_type=CommandType.SLASH_COMMAND,
            command_name="recent_command",
            user_id="user-123",
            guild_id="guild-456",
            channel_id="channel-789",
            parameters={}
        )

        # Run cleanup
        cleanup_service = LogCleanupService(repository, config)
        deleted_count = await cleanup_service.cleanup_expired_logs()

        assert deleted_count == 1

        # Verify old log was deleted
        old_retrieved = await repository.get_by_id(old_log.id)
        assert old_retrieved is None

        # Verify recent log still exists
        recent_retrieved = await repository.get_by_id(recent_log.id)
        assert recent_retrieved is not None
