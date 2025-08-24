# Integration Requirements Specification
## Summary Bot NG - External API Integration & Dependencies

### 1. OpenAI API Integration

#### 1.1 Service Requirements

**Primary Model**: GPT-4 (gpt-4 or gpt-4-turbo)
- **Reasoning**: Superior context understanding and summarization quality
- **Fallback Models**: GPT-3.5-turbo for cost optimization during high volume
- **Context Window**: 128K tokens for GPT-4-turbo (handles large conversation histories)

**API Endpoint**: `https://api.openai.com/v1/chat/completions`

**Authentication**: 
- Bearer token authentication via `OPENAI_API_KEY` environment variable
- API key rotation capability for security
- Organization ID support for billing isolation

#### 1.2 Request Configuration

**Standard Request Format**:
```json
{
  "model": "gpt-4",
  "messages": [
    {
      "role": "system",
      "content": "You are an expert at summarizing Discord conversations..."
    },
    {
      "role": "user", 
      "content": "Please summarize the following conversation: [conversation_text]"
    }
  ],
  "max_tokens": 1500,
  "temperature": 0.3,
  "top_p": 1,
  "frequency_penalty": 0,
  "presence_penalty": 0
}
```

**Token Management**:
- Input token estimation before API calls
- Output token tracking for billing
- Dynamic max_tokens adjustment based on content length
- Token usage monitoring and alerting

#### 1.3 Rate Limiting & Error Handling

**Rate Limits** (as of API limits):
- GPT-4: 10,000 TPM (tokens per minute), 500 RPM (requests per minute)
- GPT-3.5-turbo: 160,000 TPM, 3,500 RPM
- Implement exponential backoff with jitter

**Error Handling Strategy**:
```python
import openai
import asyncio
import random
from tenacity import retry, stop_after_attempt, wait_exponential

class OpenAIIntegration:
    def __init__(self, api_key: str, organization_id: Optional[str] = None):
        self.client = openai.AsyncOpenAI(
            api_key=api_key,
            organization=organization_id
        )
        self.rate_limiter = RateLimiter()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True
    )
    async def generate_summary(
        self, 
        conversation_text: str, 
        format_type: str = "structured"
    ) -> Dict[str, Any]:
        """Generate summary with automatic retries and rate limiting"""
        
        # Wait for rate limit availability
        await self.rate_limiter.acquire()
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4",
                messages=self._build_messages(conversation_text, format_type),
                max_tokens=self._calculate_max_tokens(conversation_text),
                temperature=0.3
            )
            
            # Track usage metrics
            self._track_usage(response.usage)
            
            return self._parse_response(response)
            
        except openai.RateLimitError as e:
            # Handle rate limiting with longer backoff
            wait_time = self._extract_retry_after(e) or 60
            await asyncio.sleep(wait_time)
            raise
            
        except openai.APIError as e:
            # Handle API errors
            if e.status_code >= 500:
                # Server errors - retry
                raise
            else:
                # Client errors - don't retry
                raise ValueError(f"OpenAI API error: {e.message}")
```

**Circuit Breaker Implementation**:
```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=300):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    async def call(self, func, *args, **kwargs):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
            else:
                raise CircuitBreakerOpenError("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
            
            raise
```

#### 1.4 Prompt Engineering Requirements

**System Prompts by Format**:

```python
PROMPTS = {
    "brief": """You are an expert at creating concise summaries of Discord conversations. 
    Create a brief 2-3 sentence summary capturing the main topic and outcome.""",
    
    "structured": """You are an expert at summarizing Discord conversations in a structured format.
    Create a summary with the following sections:
    - Overview: Brief description of the conversation
    - Key Points: Main discussion points (bullet points)
    - Decisions: Any decisions made or conclusions reached
    - Action Items: Tasks or follow-ups identified
    
    Keep each section concise but informative.""",
    
    "detailed": """You are an expert at creating comprehensive summaries of Discord conversations.
    Provide a detailed analysis including context, key discussions, participant contributions,
    decisions made, and follow-up actions. Include relevant technical details and code discussions.""",
    
    "technical": """You are a technical expert at summarizing development discussions.
    Focus on:
    - Technical problems discussed
    - Solutions proposed and implemented
    - Code changes or architecture decisions
    - Bug reports and fixes
    - Performance or security considerations
    
    Use appropriate technical terminology and highlight code snippets or technical concepts."""
}
```

