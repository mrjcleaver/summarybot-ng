"""
End-to-end tests for complete summarization workflows.

Tests the entire workflow from user trigger through to response,
including Discord commands, webhook triggers, and scheduled summaries.
"""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import discord

from src.discord_bot.bot import SummaryBot
from src.webhook_service.server import WebhookServer
from src.container import ServiceContainer
from src.config.settings import BotConfig
from src.models.summary import SummaryOptions


@pytest.mark.e2e
class TestDiscordSummarizationWorkflow:
    """End-to-end tests for Discord-triggered summarization workflow."""

    @pytest_asyncio.fixture
    async def full_system_setup(self, mock_config):
        """Setup complete system with all components."""
        # Create service container
        container = ServiceContainer(mock_config)

        # Mock external APIs
        with patch('src.summarization.claude_client.ClaudeClient') as mock_claude, \
             patch('discord.Client') as mock_discord_client:

            # Setup Claude mock
            claude_instance = AsyncMock()
            claude_instance.create_summary.return_value = MagicMock(
                content="# Summary\n\nKey discussion points about the project timeline...",
                model="claude-3-5-sonnet-20241022",
                input_tokens=1500,
                output_tokens=300,
                total_tokens=1800,
                response_id="e2e_test_response"
            )
            claude_instance.health_check.return_value = True
            claude_instance.get_usage_stats.return_value = MagicMock(
                total_requests=1,
                total_tokens=1800,
                total_cost=0.02,
                to_dict=lambda: {"total_requests": 1, "total_tokens": 1800}
            )
            mock_claude.return_value = claude_instance

            # Setup Discord mock
            discord_instance = AsyncMock()
            discord_instance.user = MagicMock(id=999, name="SummaryBot")
            discord_instance.is_ready.return_value = True
            mock_discord_client.return_value = discord_instance

            await container.initialize()

            # Create bot
            bot = SummaryBot(
                config=mock_config,
                services={'container': container}
            )

            yield {
                'container': container,
                'bot': bot,
                'claude_client': claude_instance
            }

            await container.cleanup()

    @pytest.mark.asyncio
    async def test_complete_discord_summarization_flow(
        self,
        full_system_setup,
        sample_messages
    ):
        """
        Test complete flow: Discord user triggers /summarize -> bot fetches messages
        -> engine processes with Claude -> summary stored -> response sent.
        """
        bot = full_system_setup['bot']
        container = full_system_setup['container']

        # Create mock interaction
        interaction = AsyncMock(spec=discord.Interaction)
        interaction.guild_id = 123456789
        interaction.guild = MagicMock()
        interaction.guild.id = 123456789
        interaction.guild.name = "Test Guild"
        interaction.guild.me = MagicMock()
        interaction.user = MagicMock(id=111111, name="TestUser")

        # Create mock channel
        channel = MagicMock(spec=discord.TextChannel)
        channel.id = 987654321
        channel.name = "general"
        channel.permissions_for = MagicMock(return_value=MagicMock(
            read_message_history=True,
            send_messages=True
        ))

        # Mock message history
        channel.history = MagicMock(return_value=AsyncMock())
        channel.history.return_value.__aiter__ = MagicMock(
            return_value=iter(sample_messages)
        )

        interaction.channel = channel
        interaction.response = AsyncMock()
        interaction.followup = AsyncMock()

        # Setup command handler
        from src.command_handlers.summarize import SummarizeCommandHandler
        handler = SummarizeCommandHandler(
            summarization_engine=container.summarization_engine
        )

        # Execute the complete flow
        await handler.handle_summarize(
            interaction=interaction,
            channel=channel,
            hours=24,
            length="detailed",
            include_bots=False
        )

        # Verify complete workflow

        # 1. User interaction was deferred
        interaction.response.defer.assert_called_once()

        # 2. Status update was sent
        assert interaction.followup.send.call_count >= 2

        # 3. Messages were processed by engine
        # (implicitly tested by successful completion)

        # 4. Summary was generated
        final_call = interaction.followup.send.call_args_list[-1]
        assert 'embed' in final_call[1]
        summary_embed = final_call[1]['embed']

        # 5. Response contains summary content
        assert summary_embed is not None

    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self, full_system_setup):
        """Test workflow handles and recovers from errors gracefully."""
        bot = full_system_setup['bot']
        container = full_system_setup['container']

        # Create mock interaction
        interaction = AsyncMock(spec=discord.Interaction)
        interaction.guild_id = 123456789
        interaction.guild = MagicMock()
        interaction.guild.me = MagicMock()
        interaction.user = MagicMock()
        interaction.channel = MagicMock()
        interaction.channel.id = 987654321
        interaction.channel.permissions_for = MagicMock(return_value=MagicMock(
            read_message_history=True
        ))
        interaction.response = AsyncMock()
        interaction.followup = AsyncMock()

        # Mock channel with no messages (error condition)
        interaction.channel.history = MagicMock(return_value=AsyncMock())
        interaction.channel.history.return_value.__aiter__ = MagicMock(
            return_value=iter([])
        )

        # Setup handler
        from src.command_handlers.summarize import SummarizeCommandHandler
        handler = SummarizeCommandHandler(
            summarization_engine=container.summarization_engine
        )

        # Execute - should handle error gracefully
        await handler.handle_summarize(
            interaction=interaction,
            channel=interaction.channel,
            hours=24,
            length="detailed",
            include_bots=False
        )

        # Should send error message to user
        assert interaction.followup.send.called

        # Verify error was communicated
        calls = interaction.followup.send.call_args_list
        error_sent = any('embed' in call[1] for call in calls)
        assert error_sent

    @pytest.mark.asyncio
    async def test_scheduled_summary_workflow(self, full_system_setup):
        """Test scheduled summary execution workflow."""
        # This would test the scheduler triggering a summary
        # Placeholder for scheduled summary E2E test
        container = full_system_setup['container']

        # Create scheduled task
        from src.scheduling.scheduler import TaskScheduler

        scheduler = TaskScheduler()

        # Schedule a summary task
        task_id = await scheduler.schedule_task(
            task_type="summary",
            schedule="0 9 * * *",  # Daily at 9 AM
            config={
                "channel_id": "987654321",
                "guild_id": "123456789",
                "summary_options": {"length": "detailed"}
            }
        )

        assert task_id is not None


