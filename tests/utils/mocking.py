"""
Mocking utilities and helpers for testing.

Provides AsyncMock utilities, mock factories, response builders,
and test data generators for consistent mocking across test suites.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Union, TypeVar, Generic
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from contextlib import asynccontextmanager, contextmanager
import random
import string


T = TypeVar('T')


# AsyncMock Utilities

class AsyncIteratorMock:
    """Mock async iterator for testing async for loops."""

    def __init__(self, items: List[Any]):
        """Initialize with items to iterate over."""
        self.items = items
        self.index = 0

    def __aiter__(self):
        """Return self as async iterator."""
        return self

    async def __anext__(self):
        """Get next item asynchronously."""
        if self.index >= len(self.items):
            raise StopAsyncIteration
        item = self.items[self.index]
        self.index += 1
        await asyncio.sleep(0)  # Simulate async operation
        return item


class AsyncContextManagerMock:
    """Mock async context manager for testing async with statements."""

    def __init__(self, return_value: Any = None, side_effect: Optional[Exception] = None):
        """Initialize with return value or exception."""
        self.return_value = return_value
        self.side_effect = side_effect
        self.enter_called = False
        self.exit_called = False

    async def __aenter__(self):
        """Enter async context."""
        self.enter_called = True
        if self.side_effect:
            raise self.side_effect
        return self.return_value

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context."""
        self.exit_called = True
        return False


def create_async_mock(return_value: Any = None, side_effect: Optional[Exception] = None) -> AsyncMock:
    """Create configured AsyncMock with common patterns."""
    mock = AsyncMock()

    if side_effect:
        mock.side_effect = side_effect
    elif return_value is not None:
        mock.return_value = return_value

    return mock


def create_coro_mock(return_value: Any = None) -> Mock:
    """Create a mock that returns a coroutine."""
    async def coro(*args, **kwargs):
        return return_value

    mock = Mock()
    mock.return_value = coro()
    return mock


# Response Builder Classes

class ResponseBuilder(Generic[T]):
    """Builder pattern for creating test response objects."""

    def __init__(self, base_class: type):
        """Initialize with base class."""
        self.base_class = base_class
        self.attributes: Dict[str, Any] = {}

    def with_attr(self, name: str, value: Any) -> 'ResponseBuilder[T]':
        """Set an attribute."""
        self.attributes[name] = value
        return self

    def with_attrs(self, **kwargs) -> 'ResponseBuilder[T]':
        """Set multiple attributes."""
        self.attributes.update(kwargs)
        return self

    def build(self) -> T:
        """Build the object."""
        obj = MagicMock(spec=self.base_class)
        for name, value in self.attributes.items():
            setattr(obj, name, value)
        return obj


class ClaudeResponseBuilder:
    """Builder for creating Claude API response mocks."""

    def __init__(self):
        """Initialize with defaults."""
        self.content = "Default summary content"
        self.model = "claude-3-sonnet-20240229"
        self.input_tokens = 1000
        self.output_tokens = 200
        self.stop_reason = "end_turn"
        self.response_id = "msg_test123"

    def with_content(self, content: str) -> 'ClaudeResponseBuilder':
        """Set response content."""
        self.content = content
        return self

    def with_model(self, model: str) -> 'ClaudeResponseBuilder':
        """Set model name."""
        self.model = model
        return self

    def with_tokens(self, input_tokens: int, output_tokens: int) -> 'ClaudeResponseBuilder':
        """Set token counts."""
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        return self

    def truncated(self) -> 'ClaudeResponseBuilder':
        """Configure as truncated response."""
        self.stop_reason = "max_tokens"
        return self

    def build(self):
        """Build the response object."""
        from src.summarization.claude_client import ClaudeResponse

        return ClaudeResponse(
            content=self.content,
            model=self.model,
            usage={"input_tokens": self.input_tokens, "output_tokens": self.output_tokens},
            stop_reason=self.stop_reason,
            response_id=self.response_id,
            created_at=datetime.utcnow()
        )


