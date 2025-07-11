-- crud_queries.sql
-- Basic CRUD (Create, Read, Update, Delete) query templates for each table.
-- These are parameterized queries, meant to be used with a database connector.

-- 1. Users Table CRUD

-- CREATE User
-- Parameters: :username, :password_hash, :role
INSERT INTO users (username, password_hash, role)
VALUES (:username, :password_hash, :role)
RETURNING id, username, role, created_at, updated_at;

-- READ User(s)
-- Get all users
SELECT id, username, role, created_at, updated_at FROM users;

-- Get user by ID
-- Parameters: :user_id
SELECT id, username, role, created_at, updated_at FROM users
WHERE id = :user_id;

-- Get user by username
-- Parameters: :username
SELECT id, username, role, created_at, updated_at FROM users
WHERE username = :username;

-- UPDATE User
-- Parameters: :username, :password_hash, :role, :user_id
UPDATE users
SET
    username = :username,
    password_hash = :password_hash,
    role = :role,
    updated_at = CURRENT_TIMESTAMP -- Trigger also handles this, but explicit is fine
WHERE id = :user_id
RETURNING id, username, role, created_at, updated_at;

-- DELETE User
-- Parameters: :user_id
DELETE FROM users
WHERE id = :user_id
RETURNING id;


-- 2. VKYC Recordings Table CRUD

-- CREATE VKYC Recording
-- Parameters: :customer_id, :recording_name, :recording_path, :duration_seconds, :recording_timestamp, :status, :uploaded_by
INSERT INTO vkyc_recordings (customer_id, recording_name, recording_path, duration_seconds, recording_timestamp, status, uploaded_by)
VALUES (:customer_id, :recording_name, :recording_path, :duration_seconds, :recording_timestamp, :status, :uploaded_by)
RETURNING id, customer_id, recording_name, recording_path, status, created_at;

-- READ VKYC Recording(s)
-- Get all recordings
SELECT id, customer_id, recording_name, recording_path, duration_seconds, recording_timestamp, status, uploaded_by, created_at
FROM vkyc_recordings;

-- Get recording by ID
-- Parameters: :recording_id
SELECT id, customer_id, recording_name, recording_path, duration_seconds, recording_timestamp, status, uploaded_by, created_at
FROM vkyc_recordings
WHERE id = :recording_id;

-- Get recordings by customer ID
-- Parameters: :customer_id
SELECT id, customer_id, recording_name, recording_path, duration_seconds, recording_timestamp, status, uploaded_by, created_at
FROM vkyc_recordings
WHERE customer_id = :customer_id
ORDER BY recording_timestamp DESC;

-- Get recordings by status
-- Parameters: :status
SELECT id, customer_id, recording_name, recording_path, duration_seconds, recording_timestamp, status, uploaded_by, created_at
FROM vkyc_recordings
WHERE status = :status
ORDER BY created_at DESC;

-- UPDATE VKYC Recording Status (common operation)
-- Parameters: :new_status, :recording_id
-- Note: For full updates, list all fields. This is a common partial update.
UPDATE vkyc_recordings
SET
    status = :new_status
WHERE id = :recording_id
RETURNING id, status;

-- DELETE VKYC Recording
-- Parameters: :recording_id
DELETE FROM vkyc_recordings
WHERE id = :recording_id
RETURNING id;


-- 3. Audit Logs Table CRUD (Read and Create primarily, updates/deletes are rare for audit)

-- CREATE Audit Log (via stored procedure for consistency and validation)
-- Parameters: :user_id, :action, :resource_id, :ip_address, :details
-- Example usage in application code:
-- SELECT log_audit_event(:user_id, :action, :resource_id, :ip_address, :details);

-- READ Audit Log(s)
-- Get all audit logs (caution for large tables)
SELECT id, user_id, action, resource_id, timestamp, ip_address, details
FROM audit_logs
ORDER BY timestamp DESC;

-- Get audit logs by user ID
-- Parameters: :user_id
SELECT id, user_id, action, resource_id, timestamp, ip_address, details
FROM audit_logs
WHERE user_id = :user_id
ORDER BY timestamp DESC;

-- Get audit logs by action type
-- Parameters: :action
SELECT id, user_id, action, resource_id, timestamp, ip_address, details
FROM audit_logs
WHERE action = :action
ORDER BY timestamp DESC;

-- Get audit logs for a specific resource
-- Parameters: :resource_id
SELECT id, user_id, action, resource_id, timestamp, ip_address, details
FROM audit_logs
WHERE resource_id = :resource_id
ORDER BY timestamp DESC;

-- Get audit logs within a time range for a user
-- Parameters: :user_id, :start_timestamp, :end_timestamp
SELECT id, user_id, action, resource_id, timestamp, ip_address, details
FROM audit_logs
WHERE user_id = :user_id
  AND timestamp BETWEEN :start_timestamp AND :end_timestamp
ORDER BY timestamp DESC;

-- Note: UPDATE and DELETE operations on audit_logs are generally discouraged
-- to maintain the integrity and immutability of the audit trail.
-- If necessary, they should be highly restricted and audited themselves.