#### 1.5 Content Filtering & Moderation

**Content Preparation**:
- Remove personally identifiable information (PII)
- Filter out spam and irrelevant content
- Preserve code blocks and technical discussions
- Handle Discord-specific formatting (mentions, channels, emojis)

**Content Length Management**:
```python
def prepare_content_for_openai(messages: List[DiscordMessage]) -> str:
    """Prepare Discord messages for OpenAI processing"""
    
    # Filter and clean messages
    cleaned_messages = []
    for msg in messages:
        if should_include_message(msg):
            cleaned_content = clean_message_content(msg.content)
            cleaned_messages.append({
                'author': msg.author.display_name or msg.author.username,
                'timestamp': msg.timestamp.isoformat(),
                'content': cleaned_content
            })
    
    # Format for AI processing
    conversation_text = format_conversation_for_ai(cleaned_messages)
    
    # Truncate if needed (stay within token limits)
    if estimate_tokens(conversation_text) > 100000:  # Reserve space for output
        conversation_text = truncate_conversation(conversation_text, 100000)
    
    return conversation_text
```

### 2. Discord API Integration

#### 2.1 Discord.py Library Requirements

**Library Version**: discord.py >= 2.3.0
- Async/await support for better performance
- Application commands (slash commands) support
- Thread support for Discord threads
- Voice channel support (future feature)

**Required Intents**:
```python
import discord

intents = discord.Intents.default()
intents.message_content = True  # Required to read message content
intents.guild_messages = True   # Required for message history
intents.guild_reactions = True  # Required for reaction-based triggers
intents.guilds = True          # Required for guild information
intents.members = False        # Not required, privacy-conscious
```

#### 2.2 Bot Configuration & Permissions

**Required Bot Permissions**:
- `READ_MESSAGE_HISTORY`: Access historical messages
- `SEND_MESSAGES`: Send summary responses
- `USE_SLASH_COMMANDS`: Register and use application commands
- `EMBED_LINKS`: Send rich embed responses
- `ADD_REACTIONS`: Add reaction-based feedback
- `VIEW_CHANNEL`: Access channel information
- `MANAGE_MESSAGES`: Clean up bot messages (optional)

**OAuth2 Scopes**:
- `bot`: Basic bot functionality
- `applications.commands`: Slash commands

#### 2.3 Message History Fetching

**Implementation Requirements**:
```python
import discord
from datetime import datetime, timedelta
from typing import List, Optional

class DiscordMessageFetcher:
    def __init__(self, bot: discord.Client):
        self.bot = bot
        self.rate_limiter = DiscordRateLimiter()
    
    async def fetch_messages(
        self,
        channel_id: int,
        hours_back: int = 24,
        limit: Optional[int] = None
    ) -> List[discord.Message]:
        """Fetch messages from a Discord channel with rate limiting"""
        
        try:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                raise ChannelNotFoundError(f"Channel {channel_id} not found")
            
            # Check bot permissions
            permissions = channel.permissions_for(channel.guild.me)
            if not permissions.read_message_history:
                raise InsufficientPermissionsError("Missing READ_MESSAGE_HISTORY permission")
            
            # Calculate time range
            after_time = datetime.utcnow() - timedelta(hours=hours_back)
            
            # Fetch messages with rate limiting
            messages = []
            async for message in channel.history(
                limit=limit,
                after=after_time,
                oldest_first=True
            ):
                await self.rate_limiter.wait_if_needed()
                messages.append(message)
                
                # Progress callback for long operations
                if len(messages) % 100 == 0:
                    await self._progress_callback(len(messages))
            
            return messages
            
        except discord.Forbidden:
            raise InsufficientPermissionsError("Bot lacks permission to access this channel")
        except discord.NotFound:
            raise ChannelNotFoundError(f"Channel {channel_id} not found")
        except discord.HTTPException as e:
            raise DiscordAPIError(f"Discord API error: {e}")
```

