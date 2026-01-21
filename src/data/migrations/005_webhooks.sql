-- Webhooks table for persistent webhook storage
-- SQLite version
-- Created: 2026-01-21

-- ============================================================================
-- WEBHOOKS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS webhooks (
    id TEXT PRIMARY KEY,
    guild_id TEXT NOT NULL,
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'generic',
    headers TEXT NOT NULL DEFAULT '{}',  -- JSON object
    enabled INTEGER NOT NULL DEFAULT 1,
    last_delivery TEXT,
    last_status TEXT,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_webhooks_guild_id ON webhooks(guild_id);
CREATE INDEX IF NOT EXISTS idx_webhooks_enabled ON webhooks(enabled);

-- Insert schema version
INSERT OR IGNORE INTO schema_version (version, applied_at, description)
VALUES (5, datetime('now'), 'Add webhooks table for persistent storage');
