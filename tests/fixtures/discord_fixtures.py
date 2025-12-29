"""
Discord-specific test fixtures and utilities.

Provides reusable mock Discord objects and test data generators
for consistent testing across all test modules.
"""

from unittest.mock import MagicMock, AsyncMock
from datetime import datetime, timedelta
from typing import List, Optional
import discord

from src.models.message import ProcessedMessage


def create_mock_user(
    user_id: int = 111111111,
    username: str = "testuser",
    display_name: str = "Test User",
    bot: bool = False,
    roles: Optional[List[str]] = None
) -> MagicMock:
    """Create a mock Discord user."""
    user = MagicMock(spec=discord.User)
    user.id = user_id
    user.name = username
    user.display_name = display_name
    user.bot = bot
    
    if roles:
        user.roles = [MagicMock(name=role) for role in roles]
    else:
        user.roles = [MagicMock(name="@everyone")]
    
    return user


def create_mock_member(
    user_id: int = 111111111,
    username: str = "testuser",
    display_name: str = "Test User",
    roles: Optional[List[str]] = None,
    permissions: Optional[discord.Permissions] = None
) -> MagicMock:
    """Create a mock Discord member."""
    member = MagicMock(spec=discord.Member)
    member.id = user_id
    member.name = username
    member.display_name = display_name
    member.bot = False
    
    if roles:
        member.roles = [MagicMock(name=role) for role in roles]
    else:
        member.roles = [MagicMock(name="@everyone")]
    
    if permissions:
        member.guild_permissions = permissions
    else:
        member.guild_permissions = discord.Permissions.none()
    
    return member


def create_mock_guild(
    guild_id: int = 123456789,
    name: str = "Test Guild",
    member_count: int = 100,
    channels: Optional[List[str]] = None
) -> MagicMock:
    """Create a mock Discord guild."""
    guild = MagicMock(spec=discord.Guild)
    guild.id = guild_id
    guild.name = name
    guild.member_count = member_count
    
    if channels:
        guild.channels = [create_mock_channel(name=ch) for ch in channels]
    else:
        guild.channels = []
    
    return guild


def create_mock_channel(
    channel_id: int = 987654321,
    name: str = "test-channel",
    guild_id: int = 123456789,
    channel_type: discord.ChannelType = discord.ChannelType.text,
    permissions: Optional[discord.Permissions] = None
) -> MagicMock:
    """Create a mock Discord channel."""
    if channel_type == discord.ChannelType.text:
        channel = MagicMock(spec=discord.TextChannel)
    elif channel_type == discord.ChannelType.voice:
        channel = MagicMock(spec=discord.VoiceChannel)
    elif channel_type == discord.ChannelType.category:
        channel = MagicMock(spec=discord.CategoryChannel)
    else:
        channel = MagicMock(spec=discord.abc.GuildChannel)
    
    channel.id = channel_id
    channel.name = name
    channel.type = channel_type
    
    # Mock guild
    channel.guild = create_mock_guild(guild_id)
    
    # Mock permissions
    if permissions:
        channel.permissions_for.return_value = permissions
    else:
        channel.permissions_for.return_value = discord.Permissions.all()
    
    return channel


def create_mock_thread(
    thread_id: int = 555555555,
    name: str = "Test Thread",
    parent_channel_id: int = 987654321,
    parent_message_id: int = 444444444,
    archived: bool = False
) -> MagicMock:
    """Create a mock Discord thread."""
    thread = MagicMock(spec=discord.Thread)
    thread.id = thread_id
    thread.name = name
    thread.archived = archived
    thread.parent_id = parent_channel_id
    thread.parent = create_mock_channel(parent_channel_id)
    
    # Mock starter message
    thread.starter_message = MagicMock()
    thread.starter_message.id = parent_message_id
    
    return thread


def create_mock_message(
    message_id: int = 555555555,
    content: str = "Test message content",
    author: Optional[MagicMock] = None,
    channel: Optional[MagicMock] = None,
    timestamp: Optional[datetime] = None,
    attachments: Optional[List[MagicMock]] = None,
    embeds: Optional[List[MagicMock]] = None,
    reference: Optional[MagicMock] = None,
    thread: Optional[MagicMock] = None
) -> MagicMock:
    """Create a mock Discord message."""
    message = MagicMock(spec=discord.Message)
    message.id = message_id
    message.content = content
    
    if author:
        message.author = author
    else:
        message.author = create_mock_user()
    
    if channel:
        message.channel = channel
    else:
        message.channel = create_mock_channel()
    
    if timestamp:
        message.created_at = timestamp
    else:
        message.created_at = datetime.utcnow()
    
    if attachments:
        message.attachments = attachments
    else:
        message.attachments = []
    
    if embeds:
        message.embeds = embeds
    else:
        message.embeds = []
    
    message.reference = reference
    message.thread = thread
    
    # Common message properties
    message.edited_at = None
    message.pinned = False
    message.mention_everyone = False
    message.mentions = []
    message.role_mentions = []
    message.channel_mentions = []
    
    return message