**Rate Limiting Strategy**:
```python
class DiscordRateLimiter:
    """Handle Discord API rate limiting"""
    
    def __init__(self):
        self.buckets = {}  # Route-specific rate limit buckets
        self.global_rate_limit = None
    
    async def wait_if_needed(self, route: str = "default"):
        """Wait if rate limited"""
        
        # Check global rate limit
        if self.global_rate_limit and time.time() < self.global_rate_limit:
            wait_time = self.global_rate_limit - time.time()
            await asyncio.sleep(wait_time)
        
        # Check route-specific rate limit
        if route in self.buckets:
            bucket = self.buckets[route]
            if bucket.remaining <= 0 and time.time() < bucket.reset_time:
                wait_time = bucket.reset_time - time.time()
                await asyncio.sleep(wait_time)
```

#### 2.4 Slash Commands Registration

**Command Registration**:
```python
from discord.ext import commands
from discord import app_commands

class SummaryCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(
        name="summarize",
        description="Generate a summary of recent messages"
    )
    @app_commands.describe(
        hours="Number of hours to look back (1-168)",
        format="Summary format",
        details="Include detailed metadata"
    )
    @app_commands.choices(format=[
        app_commands.Choice(name="Brief", value="brief"),
        app_commands.Choice(name="Structured", value="structured"),
        app_commands.Choice(name="Detailed", value="detailed"),
        app_commands.Choice(name="Technical", value="technical")
    ])
    async def summarize(
        self,
        interaction: discord.Interaction,
        hours: app_commands.Range[int, 1, 168] = 24,
        format: str = "structured",
        details: bool = False
    ):
        """Handle /summarize command"""
        
        # Defer response (Discord requires response within 3 seconds)
        await interaction.response.defer()
        
        try:
            # Validate permissions
            if not self._check_permissions(interaction):
                await interaction.followup.send(
                    "You don't have permission to use this command.",
                    ephemeral=True
                )
                return
            
            # Create and queue summary job
            job = await self._create_summary_job(
                guild_id=interaction.guild_id,
                channel_id=interaction.channel_id,
                requester_id=interaction.user.id,
                hours=hours,
                format=format,
                include_details=details
            )
            
            # Send initial response
            embed = discord.Embed(
                title="Summary Generation Started",
                description=f"Job ID: `{job.id}`\nEstimated completion: <t:{int(job.estimated_completion.timestamp())}:R>",
                color=0x00ff00
            )
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send(
                f"Error: {str(e)}",
                ephemeral=True
            )
```

#### 2.5 Thread Support

**Thread Message Fetching**:
```python
async def fetch_thread_messages(
    self, 
    thread_id: int,
    include_parent: bool = True
) -> List[discord.Message]:
    """Fetch messages from a Discord thread"""
    
    thread = self.bot.get_channel(thread_id)
    if not isinstance(thread, discord.Thread):
        raise ValueError("Provided ID is not a thread")
    
    messages = []
    
    # Optionally include the parent message
    if include_parent and thread.starter_message:
        messages.append(thread.starter_message)
    
    # Fetch thread messages
    async for message in thread.history(limit=None, oldest_first=True):
        messages.append(message)
    
    return messages
```

### 3. Webhook Integration Requirements

#### 3.1 Outbound Webhook Configuration

**Webhook Delivery System**:
```python
import aiohttp
import asyncio
from typing import Dict, Any, List

class WebhookDelivery:
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self.retry_delays = [1, 4, 16]  # Exponential backoff
    
    async def deliver_summary(
        self,
        webhook_config: WebhookDestination,
        summary_data: Dict[str, Any]
    ) -> bool:
        """Deliver summary to external webhook with retries"""
        
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'SummaryBot-NG/1.0',
            **webhook_config.headers
        }
        
        # Add authentication if configured
        if webhook_config.auth_type == 'bearer':
            headers['Authorization'] = f"Bearer {webhook_config.auth_config['token']}"
        elif webhook_config.auth_type == 'basic':
            # Basic auth implementation
            pass
        
        payload = {
            'event': 'summary_completed',
            'timestamp': datetime.utcnow().isoformat(),
            'data': summary_data
        }
        
        for attempt in range(len(self.retry_delays) + 1):
            try:
                async with self.session.post(
                    webhook_config.url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=webhook_config.timeout_seconds)
                ) as response:
                    if 200 <= response.status < 300:
                        await self._log_success(webhook_config, response.status)
                        return True
                    elif response.status == 429:
                        # Rate limited, wait longer
                        retry_after = int(response.headers.get('Retry-After', 60))
                        await asyncio.sleep(retry_after)
                    else:
                        await self._log_failure(webhook_config, response.status, await response.text())
                        
            except asyncio.TimeoutError:
                await self._log_failure(webhook_config, 0, "Timeout")
            except aiohttp.ClientError as e:
                await self._log_failure(webhook_config, 0, str(e))
            
            # Wait before retry (except on last attempt)
            if attempt < len(self.retry_delays):
                await asyncio.sleep(self.retry_delays[attempt])
        
        return False
```

