# Integration Test Specification and Analysis

**Project:** Summary Bot NG
**Document Type:** SPARC Specification Phase
**Date:** 2025-12-31
**Status:** Analysis Complete - Ready for Architecture Phase

---

## Executive Summary

**Current State:** 3 PASSED / 14 FAILED / 23 ERROR = 40 Total Integration Tests

**Root Causes Identified:**
1. **Database Architecture Mismatch:** Tests expect SQLAlchemy ORM, codebase uses dataclass-based repositories
2. **Test Fixture Configuration:** Async fixture decorator mismatches causing coroutine errors
3. **Missing Implementation:** Repository classes referenced in tests don't exist yet
4. **Fixture Setup Issues:** real_webhook_server fixture has initialization problems

**Target:** 40/40 PASSING tests with minimal architectural disruption

---

## Test Categorization and Analysis

### Category 1: Database Integration Tests (8 tests)
**Status:** 1 PASSED / 7 ERROR

#### Passing Tests (1):
- `test_migration_execution` - Empty placeholder test (passes by doing nothing)

#### Error Tests (7):
All fail with: `ImportError: cannot import name 'Base' from 'src.models.base'`

| Test | Purpose | Expected Behavior | Actual Behavior |
|------|---------|-------------------|-----------------|
| `test_create_and_retrieve_summary` | Test CRUD operations | Create/retrieve summary via SQLAlchemy ORM | ImportError: No SQLAlchemy Base |
| `test_transaction_rollback` | Test transaction management | Rollback on error | ImportError: No SQLAlchemy Base |
| `test_concurrent_database_access` | Test concurrent operations | Handle multiple sessions | ImportError: No SQLAlchemy Base |
| `test_query_summaries_by_channel` | Test query operations | Filter summaries by channel | ImportError: No SQLAlchemy Base |
| `test_update_summary` | Test update operations | Update existing summary | ImportError: No SQLAlchemy Base |
| `test_delete_summary` | Test delete operations | Delete summary by ID | ImportError: No SQLAlchemy Base |
| `test_schema_creation` | Test schema creation | Create tables via Base.metadata | ImportError: No SQLAlchemy Base |

**Root Cause:**
- Tests import `from src.models.base import Base` (line 32 in test_database_integration.py)
- Actual codebase has `BaseModel` dataclass, not SQLAlchemy `Base`
- Tests expect ORM repository with `Base.metadata.create_all`
- Actual codebase has abstract repositories: `SQLiteSummaryRepository`, `PostgreSQLSummaryRepository`

**Current Architecture:**
```python
# What exists in src/models/base.py
@dataclass
class BaseModel:
    def to_dict(self) -> Dict[str, Any]
    def to_json(self) -> str

# What tests expect
class Base(DeclarativeBase):
    metadata: MetaData
```

**Repository Pattern:**
```python
# What exists in src/data/
class SummaryRepository(ABC):          # Abstract base
class SQLiteSummaryRepository(SummaryRepository):   # Concrete implementation
class PostgreSQLSummaryRepository(SummaryRepository)  # Future implementation

# What tests expect
class SummaryRepository:
    def __init__(self, database_url: str)
    session: AsyncSession
    async def create(summary: SummaryResult) -> SummaryResult
```

---

### Category 2: Discord Bot Integration Tests (18 tests)
**Status:** 2 PASSED / 12 FAILED / 4 ERROR

#### Passing Tests (2):
- `test_bot_initialization_with_real_container` - Bot initializes with real ServiceContainer
- `test_command_registration_flow` - Commands register successfully

#### Failed Tests (12):
All fail with: `AttributeError: <coroutine object TestDiscordBotIntegration.discord_bot at 0x...> does not have the attribute 'wait_until_ready'`

**Root Cause:**
- Fixtures `bot_config` and `discord_bot` use `@pytest.fixture` instead of `@pytest_asyncio.fixture`
- Tests are async (`@pytest.mark.asyncio`) but fixtures aren't
- Pytest tries to use unawaited coroutines as objects

