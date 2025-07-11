-- essential_indexes.sql
-- Defines indexes for performance optimization.

-- Index on 'created_at' for efficient date-based queries.
CREATE INDEX idx_tasks_created_at ON tasks (created_at);

-- Index on 'description' for text search and filtering.
CREATE INDEX idx_tasks_description ON tasks (description);

-- Index on the metadata column for JSONB queries (e.g., filtering by metadata fields).
CREATE INDEX idx_tasks_metadata_gin ON tasks USING GIN (metadata);