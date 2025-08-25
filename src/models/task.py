"""
Task and scheduling models.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from enum import Enum

from .base import BaseModel, generate_id
from .summary import SummaryOptions


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SCHEDULED = "scheduled"


class ScheduleType(Enum):
    """Types of scheduling."""
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"


class DestinationType(Enum):
    """Types of delivery destinations."""
    DISCORD_CHANNEL = "discord_channel"
    WEBHOOK = "webhook"
    EMAIL = "email"
    FILE = "file"


@dataclass
class Destination(BaseModel):
    """Delivery destination for scheduled summaries."""
    type: DestinationType
    target: str  # Channel ID, webhook URL, email address, or file path
    format: str = "embed"  # embed, markdown, json
    enabled: bool = True
    
    def to_display_string(self) -> str:
        """Get human-readable destination string."""
        type_names = {
            DestinationType.DISCORD_CHANNEL: "Discord Channel",
            DestinationType.WEBHOOK: "Webhook",
            DestinationType.EMAIL: "Email",
            DestinationType.FILE: "File"
        }
        
        status = "✅" if self.enabled else "❌"
        return f"{status} {type_names[self.type]}: {self.target} ({self.format})"


@dataclass
class ScheduledTask(BaseModel):
    """A scheduled summarization task."""
    id: str = field(default_factory=generate_id)
    name: str = ""
    channel_id: str = ""
    guild_id: str = ""
    schedule_type: ScheduleType = ScheduleType.DAILY
    schedule_time: Optional[str] = None  # Time in HH:MM format
    schedule_days: List[int] = field(default_factory=list)  # Days of week (0=Monday)
    cron_expression: Optional[str] = None  # For custom scheduling
    destinations: List[Destination] = field(default_factory=list)
    summary_options: SummaryOptions = field(default_factory=SummaryOptions)
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = ""  # User ID who created the task
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    failure_count: int = 0
    max_failures: int = 3
    retry_delay_minutes: int = 5
    
    def calculate_next_run(self, from_time: Optional[datetime] = None) -> Optional[datetime]:
        """Calculate the next run time for this task."""
        if not self.is_active:
            return None
        
        base_time = from_time or datetime.utcnow()
        
        if self.schedule_type == ScheduleType.ONCE:
            # One-time tasks don't have a next run after completion
            return None if self.last_run else base_time
        
        if self.schedule_type == ScheduleType.DAILY:
            next_run = base_time.replace(second=0, microsecond=0)
            
            if self.schedule_time:
                try:
                    hour, minute = map(int, self.schedule_time.split(':'))
                    next_run = next_run.replace(hour=hour, minute=minute)
                    
                    # If the time has passed today, schedule for tomorrow
                    if next_run <= base_time:
                        next_run += timedelta(days=1)
                except ValueError:
                    # Invalid time format, use current time + 1 day
                    next_run += timedelta(days=1)
            else:
                # No specific time, run daily at the same time as now
                next_run += timedelta(days=1)
            
            return next_run
        
        if self.schedule_type == ScheduleType.WEEKLY:
            next_run = base_time.replace(second=0, microsecond=0)
            
            if self.schedule_time:
                try:
                    hour, minute = map(int, self.schedule_time.split(':'))
                    next_run = next_run.replace(hour=hour, minute=minute)
                except ValueError:
                    pass
            
            # Find next scheduled day
            current_weekday = base_time.weekday()  # 0=Monday
            scheduled_days = self.schedule_days or [current_weekday]
            
            days_ahead = None
            for day in sorted(scheduled_days):
                if day > current_weekday or (day == current_weekday and next_run > base_time):
                    days_ahead = day - current_weekday
                    break
            
            if days_ahead is None:
                # Next occurrence is next week
                days_ahead = (7 - current_weekday) + min(scheduled_days)
            
            next_run += timedelta(days=days_ahead)
            return next_run
        
        if self.schedule_type == ScheduleType.MONTHLY:
            # Simple monthly scheduling - same day of month
            next_run = base_time.replace(second=0, microsecond=0, day=1)
            
            if self.schedule_time:
                try:
                    hour, minute = map(int, self.schedule_time.split(':'))
                    next_run = next_run.replace(hour=hour, minute=minute)
                except ValueError:
                    pass
            
            # Try to use the same day of month as the original creation
            target_day = self.created_at.day
            
            # Add one month
            if next_run.month == 12:
                next_run = next_run.replace(year=next_run.year + 1, month=1)
            else:
                next_run = next_run.replace(month=next_run.month + 1)
            
            # Adjust for day of month
            try:
                next_run = next_run.replace(day=target_day)
            except ValueError:
                # Day doesn't exist in this month (e.g., Feb 31)
                # Use last day of month
                if next_run.month == 12:
                    next_run = next_run.replace(year=next_run.year + 1, month=1, day=1) - timedelta(days=1)
                else:
                    next_run = next_run.replace(month=next_run.month + 1, day=1) - timedelta(days=1)
            
            return next_run
        
        # CUSTOM type would use cron_expression (not implemented here)
        return None
    
    def should_run_now(self, current_time: Optional[datetime] = None) -> bool:
        """Check if task should run now."""
        if not self.is_active:
            return False
        
        if not self.next_run:
            self.next_run = self.calculate_next_run(current_time)
        
        if not self.next_run:
            return False
        
        current_time = current_time or datetime.utcnow()
        return current_time >= self.next_run
    
    def mark_run_started(self) -> None:
        """Mark that a run has started."""
        self.last_run = datetime.utcnow()
        self.run_count += 1
    
    def mark_run_completed(self) -> None:
        """Mark that a run completed successfully."""
        self.next_run = self.calculate_next_run()
        self.failure_count = 0  # Reset failure count on success
    
    def mark_run_failed(self) -> None:
        """Mark that a run failed."""
        self.failure_count += 1
        
        # Disable task if too many failures
        if self.failure_count >= self.max_failures:
            self.is_active = False
        else:
            # Schedule retry
            retry_time = datetime.utcnow() + timedelta(minutes=self.retry_delay_minutes)
            self.next_run = retry_time
    
    def get_schedule_description(self) -> str:
        """Get human-readable schedule description."""
        if self.schedule_type == ScheduleType.ONCE:
            return "One time"
        
        if self.schedule_type == ScheduleType.DAILY:
            time_part = f" at {self.schedule_time}" if self.schedule_time else ""
            return f"Daily{time_part}"
        
        if self.schedule_type == ScheduleType.WEEKLY:
            day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            if self.schedule_days:
                days = ", ".join([day_names[d] for d in sorted(self.schedule_days)])
            else:
                days = "Weekly"
            time_part = f" at {self.schedule_time}" if self.schedule_time else ""
            return f"{days}{time_part}"
        
        if self.schedule_type == ScheduleType.MONTHLY:
            day_part = f" on day {self.created_at.day}"
            time_part = f" at {self.schedule_time}" if self.schedule_time else ""
            return f"Monthly{day_part}{time_part}"
        
        if self.schedule_type == ScheduleType.CUSTOM:
            return f"Custom: {self.cron_expression}"
        
        return "Unknown schedule"
    
    def to_status_dict(self) -> Dict[str, Any]:
        """Get status information for display."""
        return {
            "id": self.id,
            "name": self.name,
            "schedule": self.get_schedule_description(),
            "is_active": self.is_active,
            "run_count": self.run_count,
            "failure_count": self.failure_count,
            "last_run": self.last_run,
            "next_run": self.next_run,
            "destinations": [dest.to_display_string() for dest in self.destinations],
            "created_at": self.created_at,
            "created_by": self.created_by
        }


@dataclass 
class TaskResult(BaseModel):
    """Result of a task execution."""
    task_id: str
    execution_id: str = field(default_factory=generate_id)
    status: TaskStatus = TaskStatus.PENDING
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    summary_id: Optional[str] = None
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    delivery_results: List[Dict[str, Any]] = field(default_factory=list)
    execution_time_seconds: Optional[float] = None
    
    def mark_completed(self, summary_id: str) -> None:
        """Mark task as completed successfully."""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.summary_id = summary_id
        self.execution_time_seconds = (self.completed_at - self.started_at).total_seconds()
    
    def mark_failed(self, error: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Mark task as failed."""
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error_message = error
        self.error_details = details
        self.execution_time_seconds = (self.completed_at - self.started_at).total_seconds()
    
    def add_delivery_result(self, destination_type: str, target: str, success: bool, 
                          message: Optional[str] = None) -> None:
        """Add a delivery result."""
        self.delivery_results.append({
            "destination_type": destination_type,
            "target": target,
            "success": success,
            "message": message,
            "timestamp": datetime.utcnow()
        })
    
    def get_summary_text(self) -> str:
        """Get summary text for the execution result."""
        if self.status == TaskStatus.COMPLETED:
            success_count = sum(1 for result in self.delivery_results if result["success"])
            total_deliveries = len(self.delivery_results)
            return f"✅ Completed in {self.execution_time_seconds:.1f}s, {success_count}/{total_deliveries} deliveries successful"
        
        if self.status == TaskStatus.FAILED:
            return f"❌ Failed after {self.execution_time_seconds:.1f}s: {self.error_message}"
        
        if self.status == TaskStatus.RUNNING:
            elapsed = (datetime.utcnow() - self.started_at).total_seconds()
            return f"🔄 Running for {elapsed:.1f}s"
        
        return f"⏳ {self.status.value.title()}"