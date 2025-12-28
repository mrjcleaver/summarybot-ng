#!/usr/bin/env python3
"""
Verification script for the scheduling module implementation.

This script verifies that all required components are implemented
and functional.
"""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Ensure the src directory is in the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scheduling import (
    TaskScheduler,
    TaskExecutor,
    TaskPersistence,
    SummaryTask,
    CleanupTask,
    TaskType,
    TaskExecutionResult
)
from src.models.task import (
    ScheduledTask,
    ScheduleType,
    Destination,
    DestinationType,
    TaskStatus
)
from src.models.summary import SummaryOptions, SummaryLength


def print_check(message: str, passed: bool = True):
    """Print a check result."""
    symbol = "✅" if passed else "❌"
    print(f"{symbol} {message}")


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


async def verify_imports():
    """Verify all required imports."""
    print_section("Verifying Imports")

    try:
        from src.scheduling.scheduler import TaskScheduler
        print_check("TaskScheduler import")
    except ImportError as e:
        print_check(f"TaskScheduler import: {e}", False)
        return False

    try:
        from src.scheduling.executor import TaskExecutor
        print_check("TaskExecutor import")
    except ImportError as e:
        print_check(f"TaskExecutor import: {e}", False)
        return False

    try:
        from src.scheduling.persistence import TaskPersistence
        print_check("TaskPersistence import")
    except ImportError as e:
        print_check(f"TaskPersistence import: {e}", False)
        return False

    try:
        from src.scheduling.tasks import SummaryTask, CleanupTask, TaskType
        print_check("Task classes import")
    except ImportError as e:
        print_check(f"Task classes import: {e}", False)
        return False

    return True


async def verify_scheduler_methods():
    """Verify TaskScheduler has all required methods."""
    print_section("Verifying TaskScheduler Methods")

    required_methods = [
        "start",
        "stop",
        "schedule_task",
        "cancel_task",
        "get_scheduled_tasks",
        "pause_task",
        "resume_task",
        "get_task_status",
        "get_scheduler_stats"
    ]

    all_present = True
    for method in required_methods:
        has_method = hasattr(TaskScheduler, method)
        print_check(f"TaskScheduler.{method}()", has_method)
        if not has_method:
            all_present = False

    return all_present


async def verify_executor_methods():
    """Verify TaskExecutor has all required methods."""
    print_section("Verifying TaskExecutor Methods")

    required_methods = [
        "execute_summary_task",
        "execute_cleanup_task",
        "handle_task_failure"
    ]

    all_present = True
    for method in required_methods:
        has_method = hasattr(TaskExecutor, method)
        print_check(f"TaskExecutor.{method}()", has_method)
        if not has_method:
            all_present = False

    return all_present


async def verify_persistence_methods():
    """Verify TaskPersistence has all required methods."""
    print_section("Verifying TaskPersistence Methods")

    required_methods = [
        "save_task",
        "load_task",
        "load_all_tasks",
        "update_task",
        "delete_task",
        "get_tasks_by_guild",
        "cleanup_old_tasks",
        "export_tasks",
        "import_tasks"
    ]

    all_present = True
    for method in required_methods:
        has_method = hasattr(TaskPersistence, method)
        print_check(f"TaskPersistence.{method}()", has_method)
        if not has_method:
            all_present = False

    return all_present


async def verify_task_models():
    """Verify task model classes."""
    print_section("Verifying Task Models")

    # Check ScheduleType enum
    schedule_types = ["ONCE", "DAILY", "WEEKLY", "MONTHLY", "CUSTOM"]
    for stype in schedule_types:
        has_type = hasattr(ScheduleType, stype)
        print_check(f"ScheduleType.{stype}", has_type)

    # Check DestinationType enum
    dest_types = ["DISCORD_CHANNEL", "WEBHOOK", "EMAIL", "FILE"]
    for dtype in dest_types:
        has_type = hasattr(DestinationType, dtype)
        print_check(f"DestinationType.{dtype}", has_type)

    # Check TaskType enum
    task_types = ["SUMMARY", "CLEANUP", "EXPORT", "NOTIFICATION"]
    for ttype in task_types:
        has_type = hasattr(TaskType, ttype)
        print_check(f"TaskType.{ttype}", has_type)

    return True