#### 3.2 Inbound Webhook Authentication

**API Key Management**:
```python
import secrets
import hashlib
from datetime import datetime, timedelta

class APIKeyManager:
    def __init__(self, db_connection):
        self.db = db_connection
    
    def generate_api_key(self, guild_id: str, name: str) -> str:
        """Generate a new API key for a guild"""
        key = f"sb_{secrets.token_urlsafe(32)}"
        hashed_key = hashlib.sha256(key.encode()).hexdigest()
        
        # Store in database
        self.db.execute("""
            INSERT INTO api_keys (key_hash, guild_id, name, created_at, last_used)
            VALUES (?, ?, ?, ?, NULL)
        """, (hashed_key, guild_id, name, datetime.utcnow()))
        
        return key
    
    def validate_api_key(self, key: str) -> Optional[Dict[str, Any]]:
        """Validate API key and return associated data"""
        hashed_key = hashlib.sha256(key.encode()).hexdigest()
        
        result = self.db.execute("""
            SELECT guild_id, name, created_at, last_used, rate_limit
            FROM api_keys
            WHERE key_hash = ? AND enabled = TRUE
        """, (hashed_key,)).fetchone()
        
        if result:
            # Update last_used timestamp
            self.db.execute("""
                UPDATE api_keys SET last_used = ? WHERE key_hash = ?
            """, (datetime.utcnow(), hashed_key))
            
            return dict(result)
        
        return None
```

### 4. Database Integration Requirements

#### 4.1 Database Abstraction Layer

**Support Multiple Backends**:
```python
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

class DatabaseInterface(ABC):
    """Abstract interface for database operations"""
    
    @abstractmethod
    async def create_summary(self, summary: Summary) -> str:
        """Create a new summary record"""
        pass
    
    @abstractmethod
    async def get_summary(self, summary_id: str) -> Optional[Summary]:
        """Retrieve a summary by ID"""
        pass
    
    @abstractmethod
    async def create_job(self, job: SummaryJob) -> str:
        """Create a new summary job"""
        pass
    
    @abstractmethod
    async def get_pending_jobs(self) -> List[SummaryJob]:
        """Get jobs waiting to be processed"""
        pass

class SQLiteDatabase(DatabaseInterface):
    """SQLite implementation for development"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.connection = None
    
    async def connect(self):
        import aiosqlite
        self.connection = await aiosqlite.connect(self.db_path)
        await self._create_tables()
    
    # Implementation methods...

class PostgreSQLDatabase(DatabaseInterface):
    """PostgreSQL implementation for production"""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.pool = None
    
    async def connect(self):
        import asyncpg
        self.pool = await asyncpg.create_pool(self.connection_string)
    
    # Implementation methods...
```

#### 4.2 Migration System

**Database Migrations**:
```python
class MigrationManager:
    def __init__(self, db: DatabaseInterface):
        self.db = db
        self.migrations = [
            Migration001_InitialSchema(),
            Migration002_AddIndexes(),
            Migration003_AddWebhookSupport(),
            # Add new migrations here
        ]
    
    async def migrate(self):
        """Run all pending migrations"""
        current_version = await self._get_schema_version()
        
        for migration in self.migrations[current_version:]:
            await migration.up(self.db)
            await self._update_schema_version(migration.version)
    
    async def rollback(self, target_version: int):
        """Rollback to a specific schema version"""
        current_version = await self._get_schema_version()
        
        for migration in reversed(self.migrations[target_version:current_version]):
            await migration.down(self.db)
            await self._update_schema_version(migration.version - 1)
```

### 5. External Service Dependencies

#### 5.1 Redis (Optional - Production Caching)

