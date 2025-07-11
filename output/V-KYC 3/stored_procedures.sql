-- stored_procedures.sql
-- Contains PostgreSQL stored procedures and functions for common database operations,
-- enhancing security, performance, and data integrity.

-- Function: create_user
-- Creates a new user with a hashed password and logs the action.
-- In a real application, password hashing would happen in the application layer before calling this.
CREATE OR REPLACE FUNCTION create_user(
    p_username VARCHAR,
    p_password_hash VARCHAR,
    p_role VARCHAR,
    p_email VARCHAR,
    p_acting_user_id UUID DEFAULT NULL, -- User performing the action (for audit)
    p_ip_address INET DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    new_user_id UUID;
    system_auditor_id UUID;
BEGIN
    -- Validate role
    IF p_role NOT IN ('Team Lead', 'Process Manager', 'Administrator', 'Auditor') THEN
        RAISE EXCEPTION 'Invalid role specified: %', p_role;
    END IF;

    -- Insert new user
    INSERT INTO users (username, password_hash, role, email)
    VALUES (p_username, p_password_hash, p_role, p_email)
    RETURNING id INTO new_user_id;

    -- Log the action in audit_logs
    -- If p_acting_user_id is NULL, try to find a 'system_auditor' user
    IF p_acting_user_id IS NULL THEN
        SELECT id INTO system_auditor_id FROM users WHERE username = 'system_auditor' LIMIT 1;
        IF system_auditor_id IS NULL THEN
            RAISE WARNING 'System auditor user not found. Audit log for user creation might be incomplete.';
            p_acting_user_id := new_user_id; -- Fallback to the newly created user if no system auditor
        ELSE
            p_acting_user_id := system_auditor_id;
        END IF;
    END IF;

    INSERT INTO audit_logs (user_id, action, resource_type, resource_id, ip_address, details)
    VALUES (
        p_acting_user_id,
        'CREATE',
        'user',
        new_user_id,
        COALESCE(p_ip_address, inet_client_addr()),
        jsonb_build_object(
            'username', p_username,
            'role', p_role,
            'email', p_email
        )
    );

    RETURN new_user_id;
EXCEPTION
    WHEN unique_violation THEN
        RAISE EXCEPTION 'User with username "%" or email "%" already exists.', p_username, p_email;
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Failed to create user: %', SQLERRM;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION create_user(VARCHAR, VARCHAR, VARCHAR, VARCHAR, UUID, INET) IS 'Creates a new user and logs the action.';

-- Function: get_vkyc_recording_details
-- Retrieves details of a V-KYC recording along with its audit history.
CREATE OR REPLACE FUNCTION get_vkyc_recording_details(
    p_vkyc_recording_id UUID
)
RETURNS TABLE (
    id UUID,
    vkyc_case_id VARCHAR,
    customer_name VARCHAR,
    recording_date DATE,
    duration_seconds INTEGER,
    file_path TEXT,
    status VARCHAR,
    uploaded_by_user_id UUID,
    uploaded_by_username VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE,
    metadata_json JSONB,
    audit_history JSONB -- Array of audit log entries for this recording
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        vr.id,
        vr.vkyc_case_id,
        vr.customer_name,
        vr.recording_date,
        vr.duration_seconds,
        vr.file_path,
        vr.status,
        vr.uploaded_by_user_id,
        u.username AS uploaded_by_username,
        vr.created_at,
        vr.metadata_json,
        (
            SELECT jsonb_agg(
                jsonb_build_object(
                    'audit_id', al.id,
                    'action', al.action,
                    'user_id', al.user_id,
                    'username', au.username,
                    'timestamp', al.timestamp,
                    'ip_address', al.ip_address,
                    'details', al.details
                ) ORDER BY al.timestamp DESC
            )
            FROM audit_logs al
            JOIN users au ON al.user_id = au.id
            WHERE al.resource_type = 'vkyc_recording' AND al.resource_id = vr.id
        ) AS audit_history
    FROM
        vkyc_recordings vr
    JOIN
        users u ON vr.uploaded_by_user_id = u.id
    WHERE
        vr.id = p_vkyc_recording_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'V-KYC Recording with ID % not found.', p_vkyc_recording_id;
    END IF;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_vkyc_recording_details(UUID) IS 'Retrieves V-KYC recording details and its audit history.';

-- Function: log_audit_event
-- Manually logs an audit event. Useful for application-level actions not covered by triggers (e.g., login, logout).
CREATE OR REPLACE FUNCTION log_audit_event(
    p_user_id UUID,
    p_action VARCHAR,
    p_resource_type VARCHAR,
    p_resource_id UUID DEFAULT NULL,
    p_ip_address INET DEFAULT NULL,
    p_details JSONB DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    new_audit_id UUID;
BEGIN
    IF p_user_id IS NULL THEN
        RAISE EXCEPTION 'User ID cannot be NULL for an audit event.';
    END IF;
    IF p_action IS NULL OR p_action = '' THEN
        RAISE EXCEPTION 'Action cannot be empty for an audit event.';
    END IF;
    IF p_resource_type IS NULL OR p_resource_type = '' THEN
        RAISE EXCEPTION 'Resource type cannot be empty for an audit event.';
    END IF;

    INSERT INTO audit_logs (user_id, action, resource_type, resource_id, ip_address, details)
    VALUES (p_user_id, p_action, p_resource_type, p_resource_id, COALESCE(p_ip_address, inet_client_addr()), p_details)
    RETURNING id INTO new_audit_id;

    RETURN new_audit_id;
EXCEPTION
    WHEN foreign_key_violation THEN
        RAISE EXCEPTION 'User with ID % does not exist.', p_user_id;
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Failed to log audit event: %', SQLERRM;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION log_audit_event(UUID, VARCHAR, VARCHAR, UUID, INET, JSONB) IS 'Manually logs an audit event into the audit_logs table.';