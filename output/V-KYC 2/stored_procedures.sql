-- stored_procedures.sql
-- Defines PostgreSQL functions (stored procedures) for common database operations.
-- These functions encapsulate business logic, improve security, and reduce network round trips.

-- Function: create_user
-- Creates a new user and returns the ID of the newly created user.
CREATE OR REPLACE FUNCTION create_user(
    p_username VARCHAR(255),
    p_password_hash VARCHAR(255),
    p_email VARCHAR(255),
    p_role VARCHAR(50)
)
RETURNS UUID AS $$
DECLARE
    new_user_id UUID;
BEGIN
    -- Input validation for role (redundant if CHECK constraint is active, but good for explicit API)
    IF p_role NOT IN ('Team Lead', 'Process Manager', 'Admin') THEN
        RAISE EXCEPTION 'Invalid user role: %', p_role;
    END IF;

    INSERT INTO users (username, password_hash, email, role)
    VALUES (p_username, p_password_hash, p_email, p_role)
    RETURNING id INTO new_user_id;

    -- Log the action
    PERFORM log_audit_event(new_user_id, 'user_created', NULL, '127.0.0.1', jsonb_build_object('username', p_username, 'role', p_role));

    RETURN new_user_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION create_user IS 'Creates a new user and logs the creation event.';

-- Function: log_audit_event
-- Inserts an entry into the audit_logs table.
CREATE OR REPLACE FUNCTION log_audit_event(
    p_user_id UUID,
    p_action VARCHAR(100),
    p_recording_id UUID DEFAULT NULL,
    p_ip_address VARCHAR(45) DEFAULT NULL,
    p_details JSONB DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    new_log_id UUID;
BEGIN
    INSERT INTO audit_logs (user_id, action, recording_id, ip_address, details)
    VALUES (p_user_id, p_action, p_recording_id, p_ip_address, p_details)
    RETURNING id INTO new_log_id;

    RETURN new_log_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION log_audit_event IS 'Logs a significant user action to the audit_logs table.';

-- Function: get_recordings_by_user
-- Retrieves all recordings uploaded by a specific user.
CREATE OR REPLACE FUNCTION get_recordings_by_user(p_user_id UUID)
RETURNS TABLE (
    id UUID,
    vkyc_id VARCHAR(100),
    customer_name VARCHAR(255),
    recording_date DATE,
    duration_seconds INTEGER,
    file_name VARCHAR(255),
    storage_path TEXT,
    uploaded_by_user_id UUID,
    uploaded_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50)
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        r.id,
        r.vkyc_id,
        r.customer_name,
        r.recording_date,
        r.duration_seconds,
        r.file_name,
        r.storage_path,
        r.uploaded_by_user_id,
        r.uploaded_at,
        r.status
    FROM
        recordings r
    WHERE
        r.uploaded_by_user_id = p_user_id
    ORDER BY
        r.uploaded_at DESC;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_recordings_by_user IS 'Retrieves all recordings uploaded by a specified user.';

-- Function: update_recording_status
-- Updates the status of a specific recording and logs the action.
CREATE OR REPLACE FUNCTION update_recording_status(
    p_recording_id UUID,
    p_new_status VARCHAR(50),
    p_acting_user_id UUID,
    p_ip_address VARCHAR(45) DEFAULT NULL
)
RETURNS BOOLEAN AS $$
DECLARE
    current_status VARCHAR(50);
    recording_exists BOOLEAN;
BEGIN
    -- Check if recording exists
    SELECT EXISTS(SELECT 1 FROM recordings WHERE id = p_recording_id) INTO recording_exists;
    IF NOT recording_exists THEN
        RAISE EXCEPTION 'Recording with ID % does not exist.', p_recording_id;
    END IF;

    -- Validate new status (redundant if CHECK constraint is active, but good for explicit API)
    IF p_new_status NOT IN ('available', 'processing', 'archived', 'deleted', 'error') THEN
        RAISE EXCEPTION 'Invalid recording status: %', p_new_status;
    END IF;

    SELECT status INTO current_status FROM recordings WHERE id = p_recording_id;

    IF current_status = p_new_status THEN
        -- No change, just return true
        RETURN TRUE;
    END IF;

    UPDATE recordings
    SET status = p_new_status
    WHERE id = p_recording_id;

    -- Log the action
    PERFORM log_audit_event(
        p_acting_user_id,
        'recording_status_updated',
        p_recording_id,
        p_ip_address,
        jsonb_build_object('old_status', current_status, 'new_status', p_new_status)
    );

    RETURN TRUE;
EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Failed to update recording status: %', SQLERRM;
        RETURN FALSE;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION update_recording_status IS 'Updates the status of a recording and logs the change.';

-- Function: delete_user_and_audit
-- Deletes a user and logs the action.
-- Note: ON DELETE CASCADE on audit_logs.user_id will handle audit log deletion.
-- ON DELETE RESTRICT on recordings.uploaded_by_user_id prevents deletion if user has recordings.
CREATE OR REPLACE FUNCTION delete_user_and_audit(
    p_user_id UUID,
    p_acting_user_id UUID, -- The user performing the deletion (e.g., an Admin)
    p_ip_address VARCHAR(45) DEFAULT NULL
)
RETURNS BOOLEAN AS $$
DECLARE
    user_name VARCHAR(255);
    has_recordings BOOLEAN;
BEGIN
    -- Check if user exists
    SELECT username INTO user_name FROM users WHERE id = p_user_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'User with ID % does not exist.', p_user_id;
    END IF;

    -- Check if the user has any recordings (due to ON DELETE RESTRICT)
    SELECT EXISTS(SELECT 1 FROM recordings WHERE uploaded_by_user_id = p_user_id) INTO has_recordings;
    IF has_recordings THEN
        RAISE EXCEPTION 'Cannot delete user % (ID: %) because they have associated recordings. Please reassign or delete recordings first.', user_name, p_user_id;
    END IF;

    DELETE FROM users WHERE id = p_user_id;

    -- Log the action by the acting user
    PERFORM log_audit_event(
        p_acting_user_id,
        'user_deleted',
        NULL,
        p_ip_address,
        jsonb_build_object('deleted_user_id', p_user_id, 'deleted_username', user_name)
    );

    RETURN TRUE;
EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Failed to delete user: %', SQLERRM;
        RETURN FALSE;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION delete_user_and_audit IS 'Deletes a user and logs the deletion event. Prevents deletion if user has associated recordings.';