# Command Logging System - Specification

## 1. Introduction

### 1.1 Purpose
This document specifies a comprehensive command logging system for Summary Bot NG that tracks all command executions across Discord slash commands, scheduled tasks, and webhook endpoints to provide audit trails, debugging capabilities, and operational insights.

### 1.2 Scope
- Log ALL command executions (Discord, scheduled, webhooks)
- Capture execution context, parameters, and results
- Support querying and analysis of historical commands
- Ensure sensitive data protection
- Enable performance monitoring and debugging

### 1.3 Out of Scope
- User behavior analytics beyond command execution
- Real-time alerting (future enhancement)
- Integration with external monitoring services (future enhancement)

---

## 2. Functional Requirements

### FR-1: Command Logging
**Priority:** High
**Description:** System shall log all command executions with complete context

**Acceptance Criteria:**
- All Discord slash commands are logged before and after execution
- All scheduled task executions are logged with scheduling context
- All webhook requests are logged with authentication metadata
- Each log entry includes unique identifier and timestamp
- Log entries capture both success and failure cases

### FR-2: Data Capture
**Priority:** High
**Description:** System shall capture comprehensive command metadata

**Acceptance Criteria:**
- Command type (slash_command, scheduled_task, webhook_request)
- Execution context (user_id, guild_id, channel_id)
- Command parameters (sanitized for sensitive data)
- Execution timing (start_time, end_time, duration_ms)
- Execution results (success/failure, error codes, output summary)
- Request metadata (IP address, user agent for webhooks)

### FR-3: Sensitive Data Protection
**Priority:** Critical
**Description:** System shall protect sensitive information in logs

**Acceptance Criteria:**
- API keys are never stored in logs
- Passwords and tokens are redacted
- User messages content is summarized, not stored verbatim
- Webhook signatures are hashed, not stored
- PII is minimized according to data retention policy

### FR-4: Query Interface
**Priority:** Medium
**Description:** System shall provide query capabilities for log analysis

**Acceptance Criteria:**
- Query by time range (start_time, end_time)
- Filter by command type, user_id, guild_id, channel_id
- Filter by execution status (success, failed, timeout)
- Pagination support (limit, offset)
- Order by timestamp (ascending/descending)
- Export results as JSON or CSV

### FR-5: Performance Requirements
**Priority:** High
**Description:** Logging shall not impact command execution performance

**Acceptance Criteria:**
- Async logging with non-blocking writes
- Maximum 10ms overhead for log entry creation
- Batch writes for scheduled task logs
- Database writes use connection pooling
- No command execution blocked by logging failures

### FR-6: Log Retention
**Priority:** Medium
**Description:** System shall manage log retention and cleanup

**Acceptance Criteria:**
- Configurable retention period (default: 90 days)
- Automatic cleanup of expired logs
- Archive option for long-term storage
- Manual cleanup commands for administrators
- Retention policy per guild (optional)

---

## 3. Non-Functional Requirements

### NFR-1: Performance
- **Latency:** Logging adds <10ms to command execution
- **Throughput:** Support 1000 log writes per second
- **Storage:** Efficient indexing for <100ms query response

### NFR-2: Scalability
- **Volume:** Handle 10M+ log entries
- **Growth:** Support partitioning by time period
- **Cleanup:** Batch deletion without blocking

### NFR-3: Reliability
- **Durability:** ACID guarantees for critical logs
- **Recovery:** Graceful degradation if logging fails
- **Consistency:** All command executions logged exactly once

### NFR-4: Security
- **Access Control:** Only admins can query logs
- **Encryption:** Sensitive fields encrypted at rest
- **Audit Trail:** Log access is itself logged
- **Compliance:** GDPR-compliant data retention

### NFR-5: Maintainability
- **Modularity:** <500 lines per module
- **Testing:** 90%+ test coverage
- **Documentation:** Inline and API documentation
- **Configuration:** Environment-based settings

---

## 4. Data Model Specification

### 4.1 Command Log Entry

