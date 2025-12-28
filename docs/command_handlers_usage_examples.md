# Command Handlers Usage Examples

## Overview

This document provides practical examples of how to use the command handlers module in Summary Bot NG.

## Basic Setup

```python
from src.command_handlers import (
    SummarizeCommandHandler,
    ConfigCommandHandler,
    ScheduleCommandHandler
)
from src.summarization import SummarizationEngine
from src.permissions import PermissionManager
from src.config import ConfigManager
from src.scheduling import TaskScheduler
from src.message_processing import MessageFetcher, MessageFilter, MessageCleaner

# Initialize dependencies
config_manager = ConfigManager()
permission_manager = PermissionManager(config)
summarization_engine = SummarizationEngine(claude_client, cache)
task_scheduler = TaskScheduler(summarization_engine, message_processor)
message_fetcher = MessageFetcher(discord_client)
message_filter = MessageFilter()
message_cleaner = MessageCleaner()

# Create command handlers
summarize_handler = SummarizeCommandHandler(
    summarization_engine=summarization_engine,
    permission_manager=permission_manager,
    message_fetcher=message_fetcher,
    message_filter=message_filter,
    message_cleaner=message_cleaner
)

config_handler = ConfigCommandHandler(
    summarization_engine=summarization_engine,
    permission_manager=permission_manager,
    config_manager=config_manager
)

schedule_handler = ScheduleCommandHandler(
    summarization_engine=summarization_engine,
    permission_manager=permission_manager,
    task_scheduler=task_scheduler
)
```

## Command Registration

### Discord.py Bot Commands

```python
import discord
from discord import app_commands

class SummaryBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        super().__init__(command_prefix="!", intents=intents)

        # Setup command handlers
        self.setup_handlers()

    def setup_handlers(self):
        # Create handlers
        self.summarize_handler = SummarizeCommandHandler(...)
        self.config_handler = ConfigCommandHandler(...)
        self.schedule_handler = ScheduleCommandHandler(...)

        # Register commands
        self.tree.command(name="summarize")(self.cmd_summarize)
        self.tree.command(name="quick-summary")(self.cmd_quick_summary)
        self.tree.command(name="config")(self.cmd_config)
        self.tree.command(name="schedule")(self.cmd_schedule)

    @app_commands.command(name="summarize", description="Generate a summary of messages")
    @app_commands.describe(
        channel="Channel to summarize (defaults to current)",
        hours="Hours to look back (default: 24)",
        length="Summary length: brief, detailed, or comprehensive",
        include_bots="Include bot messages in summary"
    )
    async def cmd_summarize(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel = None,
        hours: int = 24,
        length: str = "detailed",
        include_bots: bool = False
    ):
        await self.summarize_handler.handle_summarize(
            interaction=interaction,
            channel=channel,
            hours=hours,
            length=length,
            include_bots=include_bots
        )

    @app_commands.command(name="quick-summary", description="Quick summary of recent messages")
    @app_commands.describe(minutes="Minutes to look back (5-1440)")
    async def cmd_quick_summary(
        self,
        interaction: discord.Interaction,
        minutes: int = 60
    ):
        await self.summarize_handler.handle_quick_summary(
            interaction=interaction,
            minutes=minutes
        )
```

## Usage Examples

### 1. Basic Summarization

```python
# User runs: /summarize
# Result: Summarizes last 24 hours in current channel

@app_commands.command(name="summarize")
async def cmd_summarize(interaction: discord.Interaction):
    await summarize_handler.handle_summarize(interaction)
```

**Expected Output:**
```
✅ Summary Generated

Channel: #general
Time Range: 2024-01-15 10:00 to 2024-01-16 10:00
Messages: 150

📝 Key Points:
• Discussion about new feature implementation
• Bug fixes for authentication system
• Planning for upcoming sprint

⚡ Action Items:
🔴 Fix critical bug in login flow
🟡 Review pull request #123
🟢 Update documentation

👥 Participants:
• Alice (45 messages)
• Bob (32 messages)
• Charlie (28 messages)
```

### 2. Custom Time Range

```python
# User runs: /summarize hours:48 length:brief
# Result: Brief summary of last 48 hours

await summarize_handler.handle_summarize(
    interaction=interaction,
    hours=48,
    length="brief"
)
```

### 3. Specific Channel

```python
# User runs: /summarize channel:#dev-team length:comprehensive
# Result: Comprehensive summary of #dev-team

await summarize_handler.handle_summarize(
    interaction=interaction,
    channel=dev_channel,
    length="comprehensive"
)
```

### 4. Quick Summary

```python
# User runs: /quick-summary minutes:30
# Result: Brief summary of last 30 minutes

await summarize_handler.handle_quick_summary(
    interaction=interaction,
    minutes=30
)
```

