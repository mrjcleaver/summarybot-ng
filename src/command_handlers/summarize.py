"""
Summarization command handlers for Discord slash commands.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List
import discord

from .base import BaseCommandHandler
from .utils import (
    parse_time_string,
    validate_time_range,
    format_duration,
    format_error_response,
    format_success_response
)
from ..models.summary import SummaryOptions, SummaryLength, SummarizationContext
from ..models.message import ProcessedMessage
from ..message_processing import MessageFetcher, MessageFilter, MessageCleaner
from ..exceptions import (
    UserError,
    InsufficientContentError,
    ChannelAccessError,
    create_error_context
)

logger = logging.getLogger(__name__)


class SummarizeCommandHandler(BaseCommandHandler):
    """Handler for summarization commands."""

    def __init__(self, summarization_engine, permission_manager=None,
                 message_fetcher: Optional[MessageFetcher] = None,
                 message_filter: Optional[MessageFilter] = None,
                 message_cleaner: Optional[MessageCleaner] = None):
        """
        Initialize summarize command handler.

        Args:
            summarization_engine: SummarizationEngine instance
            permission_manager: PermissionManager instance (optional)
            message_fetcher: MessageFetcher instance
            message_filter: MessageFilter instance
            message_cleaner: MessageCleaner instance
        """
        super().__init__(summarization_engine, permission_manager)

        self.message_fetcher = message_fetcher
        self.message_filter = message_filter
        self.message_cleaner = message_cleaner

        # Override rate limits for summarization (more restrictive)
        self.max_requests_per_minute = 3
        self.rate_limit_window = 60

    async def _execute_command(self, interaction: discord.Interaction, **kwargs) -> None:
        """
        Execute summarization command.
        Routes to appropriate handler based on command options.
        """
        # This is a placeholder - actual routing happens in handle_* methods
        pass

    async def handle_summarize_interaction(
        self,
        interaction: discord.Interaction,
        messages: Optional[int] = None,
        hours: Optional[int] = None,
        minutes: Optional[int] = None
    ) -> None:
        """
        Handle /summarize slash command interaction.

        This is the main entry point from Discord slash commands.

        Args:
            interaction: Discord interaction (already deferred)
            messages: Number of messages to summarize (overrides time-based)
            hours: Hours of messages to look back
            minutes: Minutes of messages to look back
        """
        try:
            # Default to 100 messages or 24 hours
            if messages:
                # Message count mode
                await self.handle_quick_summary(
                    interaction,
                    channel=interaction.channel,
                    message_count=messages
                )
            elif hours or minutes:
                # Time-based mode
                total_hours = (hours or 0) + (minutes or 0) / 60
                await self.handle_summarize(
                    interaction,
                    channel=interaction.channel,
                    hours=int(total_hours) if total_hours > 0 else 24,
                    length="detailed",
                    include_bots=False
                )
            else:
                # Default: last 100 messages
                await self.handle_quick_summary(
                    interaction,
                    channel=interaction.channel,
                    message_count=100
                )

        except Exception as e:
            logger.error(f"Error in handle_summarize_interaction: {e}", exc_info=True)
            try:
                await interaction.followup.send(
                    f"❌ Failed to create summary: {str(e)}",
                    ephemeral=True
                )
            except:
                pass

    async def fetch_messages(self, channel: discord.TextChannel, limit: int = 100) -> list[discord.Message]:
        """
        Fetch messages from a Discord channel.

        This is a convenience method for fetching messages with a simple limit.
        For time-based fetching, use _fetch_and_process_messages instead.

        Args:
            channel: Discord text channel to fetch from
            limit: Maximum number of messages to fetch

        Returns:
            List of Discord messages
        """
        messages = []
        async for message in channel.history(limit=limit):
            messages.append(message)
        return messages

    async def fetch_recent_messages(self, channel: discord.TextChannel, time_delta: timedelta) -> list[discord.Message]:
        """
        Fetch recent messages from a channel within a time window.

        Args:
            channel: Discord text channel to fetch from
            time_delta: Time window to fetch messages from (e.g., timedelta(hours=1))

        Returns:
            List of Discord messages within the time window
        """
        now = datetime.utcnow()
        after_time = now - time_delta

        messages = []
        async for message in channel.history(limit=1000, after=after_time):
            messages.append(message)

        return messages

    async def handle_summarize(self,
                              interaction: discord.Interaction,
                              channel: Optional[discord.TextChannel] = None,
                              hours: int = 24,
                              length: str = "detailed",
                              include_bots: bool = False,
                              start_time: Optional[str] = None,
                              end_time: Optional[str] = None) -> None:
        """
        Handle the /summarize command for full customizable summaries.

        Args:
            interaction: Discord interaction object
            channel: Target channel (defaults to current channel)
            hours: Number of hours to look back (if start_time not specified)
            length: Summary length (brief/detailed/comprehensive)
            include_bots: Whether to include bot messages
            start_time: Custom start time string
            end_time: Custom end time string
        """
        await self.defer_response(interaction)

        try:
            # Check permissions
            if self.permission_manager:
                # Check command permission
                has_permission = await self.permission_manager.check_command_permission(
                    user_id=str(interaction.user.id),
                    command="summarize",
                    guild_id=str(interaction.guild_id) if interaction.guild else None
                )

                if not has_permission:
                    error_msg = "You don't have permission to use this command."
                    await interaction.response.send_message(content=error_msg, ephemeral=True)
                    return

            # Determine target channel
            target_channel = channel or interaction.channel

            # Check channel access permission
            if self.permission_manager and target_channel:
                has_access = await self.permission_manager.check_channel_access(
                    user_id=str(interaction.user.id),
                    channel_id=str(target_channel.id),
                    guild_id=str(interaction.guild_id) if interaction.guild else None
                )

                if not has_access:
                    error_msg = f"You don't have access to {target_channel.mention}."
                    await interaction.followup.send(content=error_msg, ephemeral=True)
                    return
            if not isinstance(target_channel, discord.TextChannel):
                raise UserError(
                    message=f"Invalid channel type: {type(target_channel)}",
                    error_code="INVALID_CHANNEL",
                    user_message="Summaries can only be created for text channels."
                )

            # Check channel access
            if not target_channel.permissions_for(interaction.guild.me).read_message_history:
                raise ChannelAccessError(
                    channel_id=str(target_channel.id),
                    reason=f"I don't have permission to read messages in {target_channel.mention}."
                )

            # Parse time range
            now = datetime.utcnow()

            if start_time:
                parsed_start = parse_time_string(start_time)
            else:
                parsed_start = now - timedelta(hours=hours)

            if end_time:
                parsed_end = parse_time_string(end_time)
            else:
                parsed_end = now

            # Validate time range
            validate_time_range(parsed_start, parsed_end, max_hours=168)  # 1 week max

            # Parse summary length
            try:
                summary_length = SummaryLength(length.lower())
            except ValueError:
                raise UserError(
                    message=f"Invalid summary length: {length}",
                    error_code="INVALID_LENGTH",
                    user_message=f"Invalid summary length. Choose from: brief, detailed, comprehensive."
                )

            # Create summary options
            summary_options = SummaryOptions(
                summary_length=summary_length,
                include_bots=include_bots,
                include_attachments=True,
                min_messages=5
            )

            # Send status update
            status_embed = discord.Embed(
                title="🔄 Generating Summary",
                description=f"Analyzing messages in {target_channel.mention}...",
                color=0x4A90E2,
                timestamp=datetime.utcnow()
            )
            status_embed.add_field(
                name="Time Range",
                value=f"{parsed_start.strftime('%Y-%m-%d %H:%M')} to {parsed_end.strftime('%Y-%m-%d %H:%M')}",
                inline=False
            )
            await interaction.followup.send(embed=status_embed)

            # Fetch messages first (for testability)
            raw_messages = await self.fetch_messages(target_channel, limit=10000)

            # Filter messages by time range
            time_filtered_messages = [
                msg for msg in raw_messages
                if parsed_start <= msg.created_at <= parsed_end
            ]

            # Then process them
            processed_messages = await self._process_messages(
                time_filtered_messages,
                summary_options
            )

            if len(processed_messages) < summary_options.min_messages:
                raise InsufficientContentError(
                    message_count=len(processed_messages),
                    min_required=summary_options.min_messages
                )

            # Create summarization context
            context = SummarizationContext(
                channel_name=target_channel.name,
                guild_name=interaction.guild.name,
                total_participants=len(set(msg.author_id for msg in processed_messages)),
                time_span_hours=(parsed_end - parsed_start).total_seconds() / 3600
            )

            # Generate summary
            summary_result = await self.summarization_engine.summarize_messages(
                messages=processed_messages,
                options=summary_options,
                context=context,
                channel_id=str(target_channel.id),
                guild_id=str(interaction.guild_id)
            )

            # Send summary as embed
            summary_embed_dict = summary_result.to_embed_dict()
            summary_embed = discord.Embed.from_dict(summary_embed_dict)

            await interaction.followup.send(embed=summary_embed)

            # Log success
            logger.info(
                f"Summary generated - Guild: {interaction.guild_id}, "
                f"Channel: {target_channel.id}, Messages: {len(processed_messages)}, "
                f"User: {interaction.user.id}"
            )

        except (UserError, InsufficientContentError, ChannelAccessError) as e:
            logger.warning(f"Summarization failed: {e.to_log_string()}")
            await self.send_error_response(interaction, e)

        except Exception as e:
            logger.exception(f"Unexpected error in summarize command: {e}")
            error = UserError(
                message=str(e),
                error_code="SUMMARIZE_FAILED",
                user_message="Failed to generate summary. Please try again later."
            )
            await self.send_error_response(interaction, error)

    async def handle_quick_summary(self,
                                  interaction: discord.Interaction,
                                  minutes: int = 60) -> None:
        """
        Handle quick summary command for recent messages.

        Args:
            interaction: Discord interaction object
            minutes: Number of minutes to look back (default: 60)
        """
        await self.defer_response(interaction)

        try:
            # Validate minutes
            if minutes < 5 or minutes > 1440:  # 5 min to 24 hours
                raise UserError(
                    message=f"Invalid minutes: {minutes}",
                    error_code="INVALID_DURATION",
                    user_message="Minutes must be between 5 and 1440 (24 hours)."
                )

            # Fetch recent messages using the dedicated method
            target_channel = interaction.channel
            time_delta = timedelta(minutes=minutes)
            raw_messages = await self.fetch_recent_messages(target_channel, time_delta)

            # Process messages
            summary_options = SummaryOptions(
                summary_length=SummaryLength.BRIEF,
                include_bots=False
            )
            processed_messages = await self._process_messages(raw_messages, summary_options)

            if len(processed_messages) < summary_options.min_messages:
                raise InsufficientContentError(
                    message_count=len(processed_messages),
                    min_required=summary_options.min_messages
                )

            # Create summarization context
            context = SummarizationContext(
                channel_name=target_channel.name,
                guild_name=interaction.guild.name,
                total_participants=len(set(msg.author_id for msg in processed_messages)),
                time_span_hours=minutes / 60
            )

            # Generate summary
            summary_result = await self.summarization_engine.summarize_messages(
                messages=processed_messages,
                options=summary_options,
                context=context,
                channel_id=str(target_channel.id),
                guild_id=str(interaction.guild_id)
            )

            # Send summary as embed
            summary_embed_dict = summary_result.to_embed_dict()
            summary_embed = discord.Embed.from_dict(summary_embed_dict)

            await interaction.followup.send(embed=summary_embed)

        except Exception as e:
            logger.exception(f"Quick summary failed: {e}")
            await self.send_error_response(interaction, e)

    async def handle_scheduled_summary(self,
                                      interaction: discord.Interaction,
                                      channel: discord.TextChannel,
                                      schedule: str,
                                      length: str = "detailed") -> None:
        """
        Handle scheduled summary setup command.

        Args:
            interaction: Discord interaction object
            channel: Target channel for summaries
            schedule: Schedule specification (e.g., "daily", "weekly")
            length: Summary length
        """
        # This is a placeholder - actual scheduling happens in schedule.py
        embed = discord.Embed(
            title="ℹ️ Scheduled Summaries",
            description="Scheduled summary feature is coming soon!",
            color=0x4A90E2
        )

        embed.add_field(
            name="Requested Schedule",
            value=f"Channel: {channel.mention}\nSchedule: {schedule}\nLength: {length}",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def _process_messages(self,
                               raw_messages: List[discord.Message],
                               options: SummaryOptions) -> List[ProcessedMessage]:
        """
        Process raw Discord messages into ProcessedMessages.

        Args:
            raw_messages: List of raw Discord messages
            options: Summary options for filtering

        Returns:
            List of processed messages
        """
        if not raw_messages:
            return []

        # Filter messages
        if self.message_filter:
            self.message_filter.options = options
            filtered_messages = self.message_filter.filter_messages(raw_messages)
        else:
            # Basic filtering
            filtered_messages = [
                msg for msg in raw_messages
                if not msg.author.bot or options.include_bots
            ]

        # Clean and process messages
        processed_messages = []

        for message in filtered_messages:
            if self.message_cleaner:
                processed = self.message_cleaner.clean_message(message)
            else:
                # Basic processing
                processed = ProcessedMessage(
                    id=str(message.id),
                    author_name=message.author.display_name,
                    author_id=str(message.author.id),
                    content=message.content,
                    timestamp=message.created_at,
                    attachments=[],
                    references=[],
                    mentions=[]
                )

            # Only include messages with substantial content
            if processed.has_substantial_content():
                processed_messages.append(processed)

        return processed_messages

    async def _fetch_and_process_messages(self,
                                         channel: discord.TextChannel,
                                         start_time: datetime,
                                         end_time: datetime,
                                         options: SummaryOptions) -> List[ProcessedMessage]:
        """
        Fetch and process messages from a channel.

        Args:
            channel: Discord text channel
            start_time: Start of time range
            end_time: End of time range
            options: Summary options

        Returns:
            List of processed messages
        """
        # Fetch messages from Discord
        if self.message_fetcher:
            raw_messages = await self.message_fetcher.fetch_messages(
                channel_id=str(channel.id),
                start_time=start_time,
                end_time=end_time,
                limit=10000
            )
        else:
            # Fallback: fetch directly from channel
            raw_messages = []
            async for message in channel.history(
                limit=10000,
                after=start_time,
                before=end_time,
                oldest_first=True
            ):
                raw_messages.append(message)

        return await self._process_messages(raw_messages, options)

    async def estimate_summary_cost(self,
                                   interaction: discord.Interaction,
                                   channel: Optional[discord.TextChannel] = None,
                                   hours: int = 24) -> None:
        """
        Estimate cost for generating a summary.

        Args:
            interaction: Discord interaction object
            channel: Target channel
            hours: Hours to look back
        """
        await self.defer_response(interaction, ephemeral=True)

        try:
            target_channel = channel or interaction.channel
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours)

            # Fetch messages to estimate
            options = SummaryOptions()
            processed_messages = await self._fetch_and_process_messages(
                target_channel,
                start_time,
                end_time,
                options
            )

            # Get cost estimate
            cost_estimate = await self.summarization_engine.estimate_cost(
                messages=processed_messages,
                options=options
            )

            # Create response embed
            embed = discord.Embed(
                title="💰 Summary Cost Estimate",
                description=f"Estimated cost for summarizing {target_channel.mention}",
                color=0x4A90E2,
                timestamp=datetime.utcnow()
            )

            embed.add_field(
                name="Messages",
                value=str(cost_estimate.message_count),
                inline=True
            )

            embed.add_field(
                name="Estimated Cost",
                value=f"${cost_estimate.estimated_cost_usd:.4f} USD",
                inline=True
            )

            embed.add_field(
                name="Input Tokens",
                value=f"{cost_estimate.input_tokens:,}",
                inline=True
            )

            embed.add_field(
                name="Output Tokens",
                value=f"{cost_estimate.output_tokens:,}",
                inline=True
            )

            embed.add_field(
                name="Model",
                value=cost_estimate.model,
                inline=True
            )

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.exception(f"Cost estimation failed: {e}")
            await self.send_error_response(interaction, e)
