"""
Event handlers for Discord bot events.
"""

import logging
from typing import TYPE_CHECKING
import discord

from ..exceptions.discord_errors import DiscordError
from ..exceptions.base import SummaryBotException, ErrorContext, create_error_context
from .utils import create_error_embed, create_info_embed

if TYPE_CHECKING:
    from .bot import SummaryBot

logger = logging.getLogger(__name__)


class EventHandler:
    """Handles Discord events for the Summary Bot."""

    def __init__(self, bot: 'SummaryBot'):
        """
        Initialize the event handler.

        Args:
            bot: The SummaryBot instance
        """
        self.bot = bot
        self.config = bot.config

    async def on_ready(self) -> None:
        """
        Handle the bot ready event.

        This is called when the bot has successfully connected to Discord
        and is ready to receive events.
        """
        logger.info(f"Bot is ready! Logged in as {self.bot.client.user}")
        logger.info(f"Bot ID: {self.bot.client.user.id}")
        logger.info(f"Connected to {len(self.bot.client.guilds)} guilds")

        # Log guild information
        for guild in self.bot.client.guilds:
            logger.info(f"  - {guild.name} (ID: {guild.id}, Members: {guild.member_count})")

        # Set bot status
        await self._update_presence()

        # Sync commands for all guilds (guild-specific sync is instant)
        try:
            # Sync to each guild individually for instant availability
            for guild in self.bot.client.guilds:
                try:
                    # Sync guild commands
                    await self.bot.sync_commands(guild_id=str(guild.id))
                    logger.info(f"Synced commands for guild: {guild.name} (ID: {guild.id})")
                except Exception as e:
                    logger.error(f"Failed to sync commands for guild {guild.id}: {e}")

            logger.info("Successfully synced slash commands to all guilds")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}", exc_info=True)

    async def on_guild_join(self, guild: discord.Guild) -> None:
        """
        Handle the bot joining a new guild.

        Args:
            guild: The guild that was joined
        """
        logger.info(f"Joined new guild: {guild.name} (ID: {guild.id}, Members: {guild.member_count})")

        # Initialize default configuration for the guild
        guild_config = self.config.get_guild_config(str(guild.id))
        logger.info(f"Created default configuration for guild {guild.id}")

        # Try to send a welcome message to the system channel or first available text channel
        welcome_channel = guild.system_channel
        if not welcome_channel:
            # Find the first text channel we can send messages to
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    welcome_channel = channel
                    break

        if welcome_channel:
            try:
                embed = create_info_embed(
                    title="Thanks for adding Summary Bot NG!",
                    description=(
                        "I'm here to help you summarize Discord conversations using AI.\n\n"
                        "**Getting Started:**\n"
                        "• Use `/summarize` to create summaries of channel conversations\n"
                        "• Use `/config` to configure bot settings\n"
                        "• Use `/help` to see all available commands\n\n"
                        "**Permissions:**\n"
                        "Make sure I have permissions to:\n"
                        "• Read message history\n"
                        "• Send messages\n"
                        "• Use slash commands\n\n"
                        "Need help? Check out the documentation or contact your server admins."
                    )
                )
                await welcome_channel.send(embed=embed)
                logger.info(f"Sent welcome message to {guild.name}")
            except discord.Forbidden:
                logger.warning(f"Could not send welcome message to {guild.name} - missing permissions")
            except Exception as e:
                logger.error(f"Error sending welcome message to {guild.name}: {e}", exc_info=True)

        # Sync commands for this guild
        try:
            # Sync guild commands
            await self.bot.sync_commands(guild_id=str(guild.id))
            logger.info(f"Synced commands for guild {guild.id}")
        except Exception as e:
            logger.error(f"Failed to sync commands for guild {guild.id}: {e}", exc_info=True)

    async def on_guild_remove(self, guild: discord.Guild) -> None:
        """
        Handle the bot being removed from a guild.

        Args:
            guild: The guild that was left
        """
        logger.info(f"Removed from guild: {guild.name} (ID: {guild.id})")

        # Optionally clean up guild configuration
        # Note: We might want to keep configuration for a grace period
        # in case the bot is re-added

    async def on_application_command_error(
        self,
        interaction: discord.Interaction,
        error: Exception
    ) -> None:
        """
        Handle errors that occur during command execution.

        Args:
            interaction: The interaction that caused the error
            error: The exception that was raised
        """
        # Extract context information
        context = create_error_context(
            user_id=str(interaction.user.id) if interaction.user else None,
            guild_id=str(interaction.guild_id) if interaction.guild_id else None,
            channel_id=str(interaction.channel_id) if interaction.channel_id else None,
            command=interaction.command.name if interaction.command else "unknown",
            operation="command_execution"
        )

        # Handle different error types
        if isinstance(error, SummaryBotException):
            # Our custom exceptions
            logger.warning(f"Command error: {error.to_log_string()}")

            embed = create_error_embed(
                title="Command Failed",
                description=error.get_user_response(),
                error_code=error.error_code
            )

            # Add retry message if applicable
            if error.retryable:
                embed.description += "\n\n*This error may be temporary. Please try again.*"

        elif isinstance(error, discord.Forbidden):
            # Discord permission errors
            logger.warning(
                f"Permission error in command {context.command}: {error}",
                extra={"context": context.to_dict()}
            )

            embed = create_error_embed(
                title="Permission Denied",
                description=(
                    "I don't have the necessary permissions to perform this action.\n"
                    "Please ask a server administrator to check my permissions."
                ),
                error_code="DISCORD_PERMISSION_ERROR",
                details=str(error)
            )

        elif isinstance(error, discord.NotFound):
            # Resource not found errors
            logger.warning(
                f"Resource not found in command {context.command}: {error}",
                extra={"context": context.to_dict()}
            )

            embed = create_error_embed(
                title="Not Found",
                description="The requested resource could not be found. It may have been deleted.",
                error_code="RESOURCE_NOT_FOUND"
            )

        elif isinstance(error, discord.HTTPException):
            # Discord API errors
            logger.error(
                f"Discord API error in command {context.command}: {error}",
                exc_info=True,
                extra={"context": context.to_dict()}
            )

            embed = create_error_embed(
                title="Discord API Error",
                description="An error occurred while communicating with Discord.",
                error_code="DISCORD_API_ERROR",
                details=f"Status: {error.status}, Code: {error.code}" if hasattr(error, 'status') else None
            )

        else:
            # Unexpected errors
            logger.error(
                f"Unexpected error in command {context.command}: {error}",
                exc_info=True,
                extra={"context": context.to_dict()}
            )

            embed = create_error_embed(
                title="Unexpected Error",
                description=(
                    "An unexpected error occurred while processing your command.\n"
                    "The development team has been notified."
                ),
                error_code="UNEXPECTED_ERROR"
            )

        # Send error response
        try:
            if interaction.response.is_done():
                # If we already responded, send a followup
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                # Send initial response
                await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Failed to send error response: {e}", exc_info=True)

    async def on_error(self, event: str, *args, **kwargs) -> None:
        """
        Handle generic errors in event handlers.

        Args:
            event: The name of the event that raised the error
            args: Event arguments
            kwargs: Event keyword arguments
        """
        logger.error(f"Error in event {event}", exc_info=True)

    async def _update_presence(self) -> None:
        """Update the bot's presence/status."""
        try:
            activity = discord.Activity(
                type=discord.ActivityType.watching,
                name="conversations | /help"
            )
            await self.bot.client.change_presence(
                status=discord.Status.online,
                activity=activity
            )
            logger.info("Updated bot presence")
        except Exception as e:
            logger.error(f"Failed to update presence: {e}", exc_info=True)

    def register_events(self) -> None:
        """Register all event handlers with the Discord client."""
        client = self.bot.client

        client.event(self.on_ready)
        client.event(self.on_guild_join)
        client.event(self.on_guild_remove)
        client.event(self.on_error)

        # Register command error handler
        client.tree.error(self.on_application_command_error)

        logger.info("Registered event handlers")
