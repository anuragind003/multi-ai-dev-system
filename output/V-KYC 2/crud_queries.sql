-- crud_queries.sql
-- Basic CRUD (Create, Read, Update, Delete) query templates for the database tables.
-- These are parameterized queries, meant to be used with a database connector
-- that supports parameter binding (e.g., psycopg2 in Python).

-- --- USERS TABLE ---

-- CREATE User
-- Parameters: :id (UUID, optional, if not using default), :username, :password_hash, :email, :role
INSERT INTO users (id, username, password_hash, email, role)
VALUES (:id, :username, :password_hash, :email, :role);

-- READ User by ID
-- Parameters: :user_id
SELECT id, username, email, role, created_at
FROM users
WHERE id = :user_id;

-- READ User by Username
-- Parameters: :username
SELECT id, username, email, role, created_at
FROM users
WHERE username = :username;

-- READ All Users (with pagination example)
-- Parameters: :limit, :offset
SELECT id, username, email, role, created_at
FROM users
ORDER BY created_at DESC
LIMIT :limit OFFSET :offset;

-- UPDATE User Email and Role
-- Parameters: :new_email, :new_role, :user_id
UPDATE users
SET email = :new_email, role = :new_role
WHERE id = :user_id;

-- DELETE User
-- Parameters: :user_id
-- Note: This will fail if there are related recordings due to ON DELETE RESTRICT.
-- Use the stored procedure `delete_user_and_audit` for safer deletion.
DELETE FROM users
WHERE id = :user_id;


-- --- RECORDINGS TABLE ---

-- CREATE Recording
-- Parameters: :id (UUID, optional), :vkyc_id, :customer_name, :recording_date, :duration_seconds,
--             :file_name, :storage_path, :uploaded_by_user_id, :status (optional, default 'available')
INSERT INTO recordings (id, vkyc_id, customer_name, recording_date, duration_seconds, file_name, storage_path, uploaded_by_user_id, status)
VALUES (:id, :vkyc_id, :customer_name, :recording_date, :duration_seconds, :file_name, :storage_path, :uploaded_by_user_id, :status);

-- READ Recording by ID
-- Parameters: :recording_id
SELECT id, vkyc_id, customer_name, recording_date, duration_seconds, file_name, storage_path, uploaded_by_user_id, uploaded_at, status
FROM recordings
WHERE id = :recording_id;

-- READ Recording by VKYC ID
-- Parameters: :vkyc_id
SELECT id, vkyc_id, customer_name, recording_date, duration_seconds, file_name, storage_path, uploaded_by_user_id, uploaded_at, status
FROM recordings
WHERE vkyc_id = :vkyc_id;

-- READ Recordings by User ID
-- Parameters: :user_id
SELECT id, vkyc_id, customer_name, recording_date, duration_seconds, file_name, storage_path, uploaded_by_user_id, uploaded_at, status
FROM recordings
WHERE uploaded_by_user_id = :user_id
ORDER BY uploaded_at DESC;

-- UPDATE Recording Status and Storage Path
-- Parameters: :new_status, :new_storage_path, :recording_id
UPDATE recordings
SET status = :new_status, storage_path = :new_storage_path
WHERE id = :recording_id;

-- DELETE Recording
-- Parameters: :recording_id
DELETE FROM recordings
WHERE id = :recording_id;


-- --- AUDIT_LOGS TABLE ---

-- CREATE Audit Log Entry
-- Parameters: :id (UUID, optional), :user_id, :action, :recording_id (optional), :ip_address (optional), :details (JSONB, optional)
INSERT INTO audit_logs (id, user_id, action, recording_id, ip_address, details)
VALUES (:id, :user_id, :action, :recording_id, :ip_address, :details);

-- READ Audit Logs by User ID
-- Parameters: :user_id, :limit, :offset
SELECT id, user_id, action, recording_id, timestamp, ip_address, details
FROM audit_logs
WHERE user_id = :user_id
ORDER BY timestamp DESC
LIMIT :limit OFFSET :offset;

-- READ Audit Logs by Action Type
-- Parameters: :action_type, :limit, :offset
SELECT id, user_id, action, recording_id, timestamp, ip_address, details
FROM audit_logs
WHERE action = :action_type
ORDER BY timestamp DESC
LIMIT :limit OFFSET :offset;

-- READ Audit Logs for a specific Recording
-- Parameters: :recording_id, :limit, :offset
SELECT id, user_id, action, recording_id, timestamp, ip_address, details
FROM audit_logs
WHERE recording_id = :recording_id
ORDER BY timestamp DESC
LIMIT :limit OFFSET :offset;

-- DELETE Audit Logs older than a specific date
-- Parameters: :cutoff_timestamp
DELETE FROM audit_logs
WHERE timestamp < :cutoff_timestamp;