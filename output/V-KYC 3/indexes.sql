-- indexes.sql
-- Defines essential indexes for performance optimization.
-- These indexes are crucial for speeding up common queries and maintaining database efficiency.

-- Indexes for 'users' table
-- Index on username for fast lookups during login/authentication
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users (username);
-- Index on email for fast lookups or unique constraint enforcement
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users (email);
-- Index on role for queries filtering users by their role
CREATE INDEX IF NOT EXISTS idx_users_role ON users (role);

-- Indexes for 'vkyc_recordings' table
-- Index on vkyc_case_id for fast lookups of specific recordings
CREATE UNIQUE INDEX IF NOT EXISTS idx_vkyc_recordings_case_id ON vkyc_recordings (vkyc_case_id);
-- Index on uploaded_by_user_id for efficient queries linking recordings to users
CREATE INDEX IF NOT EXISTS idx_vkyc_recordings_uploaded_by_user ON vkyc_recordings (uploaded_by_user_id);
-- Index on recording_date for time-based queries (e.g., recordings from a specific day/range)
CREATE INDEX IF NOT EXISTS idx_vkyc_recordings_date ON vkyc_recordings (recording_date);
-- Index on status for filtering recordings by their current state
CREATE INDEX IF NOT EXISTS idx_vkyc_recordings_status ON vkyc_recordings (status);
-- Index on file_path for quick lookup and uniqueness enforcement
CREATE UNIQUE INDEX IF NOT EXISTS idx_vkyc_recordings_file_path ON vkyc_recordings (file_path);

-- Indexes for 'audit_logs' table
-- Index on user_id for efficient retrieval of actions performed by a specific user
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs (user_id);
-- Index on timestamp for time-series analysis and chronological ordering
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs (timestamp DESC); -- Often queried in reverse chronological order
-- Composite index on resource_type and resource_id for quickly finding all actions related to a specific resource
CREATE INDEX IF NOT EXISTS idx_audit_logs_resource ON audit_logs (resource_type, resource_id);
-- Index on action for filtering by specific types of actions
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs (action);
-- Index on IP address for security analysis (e.g., identifying suspicious IPs)
CREATE INDEX IF NOT EXISTS idx_audit_logs_ip_address ON audit_logs (ip_address);

-- Note: PostgreSQL automatically creates indexes for PRIMARY KEY and UNIQUE constraints.
-- The indexes defined here are additional for common query patterns.