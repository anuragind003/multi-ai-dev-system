-- stored_procedures.sql
-- Contains stored procedures and functions for common database operations.

-- Function to log audit events
-- This function encapsulates the logic for inserting into the audit_logs table,
-- ensuring consistency and potentially adding more logic in the future (e.g., validation).
CREATE OR REPLACE FUNCTION log_audit_event(
    p_user_id UUID,
    p_action VARCHAR,
    p_resource_type VARCHAR DEFAULT NULL,
    p_resource_id UUID DEFAULT NULL,
    p_ip_address INET DEFAULT NULL
)
RETURNS VOID AS $$
BEGIN
    INSERT INTO audit_logs (user_id, action, resource_type, resource_id, ip_address)
    VALUES (p_user_id, p_action, p_resource_type, p_resource_id, p_ip_address);
EXCEPTION
    WHEN foreign_key_violation THEN
        RAISE EXCEPTION 'User ID % does not exist. Cannot log audit event.', p_user_id;
    WHEN others THEN
        RAISE EXCEPTION 'An error occurred while logging audit event: %', SQLERRM;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION log_audit_event IS 'Logs an audit event for a specific user action.';

-- Example usage of log_audit_event:
-- SELECT log_audit_event('a1b2c3d4-e5f6-7890-1234-567890abcdef', 'user_login', 'user', 'a1b2c3d4-e5f6-7890-1234-567890abcdef', '192.168.1.1'::INET);
-- SELECT log_audit_event('a1b2c3d4-e5f6-7890-1234-567890abcdef', 'update_vkyc_status', 'vkyc_recording', 'b2c3d4e5-f6a7-8901-2345-67890abcdef0', '10.0.0.5'::INET);

-- Function to get VKYC recordings by status and date range
CREATE OR REPLACE FUNCTION get_vkyc_recordings_by_status_and_date(
    p_status VARCHAR,
    p_start_date DATE,
    p_end_date DATE
)
RETURNS TABLE (
    id UUID,
    customer_id VARCHAR,
    recording_date DATE,
    recording_time TIME,
    status VARCHAR,
    file_path TEXT,
    duration_seconds INTEGER,
    agent_id VARCHAR,
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
        vr.status = p_status AND
        vr.recording_date BETWEEN p_start_date AND p_end_date
    ORDER BY
        vr.recording_date DESC, vr.recording_time DESC;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_vkyc_recordings_by_status_and_date IS 'Retrieves VKYC recordings filtered by status and a date range.';

-- Example usage:
-- SELECT * FROM get_vkyc_recordings_by_status_and_date('approved', '2023-01-01', '2023-12-31');