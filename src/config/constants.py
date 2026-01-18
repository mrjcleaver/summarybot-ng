"""
Configuration constants for the summarization bot.
Single source of truth for all default values.
"""

# Model Configuration
# Note: Using Haiku as default since it's reliably available on OpenRouter
# Users can configure other models via SUMMARIZATION_MODEL env var or /config command
DEFAULT_SUMMARIZATION_MODEL = "claude-3-haiku-20240307"
DEFAULT_BRIEF_MODEL = "claude-3-haiku-20240307"

# Valid model choices
# Note: Only include models verified to work on OpenRouter
VALID_MODELS = [
    "claude-3-opus-20240229",
    "claude-3-haiku-20240307",
    "claude-3-5-sonnet-20240620",
    "claude-3-5-sonnet-20241022"
]

# Model aliases for backward compatibility
MODEL_ALIASES = {
    "anthropic/claude-3-sonnet-20240229": "claude-3-sonnet-20240229",
    "anthropic/claude-3-haiku-20240307": "claude-3-haiku-20240307",
    "anthropic/claude-3-opus-20240229": "claude-3-opus-20240229"
}
