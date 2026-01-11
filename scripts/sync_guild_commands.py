#!/usr/bin/env python3
"""
Script to force sync slash commands for a specific Discord guild.
This is useful when you add new commands and want them to appear immediately.

Usage:
    python scripts/sync_guild_commands.py <GUILD_ID>

Example:
    python scripts/sync_guild_commands.py 1234567890
"""

import asyncio
import sys
import os
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import ConfigManager
from src.discord_bot import SummaryBot

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def sync_guild_commands(guild_id: str):
    """
    Sync slash commands for a specific guild.

    Args:
        guild_id: The Discord guild (server) ID
    """
    try:
        logger.info(f"Starting guild command sync for guild ID: {guild_id}")

        # Load configuration
        config_manager = ConfigManager()
        config = await config_manager.load_config()

        # Create bot instance
        bot = SummaryBot(config)

        # Initialize services (minimal setup for command sync)
        bot.services = {}

        # Setup commands
        await bot.command_registry.setup_commands()
        logger.info(f"Registered {bot.command_registry.get_command_count()} commands")

        # List commands that will be synced
        command_names = bot.command_registry.get_command_names()
        logger.info(f"Commands to sync: {', '.join(command_names)}")

        # Connect to Discord (needed for sync)
        logger.info("Connecting to Discord...")

        @bot.client.event
        async def on_ready():
            logger.info(f"Bot connected as {bot.client.user}")

            # Perform guild-specific sync
            try:
                logger.info(f"Syncing commands for guild {guild_id}...")
                count = await bot.command_registry.sync_commands(guild_id=guild_id)
                logger.info(f"✅ Successfully synced {count} commands for guild {guild_id}")
                logger.info("Commands should appear in Discord within ~1 minute")

                # Close the bot
                await bot.client.close()

            except Exception as e:
                logger.error(f"❌ Failed to sync commands: {e}", exc_info=True)
                await bot.client.close()
                sys.exit(1)

        # Start the bot (will connect, sync, and disconnect)
        await bot.client.start(config.discord_token)

    except KeyboardInterrupt:
        logger.info("Sync cancelled by user")
    except Exception as e:
        logger.error(f"Error during sync: {e}", exc_info=True)
        sys.exit(1)


async def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/sync_guild_commands.py <GUILD_ID>")
        print()
        print("To find your guild ID:")
        print("1. Open Discord")
        print("2. Go to User Settings > Advanced")
        print("3. Enable 'Developer Mode'")
        print("4. Right-click your server name and select 'Copy ID'")
        sys.exit(1)

    guild_id = sys.argv[1]

    # Validate guild ID
    if not guild_id.isdigit():
        logger.error(f"Invalid guild ID: {guild_id} (must be numeric)")
        sys.exit(1)

    await sync_guild_commands(guild_id)


if __name__ == "__main__":
    asyncio.run(main())
