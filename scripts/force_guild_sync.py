#!/usr/bin/env python3
"""Force clear and resync commands for a guild."""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import ConfigManager
from src.discord_bot import SummaryBot
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def force_sync(guild_id: str):
    """Clear and resync commands."""
    config_manager = ConfigManager()
    config = await config_manager.load_config()

    bot = SummaryBot(config)
    bot.services = {}

    @bot.client.event
    async def on_ready():
        logger.info(f"Bot connected as {bot.client.user}")

        # Setup commands first
        await bot.command_registry.setup_commands()
        logger.info(f"Registered {bot.command_registry.get_command_count()} commands")
        logger.info(f"Commands: {', '.join(bot.command_registry.get_command_names())}")

        try:
            # Step 1: Clear existing commands for this guild
            logger.info(f"\nStep 1: Clearing existing commands for guild {guild_id}...")
            await bot.command_registry.clear_commands(guild_id=guild_id)
            logger.info("✅ Cleared old commands")

            # Step 2: Sync new commands
            logger.info(f"\nStep 2: Syncing new commands to guild {guild_id}...")
            count = await bot.command_registry.sync_commands(guild_id=guild_id)
            logger.info(f"✅ Synced {count} commands")

            logger.info("\n🎉 Commands should appear in Discord within ~1 minute")

        except Exception as e:
            logger.error(f"❌ Failed: {e}", exc_info=True)

        await bot.client.close()

    await bot.client.start(config.discord_token)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python force_guild_sync.py <GUILD_ID>")
        sys.exit(1)

    asyncio.run(force_sync(sys.argv[1]))
