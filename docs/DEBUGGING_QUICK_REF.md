# Debugging Quick Reference

**Quick reference for common debugging scenarios in SummaryBot-NG**

## Async Testing Issues

### "coroutine was never awaited"

```python
# ❌ WRONG
result = async_function()

# ✅ CORRECT
result = await async_function()
```

### Mock async methods properly

```python
from unittest.mock import AsyncMock, MagicMock

# ✅ Async methods
mock.async_method = AsyncMock()
await mock.async_method()

# ✅ Sync properties
mock.sync_property = MagicMock()
value = mock.sync_property
```

### Handle both sync and async

```python
import inspect

result = method_that_might_be_async()
if inspect.iscoroutine(result):
    result = await result
```

## Test Fixtures

### Async fixtures

```python
import pytest_asyncio

@pytest_asyncio.fixture  # Not @pytest.fixture
async def async_fixture():
    resource = await create_resource()
    yield resource
    await resource.cleanup()
```

### Sync fixtures

```python
import pytest

@pytest.fixture
def sync_fixture():
    return create_config()
```

## Discord Testing

### Mock interaction properly

```python
from unittest.mock import MagicMock, AsyncMock

mock_interaction = MagicMock()
mock_interaction.user.id = 12345  # Sync property
mock_interaction.response = MagicMock()
mock_interaction.response.is_done.return_value = False  # Sync
mock_interaction.response.send_message = AsyncMock()  # Async
```

### Real embed values

```python
# ❌ WRONG - Returns MagicMock
mock_result.embed_dict = MagicMock()

# ✅ CORRECT - Real values
mock_result.embed_dict = {
    "title": "Summary",
    "color": 0x00FF00,  # int, not MagicMock
    "fields": []
}
```

## CommandTree Errors

### "Client already has command tree"

```python
# ✅ Handle exception
try:
    self.client.tree = discord.app_commands.CommandTree(self.client)
except discord.errors.ClientException:
    logger.debug("Using existing tree")
```

## Test Assertions

### Assert on objects, not strings

```python
# ❌ WRONG
assert "Rate Limit" in str(call_args)

# ✅ CORRECT
embed = call_args.kwargs['embed']
assert "Rate Limit" in embed.title
```

## Running Tests

### Run specific test

```bash
poetry run pytest tests/path/test_file.py::TestClass::test_method -v
```

### Run with output

```bash
poetry run pytest tests/ -v --tb=short
```

### Run integration tests only

```bash
poetry run pytest tests/integration/ -v
```

### Stop on first failure

```bash
poetry run pytest tests/ -x
```

## Common Patterns

### Parametrized async tests

```python
@pytest.mark.asyncio
@pytest.mark.parametrize("value,expected", [(1, "a"), (2, "b")])
async def test_param(value, expected):
    result = await process(value)
    assert result == expected
```

### Testing exceptions

```python
@pytest.mark.asyncio
async def test_exception():
    with pytest.raises(CustomError):
        await function_that_raises()
```

### Cleanup in fixtures

```python
@pytest_asyncio.fixture
async def resource():
    r = await create()
    yield r
    await r.cleanup()  # Always runs
```

## File Organization

```
tests/
  unit/           # Fast, isolated tests
  integration/    # Tests with real components
  e2e/           # Full system tests
  fixtures/      # Shared test fixtures
  conftest.py    # Global fixtures
```

## Debug Checklist

- [ ] Test marked with `@pytest.mark.asyncio`?
- [ ] Async fixture using `@pytest_asyncio.fixture`?
- [ ] All async calls awaited?
- [ ] Mocks configured correctly (AsyncMock vs MagicMock)?
- [ ] Real values in mock returns (not MagicMock)?
- [ ] Assertions on actual values (not strings)?
- [ ] Cleanup in fixture yield?

## Quick Fixes

### Fix coroutine warning
Add `inspect.iscoroutine()` check

### Fix fixture deprecation
Change `@pytest.fixture` to `@pytest_asyncio.fixture`

### Fix CommandTree error
Add try-except around tree creation

### Fix mock type error
Return real values instead of MagicMock

### Fix assertion error
Assert on object attributes, not string repr

---

**See Also**:
- `DEBUG_FIXES_REPORT.md` - Detailed bug analysis
- `ASYNC_TESTING_GUIDE.md` - Comprehensive async testing guide
