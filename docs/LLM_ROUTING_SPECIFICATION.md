# LLM Routing Specification
**Summary Bot NG - AI Provider Configuration**

## Overview

Summary Bot NG uses different AI providers based on the deployment environment:

- **Development Environment**: Direct Claude API (Anthropic)
- **Runtime/Production Environment**: OpenRouter Proxy

This dual-provider strategy allows for:
- Cost optimization in production
- Flexible model selection via OpenRouter
- Simplified development with direct API access
- Unified interface regardless of backend

---

## Architecture

### LLM Routing Logic

```mermaid
graph TD
    A[Application Start] --> B{Check Environment}
    B -->|Production/Runtime| C[Use OpenRouter]
    B -->|Development| D[Use Claude Direct]

    C --> E[OpenRouter API]
    E --> F[Multiple LLM Backends]
    F --> G[Claude Models]
    F --> H[GPT Models]
    F --> I[Other Models]

    D --> J[Anthropic API]
    J --> K[Claude Models Only]

    style C fill:#90EE90
    style D fill:#87CEEB
```

### Environment Detection

The system determines which provider to use based on:

1. **Primary**: `LLM_ROUTE` environment variable
   - `openrouter` → Use OpenRouter
   - `anthropic` → Use Claude Direct

2. **Fallback**: Environment detection
   - Production indicators: `RAILWAY_ENVIRONMENT`, `RENDER`, `HEROKU_APP_NAME`, etc.
   - Development indicators: `localhost`, `127.0.0.1`, development mode flags

---

## Configuration

### Environment Variables

#### Development Configuration

```bash
# Development uses direct Claude API
LLM_ROUTE=anthropic
CLAUDE_API_KEY=sk-ant-api03-your-development-key-here

# OpenRouter not required in development
# OPENROUTER_API_KEY=not-needed
```

#### Production/Runtime Configuration

```bash
# Production uses OpenRouter
LLM_ROUTE=openrouter
OPENROUTER_API_KEY=sk-or-v1-your-production-key-here
OPENROUTER_MODEL=anthropic/claude-3-sonnet-20240229

# Claude API key used as fallback or for OpenRouter authorization
CLAUDE_API_KEY=sk-ant-bypass-this-key-check-as-we-use-openrouter
```

### Configuration Priority

1. **Explicit Configuration**: `LLM_ROUTE` environment variable (highest priority)
2. **Environment Detection**: Auto-detect based on deployment platform
3. **Default Fallback**: Use Claude direct (development mode)

---

## Implementation Details

### Provider Selection Logic

```python
def select_llm_provider():
    """
    Select LLM provider based on environment.

    Returns:
        tuple: (provider_name, api_key, base_url, model)
    """
    llm_route = os.getenv('LLM_ROUTE', '').lower()

    # Explicit configuration takes precedence
    if llm_route == 'openrouter':
        return (
            'openrouter',
            os.getenv('OPENROUTER_API_KEY'),
            'https://openrouter.ai/api',  # Client appends /v1/messages
            os.getenv('OPENROUTER_MODEL', 'anthropic/claude-3-sonnet-20240229')
        )
    elif llm_route == 'anthropic':
        return (
            'anthropic',
            os.getenv('CLAUDE_API_KEY'),
            None,  # Use default Anthropic endpoint
            'claude-3-sonnet-20240229'
        )

    # Auto-detect environment
    if is_production_environment():
        # Production → OpenRouter
        return (
            'openrouter',
            os.getenv('OPENROUTER_API_KEY'),
            'https://openrouter.ai/api',  # Client appends /v1/messages
            os.getenv('OPENROUTER_MODEL', 'anthropic/claude-3-sonnet-20240229')
        )
    else:
        # Development → Claude Direct
        return (
            'anthropic',
            os.getenv('CLAUDE_API_KEY'),
            None,
            'claude-3-sonnet-20240229'
        )

def is_production_environment():
    """
    Detect if running in production environment.

    Returns:
        bool: True if production, False if development
    """
    production_indicators = [
        os.getenv('RAILWAY_ENVIRONMENT'),
        os.getenv('RENDER'),
        os.getenv('HEROKU_APP_NAME'),
        os.getenv('FLY_APP_NAME'),
        os.getenv('NODE_ENV') == 'production',
        os.getenv('ENVIRONMENT') == 'production',
    ]

    return any(production_indicators)
```

---

## Provider Comparison

### Claude Direct (Development)

**Advantages:**
- Direct API access (lower latency)
- Simpler debugging and error messages
- No proxy overhead
- Full access to Anthropic features

**Use Cases:**
- Local development
- Testing and debugging
- Development environments
- CI/CD testing pipelines

**Configuration:**
```bash
LLM_ROUTE=anthropic
CLAUDE_API_KEY=sk-ant-api03-...
```

### OpenRouter (Production)

