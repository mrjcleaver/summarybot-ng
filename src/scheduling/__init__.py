"""
Scheduling module for automated summary generation and task execution.

This module provides task scheduling functionality with support for:
- Cron-style and one-time task scheduling
- Task persistence and recovery
- Integration with summarization engine
- Multiple delivery destinations
- Failure recovery and retry logic
"""

from .scheduler import TaskScheduler
from .tasks import SummaryTask, CleanupTask, TaskType
from .executor import TaskExecutor, TaskExecutionResult
from .persistence import TaskPersistence

__all__ = [
    'TaskScheduler',
    'SummaryTask',
    'CleanupTask',
    'TaskType',
    'TaskExecutor',
    'TaskExecutionResult',
    'TaskPersistence',
]
