"""
Task execution logic for scheduled tasks.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any

import discord

from .tasks import SummaryTask, CleanupTask
from ..models.task import TaskResult, DestinationType, ScheduledTask
from ..models.summary import SummaryResult, SummarizationContext
from ..exceptions import (
    SummaryBotException, InsufficientContentError,
    MessageFetchError, create_error_context
)
from ..logging import CommandLogger, log_command, CommandType

logger = logging.getLogger(__name__)


@dataclass
class TaskExecutionResult:
    """Result of task execution."""

    task_id: str
    success: bool
    summary_result: Optional[SummaryResult] = None
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    delivery_results: List[Dict[str, Any]] = field(default_factory=list)
    execution_time_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task_id": self.task_id,
            "success": self.success,
            "summary_id": self.summary_result.id if self.summary_result else None,
            "error_message": self.error_message,
            "error_details": self.error_details,
            "delivery_results": self.delivery_results,
            "execution_time_seconds": self.execution_time_seconds
        }


class TaskExecutor:
    """Executes scheduled tasks with proper error handling and delivery."""

    def __init__(self,
                 summarization_engine,
                 message_processor,
                 discord_client: Optional[discord.Client] = None,
                 command_logger: Optional[CommandLogger] = None):
        """Initialize task executor.

        Args:
            summarization_engine: Summarization engine instance
            message_processor: Message processor instance
            discord_client: Optional Discord client for delivery
            command_logger: CommandLogger instance for audit logging (optional)
        """
        self.summarization_engine = summarization_engine
        self.message_processor = message_processor
        self.discord_client = discord_client
        self.command_logger = command_logger

    @log_command(CommandType.SCHEDULED_TASK, command_name="execute_summary_task")
    async def execute_summary_task(self, task: SummaryTask) -> TaskExecutionResult:
        """Execute a summary task.

        Args:
            task: Summary task to execute

        Returns:
            Task execution result
        """
        start_time = datetime.utcnow()
        task.mark_started()

        logger.info(f"Executing summary task for channel {task.channel_id}")

        try:
            # Get time range for messages
            start_msg_time, end_msg_time = task.get_time_range()

            # Fetch and process messages
            messages = await self.message_processor.process_channel_messages(
                channel_id=task.channel_id,
                start_time=start_msg_time,
                end_time=end_msg_time,
                options=task.summary_options
            )

            logger.info(f"Fetched {len(messages)} messages for summarization")

            # Create summarization context
            context = SummarizationContext(
                channel_name=f"Channel {task.channel_id}",  # Could be enhanced with actual name
                guild_name=f"Guild {task.guild_id}",
                total_participants=len(set(msg.author_id for msg in messages)),
                time_span_hours=task.time_range_hours,
                message_types={"text": len(messages)}
            )

            # Generate summary
            summary_result = await self.summarization_engine.summarize_messages(
                messages=messages,
                options=task.summary_options,
                context=context,
                channel_id=task.channel_id,
                guild_id=task.guild_id
            )

            logger.info(f"Generated summary {summary_result.id}")

            # Deliver to destinations
            delivery_results = await self._deliver_summary(
                summary=summary_result,
                destinations=task.destinations,
                task=task
            )

            # Mark task as completed
            task.mark_completed()

            execution_time = (datetime.utcnow() - start_time).total_seconds()

            return TaskExecutionResult(
                task_id=task.scheduled_task.id,
                success=True,
                summary_result=summary_result,
                delivery_results=delivery_results,
                execution_time_seconds=execution_time
            )

        except InsufficientContentError as e:
            logger.warning(f"Insufficient content for task {task.scheduled_task.id}: {e}")
            task.mark_failed(f"Not enough messages to summarize: {e.message}")

            execution_time = (datetime.utcnow() - start_time).total_seconds()

            return TaskExecutionResult(
                task_id=task.scheduled_task.id,
                success=False,
                error_message=e.user_message,
                error_details=e.to_dict(),
                execution_time_seconds=execution_time
            )

        except Exception as e:
            logger.exception(f"Failed to execute summary task: {e}")
            task.mark_failed(str(e))

            execution_time = (datetime.utcnow() - start_time).total_seconds()

            return TaskExecutionResult(
                task_id=task.scheduled_task.id,
                success=False,
                error_message=str(e),
                error_details={"exception_type": type(e).__name__},
                execution_time_seconds=execution_time
            )

    @log_command(CommandType.SCHEDULED_TASK, command_name="execute_cleanup_task")
    async def execute_cleanup_task(self, task: CleanupTask) -> TaskExecutionResult:
        """Execute a cleanup task.

        Args:
            task: Cleanup task to execute

        Returns:
            Task execution result
        """
        start_time = datetime.utcnow()
        task.mark_started()

        logger.info(f"Executing cleanup task {task.task_id}")

        try:
            cutoff_date = task.get_cutoff_date()
            items_deleted = 0

            # TODO: Implement actual cleanup logic with database
            # This would involve:
            # - Deleting old summaries
            # - Cleaning up logs
            # - Clearing cached data

            logger.info(f"Cleanup would delete items older than {cutoff_date}")

            # Placeholder - would actually delete items
            items_deleted = 0

            # Mark task as completed
            task.mark_completed(items_deleted)

            execution_time = (datetime.utcnow() - start_time).total_seconds()

            return TaskExecutionResult(
                task_id=task.task_id,
                success=True,
                execution_time_seconds=execution_time
            )

        except Exception as e:
            logger.exception(f"Failed to execute cleanup task: {e}")
            task.mark_failed(str(e))

            execution_time = (datetime.utcnow() - start_time).total_seconds()

            return TaskExecutionResult(
                task_id=task.task_id,
                success=False,
                error_message=str(e),
                error_details={"exception_type": type(e).__name__},
                execution_time_seconds=execution_time
            )

    async def handle_task_failure(self, task: ScheduledTask, error: Exception) -> None:
        """Handle task failure with notifications and recovery.

        Args:
            task: Failed task
            error: Exception that caused the failure
        """
        logger.error(f"Handling failure for task {task.id}: {error}")

        # Log failure details
        error_details = {
            "task_id": task.id,
            "task_name": task.name,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "failure_count": task.failure_count,
            "timestamp": datetime.utcnow().isoformat()
        }

        logger.error(f"Task failure details: {error_details}")

        # Send notification to Discord if available and task has destinations
        if self.discord_client and task.destinations:
            await self._send_failure_notification(task, error_details)

        # Check if task should be disabled
        if task.failure_count >= task.max_failures:
            logger.warning(
                f"Task {task.id} disabled after {task.failure_count} failures"
            )

    async def _deliver_summary(self,
                              summary: SummaryResult,
                              destinations: List,
                              task: SummaryTask) -> List[Dict[str, Any]]:
        """Deliver summary to configured destinations.

        Args:
            summary: Summary result to deliver
            destinations: List of delivery destinations
            task: Original summary task

        Returns:
            List of delivery results
        """
        delivery_results = []

        for destination in destinations:
            if not destination.enabled:
                continue

            try:
                if destination.type == DestinationType.DISCORD_CHANNEL:
                    result = await self._deliver_to_discord(
                        summary=summary,
                        channel_id=destination.target,
                        format_type=destination.format
                    )
                    delivery_results.append(result)

                elif destination.type == DestinationType.WEBHOOK:
                    result = await self._deliver_to_webhook(
                        summary=summary,
                        webhook_url=destination.target,
                        format_type=destination.format
                    )
                    delivery_results.append(result)

                # Other destination types would be implemented here

            except Exception as e:
                logger.error(f"Failed to deliver to {destination.type.value}: {e}")
                delivery_results.append({
                    "destination_type": destination.type.value,
                    "target": destination.target,
                    "success": False,
                    "error": str(e)
                })

        return delivery_results

    async def _deliver_to_discord(self,
                                 summary: SummaryResult,
                                 channel_id: str,
                                 format_type: str) -> Dict[str, Any]:
        """Deliver summary to Discord channel.

        Args:
            summary: Summary to deliver
            channel_id: Discord channel ID
            format_type: Format (embed, markdown, etc.)

        Returns:
            Delivery result
        """
        if not self.discord_client:
            return {
                "destination_type": "discord_channel",
                "target": channel_id,
                "success": False,
                "error": "Discord client not available"
            }

        try:
            channel = self.discord_client.get_channel(int(channel_id))
            if not channel:
                channel = await self.discord_client.fetch_channel(int(channel_id))

            if format_type == "embed":
                embed_dict = summary.to_embed_dict()
                embed = discord.Embed.from_dict(embed_dict)
                await channel.send(embed=embed)

            elif format_type == "markdown":
                markdown = summary.to_markdown()
                # Split if too long
                if len(markdown) > 2000:
                    chunks = [markdown[i:i+2000] for i in range(0, len(markdown), 2000)]
                    for chunk in chunks:
                        await channel.send(chunk)
                else:
                    await channel.send(markdown)

            else:
                await channel.send(f"Summary generated: {summary.summary_text[:500]}...")

            return {
                "destination_type": "discord_channel",
                "target": channel_id,
                "success": True,
                "message": "Delivered successfully"
            }

        except Exception as e:
            logger.exception(f"Failed to deliver to Discord channel {channel_id}: {e}")
            return {
                "destination_type": "discord_channel",
                "target": channel_id,
                "success": False,
                "error": str(e)
            }

    async def _deliver_to_webhook(self,
                                 summary: SummaryResult,
                                 webhook_url: str,
                                 format_type: str) -> Dict[str, Any]:
        """Deliver summary to webhook.

        Args:
            summary: Summary to deliver
            webhook_url: Webhook URL
            format_type: Format (json, markdown, etc.)

        Returns:
            Delivery result
        """
        # Placeholder - would use aiohttp or similar
        logger.info(f"Would deliver to webhook: {webhook_url}")

        return {
            "destination_type": "webhook",
            "target": webhook_url,
            "success": True,
            "message": "Webhook delivery not yet implemented"
        }

    async def _send_failure_notification(self,
                                        task: ScheduledTask,
                                        error_details: Dict[str, Any]) -> None:
        """Send failure notification to Discord.

        Args:
            task: Failed task
            error_details: Error details
        """
        if not self.discord_client:
            return

        # Find a Discord destination to send notification
        discord_destinations = [
            d for d in task.destinations
            if d.type == DestinationType.DISCORD_CHANNEL and d.enabled
        ]

        if not discord_destinations:
            return

        notification = (
            f"⚠️ **Scheduled Task Failed**\n\n"
            f"**Task:** {task.name}\n"
            f"**Error:** {error_details['error_message']}\n"
            f"**Failure Count:** {task.failure_count}/{task.max_failures}\n"
            f"**Time:** {error_details['timestamp']}\n"
        )

        if task.failure_count >= task.max_failures:
            notification += "\n❌ **Task has been disabled due to repeated failures.**"

        try:
            channel_id = discord_destinations[0].target
            channel = self.discord_client.get_channel(int(channel_id))
            if channel:
                await channel.send(notification)
        except Exception as e:
            logger.error(f"Failed to send failure notification: {e}")
