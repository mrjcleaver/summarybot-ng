# Cross-Server Summarization Mode - SPARC Specification

## Executive Summary

This document specifies a **cross-server (cross-guild) summarization mode** that enables authorized users to generate unified summaries from channels spanning multiple Discord servers. This is designed for organizations, communities, or individuals who manage related servers and need consolidated intelligence across their network.

---

## 1. SPECIFICATION

### 1.1 Problem Statement

Organizations often operate multiple Discord servers for different purposes:
- Regional communities (EU, NA, APAC servers)
- Product-specific servers (App A, App B, Platform)
- Team-specific servers (Engineering, Marketing, Support)
- Event-based servers (Conference 2024, Hackathon, etc.)

Currently, summaries are scoped to a single guild. Users must manually:
1. Request summaries from each server individually
2. Mentally synthesize information across summaries
3. Track action items scattered across multiple outputs

### 1.2 Goals

| Goal | Description | Success Metric |
|------|-------------|----------------|
| **G1** | Enable unified summaries across 2-10 servers | Single summary from N servers |
| **G2** | Maintain security through explicit consent | Zero unauthorized cross-server access |
| **G3** | Preserve per-server context in output | Clear server attribution in summaries |
| **G4** | Support scheduled cross-server summaries | Cron-based automated federation |
| **G5** | Minimize API overhead | <20% token increase vs separate summaries |

### 1.3 Non-Goals (Out of Scope)

- Real-time cross-server message streaming
- Cross-server moderation or actions
- Public federation (servers must be explicitly linked)
- Cross-platform summarization (Slack, Teams, etc.)

### 1.4 Constraints

| Constraint | Rationale |
|------------|-----------|
| Bot must be member of all target servers | Discord API requirement |
| User must have summary permissions in ALL servers | Security |
| Maximum 10 servers per federation | Performance/token limits |
| Maximum 50 channels per cross-server summary | API rate limits |
| Servers must opt-in to federation | Privacy/consent |

### 1.5 User Stories

```gherkin
Feature: Cross-Server Summarization

  Scenario: Organization admin creates federation
    Given I am an admin in servers "Engineering", "Support", and "Product"
    And the bot is installed in all three servers
    When I run `/federation create name:"Product Team" servers:Engineering,Support,Product`
    Then a federation is created with me as owner
    And each server admin receives a consent request
    And the federation becomes active only after all consent

  Scenario: User requests cross-server summary
    Given I have the "Cross-Server Summarizer" role in federation "Product Team"
    When I run `/summarize federation:"Product Team" hours:24`
    Then messages are collected from all federated channels
    And a unified summary is generated with server context
    And the summary is delivered to my current channel

  Scenario: Scheduled cross-server summary
    Given federation "Product Team" exists and is active
    When I run `/schedule federation:"Product Team" frequency:daily time:09:00 destination:#daily-digest`
    Then a daily summary task is created
    And it executes at 09:00 UTC each day
    And summaries are posted to #daily-digest

  Scenario: Server leaves federation
    Given "Support" server admin revokes federation consent
    When the next cross-server summary runs
    Then "Support" channels are excluded
    And federation owner is notified
    And summary proceeds with remaining servers
```

### 1.6 Acceptance Criteria

- [ ] Federation creation with multi-server consent flow
- [ ] Cross-server message collection with rate limiting
- [ ] Unified summarization with server attribution
- [ ] Permission validation across all federated servers
- [ ] Scheduled task support for federations
- [ ] Federation management (add/remove servers, transfer ownership)
- [ ] Audit logging for all cross-server operations
- [ ] Graceful degradation when servers become unavailable

---

## 2. PSEUDOCODE

### 2.1 Federation Creation Flow

```pseudocode
FUNCTION create_federation(owner_id, federation_name, server_ids):
    // Validate owner has admin in all servers
    FOR each server_id IN server_ids:
        IF NOT user_is_admin(owner_id, server_id):
            RETURN Error("You must be admin in all servers")
        IF NOT bot_is_member(server_id):
            RETURN Error("Bot not installed in server {server_id}")

    // Create pending federation
    federation = Federation(
        id: generate_uuid(),
        name: federation_name,
        owner_id: owner_id,
        status: "pending_consent",
        created_at: now()
    )

    // Create server links with pending consent
    FOR each server_id IN server_ids:
        link = FederationServer(
            federation_id: federation.id,
            server_id: server_id,
            consent_status: "pending",
            consented_by: null,
            consented_at: null
        )
        SAVE link

        // Notify server admins
        admin_channel = get_admin_channel(server_id)
        SEND consent_request_embed(federation, admin_channel)

    SAVE federation
    RETURN federation