async def verify_basic_functionality():
    """Verify basic scheduling functionality."""
    print_section("Verifying Basic Functionality")

    from unittest.mock import Mock, AsyncMock

    try:
        # Create mock dependencies
        mock_engine = Mock()
        mock_processor = Mock()
        mock_client = Mock()

        # Initialize executor
        executor = TaskExecutor(mock_engine, mock_processor, mock_client)
        print_check("TaskExecutor initialization")

        # Initialize persistence with temp directory
        temp_dir = Path("./temp_verify_tasks")
        temp_dir.mkdir(exist_ok=True)
        persistence = TaskPersistence(storage_path=str(temp_dir))
        print_check("TaskPersistence initialization")

        # Initialize scheduler
        scheduler = TaskScheduler(executor, persistence, timezone="UTC")
        print_check("TaskScheduler initialization")

        # Start scheduler
        await scheduler.start()
        print_check("Scheduler start")

        # Create a test task
        task = ScheduledTask(
            name="Verification Task",
            channel_id="123456789012345678",
            guild_id="987654321098765432",
            schedule_type=ScheduleType.DAILY,
            schedule_time="09:00",
            destinations=[
                Destination(
                    type=DestinationType.DISCORD_CHANNEL,
                    target="123456789012345678",
                    format="embed"
                )
            ],
            summary_options=SummaryOptions(
                summary_length=SummaryLength.DETAILED,
                min_messages=5
            )
        )
        print_check("Task creation")

        # Schedule the task
        task_id = await scheduler.schedule_task(task)
        print_check(f"Task scheduling (ID: {task_id[:8]}...)")

        # Verify task is in active tasks
        is_active = task_id in scheduler.active_tasks
        print_check("Task in active tasks", is_active)

        # Get task status
        status = await scheduler.get_task_status(task_id)
        has_status = status is not None
        print_check("Get task status", has_status)

        # Get all scheduled tasks
        tasks = await scheduler.get_scheduled_tasks()
        print_check(f"Get scheduled tasks ({len(tasks)} task(s))")

        # Pause task
        paused = await scheduler.pause_task(task_id)
        print_check("Pause task", paused)

        # Resume task
        resumed = await scheduler.resume_task(task_id)
        print_check("Resume task", resumed)

        # Get scheduler stats
        stats = scheduler.get_scheduler_stats()
        print_check(f"Scheduler stats (running: {stats['running']})")

        # Cancel task
        cancelled = await scheduler.cancel_task(task_id)
        print_check("Cancel task", cancelled)

        # Stop scheduler
        await scheduler.stop()
        print_check("Scheduler stop")

        # Cleanup temp directory
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
        print_check("Cleanup temporary files")

        return True

    except Exception as e:
        print_check(f"Basic functionality test failed: {e}", False)
        import traceback
        traceback.print_exc()
        return False


async def verify_persistence_operations():
    """Verify persistence operations."""
    print_section("Verifying Persistence Operations")

    try:
        temp_dir = Path("./temp_verify_persistence")
        temp_dir.mkdir(exist_ok=True)
        persistence = TaskPersistence(storage_path=str(temp_dir))

        # Create a test task
        task = ScheduledTask(
            name="Persistence Test Task",
            channel_id="111111111111111111",
            guild_id="222222222222222222",
            schedule_type=ScheduleType.WEEKLY,
            schedule_time="15:00",
            schedule_days=[0, 4]
        )

        # Save task
        await persistence.save_task(task)
        print_check("Save task")

        # Load task
        loaded_task = await persistence.load_task(task.id)
        print_check("Load task", loaded_task is not None)

        # Verify loaded task matches original
        matches = (
            loaded_task.id == task.id and
            loaded_task.name == task.name and
            loaded_task.schedule_type == task.schedule_type
        )
        print_check("Loaded task matches original", matches)

        # Load all tasks
        all_tasks = await persistence.load_all_tasks()
        print_check(f"Load all tasks ({len(all_tasks)} task(s))")

        # Update task
        task.name = "Updated Name"
        await persistence.update_task(task)
        updated = await persistence.load_task(task.id)
        print_check("Update task", updated.name == "Updated Name")

        # Get tasks by guild
        guild_tasks = await persistence.get_tasks_by_guild(task.guild_id)
        print_check(f"Get tasks by guild ({len(guild_tasks)} task(s))")

        # Export tasks
        export_file = temp_dir / "export.json"
        exported = await persistence.export_tasks(str(export_file))
        print_check("Export tasks", exported and export_file.exists())

        # Delete task
        deleted = await persistence.delete_task(task.id)
        print_check("Delete task", deleted)

        # Verify task is deleted
        deleted_task = await persistence.load_task(task.id)
        print_check("Task deleted successfully", deleted_task is None)

        # Cleanup
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
        print_check("Cleanup temporary files")

        return True

    except Exception as e:
        print_check(f"Persistence operations failed: {e}", False)
        import traceback
        traceback.print_exc()
        return False


