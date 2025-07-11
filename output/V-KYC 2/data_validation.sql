-- data_validation.sql
-- Defines additional data validation rules using PostgreSQL features like CHECK constraints,
-- and triggers. Some basic validations are already in schema.sql.
-- This file focuses on more complex or explicit validation examples.

-- Note: Basic CHECK constraints (e.g., for `role`, `status`, `duration_seconds > 0`)
-- are already defined directly in `schema.sql` and applied via migrations.

-- --- Advanced Validation using Triggers ---

-- Trigger Function: validate_vkyc_id_format
-- Ensures that the vkyc_id follows a specific pattern (e.g., 3 uppercase letters + 6 digits).
-- This function is already included in initial_schema.py and schema.sql for completeness,
-- but explicitly defining it here highlights its validation purpose.
CREATE OR REPLACE FUNCTION validate_vkyc_id_format()
RETURNS TRIGGER AS $$
BEGIN
    -- Example pattern: 'ABC123456' (3 uppercase letters, 6 digits)
    IF NEW.vkyc_id !~ '^[A-Z]{3}[0-9]{6}$' THEN
        RAISE EXCEPTION 'Invalid VKYC ID format. Must be 3 uppercase letters followed by 6 digits (e.g., ABC123456).';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger: trg_validate_vkyc_id
-- Applies the `validate_vkyc_id_format` function before insert or update on `recordings`.
DROP TRIGGER IF EXISTS trg_validate_vkyc_id ON recordings;
CREATE TRIGGER trg_validate_vkyc_id
BEFORE INSERT OR UPDATE ON recordings
FOR EACH ROW
EXECUTE FUNCTION validate_vkyc_id_format();

COMMENT ON FUNCTION validate_vkyc_id_format IS 'Ensures VKYC ID adheres to a specific alphanumeric format.';
COMMENT ON TRIGGER trg_validate_vkyc_id ON recordings IS 'Activates before insert/update on recordings to validate VKYC ID format.';

-- Trigger Function: prevent_user_deletion_with_active_recordings
-- Prevents a user from being deleted if they have any 'available' or 'processing' recordings.
-- This adds a layer of business logic validation beyond simple foreign key constraints.
CREATE OR REPLACE FUNCTION prevent_user_deletion_with_active_recordings()
RETURNS TRIGGER AS $$
DECLARE
    active_recordings_count INTEGER;
BEGIN
    SELECT COUNT(*)
    INTO active_recordings_count
    FROM recordings
    WHERE uploaded_by_user_id = OLD.id
      AND status IN ('available', 'processing');

    IF active_recordings_count > 0 THEN
        RAISE EXCEPTION 'Cannot delete user with ID % (username: %) because they have % active recordings. Please archive or delete recordings first.', OLD.id, OLD.username, active_recordings_count;
    END IF;

    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

-- Trigger: trg_prevent_user_deletion
-- Applies the `prevent_user_deletion_with_active_recordings` function before delete on `users`.
DROP TRIGGER IF EXISTS trg_prevent_user_deletion ON users;
CREATE TRIGGER trg_prevent_user_deletion
BEFORE DELETE ON users
FOR EACH ROW
EXECUTE FUNCTION prevent_user_deletion_with_active_recordings();

COMMENT ON FUNCTION prevent_user_deletion_with_active_recordings IS 'Prevents deletion of a user if they have active recordings.';
COMMENT ON TRIGGER trg_prevent_user_deletion ON users IS 'Activates before delete on users to prevent deletion of users with active recordings.';

-- --- Additional CHECK Constraints (if not already in schema.sql) ---
-- These are already in schema.sql, but listed here for conceptual clarity of validation rules.

-- Ensure email format (basic regex, more complex validation typically done in application layer)
-- ALTER TABLE users ADD CONSTRAINT chk_users_email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$');
-- (This is often too restrictive for a DB-level check and better handled by application logic)

-- Ensure file_name is not empty (beyond NOT NULL, which allows empty string)
ALTER TABLE recordings DROP CONSTRAINT IF EXISTS chk_recordings_file_name_not_empty;
ALTER TABLE recordings ADD CONSTRAINT chk_recordings_file_name_not_empty CHECK (TRIM(file_name) <> '');

COMMENT ON CONSTRAINT chk_recordings_file_name_not_empty ON recordings IS 'Ensures the file_name field is not an empty string or just whitespace.';

-- Ensure storage_path is not empty
ALTER TABLE recordings DROP CONSTRAINT IF EXISTS chk_recordings_storage_path_not_empty;
ALTER TABLE recordings ADD CONSTRAINT chk_recordings_storage_path_not_empty CHECK (TRIM(storage_path) <> '');

COMMENT ON CONSTRAINT chk_recordings_storage_path_not_empty ON recordings IS 'Ensures the storage_path field is not an empty string or just whitespace.';