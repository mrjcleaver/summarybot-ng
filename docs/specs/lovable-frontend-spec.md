# SummaryBot Dashboard - Frontend Specification for Lovable

## Overview

Build a React dashboard for configuring a Discord summarization bot. The frontend is a **thin client** that calls a REST API - all business logic lives on the backend.

**Tech Stack**: React 18, TanStack Query, React Router, shadcn/ui, Tailwind CSS

---

## Authentication

Users authenticate via Discord OAuth. The backend handles the OAuth flow.

### Login Flow

1. User clicks "Login with Discord"
2. Frontend redirects to `GET /api/v1/auth/login`
3. Backend returns Discord OAuth URL
4. User authorizes on Discord
5. Discord redirects to `/callback?code=xxx`
6. Frontend sends code to `POST /api/v1/auth/callback`
7. Backend returns JWT token + user info
8. Frontend stores JWT in localStorage

### Auth State

```typescript
interface AuthState {
  token: string | null;
  user: {
    id: string;
    username: string;
    avatar_url: string;
  } | null;
  guilds: Guild[];
}
```

### Protected Routes

All routes except `/` and `/callback` require authentication. Redirect to `/` if no token.

---

## API Client

Create a simple API client that:
- Adds `Authorization: Bearer {token}` header to all requests
- Handles 401 responses by clearing auth state and redirecting to `/`
- Base URL: `/api/v1`

```typescript
// Example pattern
const api = {
  get: <T>(path: string) => fetch(`/api/v1${path}`, { headers }).then(r => r.json()) as Promise<T>,
  post: <T>(path: string, body: unknown) => fetch(...).then(r => r.json()) as Promise<T>,
  patch: <T>(path: string, body: unknown) => fetch(...).then(r => r.json()) as Promise<T>,
  delete: (path: string) => fetch(...),
};
```

---

## Pages & Routes

```
/                     → Landing page (unauthenticated) or redirect to /guilds
/callback             → OAuth callback handler (processes ?code= param)
/guilds               → Guild selector grid
/guilds/:id           → Guild dashboard (overview)
/guilds/:id/channels  → Channel configuration
/guilds/:id/summaries → Summary history list + detail view
/guilds/:id/schedules → Scheduled task management
/guilds/:id/webhooks  → Webhook configuration
/guilds/:id/settings  → Guild settings
```

---

## Page Specifications

### 1. Landing Page (`/`)

**If not authenticated:**
- Hero section with bot description
- "Login with Discord" button (purple, Discord branded)
- Feature highlights (3-4 cards)

**If authenticated:**
- Redirect to `/guilds`

---

### 2. OAuth Callback (`/callback`)

- Extract `code` from URL query params
- Show loading spinner
- Call `POST /api/v1/auth/callback` with `{ code }`
- On success: store token, redirect to `/guilds`
- On error: show error message, link to retry

---

### 3. Guild Selector (`/guilds`)

**Layout:** Header with user avatar + logout, grid of guild cards

**API Call:** `GET /api/v1/guilds`

**Response:**
```typescript
interface GuildsResponse {
  guilds: Array<{
    id: string;
    name: string;
    icon_url: string | null;
    member_count: number;
    summary_count: number;
    last_summary_at: string | null;
    config_status: "configured" | "needs_setup" | "inactive";
  }>;
}
```

**UI:**
- Grid of cards (3 columns on desktop, 1 on mobile)
- Each card shows: icon, name, member count, summary count
- Badge for config status
- Click navigates to `/guilds/:id`

---

### 4. Guild Dashboard (`/guilds/:id`)

**Layout:** Sidebar navigation + main content area

**Sidebar Links:**
- Overview (current)
- Channels
- Summaries
- Schedules
- Webhooks
- Settings

**API Call:** `GET /api/v1/guilds/:id`

