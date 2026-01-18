#!/usr/bin/env python3
"""
Migrate config.json to use new field names and defaults.
Run this on Fly.io to update the persisted configuration.
"""

import json
import sys
from pathlib import Path

CONFIG_PATH = "/app/data/config.json"

def migrate_config():
    """Migrate config.json to new format."""
    print(f"Loading config from {CONFIG_PATH}")

    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)

    migrated = False

    # Migrate guild configs
    for guild_id, guild_config in config.get('guild_configs', {}).items():
        summary_opts = guild_config.get('default_summary_options', {})

        # Check if old field exists
        if 'claude_model' in summary_opts:
            old_model = summary_opts['claude_model']
            print(f"  Guild {guild_id}: Migrating claude_model={old_model} -> summarization_model=openrouter/auto")

            # Add new field
            summary_opts['summarization_model'] = 'openrouter/auto'

            # Remove old field
            del summary_opts['claude_model']

            migrated = True
        elif 'summarization_model' in summary_opts:
            print(f"  Guild {guild_id}: Already migrated (summarization_model={summary_opts['summarization_model']})")
        else:
            print(f"  Guild {guild_id}: Adding summarization_model=openrouter/auto")
            summary_opts['summarization_model'] = 'openrouter/auto'
            migrated = True

    if migrated:
        # Backup original
        backup_path = CONFIG_PATH + '.backup'
        print(f"\nCreating backup at {backup_path}")
        with open(backup_path, 'w') as f:
            json.dump(config, f, indent=2)

        # Write updated config
        print(f"Writing updated config to {CONFIG_PATH}")
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=2)

        print("\n✅ Migration complete!")
        return 0
    else:
        print("\nNo migration needed - config is already up to date")
        return 0

if __name__ == '__main__':
    try:
        sys.exit(migrate_config())
    except Exception as e:
        print(f"\n❌ Migration failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
