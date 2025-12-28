# Command Handlers Module Documentation

## Overview

The `command_handlers` module provides Discord slash command handling with built-in error handling, rate limiting, permission management, and user-friendly response formatting.

## Module Structure

```
src/command_handlers/
├── __init__.py          # Public interface exports
├── base.py              # BaseCommandHandler abstract class
├── summarize.py         # Summarization command handlers
├── config.py            # Configuration command handlers
├── schedule.py          # Scheduling command handlers
└── utils.py             # Utility functions for commands
```

## Components

### 1. Base Command Handler (`base.py`)

#### `BaseCommandHandler`

Abstract base class providing common functionality for all command handlers.

**Features:**
- Built-in rate limiting with configurable limits
- Permission checking integration
- Automatic error handling and user-friendly responses
- Response deferral for long-running operations
- Structured logging

**Key Methods:**

```python
async def handle_command(interaction: discord.Interaction, **kwargs) -> None
    """Main entry point with error handling and rate limiting."""

async def _execute_command(interaction: discord.Interaction, **kwargs) -> None
    """Abstract method - implement command logic here."""

async def defer_response(interaction: discord.Interaction, ephemeral: bool = False) -> None
    """Defer response for operations taking >3 seconds."""

async def send_error_response(interaction: discord.Interaction, error: Exception) -> None
    """Send formatted error embed to user."""

async def send_success_response(interaction: discord.Interaction, title: str, description: str, ...) -> None
    """Send formatted success embed to user."""
```

**Usage Example:**

```python
class MyCommandHandler(BaseCommandHandler):
    async def _execute_command(self, interaction: discord.Interaction, **kwargs) -> None:
        # Your command logic here
        await self.defer_response(interaction)
        result = await self.do_something()
        await self.send_success_response(
            interaction,
            "Success",
            "Operation completed successfully!"
        )

# In your bot setup
handler = MyCommandHandler(
    summarization_engine=engine,
    permission_manager=permissions,
    rate_limit_enabled=True
)

@bot.slash_command(name="mycommand")
async def my_command(interaction: discord.Interaction):
    await handler.handle_command(interaction)
```

#### `RateLimitTracker`

Simple in-memory rate limit tracking.

```python
tracker = RateLimitTracker()
allowed, reset_time = tracker.check_rate_limit(
    user_id="123456789",
    max_requests=5,
    window_seconds=60
)
```

### 2. Summarize Command Handler (`summarize.py`)

#### `SummarizeCommandHandler`

Handles all summarization-related commands.

**Commands Supported:**

1. **Full Summarize** - Customizable summary with all options
2. **Quick Summary** - Fast summary of recent messages
3. **Scheduled Summary** - Setup automated summaries
4. **Cost Estimation** - Estimate API cost before summarizing

**Key Methods:**

```python
async def handle_summarize(
    interaction: discord.Interaction,
    channel: Optional[discord.TextChannel] = None,
    hours: int = 24,
    length: str = "detailed",
    include_bots: bool = False,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None
) -> None
    """Generate a full customizable summary."""

async def handle_quick_summary(
    interaction: discord.Interaction,
    minutes: int = 60
) -> None
    """Quick summary of recent messages."""

async def estimate_summary_cost(
    interaction: discord.Interaction,
    channel: Optional[discord.TextChannel] = None,
    hours: int = 24
) -> None
    """Estimate cost before generating summary."""
```

**Example Discord Integration:**

```python
summarize_handler = SummarizeCommandHandler(
    summarization_engine=engine,
    permission_manager=permissions,
    message_fetcher=fetcher,
    message_filter=filter_,
    message_cleaner=cleaner
)

@bot.slash_command(name="summarize", description="Generate a channel summary")
async def summarize(
    interaction: discord.Interaction,
    channel: discord.TextChannel = None,
    hours: int = 24,
    length: str = "detailed"
):
    await summarize_handler.handle_summarize(
        interaction=interaction,
        channel=channel,
        hours=hours,
        length=length
    )
```

### 3. Config Command Handler (`config.py`)

#### `ConfigCommandHandler`

Manages bot configuration for guilds.

**Features:**
- View current guild configuration
- Enable/exclude channels for summaries
- Set default summary options
- Reset configuration to defaults

**Key Methods:**

```python
async def handle_config_view(interaction: discord.Interaction) -> None
    """Display current configuration."""

async def handle_config_set_channels(
    interaction: discord.Interaction,
    action: str,  # "enable" or "exclude"
    channels: str  # Comma-separated channel mentions/IDs
) -> None
    """Configure enabled/excluded channels."""

async def handle_config_set_defaults(
    interaction: discord.Interaction,
    length: Optional[str] = None,
    include_bots: Optional[bool] = None,
    min_messages: Optional[int] = None,
    model: Optional[str] = None
) -> None
    """Set default summary options."""

async def handle_config_reset(interaction: discord.Interaction) -> None
    """Reset configuration to defaults."""
```