```yaml
entity: CommandLog
description: Records a single command execution
table_name: command_logs

attributes:
  id:
    type: TEXT (UUID)
    constraints: PRIMARY KEY
    description: Unique log entry identifier

  command_type:
    type: TEXT (ENUM)
    constraints: NOT NULL
    values: [slash_command, scheduled_task, webhook_request]
    description: Type of command executed

  command_name:
    type: TEXT
    constraints: NOT NULL
    description: Name/identifier of command (e.g., "summarize", "schedule_create")

  user_id:
    type: TEXT
    nullable: true
    description: Discord user ID (null for scheduled tasks)

  guild_id:
    type: TEXT
    constraints: NOT NULL
    indexed: true
    description: Discord guild ID

  channel_id:
    type: TEXT
    constraints: NOT NULL
    indexed: true
    description: Discord channel ID

  parameters:
    type: TEXT (JSON)
    constraints: NOT NULL
    default: '{}'
    description: Command parameters (sanitized)

  execution_context:
    type: TEXT (JSON)
    constraints: NOT NULL
    default: '{}'
    description: Additional context (IP, user_agent, task_id, etc.)

  status:
    type: TEXT (ENUM)
    constraints: NOT NULL
    values: [success, failed, timeout, cancelled]
    indexed: true
    description: Execution outcome

  error_code:
    type: TEXT
    nullable: true
    description: Error code if failed

  error_message:
    type: TEXT
    nullable: true
    description: Error message (sanitized)

  started_at:
    type: TEXT (ISO8601)
    constraints: NOT NULL
    indexed: true
    description: Command execution start time

  completed_at:
    type: TEXT (ISO8601)
    nullable: true
    description: Command execution completion time

  duration_ms:
    type: INTEGER
    nullable: true
    description: Execution duration in milliseconds

  result_summary:
    type: TEXT (JSON)
    nullable: true
    description: Summary of execution results (messages processed, summary length, etc.)

  metadata:
    type: TEXT (JSON)
    constraints: NOT NULL
    default: '{}'
    description: Extensible metadata field

indexes:
  - name: idx_command_logs_guild_time
    columns: [guild_id, started_at DESC]

  - name: idx_command_logs_user_time
    columns: [user_id, started_at DESC]

  - name: idx_command_logs_type_status
    columns: [command_type, status]

  - name: idx_command_logs_started_at
    columns: [started_at DESC]

  - name: idx_command_logs_channel_time
    columns: [channel_id, started_at DESC]

constraints:
  - CHECK (duration_ms >= 0)
  - CHECK (completed_at >= started_at OR completed_at IS NULL)
```

### 4.2 Sensitive Data Sanitization Rules

```yaml
sanitization_rules:
  api_keys:
    action: redact
    replacement: "[REDACTED_API_KEY]"

  passwords:
    action: redact
    replacement: "[REDACTED_PASSWORD]"

  tokens:
    action: redact
    replacement: "[REDACTED_TOKEN]"
    patterns:
      - ".*token.*"
      - ".*secret.*"
      - ".*key.*"
    case_insensitive: true

  webhook_signatures:
    action: hash
    algorithm: sha256
    prefix: "sha256:"

  message_content:
    action: truncate
    max_length: 200
    suffix: "... [truncated]"

  email_addresses:
    action: mask
    pattern: "(.{2}).*@(.*)(.{2})"
    replacement: "$1***@***$2"

  ip_addresses:
    action: mask_partial
    pattern: "(\\d+\\.\\d+)\\.(\\d+\\.\\d+)"
    replacement: "$1.*.***"
```

---

## 5. Architecture Specification

### 5.1 System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Command Sources                          │
├─────────────────────────────────────────────────────────────┤
│  Discord Commands  │  Scheduled Tasks  │  Webhook Requests  │
└──────────┬──────────────────┬────────────────────┬──────────┘
           │                  │                    │
           v                  v                    v
    ┌──────────────────────────────────────────────────────┐
    │            Command Logging Middleware                 │
    │  - CommandLogDecorator                               │
    │  - ScheduledTaskLogger                               │
    │  - WebhookRequestLogger                              │
    └──────────────────────────┬───────────────────────────┘
                               │
                               v
                    ┌──────────────────────┐
                    │  LogSanitizer        │
                    │  - Redact secrets    │
                    │  - Hash signatures   │
                    │  - Truncate content  │
                    └──────────┬───────────┘
                               │
                               v
                    ┌──────────────────────┐
                    │  CommandLogRepository│
                    │  - Async writes      │
                    │  - Batch operations  │
                    │  - Query interface   │
                    └──────────┬───────────┘
                               │
                               v
                    ┌──────────────────────┐
                    │  Database (SQLite)   │
                    │  - command_logs      │
                    │  - Indexes           │
                    └──────────────────────┘
