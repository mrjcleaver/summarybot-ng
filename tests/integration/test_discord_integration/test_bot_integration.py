"""
Integration tests for Discord bot functionality.

Tests cover Discord bot integration, command handling, and real Discord API interactions
with mocked external dependencies.
"""

import pytest
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
    
    @pytest.fixture
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
    
    @pytest.fixture
    async def discord_bot(self, bot_config, mock_services):
        """Create SummaryBot instance for testing."""
        with patch('discord.Client.__init__', return_value=None):
            bot = SummaryBot(bot_config, mock_services)
            bot.user = MagicMock()
            bot.user.id = 987654321
            bot.user.name = "TestBot"
            return bot
    
    @pytest.fixture
    def mock_guild(self):
        """Mock Discord guild."""
        guild = MagicMock(spec=discord.Guild)
        guild.id = 123456789
        guild.name = "Test Guild"
        guild.member_count = 100
        guild.channels = []
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
        interaction.response = AsyncMock()
        interaction.followup = AsyncMock()
        return interaction
    
    @pytest.mark.asyncio
    async def test_bot_startup_success(self, discord_bot, mock_services):
        """Test successful bot startup sequence."""
        with patch.object(discord_bot, 'wait_until_ready'), \
             patch.object(discord_bot, 'setup_commands'), \
             patch.object(discord_bot, 'sync_commands'):
            
            await discord_bot.start()
            
            # Verify startup sequence
            discord_bot.setup_commands.assert_called_once()
            discord_bot.sync_commands.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_bot_command_registration(self, discord_bot):
        """Test command registration during setup."""
        with patch.object(discord_bot, 'add_cog') as mock_add_cog:
            await discord_bot.setup_commands()
            
            # Verify commands were registered
            assert mock_add_cog.call_count > 0
    
    @pytest.mark.asyncio
    async def test_summarize_command_execution(
        self, 
        discord_bot, 
        mock_interaction, 
        mock_services
    ):
        """Test summarize command execution through bot."""
        # Setup mock summarization result
        mock_summary = MagicMock()
        mock_summary.to_embed.return_value = discord.Embed(title="Test Summary")
        
        mock_engine = mock_services.get_summarization_engine()
        mock_engine.summarize_messages.return_value = mock_summary
        
        mock_permission_manager = mock_services.get_permission_manager()
        mock_permission_manager.check_command_permission.return_value = True
        mock_permission_manager.check_channel_access.return_value = True
        
        # Execute summarize command
        handler = SummarizeCommandHandler(mock_engine, mock_permission_manager)
        
        with patch.object(handler, 'fetch_messages', return_value=[]):
            await handler.handle_summarize(mock_interaction)
        
        # Verify permission checks were performed
        mock_permission_manager.check_command_permission.assert_called()
        mock_permission_manager.check_channel_access.assert_called()
        
        # Verify response was sent
        mock_interaction.response.send_message.assert_called()
    
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
        
        with patch('src.config.settings.ConfigManager.save_config') as mock_save:
            await event_handler.on_guild_join(mock_guild)
            
            # Verify guild configuration was created
            mock_save.assert_called_once()
    
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
        
        # Verify error response was sent
        mock_interaction.response.send_message.assert_called()
        call_args = mock_interaction.response.send_message.call_args
        assert "error" in call_args[1].get("content", "").lower()
    
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
        
        # Mock channel history
        mock_channel.history.return_value.__aiter__ = AsyncMock(return_value=iter(mock_messages))
        
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
        with patch.object(discord_bot, 'close') as mock_close:
            await discord_bot.stop()
            mock_close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_command_sync_per_guild(self, discord_bot, mock_guild):
        """Test command synchronization per guild."""
        with patch.object(discord_bot, 'tree') as mock_tree:
            await discord_bot.sync_commands(guild_id=str(mock_guild.id))
            
            # Verify guild-specific sync was called
            mock_tree.sync.assert_called()
    
    @pytest.mark.asyncio
    async def test_bot_ready_event(self, discord_bot):
        """Test bot ready event handling."""
        event_handler = EventHandler(discord_bot)
        
        with patch('builtins.print') as mock_print:
            await event_handler.on_ready()
            
            # Verify ready message was logged
            mock_print.assert_called()
            call_args = str(mock_print.call_args)
            assert "ready" in call_args.lower() or "logged in" in call_args.lower()


@pytest.mark.integration
class TestCommandHandlerIntegration:
    """Test command handler integration with Discord components."""
    
    @pytest.fixture
    def mock_summarization_engine(self):
        """Mock summarization engine."""
        engine = AsyncMock(spec=SummarizationEngine)
        engine.summarize_messages.return_value = MagicMock(
            id="test_summary",
            summary_text="Integration test summary",
            key_points=["Point 1", "Point 2"],
            to_embed=MagicMock(return_value=discord.Embed(title="Test"))
        )
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
        # Mock message fetching
        with patch.object(summarize_handler, 'fetch_messages') as mock_fetch:
            mock_fetch.return_value = [
                MagicMock(content="Test message 1"),
                MagicMock(content="Test message 2"),
                MagicMock(content="Test message 3")
            ]
            
            await summarize_handler.handle_summarize(mock_interaction)
            
            # Verify full execution chain
            mock_fetch.assert_called_once()
            mock_summarization_engine.summarize_messages.assert_called_once()
            mock_interaction.response.send_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_quick_summary_command(
        self, 
        summarize_handler, 
        mock_interaction,
        mock_summarization_engine
    ):
        """Test quick summary command with recent messages."""
        with patch.object(summarize_handler, 'fetch_recent_messages') as mock_fetch:
            mock_fetch.return_value = [MagicMock(content="Recent message")]
            
            await summarize_handler.handle_quick_summary(mock_interaction)
            
            # Verify quick summary execution
            mock_fetch.assert_called_once()
            mock_summarization_engine.summarize_messages.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_scheduled_summary_command(
        self, 
        summarize_handler, 
        mock_interaction
    ):
        """Test scheduled summary command."""
        with patch('src.scheduling.scheduler.TaskScheduler') as mock_scheduler:
            mock_scheduler_instance = AsyncMock()
            mock_scheduler.return_value = mock_scheduler_instance
            mock_scheduler_instance.schedule_task.return_value = "task_123"
            
            await summarize_handler.handle_scheduled_summary(mock_interaction)
            
            # Verify task was scheduled
            mock_scheduler_instance.schedule_task.assert_called_once()
            mock_interaction.response.send_message.assert_called_once()
    
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
        
        with patch.object(summarize_handler, 'fetch_messages', return_value=[MagicMock()]):
            await summarize_handler.handle_summarize(mock_interaction)
            
            # Verify error response was sent
            mock_interaction.response.send_message.assert_called()
            call_args = mock_interaction.response.send_message.call_args
            assert "error" in call_args[1].get("content", "").lower()