**Location:** `tests/integration/test_discord_integration/test_bot_integration.py`

```python
# Current (WRONG):
@pytest.fixture
async def bot_config(self):
    ...

@pytest.fixture
async def discord_bot(self, bot_config, mock_services):
    ...

# Should be:
@pytest_asyncio.fixture
async def bot_config(self):
    ...

@pytest_asyncio.fixture
async def discord_bot(self, bot_config, mock_services):
    ...
```

**Affected Tests:**
1. `test_bot_startup_success`
2. `test_bot_command_registration`
3. `test_summarize_command_execution`
4. `test_command_permission_denied`
5. `test_guild_join_event`
6. `test_application_command_error_handling`
7. `test_message_fetching_integration`
8. `test_bot_shutdown_graceful`
9. `test_command_sync_per_guild`
10. `test_bot_ready_event`
11. `test_summarize_command_full_flow` (also ERROR)
12. `test_quick_summary_command` (ERROR)

#### Error Tests (4):
Additional errors in `TestCommandHandlerIntegration`:

| Test | Primary Error | Secondary Issue |
|------|--------------|-----------------|
| `test_summarize_command_full_flow` | Missing `mock_interaction` fixture | Fixture not defined in class |
| `test_quick_summary_command` | Missing `mock_summarization_engine` | Fixture not defined in class |
| `test_scheduled_summary_command` | Missing `mock_interaction` | Fixture not defined in class |
| `test_error_handling_in_command` | Missing `mock_interaction`, `mock_summarization_engine` | Fixtures not defined in class |

**Pattern Identified:**
- `test_discord_integration.py` tests (PASS) use fixtures from `conftest.py`
- `test_discord_integration/test_bot_integration.py` tests (FAIL) define their own class-level fixtures
- Class-level async fixtures not properly decorated

---

### Category 3: Webhook Integration Tests (14 tests)
**Status:** 0 PASSED / 4 FAILED / 10 ERROR

#### Error Tests (9):
All fail with: `AttributeError: 'async_generator' object has no attribute 'app'`

**Root Cause:**
```python
# Current implementation (WRONG):
@pytest_asyncio.fixture
async def real_webhook_server(self, mock_config):
    ...
    yield server  # This creates an async generator
    ...

@pytest.fixture
def test_client(self, real_webhook_server):
    return TestClient(real_webhook_server.app)  # Tries to access .app on generator
```

**The Issue:**
- `real_webhook_server` is an async fixture (yields async)
- `test_client` is a sync fixture trying to use the async fixture
- Async generators don't have `.app` attribute

**Affected Tests:**
1. `test_health_check_endpoint` (ERROR)
2. `test_root_endpoint` (ERROR)
3. `test_full_api_request_flow` (ERROR)
4. `test_authentication_required` (ERROR)
5. `test_rate_limiting_enforcement` (ERROR)
6. `test_concurrent_api_requests` (ERROR)
7. `test_error_handling_in_api` (ERROR)
8. `test_cors_headers` (ERROR)
9. `test_gzip_compression` (ERROR)

#### Failed Tests (4):
Additional fixture errors + NotImplementedError in tests:
10. `test_full_api_request_flow` (FAILED + ERROR)
11. `test_error_propagation_through_layers` (FAILED + ERROR)
12. `test_permission_check_integration` (FAILED + ERROR)
13. `test_concurrent_command_execution` (FAILED + ERROR)

#### Placeholder Tests (2):
- `test_summary_persistence` - Empty placeholder (ERROR from fixture)
- `test_summary_retrieval` - Expects 404/501 unimplemented (ERROR from fixture)

---

## Architecture Analysis

### What Works (3 Passing Tests)

1. **test_migration_execution** (Database)
   - Passes because it's empty placeholder
   - No actual implementation to fail

2. **test_bot_initialization_with_real_container** (Discord)
   - Uses properly decorated `@pytest_asyncio.fixture`
   - Uses `real_service_container` from `conftest.py`
   - Tests actual `ServiceContainer` + `SummaryBot` integration