**Permission Requirements:**
- All config commands require `Administrator` or `Manage Guild` permissions

### 4. Schedule Command Handler (`schedule.py`)

#### `ScheduleCommandHandler`

Manages automated scheduled summaries.

**Features:**
- Create scheduled summaries (hourly, daily, weekly, monthly)
- List all scheduled summaries
- Pause/resume schedules
- Delete schedules

**Key Methods:**

```python
async def handle_schedule_create(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    frequency: str,  # "hourly", "daily", "weekly", "monthly"
    time_of_day: Optional[str] = None,  # "HH:MM" format
    length: str = "detailed"
) -> None
    """Create a new scheduled summary."""

async def handle_schedule_list(interaction: discord.Interaction) -> None
    """List all scheduled summaries for the guild."""

async def handle_schedule_delete(
    interaction: discord.Interaction,
    task_id: str
) -> None
    """Delete a scheduled summary."""

async def handle_schedule_pause(
    interaction: discord.Interaction,
    task_id: str
) -> None
    """Pause a scheduled summary."""

async def handle_schedule_resume(
    interaction: discord.Interaction,
    task_id: str
) -> None
    """Resume a paused scheduled summary."""
```

### 5. Utility Functions (`utils.py`)

#### Response Formatting

```python
def format_error_response(error_message: str, error_code: str = "ERROR") -> discord.Embed
def format_success_response(title: str, description: str, fields: Optional[Dict[str, str]] = None) -> discord.Embed
def format_info_response(title: str, description: str, fields: Optional[Dict[str, str]] = None) -> discord.Embed
```

#### Time Parsing

```python
def parse_time_string(time_str: str) -> datetime
    """
    Parse flexible time strings:
    - "1h", "30m", "2d", "1w"
    - "2 hours ago", "yesterday"
    - ISO format: "2024-01-15T10:30:00"
    """

def validate_time_range(start_time: datetime, end_time: datetime, max_hours: int = 168) -> None
    """Validate time range is reasonable."""
```

#### Text Utilities

```python
def format_duration(seconds: float) -> str
    """Format duration to human-readable string (e.g., "2h 30m")."""

def truncate_text(text: str, max_length: int = 1024, suffix: str = "...") -> str
    """Truncate text to fit Discord field limits."""

def extract_channel_id(channel_mention: str) -> Optional[str]
    """Extract channel ID from mention string."""

def create_progress_bar(current: int, total: int, length: int = 10) -> str
    """Create text-based progress bar."""
```

## Error Handling

All command handlers automatically handle errors and convert them to user-friendly responses:

### Error Types

1. **UserError** - Errors caused by user input
   - Invalid time ranges
   - Invalid channel mentions
   - Missing parameters

2. **PermissionError** - User lacks required permissions
   - Automatic permission check before command execution
   - Clear permission denied message

3. **RateLimitError** - User exceeded rate limits
   - Shows time until reset
   - Displays rate limit rules

4. **SummarizationError** - Errors during summary generation
   - Insufficient content
   - API failures
   - Processing errors

### Error Response Format

All errors are formatted as Discord embeds with:
- ❌ Title indicating error
- Clear description of what went wrong
- Error code for debugging
- Retry hint if error is retryable

## Rate Limiting

Built-in rate limiting prevents spam and abuse:

### Default Limits

- **Summarize Commands**: 3 requests per 60 seconds
- **Config Commands**: 5 requests per 60 seconds
- **Schedule Commands**: 5 requests per 60 seconds

### Customization

```python
handler = SummarizeCommandHandler(...)
handler.max_requests_per_minute = 10
handler.rate_limit_window = 120  # 2 minutes
```

### Disable Rate Limiting

```python
handler = BaseCommandHandler(
    summarization_engine=engine,
    rate_limit_enabled=False
)
```

## Integration Example

Complete example of integrating all command handlers:

