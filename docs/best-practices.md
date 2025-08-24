# Best Practices Guide: Summary Bot NG

## 1. Discord.py Development Best Practices

### Command Architecture

#### Use Application Commands (Slash Commands)
```python
import discord
from discord.ext import commands

class SummaryBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True  # Required for message reading
        super().__init__(command_prefix='!', intents=intents)

    @discord.app_commands.command(name="summarize", description="Summarize channel messages")
    async def summarize(self, interaction: discord.Interaction, hours: int = 24):
        await interaction.response.defer()  # Prevent timeout
        # Summarization logic here
        await interaction.followup.send("Summary generated!")
```

#### Implement Proper Cog Structure
```python
# cogs/summarization.py
class SummarizationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.summary_engine = SummaryEngine()

    @commands.hybrid_command(name="summary")
    async def create_summary(self, ctx, hours: int = 24):
        """Create a summary of recent messages"""
        try:
            messages = await self.fetch_messages(ctx.channel, hours)
            summary = await self.summary_engine.generate_summary(messages)
            await ctx.send(embed=self.create_summary_embed(summary))
        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            await ctx.send("Sorry, I couldn't generate a summary right now.")

async def setup(bot):
    await bot.add_cog(SummarizationCog(bot))
```

#### Rate Limit Handling
```python
import asyncio
from discord.errors import HTTPException

async def safe_send(channel, content, max_retries=3):
    """Send message with automatic retry on rate limits"""
    for attempt in range(max_retries):
        try:
            return await channel.send(content)
        except HTTPException as e:
            if e.status == 429:  # Rate limited
                retry_after = float(e.response.headers.get('Retry-After', 1))
                logger.warning(f"Rate limited, waiting {retry_after}s")
                await asyncio.sleep(retry_after)
            else:
                raise
        except Exception as e:
            logger.error(f"Send failed (attempt {attempt + 1}): {e}")
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

### Error Handling Patterns

#### Global Error Handler
```python
@bot.event
async def on_command_error(ctx, error):
    """Global error handler for commands"""
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"Command on cooldown. Try again in {error.retry_after:.2f}s")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have permission to use this command.")
    elif isinstance(error, commands.CommandNotFound):
        return  # Ignore unknown commands
    else:
        logger.error(f"Unexpected error in {ctx.command}: {error}")
        await ctx.send("An unexpected error occurred. Please try again later.")
```

#### Graceful Shutdown
```python
import signal
import sys

class SummaryBot(commands.Bot):
    async def setup_hook(self):
        """Called when bot is starting up"""
        logger.info("Bot is starting up...")
        
        # Setup signal handlers for graceful shutdown
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.shutdown()))
    
    async def shutdown(self):
        """Graceful shutdown procedure"""
        logger.info("Shutting down bot...")
        await self.close()
        sys.exit(0)
```

## 2. OpenAI Integration Best Practices

### Cost Optimization

#### Token Management
```python
import tiktoken

class TokenManager:
    def __init__(self, model="gpt-4o"):
        self.model = model
        self.encoder = tiktoken.encoding_for_model(model)
        self.max_tokens = 8192  # Model context limit
        self.target_summary_tokens = 500
    
    def count_tokens(self, text: str) -> int:
        return len(self.encoder.encode(text))
    
    def truncate_to_fit(self, messages: str, system_prompt: str) -> str:
        """Truncate messages to fit within context limit"""
        system_tokens = self.count_tokens(system_prompt)
        available_tokens = self.max_tokens - system_tokens - self.target_summary_tokens - 100  # Buffer
        
        message_tokens = self.count_tokens(messages)
        if message_tokens <= available_tokens:
            return messages
        
        # Truncate from the beginning (keep most recent messages)
        words = messages.split()
        while self.count_tokens(' '.join(words)) > available_tokens and words:
            words.pop(0)
        
        return ' '.join(words)
```

#### Response Caching
```python
import asyncio
from functools import wraps
from typing import Dict, Any
import hashlib
import json

