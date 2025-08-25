"""
Pytest configuration and fixtures for Summary Bot NG test suite.

This module provides shared fixtures and configuration for all test modules,
supporting unit, integration, and end-to-end testing scenarios.
"""

import asyncio
import os
import tempfile
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
import discord
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Test environment setup
os.environ["TESTING"] = "1"
os.environ["CLAUDE_API_KEY"] = "test_api_key"
os.environ["DISCORD_TOKEN"] = "test_discord_token"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield tmp_dir


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    from src.config.settings import BotConfig, GuildConfig, SummaryOptions
    
    guild_config = GuildConfig(
        guild_id="123456789",
        enabled_channels=["channel1", "channel2"],
        excluded_channels=["excluded1"],
        default_summary_options=SummaryOptions(
            summary_length="standard",
            include_bots=False,
            include_attachments=True,
            min_messages=5
        ),
        permission_settings={}
    )
    
    return BotConfig(
        discord_token="test_token",
        claude_api_key="test_api_key",
        guild_configs={"123456789": guild_config},
        webhook_port=5000,
        max_message_batch=10000,
        cache_ttl=3600
    )


@pytest.fixture
def mock_discord_client():
    """Mock Discord client for testing."""
    client = AsyncMock(spec=discord.Client)
    client.user = MagicMock()
    client.user.id = 987654321
    client.user.name = "TestBot"
    return client


@pytest.fixture
def mock_discord_guild():
    """Mock Discord guild for testing."""
    guild = MagicMock(spec=discord.Guild)
    guild.id = 123456789
    guild.name = "Test Guild"
    guild.member_count = 100
    return guild


@pytest.fixture
def mock_discord_channel():
    """Mock Discord text channel for testing."""
    channel = MagicMock(spec=discord.TextChannel)
    channel.id = 987654321
    channel.name = "test-channel"
    channel.guild = MagicMock()
    channel.guild.id = 123456789
    return channel


@pytest.fixture
def mock_discord_user():
    """Mock Discord user for testing."""
    user = MagicMock(spec=discord.User)
    user.id = 111111111
    user.name = "testuser"
    user.display_name = "Test User"
    user.bot = False
    return user


@pytest.fixture
def mock_discord_message(mock_discord_user, mock_discord_channel):
    """Mock Discord message for testing."""
    message = MagicMock(spec=discord.Message)
    message.id = 555555555
    message.author = mock_discord_user
    message.channel = mock_discord_channel
    message.content = "Test message content"
    message.created_at = datetime.utcnow()
    message.attachments = []
    message.embeds = []
    message.reference = None
    return message


@pytest.fixture
def sample_messages(mock_discord_user, mock_discord_channel):
    """Generate sample Discord messages for testing."""
    messages = []
    base_time = datetime.utcnow() - timedelta(hours=1)
    
    for i in range(10):
        message = MagicMock(spec=discord.Message)
        message.id = 1000000000 + i
        message.author = mock_discord_user
        message.channel = mock_discord_channel
        message.content = f"Test message {i+1}"
        message.created_at = base_time + timedelta(minutes=i * 5)
        message.attachments = []
        message.embeds = []
        message.reference = None
        messages.append(message)
    
    return messages


@pytest.fixture
def mock_claude_client():
    """Mock Claude API client for testing."""
    from src.summarization.claude_client import ClaudeClient
    
    client = AsyncMock(spec=ClaudeClient)
    client.create_summary.return_value = MagicMock(
        content="This is a test summary of the conversation.",
        usage=MagicMock(
            input_tokens=1000,
            output_tokens=200,
            total_tokens=1200
        )
    )
    client.health_check.return_value = True
    return client


@pytest.fixture
def mock_database():
    """Mock database session for testing."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_cache():
    """Mock cache interface for testing."""
    from src.cache.base import CacheInterface
    
    cache = AsyncMock(spec=CacheInterface)
    cache.get.return_value = None
    cache.set.return_value = True
    cache.delete.return_value = True
    cache.clear.return_value = 0
    return cache


@pytest.fixture
async def test_db_engine():
    """Create test database engine."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    yield engine
    await engine.dispose()


