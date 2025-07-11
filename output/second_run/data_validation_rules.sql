-- data_validation_rules.sql
-- Defines data validation rules using CHECK constraints and triggers.

-- Add CHECK constraint to 'tasks' table to ensure description is not empty.
ALTER TABLE tasks
ADD CONSTRAINT chk_description_not_empty
CHECK (description <> '');

-- Example:  Trigger to validate metadata (example: due_date format)
CREATE OR REPLACE FUNCTION validate_task_metadata()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.metadata IS NOT NULL THEN
        -- Example: Validate due_date format (requires a date in ISO format)
        IF NEW.metadata ->> 'due_date' IS NOT NULL THEN
            -- Attempt to parse the date.  If it fails, raise an exception.
            PERFORM NEW.metadata ->> 'due_date' :: DATE;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validate_task_metadata
BEFORE INSERT OR UPDATE ON tasks
FOR EACH ROW
EXECUTE FUNCTION validate_task_metadata();

-- Example:  Constraint to ensure priority is one of a set of allowed values.
ALTER TABLE tasks
ADD CONSTRAINT chk_priority_valid
CHECK (
    (metadata ->> 'priority') IN ('high', 'medium', 'low', NULL)
);

-- Example:  Constraint to ensure status is one of a set of allowed values.
ALTER TABLE tasks
ADD CONSTRAINT chk_status_valid
CHECK (
    (metadata ->> 'status') IN ('in progress', 'completed', 'pending', NULL)
);