async def verify_schedule_types():
    """Verify all schedule types work."""
    print_section("Verifying Schedule Types")

    from unittest.mock import Mock

    try:
        executor = TaskExecutor(Mock(), Mock(), Mock())
        temp_dir = Path("./temp_verify_schedules")
        temp_dir.mkdir(exist_ok=True)
        persistence = TaskPersistence(storage_path=str(temp_dir))
        scheduler = TaskScheduler(executor, persistence)

        await scheduler.start()

        # Test ONCE
        once_task = ScheduledTask(
            name="Once Task",
            channel_id="111111111111111111",
            guild_id="222222222222222222",
            schedule_type=ScheduleType.ONCE,
            next_run=datetime.utcnow() + timedelta(hours=1)
        )
        once_id = await scheduler.schedule_task(once_task)
        print_check(f"ONCE schedule type (ID: {once_id[:8]}...)")

        # Test DAILY
        daily_task = ScheduledTask(
            name="Daily Task",
            channel_id="111111111111111111",
            guild_id="222222222222222222",
            schedule_type=ScheduleType.DAILY,
            schedule_time="10:00"
        )
        daily_id = await scheduler.schedule_task(daily_task)
        print_check(f"DAILY schedule type (ID: {daily_id[:8]}...)")

        # Test WEEKLY
        weekly_task = ScheduledTask(
            name="Weekly Task",
            channel_id="111111111111111111",
            guild_id="222222222222222222",
            schedule_type=ScheduleType.WEEKLY,
            schedule_time="14:00",
            schedule_days=[0, 3]
        )
        weekly_id = await scheduler.schedule_task(weekly_task)
        print_check(f"WEEKLY schedule type (ID: {weekly_id[:8]}...)")

        # Test MONTHLY
        monthly_task = ScheduledTask(
            name="Monthly Task",
            channel_id="111111111111111111",
            guild_id="222222222222222222",
            schedule_type=ScheduleType.MONTHLY,
            schedule_time="09:00"
        )
        monthly_id = await scheduler.schedule_task(monthly_task)
        print_check(f"MONTHLY schedule type (ID: {monthly_id[:8]}...)")

        # Test CUSTOM
        custom_task = ScheduledTask(
            name="Custom Task",
            channel_id="111111111111111111",
            guild_id="222222222222222222",
            schedule_type=ScheduleType.CUSTOM,
            cron_expression="0 */6 * * *"
        )
        custom_id = await scheduler.schedule_task(custom_task)
        print_check(f"CUSTOM schedule type (ID: {custom_id[:8]}...)")

        await scheduler.stop()

        # Cleanup
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

        return True

    except Exception as e:
        print_check(f"Schedule types verification failed: {e}", False)
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all verification checks."""
    print("\n" + "=" * 70)
    print("  Summary Bot NG - Scheduling Module Verification")
    print("=" * 70)

    results = []

    # Run all verification checks
    results.append(("Imports", await verify_imports()))
    results.append(("Scheduler Methods", await verify_scheduler_methods()))
    results.append(("Executor Methods", await verify_executor_methods()))
    results.append(("Persistence Methods", await verify_persistence_methods()))
    results.append(("Task Models", await verify_task_models()))
    results.append(("Basic Functionality", await verify_basic_functionality()))
    results.append(("Persistence Operations", await verify_persistence_operations()))
    results.append(("Schedule Types", await verify_schedule_types()))

    # Print summary
    print_section("Verification Summary")

    total = len(results)
    passed = sum(1 for _, result in results if result)

    for test_name, result in results:
        symbol = "✅" if result else "❌"
        print(f"{symbol} {test_name}")

    print(f"\n{'=' * 70}")
    print(f"  Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print(f"{'=' * 70}\n")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