@pytest.fixture
async def test_db_session(test_db_engine):
    """Create test database session."""
    async_session = sessionmaker(
        test_db_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session


@pytest.fixture
def mock_summarization_engine():
    """Mock summarization engine for testing."""
    from src.summarization.engine import SummarizationEngine
    
    engine = AsyncMock(spec=SummarizationEngine)
    engine.summarize_messages.return_value = MagicMock(
        id="test_summary_123",
        channel_id="987654321",
        guild_id="123456789",
        start_time=datetime.utcnow() - timedelta(hours=1),
        end_time=datetime.utcnow(),
        message_count=10,
        key_points=["Point 1", "Point 2"],
        action_items=[],
        technical_terms=[],
        participants=["testuser"],
        summary_text="This is a test summary.",
        metadata={},
        created_at=datetime.utcnow()
    )
    return engine


@pytest.fixture
def mock_permission_manager():
    """Mock permission manager for testing."""
    from src.permissions.manager import PermissionManager
    
    manager = AsyncMock(spec=PermissionManager)
    manager.check_channel_access.return_value = True
    manager.check_command_permission.return_value = True
    manager.get_user_permissions.return_value = MagicMock(
        can_summarize=True,
        can_schedule=True,
        can_configure=False
    )
    return manager


@pytest.fixture
def mock_message_fetcher():
    """Mock message fetcher for testing."""
    from src.message_processing.fetcher import MessageFetcher
    
    fetcher = AsyncMock(spec=MessageFetcher)
    return fetcher


@pytest.fixture
def mock_task_scheduler():
    """Mock task scheduler for testing."""
    from src.scheduling.scheduler import TaskScheduler
    
    scheduler = AsyncMock(spec=TaskScheduler)
    scheduler.schedule_task.return_value = "task_123"
    scheduler.cancel_task.return_value = True
    scheduler.get_scheduled_tasks.return_value = []
    return scheduler


@pytest.fixture
def mock_webhook_server():
    """Mock webhook server for testing."""
    from src.webhook_service.server import WebhookServer
    
    server = AsyncMock(spec=WebhookServer)
    return server


# Test data factories
@pytest.fixture
def summary_result_factory():
    """Factory for creating SummaryResult test objects."""
    def create_summary_result(**kwargs):
        from src.models.summary import SummaryResult
        
        defaults = {
            "id": "test_summary_123",
            "channel_id": "987654321",
            "guild_id": "123456789",
            "start_time": datetime.utcnow() - timedelta(hours=1),
            "end_time": datetime.utcnow(),
            "message_count": 10,
            "key_points": ["Point 1", "Point 2"],
            "action_items": [],
            "technical_terms": [],
            "participants": ["testuser"],
            "summary_text": "This is a test summary.",
            "metadata": {},
            "created_at": datetime.utcnow()
        }
        defaults.update(kwargs)
        return SummaryResult(**defaults)
    
    return create_summary_result


@pytest.fixture
def processed_message_factory():
    """Factory for creating ProcessedMessage test objects."""
    def create_processed_message(**kwargs):
        from src.models.message import ProcessedMessage
        
        defaults = {
            "id": "555555555",
            "author_name": "testuser",
            "author_id": "111111111",
            "content": "Test message content",
            "timestamp": datetime.utcnow(),
            "thread_info": None,
            "attachments": [],
            "references": []
        }
        defaults.update(kwargs)
        return ProcessedMessage(**defaults)
    
    return create_processed_message


# Error simulation fixtures
@pytest.fixture
def claude_api_error():
    """Simulate Claude API error."""
    from src.exceptions.summarization import ClaudeAPIError
    return ClaudeAPIError("API rate limit exceeded", "RATE_LIMIT_EXCEEDED")


@pytest.fixture
def discord_permission_error():
    """Simulate Discord permission error."""
    from src.exceptions.discord_errors import DiscordPermissionError
    return DiscordPermissionError("Missing read message history permission", "MISSING_PERMISSIONS")


@pytest.fixture
def insufficient_content_error():
    """Simulate insufficient content error."""
    from src.exceptions.summarization import InsufficientContentError
    return InsufficientContentError("Not enough messages for summarization", "INSUFFICIENT_CONTENT")


# Test utilities
@pytest.fixture
def assert_logs():
    """Utility for asserting log messages in tests."""
    def _assert_logs(caplog, level, message_contains):
        assert any(
            level.upper() in record.levelname and message_contains in record.message
            for record in caplog.records
        )
    return _assert_logs


@pytest.fixture
def performance_monitor():
    """Monitor performance during tests."""
    import time
    
    class PerformanceMonitor:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def start(self):
            self.start_time = time.time()
        
        def stop(self):
            self.end_time = time.time()
        
        @property
        def duration(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None
    
    return PerformanceMonitor()


# Async test markers
pytest_asyncio.plugin.pytest_asyncio_mode = "auto"


# Custom markers for test categorization
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "e2e: marks tests as end-to-end tests"
    )
    config.addinivalue_line(
        "markers", "performance: marks tests as performance tests"
    )
    config.addinivalue_line(
        "markers", "security: marks tests as security tests"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )


# Cleanup hooks
@pytest.fixture(autouse=True)
async def cleanup_after_test():
    """Cleanup resources after each test."""
    yield
    # Add any cleanup logic here
    pass