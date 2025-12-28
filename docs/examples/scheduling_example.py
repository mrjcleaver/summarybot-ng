"""
Example usage of the scheduling module for Summary Bot NG.

This example demonstrates how to integrate the scheduling module
with a Discord bot for automated summary generation.
"""

import asyncio
from datetime import datetime
from discord.ext import commands

from src.scheduling import TaskScheduler, TaskExecutor, TaskPersistence
from src.models.task import (
    ScheduledTask, ScheduleType, Destination, DestinationType
)
from src.models.summary import SummaryOptions, SummaryLength


async def basic_scheduling_example(bot, summarization_engine, message_processor):
    """Basic example of setting up and using the scheduler."""

    # 1. Initialize persistence layer
    persistence = TaskPersistence(storage_path="./data/tasks")

    # 2. Initialize task executor
    executor = TaskExecutor(
        summarization_engine=summarization_engine,
        message_processor=message_processor,
        discord_client=bot
    )

    # 3. Initialize scheduler
    scheduler = TaskScheduler(
        task_executor=executor,
        persistence=persistence,
        timezone="UTC"
    )

    # 4. Start the scheduler
    await scheduler.start()
    print("Scheduler started!")

    # 5. Schedule a daily summary
    daily_task = ScheduledTask(
        name="Daily Dev Channel Summary",
        channel_id="123456789",
        guild_id="987654321",
        schedule_type=ScheduleType.DAILY,
        schedule_time="09:00",  # 9 AM UTC
        destinations=[
            Destination(
                type=DestinationType.DISCORD_CHANNEL,
                target="123456789",
                format="embed"
            )
        ],
        summary_options=SummaryOptions(
            summary_length=SummaryLength.DETAILED,
            min_messages=10,
            include_bots=False
        )
    )

    task_id = await scheduler.schedule_task(daily_task)
    print(f"Scheduled daily task: {task_id}")

    # 6. Schedule a weekly summary
    weekly_task = ScheduledTask(
        name="Weekly Team Recap",
        channel_id="987654321",
        guild_id="987654321",
        schedule_type=ScheduleType.WEEKLY,
        schedule_time="17:00",
        schedule_days=[4],  # Friday
        destinations=[
            Destination(
                type=DestinationType.DISCORD_CHANNEL,
                target="987654321",
                format="markdown"
            )
        ],
        summary_options=SummaryOptions(
            summary_length=SummaryLength.COMPREHENSIVE,
            extract_action_items=True,
            extract_technical_terms=True
        )
    )

    await scheduler.schedule_task(weekly_task)
    print("Scheduled weekly task!")

    # 7. Get scheduler stats
    stats = scheduler.get_scheduler_stats()
    print(f"Active tasks: {stats['active_tasks']}")
    print(f"Next runs: {stats['next_run_times']}")

    return scheduler


