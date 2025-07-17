-- seed_data.sql
-- Inserts initial data for development and testing purposes.
-- Ensure UUIDs are generated or provided if not using gen_random_uuid() default.

-- Insert sample users
INSERT INTO users (id, username, password_hash, email, role) VALUES
    ('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'admin_user', 'hashed_admin_password_123', 'admin@example.com', 'admin'),
    ('b1c2d3e4-f5a6-7890-1234-567890abcdef', 'agent_alpha', 'hashed_agent_password_456', 'agent.alpha@example.com', 'agent'),
    ('c2d3e4f5-a6b7-8901-2345-67890abcdef0', 'test_user', 'hashed_user_password_789', 'user@example.com', 'user')
ON CONFLICT (username) DO NOTHING; -- Prevents errors if data already exists

-- Insert sample VKYC recordings
INSERT INTO vkyc_recordings (id, customer_id, recording_date, recording_time, status, file_path, duration_seconds, agent_id) VALUES
    ('d3e4f5a6-b7c8-9012-3456-7890abcdef01', 'CUST-001', '2023-10-20', '10:30:00', 'approved', 's3://vkyc-recordings/cust001_20231020.mp4', 120, 'agent_alpha'),
    ('e4f5a6b7-c8d9-0123-4567-890abcdef012', 'CUST-002', '2023-10-21', '11:00:00', 'pending', 's3://vkyc-recordings/cust002_20231021.mp4', 180, 'agent_alpha'),
    ('f5a6b7c8-d9e0-1234-5678-90abcdef0123', 'CUST-003', '2023-10-22', '14:15:00', 'rejected', 's3://vkyc-recordings/cust003_20231022.mp4', 90, 'agent_beta')
ON CONFLICT (id) DO NOTHING;

-- Insert sample audit logs
-- Ensure user_id and resource_id match existing IDs from above or are valid UUIDs
INSERT INTO audit_logs (user_id, action, resource_type, resource_id, ip_address) VALUES
    ('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'login', 'user', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', '192.168.1.1'::INET),
    ('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'update_vkyc_status', 'vkyc_recording', 'd3e4f5a6-b7c8-9012-3456-7890abcdef01', '192.168.1.1'::INET),
    ('b1c2d3e4-f5a6-7890-1234-567890abcdef', 'view_recording', 'vkyc_recording', 'e4f5a6b7-c8d9-0123-4567-890abcdef012', '10.0.0.5'::INET),
    ('c2d3e4f5-a6b7-8901-2345-67890abcdef0', 'logout', 'user', 'c2d3e4f5-a6b7-8901-2345-67890abcdef0', '172.16.0.10'::INET)
ON CONFLICT (id) DO NOTHING;

-- Use the stored procedure to log an event
-- This requires the stored procedure to be created first.
-- SELECT log_audit_event('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'system_startup', NULL, NULL, '127.0.0.1'::INET);