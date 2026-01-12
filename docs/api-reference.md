# API Reference

This document provides comprehensive API documentation for Summary Bot NG, including REST endpoints, webhook configurations, and Discord command interfaces.

## 🌐 REST API Endpoints

The bot exposes several HTTP endpoints for external integration and programmatic access.

### Base URL
```
http://localhost:5000  # Default development
https://your-domain.com  # Production deployment
```

### Authentication
Most endpoints require API key authentication via header:
```http
Authorization: Bearer your_api_key_here
```

---

## 📨 Summary Endpoints

### POST /api/v1/summary

Generate a summary from Discord channel messages.

#### Request
```http
POST /api/v1/summary
Content-Type: application/json
Authorization: Bearer your_api_key

{
  "channel_id": "123456789012345678",
  "message_count": 50,
  "prompt_template": "default",
  "include_links": true,
  "time_range": {
    "start": "2024-01-01T00:00:00Z",
    "end": "2024-01-02T00:00:00Z"
  },
  "filters": {
    "users": ["user1", "user2"],
    "exclude_bots": true,
    "min_length": 10
  }
}
```

#### Parameters
- `channel_id` (required): Discord channel ID to summarize
- `message_count` (optional): Maximum messages to process (default: 50, max: 500)
- `prompt_template` (optional): Template name (default, technical, meeting)
- `include_links` (optional): Include message links in summary (default: true)
- `time_range` (optional): Date range filter
- `filters` (optional): Additional content filters

#### Response
```json
{
  "success": true,
  "data": {
    "summary": "## Technical Discussion\n\n- Database optimization strategies discussed...",
    "metadata": {
      "message_count": 47,
      "time_range": "2024-01-01 to 2024-01-02",
      "processing_time": 2.34,
      "tokens_used": 1250,
      "channel_name": "#development"
    },
    "links": [
      {
        "text": "Database optimization PR",
        "url": "https://discord.com/channels/123/456/789"
      }
    ]
  }
}
```

### GET /api/v1/summary/{summary_id}

Retrieve a previously generated summary.

#### Response
```json
{
  "success": true,
  "data": {
    "id": "summary_123456",
    "content": "## Meeting Summary...",
    "created_at": "2024-01-01T12:00:00Z",
    "channel_id": "123456789012345678",
    "metadata": { ... }
  }
}
```

---

## 🔄 Webhook Endpoints

### POST /webhook/summary

Receive webhook notifications when summaries are generated.

#### Webhook Payload
```json
{
  "event": "summary.created",
  "timestamp": "2024-01-01T12:00:00Z",
  "data": {
    "summary_id": "summary_123456",
    "channel_id": "123456789012345678",
    "summary": "## Summary Content...",
    "metadata": {
      "message_count": 25,
      "processing_time": 1.8
    }
  },
  "signature": "sha256=hash_signature"
}
```

### POST /webhook/external

Receive external summary requests from third-party systems.

#### Request
```json
{
  "source": "confluence",
  "channel_url": "https://discord.com/channels/123/456",
  "options": {
    "format": "markdown",
    "max_length": 2000
  }
}
```

---

## ⚡ Status & Health Endpoints

### GET /health

Health check endpoint for monitoring.

#### Response
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime": 3600,
  "services": {
    "discord": "connected",
    "claude_api": "available",
    "database": "connected"
  }
}
```

### GET /api/v1/status

Detailed system status information.

#### Response
```json
{
  "bot": {
    "user_id": "987654321",
    "username": "Summary Bot NG",
    "guilds": 5,
    "online": true
  },
  "api": {
    "requests_today": 150,
    "rate_limit": "100/hour",
    "quota_remaining": 8500
  },
  "storage": {
    "summaries_stored": 1250,
    "disk_usage": "45.2MB"
  }
}
```

---

## 🎯 Discord Slash Commands

### /summarize

Main command for generating summaries within Discord.

#### Basic Usage
```
/summarize
```

#### Parameters
- `channel` (optional): Target channel (defaults to current)
- `count` (optional): Number of messages (1-100, default: 25)
- `prompt` (optional): Summary focus (default, technical, meeting)
- `format` (optional): Output format (markdown, html)

#### Examples
```bash
# Summarize last 25 messages in current channel
/summarize

# Summarize specific channel
/summarize channel:#development count:50

# Technical summary with custom prompt
/summarize prompt:technical count:100

# Meeting summary in HTML format
/summarize prompt:meeting format:html
```

### /summary-config

Configure bot settings per server.

#### Subcommands
- `/summary-config set-channel` - Set default summary channel
- `/summary-config set-role` - Set required role for summaries
- `/summary-config set-template` - Set default prompt template

#### Examples
```bash
# Set default summary output channel
/summary-config set-channel channel:#summaries

# Require specific role to use bot
/summary-config set-role role:@moderator

# Set default template for server
/summary-config set-template template:technical
```

### /summary-history

View and manage summary history.

#### Examples
```bash
# List recent summaries
/summary-history list

