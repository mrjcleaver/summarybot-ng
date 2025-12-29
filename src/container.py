"""
Service container for dependency injection.

Provides centralized management of application services and their dependencies.
"""

from typing import Optional
from .config.settings import BotConfig
from .summarization.engine import SummarizationEngine
from .summarization.claude_client import ClaudeClient
from .summarization.cache import SummaryCache
from .data.repositories import SummaryRepository, ConfigRepository, TaskRepository


class ServiceContainer:
    """Dependency injection container for application services."""

    def __init__(self, config: BotConfig):
        """Initialize the service container.

        Args:
            config: Bot configuration
        """
        self.config = config
        self._claude_client: Optional[ClaudeClient] = None
        self._cache: Optional[SummaryCache] = None
        self._summarization_engine: Optional[SummarizationEngine] = None
        self._summary_repository: Optional[SummaryRepository] = None
        self._config_repository: Optional[ConfigRepository] = None
        self._task_repository: Optional[TaskRepository] = None

    @property
    def claude_client(self) -> ClaudeClient:
        """Get Claude API client instance."""
        if self._claude_client is None:
            self._claude_client = ClaudeClient(api_key=self.config.claude_api_key)
        return self._claude_client

    @property
    def cache(self) -> Optional[SummaryCache]:
        """Get summary cache instance."""
        if self._cache is None and self.config.cache_config:
            from .summarization.cache import create_cache
            self._cache = create_cache(self.config.cache_config)
        return self._cache

    @property
    def summarization_engine(self) -> SummarizationEngine:
        """Get summarization engine instance."""
        if self._summarization_engine is None:
            self._summarization_engine = SummarizationEngine(
                claude_client=self.claude_client,
                cache=self.cache
            )
        return self._summarization_engine

    @property
    def summary_repository(self) -> Optional[SummaryRepository]:
        """Get summary repository instance."""
        if self._summary_repository is None and self.config.database_config:
            self._summary_repository = SummaryRepository(
                database_url=self.config.database_config.url
            )
        return self._summary_repository

    @property
    def config_repository(self) -> Optional[ConfigRepository]:
        """Get config repository instance."""
        if self._config_repository is None and self.config.database_config:
            self._config_repository = ConfigRepository(
                database_url=self.config.database_config.url
            )
        return self._config_repository

    @property
    def task_repository(self) -> Optional[TaskRepository]:
        """Get task repository instance."""
        if self._task_repository is None and self.config.database_config:
            self._task_repository = TaskRepository(
                database_url=self.config.database_config.url
            )
        return self._task_repository

    async def initialize(self):
        """Initialize all services."""
        # Initialize database repositories if configured
        if self.config.database_config:
            if self._summary_repository:
                await self._summary_repository.initialize()
            if self._config_repository:
                await self._config_repository.initialize()
            if self._task_repository:
                await self._task_repository.initialize()

        # Initialize cache if configured
        if self._cache:
            await self._cache.initialize()

    async def cleanup(self):
        """Cleanup all services."""
        # Cleanup repositories
        if self._summary_repository:
            await self._summary_repository.close()
        if self._config_repository:
            await self._config_repository.close()
        if self._task_repository:
            await self._task_repository.close()

        # Cleanup cache
        if self._cache:
            await self._cache.close()

        # Cleanup Claude client
        if self._claude_client:
            await self._claude_client.close()

    async def health_check(self) -> dict:
        """Perform health check on all services."""
        health_status = {
            "status": "healthy",
            "services": {}
        }

        # Check summarization engine
        if self._summarization_engine:
            health_status["services"]["summarization_engine"] = \
                await self._summarization_engine.health_check()

        # Check database
        if self.config.database_config and self._summary_repository:
            try:
                health_status["services"]["database"] = \
                    await self._summary_repository.health_check()
            except Exception as e:
                health_status["services"]["database"] = {"status": "unhealthy", "error": str(e)}
                health_status["status"] = "degraded"

        # Check cache
        if self._cache:
            try:
                health_status["services"]["cache"] = await self._cache.health_check()
            except Exception as e:
                health_status["services"]["cache"] = {"status": "unhealthy", "error": str(e)}
                health_status["status"] = "degraded"

        return health_status