FUNCTION handle_consent_response(federation_id, server_id, admin_id, approved):
    link = GET FederationServer WHERE federation_id AND server_id

    IF approved:
        link.consent_status = "approved"
        link.consented_by = admin_id
        link.consented_at = now()
    ELSE:
        link.consent_status = "denied"
        link.denied_by = admin_id
        link.denied_at = now()

    SAVE link

    // Check if all servers consented
    federation = GET Federation WHERE id = federation_id
    all_links = GET FederationServer WHERE federation_id

    IF all approved:
        federation.status = "active"
        NOTIFY owner("Federation is now active")
    ELSE IF any denied:
        federation.status = "partial"
        NOTIFY owner("Server {name} denied federation")

    SAVE federation
```

### 2.2 Cross-Server Message Collection

```pseudocode
FUNCTION collect_federation_messages(federation_id, time_range, options):
    federation = GET Federation WHERE id = federation_id

    IF federation.status != "active":
        RETURN Error("Federation not active")

    // Get all consented servers
    active_links = GET FederationServer
        WHERE federation_id AND consent_status = "approved"

    all_messages = []
    collection_errors = []

    // Collect from each server in parallel with rate limiting
    semaphore = Semaphore(3)  // Max 3 concurrent servers

    FOR each link IN active_links PARALLEL:
        WITH semaphore:
            TRY:
                server = GET discord_server(link.server_id)
                channels = get_summarizable_channels(server, options)

                FOR each channel IN channels:
                    IF user_can_access(channel, requesting_user):
                        messages = fetch_messages(channel, time_range)

                        // Tag with server context
                        FOR each msg IN messages:
                            msg.server_name = server.name
                            msg.server_id = server.id

                        all_messages.extend(messages)
            CATCH error:
                collection_errors.append({
                    server_id: link.server_id,
                    error: error.message
                })

    // Sort by timestamp
    all_messages.sort(key=lambda m: m.created_at)

    RETURN {
        messages: all_messages,
        errors: collection_errors,
        servers_collected: len(active_links) - len(collection_errors)
    }
```

### 2.3 Cross-Server Summarization

```pseudocode
FUNCTION summarize_federation(federation_id, options, requesting_user):
    // Validate permissions
    IF NOT user_has_federation_access(requesting_user, federation_id):
        RETURN Error("No cross-server permission")

    // Collect messages
    collection = collect_federation_messages(
        federation_id,
        options.time_range,
        options
    )

    IF collection.messages.length == 0:
        RETURN Error("No messages found in time range")

    // Build cross-server aware prompt
    prompt = build_cross_server_prompt(
        messages: collection.messages,
        options: options,
        federation: GET Federation WHERE id = federation_id
    )

    // Generate summary
    summary = call_claude_api(prompt)

    // Parse with server attribution
    parsed = parse_cross_server_response(summary)

    // Store summary with federation context
    result = CrossServerSummary(
        federation_id: federation_id,
        servers_included: collection.servers_collected,
        message_count: collection.messages.length,
        summary: parsed.summary,
        key_points_by_server: parsed.key_points_by_server,
        action_items: parsed.action_items,
        collection_errors: collection.errors
    )

    SAVE result
    RETURN result
