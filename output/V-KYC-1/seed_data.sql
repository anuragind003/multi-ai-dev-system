-- seed_data.sql
-- Provides initial data for development and testing environments.
-- Uses fixed UUIDs for predictability in testing.

-- Ensure UUID extension is enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Clear existing data (optional, for clean re-seeding)
TRUNCATE TABLE audit_logs RESTART IDENTITY CASCADE;
TRUNCATE TABLE vkyc_recordings RESTART IDENTITY CASCADE;
TRUNCATE TABLE users RESTART IDENTITY CASCADE;

-- Insert sample users
INSERT INTO users (id, username, password_hash, role) VALUES
('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'admin_user', 'hashed_password_admin_123', 'admin'),
('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a12', 'auditor_user', 'hashed_password_auditor_456', 'auditor'),
('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a13', 'viewer_user', 'hashed_password_viewer_789', 'viewer');

-- Insert sample VKYC recordings
INSERT INTO vkyc_recordings (id, customer_id, recording_name, recording_path, duration_seconds, recording_timestamp, status, uploaded_by) VALUES
('b0eebc99-9c0b-4ef8-bb6d-6bb9bd380b11', 'CUST001', 'KYC_Recording_CUST001_20231026', 's3://vkyc-recordings/CUST001/rec_20231026_001.mp4', 300, '2023-10-26 10:00:00+00', 'completed', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11'),
('b0eebc99-9c0b-4ef8-bb6d-6bb9bd380b12', 'CUST002', 'KYC_Recording_CUST002_20231027', 's3://vkyc-recordings/CUST002/rec_20231027_002.mp4', 450, '2023-10-27 11:30:00+00', 'uploaded', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a13'),
('b0eebc99-9c0b-4ef8-bb6d-6bb9bd380b13', 'CUST003', 'KYC_Recording_CUST003_20231027_Failed', 's3://vkyc-recordings/CUST003/rec_20231027_003.mp4', 200, '2023-10-27 14:00:00+00', 'failed', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11');

-- Insert sample audit logs
-- Using the log_audit_event function for consistency
SELECT log_audit_event(
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', -- admin_user
    'login',
    NULL,
    '192.168.1.100',
    '{"status": "success", "method": "password"}'::jsonb
);

SELECT log_audit_event(
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a12', -- auditor_user
    'view_recording_metadata',
    'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380b11', -- CUST001 recording
    '192.168.1.101',
    '{"accessed_fields": ["customer_id", "recording_name"]}'::jsonb
);

SELECT log_audit_event(
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a12', -- auditor_user
    'download_recording',
    'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380b11', -- CUST001 recording
    '192.168.1.101',
    '{"download_size_mb": 50}'::jsonb
);

SELECT log_audit_event(
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a13', -- viewer_user
    'view_recording_metadata',
    'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380b12', -- CUST002 recording
    '192.168.1.102',
    '{"accessed_fields": ["recording_name", "status"]}'::jsonb
);

SELECT log_audit_event(
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', -- admin_user
    'user_created',
    NULL,
    '192.168.1.100',
    '{"new_user_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a14", "username": "new_user", "role": "viewer"}'::jsonb
);

SELECT log_audit_event(
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', -- admin_user
    'recording_uploaded',
    'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380b13', -- CUST003 recording
    '192.168.1.100',
    '{"file_size_bytes": 10240000}'::jsonb
);

SELECT update_recording_status_and_log(
    'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380b12', -- CUST002 recording
    'completed',
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', -- admin_user
    '192.168.1.100',
    '{"reason": "manual review"}'::jsonb
);

-- Verify data
SELECT 'Users Count', COUNT(*) FROM users;
SELECT 'Recordings Count', COUNT(*) FROM vkyc_recordings;
SELECT 'Audit Logs Count', COUNT(*) FROM audit_logs;