**Advantages:**
- Unified API for multiple models
- Cost optimization and model selection
- Fallback to alternative models
- Usage analytics and monitoring
- No vendor lock-in

**Use Cases:**
- Production deployments
- Runtime environments
- Multi-model experiments
- Cost-sensitive applications

**Configuration:**
```bash
LLM_ROUTE=openrouter
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=anthropic/claude-3-sonnet-20240229
```

---

## API Compatibility

Both providers use compatible APIs:

### Request Format (Identical)

```python
response = client.messages.create(
    model="claude-3-sonnet-20240229",  # or "anthropic/claude-3-sonnet-20240229"
    max_tokens=4000,
    temperature=0.3,
    system="You are a helpful assistant",
    messages=[
        {"role": "user", "content": "Hello"}
    ]
)
```

### Model Mapping

| Claude Direct | OpenRouter | Description |
|--------------|-----------|-------------|
| `claude-3-sonnet-20240229` | `anthropic/claude-3-sonnet-20240229` | Balanced model |
| `claude-3-opus-20240229` | `anthropic/claude-3-opus-20240229` | Powerful model |
| `claude-3-haiku-20240307` | `anthropic/claude-3-haiku-20240307` | Fast model |
| `claude-3-5-sonnet-20240620` | `anthropic/claude-3-5-sonnet-20240620` | Latest model |

---

## Error Handling

### Authentication Errors

**Development (Claude Direct):**
```
401 Unauthorized from api.anthropic.com
→ Check CLAUDE_API_KEY is valid
```

**Production (OpenRouter):**
```
401 Unauthorized from openrouter.ai
→ Check OPENROUTER_API_KEY is valid
→ Check OpenRouter account has credits
```

### Fallback Strategy

1. **Primary Provider Fails**: Log error and retry with exponential backoff
2. **All Retries Exhausted**: Return error to user with provider information
3. **Configuration Missing**: Fail fast on startup with clear error message

---

## Testing Strategy

### Development Testing

```bash
# Test with Claude Direct
export LLM_ROUTE=anthropic
export CLAUDE_API_KEY=sk-ant-...
poetry run pytest tests/
```

### Production Testing

```bash
# Test with OpenRouter
export LLM_ROUTE=openrouter
export OPENROUTER_API_KEY=sk-or-v1-...
poetry run pytest tests/integration/
```

### Automated Testing

```yaml
# CI/CD Pipeline
test-development:
  env:
    LLM_ROUTE: anthropic
    CLAUDE_API_KEY: ${{ secrets.CLAUDE_API_KEY }}
  run: poetry run pytest

test-production:
  env:
    LLM_ROUTE: openrouter
    OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
  run: poetry run pytest tests/integration/
```

---

## Migration Guide

### From Claude-Only to Dual-Provider

1. **Add OpenRouter Configuration**
   ```bash
   echo "LLM_ROUTE=openrouter" >> .env.production
   echo "OPENROUTER_API_KEY=sk-or-v1-..." >> .env.production
   ```

2. **Update Deployment**
   - Set environment variables in production platform
   - Deploy updated code with routing logic

3. **Verify**
   - Check logs for "Using OpenRouter proxy" message
   - Test summarization functionality
   - Monitor API usage on OpenRouter dashboard

---

## Monitoring

### Metrics to Track

- **Request Distribution**: Claude Direct vs OpenRouter
- **Latency**: Compare response times between providers
- **Cost**: Track API costs per provider
- **Error Rates**: Monitor failure rates by provider
- **Token Usage**: Track input/output tokens

### Logging

```python
logger.info(
    f"LLM Provider: {provider_name}",
    extra={
        "provider": provider_name,
        "model": model_name,
        "environment": "production" if is_production else "development"
    }
)
```

---

## Security Considerations

1. **API Key Management**
   - Never commit API keys to version control
   - Use environment variables or secrets management
   - Rotate keys regularly

2. **Key Separation**
   - Use different keys for development and production
   - Implement key rotation procedures
   - Monitor for unauthorized access

3. **Rate Limiting**
   - Implement client-side rate limiting
   - Monitor usage to prevent API abuse
   - Set up alerts for unusual patterns

---

## Future Enhancements

1. **Dynamic Provider Switching**
   - Switch providers based on model availability
   - Implement cost-based routing
   - Fallback to alternative models

2. **Multi-Provider Support**
   - Support for additional providers (Azure OpenAI, AWS Bedrock)
   - Provider health checks and automatic failover
   - Load balancing across multiple providers

3. **Model Selection**
   - User-selectable models per request
   - Automatic model selection based on task complexity
   - A/B testing different models

---

## References

- [Anthropic API Documentation](https://docs.anthropic.com/claude/reference/)
- [OpenRouter Documentation](https://openrouter.ai/docs)
- [Summary Bot NG Configuration Guide](./configuration.md)
- [Deployment Guide](./deployment-architecture.md)