```

### 2.4 Cross-Server Prompt Building

```pseudocode
FUNCTION build_cross_server_prompt(messages, options, federation):
    // Group messages by server for context
    messages_by_server = group_by(messages, "server_name")

    system_prompt = """
    You are summarizing a conversation spanning multiple Discord servers
    in the "{federation.name}" federation.

    CRITICAL: Maintain server context throughout your summary.

    Servers included:
    {for server in messages_by_server.keys():
        - {server}: {len(messages_by_server[server])} messages
    }

    FORMAT REQUIREMENTS:
    1. Start with a unified executive summary
    2. Provide per-server highlights section
    3. Cross-server themes and connections
    4. Action items tagged with [ServerName]
    5. Key participants with their home server

    Summary length: {options.length}
    Perspective: {options.perspective}
    """

    // Build message content with server tags
    user_content = ""
    FOR server_name, server_messages IN messages_by_server:
        user_content += f"\n\n## Messages from {server_name}\n\n"
        FOR msg IN server_messages:
            user_content += format_message(msg)

    RETURN {
        system: system_prompt,
        user: user_content,
        max_tokens: get_token_limit(options.length)
    }
```

---

## 3. ARCHITECTURE

### 3.1 System Components

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Cross-Server Layer                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │  Federation  │  │   Consent    │  │  Permission  │               │
│  │   Manager    │──│   Handler    │──│   Validator  │               │
│  └──────────────┘  └──────────────┘  └──────────────┘               │
│         │                                    │                       │
│         ▼                                    ▼                       │
│  ┌──────────────┐                   ┌──────────────┐                │
│  │  Federation  │                   │   Federated  │                │
│  │   Registry   │                   │  Permission  │                │
│  │  (Database)  │                   │    Cache     │                │
│  └──────────────┘                   └──────────────┘                │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Existing Summarization Layer                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │   Message    │  │   Prompt     │  │    Claude    │               │
│  │   Fetcher    │◄─│   Builder    │──│    Client    │               │
│  │  (Extended)  │  │  (Extended)  │  │              │               │
│  └──────────────┘  └──────────────┘  └──────────────┘               │
│         │                                    │                       │
│         ▼                                    ▼                       │
│  ┌──────────────┐                   ┌──────────────┐                │
│  │   Response   │                   │   Summary    │                │
│  │    Parser    │                   │    Cache     │                │
│  │  (Extended)  │                   │  (Extended)  │                │
│  └──────────────┘                   └──────────────┘                │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 New Database Schema

```sql
-- Federation: A named group of servers
CREATE TABLE federations (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    owner_id TEXT NOT NULL,           -- Discord user ID
    status TEXT NOT NULL DEFAULT 'pending_consent',
        -- pending_consent, active, suspended, archived
    max_servers INTEGER DEFAULT 10,
    max_channels_per_summary INTEGER DEFAULT 50,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    settings JSON                      -- Federation-specific options
);

CREATE INDEX idx_federations_owner ON federations(owner_id);
CREATE INDEX idx_federations_status ON federations(status);

-- Federation-Server Links: Consent tracking
CREATE TABLE federation_servers (
    id TEXT PRIMARY KEY,
    federation_id TEXT NOT NULL REFERENCES federations(id) ON DELETE CASCADE,
    server_id TEXT NOT NULL,           -- Discord guild ID
    consent_status TEXT NOT NULL DEFAULT 'pending',
        -- pending, approved, denied, revoked
    consented_by TEXT,                 -- Admin who approved
    consented_at TIMESTAMP,
    revoked_by TEXT,
    revoked_at TIMESTAMP,
    included_channels JSON,            -- Specific channels (null = all)
    excluded_channels JSON,            -- Channels to exclude
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(federation_id, server_id)
);

CREATE INDEX idx_fed_servers_federation ON federation_servers(federation_id);
CREATE INDEX idx_fed_servers_server ON federation_servers(server_id);
CREATE INDEX idx_fed_servers_status ON federation_servers(consent_status);

-- Federation Roles: Who can use the federation
CREATE TABLE federation_roles (
    id TEXT PRIMARY KEY,
    federation_id TEXT NOT NULL REFERENCES federations(id) ON DELETE CASCADE,
    role_type TEXT NOT NULL,           -- owner, admin, member
    user_id TEXT,                      -- Specific user
    role_id TEXT,                      -- Or role in any member server
    granted_by TEXT NOT NULL,
    granted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(federation_id, user_id),
    UNIQUE(federation_id, role_id)
);

CREATE INDEX idx_fed_roles_federation ON federation_roles(federation_id);
CREATE INDEX idx_fed_roles_user ON federation_roles(user_id);

