"""
Test utilities and helpers.

This package provides mocking utilities, test data generators,
and helper functions for testing across the test suite.
"""

from .mocking import (
    AsyncIteratorMock,
    AsyncContextManagerMock,
    create_async_mock,
    create_coro_mock,
    ResponseBuilder,
    ClaudeResponseBuilder,
    DiscordMessageBuilder,
    create_mock_with_methods,
    create_error_mock,
    generate_random_string,
    generate_user_id,
    generate_snowflake,
    generate_message_batch,
    FakeDataGenerator,
    mock_environment,
    async_timeout,
    AsyncCallRecorder,
    FrozenTime,
)

__all__ = [
    # Async mocking
    "AsyncIteratorMock",
    "AsyncContextManagerMock",
    "create_async_mock",
    "create_coro_mock",

    # Builders
    "ResponseBuilder",
    "ClaudeResponseBuilder",
    "DiscordMessageBuilder",

    # Mock factories
    "create_mock_with_methods",
    "create_error_mock",

    # Data generators
    "generate_random_string",
    "generate_user_id",
    "generate_snowflake",
    "generate_message_batch",
    "FakeDataGenerator",

    # Context managers
    "mock_environment",
    "async_timeout",

    # Assertion helpers
    "AsyncCallRecorder",

    # Time mocking
    "FrozenTime",
]