**Redis Integration for Caching & Job Queues**:
```python
import redis.asyncio as redis
import pickle

class RedisIntegration:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
        self.job_queue = "summary_jobs"
    
    async def cache_messages(
        self, 
        cache_key: str, 
        messages: List[DiscordMessage],
        ttl: int = 3600
    ):
        """Cache fetched messages to avoid re-fetching"""
        serialized = pickle.dumps(messages)
        await self.redis.setex(cache_key, ttl, serialized)
    
    async def get_cached_messages(self, cache_key: str) -> Optional[List[DiscordMessage]]:
        """Retrieve cached messages"""
        data = await self.redis.get(cache_key)
        if data:
            return pickle.loads(data)
        return None
    
    async def enqueue_job(self, job: SummaryJob):
        """Add job to processing queue"""
        job_data = job.to_dict()
        await self.redis.lpush(self.job_queue, pickle.dumps(job_data))
    
    async def dequeue_job(self) -> Optional[SummaryJob]:
        """Get next job from queue"""
        data = await self.redis.brpop(self.job_queue, timeout=10)
        if data:
            job_data = pickle.loads(data[1])
            return SummaryJob.from_dict(job_data)
        return None
```

#### 5.2 Monitoring & Logging Integration

**Integration with Monitoring Services**:
```python
import logging
from prometheus_client import Counter, Histogram, Gauge

# Metrics
REQUEST_COUNT = Counter('summary_requests_total', 'Total summary requests', ['type', 'status'])
PROCESSING_TIME = Histogram('summary_processing_seconds', 'Time spent processing summaries')
QUEUE_SIZE = Gauge('job_queue_size', 'Number of jobs in queue')

class MonitoringIntegration:
    def __init__(self):
        self.logger = logging.getLogger('summarybot')
    
    def log_request(self, request_type: str, status: str):
        REQUEST_COUNT.labels(type=request_type, status=status).inc()
    
    def log_processing_time(self, seconds: float):
        PROCESSING_TIME.observe(seconds)
    
    def update_queue_size(self, size: int):
        QUEUE_SIZE.set(size)
```

### 6. Integration Testing Requirements

#### 6.1 API Integration Tests

**OpenAI API Tests**:
```python
import pytest
from unittest.mock import AsyncMock, patch

class TestOpenAIIntegration:
    @pytest.mark.asyncio
    async def test_successful_summary_generation(self):
        """Test successful summary generation"""
        mock_response = {
            "choices": [{
                "message": {
                    "content": "Test summary content"
                }
            }],
            "usage": {
                "total_tokens": 150,
                "prompt_tokens": 100,
                "completion_tokens": 50
            }
        }
        
        with patch('openai.AsyncOpenAI.chat.completions.create') as mock_create:
            mock_create.return_value = MockResponse(mock_response)
            
            integration = OpenAIIntegration("test-api-key")
            result = await integration.generate_summary("Test conversation", "structured")
            
            assert result is not None
            assert "summary" in result
    
    @pytest.mark.asyncio
    async def test_rate_limit_handling(self):
        """Test handling of rate limit errors"""
        with patch('openai.AsyncOpenAI.chat.completions.create') as mock_create:
            mock_create.side_effect = openai.RateLimitError("Rate limit exceeded")
            
            integration = OpenAIIntegration("test-api-key")
            
            with pytest.raises(openai.RateLimitError):
                await integration.generate_summary("Test conversation", "structured")
```

**Discord API Tests**:
```python
class TestDiscordIntegration:
    @pytest.mark.asyncio
    async def test_message_fetching(self):
        """Test message fetching from Discord"""
        # Mock Discord client and messages
        mock_bot = AsyncMock()
        mock_channel = AsyncMock()
        mock_bot.get_channel.return_value = mock_channel
        
        fetcher = DiscordMessageFetcher(mock_bot)
        messages = await fetcher.fetch_messages(12345, hours_back=1)
        
        assert isinstance(messages, list)
        mock_channel.history.assert_called_once()
```

### 7. Security & Compliance Requirements

#### 7.1 Data Privacy

**Message Content Handling**:
- Encrypt API keys and tokens at rest
- Minimize message content retention
- Implement data retention policies
- Support GDPR deletion requests
- Anonymize user data in logs

#### 7.2 API Security

**Webhook Security**:
- HTTPS only for webhook endpoints
- Request signature validation
- IP whitelisting support
- Rate limiting per client
- Request size limits

This comprehensive integration specification ensures robust, secure, and scalable integration with all required external services while maintaining proper error handling and monitoring capabilities.