### 5. Cost Estimation

```python
# User runs: /estimate-cost channel:#general hours:24
# Result: Shows estimated API cost

await summarize_handler.estimate_summary_cost(
    interaction=interaction,
    channel=general_channel,
    hours=24
)
```

**Expected Output:**
```
💰 Summary Cost Estimate

Messages: 150
Estimated Cost: $0.0234 USD
Input Tokens: 45,000
Output Tokens: 2,000
Model: claude-3-sonnet-20240229
```

## Configuration Management

### 1. View Configuration

```python
# User runs: /config view
# Result: Displays current guild settings

@app_commands.command(name="config")
async def cmd_config(interaction: discord.Interaction, action: str):
    if action == "view":
        await config_handler.handle_config_view(interaction)
```

**Expected Output:**
```
⚙️ Current Configuration
Settings for My Server

📝 Enabled Channels
#general
#dev-team
#announcements

🎯 Default Summary Options
Length: detailed
Include bots: false
Min messages: 5
Model: claude-3-sonnet-20240229
```

### 2. Set Enabled Channels

```python
# User runs: /config set-channels action:enable channels:#general,#dev
# Result: Updates enabled channels

await config_handler.handle_config_set_channels(
    interaction=interaction,
    action="enable",
    channels="#general,#dev-team"
)
```

### 3. Set Default Options

```python
# User runs: /config defaults length:brief include_bots:true
# Result: Updates default summary options

await config_handler.handle_config_set_defaults(
    interaction=interaction,
    length="brief",
    include_bots=True,
    min_messages=10
)
```

### 4. Reset Configuration

```python
# User runs: /config reset
# Result: Resets all settings to defaults

await config_handler.handle_config_reset(interaction)
```

## Scheduled Summaries

### 1. Create Schedule

```python
# User runs: /schedule create channel:#general frequency:daily time:09:00
# Result: Creates daily summary at 9 AM UTC

@app_commands.command(name="schedule")
async def cmd_schedule(
    interaction: discord.Interaction,
    action: str,
    channel: discord.TextChannel = None,
    frequency: str = "daily",
    time_of_day: str = None
):
    if action == "create":
        await schedule_handler.handle_schedule_create(
            interaction=interaction,
            channel=channel,
            frequency=frequency,
            time_of_day=time_of_day
        )
```

**Expected Output:**
```
✅ Scheduled Summary Created

Automatic summaries will be posted to #general

Schedule: Daily at 09:00 UTC
Length: Detailed
Task ID: sched_abc123xyz
Status: Active

Use /schedule list to view all scheduled summaries
```

### 2. List Schedules

```python
# User runs: /schedule list
# Result: Shows all scheduled summaries

await schedule_handler.handle_schedule_list(interaction)
```

**Expected Output:**
```
📅 Scheduled Summaries
Active summaries for My Server

#1
✅ Status: Active
📝 Channel: #general
🔄 Schedule: Daily at 09:00 UTC
📏 Length: detailed
🆔 ID: sched_abc123xyz

#2
⏸️ Status: Paused
📝 Channel: #dev-team
🔄 Schedule: Weekly at 14:00 UTC
📏 Length: comprehensive
🆔 ID: sched_def456uvw
```

### 3. Pause/Resume Schedule

```python
# User runs: /schedule pause task_id:sched_abc123xyz
await schedule_handler.handle_schedule_pause(
    interaction=interaction,
    task_id="sched_abc123xyz"
)

# User runs: /schedule resume task_id:sched_abc123xyz
await schedule_handler.handle_schedule_resume(
    interaction=interaction,
    task_id="sched_abc123xyz"
)
```

### 4. Delete Schedule

```python
# User runs: /schedule delete task_id:sched_abc123xyz
await schedule_handler.handle_schedule_delete(
    interaction=interaction,
    task_id="sched_abc123xyz"
)
```

## Error Handling Examples

### 1. User Input Error

```python
# User runs: /summarize hours:200
# Result: Error - time range too large

# Handler automatically catches and formats:
try:
    validate_time_range(start_time, end_time, max_hours=168)
except UserError as e:
    await send_error_response(interaction, e)
```

**Expected Output:**
```
❌ Error

Time range cannot exceed 168 hours. Please choose a shorter time period.

Error Code: TIME_RANGE_TOO_LARGE
```

### 2. Permission Error

```python
# Non-admin user runs: /config set-channels
# Result: Permission denied

# Handler checks permissions automatically
if not await _check_admin_permission(interaction):
    await send_permission_error(interaction)
```

**Expected Output:**
```
🔒 Permission Denied

You don't have permission to use this command.

Need Help?
Contact a server administrator if you believe this is an error.
```

