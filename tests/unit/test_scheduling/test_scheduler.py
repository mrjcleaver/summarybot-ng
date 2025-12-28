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
