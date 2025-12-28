"""
Unit tests for task definitions.
"""

import pytest
from datetime import datetime, timedelta

from src.scheduling.tasks import SummaryTask, CleanupTask, TaskMetadata, TaskType
from src.models.task import ScheduledTask, ScheduleType, Destination, DestinationType, TaskStatus
from src.models.summary import SummaryOptions, SummaryLength


@pytest.fixture
def sample_scheduled_task():
    """Create a sample scheduled task."""
    return ScheduledTask(
        name="Test Summary",
        channel_id="123456789",
        guild_id="987654321",
        schedule_type=ScheduleType.DAILY,
        schedule_time="09:00"
    )


@pytest.fixture
def sample_summary_task(sample_scheduled_task):
    """Create a sample summary task."""
    return SummaryTask(
        scheduled_task=sample_scheduled_task,
        channel_id="123456789",
        guild_id="987654321",
        summary_options=SummaryOptions(
            summary_length=SummaryLength.DETAILED
        ),
        time_range_hours=24
    )


def test_summary_task_creation(sample_summary_task):
    """Test creating a summary task."""
    assert sample_summary_task.channel_id == "123456789"
    assert sample_summary_task.guild_id == "987654321"
    assert sample_summary_task.status == TaskStatus.PENDING
    assert sample_summary_task.time_range_hours == 24


def test_summary_task_get_time_range(sample_summary_task):
    """Test getting time range for summary task."""
    start_time, end_time = sample_summary_task.get_time_range()

    assert isinstance(start_time, datetime)
    assert isinstance(end_time, datetime)
    assert end_time > start_time

    # Should be approximately 24 hours apart
    time_diff = (end_time - start_time).total_seconds() / 3600
    assert abs(time_diff - 24.0) < 0.1


def test_summary_task_mark_started(sample_summary_task):
    """Test marking task as started."""
    sample_summary_task.mark_started()

    assert sample_summary_task.status == TaskStatus.RUNNING
    assert sample_summary_task.started_at is not None


def test_summary_task_mark_completed(sample_summary_task):
    """Test marking task as completed."""
    sample_summary_task.mark_started()
    sample_summary_task.mark_completed()

    assert sample_summary_task.status == TaskStatus.COMPLETED
    assert sample_summary_task.completed_at is not None


def test_summary_task_mark_failed(sample_summary_task):
    """Test marking task as failed."""
    sample_summary_task.mark_started()
    sample_summary_task.mark_failed("Test error")

    assert sample_summary_task.status == TaskStatus.FAILED
    assert sample_summary_task.error_message == "Test error"
    assert sample_summary_task.retry_count == 1


def test_summary_task_should_retry(sample_summary_task):
    """Test retry logic."""
    # Fresh task shouldn't retry (not failed)
    assert sample_summary_task.should_retry() is False

    # Failed task should retry if under max retries
    sample_summary_task.mark_failed("Error 1")
    assert sample_summary_task.should_retry() is True

    # Exhaust retries
    sample_summary_task.scheduled_task.max_failures = 2
    sample_summary_task.mark_failed("Error 2")
    assert sample_summary_task.should_retry() is False


def test_summary_task_get_retry_delay(sample_summary_task):
    """Test exponential backoff for retries."""
    sample_summary_task.scheduled_task.retry_delay_minutes = 5

    # First retry: 5 minutes
    delay1 = sample_summary_task.get_retry_delay()
    assert delay1 == 5 * 60

    # Second retry: 10 minutes
    sample_summary_task.retry_count = 1
    delay2 = sample_summary_task.get_retry_delay()
    assert delay2 == 10 * 60

    # Third retry: 20 minutes
    sample_summary_task.retry_count = 2
    delay3 = sample_summary_task.get_retry_delay()
    assert delay3 == 20 * 60


def test_summary_task_to_dict(sample_summary_task):
    """Test converting summary task to dictionary."""
    task_dict = sample_summary_task.to_dict()

    assert task_dict["type"] == TaskType.SUMMARY.value
    assert task_dict["channel_id"] == "123456789"
    assert task_dict["guild_id"] == "987654321"
    assert "summary_options" in task_dict
    assert "destinations" in task_dict