async def discord_cog_example():
    """Example of integrating scheduler into a Discord cog."""

    class SchedulingCog(commands.Cog):
        """Cog for managing scheduled summaries."""

        def __init__(self, bot):
            self.bot = bot
            self.scheduler = None

        async def cog_load(self):
            """Initialize and start scheduler when cog loads."""
            persistence = TaskPersistence("./data/tasks")

            executor = TaskExecutor(
                summarization_engine=self.bot.summarization_engine,
                message_processor=self.bot.message_processor,
                discord_client=self.bot
            )

            self.scheduler = TaskScheduler(
                task_executor=executor,
                persistence=persistence
            )

            await self.scheduler.start()
            print("Scheduling service started!")

        async def cog_unload(self):
            """Stop scheduler when cog unloads."""
            if self.scheduler:
                await self.scheduler.stop()
                print("Scheduling service stopped!")

        @commands.slash_command(name="schedule")
        async def schedule_summary(
            self,
            ctx,
            frequency: str,
            time: str,
            channel: commands.TextChannel = None
        ):
            """Schedule a recurring summary.

            Args:
                frequency: daily, weekly, or monthly
                time: Time in HH:MM format (UTC)
                channel: Channel to summarize (default: current channel)
            """
            await ctx.defer()

            target_channel = channel or ctx.channel

            # Map frequency to schedule type
            schedule_types = {
                "daily": ScheduleType.DAILY,
                "weekly": ScheduleType.WEEKLY,
                "monthly": ScheduleType.MONTHLY
            }

            if frequency not in schedule_types:
                await ctx.respond("Invalid frequency! Use: daily, weekly, or monthly")
                return

            # Create task
            task = ScheduledTask(
                name=f"{frequency.title()} summary for #{target_channel.name}",
                channel_id=str(target_channel.id),
                guild_id=str(ctx.guild.id),
                schedule_type=schedule_types[frequency],
                schedule_time=time,
                destinations=[
                    Destination(
                        type=DestinationType.DISCORD_CHANNEL,
                        target=str(target_channel.id),
                        format="embed"
                    )
                ],
                summary_options=SummaryOptions(
                    summary_length=SummaryLength.DETAILED,
                    min_messages=5
                ),
                created_by=str(ctx.author.id)
            )

            # Schedule task
            task_id = await self.scheduler.schedule_task(task)

            # Send confirmation
            await ctx.respond(
                f"✅ Scheduled {frequency} summary for {target_channel.mention} "
                f"at {time} UTC!\n"
                f"Task ID: `{task_id[:8]}...`"
            )

        @commands.slash_command(name="list_schedules")
        async def list_schedules(self, ctx):
            """List all scheduled tasks for this server."""
            await ctx.defer()

            tasks = await self.scheduler.get_scheduled_tasks(
                guild_id=str(ctx.guild.id)
            )

            if not tasks:
                await ctx.respond("No scheduled tasks found for this server.")
                return

            # Build response
            embed = {
                "title": "📅 Scheduled Summaries",
                "description": f"Found {len(tasks)} scheduled task(s)",
                "fields": []
            }

            for task in tasks[:10]:  # Limit to 10
                status = "✅ Active" if task.is_active else "❌ Inactive"
                next_run = task.next_run.strftime("%Y-%m-%d %H:%M UTC") if task.next_run else "Not scheduled"

                embed["fields"].append({
                    "name": task.name or f"Task {task.id[:8]}",
                    "value": (
                        f"**Schedule:** {task.get_schedule_description()}\n"
                        f"**Next run:** {next_run}\n"
                        f"**Status:** {status}\n"
                        f"**Runs:** {task.run_count} (Failed: {task.failure_count})"
                    ),
                    "inline": False
                })

            await ctx.respond(embed=embed)

        @commands.slash_command(name="cancel_schedule")
        async def cancel_schedule(self, ctx, task_id: str):
            """Cancel a scheduled task.

            Args:
                task_id: ID of the task to cancel
            """
            await ctx.defer()

            # Verify task exists and belongs to this guild
            task_status = await self.scheduler.get_task_status(task_id)

            if not task_status:
                await ctx.respond("❌ Task not found!")
                return

            if task_status["guild_id"] != str(ctx.guild.id):
                await ctx.respond("❌ You can only cancel tasks in your own server!")
                return

            # Cancel task
            success = await self.scheduler.cancel_task(task_id)

            if success:
                await ctx.respond(f"✅ Cancelled task `{task_id}`")
            else:
                await ctx.respond(f"❌ Failed to cancel task `{task_id}`")

        @commands.slash_command(name="scheduler_stats")
        async def scheduler_stats(self, ctx):
            """Show scheduler statistics."""
            stats = self.scheduler.get_scheduler_stats()

            embed = {
                "title": "📊 Scheduler Statistics",
                "fields": [
                    {
                        "name": "Status",
                        "value": "🟢 Running" if stats["running"] else "🔴 Stopped",
                        "inline": True
                    },
                    {
                        "name": "Active Tasks",
                        "value": str(stats["active_tasks"]),
                        "inline": True
                    },
                    {
                        "name": "Timezone",
                        "value": stats["timezone"],
                        "inline": True
                    }
                ]
            }

            # Add upcoming tasks
            if stats["next_run_times"]:
                upcoming = "\n".join([
                    f"• {task['task_name']}: {task['next_run']}"
                    for task in stats["next_run_times"][:5]
                ])
                embed["fields"].append({
                    "name": "⏭️ Upcoming Executions",
                    "value": upcoming,
                    "inline": False
                })

            await ctx.respond(embed=embed)

    return SchedulingCog


