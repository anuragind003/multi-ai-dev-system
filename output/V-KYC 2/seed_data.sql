-- seed_data.sql
-- Provides initial seed data for development and testing environments.
-- Uses uuid_generate_v4() for IDs to match schema.

-- Insert sample users
INSERT INTO users (id, username, password_hash, email, role) VALUES
    ('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'admin_user', 'hashed_admin_password_123', 'admin@example.com', 'Admin'),
    ('b1c2d3e4-f5a6-7b8c-9d0e-1f2a3b4c5d6e', 'team_lead_alpha', 'hashed_lead_password_456', 'lead.alpha@example.com', 'Team Lead'),
    ('c7d8e9f0-a1b2-c3d4-e5f6-a7b8c9d0e1f2', 'process_mgr_beta', 'hashed_manager_password_789', 'manager.beta@example.com', 'Process Manager'),
    ('d3e4f5a6-b7c8-d9e0-f1a2-b3c4d5e6f7a8', 'uploader_gamma', 'hashed_uploader_password_012', 'uploader.gamma@example.com', 'Team Lead');

-- Insert sample recordings
INSERT INTO recordings (id, vkyc_id, customer_name, recording_date, duration_seconds, file_name, storage_path, uploaded_by_user_id, status) VALUES
    ('e0f1a2b3-c4d5-e6f7-a8b9-c0d1e2f3a4b5', 'ABC123456', 'Alice Smith', '2023-01-15', 300, 'alice_smith_vkyc.mp4', '/recordings/2023/01/alice_smith_vkyc.mp4', 'b1c2d3e4-f5a6-7b8c-9d0e-1f2a3b4c5d6e', 'available'),
    ('f6a7b8c9-d0e1-f2a3-b4c5-d6e7f8a9b0c1', 'XYZ987654', 'Bob Johnson', '2023-01-16', 450, 'bob_johnson_vkyc.mov', '/recordings/2023/01/bob_johnson_vkyc.mov', 'd3e4f5a6-b7c8-d9e0-f1a2-b3c4d5e6f7a8', 'processing'),
    ('1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d', 'PQR112233', 'Charlie Brown', '2023-02-01', 280, 'charlie_brown_vkyc.mp4', '/recordings/2023/02/charlie_brown_vkyc.mp4', 'b1c2d3e4-f5a6-7b8c-9d0e-1f2a3b4c5d6e', 'archived'),
    ('2e3f4a5b-6c7d-8e9f-0a1b-2c3d4e5f6a7b', 'MNO445566', 'Diana Prince', '2023-02-05', 500, 'diana_prince_vkyc.webm', '/recordings/2023/02/diana_prince_vkyc.webm', 'd3e4f5a6-b7c8-d9e0-f1a2-b3c4d5e6f7a8', 'available');

-- Insert sample audit logs
INSERT INTO audit_logs (id, user_id, action, recording_id, ip_address, details) VALUES
    ('3f4a5b6c-7d8e-9f0a-1b2c-3d4e5f6a7b8c', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'user_login', NULL, '192.168.1.100', '{"status": "success"}'),
    ('4a5b6c7d-8e9f-0a1b-2c3d-4e5f6a7b8c9d', 'b1c2d3e4-f5a6-7b8c-9d0e-1f2a3b4c5d6e', 'recording_uploaded', 'e0f1a2b3-c4d5-e6f7-a8b9-c0d1e2f3a4b5', '192.168.1.101', '{"file_size_mb": 50.5}'),
    ('5b6c7d8e-9f0a-1b2c-3d4e-5f6a7b8c9d0e', 'd3e4f5a6-b7c8-d9e0-f1a2-b3c4d5e6f7a8', 'recording_uploaded', 'f6a7b8c9-d0e1-f2a3-b4c5-d6e7f8a9b0c1', '192.168.1.102', '{"file_size_mb": 75.2}'),
    ('6c7d8e9f-0a1b-2c3d-4e5f-6a7b8c9d0e1f', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'user_role_updated', 'b1c2d3e4-f5a6-7b8c-9d0e-1f2a3b4c5d6e', '192.168.1.100', '{"old_role": "Team Lead", "new_role": "Admin"}'),
    ('7d8e9f0a-1b2c-3d4e-5f6a-7b8c9d0e1f2a', 'b1c2d3e4-f5a6-7b8c-9d0e-1f2a3b4c5d6e', 'recording_status_updated', 'e0f1a2b3-c4d5-e6f7-a8b9-c0d1e2f3a4b5', '192.168.1.101', '{"old_status": "available", "new_status": "processing"}');

-- Note: Password hashes are placeholders. In a real application, use strong hashing (e.g., bcrypt).
-- UUIDs are hardcoded for reproducibility in seeding, but uuid_generate_v4() is used by default in schema.