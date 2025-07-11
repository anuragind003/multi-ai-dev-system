-- stored_procedures.sql
-- Contains stored procedures and functions for common, encapsulated operations.

-- Function to log audit events
-- This function encapsulates the logic for inserting into the audit_logs table,
-- ensuring consistency and potentially adding internal validation or enrichment.
CREATE OR REPLACE FUNCTION log_audit_event(
    p_user_id UUID,
    p_action audit_action_enum,
    p_resource_id UUID DEFAULT NULL,
    p_ip_address VARCHAR(45) DEFAULT NULL,
    p_details JSONB DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    v_audit_id UUID;
BEGIN
    -- Basic validation: Ensure user_id is not null
    IF p_user_id IS NULL THEN
        RAISE EXCEPTION 'User ID cannot be NULL for an audit event.';
    END IF;

    -- Insert the audit log entry
    INSERT INTO audit_logs (user_id, action, resource_id, ip_address, details)
    VALUES (p_user_id, p_action, p_resource_id, p_ip_address, p_details)
    RETURNING id INTO v_audit_id;

    RETURN v_audit_id;
EXCEPTION
    WHEN foreign_key_violation THEN
        RAISE EXCEPTION 'Foreign key violation: User ID % or Resource ID % does not exist.', p_user_id, p_resource_id;
    WHEN OTHERS THEN
        RAISE EXCEPTION 'An error occurred while logging audit event: %', SQLERRM;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION log_audit_event(UUID, audit_action_enum, UUID, VARCHAR, JSONB) IS 'Logs an audit event for a user action.';

-- Example of a more complex function: Get user activity summary
CREATE OR REPLACE FUNCTION get_user_activity_summary(
    p_user_id UUID,
    p_start_date TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    p_end_date TIMESTAMP WITH TIME ZONE DEFAULT NULL
)
RETURNS TABLE (
    action audit_action_enum,
    action_count BIGINT,
    last_action_timestamp TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        al.action,
        COUNT(al.id) AS action_count,
        MAX(al.timestamp) AS last_action_timestamp
    FROM
        audit_logs al
    WHERE
        al.user_id = p_user_id
        AND (p_start_date IS NULL OR al.timestamp >= p_start_date)
        AND (p_end_date IS NULL OR al.timestamp <= p_end_date)
    GROUP BY
        al.action
    ORDER BY
        action_count DESC;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_user_activity_summary(UUID, TIMESTAMP WITH TIME ZONE, TIMESTAMP WITH TIME ZONE) IS 'Retrieves a summary of actions performed by a specific user within a given date range.';

-- Function to update recording status and log audit event
CREATE OR REPLACE FUNCTION update_recording_status_and_log(
    p_recording_id UUID,
    p_new_status recording_status_enum,
    p_user_id UUID,
    p_ip_address VARCHAR(45) DEFAULT NULL,
    p_details JSONB DEFAULT NULL
)
RETURNS BOOLEAN AS $$
DECLARE
    v_old_status recording_status_enum;
    v_audit_details JSONB;
BEGIN
    -- Get current status
    SELECT status INTO v_old_status FROM vkyc_recordings WHERE id = p_recording_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Recording with ID % not found.', p_recording_id;
    END IF;

    IF v_old_status = p_new_status THEN
        RAISE NOTICE 'Recording % already has status %.', p_recording_id, p_new_status;
        RETURN FALSE;
    END IF;

    -- Update the recording status
    UPDATE vkyc_recordings
    SET status = p_new_status
    WHERE id = p_recording_id;

    -- Log the audit event
    v_audit_details := jsonb_build_object(
        'old_status', v_old_status,
        'new_status', p_new_status
    );
    IF p_details IS NOT NULL THEN
        v_audit_details := v_audit_details || p_details; -- Merge additional details
    END IF;

    PERFORM log_audit_event(
        p_user_id,
        'recording_status_updated',
        p_recording_id,
        p_ip_address,
        v_audit_details
    );

    RETURN TRUE;
EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Failed to update recording status and log audit: %', SQLERRM;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION update_recording_status_and_log(UUID, recording_status_enum, UUID, VARCHAR, JSONB) IS 'Updates the status of a VKYC recording and logs the change as an audit event.';