"""
Dashboard API module for SummaryBot NG.

Provides a REST API for the web dashboard with Discord OAuth authentication.
"""

from .router import create_dashboard_router
from .auth import DashboardAuth
from .models import DashboardSession, DashboardUser

__all__ = [
    "create_dashboard_router",
    "DashboardAuth",
    "DashboardSession",
    "DashboardUser",
]
