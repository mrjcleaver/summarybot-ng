"""
Scheduling command handlers for automated summaries.
"""

import logging
from typing import Optional
from datetime import datetime, time
import discord

from .base import BaseCommandHandler
from .utils import format_error_response, format_success_response, format_info_response
from ..exceptions import UserError, create_error_context
from ..models.task import ScheduledTask, TaskType, TaskStatus
from ..models.summary import SummaryLength

logger = logging.getLogger(__name__)


class ScheduleCommandHandler(BaseCommandHandler):
    """Handler for scheduling commands."""

    def __init__(self, summarization_engine, permission_manager=None,
                 task_scheduler=None):
        """
        Initialize schedule command handler.

        Args:
            summarization_engine: SummarizationEngine instance
            permission_manager: PermissionManager instance (optional)
            task_scheduler: TaskScheduler instance for managing scheduled tasks
        """
        super().__init__(summarization_engine, permission_manager)
        self.task_scheduler = task_scheduler

        # Scheduling commands require admin permissions
        self.requires_admin = True

    async def _execute_command(self, interaction: discord.Interaction, **kwargs) -> None:
        """Execute scheduling command."""
        pass

    async def _check_admin_permission(self, interaction: discord.Interaction) -> bool:
        """
        Check if user has admin permissions.

        Args:
            interaction: Discord interaction object

        Returns:
            True if user is admin
        """
        if not interaction.guild:
            return False

        member = interaction.guild.get_member(interaction.user.id)
        if not member:
            return False

        return member.guild_permissions.administrator or member.guild_permissions.manage_guild

    async def handle_schedule_create(self,
                                    interaction: discord.Interaction,
                                    channel: discord.TextChannel,
                                    frequency: str,
                                    time_of_day: Optional[str] = None,
                                    length: str = "detailed") -> None:
        """
        Create a new scheduled summary.

        Args:
            interaction: Discord interaction object
            channel: Target channel for summaries
            frequency: Schedule frequency (daily, weekly, custom)
            time_of_day: Time to generate summary (HH:MM format)
            length: Summary length
        """
        try:
            # Check admin permission
            if not await self._check_admin_permission(interaction):
                await self.send_permission_error(interaction)
                return

            if not self.task_scheduler:
                raise UserError(
                    message="Task scheduler not available",
                    error_code="NO_SCHEDULER",
                    user_message="Scheduled summaries feature is not available."
                )

            # Validate frequency
            valid_frequencies = ["hourly", "daily", "weekly", "monthly"]
            if frequency.lower() not in valid_frequencies:
                raise UserError(
                    message=f"Invalid frequency: {frequency}",
                    error_code="INVALID_FREQUENCY",
                    user_message=f"Frequency must be one of: {', '.join(valid_frequencies)}"
                )

            # Parse time if provided
            schedule_time = None
            if time_of_day:
                try:
                    hour, minute = map(int, time_of_day.split(':'))
                    schedule_time = time(hour=hour, minute=minute)
                except ValueError:
                    raise UserError(
                        message=f"Invalid time format: {time_of_day}",
                        error_code="INVALID_TIME",
                        user_message="Time must be in HH:MM format (e.g., 09:00, 14:30)"
                    )

            # Validate summary length
            try:
                summary_length = SummaryLength(length.lower())
            except ValueError:
                raise UserError(
                    message=f"Invalid length: {length}",
                    error_code="INVALID_LENGTH",
                    user_message="Length must be 'brief', 'detailed', or 'comprehensive'."
                )

            # Create scheduled task
            task = ScheduledTask(
                guild_id=str(interaction.guild_id),
                channel_id=str(channel.id),
                task_type=TaskType.SUMMARY,
                frequency=frequency.lower(),
                schedule_time=schedule_time,
                enabled=True,
                metadata={
                    "summary_length": summary_length.value,
                    "created_by": str(interaction.user.id),
                    "channel_name": channel.name
                }
            )

            # Schedule the task
            task_id = await self.task_scheduler.schedule_task(task)

            # Create success response
            schedule_desc = f"{frequency.capitalize()}"
            if schedule_time:
                schedule_desc += f" at {schedule_time.strftime('%H:%M')} UTC"

            embed = format_success_response(
                title="Scheduled Summary Created",
                description=f"Automatic summaries will be posted to {channel.mention}",
                fields={
                    "Schedule": schedule_desc,
                    "Length": summary_length.value.capitalize(),
                    "Task ID": task_id,
                    "Status": "Active"
                }
            )

            embed.set_footer(text=f"Use /schedule list to view all scheduled summaries")

            await interaction.response.send_message(embed=embed)

            logger.info(
                f"Scheduled summary created - Guild: {interaction.guild_id}, "
                f"Channel: {channel.id}, Frequency: {frequency}, User: {interaction.user.id}"
            )

        except UserError as e:
            await self.send_error_response(interaction, e)
        except Exception as e:
            logger.exception(f"Failed to create scheduled summary: {e}")
            await self.send_error_response(interaction, e)

    async def handle_schedule_list(self, interaction: discord.Interaction) -> None:
        """
        List all scheduled summaries for the guild.

        Args:
            interaction: Discord interaction object
        """
        try:
            if not self.task_scheduler:
                raise UserError(
                    message="Task scheduler not available",
                    error_code="NO_SCHEDULER",
                    user_message="Scheduled summaries feature is not available."
                )

            guild_id = str(interaction.guild_id)
            tasks = await self.task_scheduler.get_scheduled_tasks(guild_id)

            # Filter for summary tasks only
            summary_tasks = [t for t in tasks if t.task_type == TaskType.SUMMARY]

            if not summary_tasks:
                embed = format_info_response(
                    title="Scheduled Summaries",
                    description="No scheduled summaries configured for this server.",
                    fields={
                        "Get Started": "Use `/schedule create` to set up automatic summaries."
                    }
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Create embed with task list
            embed = discord.Embed(
                title="📅 Scheduled Summaries",
                description=f"Active summaries for {interaction.guild.name}",
                color=0x4A90E2,
                timestamp=datetime.utcnow()
            )

            for i, task in enumerate(summary_tasks[:10], 1):  # Limit to 10
                channel = interaction.guild.get_channel(int(task.channel_id))
                channel_name = channel.mention if channel else f"Channel {task.channel_id}"

                schedule_desc = task.frequency.capitalize()
                if task.schedule_time:
                    schedule_desc += f" at {task.schedule_time.strftime('%H:%M')} UTC"

                status_emoji = "✅" if task.enabled else "⏸️"
                length = task.metadata.get("summary_length", "detailed")

                field_value = (
                    f"{status_emoji} **Status:** {'Active' if task.enabled else 'Paused'}\n"
                    f"📝 **Channel:** {channel_name}\n"
                    f"🔄 **Schedule:** {schedule_desc}\n"
                    f"📏 **Length:** {length}\n"
                    f"🆔 **ID:** `{task.id}`"
                )

                embed.add_field(
                    name=f"#{i}",
                    value=field_value,
                    inline=False
                )

            if len(summary_tasks) > 10:
                embed.set_footer(text=f"Showing 10 of {len(summary_tasks)} scheduled summaries")

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            logger.exception(f"Failed to list scheduled summaries: {e}")
            await self.send_error_response(interaction, e)

    async def handle_schedule_delete(self,
                                    interaction: discord.Interaction,
                                    task_id: str) -> None:
        """
        Delete a scheduled summary.

        Args:
            interaction: Discord interaction object
            task_id: ID of task to delete
        """
        try:
            # Check admin permission
            if not await self._check_admin_permission(interaction):
                await self.send_permission_error(interaction)
                return

            if not self.task_scheduler:
                raise UserError(
                    message="Task scheduler not available",
                    error_code="NO_SCHEDULER",
                    user_message="Scheduled summaries feature is not available."
                )

            # Cancel the task
            success = await self.task_scheduler.cancel_task(task_id)

            if not success:
                raise UserError(
                    message=f"Task not found: {task_id}",
                    error_code="TASK_NOT_FOUND",
                    user_message=f"Could not find scheduled summary with ID `{task_id}`."
                )

            embed = format_success_response(
                title="Scheduled Summary Deleted",
                description=f"Successfully deleted scheduled summary.",
                fields={"Task ID": f"`{task_id}`"}
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)

            logger.info(
                f"Scheduled summary deleted - Guild: {interaction.guild_id}, "
                f"Task: {task_id}, User: {interaction.user.id}"
            )

        except UserError as e:
            await self.send_error_response(interaction, e)
        except Exception as e:
            logger.exception(f"Failed to delete scheduled summary: {e}")
            await self.send_error_response(interaction, e)

    async def handle_schedule_pause(self,
                                   interaction: discord.Interaction,
                                   task_id: str) -> None:
        """
        Pause a scheduled summary.

        Args:
            interaction: Discord interaction object
            task_id: ID of task to pause
        """
        try:
            # Check admin permission
            if not await self._check_admin_permission(interaction):
                await self.send_permission_error(interaction)
                return

            if not self.task_scheduler:
                raise UserError(
                    message="Task scheduler not available",
                    error_code="NO_SCHEDULER",
                    user_message="Scheduled summaries feature is not available."
                )

            # Update task status
            await self.task_scheduler.update_task_status(task_id, enabled=False)

            embed = format_success_response(
                title="Scheduled Summary Paused",
                description="The scheduled summary has been paused.",
                fields={
                    "Task ID": f"`{task_id}`",
                    "Note": "Use `/schedule resume` to resume this summary."
                }
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            logger.exception(f"Failed to pause scheduled summary: {e}")
            await self.send_error_response(interaction, e)

    async def handle_schedule_resume(self,
                                    interaction: discord.Interaction,
                                    task_id: str) -> None:
        """
        Resume a paused scheduled summary.

        Args:
            interaction: Discord interaction object
            task_id: ID of task to resume
        """
        try:
            # Check admin permission
            if not await self._check_admin_permission(interaction):
                await self.send_permission_error(interaction)
                return

            if not self.task_scheduler:
                raise UserError(
                    message="Task scheduler not available",
                    error_code="NO_SCHEDULER",
                    user_message="Scheduled summaries feature is not available."
                )

            # Update task status
            await self.task_scheduler.update_task_status(task_id, enabled=True)

            embed = format_success_response(
                title="Scheduled Summary Resumed",
                description="The scheduled summary has been resumed.",
                fields={"Task ID": f"`{task_id}`"}
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            logger.exception(f"Failed to resume scheduled summary: {e}")
            await self.send_error_response(interaction, e)
