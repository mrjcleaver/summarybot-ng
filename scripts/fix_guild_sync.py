#!/usr/bin/env python3
"""Fix guild sync by copying global commands to guild tree."""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import ConfigManager
from src.discord_bot import SummaryBot
import logging
import discord

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def fix_sync(guild_id: str):
    """Copy global commands to guild and sync."""
    config_manager = ConfigManager()
    config = await config_manager.load_config()

    bot = SummaryBot(config)
    bot.services = {}

    @bot.client.event
    async def on_ready():
        logger.info(f"Bot connected as {bot.client.user}")

        # Setup commands
        await bot.command_registry.setup_commands()
        logger.info(f"Setup {len(bot.client.tree.get_commands())} commands")

        guild_obj = discord.Object(id=int(guild_id))

        try:
            # Copy global commands to this guild
            logger.info(f"\nCopying commands to guild {guild_id}...")
            bot.client.tree.copy_global_to(guild=guild_obj)
            logger.info("✅ Commands copied to guild tree")

            # Now sync
            logger.info(f"Syncing to guild...")
            synced = await bot.client.tree.sync(guild=guild_obj)
            logger.info(f"✅ Successfully synced {len(synced)} commands!")

            for cmd in synced:
                logger.info(f"  - {cmd.name}")

            logger.info("\n🎉 Commands should now appear in Discord!")

        except Exception as e:
            logger.error(f"❌ Failed: {e}", exc_info=True)

        await bot.client.close()

    await bot.client.start(config.discord_token)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fix_guild_sync.py <GUILD_ID>")
        sys.exit(1)

    asyncio.run(fix_sync(sys.argv[1]))
