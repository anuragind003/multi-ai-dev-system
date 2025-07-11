-- schema.sql
-- Defines the database schema for users, recordings, and audit logs.
-- Includes tables, primary keys, foreign keys, unique constraints,
-- not null constraints, default values, and check constraints.

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table: users
-- Stores user authentication and authorization information.
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    role VARCHAR(50) NOT NULL CHECK (role IN ('Team Lead', 'Process Manager', 'Admin')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE users IS 'Stores user authentication and authorization information.';
COMMENT ON COLUMN users.id IS 'Unique identifier for the user.';
COMMENT ON COLUMN users.username IS 'Unique username for login.';
COMMENT ON COLUMN users.password_hash IS 'Hashed password for security.';
COMMENT ON COLUMN users.email IS 'Unique email address for the user.';
COMMENT ON COLUMN users.role IS 'User role (e.g., Team Lead, Process Manager, Admin) for access control.';
COMMENT ON COLUMN users.created_at IS 'Timestamp when the user account was created.';

-- Table: recordings
-- Stores metadata for each V-KYC recording.
CREATE TABLE IF NOT EXISTS recordings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vkyc_id VARCHAR(100) UNIQUE NOT NULL,
    customer_name VARCHAR(255) NOT NULL,
    recording_date DATE NOT NULL,
    duration_seconds INTEGER NOT NULL CHECK (duration_seconds > 0),
    file_name VARCHAR(255) NOT NULL,
    storage_path TEXT NOT NULL,
    uploaded_by_user_id UUID NOT NULL,
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'available' CHECK (status IN ('available', 'processing', 'archived', 'deleted', 'error')),
    CONSTRAINT fk_uploaded_by_user FOREIGN KEY (uploaded_by_user_id) REFERENCES users(id) ON DELETE RESTRICT
);

COMMENT ON TABLE recordings IS 'Stores metadata for each V-KYC recording.';
COMMENT ON COLUMN recordings.id IS 'Unique identifier for the recording.';
COMMENT ON COLUMN recordings.vkyc_id IS 'Unique V-KYC identifier for the recording.';
COMMENT ON COLUMN recordings.customer_name IS 'Name of the customer associated with the recording.';
COMMENT ON COLUMN recordings.recording_date IS 'Date when the recording was made.';
COMMENT ON COLUMN recordings.duration_seconds IS 'Duration of the recording in seconds.';
COMMENT ON COLUMN recordings.file_name IS 'Original file name of the recording.';
COMMENT ON COLUMN recordings.storage_path IS 'Path or URL where the recording file is stored.';
COMMENT ON COLUMN recordings.uploaded_by_user_id IS 'ID of the user who uploaded the recording.';
COMMENT ON COLUMN recordings.uploaded_at IS 'Timestamp when the recording metadata was uploaded.';
COMMENT ON COLUMN recordings.status IS 'Current status of the recording (e.g., available, processing, archived).';

-- Table: audit_logs
-- Records all significant user actions for auditing purposes.
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    action VARCHAR(100) NOT NULL,
    recording_id UUID, -- Optional: NULL if action is not related to a specific recording
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45), -- Supports IPv4 and IPv6
    details JSONB, -- Stores additional details about the action in JSON format
    CONSTRAINT fk_audit_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_audit_recording FOREIGN KEY (recording_id) REFERENCES recordings(id) ON DELETE SET NULL
);

COMMENT ON TABLE audit_logs IS 'Records all significant user actions for auditing purposes.';
COMMENT ON COLUMN audit_logs.id IS 'Unique identifier for the audit log entry.';
COMMENT ON COLUMN audit_logs.user_id IS 'ID of the user who performed the action.';
COMMENT ON COLUMN audit_logs.action IS 'Description of the action performed (e.g., "user_login", "recording_uploaded", "user_deleted").';
COMMENT ON COLUMN audit_logs.recording_id IS 'Optional: ID of the recording affected by the action.';
COMMENT ON COLUMN audit_logs.timestamp IS 'Timestamp when the action occurred.';
COMMENT ON COLUMN audit_logs.ip_address IS 'IP address from which the action was performed.';
COMMENT ON COLUMN audit_logs.details IS 'Additional details about the action in JSONB format.';

-- Add a trigger to ensure vkyc_id format (example of more complex validation)
-- This is also included in data_validation.sql for clarity, but can be part of schema.
CREATE OR REPLACE FUNCTION validate_vkyc_id_format()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.vkyc_id !~ '^[A-Z]{3}[0-9]{6}$' THEN
        RAISE EXCEPTION 'Invalid VKYC ID format. Must be 3 uppercase letters followed by 6 digits (e.g., ABC123456).';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_validate_vkyc_id ON recordings;
CREATE TRIGGER trg_validate_vkyc_id
BEFORE INSERT OR UPDATE ON recordings
FOR EACH ROW
EXECUTE FUNCTION validate_vkyc_id_format();