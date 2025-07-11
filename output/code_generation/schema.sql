-- schema.sql
-- Defines the database schema for the VKYC portal, including tables, relationships, and constraints.

-- Enable UUID generation if not already enabled (for PostgreSQL 13+ gen_random_uuid() is built-in)
-- For older versions, you might need: CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table: users
-- Stores user accounts for the VKYC portal.
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'user', -- e.g., 'admin', 'user', 'agent'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE users IS 'Stores user accounts for the VKYC portal.';
COMMENT ON COLUMN users.id IS 'Unique identifier for the user.';
COMMENT ON COLUMN users.username IS 'Unique username for login.';
COMMENT ON COLUMN users.password_hash IS 'Hashed password for security.';
COMMENT ON COLUMN users.email IS 'Unique email address for the user.';
COMMENT ON COLUMN users.role IS 'Role of the user (e.g., admin, user, agent).';
COMMENT ON COLUMN users.created_at IS 'Timestamp when the user account was created.';
COMMENT ON COLUMN users.updated_at IS 'Timestamp when the user account was last updated.';

-- Table: vkyc_recordings
-- Stores metadata for each V-KYC recording.
CREATE TABLE IF NOT EXISTS vkyc_recordings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id VARCHAR(255) NOT NULL,
    recording_date DATE NOT NULL,
    recording_time TIME NOT NULL,
    status VARCHAR(50) NOT NULL, -- e.g., 'pending', 'approved', 'rejected', 'in_progress'
    file_path TEXT NOT NULL, -- S3 path or local file system path
    duration_seconds INTEGER,
    agent_id VARCHAR(255), -- Identifier for the agent who conducted the recording
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE vkyc_recordings IS 'Stores metadata for each V-KYC recording.';
COMMENT ON COLUMN vkyc_recordings.id IS 'Unique identifier for the V-KYC recording.';
COMMENT ON COLUMN vkyc_recordings.customer_id IS 'Identifier for the customer associated with the recording.';
COMMENT ON COLUMN vkyc_recordings.recording_date IS 'Date when the recording was made.';
COMMENT ON COLUMN vkyc_recordings.recording_time IS 'Time when the recording was made.';
COMMENT ON COLUMN vkyc_recordings.status IS 'Current status of the V-KYC recording.';
COMMENT ON COLUMN vkyc_recordings.file_path IS 'Path to the stored recording file.';
COMMENT ON COLUMN vkyc_recordings.duration_seconds IS 'Duration of the recording in seconds.';
COMMENT ON COLUMN vkyc_recordings.agent_id IS 'Identifier of the agent who performed the V-KYC.';
COMMENT ON COLUMN vkyc_recordings.created_at IS 'Timestamp when the recording metadata was created.';

-- Table: audit_logs
-- Records user actions for auditing purposes.
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    action VARCHAR(255) NOT NULL, -- e.g., 'login', 'logout', 'create_user', 'update_recording_status'
    resource_type VARCHAR(255), -- e.g., 'user', 'vkyc_recording'
    resource_id UUID, -- ID of the resource affected by the action
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ip_address INET, -- IP address from which the action originated
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT -- Prevent deleting users with associated audit logs
);

COMMENT ON TABLE audit_logs IS 'Records user actions for auditing purposes.';
COMMENT ON COLUMN audit_logs.id IS 'Unique identifier for the audit log entry.';
COMMENT ON COLUMN audit_logs.user_id IS 'ID of the user who performed the action.';
COMMENT ON COLUMN audit_logs.action IS 'Description of the action performed.';
COMMENT ON COLUMN audit_logs.resource_type IS 'Type of resource affected by the action (e.g., user, vkyc_recording).';
COMMENT ON COLUMN audit_logs.resource_id IS 'ID of the specific resource affected by the action.';
COMMENT ON COLUMN audit_logs.timestamp IS 'Timestamp when the action occurred.';
COMMENT ON COLUMN audit_logs.ip_address IS 'IP address from which the action originated.';

-- Add a trigger to automatically update `updated_at` column for the `users` table
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();