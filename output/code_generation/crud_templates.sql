-- crud_templates.sql
-- Basic SQL CRUD (Create, Read, Update, Delete) query templates for the VKYC portal tables.

-- ====================================================================================================
-- USERS TABLE CRUD
-- ====================================================================================================

-- CREATE User (using stored procedure for robust creation and logging)
-- CALL create_user('new_user_name', 'hashed_password_string', 'new_user@example.com', 'user');
-- SELECT create_user('new_user_name', 'hashed_password_string', 'new_user@example.com', 'user');

-- READ Users
-- Get all users
SELECT id, username, email, role, created_at, updated_at FROM users;

-- Get user by ID
SELECT id, username, email, role, created_at, updated_at FROM users WHERE id = 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11';

-- Get user by username
SELECT id, username, email, role, created_at, updated_at FROM users WHERE username = 'admin_user';

-- Get user by email
SELECT id, username, email, role, created_at, updated_at FROM users WHERE email = 'admin@example.com';

-- UPDATE User
-- Update user role
UPDATE users SET role = 'admin', updated_at = CURRENT_TIMESTAMP WHERE id = 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11';

-- Update user email
UPDATE users SET email = 'new_email@example.com', updated_at = CURRENT_TIMESTAMP WHERE username = 'regular_user';

-- Update password (using stored procedure for robust update and logging)
-- SELECT update_user_password('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'new_hashed_password_string');

-- DELETE User
DELETE FROM users WHERE id = 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a13';
-- Note: Deleting a user will CASCADE delete their audit_logs entries.

-- ====================================================================================================
-- VKYC_RECORDINGS TABLE CRUD
-- ====================================================================================================

-- CREATE VKYC Recording
INSERT INTO vkyc_recordings (customer_id, recording_date, recording_time, status, file_path, duration_seconds, agent_id) VALUES
('CUST-004', '2023-10-27', '15:00:00', 'pending', '/recordings/2023/10/CUST-004_1.mp4', 100, 'AGENT-D');

-- READ VKYC Recordings
-- Get all recordings
SELECT id, customer_id, recording_date, recording_time, status, file_path, duration_seconds, agent_id, created_at FROM vkyc_recordings;

-- Get recording by ID
SELECT id, customer_id, recording_date, recording_time, status, file_path, duration_seconds, agent_id, created_at FROM vkyc_recordings WHERE id = 'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380b11';

-- Get recordings for a specific customer
SELECT id, customer_id, recording_date, recording_time, status, file_path, duration_seconds, agent_id, created_at FROM vkyc_recordings WHERE customer_id = 'CUST-001';

-- Get pending recordings
SELECT id, customer_id, recording_date, recording_time, status, file_path, duration_seconds, agent_id, created_at FROM vkyc_recordings WHERE status = 'pending' ORDER BY recording_date DESC, recording_time DESC;

-- Get recordings by agent and date range
SELECT id, customer_id, recording_date, recording_time, status, file_path, duration_seconds, agent_id, created_at
FROM vkyc_recordings
WHERE agent_id = 'AGENT-A' AND recording_date BETWEEN '2023-10-20' AND '2023-10-22';

-- UPDATE VKYC Recording
-- Update status of a recording
UPDATE vkyc_recordings SET status = 'approved' WHERE id = 'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380b12';

-- Update file path and duration
UPDATE vkyc_recordings SET file_path = '/recordings/archive/CUST-003_1_archived.mp4', duration_seconds = 115 WHERE customer_id = 'CUST-003';

-- DELETE VKYC Recording
DELETE FROM vkyc_recordings WHERE id = 'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380b14';
DELETE FROM vkyc_recordings WHERE customer_id = 'CUST-004' AND status = 'pending';

-- ====================================================================================================
-- AUDIT_LOGS TABLE CRUD
-- ====================================================================================================

-- CREATE Audit Log (using stored procedure for robust logging)
-- SELECT log_audit_event('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'admin_logout', 'user', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', '192.168.1.100'::inet);

-- READ Audit Logs
-- Get all audit logs
SELECT id, user_id, action, resource_type, resource_id, timestamp, ip_address FROM audit_logs ORDER BY timestamp DESC;

-- Get audit logs for a specific user
SELECT id, user_id, action, resource_type, resource_id, timestamp, ip_address FROM audit_logs WHERE user_id = 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11' ORDER BY timestamp DESC;

-- Get audit logs for a specific action type
SELECT id, user_id, action, resource_type, resource_id, timestamp, ip_address FROM audit_logs WHERE action = 'recording_view' ORDER BY timestamp DESC;

-- Get audit logs for a specific resource
SELECT id, user_id, action, resource_type, resource_id, timestamp, ip_address FROM audit_logs WHERE resource_type = 'vkyc_recording' AND resource_id = 'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380b11' ORDER BY timestamp DESC;

-- Get audit logs within a time range
SELECT id, user_id, action, resource_type, resource_id, timestamp, ip_address
FROM audit_logs
WHERE timestamp BETWEEN '2023-10-20 00:00:00+00' AND '2023-10-27 23:59:59+00'
ORDER BY timestamp DESC;

-- UPDATE Audit Log (Generally not recommended to update audit logs to maintain integrity)
-- If an update is absolutely necessary, it should be done with extreme caution and possibly logged itself.
-- Example (for demonstration, avoid in production unless critical):
-- UPDATE audit_logs SET action = 'user_login_failed' WHERE id = 'c0eebc99-9c0b-4ef8-bb6d-6bb9bd380c11';

-- DELETE Audit Log (Generally not recommended to delete audit logs, except for data retention policies)
-- Example (for demonstration, avoid in production unless critical for retention):
-- DELETE FROM audit_logs WHERE timestamp < NOW() - INTERVAL '1 year';