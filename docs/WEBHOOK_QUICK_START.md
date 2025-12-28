# Webhook Service - Quick Start Guide

## 🚀 Getting Started in 5 Minutes

### 1. Install Dependencies

```bash
pip install fastapi uvicorn python-jose[cryptography] pydantic anthropic
```

### 2. Configure API Keys

Edit your `.env` file or configuration:

```python
from src.config.settings import BotConfig, WebhookConfig

config = BotConfig(
    discord_token="your-discord-token",
    claude_api_key="your-claude-key",
    webhook_config=WebhookConfig(
        host="0.0.0.0",
        port=5000,
        api_keys={
            "sk_test_abc123": "user_123"  # Your API key
        }
    )
)
```

### 3. Start the Server

```python
from src.config.settings import BotConfig
from src.summarization.engine import SummarizationEngine
from src.summarization.claude_client import ClaudeClient
from src.summarization.cache import SummaryCache
from src.webhook_service.server import WebhookServer
import asyncio

async def main():
    # Load config
    config = BotConfig.load_from_env()

    # Initialize components
    claude_client = ClaudeClient(api_key=config.claude_api_key)
    cache = SummaryCache()
    engine = SummarizationEngine(claude_client, cache)

    # Start server
    server = WebhookServer(config, engine)
    await server.start_server()

    # Keep running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await server.stop_server()

if __name__ == "__main__":
    asyncio.run(main())
```

### 4. Test the API

```bash
# Check health
curl http://localhost:5000/health

# View docs
open http://localhost:5000/docs

# Create a summary
curl -X POST http://localhost:5000/api/v1/summarize \
  -H "X-API-Key: sk_test_abc123" \
  -H "Content-Type: application/json" \
  -d '{
    "channel_id": "123456789012345678",
    "summary_type": "detailed"
  }'
```

## 📖 Common Operations

### Create a Summary

```python
import requests

response = requests.post(
    "http://localhost:5000/api/v1/summarize",
    headers={"X-API-Key": "sk_test_abc123"},
    json={
        "channel_id": "123456789012345678",
        "summary_type": "detailed",
        "max_length": 4000,
        "include_threads": True,
        "exclude_bots": True
    }
)

print(response.json())
```

### Generate JWT Token

```python
from src.webhook_service.auth import create_jwt_token

token = create_jwt_token(
    user_id="user_123",
    permissions=["read", "write"],
    expires_minutes=60
)

print(f"Your token: {token}")
```

### Use JWT Token

```python
import requests

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

response = requests.post(
    "http://localhost:5000/api/v1/summarize",
    headers=headers,
    json={...}
)
```

## 🔍 Debugging

### Check Server Status

```python
response = requests.get("http://localhost:5000/health")
print(response.json())
```

### View API Documentation

Open your browser: http://localhost:5000/docs

### Check Logs

The server logs all requests and errors. Look for:
- Request IDs for tracking
- Error codes for troubleshooting
- Response times for performance

## ⚡ Quick Tips

1. **Use the interactive docs** at `/docs` to test endpoints
2. **Check rate limits** in response headers (`X-RateLimit-*`)
3. **Include request IDs** via `X-Request-ID` header for tracking
4. **Use appropriate summary types**: `brief`, `detailed`, `comprehensive`
5. **Set reasonable `max_length`** values (100-10000 tokens)

## 🛠️ Troubleshooting

### "Invalid API key"
- Check your API key is configured in `webhook_config.api_keys`
- Ensure the key is at least 10 characters long

### "Rate limit exceeded"
- Wait 60 seconds and try again
- Increase `rate_limit` in configuration

### "Health check failed"
- Check Claude API key is valid
- Verify network connectivity
- Review server logs for errors

## 📚 Next Steps

- Read the [complete API documentation](webhook_service_README.md)
- Review [implementation details](WEBHOOK_SERVICE_IMPLEMENTATION.md)
- Check [specification](../specs/phase_3_modules.md)
- See [API specifications](../architecture/api-specifications.md)

## 🔗 Useful Links

- OpenAPI Docs: http://localhost:5000/docs
- ReDoc: http://localhost:5000/redoc
- Health Check: http://localhost:5000/health
- API Info: http://localhost:5000/
