"""
API test fixtures for Claude API and Webhook services.

Provides mock responses, request builders, and test data for API testing.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock
import json

import pytest
from anthropic.types import Message, ContentBlock, Usage


# Claude API Response Fixtures

def create_claude_message_response(
    content: str = "This is a test summary.",
    model: str = "claude-3-sonnet-20240229",
    input_tokens: int = 1000,
    output_tokens: int = 200,
    stop_reason: str = "end_turn",
    message_id: str = "msg_test123"
) -> Message:
    """Create a mock Anthropic Message response."""
    # Create content block
    content_block = MagicMock(spec=ContentBlock)
    content_block.text = content
    content_block.type = "text"

    # Create usage
    usage = MagicMock(spec=Usage)
    usage.input_tokens = input_tokens
    usage.output_tokens = output_tokens

    # Create message
    message = MagicMock(spec=Message)
    message.id = message_id
    message.type = "message"
    message.role = "assistant"
    message.content = [content_block]
    message.model = model
    message.stop_reason = stop_reason
    message.stop_sequence = None
    message.usage = usage

    return message


def create_claude_streaming_response(
    chunks: List[str],
    model: str = "claude-3-sonnet-20240229"
) -> AsyncMock:
    """Create a mock streaming response from Claude API."""
    async def mock_stream():
        for chunk in chunks:
            yield MagicMock(
                type="content_block_delta",
                delta=MagicMock(text=chunk, type="text_delta")
            )

    stream = AsyncMock()
    stream.__aiter__.return_value = mock_stream()
    return stream


@pytest.fixture
def claude_success_response():
    """Fixture for successful Claude API response."""
    return create_claude_message_response(
        content="This is a comprehensive summary of the discussion.",
        input_tokens=2500,
        output_tokens=450
    )


@pytest.fixture
def claude_truncated_response():
    """Fixture for truncated Claude API response (hit max_tokens)."""
    return create_claude_message_response(
        content="This summary was cut off due to token lim",
        stop_reason="max_tokens",
        input_tokens=3000,
        output_tokens=4000
    )


@pytest.fixture
def claude_error_responses():
    """Fixture providing various Claude API error scenarios."""
    from anthropic import (
        RateLimitError,
        AuthenticationError,
        APITimeoutError,
        APIConnectionError,
        BadRequestError
    )

    return {
        "rate_limit": RateLimitError("Rate limit exceeded", body={"error": {"message": "Rate limit exceeded"}}),
        "auth_error": AuthenticationError("Invalid API key"),
        "timeout": APITimeoutError("Request timeout"),
        "connection": APIConnectionError("Connection failed"),
        "bad_request": BadRequestError("Invalid request parameters", body={"error": {"message": "Invalid parameters"}})
    }


@pytest.fixture
def claude_cost_data():
    """Fixture for Claude API cost calculation test data."""
    return {
        "claude-3-sonnet-20240229": {
            "input_cost": 0.003,  # per 1K tokens
            "output_cost": 0.015,  # per 1K tokens
            "test_cases": [
                {"input": 1000, "output": 200, "expected_cost": 0.006},
                {"input": 5000, "output": 1000, "expected_cost": 0.030},
                {"input": 10000, "output": 2000, "expected_cost": 0.060},
            ]
        },
        "claude-3-opus-20240229": {
            "input_cost": 0.015,
            "output_cost": 0.075,
            "test_cases": [
                {"input": 1000, "output": 200, "expected_cost": 0.030},
            ]
        }
    }


# Webhook Request/Response Fixtures

@pytest.fixture
def webhook_request_summary():
    """Sample webhook request for triggering a summary."""
    return {
        "event": "trigger_summary",
        "guild_id": "123456789",
        "channel_id": "987654321",
        "time_range": {
            "start": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
            "end": datetime.utcnow().isoformat()
        },
        "options": {
            "summary_length": "detailed",
            "include_bots": False,
            "include_attachments": True
        },
        "callback_url": "https://example.com/webhook/callback"
    }


@pytest.fixture
def webhook_request_schedule():
    """Sample webhook request for scheduling a summary."""
    return {
        "event": "schedule_summary",
        "guild_id": "123456789",
        "channel_id": "987654321",
        "schedule": {
            "frequency": "daily",
            "time": "18:00",
            "timezone": "UTC"
        },
        "options": {
            "summary_length": "brief",
            "min_messages": 10
        }
    }


@pytest.fixture
def webhook_response_success():
    """Sample successful webhook response."""
    return {
        "status": "success",
        "summary_id": "sum_abc123def456",
        "message": "Summary generated successfully",
        "data": {
            "channel_id": "987654321",
            "message_count": 45,
            "summary_url": "https://example.com/summaries/sum_abc123def456"
        },
        "timestamp": datetime.utcnow().isoformat()
    }


@pytest.fixture
def webhook_response_error():
    """Sample error webhook response."""
    return {
        "status": "error",
        "error_code": "INSUFFICIENT_MESSAGES",
        "message": "Not enough messages to generate summary",
        "details": {
            "required": 5,
            "found": 2
        },
        "timestamp": datetime.utcnow().isoformat()
    }


@pytest.fixture
def webhook_authentication_headers():
    """Sample webhook authentication headers."""
    return {
        "X-Webhook-Signature": "sha256=abcdef1234567890",
        "X-Webhook-Timestamp": str(int(datetime.utcnow().timestamp())),
        "Content-Type": "application/json",
        "User-Agent": "SummaryBot-Webhook/1.0"
    }


# Summary Result Fixtures

@pytest.fixture
def sample_summary_results():
    """Collection of sample summary results for various scenarios."""
    from src.models.summary import SummaryResult, ActionItem, TechnicalTerm, Participant, SummarizationContext, Priority

    base_time = datetime.utcnow() - timedelta(hours=2)

    return {
        "technical_discussion": SummaryResult(
            id="sum_tech_001",
            channel_id="987654321",
            guild_id="123456789",
            start_time=base_time,
            end_time=datetime.utcnow(),
            message_count=48,
            key_points=[
                "Team discussed migration from REST to GraphQL",
                "Identified performance bottlenecks in current API",
                "Decided on incremental migration strategy"
            ],
            action_items=[
                ActionItem(
                    description="Create GraphQL schema for user endpoints",
                    assignee="dev_lead",
                    priority=Priority.HIGH,
                    deadline=datetime.utcnow() + timedelta(days=7)
                ),
                ActionItem(
                    description="Set up GraphQL server with Apollo",
                    assignee="backend_dev",
                    priority=Priority.HIGH
                )
            ],
            technical_terms=[
                TechnicalTerm(
                    term="GraphQL",
                    definition="A query language for APIs",
                    context="API architecture discussion",
                    source_message_id="msg_001"
                ),
                TechnicalTerm(
                    term="Apollo Server",
                    definition="GraphQL server implementation",
                    context="Technology selection",
                    source_message_id="msg_015"
                )
            ],
            participants=[
                Participant(
                    user_id="111111111",
                    display_name="Dev Lead",
                    message_count=15,
                    key_contributions=["Proposed GraphQL migration", "Outlined implementation plan"]
                ),
                Participant(
                    user_id="222222222",
                    display_name="Backend Dev",
                    message_count=12,
                    key_contributions=["Identified API bottlenecks", "Suggested caching strategy"]
                )
            ],
            summary_text="The team held a technical discussion about migrating from REST to GraphQL...",
            context=SummarizationContext(
                channel_name="backend-dev",
                guild_name="Tech Team",
                total_participants=4,
                time_span_hours=2.0,
                message_types={"text": 45, "code": 3},
                dominant_topics=["API architecture", "Performance optimization"],
                thread_count=2
            )
        ),
        "planning_session": SummaryResult(
            id="sum_plan_001",
            channel_id="987654322",
            guild_id="123456789",
            start_time=base_time,
            end_time=datetime.utcnow(),
            message_count=32,
            key_points=[
                "Q1 roadmap priorities defined",
                "Resource allocation for new features",
                "Timeline for beta release established"
            ],
            action_items=[
                ActionItem(
                    description="Finalize feature specifications",
                    assignee="product_owner",
                    priority=Priority.HIGH,
                    deadline=datetime.utcnow() + timedelta(days=3)
                ),
                ActionItem(
                    description="Schedule design review meeting",
                    assignee="design_lead",
                    priority=Priority.MEDIUM,
                    deadline=datetime.utcnow() + timedelta(days=5)
                )
            ],
            participants=[
                Participant(
                    user_id="333333333",
                    display_name="Product Owner",
                    message_count=10,
                    key_contributions=["Defined Q1 priorities"]
                ),
                Participant(
                    user_id="444444444",
                    display_name="Tech Lead",
                    message_count=8,
                    key_contributions=["Proposed technical approach"]
                )
            ],
            summary_text="Team planning session focused on Q1 roadmap and resource allocation...",
            context=SummarizationContext(
                channel_name="project-planning",
                guild_name="Tech Team",
                total_participants=6,
                time_span_hours=1.5,
                message_types={"text": 32},
                dominant_topics=["Roadmap planning", "Resource allocation"]
            )
        ),
        "minimal": SummaryResult(
            id="sum_min_001",
            channel_id="987654323",
            guild_id="123456789",
            start_time=base_time,
            end_time=datetime.utcnow(),
            message_count=8,
            key_points=["Brief discussion about deployment"],
            summary_text="Short conversation about deployment procedures.",
            participants=[
                Participant(
                    user_id="555555555",
                    display_name="DevOps",
                    message_count=5
                )
            ]
        )
    }


# API Client Mock Builders

def create_mock_anthropic_client(
    default_response: Optional[Message] = None,
    should_fail: bool = False,
    failure_type: str = "timeout"
) -> AsyncMock:
    """Create a mock Anthropic async client."""
    from anthropic import AsyncAnthropic

    client = AsyncMock(spec=AsyncAnthropic)

    if should_fail:
        # Configure to raise errors
        from anthropic import APITimeoutError, RateLimitError, AuthenticationError

        error_map = {
            "timeout": APITimeoutError("Request timeout"),
            "rate_limit": RateLimitError("Rate limit exceeded", body={"error": {"message": "Rate limit"}}),
            "auth": AuthenticationError("Invalid API key")
        }

        client.messages.create.side_effect = error_map.get(failure_type, APITimeoutError("Error"))
    else:
        # Configure successful response
        response = default_response or create_claude_message_response()
        client.messages.create.return_value = response

    return client


@pytest.fixture
def mock_anthropic_client_factory():
    """Factory for creating configured Anthropic client mocks."""
    return create_mock_anthropic_client


# Webhook Server Mock

@pytest.fixture
def mock_webhook_server():
    """Mock webhook server for testing."""
    from aiohttp import web

    server = AsyncMock()
    server.start = AsyncMock()
    server.stop = AsyncMock()
    server.is_running = MagicMock(return_value=True)

    # Mock request handler
    async def mock_handler(request):
        return web.json_response({"status": "success"})

    server.app = MagicMock()
    server.app.router = MagicMock()
    server.app.router.add_post = MagicMock()

    return server


# API Authentication

@pytest.fixture
def api_tokens():
    """Test API tokens and secrets."""
    return {
        "valid_token": "sk-ant-test-valid-token-12345",
        "invalid_token": "sk-ant-test-invalid-token",
        "webhook_secret": "webhook_secret_key_12345",
        "jwt_secret": "jwt_secret_for_testing"
    }


@pytest.fixture
def signed_webhook_payload():
    """Generate a properly signed webhook payload."""
    import hmac
    import hashlib

    payload = {
        "event": "test_event",
        "data": {"test": "data"}
    }

    secret = "webhook_secret_key_12345"
    payload_json = json.dumps(payload, separators=(',', ':'))
    signature = hmac.new(
        secret.encode(),
        payload_json.encode(),
        hashlib.sha256
    ).hexdigest()

    return {
        "payload": payload,
        "signature": f"sha256={signature}",
        "headers": {
            "X-Webhook-Signature": f"sha256={signature}",
            "Content-Type": "application/json"
        }
    }


# Test Data Generators

def generate_conversation_messages(
    count: int = 50,
    topic: str = "technical",
    include_code: bool = False
) -> List[Dict[str, Any]]:
    """Generate realistic conversation message data."""
    topics = {
        "technical": [
            "We should refactor the authentication module",
            "The database queries are too slow",
            "Let's implement caching for better performance",
            "Need to add proper error handling here"
        ],
        "planning": [
            "What are our priorities for next sprint?",
            "We need to allocate resources for the new feature",
            "Timeline looks aggressive, can we adjust?",
            "Let's schedule a design review"
        ],
        "casual": [
            "Good morning everyone!",
            "How's everyone doing today?",
            "Great work on the last release!",
            "Thanks for the help!"
        ]
    }

    templates = topics.get(topic, topics["technical"])
    messages = []

    for i in range(count):
        message = {
            "id": f"msg_{i+1:06d}",
            "content": templates[i % len(templates)],
            "author": f"user_{(i % 5) + 1}",
            "timestamp": (datetime.utcnow() - timedelta(minutes=count-i)).isoformat()
        }

        if include_code and i % 10 == 0:
            message["content"] += "\n```python\ndef example():\n    pass\n```"

        messages.append(message)

    return messages


@pytest.fixture
def conversation_data_factory():
    """Factory for generating conversation test data."""
    return generate_conversation_messages
