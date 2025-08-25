"""
Summarization engine module for Summary Bot NG.

This module provides core AI-powered summarization logic with Claude API integration.
"""

from .engine import SummarizationEngine
from .claude_client import ClaudeClient, ClaudeResponse, ClaudeOptions
from .prompt_builder import PromptBuilder, SummarizationPrompt
from .response_parser import ResponseParser, ParsedSummary
from .cache import SummaryCache
from .optimization import SummaryOptimizer

__all__ = [
    'SummarizationEngine',
    'ClaudeClient',
    'ClaudeResponse', 
    'ClaudeOptions',
    'PromptBuilder',
    'SummarizationPrompt',
    'ResponseParser',
    'ParsedSummary',
    'SummaryCache',
    'SummaryOptimizer'
]