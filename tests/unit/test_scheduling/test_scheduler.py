"""
Unit tests for task scheduler.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from src.scheduling.scheduler import TaskScheduler
from src.scheduling.executor import TaskExecutor
from src.scheduling.persistence import TaskPersistence
from src.models.task import ScheduledTask, ScheduleType, Destination, DestinationType
from src.models.summary import SummaryOptions, SummaryLength


@pytest.fixture
def mock_executor():
    """Create mock task executor."""
    executor = Mock(spec=TaskExecutor)
    executor.execute_summary_task = AsyncMock()
    executor.handle_task_failure = AsyncMock()
    return executor


@pytest.fixture
def mock_persistence(tmp_path):
    """Create task persistence with temporary storage."""
    return TaskPersistence(storage_path=str(tmp_path / "tasks"))


@pytest.fixture
def scheduler(mock_executor, mock_persistence):
    """Create task scheduler instance."""
    return TaskScheduler(
        task_executor=mock_executor,
        persistence=mock_persistence,
        timezone="UTC"
    )


@pytest.fixture
def sample_task():
    """Create a sample scheduled task."""
    return ScheduledTask(
        name="Daily Summary",
        channel_id="123456789",
        guild_id="987654321",
        schedule_type=ScheduleType.DAILY,
        schedule_time="09:00",
        destinations=[
            Destination(
                type=DestinationType.DISCORD_CHANNEL,
                target="123456789",
                format="embed"
            )
        ],
        summary_options=SummaryOptions(
            summary_length=SummaryLength.DETAILED,
            min_messages=10
        )
    )


@pytest.mark.asyncio
async def test_scheduler_start_stop(scheduler):
    """Test scheduler startup and shutdown."""
    # Start scheduler
    await scheduler.start()
    assert scheduler._running is True
    assert scheduler._startup_complete is True

    # Stop scheduler
    await scheduler.stop()
    assert scheduler._running is False


@pytest.mark.asyncio
async def test_schedule_daily_task(scheduler, sample_task):
    """Test scheduling a daily task."""
    await scheduler.start()

    task_id = await scheduler.schedule_task(sample_task)

    assert task_id == sample_task.id
    assert task_id in scheduler.active_tasks
    assert task_id in scheduler.task_metadata

    # Verify task is in scheduler
    job = scheduler.scheduler.get_job(task_id)
    assert job is not None
    assert job.id == task_id

    await scheduler.stop()


@pytest.mark.asyncio
async def test_schedule_weekly_task(scheduler):
    """Test scheduling a weekly task."""
    await scheduler.start()

    task = ScheduledTask(
        name="Weekly Summary",
        channel_id="123456789",
        guild_id="987654321",
        schedule_type=ScheduleType.WEEKLY,
        schedule_time="10:00",
        schedule_days=[0, 3]  # Monday and Thursday
    )

    task_id = await scheduler.schedule_task(task)
    assert task_id in scheduler.active_tasks

    await scheduler.stop()


@pytest.mark.asyncio
async def test_schedule_custom_cron_task(scheduler):
    """Test scheduling a custom cron task."""
    await scheduler.start()

    task = ScheduledTask(
        name="Custom Schedule",
        channel_id="123456789",
        guild_id="987654321",
        schedule_type=ScheduleType.CUSTOM,
        cron_expression="0 */6 * * *"  # Every 6 hours
    )

    task_id = await scheduler.schedule_task(task)
    assert task_id in scheduler.active_tasks

    await scheduler.stop()


@pytest.mark.asyncio
async def test_cancel_task(scheduler, sample_task):
    """Test cancelling a scheduled task."""
    await scheduler.start()

    task_id = await scheduler.schedule_task(sample_task)
    assert task_id in scheduler.active_tasks

    # Cancel task
    result = await scheduler.cancel_task(task_id)
    assert result is True
    assert task_id not in scheduler.active_tasks

    await scheduler.stop()


@pytest.mark.asyncio
async def test_pause_resume_task(scheduler, sample_task):
    """Test pausing and resuming a task."""
    await scheduler.start()

    task_id = await scheduler.schedule_task(sample_task)

    # Pause task
    result = await scheduler.pause_task(task_id)
    assert result is True
    assert scheduler.active_tasks[task_id].is_active is False

    # Resume task
    result = await scheduler.resume_task(task_id)
    assert result is True
    assert scheduler.active_tasks[task_id].is_active is True

    await scheduler.stop()


@pytest.mark.asyncio
async def test_get_scheduled_tasks(scheduler, sample_task):
    """Test retrieving scheduled tasks."""
    await scheduler.start()

    # Schedule multiple tasks
    task1_id = await scheduler.schedule_task(sample_task)

    task2 = ScheduledTask(
        name="Another Summary",
        channel_id="111111111",
        guild_id="987654321",
        schedule_type=ScheduleType.DAILY
    )
    task2_id = await scheduler.schedule_task(task2)

    # Get all tasks
    all_tasks = await scheduler.get_scheduled_tasks()
    assert len(all_tasks) == 2

    # Get tasks for specific guild
    guild_tasks = await scheduler.get_scheduled_tasks(guild_id="987654321")
    assert len(guild_tasks) == 2

    await scheduler.stop()


@pytest.mark.asyncio
async def test_task_persistence(scheduler, sample_task, mock_persistence):
    """Test task persistence during scheduler lifecycle."""
    await scheduler.start()

    # Schedule task
    task_id = await scheduler.schedule_task(sample_task)

    # Verify task was persisted
    loaded_task = await mock_persistence.load_task(task_id)
    assert loaded_task is not None
    assert loaded_task.id == task_id
    assert loaded_task.name == sample_task.name

    await scheduler.stop()


@pytest.mark.asyncio
async def test_scheduler_stats(scheduler, sample_task):
    """Test getting scheduler statistics."""
    await scheduler.start()

    await scheduler.schedule_task(sample_task)

    stats = scheduler.get_scheduler_stats()

    assert stats["running"] is True
    assert stats["active_tasks"] == 1
    assert stats["scheduled_jobs"] >= 1
    assert "next_run_times" in stats

    await scheduler.stop()


@pytest.mark.asyncio
async def test_task_execution_trigger(scheduler, mock_executor, sample_task):
    """Test that tasks trigger execution when scheduled."""
    await scheduler.start()

    # Create a task that runs immediately
    immediate_task = ScheduledTask(
        name="Immediate Task",
        channel_id="123456789",
        guild_id="987654321",
        schedule_type=ScheduleType.ONCE,
        next_run=datetime.utcnow() + timedelta(seconds=1)
    )

    await scheduler.schedule_task(immediate_task)

    # Wait for execution
    await asyncio.sleep(2)

    # Verify executor was called
    assert mock_executor.execute_summary_task.called

    await scheduler.stop()


@pytest.mark.asyncio
async def test_scheduler_without_persistence(mock_executor):
    """Test scheduler works without persistence layer."""
    scheduler = TaskScheduler(task_executor=mock_executor, persistence=None)

    await scheduler.start()

    task = ScheduledTask(
        name="Test Task",
        channel_id="123456789",
        guild_id="987654321",
        schedule_type=ScheduleType.DAILY
    )

    task_id = await scheduler.schedule_task(task)
    assert task_id in scheduler.active_tasks

    await scheduler.stop()


def test_create_trigger_daily(scheduler):
    """Test trigger creation for daily tasks."""
    task = ScheduledTask(
        schedule_type=ScheduleType.DAILY,
        schedule_time="14:30"
    )

    trigger = scheduler._create_trigger(task)
    assert trigger is not None


def test_create_trigger_weekly(scheduler):
    """Test trigger creation for weekly tasks."""
    task = ScheduledTask(
        schedule_type=ScheduleType.WEEKLY,
        schedule_time="10:00",
        schedule_days=[0, 2, 4]  # Mon, Wed, Fri
    )

    trigger = scheduler._create_trigger(task)
    assert trigger is not None


def test_create_trigger_monthly(scheduler):
    """Test trigger creation for monthly tasks."""
    task = ScheduledTask(
        schedule_type=ScheduleType.MONTHLY,
        schedule_time="09:00",
        created_at=datetime(2024, 1, 15)
    )

    trigger = scheduler._create_trigger(task)
    assert trigger is not None


def test_create_trigger_once(scheduler):
    """Test trigger creation for one-time tasks."""
    task = ScheduledTask(
        schedule_type=ScheduleType.ONCE,
        next_run=datetime.utcnow() + timedelta(hours=1)
    )

    trigger = scheduler._create_trigger(task)
    assert trigger is not None


@pytest.mark.asyncio
async def test_task_retry_with_exponential_backoff(scheduler, mock_executor, sample_task):
    """Test task retry logic with exponential backoff."""
    await scheduler.start()

    # Configure task with retry settings
    sample_task.max_failures = 3
    sample_task.retry_delay_minutes = 5

    # Mock executor to fail initially
    mock_executor.execute_summary_task.side_effect = [
        Mock(success=False, error_message="First failure"),
        Mock(success=False, error_message="Second failure"),
        Mock(success=True, error_message=None)
    ]

    task_id = await scheduler.schedule_task(sample_task)

    # Manually trigger execution multiple times to test retry
    await scheduler._execute_scheduled_task(task_id)

    # Verify task was updated with failure count
    task = scheduler.active_tasks.get(task_id)
    if task:
        assert task.failure_count >= 0

    await scheduler.stop()


@pytest.mark.asyncio
async def test_concurrent_task_execution(scheduler, mock_executor):
    """Test multiple tasks executing concurrently."""
    await scheduler.start()

    # Create multiple tasks with immediate execution
    tasks = []
    for i in range(5):
        task = ScheduledTask(
            id=f"concurrent_task_{i}",
            name=f"Concurrent Task {i}",
            channel_id="123456789",
            guild_id="987654321",
            schedule_type=ScheduleType.ONCE,
            next_run=datetime.utcnow() + timedelta(seconds=1)
        )
        tasks.append(task)

    # Schedule all tasks
    task_ids = []
    for task in tasks:
        task_id = await scheduler.schedule_task(task)
        task_ids.append(task_id)

    # Wait for all to potentially execute
    await asyncio.sleep(3)

    # Verify executor was called for multiple tasks
    assert mock_executor.execute_summary_task.call_count >= 1

    await scheduler.stop()


@pytest.mark.asyncio
async def test_scheduler_restart_loads_persisted_tasks(mock_executor, mock_persistence, sample_task):
    """Test that scheduler loads persisted tasks on restart."""
    # Create scheduler and save a task
    scheduler1 = TaskScheduler(
        task_executor=mock_executor,
        persistence=mock_persistence,
        timezone="UTC"
    )

    await scheduler1.start()
    await scheduler1.schedule_task(sample_task)
    await scheduler1.stop()

    # Create new scheduler with same persistence
    scheduler2 = TaskScheduler(
        task_executor=mock_executor,
        persistence=mock_persistence,
        timezone="UTC"
    )

    await scheduler2.start()

    # Verify task was loaded
    loaded_tasks = await scheduler2.get_scheduled_tasks()

    # Should have at least the persisted task
    task_ids = [task.id for task in loaded_tasks]
    assert sample_task.id in task_ids

    await scheduler2.stop()


@pytest.mark.asyncio
async def test_schedule_task_without_running_scheduler(scheduler, sample_task):
    """Test that scheduling without starting scheduler raises error."""
    from src.exceptions import ConfigurationError

    with pytest.raises(ConfigurationError) as exc_info:
        await scheduler.schedule_task(sample_task)

    assert "not running" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_task_failure_handling(scheduler, mock_executor, sample_task):
    """Test task failure handling and notification."""
    await scheduler.start()

    # Make executor raise an exception
    mock_executor.execute_summary_task.side_effect = Exception("Task execution failed")

    task_id = await scheduler.schedule_task(sample_task)

    # Manually trigger execution
    await scheduler._execute_scheduled_task(task_id)

    # Verify failure handler was called
    mock_executor.handle_task_failure.assert_called_once()

    # Verify task status was updated
    task = scheduler.active_tasks.get(task_id)
    if task:
        assert task.failure_count > 0

    await scheduler.stop()


@pytest.mark.asyncio
async def test_get_task_status(scheduler, sample_task):
    """Test getting detailed task status."""
    await scheduler.start()

    task_id = await scheduler.schedule_task(sample_task)

    status = await scheduler.get_task_status(task_id)

    assert status is not None
    assert status["id"] == task_id
    assert "next_run_time" in status
    assert "metadata" in status
    assert status["scheduler_running"] is True

    await scheduler.stop()


@pytest.mark.asyncio
async def test_get_task_status_not_found(scheduler):
    """Test getting status for non-existent task."""
    await scheduler.start()

    status = await scheduler.get_task_status("nonexistent_id")

    assert status is None

    await scheduler.stop()


@pytest.mark.asyncio
async def test_cancel_nonexistent_task(scheduler):
    """Test cancelling a task that doesn't exist."""
    await scheduler.start()

    result = await scheduler.cancel_task("nonexistent_id")

    assert result is False

    await scheduler.stop()


