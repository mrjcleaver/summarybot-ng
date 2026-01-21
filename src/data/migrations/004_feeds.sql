-- Migration 004: Feed configurations for RSS/Atom distribution
-- Created: 2026-01-21

-- Feed configuration table
CREATE TABLE IF NOT EXISTS feed_configs (
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

-- Index for guild lookups
CREATE INDEX IF NOT EXISTS idx_feed_guild ON feed_configs(guild_id);

-- Index for token authentication
CREATE INDEX IF NOT EXISTS idx_feed_token ON feed_configs(token);

-- Index for channel-specific feeds
CREATE INDEX IF NOT EXISTS idx_feed_channel ON feed_configs(guild_id, channel_id);

-- Update schema version
INSERT INTO schema_version (version, applied_at, description)
VALUES (4, datetime('now'), 'Add feed_configs table for RSS/Atom distribution');
