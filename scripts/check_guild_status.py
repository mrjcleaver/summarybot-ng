#!/usr/bin/env python3
"""Check if bot is in a guild and has proper permissions."""

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


async def check_guild(guild_id: str):
    """Check guild status."""
    config_manager = ConfigManager()
    config = await config_manager.load_config()

    bot = SummaryBot(config)
    bot.services = {}

    @bot.client.event
    async def on_ready():
        logger.info(f"Bot connected as {bot.client.user}")
        logger.info(f"Bot is in {len(bot.client.guilds)} guilds:")

        target_guild = None
        for guild in bot.client.guilds:
            is_target = "**TARGET**" if str(guild.id) == guild_id else ""
            logger.info(f"  - {guild.name} (ID: {guild.id}) {is_target}")
            if str(guild.id) == guild_id:
                target_guild = guild

        if target_guild:
            logger.info(f"\n✅ Bot IS in guild {guild_id} ({target_guild.name})")
            logger.info(f"Bot permissions in this guild:")
            me = target_guild.me
            perms = me.guild_permissions
            logger.info(f"  - Administrator: {perms.administrator}")
            logger.info(f"  - Manage Guild: {perms.manage_guild}")
            logger.info(f"  - Use Application Commands: {perms.use_application_commands}")
            logger.info(f"  - Send Messages: {perms.send_messages}")
            logger.info(f"  - Read Message History: {perms.read_message_history}")
        else:
            logger.error(f"\n❌ Bot is NOT in guild {guild_id}")
            logger.error("The bot needs to be added to this server first!")

        await bot.client.close()

    await bot.client.start(config.discord_token)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_guild_status.py <GUILD_ID>")
        sys.exit(1)

    asyncio.run(check_guild(sys.argv[1]))