class SummaryCache:
    def __init__(self, ttl: int = 3600):  # 1 hour TTL
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = ttl
    
    def _generate_key(self, messages: str, model: str) -> str:
        content = f"{messages}:{model}"
        return hashlib.md5(content.encode()).hexdigest()
    
    async def get(self, messages: str, model: str) -> str | None:
        key = self._generate_key(messages, model)
        if key in self.cache:
            entry = self.cache[key]
            if asyncio.get_event_loop().time() - entry['timestamp'] < self.ttl:
                return entry['summary']
            else:
                del self.cache[key]
        return None
    
    async def set(self, messages: str, model: str, summary: str):
        key = self._generate_key(messages, model)
        self.cache[key] = {
            'summary': summary,
            'timestamp': asyncio.get_event_loop().time()
        }

# Usage in SummaryEngine
cache = SummaryCache()

async def generate_summary(self, messages: str) -> str:
    # Check cache first
    cached = await cache.get(messages, self.model)
    if cached:
        return cached
    
    # Generate new summary
    summary = await self._call_openai(messages)
    await cache.set(messages, self.model, summary)
    return summary
```

### Error Handling and Resilience

#### Retry Logic with Exponential Backoff
```python
import openai
import asyncio
from typing import Optional
import random

class ResilientOpenAIClient:
    def __init__(self, api_key: str, max_retries: int = 3):
        self.client = openai.AsyncOpenAI(api_key=api_key)
        self.max_retries = max_retries
    
    async def generate_summary(self, messages: str) -> Optional[str]:
        for attempt in range(self.max_retries):
            try:
                response = await self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": self._get_system_prompt()},
                        {"role": "user", "content": messages}
                    ],
                    max_tokens=500,
                    temperature=0.3,
                    timeout=30  # 30 second timeout
                )
                return response.choices[0].message.content
            
            except openai.RateLimitError as e:
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"Rate limited, waiting {wait_time}s (attempt {attempt + 1})")
                await asyncio.sleep(wait_time)
            
            except openai.APITimeoutError:
                logger.warning(f"API timeout (attempt {attempt + 1})")
                if attempt == self.max_retries - 1:
                    return "Summary temporarily unavailable due to timeout."
            
            except openai.APIError as e:
                logger.error(f"OpenAI API error: {e}")
                if attempt == self.max_retries - 1:
                    return "Summary unavailable due to API error."
                await asyncio.sleep(2 ** attempt)
        
        return None
```

### Prompt Engineering

#### Optimized Summarization Prompts
```python
class PromptTemplates:
    DISCORD_SUMMARY = """
    You are an expert at summarizing Discord channel conversations. Create a concise, 
    structured summary of the following messages.

    Guidelines:
    - Focus on key decisions, important information, and actionable items
    - Preserve important technical details and links
    - Group related discussions together
    - Use bullet points for clarity
    - Ignore off-topic conversations and spam
    - Maximum 500 words

    Format your response as:
    ## Key Discussion Points
    - [Main topics discussed]

    ## Important Decisions/Outcomes
    - [Decisions made or conclusions reached]

    ## Action Items
    - [Tasks or follow-ups mentioned]

    ## Technical Details
    - [Code snippets, links, or technical information]

    Messages to summarize:
    {messages}
    """
    
    @staticmethod
    def get_system_prompt(channel_type: str = "general") -> str:
        if channel_type == "dev":
            return PromptTemplates.DISCORD_SUMMARY.replace(
                "## Technical Details",
                "## Code Changes\n- [Code snippets and technical discussions]\n\n## Technical Details"
            )
        return PromptTemplates.DISCORD_SUMMARY
```

## 3. Webhook Implementation Best Practices

### Security Implementation

#### Signature Verification
```python
from fastapi import FastAPI, HTTPException, Request, Header
import hmac
import hashlib
from typing import Optional

app = FastAPI()

