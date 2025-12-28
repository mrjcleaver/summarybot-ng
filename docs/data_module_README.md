# Data Module Documentation

## Overview

The data module provides a comprehensive data access layer for Summary Bot NG, implementing the repository pattern with support for multiple database backends.

## Architecture

```
src/data/
├── __init__.py              # Public interface exports
├── base.py                  # Abstract repository interfaces
├── sqlite.py               # SQLite implementation
├── postgresql.py           # PostgreSQL stub (future)
├── migrations/             # Database migrations
│   ├── __init__.py         # Migration runner
│   └── 001_initial_schema.sql
└── repositories/           # Concrete repository implementations
    └── __init__.py         # Repository factory
```

## Features

- Repository pattern for clean separation of data access
- Abstract interfaces for multiple backend support
- SQLite implementation with full async support using aiosqlite
- Connection pooling for performance
- Transaction support for data consistency
- Database migration system
- Factory pattern for easy repository creation
- Comprehensive error handling

## Quick Start

### 1. Initialize Database

```python
from src.data.migrations import run_migrations

# Run all pending migrations
await run_migrations("data/summarybot.db")
```

### 2. Initialize Repositories

```python
from src.data import initialize_repositories

# Initialize with SQLite backend
initialize_repositories(
    backend="sqlite",
    db_path="data/summarybot.db",
    pool_size=5
)
```

### 3. Use Repositories

```python
from src.data import get_summary_repository, get_config_repository, get_task_repository
from src.data.base import SearchCriteria

# Summary operations
summary_repo = await get_summary_repository()
await summary_repo.save_summary(summary_result)
summary = await summary_repo.get_summary(summary_id)
summaries = await summary_repo.find_summaries(
    SearchCriteria(guild_id="123", limit=10)
)

# Configuration operations
config_repo = await get_config_repository()
await config_repo.save_guild_config(guild_config)
config = await config_repo.get_guild_config(guild_id)

# Task operations
task_repo = await get_task_repository()
await task_repo.save_task(scheduled_task)
tasks = await task_repo.get_active_tasks()
```

## Repository Interfaces

### SummaryRepository

Manages summary data storage and retrieval.

**Methods:**
- `save_summary(summary: SummaryResult) -> str`
- `get_summary(summary_id: str) -> Optional[SummaryResult]`
- `find_summaries(criteria: SearchCriteria) -> List[SummaryResult]`
- `delete_summary(summary_id: str) -> bool`
- `count_summaries(criteria: SearchCriteria) -> int`
- `get_summaries_by_channel(channel_id: str, limit: int) -> List[SummaryResult]`

### ConfigRepository

Manages guild configuration storage.

**Methods:**
- `save_guild_config(config: GuildConfig) -> None`
- `get_guild_config(guild_id: str) -> Optional[GuildConfig]`
- `delete_guild_config(guild_id: str) -> bool`
- `get_all_guild_configs() -> List[GuildConfig]`

### TaskRepository

Manages scheduled task storage and execution tracking.

**Methods:**
- `save_task(task: ScheduledTask) -> str`
- `get_task(task_id: str) -> Optional[ScheduledTask]`
- `get_tasks_by_guild(guild_id: str) -> List[ScheduledTask]`
- `get_active_tasks() -> List[ScheduledTask]`
- `delete_task(task_id: str) -> bool`
- `save_task_result(result: TaskResult) -> str`
- `get_task_results(task_id: str, limit: int) -> List[TaskResult]`

## Database Schema

### Summaries Table

Stores generated summaries with all metadata.

**Columns:**
- `id` - Unique summary identifier
- `channel_id` - Discord channel ID
- `guild_id` - Discord guild ID
- `start_time` - Summary time range start
- `end_time` - Summary time range end
- `message_count` - Number of messages summarized
- `summary_text` - Main summary content
- `key_points` - JSON array of key points
- `action_items` - JSON array of action items
- `technical_terms` - JSON array of technical terms
- `participants` - JSON array of participants
- `metadata` - JSON object for extensibility
- `created_at` - Summary creation timestamp
- `context` - JSON summarization context

**Indexes:**
- `idx_summaries_guild_id`
- `idx_summaries_channel_id`
- `idx_summaries_created_at`
- `idx_summaries_guild_channel`
- `idx_summaries_time_range`

### Guild Configs Table

Stores per-guild configuration settings.

**Columns:**
- `guild_id` - Unique guild identifier (primary key)
- `enabled_channels` - JSON array of enabled channel IDs
- `excluded_channels` - JSON array of excluded channel IDs
- `default_summary_options` - JSON summary options
- `permission_settings` - JSON permission configuration
- `webhook_enabled` - Boolean flag
- `webhook_secret` - Optional webhook secret

### Scheduled Tasks Table

Stores scheduled summary tasks.