def test_summary_task_execution_summary(sample_summary_task):
    """Test getting execution summary."""
    # Pending
    summary = sample_summary_task.get_execution_summary()
    assert "Pending" in summary

    # Running
    sample_summary_task.mark_started()
    summary = sample_summary_task.get_execution_summary()
    assert "Running" in summary

    # Completed
    sample_summary_task.mark_completed()
    summary = sample_summary_task.get_execution_summary()
    assert "Completed" in summary


def test_cleanup_task_creation():
    """Test creating a cleanup task."""
    task = CleanupTask(
        task_id="cleanup_123",
        guild_id="987654321",
        retention_days=30,
        delete_summaries=True,
        delete_logs=True
    )

    assert task.task_id == "cleanup_123"
    assert task.retention_days == 30
    assert task.status == TaskStatus.PENDING


def test_cleanup_task_get_cutoff_date():
    """Test getting cutoff date for cleanup."""
    task = CleanupTask(
        task_id="cleanup_123",
        retention_days=90
    )

    cutoff = task.get_cutoff_date()
    expected = datetime.utcnow() - timedelta(days=90)

    # Should be within a few seconds
    diff = abs((cutoff - expected).total_seconds())
    assert diff < 5


def test_cleanup_task_mark_completed():
    """Test marking cleanup task as completed."""
    task = CleanupTask(task_id="cleanup_123")

    task.mark_started()
    task.mark_completed(items_deleted=42)

    assert task.status == TaskStatus.COMPLETED
    assert task.items_deleted == 42


def test_cleanup_task_to_dict():
    """Test converting cleanup task to dictionary."""
    task = CleanupTask(
        task_id="cleanup_123",
        guild_id="987654321",
        retention_days=60
    )

    task_dict = task.to_dict()

    assert task_dict["type"] == TaskType.CLEANUP.value
    assert task_dict["task_id"] == "cleanup_123"
    assert task_dict["retention_days"] == 60


def test_task_metadata_creation():
    """Test creating task metadata."""
    metadata = TaskMetadata(
        task_id="task_123",
        task_type=TaskType.SUMMARY,
        created_at=datetime.utcnow()
    )

    assert metadata.task_id == "task_123"
    assert metadata.execution_count == 0
    assert metadata.failure_count == 0


def test_task_metadata_update_execution():
    """Test updating execution statistics."""
    metadata = TaskMetadata(
        task_id="task_123",
        task_type=TaskType.SUMMARY,
        created_at=datetime.utcnow()
    )

    # First execution: 5 seconds
    metadata.update_execution(5.0, failed=False)
    assert metadata.execution_count == 1
    assert metadata.failure_count == 0
    assert metadata.average_duration_seconds == 5.0

    # Second execution: 10 seconds
    metadata.update_execution(10.0, failed=False)
    assert metadata.execution_count == 2
    assert metadata.average_duration_seconds == 7.5

    # Failed execution
    metadata.update_execution(3.0, failed=True)
    assert metadata.failure_count == 1


def test_task_metadata_success_rate():
    """Test calculating success rate."""
    metadata = TaskMetadata(
        task_id="task_123",
        task_type=TaskType.SUMMARY,
        created_at=datetime.utcnow()
    )

    # No executions
    assert metadata.get_success_rate() == 0.0

    # All successful
    metadata.update_execution(5.0, failed=False)
    metadata.update_execution(6.0, failed=False)
    metadata.update_execution(7.0, failed=False)
    assert metadata.get_success_rate() == 100.0

    # One failure
    metadata.update_execution(8.0, failed=True)
    assert metadata.get_success_rate() == 75.0


def test_task_metadata_to_dict():
    """Test converting metadata to dictionary."""
    metadata = TaskMetadata(
        task_id="task_123",
        task_type=TaskType.SUMMARY,
        created_at=datetime.utcnow()
    )

    metadata.update_execution(5.0, failed=False)

    meta_dict = metadata.to_dict()

    assert meta_dict["task_id"] == "task_123"
    assert meta_dict["task_type"] == TaskType.SUMMARY.value
    assert meta_dict["execution_count"] == 1
    assert "success_rate" in meta_dict
