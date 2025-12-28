"""
Discord Bot module for Summary Bot NG.

This module provides the Discord bot client and event handling.
"""

from .bot import SummaryBot
from .events import EventHandler
from .commands import CommandRegistry
from .utils import (
    create_embed,
    create_error_embed,
    create_success_embed,
    create_info_embed,
    format_timestamp,
    truncate_text
)

__all__ = [
    'SummaryBot',
    'EventHandler',
    'CommandRegistry',
    'create_embed',
    'create_error_embed',
    'create_success_embed',
    'create_info_embed',
    'format_timestamp',
    'truncate_text'
]
