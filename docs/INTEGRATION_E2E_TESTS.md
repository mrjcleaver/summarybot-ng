# Integration and End-to-End Tests Documentation

## Overview

Comprehensive integration and end-to-end tests for Summary Bot NG, validating complete workflows and cross-component interactions.

## Test Structure

### Integration Tests (`/tests/integration/`)

Integration tests verify real component interactions with mocked external APIs.

#### 1. Discord Integration Tests (`test_discord_integration.py`)

**Purpose**: Test full Discord command flow from interaction to response

**Coverage**:
- Bot initialization with real service container
- Command registration and execution
- Full summarize command flow (interaction → handler → engine → response)
- Error propagation through layers
- Permission checking in command flow
- Concurrent command execution

**Key Tests**:
```python
test_bot_initialization_with_real_container()
test_command_registration_flow()
test_full_summarize_command_flow()
test_error_propagation_through_layers()
test_permission_check_integration()
test_concurrent_command_execution()
test_cost_estimation_integration()
```

**Test Approach**:
- Uses real `ServiceContainer` with mocked `ClaudeClient`
- Mocks Discord API but uses real bot components
- Tests complete message flow with actual processing logic

#### 2. Webhook Integration Tests (`test_webhook_integration.py`)

**Purpose**: Test full API request flow through webhook service

**Coverage**:
- Health check and root endpoints
- Complete API request flow (request → auth → handler → engine → response)
- Authentication and authorization
- Rate limiting enforcement
- Concurrent API request handling
- CORS and compression middleware
- Error handling and recovery

**Key Tests**:
```python
test_health_check_endpoint()
test_root_endpoint()
test_full_api_request_flow()
test_authentication_required()
test_rate_limiting_enforcement()
test_concurrent_api_requests()
test_error_handling_in_api()
test_cors_headers()
```

**Test Approach**:
- Uses `AsyncClient` for async HTTP testing
- Real FastAPI app with mocked Claude API
- Tests middleware stack integration

#### 3. Database Integration Tests (`test_database_integration.py`)

**Purpose**: Test repository operations with real database

**Coverage**:
- Create and retrieve operations
- Transaction handling and rollback
- Concurrent database access
- Query operations (by channel, by guild, etc.)
- Update and delete operations
- Schema creation and migrations

**Key Tests**:
```python
test_create_and_retrieve_summary()
test_transaction_rollback()
test_concurrent_database_access()
test_query_summaries_by_channel()
test_update_summary()
test_delete_summary()
test_migration_execution()
```

**Test Approach**:
- Uses in-memory SQLite for fast, isolated testing
- Tests real SQLAlchemy async operations
- Validates concurrent access patterns

### End-to-End Tests (`/tests/e2e/`)

E2E tests validate complete workflows across all system components.

#### 1. Summarization Workflow Tests (`test_summarization_workflow.py`)

**Purpose**: Test complete summarization workflows from trigger to response

**Test Classes**:

**`TestDiscordSummarizationWorkflow`**:
- Complete Discord user flow: `/summarize` → fetch → process → store → respond
- Error recovery scenarios
- Scheduled summary workflow

**`TestWebhookSummarizationWorkflow`**:
- Webhook-triggered summary flow
- API request → authentication → processing → storage → response

**`TestCrossComponentWorkflow`**:
- Bot and webhook service coexistence
- System-wide health checks

**Key Scenarios**:
```python
test_complete_discord_summarization_flow()
test_error_recovery_workflow()
test_scheduled_summary_workflow()
test_webhook_triggered_summary_workflow()
test_bot_and_webhook_coexistence()
test_system_health_checks()
```

#### 2. Full System Tests (`test_full_system.py`)

**Purpose**: Test complete system integration with all services running

**Coverage**:
- System startup and initialization
- Shared service access between components
- Concurrent bot and webhook operations
- Health check endpoints
- Graceful shutdown
- Error isolation
- Resource cleanup
- Performance under load
- Memory usage

**Key Tests**:
```python
test_system_startup()
test_shared_service_access()
test_concurrent_bot_and_webhook_operations()
test_system_health_check_endpoint()
test_graceful_shutdown()
test_error_isolation()
test_resource_cleanup_on_error()
test_sustained_load()
test_memory_usage()
```

## Test Patterns

### 1. Fixture Organization

