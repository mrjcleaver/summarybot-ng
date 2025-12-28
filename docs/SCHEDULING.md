# Scheduling Module Documentation

## Overview

The scheduling module provides automated task execution capabilities for Summary Bot NG, including scheduled summary generation, cleanup tasks, and custom scheduled operations.

## Features

- **Flexible Scheduling**: Support for cron-style schedules, intervals, and one-time tasks
- **Task Persistence**: Tasks survive bot restarts through file or database persistence
- **Failure Recovery**: Automatic retry with exponential backoff
- **Multiple Destinations**: Deliver summaries to Discord channels, webhooks, emails, or files
- **Execution Tracking**: Comprehensive metrics and status tracking
- **Timezone Support**: Configurable timezone for all scheduled tasks

## Architecture

### Components

1. **TaskScheduler** (`scheduler.py`)
   - Main orchestrator using APScheduler
   - Manages task lifecycle and execution
   - Handles persistence and recovery

2. **TaskExecutor** (`executor.py`)
   - Executes scheduled tasks
   - Manages delivery to multiple destinations
   - Handles failure notifications

3. **Task Definitions** (`tasks.py`)
   - SummaryTask: Automated summary generation
   - CleanupTask: Periodic data cleanup
   - TaskMetadata: Execution statistics

4. **TaskPersistence** (`persistence.py`)
   - File-based or database persistence
   - Task import/export functionality
   - Automatic cleanup of old tasks

## Usage

### Basic Setup

```python
from src.scheduling import TaskScheduler, TaskExecutor, TaskPersistence
from src.models.task import ScheduledTask, ScheduleType

# Initialize components
persistence = TaskPersistence(storage_path="./data/tasks")
executor = TaskExecutor(
    summarization_engine=engine,
    message_processor=processor,
    discord_client=client
)

scheduler = TaskScheduler(
    task_executor=executor,
    persistence=persistence,
    timezone="UTC"
)

# Start scheduler
await scheduler.start()
```

### Scheduling a Daily Summary

```python
from src.models.task import ScheduledTask, Destination, DestinationType
from src.models.summary import SummaryOptions, SummaryLength

# Create scheduled task
task = ScheduledTask(
    name="Daily Dev Channel Summary",
    channel_id="123456789",
    guild_id="987654321",
    schedule_type=ScheduleType.DAILY,
    schedule_time="09:00",  # 9 AM UTC
    destinations=[
        Destination(
            type=DestinationType.DISCORD_CHANNEL,
            target="123456789",
            format="embed",
            enabled=True
        )
    ],
    summary_options=SummaryOptions(
        summary_length=SummaryLength.DETAILED,
        min_messages=10,
        include_bots=False
    )
)

# Schedule the task
task_id = await scheduler.schedule_task(task)
print(f"Scheduled task: {task_id}")
```

### Weekly Summary with Multiple Destinations

```python
task = ScheduledTask(
    name="Weekly Team Update",
    channel_id="123456789",
    guild_id="987654321",
    schedule_type=ScheduleType.WEEKLY,
    schedule_time="17:00",  # 5 PM
    schedule_days=[4],  # Friday (0=Monday)
    destinations=[
        Destination(
            type=DestinationType.DISCORD_CHANNEL,
            target="123456789",
            format="embed"
        ),
        Destination(
            type=DestinationType.WEBHOOK,
            target="https://hooks.slack.com/services/...",
            format="json"
        )
    ],
    summary_options=SummaryOptions(
        summary_length=SummaryLength.COMPREHENSIVE,
        extract_action_items=True,
        extract_technical_terms=True
    )
)

await scheduler.schedule_task(task)
```

### Custom Cron Schedule

```python
task = ScheduledTask(
    name="Every 6 Hours Summary",
    channel_id="123456789",
    guild_id="987654321",
    schedule_type=ScheduleType.CUSTOM,
    cron_expression="0 */6 * * *",  # Every 6 hours
    destinations=[...]
)

await scheduler.schedule_task(task)
```

### Managing Tasks

```python
# Get all scheduled tasks
all_tasks = await scheduler.get_scheduled_tasks()

# Get tasks for specific guild
guild_tasks = await scheduler.get_scheduled_tasks(guild_id="987654321")

# Get task status
status = await scheduler.get_task_status(task_id)
print(f"Next run: {status['next_run_time']}")
print(f"Success rate: {status['metadata']['success_rate']}%")

# Pause/resume task
await scheduler.pause_task(task_id)
await scheduler.resume_task(task_id)

# Cancel task
await scheduler.cancel_task(task_id)
```

### Scheduler Statistics

```python
stats = scheduler.get_scheduler_stats()
print(f"Running: {stats['running']}")
print(f"Active tasks: {stats['active_tasks']}")
print(f"Next runs: {stats['next_run_times']}")
```

## Schedule Types

### DAILY
Runs every day at a specified time.

```python
ScheduledTask(
    schedule_type=ScheduleType.DAILY,
    schedule_time="14:30"  # 2:30 PM
)
```

### WEEKLY
Runs on specific days of the week.

```python
ScheduledTask(
    schedule_type=ScheduleType.WEEKLY,
    schedule_time="10:00",
    schedule_days=[0, 2, 4]  # Monday, Wednesday, Friday
)
```

### MONTHLY
Runs on a specific day of each month.

```python
ScheduledTask(
    schedule_type=ScheduleType.MONTHLY,
    schedule_time="09:00",
    created_at=datetime(2024, 1, 15)  # Runs on 15th of each month
)
```

### CUSTOM
Uses a cron expression for maximum flexibility.

