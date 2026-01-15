"""
Fallback chain executor for reliable prompt resolution.

Implements 4-level fallback strategy:
1. Custom prompt from GitHub repository
2. Stale cache (up to 1 hour old)
3. Default prompt for category
4. Global fallback prompt

Ensures the bot always has a working prompt, even during GitHub outages.
"""

import logging
from typing import Optional, Callable, Awaitable

from .models import PromptContext, ResolvedPrompt, PromptSource
from .cache import PromptCacheManager
from .default_provider import DefaultPromptProvider
from .github_client import GitHubRateLimitError, GitHubTimeoutError

logger = logging.getLogger(__name__)


class FallbackChainExecutor:
    """
    Executes fallback chain for prompt resolution.

    Guarantees a prompt is always returned, falling back through
    multiple sources until a working prompt is found.
    """

    def __init__(
        self,
        cache_manager: PromptCacheManager,
        default_provider: DefaultPromptProvider
    ):
        """
        Initialize the fallback chain executor.

        Args:
            cache_manager: Cache manager for checking stale cache
            default_provider: Default prompt provider
        """
        self.cache_manager = cache_manager
        self.default_provider = default_provider

    async def resolve_with_fallback(
        self,
        guild_id: str,
        context: PromptContext,
        custom_fetcher: Optional[Callable[[str, PromptContext], Awaitable[Optional[ResolvedPrompt]]]] = None
    ) -> ResolvedPrompt:
        """
        Resolve prompt with full fallback chain.

        Args:
            guild_id: Discord guild ID
            context: Prompt context
            custom_fetcher: Optional async function to fetch custom prompt from GitHub

        Returns:
            ResolvedPrompt (guaranteed to return something)

        Fallback Order:
        1. Custom prompt from GitHub (if custom_fetcher provided)
        2. Stale cache (up to 1 hour old)
        3. Default prompt for category
        4. Global fallback prompt
        """
        # LEVEL 1: Try custom prompt from GitHub
        if custom_fetcher:
            try:
                logger.debug(f"Attempting custom prompt fetch for guild {guild_id}")
                custom_prompt = await custom_fetcher(guild_id, context)

                if custom_prompt:
                    logger.info(
                        f"Using custom prompt for guild {guild_id} "
                        f"(source={custom_prompt.source.value})"
                    )
                    return custom_prompt

            except GitHubRateLimitError as e:
                logger.warning(
                    f"GitHub rate limit exceeded for guild {guild_id}: {e}"
                )
                # Continue to fallback

            except GitHubTimeoutError as e:
                logger.error(
                    f"GitHub timeout for guild {guild_id}: {e}"
                )
                # Continue to fallback

            except Exception as e:
                logger.error(
                    f"Custom prompt fetch failed for guild {guild_id}: {e}",
                    exc_info=True
                )
                # Continue to fallback

        # LEVEL 2: Try stale cache (even if expired)
        try:
            stale_prompt = await self.cache_manager.get_stale(guild_id, context)
            if stale_prompt:
                logger.warning(
                    f"Using stale cached prompt for guild {guild_id} "
                    f"(age={stale_prompt.age_minutes:.1f}m)"
                )

                return ResolvedPrompt(
                    content=stale_prompt.content,
                    source=PromptSource.CACHED,
                    version=stale_prompt.version,
                    is_stale=True,
                    repo_url=stale_prompt.repo_url
                )
        except Exception as e:
            logger.error(f"Failed to fetch stale cache: {e}", exc_info=True)

        # LEVEL 3: Try default prompt for category
        try:
            default_prompt = self.default_provider.get_prompt(context)
            if default_prompt:
                logger.info(
                    f"Using default prompt for guild {guild_id} "
                    f"(category={context.category})"
                )
                return default_prompt
        except Exception as e:
            logger.error(f"Failed to fetch default prompt: {e}", exc_info=True)

        # LEVEL 4: Global fallback (always available)
        logger.warning(
            f"Using global fallback prompt for guild {guild_id} "
            "(all other sources failed)"
        )
        return self.default_provider.get_fallback_prompt()

    async def try_custom_with_stale_fallback(
        self,
        guild_id: str,
        context: PromptContext,
        custom_fetcher: Callable[[str, PromptContext], Awaitable[Optional[ResolvedPrompt]]]
    ) -> Optional[ResolvedPrompt]:
        """
        Try custom prompt, fall back to stale cache on failure.

        This is useful for when we want to attempt a fresh fetch but
        don't want to wait for the full fallback chain.

        Args:
            guild_id: Discord guild ID
            context: Prompt context
            custom_fetcher: Async function to fetch custom prompt

        Returns:
            ResolvedPrompt or None if both custom and stale fail
        """
        # Try custom first
        try:
            custom_prompt = await custom_fetcher(guild_id, context)
            if custom_prompt:
                return custom_prompt
        except Exception as e:
            logger.error(f"Custom fetch failed: {e}", exc_info=True)

        # Fall back to stale
        stale_prompt = await self.cache_manager.get_stale(guild_id, context)
        if stale_prompt:
            logger.info(f"Using stale cache as fallback (age={stale_prompt.age_minutes:.1f}m)")
            return ResolvedPrompt(
                content=stale_prompt.content,
                source=PromptSource.CACHED,
                version=stale_prompt.version,
                is_stale=True,
                repo_url=stale_prompt.repo_url
            )

        return None

    def should_use_cache(
        self,
        guild_id: str,
        last_sync_status: Optional[str] = None
    ) -> bool:
        """
        Determine if we should skip GitHub and use cache/defaults.

        Args:
            guild_id: Discord guild ID
            last_sync_status: Status of last GitHub sync

        Returns:
            True if should skip GitHub and use cache
        """
        # If last sync was rate limited, use cache for a while
        if last_sync_status == "rate_limited":
            logger.info(f"Skipping GitHub fetch for guild {guild_id} (rate limited)")
            return True

        # If last sync failed multiple times, use cache
        if last_sync_status == "failed":
            logger.info(f"Skipping GitHub fetch for guild {guild_id} (previous failures)")
            return True

        return False
