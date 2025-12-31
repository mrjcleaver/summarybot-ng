# Integration Test Fix Recommendations

**Quick Reference Guide for Fixing 40 Integration Tests**

---

## Current Status

```
3 PASSED / 14 FAILED / 23 ERROR = 40 Total Tests
```

**Goal:** 40/40 PASSING

---

## The Big Picture

### Three Main Issues

1. **Database Architecture Mismatch** (7 tests)
   - Tests expect SQLAlchemy ORM
   - Code uses dataclass + repository pattern
   - **Fix:** Update tests to match code (recommended)

2. **Fixture Decorator Problems** (16 tests)
   - Async fixtures missing `@pytest_asyncio.fixture`
   - **Fix:** Add 3 characters to 6 fixture definitions

3. **Async/Sync Mixing** (9 tests)
   - Webhook tests mix async generators with sync clients
   - **Fix:** Make all webhook fixtures properly async

---

## Quick Fix Guide

### Fix 1: Discord Bot Fixture Decorators (Fixes 12 tests)

**File:** `tests/integration/test_discord_integration/test_bot_integration.py`

**Change:**
```python
# BEFORE (lines 26-27, 54-55)
@pytest.fixture
async def bot_config(self):

@pytest.fixture
async def discord_bot(self, bot_config, mock_services):

# AFTER
@pytest_asyncio.fixture
async def bot_config(self):

@pytest_asyncio.fixture
async def discord_bot(self, bot_config, mock_services):
```

**Tests Fixed:**
- test_bot_startup_success
- test_bot_command_registration
- test_summarize_command_execution
- test_command_permission_denied
- test_guild_join_event
- test_application_command_error_handling
- test_message_fetching_integration
- test_bot_shutdown_graceful
- test_command_sync_per_guild
- test_bot_ready_event
- Plus 2 more in combined errors

**Estimated Time:** 2 minutes

---

### Fix 2: Add Missing Fixtures (Fixes 4 tests)

**File:** `tests/integration/test_discord_integration/test_bot_integration.py`

**Add after line 295:**
```python
@pytest.fixture
def mock_interaction(self, mock_channel, mock_guild):
    """Mock Discord interaction - reuse from conftest pattern."""
    user = MagicMock(spec=discord.User)
    user.id = 111111111
    user.name = "testuser"
    user.display_name = "Test User"

    interaction = AsyncMock(spec=discord.Interaction)
    interaction.guild = mock_guild
    interaction.channel = mock_channel
    interaction.user = user
    interaction.response = AsyncMock()
    interaction.followup = AsyncMock()
    return interaction
```

**Tests Fixed:**
- test_summarize_command_full_flow
- test_quick_summary_command
- test_scheduled_summary_command
- test_error_handling_in_command

**Estimated Time:** 5 minutes

---

### Fix 3: Webhook Async/Sync Fixtures (Fixes 9 tests)

**File:** `tests/integration/test_webhook_integration.py`

**Option A - Make test_client async (RECOMMENDED):**

```python
# BEFORE (line 61-64)
@pytest.fixture
def test_client(self, real_webhook_server):
    """Create TestClient for synchronous testing."""
    return TestClient(real_webhook_server.app)

# AFTER - Remove this fixture entirely and update all tests to use AsyncClient directly
# Tests already use AsyncClient in most cases, just remove TestClient usage
```

**Better approach - Update test methods:**

```python
# In test_health_check_endpoint and test_root_endpoint, replace:
response = test_client.get("/health")

# With:
async with AsyncClient(app=real_webhook_server.app, base_url="http://test") as client:
    response = await client.get("/health")
```

**Tests Fixed:**
- test_health_check_endpoint
- test_root_endpoint
- test_full_api_request_flow
- test_authentication_required
- test_rate_limiting_enforcement
- test_concurrent_api_requests
- test_error_handling_in_api
- test_cors_headers
- test_gzip_compression

**Estimated Time:** 15 minutes

---

### Fix 4: Database Tests (Fixes 7 tests)

**File:** `tests/integration/test_database_integration.py`

**Strategy:** Replace SQLAlchemy expectations with RepositoryFactory pattern

#### Step 1: Update Fixtures

```python
# BEFORE (lines 23-38)
@pytest_asyncio.fixture
async def test_database_engine(self):
    """Create test database engine."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False
    )
    from src.models.base import Base  # <-- THIS FAILS
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

# AFTER
@pytest_asyncio.fixture
async def test_database_factory(self):
    """Create test repository factory."""
    from src.data.repositories import RepositoryFactory

    factory = RepositoryFactory(
        backend="sqlite",
        db_path=":memory:",
        pool_size=5
    )

    # Initialize connection
    await factory.get_connection()

    yield factory

    await factory.close()

@pytest_asyncio.fixture
async def test_summary_repo(self, test_database_factory):
    """Get summary repository for testing."""
    return await test_database_factory.get_summary_repository()
```

#### Step 2: Update Test Methods

