-- Guild Prompt Configurations for External Prompt Hosting
-- SQLite version
-- Created: 2026-01-15

-- ============================================================================
-- GUILD PROMPT CONFIGURATIONS TABLE
-- ============================================================================
-- Stores guild-specific configurations for custom prompt repositories
CREATE TABLE IF NOT EXISTS guild_prompt_configs (
    guild_id TEXT PRIMARY KEY,
    repo_url TEXT,                  -- GitHub repository URL (e.g., "github.com/user/repo")
    branch TEXT DEFAULT 'main',     -- Branch to fetch from
    enabled INTEGER NOT NULL DEFAULT 1,  -- Boolean: feature enabled for this guild
    auth_token TEXT,                -- Encrypted PAT for private repositories (Fernet encrypted)
    last_sync TEXT,                 -- ISO timestamp of last successful sync
    last_sync_status TEXT DEFAULT 'never',  -- Status: success, failed, rate_limited, never
    validation_errors TEXT,         -- JSON array of validation errors from last sync
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_guild_prompt_configs_enabled
    ON guild_prompt_configs(enabled)
    WHERE enabled = 1;

CREATE INDEX IF NOT EXISTS idx_guild_prompt_configs_last_sync
    ON guild_prompt_configs(last_sync DESC);

CREATE INDEX IF NOT EXISTS idx_guild_prompt_configs_status
    ON guild_prompt_configs(last_sync_status);

-- ============================================================================
-- PROMPT CACHE TABLE (Optional - for persistent caching across restarts)
-- ============================================================================
-- Stores cached prompts with metadata for faster resolution
CREATE TABLE IF NOT EXISTS prompt_cache (
    cache_key TEXT PRIMARY KEY,     -- Format: "prompt:{guild_id}:{context_hash}"
    guild_id TEXT NOT NULL,
    content TEXT NOT NULL,          -- Cached prompt content
    source TEXT NOT NULL,           -- Source: custom, default, fallback
    version TEXT NOT NULL,          -- Schema version: v1, v2
    repo_url TEXT,                  -- Source repository URL
    context_hash TEXT NOT NULL,     -- Hash of context (category+channel+type)
    cached_at TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at TEXT NOT NULL,       -- TTL expiration timestamp
    FOREIGN KEY (guild_id) REFERENCES guild_prompt_configs(guild_id) ON DELETE CASCADE
);

-- Indexes for cache performance
CREATE INDEX IF NOT EXISTS idx_prompt_cache_guild_id
    ON prompt_cache(guild_id);

CREATE INDEX IF NOT EXISTS idx_prompt_cache_expires_at
    ON prompt_cache(expires_at);

-- Index for cleanup of expired entries
CREATE INDEX IF NOT EXISTS idx_prompt_cache_expired
    ON prompt_cache(expires_at)
    WHERE datetime(expires_at) < datetime('now');

-- ============================================================================
-- PROMPT FETCH LOG TABLE (Optional - for observability)
-- ============================================================================
-- Tracks GitHub fetch attempts for monitoring and debugging
CREATE TABLE IF NOT EXISTS prompt_fetch_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id TEXT NOT NULL,
    repo_url TEXT NOT NULL,
    file_path TEXT NOT NULL,
    status TEXT NOT NULL,           -- Status: success, failed, timeout, rate_limited
    status_code INTEGER,            -- HTTP status code (if applicable)
    error_message TEXT,             -- Error details if failed
    duration_ms INTEGER,            -- Fetch duration in milliseconds
    fetched_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (guild_id) REFERENCES guild_prompt_configs(guild_id) ON DELETE CASCADE
);

-- Indexes for log queries
CREATE INDEX IF NOT EXISTS idx_prompt_fetch_log_guild_id
    ON prompt_fetch_log(guild_id);

CREATE INDEX IF NOT EXISTS idx_prompt_fetch_log_fetched_at
    ON prompt_fetch_log(fetched_at DESC);

CREATE INDEX IF NOT EXISTS idx_prompt_fetch_log_status
    ON prompt_fetch_log(status);

-- Composite index for guild+status queries
CREATE INDEX IF NOT EXISTS idx_prompt_fetch_log_guild_status
    ON prompt_fetch_log(guild_id, status, fetched_at DESC);

-- ============================================================================
-- UPDATE SCHEMA VERSION
-- ============================================================================
INSERT OR IGNORE INTO schema_version (version, applied_at, description)
VALUES (3, datetime('now'), 'External prompt hosting: guild_prompt_configs, prompt_cache, prompt_fetch_log');
