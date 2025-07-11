-- stored_procedures_functions.sql
-- Defines stored procedures and functions for common database operations.

-- Function to create a new task.
CREATE OR REPLACE FUNCTION create_task(p_description TEXT, p_metadata JSONB DEFAULT NULL)
RETURNS UUID AS $$
DECLARE
    new_task_id UUID;
BEGIN
    INSERT INTO tasks (description, metadata)
    VALUES (p_description, p_metadata)
    RETURNING id INTO new_task_id;
    RETURN new_task_id;
END;
$$ LANGUAGE plpgsql;

-- Function to retrieve a task by ID.
CREATE OR REPLACE FUNCTION get_task_by_id(p_id UUID)
RETURNS JSONB AS $$
BEGIN
    RETURN (SELECT row_to_json(tasks) FROM tasks WHERE id = p_id);
END;
$$ LANGUAGE plpgsql;

-- Function to update a task.
CREATE OR REPLACE FUNCTION update_task(p_id UUID, p_description TEXT, p_metadata JSONB DEFAULT NULL)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE tasks
    SET description = p_description,
        metadata = p_metadata,
        created_at = NOW() -- Update created_at on update
    WHERE id = p_id;
    RETURN FOUND; -- Returns TRUE if a row was updated, FALSE otherwise.
END;
$$ LANGUAGE plpgsql;

-- Function to delete a task.
CREATE OR REPLACE FUNCTION delete_task(p_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    DELETE FROM tasks WHERE id = p_id;
    RETURN FOUND; -- Returns TRUE if a row was deleted, FALSE otherwise.
END;
$$ LANGUAGE plpgsql;