def create_mock_messages(
    count: int = 10,
    channel_id: int = 987654321,
    start_time: Optional[datetime] = None,
    time_interval_minutes: int = 5,
    users: Optional[List[MagicMock]] = None,
    content_template: str = "Test message {i}"
) -> List[MagicMock]:
    """Create a list of mock Discord messages."""
    if start_time is None:
        start_time = datetime.utcnow() - timedelta(hours=1)
    
    if users is None:
        users = [
            create_mock_user(111111111, "user1", "User One"),
            create_mock_user(222222222, "user2", "User Two"), 
            create_mock_user(333333333, "user3", "User Three")
        ]
    
    messages = []
    channel = create_mock_channel(channel_id)
    
    for i in range(count):
        author = users[i % len(users)]
        timestamp = start_time + timedelta(minutes=i * time_interval_minutes)
        content = content_template.format(i=i+1)
        
        message = create_mock_message(
            message_id=1000000000 + i,
            content=content,
            author=author,
            channel=channel,
            timestamp=timestamp
        )
        
        messages.append(message)
    
    return messages


def create_mock_attachment(
    filename: str = "test_file.pdf",
    size: int = 1024,
    content_type: str = "application/pdf",
    url: str = "https://cdn.discord.com/attachments/test_file.pdf"
) -> MagicMock:
    """Create a mock Discord attachment."""
    attachment = MagicMock(spec=discord.Attachment)
    attachment.filename = filename
    attachment.size = size
    attachment.content_type = content_type
    attachment.url = url
    attachment.proxy_url = url
    
    return attachment


def create_mock_embed(
    title: str = "Test Embed",
    description: str = "Test embed description",
    color: int = 0x00ff00,
    fields: Optional[List[dict]] = None
) -> MagicMock:
    """Create a mock Discord embed."""
    embed = MagicMock(spec=discord.Embed)
    embed.title = title
    embed.description = description
    embed.color = color
    
    if fields:
        embed.fields = [MagicMock(**field) for field in fields]
    else:
        embed.fields = []
    
    return embed


def create_mock_interaction(
    guild_id: int = 123456789,
    channel_id: int = 987654321,
    user_id: int = 111111111,
    command_name: str = "summarize",
    options: Optional[dict] = None
) -> AsyncMock:
    """Create a mock Discord interaction."""
    interaction = AsyncMock(spec=discord.Interaction)
    
    # Mock guild, channel, and user
    interaction.guild = create_mock_guild(guild_id)
    interaction.channel = create_mock_channel(channel_id)
    interaction.user = create_mock_user(user_id)
    
    # Mock command
    interaction.command = MagicMock()
    interaction.command.name = command_name
    
    # Mock options
    if options:
        interaction.options = options
    else:
        interaction.options = {}
    
    # Mock response methods
    interaction.response = AsyncMock()
    interaction.followup = AsyncMock()
    interaction.edit_original_response = AsyncMock()
    
    # Common interaction properties
    interaction.type = discord.InteractionType.application_command
    interaction.token = "mock_interaction_token"
    interaction.id = 999999999
    interaction.created_at = datetime.utcnow()
    
    return interaction


def create_processed_messages(
    count: int = 10,
    channel_id: str = "987654321",
    start_time: Optional[datetime] = None,
    time_interval_minutes: int = 5,
    content_template: str = "Processed message {i}"
) -> List[ProcessedMessage]:
    """Create a list of ProcessedMessage objects for testing."""
    if start_time is None:
        start_time = datetime.utcnow() - timedelta(hours=1)
    
    messages = []
    users = ["user1", "user2", "user3"]
    user_ids = ["111111111", "222222222", "333333333"]
    
    for i in range(count):
        user_index = i % len(users)
        timestamp = start_time + timedelta(minutes=i * time_interval_minutes)
        
        message = ProcessedMessage(
            id=f"processed_msg_{i+1}",
            author_name=users[user_index],
            author_id=user_ids[user_index],
            content=content_template.format(i=i+1),
            timestamp=timestamp,
            thread_info=None,
            attachments=[],
            references=[]
        )
        
        messages.append(message)
    
    return messages