class WebhookSecurity:
    def __init__(self, secret_key: str):
        self.secret_key = secret_key.encode()
    
    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """Verify webhook signature using HMAC-SHA256"""
        if not signature.startswith('sha256='):
            return False
        
        expected = hmac.new(
            self.secret_key,
            payload,
            hashlib.sha256
        ).hexdigest()
        
        received = signature[7:]  # Remove 'sha256=' prefix
        return hmac.compare_digest(expected, received)

webhook_security = WebhookSecurity(settings.webhook_secret)

@app.post("/webhook")
async def handle_webhook(
    request: Request,
    x_signature_256: Optional[str] = Header(None)
):
    payload = await request.body()
    
    if not x_signature_256 or not webhook_security.verify_signature(payload, x_signature_256):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Process webhook
    return {"status": "processed"}
```

#### Rate Limiting
```python
from fastapi import FastAPI, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/webhook")
@limiter.limit("30/minute")  # 30 requests per minute per IP
async def handle_webhook(request: Request):
    # Webhook processing logic
    pass
```

### Reliable Processing

#### Idempotency Implementation
```python
import asyncio
from typing import Set
import time

class IdempotencyManager:
    def __init__(self, ttl: int = 3600):
        self.processed_requests: Set[str] = set()
        self.ttl = ttl
        self.cleanup_task = asyncio.create_task(self._cleanup_expired())
    
    async def is_duplicate(self, request_id: str) -> bool:
        return request_id in self.processed_requests
    
    async def mark_processed(self, request_id: str):
        self.processed_requests.add(request_id)
    
    async def _cleanup_expired(self):
        while True:
            await asyncio.sleep(self.ttl)
            # In production, use Redis with expiration
            # This is a simplified in-memory version

idempotency = IdempotencyManager()

@app.post("/webhook")
async def handle_webhook(request: Request):
    request_id = request.headers.get('x-request-id')
    if not request_id:
        request_id = hashlib.sha256(await request.body()).hexdigest()
    
    if await idempotency.is_duplicate(request_id):
        return {"status": "already_processed"}
    
    try:
        # Process webhook
        result = await process_webhook_data(await request.json())
        await idempotency.mark_processed(request_id)
        return result
    except Exception as e:
        logger.error(f"Webhook processing failed: {e}")
        raise HTTPException(status_code=500, detail="Processing failed")
```

### Async Queue Processing

#### Background Task Processing
```python
import asyncio
from typing import Dict, Any
import json

class WebhookQueue:
    def __init__(self, max_workers: int = 5):
        self.queue = asyncio.Queue()
        self.max_workers = max_workers
        self.workers = []
        self.running = False
    
    async def start(self):
        self.running = True
        self.workers = [
            asyncio.create_task(self._worker(f"worker-{i}"))
            for i in range(self.max_workers)
        ]
    
    async def stop(self):
        self.running = False
        # Wait for current tasks to complete
        await asyncio.gather(*self.workers, return_exceptions=True)
    
    async def enqueue(self, webhook_data: Dict[str, Any]):
        await self.queue.put(webhook_data)
    
    async def _worker(self, worker_name: str):
        while self.running:
            try:
                data = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                await self._process_webhook(data)
                self.queue.task_done()
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Worker {worker_name} error: {e}")
    
    async def _process_webhook(self, data: Dict[str, Any]):
        # Process webhook data (send to Discord, external APIs, etc.)
        webhook_type = data.get('type')
        if webhook_type == 'summary_request':
            await self._handle_summary_request(data)
        elif webhook_type == 'schedule_update':
            await self._handle_schedule_update(data)

webhook_queue = WebhookQueue()

# Start queue processing on startup
@app.on_event("startup")
async def startup_event():
    await webhook_queue.start()

@app.on_event("shutdown")
async def shutdown_event():
    await webhook_queue.stop()

@app.post("/webhook")
async def handle_webhook(request: Request):
    # Quick validation and queue
    data = await request.json()
    await webhook_queue.enqueue(data)
    return {"status": "queued"}
