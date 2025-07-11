-- schema.sql
-- Defines the database schema for the V-KYC Recording Management System.
-- This script creates tables, defines relationships, and sets up constraints.

-- Enable UUID generation if not already enabled (for PostgreSQL 13+ it's often built-in,
-- but for older versions or explicit enablement, 'uuid-ossp' extension is common).
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp"; -- Uncomment if using uuid-ossp for gen_random_uuid()

-- Table: users
-- Stores user authentication and authorization details.
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL CHECK (role IN ('Team Lead', 'Process Manager', 'Administrator', 'Auditor')),
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE users IS 'Stores user authentication and authorization details.';
COMMENT ON COLUMN users.id IS 'Unique identifier for the user.';
COMMENT ON COLUMN users.username IS 'Unique username for login.';
COMMENT ON COLUMN users.password_hash IS 'Hashed password for security.';
COMMENT ON COLUMN users.role IS 'User role (e.g., Team Lead, Process Manager, Administrator, Auditor).';
COMMENT ON COLUMN users.email IS 'Unique email address for the user.';
COMMENT ON COLUMN users.created_at IS 'Timestamp when the user record was created.';

-- Table: vkyc_recordings
-- Stores metadata for V-KYC recordings, linking to the actual file location.
CREATE TABLE IF NOT EXISTS vkyc_recordings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vkyc_case_id VARCHAR(100) UNIQUE NOT NULL,
    customer_name VARCHAR(255) NOT NULL,
    recording_date DATE NOT NULL,
    duration_seconds INTEGER NOT NULL CHECK (duration_seconds > 0),
    file_path TEXT UNIQUE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'completed' CHECK (status IN ('completed', 'processing', 'failed', 'archived')),
    uploaded_by_user_id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata_json JSONB NULL, -- Stores additional flexible metadata
    CONSTRAINT fk_uploaded_by_user FOREIGN KEY (uploaded_by_user_id) REFERENCES users(id) ON DELETE RESTRICT
);

COMMENT ON TABLE vkyc_recordings IS 'Stores metadata for V-KYC recordings.';
COMMENT ON COLUMN vkyc_recordings.id IS 'Unique identifier for the V-KYC recording.';
COMMENT ON COLUMN vkyc_recordings.vkyc_case_id IS 'Unique identifier for the V-KYC case.';
COMMENT ON COLUMN vkyc_recordings.customer_name IS 'Name of the customer associated with the recording.';
COMMENT ON COLUMN vkyc_recordings.recording_date IS 'Date when the recording was made.';
COMMENT ON COLUMN vkyc_recordings.duration_seconds IS 'Duration of the recording in seconds.';
COMMENT ON COLUMN vkyc_recordings.file_path IS 'Path or URL to the actual recording file.';
COMMENT ON COLUMN vkyc_recordings.status IS 'Current status of the recording (e.g., completed, processing).';
COMMENT ON COLUMN vkyc_recordings.uploaded_by_user_id IS 'ID of the user who uploaded this recording.';
COMMENT ON COLUMN vkyc_recordings.created_at IS 'Timestamp when the recording metadata was created.';
COMMENT ON COLUMN vkyc_recordings.metadata_json IS 'JSONB field for flexible additional metadata.';

-- Table: audit_logs
-- Records all significant user actions for auditing purposes.
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    action VARCHAR(100) NOT NULL, -- e.g., 'CREATE', 'UPDATE', 'DELETE', 'LOGIN', 'LOGOUT', 'VIEW'
    resource_type VARCHAR(100) NOT NULL, -- e.g., 'user', 'vkyc_recording'
    resource_id UUID NULL, -- ID of the resource affected by the action (can be NULL for actions like login)
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ip_address INET NULL, -- IP address from which the action originated
    details JSONB NULL, -- Additional details about the action (e.g., old_value, new_value)
    CONSTRAINT fk_audit_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT
);

COMMENT ON TABLE audit_logs IS 'Records all significant user actions for auditing purposes.';
COMMENT ON COLUMN audit_logs.id IS 'Unique identifier for the audit log entry.';
COMMENT ON COLUMN audit_logs.user_id IS 'ID of the user who performed the action.';
COMMENT ON COLUMN audit_logs.action IS 'Type of action performed (e.g., CREATE, UPDATE, DELETE, LOGIN).';
COMMENT ON COLUMN audit_logs.resource_type IS 'Type of resource affected by the action (e.g., user, vkyc_recording).';
COMMENT ON COLUMN audit_logs.resource_id IS 'ID of the specific resource affected, if applicable.';
COMMENT ON COLUMN audit_logs.timestamp IS 'Timestamp when the action occurred.';
COMMENT ON COLUMN audit_logs.ip_address IS 'IP address from which the action originated.';
COMMENT ON COLUMN audit_logs.details IS 'JSONB field for additional details about the action.';

-- Add a function to automatically log changes to vkyc_recordings table
-- This is an example of an audit trigger, often used in conjunction with a dedicated audit table.
-- For simplicity, this example logs to the `audit_logs` table.
CREATE OR REPLACE FUNCTION log_vkyc_recording_changes()
RETURNS TRIGGER AS $$
DECLARE
    _user_id UUID;
    _action TEXT;
    _details JSONB;
BEGIN
    -- In a real application, the current user's ID would be passed via a session variable
    -- or retrieved from a connection context. For this example, we'll assume a placeholder
    -- or fetch from a temporary context.
    -- For demonstration, let's assume a 'system' user or a user ID passed via SET SESSION.
    -- SET SESSION "app.current_user_id" = 'your_user_id_here';
    BEGIN
        _user_id := current_setting('app.current_user_id', TRUE)::UUID;
    EXCEPTION
        WHEN OTHERS THEN
            -- Fallback if session variable is not set, e.g., use a default system user ID
            -- In a production system, you'd want to ensure this is always set.
            _user_id := (SELECT id FROM users WHERE username = 'system_auditor' LIMIT 1);
            IF _user_id IS NULL THEN
                RAISE EXCEPTION 'Audit trigger failed: app.current_user_id not set and system_auditor user not found.';
            END IF;
    END;

    IF TG_OP = 'INSERT' THEN
        _action := 'CREATE';
        _details := jsonb_build_object('new_data', to_jsonb(NEW));
    ELSIF TG_OP = 'UPDATE' THEN
        _action := 'UPDATE';
        _details := jsonb_build_object('old_data', to_jsonb(OLD), 'new_data', to_jsonb(NEW));
    ELSIF TG_OP = 'DELETE' THEN
        _action := 'DELETE';
        _details := jsonb_build_object('old_data', to_jsonb(OLD));
    END IF;

    INSERT INTO audit_logs (user_id, action, resource_type, resource_id, ip_address, details)
    VALUES (
        _user_id,
        _action,
        'vkyc_recording',
        COALESCE(NEW.id, OLD.id),
        inet_client_addr(), -- Captures the IP address of the client connection
        _details
    );

    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Create the trigger
CREATE TRIGGER vkyc_recording_audit_trigger
AFTER INSERT OR UPDATE OR DELETE ON vkyc_recordings
FOR EACH ROW EXECUTE FUNCTION log_vkyc_recording_changes();

COMMENT ON FUNCTION log_vkyc_recording_changes() IS 'Function to log changes to the vkyc_recordings table into audit_logs.';
COMMENT ON TRIGGER vkyc_recording_audit_trigger IS 'Trigger to automatically log INSERT, UPDATE, DELETE operations on vkyc_recordings.';

-- Note: For a comprehensive audit trail, similar triggers could be added to other tables (e.g., users).
-- For user login/logout, the audit log entry would typically be created by the application logic.