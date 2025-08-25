"""
Main application entry point for Summary Bot NG.
"""

import asyncio
import logging
import signal
import sys
from typing import Optional

import discord
from anthropic import AsyncAnthropic

from config import ConfigManager, BotConfig
from exceptions import handle_unexpected_error
from summarization import SummarizationEngine, ClaudeClient
from summarization.cache import SummaryCache, MemoryCache
from message_processing import MessageProcessor


class SummaryBotApp:
    """Main application class for Summary Bot NG."""
    
    def __init__(self):
        self.config: Optional[BotConfig] = None
        self.discord_client: Optional[discord.Client] = None
        self.summarization_engine: Optional[SummarizationEngine] = None
        self.message_processor: Optional[MessageProcessor] = None
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
    
    async def initialize(self, config_path: Optional[str] = None):
        """Initialize the application with configuration."""
        try:
            # Load configuration
            config_manager = ConfigManager(config_path)
            self.config = await config_manager.load_config()
            
            # Set log level
            logging.getLogger().setLevel(self.config.log_level.value)
            
            self.logger.info("Configuration loaded successfully")
            
            # Initialize Discord client
            intents = discord.Intents.default()
            intents.message_content = True
            intents.guilds = True
            
            self.discord_client = discord.Client(intents=intents)
            
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
            
            # Initialize message processor
            self.message_processor = MessageProcessor(self.discord_client)
            
            self.logger.info("Application initialized successfully")
            
        except Exception as e:
            error = handle_unexpected_error(e)
            self.logger.error(f"Failed to initialize application: {error.to_log_string()}")
            raise
    
    async def start(self):
        """Start the application."""
        if not self.config or not self.discord_client:
            raise RuntimeError("Application not initialized")
        
        self.running = True
        self.logger.info("Starting Summary Bot NG...")
        
        # Setup signal handlers for graceful shutdown
        for sig in [signal.SIGINT, signal.SIGTERM]:
            signal.signal(sig, self._signal_handler)
        
        try:
            # Start Discord client
            await self.discord_client.start(self.config.discord_token)
            
        except Exception as e:
            error = handle_unexpected_error(e)
            self.logger.error(f"Failed to start application: {error.to_log_string()}")
            raise
    
    async def stop(self):
        """Stop the application gracefully."""
        self.logger.info("Stopping Summary Bot NG...")
        self.running = False
        
        if self.discord_client:
            await self.discord_client.close()
        
        self.logger.info("Summary Bot NG stopped")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        asyncio.create_task(self.stop())


async def main():
    """Main entry point."""
    app = SummaryBotApp()
    
    try:
        await app.initialize()
        await app.start()
    except KeyboardInterrupt:
        await app.stop()
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())