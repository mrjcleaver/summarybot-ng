"""
Integration tests for Discord bot functionality.

Tests cover Discord bot integration, command handling, and real Discord API interactions
with mocked external dependencies.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import discord
from discord.ext import commands

from src.discord_bot.bot import SummaryBot
from src.discord_bot.events import EventHandler
from src.command_handlers.summarize import SummarizeCommandHandler
from src.config.settings import BotConfig, GuildConfig, SummaryOptions
from src.summarization.engine import SummarizationEngine
from src.permissions.manager import PermissionManager


@pytest.mark.integration
class TestDiscordBotIntegration:
    """Test Discord bot integration scenarios."""
    
    @pytest_asyncio.fixture
    async def bot_config(self):
        """Create bot configuration for testing."""
        guild_config = GuildConfig(
            guild_id="123456789",
            enabled_channels=["987654321"],
            excluded_channels=[],
            default_summary_options=SummaryOptions(summary_length="standard"),
            permission_settings={}
        )
        
        return BotConfig(
            discord_token="test_token",
            claude_api_key="test_api_key",
            guild_configs={"123456789": guild_config}
        )
    
    @pytest.fixture
    def mock_services(self):
        """Mock service container dependencies."""
        services = MagicMock()
        services.get_summarization_engine.return_value = AsyncMock(spec=SummarizationEngine)
        services.get_permission_manager.return_value = AsyncMock(spec=PermissionManager)
        services.get_command_handlers.return_value = {
            "summarize": AsyncMock(spec=SummarizeCommandHandler)
        }
        return services
    
    @pytest_asyncio.fixture
    async def discord_bot(self, bot_config, mock_services):
        """Create SummaryBot instance for testing."""
        with patch('discord.Client') as mock_client_class:
            # Create a mock client instance with all necessary attributes
            mock_client = MagicMock()
            mock_client.http = MagicMock()
            mock_client.user = MagicMock()
            mock_client.user.id = 987654321
            mock_client.user.name = "TestBot"
            mock_client.guilds = []
            mock_client.latency = 0.05

            # Mock the connection state for CommandTree
            mock_connection = MagicMock()
            mock_connection._command_tree = None
            mock_client._connection = mock_connection

            # Mock async methods
            mock_client.start = AsyncMock()
            mock_client.close = AsyncMock()
            mock_client.wait_until_ready = AsyncMock()
            mock_client.change_presence = AsyncMock()

            # Mock command tree with async sync method
            mock_tree = MagicMock()
            mock_tree.sync = AsyncMock(return_value=[])
            mock_client.tree = mock_tree

            mock_client_class.return_value = mock_client

            bot = SummaryBot(bot_config, mock_services)
            # Override the tree with our mock
            bot.client.tree = mock_tree
            return bot
    
    @pytest.fixture
    def mock_guild(self):
        """Mock Discord guild."""
        guild = MagicMock(spec=discord.Guild)
        guild.id = 123456789
        guild.name = "Test Guild"
        guild.member_count = 100
        guild.channels = []
        guild.text_channels = []
        guild.system_channel = None
        guild.me = MagicMock()
        return guild
    
    @pytest.fixture
    def mock_channel(self, mock_guild):
        """Mock Discord channel."""
        channel = MagicMock(spec=discord.TextChannel)
        channel.id = 987654321
        channel.name = "test-channel"
        channel.guild = mock_guild
        channel.permissions_for.return_value = discord.Permissions.all()
        return channel
    
    @pytest.fixture
    def mock_interaction(self, mock_channel, mock_guild):
        """Mock Discord interaction."""
        user = MagicMock(spec=discord.User)
        user.id = 111111111
        user.name = "testuser"
        user.display_name = "Test User"

        interaction = AsyncMock(spec=discord.Interaction)
        interaction.guild = mock_guild
        interaction.channel = mock_channel
        interaction.user = user

        # Mock response object with sync properties and async methods
        mock_response = MagicMock()
        mock_response.is_done.return_value = False  # Sync method returning bool
        mock_response.defer = AsyncMock()  # Async method
        mock_response.send_message = AsyncMock()  # Async method
        interaction.response = mock_response

        # Mock followup with async methods
        mock_followup = MagicMock()
        mock_followup.send = AsyncMock()
        interaction.followup = mock_followup

        return interaction
    
    @pytest.mark.asyncio
    async def test_bot_startup_success(self, discord_bot, mock_services):
        """Test successful bot startup sequence."""
        with patch.object(discord_bot, 'setup_commands') as mock_setup:
            mock_setup.return_value = AsyncMock()

            await discord_bot.start()

            # Verify startup sequence
            mock_setup.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_bot_command_registration(self, discord_bot):
        """Test command registration during setup."""
        await discord_bot.setup_commands()

        # Verify commands were registered by checking command count
        command_count = discord_bot.command_registry.get_command_count()
        assert command_count > 0

        # Verify specific commands exist
        command_names = discord_bot.command_registry.get_command_names()
        assert "help" in command_names
        assert "about" in command_names
    
    @pytest.mark.asyncio
    async def test_summarize_command_execution(
        self,
        discord_bot,
        mock_interaction,
        mock_services
    ):
        """Test summarize command execution through bot."""
        # Setup mock summarization result with proper to_embed_dict()
        mock_summary = MagicMock()
        mock_summary.to_embed_dict.return_value = {
            "title": "📋 Summary for #test-channel",
            "description": "Test summary content",
            "color": 0x4A90E2,  # Must be int, not MagicMock
            "fields": [
                {
                    "name": "Key Points",
                    "value": "• Test point 1\n• Test point 2",
                    "inline": False
                }
            ],
            "timestamp": datetime.utcnow().isoformat()
        }

        mock_engine = mock_services.get_summarization_engine()
        mock_engine.summarize_messages.return_value = mock_summary

        mock_permission_manager = mock_services.get_permission_manager()
        mock_permission_manager.check_command_permission.return_value = True
        mock_permission_manager.check_channel_access.return_value = True

        # Execute summarize command
        handler = SummarizeCommandHandler(mock_engine, mock_permission_manager)

        # Create minimum 5 mock messages to pass validation
        base_time = datetime.utcnow()
        mock_messages = []
        for i in range(6):
            msg = MagicMock()
            msg.content = f"Test message {i+1} with enough content to be meaningful"
            msg.created_at = base_time - timedelta(minutes=i)
            msg.author = MagicMock()
            msg.author.bot = False
            msg.author.id = 111111111 + i
            msg.author.display_name = f"User{i+1}"
            msg.id = str(1000000 + i)
            msg.attachments = []
            mock_messages.append(msg)

        with patch.object(handler, 'fetch_messages', return_value=mock_messages):
            await handler.handle_summarize(mock_interaction)

        # Verify permission checks were performed
        mock_permission_manager.check_command_permission.assert_called()
        mock_permission_manager.check_channel_access.assert_called()

        # Verify response was sent (via followup since we defer)
        # The first call is the status embed, second call is the summary
        assert mock_interaction.followup.send.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_command_permission_denied(
        self, 
        discord_bot, 
        mock_interaction, 
        mock_services
    ):
        """Test command execution with insufficient permissions."""
        mock_permission_manager = mock_services.get_permission_manager()
        mock_permission_manager.check_command_permission.return_value = False
        
        handler = SummarizeCommandHandler(None, mock_permission_manager)
        
        await handler.handle_summarize(mock_interaction)
        
        # Verify permission error response
        mock_interaction.response.send_message.assert_called()
        call_args = mock_interaction.response.send_message.call_args
        assert "permission" in call_args[1].get("content", "").lower()
    
    @pytest.mark.asyncio
    async def test_guild_join_event(self, discord_bot, mock_guild):
        """Test guild join event handling."""
        event_handler = EventHandler(discord_bot)

        # Reset tree sync mock
        discord_bot.client.tree.sync.reset_mock()

        # Mock get_guild_config to avoid real config access
        with patch.object(discord_bot.config, 'get_guild_config') as mock_get_config:
            # Create a mock guild config
            from src.config.settings import GuildConfig, SummaryOptions
            mock_guild_config = GuildConfig(
                guild_id=str(mock_guild.id),
                enabled_channels=[],
                excluded_channels=[],
                default_summary_options=SummaryOptions(),
                permission_settings={}
            )
            mock_get_config.return_value = mock_guild_config

            await event_handler.on_guild_join(mock_guild)

            # Verify guild config was accessed (creating default config)
            mock_get_config.assert_called_once_with(str(mock_guild.id))
    
    @pytest.mark.asyncio
    async def test_application_command_error_handling(
        self,
        discord_bot,
        mock_interaction
    ):
        """Test application command error handling."""
        event_handler = EventHandler(discord_bot)
        test_error = Exception("Test error")

        await event_handler.on_application_command_error(mock_interaction, test_error)

        # Verify error response was sent as embed
        mock_interaction.response.send_message.assert_called()
        call_args = mock_interaction.response.send_message.call_args
        # Error handler sends embed, not content
        assert "embed" in call_args[1] or "error" in call_args[1].get("content", "").lower()
    
    @pytest.mark.asyncio
    async def test_message_fetching_integration(
        self,
        discord_bot,
        mock_channel,
        mock_services
    ):
        """Test message fetching integration with Discord API."""
        # Create mock messages
        mock_messages = []
        for i in range(5):
            message = MagicMock(spec=discord.Message)
            message.id = 1000000 + i
            message.content = f"Test message {i+1}"
            message.author = MagicMock()
            message.author.bot = False
            message.created_at = datetime.utcnow() - timedelta(hours=1, minutes=i*5)
            mock_messages.append(message)

        # Create proper async iterator for channel history
        async def async_message_iterator():
            for msg in mock_messages:
                yield msg

        mock_history = MagicMock()
        mock_history.__aiter__ = lambda self: async_message_iterator()
        mock_channel.history.return_value = mock_history

        # Mock get_channel to return our mock channel
        discord_bot.client.get_channel = MagicMock(return_value=mock_channel)

        from src.message_processing.fetcher import MessageFetcher
        fetcher = MessageFetcher(discord_bot)

        messages = await fetcher.fetch_messages(
            channel_id=str(mock_channel.id),
            start_time=datetime.utcnow() - timedelta(hours=2),
            end_time=datetime.utcnow(),
            limit=10
        )

        # Verify messages were fetched
        assert len(messages) == 5
        assert all(hasattr(msg, 'content') for msg in messages)
    
    @pytest.mark.asyncio
    async def test_bot_shutdown_graceful(self, discord_bot):
        """Test graceful bot shutdown."""
        # Verify bot starts as not running
        assert not discord_bot.is_running

        # Simulate bot running
        discord_bot._is_running = True

        # Test graceful shutdown
        await discord_bot.stop()

        # Verify client.close was called
        discord_bot.client.close.assert_called_once()
        assert not discord_bot.is_running
    
    @pytest.mark.asyncio
    async def test_command_sync_per_guild(self, discord_bot, mock_guild):
        """Test command synchronization per guild."""
        # Mock the command_registry.sync_commands to avoid real Discord API calls
        with patch.object(discord_bot.command_registry, 'sync_commands', new_callable=AsyncMock) as mock_sync:
            mock_sync.return_value = 5  # Return number of synced commands

            await discord_bot.sync_commands(guild_id=str(mock_guild.id))

            # Verify guild-specific sync was called with the guild ID
            mock_sync.assert_called_once_with(str(mock_guild.id))
    
    @pytest.mark.asyncio
    async def test_bot_ready_event(self, discord_bot):
        """Test bot ready event handling."""
        event_handler = EventHandler(discord_bot)

        # Reset the tree sync mock to track calls
        discord_bot.client.tree.sync.reset_mock()

        with patch('src.discord_bot.events.logger') as mock_logger:
            await event_handler.on_ready()

            # Verify ready message was logged
            mock_logger.info.assert_called()
            # Check that one of the log calls mentions "ready" or "logged in"
            log_calls = [str(call) for call in mock_logger.info.call_args_list]
            assert any("ready" in call.lower() or "logged in" in call.lower() for call in log_calls)


@pytest.mark.integration
class TestCommandHandlerIntegration:
    """Test command handler integration with Discord components."""

    @pytest.fixture
    def mock_guild(self):
        """Mock Discord guild for command handler tests."""
        guild = MagicMock(spec=discord.Guild)
        guild.id = 123456789
        guild.name = "Test Guild"
        guild.member_count = 100
        guild.channels = []
        return guild

    @pytest.fixture
    def mock_channel(self, mock_guild):
        """Mock Discord channel for command handler tests."""
        channel = MagicMock(spec=discord.TextChannel)
        channel.id = 987654321
        channel.name = "test-channel"
        channel.guild = mock_guild
        channel.permissions_for.return_value = discord.Permissions.all()
        return channel

    @pytest.fixture
    def mock_interaction(self, mock_channel, mock_guild):
        """Mock Discord interaction for command handler tests."""
        user = MagicMock(spec=discord.User)
        user.id = 111111111
        user.name = "testuser"
        user.display_name = "Test User"

        interaction = AsyncMock(spec=discord.Interaction)
        interaction.guild = mock_guild
        interaction.channel = mock_channel
        interaction.user = user

        # Mock response object with sync properties and async methods
        mock_response = MagicMock()
        mock_response.is_done.return_value = False  # Sync method returning bool
        mock_response.defer = AsyncMock()  # Async method
        mock_response.send_message = AsyncMock()  # Async method
        interaction.response = mock_response

        # Mock followup with async methods
        mock_followup = MagicMock()
        mock_followup.send = AsyncMock()
        interaction.followup = mock_followup

        return interaction

    @pytest.fixture
    def mock_summarization_engine(self):
        """Mock summarization engine."""
        engine = AsyncMock(spec=SummarizationEngine)

        # Create a proper mock with to_embed_dict() that returns a valid embed dictionary
        mock_summary = MagicMock()
        mock_summary.id = "test_summary"
        mock_summary.summary_text = "Integration test summary"
        mock_summary.key_points = ["Point 1", "Point 2"]
        mock_summary.to_embed_dict.return_value = {
            "title": "📋 Summary for #test-channel",
            "description": "Integration test summary",
            "color": 0x4A90E2,  # Must be int, not MagicMock
            "fields": [
                {
                    "name": "Key Points",
                    "value": "• Point 1\n• Point 2",
                    "inline": False
                }
            ],
            "timestamp": datetime.utcnow().isoformat()
        }

        engine.summarize_messages.return_value = mock_summary
        return engine

    @pytest.fixture
    def mock_permission_manager(self):
        """Mock permission manager."""
        manager = AsyncMock(spec=PermissionManager)
        manager.check_command_permission.return_value = True
        manager.check_channel_access.return_value = True
        return manager

    @pytest.fixture
    def summarize_handler(self, mock_summarization_engine, mock_permission_manager):
        """Create summarize command handler."""
        return SummarizeCommandHandler(mock_summarization_engine, mock_permission_manager)
    
    @pytest.mark.asyncio
    async def test_summarize_command_full_flow(
        self,
        summarize_handler,
        mock_interaction,
        mock_summarization_engine
    ):
        """Test complete summarize command execution flow."""
        # Mock message fetching with proper datetime (need minimum 5 messages)
        with patch.object(summarize_handler, 'fetch_messages') as mock_fetch:
            base_time = datetime.utcnow()
            mock_messages = []
            for i in range(10):  # Create 10 messages to exceed minimum requirement
                msg = MagicMock()
                msg.content = f"Test message {i+1} with enough content to be meaningful"
                msg.created_at = base_time - timedelta(minutes=i)
                msg.author = MagicMock()
                msg.author.bot = False
                msg.author.id = 111111111 + i
                msg.author.display_name = f"User{i+1}"
                msg.id = str(1000000 + i)
                msg.attachments = []
                mock_messages.append(msg)

            mock_fetch.return_value = mock_messages

            await summarize_handler.handle_summarize(mock_interaction)

            # Verify full execution chain
            mock_fetch.assert_called_once()
            mock_summarization_engine.summarize_messages.assert_called_once()
            # Response is sent via followup.send (not response.send_message) since we defer
            assert mock_interaction.followup.send.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_quick_summary_command(
        self,
        summarize_handler,
        mock_interaction,
        mock_summarization_engine
    ):
        """Test quick summary command with recent messages."""
        with patch.object(summarize_handler, 'fetch_recent_messages') as mock_fetch:
            # Create minimum 5 messages for validation
            base_time = datetime.utcnow()
            mock_messages = []
            for i in range(6):
                msg = MagicMock()
                msg.content = f"Recent message {i+1} with content"
                msg.created_at = base_time - timedelta(minutes=i)
                msg.author = MagicMock()
                msg.author.bot = False
                mock_messages.append(msg)
            mock_fetch.return_value = mock_messages

            await summarize_handler.handle_quick_summary(mock_interaction)

            # Verify quick summary execution
            mock_fetch.assert_called_once()
            mock_summarization_engine.summarize_messages.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_scheduled_summary_command(
        self,
        summarize_handler,
        mock_interaction,
        mock_channel
    ):
        """Test scheduled summary command."""
        # Call with correct arguments: channel and schedule
        await summarize_handler.handle_scheduled_summary(
            mock_interaction,
            channel=mock_channel,
            schedule="daily"
        )

        # Verify response was sent (method is a placeholder that sends "coming soon" message)
        mock_interaction.response.send_message.assert_called_once()
        call_args = mock_interaction.response.send_message.call_args
        # Should send an embed
        assert "embed" in call_args[1]
    
    @pytest.mark.asyncio
    async def test_error_handling_in_command(
        self,
        summarize_handler,
        mock_interaction,
        mock_summarization_engine
    ):
        """Test error handling within command execution."""
        # Configure summarization engine to raise an error
        mock_summarization_engine.summarize_messages.side_effect = Exception("Test error")

        # Create minimum 5 mock messages with proper attributes
        base_time = datetime.utcnow()
        mock_messages = []
        for i in range(6):
            msg = MagicMock()
            msg.content = f"Test message {i+1} with enough content to be meaningful"
            msg.created_at = base_time - timedelta(minutes=i)
            msg.author = MagicMock()
            msg.author.bot = False
            msg.author.id = 111111111 + i
            msg.author.display_name = f"User{i+1}"
            msg.id = str(1000000 + i)
            msg.attachments = []
            mock_messages.append(msg)

        with patch.object(summarize_handler, 'fetch_messages', return_value=mock_messages):
            await summarize_handler.handle_summarize(mock_interaction)

            # Verify error response was sent via followup.send
            # First call is status embed, second call should be error
            assert mock_interaction.followup.send.call_count >= 1
            # Check that an error was sent (last call should be error)
            last_call_kwargs = mock_interaction.followup.send.call_args_list[-1][1]
            # Error is sent as embed
            assert "embed" in last_call_kwargs