class DiscordMessageBuilder:
    """Builder for creating Discord message mocks."""

    def __init__(self):
        """Initialize with defaults."""
        self.message_id = random.randint(100000000, 999999999)
        self.content = "Test message"
        self.author_id = 111111111
        self.author_name = "testuser"
        self.channel_id = 987654321
        self.timestamp = datetime.utcnow()
        self.attachments_list = []
        self.embeds_list = []
        self.is_bot = False

    def with_id(self, message_id: int) -> 'DiscordMessageBuilder':
        """Set message ID."""
        self.message_id = message_id
        return self

    def with_content(self, content: str) -> 'DiscordMessageBuilder':
        """Set message content."""
        self.content = content
        return self

    def with_author(self, user_id: int, username: str, is_bot: bool = False) -> 'DiscordMessageBuilder':
        """Set message author."""
        self.author_id = user_id
        self.author_name = username
        self.is_bot = is_bot
        return self

    def with_timestamp(self, timestamp: datetime) -> 'DiscordMessageBuilder':
        """Set message timestamp."""
        self.timestamp = timestamp
        return self

    def with_attachments(self, count: int = 1) -> 'DiscordMessageBuilder':
        """Add attachments."""
        for i in range(count):
            attachment = MagicMock()
            attachment.filename = f"file_{i}.pdf"
            attachment.url = f"https://cdn.discord.com/file_{i}.pdf"
            self.attachments_list.append(attachment)
        return self

    def from_bot(self) -> 'DiscordMessageBuilder':
        """Configure as bot message."""
        self.is_bot = True
        return self

    def build(self) -> MagicMock:
        """Build the message mock."""
        import discord

        message = MagicMock(spec=discord.Message)
        message.id = self.message_id
        message.content = self.content
        message.created_at = self.timestamp

        # Author
        author = MagicMock(spec=discord.User)
        author.id = self.author_id
        author.name = self.author_name
        author.bot = self.is_bot
        message.author = author

        # Channel
        channel = MagicMock(spec=discord.TextChannel)
        channel.id = self.channel_id
        message.channel = channel

        # Attachments and embeds
        message.attachments = self.attachments_list
        message.embeds = self.embeds_list

        return message


# Mock Factory Functions

def create_mock_with_methods(spec_class: type, **methods) -> MagicMock:
    """Create a mock with specified methods configured."""
    mock = MagicMock(spec=spec_class)

    for method_name, return_value in methods.items():
        method = getattr(mock, method_name)
        if asyncio.iscoroutinefunction(getattr(spec_class, method_name, None)):
            method.return_value = return_value
        else:
            method.return_value = return_value

    return mock


def create_error_mock(exception_class: type, message: str = "Mock error") -> Mock:
    """Create a mock that raises an exception when called."""
    mock = Mock()
    mock.side_effect = exception_class(message)
    return mock


# Test Data Generators

def generate_random_string(length: int = 10, include_special: bool = False) -> str:
    """Generate random string for testing."""
    chars = string.ascii_letters + string.digits
    if include_special:
        chars += string.punctuation

    return ''.join(random.choice(chars) for _ in range(length))


def generate_user_id() -> str:
    """Generate random Discord-style user ID."""
    return str(random.randint(100000000000000000, 999999999999999999))


def generate_snowflake() -> int:
    """Generate Discord snowflake ID."""
    return random.randint(100000000000000000, 999999999999999999)


def generate_message_batch(
    count: int = 10,
    start_time: Optional[datetime] = None,
    interval_minutes: int = 5
) -> List[Dict[str, Any]]:
    """Generate a batch of message data."""
    if start_time is None:
        start_time = datetime.utcnow() - timedelta(hours=2)

    messages = []
    for i in range(count):
        messages.append({
            "id": generate_snowflake(),
            "content": f"Message content {i+1}",
            "author_id": generate_user_id(),
            "timestamp": start_time + timedelta(minutes=i * interval_minutes),
            "channel_id": generate_snowflake()
        })

    return messages


