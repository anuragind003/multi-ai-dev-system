-- indexes.sql
-- Defines essential indexes for performance optimization.
-- These indexes are crucial for speeding up common queries,
-- especially those involving lookups, joins, and filtering.

-- Indexes for 'users' table
-- Index on username for fast login and unique checks
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users (username);
-- Index on email for fast email-based lookups and unique checks
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users (email);
-- Index on role for filtering users by their role
CREATE INDEX IF NOT EXISTS idx_users_role ON users (role);

-- Indexes for 'recordings' table
-- Index on vkyc_id for fast unique lookups
CREATE UNIQUE INDEX IF NOT EXISTS idx_recordings_vkyc_id ON recordings (vkyc_id);
-- Index on uploaded_by_user_id for efficient joins with users table and filtering by uploader
CREATE INDEX IF NOT EXISTS idx_recordings_uploaded_by_user_id ON recordings (uploaded_by_user_id);
-- Index on recording_date for time-based queries and range scans
CREATE INDEX IF NOT EXISTS idx_recordings_recording_date ON recordings (recording_date);
-- Index on status for filtering recordings by their current state
CREATE INDEX IF NOT EXISTS idx_recordings_status ON recordings (status);
-- Combined index for common queries filtering by user and date
CREATE INDEX IF NOT EXISTS idx_recordings_user_date ON recordings (uploaded_by_user_id, recording_date);

-- Indexes for 'audit_logs' table
-- Index on user_id for efficient lookups of actions by a specific user
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs (user_id);
-- Index on timestamp for time-series analysis and range queries on audit events
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs (timestamp DESC); -- Descending for most recent logs
-- Index on action for filtering audit logs by the type of action
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs (action);
-- Index on recording_id for linking audit events to specific recordings
CREATE INDEX IF NOT EXISTS idx_audit_logs_recording_id ON audit_logs (recording_id);
-- Combined index for common queries filtering by user and action
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_action ON audit_logs (user_id, action);

-- Note: PostgreSQL automatically creates indexes for PRIMARY KEY and UNIQUE constraints.
-- These explicit CREATE INDEX statements are for additional performance optimizations
-- on frequently queried columns or combinations of columns.