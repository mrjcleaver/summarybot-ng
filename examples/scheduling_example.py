"""
Example usage of the scheduling module for Summary Bot NG.

This example demonstrates how to set up and use the task scheduler
for automated summary generation.
"""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path

# Import scheduling components
from src.scheduling import (
    TaskScheduler,
    TaskExecutor,
    TaskPersistence,
    SummaryTask,
    CleanupTask,
    TaskType
)

# Import models
from src.models.task import (
    ScheduledTask,
    ScheduleType,
    Destination,
    DestinationType
)
from src.models.summary import SummaryOptions, SummaryLength

# Import core components (would be initialized from main application)
# from src.summarization import SummarizationEngine
# from src.message_processing import MessageProcessor
# import discord


async def example_basic_daily_schedule():
    """Example: Schedule a daily summary at 9 AM."""
    print("\n=== Example 1: Basic Daily Schedule ===\n")

    # Note: In production, these would be initialized with real instances
    # summarization_engine = SummarizationEngine(claude_client, cache)
    # message_processor = MessageProcessor(discord_client)
    # executor = TaskExecutor(summarization_engine, message_processor, discord_client)

    # For this example, we'll use mock components
    from unittest.mock import Mock, AsyncMock

    mock_engine = Mock()
    mock_processor = Mock()
    mock_client = Mock()

    executor = TaskExecutor(mock_engine, mock_processor, mock_client)
    persistence = TaskPersistence(storage_path="./data/tasks")
    scheduler = TaskScheduler(executor, persistence, timezone="UTC")

    # Create a daily summary task
    task = ScheduledTask(
        name="Daily Channel Summary",
        channel_id="123456789012345678",
        guild_id="987654321098765432",
        schedule_type=ScheduleType.DAILY,
        schedule_time="09:00",  # 9 AM UTC
        destinations=[
            Destination(
                type=DestinationType.DISCORD_CHANNEL,
                target="123456789012345678",
                format="embed",
                enabled=True
            )
        ],
        summary_options=SummaryOptions(
            summary_length=SummaryLength.DETAILED,
            min_messages=10,
            include_bots=False,
            extract_action_items=True,
            extract_key_points=True
        )
    )

    # Start the scheduler
    await scheduler.start()
    print(f"✅ Scheduler started")

    # Schedule the task
    task_id = await scheduler.schedule_task(task)
    print(f"✅ Task scheduled with ID: {task_id}")
    print(f"   Schedule: {task.get_schedule_description()}")
    print(f"   Next run: {task.next_run}")

    # Get task status
    status = await scheduler.get_task_status(task_id)
    print(f"\n📊 Task Status:")
    print(f"   Name: {status['name']}")
    print(f"   Active: {status['is_active']}")
    print(f"   Run count: {status['run_count']}")

    # Get scheduler stats
    stats = scheduler.get_scheduler_stats()
    print(f"\n📈 Scheduler Stats:")
    print(f"   Running: {stats['running']}")
    print(f"   Active tasks: {stats['active_tasks']}")
    print(f"   Scheduled jobs: {stats['scheduled_jobs']}")

    # Cleanup
    await scheduler.stop()
    print(f"\n✅ Scheduler stopped")


async def example_weekly_summary():
    """Example: Schedule a weekly summary on Monday and Friday."""
    print("\n=== Example 2: Weekly Summary ===\n")

    from unittest.mock import Mock

    executor = TaskExecutor(Mock(), Mock(), Mock())
    persistence = TaskPersistence(storage_path="./data/tasks")
    scheduler = TaskScheduler(executor, persistence)

    await scheduler.start()

    task = ScheduledTask(
        name="Weekly Team Standup Summary",
        channel_id="111111111111111111",
        guild_id="222222222222222222",
        schedule_type=ScheduleType.WEEKLY,
        schedule_time="17:00",  # 5 PM
        schedule_days=[0, 4],  # Monday (0) and Friday (4)
        destinations=[
            Destination(
                type=DestinationType.DISCORD_CHANNEL,
                target="333333333333333333",
                format="markdown"
            )
        ],
        summary_options=SummaryOptions(
            summary_length=SummaryLength.CONCISE,
            min_messages=5
        )
    )

    task_id = await scheduler.schedule_task(task)
    print(f"✅ Weekly task scheduled: {task_id}")
    print(f"   Schedule: {task.get_schedule_description()}")

    await scheduler.stop()