**Columns:**
- `id` - Unique task identifier
- `name` - Task name
- `channel_id` - Target channel ID
- `guild_id` - Target guild ID
- `schedule_type` - once, daily, weekly, monthly, custom
- `schedule_time` - HH:MM format
- `schedule_days` - JSON array of weekday numbers
- `cron_expression` - For custom scheduling
- `destinations` - JSON array of delivery destinations
- `summary_options` - JSON summary options
- `is_active` - Boolean active flag
- `created_at` - Task creation timestamp
- `created_by` - User ID who created the task
- `last_run` - Last execution timestamp
- `next_run` - Next scheduled execution
- `run_count` - Total execution count
- `failure_count` - Consecutive failure count
- `max_failures` - Maximum allowed failures
- `retry_delay_minutes` - Retry delay

**Indexes:**
- `idx_scheduled_tasks_guild_id`
- `idx_scheduled_tasks_channel_id`
- `idx_scheduled_tasks_is_active`
- `idx_scheduled_tasks_next_run`
- `idx_scheduled_tasks_active_next_run`

### Task Results Table

Stores execution results for scheduled tasks.

**Columns:**
- `execution_id` - Unique execution identifier
- `task_id` - Foreign key to scheduled_tasks
- `status` - pending, running, completed, failed, cancelled
- `started_at` - Execution start timestamp
- `completed_at` - Execution completion timestamp
- `summary_id` - Generated summary ID
- `error_message` - Error message if failed
- `error_details` - JSON error details
- `delivery_results` - JSON array of delivery results
- `execution_time_seconds` - Execution duration

**Indexes:**
- `idx_task_results_task_id`
- `idx_task_results_started_at`
- `idx_task_results_status`
- `idx_task_results_summary_id`

## Connection Pooling

The SQLite implementation includes connection pooling for improved performance:

```python
# Configure pool size
initialize_repositories(
    backend="sqlite",
    db_path="data/summarybot.db",
    pool_size=10  # Number of connections in pool
)
```

Connection pool features:
- Automatic connection reuse
- Thread-safe connection management
- WAL mode for better concurrency
- Foreign key enforcement
- Automatic connection lifecycle management

## Transactions

The data module supports database transactions for atomic operations:

```python
async with connection.begin_transaction() as tx:
    await summary_repo.save_summary(summary1)
    await summary_repo.save_summary(summary2)
    # Automatically commits on success, rolls back on exception
```

## Search Criteria

Use `SearchCriteria` to filter summaries:

```python
from src.data.base import SearchCriteria
from datetime import datetime, timedelta

# Search for recent summaries in a specific channel
criteria = SearchCriteria(
    guild_id="123456789",
    channel_id="987654321",
    start_time=datetime.utcnow() - timedelta(days=7),
    end_time=datetime.utcnow(),
    limit=20,
    offset=0,
    order_by="created_at",
    order_direction="DESC"
)

results = await summary_repo.find_summaries(criteria)
```

## Migration System

The migration system manages database schema changes:

```python
from src.data.migrations import MigrationRunner

# Create migration runner
runner = MigrationRunner("data/summarybot.db")

# Run all pending migrations
await runner.run_migrations()

# Check current version
version = await runner.get_current_version()

# Reset database (WARNING: destroys all data)
await runner.reset_database()
```

### Creating New Migrations

1. Create a new SQL file in `src/data/migrations/`
2. Name it with incremental version: `002_add_new_feature.sql`
3. Write SQL statements separated by semicolons
4. Run migrations to apply changes

## Error Handling

All repository methods may raise:
- `aiosqlite.Error` - Database errors
- `json.JSONDecodeError` - JSON parsing errors
- `ValueError` - Invalid parameters
- `NotImplementedError` - PostgreSQL operations (not yet implemented)

Always wrap repository calls in try-except blocks:

```python
try:
    summary = await summary_repo.get_summary(summary_id)
except aiosqlite.Error as e:
    logger.error(f"Database error: {e}")
    # Handle error appropriately
```

## Performance Considerations

1. **Connection Pooling**: Use appropriate pool size (5-10 for most cases)
2. **Indexes**: All commonly queried fields have indexes
3. **WAL Mode**: Enabled for better concurrent read/write performance
4. **Batch Operations**: Consider batching when saving multiple records
5. **Pagination**: Use limit/offset in SearchCriteria for large result sets

## Testing

The data module includes comprehensive test coverage:

```python
# Unit tests for repositories
pytest tests/unit/test_data/

# Integration tests with real database
pytest tests/integration/test_data_integration/
```

## Future Enhancements

- PostgreSQL implementation for production deployments
- Read replicas support
- Database sharding for large-scale deployments
- Advanced query builder
- Automatic backup and restore
- Performance monitoring and optimization
- Connection pooling metrics

## Dependencies

Required packages:
- `aiosqlite>=0.19.0` - Async SQLite driver
- `asyncpg` - PostgreSQL driver (future)

## Support

For issues or questions about the data module:
1. Check this documentation
2. Review the specification in `/workspaces/summarybot-ng/specs/phase_3_modules.md`
3. Examine the test files for usage examples
4. Submit an issue on the project repository