**Response:**
```typescript
interface GuildDetail {
  id: string;
  name: string;
  icon_url: string | null;
  member_count: number;
  channels: Channel[];
  categories: Category[];
  config: GuildConfig;
  stats: {
    total_summaries: number;
    summaries_this_week: number;
    active_schedules: number;
    last_summary_at: string | null;
  };
}

interface Channel {
  id: string;
  name: string;
  type: "text" | "voice" | "forum";
  category: string | null;
  enabled: boolean;
}

interface Category {
  id: string;
  name: string;
  channel_count: number;
}

interface GuildConfig {
  enabled_channels: string[];
  excluded_channels: string[];
  default_options: SummaryOptions;
}

interface SummaryOptions {
  summary_length: "brief" | "detailed" | "comprehensive";
  perspective: "general" | "developer" | "marketing" | "executive" | "support";
  include_action_items: boolean;
  include_technical_terms: boolean;
}
```

**Overview Content:**
- Stats cards row (total summaries, this week, active schedules)
- Recent summaries list (last 5)
- Quick actions (Generate Summary button, View Schedules)

---

### 5. Channel Configuration (`/guilds/:id/channels`)

**Purpose:** Toggle which channels are included in summaries

**API Calls:**
- Read: `GET /api/v1/guilds/:id` (uses channels from guild detail)
- Update: `PATCH /api/v1/guilds/:id/config`

**Update Request:**
```typescript
interface ConfigUpdate {
  enabled_channels?: string[];
  excluded_channels?: string[];
}
```

**UI:**
- Group channels by category (collapsible sections)
- Each channel row: icon, #name, toggle switch
- "Enable All" / "Disable All" buttons per category
- Save button (or auto-save with debounce)
- "Sync Channels" button calls `POST /api/v1/guilds/:id/channels/sync`

---

### 6. Summary History (`/guilds/:id/summaries`)

**API Call:** `GET /api/v1/guilds/:id/summaries?limit=20&offset=0`

**Query Params:**
- `channel_id` (optional): filter by channel
- `start_date`, `end_date` (optional): date range
- `limit`, `offset`: pagination

**Response:**
```typescript
interface SummariesResponse {
  summaries: Array<{
    id: string;
    channel_id: string;
    channel_name: string;
    start_time: string;
    end_time: string;
    message_count: number;
    created_at: string;
    summary_length: string;
    preview: string; // First 200 chars
  }>;
  total: number;
  limit: number;
  offset: number;
}
```

**UI:**
- Filter bar: channel dropdown, date range picker
- List view with cards/rows
- Each item: channel name, date range, message count, preview
- Click opens detail modal or side panel

**Summary Detail** (`GET /api/v1/guilds/:id/summaries/:summaryId`):

```typescript
interface SummaryDetail {
  id: string;
  channel_id: string;
  channel_name: string;
  start_time: string;
  end_time: string;
  message_count: number;
  summary_text: string;
  key_points: string[];
  action_items: Array<{
    text: string;
    assignee: string | null;
    priority: "low" | "medium" | "high";
  }>;
  technical_terms: Array<{
    term: string;
    definition: string;
  }>;
  participants: Array<{
    username: string;
    message_count: number;
  }>;
  metadata: {
    model: string;
    tokens_used: number;
    processing_time_ms: number;
  };
  created_at: string;
}
```

**Detail UI:**
- Full summary text (markdown rendered)
- Collapsible sections: Key Points, Action Items, Technical Terms, Participants
- Metadata footer (model, tokens, time)

**Generate Summary Button:**
Opens modal with:
- Channel multi-select
- Time range (dropdown: 1h, 6h, 12h, 24h, 48h, 7d, custom)
- Options (length, perspective)
- Generate button

Calls `POST /api/v1/guilds/:id/summaries/generate`:
```typescript
interface GenerateRequest {
  channel_ids: string[];
  time_range: {
    type: "hours" | "days" | "custom";
    value?: number;
    start?: string;
    end?: string;
  };
  options: SummaryOptions;
}

interface GenerateResponse {
  task_id: string;
  status: "processing";
}
```

Poll `GET /api/v1/guilds/:id/summaries/tasks/:taskId` until complete:
```typescript
interface TaskStatus {
  task_id: string;
  status: "processing" | "completed" | "failed";
  summary_id?: string;
  error?: string;
}
```

