"""
Tests for command logging models.
"""

import pytest
from datetime import datetime, timedelta
import os
from src.logging.models import (
    CommandLog,
    CommandType,
    CommandStatus,
    LoggingConfig
)


class TestCommandType:
    """Test CommandType enum."""

    def test_command_type_values(self):
        """Test all command type values are defined."""
        assert CommandType.SLASH_COMMAND.value == "slash_command"
        assert CommandType.SCHEDULED_TASK.value == "scheduled_task"
        assert CommandType.WEBHOOK_REQUEST.value == "webhook_request"


class TestCommandStatus:
    """Test CommandStatus enum."""

    def test_command_status_values(self):
        """Test all command status values are defined."""
        assert CommandStatus.SUCCESS.value == "success"
        assert CommandStatus.FAILED.value == "failed"
        assert CommandStatus.TIMEOUT.value == "timeout"
        assert CommandStatus.CANCELLED.value == "cancelled"


class TestCommandLog:
    """Test CommandLog dataclass."""

    def test_create_minimal_log(self):
        """Test creating a log with minimal fields."""
        log = CommandLog(
            command_type=CommandType.SLASH_COMMAND,
            command_name="test_command",
            guild_id="123456",
            channel_id="789012"
        )

        assert log.id is not None
        assert log.command_type == CommandType.SLASH_COMMAND
        assert log.command_name == "test_command"
        assert log.guild_id == "123456"
        assert log.channel_id == "789012"
        assert log.status == CommandStatus.SUCCESS
        assert log.started_at is not None

    def test_create_complete_log(self):
        """Test creating a log with all fields."""
        started_at = datetime.utcnow()
        completed_at = started_at + timedelta(seconds=5)

        log = CommandLog(
            id="test-log-123",
            command_type=CommandType.SLASH_COMMAND,
            command_name="summarize",
            user_id="user-123",
            guild_id="guild-456",
            channel_id="channel-789",
            parameters={"count": 100, "format": "detailed"},
            execution_context={"interaction_id": "int-123"},
            status=CommandStatus.SUCCESS,
            error_code=None,
            error_message=None,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=5000,
            result_summary={"messages_processed": 50},
            metadata={"model": "claude-3-sonnet"}
        )

        assert log.id == "test-log-123"
        assert log.user_id == "user-123"
        assert log.parameters["count"] == 100
        assert log.duration_ms == 5000
        assert log.result_summary["messages_processed"] == 50

    def test_to_dict(self):
        """Test converting log to dictionary."""
        log = CommandLog(
            command_type=CommandType.SLASH_COMMAND,
            command_name="test",
            guild_id="123",
            channel_id="456"
        )

        log_dict = log.to_dict()

        assert log_dict["id"] == log.id
        assert log_dict["command_type"] == "slash_command"
        assert log_dict["command_name"] == "test"
        assert log_dict["guild_id"] == "123"
        assert log_dict["status"] == "success"
        assert isinstance(log_dict["parameters"], str)  # JSON string
        assert isinstance(log_dict["started_at"], str)  # ISO format

    def test_from_dict(self):
        """Test creating log from dictionary."""
        data = {
            "id": "test-123",
            "command_type": "slash_command",
            "command_name": "test",
            "user_id": "user-123",
            "guild_id": "guild-456",
            "channel_id": "channel-789",
            "parameters": '{"key": "value"}',
            "execution_context": '{}',
            "status": "success",
            "error_code": None,
            "error_message": None,
            "started_at": datetime.utcnow().isoformat(),
            "completed_at": None,
            "duration_ms": None,
            "result_summary": '{}',
            "metadata": '{}'
        }

        log = CommandLog.from_dict(data)

        assert log.id == "test-123"
        assert log.command_type == CommandType.SLASH_COMMAND
        assert log.command_name == "test"
        assert log.user_id == "user-123"
        assert log.parameters == {"key": "value"}
        assert log.status == CommandStatus.SUCCESS

    def test_scheduled_task_log(self):
        """Test log for scheduled task (no user_id)."""
        log = CommandLog(
            command_type=CommandType.SCHEDULED_TASK,
            command_name="daily_summary",
            user_id=None,
            guild_id="guild-123",
            channel_id="channel-456"
        )

        assert log.user_id is None
        assert log.command_type == CommandType.SCHEDULED_TASK


class TestLoggingConfig:
    """Test LoggingConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = LoggingConfig()

        assert config.enabled is True
        assert config.retention_days == 90
        assert config.async_writes is True
        assert config.batch_size == 100
        assert config.flush_interval_seconds == 5
        assert config.sanitize_enabled is True
        assert config.max_message_length == 200
        assert "token" in config.redact_patterns
        assert "password" in config.redact_patterns

    def test_from_env_default(self):
        """Test loading config from environment with defaults."""
        # Clear any existing env vars
        env_vars = [
            "COMMAND_LOG_ENABLED",
            "COMMAND_LOG_RETENTION_DAYS",
            "COMMAND_LOG_ASYNC_WRITES",
            "COMMAND_LOG_BATCH_SIZE"
        ]
        for var in env_vars:
            os.environ.pop(var, None)

        config = LoggingConfig.from_env()

        assert config.enabled is True
        assert config.retention_days == 90

    def test_from_env_custom(self):
        """Test loading config from environment with custom values."""
        os.environ["COMMAND_LOG_ENABLED"] = "false"
        os.environ["COMMAND_LOG_RETENTION_DAYS"] = "30"
        os.environ["COMMAND_LOG_BATCH_SIZE"] = "50"
        os.environ["COMMAND_LOG_FLUSH_INTERVAL_SECONDS"] = "10"

        try:
            config = LoggingConfig.from_env()

            assert config.enabled is False
            assert config.retention_days == 30
            assert config.batch_size == 50
            assert config.flush_interval_seconds == 10
        finally:
            # Clean up
            for var in [
                "COMMAND_LOG_ENABLED",
                "COMMAND_LOG_RETENTION_DAYS",
                "COMMAND_LOG_BATCH_SIZE",
                "COMMAND_LOG_FLUSH_INTERVAL_SECONDS"
            ]:
                os.environ.pop(var, None)

    def test_custom_config(self):
        """Test creating custom configuration."""
        config = LoggingConfig(
            enabled=False,
            retention_days=30,
            batch_size=50,
            redact_patterns=["secret", "key"]
        )

        assert config.enabled is False
        assert config.retention_days == 30
        assert config.batch_size == 50
        assert config.redact_patterns == ["secret", "key"]
