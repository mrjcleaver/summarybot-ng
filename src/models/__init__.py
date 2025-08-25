"""
Data models module for Summary Bot NG.

This module provides data models and DTOs for all domain objects 
with serialization support.
"""

from .base import BaseModel, SerializableModel
from .summary import (
    SummaryResult, SummaryOptions, ActionItem, TechnicalTerm, 
    Participant, SummarizationContext
)
from .message import (
    ProcessedMessage, MessageReference, AttachmentInfo, ThreadInfo,
    CodeBlock, MessageMention
)
from .user import User, UserPermissions
from .task import ScheduledTask, TaskResult, TaskStatus
from .webhook import WebhookRequest, WebhookResponse, WebhookDelivery

__all__ = [
    # Base models
    'BaseModel',
    'SerializableModel',
    
    # Summary models
    'SummaryResult',
    'SummaryOptions', 
    'ActionItem',
    'TechnicalTerm',
    'Participant',
    'SummarizationContext',
    
    # Message models
    'ProcessedMessage',
    'MessageReference',
    'AttachmentInfo',
    'ThreadInfo',
    'CodeBlock',
    'MessageMention',
    
    # User models
    'User',
    'UserPermissions',
    
    # Task models
    'ScheduledTask',
    'TaskResult',
    'TaskStatus',
    
    # Webhook models
    'WebhookRequest',
    'WebhookResponse',
    'WebhookDelivery'
]