```

### 5.2 Module Structure

```
src/
├── logging/
│   ├── __init__.py
│   ├── models.py              # CommandLog, LogEntry data classes
│   ├── logger.py              # CommandLogger main class
│   ├── decorators.py          # @log_command decorator
│   ├── sanitizer.py           # LogSanitizer for sensitive data
│   ├── repository.py          # CommandLogRepository
│   └── query.py               # LogQueryBuilder, LogAnalyzer
├── data/
│   └── migrations/
│       └── 002_command_logs.sql   # Database schema
└── config/
    └── logging_config.py      # Configuration settings
```

---

## 6. Integration Points

### 6.1 Discord Command Integration

**Location:** `src/command_handlers/base.py`

**Integration Method:** Decorator pattern on `handle_command()`

**Pseudocode:**
```python
class BaseCommandHandler:
    @log_command(command_type="slash_command")
    async def handle_command(self, interaction, **kwargs):
        # Existing logic
        pass
```

### 6.2 Scheduled Task Integration

**Location:** `src/scheduling/executor.py`

**Integration Method:** Before/after hooks in task execution

**Pseudocode:**
```python
class TaskExecutor:
    async def execute_task(self, task: SummaryTask):
        log_entry = await self.logger.start_task_log(task)
        try:
            result = await self._run_task(task)
            await self.logger.complete_task_log(log_entry, result)
        except Exception as e:
            await self.logger.fail_task_log(log_entry, e)
```

### 6.3 Webhook Integration

**Location:** `src/webhook_service/endpoints.py`

**Integration Method:** Middleware on FastAPI endpoints

**Pseudocode:**
```python
@router.post("/summaries")
@log_webhook_request
async def create_summary_from_messages(request: Dict[str, Any]):
    # Existing logic
    pass
```

---

## 7. Storage Strategy

### 7.1 Database Schema (SQLite)

```sql
-- See migration file: 002_command_logs.sql
CREATE TABLE command_logs (
    id TEXT PRIMARY KEY,
    command_type TEXT NOT NULL,
    command_name TEXT NOT NULL,
    user_id TEXT,
    guild_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    parameters TEXT NOT NULL,          -- JSON
    execution_context TEXT NOT NULL,   -- JSON
    status TEXT NOT NULL,
    error_code TEXT,
    error_message TEXT,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    duration_ms INTEGER,
    result_summary TEXT,               -- JSON
    metadata TEXT NOT NULL DEFAULT '{}' -- JSON
);

-- Indexes for performance
CREATE INDEX idx_command_logs_guild_time
    ON command_logs(guild_id, started_at DESC);
CREATE INDEX idx_command_logs_user_time
    ON command_logs(user_id, started_at DESC);
CREATE INDEX idx_command_logs_type_status
    ON command_logs(command_type, status);
CREATE INDEX idx_command_logs_started_at
    ON command_logs(started_at DESC);
CREATE INDEX idx_command_logs_channel_time
    ON command_logs(channel_id, started_at DESC);
```

### 7.2 Partitioning Strategy (Future)

For PostgreSQL migration, partition by month:
```sql
CREATE TABLE command_logs_2024_01 PARTITION OF command_logs
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
```

---

## 8. Query Interface Specification

### 8.1 Search API

```python
class CommandLogQuery:
    """Query builder for command logs."""

    def __init__(self):
        self.filters = {}
        self.time_range = None
        self.limit = 100
        self.offset = 0
        self.order_by = "started_at"
        self.order_direction = "DESC"

    def by_guild(self, guild_id: str) -> 'CommandLogQuery':
        """Filter by guild ID."""

    def by_user(self, user_id: str) -> 'CommandLogQuery':
        """Filter by user ID."""

    def by_channel(self, channel_id: str) -> 'CommandLogQuery':
        """Filter by channel ID."""

    def by_command_type(self, command_type: str) -> 'CommandLogQuery':
        """Filter by command type."""

    def by_status(self, status: str) -> 'CommandLogQuery':
        """Filter by execution status."""

    def in_time_range(self, start: datetime, end: datetime) -> 'CommandLogQuery':
        """Filter by time range."""

    def paginate(self, limit: int, offset: int) -> 'CommandLogQuery':
        """Set pagination."""

    async def execute(self) -> List[CommandLog]:
        """Execute query and return results."""

    async def count(self) -> int:
        """Count matching records."""
