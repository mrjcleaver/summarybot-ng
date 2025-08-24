# Phase 3: Modular Architecture Design - Summary Bot NG

## 1. System Architecture Overview

### 1.1 Architecture Pattern
The Summary Bot NG follows a **Layered Architecture** with **Dependency Injection** and **Event-Driven** components:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Presentation Layer                           │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Discord Bot   │  │  Webhook API    │  │   CLI Tools     │ │
│  │   Interface     │  │   Interface     │  │   Interface     │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│                   Application Layer                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  Command        │  │  Scheduling     │  │  Configuration  │ │
│  │  Handlers       │  │  Service        │  │  Manager        │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│                    Business Logic Layer                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ Summarization   │  │  Message        │  │   Permission    │ │
│  │   Engine        │  │  Processor      │  │   Manager       │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│                 Infrastructure Layer                           │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Data Access   │  │   External      │  │   Caching       │ │
│  │   Layer         │  │   APIs          │  │   Layer         │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Module Dependencies
```
Core Modules (No Dependencies)
├── config/
├── models/
└── exceptions/

Business Logic Modules (Depend on Core)
├── summarization/
├── message_processing/
└── permissions/

Application Services (Depend on Business Logic)
├── command_handlers/
├── scheduling/
└── webhook_service/

Interface Modules (Depend on Application Services)
├── discord_bot/
├── web_api/
└── cli/
```

## 2. Core Module Specifications

### 2.1 Configuration Module (`config/`)

#### 2.1.1 Module Purpose
Central configuration management with environment variable loading, validation, and type safety.

#### 2.1.2 Module Structure
```
config/
├── __init__.py
├── settings.py          # Main configuration class
├── environment.py       # Environment variable handling
├── validation.py        # Configuration validation
└── defaults.py         # Default configuration values
```

#### 2.1.3 Public Interface
```python
# settings.py
@dataclass
class BotConfig:
    discord_token: str
    claude_api_key: str
    guild_configs: Dict[str, GuildConfig]
    webhook_port: int = 5000
    max_message_batch: int = 10000
    cache_ttl: int = 3600
    
    @classmethod
    def load_from_env(cls) -> 'BotConfig'
    
    def get_guild_config(self, guild_id: str) -> GuildConfig
    
    def validate_configuration(self) -> List[ValidationError]

@dataclass
class GuildConfig:
    guild_id: str
    enabled_channels: List[str]
    excluded_channels: List[str]
    default_summary_options: SummaryOptions
    permission_settings: PermissionSettings
    
class ConfigManager:
    def __init__(self, config_path: Optional[str] = None)
    
    async def load_config(self) -> BotConfig
    async def save_config(self, config: BotConfig) -> None
    async def reload_config(self) -> BotConfig
    def validate_config(self, config: BotConfig) -> bool
```

#### 2.1.4 Dependencies
- **External**: `pydantic`, `python-dotenv`
- **Internal**: None

#### 2.1.5 Testing Strategy
- Unit tests for configuration loading and validation
- Integration tests for environment variable processing
- Configuration schema validation tests

### 2.2 Models Module (`models/`)

#### 2.2.1 Module Purpose
Data models and DTOs for all domain objects with serialization support.

#### 2.2.2 Module Structure
```
models/
├── __init__.py
├── summary.py           # Summary-related models
├── message.py           # Message processing models
├── user.py             # User and permission models
├── task.py             # Scheduled task models
├── webhook.py          # Webhook-related models
└── base.py             # Base model classes
```

#### 2.2.3 Public Interface
```python
# summary.py
@dataclass
class SummaryResult:
    id: str
    channel_id: str
    guild_id: str
    start_time: datetime
    end_time: datetime
    message_count: int
    key_points: List[str]
    action_items: List[ActionItem]
    technical_terms: List[TechnicalTerm]
    participants: List[Participant]
    summary_text: str
    metadata: Dict[str, Any]
    created_at: datetime
    
    def to_dict(self) -> Dict[str, Any]
    def to_embed(self) -> discord.Embed
    def to_markdown(self) -> str
    def to_json(self) -> str

@dataclass
class SummaryOptions:
    summary_length: SummaryLength
    include_bots: bool = False
    include_attachments: bool = True
    excluded_users: List[str] = field(default_factory=list)
    min_messages: int = 5
    claude_model: str = "claude-3-sonnet-20240229"
    temperature: float = 0.3
    max_tokens: int = 4000

# message.py
@dataclass
class ProcessedMessage:
    id: str
    author_name: str
    author_id: str
    content: str
    timestamp: datetime
    thread_info: Optional[ThreadInfo]
    attachments: List[AttachmentInfo]
    references: List[MessageReference]
    
    def clean_content(self) -> str
    def extract_code_blocks(self) -> List[CodeBlock]
    def get_mentions(self) -> List[str]
```

