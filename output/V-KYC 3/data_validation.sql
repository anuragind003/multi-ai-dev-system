-- data_validation.sql
-- Contains additional data validation rules, typically implemented as triggers or functions,
-- beyond basic column constraints defined in the schema.

-- Function: validate_vkyc_recording_metadata
-- Validates the structure and content of the JSONB metadata for vkyc_recordings.
-- This is an example; actual validation rules would depend on expected metadata structure.
CREATE OR REPLACE FUNCTION validate_vkyc_recording_metadata()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.metadata_json IS NOT NULL THEN
        -- Example 1: Ensure 'agent_id' exists and is a string
        IF NOT (NEW.metadata_json ? 'agent_id') THEN
            RAISE EXCEPTION 'Metadata must contain an "agent_id" field.';
        END IF;
        IF jsonb_typeof(NEW.metadata_json->'agent_id') <> 'string' THEN
            RAISE EXCEPTION 'Metadata "agent_id" must be a string.';
        END IF;

        -- Example 2: If 'resolution' exists, ensure it's a valid string (e.g., '720p', '1080p')
        IF NEW.metadata_json ? 'resolution' THEN
            IF jsonb_typeof(NEW.metadata_json->'resolution') <> 'string' THEN
                RAISE EXCEPTION 'Metadata "resolution" must be a string.';
            END IF;
            IF NOT (NEW.metadata_json->>'resolution' IN ('720p', '1080p', '1440p', '2160p')) THEN
                RAISE EXCEPTION 'Metadata "resolution" must be one of "720p", "1080p", "1440p", "2160p".';
            END IF;
        END IF;

        -- Example 3: Ensure 'notes' (if present) is a string and not excessively long
        IF NEW.metadata_json ? 'notes' THEN
            IF jsonb_typeof(NEW.metadata_json->'notes') <> 'string' THEN
                RAISE EXCEPTION 'Metadata "notes" must be a string.';
            END IF;
            IF LENGTH(NEW.metadata_json->>'notes') > 500 THEN
                RAISE EXCEPTION 'Metadata "notes" exceeds maximum length of 500 characters.';
            END IF;
        END IF;

        -- Add more validation rules as needed for your JSONB structure
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger: trg_validate_vkyc_metadata
-- Executes the validation function before an insert or update on vkyc_recordings.
CREATE TRIGGER trg_validate_vkyc_metadata
BEFORE INSERT OR UPDATE OF metadata_json ON vkyc_recordings
FOR EACH ROW EXECUTE FUNCTION validate_vkyc_recording_metadata();

COMMENT ON FUNCTION validate_vkyc_recording_metadata() IS 'Validates the JSONB metadata field of vkyc_recordings.';
COMMENT ON TRIGGER trg_validate_vkyc_metadata IS 'Trigger to validate vkyc_recordings metadata before insert or update.';

-- Function: validate_user_email_format
-- Ensures that the email address stored in the users table follows a basic email format.
CREATE OR REPLACE FUNCTION validate_user_email_format()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.email IS NOT NULL AND NEW.email !~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$' THEN
        RAISE EXCEPTION 'Invalid email format for user: %', NEW.email;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger: trg_validate_user_email
-- Executes the email format validation function before an insert or update on users.
CREATE TRIGGER trg_validate_user_email
BEFORE INSERT OR UPDATE OF email ON users
FOR EACH ROW EXECUTE FUNCTION validate_user_email_format();

COMMENT ON FUNCTION validate_user_email_format() IS 'Validates the email format for users.';
COMMENT ON TRIGGER trg_validate_user_email IS 'Trigger to validate user email format before insert or update.';

-- Function: enforce_audit_log_immutability
-- Prevents updates and deletes on the audit_logs table to ensure data integrity.
-- Only allows inserts.
CREATE OR REPLACE FUNCTION enforce_audit_log_immutability()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        RAISE EXCEPTION 'Updates to audit_logs are not allowed.';
    ELSIF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Deletions from audit_logs are not allowed.';
    END IF;
    RETURN OLD; -- For DELETE, return OLD; for UPDATE, this path should not be reached.
END;
$$ LANGUAGE plpgsql;

-- Trigger: trg_enforce_audit_log_immutability
-- Applies the immutability rule to the audit_logs table.
CREATE TRIGGER trg_enforce_audit_log_immutability
BEFORE UPDATE OR DELETE ON audit_logs
FOR EACH ROW EXECUTE FUNCTION enforce_audit_log_immutability();

COMMENT ON FUNCTION enforce_audit_log_immutability() IS 'Enforces immutability for audit_logs table, preventing updates and deletes.';
COMMENT ON TRIGGER trg_enforce_audit_log_immutability IS 'Trigger to prevent updates and deletes on the audit_logs table.';

-- Note: For data retention policies, instead of DELETE, consider soft deletes or
-- a separate archival process that moves old data to a different table/storage.
-- If hard deletion is required for retention, it should be done by a highly privileged
-- and audited process, bypassing this trigger or by disabling it temporarily.