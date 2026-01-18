"""
Configuration constants for the summarization bot.
Single source of truth for all default values.
"""

# Model Configuration
DEFAULT_SUMMARIZATION_MODEL = "openrouter/auto"
DEFAULT_BRIEF_MODEL = "claude-3-haiku-20240307"

# Valid model choices
VALID_MODELS = [
    "claude-3-opus-20240229",
    "claude-3-sonnet-20240229",
    "claude-3-haiku-20240307",
    "claude-3-5-sonnet-20240620",
    "openrouter/auto"
]

# Model aliases for backward compatibility
MODEL_ALIASES = {
    "anthropic/claude-3-sonnet-20240229": "claude-3-sonnet-20240229",
    "anthropic/claude-3-haiku-20240307": "claude-3-haiku-20240307",
    "anthropic/claude-3-opus-20240229": "claude-3-opus-20240229"
}
