#!/usr/bin/env python3
"""Debug command sync issues."""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import ConfigManager
from src.discord_bot import SummaryBot
import logging
import discord

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def debug_sync(guild_id: str):
    """Debug sync process."""
    config_manager = ConfigManager()
    config = await config_manager.load_config()

    bot = SummaryBot(config)
    bot.services = {}

    @bot.client.event
    async def on_ready():
        logger.info(f"Bot connected as {bot.client.user}")

        # Setup commands
        await bot.command_registry.setup_commands()

        # Debug: Check what's in the tree
        logger.info("\n=== TREE CONTENTS ===")
        logger.info(f"Tree command count: {len(bot.client.tree.get_commands())}")
        for cmd in bot.client.tree.get_commands():
            logger.info(f"  - {cmd.name} (type: {type(cmd).__name__})")
            if isinstance(cmd, discord.app_commands.Group):
                logger.info(f"    Group has {len(cmd.commands)} subcommands:")
                for subcmd in cmd.commands:
                    logger.info(f"      - {subcmd.name}")

        # Try syncing with more detail
        guild_obj = discord.Object(id=int(guild_id))

        logger.info(f"\n=== ATTEMPTING SYNC TO GUILD {guild_id} ===")
        try:
            # Get current commands in guild
            existing = await bot.client.tree.fetch_commands(guild=guild_obj)
            logger.info(f"Existing commands in guild: {len(existing)}")
            for cmd in existing:
                logger.info(f"  - {cmd.name}")

            # Sync
            synced = await bot.client.tree.sync(guild=guild_obj)
            logger.info(f"\n✅ Sync returned {len(synced)} commands")
            for cmd in synced:
                logger.info(f"  - {cmd.name} (ID: {cmd.id})")

        except discord.HTTPException as e:
            logger.error(f"❌ HTTP Error: {e.status} - {e.text}")
        except Exception as e:
            logger.error(f"❌ Error: {e}", exc_info=True)

        await bot.client.close()

    await bot.client.start(config.discord_token)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_sync.py <GUILD_ID>")
        sys.exit(1)

    asyncio.run(debug_sync(sys.argv[1]))
