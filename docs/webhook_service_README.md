# Webhook Service Module

## Overview

The webhook service module provides a FastAPI-based HTTP API for external integrations with Summary Bot NG. It exposes RESTful endpoints for creating summaries, retrieving summary results, and scheduling automated summaries.

## Architecture

The webhook service follows a modular architecture:

```
webhook_service/
├── __init__.py          # Public API exports
├── server.py           # FastAPI application and server lifecycle
├── endpoints.py        # API endpoint handlers
├── auth.py            # Authentication middleware (API keys & JWT)
├── validators.py      # Pydantic request/response models
└── formatters.py      # Response formatting utilities
```

## Features

### 1. Authentication & Security

- **API Key Authentication**: Via `X-API-Key` header
- **JWT Token Authentication**: Via `Authorization: Bearer <token>` header
- **Rate Limiting**: Configurable requests per minute
- **CORS Support**: Configurable allowed origins
- **Request Validation**: Automatic via Pydantic models

### 2. API Endpoints

#### POST /api/v1/summarize
Create a new summary from Discord messages.

**Request Body:**
```json
{
  "channel_id": "123456789012345678",
  "guild_id": "987654321098765432",
  "time_range": {
    "start": "2024-01-01T00:00:00Z",
    "end": "2024-01-01T23:59:59Z"
  },
  "summary_type": "detailed",
  "output_format": "json",
  "max_length": 4000,
  "include_threads": true,
  "exclude_bots": true,
  "include_technical_terms": true,
  "include_action_items": true,
  "custom_prompt": null,
  "model": "claude-3-sonnet-20240229",
  "temperature": 0.3,
  "webhook_url": "https://example.com/webhook"
}
```

**Response:**
```json
{
  "id": "sum_1234567890",
  "channel_id": "123456789012345678",
  "guild_id": "987654321098765432",
  "summary_text": "The team discussed...",
  "key_points": ["Point 1", "Point 2"],
  "action_items": [
    {
      "description": "Implement feature X",
      "assignee": "user123",
      "priority": "high",
      "deadline": "2024-01-15T00:00:00Z"
    }
  ],
  "technical_terms": [
    {
      "term": "REST",
      "definition": "Representational State Transfer"
    }
  ],
  "participants": [
    {
      "user_id": "123",
      "display_name": "Alice",
      "message_count": 42,
      "key_contributions": ["Proposed solution"]
    }
  ],
  "message_count": 150,
  "start_time": "2024-01-01T00:00:00Z",
  "end_time": "2024-01-01T23:59:59Z",
  "created_at": "2024-01-02T00:00:00Z",
  "metadata": {
    "input_tokens": 1500,
    "output_tokens": 500,
    "cost_usd": 0.015
  }
}
```

#### GET /api/v1/summary/{summary_id}
Retrieve a previously generated summary.

**Response:** Same as POST /api/v1/summarize

#### POST /api/v1/schedule
Schedule automatic summary generation.

**Request Body:**
```json
{
  "channel_id": "123456789012345678",
  "guild_id": "987654321098765432",
  "frequency": "daily",
  "summary_type": "detailed",
  "webhook_url": "https://example.com/webhook",
  "enabled": true
}
```

**Response:**
```json
{
  "schedule_id": "sch_1234567890",
  "channel_id": "123456789012345678",
  "guild_id": "987654321098765432",
  "frequency": "daily",
  "summary_type": "detailed",
  "next_run": "2024-01-02T00:00:00Z",
  "enabled": true,
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### DELETE /api/v1/schedule/{schedule_id}
Cancel a scheduled summary.

**Response:** 204 No Content

#### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "services": {
    "summarization_engine": "healthy",
    "claude_api": "healthy",
    "cache": "healthy"
  }
}
```

#### GET /
API information endpoint.

**Response:**
```json
{
  "name": "Summary Bot NG API",
  "version": "2.0.0",
  "docs": "/docs",
  "health": "/health"
}
```

### 3. Response Formats

The API supports multiple output formats:

- **JSON** (default): Structured JSON response
- **Markdown**: Formatted markdown document
- **HTML**: Styled HTML document
- **Plain Text**: Simple text format

### 4. Error Handling

All errors follow a consistent format:

