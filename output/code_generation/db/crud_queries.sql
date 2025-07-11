-- db/crud_queries.sql
-- This file provides basic CRUD (Create, Read, Update, Delete) query templates
-- for the 'users', 'vkyc_recordings', and 'audit_logs' tables.
-- These are templates and should be parameterized in application code to prevent SQL injection.

-- =============================================================================
-- USERS TABLE CRUD OPERATIONS
-- =============================================================================

-- CREATE User
-- Note: password_hash should be generated securely (e.g., bcrypt) in application code.
INSERT INTO users (username, password_hash, email, role)
VALUES ('new_user', '$2b$12$HASHEDPASSWORDHERE', 'new.user@example.com', 'user');

-- READ Users
-- Select all users (use with caution on large tables)
SELECT id, username, email, role, created_at, updated_at FROM users;

-- Select a user by ID
SELECT id, username, email, role, created_at, updated_at FROM users WHERE id = 'a1b2c3d4-e5f6-7890-1234-567890abcdef';

-- Select a user by username
SELECT id, username, email, role, created_at, updated_at FROM users WHERE username = 'john_doe';

-- Select users by role
SELECT id, username, email, role, created_at, updated_at FROM users WHERE role = 'auditor';

-- UPDATE User
-- Update user email and role by ID
UPDATE users
SET email = 'updated.email@example.com', role = 'admin', updated_at = CURRENT_TIMESTAMP
WHERE id = 'a1b2c3d4-e5f6-7890-1234-567890abcdef';

-- Update user password hash by username
UPDATE users
SET password_hash = '$2b$12$NEWHASHEDPASSWORDHERE', updated_at = CURRENT_TIMESTAMP
WHERE username = 'new_user';

-- DELETE User
DELETE FROM users WHERE id = 'a1b2c3d4-e5f6-7890-1234-567890abcdef';
DELETE FROM users WHERE username = 'new_user';

-- =============================================================================
-- VKYC_RECORDINGS TABLE CRUD OPERATIONS
-- =============================================================================

-- CREATE VKYC Recording
INSERT INTO vkyc_recordings (customer_id, recording_date, recording_time, status, file_path, duration_seconds, agent_id)
VALUES ('CUST006', '2023-10-27', '10:00:00', 'PENDING', '/recordings/2023/10/CUST006_1000.mp4', 180, 'AGENT004');

-- READ VKYC Recordings
-- Select all recordings
SELECT id, customer_id, recording_date, recording_time, status, file_path, duration_seconds, agent_id, created_at FROM vkyc_recordings;

-- Select a recording by ID
SELECT id, customer_id, recording_date, recording_time, status, file_path, duration_seconds, agent_id, created_at FROM vkyc_recordings WHERE id = 'b1c2d3e4-f5a6-7890-1234-567890abcdef';

-- Select recordings by customer ID
SELECT id, customer_id, recording_date, recording_time, status, file_path, duration_seconds, agent_id, created_at FROM vkyc_recordings WHERE customer_id = 'CUST001';

-- Select recordings by status
SELECT id, customer_id, recording_date, recording_time, status, file_path, duration_seconds, agent_id, created_at FROM vkyc_recordings WHERE status = 'REVIEW_REQUIRED';

-- Select recordings within a date range
SELECT id, customer_id, recording_date, recording_time, status, file_path, duration_seconds, agent_id, created_at
FROM vkyc_recordings
WHERE recording_date BETWEEN '2023-10-20' AND '2023-10-21';

-- UPDATE VKYC Recording
-- Update status and agent_id for a specific recording
UPDATE vkyc_recordings
SET status = 'APPROVED', agent_id = 'AGENT005'
WHERE id = 'b1c2d3e4-f5a6-7890-1234-567890abcdef';

-- Update file_path and duration for a recording
UPDATE vkyc_recordings
SET file_path = '/recordings/updated/CUST006_new.mp4', duration_seconds = 200
WHERE customer_id = 'CUST006';

-- DELETE VKYC Recording
DELETE FROM vkyc_recordings WHERE id = 'b1c2d3e4-f5a6-7890-1234-567890abcdef';
DELETE FROM vkyc_recordings WHERE customer_id = 'CUST006';

-- =============================================================================
-- AUDIT_LOGS TABLE CRUD OPERATIONS
-- =============================================================================

-- CREATE Audit Log
-- Note: user_id and resource_id should be valid UUIDs from respective tables.
INSERT INTO audit_logs (user_id, action, resource_type, resource_id, ip_address)
VALUES ('a1b2c3d4-e5f6-7890-1234-567890abcdef', 'DELETE_RECORDING', 'VKYC_RECORDING', 'b1c2d3e4-f5a6-7890-1234-567890abcdef', '192.168.1.100');

-- READ Audit Logs
-- Select all audit logs (use with caution)
SELECT id, user_id, action, resource_type, resource_id, timestamp, ip_address FROM audit_logs;

-- Select audit logs for a specific user
SELECT id, user_id, action, resource_type, resource_id, timestamp, ip_address
FROM audit_logs
WHERE user_id = 'a1b2c3d4-e5f6-7890-1234-567890abcdef'
ORDER BY timestamp DESC;

-- Select audit logs for a specific resource type and ID
SELECT id, user_id, action, resource_type, resource_id, timestamp, ip_address
FROM audit_logs
WHERE resource_type = 'VKYC_RECORDING' AND resource_id = 'b1c2d3e4-f5a6-7890-1234-567890abcdef'
ORDER BY timestamp DESC;

-- Select audit logs for a specific action
SELECT id, user_id, action, resource_type, resource_id, timestamp, ip_address
FROM audit_logs
WHERE action = 'LOGIN'
ORDER BY timestamp DESC;

-- UPDATE Audit Log (Rarely updated, typically append-only)
-- If an update is needed, it's usually for correction, not typical CRUD.
-- Example: Correcting an IP address (hypothetical)
-- UPDATE audit_logs
-- SET ip_address = '192.168.1.101'
-- WHERE id = 'c1d2e3f4-a5b6-7890-1234-567890abcdef';

-- DELETE Audit Log (Rarely deleted, typically retained for compliance)
-- Deletion should be handled with extreme care, usually only for data retention policies.
-- Example: Delete logs older than 5 years
-- DELETE FROM audit_logs WHERE timestamp < NOW() - INTERVAL '5 years';