async def example_custom_cron():
    """Example: Use custom cron expression for complex scheduling."""
    print("\n=== Example 3: Custom Cron Expression ===\n")

    from unittest.mock import Mock

    executor = TaskExecutor(Mock(), Mock(), Mock())
    persistence = TaskPersistence(storage_path="./data/tasks")
    scheduler = TaskScheduler(executor, persistence)

    await scheduler.start()

    # Every 6 hours at minute 0
    task = ScheduledTask(
        name="Every 6 Hours Summary",
        channel_id="444444444444444444",
        guild_id="555555555555555555",
        schedule_type=ScheduleType.CUSTOM,
        cron_expression="0 */6 * * *",
        destinations=[
            Destination(
                type=DestinationType.DISCORD_CHANNEL,
                target="444444444444444444",
                format="embed"
            )
        ]
    )

    task_id = await scheduler.schedule_task(task)
    print(f"✅ Custom cron task scheduled: {task_id}")
    print(f"   Cron: {task.cron_expression}")

    await scheduler.stop()


async def example_multiple_destinations():
    """Example: Deliver summary to multiple destinations."""
    print("\n=== Example 4: Multiple Destinations ===\n")

    from unittest.mock import Mock

    executor = TaskExecutor(Mock(), Mock(), Mock())
    persistence = TaskPersistence(storage_path="./data/tasks")
    scheduler = TaskScheduler(executor, persistence)

    await scheduler.start()

    task = ScheduledTask(
        name="Multi-Destination Summary",
        channel_id="666666666666666666",
        guild_id="777777777777777777",
        schedule_type=ScheduleType.DAILY,
        schedule_time="18:00",
        destinations=[
            # Send to main channel as embed
            Destination(
                type=DestinationType.DISCORD_CHANNEL,
                target="666666666666666666",
                format="embed",
                enabled=True
            ),
            # Also send to admin channel as markdown
            Destination(
                type=DestinationType.DISCORD_CHANNEL,
                target="888888888888888888",
                format="markdown",
                enabled=True
            ),
            # Post to webhook for external system
            Destination(
                type=DestinationType.WEBHOOK,
                target="https://example.com/summaries",
                format="json",
                enabled=True
            )
        ]
    )

    task_id = await scheduler.schedule_task(task)
    print(f"✅ Multi-destination task scheduled: {task_id}")
    print(f"   Destinations: {len(task.destinations)}")
    for i, dest in enumerate(task.destinations, 1):
        print(f"   {i}. {dest.to_display_string()}")

    await scheduler.stop()


async def example_task_management():
    """Example: Manage scheduled tasks (pause, resume, cancel)."""
    print("\n=== Example 5: Task Management ===\n")

    from unittest.mock import Mock

    executor = TaskExecutor(Mock(), Mock(), Mock())
    persistence = TaskPersistence(storage_path="./data/tasks")
    scheduler = TaskScheduler(executor, persistence)

    await scheduler.start()

    # Schedule a task
    task = ScheduledTask(
        name="Managed Task",
        channel_id="999999999999999999",
        guild_id="000000000000000000",
        schedule_type=ScheduleType.DAILY,
        schedule_time="12:00"
    )

    task_id = await scheduler.schedule_task(task)
    print(f"✅ Task created: {task_id}")

    # Pause the task
    await scheduler.pause_task(task_id)
    print(f"⏸  Task paused")

    # Resume the task
    await scheduler.resume_task(task_id)
    print(f"▶️  Task resumed")

    # Get all scheduled tasks
    all_tasks = await scheduler.get_scheduled_tasks()
    print(f"\n📋 Total scheduled tasks: {len(all_tasks)}")

    # Get tasks for specific guild
    guild_tasks = await scheduler.get_scheduled_tasks(guild_id="000000000000000000")
    print(f"   Tasks for guild: {len(guild_tasks)}")

    # Cancel the task
    await scheduler.cancel_task(task_id)
    print(f"\n🗑  Task cancelled and removed")

    await scheduler.stop()


