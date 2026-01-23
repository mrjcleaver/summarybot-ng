-- Migration 006: Add prompt and source content tracking to summaries
-- Created: 2026-01-23

-- Add columns for tracking prompt content and source messages
ALTER TABLE summaries ADD COLUMN prompt_system TEXT;
ALTER TABLE summaries ADD COLUMN prompt_user TEXT;
ALTER TABLE summaries ADD COLUMN prompt_template_id TEXT;
ALTER TABLE summaries ADD COLUMN source_content TEXT;

-- Update schema version
INSERT INTO schema_version (version, applied_at, description)
VALUES (6, datetime('now'), 'Add prompt and source content tracking to summaries');