@pytest.mark.e2e
class TestWebhookSummarizationWorkflow:
    """End-to-end tests for webhook-triggered summarization workflow."""

    @pytest_asyncio.fixture
    async def webhook_system_setup(self, mock_config):
        """Setup webhook server with full system."""
        container = ServiceContainer(mock_config)

        with patch('src.summarization.claude_client.ClaudeClient') as mock_claude:
            claude_instance = AsyncMock()
            claude_instance.create_summary.return_value = MagicMock(
                content="Webhook summary content",
                model="claude-3-5-sonnet-20241022",
                input_tokens=1000,
                output_tokens=200,
                total_tokens=1200,
                response_id="webhook_test"
            )
            claude_instance.health_check.return_value = True
            claude_instance.get_usage_stats.return_value = MagicMock(
                to_dict=lambda: {"total_requests": 1}
            )
            mock_claude.return_value = claude_instance

            await container.initialize()

            server = WebhookServer(
                config=mock_config,
                summarization_engine=container.summarization_engine
            )

            yield {
                'container': container,
                'server': server
            }

            await container.cleanup()

    @pytest.mark.asyncio
    async def test_webhook_triggered_summary_workflow(
        self,
        webhook_system_setup,
        sample_messages
    ):
        """
        Test webhook flow: API request -> authentication -> processing
        -> engine summarization -> database storage -> response.
        """
        server = webhook_system_setup['server']

        from httpx import AsyncClient

        async with AsyncClient(app=server.app, base_url="http://test") as client:
            # Prepare messages
            messages_data = [
                {
                    "id": str(msg.id),
                    "author_name": msg.author.display_name,
                    "author_id": str(msg.author.id),
                    "content": msg.content,
                    "timestamp": msg.created_at.isoformat(),
                    "attachments": [],
                    "references": [],
                    "mentions": []
                }
                for msg in sample_messages
            ]

            # Make webhook request
            response = await client.post(
                "/api/v1/summaries",
                json={
                    "messages": messages_data,
                    "channel_id": "987654321",
                    "guild_id": "123456789",
                    "options": {
                        "summary_length": "detailed",
                        "include_bots": False,
                        "min_messages": 5
                    }
                },
                headers={"X-API-Key": "test_api_key"}
            )

            # Verify successful processing
            assert response.status_code in [200, 201]

            data = response.json()
            # Response should contain summary data
            assert data is not None


@pytest.mark.e2e
class TestCrossComponentWorkflow:
    """End-to-end tests for workflows spanning multiple components."""

    @pytest.mark.asyncio
    async def test_bot_and_webhook_coexistence(self, mock_config):
        """Test that bot and webhook service can run together."""
        container = ServiceContainer(mock_config)

        with patch('src.summarization.claude_client.ClaudeClient') as mock_claude, \
             patch('discord.Client') as mock_discord:

            # Setup mocks
            claude_instance = AsyncMock()
            claude_instance.health_check.return_value = True
            claude_instance.get_usage_stats.return_value = MagicMock(
                to_dict=lambda: {}
            )
            mock_claude.return_value = claude_instance

            discord_instance = AsyncMock()
            discord_instance.user = MagicMock()
            mock_discord.return_value = discord_instance

            await container.initialize()

            # Create both bot and webhook server
            bot = SummaryBot(config=mock_config, services={'container': container})
            webhook = WebhookServer(
                config=mock_config,
                summarization_engine=container.summarization_engine
            )

            # Both should be able to access the same engine
            assert bot.services['container'] == container
            assert webhook.summarization_engine == container.summarization_engine

            # Cleanup
            await container.cleanup()

    @pytest.mark.asyncio
    async def test_system_health_checks(self, mock_config):
        """Test system-wide health check workflow."""
        container = ServiceContainer(mock_config)

        with patch('src.summarization.claude_client.ClaudeClient') as mock_claude:
            claude_instance = AsyncMock()
            claude_instance.health_check.return_value = True
            claude_instance.get_usage_stats.return_value = MagicMock(
                to_dict=lambda: {"total_requests": 0}
            )
            mock_claude.return_value = claude_instance

            await container.initialize()

            # Perform health check
            health_status = await container.health_check()

            # Verify health status
            assert health_status is not None
            assert 'status' in health_status
            assert health_status['status'] in ['healthy', 'degraded', 'unhealthy']

            await container.cleanup()