async def advanced_scheduling_example():
    """Advanced examples with custom schedules and multiple destinations."""

    # Custom cron schedule - every 6 hours
    every_6_hours = ScheduledTask(
        name="Frequent Updates",
        channel_id="123456789",
        guild_id="987654321",
        schedule_type=ScheduleType.CUSTOM,
        cron_expression="0 */6 * * *",
        destinations=[
            Destination(
                type=DestinationType.DISCORD_CHANNEL,
                target="123456789",
                format="embed"
            )
        ]
    )

    # Multi-destination task
    multi_dest = ScheduledTask(
        name="Multi-Platform Summary",
        channel_id="123456789",
        guild_id="987654321",
        schedule_type=ScheduleType.DAILY,
        schedule_time="18:00",
        destinations=[
            # Discord
            Destination(
                type=DestinationType.DISCORD_CHANNEL,
                target="123456789",
                format="embed",
                enabled=True
            ),
            # Slack webhook
            Destination(
                type=DestinationType.WEBHOOK,
                target="https://hooks.slack.com/services/...",
                format="json",
                enabled=True
            )
        ]
    )

    # One-time summary
    one_time = ScheduledTask(
        name="Project Deadline Summary",
        channel_id="123456789",
        guild_id="987654321",
        schedule_type=ScheduleType.ONCE,
        next_run=datetime(2024, 12, 31, 23, 59),
        destinations=[
            Destination(
                type=DestinationType.DISCORD_CHANNEL,
                target="123456789",
                format="markdown"
            )
        ],
        summary_options=SummaryOptions(
            summary_length=SummaryLength.COMPREHENSIVE,
            extract_action_items=True,
            extract_technical_terms=True,
            include_participant_analysis=True
        )
    )

    return [every_6_hours, multi_dest, one_time]


async def cleanup_example(executor):
    """Example of running cleanup tasks."""
    from src.scheduling.tasks import CleanupTask

    # Create cleanup task
    cleanup = CleanupTask(
        task_id="monthly_cleanup",
        retention_days=90,  # Keep 90 days
        delete_summaries=True,
        delete_logs=True,
        delete_cached_data=True
    )

    # Execute cleanup
    result = await executor.execute_cleanup_task(cleanup)

    print(f"Cleanup completed!")
    print(f"Items deleted: {result.items_deleted}")
    print(f"Duration: {result.execution_time_seconds}s")


async def monitoring_example(scheduler, task_id):
    """Example of monitoring task execution."""

    # Get detailed status
    status = await scheduler.get_task_status(task_id)

    print(f"Task: {status['name']}")
    print(f"Schedule: {status['schedule']}")
    print(f"Active: {status['is_active']}")
    print(f"Runs: {status['run_count']}")
    print(f"Failures: {status['failure_count']}")

    if status['metadata']:
        meta = status['metadata']
        print(f"Success rate: {meta['success_rate']}%")
        print(f"Avg duration: {meta['average_duration_seconds']}s")

    # Get all guild tasks
    all_tasks = await scheduler.get_scheduled_tasks(
        guild_id=status['guild_id']
    )

    print(f"\nTotal tasks in guild: {len(all_tasks)}")


if __name__ == "__main__":
    print("This file contains example code for the scheduling module.")
    print("Import and use the functions in your bot implementation.")