```python
# BEFORE (test_create_and_retrieve_summary)
async def test_create_and_retrieve_summary(self, test_db_session):
    from src.data.repositories.summary_repository import SummaryRepository

    repo = SummaryRepository(database_url="sqlite+aiosqlite:///:memory:")
    repo.session = test_db_session  # <-- This pattern doesn't exist

    saved_summary = await repo.create(summary_data)
    retrieved = await repo.get_by_id(saved_summary.id)

# AFTER
async def test_create_and_retrieve_summary(self, test_summary_repo):
    # Create summary using dataclass
    summary_data = SummaryResult(
        channel_id="123456",
        guild_id="789012",
        start_time=datetime.utcnow() - timedelta(hours=1),
        end_time=datetime.utcnow(),
        message_count=50,
        summary_text="Test summary for database integration",
        key_points=["Point 1", "Point 2", "Point 3"],
        action_items=["Action 1"],
        participants=["user1", "user2"],
        metadata={"test": True}
    )

    # Save using repository
    saved_summary = await test_summary_repo.save(summary_data)

    assert saved_summary.id is not None
    assert saved_summary.channel_id == "123456"

    # Retrieve using repository
    retrieved = await test_summary_repo.get_by_id(saved_summary.id)

    assert retrieved is not None
    assert retrieved.id == saved_summary.id
    assert retrieved.summary_text == summary_data.summary_text
```

**Apply same pattern to all 7 database tests:**
1. Remove SQLAlchemy imports
2. Use `test_summary_repo` fixture
3. Call repository methods directly
4. Test with dataclass models

**Estimated Time:** 1-2 hours

---

## Implementation Order

### Phase 1: Quick Wins (20 minutes)
1. Fix Discord bot fixture decorators → 12 tests passing
2. Add missing Discord fixtures → 4 tests passing
3. Fix webhook async/sync → 9 tests passing

**Result:** 28/40 tests passing (from 3/40)

### Phase 2: Database Rewrite (2 hours)
4. Update database test fixtures
5. Rewrite 7 database test methods

**Result:** 35/40 tests passing

### Phase 3: Edge Cases (30 minutes)
6. Fix any remaining combined FAILED+ERROR tests
7. Remove placeholder tests or implement

**Result:** 40/40 tests passing

---

## Testing Your Changes

After each fix, run:

```bash
# Test specific category
poetry run pytest tests/integration/test_discord_integration/ -v
poetry run pytest tests/integration/test_webhook_integration.py -v
poetry run pytest tests/integration/test_database_integration.py -v

# Test everything
poetry run pytest tests/integration/ -v

# Count results
poetry run pytest tests/integration/ -v | grep -E "passed|failed|error"
```

---

## Alternative: Use Existing Working Patterns

The **easiest fix** is to follow the pattern of the 3 PASSING tests:

### Working Pattern (from test_discord_integration.py):

```python
@pytest_asyncio.fixture
async def real_service_container(self, mock_config):
    """Create real service container with mocked external dependencies."""
    container = ServiceContainer(mock_config)

    with patch('src.summarization.claude_client.ClaudeClient') as mock_claude:
        mock_instance = AsyncMock()
        # ... setup mocks ...
        await container.initialize()
        yield container
        await container.cleanup()

@pytest.mark.asyncio
async def test_bot_initialization_with_real_container(
    self,
    mock_config,
    real_service_container
):
    bot = SummaryBot(
        config=mock_config,
        services={'container': real_service_container}
    )

    assert bot.config == mock_config
    # ... assertions ...
```

**Key Success Factors:**
1. Use `@pytest_asyncio.fixture` for async fixtures
2. Use fixtures from `conftest.py` when possible
3. Use real implementations with mocked external APIs
4. Proper async/await in tests

---

## Common Mistakes to Avoid

1. **Don't use `@pytest.fixture` for async fixtures**
   - Always use `@pytest_asyncio.fixture`

2. **Don't mix async generators with sync code**
   - If fixture yields async, consumer must be async

3. **Don't expect SQLAlchemy when code uses dataclasses**
   - Read the actual source code first

4. **Don't create duplicate fixtures**
   - Use `conftest.py` fixtures when available

5. **Don't forget to await async fixtures**
   - Pytest handles this if decorators are correct

---

## Expected Final State

```
40 PASSED / 0 FAILED / 0 ERROR = 40 Total Tests

tests/integration/test_database_integration.py ............... 8 passed
tests/integration/test_discord_integration.py ................. 5 passed
tests/integration/test_discord_integration/test_bot_integration.py ... 13 passed
tests/integration/test_webhook_integration.py ................ 14 passed
```

---

## Need Help?

### If tests still fail after fixes:

1. **Check fixture decorators:**
   ```bash
   grep -n "@pytest.fixture" tests/integration/*.py
   # Should only return sync fixtures
   ```

2. **Check imports:**
   ```bash
   grep -n "from src.models.base import Base" tests/integration/*.py
   # Should return nothing
   ```

3. **Run single test with full traceback:**
   ```bash
   poetry run pytest tests/integration/test_database_integration.py::TestDatabaseRepositoryIntegration::test_create_and_retrieve_summary -vv
   ```

4. **Check pytest-asyncio mode:**
   ```bash
   grep "asyncio_mode" pytest.ini
   # Should be "auto" or "strict"
   ```

---

## Summary

**Total Fix Time:** ~3-4 hours
**Difficulty:** Easy to Medium
**Risk:** Low (only test changes)
**Benefit:** 37 additional passing tests

**Start with Phase 1 quick wins** (20 minutes) to see immediate progress!