---

### 7. Schedule Management (`/guilds/:id/schedules`)

**API Calls:**
- List: `GET /api/v1/guilds/:id/schedules`
- Create: `POST /api/v1/guilds/:id/schedules`
- Update: `PATCH /api/v1/guilds/:id/schedules/:scheduleId`
- Delete: `DELETE /api/v1/guilds/:id/schedules/:scheduleId`
- Run Now: `POST /api/v1/guilds/:id/schedules/:scheduleId/run`

**List Response:**
```typescript
interface SchedulesResponse {
  schedules: Array<{
    id: string;
    name: string;
    channel_ids: string[];
    schedule_type: "daily" | "weekly" | "monthly" | "once";
    schedule_time: string; // "HH:MM"
    schedule_days: number[] | null; // 0-6 for weekly
    timezone: string;
    is_active: boolean;
    destinations: Destination[];
    summary_options: SummaryOptions;
    last_run: string | null;
    next_run: string | null;
    run_count: number;
    failure_count: number;
  }>;
}

interface Destination {
  type: "discord_channel" | "webhook";
  target: string; // channel ID or webhook ID
  format: "embed" | "markdown" | "json";
}
```

**UI:**
- List/table of schedules with columns: name, channels, frequency, next run, status
- Toggle for is_active
- Actions: Edit, Delete, Run Now
- "Create Schedule" button opens form

**Schedule Form (Create/Edit):**
- Name (text input)
- Channels (multi-select from guild channels)
- Schedule type (radio: Daily, Weekly, Monthly, Once)
- Time (time picker)
- Days (checkbox group, shown for Weekly)
- Timezone (dropdown with common timezones)
- Destination (select channel or webhook)
- Summary options (length, perspective dropdowns)

**Create/Update Request:**
```typescript
interface ScheduleRequest {
  name: string;
  channel_ids: string[];
  schedule_type: "daily" | "weekly" | "monthly" | "once";
  schedule_time: string;
  schedule_days?: number[];
  timezone: string;
  destinations: Destination[];
  summary_options: SummaryOptions;
}
```

---

### 8. Webhook Configuration (`/guilds/:id/webhooks`)

**API Calls:**
- List: `GET /api/v1/guilds/:id/webhooks`
- Create: `POST /api/v1/guilds/:id/webhooks`
- Update: `PATCH /api/v1/guilds/:id/webhooks/:webhookId`
- Delete: `DELETE /api/v1/guilds/:id/webhooks/:webhookId`
- Test: `POST /api/v1/guilds/:id/webhooks/:webhookId/test`

**List Response:**
```typescript
interface WebhooksResponse {
  webhooks: Array<{
    id: string;
    name: string;
    url_preview: string; // Masked, e.g., "https://hooks.slack.com/...xxxx"
    type: "discord" | "slack" | "notion" | "generic";
    enabled: boolean;
    last_delivery: string | null;
    last_status: "success" | "failed" | null;
    created_at: string;
  }>;
}
```

**UI:**
- List of webhooks with status indicators
- Green/red dot for last_status
- Actions: Edit, Test, Delete
- "Add Webhook" button

**Webhook Form:**
- Name (text input)
- URL (text input, type="url")
- Type (dropdown: Discord, Slack, Notion, Generic)
- Enabled toggle

**Test Button:**
Shows loading, then success/error toast with response details.

---

### 9. Guild Settings (`/guilds/:id/settings`)

**API Call:** `PATCH /api/v1/guilds/:id/config`

**UI Sections:**

**Default Summary Options:**
- Summary Length (radio: Brief, Detailed, Comprehensive)
- Perspective (dropdown)
- Include Action Items (toggle)
- Include Technical Terms (toggle)

**Request:**
```typescript
interface SettingsUpdate {
  default_options: SummaryOptions;
}
```

---

## Components Library

Use shadcn/ui components. Key components needed:

