-- Migration: Add warnings column to summaries table
-- Version: 008
-- Description: Store warnings generated during summary creation (e.g., model fallback)

-- SQLite doesn't support IF NOT EXISTS for ALTER TABLE, so we use a workaround
-- This will fail silently if the column already exists (handled by migration runner)
ALTER TABLE summaries ADD COLUMN warnings TEXT DEFAULT '[]';
