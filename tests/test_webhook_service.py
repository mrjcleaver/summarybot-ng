"""
Tests for webhook service module.
"""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch

from src.config.settings import BotConfig, WebhookConfig
from src.summarization.engine import SummarizationEngine
from src.webhook_service.server import WebhookServer
from src.webhook_service.validators import SummaryRequestModel, TimeRangeModel
from src.webhook_service.formatters import ResponseFormatter, OutputFormat
from src.models.summary import SummaryResult, ActionItem, TechnicalTerm, Participant, Priority


@pytest.fixture
def test_config():
    """Create test configuration."""
    return BotConfig(
        discord_token="test_discord_token",
        claude_api_key="test_claude_key",
        webhook_config=WebhookConfig(
            host="127.0.0.1",
            port=5000,
            enabled=True,
            cors_origins=["http://localhost:3000"],
            rate_limit=100,
            jwt_secret="test-secret-key",
            jwt_expiration_minutes=60,
            api_keys={
                "test_api_key_123": "test_user_123"
            }
        )
    )


@pytest.fixture
def mock_engine():
    """Create mock summarization engine."""
    engine = Mock(spec=SummarizationEngine)

    # Mock health check
    engine.health_check = AsyncMock(return_value={
        "status": "healthy",
        "claude_api": "healthy",
        "cache": "healthy"
    })

    return engine


@pytest.fixture
def client(test_config, mock_engine):
    """Create test client."""
    server = WebhookServer(test_config, mock_engine)
    return TestClient(server.get_app())


class TestWebhookServer:
    """Test webhook server functionality."""

    def test_root_endpoint(self, client):
        """Test root endpoint returns API info."""
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "Summary Bot NG API"
        assert data["version"] == "2.0.0"
        assert "docs" in data
        assert "health" in data

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "services" in data
        assert data["services"]["summarization_engine"] == "healthy"

    def test_openapi_docs(self, client):
        """Test OpenAPI documentation is available."""
        response = client.get("/openapi.json")
        assert response.status_code == 200

        data = response.json()
        assert data["info"]["title"] == "Summary Bot NG API"
        assert data["info"]["version"] == "2.0.0"

    def test_cors_headers(self, client):
        """Test CORS headers are set correctly."""
        response = client.options(
            "/api/v1/summarize",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST"
            }
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers


class TestAuthentication:
    """Test authentication functionality."""

    def test_api_key_auth_success(self, client):
        """Test successful API key authentication."""
        response = client.post(
            "/api/v1/summarize",
            headers={
                "X-API-Key": "test_api_key_123",
                "Content-Type": "application/json"
            },
            json={
                "channel_id": "123456789012345678",
                "summary_type": "detailed"
            }
        )
        # Should not return 401 Unauthorized
        assert response.status_code != 401

    def test_api_key_auth_failure(self, client):
        """Test failed API key authentication."""
        response = client.post(
            "/api/v1/summarize",
            headers={
                "X-API-Key": "invalid_key",
                "Content-Type": "application/json"
            },
            json={
                "channel_id": "123456789012345678",
                "summary_type": "detailed"
            }
        )
        assert response.status_code == 401

    def test_missing_auth(self, client):
        """Test request without authentication."""
        response = client.post(
            "/api/v1/summarize",
            headers={"Content-Type": "application/json"},
            json={
                "channel_id": "123456789012345678",
                "summary_type": "detailed"
            }
        )
        assert response.status_code == 401


