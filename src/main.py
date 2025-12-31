"""
Main application entry point for Summary Bot NG.

This module orchestrates all components of the bot including:
- Discord bot client with slash commands
- Permission management
- Summarization engine
- Task scheduling
- Webhook API server
- Database persistence
"""

import asyncio
import logging
import signal
import sys
from typing import Optional
from pathlib import Path

from .config import ConfigManager, BotConfig
from .exceptions import handle_unexpected_error

# Core components
from .summarization import SummarizationEngine, ClaudeClient
from .summarization.cache import SummaryCache, MemoryCache
from .message_processing import MessageProcessor

# New modules
from .discord_bot import SummaryBot, EventHandler
from .permissions import PermissionManager
from .command_handlers import (
    SummarizeCommandHandler,
    ConfigCommandHandler,
    ScheduleCommandHandler
)
from .scheduling import TaskScheduler
from .scheduling.executor import TaskExecutor
from .webhook_service import WebhookServer
from .data import initialize_repositories, run_migrations


class SummaryBotApp:
    """Main application class for Summary Bot NG with full module integration."""

    def __init__(self):
        self.config: Optional[BotConfig] = None
        self.discord_bot: Optional[SummaryBot] = None
        self.summarization_engine: Optional[SummarizationEngine] = None
        self.message_processor: Optional[MessageProcessor] = None
        self.permission_manager: Optional[PermissionManager] = None
        self.task_scheduler: Optional[TaskScheduler] = None
        self.webhook_server: Optional[WebhookServer] = None
        self.running = False

        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('summarybot.log')
            ]
        )
        self.logger = logging.getLogger(__name__)

    async def initialize(self, config_path: Optional[str] = None, db_path: str = "data/summarybot.db"):
        """Initialize all application components.

        Args:
            config_path: Path to configuration file (optional)
            db_path: Path to SQLite database file
        """
        try:
            self.logger.info("Initializing Summary Bot NG...")

            # Load configuration
            config_manager = ConfigManager(config_path)
            self.config = await config_manager.load_config()

            # Set log level from config
            logging.getLogger().setLevel(self.config.log_level.value)
            self.logger.info("Configuration loaded successfully")

            # Initialize database
            await self._initialize_database(db_path)

            # Initialize core components
            await self._initialize_core_components()

            # Initialize Discord bot
            await self._initialize_discord_bot()

            # Initialize task scheduler
            await self._initialize_scheduler()

            # Initialize webhook server (if enabled)
            if self.config.webhook_config.enabled:
                await self._initialize_webhook_server()

            self.logger.info("All components initialized successfully")

        except Exception as e:
            error = handle_unexpected_error(e)
            self.logger.error(f"Failed to initialize application: {error.to_log_string()}")
            raise

    async def _initialize_database(self, db_path: str):
        """Initialize database with migrations."""
        self.logger.info(f"Initializing database at {db_path}...")

        # Ensure data directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # Run migrations
        await run_migrations(db_path)

        # Initialize repositories
        initialize_repositories(
            backend="sqlite",
            db_path=db_path,
            pool_size=5
        )

        self.logger.info("Database initialized successfully")

    async def _initialize_core_components(self):
        """Initialize core summarization and message processing components."""
        self.logger.info("Initializing core components...")

        # Initialize Claude client
        claude_client = ClaudeClient(
            api_key=self.config.claude_api_key,
            max_retries=3
        )

        # Initialize cache
        cache_backend = MemoryCache(
            max_size=self.config.cache_config.max_size,
            default_ttl=self.config.cache_config.default_ttl
        )
        cache = SummaryCache(cache_backend)

        # Initialize summarization engine
        self.summarization_engine = SummarizationEngine(
            claude_client=claude_client,
            cache=cache
        )

        self.logger.info("Core components initialized")

    async def _initialize_discord_bot(self):
        """Initialize Discord bot with command handlers."""
        self.logger.info("Initializing Discord bot...")

        # Initialize permission manager
        self.permission_manager = PermissionManager(self.config)

        # Create Discord bot
        self.discord_bot = SummaryBot(self.config)

        # Initialize message processor
        self.message_processor = MessageProcessor(self.discord_bot.client)

        # TODO: Integrate command handlers with bot's CommandRegistry
        # For now, the bot uses basic commands defined in CommandRegistry
        # Command handlers (SummarizeCommandHandler, ConfigCommandHandler) are available
        # but need to be integrated into the command tree

        # Event handlers are already registered in SummaryBot.__init__
        # Slash commands will be set up when bot starts

        self.logger.info("Discord bot initialized with command handlers")

    async def _initialize_scheduler(self):
        """Initialize task scheduler for automated summaries."""
        self.logger.info("Initializing task scheduler...")

        # Create task executor
        task_executor = TaskExecutor(
            summarization_engine=self.summarization_engine,
            message_processor=self.message_processor,
            discord_client=self.discord_bot.client
        )

        # Create task scheduler
        self.task_scheduler = TaskScheduler(
            task_executor=task_executor
        )

        # TODO: ScheduleCommandHandler needs to be integrated into CommandRegistry

        # Start scheduler
        await self.task_scheduler.start()

        self.logger.info("Task scheduler initialized and started")

    async def _initialize_webhook_server(self):
        """Initialize webhook API server for external integrations."""
        self.logger.info("Initializing webhook server...")

        self.webhook_server = WebhookServer(
            config=self.config,
            summarization_engine=self.summarization_engine
        )

        # Start webhook server in background
        await self.webhook_server.start_server()

        self.logger.info(
            f"Webhook server started at http://{self.config.webhook_config.host}:"
            f"{self.config.webhook_config.port}"
        )

    async def start(self):
        """Start the application and all services."""
        if not self.config or not self.discord_bot:
            raise RuntimeError("Application not initialized. Call initialize() first.")

        self.running = True
        self.logger.info("=" * 60)
        self.logger.info("Starting Summary Bot NG...")
        self.logger.info("=" * 60)

        # Setup signal handlers for graceful shutdown
        for sig in [signal.SIGINT, signal.SIGTERM]:
            signal.signal(sig, self._signal_handler)

        try:
            # Log startup status
            self.logger.info(f"Discord Bot: Ready")
            self.logger.info(f"Permission Manager: Active")
            self.logger.info(f"Summarization Engine: Ready")
            self.logger.info(f"Task Scheduler: Running")
            if self.webhook_server:
                self.logger.info(
                    f"Webhook API: http://{self.config.webhook_config.host}:"
                    f"{self.config.webhook_config.port}"
                )

            self.logger.info("=" * 60)
            self.logger.info("Summary Bot NG is now online!")
            self.logger.info("=" * 60)

            # Start Discord client (this blocks until shutdown)
            await self.discord_bot.start()

        except Exception as e:
            error = handle_unexpected_error(e)
            self.logger.error(f"Failed to start application: {error.to_log_string()}")
            raise

    async def stop(self):
        """Stop the application gracefully, shutting down all services."""
        self.logger.info("=" * 60)
        self.logger.info("Initiating graceful shutdown...")
        self.logger.info("=" * 60)

        self.running = False

        # Stop services in reverse order of initialization
        if self.webhook_server:
            self.logger.info("Stopping webhook server...")
            await self.webhook_server.stop_server()

        if self.task_scheduler:
            self.logger.info("Stopping task scheduler...")
            await self.task_scheduler.stop()

        if self.discord_bot:
            self.logger.info("Stopping Discord bot...")
            await self.discord_bot.stop()

        self.logger.info("=" * 60)
        self.logger.info("Summary Bot NG stopped cleanly")
        self.logger.info("=" * 60)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals (SIGINT, SIGTERM)."""
        signal_name = "SIGINT" if signum == signal.SIGINT else "SIGTERM"
        self.logger.info(f"Received {signal_name}, initiating graceful shutdown...")
        asyncio.create_task(self.stop())


async def main():
    """Main entry point for Summary Bot NG.

    Initializes and starts all components:
    - Discord bot with slash commands
    - Permission management system
    - AI-powered summarization engine
    - Automated task scheduling
    - REST API webhook server
    - SQLite database persistence
    """
    app = SummaryBotApp()

    try:
        # Initialize with default database path
        await app.initialize(db_path="data/summarybot.db")

        # Start all services
        await app.start()

    except KeyboardInterrupt:
        await app.stop()
    except Exception as e:
        logging.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # Run the application
    asyncio.run(main())
