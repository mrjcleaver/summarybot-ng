-- Migration: Add command_logs table for audit trail
-- Version: 002
-- Description: Add comprehensive command logging for Discord commands, scheduled tasks, and webhooks

-- ============================================================================
-- COMMAND LOGS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS command_logs (
    -- Identity
    id TEXT PRIMARY KEY,
    command_type TEXT NOT NULL CHECK(command_type IN ('slash_command', 'scheduled_task', 'webhook_request')),
    command_name TEXT NOT NULL,

    -- Context
    user_id TEXT,  -- NULL for scheduled tasks
    guild_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,

    -- Execution data
    parameters TEXT NOT NULL DEFAULT '{}',  -- JSON
    execution_context TEXT NOT NULL DEFAULT '{}',  -- JSON

    -- Results
    status TEXT NOT NULL CHECK(status IN ('success', 'failed', 'timeout', 'cancelled')),
    error_code TEXT,
    error_message TEXT,

    -- Timing
    started_at TEXT NOT NULL,
    completed_at TEXT,
    duration_ms INTEGER CHECK(duration_ms >= 0),

    -- Output
    result_summary TEXT,  -- JSON
    metadata TEXT NOT NULL DEFAULT '{}',  -- JSON

    -- Constraints
    CHECK(completed_at IS NULL OR completed_at >= started_at)
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- Query by guild and time (most common query pattern)
CREATE INDEX IF NOT EXISTS idx_command_logs_guild_time
    ON command_logs(guild_id, started_at DESC);

-- Query by user and time
CREATE INDEX IF NOT EXISTS idx_command_logs_user_time
    ON command_logs(user_id, started_at DESC)
    WHERE user_id IS NOT NULL;

-- Query by channel and time
CREATE INDEX IF NOT EXISTS idx_command_logs_channel_time
    ON command_logs(channel_id, started_at DESC);

-- Query by type and status (for analytics)
CREATE INDEX IF NOT EXISTS idx_command_logs_type_status
    ON command_logs(command_type, status);

-- Query by time only (for cleanup operations)
CREATE INDEX IF NOT EXISTS idx_command_logs_started_at
    ON command_logs(started_at DESC);

-- Composite index for failed commands in guild (error monitoring)
CREATE INDEX IF NOT EXISTS idx_command_logs_guild_status_time
    ON command_logs(guild_id, status, started_at DESC)
    WHERE status = 'failed';

-- ============================================================================
-- SCHEMA VERSION UPDATE
-- ============================================================================
INSERT OR IGNORE INTO schema_version (version, applied_at, description)
VALUES (2, datetime('now'), 'Add command_logs table for audit trail');