# Get specific summary
/summary-history get id:summary_123

# Delete summary
/summary-history delete id:summary_123
```

---

## 🔧 Configuration API

### GET /api/v1/config

Get current bot configuration.

#### Response
```json
{
  "discord": {
    "prefix": "/",
    "max_message_count": 500,
    "default_prompt": "default"
  },
  "llm": {
    "provider": "openrouter",
    "model": "anthropic/claude-3-sonnet-20240229",
    "max_tokens": 4000,
    "temperature": 0.7
  },
  "webhook": {
    "enabled": true,
    "port": 5000,
    "timeout": 30
  }
}
```

### PUT /api/v1/config

Update bot configuration.

#### Request
```json
{
  "discord": {
    "max_message_count": 750
  },
  "llm": {
    "temperature": 0.5
  }
}
```

---

## 🔐 Authentication & Security

### API Key Authentication
```http
Authorization: Bearer sk-summarybot-1234567890abcdef
```

### Webhook Signature Verification
Webhooks include HMAC-SHA256 signature in header:
```http
X-Signature-256: sha256=computed_signature
```

Verify signature using your webhook secret:
```python
import hmac
import hashlib

def verify_signature(payload, signature, secret):
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)
```

### Rate Limiting
- **API Endpoints**: 100 requests per hour per API key
- **Discord Commands**: 10 requests per minute per user
- **Webhook Endpoints**: 1000 requests per hour

Rate limit headers:
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

---

## 📊 Error Handling

### Error Response Format
```json
{
  "success": false,
  "error": {
    "code": "INVALID_CHANNEL",
    "message": "Channel not found or bot lacks access",
    "details": {
      "channel_id": "123456789012345678"
    }
  }
}
```

### Common Error Codes
- `INVALID_API_KEY` (401): Invalid or missing API key
- `RATE_LIMITED` (429): Rate limit exceeded
- `INVALID_CHANNEL` (404): Channel not found or inaccessible
- `LLM_API_ERROR` (502): Claude/OpenRouter API error
- `INVALID_PARAMETERS` (400): Invalid request parameters
- `INSUFFICIENT_PERMISSIONS` (403): Bot lacks required permissions

---

## 🔌 Integration Examples

### Python Integration
```python
import requests

class SummaryBotAPI:
    def __init__(self, api_key, base_url="http://localhost:5000"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {api_key}"}
    
    def create_summary(self, channel_id, **kwargs):
        data = {"channel_id": channel_id, **kwargs}
        response = requests.post(
            f"{self.base_url}/api/v1/summary",
            json=data,
            headers=self.headers
        )
        return response.json()

# Usage
client = SummaryBotAPI("your-api-key")
summary = client.create_summary(
    channel_id="123456789",
    message_count=50,
    prompt_template="technical"
)
```

### Node.js Integration
```javascript
const axios = require('axios');

class SummaryBotAPI {
  constructor(apiKey, baseUrl = 'http://localhost:5000') {
    this.apiKey = apiKey;
    this.baseUrl = baseUrl;
    this.headers = { Authorization: `Bearer ${apiKey}` };
  }

  async createSummary(channelId, options = {}) {
    const { data } = await axios.post(
      `${this.baseUrl}/api/v1/summary`,
      { channel_id: channelId, ...options },
      { headers: this.headers }
    );
    return data;
  }
}

// Usage
const client = new SummaryBotAPI('your-api-key');
const summary = await client.createSummary('123456789', {
  message_count: 50,
  prompt_template: 'meeting'
});
```

### cURL Examples
```bash
# Create summary
curl -X POST http://localhost:5000/api/v1/summary \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "channel_id": "123456789",
    "message_count": 50,
    "prompt_template": "default"
  }'

# Get health status
curl http://localhost:5000/health

# Get bot status
curl -H "Authorization: Bearer your-api-key" \
  http://localhost:5000/api/v1/status
```

---

## 📋 OpenAPI Specification

A complete OpenAPI 3.0 specification is available at:
```
GET /api/v1/openapi.json
```

This can be imported into tools like Postman or used to generate client SDKs.

---

## 🎯 Best Practices

### API Usage
1. **Always authenticate**: Include API key in requests
2. **Handle rate limits**: Implement exponential backoff
3. **Validate responses**: Check `success` field before processing
4. **Use webhooks**: For real-time updates instead of polling
5. **Cache responses**: Store summaries locally when possible

### Discord Commands
1. **Use sparingly**: Avoid overwhelming channels with summaries
2. **Target specific channels**: Use channel parameter for focused summaries
3. **Consider permissions**: Ensure users have appropriate roles
4. **Monitor usage**: Track command frequency to avoid spam

### Error Handling
1. **Implement retries**: For temporary failures
2. **Log errors**: For debugging and monitoring
3. **Graceful degradation**: Provide fallbacks when API unavailable
4. **User feedback**: Show meaningful error messages in Discord