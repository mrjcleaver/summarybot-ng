# Async Testing Best Practices Guide

**Purpose**: Guide for writing reliable async tests in SummaryBot-NG
**Audience**: Developers writing unit, integration, and E2E tests
**Last Updated**: 2025-12-31

## Table of Contents

1. [Overview](#overview)
2. [Async/Sync Compatibility](#asyncsync-compatibility)
3. [Test Fixtures](#test-fixtures)
4. [Common Patterns](#common-patterns)
5. [Troubleshooting](#troubleshooting)
6. [Examples](#examples)

## Overview

SummaryBot-NG uses asyncio extensively for Discord bot interactions, API calls, and database operations. Testing async code requires special considerations to ensure tests accurately reflect production behavior.

### Key Principles

1. **Mirror Production**: Tests should behave like production code
2. **Explicit Async**: Always mark async functions and fixtures explicitly
3. **Await Everything**: Never forget to await coroutines
4. **Handle Both**: Support both sync and async mocks when needed

## Async/Sync Compatibility

### The Problem

Discord.py and other libraries have methods that are synchronous in production but may be mocked as async in tests. This creates a compatibility challenge.

**Example Issue**:
```python
# In production: is_done() is synchronous
if interaction.response.is_done():  # ✅ Works in production
    ...

# In tests: is_done() returns a coroutine when mocked
if interaction.response.is_done():  # ❌ RuntimeWarning: coroutine not awaited
    ...
```

### The Solution

Use `inspect.iscoroutine()` to detect and handle both cases:

```python
import inspect

# Handle both sync and async is_done()
is_done_result = interaction.response.is_done()
if inspect.iscoroutine(is_done_result):
    is_done = await is_done_result  # Async mock
else:
    is_done = is_done_result  # Sync production

if is_done:
    await interaction.followup.send(embed=embed)
```

### When to Use This Pattern

Apply this pattern when:
- Method may be sync in production, async in tests
- Using `AsyncMock` for Discord interaction objects
- Testing code that calls methods on mocked objects
- Seeing "coroutine was never awaited" warnings

### Common Methods Requiring This Pattern

```python
# Discord.py interactions
interaction.response.is_done()
interaction.response.defer()

# Custom methods that might be mocked
client.get_usage_stats()
manager.check_permission()

# Any method that returns different types in prod vs test
```

## Test Fixtures

### Async Fixture Decorators

**Rule**: Use `@pytest_asyncio.fixture` for async fixtures, `@pytest.fixture` for sync fixtures.

#### Correct Usage

```python
import pytest
import pytest_asyncio

# ✅ Async fixture
@pytest_asyncio.fixture
async def service_container():
    """Create service container."""
    container = ServiceContainer()
    await container.initialize()
    yield container
    await container.cleanup()

# ✅ Sync fixture
@pytest.fixture
def bot_config():
    """Create bot configuration."""
    return BotConfig(
        discord_token="test_token",
        claude_api_key="test_key"
    )
```

#### Incorrect Usage

```python
import pytest

# ❌ WRONG - async fixture with @pytest.fixture
@pytest.fixture
async def service_container():  # Will cause deprecation warnings
    ...

# ❌ WRONG - missing decorator
async def service_container():  # Won't be recognized as fixture
    ...
```

### Fixture Scope

Choose appropriate scope based on fixture lifetime:

```python
# Session-level: Shared across all tests (expensive setup)
@pytest_asyncio.fixture(scope="session")
async def database_pool():
    pool = await create_pool()
    yield pool
    await pool.close()

# Module-level: Shared within test module
@pytest_asyncio.fixture(scope="module")
async def bot_instance():
    bot = SummaryBot(config)
    await bot.initialize()
    yield bot
    await bot.cleanup()

# Function-level: New instance per test (default)
@pytest_asyncio.fixture
async def mock_interaction():
    return AsyncMock(spec=discord.Interaction)
```

### Fixture Dependencies

Async fixtures can depend on both sync and async fixtures:

```python
@pytest.fixture
def config():
    """Sync fixture."""
    return BotConfig()

@pytest_asyncio.fixture
async def database(config):
    """Async fixture depending on sync fixture."""
    db = Database(config.database_url)
    await db.connect()
    yield db
    await db.disconnect()

@pytest_asyncio.fixture
async def container(config, database):
    """Async fixture depending on both."""
    container = ServiceContainer(config, database)
    await container.initialize()
    yield container
    await container.cleanup()
```

## Common Patterns

### Pattern 1: Testing Async Methods

```python
import pytest

@pytest.mark.asyncio
async def test_async_method():
    """Test an async method."""
    engine = SummarizationEngine()

    # ✅ Await async methods
    result = await engine.create_summary(messages)

    # ✅ Assert on result
    assert result.summary_text
    assert len(result.action_items) > 0
```

### Pattern 2: Mock Async Dependencies

```python
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_with_async_mock():
    """Test with async mock."""
    # ✅ Use AsyncMock for async methods
    mock_client = AsyncMock()
    mock_client.create_message.return_value = {"id": "msg_123"}

    engine = SummarizationEngine(client=mock_client)
    result = await engine.create_summary(messages)

    # ✅ Verify async mock was called
    mock_client.create_message.assert_called_once()
```

### Pattern 3: Testing Error Handling

```python
@pytest.mark.asyncio
async def test_error_handling():
    """Test async error handling."""
    mock_client = AsyncMock()

    # ✅ Make async mock raise exception
    mock_client.create_message.side_effect = APIError("Rate limited")

    engine = SummarizationEngine(client=mock_client)

    # ✅ Use pytest.raises for async exceptions
    with pytest.raises(APIError):
        await engine.create_summary(messages)
```

### Pattern 4: Mixed Sync/Async Mocks

```python
from unittest.mock import MagicMock, AsyncMock

@pytest.mark.asyncio
async def test_mixed_mocks():
    """Test with both sync and async mocks."""
    # ✅ Sync properties use MagicMock
    mock_interaction = MagicMock()
    mock_interaction.user.id = 12345
    mock_interaction.guild_id = 67890

    # ✅ Async methods use AsyncMock
    mock_interaction.response = MagicMock()
    mock_interaction.response.is_done.return_value = False  # Sync return
    mock_interaction.response.send_message = AsyncMock()  # Async method

    # Use in test
    handler = CommandHandler()
    await handler.handle_interaction(mock_interaction)

    # ✅ Verify async method called
    mock_interaction.response.send_message.assert_called_once()
```

### Pattern 5: Parametrized Async Tests

```python
@pytest.mark.asyncio
@pytest.mark.parametrize("message_count,expected_length", [
    (10, "short"),
    (100, "standard"),
    (1000, "detailed"),
])
async def test_summary_length(message_count, expected_length):
    """Test summary adapts to message count."""
    messages = create_test_messages(message_count)
    engine = SummarizationEngine()

    result = await engine.create_summary(messages)

    assert result.summary_length == expected_length
```

## Troubleshooting

### Common Errors and Solutions

#### Error 1: "coroutine was never awaited"

**Symptom**:
```
RuntimeWarning: coroutine 'AsyncMockMixin._execute_mock_call' was never awaited
```

**Cause**: Calling async mock method without await

**Solution**:
```python
# ❌ WRONG
result = mock_client.create_message()

# ✅ CORRECT
result = await mock_client.create_message()
```

#### Error 2: "SyntaxError: 'await' outside async function"

**Symptom**:
```python
SyntaxError: 'await' outside async function
```

**Cause**: Using await in non-async function

**Solution**:
```python
# ❌ WRONG
@pytest.mark.asyncio
def test_something():  # Missing 'async'
    result = await some_async_function()

# ✅ CORRECT
@pytest.mark.asyncio
async def test_something():  # Added 'async'
    result = await some_async_function()
```

#### Error 3: "pytest-asyncio fixture deprecation warning"

**Symptom**:
```
PytestDeprecationWarning: asyncio test requested async @pytest.fixture in strict mode
```

**Cause**: Using `@pytest.fixture` instead of `@pytest_asyncio.fixture`

**Solution**:
```python
# ❌ WRONG
@pytest.fixture
async def async_fixture():
    ...

# ✅ CORRECT
@pytest_asyncio.fixture
async def async_fixture():
    ...
```

#### Error 4: "Expected int parameter, received MagicMock"

**Symptom**:
```
TypeError: Expected int parameter, received MagicMock instead
```

**Cause**: Mock returning MagicMock instead of actual value

**Solution**:
```python
# ❌ WRONG - MagicMock returns MagicMock for attributes
mock_embed = MagicMock()
# mock_embed.color returns MagicMock, not int

# ✅ CORRECT - Return actual dict with real values
mock_result.summary_embed_dict = {
    "title": "Summary",
    "color": 0x00FF00,  # Real int value
    "fields": []
}
```

## Examples

### Example 1: Complete Test with Fixtures

```python
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def bot_config():
    """Sync fixture for config."""
    return BotConfig(
        discord_token="test_token",
        claude_api_key="test_key"
    )

@pytest_asyncio.fixture
async def service_container(bot_config):
    """Async fixture for container."""
    container = ServiceContainer(bot_config)
    await container.initialize()
    yield container
    await container.cleanup()

@pytest.mark.asyncio
async def test_summarize_command(service_container):
    """Test summarize command end-to-end."""
    # Arrange
    mock_interaction = MagicMock(spec=discord.Interaction)
    mock_interaction.user.id = 12345
    mock_interaction.channel_id = 67890
    mock_interaction.response = MagicMock()
    mock_interaction.response.is_done.return_value = False
    mock_interaction.response.send_message = AsyncMock()

    handler = SummarizeCommandHandler(
        summarization_engine=service_container.summarization_engine
    )

    # Act
    await handler.handle_command(mock_interaction)

    # Assert
    mock_interaction.response.send_message.assert_called_once()
    call_args = mock_interaction.response.send_message.call_args
    assert 'embed' in call_args.kwargs
```

### Example 2: Testing with Real Discord Objects

```python
import discord
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_with_real_discord_embed():
    """Test using actual Discord embed."""
    # Create real Discord embed
    embed = discord.Embed(
        title="Test Summary",
        description="This is a test",
        color=0x00FF00
    )
    embed.add_field(name="Messages", value="10", inline=True)

    # Mock interaction but use real embed
    mock_interaction = AsyncMock(spec=discord.Interaction)

    # Send embed
    await mock_interaction.response.send_message(embed=embed)

    # Verify
    mock_interaction.response.send_message.assert_called_once()
    sent_embed = mock_interaction.response.send_message.call_args.kwargs['embed']
    assert sent_embed.title == "Test Summary"
    assert sent_embed.color.value == 0x00FF00
```

### Example 3: Integration Test Pattern

```python
@pytest.mark.integration
class TestDiscordIntegration:
    """Integration tests for Discord bot."""

    @pytest_asyncio.fixture
    async def bot_instance(self, bot_config):
        """Create bot for each test."""
        bot = SummaryBot(bot_config)
        await bot.initialize()
        yield bot
        await bot.cleanup()

    @pytest.mark.asyncio
    async def test_bot_startup(self, bot_instance):
        """Test bot starts successfully."""
        assert bot_instance.is_ready
        assert bot_instance.client.user is not None

    @pytest.mark.asyncio
    async def test_command_registration(self, bot_instance):
        """Test commands are registered."""
        await bot_instance.setup_commands()
        command_count = bot_instance.command_registry.get_command_count()
        assert command_count > 0
```

## Best Practices Checklist

### Writing Tests
- [ ] Use `@pytest.mark.asyncio` for async test functions
- [ ] Use `@pytest_asyncio.fixture` for async fixtures
- [ ] Always await async function calls
- [ ] Use `AsyncMock` for async methods, `MagicMock` for sync
- [ ] Handle both sync and async with `inspect.iscoroutine()`

### Mocking
- [ ] Mock at the right level (unit vs integration)
- [ ] Return real values, not MagicMock objects
- [ ] Configure sync properties with `MagicMock`
- [ ] Configure async methods with `AsyncMock`
- [ ] Verify mocks were called as expected

### Assertions
- [ ] Assert on actual values, not string representations
- [ ] Check object attributes directly
- [ ] Verify mock call counts and arguments
- [ ] Test both success and error cases
- [ ] Include edge cases and boundary conditions

## Additional Resources

### Documentation
- [pytest-asyncio docs](https://pytest-asyncio.readthedocs.io/)
- [unittest.mock docs](https://docs.python.org/3/library/unittest.mock.html)
- [Discord.py docs](https://discordpy.readthedocs.io/)

### Related Guides
- `DEBUG_FIXES_REPORT.md` - Recent bug fixes and lessons learned
- `TESTING_GUIDE.md` - General testing practices
- `SPARC_INTEGRATION_TEST_ARCHITECTURE.md` - Integration test patterns

---

**Last Updated**: 2025-12-31
**Maintained By**: SummaryBot-NG Team
**Version**: 1.0
