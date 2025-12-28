"""
Main Discord bot client for Summary Bot NG.
"""

import logging
import asyncio
from typing import Optional
import discord
from discord.ext import commands

from ..config.settings import BotConfig
from ..exceptions.discord_errors import DiscordError
from .events import EventHandler
from .commands import CommandRegistry

logger = logging.getLogger(__name__)


class SummaryBot:
    """
    Main Discord bot class for Summary Bot NG.

    This class manages the Discord client connection, event handling,
    and command registration.
    """

    def __init__(self, config: BotConfig, services: Optional[dict] = None):
        """
        Initialize the Summary Bot.

        Args:
            config: Bot configuration
            services: Optional service container with dependencies
        """
        self.config = config
        self.services = services or {}

        # Configure intents
        intents = discord.Intents.default()
        intents.message_content = True  # Required for reading message content
        intents.guilds = True  # Required for guild events
        intents.members = True  # Optional: for member information

        # Initialize Discord client
        self.client = discord.Client(intents=intents)
        self.client.tree = discord.app_commands.CommandTree(self.client)

        # Initialize components
        self.event_handler = EventHandler(self)
        self.command_registry = CommandRegistry(self)

        # State tracking
        self._is_running = False
        self._ready_event = asyncio.Event()

        logger.info("Summary Bot initialized")

    async def start(self) -> None:
        """
        Start the Discord bot.

        This method:
        1. Registers event handlers
        2. Sets up slash commands
        3. Connects to Discord
        4. Starts the bot event loop

        Raises:
            DiscordError: If bot fails to start
        """
        if self._is_running:
            logger.warning("Bot is already running")
            return

        try:
            logger.info("Starting Summary Bot...")

            # Register event handlers
            self.event_handler.register_events()
            logger.info("Event handlers registered")

            # Setup slash commands
            await self.setup_commands()
            logger.info("Slash commands configured")

            # Start the bot
            self._is_running = True
            logger.info("Connecting to Discord...")

            # Run the bot (this blocks until the bot disconnects)
            await self.client.start(self.config.discord_token)

        except discord.LoginFailure as e:
            logger.error(f"Failed to login to Discord: {e}")
            raise DiscordError(
                message=f"Discord login failed: {e}",
                error_code="DISCORD_LOGIN_FAILED"
            )
        except Exception as e:
            logger.error(f"Failed to start bot: {e}", exc_info=True)
            self._is_running = False
            raise

    async def stop(self) -> None:
        """
        Stop the Discord bot gracefully.

        This method:
        1. Closes the Discord connection
        2. Cleans up resources
        3. Waits for pending operations to complete
        """
        if not self._is_running:
            logger.warning("Bot is not running")
            return

        try:
            logger.info("Stopping Summary Bot...")

            # Update status to show bot is shutting down
            await self.client.change_presence(
                status=discord.Status.idle,
                activity=discord.Activity(
                    type=discord.ActivityType.playing,
                    name="Shutting down..."
                )
            )

            # Close the client connection
            await self.client.close()

            # Wait a moment for cleanup
            await asyncio.sleep(1)

            self._is_running = False
            logger.info("Summary Bot stopped successfully")

        except Exception as e:
            logger.error(f"Error stopping bot: {e}", exc_info=True)
            raise

    async def setup_commands(self) -> None:
        """
        Set up all slash commands for the bot.

        This method registers all command handlers with the command tree.
        """
        await self.command_registry.setup_commands()
        logger.info(f"Registered {self.command_registry.get_command_count()} slash commands")

    async def sync_commands(self, guild_id: Optional[str] = None) -> None:
        """
        Sync slash commands with Discord.

        Args:
            guild_id: Optional guild ID to sync commands for a specific guild.
                     If None, syncs globally.

        Note:
            Global command sync can take up to 1 hour to propagate.
            Guild-specific sync is nearly instant.
        """
        try:
            count = await self.command_registry.sync_commands(guild_id)

            if guild_id:
                logger.info(f"Synced {count} commands for guild {guild_id}")
            else:
                logger.info(f"Synced {count} commands globally (may take up to 1 hour to propagate)")

        except Exception as e:
            logger.error(f"Failed to sync commands: {e}", exc_info=True)
            raise

    async def wait_until_ready(self, timeout: float = 30.0) -> None:
        """
        Wait until the bot is ready.

        Args:
            timeout: Maximum time to wait in seconds

        Raises:
            TimeoutError: If bot doesn't become ready within timeout
        """
        try:
            await asyncio.wait_for(
                self.client.wait_until_ready(),
                timeout=timeout
            )
            logger.info("Bot is ready")
        except asyncio.TimeoutError:
            logger.error(f"Bot did not become ready within {timeout} seconds")
            raise TimeoutError("Bot ready timeout")

    @property
    def is_ready(self) -> bool:
        """
        Check if the bot is ready and connected.

        Returns:
            bool: True if bot is ready, False otherwise
        """
        return self.client.is_ready()

    @property
    def is_running(self) -> bool:
        """
        Check if the bot is currently running.

        Returns:
            bool: True if bot is running, False otherwise
        """
        return self._is_running

    @property
    def user(self) -> Optional[discord.ClientUser]:
        """
        Get the bot's user object.

        Returns:
            Optional[discord.ClientUser]: Bot user or None if not logged in
        """
        return self.client.user

    @property
    def guilds(self) -> list[discord.Guild]:
        """
        Get list of guilds the bot is in.

        Returns:
            list[discord.Guild]: List of guilds
        """
        return self.client.guilds

    def get_guild(self, guild_id: int) -> Optional[discord.Guild]:
        """
        Get a guild by ID.

        Args:
            guild_id: Guild ID

        Returns:
            Optional[discord.Guild]: Guild object or None if not found
        """
        return self.client.get_guild(guild_id)

    def get_channel(self, channel_id: int) -> Optional[discord.abc.GuildChannel]:
        """
        Get a channel by ID.

        Args:
            channel_id: Channel ID

        Returns:
            Optional[discord.abc.GuildChannel]: Channel object or None if not found
        """
        return self.client.get_channel(channel_id)

    async def get_or_fetch_guild(self, guild_id: int) -> Optional[discord.Guild]:
        """
        Get a guild by ID, fetching from API if not in cache.

        Args:
            guild_id: Guild ID

        Returns:
            Optional[discord.Guild]: Guild object or None if not found
        """
        guild = self.get_guild(guild_id)
        if guild:
            return guild

        try:
            return await self.client.fetch_guild(guild_id)
        except discord.NotFound:
            return None
        except Exception as e:
            logger.error(f"Failed to fetch guild {guild_id}: {e}")
            return None

    async def get_or_fetch_channel(
        self,
        channel_id: int
    ) -> Optional[discord.abc.GuildChannel]:
        """
        Get a channel by ID, fetching from API if not in cache.

        Args:
            channel_id: Channel ID

        Returns:
            Optional[discord.abc.GuildChannel]: Channel object or None if not found
        """
        channel = self.get_channel(channel_id)
        if channel:
            return channel

        try:
            return await self.client.fetch_channel(channel_id)
        except discord.NotFound:
            return None
        except Exception as e:
            logger.error(f"Failed to fetch channel {channel_id}: {e}")
            return None

    def __repr__(self) -> str:
        """String representation of the bot."""
        status = "running" if self._is_running else "stopped"
        user = self.client.user.name if self.client.user else "Not logged in"
        return f"<SummaryBot user={user} status={status} guilds={len(self.guilds)}>"
