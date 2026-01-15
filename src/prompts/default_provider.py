"""
Default prompt provider for built-in prompts.

Provides fallback prompts when custom prompts are unavailable.
"""

import logging
from pathlib import Path
from typing import Optional, Dict

from .models import PromptContext, ResolvedPrompt, PromptSource

logger = logging.getLogger(__name__)


class DefaultPromptProvider:
    """
    Provides built-in default prompts.

    Prompts are loaded from the defaults/ directory and cached in memory.
    """

    def __init__(self):
        """Initialize the default prompt provider."""
        self.defaults_dir = Path(__file__).parent / "defaults"
        self._cache: Dict[str, str] = {}
        self._load_defaults()

    def _load_defaults(self) -> None:
        """Load all default prompts into memory cache."""
        if not self.defaults_dir.exists():
            logger.warning(f"Defaults directory not found: {self.defaults_dir}")
            return

        for prompt_file in self.defaults_dir.glob("*.md"):
            prompt_name = prompt_file.stem
            try:
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self._cache[prompt_name] = content
                    logger.debug(f"Loaded default prompt: {prompt_name}")
            except Exception as e:
                logger.error(f"Failed to load default prompt {prompt_name}: {e}")

    def get_prompt(self, context: PromptContext) -> Optional[ResolvedPrompt]:
        """
        Get default prompt for the given context.

        Args:
            context: Prompt context

        Returns:
            ResolvedPrompt or None if no matching default
        """
        # Try category-specific prompt first
        category_prompt = self._cache.get(context.category)
        if category_prompt:
            return ResolvedPrompt(
                content=category_prompt,
                source=PromptSource.DEFAULT,
                version="v1",
                variables=context.to_dict()
            )

        # Fall back to default.md
        default_prompt = self._cache.get("default")
        if default_prompt:
            return ResolvedPrompt(
                content=default_prompt,
                source=PromptSource.DEFAULT,
                version="v1",
                variables=context.to_dict()
            )

        return None

    def get_fallback_prompt(self) -> ResolvedPrompt:
        """
        Get the global fallback prompt (always available).

        Returns:
            ResolvedPrompt with hardcoded fallback
        """
        # Try to use default.md if available
        if "default" in self._cache:
            return ResolvedPrompt(
                content=self._cache["default"],
                source=PromptSource.FALLBACK,
                version="v1"
            )

        # Ultimate fallback - hardcoded
        return ResolvedPrompt(
            content=self._get_hardcoded_fallback(),
            source=PromptSource.FALLBACK,
            version="v1"
        )

    def _get_hardcoded_fallback(self) -> str:
        """Get hardcoded fallback prompt (used when files can't be read)."""
        return """# Discord Conversation Summary

You are a helpful AI assistant that creates summaries of Discord conversations.

Analyze the following messages and provide a clear, concise summary:

{messages}

Please organize your summary with:
- Main topics discussed
- Key decisions or conclusions
- Important points raised
- Any action items or follow-ups

Use Markdown formatting for readability.
"""

    @property
    def available_categories(self) -> list[str]:
        """Get list of available category prompts."""
        return [name for name in self._cache.keys() if name != "default"]
