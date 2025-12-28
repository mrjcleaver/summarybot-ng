# Discord Bot Module - API Reference

## Module: `src.discord_bot`

### Exported Components

```python
from src.discord_bot import (
    SummaryBot,           # Main bot class
    EventHandler,         # Event handling
    CommandRegistry,      # Command management
    create_embed,         # Embed utilities
    create_error_embed,
    create_success_embed,
    create_info_embed,
    format_timestamp,     # Text utilities
    truncate_text
)
```

---

## SummaryBot

Main Discord bot client for Summary Bot NG.

### Constructor

```python
SummaryBot(config: BotConfig, services: Optional[dict] = None)
```

**Parameters**:
- `config`: Bot configuration (BotConfig instance)
- `services`: Optional service container with dependencies

**Example**:
```python
config = BotConfig.load_from_env()
bot = SummaryBot(config=config)
```

### Methods

#### `async start() -> None`
Start the Discord bot and connect to Discord.

**Raises**:
- `DiscordError`: If bot fails to start or login

**Example**:
```python
await bot.start()
```

#### `async stop() -> None`
Stop the Discord bot gracefully.

**Example**:
```python
await bot.stop()
```

#### `async setup_commands() -> None`
Set up all slash commands for the bot.

**Example**:
```python
await bot.setup_commands()
```

#### `async sync_commands(guild_id: Optional[str] = None) -> None`
Sync slash commands with Discord.

**Parameters**:
- `guild_id`: Optional guild ID for guild-specific sync (faster)

**Note**: Global sync takes up to 1 hour to propagate.

**Example**:
```python
# Global sync
await bot.sync_commands()

# Guild-specific sync (instant)
await bot.sync_commands(guild_id="123456789")
```

#### `async wait_until_ready(timeout: float = 30.0) -> None`
Wait until the bot is ready.

**Parameters**:
- `timeout`: Maximum time to wait in seconds

**Raises**:
- `TimeoutError`: If bot doesn't become ready within timeout

**Example**:
```python
await bot.wait_until_ready(timeout=10.0)
```

### Properties

#### `is_ready -> bool`
Check if the bot is ready and connected.

#### `is_running -> bool`
Check if the bot is currently running.

#### `user -> Optional[discord.ClientUser]`
Get the bot's user object.

#### `guilds -> list[discord.Guild]`
Get list of guilds the bot is in.

### Helper Methods

#### `get_guild(guild_id: int) -> Optional[discord.Guild]`
Get a guild by ID from cache.

#### `get_channel(channel_id: int) -> Optional[discord.abc.GuildChannel]`
Get a channel by ID from cache.

#### `async get_or_fetch_guild(guild_id: int) -> Optional[discord.Guild]`
Get a guild by ID, fetching from API if not in cache.

#### `async get_or_fetch_channel(channel_id: int) -> Optional[discord.abc.GuildChannel]`
Get a channel by ID, fetching from API if not in cache.

---

## EventHandler

Handles Discord events for the Summary Bot.

### Constructor

```python
EventHandler(bot: SummaryBot)
```

### Methods

#### `async on_ready() -> None`
Handle the bot ready event. Called when bot successfully connects.

#### `async on_guild_join(guild: discord.Guild) -> None`
Handle the bot joining a new guild.

#### `async on_guild_remove(guild: discord.Guild) -> None`
Handle the bot being removed from a guild.

#### `async on_application_command_error(interaction: discord.Interaction, error: Exception) -> None`
Handle errors during command execution.

#### `def register_events() -> None`
Register all event handlers with the Discord client.

---

## CommandRegistry

Manages Discord slash command registration and setup.

### Constructor

```python
CommandRegistry(bot: SummaryBot)
```

### Methods

#### `async setup_commands() -> None`
Set up all slash commands for the bot.

#### `async sync_commands(guild_id: Optional[str] = None) -> int`
Sync slash commands with Discord.

**Returns**: Number of commands synced

#### `async clear_commands(guild_id: Optional[str] = None) -> None`
Clear all slash commands.

#### `get_command_count() -> int`
Get the number of registered commands.

#### `get_command_names() -> list[str]`
Get a list of all registered command names.

---

## Utility Functions

### Embed Creation

#### `create_embed(...) -> discord.Embed`
Create a Discord embed with common formatting.

**Parameters**:
- `title: str`: Embed title
- `description: str = None`: Embed description
- `color: int = 0x4A90E2`: Embed color (hex)
- `fields: List[Dict[str, Any]] = None`: List of fields
- `footer: str = None`: Footer text
- `timestamp: datetime = None`: Timestamp
- `thumbnail_url: str = None`: Thumbnail URL
- `image_url: str = None`: Main image URL

