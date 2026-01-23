-- Migration 005: Error logging for operational error tracking
-- Created: 2026-01-22

-- Error logs table for tracking operational errors
CREATE TABLE IF NOT EXISTS error_logs (
    id TEXT PRIMARY KEY,
    guild_id TEXT,                          -- Discord guild (nullable for system-wide errors)
    channel_id TEXT,                        -- Discord channel involved (if applicable)
    error_type TEXT NOT NULL,               -- Category: discord_permission, api_error, etc.
    severity TEXT NOT NULL DEFAULT 'error', -- info, warning, error, critical
    error_code TEXT,                        -- Specific code (e.g., "403", "MISSING_ACCESS")
    message TEXT NOT NULL,                  -- Human-readable error message
    details TEXT,                           -- JSON with additional context
    operation TEXT,                         -- What operation was attempted
    user_id TEXT,                           -- User who triggered the operation
    stack_trace TEXT,                       -- For debugging
    created_at TEXT NOT NULL,               -- When the error occurred
    resolved_at TEXT,                       -- When resolved (null = unresolved)
    resolution_notes TEXT                   -- How it was resolved
);

-- Index for guild-specific error queries
CREATE INDEX IF NOT EXISTS idx_error_guild ON error_logs(guild_id, created_at DESC);

-- Index for error type filtering
CREATE INDEX IF NOT EXISTS idx_error_type ON error_logs(error_type, created_at DESC);

-- Index for severity filtering
CREATE INDEX IF NOT EXISTS idx_error_severity ON error_logs(severity, created_at DESC);

-- Index for cleanup queries (old error deletion)
CREATE INDEX IF NOT EXISTS idx_error_created ON error_logs(created_at);

-- Index for unresolved errors
CREATE INDEX IF NOT EXISTS idx_error_unresolved ON error_logs(resolved_at) WHERE resolved_at IS NULL;

-- Update schema version
INSERT INTO schema_version (version, applied_at, description)
VALUES (5, datetime('now'), 'Add error_logs table for operational error tracking');