3. **test_command_registration_flow** (Discord)
   - Same proper fixture usage
   - Tests real command registration logic

**Success Pattern:**
- Use fixtures from `conftest.py` (properly decorated)
- Use real implementations (ServiceContainer, SummaryBot)
- Mock only external APIs (Claude, Discord)

---

## Current vs Expected Architecture

### Database Layer

#### Current Implementation:
```
src/models/
├── base.py              → @dataclass BaseModel
├── summary.py           → @dataclass SummaryResult(BaseModel)
├── task.py              → @dataclass ScheduledTask(BaseModel)
└── message.py           → @dataclass ProcessedMessage(BaseModel)

src/data/
├── base.py              → ABC SummaryRepository, ConfigRepository, TaskRepository
├── sqlite.py            → SQLiteSummaryRepository(SummaryRepository)
├── postgresql.py        → PostgreSQLSummaryRepository (stub)
└── repositories/
    └── __init__.py      → RepositoryFactory
```

**Pattern:** Repository pattern with abstract base classes, dataclass models

#### Test Expectations:
```
src/models/
└── base.py              → SQLAlchemy DeclarativeBase

from src.data.repositories.summary_repository import SummaryRepository
repo = SummaryRepository(database_url="...")
repo.session = test_db_session
await repo.create(summary_data)
```

**Pattern:** SQLAlchemy ORM with Base.metadata, direct session injection

### Discord Bot Layer

#### Current Implementation:
```python
class SummaryBot:
    def __init__(self, config: BotConfig, services: Optional[dict] = None)

# From container.py
class ServiceContainer:
    @property
    def summarization_engine(self) -> SummarizationEngine
```

**Pattern:** Dependency injection via ServiceContainer

#### Test Expectations:
```python
# Works in test_discord_integration.py
bot = SummaryBot(config=mock_config, services={'container': real_service_container})

# Fails in test_bot_integration.py
@pytest.fixture  # Should be @pytest_asyncio.fixture
async def discord_bot(self, bot_config, mock_services):
    ...
```

**Pattern:** Class-level fixtures not properly decorated

### Webhook Layer

#### Current Implementation:
```python
class WebhookServer:
    def __init__(self, config: BotConfig, summarization_engine: SummarizationEngine)
    app: FastAPI
```

#### Test Expectations:
```python
@pytest_asyncio.fixture
async def real_webhook_server(self, mock_config):
    yield server  # Creates async generator

@pytest.fixture  # WRONG: Should be @pytest_asyncio.fixture or use differently
def test_client(self, real_webhook_server):
    return TestClient(real_webhook_server.app)  # Can't access .app on generator
```

**Pattern:** Mixing async/sync fixtures incorrectly

---

## Root Cause Summary

| Issue | Tests Affected | Severity | Type |
|-------|---------------|----------|------|
| **No SQLAlchemy Base** | 7 database tests | HIGH | Architecture Mismatch |
| **Wrong fixture decorators** | 12 Discord bot tests | MEDIUM | Test Configuration |
| **Missing class fixtures** | 4 Discord handler tests | MEDIUM | Test Configuration |
| **Async/sync fixture mix** | 9 webhook tests | MEDIUM | Test Configuration |
| **Empty placeholders** | 1 database test (passes) | LOW | Incomplete Implementation |
| **Fixture dependency chain** | 4 webhook tests | MEDIUM | Test Configuration |

---

## Requirements for Fixes

### Requirement 1: Database Architecture Decision

**Option A: Migrate to SQLAlchemy ORM** (Tests Correct)
- Create SQLAlchemy Base declarative models
- Implement ORM-based repositories
- Add alembic migrations
- **Pros:** Tests already written, standard pattern
- **Cons:** Major refactor, changes entire data layer

**Option B: Update Tests for Current Architecture** (Code Correct)
- Remove SQLAlchemy Base imports
- Use RepositoryFactory pattern
- Test dataclass models + abstract repositories
- **Pros:** No code changes, tests match reality
- **Cons:** Rewrite 7 test files