**Example**:
```python
embed = create_embed(
    title="Summary Complete",
    description="Your summary is ready!",
    color=0x2ECC71,
    fields=[
        {"name": "Messages", "value": "150", "inline": True},
        {"name": "Duration", "value": "2 hours", "inline": True}
    ],
    footer="Summary Bot NG"
)
```

#### `create_error_embed(...) -> discord.Embed`
Create an error embed with standard formatting.

**Parameters**:
- `title: str = "Error"`: Error title
- `description: str = None`: Error description
- `error_code: str = None`: Error code
- `details: str = None`: Additional details

**Example**:
```python
embed = create_error_embed(
    title="Permission Denied",
    description="You don't have permission to use this command.",
    error_code="PERMISSION_DENIED"
)
```

#### `create_success_embed(...) -> discord.Embed`
Create a success embed.

#### `create_info_embed(...) -> discord.Embed`
Create an info embed.

### Text Formatting

#### `format_timestamp(dt: datetime, style: str = "f") -> str`
Format a datetime as a Discord timestamp.

**Styles**:
- `'t'`: Short time (16:20)
- `'T'`: Long time (16:20:30)
- `'d'`: Short date (20/04/2021)
- `'D'`: Long date (20 April 2021)
- `'f'`: Short date/time (default)
- `'F'`: Long date/time
- `'R'`: Relative time (2 months ago)

**Example**:
```python
from datetime import datetime
now = datetime.utcnow()
formatted = format_timestamp(now, style="R")  # "2 minutes ago"
```

#### `truncate_text(text: str, max_length: int, suffix: str = "...") -> str`
Truncate text to a maximum length.

**Example**:
```python
long_text = "This is a very long message..."
short = truncate_text(long_text, max_length=20)  # "This is a very l..."
```

#### `format_code_block(code: str, language: str = "") -> str`
Format text as a Discord code block.

**Example**:
```python
code = "print('Hello, World!')"
block = format_code_block(code, language="python")
```

#### `format_list(items: List[str], bullet: str = "•") -> str`
Format a list of items with bullets.

**Example**:
```python
items = ["First", "Second", "Third"]
formatted = format_list(items)  # "• First\n• Second\n• Third"
```

### Mention Parsing

#### `parse_channel_mention(mention: str) -> Optional[int]`
Parse a channel mention to extract the channel ID.

**Example**:
```python
channel_id = parse_channel_mention("<#123456789>")  # 123456789
```

#### `parse_user_mention(mention: str) -> Optional[int]`
Parse a user mention to extract the user ID.

**Example**:
```python
user_id = parse_user_mention("<@!123456789>")  # 123456789
```

#### `parse_role_mention(mention: str) -> Optional[int]`
Parse a role mention to extract the role ID.

### Display Utilities

#### `create_progress_bar(current: int, total: int, length: int = 10, filled: str = "█", empty: str = "░") -> str`
Create a text-based progress bar.

**Example**:
```python
bar = create_progress_bar(50, 100)  # "█████░░░░░ 50%"
```

#### `format_file_size(size_bytes: int) -> str`
Format file size in human-readable format.

**Example**:
```python
size = format_file_size(1048576)  # "1.0 MB"
```

#### `split_message(text: str, max_length: int = 2000) -> List[str]`
Split a long message respecting Discord's character limit.

**Example**:
```python
long_text = "A" * 5000
parts = split_message(long_text)  # Returns list of 3 strings
```

#### `get_permission_names(permissions: discord.Permissions) -> List[str]`
Get a list of permission names from a Permissions object.

---

## Built-in Commands

The following commands are automatically registered:

### `/help`
Show help information about the bot and its commands.

### `/about`
Display information about Summary Bot NG.

### `/status`
Check the bot's current status and health.

### `/ping`
Check the bot's response time.

---

## Error Handling

All methods properly handle and categorize errors:

### Custom Exceptions
- `SummaryBotException`: Base custom exception
- Error codes for tracking
- User-friendly messages
- Retryable flag support

### Discord Errors
- `discord.Forbidden`: Permission errors
- `discord.NotFound`: Resource not found
- `discord.HTTPException`: API errors

All errors are logged and user-friendly error embeds are sent to users.

---

## Discord Intents

Required intents:
```python
intents = discord.Intents.default()
intents.message_content = True  # For reading messages
intents.guilds = True           # For guild events
intents.members = True          # For member info (optional)
```

## Discord Permissions

Required bot permissions:
- Read Message History
- Send Messages
- Use Application Commands
- View Channels
- Embed Links