```

### 8.2 Example Queries

```python
# Get last 50 failed commands in a guild
logs = await CommandLogQuery() \
    .by_guild("123456789") \
    .by_status("failed") \
    .paginate(limit=50, offset=0) \
    .execute()

# Get all commands by a user in last 24 hours
logs = await CommandLogQuery() \
    .by_user("987654321") \
    .in_time_range(
        start=datetime.utcnow() - timedelta(days=1),
        end=datetime.utcnow()
    ) \
    .execute()

# Count webhook requests today
count = await CommandLogQuery() \
    .by_command_type("webhook_request") \
    .in_time_range(
        start=datetime.utcnow().replace(hour=0, minute=0),
        end=datetime.utcnow()
    ) \
    .count()
```

---

## 9. Configuration Specification

### 9.1 Environment Variables

```bash
# Command Logging Configuration
COMMAND_LOG_ENABLED=true
COMMAND_LOG_LEVEL=INFO
COMMAND_LOG_RETENTION_DAYS=90
COMMAND_LOG_BATCH_SIZE=100
COMMAND_LOG_ASYNC_WRITES=true

# Sensitive Data Protection
COMMAND_LOG_SANITIZE_ENABLED=true
COMMAND_LOG_TRUNCATE_MESSAGES=true
COMMAND_LOG_MAX_MESSAGE_LENGTH=200
COMMAND_LOG_REDACT_PATTERNS=token,secret,key,password,api_key

# Performance Tuning
COMMAND_LOG_MAX_QUEUE_SIZE=10000
COMMAND_LOG_FLUSH_INTERVAL_SECONDS=5
COMMAND_LOG_CONNECTION_POOL_SIZE=10

# Cleanup Configuration
COMMAND_LOG_AUTO_CLEANUP=true
COMMAND_LOG_CLEANUP_SCHEDULE="0 2 * * *"  # Daily at 2 AM
```

### 9.2 Configuration Class

```python
@dataclass
class CommandLoggingConfig:
    """Configuration for command logging system."""

    enabled: bool = True
    log_level: str = "INFO"
    retention_days: int = 90
    batch_size: int = 100
    async_writes: bool = True

    # Sanitization
    sanitize_enabled: bool = True
    truncate_messages: bool = True
    max_message_length: int = 200
    redact_patterns: List[str] = field(default_factory=lambda: [
        "token", "secret", "key", "password", "api_key"
    ])

    # Performance
    max_queue_size: int = 10000
    flush_interval_seconds: int = 5
    connection_pool_size: int = 10

    # Cleanup
    auto_cleanup: bool = True
    cleanup_schedule: str = "0 2 * * *"

    @classmethod
    def from_env(cls) -> 'CommandLoggingConfig':
        """Load configuration from environment variables."""
        return cls(
            enabled=os.getenv("COMMAND_LOG_ENABLED", "true").lower() == "true",
            log_level=os.getenv("COMMAND_LOG_LEVEL", "INFO"),
            retention_days=int(os.getenv("COMMAND_LOG_RETENTION_DAYS", "90")),
            # ... etc
        )
```

---

## 10. Testing Strategy

### 10.1 Unit Tests

```python
# test_command_logger.py
async def test_log_slash_command_success():
    """Test logging successful slash command."""

async def test_log_slash_command_failure():
    """Test logging failed slash command."""

async def test_sanitize_api_key():
    """Test API key sanitization."""

async def test_sanitize_message_content():
    """Test message content truncation."""
```

### 10.2 Integration Tests

```python
# test_logging_integration.py
async def test_discord_command_logging_integration():
    """Test full Discord command logging flow."""

async def test_scheduled_task_logging_integration():
    """Test scheduled task logging flow."""

async def test_webhook_logging_integration():
    """Test webhook request logging flow."""
```

### 10.3 Performance Tests

```python
# test_logging_performance.py
async def test_logging_overhead_under_10ms():
    """Verify logging adds <10ms overhead."""