-- Cross-Server Summaries: Track federated summary results
CREATE TABLE cross_server_summaries (
    id TEXT PRIMARY KEY,
    federation_id TEXT NOT NULL REFERENCES federations(id),
    requesting_user_id TEXT NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    servers_included JSON NOT NULL,    -- [{id, name, channel_count, message_count}]
    total_messages INTEGER NOT NULL,
    summary_text TEXT NOT NULL,
    key_points_by_server JSON,         -- {server_name: [points]}
    unified_key_points JSON,           -- Cross-cutting themes
    action_items JSON,                 -- [{text, server, assignee, priority}]
    technical_terms JSON,
    participants JSON,                 -- [{name, server, message_count}]
    collection_errors JSON,            -- Any servers that failed
    metadata JSON,                     -- Model, tokens, timing
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_css_federation ON cross_server_summaries(federation_id);
CREATE INDEX idx_css_created ON cross_server_summaries(created_at);

-- Scheduled Federation Tasks: Cross-server automation
CREATE TABLE federation_scheduled_tasks (
    id TEXT PRIMARY KEY,
    federation_id TEXT NOT NULL REFERENCES federations(id),
    name TEXT NOT NULL,
    schedule_type TEXT NOT NULL,       -- daily, weekly, monthly, custom
    schedule_time TEXT,                -- HH:MM UTC
    schedule_days JSON,                -- [0-6] for weekly
    cron_expression TEXT,              -- For custom
    summary_options JSON NOT NULL,     -- Length, perspective, etc.
    destinations JSON NOT NULL,        -- [{type, server_id, channel_id}]
    is_active BOOLEAN DEFAULT TRUE,
    created_by TEXT NOT NULL,
    last_run TIMESTAMP,
    next_run TIMESTAMP,
    run_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    max_failures INTEGER DEFAULT 3,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_fst_federation ON federation_scheduled_tasks(federation_id);
CREATE INDEX idx_fst_next_run ON federation_scheduled_tasks(next_run)
    WHERE is_active = TRUE;

-- Audit Log: Cross-server specific logging
CREATE TABLE federation_audit_log (
    id TEXT PRIMARY KEY,
    federation_id TEXT REFERENCES federations(id),
    event_type TEXT NOT NULL,
        -- federation_created, consent_granted, consent_revoked,
        -- summary_requested, summary_generated, task_executed,
        -- member_added, member_removed, settings_changed
    actor_id TEXT NOT NULL,            -- Who did it
    target_server_id TEXT,             -- Which server affected
    details JSON,                      -- Event-specific data
    ip_hash TEXT,                      -- For security (hashed)
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_fal_federation ON federation_audit_log(federation_id);
CREATE INDEX idx_fal_event ON federation_audit_log(event_type);
CREATE INDEX idx_fal_created ON federation_audit_log(created_at);
```

### 3.3 New Module Structure

```
/src
├── federation/                       # NEW: Cross-server module
│   ├── __init__.py
│   ├── models.py                     # Federation, FederationServer, etc.
│   ├── manager.py                    # FederationManager class
│   ├── consent.py                    # ConsentHandler for approvals
│   ├── permissions.py                # Cross-server permission validation
│   └── collector.py                  # FederatedMessageCollector
│
├── command_handlers/
│   ├── federation.py                 # NEW: /federation commands
│   └── summarize.py                  # EXTEND: federation parameter
│
├── summarization/
│   ├── prompt_builder.py             # EXTEND: cross-server prompts
│   └── response_parser.py            # EXTEND: server-attributed parsing
│
├── scheduling/
│   ├── executor.py                   # EXTEND: federation task execution
│   └── federation_tasks.py           # NEW: Federation task management
│
└── data/
    └── sqlite.py                     # EXTEND: new tables
```

### 3.4 API Contracts

#### FederationManager Interface

```python
class FederationManager:
    async def create_federation(
        self,
        owner_id: str,
        name: str,
        server_ids: list[str],
        description: str | None = None
    ) -> Federation:
        """Create a new federation and initiate consent requests."""

    async def get_federation(
        self,
        federation_id: str,
        include_servers: bool = True
    ) -> Federation | None:
        """Retrieve federation by ID."""

    async def list_user_federations(
        self,
        user_id: str,
        include_pending: bool = False
    ) -> list[Federation]:
        """List federations user has access to."""

    async def add_server(
        self,
        federation_id: str,
        server_id: str,
        added_by: str
    ) -> FederationServer:
        """Add a server to existing federation (requires consent)."""

    async def remove_server(
        self,
        federation_id: str,
        server_id: str,
        removed_by: str,
        reason: str | None = None
    ) -> bool:
        """Remove a server from federation."""

    async def update_settings(
        self,
        federation_id: str,
        settings: FederationSettings,
        updated_by: str
    ) -> Federation:
        """Update federation configuration."""

    async def transfer_ownership(
        self,
        federation_id: str,
        new_owner_id: str,
        transferred_by: str
    ) -> Federation:
        """Transfer federation ownership."""

    async def archive_federation(
        self,
        federation_id: str,
        archived_by: str
    ) -> bool:
        """Archive (soft delete) a federation."""
```

#### FederatedMessageCollector Interface

```python
class FederatedMessageCollector:
    async def collect(
        self,
        federation: Federation,
        time_range: TimeRange,
        options: CollectionOptions,
        requesting_user: discord.User
    ) -> FederatedCollection:
        """
        Collect messages from all consented federation servers.

        Returns:
            FederatedCollection with:
            - messages: List[FederatedMessage] sorted by timestamp
            - servers_collected: int
            - collection_stats: Dict[str, ServerCollectionStats]
            - errors: List[CollectionError]
        """

    async def estimate_collection(
        self,
        federation: Federation,
        time_range: TimeRange
    ) -> CollectionEstimate:
        """Estimate message count and API costs before collection."""
```

---

## 4. REFINEMENT (TDD Approach)

### 4.1 Test Strategy

```
tests/
├── unit/
│   └── federation/
│       ├── test_models.py            # Federation model tests
│       ├── test_manager.py           # FederationManager unit tests
│       ├── test_consent.py           # Consent flow tests
│       ├── test_permissions.py       # Permission validation tests
│       └── test_collector.py         # Message collection tests
│
├── integration/
│   └── federation/
│       ├── test_federation_flow.py   # End-to-end federation lifecycle
│       ├── test_cross_server_summary.py  # Full summarization flow
│       └── test_scheduled_federation.py  # Scheduled task tests
│
└── fixtures/
    └── federation/
        ├── mock_guilds.py            # Mock Discord guilds
        ├── mock_messages.py          # Mock cross-server messages
        └── sample_federations.py     # Test federation data
```

### 4.2 Key Test Cases

```python
# tests/unit/federation/test_manager.py

class TestFederationCreation:
    """TDD: Federation creation flow."""

    async def test_create_federation_requires_admin_in_all_servers(self):
        """Owner must be admin in every server."""
        # RED: Write failing test first
        manager = FederationManager(db, bot)

        with pytest.raises(PermissionError) as exc:
            await manager.create_federation(
                owner_id="user123",
                name="Test Fed",
                server_ids=["server1", "server2"]  # user not admin in server2
            )

        assert "must be admin" in str(exc.value)

    async def test_create_federation_requires_bot_in_all_servers(self):
        """Bot must be member of all target servers."""
        manager = FederationManager(db, bot)

        with pytest.raises(BotNotInServerError):
            await manager.create_federation(
                owner_id="admin123",
                name="Test Fed",
                server_ids=["server1", "missing_server"]
            )

    async def test_federation_starts_in_pending_state(self):
        """New federations require consent from all servers."""
        manager = FederationManager(db, bot)

        federation = await manager.create_federation(
            owner_id="admin123",
            name="Test Fed",
            server_ids=["server1", "server2"]
        )

        assert federation.status == "pending_consent"
        assert len(federation.servers) == 2
        assert all(s.consent_status == "pending" for s in federation.servers)

    async def test_federation_activates_after_all_consent(self):
        """Federation becomes active when all servers consent."""
        manager = FederationManager(db, bot)
        federation = await create_test_federation(manager)

        # Consent from both servers
        await manager.handle_consent("server1", "admin1", approved=True)
        await manager.handle_consent("server2", "admin2", approved=True)

        updated = await manager.get_federation(federation.id)
        assert updated.status == "active"


class TestCrossServerCollection:
    """TDD: Cross-server message collection."""

    async def test_collects_from_all_consented_servers(self):
        """Messages collected from all active federation servers."""
        collector = FederatedMessageCollector(bot)
        federation = await create_active_federation()

        result = await collector.collect(
            federation=federation,
            time_range=TimeRange(hours=24),
            options=CollectionOptions(),
            requesting_user=mock_user
        )

        # Should have messages from both servers
        server_ids = {m.server_id for m in result.messages}
        assert "server1" in server_ids
        assert "server2" in server_ids

    async def test_excludes_servers_without_consent(self):
        """Servers with revoked consent are excluded."""
        collector = FederatedMessageCollector(bot)
        federation = await create_partial_federation()  # server2 revoked

        result = await collector.collect(
            federation=federation,
            time_range=TimeRange(hours=24),
            options=CollectionOptions(),
            requesting_user=mock_user
        )

        server_ids = {m.server_id for m in result.messages}
        assert "server1" in server_ids
        assert "server2" not in server_ids

    async def test_messages_tagged_with_server_context(self):
        """Each message includes server attribution."""
        collector = FederatedMessageCollector(bot)
        federation = await create_active_federation()

        result = await collector.collect(...)

        for message in result.messages:
            assert message.server_id is not None
            assert message.server_name is not None

    async def test_handles_server_unavailable_gracefully(self):
        """Collection continues even if one server fails."""
        collector = FederatedMessageCollector(bot)
        federation = await create_active_federation()

        # Simulate server1 being unavailable
        with mock_server_unavailable("server1"):
            result = await collector.collect(...)

        assert len(result.errors) == 1
        assert result.errors[0].server_id == "server1"
        assert len(result.messages) > 0  # server2 messages collected


class TestCrossServerSummarization:
    """TDD: Cross-server summary generation."""

    async def test_summary_includes_server_attribution(self):
        """Summary clearly attributes content to source servers."""
        engine = SummarizationEngine(claude_client, prompt_builder)
        messages = create_multi_server_messages()

        result = await engine.summarize_federated(
            messages=messages,
            options=SummaryOptions(length="detailed")
        )

        # Should have per-server sections
        assert result.key_points_by_server is not None
        assert "Engineering Server" in result.key_points_by_server
        assert "Support Server" in result.key_points_by_server

    async def test_action_items_tagged_with_server(self):
        """Action items indicate which server they came from."""
        engine = SummarizationEngine(claude_client, prompt_builder)
        messages = create_multi_server_messages()

        result = await engine.summarize_federated(messages, options)

        for item in result.action_items:
            assert item.source_server is not None
```

### 4.3 Implementation Order (TDD Red-Green-Refactor)

| Phase | Component | Tests First | Then Implement |
|-------|-----------|-------------|----------------|
| 1 | Models | `test_models.py` | `federation/models.py` |
| 2 | Database | `test_sqlite.py` (extended) | Schema migrations |
| 3 | Manager | `test_manager.py` | `federation/manager.py` |
| 4 | Consent | `test_consent.py` | `federation/consent.py` |
| 5 | Permissions | `test_permissions.py` | `federation/permissions.py` |
| 6 | Collector | `test_collector.py` | `federation/collector.py` |
| 7 | Prompt Builder | `test_prompt_builder.py` (extended) | Prompt extensions |
| 8 | Response Parser | `test_response_parser.py` (extended) | Parser extensions |
| 9 | Commands | `test_federation_commands.py` | Command handlers |
| 10 | Scheduling | `test_federation_tasks.py` | Task executor extensions |

---

## 5. COMPLETION

### 5.1 Command Interface

```
/federation create <name> <servers...>
    Create a new federation with specified servers
    Options:
      --description: Federation description
      --max-channels: Max channels per summary (default: 50)

/federation list
    List your federations and their status

/federation info <name>
    Show federation details, member servers, consent status

/federation add-server <federation> <server>
    Add a server to an existing federation

/federation remove-server <federation> <server>
    Remove a server from federation

/federation consent <federation> [approve|deny]
    Respond to a federation consent request (server admins only)

/federation delete <name>
    Archive/delete a federation you own

/summarize federation:<name> [options...]
    Generate cross-server summary
    Options:
      --hours: Time range (default: 24)
      --length: brief|detailed|comprehensive
      --perspective: developer|marketing|product|...
      --exclude-server: Exclude specific server(s)

/schedule create federation:<name> [schedule options...]
    Create scheduled cross-server summary
```

### 5.2 Integration Points

1. **Existing Commands**: Extend `/summarize` to accept `federation:` parameter
2. **Existing Scheduler**: Extend `TaskExecutor` for federation tasks
3. **Existing Cache**: Extend cache key to include federation context
4. **Existing Audit Log**: New event types for federation operations
5. **Existing Permissions**: New `FederatedPermissionValidator` class

### 5.3 Migration Strategy

1. **Database Migration**: Add new tables via Alembic/manual SQL
2. **Feature Flag**: `ENABLE_CROSS_SERVER=true` environment variable
3. **Gradual Rollout**: Enable for specific guilds first
4. **Monitoring**: Track federation usage, error rates, token costs

### 5.4 Security Considerations

| Risk | Mitigation |
|------|------------|
| Unauthorized cross-server access | Explicit consent per server, audit logging |
| Data leakage between servers | Permission checks at collection time |
| Abuse by malicious federation owners | Rate limiting, max server/channel limits |
| Consent spoofing | Server admin role verification |
| Stale consent | Periodic consent revalidation option |

### 5.5 Performance Considerations

| Concern | Solution |
|---------|----------|
| API rate limits | Semaphore-based concurrency (max 3 servers) |
| Token costs | Estimate before collection, warn if high |
| Collection time | Parallel fetching with timeout per server |
| Cache invalidation | Federation-aware cache keys |
| Database growth | Configurable retention for audit logs |

### 5.6 Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Federation creation success | >95% | consent completion rate |
| Cross-server summary latency | <60s | p95 response time |
| Token efficiency | <20% overhead | vs. separate summaries |
| User satisfaction | >4/5 | post-summary feedback |
| Error rate | <2% | failed collections |

---

## 6. OPEN QUESTIONS

1. **Consent Expiration**: Should federation consent expire and require renewal?
2. **Channel Selection**: Allow per-server channel inclusion/exclusion in UI?
3. **Summary Destinations**: Support posting to channels in different servers?
4. **Federation Limits**: What are reasonable limits (servers, channels, messages)?
5. **Cost Allocation**: How to attribute API costs across federation members?

---

## Appendix A: Example Cross-Server Summary Output

```markdown
# Cross-Server Summary: Product Team Federation
**Period**: Last 24 hours | **Servers**: 3 | **Messages**: 847

## Executive Summary
Product launch preparations are progressing across all teams. Engineering
resolved the critical auth bug, Support is preparing FAQ documentation,
and Marketing finalized the launch announcement copy.

## Per-Server Highlights

### 🔧 Engineering Server (412 messages)
- Fixed OAuth token refresh bug (PR #1234 merged)
- Database migration completed for v2.0 schema
- Load testing showed 15% improvement after caching

### 📞 Support Server (289 messages)
- Created 12 new FAQ entries for launch features
- Escalation path documented for premium tier issues
- Training scheduled for Monday 9 AM UTC

### 📢 Marketing Server (146 messages)
- Launch blog post finalized and approved
- Social media queue loaded for launch day
- Press kit sent to 47 outlets

## Cross-Server Themes
1. **Launch Readiness**: All teams aligned on Thursday launch date
2. **Documentation**: Parallel efforts in Support and Marketing on user guides
3. **Monitoring**: Engineering and Support coordinating on launch day coverage

## Action Items
| Action | Server | Assignee | Priority |
|--------|--------|----------|----------|
| Deploy v2.0 to production | Engineering | @devops | 🔴 High |
| Final FAQ review | Support | @lead-support | 🟡 Medium |
| Schedule launch tweet | Marketing | @social | 🟡 Medium |
```

---

*Document Version: 1.0*
*Created: SPARC Specification Phase*
*Status: Ready for Architecture Review*
