# RSS and ATOM Feed Distribution for SummaryBot-NG

## Overview

Add RSS 2.0 and Atom 1.0 feed distribution for Discord channel summaries, allowing users to subscribe to summary feeds per guild or channel.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Feed Reader    │────▶│  /feeds/* API    │────▶│ FeedGenerator   │
│  (Feedly, etc)  │     │  (public/token)  │     │ (RSS/Atom XML)  │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                │                        │
                                ▼                        ▼
                        ┌──────────────────┐     ┌─────────────────┐
                        │ FeedRepository   │     │ SummaryRepository│
                        │ (feed configs)   │     │ (summary data)  │
                        └──────────────────┘     └─────────────────┘
```

## New Files to Create

| File | Purpose |
|------|---------|
| `src/models/feed.py` | FeedConfig dataclass and FeedType enum |
| `src/feeds/__init__.py` | Package exports |
| `src/feeds/generator.py` | RSS 2.0 and Atom 1.0 XML generation |
| `src/dashboard/routes/feeds.py` | Feed management + serving endpoints |
| `src/data/migrations/003_feeds.sql` | Database schema for feed configs |

## Files to Modify

| File | Changes |
|------|---------|
| `src/dashboard/models.py` | Add feed Pydantic schemas |
| `src/dashboard/router.py` | Include feeds_router |
| `src/data/base.py` | Add FeedRepository interface |
| `src/data/sqlite.py` | Implement SQLiteFeedRepository |

## API Endpoints

### Feed Management (JWT Auth Required)
```
GET    /api/v1/guilds/{guild_id}/feeds              - List feeds
POST   /api/v1/guilds/{guild_id}/feeds              - Create feed
GET    /api/v1/guilds/{guild_id}/feeds/{feed_id}    - Get feed details
PATCH  /api/v1/guilds/{guild_id}/feeds/{feed_id}    - Update feed
DELETE /api/v1/guilds/{guild_id}/feeds/{feed_id}    - Delete feed
POST   /api/v1/guilds/{guild_id}/feeds/{feed_id}/regenerate-token - New token
```

### Public Feed Serving (Token or Public)
```
GET /feeds/{feed_id}.rss   - RSS 2.0 feed
GET /feeds/{feed_id}.atom  - Atom 1.0 feed
```

Authentication: `?token=<feed_token>` or public if `is_public=true`

## Data Model

```python
@dataclass
class FeedConfig:
    id: str                          # Unique feed ID
    guild_id: str                    # Discord guild
    channel_id: Optional[str]        # None = all channels
    feed_type: FeedType              # RSS or ATOM
    is_public: bool                  # Public feeds need no auth
    token: Optional[str]             # Secret token for private feeds
    title: Optional[str]             # Custom feed title
    description: Optional[str]       # Custom description
    max_items: int = 50              # Items in feed (1-100)
    include_full_content: bool       # Full summary vs excerpt
    created_at: datetime
    created_by: str                  # Discord user ID
    last_accessed: Optional[datetime]
    access_count: int = 0
```

## Feed Generation

### RSS 2.0 Item Structure
```xml
<item>
  <title>Summary: #channel - Jan 21, 2026</title>
  <link>https://summarybot.lovable.app/guilds/{guild_id}/summaries/{id}</link>
  <guid isPermaLink="false">summarybot:summary:{id}</guid>
  <pubDate>Wed, 21 Jan 2026 14:30:00 GMT</pubDate>
  <description><![CDATA[{summary content}]]></description>
</item>
```

### Atom 1.0 Entry Structure
```xml
<entry>
  <id>urn:summarybot:summary:{id}</id>
  <title>Summary: #channel - Jan 21, 2026</title>
  <link href="..."/>
  <updated>2026-01-21T14:30:00Z</updated>
  <content type="html"><![CDATA[{summary content}]]></content>
</entry>
```

## Caching Strategy

- **ETag**: Hash of feed_id + latest summary timestamp + count
- **Last-Modified**: Newest summary's created_at
- **Cache-Control**: `public, max-age=300` (5 minutes)
- Return **304 Not Modified** when client cache is valid

## Database Migration

```sql
CREATE TABLE feed_configs (
    id TEXT PRIMARY KEY,
    guild_id TEXT NOT NULL,
    channel_id TEXT,
    feed_type TEXT NOT NULL DEFAULT 'rss',
    is_public INTEGER NOT NULL DEFAULT 0,
    token TEXT UNIQUE,
    title TEXT,
    description TEXT,
    max_items INTEGER NOT NULL DEFAULT 50,
    include_full_content INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL,
    last_accessed TEXT,
    access_count INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX idx_feed_guild ON feed_configs(guild_id);
CREATE INDEX idx_feed_token ON feed_configs(token);
```

## Implementation Phases

### Phase 1: Core Models
1. Create `src/models/feed.py` with FeedConfig and FeedType
2. Add FeedRepository interface to `src/data/base.py`
3. Implement SQLiteFeedRepository in `src/data/sqlite.py`
4. Create database migration `003_feeds.sql`

### Phase 2: Feed Generation
5. Create `src/feeds/generator.py` with FeedGenerator class
6. Implement RSS 2.0 XML generation
7. Implement Atom 1.0 XML generation
8. Add caching logic with ETag/Last-Modified

### Phase 3: API Endpoints
9. Add Pydantic schemas to `src/dashboard/models.py`
10. Create `src/dashboard/routes/feeds.py`
11. Wire up routes in `src/dashboard/router.py`

### Phase 4: Testing
12. Test feed generation with sample summaries
13. Test API endpoints with curl
14. Test caching behavior

## Environment Variables

```bash
FEED_BASE_URL=https://summarybot-ng.fly.dev  # Base URL for links
FEED_DEFAULT_MAX_ITEMS=50                     # Default items
FEED_CACHE_TTL=300                           # Cache TTL seconds
```

## Verification

1. **Create a feed**:
   ```bash
   curl -X POST https://summarybot-ng.fly.dev/api/v1/guilds/{guild_id}/feeds \
     -H "Authorization: Bearer {jwt}" \
     -H "Content-Type: application/json" \
     -d '{"feed_type": "rss", "is_public": true}'
   ```

2. **Access RSS feed**:
   ```bash
   curl https://summarybot-ng.fly.dev/feeds/{feed_id}.rss
   ```

3. **Verify XML is valid RSS 2.0**:
   ```bash
   curl -s .../feeds/{id}.rss | xmllint --noout -
   ```

4. **Test caching**:
   ```bash
   curl -I https://summarybot-ng.fly.dev/feeds/{feed_id}.rss
   # Check for ETag and Last-Modified headers
   ```

5. **Add to feed reader** (Feedly, NewsBlur, etc.) and verify summaries appear
