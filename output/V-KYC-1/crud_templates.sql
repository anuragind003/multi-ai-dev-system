-- crud_templates.sql
-- Provides basic CRUD (Create, Read, Update, Delete) SQL query templates
-- for each table, using parameterized placeholders for secure execution.

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
-- Parameters: :user_id, :new_username, :new_password_hash, :new_role
UPDATE users
SET
    username = COALESCE(:new_username, username),
    password_hash = COALESCE(:new_password_hash, password_hash),
    role = COALESCE(:new_role, role),
    updated_at = CURRENT_TIMESTAMP
WHERE id = :user_id
RETURNING id, username, role, created_at, updated_at;

-- DELETE User
-- Parameters: :user_id
DELETE FROM users
WHERE id = :user_id
RETURNING id, username;


-- 2. VKYC Recordings Table CRUD

-- CREATE VKYC Recording
-- Parameters: :customer_id, :recording_name, :recording_path, :duration_seconds, :recording_timestamp, :status, :uploaded_by
INSERT INTO vkyc_recordings (customer_id, recording_name, recording_path, duration_seconds, recording_timestamp, status, uploaded_by)
VALUES (:customer_id, :recording_name, :recording_path, :duration_seconds, :recording_timestamp, :status, :uploaded_by)
RETURNING id, customer_id, recording_name, recording_path, duration_seconds, recording_timestamp, status, uploaded_by, created_at;

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
ORDER BY recording_timestamp DESC;

-- UPDATE VKYC Recording
-- Parameters: :recording_id, :new_customer_id, :new_recording_name, :new_recording_path, :new_duration_seconds, :new_recording_timestamp, :new_status
UPDATE vkyc_recordings
SET
    customer_id = COALESCE(:new_customer_id, customer_id),
    recording_name = COALESCE(:new_recording_name, recording_name),
    recording_path = COALESCE(:new_recording_path, recording_path),
    duration_seconds = COALESCE(:new_duration_seconds, duration_seconds),
    recording_timestamp = COALESCE(:new_recording_timestamp, recording_timestamp),
    status = COALESCE(:new_status, status)
WHERE id = :recording_id
RETURNING id, customer_id, recording_name, recording_path, duration_seconds, recording_timestamp, status, uploaded_by, created_at;

-- DELETE VKYC Recording
-- Parameters: :recording_id
DELETE FROM vkyc_recordings
WHERE id = :recording_id
RETURNING id, recording_name;


-- 3. Audit Logs Table CRUD (Read and Create only, updates/deletes are rare for audit logs)

-- CREATE Audit Log (typically via stored procedure)
-- Parameters: :user_id, :action, :resource_id, :ip_address, :details
INSERT INTO audit_logs (user_id, action, resource_id, timestamp, ip_address, details)
VALUES (:user_id, :action, :resource_id, CURRENT_TIMESTAMP, :ip_address, :details)
RETURNING id, user_id, action, resource_id, timestamp, ip_address, details;

-- READ Audit Log(s)
-- Get all audit logs (use with caution, can be very large)
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

-- Get audit logs within a time range
-- Parameters: :start_timestamp, :end_timestamp
SELECT id, user_id, action, resource_id, timestamp, ip_address, details
FROM audit_logs
WHERE timestamp BETWEEN :start_timestamp AND :end_timestamp
ORDER BY timestamp DESC;