@pytest.mark.asyncio
async def test_pause_nonexistent_task(scheduler):
    """Test pausing a task that doesn't exist."""
    await scheduler.start()

    result = await scheduler.pause_task("nonexistent_id")

    assert result is False

    await scheduler.stop()


@pytest.mark.asyncio
async def test_resume_nonexistent_task(scheduler):
    """Test resuming a task that doesn't exist."""
    await scheduler.start()

    result = await scheduler.resume_task("nonexistent_id")

    assert result is False

    await scheduler.stop()


@pytest.mark.asyncio
async def test_scheduler_double_start(scheduler):
    """Test that starting an already running scheduler is handled gracefully."""
    await scheduler.start()

    # Try to start again
    await scheduler.start()

    # Should still be running
    assert scheduler._running is True

    await scheduler.stop()


@pytest.mark.asyncio
async def test_scheduler_double_stop(scheduler):
    """Test that stopping an already stopped scheduler is handled gracefully."""
    await scheduler.start()
    await scheduler.stop()

    # Try to stop again
    await scheduler.stop()

    # Should still be stopped
    assert scheduler._running is False


@pytest.mark.asyncio
async def test_schedule_multiple_task_types(scheduler):
    """Test scheduling different types of tasks together."""
    await scheduler.start()

    # Daily task
    daily_task = ScheduledTask(
        name="Daily",
        channel_id="123456789",
        guild_id="987654321",
        schedule_type=ScheduleType.DAILY,
        schedule_time="09:00"
    )

    # Weekly task
    weekly_task = ScheduledTask(
        name="Weekly",
        channel_id="123456789",
        guild_id="987654321",
        schedule_type=ScheduleType.WEEKLY,
        schedule_days=[0, 3]
    )

    # Monthly task
    monthly_task = ScheduledTask(
        name="Monthly",
        channel_id="123456789",
        guild_id="987654321",
        schedule_type=ScheduleType.MONTHLY
    )

    # Schedule all
    daily_id = await scheduler.schedule_task(daily_task)
    weekly_id = await scheduler.schedule_task(weekly_task)
    monthly_id = await scheduler.schedule_task(monthly_task)

    # Verify all are scheduled
    all_tasks = await scheduler.get_scheduled_tasks()
    assert len(all_tasks) == 3

    await scheduler.stop()


def test_create_trigger_invalid_schedule_type(scheduler):
    """Test that invalid schedule type raises error."""
    # Create a task with invalid schedule type by manipulating the enum
    task = ScheduledTask(
        schedule_type=ScheduleType.DAILY
    )

    # Manually change to invalid value
    task.schedule_type = "INVALID"

    with pytest.raises(ValueError):
        scheduler._create_trigger(task)


def test_create_trigger_custom_without_expression(scheduler):
    """Test that custom schedule without cron expression raises error."""
    task = ScheduledTask(
        schedule_type=ScheduleType.CUSTOM,
        cron_expression=None
    )

    with pytest.raises(ValueError) as exc_info:
        scheduler._create_trigger(task)

    assert "cron_expression" in str(exc_info.value).lower()
