#!/usr/bin/env python3
"""
Script to list all scheduled tasks from the database.
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path

# Database path
DB_PATH = Path(__file__).parent.parent / "data" / "summarybot.db"


def list_all_tasks():
    """List all scheduled tasks."""
    if not DB_PATH.exists():
        print(f"❌ Database not found at: {DB_PATH}")
        return

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get all tasks
    cursor.execute("""
        SELECT
            id, name, channel_id, guild_id, schedule_type,
            schedule_time, is_active, created_at, next_run,
            last_run, run_count, destinations, summary_options
        FROM scheduled_tasks
        ORDER BY created_at DESC
    """)

    tasks = cursor.fetchall()

    if not tasks:
        print("📭 No scheduled tasks found.")
        return

    print(f"📋 Found {len(tasks)} scheduled task(s):\n")
    print("=" * 80)

    for i, task in enumerate(tasks, 1):
        status = "✅ Active" if task['is_active'] else "⏸️  Paused"

        # Parse destinations
        try:
            destinations = json.loads(task['destinations'])
            dest_count = len(destinations)
            dest_summary = f"{dest_count} destination(s)"
        except:
            dest_summary = "Unknown"

        # Parse summary options
        try:
            options = json.loads(task['summary_options'])
            length = options.get('summary_length', 'unknown')
        except:
            length = "unknown"

        print(f"\n{i}. Task: {task['name'] or '(unnamed)'}")
        print(f"   ID: {task['id']}")
        print(f"   Status: {status}")
        print(f"   Channel ID: {task['channel_id']}")
        print(f"   Guild ID: {task['guild_id']}")
        print(f"   Schedule: {task['schedule_type']} at {task['schedule_time'] or 'default time'}")
        print(f"   Summary Length: {length}")
        print(f"   Destinations: {dest_summary}")
        print(f"   Created: {task['created_at']}")
        print(f"   Next Run: {task['next_run'] or 'Not scheduled'}")
        print(f"   Last Run: {task['last_run'] or 'Never'}")
        print(f"   Run Count: {task['run_count']}")
        print("   " + "-" * 76)

    conn.close()
    print("\n" + "=" * 80)


def list_active_tasks():
    """List only active tasks."""
    if not DB_PATH.exists():
        print(f"❌ Database not found at: {DB_PATH}")
        return

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get active tasks only
    cursor.execute("""
        SELECT
            id, name, channel_id, schedule_type,
            schedule_time, next_run, run_count
        FROM scheduled_tasks
        WHERE is_active = 1
        ORDER BY next_run ASC
    """)

    tasks = cursor.fetchall()

    if not tasks:
        print("📭 No active scheduled tasks found.")
        return

    print(f"✅ Found {len(tasks)} active scheduled task(s):\n")

    for i, task in enumerate(tasks, 1):
        print(f"{i}. {task['name'] or task['id'][:8]}")
        print(f"   Channel: {task['channel_id']}")
        print(f"   Schedule: {task['schedule_type']} at {task['schedule_time'] or 'default'}")
        print(f"   Next Run: {task['next_run'] or 'Not scheduled'}")
        print(f"   Executions: {task['run_count']}")
        print()

    conn.close()


def get_task_details(task_id):
    """Get detailed information about a specific task."""
    if not DB_PATH.exists():
        print(f"❌ Database not found at: {DB_PATH}")
        return

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM scheduled_tasks WHERE id = ?", (task_id,))
    task = cursor.fetchone()

    if not task:
        print(f"❌ Task not found: {task_id}")
        return

    print(f"📋 Task Details for: {task['id']}\n")
    print("=" * 80)

    for key in task.keys():
        value = task[key]

        # Pretty print JSON fields
        if key in ['destinations', 'summary_options', 'metadata'] and value:
            try:
                parsed = json.loads(value)
                value = json.dumps(parsed, indent=2)
            except:
                pass

        print(f"{key}: {value}")

    # Get recent execution results
    cursor.execute("""
        SELECT status, started_at, execution_time_seconds, error_message
        FROM task_results
        WHERE task_id = ?
        ORDER BY started_at DESC
        LIMIT 5
    """, (task_id,))

    results = cursor.fetchall()

    if results:
        print("\n" + "=" * 80)
        print(f"Recent Executions (last {len(results)}):\n")

        for i, result in enumerate(results, 1):
            status_icon = "✅" if result['status'] == 'completed' else "❌"
            print(f"{i}. {status_icon} {result['status']} - {result['started_at']}")
            print(f"   Duration: {result['execution_time_seconds']}s")
            if result['error_message']:
                print(f"   Error: {result['error_message']}")
            print()

    conn.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "all":
            list_all_tasks()
        elif command == "active":
            list_active_tasks()
        elif command == "details" and len(sys.argv) > 2:
            get_task_details(sys.argv[2])
        else:
            print("Usage:")
            print("  python list_scheduled_tasks.py all        # List all tasks")
            print("  python list_scheduled_tasks.py active     # List active tasks only")
            print("  python list_scheduled_tasks.py details <task_id>  # Get task details")
    else:
        # Default: list active tasks
        list_active_tasks()