#### 2.2.4 Dependencies
- **External**: `pydantic`, `discord.py`
- **Internal**: None

#### 2.2.5 Testing Strategy
- Model serialization/deserialization tests
- Data validation tests
- Model relationship tests

### 2.3 Exceptions Module (`exceptions/`)

#### 2.3.1 Module Purpose
Custom exception hierarchy for error handling and reporting.

#### 2.3.2 Module Structure
```
exceptions/
├── __init__.py
├── base.py              # Base exception classes
├── summarization.py     # Summarization-specific errors
├── discord_errors.py    # Discord API-related errors
├── api_errors.py        # External API errors
└── validation.py        # Validation errors
```

#### 2.3.3 Public Interface
```python
# base.py
class SummaryBotException(Exception):
    def __init__(self, message: str, error_code: str, context: Dict[str, Any] = None)
    
    @property
    def error_code(self) -> str
    
    @property
    def context(self) -> Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]

# summarization.py
class SummarizationError(SummaryBotException):
    """Raised when summarization process fails"""
    
class ClaudeAPIError(SummaryBotException):
    """Raised when Claude API call fails"""
    
class InsufficientContentError(SummaryBotException):
    """Raised when not enough content for summarization"""

# discord_errors.py
class DiscordPermissionError(SummaryBotException):
    """Raised when bot lacks required Discord permissions"""
    
class ChannelAccessError(SummaryBotException):
    """Raised when channel cannot be accessed"""
```

#### 2.3.4 Dependencies
- **External**: None
- **Internal**: None

#### 2.3.5 Testing Strategy
- Exception hierarchy tests
- Error code validation tests
- Context preservation tests

## 3. Business Logic Modules

### 3.1 Summarization Engine Module (`summarization/`)

#### 3.1.1 Module Purpose
Core AI-powered summarization logic with Claude API integration.

#### 3.1.2 Module Structure
```
summarization/
├── __init__.py
├── engine.py            # Main summarization engine
├── claude_client.py     # Claude API client
├── prompt_builder.py    # Dynamic prompt generation
├── response_parser.py   # Claude response processing
├── cache.py            # Summary caching logic
└── optimization.py     # Performance optimizations
```

#### 3.1.3 Public Interface
```python
# engine.py
class SummarizationEngine:
    def __init__(self, claude_client: ClaudeClient, cache: SummaryCache)
    
    async def summarize_messages(
        self,
        messages: List[ProcessedMessage],
        options: SummaryOptions,
        context: SummarizationContext
    ) -> SummaryResult
    
    async def batch_summarize(
        self,
        requests: List[SummarizationRequest]
    ) -> List[SummaryResult]
    
    def estimate_cost(
        self,
        messages: List[ProcessedMessage],
        options: SummaryOptions
    ) -> CostEstimate

# claude_client.py
class ClaudeClient:
    def __init__(self, api_key: str, base_url: str = None)
    
    async def create_summary(
        self,
        prompt: str,
        system_prompt: str,
        options: ClaudeOptions
    ) -> ClaudeResponse
    
    async def health_check(self) -> bool
    
    def get_usage_stats(self) -> UsageStats

# prompt_builder.py
class PromptBuilder:
    def build_system_prompt(self, options: SummaryOptions) -> str
    
    def build_user_prompt(
        self,
        messages: List[ProcessedMessage],
        context: SummarizationContext
    ) -> str
    
    def optimize_prompt_length(
        self,
        prompt: str,
        max_tokens: int
    ) -> str
```

#### 3.1.4 Dependencies
- **External**: `anthropic`, `asyncio`, `redis` (optional)
- **Internal**: `models`, `exceptions`, `config`

#### 3.1.5 Testing Strategy
- Mock Claude API responses for unit tests
- Integration tests with Claude API
- Prompt quality and optimization tests
- Cache behavior tests

### 3.2 Message Processing Module (`message_processing/`)

#### 3.2.1 Module Purpose
Discord message fetching, filtering, and preprocessing for summarization.

#### 3.2.2 Module Structure
```
message_processing/
├── __init__.py
├── fetcher.py           # Discord message fetching
├── filter.py           # Message filtering logic
├── cleaner.py          # Content cleaning and normalization
├── extractor.py        # Information extraction
└── validator.py        # Message validation
```

