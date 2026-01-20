# SummaryBot NG Dashboard Specification

## Design Principles

1. **Bot as Source of Truth**: The Discord bot owns all data. No external database.
2. **Thin Frontend**: UI is a pure rendering layer with no business logic.
3. **No Cloud Lock-in**: Deployable anywhere (VPS, Docker, self-hosted).
4. **Discord OAuth**: Users authenticate via Discord, permissions verified against actual servers.
5. **API-First**: All functionality exposed via REST API that the frontend consumes.

---

## 1. Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              User Browser                                │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    Thin React Frontend                             │  │
│  │  - Renders API responses                                          │  │
│  │  - Stores JWT in memory/localStorage                              │  │
│  │  - Zero business logic                                            │  │
│  └──────────────────────────────┬────────────────────────────────────┘  │
└─────────────────────────────────┼───────────────────────────────────────┘
                                  │ HTTPS
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         SummaryBot Backend                               │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │                        API Layer (FastAPI)                          ││
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              ││
│  │  │   Auth       │  │   Guilds     │  │   Summaries  │              ││
│  │  │   /auth/*    │  │   /guilds/*  │  │   /summaries ││              ││
│  │  └──────────────┘  └──────────────┘  └──────────────┘              ││
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              ││
│  │  │   Schedules  │  │   Webhooks   │  │   Prompts    │              ││
│  │  │   /tasks/*   │  │   /webhooks/*│  │   /prompts/* │              ││
│  │  └──────────────┘  └──────────────┘  └──────────────┘              ││
│  └─────────────────────────────┬───────────────────────────────────────┘│
│                                │                                         │
│  ┌─────────────────────────────┴───────────────────────────────────────┐│
│  │                      Core Bot Services                               ││
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              ││
│  │  │  Discord.py  │  │  Scheduler   │  │  Summarizer  │              ││
│  │  │  Gateway     │  │  (APScheduler)│  │  (Claude)    │              ││
│  │  └──────────────┘  └──────────────┘  └──────────────┘              ││
│  └─────────────────────────────┬───────────────────────────────────────┘│
│                                │                                         │
│  ┌─────────────────────────────┴───────────────────────────────────────┐│
│  │                         Data Layer                                   ││
│  │  ┌──────────────────────────────────────────────────────────────┐   ││
│  │  │                    SQLite (Primary)                           │   ││
│  │  │  summaries | guild_configs | scheduled_tasks | task_results  │   ││
│  │  │  users | sessions | command_logs                              │   ││
│  │  └──────────────────────────────────────────────────────────────┘   ││
│  └─────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           Discord API                                    │
│  - Gateway (bot events)                                                  │
│  - OAuth2 (user authentication)                                          │
│  - REST (guild/channel info)                                             │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Authentication

### 2.1 Discord OAuth2 Flow

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  Browser │     │ Frontend │     │ Backend  │     │ Discord  │
└────┬─────┘     └────┬─────┘     └────┬─────┘     └────┬─────┘
     │                │                │                │
     │─── Click ─────►│                │                │
     │   "Login"      │                │                │
     │                │─── GET ───────►│                │
     │                │  /auth/login   │                │
     │                │◄── Redirect ───│                │
     │                │    URL         │                │
     │◄─── Redirect ──────────────────────────────────►│
     │    to Discord                   │                │
     │                │                │                │
     │    [User authorizes app]        │                │
     │                │                │                │
     │◄─── Redirect ──────────────────────────────────│
     │    with code   │                │                │
     │                │                │                │
     │─── GET ───────►│                │                │
     │  /callback     │─── POST ──────►│                │
     │  ?code=xxx     │  /auth/callback│                │
     │                │  {code}        │─── Exchange ──►│
     │                │                │    code        │
     │                │                │◄── Tokens ─────│
     │                │                │                │
     │                │                │─── GET ───────►│
     │                │                │  /users/@me    │
     │                │                │◄── User ───────│
     │                │                │                │
     │                │                │─── GET ───────►│
     │                │                │  /users/@me/   │
     │                │                │   guilds       │
     │                │                │◄── Guilds ─────│
     │                │                │                │
     │                │◄── JWT Token ──│                │
     │◄─── Store ─────│                │                │
     │    JWT         │                │                │
```

### 2.2 OAuth Scopes Required

```
identify        - Get user ID, username, avatar
guilds          - List user's guilds
guilds.members.read - Get user's roles in guilds (for permission check)
```

### 2.3 Permission Verification

The backend verifies the user has appropriate permissions in each guild:

```python
async def get_user_manageable_guilds(discord_token: str) -> list[Guild]:
    """Get guilds where user can manage the bot."""
    user_guilds = await discord_api.get_user_guilds(discord_token)
    bot_guilds = {g.id for g in bot.guilds}  # Guilds bot is in

    manageable = []
    for guild in user_guilds:
        # User must have MANAGE_GUILD or ADMINISTRATOR permission
        permissions = guild.permissions
        can_manage = (
            permissions & ADMINISTRATOR or
            permissions & MANAGE_GUILD
        )

        # Bot must also be in the guild
        if can_manage and guild.id in bot_guilds:
            manageable.append(guild)

    return manageable
```

### 2.4 JWT Token Structure

```json
{
  "sub": "discord_user_id",
  "username": "user#1234",
  "avatar": "avatar_hash",
  "guilds": ["guild_id_1", "guild_id_2"],
  "iat": 1234567890,
  "exp": 1234571490
}
```

### 2.5 Session Storage

```sql
CREATE TABLE dashboard_sessions (
    id TEXT PRIMARY KEY,
    discord_user_id TEXT NOT NULL,
    discord_username TEXT NOT NULL,
    discord_avatar TEXT,
    discord_access_token TEXT NOT NULL,  -- Encrypted
    discord_refresh_token TEXT NOT NULL, -- Encrypted
    token_expires_at TIMESTAMP NOT NULL,
    manageable_guild_ids JSON NOT NULL,  -- Cached guild list
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);

CREATE INDEX idx_sessions_user ON dashboard_sessions(discord_user_id);
CREATE INDEX idx_sessions_expires ON dashboard_sessions(expires_at);
```

---

## 3. API Specification

### 3.1 Base Configuration

```
Base URL: /api/v1
Content-Type: application/json
Authentication: Bearer <jwt_token>
```

### 3.2 Authentication Endpoints

#### `GET /auth/login`
Initiate Discord OAuth flow.

**Response:**
```json
{
  "redirect_url": "https://discord.com/oauth2/authorize?client_id=...&scope=..."
}
```

#### `POST /auth/callback`
Exchange OAuth code for session.

**Request:**
```json
{
  "code": "oauth_code_from_discord"
}
```

**Response:**
```json
{
  "token": "jwt_token",
  "user": {
    "id": "123456789",
    "username": "User#1234",
    "avatar_url": "https://cdn.discordapp.com/..."
  },
  "guilds": [
    {
      "id": "987654321",
      "name": "My Server",
      "icon_url": "https://cdn.discordapp.com/...",
      "role": "owner"
    }
  ]
}
```

#### `POST /auth/refresh`
Refresh JWT token.

**Response:**
```json
{
  "token": "new_jwt_token"
}
```

#### `POST /auth/logout`
Invalidate session.

**Response:**
```json
{
  "success": true
}
```

### 3.3 Guild Endpoints

#### `GET /guilds`
List guilds user can manage.

**Response:**
```json
{
  "guilds": [
    {
      "id": "987654321",
      "name": "My Server",
      "icon_url": "https://cdn.discordapp.com/...",
      "member_count": 150,
      "bot_joined_at": "2024-01-15T10:30:00Z",
      "config_status": "configured",
      "summary_count": 47,
      "last_summary_at": "2024-03-10T14:00:00Z"
    }
  ]
}
```

#### `GET /guilds/{guild_id}`
Get guild details with channels.

**Response:**
```json
{
  "id": "987654321",
  "name": "My Server",
  "icon_url": "https://cdn.discordapp.com/...",
  "channels": [
    {
      "id": "111111111",
      "name": "general",
      "type": "text",
      "category": "Text Channels",
      "enabled": true
    }
  ],
  "categories": [
    {
      "id": "222222222",
      "name": "Text Channels",
      "channel_count": 5
    }
  ],
  "config": {
    "enabled_channels": ["111111111"],
    "excluded_channels": [],
    "default_options": {
      "summary_length": "detailed",
      "perspective": "general",
      "include_action_items": true
    }
  }
}
```

#### `PATCH /guilds/{guild_id}/config`
Update guild configuration.

**Request:**
```json
{
  "enabled_channels": ["111111111", "333333333"],
  "excluded_channels": ["444444444"],
  "default_options": {
    "summary_length": "brief",
    "perspective": "developer"
  }
}
```

**Response:**
```json
{
  "success": true,
  "config": { ... }
}
```

#### `POST /guilds/{guild_id}/channels/sync`
Force sync channels from Discord.

**Response:**
```json
{
  "success": true,
  "channels_added": 2,
  "channels_removed": 1,
  "channels": [...]
}
```

### 3.4 Summary Endpoints

#### `GET /guilds/{guild_id}/summaries`
List summaries for a guild.

**Query Parameters:**
- `channel_id` (optional): Filter by channel
- `start_date` (optional): Filter from date
- `end_date` (optional): Filter to date
- `limit` (default: 20, max: 100)
- `offset` (default: 0)

**Response:**
```json
{
  "summaries": [
    {
      "id": "sum_abc123",
      "channel_id": "111111111",
      "channel_name": "#general",
      "start_time": "2024-03-10T00:00:00Z",
      "end_time": "2024-03-10T23:59:59Z",
      "message_count": 247,
      "created_at": "2024-03-11T09:00:00Z",
      "summary_length": "detailed",
      "preview": "The team discussed the upcoming release..."
    }
  ],
  "total": 47,
  "limit": 20,
  "offset": 0
}
```

#### `GET /guilds/{guild_id}/summaries/{summary_id}`
Get full summary details.

**Response:**
```json
{
  "id": "sum_abc123",
  "channel_id": "111111111",
  "channel_name": "#general",
  "start_time": "2024-03-10T00:00:00Z",
  "end_time": "2024-03-10T23:59:59Z",
  "message_count": 247,
  "summary_text": "Full summary content...",
  "key_points": [
    "Discussed Q2 roadmap priorities",
    "Agreed on new testing strategy"
  ],
  "action_items": [
    {
      "text": "Update documentation",
      "assignee": "alice",
      "priority": "high",
      "deadline": null
    }
  ],
  "technical_terms": [
    {
      "term": "CI/CD",
      "definition": "Continuous Integration/Continuous Deployment"
    }
  ],
  "participants": [
    {
      "username": "alice",
      "message_count": 45,
      "top_contributor": true
    }
  ],
  "metadata": {
    "model": "claude-3-haiku",
    "tokens_used": 2847,
    "processing_time_ms": 3200
  },
  "created_at": "2024-03-11T09:00:00Z"
}
```

#### `POST /guilds/{guild_id}/summaries/generate`
Generate an on-demand summary (same as /summarize command).

**Request:**
```json
{
  "channel_ids": ["111111111"],
  "time_range": {
    "type": "hours",
    "value": 24
  },
  "options": {
    "summary_length": "detailed",
    "perspective": "developer",
    "include_action_items": true
  }
}
```

**Response:**
```json
{
  "task_id": "task_xyz789",
  "status": "processing",
  "estimated_seconds": 15
}
```

#### `GET /guilds/{guild_id}/summaries/tasks/{task_id}`
Check summary generation status.

**Response:**
```json
{
  "task_id": "task_xyz789",
  "status": "completed",
  "summary_id": "sum_abc123",
  "created_at": "2024-03-11T09:00:15Z"
}
```

### 3.5 Schedule Endpoints

#### `GET /guilds/{guild_id}/schedules`
List scheduled tasks.

**Response:**
```json
{
  "schedules": [
    {
      "id": "sched_abc123",
      "name": "Daily #general summary",
      "channel_ids": ["111111111"],
      "category_id": null,
      "schedule_type": "daily",
      "schedule_time": "09:00",
      "schedule_days": null,
      "timezone": "UTC",
      "is_active": true,
      "destinations": [
        {
          "type": "discord_channel",
          "target": "222222222",
          "format": "embed"
        }
      ],
      "summary_options": {
        "summary_length": "brief",
        "perspective": "general"
      },
      "last_run": "2024-03-10T09:00:00Z",
      "next_run": "2024-03-11T09:00:00Z",
      "run_count": 45,
      "failure_count": 0
    }
  ]
}
```

#### `POST /guilds/{guild_id}/schedules`
Create a scheduled task.

**Request:**
```json
{
  "name": "Weekly team summary",
  "channel_ids": ["111111111", "333333333"],
  "schedule_type": "weekly",
  "schedule_time": "17:00",
  "schedule_days": [4],
  "timezone": "America/New_York",
  "destinations": [
    {
      "type": "discord_channel",
      "target": "222222222",
      "format": "embed"
    }
  ],
  "summary_options": {
    "summary_length": "comprehensive",
    "perspective": "executive"
  }
}
```

**Response:**
```json
{
  "id": "sched_def456",
  "name": "Weekly team summary",
  ...
}
```

#### `PATCH /guilds/{guild_id}/schedules/{schedule_id}`
Update a scheduled task.

#### `DELETE /guilds/{guild_id}/schedules/{schedule_id}`
Delete a scheduled task.

#### `POST /guilds/{guild_id}/schedules/{schedule_id}/run`
Trigger immediate execution.

**Response:**
```json
{
  "execution_id": "exec_abc123",
  "status": "started"
}
```

#### `GET /guilds/{guild_id}/schedules/{schedule_id}/history`
Get execution history.

**Response:**
```json
{
  "executions": [
    {
      "execution_id": "exec_abc123",
      "status": "completed",
      "started_at": "2024-03-10T09:00:00Z",
      "completed_at": "2024-03-10T09:00:23Z",
      "summary_id": "sum_abc123",
      "delivery_results": [
        {
          "destination": "discord_channel:222222222",
          "success": true
        }
      ]
    }
  ]
}
```

### 3.6 Webhook Endpoints

#### `GET /guilds/{guild_id}/webhooks`
List configured webhooks.

**Response:**
```json
{
  "webhooks": [
    {
      "id": "wh_abc123",
      "name": "Slack #summaries",
      "url_preview": "https://hooks.slack.com/...xxxx",
      "type": "slack",
      "enabled": true,
      "last_delivery": "2024-03-10T09:00:00Z",
      "last_status": "success",
      "created_at": "2024-01-15T10:00:00Z"
    }
  ]
}
```

#### `POST /guilds/{guild_id}/webhooks`
Create a webhook.

**Request:**
```json
{
  "name": "Notion database",
  "url": "https://api.notion.com/v1/...",
  "type": "notion",
  "headers": {
    "Authorization": "Bearer secret_xxx"
  }
}
```

#### `POST /guilds/{guild_id}/webhooks/{webhook_id}/test`
Test webhook delivery.

**Response:**
```json
{
  "success": true,
  "response_code": 200,
  "response_time_ms": 245
}
```

### 3.7 Prompt Template Endpoints

#### `GET /guilds/{guild_id}/prompts`
List prompt templates.

**Response:**
```json
{
  "prompts": [
    {
      "id": "prompt_abc123",
      "name": "Default",
      "is_active": true,
      "source": "builtin",
      "preview": "You are a helpful assistant..."
    },
    {
      "id": "prompt_def456",
      "name": "Technical Focus",
      "is_active": false,
      "source": "custom",
      "preview": "Focus on technical details..."
    }
  ],
  "github_config": {
    "enabled": true,
    "repo_url": "https://github.com/org/prompts",
    "last_sync": "2024-03-10T08:00:00Z"
  }
}
```

#### `POST /guilds/{guild_id}/prompts`
Create custom prompt template.

**Request:**
```json
{
  "name": "Marketing Focus",
  "template": "You are summarizing for a marketing team. Focus on..."
}
```

#### `PATCH /guilds/{guild_id}/prompts/{prompt_id}/activate`
Set as active prompt.

#### `GET /guilds/{guild_id}/prompts/preview`
Preview a prompt with sample data.

**Request:**
```json
{
  "template": "Custom prompt template...",
  "sample_messages": 10
}
```

**Response:**
```json
{
  "rendered_prompt": "Full system prompt with context...",
  "estimated_tokens": 1250
}
```

### 3.8 Analytics Endpoints

#### `GET /guilds/{guild_id}/analytics`
Get usage analytics.

**Query Parameters:**
- `period`: day, week, month, year
- `start_date`, `end_date`

**Response:**
```json
{
  "period": "month",
  "summaries": {
    "total": 124,
    "by_channel": [
      {"channel_id": "111111111", "name": "#general", "count": 45},
      {"channel_id": "333333333", "name": "#dev", "count": 79}
    ],
    "by_day": [
      {"date": "2024-03-01", "count": 4},
      {"date": "2024-03-02", "count": 5}
    ]
  },
  "tokens": {
    "total": 125000,
    "by_model": {
      "claude-3-haiku": 80000,
      "claude-3-sonnet": 45000
    }
  },
  "schedules": {
    "executions": 92,
    "success_rate": 0.98
  }
}
```

---

## 4. Real-Time Updates

### 4.1 Server-Sent Events (SSE)

The API provides an SSE endpoint for real-time updates:

#### `GET /guilds/{guild_id}/events`

**Event Types:**

```
event: summary_started
data: {"task_id": "task_xyz", "channel_ids": ["111111111"]}

event: summary_completed
data: {"task_id": "task_xyz", "summary_id": "sum_abc123"}

event: schedule_executed
data: {"schedule_id": "sched_abc", "status": "completed"}

event: config_updated
data: {"updated_by": "user_id", "changes": ["enabled_channels"]}

event: channel_sync
data: {"added": 1, "removed": 0}
```

### 4.2 Frontend SSE Handling

```typescript
// Thin client SSE connection
const eventSource = new EventSource(
  `/api/v1/guilds/${guildId}/events`,
  { headers: { Authorization: `Bearer ${token}` } }
);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  // Dispatch to state management (React Query invalidation, etc.)
  queryClient.invalidateQueries(['guild', guildId]);
};
```

---

## 5. Database Schema Additions

### 5.1 New Tables for Dashboard

```sql
-- Dashboard user sessions
CREATE TABLE dashboard_sessions (
    id TEXT PRIMARY KEY,
    discord_user_id TEXT NOT NULL,
    discord_username TEXT NOT NULL,
    discord_discriminator TEXT,
    discord_avatar TEXT,
    discord_access_token_encrypted TEXT NOT NULL,
    discord_refresh_token_encrypted TEXT NOT NULL,
    discord_token_expires_at TIMESTAMP NOT NULL,
    manageable_guild_ids JSON NOT NULL,
    jwt_token_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    ip_address TEXT,
    user_agent TEXT
);

CREATE INDEX idx_dashboard_sessions_user ON dashboard_sessions(discord_user_id);
CREATE INDEX idx_dashboard_sessions_expires ON dashboard_sessions(expires_at);
CREATE INDEX idx_dashboard_sessions_jwt ON dashboard_sessions(jwt_token_hash);

-- Dashboard audit log (separate from command_logs)
CREATE TABLE dashboard_audit_log (
    id TEXT PRIMARY KEY,
    session_id TEXT REFERENCES dashboard_sessions(id),
    discord_user_id TEXT NOT NULL,
    guild_id TEXT,
    action TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT,
    changes JSON,
    ip_address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_dashboard_audit_guild ON dashboard_audit_log(guild_id);
CREATE INDEX idx_dashboard_audit_user ON dashboard_audit_log(discord_user_id);
CREATE INDEX idx_dashboard_audit_created ON dashboard_audit_log(created_at);

-- Custom prompt templates (extends existing github-based system)
CREATE TABLE custom_prompts (
    id TEXT PRIMARY KEY,
    guild_id TEXT NOT NULL,
    name TEXT NOT NULL,
    template TEXT NOT NULL,
    is_active BOOLEAN DEFAULT FALSE,
    created_by TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE INDEX idx_custom_prompts_guild ON custom_prompts(guild_id);
CREATE UNIQUE INDEX idx_custom_prompts_active ON custom_prompts(guild_id)
    WHERE is_active = TRUE;

-- Webhook configurations (extracted from guild_configs)
CREATE TABLE webhooks (
    id TEXT PRIMARY KEY,
    guild_id TEXT NOT NULL,
    name TEXT NOT NULL,
    url_encrypted TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'generic',
    headers_encrypted JSON,
    enabled BOOLEAN DEFAULT TRUE,
    last_delivery_at TIMESTAMP,
    last_delivery_status TEXT,
    last_delivery_error TEXT,
    failure_count INTEGER DEFAULT 0,
    created_by TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE INDEX idx_webhooks_guild ON webhooks(guild_id);
```

### 5.2 Encryption

Sensitive fields (tokens, webhook URLs) are encrypted at rest:

```python
from cryptography.fernet import Fernet

# Key from environment: DASHBOARD_ENCRYPTION_KEY
cipher = Fernet(os.environ['DASHBOARD_ENCRYPTION_KEY'])

def encrypt(value: str) -> str:
    return cipher.encrypt(value.encode()).decode()

def decrypt(value: str) -> str:
    return cipher.decrypt(value.encode()).decode()
```

---

## 6. Frontend Specification

### 6.1 Technology Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Framework | React 18 | Lovable default |
| State | TanStack Query | Server state, caching, invalidation |
| Routing | React Router | Standard |
| UI | shadcn/ui | Lovable default, headless |
| Forms | React Hook Form | Minimal, performant |
| Styling | Tailwind CSS | Lovable default |

### 6.2 Pages

```
/                     → Landing (if not logged in) or redirect to /guilds
/login                → Initiates Discord OAuth
/callback             → OAuth callback handler
/guilds               → Guild selector
/guilds/:id           → Guild dashboard
/guilds/:id/channels  → Channel configuration
/guilds/:id/summaries → Summary history
/guilds/:id/schedules → Schedule management
/guilds/:id/webhooks  → Webhook configuration
/guilds/:id/prompts   → Prompt templates
/guilds/:id/analytics → Usage analytics
/guilds/:id/settings  → Guild settings
```

### 6.3 Frontend Responsibilities

The frontend ONLY:

1. **Renders API responses** - No data transformation
2. **Handles user input** - Forms, clicks, navigation
3. **Manages auth state** - JWT storage, refresh
4. **Provides optimistic UI** - For better UX
5. **Caches responses** - Via TanStack Query

The frontend NEVER:

1. Validates business rules (server does this)
2. Computes derived data (server provides it)
3. Makes decisions about permissions (server enforces)
4. Stores configuration (server owns it)

### 6.4 API Client Pattern

```typescript
// api/client.ts
const apiClient = {
  async get<T>(path: string): Promise<T> {
    const res = await fetch(`/api/v1${path}`, {
      headers: { Authorization: `Bearer ${getToken()}` }
    });
    if (!res.ok) throw new ApiError(res);
    return res.json();
  },

  async post<T>(path: string, body: unknown): Promise<T> {
    const res = await fetch(`/api/v1${path}`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${getToken()}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(body)
    });
    if (!res.ok) throw new ApiError(res);
    return res.json();
  },
  // ... patch, delete
};

// hooks/useGuild.ts
export function useGuild(guildId: string) {
  return useQuery({
    queryKey: ['guild', guildId],
    queryFn: () => apiClient.get<Guild>(`/guilds/${guildId}`)
  });
}

// components/GuildDashboard.tsx
function GuildDashboard({ guildId }: Props) {
  const { data: guild, isLoading } = useGuild(guildId);

  if (isLoading) return <Skeleton />;

  // Pure rendering - no logic
  return (
    <div>
      <h1>{guild.name}</h1>
      <ChannelList channels={guild.channels} />
    </div>
  );
}
```

---

## 7. Deployment Options

### 7.1 Single Process (Simplest)

Bot and API run in same process:

```python
# main.py
import asyncio
from discord_bot import bot
from api import app  # FastAPI app

async def main():
    # Run both concurrently
    await asyncio.gather(
        bot.start(DISCORD_TOKEN),
        uvicorn.Server(config).serve()
    )

asyncio.run(main())
```

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
EXPOSE 8000
CMD ["python", "main.py"]
```

### 7.2 Separate Processes (Scalable)

```yaml
# docker-compose.yml
services:
  bot:
    build: .
    command: python -m src.bot
    environment:
      - DISCORD_TOKEN
      - DATABASE_URL=sqlite:///data/bot.db
    volumes:
      - ./data:/app/data

  api:
    build: .
    command: uvicorn src.api:app --host 0.0.0.0
    environment:
      - DATABASE_URL=sqlite:///data/bot.db
      - JWT_SECRET
    volumes:
      - ./data:/app/data
    ports:
      - "8000:8000"

  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    environment:
      - API_URL=http://api:8000
```

### 7.3 Frontend Hosting Options

| Option | Pros | Cons |
|--------|------|------|
| Same server (nginx) | Simple, single deployment | Couples frontend/backend |
| Vercel/Netlify | Free, CDN, easy | External dependency |
| Cloudflare Pages | Free, fast | External dependency |
| Static in API | Simplest | No CDN |

Recommended: Serve static frontend from FastAPI in development, CDN in production.

```python
# api/main.py
from fastapi.staticfiles import StaticFiles

app.mount("/", StaticFiles(directory="frontend/dist", html=True))
```

---

## 8. Security Considerations

| Concern | Mitigation |
|---------|------------|
| Token theft | Short JWT expiry (1h), secure cookies |
| CSRF | SameSite cookies, CSRF tokens |
| XSS | CSP headers, no dangerouslySetInnerHTML |
| Injection | Parameterized queries (already in place) |
| Webhook secrets | Encrypted at rest, never logged |
| Rate limiting | Per-user, per-endpoint limits |
| Session hijacking | Bind session to IP/UA, rotate tokens |

---

## 9. Environment Variables

```env
# Discord OAuth
DISCORD_CLIENT_ID=your_app_client_id
DISCORD_CLIENT_SECRET=your_app_client_secret
DISCORD_REDIRECT_URI=https://yourdomain.com/api/v1/auth/callback

# Security
JWT_SECRET=random_32_byte_hex
DASHBOARD_ENCRYPTION_KEY=fernet_key_here

# Existing bot config
DISCORD_TOKEN=bot_token
OPENROUTER_API_KEY=api_key

# API config
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=https://yourdomain.com
```

---

## 10. Implementation Phases

### Phase 1: Core API (Week 1-2)
- [ ] FastAPI setup with existing bot
- [ ] Discord OAuth endpoints
- [ ] JWT authentication middleware
- [ ] Guild list and details endpoints
- [ ] Basic session management

### Phase 2: Configuration (Week 2-3)
- [ ] Channel enable/disable endpoints
- [ ] Schedule CRUD endpoints
- [ ] Webhook CRUD endpoints
- [ ] Config update endpoints

### Phase 3: Summaries (Week 3-4)
- [ ] Summary list and detail endpoints
- [ ] On-demand summary generation
- [ ] Task status polling
- [ ] SSE for real-time updates

### Phase 4: Frontend (Week 4-6)
- [ ] Auth flow (login, callback, logout)
- [ ] Guild selector
- [ ] Channel configuration UI
- [ ] Schedule management UI
- [ ] Summary viewer

### Phase 5: Polish (Week 6-7)
- [ ] Analytics endpoints
- [ ] Prompt template management
- [ ] Error handling improvements
- [ ] Rate limiting
- [ ] Audit logging

---

## Appendix A: Error Response Format

```json
{
  "error": {
    "code": "FORBIDDEN",
    "message": "You don't have permission to manage this guild",
    "details": {
      "guild_id": "987654321",
      "required_permission": "MANAGE_GUILD"
    }
  }
}
```

### Error Codes

| Code | HTTP | Description |
|------|------|-------------|
| `UNAUTHORIZED` | 401 | Missing or invalid token |
| `FORBIDDEN` | 403 | Valid token but no permission |
| `NOT_FOUND` | 404 | Resource doesn't exist |
| `VALIDATION_ERROR` | 422 | Invalid request body |
| `RATE_LIMITED` | 429 | Too many requests |
| `DISCORD_ERROR` | 502 | Discord API error |
| `INTERNAL_ERROR` | 500 | Unexpected server error |

---

## Appendix B: OpenAPI Schema

The full OpenAPI 3.0 schema will be auto-generated by FastAPI and available at `/api/v1/openapi.json`.

This enables:
- Auto-generated TypeScript types for frontend
- API documentation at `/api/v1/docs`
- Client SDK generation

---

*Document Version: 1.0*
*Architecture: Bot-Centric with Thin Frontend*
*Status: Ready for Implementation*