### 3. Rate Limit Error

```python
# User sends too many commands
# Result: Rate limit exceeded

# Handler tracks requests automatically
allowed, reset_time = rate_limiter.check_rate_limit(user_id)
if not allowed:
    await send_rate_limit_response(interaction, reset_time)
```

**Expected Output:**
```
⏱️ Rate Limit Exceeded

You're sending commands too quickly. Please wait 45 seconds before trying again.

Rate Limit
5 requests per 60 seconds
```

### 4. Insufficient Content

```python
# User tries to summarize channel with 2 messages
# Result: Not enough content

if len(processed_messages) < min_messages:
    raise InsufficientContentError(
        message_count=len(processed_messages),
        min_required=min_messages
    )
```

**Expected Output:**
```
❌ Error

Not enough messages to summarize. Found 2, need at least 5.

Error Code: INSUFFICIENT_CONTENT
```

## Utility Function Examples

### Time String Parsing

```python
from src.command_handlers.utils import parse_time_string

# Relative formats
parse_time_string("1h")          # 1 hour ago
parse_time_string("30m")         # 30 minutes ago
parse_time_string("2d")          # 2 days ago
parse_time_string("1w")          # 1 week ago

# "Ago" format
parse_time_string("2 hours ago")
parse_time_string("30 minutes ago")

# Keywords
parse_time_string("yesterday")
parse_time_string("last week")
parse_time_string("today")

# ISO format
parse_time_string("2024-01-15T10:30:00")
```

### Duration Formatting

```python
from src.command_handlers.utils import format_duration

format_duration(45)       # "45s"
format_duration(150)      # "2m 30s"
format_duration(3665)     # "1h 1m"
format_duration(90000)    # "1d 1h"
```

### Progress Bar

```python
from src.command_handlers.utils import create_progress_bar

create_progress_bar(40, 100)  # "[████░░░░░░] 40%"
create_progress_bar(75, 100)  # "[███████░░░] 75%"
create_progress_bar(100, 100) # "[██████████] 100%"
```

## Advanced Patterns

### Custom Error Handling

```python
class CustomCommandHandler(BaseCommandHandler):
    async def _execute_command(self, interaction, **kwargs):
        try:
            # Your command logic
            result = await self.process_command(kwargs)

            # Custom success response
            embed = discord.Embed(
                title="✅ Success",
                description="Operation completed",
                color=0x00FF00
            )
            await interaction.followup.send(embed=embed)

        except CustomError as e:
            # Custom error handling
            await self.send_custom_error(interaction, e)
```

### Rate Limit Customization

```python
class SlowCommandHandler(BaseCommandHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Custom rate limits
        self.max_requests_per_minute = 1  # Only 1 request per minute
        self.rate_limit_window = 60
```

### Permission Bypass

```python
# For testing or admin commands
handler = SummarizeCommandHandler(
    summarization_engine=engine,
    permission_manager=None,  # No permission checks
    rate_limit_enabled=False  # No rate limiting
)
```

## Testing Examples

### Unit Test

```python
import pytest
from unittest.mock import Mock, AsyncMock

@pytest.mark.asyncio
async def test_summarize_handler():
    # Mock dependencies
    engine = Mock()
    permission_manager = Mock()

    # Create handler
    handler = SummarizeCommandHandler(
        summarization_engine=engine,
        permission_manager=permission_manager
    )

    # Mock interaction
    interaction = Mock(spec=discord.Interaction)
    interaction.user.id = "12345"
    interaction.guild_id = "67890"

    # Test
    await handler.handle_summarize(interaction)

    # Verify
    engine.summarize_messages.assert_called_once()
```

### Integration Test

```python
@pytest.mark.asyncio
async def test_full_summarize_workflow():
    # Setup real components
    config = load_test_config()
    engine = SummarizationEngine(test_claude_client, test_cache)
    permission_manager = PermissionManager(config)

    # Create handler
    handler = SummarizeCommandHandler(
        summarization_engine=engine,
        permission_manager=permission_manager
    )

    # Test with real Discord interaction
    # (requires Discord bot token and test server)
    async with discord_test_server() as server:
        interaction = await server.create_interaction("/summarize")
        await handler.handle_summarize(interaction)

        # Verify summary was created
        assert interaction.followup.send.called
```

## Conclusion

The command handlers module provides a robust, user-friendly interface for Discord slash commands with:

- **Comprehensive error handling**
- **Rate limiting protection**
- **Permission validation**
- **Rich Discord embeds**
- **Flexible configuration**
- **Extensible architecture**

All handlers follow consistent patterns and best practices, making the codebase maintainable and easy to extend.