#### 3.2.3 Public Interface
```python
# fetcher.py
class MessageFetcher:
    def __init__(self, discord_client: discord.Client)
    
    async def fetch_messages(
        self,
        channel_id: str,
        start_time: datetime,
        end_time: datetime,
        limit: int = None
    ) -> List[discord.Message]
    
    async def fetch_thread_messages(
        self,
        thread_id: str,
        include_parent: bool = True
    ) -> List[discord.Message]

# filter.py
class MessageFilter:
    def __init__(self, options: SummaryOptions)
    
    def filter_messages(
        self,
        messages: List[discord.Message]
    ) -> List[discord.Message]
    
    def is_valid_message(self, message: discord.Message) -> bool
    
    def should_include_bot_message(self, message: discord.Message) -> bool

# cleaner.py
class MessageCleaner:
    def clean_message(self, message: discord.Message) -> ProcessedMessage
    
    def extract_code_blocks(self, content: str) -> List[CodeBlock]
    
    def normalize_mentions(self, content: str) -> str
    
    def remove_formatting(self, content: str) -> str
```

#### 3.2.4 Dependencies
- **External**: `discord.py`, `re`, `html2text`
- **Internal**: `models`, `exceptions`, `config`

#### 3.2.5 Testing Strategy
- Mock Discord message objects for testing
- Message filtering logic tests
- Content cleaning validation tests
- Edge case handling tests

### 3.3 Permission Management Module (`permissions/`)

#### 3.3.1 Module Purpose
User permission validation and access control for bot operations.

#### 3.3.2 Module Structure
```
permissions/
├── __init__.py
├── manager.py           # Main permission manager
├── validators.py        # Permission validation logic
├── roles.py            # Role-based access control
└── cache.py            # Permission caching
```

#### 3.3.3 Public Interface
```python
# manager.py
class PermissionManager:
    def __init__(self, config: BotConfig)
    
    async def check_channel_access(
        self,
        user_id: str,
        channel_id: str,
        guild_id: str
    ) -> bool
    
    async def check_command_permission(
        self,
        user_id: str,
        command: str,
        guild_id: str
    ) -> bool
    
    async def get_user_permissions(
        self,
        user_id: str,
        guild_id: str
    ) -> UserPermissions

# validators.py
class PermissionValidator:
    def validate_summarize_permission(
        self,
        user: discord.User,
        channel: discord.TextChannel
    ) -> ValidationResult
    
    def validate_webhook_access(
        self,
        request: WebhookRequest
    ) -> ValidationResult
```

#### 3.3.4 Dependencies
- **External**: `discord.py`
- **Internal**: `models`, `exceptions`, `config`

#### 3.3.5 Testing Strategy
- Permission validation tests
- Role hierarchy tests
- Cache invalidation tests
- Access control matrix tests

## 4. Application Service Modules

### 4.1 Command Handlers Module (`command_handlers/`)

#### 4.1.1 Module Purpose
Discord slash command processing and response handling.

#### 4.1.2 Module Structure
```
command_handlers/
├── __init__.py
├── base.py              # Base command handler
├── summarize.py         # Summarize command handler
├── config.py           # Configuration commands
├── schedule.py         # Scheduling commands
└── utils.py            # Command utilities
```

#### 4.1.3 Public Interface
```python
# base.py
class BaseCommandHandler:
    def __init__(self, 
                 summarization_engine: SummarizationEngine,
                 permission_manager: PermissionManager)
    
    async def handle_command(self, interaction: discord.Interaction) -> None
    
    async def defer_response(self, interaction: discord.Interaction) -> None
    
    async def send_error_response(
        self,
        interaction: discord.Interaction,
        error: Exception
    ) -> None

# summarize.py
class SummarizeCommandHandler(BaseCommandHandler):
    async def handle_summarize(self, interaction: discord.Interaction) -> None
    
    async def handle_quick_summary(self, interaction: discord.Interaction) -> None
    
    async def handle_scheduled_summary(self, interaction: discord.Interaction) -> None
```

#### 4.1.4 Dependencies
- **External**: `discord.py`
- **Internal**: `summarization`, `permissions`, `models`, `exceptions`

#### 4.1.5 Testing Strategy
- Command interaction tests
- Error handling tests
- Permission integration tests
- Response formatting tests

### 4.2 Scheduling Service Module (`scheduling/`)

#### 4.2.1 Module Purpose
Automated summary generation and task scheduling.

#### 4.2.2 Module Structure
```
scheduling/
├── __init__.py
├── scheduler.py         # Main task scheduler
├── tasks.py            # Task definitions
├── executor.py         # Task execution logic
└── persistence.py      # Task state persistence
```

