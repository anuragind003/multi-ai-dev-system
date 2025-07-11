-- schema.sql
-- Defines the database schema for users, VKYC recordings, and audit logs.
-- Includes table definitions, relationships, constraints, and custom types.

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Custom ENUM types for roles and actions
-- Role for users
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_role_enum') THEN
        CREATE TYPE user_role_enum AS ENUM ('admin', 'auditor', 'viewer');
    END IF;
END $$;

-- Action types for audit logs
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'audit_action_enum') THEN
        CREATE TYPE audit_action_enum AS ENUM ('login', 'view_recording_metadata', 'download_recording', 'user_created', 'user_updated', 'user_deleted', 'recording_uploaded', 'recording_status_updated');
    END IF;
END $$;

-- Status for VKYC recordings
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'recording_status_enum') THEN
        CREATE TYPE recording_status_enum AS ENUM ('pending_upload', 'uploaded', 'processing', 'completed', 'failed', 'archived');
    END IF;
END $$;


-- 2. Table: users
-- Stores user accounts for the VKYC team with their roles.
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role user_role_enum NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

COMMENT ON TABLE users IS 'Stores user accounts for the VKYC team with their roles.';
COMMENT ON COLUMN users.id IS 'Unique identifier for the user.';
COMMENT ON COLUMN users.username IS 'Unique username for login.';
COMMENT ON COLUMN users.password_hash IS 'Hashed password for security.';
COMMENT ON COLUMN users.role IS 'Role of the user (admin, auditor, viewer).';
COMMENT ON COLUMN users.created_at IS 'Timestamp when the user account was created.';
COMMENT ON COLUMN users.updated_at IS 'Timestamp when the user account was last updated.';

-- 3. Table: vkyc_recordings
-- Stores metadata about each V-KYC recording.
CREATE TABLE IF NOT EXISTS vkyc_recordings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id VARCHAR(255) NOT NULL,
    recording_name VARCHAR(255) NOT NULL,
    recording_path TEXT UNIQUE NOT NULL, -- Path/key in object storage
    duration_seconds INTEGER,
    recording_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    status recording_status_enum NOT NULL DEFAULT 'uploaded', -- Default status upon initial upload
    uploaded_by UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,

    CONSTRAINT fk_uploaded_by FOREIGN KEY (uploaded_by) REFERENCES users(id) ON DELETE RESTRICT,
    CONSTRAINT chk_duration_positive CHECK (duration_seconds IS NULL OR duration_seconds >= 0)
);

COMMENT ON TABLE vkyc_recordings IS 'Stores metadata about each V-KYC recording.';
COMMENT ON COLUMN vkyc_recordings.id IS 'Unique identifier for the recording.';
COMMENT ON COLUMN vkyc_recordings.customer_id IS 'Identifier for the customer associated with the recording.';
COMMENT ON COLUMN vkyc_recordings.recording_name IS 'Display name of the recording.';
COMMENT ON COLUMN vkyc_recordings.recording_path IS 'Path or key in object storage where the recording file is stored.';
COMMENT ON COLUMN vkyc_recordings.duration_seconds IS 'Duration of the recording in seconds.';
COMMENT ON COLUMN vkyc_recordings.recording_timestamp IS 'Timestamp when the V-KYC recording was originally made.';
COMMENT ON COLUMN vkyc_recordings.status IS 'Current status of the recording (e.g., uploaded, processing, completed, failed).';
COMMENT ON COLUMN vkyc_recordings.uploaded_by IS 'ID of the user who uploaded or initiated the recording entry.';
COMMENT ON COLUMN vkyc_recordings.created_at IS 'Timestamp when the recording metadata was created in the database.';

-- 4. Table: audit_logs
-- Records all significant user actions, especially access and download of recordings.
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    action audit_action_enum NOT NULL,
    resource_id UUID, -- Can be NULL if action is not resource-specific (e.g., login)
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45), -- Supports IPv4 and IPv6
    details JSONB, -- Additional context for the action (e.g., old_value, new_value for updates)

    CONSTRAINT fk_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT,
    CONSTRAINT fk_resource_id FOREIGN KEY (resource_id) REFERENCES vkyc_recordings(id) ON DELETE SET NULL -- If recording is deleted, log remains but resource_id is null
);

COMMENT ON TABLE audit_logs IS 'Records all significant user actions, especially access and download of recordings.';
COMMENT ON COLUMN audit_logs.id IS 'Unique identifier for the audit log entry.';
COMMENT ON COLUMN audit_logs.user_id IS 'ID of the user who performed the action.';
COMMENT ON COLUMN audit_logs.action IS 'Type of action performed (e.g., login, view_recording_metadata, download_recording).';
COMMENT ON COLUMN audit_logs.resource_id IS 'ID of the resource affected by the action (e.g., vkyc_recording ID). Nullable for non-resource specific actions.';
COMMENT ON COLUMN audit_logs.timestamp IS 'Timestamp when the action occurred.';
COMMENT ON COLUMN audit_logs.ip_address IS 'IP address from which the action was performed.';
COMMENT ON COLUMN audit_logs.details IS 'Additional context for the action in JSONB format (e.g., success/failure, specific parameters).';

-- 5. Trigger function to update 'updated_at' column automatically
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 6. Apply trigger to 'users' table
DROP TRIGGER IF EXISTS set_updated_at ON users;
CREATE TRIGGER set_updated_at
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Note: No 'updated_at' for vkyc_recordings or audit_logs as per schema,
-- but if needed, similar triggers can be added.
-- Audit logs should generally be immutable after creation.