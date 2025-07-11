-- crud_queries.sql
-- Provides basic CRUD (Create, Read, Update, Delete) query templates
-- for each table in the VKYC Recordings database.
-- These templates use placeholders for parameters, which should be replaced
-- with actual values when executed via a database client or ORM.

-- --- USERS TABLE ---

-- CREATE User
-- Note: password_hash should be a securely hashed password.
-- Use uuid_generate_v4() for 'id' if not provided by application.
INSERT INTO users (id, username, password_hash, role, email)
VALUES (uuid_generate_v4(), 'new_user_name', 'hashed_password_string', 'Team Lead', 'new.user@example.com');

-- READ Users
-- Select all users
SELECT id, username, role, email, created_at FROM users;
-- Select user by ID
SELECT id, username, role, email, created_at FROM users WHERE id = 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11';
-- Select user by username
SELECT id, username, role, email, created_at FROM users WHERE username = 'admin_user';
-- Select users by role
SELECT id, username, role, email, created_at FROM users WHERE role = 'Process Manager';

-- UPDATE User
-- Update user role and email by ID
UPDATE users
SET role = 'Administrator', email = 'updated.admin@example.com'
WHERE id = 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11';
-- Update password hash (e.g., after a password reset)
UPDATE users
SET password_hash = 'new_hashed_password_string'
WHERE username = 'admin_user';

-- DELETE User
-- Delete user by ID
DELETE FROM users WHERE id = 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11';
-- Note: Deleting a user with associated vkyc_recordings will fail due to ON DELETE RESTRICT.
-- Deleting a user will CASCADE delete their audit_logs.


-- --- VKYC_RECORDINGS TABLE ---

-- CREATE VKYC Recording
-- Use uuid_generate_v4() for 'id' if not provided by application.
INSERT INTO vkyc_recordings (id, vkyc_case_id, customer_name, recording_date, duration_seconds, file_path, status, uploaded_by_user_id, metadata_json)
VALUES (
    uuid_generate_v4(),
    'VKYC-20231101-001',
    'John Doe',
    '2023-11-01',
    360,
    '/recordings/2023/11/VKYC-20231101-001.mp4',
    'completed',
    'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22', -- Must be an existing user ID
    '{"agent_name": "AgentX", "branch": "Main", "language": "English"}'::jsonb
);

-- READ VKYC Recordings
-- Select all recordings
SELECT * FROM vkyc_recordings;
-- Select recording by ID
SELECT * FROM vkyc_recordings WHERE id = 'd0eebc99-9c0b-4ef8-bb6d-6bb9bd380a44';
-- Select recording by VKYC case ID
SELECT * FROM vkyc_recordings WHERE vkyc_case_id = 'VKYC-20231026-001';
-- Select recordings by customer name (case-insensitive search)
SELECT * FROM vkyc_recordings WHERE customer_name ILIKE '%Alice%';
-- Select recordings by date range
SELECT * FROM vkyc_recordings WHERE recording_date BETWEEN '2023-10-26' AND '2023-10-27';
-- Select recordings by status
SELECT * FROM vkyc_recordings WHERE status = 'reviewed';
-- Select recordings uploaded by a specific user (join with users table)
SELECT vr.*, u.username AS uploaded_by_username
FROM vkyc_recordings vr
JOIN users u ON vr.uploaded_by_user_id = u.id
WHERE u.username = 'teamlead_alpha';
-- Select recordings with specific metadata (using JSONB operators)
SELECT * FROM vkyc_recordings WHERE metadata_json @> '{"region": "APAC"}';

-- UPDATE VKYC Recording
-- Update status and metadata for a recording by ID
UPDATE vkyc_recordings
SET
    status = 'reviewed',
    metadata_json = jsonb_set(metadata_json, '{review_notes}', '"Approved by Manager"', true)
WHERE id = 'd0eebc99-9c0b-4ef8-bb6d-6bb9bd380a44';
-- Update file path
UPDATE vkyc_recordings
SET file_path = '/new_path/VKYC-20231026-001_v2.mp4'
WHERE vkyc_case_id = 'VKYC-20231026-001';

-- DELETE VKYC Recording
-- Delete recording by ID
DELETE FROM vkyc_recordings WHERE id = 'f0eebc99-9c0b-4ef8-bb6d-6bb9bd380a66';


-- --- AUDIT_LOGS TABLE ---

-- CREATE Audit Log
-- Use uuid_generate_v4() for 'id' if not provided by application.
INSERT INTO audit_logs (id, user_id, action, resource_type, resource_id, ip_address, details)
VALUES (
    uuid_generate_v4(),
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', -- Must be an existing user ID
    'UPDATE',
    'VKYC_RECORDING',
    'd0eebc99-9c0b-4ef8-bb6d-6bb9bd380a44', -- Optional: ID of the resource affected
    '192.168.1.105',
    '{"field_changed": "status", "old_value": "completed", "new_value": "pending_review"}'::jsonb
);

-- READ Audit Logs
-- Select all audit logs
SELECT * FROM audit_logs;
-- Select audit logs by user ID
SELECT * FROM audit_logs WHERE user_id = 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11';
-- Select audit logs by action type
SELECT * FROM audit_logs WHERE action = 'CREATE';
-- Select audit logs for a specific resource
SELECT * FROM audit_logs WHERE resource_type = 'VKYC_RECORDING' AND resource_id = 'd0eebc99-9c0b-4ef8-bb6d-6bb9bd380a44';
-- Select audit logs within a time range
SELECT * FROM audit_logs WHERE timestamp BETWEEN '2023-10-26 00:00:00+00' AND '2023-10-27 23:59:59+00';
-- Select audit logs with specific details (using JSONB operators)
SELECT * FROM audit_logs WHERE details @> '{"field_changed": "status"}';

-- UPDATE Audit Log (Generally not recommended for audit logs, but for completeness)
-- Audit logs are typically append-only. Updates should be rare and themselves audited.
UPDATE audit_logs
SET details = jsonb_set(details, '{correction}', '"Corrected IP address"', true)
WHERE id = 'some_audit_log_id';

-- DELETE Audit Log (Generally not recommended for audit logs, but for completeness)
-- Deleting audit logs should be restricted and only for specific data retention policies.
DELETE FROM audit_logs WHERE timestamp < (CURRENT_TIMESTAMP - INTERVAL '5 years');