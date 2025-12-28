-- Initial database schema for Summary Bot NG
-- SQLite version
-- Created: 2024-08-24

-- ============================================================================
-- SUMMARIES TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS summaries (
    id TEXT PRIMARY KEY,
    channel_id TEXT NOT NULL,
    guild_id TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    message_count INTEGER NOT NULL,
    summary_text TEXT NOT NULL,
    key_points TEXT NOT NULL,  -- JSON array
    action_items TEXT NOT NULL,  -- JSON array of action item objects
    technical_terms TEXT NOT NULL,  -- JSON array of technical term objects
    participants TEXT NOT NULL,  -- JSON array of participant objects
    metadata TEXT NOT NULL,  -- JSON object for extensibility
    created_at TEXT NOT NULL,
    context TEXT NOT NULL  -- JSON object for summarization context
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_summaries_guild_id ON summaries(guild_id);
CREATE INDEX IF NOT EXISTS idx_summaries_channel_id ON summaries(channel_id);
CREATE INDEX IF NOT EXISTS idx_summaries_created_at ON summaries(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_summaries_guild_channel ON summaries(guild_id, channel_id);
CREATE INDEX IF NOT EXISTS idx_summaries_time_range ON summaries(start_time, end_time);

-- ============================================================================
-- GUILD CONFIGURATIONS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS guild_configs (
    guild_id TEXT PRIMARY KEY,
    enabled_channels TEXT NOT NULL,  -- JSON array
    excluded_channels TEXT NOT NULL,  -- JSON array
    default_summary_options TEXT NOT NULL,  -- JSON object
    permission_settings TEXT NOT NULL,  -- JSON object
    webhook_enabled INTEGER NOT NULL DEFAULT 0,  -- Boolean as integer
    webhook_secret TEXT
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_guild_configs_guild_id ON guild_configs(guild_id);

-- ============================================================================
-- SCHEDULED TASKS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS scheduled_tasks (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    guild_id TEXT NOT NULL,
    schedule_type TEXT NOT NULL,  -- once, daily, weekly, monthly, custom
    schedule_time TEXT,  -- HH:MM format
    schedule_days TEXT NOT NULL,  -- JSON array of weekday numbers
    cron_expression TEXT,  -- For custom scheduling
    destinations TEXT NOT NULL,  -- JSON array of destination objects
    summary_options TEXT NOT NULL,  -- JSON object
    is_active INTEGER NOT NULL DEFAULT 1,  -- Boolean as integer
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL,  -- User ID
    last_run TEXT,
    next_run TEXT,
    run_count INTEGER NOT NULL DEFAULT 0,
    failure_count INTEGER NOT NULL DEFAULT 0,
    max_failures INTEGER NOT NULL DEFAULT 3,
    retry_delay_minutes INTEGER NOT NULL DEFAULT 5
);

-- Indexes for efficient task scheduling queries
CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_guild_id ON scheduled_tasks(guild_id);
CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_channel_id ON scheduled_tasks(channel_id);
CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_is_active ON scheduled_tasks(is_active);
CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_next_run ON scheduled_tasks(next_run);
CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_active_next_run ON scheduled_tasks(is_active, next_run)
    WHERE is_active = 1;

-- ============================================================================
-- TASK EXECUTION RESULTS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS task_results (
    execution_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    status TEXT NOT NULL,  -- pending, running, completed, failed, cancelled
    started_at TEXT NOT NULL,
    completed_at TEXT,
    summary_id TEXT,
    error_message TEXT,
    error_details TEXT,  -- JSON object
    delivery_results TEXT NOT NULL,  -- JSON array
    execution_time_seconds REAL,
    FOREIGN KEY (task_id) REFERENCES scheduled_tasks(id) ON DELETE CASCADE
);

-- Indexes for task result queries
CREATE INDEX IF NOT EXISTS idx_task_results_task_id ON task_results(task_id);
CREATE INDEX IF NOT EXISTS idx_task_results_started_at ON task_results(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_task_results_status ON task_results(status);
CREATE INDEX IF NOT EXISTS idx_task_results_summary_id ON task_results(summary_id);

-- ============================================================================
-- SCHEMA VERSION TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL,
    description TEXT NOT NULL
);

-- Insert initial schema version
INSERT OR IGNORE INTO schema_version (version, applied_at, description)
VALUES (1, datetime('now'), 'Initial schema with summaries, configs, and tasks');
