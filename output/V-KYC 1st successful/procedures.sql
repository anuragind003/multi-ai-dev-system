-- procedures.sql
-- Stored procedures and functions for common database operations.

-- Function to create a new user
CREATE OR REPLACE FUNCTION create_user(
    p_username VARCHAR(255),
    p_password_hash VARCHAR(255),
    p_email VARCHAR(255),
    p_role VARCHAR(50) DEFAULT 'user'
)
RETURNS UUID AS $$
DECLARE
    new_user_id UUID;
BEGIN
    INSERT INTO users (username, password_hash, email, role)
    VALUES (p_username, p_password_hash, p_email, p_role)
    RETURNING id INTO new_user_id;

    RETURN new_user_id;
EXCEPTION
    WHEN unique_violation THEN
        RAISE EXCEPTION 'User with username % or email % already exists.', p_username, p_email;
    WHEN others THEN
        RAISE EXCEPTION 'An error occurred while creating user: %', SQLERRM;
END;
$$ LANGUAGE plpgsql;

-- Function to create a new VKYC recording entry
CREATE OR REPLACE FUNCTION create_vkyc_recording(
    p_customer_id VARCHAR(255),
    p_recording_date DATE,
    p_recording_time TIME,
    p_status VARCHAR(50),
    p_file_path TEXT,
    p_duration_seconds INTEGER DEFAULT NULL,
    p_agent_id VARCHAR(255) DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    new_recording_id UUID;
BEGIN
    INSERT INTO vkyc_recordings (customer_id, recording_date, recording_time, status, file_path, duration_seconds, agent_id)
    VALUES (p_customer_id, p_recording_date, p_recording_time, p_status, p_file_path, p_duration_seconds, p_agent_id)
    RETURNING id INTO new_recording_id;

    RETURN new_recording_id;
EXCEPTION
    WHEN check_violation THEN
        RAISE EXCEPTION 'Invalid status or duration_seconds value for VKYC recording.';
    WHEN others THEN
        RAISE EXCEPTION 'An error occurred while creating VKYC recording: %', SQLERRM;
END;
$$ LANGUAGE plpgsql;

-- Function to update the status of a VKYC recording and log the action
CREATE OR REPLACE FUNCTION update_vkyc_recording_status(
    p_recording_id UUID,
    p_new_status VARCHAR(50),
    p_user_id UUID,
    p_ip_address INET DEFAULT NULL
)
RETURNS BOOLEAN AS $$
DECLARE
    current_status VARCHAR(50);
    recording_exists BOOLEAN;
BEGIN
    SELECT EXISTS(SELECT 1 FROM vkyc_recordings WHERE id = p_recording_id) INTO recording_exists;

    IF NOT recording_exists THEN
        RAISE EXCEPTION 'VKYC recording with ID % not found.', p_recording_id;
    END IF;

    SELECT status INTO current_status FROM vkyc_recordings WHERE id = p_recording_id;

    IF current_status = p_new_status THEN
        RAISE NOTICE 'VKYC recording % already has status %.', p_recording_id, p_new_status;
        RETURN FALSE;
    END IF;

    UPDATE vkyc_recordings
    SET status = p_new_status
    WHERE id = p_recording_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Failed to update VKYC recording status for ID %.', p_recording_id;
    END IF;

    -- Log the audit event
    PERFORM log_audit_event(
        p_user_id,
        'UPDATE_VKYC_STATUS',
        'vkyc_recording',
        p_recording_id,
        p_ip_address,
        'Status changed from ' || current_status || ' to ' || p_new_status
    );

    RETURN TRUE;
EXCEPTION
    WHEN check_violation THEN
        RAISE EXCEPTION 'Invalid status value "%" for VKYC recording.', p_new_status;
    WHEN foreign_key_violation THEN
        RAISE EXCEPTION 'User ID % for audit log does not exist.', p_user_id;
    WHEN others THEN
        RAISE EXCEPTION 'An error occurred while updating VKYC recording status: %', SQLERRM;
END;
$$ LANGUAGE plpgsql;

-- Function to log an audit event
CREATE OR REPLACE FUNCTION log_audit_event(
    p_user_id UUID,
    p_action VARCHAR(255),
    p_resource_type VARCHAR(255) DEFAULT NULL,
    p_resource_id UUID DEFAULT NULL,
    p_ip_address INET DEFAULT NULL,
    p_details TEXT DEFAULT NULL -- Optional field for more details
)
RETURNS UUID AS $$
DECLARE
    new_log_id UUID;
BEGIN
    INSERT INTO audit_logs (user_id, action, resource_type, resource_id, ip_address)
    VALUES (p_user_id, p_action, p_resource_type, p_resource_id, p_ip_address)
    RETURNING id INTO new_log_id;

    RETURN new_log_id;
EXCEPTION
    WHEN foreign_key_violation THEN
        RAISE EXCEPTION 'User with ID % does not exist. Cannot log audit event.', p_user_id;
    WHEN others THEN
        RAISE EXCEPTION 'An error occurred while logging audit event: %', SQLERRM;
END;
$$ LANGUAGE plpgsql;

-- Function to get VKYC recordings by customer ID
CREATE OR REPLACE FUNCTION get_vkyc_recordings_by_customer(
    p_customer_id VARCHAR(255)
)
RETURNS TABLE (
    id UUID,
    customer_id VARCHAR(255),
    recording_date DATE,
    recording_time TIME,
    status VARCHAR(50),
    file_path TEXT,
    duration_seconds INTEGER,
    agent_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        vr.id,
        vr.customer_id,
        vr.recording_date,
        vr.recording_time,
        vr.status,
        vr.file_path,
        vr.duration_seconds,
        vr.agent_id,
        vr.created_at
    FROM vkyc_recordings vr
    WHERE vr.customer_id = p_customer_id
    ORDER BY vr.recording_date DESC, vr.recording_time DESC;
END;
$$ LANGUAGE plpgsql;