def create_mock_permissions(
    **permissions
) -> discord.Permissions:
    """Create Discord permissions object with specified permissions."""
    # Default permissions
    default_perms = {
        'read_messages': True,
        'send_messages': True,
        'read_message_history': True,
        'embed_links': True,
        'attach_files': True,
        'use_external_emojis': True,
        'add_reactions': True
    }
    
    # Override with provided permissions
    default_perms.update(permissions)
    
    return discord.Permissions(**default_perms)


def create_mock_role(
    role_id: int = 444444444,
    name: str = "Test Role",
    permissions: Optional[discord.Permissions] = None,
    position: int = 1,
    mentionable: bool = True,
    hoist: bool = False,
    color: int = 0x000000
) -> MagicMock:
    """Create a mock Discord role."""
    role = MagicMock(spec=discord.Role)
    role.id = role_id
    role.name = name
    role.position = position
    role.mentionable = mentionable
    role.hoist = hoist
    role.color = discord.Color(color)
    
    if permissions:
        role.permissions = permissions
    else:
        role.permissions = discord.Permissions.none()
    
    return role


def create_mock_reaction(
    emoji: str = "👍",
    count: int = 1,
    me: bool = False
) -> MagicMock:
    """Create a mock Discord reaction."""
    reaction = MagicMock(spec=discord.Reaction)
    reaction.emoji = emoji
    reaction.count = count
    reaction.me = me

    # Mock emoji object for custom emojis
    if not emoji.isascii() or len(emoji) > 2:
        emoji_obj = MagicMock()
        emoji_obj.name = emoji
        emoji_obj.id = 888888888
        emoji_obj.animated = False
        reaction.emoji = emoji_obj

    return reaction


def create_mock_webhook(
    webhook_id: int = 777777777,
    name: str = "Test Webhook",
    channel_id: int = 987654321,
    token: str = "webhook_token_12345"
) -> MagicMock:
    """Create a mock Discord webhook."""
    webhook = MagicMock(spec=discord.Webhook)
    webhook.id = webhook_id
    webhook.name = name
    webhook.channel_id = channel_id
    webhook.token = token
    webhook.url = f"https://discord.com/api/webhooks/{webhook_id}/{token}"

    # Mock send method
    webhook.send = AsyncMock()

    return webhook


def create_mock_application_command(
    command_id: int = 666666666,
    name: str = "summarize",
    description: str = "Generate a summary",
    options: Optional[List[Dict[str, Any]]] = None
) -> MagicMock:
    """Create a mock Discord application command."""
    from discord import app_commands

    command = MagicMock(spec=app_commands.Command)
    command.id = command_id
    command.name = name
    command.description = description
    command.options = options or []

    return command


def create_mock_voice_state(
    user_id: int = 111111111,
    channel_id: Optional[int] = None,
    muted: bool = False,
    deafened: bool = False
) -> MagicMock:
    """Create a mock Discord voice state."""
    voice_state = MagicMock(spec=discord.VoiceState)

    if channel_id:
        voice_state.channel = create_mock_channel(channel_id, channel_type=discord.ChannelType.voice)
    else:
        voice_state.channel = None

    voice_state.mute = muted
    voice_state.deaf = deafened
    voice_state.self_mute = muted
    voice_state.self_deaf = deafened

    # Mock user
    user = create_mock_user(user_id)
    voice_state.user = user

    return voice_state


