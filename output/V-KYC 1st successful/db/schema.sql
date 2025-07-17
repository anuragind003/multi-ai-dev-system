-- db/schema.sql
-- This file defines the complete PostgreSQL schema for the VKYC Recordings system.
-- It includes tables, their columns, data types, primary keys, foreign keys,
-- unique constraints, not null constraints, and default values.

-- Enable UUID generation if not already enabled (for gen_random_uuid())
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table: users
-- Stores user accounts for the VKYC portal.
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'user', -- e.g., 'admin', 'user', 'auditor'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Add a trigger to automatically update the 'updated_at' column for 'users' table
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER users_updated_at_trigger
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Table: vkyc_recordings
-- Stores metadata for each V-KYC recording.
CREATE TABLE IF NOT EXISTS vkyc_recordings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id VARCHAR(255) NOT NULL,
    recording_date DATE NOT NULL,
    recording_time TIME NOT NULL,
    status VARCHAR(50) NOT NULL, -- e.g., 'PENDING', 'APPROVED', 'REJECTED', 'REVIEW_REQUIRED'
    file_path TEXT NOT NULL, -- Path or URL to the actual recording file
    duration_seconds INTEGER,
    agent_id VARCHAR(255), -- Identifier for the agent who conducted the VKYC
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table: audit_logs
-- Records user actions for auditing purposes.
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    action VARCHAR(255) NOT NULL, -- e.g., 'LOGIN', 'CREATE_RECORDING', 'UPDATE_STATUS', 'VIEW_RECORDING'
    resource_type VARCHAR(255), -- e.g., 'VKYC_RECORDING', 'USER'
    resource_id UUID, -- ID of the resource affected by the action (e.g., vkyc_recordings.id)
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ip_address INET, -- IP address from which the action originated
    CONSTRAINT fk_user
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE -- If a user is deleted, their audit logs are also deleted.
);

-- Add comments to tables and columns for better documentation
COMMENT ON TABLE users IS 'Stores user accounts for the VKYC portal.';
COMMENT ON COLUMN users.id IS 'Unique identifier for the user.';
COMMENT ON COLUMN users.username IS 'Unique username for login.';
COMMENT ON COLUMN users.password_hash IS 'Hashed password for security.';
COMMENT ON COLUMN users.email IS 'Unique email address for the user.';
COMMENT ON COLUMN users.role IS 'User role (e.g., admin, user, auditor) for access control.';
COMMENT ON COLUMN users.created_at IS 'Timestamp when the user account was created.';
COMMENT ON COLUMN users.updated_at IS 'Timestamp when the user account was last updated.';

COMMENT ON TABLE vkyc_recordings IS 'Stores metadata for each V-KYC recording.';
COMMENT ON COLUMN vkyc_recordings.id IS 'Unique identifier for the VKYC recording.';
COMMENT ON COLUMN vkyc_recordings.customer_id IS 'Identifier for the customer associated with the recording.';
COMMENT ON COLUMN vkyc_recordings.recording_date IS 'Date when the VKYC recording was made.';
COMMENT ON COLUMN vkyc_recordings.recording_time IS 'Time when the VKYC recording was made.';
COMMENT ON COLUMN vkyc_recordings.status IS 'Current status of the VKYC recording (e.g., PENDING, APPROVED, REJECTED).';
COMMENT ON COLUMN vkyc_recordings.file_path IS 'Path or URL to the actual recording file storage.';
COMMENT ON COLUMN vkyc_recordings.duration_seconds IS 'Duration of the recording in seconds.';
COMMENT ON COLUMN vkyc_recordings.agent_id IS 'Identifier of the agent who conducted the VKYC.';
COMMENT ON COLUMN vkyc_recordings.created_at IS 'Timestamp when the recording metadata was created.';

COMMENT ON TABLE audit_logs IS 'Records user actions for auditing purposes.';
COMMENT ON COLUMN audit_logs.id IS 'Unique identifier for the audit log entry.';
COMMENT ON COLUMN audit_logs.user_id IS 'ID of the user who performed the action.';
COMMENT ON COLUMN audit_logs.action IS 'Description of the action performed (e.g., LOGIN, CREATE_RECORDING).';
COMMENT ON COLUMN audit_logs.resource_type IS 'Type of resource affected by the action (e.g., VKYC_RECORDING, USER).';
COMMENT ON COLUMN audit_logs.resource_id IS 'ID of the specific resource affected by the action.';
COMMENT ON COLUMN audit_logs.timestamp IS 'Timestamp when the action occurred.';
COMMENT ON COLUMN audit_logs.ip_address IS 'IP address from which the action originated.';