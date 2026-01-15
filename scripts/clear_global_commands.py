#!/usr/bin/env python3
"""
Script to clear global Discord slash commands.
This removes duplicate commands that were registered globally.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import discord
from discord.ext import commands
from dotenv import load_dotenv


async def clear_global_commands():
    """Clear all global slash commands."""
    # Load environment
    load_dotenv()

    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("❌ DISCORD_TOKEN not found in environment")
        return False

    # Create minimal bot
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)
    tree = discord.app_commands.CommandTree(client)

    @client.event
    async def on_ready():
        print(f"✅ Logged in as {client.user}")
        print(f"📋 Clearing global commands...")

        try:
            # Clear all global commands
            tree.clear_commands(guild=None)
            synced = await tree.sync()

            print(f"✅ Cleared {len(synced)} global commands")
            print("✨ Global commands have been removed!")

        except Exception as e:
            print(f"❌ Error: {e}")

        finally:
            await client.close()

    # Start bot
    try:
        await client.start(token)
    except Exception as e:
        print(f"❌ Failed to start bot: {e}")
        return False

    return True


if __name__ == "__main__":
    print("=" * 60)
    print("Discord Global Command Cleaner")
    print("=" * 60)
    print()

    asyncio.run(clear_global_commands())

    print()
    print("=" * 60)
    print("Done! Discord will update commands within a few minutes.")
    print("=" * 60)