def create_conversation_scenario(
    scenario_type: str = "technical_discussion",
    duration_hours: int = 2,
    participant_count: int = 5,
    message_density: int = 30  # messages per hour
) -> List[MagicMock]:
    """Create realistic conversation scenarios for testing."""
    scenarios = {
        "technical_discussion": {
            "topics": [
                "We need to implement the new authentication system",
                "I think we should use JWT tokens for this",
                "What about refresh token rotation?",
                "Good point, let's also consider rate limiting",
                "The API endpoints need to be secured properly",
                "Should we use OAuth2 or custom implementation?",
                "Let me share the architecture diagram",
                "This looks good, but what about error handling?"
            ],
            "users": ["dev_lead", "backend_dev", "security_expert", "qa_engineer", "architect"]
        },
        "project_planning": {
            "topics": [
                "Sprint planning for next quarter",
                "We have 5 major features to implement",
                "Timeline looks tight, can we prioritize?",
                "User authentication is highest priority",
                "Reporting dashboard can wait until Q2",
                "What about the mobile app integration?",
                "That depends on the API completion",
                "Let's schedule a follow-up meeting"
            ],
            "users": ["project_manager", "tech_lead", "product_owner", "ui_designer", "developer"]
        },
        "bug_triage": {
            "topics": [
                "Found a critical bug in production",
                "Users can't login after the latest deploy",
                "Checking the error logs now...",
                "It's related to the database connection",
                "Rolling back to previous version",
                "Rollback complete, investigating root cause",
                "Issue was with the connection pool configuration",
                "Fix deployed, monitoring for any issues"
            ],
            "users": ["devops_engineer", "senior_dev", "qa_lead", "support_manager", "cto"]
        },
        "code_review": {
            "topics": [
                "Reviewing the pull request for feature X",
                "The implementation looks solid overall",
                "I have some concerns about error handling",
                "Could we add more test coverage?",
                "The performance seems optimized",
                "Good use of async/await patterns",
                "Let's add documentation for this method",
                "Approved with minor suggestions"
            ],
            "users": ["senior_dev", "code_reviewer", "junior_dev", "tech_lead"]
        }
    }

    if scenario_type not in scenarios:
        scenario_type = "technical_discussion"

    scenario = scenarios[scenario_type]
    topics = scenario["topics"]
    usernames = scenario["users"][:participant_count]

    # Create users
    users = []
    for i, username in enumerate(usernames):
        user = create_mock_user(
            user_id=200000000 + i,
            username=username,
            display_name=username.replace("_", " ").title()
        )
        users.append(user)

    # Generate messages
    messages = []
    total_messages = duration_hours * message_density
    start_time = datetime.utcnow() - timedelta(hours=duration_hours)

    for i in range(total_messages):
        # Select topic and user
        topic_index = i % len(topics)
        user_index = i % len(users)

        # Calculate timestamp
        time_progress = i / total_messages
        timestamp = start_time + timedelta(hours=duration_hours * time_progress)

        # Create message with realistic content
        content = topics[topic_index]
        if i > 0:
            # Add variety to repeated topics
            variations = [
                f"{content} - what do you think?",
                f"Regarding {content.lower()}, I have concerns",
                f"Update on {content.lower()}",
                f"{content} is now complete",
                f"Quick question about {content.lower()}"
            ]
            content = variations[i % len(variations)]

        message = create_mock_message(
            message_id=300000000 + i,
            content=content,
            author=users[user_index],
            timestamp=timestamp
        )

        messages.append(message)

    return messages


# Additional helper functions

def create_message_with_reply(
    content: str = "This is a reply",
    replied_to_id: int = 500000000
) -> MagicMock:
    """Create a message that replies to another message."""
    # Create the reference
    reference = MagicMock(spec=discord.MessageReference)
    reference.message_id = replied_to_id

    # Create the message
    message = create_mock_message(content=content, reference=reference)

    return message


def create_message_with_code(
    language: str = "python",
    code: str = "def example():\n    pass"
) -> MagicMock:
    """Create a message containing a code block."""
    content = f"```{language}\n{code}\n```"
    return create_mock_message(content=content)


def create_bulk_messages_with_variety(
    count: int = 50,
    include_bots: bool = True,
    include_attachments: bool = True,
    include_embeds: bool = True,
    include_threads: bool = True
) -> List[MagicMock]:
    """Create a diverse set of messages for comprehensive testing."""
    messages = []
    base_time = datetime.utcnow() - timedelta(hours=2)

    for i in range(count):
        # Determine message characteristics
        is_bot = include_bots and i % 10 == 0
        has_attachment = include_attachments and i % 8 == 0
        has_embed = include_embeds and i % 12 == 0
        in_thread = include_threads and i % 15 == 0

        # Create base message
        message = create_mock_message(
            message_id=400000000 + i,
            content=f"Message content {i+1}",
            timestamp=base_time + timedelta(minutes=i * 2)
        )

        # Modify author for bots
        if is_bot:
            message.author.bot = True
            message.author.name = f"BotUser{i}"

        # Add attachments
        if has_attachment:
            message.attachments = [create_mock_attachment(f"file_{i}.pdf")]

        # Add embeds
        if has_embed:
            message.embeds = [create_mock_embed(f"Embed Title {i}")]

        # Add thread
        if in_thread:
            message.thread = create_mock_thread(thread_id=500000000 + i)

        messages.append(message)

    return messages