```json
{
  "error": "ERROR_CODE",
  "message": "Human-readable error message",
  "details": {
    "field": "channel_id",
    "reason": "Invalid format"
  },
  "request_id": "req_1234567890"
}
```

**Common Error Codes:**
- `VALIDATION_ERROR`: Invalid request parameters
- `AUTHENTICATION_REQUIRED`: Missing or invalid credentials
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `INSUFFICIENT_CONTENT`: Not enough messages to summarize
- `SUMMARIZATION_FAILED`: AI summarization error
- `INTERNAL_ERROR`: Unexpected server error

## Configuration

### Environment Variables

The webhook service is configured via the `BotConfig` class:

```python
from src.config.settings import BotConfig, WebhookConfig

config = BotConfig(
    discord_token="...",
    claude_api_key="...",
    webhook_config=WebhookConfig(
        host="0.0.0.0",
        port=5000,
        enabled=True,
        cors_origins=["https://example.com"],
        rate_limit=100,
        jwt_secret="your-secret-key",
        jwt_expiration_minutes=60,
        api_keys={
            "sk_live_abc123": "user_123",
            "sk_test_xyz789": "user_456"
        }
    )
)
```

### CORS Configuration

Configure allowed origins to enable cross-origin requests:

```python
webhook_config = WebhookConfig(
    cors_origins=[
        "https://app.example.com",
        "https://dashboard.example.com"
    ]
)
```

### Rate Limiting

Configure rate limiting per client (by API key or IP):

```python
webhook_config = WebhookConfig(
    rate_limit=100  # 100 requests per minute
)
```

## Usage Examples

### Starting the Server

```python
from src.config.settings import BotConfig
from src.summarization.engine import SummarizationEngine
from src.summarization.claude_client import ClaudeClient
from src.summarization.cache import SummaryCache
from src.webhook_service.server import WebhookServer

# Load configuration
config = BotConfig.load_from_env()

# Initialize summarization engine
claude_client = ClaudeClient(api_key=config.claude_api_key)
cache = SummaryCache()
engine = SummarizationEngine(claude_client, cache)

# Create webhook server
server = WebhookServer(config, engine)

# Start server (non-blocking)
await server.start_server()

# Server runs in background...

# Stop server
await server.stop_server()
```

### Making API Requests

#### Using cURL

```bash
# Create a summary
curl -X POST https://api.example.com/api/v1/summarize \
  -H "X-API-Key: sk_live_abc123" \
  -H "Content-Type: application/json" \
  -d '{
    "channel_id": "123456789012345678",
    "summary_type": "detailed",
    "max_length": 4000
  }'

# Get a summary
curl https://api.example.com/api/v1/summary/sum_1234567890 \
  -H "X-API-Key: sk_live_abc123"

# Health check
curl https://api.example.com/health
```

#### Using Python

```python
import requests

API_BASE = "https://api.example.com"
API_KEY = "sk_live_abc123"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

# Create summary
response = requests.post(
    f"{API_BASE}/api/v1/summarize",
    headers=headers,
    json={
        "channel_id": "123456789012345678",
        "summary_type": "detailed",
        "max_length": 4000
    }
)

summary = response.json()
print(f"Summary ID: {summary['id']}")

# Get summary
response = requests.get(
    f"{API_BASE}/api/v1/summary/{summary['id']}",
    headers=headers
)

print(response.json())
```

#### Using JWT Authentication

```python
from src.webhook_service.auth import create_jwt_token

# Create a token
token = create_jwt_token(
    user_id="user_123",
    guild_id="987654321098765432",
    permissions=["read", "write"],
    expires_minutes=60
)

# Use token in requests
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

response = requests.post(
    f"{API_BASE}/api/v1/summarize",
    headers=headers,
    json={...}
)
```

## API Documentation

Interactive API documentation is available via:

- **Swagger UI**: `http://localhost:5000/docs`
- **ReDoc**: `http://localhost:5000/redoc`
- **OpenAPI Schema**: `http://localhost:5000/openapi.json`

## Security Best Practices

1. **Always use HTTPS in production**
2. **Keep JWT secret secure** - Use environment variables
3. **Rotate API keys regularly**
4. **Configure CORS appropriately** - Don't use wildcard `*` in production
5. **Enable rate limiting** - Protect against abuse
6. **Validate webhook signatures** - When delivering results to external webhooks
7. **Monitor authentication failures** - Detect potential attacks