```

## 4. Configuration Management Best Practices

### Environment-Based Configuration

#### Pydantic Settings with Validation
```python
from pydantic_settings import BaseSettings
from pydantic import validator, Field
from typing import Optional, List
import os

class Settings(BaseSettings):
    # Discord Configuration
    discord_token: str = Field(..., min_length=50)
    discord_guild_ids: Optional[List[int]] = None
    
    # OpenAI Configuration
    openai_api_key: str = Field(..., min_length=40)
    openai_model: str = "gpt-4o"
    openai_max_tokens: int = Field(default=500, ge=100, le=2000)
    openai_temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    
    # Webhook Configuration
    webhook_secret: str = Field(..., min_length=32)
    webhook_host: str = "0.0.0.0"
    webhook_port: int = Field(default=5000, ge=1024, le=65535)
    
    # Application Configuration
    environment: str = Field(default="development", regex="^(development|staging|production)$")
    debug: bool = False
    log_level: str = Field(default="INFO", regex="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    
    # Cache Configuration
    cache_ttl: int = Field(default=3600, ge=60)  # 1 hour default
    max_cache_size: int = Field(default=1000, ge=10)
    
    # Rate Limiting
    rate_limit_per_minute: int = Field(default=30, ge=1)
    max_retries: int = Field(default=3, ge=1, le=10)
    
    @validator('discord_guild_ids', pre=True)
    def parse_guild_ids(cls, v):
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(',') if x.strip()]
        return v
    
    @validator('environment')
    def validate_environment(cls, v):
        if v == 'production' and os.getenv('DEBUG', 'false').lower() == 'true':
            raise ValueError('Debug cannot be enabled in production')
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        # Allow extra fields for flexibility
        extra = "allow"

# Create global settings instance
settings = Settings()

# Environment-specific overrides
if settings.environment == "production":
    settings.debug = False
    settings.log_level = "INFO"
elif settings.environment == "development":
    settings.debug = True
    settings.log_level = "DEBUG"
```

### Secrets Management

#### Development vs Production Secrets
```python
import os
from pathlib import Path

class SecretsManager:
    def __init__(self, environment: str):
        self.environment = environment
        self.secrets_path = Path("/var/secrets") if environment == "production" else Path(".env")
    
    def get_secret(self, key: str) -> str:
        if self.environment == "production":
            # Read from mounted secret files in production
            secret_file = self.secrets_path / key.lower().replace('_', '-')
            if secret_file.exists():
                return secret_file.read_text().strip()
        
        # Fallback to environment variables
        value = os.getenv(key)
        if not value:
            raise ValueError(f"Secret {key} not found")
        return value

secrets = SecretsManager(settings.environment)

# Usage
discord_token = secrets.get_secret("DISCORD_TOKEN")
openai_api_key = secrets.get_secret("OPENAI_API_KEY")
```

## 5. Testing Best Practices

### Async Testing Patterns

#### Bot Command Testing
```python
import pytest
import discord.ext.test as dpytest
from unittest.mock import AsyncMock, patch

@pytest.fixture
async def bot():
    bot = SummaryBot()
    await dpytest.configure(bot)
    return bot

@pytest.mark.asyncio
async def test_summarize_command(bot):
    # Mock OpenAI response
    with patch.object(bot.summary_engine, 'generate_summary') as mock_summary:
        mock_summary.return_value = "Test summary"
        
        # Simulate command
        await dpytest.message("!summarize 24")
        
        # Verify response
        assert dpytest.verify().message().contains().content("Test summary")
        mock_summary.assert_called_once()

@pytest.mark.asyncio
async def test_error_handling(bot):
    # Test API error handling
    with patch.object(bot.summary_engine, 'generate_summary') as mock_summary:
        mock_summary.side_effect = Exception("API Error")
        
        await dpytest.message("!summarize")
        assert dpytest.verify().message().contains().content("couldn't generate a summary")
