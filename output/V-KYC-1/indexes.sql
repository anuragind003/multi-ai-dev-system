-- indexes.sql
-- Defines essential indexes for performance optimization beyond primary and foreign keys.

-- Indexes for 'users' table
-- username already has a unique index from its UNIQUE constraint.
-- An index on 'role' is useful for filtering users by their role.
CREATE INDEX IF NOT EXISTS ix_users_role ON users (role);

-- Indexes for 'vkyc_recordings' table
-- customer_id: Frequently queried for specific customer recordings.
CREATE INDEX IF NOT EXISTS ix_vkyc_recordings_customer_id ON vkyc_recordings (customer_id);
-- recording_timestamp: Essential for time-based searches and sorting.
CREATE INDEX IF NOT EXISTS ix_vkyc_recordings_recording_timestamp ON vkyc_recordings (recording_timestamp DESC); -- Descending for most recent
-- status: Useful for filtering recordings by their processing status.
CREATE INDEX IF NOT EXISTS ix_vkyc_recordings_status ON vkyc_recordings (status);
-- uploaded_by: For quickly finding recordings uploaded by a specific user.
CREATE INDEX IF NOT EXISTS ix_vkyc_recordings_uploaded_by ON vkyc_recordings (uploaded_by);
-- Composite index for common queries involving customer_id and timestamp
CREATE INDEX IF NOT EXISTS ix_vkyc_recordings_customer_timestamp ON vkyc_recordings (customer_id, recording_timestamp DESC);

-- Indexes for 'audit_logs' table
-- user_id: For quickly retrieving all actions by a specific user.
CREATE INDEX IF NOT EXISTS ix_audit_logs_user_id ON audit_logs (user_id);
-- action: For filtering logs by the type of action.
CREATE INDEX IF NOT EXISTS ix_audit_logs_action ON audit_logs (action);
-- timestamp: Crucial for time-based audit trails and sorting.
CREATE INDEX IF NOT EXISTS ix_audit_logs_timestamp ON audit_logs (timestamp DESC); -- Descending for most recent
-- resource_id: For finding all actions related to a specific recording.
CREATE INDEX IF NOT EXISTS ix_audit_logs_resource_id ON audit_logs (resource_id);
-- Composite index for common audit log queries: user actions within a time range.
CREATE INDEX IF NOT EXISTS ix_audit_logs_user_action_timestamp ON audit_logs (user_id, action, timestamp DESC);
-- Composite index for common audit log queries: resource actions within a time range.
CREATE IF NOT EXISTS ix_audit_logs_resource_action_timestamp ON audit_logs (resource_id, action, timestamp DESC) WHERE resource_id IS NOT NULL;