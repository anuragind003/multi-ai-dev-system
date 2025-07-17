-- db/data_validation.sql
-- This file defines additional data validation rules using PostgreSQL CHECK constraints.
-- These constraints enforce data integrity beyond basic type and NOT NULL checks,
-- ensuring that data conforms to specific business rules.

-- =============================================================================
-- USERS TABLE VALIDATION
-- =============================================================================

-- Ensure 'email' column contains a basic valid email format
-- This is a simple regex; a more robust validation should be done in application layer.
ALTER TABLE users
ADD CONSTRAINT chk_users_email_format
CHECK (email ~* '^[A-Za-z0-9._%-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,4}$');

-- Ensure 'role' column contains only predefined values
ALTER TABLE users
ADD CONSTRAINT chk_users_role_valid
CHECK (role IN ('admin', 'user', 'auditor', 'agent')); -- Added 'agent' role for completeness

-- Ensure 'username' is not empty after trimming whitespace
ALTER TABLE users
ADD CONSTRAINT chk_users_username_not_empty
CHECK (TRIM(username) <> '');

-- Ensure 'password_hash' is not empty after trimming whitespace
ALTER TABLE users
ADD CONSTRAINT chk_users_password_hash_not_empty
CHECK (TRIM(password_hash) <> '');

-- =============================================================================
-- VKYC_RECORDINGS TABLE VALIDATION
-- =============================================================================

-- Ensure 'status' column contains only predefined values
ALTER TABLE vkyc_recordings
ADD CONSTRAINT chk_vkyc_recordings_status_valid
CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED', 'REVIEW_REQUIRED', 'PROCESSING', 'FAILED'));

-- Ensure 'duration_seconds' is a positive value if present
ALTER TABLE vkyc_recordings
ADD CONSTRAINT chk_vkyc_recordings_duration_positive
CHECK (duration_seconds IS NULL OR duration_seconds > 0);

-- Ensure 'file_path' is not empty after trimming whitespace
ALTER TABLE vkyc_recordings
ADD CONSTRAINT chk_vkyc_recordings_file_path_not_empty
CHECK (TRIM(file_path) <> '');

-- Ensure 'customer_id' is not empty after trimming whitespace
ALTER TABLE vkyc_recordings
ADD CONSTRAINT chk_vkyc_recordings_customer_id_not_empty
CHECK (TRIM(customer_id) <> '');

-- =============================================================================
-- AUDIT_LOGS TABLE VALIDATION
-- =============================================================================

-- Ensure 'action' column is not empty after trimming whitespace
ALTER TABLE audit_logs
ADD CONSTRAINT chk_audit_logs_action_not_empty
CHECK (TRIM(action) <> '');

-- Ensure 'resource_type' is not empty if present
ALTER TABLE audit_logs
ADD CONSTRAINT chk_audit_logs_resource_type_not_empty
CHECK (resource_type IS NULL OR TRIM(resource_type) <> '');

-- Ensure 'ip_address' is a valid INET type (handled by INET type itself, but can add specific range checks if needed)
-- Example: Restrict to private IP ranges (more complex, usually done in app layer or firewall)
-- ALTER TABLE audit_logs
-- ADD CONSTRAINT chk_audit_logs_ip_private_range
-- CHECK (ip_address IS NULL OR ip_address << '10.0.0.0/8' OR ip_address << '172.16.0.0/12' OR ip_address << '192.168.0.0/16');

-- Informative message
SELECT 'Data validation constraints applied successfully.' AS status;