#### 4.2.3 Public Interface
```python
# scheduler.py
class TaskScheduler:
    def __init__(self,
                 summarization_engine: SummarizationEngine,
                 message_processor: MessageProcessor)
    
    async def start(self) -> None
    
    async def stop(self) -> None
    
    async def schedule_task(self, task: ScheduledTask) -> str
    
    async def cancel_task(self, task_id: str) -> bool
    
    async def get_scheduled_tasks(self, guild_id: str) -> List[ScheduledTask]

# executor.py
class TaskExecutor:
    async def execute_summary_task(self, task: SummaryTask) -> TaskResult
    
    async def execute_cleanup_task(self, task: CleanupTask) -> TaskResult
    
    async def handle_task_failure(
        self,
        task: ScheduledTask,
        error: Exception
    ) -> None
```

#### 4.2.4 Dependencies
- **External**: `asyncio`, `apscheduler`
- **Internal**: `summarization`, `message_processing`, `models`

#### 4.2.5 Testing Strategy
- Task scheduling tests
- Task execution tests  
- Failure recovery tests
- Persistence tests

### 4.3 Webhook Service Module (`webhook_service/`)

#### 4.3.1 Module Purpose
HTTP API endpoints for external integrations and webhook handling.

#### 4.3.2 Module Structure
```
webhook_service/
├── __init__.py
├── server.py           # FastAPI server setup
├── endpoints.py        # API endpoint definitions
├── auth.py            # Authentication middleware
├── validators.py      # Request validation
└── formatters.py      # Response formatting
```

#### 4.3.3 Public Interface
```python
# server.py
class WebhookServer:
    def __init__(self,
                 config: BotConfig,
                 summarization_engine: SummarizationEngine)
    
    async def start_server(self) -> None
    
    async def stop_server(self) -> None
    
    def get_app(self) -> FastAPI

# endpoints.py
class SummaryEndpoints:
    @app.post("/api/v1/summarize")
    async def create_summary(request: SummaryRequest) -> SummaryResponse
    
    @app.get("/api/v1/summary/{summary_id}")
    async def get_summary(summary_id: str) -> SummaryResponse
    
    @app.post("/api/v1/schedule")
    async def schedule_summary(request: ScheduleRequest) -> ScheduleResponse
```

#### 4.3.4 Dependencies
- **External**: `fastapi`, `uvicorn`, `pydantic`
- **Internal**: `summarization`, `permissions`, `models`, `exceptions`

#### 4.3.5 Testing Strategy
- API endpoint tests
- Authentication tests
- Request validation tests
- Response formatting tests

## 5. Infrastructure Modules

### 5.1 Data Access Layer (`data/`)

#### 5.1.1 Module Purpose
Database operations and data persistence with support for multiple backends.

#### 5.1.2 Module Structure
```
data/
├── __init__.py
├── base.py             # Abstract data access interfaces
├── sqlite.py          # SQLite implementation
├── postgresql.py      # PostgreSQL implementation
├── migrations/        # Database migrations
└── repositories/      # Repository pattern implementations
```

#### 5.1.3 Public Interface
```python
# base.py
class SummaryRepository(ABC):
    @abstractmethod
    async def save_summary(self, summary: SummaryResult) -> str
    
    @abstractmethod
    async def get_summary(self, summary_id: str) -> Optional[SummaryResult]
    
    @abstractmethod
    async def find_summaries(self, criteria: SearchCriteria) -> List[SummaryResult]
    
    @abstractmethod
    async def delete_summary(self, summary_id: str) -> bool

class ConfigRepository(ABC):
    @abstractmethod
    async def save_guild_config(self, config: GuildConfig) -> None
    
    @abstractmethod
    async def get_guild_config(self, guild_id: str) -> Optional[GuildConfig]
```

#### 5.1.4 Dependencies
- **External**: `sqlalchemy`, `aiosqlite`, `asyncpg`
- **Internal**: `models`, `exceptions`

#### 5.1.5 Testing Strategy
- Repository pattern tests
- Database migration tests
- Transaction handling tests
- Connection pooling tests

### 5.2 Caching Layer (`cache/`)

#### 5.2.1 Module Purpose
Summary and configuration caching with multiple backend support.

#### 5.2.2 Module Structure
```
cache/
├── __init__.py
├── base.py             # Abstract cache interfaces
├── memory.py          # In-memory cache implementation
├── redis.py           # Redis cache implementation
└── utils.py           # Cache utilities and helpers
```

