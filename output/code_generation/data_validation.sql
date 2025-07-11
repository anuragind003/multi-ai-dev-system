-- data_validation.sql
-- Defines data validation rules using CHECK constraints and triggers.

-- =============================================================================
-- USERS TABLE VALIDATION
-- =============================================================================

-- Ensure 'role' column has allowed values
ALTER TABLE users
ADD CONSTRAINT chk_users_role CHECK (role IN ('admin', 'user', 'agent'));

COMMENT ON CONSTRAINT chk_users_role ON users IS 'Ensures user role is one of the predefined values: admin, user, agent.';

-- Ensure email format (basic check, more complex validation should be in application)
-- This regex is a simple check for @ and . in the email.
ALTER TABLE users
ADD CONSTRAINT chk_users_email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$');

COMMENT ON CONSTRAINT chk_users_email_format ON users IS 'Ensures email format is basic valid (contains @ and .).';

-- =============================================================================
-- VKYC_RECORDINGS TABLE VALIDATION
-- =============================================================================

-- Ensure 'status' column has allowed values
ALTER TABLE vkyc_recordings
ADD CONSTRAINT chk_vkyc_recordings_status CHECK (status IN ('pending', 'approved', 'rejected', 'in_progress', 'review_required'));

COMMENT ON CONSTRAINT chk_vkyc_recordings_status ON vkyc_recordings IS 'Ensures VKYC recording status is one of the predefined values.';

-- Ensure 'duration_seconds' is non-negative
ALTER TABLE vkyc_recordings
ADD CONSTRAINT chk_vkyc_recordings_duration_positive CHECK (duration_seconds >= 0);

COMMENT ON CONSTRAINT chk_vkyc_recordings_duration_positive ON vkyc_recordings IS 'Ensures recording duration is non-negative.';

-- Ensure recording_date is not in the future
ALTER TABLE vkyc_recordings
ADD CONSTRAINT chk_vkyc_recordings_date_not_future CHECK (recording_date <= CURRENT_DATE);

COMMENT ON CONSTRAINT chk_vkyc_recordings_date_not_future ON vkyc_recordings IS 'Ensures recording date is not in the future.';

-- =============================================================================
-- AUDIT_LOGS TABLE VALIDATION
-- =============================================================================

-- Ensure 'action' is not empty (already NOT NULL, but good for explicit intent)
ALTER TABLE audit_logs
ADD CONSTRAINT chk_audit_logs_action_not_empty CHECK (TRIM(action) <> '');

COMMENT ON CONSTRAINT chk_audit_logs_action_not_empty ON audit_logs IS 'Ensures the audit action description is not empty.';

-- Ensure timestamp is not in the future (application should handle this, but as a safeguard)
ALTER TABLE audit_logs
ADD CONSTRAINT chk_audit_logs_timestamp_not_future CHECK (timestamp <= NOW() + INTERVAL '1 minute'); -- Allow a small buffer

COMMENT ON CONSTRAINT chk_audit_logs_timestamp_not_future ON audit_logs IS 'Ensures audit log timestamp is not significantly in the future.';