async def example_one_time_task():
    """Example: Schedule a one-time summary."""
    print("\n=== Example 6: One-Time Task ===\n")

    from unittest.mock import Mock

    executor = TaskExecutor(Mock(), Mock(), Mock())
    persistence = TaskPersistence(storage_path="./data/tasks")
    scheduler = TaskScheduler(executor, persistence)

    await scheduler.start()

    # Schedule a summary to run once in 1 hour
    task = ScheduledTask(
        name="One-Time Event Summary",
        channel_id="111222333444555666",
        guild_id="777888999000111222",
        schedule_type=ScheduleType.ONCE,
        next_run=datetime.utcnow() + timedelta(hours=1),
        destinations=[
            Destination(
                type=DestinationType.DISCORD_CHANNEL,
                target="111222333444555666",
                format="embed"
            )
        ]
    )

    task_id = await scheduler.schedule_task(task)
    print(f"✅ One-time task scheduled: {task_id}")
    print(f"   Will run at: {task.next_run}")

    await scheduler.stop()


async def example_task_persistence():
    """Example: Demonstrate task persistence across restarts."""
    print("\n=== Example 7: Task Persistence ===\n")

    from unittest.mock import Mock

    executor = TaskExecutor(Mock(), Mock(), Mock())
    persistence = TaskPersistence(storage_path="./data/tasks")

    # First scheduler instance
    print("📝 Creating first scheduler instance...")
    scheduler1 = TaskScheduler(executor, persistence)
    await scheduler1.start()

    task = ScheduledTask(
        name="Persistent Task",
        channel_id="123123123123123123",
        guild_id="456456456456456456",
        schedule_type=ScheduleType.DAILY,
        schedule_time="15:00"
    )

    task_id = await scheduler1.schedule_task(task)
    print(f"✅ Task scheduled: {task_id}")

    await scheduler1.stop()
    print(f"🛑 First scheduler stopped")

    # Second scheduler instance (simulates restart)
    print(f"\n🔄 Creating second scheduler instance (simulating restart)...")
    scheduler2 = TaskScheduler(executor, persistence)
    await scheduler2.start()

    # Tasks should be loaded automatically
    loaded_tasks = await scheduler2.get_scheduled_tasks()
    print(f"✅ Loaded {len(loaded_tasks)} tasks from persistence")

    for task in loaded_tasks:
        print(f"   - {task.name} ({task.id})")

    await scheduler2.stop()


async def example_export_import():
    """Example: Export and import tasks."""
    print("\n=== Example 8: Export/Import Tasks ===\n")

    persistence = TaskPersistence(storage_path="./data/tasks")

    # Create some tasks
    tasks = [
        ScheduledTask(
            name=f"Task {i}",
            channel_id=f"{i}" * 18,
            guild_id="111111111111111111",
            schedule_type=ScheduleType.DAILY
        )
        for i in range(1, 4)
    ]

    # Save tasks
    for task in tasks:
        await persistence.save_task(task)

    print(f"✅ Created {len(tasks)} tasks")

    # Export tasks
    export_file = "./data/tasks_backup.json"
    success = await persistence.export_tasks(export_file)
    print(f"📦 Tasks exported to {export_file}: {success}")

    # Import tasks (would restore from backup)
    # count = await persistence.import_tasks(export_file)
    # print(f"📥 Imported {count} tasks")

    # Cleanup old tasks
    cleaned = await persistence.cleanup_old_tasks(days=90)
    print(f"🧹 Cleaned up {cleaned} old tasks")


