"""
Dashboard API route modules.
"""

from typing import Optional

# Service references (set by router.py)
_discord_bot = None
_summarization_engine = None
_task_scheduler = None
_config_manager = None


def set_services(
    discord_bot=None,
    summarization_engine=None,
    task_scheduler=None,
    config_manager=None,
):
    """Set service references for route handlers."""
    global _discord_bot, _summarization_engine, _task_scheduler, _config_manager
    _discord_bot = discord_bot
    _summarization_engine = summarization_engine
    _task_scheduler = task_scheduler
    _config_manager = config_manager


def get_discord_bot():
    """Get Discord bot instance."""
    return _discord_bot


def get_summarization_engine():
    """Get summarization engine."""
    return _summarization_engine


def get_task_scheduler():
    """Get task scheduler."""
    return _task_scheduler


def get_config_manager():
    """Get config manager."""
    return _config_manager


# Import routers
from .auth import router as auth_router
from .guilds import router as guilds_router
from .summaries import router as summaries_router
from .schedules import router as schedules_router
from .webhooks import router as webhooks_router
from .events import router as events_router

__all__ = [
    "auth_router",
    "guilds_router",
    "summaries_router",
    "schedules_router",
    "webhooks_router",
    "events_router",
    "set_services",
    "get_discord_bot",
    "get_summarization_engine",
    "get_task_scheduler",
    "get_config_manager",
]
