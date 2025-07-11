-- data_validation.sql
-- Defines additional data validation rules using CHECK constraints and potentially functions.
-- Some basic validations are already in schema.sql (e.g., NOT NULL, ENUM types, duration_seconds >= 0).
-- This file adds more specific or complex rules.

-- 1. Users Table Validations
-- Ensure username is not empty (beyond NOT NULL, which allows empty string)
ALTER TABLE users
ADD CONSTRAINT chk_username_not_empty CHECK (TRIM(username) <> '');

-- Ensure password_hash is not empty (beyond NOT NULL)
ALTER TABLE users
ADD CONSTRAINT chk_password_hash_not_empty CHECK (TRIM(password_hash) <> '');

-- 2. VKYC Recordings Table Validations
-- Ensure customer_id is not empty
ALTER TABLE vkyc_recordings
ADD CONSTRAINT chk_customer_id_not_empty CHECK (TRIM(customer_id) <> '');

-- Ensure recording_name is not empty
ALTER TABLE vkyc_recordings
ADD CONSTRAINT chk_recording_name_not_empty CHECK (TRIM(recording_name) <> '');

-- Ensure recording_path is not empty
ALTER TABLE vkyc_recordings
ADD CONSTRAINT chk_recording_path_not_empty CHECK (TRIM(recording_path) <> '');

-- Ensure recording_timestamp is not in the future (assuming recordings are historical)
ALTER TABLE vkyc_recordings
ADD CONSTRAINT chk_recording_timestamp_not_future CHECK (recording_timestamp <= CURRENT_TIMESTAMP + INTERVAL '1 minute'); -- Allow slight future for clock sync

-- 3. Audit Logs Table Validations
-- Ensure action is not empty (already covered by ENUM, but good practice)
ALTER TABLE audit_logs
ADD CONSTRAINT chk_action_not_empty CHECK (TRIM(action::text) <> '');

-- Validate IP address format (basic regex check for IPv4 or IPv6, can be more robust)
-- This is a simple check, a more comprehensive one might involve a custom function or external library.
ALTER TABLE audit_logs
ADD CONSTRAINT chk_ip_address_format CHECK (
    ip_address IS NULL OR
    ip_address ~ '^([0-9]{1,3}\.){3}[0-9]{1,3}$' OR -- Basic IPv4
    ip_address ~ '^[0-9a-fA-F:]+$' -- Basic IPv6 (can be more specific)
);

-- Example of a more complex JSONB validation (conceptual, might be too specific for general use)
-- This checks if 'details' JSONB contains a 'status' key when action is 'login'
-- This is just an example; real-world JSONB validation often happens in application layer
-- or via more complex PL/pgSQL functions/triggers.
/*
CREATE OR REPLACE FUNCTION validate_audit_details_jsonb()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.action = 'login' AND NEW.details IS NOT NULL THEN
        IF NOT (NEW.details ? 'status') THEN
            RAISE EXCEPTION 'Audit log for login action must contain a "status" key in details JSONB.';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validate_audit_details
BEFORE INSERT OR UPDATE ON audit_logs
FOR EACH ROW
EXECUTE FUNCTION validate_audit_details_jsonb();
*/
-- The above JSONB validation trigger is commented out as it adds complexity and might be better handled
-- at the application layer or via more specific business logic.
-- For this exercise, the simpler CHECK constraints are sufficient.