class TestValidators:
    """Test request validation models."""

    def test_summary_request_valid(self):
        """Test valid summary request."""
        request = SummaryRequestModel(
            channel_id="123456789012345678",
            summary_type="detailed",
            max_length=4000,
            temperature=0.3
        )

        assert request.channel_id == "123456789012345678"
        assert request.summary_type == "detailed"
        assert request.max_length == 4000
        assert request.temperature == 0.3

    def test_summary_request_defaults(self):
        """Test summary request with defaults."""
        request = SummaryRequestModel(
            channel_id="123456789012345678"
        )

        assert request.summary_type == "detailed"
        assert request.output_format == "json"
        assert request.include_threads is True
        assert request.exclude_bots is True

    def test_time_range_validation(self):
        """Test time range validation."""
        now = datetime.utcnow()
        past = datetime(2024, 1, 1, 0, 0, 0)

        # Valid range
        time_range = TimeRangeModel(start=past, end=now)
        assert time_range.start == past
        assert time_range.end == now

    def test_time_range_invalid_order(self):
        """Test time range with end before start."""
        now = datetime.utcnow()
        past = datetime(2024, 1, 1, 0, 0, 0)

        with pytest.raises(ValueError):
            TimeRangeModel(start=now, end=past)

    def test_max_length_bounds(self):
        """Test max_length parameter bounds."""
        # Too small
        with pytest.raises(ValueError):
            SummaryRequestModel(
                channel_id="123456789012345678",
                max_length=50
            )

        # Too large
        with pytest.raises(ValueError):
            SummaryRequestModel(
                channel_id="123456789012345678",
                max_length=20000
            )

    def test_temperature_bounds(self):
        """Test temperature parameter bounds."""
        # Too low
        with pytest.raises(ValueError):
            SummaryRequestModel(
                channel_id="123456789012345678",
                temperature=-0.1
            )

        # Too high
        with pytest.raises(ValueError):
            SummaryRequestModel(
                channel_id="123456789012345678",
                temperature=1.1
            )


class TestFormatters:
    """Test response formatting utilities."""

    @pytest.fixture
    def sample_summary(self):
        """Create sample summary result."""
        from src.models.summary import SummarizationContext

        return SummaryResult(
            id="sum_123",
            channel_id="123456789012345678",
            guild_id="987654321098765432",
            start_time=datetime(2024, 1, 1, 0, 0, 0),
            end_time=datetime(2024, 1, 1, 23, 59, 59),
            message_count=100,
            summary_text="This is a test summary.",
            key_points=["Point 1", "Point 2"],
            action_items=[
                ActionItem(
                    description="Test action",
                    assignee="user123",
                    priority=Priority.HIGH
                )
            ],
            technical_terms=[
                TechnicalTerm(
                    term="API",
                    definition="Application Programming Interface"
                )
            ],
            participants=[
                Participant(
                    user_id="123",
                    display_name="Alice",
                    message_count=50,
                    key_contributions=["Proposed solution"]
                )
            ],
            created_at=datetime.utcnow(),
            context=SummarizationContext(
                channel_name="general",
                guild_name="Test Server"
            )
        )

    def test_format_json(self, sample_summary):
        """Test JSON formatting."""
        result = ResponseFormatter.format_summary(sample_summary, OutputFormat.JSON)
        assert isinstance(result, str)
        assert "sum_123" in result
        assert "Point 1" in result

    def test_format_markdown(self, sample_summary):
        """Test Markdown formatting."""
        result = ResponseFormatter.format_summary(sample_summary, OutputFormat.MARKDOWN)
        assert isinstance(result, str)
        assert "#" in result  # Headers
        assert "This is a test summary" in result

    def test_format_html(self, sample_summary):
        """Test HTML formatting."""
        result = ResponseFormatter.format_summary(sample_summary, OutputFormat.HTML)
        assert isinstance(result, str)
        assert "<!DOCTYPE html>" in result
        assert "<html>" in result
        assert "This is a test summary" in result

    def test_format_plain_text(self, sample_summary):
        """Test plain text formatting."""
        result = ResponseFormatter.format_summary(sample_summary, OutputFormat.PLAIN_TEXT)
        assert isinstance(result, str)
        assert "SUMMARY" in result
        assert "This is a test summary" in result

    def test_format_error(self):
        """Test error formatting."""
        error = ResponseFormatter.format_error(
            error_code="TEST_ERROR",
            message="This is a test error",
            details={"field": "test"},
            request_id="req_123"
        )

        assert error["error"] == "TEST_ERROR"
        assert error["message"] == "This is a test error"
        assert error["details"]["field"] == "test"
        assert error["request_id"] == "req_123"

    def test_format_success(self):
        """Test success formatting."""
        success = ResponseFormatter.format_success(
            data={"test": "data"},
            message="Operation successful",
            request_id="req_123"
        )

        assert success["success"] is True
        assert success["message"] == "Operation successful"
        assert success["data"]["test"] == "data"
        assert success["request_id"] == "req_123"


class TestRateLimiting:
    """Test rate limiting functionality."""

    def test_rate_limit_headers(self, client):
        """Test rate limit headers are present."""
        response = client.get("/health")

        # Rate limit headers should be present
        assert "x-ratelimit-limit" in response.headers
        assert "x-ratelimit-remaining" in response.headers
        assert "x-ratelimit-reset" in response.headers


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