async def test_batch_write_throughput():
    """Test batch write performance."""

async def test_query_performance_large_dataset():
    """Test query performance with 1M+ records."""
```

---

## 11. Migration Plan

### Phase 1: Foundation (Week 1)
- Create data models and database schema
- Implement sanitizer and repository
- Unit tests for core components

### Phase 2: Integration (Week 2)
- Integrate with Discord command handlers
- Integrate with scheduled tasks
- Integrate with webhook endpoints

### Phase 3: Query Interface (Week 3)
- Implement query builder
- Add admin query commands
- Dashboard/reporting tools

### Phase 4: Optimization (Week 4)
- Performance testing and tuning
- Implement cleanup automation
- Documentation and training

---

## 12. Success Metrics

### 12.1 Technical Metrics
- **Performance:** <10ms logging overhead (95th percentile)
- **Reliability:** 99.9% log write success rate
- **Coverage:** 100% of commands logged
- **Query Speed:** <100ms for common queries

### 12.2 Operational Metrics
- **Debugging:** 50% reduction in time to diagnose issues
- **Audit:** 100% audit trail compliance
- **Storage:** <5GB storage per 1M commands
- **Retention:** Automated cleanup maintains target retention

---

## Appendix A: Security Considerations

### A.1 Threat Model
- **Threat:** Sensitive data exposure in logs
- **Mitigation:** Sanitization rules, encryption at rest

- **Threat:** Unauthorized log access
- **Mitigation:** Admin-only access, access logging

- **Threat:** Log tampering
- **Mitigation:** ACID guarantees, append-only design

### A.2 Compliance
- **GDPR:** Data minimization, retention limits, right to deletion
- **CCPA:** User data access and deletion support
- **SOC2:** Audit trail requirements met

---

## Appendix B: Example Log Entries

### B.1 Slash Command Log
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "command_type": "slash_command",
  "command_name": "summarize",
  "user_id": "123456789012345678",
  "guild_id": "987654321098765432",
  "channel_id": "111222333444555666",
  "parameters": {
    "messages": 100,
    "length": "detailed"
  },
  "execution_context": {
    "interaction_id": "abc123xyz789",
    "locale": "en-US"
  },
  "status": "success",
  "started_at": "2024-01-15T14:30:00.000Z",
  "completed_at": "2024-01-15T14:30:03.250Z",
  "duration_ms": 3250,
  "result_summary": {
    "messages_processed": 98,
    "summary_length": 450,
    "key_points_count": 5
  }
}
```

### B.2 Scheduled Task Log
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "command_type": "scheduled_task",
  "command_name": "daily_summary",
  "user_id": null,
  "guild_id": "987654321098765432",
  "channel_id": "111222333444555666",
  "parameters": {
    "schedule_type": "daily",
    "time_range_hours": 24
  },
  "execution_context": {
    "task_id": "task_abc123",
    "scheduled_time": "2024-01-15T09:00:00.000Z",
    "actual_time": "2024-01-15T09:00:02.123Z"
  },
  "status": "success",
  "started_at": "2024-01-15T09:00:02.123Z",
  "completed_at": "2024-01-15T09:00:08.456Z",
  "duration_ms": 6333,
  "result_summary": {
    "messages_processed": 245,
    "destinations_delivered": 2
  }
}
```

### B.3 Webhook Request Log
```json
{
  "id": "770e8400-e29b-41d4-a716-446655440002",
  "command_type": "webhook_request",
  "command_name": "create_summary",
  "user_id": null,
  "guild_id": "987654321098765432",
  "channel_id": "111222333444555666",
  "parameters": {
    "message_count": 50
  },
  "execution_context": {
    "source_ip": "192.168.*.***",
    "user_agent": "Zapier/1.0",
    "auth_method": "api_key",
    "signature_hash": "sha256:abc123..."
  },
  "status": "success",
  "started_at": "2024-01-15T10:15:30.000Z",
  "completed_at": "2024-01-15T10:15:32.500Z",
  "duration_ms": 2500,
  "result_summary": {
    "summary_id": "sum_1234567890"
  }
}
```

---

**Document Version:** 1.0
**Last Updated:** 2024-01-15
**Author:** SPARC Specification Agent
**Status:** Draft for Review
