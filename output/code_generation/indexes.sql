-- indexes.sql
-- Defines essential indexes for performance optimization.

-- Indexes for 'users' table
CREATE INDEX IF NOT EXISTS idx_users_username ON users (username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_users_role ON users (role);

-- Indexes for 'vkyc_recordings' table
CREATE INDEX IF NOT EXISTS idx_vkyc_recordings_customer_id ON vkyc_recordings (customer_id);
CREATE INDEX IF NOT EXISTS idx_vkyc_recordings_date ON vkyc_recordings (recording_date DESC);
CREATE INDEX IF NOT EXISTS idx_vkyc_recordings_status ON vkyc_recordings (status);
CREATE INDEX IF NOT EXISTS idx_vkyc_recordings_agent_id ON vkyc_recordings (agent_id);
-- Composite index for common queries involving date and status
CREATE INDEX IF NOT EXISTS idx_vkyc_recordings_date_status ON vkyc_recordings (recording_date DESC, status);

-- Indexes for 'audit_logs' table
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs (user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs (action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_resource_type ON audit_logs (resource_type);
-- Composite index for common queries involving user, action, and timestamp
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_action_ts ON audit_logs (user_id, action, timestamp DESC);
-- Composite index for queries by resource
CREATE INDEX IF NOT EXISTS idx_audit_logs_resource ON audit_logs (resource_type, resource_id);