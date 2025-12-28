# Scheduling Module

Automated task scheduling for Summary Bot NG with support for recurring summaries, cleanup tasks, and custom schedules.

## Structure

- `__init__.py` - Module exports
- `scheduler.py` - Main TaskScheduler class using APScheduler
- `tasks.py` - Task definition classes (SummaryTask, CleanupTask)
- `executor.py` - Task execution logic with delivery handling
- `persistence.py` - Task state persistence (file/database)

## Key Features

- ✅ Multiple schedule types (daily, weekly, monthly, cron, one-time)
- ✅ Task persistence for restart recovery
- ✅ Automatic retry with exponential backoff
- ✅ Multiple delivery destinations (Discord, webhooks, etc.)
- ✅ Comprehensive execution metrics
- ✅ Timezone support

## Quick Start

```python
from src.scheduling import TaskScheduler, TaskExecutor, TaskPersistence

# Initialize
persistence = TaskPersistence("./data/tasks")
executor = TaskExecutor(engine, processor, client)
scheduler = TaskScheduler(executor, persistence)

# Start scheduler
await scheduler.start()

# Schedule a task
task_id = await scheduler.schedule_task(task)
```

See `/docs/SCHEDULING.md` for full documentation and `/docs/examples/scheduling_example.py` for usage examples.

## Dependencies

- `apscheduler` - Task scheduling engine
- `asyncio` - Async execution
- Core modules: `models`, `exceptions`, `summarization`, `message_processing`

## Testing

Run tests:
```bash
pytest tests/unit/test_scheduling/ -v
```

## Module Statistics

- Total lines: ~1,550
- Files: 5 Python modules
- Test coverage target: >90%