**Recommendation:** **Option B** - Update tests to match existing architecture
- Current dataclass + repository pattern is valid
- Less disruptive to existing working code
- RepositoryFactory already implemented

### Requirement 2: Fixture Decorator Fixes

**Required Changes:**
```python
# tests/integration/test_discord_integration/test_bot_integration.py
@pytest_asyncio.fixture  # Add asyncio
async def bot_config(self):
    ...

@pytest_asyncio.fixture  # Add asyncio
async def discord_bot(self, bot_config, mock_services):
    ...

# OR move to conftest.py to share with all tests
```

**Impact:** Fixes 12 FAILED tests

### Requirement 3: Missing Fixture Definitions

**Required Changes:**
Add to `TestCommandHandlerIntegration` class or conftest.py:
```python
@pytest.fixture
def mock_interaction(self):
    # Define mock Discord interaction
    ...

@pytest.fixture
def mock_summarization_engine(self):
    # Already in conftest.py, just use it
    ...
```

**Impact:** Fixes 4 ERROR tests

### Requirement 4: Webhook Fixture Pattern

**Required Changes:**
```python
# Option A: Make test_client async
@pytest_asyncio.fixture
async def test_client(self, real_webhook_server):
    async with AsyncClient(app=real_webhook_server.app, base_url="http://test") as client:
        yield client

# Option B: Remove async from real_webhook_server
@pytest.fixture
def real_webhook_server(self, mock_config):
    # Synchronous setup
    server = WebhookServer(...)
    return server
```

**Impact:** Fixes 9 ERROR tests

---

## Success Criteria

### Phase 1: Fix Test Configuration (Expected: 37/40 passing)
- [ ] Fix all `@pytest.fixture` → `@pytest_asyncio.fixture` decorators
- [ ] Add missing fixture definitions
- [ ] Fix webhook async/sync fixture mixing
- [ ] Result: All fixture errors resolved

### Phase 2: Update Database Tests (Expected: 40/40 passing)
- [ ] Remove SQLAlchemy Base imports from tests
- [ ] Update tests to use RepositoryFactory
- [ ] Test dataclass models directly
- [ ] Add proper database initialization in fixtures
- [ ] Result: All tests passing

### Phase 3: Verify Integration (40/40 passing)
- [ ] All database CRUD operations work
- [ ] All Discord bot flows work
- [ ] All webhook API flows work
- [ ] No test warnings
- [ ] Clean test output

---

## Minimal Change Approach (Recommended)

### Step 1: Fixture Fixes (30 minutes)
1. Update `test_bot_integration.py` fixture decorators (2 fixtures)
2. Add missing fixtures to `TestCommandHandlerIntegration` (2 fixtures)
3. Fix `test_webhook_integration.py` async/sync pattern (2 fixtures)

**Expected Result:** ~25-30 tests passing

### Step 2: Database Test Updates (2 hours)
1. Create `test_database_integration_updated.py` with:
   - RepositoryFactory usage
   - Dataclass model testing
   - No SQLAlchemy Base dependency
2. Update fixtures in conftest.py:
   - `test_db_engine` → Use RepositoryFactory
   - `test_db_session` → Use concrete repository

**Expected Result:** 40/40 tests passing

### Step 3: Cleanup (30 minutes)
1. Remove old `test_database_integration.py`
2. Rename updated file
3. Verify all tests still pass
4. Update documentation

---

## Architecturally Sound Approach (Alternative)

If we later want SQLAlchemy ORM (for Alembic migrations, etc.):

### Step 1: Create Dual Model System
```python
# Keep dataclasses for business logic
@dataclass
class SummaryResult(BaseModel):
    ...

# Add ORM models for persistence
class SummaryORM(Base):
    __tablename__ = "summaries"
    id = Column(String, primary_key=True)
    ...

    def to_dataclass(self) -> SummaryResult:
        return SummaryResult(...)
```

### Step 2: Update Repositories
```python
class SQLAlchemySummaryRepository(SummaryRepository):
    async def create(self, summary: SummaryResult) -> SummaryResult:
        orm_obj = SummaryORM.from_dataclass(summary)
        self.session.add(orm_obj)
        await self.session.commit()
        return orm_obj.to_dataclass()
```