```python
import discord
from discord import app_commands

from src.command_handlers import (
    SummarizeCommandHandler,
    ConfigCommandHandler,
    ScheduleCommandHandler
)
from src.summarization import SummarizationEngine
from src.permissions import PermissionManager

# Initialize services
engine = SummarizationEngine(...)
permissions = PermissionManager(...)

# Initialize handlers
summarize_handler = SummarizeCommandHandler(
    summarization_engine=engine,
    permission_manager=permissions
)

config_handler = ConfigCommandHandler(
    summarization_engine=engine,
    permission_manager=permissions
)

schedule_handler = ScheduleCommandHandler(
    summarization_engine=engine,
    permission_manager=permissions
)

# Register commands
class SummaryBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # Summarize command
        @self.tree.command(name="summarize", description="Generate a channel summary")
        async def summarize(
            interaction: discord.Interaction,
            channel: discord.TextChannel = None,
            hours: int = 24,
            length: str = "detailed"
        ):
            await summarize_handler.handle_summarize(
                interaction=interaction,
                channel=channel,
                hours=hours,
                length=length
            )

        # Quick summary command
        @self.tree.command(name="quick", description="Quick summary of recent messages")
        async def quick_summary(interaction: discord.Interaction, minutes: int = 60):
            await summarize_handler.handle_quick_summary(
                interaction=interaction,
                minutes=minutes
            )

        # Config commands group
        config_group = app_commands.Group(name="config", description="Bot configuration")

        @config_group.command(name="view", description="View current configuration")
        async def config_view(interaction: discord.Interaction):
            await config_handler.handle_config_view(interaction)

        @config_group.command(name="channels", description="Configure channels")
        async def config_channels(
            interaction: discord.Interaction,
            action: str,
            channels: str
        ):
            await config_handler.handle_config_set_channels(
                interaction=interaction,
                action=action,
                channels=channels
            )

        self.tree.add_command(config_group)

        # Sync commands
        await self.tree.sync()

# Run bot
bot = SummaryBot()
bot.run(TOKEN)
```

## Testing

### Unit Testing

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.command_handlers import SummarizeCommandHandler

@pytest.mark.asyncio
async def test_summarize_command():
    # Mock dependencies
    engine = MagicMock()
    engine.summarize_messages = AsyncMock(return_value=mock_summary)

    # Create handler
    handler = SummarizeCommandHandler(
        summarization_engine=engine,
        rate_limit_enabled=False
    )

    # Mock interaction
    interaction = MagicMock()
    interaction.guild_id = "123456789"
    interaction.user.id = "987654321"

    # Test command
    await handler.handle_summarize(
        interaction=interaction,
        hours=1,
        length="brief"
    )

    # Verify
    assert engine.summarize_messages.called
```

### Integration Testing

Test with actual Discord bot in a test server:

```python
# tests/integration/test_command_handlers.py
import discord
from discord.ext import commands

async def test_full_workflow(bot_client: discord.Client):
    # Execute summarize command
    guild = bot_client.get_guild(TEST_GUILD_ID)
    channel = guild.get_channel(TEST_CHANNEL_ID)

    # Trigger command via interaction simulation
    # Verify response is correct format
    # Check database for summary storage
```

## Best Practices

### 1. Always Defer Long Operations

```python
await self.defer_response(interaction)
# ... long-running operation ...
await interaction.followup.send(embed=result_embed)
```

### 2. Use Ephemeral for Errors and Private Info

```python
await interaction.response.send_message(
    embed=error_embed,
    ephemeral=True  # Only visible to user
)
```

### 3. Provide Clear User Feedback

```python
# Bad
"Error: Invalid input"

# Good
"The time range you specified is invalid. Start time must be before end time. Please try again with a valid time range."
```

### 4. Log Important Events

```python
logger.info(
    f"Summary generated - Guild: {guild_id}, "
    f"Channel: {channel_id}, Messages: {message_count}, "
    f"User: {user_id}"
)
```

### 5. Handle Edge Cases

```python
# Check for None values
if not channel:
    channel = interaction.channel

# Validate permissions
if not channel.permissions_for(guild.me).read_message_history:
    raise ChannelAccessError(...)

# Verify data exists
if not messages:
    raise InsufficientContentError(...)
```

## Future Enhancements

Potential improvements for the command_handlers module:

1. **Persistent Rate Limiting** - Use Redis for rate limiting across restarts
2. **Command Analytics** - Track command usage and performance
3. **A/B Testing** - Test different response formats
4. **Localization** - Multi-language support for responses
5. **Command Cooldowns** - Per-guild or per-channel cooldowns
6. **Auto-complete** - Discord auto-complete for command parameters
7. **Command Middleware** - Pre/post hooks for commands
8. **Response Templates** - Customizable embed templates per guild

## Troubleshooting

### Common Issues

**Q: Rate limit triggered even for first command**
A: Check that `rate_limit_enabled=True` and verify `RateLimitTracker` is properly initialized.

**Q: Permission checks always fail**
A: Ensure `PermissionManager` is passed to handler and guild member has correct roles.

**Q: Deferred response not working**
A: Verify `defer_response()` is called before 3-second Discord timeout.

**Q: Embeds not displaying correctly**
A: Check that field values don't exceed Discord's 1024 character limit. Use `truncate_text()` utility.

## Related Modules

- `summarization/` - AI summarization engine
- `message_processing/` - Message fetching and processing
- `permissions/` - Permission management
- `models/` - Data models and DTOs
- `exceptions/` - Custom exception hierarchy

## See Also

- [Discord.py Documentation](https://discordpy.readthedocs.io/)
- [Discord Slash Commands Guide](https://discord.com/developers/docs/interactions/application-commands)
- [Phase 3 Architecture Specification](/workspaces/summarybot-ng/specs/phase_3_modules.md)