async def example_cleanup_task():
    """Example: Schedule a cleanup task."""
    print("\n=== Example 9: Cleanup Task ===\n")

    from unittest.mock import Mock

    executor = TaskExecutor(Mock(), Mock(), Mock())
    persistence = TaskPersistence(storage_path="./data/tasks")
    scheduler = TaskScheduler(executor, persistence)

    await scheduler.start()

    # Schedule monthly cleanup
    cleanup_task = ScheduledTask(
        name="Monthly Data Cleanup",
        channel_id="",  # Not needed for cleanup tasks
        guild_id="",    # Empty = all guilds
        schedule_type=ScheduleType.MONTHLY,
        schedule_time="02:00"  # 2 AM on the 1st of each month
    )

    # Configure cleanup parameters in metadata
    cleanup_task.metadata = {
        "task_type": "cleanup",
        "retention_days": 90,
        "delete_summaries": True,
        "delete_logs": True,
        "delete_cached_data": True
    }

    task_id = await scheduler.schedule_task(cleanup_task)
    print(f"✅ Cleanup task scheduled: {task_id}")
    print(f"   Will clean data older than 90 days")
    print(f"   Schedule: Monthly on day {cleanup_task.created_at.day} at 02:00")

    await scheduler.stop()


async def example_scheduler_monitoring():
    """Example: Monitor scheduler health and statistics."""
    print("\n=== Example 10: Scheduler Monitoring ===\n")

    from unittest.mock import Mock

    executor = TaskExecutor(Mock(), Mock(), Mock())
    persistence = TaskPersistence(storage_path="./data/tasks")
    scheduler = TaskScheduler(executor, persistence)

    await scheduler.start()

    # Schedule some tasks
    for i in range(3):
        task = ScheduledTask(
            name=f"Task {i+1}",
            channel_id=f"{i+1}" * 18,
            guild_id="999999999999999999",
            schedule_type=ScheduleType.DAILY,
            schedule_time=f"{9+i}:00"
        )
        await scheduler.schedule_task(task)

    print(f"✅ Created 3 monitoring tasks\n")

    # Get scheduler statistics
    stats = scheduler.get_scheduler_stats()
    print(f"📊 Scheduler Statistics:")
    print(f"   Status: {'Running' if stats['running'] else 'Stopped'}")
    print(f"   Startup complete: {stats['startup_complete']}")
    print(f"   Active tasks: {stats['active_tasks']}")
    print(f"   Scheduled jobs: {stats['scheduled_jobs']}")
    print(f"   Timezone: {stats['timezone']}")

    print(f"\n⏰ Next Run Times:")
    for job_info in stats['next_run_times']:
        print(f"   - {job_info['task_name']}: {job_info['next_run']}")

    # Get individual task status
    print(f"\n📋 Individual Task Status:")
    all_tasks = await scheduler.get_scheduled_tasks()
    for task in all_tasks:
        status = await scheduler.get_task_status(task.id)
        print(f"\n   Task: {status['name']}")
        print(f"   ID: {status['id']}")
        print(f"   Schedule: {status['schedule']}")
        print(f"   Active: {status['is_active']}")
        print(f"   Run count: {status['run_count']}")
        print(f"   Failure count: {status['failure_count']}")
        print(f"   Next run: {status.get('next_run_time', 'N/A')}")

    await scheduler.stop()


async def main():
    """Run all examples."""
    print("=" * 70)
    print("Summary Bot NG - Scheduling Module Examples")
    print("=" * 70)

    examples = [
        example_basic_daily_schedule,
        example_weekly_summary,
        example_custom_cron,
        example_multiple_destinations,
        example_task_management,
        example_one_time_task,
        example_task_persistence,
        example_export_import,
        example_cleanup_task,
        example_scheduler_monitoring
    ]

    for example in examples:
        try:
            await example()
            await asyncio.sleep(0.5)  # Small delay between examples
        except Exception as e:
            print(f"\n❌ Error in {example.__name__}: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 70)
    print("All examples completed!")
    print("=" * 70)


if __name__ == "__main__":
    # Ensure data directory exists
    Path("./data/tasks").mkdir(parents=True, exist_ok=True)

    # Run examples
    asyncio.run(main())
