-- Audit table for users
CREATE TABLE user_audit (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    operation VARCHAR(50),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    details JSONB
);

-- Trigger to log user changes
CREATE OR REPLACE FUNCTION log_user_changes()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO user_audit (user_id, operation, details)
    VALUES (NEW.id, 'INSERT', row_to_json(NEW));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER user_insert_trigger
AFTER INSERT ON users
FOR EACH ROW
EXECUTE FUNCTION log_user_changes();