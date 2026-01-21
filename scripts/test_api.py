#!/usr/bin/env python3
"""
Test script to run the dashboard API locally without Discord bot.
"""

import asyncio
import os
import sys

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set minimal environment variables for testing
os.environ.setdefault("DISCORD_CLIENT_ID", "test-client-id")
os.environ.setdefault("DISCORD_CLIENT_SECRET", "test-client-secret")
os.environ.setdefault("DISCORD_REDIRECT_URI", "http://localhost:3000/callback")
os.environ.setdefault("DASHBOARD_JWT_SECRET", "test-jwt-secret-for-local-development")
os.environ.setdefault("DASHBOARD_ENCRYPTION_KEY", "")  # Will generate ephemeral

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import dashboard router
from src.dashboard import create_dashboard_router

def create_test_app() -> FastAPI:
    """Create a test FastAPI app with dashboard routes."""
    app = FastAPI(
        title="SummaryBot Dashboard API - Test Mode",
        description="Testing the dashboard API without Discord bot",
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS for local development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health endpoint
    @app.get("/health")
    async def health():
        return {"status": "healthy", "mode": "test"}

    @app.get("/")
    async def root():
        return {
            "name": "SummaryBot Dashboard API",
            "mode": "test",
            "docs": "/docs",
            "note": "Running without Discord bot - some endpoints will return mock data"
        }

    # Add dashboard routes (without Discord bot)
    dashboard_router = create_dashboard_router(
        discord_bot=None,
        summarization_engine=None,
        task_scheduler=None,
        config_manager=None,
    )
    app.include_router(dashboard_router)

    return app


if __name__ == "__main__":
    print("=" * 60)
    print("Starting SummaryBot Dashboard API in TEST MODE")
    print("=" * 60)
    print()
    print("API Documentation: http://localhost:8000/docs")
    print("Health Check: http://localhost:8000/health")
    print()
    print("Note: Discord bot is not connected. Auth and guild")
    print("endpoints will have limited functionality.")
    print()
    print("=" * 60)

    app = create_test_app()
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