```python
ScheduledTask(
    schedule_type=ScheduleType.CUSTOM,
    cron_expression="0 0 */2 * *"  # Every 2 days at midnight
)
```

### ONCE
Runs one time at a specific datetime.

```python
ScheduledTask(
    schedule_type=ScheduleType.ONCE,
    next_run=datetime(2024, 12, 31, 23, 59)
)
```

## Delivery Destinations

### Discord Channel

```python
Destination(
    type=DestinationType.DISCORD_CHANNEL,
    target="channel_id",
    format="embed"  # or "markdown"
)
```

### Webhook

```python
Destination(
    type=DestinationType.WEBHOOK,
    target="https://webhook.url",
    format="json"
)
```

### Email (Future)

```python
Destination(
    type=DestinationType.EMAIL,
    target="team@example.com",
    format="html"
)
```

### File (Future)

```python
Destination(
    type=DestinationType.FILE,
    target="/path/to/summaries/",
    format="markdown"
)
```

## Error Handling and Retry

The scheduler includes automatic retry logic with exponential backoff:

```python
task = ScheduledTask(
    # ... other fields ...
    max_failures=3,  # Disable after 3 failures
    retry_delay_minutes=5  # Base retry delay
)
```

Retry delays use exponential backoff:
- 1st retry: 5 minutes
- 2nd retry: 10 minutes
- 3rd retry: 20 minutes

After max failures, the task is automatically disabled.

## Persistence

### File-based Persistence (Default)

```python
persistence = TaskPersistence(storage_path="./data/tasks")
```

Tasks are stored as JSON files in the specified directory.

### Database Persistence (Future)

```python
from src.scheduling.persistence import DatabaseTaskPersistence

persistence = DatabaseTaskPersistence(
    database_url="postgresql://user:pass@localhost/summarybot"
)
```

### Task Import/Export

```python
# Export all tasks
await persistence.export_tasks("backup.json")

# Import tasks
count = await persistence.import_tasks("backup.json")
print(f"Imported {count} tasks")
```

## Cleanup Tasks

Automatic cleanup of old data:

```python
from src.scheduling.tasks import CleanupTask

cleanup = CleanupTask(
    task_id="cleanup_old_summaries",
    guild_id="987654321",  # or None for all guilds
    retention_days=90,
    delete_summaries=True,
    delete_logs=True,
    delete_cached_data=True
)

result = await executor.execute_cleanup_task(cleanup)
print(f"Deleted {result.items_deleted} items")
```

## Monitoring

### Task Metadata

Each task maintains execution statistics:

```python
metadata = scheduler.task_metadata[task_id]
print(f"Executions: {metadata.execution_count}")
print(f"Failures: {metadata.failure_count}")
print(f"Success rate: {metadata.get_success_rate()}%")
print(f"Avg duration: {metadata.average_duration_seconds}s")
```

### Execution Results

```python
result = await executor.execute_summary_task(task)
print(f"Success: {result.success}")
print(f"Summary ID: {result.summary_result.id}")
print(f"Duration: {result.execution_time_seconds}s")
print(f"Deliveries: {len(result.delivery_results)}")
```

## Integration Example

Complete integration with Discord bot:

```python
from discord.ext import commands
from src.scheduling import TaskScheduler, TaskExecutor, TaskPersistence

class SchedulingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # Initialize scheduling components
        self.persistence = TaskPersistence("./data/tasks")
        self.executor = TaskExecutor(
            summarization_engine=bot.summarization_engine,
            message_processor=bot.message_processor,
            discord_client=bot
        )
        self.scheduler = TaskScheduler(
            task_executor=self.executor,
            persistence=self.persistence
        )

    async def cog_load(self):
        """Start scheduler when cog loads."""
        await self.scheduler.start()

    async def cog_unload(self):
        """Stop scheduler when cog unloads."""
        await self.scheduler.stop()

    @commands.slash_command(name="schedule_summary")
    async def schedule_summary(
        self,
        ctx,
        schedule_type: str,
        time: str
    ):
        """Schedule a recurring summary."""
        task = ScheduledTask(
            name=f"Summary for #{ctx.channel.name}",
            channel_id=str(ctx.channel.id),
            guild_id=str(ctx.guild.id),
            schedule_type=ScheduleType(schedule_type),
            schedule_time=time,
            destinations=[
                Destination(
                    type=DestinationType.DISCORD_CHANNEL,
                    target=str(ctx.channel.id),
                    format="embed"
                )
            ]
        )

        task_id = await self.scheduler.schedule_task(task)
        await ctx.respond(f"✅ Scheduled task: {task_id}")

async def setup(bot):
    await bot.add_cog(SchedulingCog(bot))
```

## Best Practices

1. **Use meaningful task names** for easier management and debugging
2. **Set appropriate min_messages** to avoid empty summaries
3. **Configure retry settings** based on task criticality
4. **Enable multiple destinations** for important summaries
5. **Monitor task metadata** to identify problematic schedules
6. **Regular backups** using export functionality
7. **Cleanup old tasks** periodically to maintain performance

## Troubleshooting

### Task Not Executing

Check:
- Scheduler is running: `scheduler._running`
- Task is active: `task.is_active`
- Next run time: `scheduler.get_task_status(task_id)`
- Timezone configuration

### Task Keeps Failing

Check:
- Error messages in logs
- Channel permissions
- Message availability
- API quota limits

### Tasks Lost After Restart

Verify:
- Persistence is configured
- Storage path is writable
- Tasks were saved before shutdown

## API Reference

See inline documentation in source files:
- `/src/scheduling/scheduler.py`
- `/src/scheduling/executor.py`
- `/src/scheduling/tasks.py`
- `/src/scheduling/persistence.py`