**Shared Fixtures** (`conftest.py`):
- `mock_config`: Complete bot configuration
- `integration_service_container`: Real container with mocked external APIs
- `integration_bot`: Configured bot instance
- `integration_webhook_server`: Webhook server instance
- `real_test_database`: In-memory database for testing
- `e2e_full_system`: Complete system setup

**Class-Level Fixtures**:
- Test-specific setup with proper async handling
- Automatic cleanup via context managers
- Isolated test environments

### 2. Mocking Strategy

**Mock External APIs Only**:
- Discord API (network calls)
- Claude API (AI service)
- External webhooks

**Use Real Components**:
- Service container
- Summarization engine
- Command handlers
- Message processors
- Database operations (with in-memory SQLite)

### 3. Async Testing

All async tests use `pytest_asyncio`:
```python
@pytest_asyncio.fixture
async def my_fixture():
    # Setup
    yield resource
    # Cleanup

@pytest.mark.asyncio
async def test_async_operation():
    result = await some_async_function()
    assert result is not None
```

## Running Tests

### Run All Integration Tests
```bash
pytest tests/integration/ -v
```

### Run Specific Integration Test File
```bash
pytest tests/integration/test_discord_integration.py -v
```

### Run E2E Tests (excluding slow tests)
```bash
pytest tests/e2e/ -v -k "not slow"
```

### Run with Coverage
```bash
pytest tests/integration/ tests/e2e/ --cov=src --cov-report=html
```

### Run Only Integration Tests Marker
```bash
pytest -m integration -v
```

### Run Only E2E Tests Marker
```bash
pytest -m e2e -v
```

## Test Markers

- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.e2e`: End-to-end tests
- `@pytest.mark.slow`: Long-running tests
- `@pytest.mark.asyncio`: Async tests

## Best Practices

### 1. Test Independence
Each test should be completely independent:
```python
@pytest_asyncio.fixture
async def isolated_container(mock_config):
    container = ServiceContainer(mock_config)
    await container.initialize()
    yield container
    await container.cleanup()  # Always cleanup
```

### 2. Clear Test Names
Use descriptive test names that explain what and why:
```python
def test_full_summarize_command_flow():
    """Test complete summarize command flow from interaction to response."""
```

### 3. Arrange-Act-Assert
Structure tests clearly:
```python
async def test_example():
    # Arrange
    container = ServiceContainer(config)

    # Act
    result = await container.summarization_engine.summarize_messages(...)

    # Assert
    assert result.summary_text is not None
```

### 4. Test One Thing
Each test should verify one specific behavior:
```python
# Good
async def test_permission_check_integration():
    """Test permission checking in command flow."""
    # Test only permission checking

# Bad - tests multiple things
async def test_everything():
    # Tests permissions, summaries, database, etc.
```

## Performance Considerations

### Integration Tests
- Target: < 5 seconds per test
- Use in-memory databases
- Mock slow external APIs
- Limit message batch sizes

### E2E Tests
- Target: < 30 seconds per test
- Mark slow tests with `@pytest.mark.slow`
- Use appropriate timeouts
- Clean up resources properly

## Troubleshooting

### Common Issues

**1. Async Fixture Warnings**
```python
# Wrong
@pytest.fixture
async def my_fixture():
    ...

# Right
@pytest_asyncio.fixture
async def my_fixture():
    ...
```

**2. Resource Leaks**
Always cleanup in fixtures:
```python
@pytest_asyncio.fixture
async def resource():
    r = await create_resource()
    yield r
    await r.cleanup()  # Critical!
```

**3. Test Isolation**
Use fresh instances per test:
```python
@pytest_asyncio.fixture
async def fresh_container(mock_config):
    # New container each test
    container = ServiceContainer(mock_config)
    await container.initialize()
    yield container
    await container.cleanup()
```

## Coverage Goals

- **Integration Tests**: 80%+ coverage of service layer
- **E2E Tests**: Validate all critical user workflows
- **Overall**: 85%+ code coverage across test suite

## Future Enhancements

1. **Performance Benchmarks**: Add performance regression tests
2. **Load Testing**: Validate system under high concurrency
3. **Chaos Testing**: Test system resilience to failures
4. **Contract Testing**: API contract validation
5. **Visual Regression**: For any UI components

## Related Documentation

- `/tests/unit/`: Unit test documentation
- `/tests/performance/`: Performance test documentation
- `/tests/security/`: Security test documentation
- `TEST_RESULTS.md`: Comprehensive test results and analysis
