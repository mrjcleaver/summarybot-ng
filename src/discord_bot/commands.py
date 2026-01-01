"""
Command registration and management for Discord slash commands.
"""

import logging
from typing import Optional, TYPE_CHECKING
import discord
from discord import app_commands

if TYPE_CHECKING:
    from .bot import SummaryBot

logger = logging.getLogger(__name__)


class CommandRegistry:
    """Manages Discord slash command registration and setup."""

    def __init__(self, bot: 'SummaryBot'):
        """
        Initialize the command registry.

        Args:
            bot: The SummaryBot instance
        """
        self.bot = bot
        self.tree = bot.client.tree
        self.command_handlers = {}  # Store command handler instances

    async def setup_commands(self) -> None:
        """
        Set up all slash commands for the bot.

        This method registers all command handlers with the command tree.
        """
        logger.info("Setting up slash commands...")

        # Register /summarize command
        @self.tree.command(
            name="summarize",
            description="Create an AI-powered summary of recent channel messages"
        )
        @discord.app_commands.describe(
            messages="Number of messages to summarize (default: 100)",
            hours="Summarize messages from the last N hours",
            minutes="Summarize messages from the last N minutes"
        )
        async def summarize_command(
            interaction: discord.Interaction,
            messages: Optional[int] = None,
            hours: Optional[int] = None,
            minutes: Optional[int] = None
        ):
            """Summarize recent channel messages."""
            # Defer response since summarization takes time
            await interaction.response.defer(ephemeral=False)

            try:
                # Get the command handler from bot services
                handler = self.bot.services.get('summarize_handler')
                if not handler:
                    await interaction.followup.send(
                        "❌ Summarization service is not available",
                        ephemeral=True
                    )
                    return

                # Call the handler's method
                await handler.handle_summarize_interaction(
                    interaction,
                    messages=messages,
                    hours=hours,
                    minutes=minutes
                )

            except Exception as e:
                logger.error(f"Error in summarize command: {e}", exc_info=True)
                try:
                    await interaction.followup.send(
                        f"❌ An error occurred: {str(e)}",
                        ephemeral=True
                    )
                except:
                    pass

        # Register help command
        @self.tree.command(
            name="help",
            description="Show help information about the bot and its commands"
        )
        async def help_command(interaction: discord.Interaction):
            """Display help information."""
            embed = discord.Embed(
                title="Summary Bot NG - Help",
                description="AI-powered conversation summarization for Discord",
                color=0x4A90E2
            )

            embed.add_field(
                name="/summarize",
                value="Create a summary of recent channel messages",
                inline=False
            )

            embed.add_field(
                name="/status",
                value="Check the bot's current status and health",
                inline=False
            )

            embed.add_field(
                name="/ping",
                value="Check the bot's response time",
                inline=False
            )

            embed.add_field(
                name="/about",
                value="Information about Summary Bot NG",
                inline=False
            )

            embed.set_footer(text="For detailed documentation, visit the project repository")

            await interaction.response.send_message(embed=embed, ephemeral=True)

        # Register about command
        @self.tree.command(
            name="about",
            description="Information about Summary Bot NG"
        )
        async def about_command(interaction: discord.Interaction):
            """Display information about the bot."""
            embed = discord.Embed(
                title="About Summary Bot NG",
                description=(
                    "An advanced Discord bot that uses Claude AI to create "
                    "intelligent summaries of channel conversations.\n\n"
                    "**Features:**\n"
                    "• AI-powered conversation summarization\n"
                    "• Action item extraction\n"
                    "• Technical term definitions\n"
                    "• Participant analysis\n"
                    "• Scheduled summaries\n"
                    "• Webhook integration\n"
                ),
                color=0x4A90E2
            )

            embed.add_field(
                name="Version",
                value="1.0.0",
                inline=True
            )

            embed.add_field(
                name="Powered by",
                value="Anthropic Claude",
                inline=True
            )

            embed.add_field(
                name="Servers",
                value=str(len(self.bot.client.guilds)),
                inline=True
            )

            embed.set_footer(text="Summary Bot NG - Open Source Project")

            await interaction.response.send_message(embed=embed, ephemeral=True)

        # Register status command
        @self.tree.command(
            name="status",
            description="Check the bot's current status and health"
        )
        async def status_command(interaction: discord.Interaction):
            """Display bot status information."""
            embed = discord.Embed(
                title="Bot Status",
                color=0x2ECC71  # Green
            )

            # Bot status
            embed.add_field(
                name="Status",
                value="🟢 Online",
                inline=True
            )

            # Latency
            latency_ms = round(self.bot.client.latency * 1000)
            latency_emoji = "🟢" if latency_ms < 100 else "🟡" if latency_ms < 300 else "🔴"
            embed.add_field(
                name="Latency",
                value=f"{latency_emoji} {latency_ms}ms",
                inline=True
            )

            # Guild count
            embed.add_field(
                name="Servers",
                value=str(len(self.bot.client.guilds)),
                inline=True
            )

            # TODO: Add more status information when other services are available
            # - Claude API status
            # - Database connection status
            # - Cache status

            embed.set_footer(text="All systems operational")

            await interaction.response.send_message(embed=embed, ephemeral=True)

        # Register ping command
        @self.tree.command(
            name="ping",
            description="Check the bot's response time"
        )
        async def ping_command(interaction: discord.Interaction):
            """Display bot latency."""
            latency_ms = round(self.bot.client.latency * 1000)

            embed = discord.Embed(
                title="🏓 Pong!",
                description=f"Bot latency: **{latency_ms}ms**",
                color=0x3498DB
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        logger.info("Slash commands setup complete")

    async def sync_commands(self, guild_id: Optional[str] = None) -> int:
        """
        Sync slash commands with Discord.

        Args:
            guild_id: Optional guild ID to sync commands for a specific guild.
                     If None, syncs globally.

        Returns:
            int: Number of commands synced
        """
        try:
            if guild_id:
                # Sync commands for a specific guild (faster)
                guild = discord.Object(id=int(guild_id))
                synced = await self.tree.sync(guild=guild)
                logger.info(f"Synced {len(synced)} commands for guild {guild_id}")
            else:
                # Global sync (slower, takes up to 1 hour to propagate)
                synced = await self.tree.sync()
                logger.info(f"Synced {len(synced)} commands globally")

            return len(synced)

        except discord.HTTPException as e:
            logger.error(f"Failed to sync commands: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error syncing commands: {e}", exc_info=True)
            raise

    async def clear_commands(self, guild_id: Optional[str] = None) -> None:
        """
        Clear all slash commands.

        Args:
            guild_id: Optional guild ID to clear commands for a specific guild.
                     If None, clears globally.
        """
        try:
            if guild_id:
                guild = discord.Object(id=int(guild_id))
                self.tree.clear_commands(guild=guild)
                await self.tree.sync(guild=guild)
                logger.info(f"Cleared commands for guild {guild_id}")
            else:
                self.tree.clear_commands(guild=None)
                await self.tree.sync()
                logger.info("Cleared global commands")

        except Exception as e:
            logger.error(f"Failed to clear commands: {e}", exc_info=True)
            raise

    def get_command_count(self) -> int:
        """
        Get the number of registered commands.

        Returns:
            int: Number of commands
        """
        return len(self.tree.get_commands())

    def get_command_names(self) -> list[str]:
        """
        Get a list of all registered command names.

        Returns:
            list[str]: List of command names
        """
        return [cmd.name for cmd in self.tree.get_commands()]