## Testing

### Unit Tests

```python
import pytest
from src.webhook_service.validators import SummaryRequestModel

def test_summary_request_validation():
    # Valid request
    request = SummaryRequestModel(
        channel_id="123456789012345678",
        summary_type="detailed"
    )
    assert request.channel_id == "123456789012345678"

    # Invalid request
    with pytest.raises(ValueError):
        SummaryRequestModel(
            channel_id="",  # Too short
            summary_type="detailed"
        )
```

### Integration Tests

```python
import pytest
from fastapi.testclient import TestClient
from src.webhook_service.server import WebhookServer

@pytest.fixture
def client(config, engine):
    server = WebhookServer(config, engine)
    return TestClient(server.get_app())

def test_create_summary(client):
    response = client.post(
        "/api/v1/summarize",
        headers={"X-API-Key": "sk_test_abc123"},
        json={
            "channel_id": "123456789012345678",
            "summary_type": "detailed"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["channel_id"] == "123456789012345678"

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded", "unhealthy"]
```

## Performance Considerations

1. **Async Operations**: All endpoints use async/await for non-blocking I/O
2. **Connection Pooling**: Database and Redis connections are pooled
3. **Caching**: Summary results are cached to reduce API costs
4. **Rate Limiting**: Prevents resource exhaustion
5. **GZip Compression**: Reduces bandwidth for large responses

## Monitoring

The webhook service provides metrics via the `/metrics` endpoint (requires API key):

```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "requests_per_minute": 45,
  "average_response_time_ms": 250,
  "active_jobs": 3,
  "queue_size": 10,
  "cache_hit_rate": 0.75,
  "error_rate": 0.02
}
```

## Troubleshooting

### Server Won't Start

- Check port availability: `lsof -i :5000`
- Verify configuration: Check `config.webhook_config.enabled`
- Check logs for error messages

### Authentication Failures

- Verify API key is configured in `webhook_config.api_keys`
- Check JWT secret matches between token creation and validation
- Ensure token hasn't expired

### Rate Limiting Issues

- Increase `rate_limit` in webhook config
- Implement exponential backoff in clients
- Use different API keys for different services

### Slow Response Times

- Check Claude API latency
- Enable caching for repeated queries
- Monitor database connection pool
- Review message batch sizes

## Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ ./src/

EXPOSE 5000

CMD ["python", "-m", "uvicorn", "src.webhook_service.server:app", "--host", "0.0.0.0", "--port", "5000"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  webhook-api:
    build: .
    ports:
      - "5000:5000"
    environment:
      - DISCORD_TOKEN=${DISCORD_TOKEN}
      - CLAUDE_API_KEY=${CLAUDE_API_KEY}
      - WEBHOOK_HOST=0.0.0.0
      - WEBHOOK_PORT=5000
      - WEBHOOK_CORS_ORIGINS=https://app.example.com
    restart: unless-stopped
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: webhook-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: webhook-api
  template:
    metadata:
      labels:
        app: webhook-api
    spec:
      containers:
      - name: webhook-api
        image: summarybot-ng:latest
        ports:
        - containerPort: 5000
        env:
        - name: DISCORD_TOKEN
          valueFrom:
            secretKeyRef:
              name: bot-secrets
              key: discord-token
        - name: CLAUDE_API_KEY
          valueFrom:
            secretKeyRef:
              name: bot-secrets
              key: claude-api-key
        livenessProbe:
          httpGet:
            path: /health
            port: 5000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 5000
          initialDelaySeconds: 5
          periodSeconds: 5
```

## Future Enhancements

1. **WebSocket Support**: Real-time summary updates
2. **GraphQL API**: Flexible querying
3. **Batch Operations**: Summarize multiple channels at once
4. **Webhook Delivery**: Push results to external endpoints
5. **API Versioning**: Support multiple API versions
6. **Advanced Analytics**: Usage statistics and insights
7. **Database Integration**: Persist summaries for retrieval

## Contributing

See the main project [CONTRIBUTING.md](/CONTRIBUTING.md) for guidelines.

## License

This module is part of Summary Bot NG and follows the project's license.
