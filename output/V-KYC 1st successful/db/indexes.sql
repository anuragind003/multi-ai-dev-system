-- db/indexes.sql
-- This file defines essential indexes for performance optimization.
-- Indexes are crucial for speeding up data retrieval operations, especially on large tables.

-- Indexes for 'users' table
-- Index on email for faster lookups, especially for login or user identification
CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);
-- Index on username for faster lookups
CREATE INDEX IF NOT EXISTS idx_users_username ON users (username);
-- Index on role for queries filtering by user roles
CREATE INDEX IF NOT EXISTS idx_users_role ON users (role);

-- Indexes for 'vkyc_recordings' table
-- Index on customer_id for efficient retrieval of all recordings for a specific customer
CREATE INDEX IF NOT EXISTS idx_vkyc_recordings_customer_id ON vkyc_recordings (customer_id);
-- Index on recording_date for date-based queries and range scans
CREATE INDEX IF NOT EXISTS idx_vkyc_recordings_recording_date ON vkyc_recordings (recording_date);
-- Index on status for filtering recordings by their current status
CREATE INDEX IF NOT EXISTS idx_vkyc_recordings_status ON vkyc_recordings (status);
-- Composite index on customer_id and status for common queries combining these filters
CREATE INDEX IF NOT EXISTS idx_vkyc_recordings_customer_status ON vkyc_recordings (customer_id, status);
-- Index on agent_id for queries related to agent performance or assignments
CREATE INDEX IF NOT EXISTS idx_vkyc_recordings_agent_id ON vkyc_recordings (agent_id);

-- Indexes for 'audit_logs' table
-- Index on user_id for efficient retrieval of audit logs for a specific user (foreign key)
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs (user_id);
-- Index on timestamp for time-based queries and sorting of audit events
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs (timestamp DESC);
-- Index on action for filtering audit logs by the type of action performed
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs (action);
-- Composite index on user_id and timestamp for common queries retrieving a user's actions over time
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_timestamp ON audit_logs (user_id, timestamp DESC);

-- Reindex system tables and user tables for optimal performance after schema changes or data loads
-- This is typically done during maintenance windows.
-- VACUUM ANALYZE; -- Run this periodically to update statistics for the query planner
-- REINDEX DATABASE vkyc_db; -- Use with caution, can lock tables