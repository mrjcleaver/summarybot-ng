"""
Webhook service module for Summary Bot NG.

This module provides HTTP API endpoints for external integrations
and webhook handling using FastAPI.
"""

from .server import WebhookServer
from .endpoints import create_summary_router
from .auth import APIKeyAuth, JWTAuth
from .validators import (
    SummaryRequestModel,
    SummaryResponseModel,
    ScheduleRequestModel,
    ScheduleResponseModel,
    ErrorResponseModel
)
from .formatters import ResponseFormatter

__all__ = [
    "WebhookServer",
    "create_summary_router",
    "APIKeyAuth",
    "JWTAuth",
    "SummaryRequestModel",
    "SummaryResponseModel",
    "ScheduleRequestModel",
    "ScheduleResponseModel",
    "ErrorResponseModel",
    "ResponseFormatter"
]
