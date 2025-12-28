# Command Handlers Module

Discord slash command handlers for Summary Bot NG with built-in error handling, rate limiting, and user-friendly responses.

## Quick Start

```python
from command_handlers import SummarizeCommandHandler
from summarization import SummarizationEngine

# Initialize
engine = SummarizationEngine(...)
handler = SummarizeCommandHandler(
    summarization_engine=engine,
    permission_manager=permissions  # optional
)

# Use in Discord bot
@bot.slash_command(name="summarize")
async def summarize(interaction: discord.Interaction, hours: int = 24):
    await handler.handle_summarize(interaction=interaction, hours=hours)
```

## Components

### Base Handler
```python
from command_handlers import BaseCommandHandler

class MyHandler(BaseCommandHandler):
    async def _execute_command(self, interaction, **kwargs):
        await self.defer_response(interaction)
        # Your logic here
        await self.send_success_response(interaction, "Done!", "Success")
```

### Summarize Handler
```python
from command_handlers import SummarizeCommandHandler

# Full summary
await handler.handle_summarize(
    interaction=interaction,
    channel=channel,
    hours=24,
    length="detailed",
    include_bots=False
)

# Quick summary
await handler.handle_quick_summary(
    interaction=interaction,
    minutes=60
)

# Cost estimate
await handler.estimate_summary_cost(
    interaction=interaction,
    hours=24
)
```

### Config Handler
```python
from command_handlers import ConfigCommandHandler

# View config
await handler.handle_config_view(interaction)

# Set channels
await handler.handle_config_set_channels(
    interaction=interaction,
    action="enable",  # or "exclude"
    channels="#general, #announcements"
)

# Set defaults
await handler.handle_config_set_defaults(
    interaction=interaction,
    length="detailed",
    include_bots=False,
    min_messages=10
)
```

### Schedule Handler
```python
from command_handlers import ScheduleCommandHandler

# Create schedule
await handler.handle_schedule_create(
    interaction=interaction,
    channel=channel,
    frequency="daily",
    time_of_day="09:00",
    length="detailed"
)

# List schedules
await handler.handle_schedule_list(interaction)

# Delete schedule
await handler.handle_schedule_delete(
    interaction=interaction,
    task_id="task_123"
)
```

### Utilities
```python
from command_handlers import (
    parse_time_string,
    validate_time_range,
    format_success_response,
    format_duration
)

# Parse flexible time strings
dt = parse_time_string("2h")        # 2 hours ago
dt = parse_time_string("yesterday")  # Yesterday
dt = parse_time_string("2024-01-15T10:30:00")  # ISO format

# Validate time range
validate_time_range(start, end, max_hours=168)

# Format responses
embed = format_success_response("Success", "Operation completed")

# Format durations
duration_str = format_duration(3665)  # "1h 1m 5s"
```

## Features

- **Error Handling**: Automatic conversion to user-friendly Discord embeds
- **Rate Limiting**: Built-in per-user rate limiting (configurable)
- **Permission Checks**: Integration with PermissionManager
- **Response Deferral**: Automatic for long-running operations
- **Logging**: Structured logging for debugging
- **Type Safety**: Full type hints throughout

## Error Handling

All errors are automatically caught and converted to user-friendly embeds:

```python
# Errors are automatically handled
await handler.handle_summarize(...)
# If error occurs, user sees:
# ❌ Error
# Clear description of what went wrong
# Error Code: SUMMARIZE_FAILED
```

Custom error handling:
```python
from exceptions import UserError

raise UserError(
    message="Technical details for logs",
    error_code="INVALID_INPUT",
    user_message="Please provide a valid channel."
)
```

## Rate Limiting

Default limits:
- Summarize commands: 3 requests per 60 seconds
- Config commands: 5 requests per 60 seconds
- Schedule commands: 5 requests per 60 seconds

Customize:
```python
handler.max_requests_per_minute = 10
handler.rate_limit_window = 120  # seconds

# Or disable
handler = BaseCommandHandler(..., rate_limit_enabled=False)
```

## Best Practices

1. **Always defer long operations**
   ```python
   await self.defer_response(interaction)
   # ... long operation ...
   await interaction.followup.send(...)
   ```

2. **Use ephemeral for errors**
   ```python
   await interaction.response.send_message(embed=embed, ephemeral=True)
   ```

3. **Validate input**
   ```python
   validate_time_range(start, end)
   ```

4. **Log important events**
   ```python
   logger.info(f"Summary generated - Guild: {guild_id}, User: {user_id}")
   ```

## Full Documentation

See [docs/command_handlers_module.md](../../docs/command_handlers_module.md) for complete API reference and examples.

## Architecture

```
command_handlers/
├── base.py          # BaseCommandHandler, RateLimitTracker
├── summarize.py     # SummarizeCommandHandler
├── config.py        # ConfigCommandHandler
├── schedule.py      # ScheduleCommandHandler
└── utils.py         # Utility functions
```

## Dependencies

**Required:**
- discord.py v2.0+
- Python 3.9+
- src.summarization.SummarizationEngine
- src.models.*
- src.exceptions.*

**Optional:**
- src.permissions.PermissionManager
- src.message_processing.*
- src.config.ConfigManager
- src.scheduling.TaskScheduler

## Testing

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_summarize():
    engine = MagicMock()
    engine.summarize_messages = AsyncMock(return_value=mock_summary)

    handler = SummarizeCommandHandler(
        summarization_engine=engine,
        rate_limit_enabled=False
    )

    interaction = MagicMock()
    await handler.handle_summarize(interaction=interaction, hours=1)

    assert engine.summarize_messages.called
```

## License

MIT License - See LICENSE file for details
