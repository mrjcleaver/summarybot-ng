"""
Configuration constants for the summarization bot.
Single source of truth for all default values.
"""

# Model Configuration
# Note: Using Haiku as default since it's reliably available on OpenRouter
# Users can configure other models via SUMMARIZATION_MODEL env var or /config command
# Updated 2026-01 to use current OpenRouter model IDs
DEFAULT_SUMMARIZATION_MODEL = "anthropic/claude-3-haiku"
DEFAULT_BRIEF_MODEL = "anthropic/claude-3-haiku"
DEFAULT_COMPREHENSIVE_MODEL = "anthropic/claude-sonnet-4.5"  # Best model for comprehensive summaries

# Valid model choices (current OpenRouter model IDs as of 2026-01)
VALID_MODELS = [
    "anthropic/claude-sonnet-4.5",
    "anthropic/claude-sonnet-4",
    "anthropic/claude-3.7-sonnet",
    "anthropic/claude-3.5-sonnet",
    "anthropic/claude-3.5-haiku",
    "anthropic/claude-3-haiku",
    "anthropic/claude-opus-4.5",
    "anthropic/claude-opus-4",
]

# Model aliases for backward compatibility (old format -> new format)
MODEL_ALIASES = {
    "claude-3-haiku-20240307": "anthropic/claude-3-haiku",
    "claude-3-5-sonnet-20240620": "anthropic/claude-3.5-sonnet",
    "claude-3-5-sonnet-20241022": "anthropic/claude-3.5-sonnet",
    "claude-3-opus-20240229": "anthropic/claude-opus-4",
    "claude-3-sonnet-20240229": "anthropic/claude-3.5-sonnet",
}
