-- seed_data.sql
-- Populates the database with initial data for development and testing purposes.
-- This script should be run after the schema has been created.

-- Insert sample users
-- Passwords are 'password123' hashed with a placeholder hash function.
-- In a real application, use a strong hashing algorithm like bcrypt.
INSERT INTO users (id, username, password_hash, role, email) VALUES
('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'admin_user', '$2a$10$abcdefghijklmnopqrstuvwxyza.abcdefghijklmno.abcdefghijklmno', 'Administrator', 'admin@example.com'),
('b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a12', 'team_lead_1', '$2a$10$abcdefghijklmnopqrstuvwxyza.abcdefghijklmno.abcdefghijklmno', 'Team Lead', 'teamlead1@example.com'),
('c0eebc99-9c0b-4ef8-bb6d-6bb9bd380a13', 'process_mgr_1', '$2a$10$abcdefghijklmnopqrstuvwxyza.abcdefghijklmno.abcdefghijklmno', 'Process Manager', 'processmgr1@example.com'),
('d0eebc99-9c0b-4ef8-bb6d-6bb9bd380a14', 'auditor_user', '$2a$10$abcdefghijklmnopqrstuvwxyza.abcdefghijklmno.abcdefghijklmno', 'Auditor', 'auditor@example.com'),
('e0eebc99-9c0b-4ef8-bb6d-6bb9bd380a15', 'system_auditor', '$2a$10$abcdefghijklmnopqrstuvwxyza.abcdefghijklmno.abcdefghijklmno', 'Administrator', 'system@example.com')
ON CONFLICT (id) DO NOTHING;

-- Insert sample V-KYC recordings
INSERT INTO vkyc_recordings (id, vkyc_case_id, customer_name, recording_date, duration_seconds, file_path, status, uploaded_by_user_id, metadata_json) VALUES
('f0eebc99-9c0b-4ef8-bb6d-6bb9bd380a16', 'VKYC-001-20231026', 'Alice Smith', '2023-10-26', 300, '/recordings/alice_smith_001.mp4', 'completed', 'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a12', '{"agent_id": "AGNT-001", "resolution": "1080p"}'),
('g0eebc99-9c0b-4ef8-bb6d-6bb9bd380a17', 'VKYC-002-20231027', 'Bob Johnson', '2023-10-27', 450, '/recordings/bob_johnson_002.mp4', 'completed', 'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a12', '{"agent_id": "AGNT-002", "resolution": "720p"}'),
('h0eebc99-9c0b-4ef8-bb6d-6bb9bd380a18', 'VKYC-003-20231027', 'Charlie Brown', '2023-10-27', 280, '/recordings/charlie_brown_003.mp4', 'processing', 'c0eebc99-9c0b-4ef8-bb6d-6bb9bd380a13', '{"agent_id": "AGNT-003", "notes": "Requires review"}')
ON CONFLICT (id) DO NOTHING;

-- Insert sample audit logs (manual entries, trigger will add more automatically)
-- Example: Admin user logs in
SELECT log_audit_event(
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', -- admin_user
    'LOGIN',
    'user_session',
    NULL, -- No specific resource ID for login
    '192.168.1.100'::INET,
    jsonb_build_object('message', 'Successful login')
);

-- Example: Team Lead views a recording
SELECT log_audit_event(
    'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a12', -- team_lead_1
    'VIEW',
    'vkyc_recording',
    'f0eebc99-9c0b-4ef8-bb6d-6bb9bd380a16', -- Alice Smith's recording
    '192.168.1.101'::INET,
    jsonb_build_object('view_type', 'full_playback')
);

-- Example: Process Manager updates a recording status (this would also trigger the audit trigger)
-- To demonstrate the trigger, we'll do a direct update here.
-- First, set the session variable for the trigger to pick up the user.
SET SESSION "app.current_user_id" = 'c0eebc99-9c0b-4ef8-bb6d-6bb9bd380a13'; -- process_mgr_1

UPDATE vkyc_recordings
SET status = 'completed', metadata_json = jsonb_set(metadata_json, '{notes}', '"Reviewed and approved"')
WHERE id = 'h0eebc99-9c0b-4ef8-bb6d-6bb9bd380a18';

RESET SESSION "app.current_user_id"; -- Reset session variable

-- Example: Auditor views audit logs
SELECT log_audit_event(
    'd0eebc99-9c0b-4ef8-bb6d-6bb9bd380a14', -- auditor_user
    'VIEW',
    'audit_logs',
    NULL,
    '192.168.1.102'::INET,
    jsonb_build_object('filter', 'all_events')
);

-- Note: The `log_vkyc_recording_changes` trigger will automatically add audit entries
-- for INSERT/UPDATE/DELETE operations on `vkyc_recordings` table.
-- Ensure the `system_auditor` user exists or `app.current_user_id` is set for triggers to work.