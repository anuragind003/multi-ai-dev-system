-- crud_queries.sql
-- Basic CRUD (Create, Read, Update, Delete) query templates for all tables.

-- =============================================================================
-- USERS TABLE CRUD OPERATIONS
-- =============================================================================

-- CREATE User
-- Note: password_hash should be generated securely (e.g., bcrypt) in application code.
INSERT INTO users (username, password_hash, email, role)
VALUES ('new_user', 'secure_hashed_password', 'new.user@example.com', 'user');

-- READ Users
SELECT id, username, email, role, created_at, updated_at
FROM users
ORDER BY created_at DESC;

-- READ User by ID
SELECT id, username, email, role, created_at, updated_at
FROM users
WHERE id = 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11'; -- Replace with actual user ID

-- READ User by Username
SELECT id, username, email, role, created_at, updated_at
FROM users
WHERE username = 'admin_user';

-- UPDATE User Role and Email
UPDATE users
SET
    email = 'updated.admin@example.com',
    role = 'admin'
WHERE id = 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11'; -- Replace with actual user ID

-- DELETE User
DELETE FROM users
WHERE id = 'c2d3e4f5-a6b7-8901-2345-67890abcdef0'; -- Replace with actual user ID
-- Note: Due to ON DELETE RESTRICT on audit_logs, this will fail if the user has audit logs.
-- You would need to handle associated audit logs first (e.g., reassign, anonymize, or delete).

-- =============================================================================
-- VKYC_RECORDINGS TABLE CRUD OPERATIONS
-- =============================================================================

-- CREATE VKYC Recording
INSERT INTO vkyc_recordings (customer_id, recording_date, recording_time, status, file_path, duration_seconds, agent_id)
VALUES ('CUST-004', '2023-10-25', '09:00:00', 'pending', 's3://vkyc-recordings/cust004_20231025.mp4', 200, 'agent_alpha');

-- READ VKYC Recordings
SELECT id, customer_id, recording_date, recording_time, status, file_path, duration_seconds, agent_id, created_at
FROM vkyc_recordings
ORDER BY recording_date DESC, recording_time DESC;

-- READ VKYC Recording by ID
SELECT id, customer_id, recording_date, recording_time, status, file_path, duration_seconds, agent_id, created_at
FROM vkyc_recordings
WHERE id = 'd3e4f5a6-b7c8-9012-3456-7890abcdef01'; -- Replace with actual recording ID

-- READ VKYC Recordings by Customer ID and Status
SELECT id, customer_id, recording_date, recording_time, status, file_path, duration_seconds, agent_id, created_at
FROM vkyc_recordings
WHERE customer_id = 'CUST-001' AND status = 'approved';

-- UPDATE VKYC Recording Status and Agent
UPDATE vkyc_recordings
SET
    status = 'approved',
    agent_id = 'agent_beta'
WHERE id = 'e4f5a6b7-c8d9-0123-4567-890abcdef012'; -- Replace with actual recording ID

-- DELETE VKYC Recording
DELETE FROM vkyc_recordings
WHERE id = 'f5a6b7c8-d9e0-1234-5678-90abcdef0123'; -- Replace with actual recording ID

-- =============================================================================
-- AUDIT_LOGS TABLE CRUD OPERATIONS
-- =============================================================================

-- CREATE Audit Log (Prefer using the log_audit_event function)
-- INSERT INTO audit_logs (user_id, action, resource_type, resource_id, ip_address)
-- VALUES ('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'manual_entry', 'system', NULL, '127.0.0.1'::INET);

-- READ Audit Logs
SELECT id, user_id, action, resource_type, resource_id, timestamp, ip_address
FROM audit_logs
ORDER BY timestamp DESC
LIMIT 100;

-- READ Audit Logs by User ID
SELECT id, user_id, action, resource_type, resource_id, timestamp, ip_address
FROM audit_logs
WHERE user_id = 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11' -- Replace with actual user ID
ORDER BY timestamp DESC;

-- READ Audit Logs by Action Type
SELECT id, user_id, action, resource_type, resource_id, timestamp, ip_address
FROM audit_logs
WHERE action = 'login'
ORDER BY timestamp DESC;

-- READ Audit Logs for a specific resource
SELECT id, user_id, action, resource_type, resource_id, timestamp, ip_address
FROM audit_logs
WHERE resource_type = 'vkyc_recording' AND resource_id = 'd3e4f5a6-b7c8-9012-3456-7890abcdef01'
ORDER BY timestamp DESC;

-- UPDATE Audit Log (Generally not recommended for audit logs, but shown for completeness)
-- UPDATE audit_logs
-- SET action = 'corrected_action'
-- WHERE id = 'some_audit_log_id';

-- DELETE Audit Log (Generally not recommended for audit logs, but shown for completeness)
-- DELETE FROM audit_logs
-- WHERE id = 'some_audit_log_id';
-- Or for cleanup of old logs (e.g., logs older than 1 year)
-- DELETE FROM audit_logs WHERE timestamp < NOW() - INTERVAL '1 year';