#### 5.2.3 Public Interface
```python
# base.py
class CacheInterface(ABC):
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int = None) -> bool
    
    @abstractmethod
    async def delete(self, key: str) -> bool
    
    @abstractmethod
    async def clear(self, pattern: str = None) -> int

class SummaryCache:
    def __init__(self, backend: CacheInterface)
    
    async def get_cached_summary(
        self,
        channel_id: str,
        start_time: datetime,
        end_time: datetime,
        options_hash: str
    ) -> Optional[SummaryResult]
    
    async def cache_summary(
        self,
        summary: SummaryResult,
        ttl: int = 3600
    ) -> None
```

#### 5.2.4 Dependencies
- **External**: `redis`, `pickle`, `hashlib`
- **Internal**: `models`, `config`

#### 5.2.5 Testing Strategy
- Cache operations tests
- TTL expiration tests
- Serialization tests
- Backend switching tests

## 6. Interface Modules

### 6.1 Discord Bot Module (`discord_bot/`)

#### 6.1.1 Module Purpose
Main Discord bot client and event handling.

#### 6.1.2 Module Structure
```
discord_bot/
├── __init__.py
├── bot.py              # Main bot client
├── events.py          # Discord event handlers
├── commands.py        # Command registration
└── utils.py           # Bot utilities
```

#### 6.1.3 Public Interface
```python
# bot.py
class SummaryBot:
    def __init__(self, config: BotConfig, services: ServiceContainer)
    
    async def start(self) -> None
    
    async def stop(self) -> None
    
    async def setup_commands(self) -> None
    
    async def sync_commands(self, guild_id: str = None) -> None

# events.py
class EventHandler:
    def __init__(self, bot: SummaryBot)
    
    async def on_ready(self) -> None
    
    async def on_guild_join(self, guild: discord.Guild) -> None
    
    async def on_application_command_error(
        self,
        interaction: discord.Interaction,
        error: Exception
    ) -> None
```

#### 6.1.4 Dependencies
- **External**: `discord.py`
- **Internal**: `command_handlers`, `config`, `exceptions`

#### 6.1.5 Testing Strategy
- Bot lifecycle tests
- Event handling tests
- Command registration tests
- Error handling tests

### 6.2 Dependency Injection Container

#### 6.2.1 Service Container
```python
# container.py
class ServiceContainer:
    def __init__(self, config: BotConfig)
    
    def configure_services(self) -> None
    
    def get_summarization_engine(self) -> SummarizationEngine
    
    def get_message_processor(self) -> MessageProcessor
    
    def get_permission_manager(self) -> PermissionManager
    
    def get_command_handlers(self) -> Dict[str, BaseCommandHandler]
```

## 7. Module Integration & Communication

### 7.1 Event System
```python
# events/event_bus.py
class EventBus:
    async def publish(self, event: Event) -> None
    
    def subscribe(self, event_type: Type[Event], handler: EventHandler) -> None
    
    def unsubscribe(self, event_type: Type[Event], handler: EventHandler) -> None

# Event types
class SummaryCompleted(Event):
    summary: SummaryResult
    
class TaskScheduled(Event):
    task: ScheduledTask
    
class ConfigurationChanged(Event):
    guild_id: str
    old_config: GuildConfig
    new_config: GuildConfig
```

### 7.2 Inter-Module Communication
- **Async/Await**: All I/O operations use async patterns
- **Dependency Injection**: Services injected through container
- **Event-Driven**: Loose coupling through event bus
- **Interface Segregation**: Small, focused interfaces

## 8. Testing Architecture

### 8.1 Test Module Structure
```
tests/
├── unit/               # Unit tests per module
│   ├── test_config/
│   ├── test_models/
│   ├── test_summarization/
│   └── ...
├── integration/        # Integration tests
│   ├── test_discord_integration/
│   ├── test_claude_integration/
│   └── test_webhook_integration/
├── e2e/               # End-to-end tests
│   ├── test_full_workflow/
│   └── test_error_scenarios/
├── fixtures/          # Test data and mocks
└── utils/            # Test utilities
```

### 8.2 Test Strategy Summary
- **Unit Tests**: 90%+ coverage per module
- **Integration Tests**: Cross-module interaction validation  
- **E2E Tests**: Complete user workflow testing
- **Performance Tests**: Load and stress testing
- **Security Tests**: Permission and validation testing

---

**Document Version**: 1.0  
**Last Updated**: 2024-08-24  
**Next Phase**: Testing Strategy (Phase 4)  
**Module Count**: 12 core modules + 6 infrastructure modules