**Pros:**
- Tests already written
- Supports migrations
- Clean separation

**Cons:**
- More complexity
- Dual model maintenance
- Not needed yet

---

## Implementation Priority

1. **HIGH:** Fix fixture decorators (quick wins, 16 tests)
2. **HIGH:** Fix webhook async/sync (quick win, 9 tests)
3. **MEDIUM:** Update database tests (preserves architecture, 7 tests)
4. **LOW:** Add missing fixture definitions (4 tests)
5. **LATER:** Consider SQLAlchemy migration (if needed)

---

## Appendix: Test Inventory

### Database Tests (8 total)
```
✓ test_migration_execution                    PASSED (placeholder)
✗ test_create_and_retrieve_summary            ERROR (no Base)
✗ test_transaction_rollback                   ERROR (no Base)
✗ test_concurrent_database_access             ERROR (no Base)
✗ test_query_summaries_by_channel             ERROR (no Base)
✗ test_update_summary                         ERROR (no Base)
✗ test_delete_summary                         ERROR (no Base)
✗ test_schema_creation                        ERROR (no Base)
```

### Discord Bot Tests (18 total)
```
✓ test_bot_initialization_with_real_container PASSED (correct fixtures)
✓ test_command_registration_flow              PASSED (correct fixtures)
✗ test_bot_startup_success                    FAILED (wrong decorator)
✗ test_bot_command_registration               FAILED (wrong decorator)
✗ test_summarize_command_execution            FAILED (wrong decorator)
✗ test_command_permission_denied              FAILED (wrong decorator)
✗ test_guild_join_event                       FAILED (wrong decorator)
✗ test_application_command_error_handling     FAILED (wrong decorator)
✗ test_message_fetching_integration           FAILED (wrong decorator)
✗ test_bot_shutdown_graceful                  FAILED (wrong decorator)
✗ test_command_sync_per_guild                 FAILED (wrong decorator)
✗ test_bot_ready_event                        FAILED (wrong decorator)
✗ test_summarize_command_full_flow            ERROR (missing fixture)
✗ test_quick_summary_command                  ERROR (missing fixture)
✗ test_scheduled_summary_command              ERROR (missing fixture)
✗ test_error_handling_in_command              ERROR (missing fixture)
✗ test_full_summarize_command_flow            FAILED+ERROR (both issues)
✗ test_error_propagation_through_layers       FAILED+ERROR (both issues)
✗ test_permission_check_integration           FAILED+ERROR (both issues)
✗ test_concurrent_command_execution           FAILED+ERROR (both issues)
```

### Webhook Tests (14 total)
```
✗ test_health_check_endpoint                  ERROR (async/sync mix)
✗ test_root_endpoint                          ERROR (async/sync mix)
✗ test_full_api_request_flow                  ERROR (async/sync mix)
✗ test_authentication_required                ERROR (async/sync mix)
✗ test_rate_limiting_enforcement              ERROR (async/sync mix)
✗ test_concurrent_api_requests                ERROR (async/sync mix)
✗ test_error_handling_in_api                  ERROR (async/sync mix)
✗ test_cors_headers                           ERROR (async/sync mix)
✗ test_gzip_compression                       ERROR (async/sync mix)
✗ test_summary_persistence                    ERROR (placeholder + fixture)
✗ test_summary_retrieval                      ERROR (fixture)
✗ test_cost_estimation_integration            ERROR (missing fixture)
```

---

## Next Steps (Architecture Phase)

1. **Review this specification** with stakeholders
2. **Decide on database approach** (Option A vs B)
3. **Create architecture document** for test fixes
4. **Plan implementation** in phases
5. **Execute TDD fixes** via Refinement phase
6. **Target:** 40/40 passing tests

---

**Document Status:** Complete and ready for Architecture Phase
**Recommended Approach:** Minimal change (update tests to match code)
**Estimated Effort:** 3-4 hours total implementation time