class FakeDataGenerator:
    """Generator for realistic fake data."""

    FIRST_NAMES = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Henry"]
    LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis"]
    TOPICS = ["API design", "Database optimization", "UI improvements", "Bug fixes", "Testing strategy"]

    @staticmethod
    def username() -> str:
        """Generate realistic username."""
        first = random.choice(FakeDataGenerator.FIRST_NAMES).lower()
        last = random.choice(FakeDataGenerator.LAST_NAMES).lower()
        number = random.randint(1, 999)
        return f"{first}_{last}{number}"

    @staticmethod
    def display_name() -> str:
        """Generate realistic display name."""
        first = random.choice(FakeDataGenerator.FIRST_NAMES)
        last = random.choice(FakeDataGenerator.LAST_NAMES)
        return f"{first} {last}"

    @staticmethod
    def channel_name() -> str:
        """Generate realistic channel name."""
        prefixes = ["general", "dev", "team", "project", "support"]
        suffixes = ["chat", "discussion", "updates", "questions", "logs"]
        return f"{random.choice(prefixes)}-{random.choice(suffixes)}"

    @staticmethod
    def message_content(include_mention: bool = False) -> str:
        """Generate realistic message content."""
        templates = [
            "Hey team, {topic}",
            "I think we should focus on {topic}",
            "Quick update on {topic}",
            "Does anyone have thoughts on {topic}?",
            "Great progress on {topic} today!",
        ]

        template = random.choice(templates)
        topic = random.choice(FakeDataGenerator.TOPICS)
        content = template.format(topic=topic)

        if include_mention:
            content = f"<@{generate_user_id()}> {content}"

        return content


# Context Managers

@contextmanager
def mock_environment(**env_vars):
    """Temporarily set environment variables for testing."""
    import os

    old_env = {}
    for key, value in env_vars.items():
        old_env[key] = os.environ.get(key)
        os.environ[key] = str(value)

    try:
        yield
    finally:
        for key, old_value in old_env.items():
            if old_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old_value


@asynccontextmanager
async def async_timeout(seconds: float = 1.0):
    """Context manager for testing async timeout behavior."""
    try:
        async with asyncio.timeout(seconds):
            yield
    except asyncio.TimeoutError:
        raise


# Assertion Helpers

class AsyncCallRecorder:
    """Record async function calls for assertion."""

    def __init__(self):
        """Initialize call recorder."""
        self.calls: List[Dict[str, Any]] = []

    async def record(self, *args, **kwargs):
        """Record a call."""
        self.calls.append({
            "args": args,
            "kwargs": kwargs,
            "timestamp": datetime.utcnow()
        })

    def assert_called_once(self):
        """Assert function was called exactly once."""
        assert len(self.calls) == 1, f"Expected 1 call, got {len(self.calls)}"

    def assert_called_with(self, *args, **kwargs):
        """Assert function was called with specific arguments."""
        for call in self.calls:
            if call["args"] == args and call["kwargs"] == kwargs:
                return
        raise AssertionError(f"No call found with args={args}, kwargs={kwargs}")

    def assert_not_called(self):
        """Assert function was never called."""
        assert len(self.calls) == 0, f"Expected no calls, got {len(self.calls)}"

    @property
    def call_count(self) -> int:
        """Get number of calls."""
        return len(self.calls)


# Time Mocking

class FrozenTime:
    """Mock time that doesn't advance."""

    def __init__(self, frozen_datetime: datetime):
        """Initialize with frozen time."""
        self.frozen_datetime = frozen_datetime

    def now(self) -> datetime:
        """Get current (frozen) time."""
        return self.frozen_datetime

    def utcnow(self) -> datetime:
        """Get current (frozen) UTC time."""
        return self.frozen_datetime

    def advance(self, **kwargs):
        """Advance frozen time by delta."""
        self.frozen_datetime += timedelta(**kwargs)

    @contextmanager
    def patch_datetime(self):
        """Patch datetime module to use frozen time."""
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = self.frozen_datetime
            mock_datetime.utcnow.return_value = self.frozen_datetime
            yield self