```

#### Webhook Testing
```python
from fastapi.testclient import TestClient
import hmac
import hashlib

@pytest.fixture
def client():
    return TestClient(app)

def create_signature(payload: str, secret: str) -> str:
    signature = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return f"sha256={signature}"

def test_webhook_valid_signature(client):
    payload = '{"type": "test", "data": {"message": "hello"}}'
    signature = create_signature(payload, "test-secret")
    
    response = client.post(
        "/webhook",
        content=payload,
        headers={"X-Signature-256": signature, "Content-Type": "application/json"}
    )
    
    assert response.status_code == 200
    assert response.json()["status"] == "processed"

def test_webhook_invalid_signature(client):
    payload = '{"type": "test"}'
    
    response = client.post(
        "/webhook",
        content=payload,
        headers={"X-Signature-256": "sha256=invalid", "Content-Type": "application/json"}
    )
    
    assert response.status_code == 401
```

### Integration Testing

#### End-to-End Testing
```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_full_summarization_workflow():
    # This test requires actual Discord bot token and OpenAI API key
    # Run only in CI with test credentials
    
    bot = SummaryBot()
    
    # Create test messages
    test_messages = [
        "User1: Hey, let's discuss the new feature",
        "User2: Great idea! I think we should implement OAuth",
        "User1: Agreed. Let's start with the backend API"
    ]
    
    # Test summarization
    summary = await bot.summary_engine.generate_summary('\n'.join(test_messages))
    
    assert summary is not None
    assert len(summary) > 0
    assert "feature" in summary.lower() or "oauth" in summary.lower()
```

## 6. Deployment Best Practices

### Container Optimization

#### Multi-stage Dockerfile
```dockerfile
# Build stage
FROM python:3.11-slim-bullseye as builder

WORKDIR /app

# Install Poetry
RUN pip install poetry==1.6.1

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Configure poetry and install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --only=main --no-dev --no-root

# Runtime stage
FROM python:3.11-slim-bullseye as runtime

# Create non-root user
RUN groupadd -r botuser && useradd -r -g botuser -s /bin/false botuser

# Install security updates
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Set ownership and permissions
RUN chown -R botuser:botuser /app
USER botuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/health')" || exit 1

EXPOSE 5000

CMD ["python", "-m", "summarybot"]
```

### Environment Configuration

#### Docker Compose for Development
```yaml
version: '3.8'

services:
  summarybot:
    build:
      context: .
      target: runtime
    environment:
      - ENVIRONMENT=development
      - DEBUG=true
    env_file:
      - .env
    ports:
      - "5000:5000"
    volumes:
      - .:/app
      - /app/__pycache__
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:5000/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data

volumes:
  redis_data:
```

### Monitoring and Observability

#### Structured Logging
```python
import logging
import json
from datetime import datetime
from typing import Dict, Any

class StructuredFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add extra fields if present
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'guild_id'):
            log_entry['guild_id'] = record.guild_id
        if hasattr(record, 'command'):
            log_entry['command'] = record.command
        
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry)

# Configure logging
def setup_logging(level: str = "INFO", structured: bool = False):
    logging.basicConfig(
        level=getattr(logging, level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('/app/logs/bot.log') if not structured else None
        ]
    )
    
    if structured:
        formatter = StructuredFormatter()
        for handler in logging.getLogger().handlers:
            if handler:
                handler.setFormatter(formatter)

# Usage in application
logger = logging.getLogger(__name__)

@bot.event
async def on_command(ctx):
    logger.info(
        "Command executed",
        extra={
            'user_id': ctx.author.id,
            'guild_id': ctx.guild.id if ctx.guild else None,
            'command': ctx.command.name if ctx.command else None
        }
    )
```

These best practices provide a comprehensive foundation for building a robust, scalable Discord bot with proper error handling, security, and maintainability. Each section can be adapted based on specific requirements and constraints of your deployment environment.