- `Button` - primary actions
- `Card` - guild cards, stat cards, summary cards
- `Switch` / `Toggle` - channel enable/disable
- `Select` - dropdowns for channel, perspective, etc.
- `Dialog` / `Sheet` - modals for forms, detail views
- `Table` - schedule list, webhook list
- `Tabs` - if using tabs instead of sidebar
- `Badge` - status indicators
- `Avatar` - user and guild icons
- `Skeleton` - loading states
- `Toast` - success/error notifications
- `Form` - with react-hook-form integration

---

## State Management

Use TanStack Query for all server state:

```typescript
// Example hooks pattern
function useGuilds() {
  return useQuery({ queryKey: ['guilds'], queryFn: () => api.get('/guilds') });
}

function useGuild(id: string) {
  return useQuery({ queryKey: ['guild', id], queryFn: () => api.get(`/guilds/${id}`) });
}

function useUpdateConfig(guildId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (config: ConfigUpdate) => api.patch(`/guilds/${guildId}/config`, config),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['guild', guildId] }),
  });
}
```

Auth state can be simple React context or zustand:

```typescript
interface AuthStore {
  token: string | null;
  user: User | null;
  setAuth: (token: string, user: User, guilds: Guild[]) => void;
  logout: () => void;
}
```

---

## Error Handling

API errors return:
```typescript
interface ApiError {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
}
```

Common codes:
- `UNAUTHORIZED` (401) - redirect to login
- `FORBIDDEN` (403) - show "no permission" message
- `NOT_FOUND` (404) - show "not found" page
- `VALIDATION_ERROR` (422) - show field errors
- `RATE_LIMITED` (429) - show "slow down" message

Use toast notifications for errors. Use inline errors for form validation.

---

## Loading States

Every data fetch should show:
1. Skeleton/spinner on initial load
2. Stale data + background refresh indicator on refetch
3. Error state with retry button

---

## Responsive Design

- Mobile-first approach
- Sidebar collapses to hamburger menu on mobile
- Guild grid: 1 col mobile, 2 col tablet, 3 col desktop
- Tables become cards on mobile

---

## Dark Mode

Support system preference and manual toggle. Use Tailwind's `dark:` classes.

Store preference in localStorage.

---

## Environment Variables

```
VITE_API_URL=/api/v1
```

In development, Vite proxy handles `/api` to backend.

---

## File Structure

```
src/
├── api/
│   └── client.ts           # API client with auth
├── components/
│   ├── ui/                  # shadcn components
│   ├── layout/
│   │   ├── Header.tsx
│   │   ├── Sidebar.tsx
│   │   └── GuildLayout.tsx
│   ├── guilds/
│   │   ├── GuildCard.tsx
│   │   └── GuildGrid.tsx
│   ├── channels/
│   │   └── ChannelList.tsx
│   ├── summaries/
│   │   ├── SummaryCard.tsx
│   │   ├── SummaryDetail.tsx
│   │   └── GenerateModal.tsx
│   ├── schedules/
│   │   ├── ScheduleList.tsx
│   │   └── ScheduleForm.tsx
│   └── webhooks/
│       ├── WebhookList.tsx
│       └── WebhookForm.tsx
├── hooks/
│   ├── useAuth.ts
│   ├── useGuilds.ts
│   ├── useSummaries.ts
│   └── useSchedules.ts
├── pages/
│   ├── Landing.tsx
│   ├── Callback.tsx
│   ├── Guilds.tsx
│   ├── GuildDashboard.tsx
│   ├── Channels.tsx
│   ├── Summaries.tsx
│   ├── Schedules.tsx
│   ├── Webhooks.tsx
│   └── Settings.tsx
├── lib/
│   └── utils.ts
├── App.tsx
└── main.tsx
```

---

## Notes for Lovable

1. **No backend logic** - All data comes from API calls
2. **Optimistic updates** - Update UI immediately, rollback on error
3. **JWT in localStorage** - Simple, works for this use case
4. **Polling for tasks** - No WebSocket needed, poll every 2s during generation
5. **Forms with react-hook-form** - Handles validation, dirty state
6. **All timestamps in UTC** - Format for display using user's locale

The backend API will be built separately. Focus on clean UI and proper API integration patterns.
