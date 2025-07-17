-- db/seed_data.sql
-- This file contains SQL statements to populate the database with initial seed data
-- for development and testing purposes.
-- Ensure UUIDs are generated using gen_random_uuid() for consistency with schema.

-- Seed data for 'users' table
INSERT INTO users (username, password_hash, email, role) VALUES
('admin_user', '$2b$12$EXAMPLEHASHFORADMINUSER1234567890123456789012345678901234567890', 'admin@example.com', 'admin'),
('john_doe', '$2b$12$EXAMPLEHASHFORJOHNDOE1234567890123456789012345678901234567890', 'john.doe@example.com', 'user'),
('jane_smith', '$2b$12$EXAMPLEHASHFORJANESMITH1234567890123456789012345678901234567890', 'jane.smith@example.com', 'auditor')
ON CONFLICT (username) DO NOTHING; -- Prevents re-inserting on subsequent runs

-- Retrieve user IDs for foreign key references
DO $$
DECLARE
    admin_user_id UUID;
    john_doe_id UUID;
    jane_smith_id UUID;
BEGIN
    SELECT id INTO admin_user_id FROM users WHERE username = 'admin_user';
    SELECT id INTO john_doe_id FROM users WHERE username = 'john_doe';
    SELECT id INTO jane_smith_id FROM users WHERE username = 'jane_smith';

    -- Seed data for 'vkyc_recordings' table
    INSERT INTO vkyc_recordings (customer_id, recording_date, recording_time, status, file_path, duration_seconds, agent_id) VALUES
    ('CUST001', '2023-10-20', '10:30:00', 'APPROVED', '/recordings/2023/10/CUST001_1030.mp4', 120, 'AGENT001'),
    ('CUST002', '2023-10-20', '11:00:00', 'PENDING', '/recordings/2023/10/CUST002_1100.mp4', 180, 'AGENT002'),
    ('CUST003', '2023-10-21', '09:15:00', 'REJECTED', '/recordings/2023/10/CUST003_0915.mp4', 90, 'AGENT001'),
    ('CUST004', '2023-10-21', '14:00:00', 'REVIEW_REQUIRED', '/recordings/2023/10/CUST004_1400.mp4', 240, 'AGENT003'),
    ('CUST005', '2023-10-22', '16:45:00', 'APPROVED', '/recordings/2023/10/CUST005_1645.mp4', 150, 'AGENT002')
    ON CONFLICT (id) DO NOTHING; -- Assuming UUIDs are generated, this might not be strictly needed if gen_random_uuid() is used

    -- Seed data for 'audit_logs' table
    -- Use the retrieved user IDs
    IF admin_user_id IS NOT NULL THEN
        INSERT INTO audit_logs (user_id, action, resource_type, resource_id, ip_address) VALUES
        (admin_user_id, 'LOGIN', 'USER', admin_user_id, '192.168.1.10'),
        (admin_user_id, 'CREATE_RECORDING', 'VKYC_RECORDING', (SELECT id FROM vkyc_recordings WHERE customer_id = 'CUST001'), '192.168.1.10'),
        (admin_user_id, 'UPDATE_STATUS', 'VKYC_RECORDING', (SELECT id FROM vkyc_recordings WHERE customer_id = 'CUST002'), '192.168.1.10');
    END IF;

    IF john_doe_id IS NOT NULL THEN
        INSERT INTO audit_logs (user_id, action, resource_type, resource_id, ip_address) VALUES
        (john_doe_id, 'LOGIN', 'USER', john_doe_id, '10.0.0.5'),
        (john_doe_id, 'VIEW_RECORDING', 'VKYC_RECORDING', (SELECT id FROM vkyc_recordings WHERE customer_id = 'CUST001'), '10.0.0.5');
    END IF;

    IF jane_smith_id IS NOT NULL THEN
        INSERT INTO audit_logs (user_id, action, resource_type, resource_id, ip_address) VALUES
        (jane_smith_id, 'LOGIN', 'USER', jane_smith_id, '172.16.0.1'),
        (jane_smith_id, 'REVIEW_RECORDING', 'VKYC_RECORDING', (SELECT id FROM vkyc_recordings WHERE customer_id = 'CUST004'), '172.16.0.1');
    END IF;

END $$;

-- Informative message
SELECT 'Seed data inserted successfully.' AS status;