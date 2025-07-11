-- db/procedures.sql
-- This file contains stored procedures and functions for common database operations.
-- These encapsulate business logic, improve performance by reducing network round-trips,
-- and enhance security by abstracting direct table access.

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
    INSERT INTO vkyc_recordings (
        customer_id,
        recording_date,
        recording_time,
        status,
        file_path,
        duration_seconds,
        agent_id
    ) VALUES (
        p_customer_id,
        p_recording_date,
        p_recording_time,
        p_status,
        p_file_path,
        p_duration_seconds,
        p_agent_id
    )
    RETURNING id INTO new_recording_id;

    RETURN new_recording_id;
END;
$$ LANGUAGE plpgsql;

-- Function to update the status of a VKYC recording
CREATE OR REPLACE FUNCTION update_vkyc_recording_status(
    p_recording_id UUID,
    p_new_status VARCHAR(50)
)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE vkyc_recordings
    SET status = p_new_status
    WHERE id = p_recording_id;

    RETURN FOUND; -- Returns true if a row was updated, false otherwise
END;
$$ LANGUAGE plpgsql;

-- Function to retrieve VKYC recordings by customer ID
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
    FROM
        vkyc_recordings vr
    WHERE
        vr.customer_id = p_customer_id
    ORDER BY
        vr.recording_date DESC, vr.recording_time DESC;
END;
$$ LANGUAGE plpgsql;

-- Function to log user actions in the audit_logs table
CREATE OR REPLACE FUNCTION log_user_action(
    p_user_id UUID,
    p_action VARCHAR(255),
    p_resource_type VARCHAR(255) DEFAULT NULL,
    p_resource_id UUID DEFAULT NULL,
    p_ip_address INET DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    new_log_id UUID;
BEGIN
    INSERT INTO audit_logs (
        user_id,
        action,
        resource_type,
        resource_id,
        ip_address
    ) VALUES (
        p_user_id,
        p_action,
        p_resource_type,
        p_resource_id,
        p_ip_address
    )
    RETURNING id INTO new_log_id;

    RETURN new_log_id;
END;
$$ LANGUAGE plpgsql;

-- Function to get audit logs for a specific user
CREATE OR REPLACE FUNCTION get_user_audit_logs(
    p_user_id UUID,
    p_limit INTEGER DEFAULT 100,
    p_offset INTEGER DEFAULT 0
)
RETURNS TABLE (
    id UUID,
    user_id UUID,
    action VARCHAR(255),
    resource_type VARCHAR(255),
    resource_id UUID,
    timestamp TIMESTAMP WITH TIME ZONE,
    ip_address INET
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        al.id,
        al.user_id,
        al.action,
        al.resource_type,
        al.resource_id,
        al.timestamp,
        al.ip_address
    FROM
        audit_logs al
    WHERE
        al.user_id = p_user_id
    ORDER BY
        al.timestamp DESC
    LIMIT p_limit OFFSET p_offset;
END;
$$ LANGUAGE plpgsql;

-- Example of a more complex function: Get VKYC recordings needing review
-- This could be based on status, duration, or other criteria
CREATE OR REPLACE FUNCTION get_recordings_for_review(
    p_status VARCHAR(50) DEFAULT 'REVIEW_REQUIRED',
    p_limit INTEGER DEFAULT 100
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
    FROM
        vkyc_recordings vr
    WHERE
        vr.status = p_status
    ORDER BY
        vr.created_at ASC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;