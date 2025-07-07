-- CRUD operations for users table (example)
-- INSERT
INSERT INTO users (username, password, email) VALUES ('testuser', 'password', 'test@example.com');

-- SELECT
SELECT * FROM users WHERE id = 1;

-- UPDATE
UPDATE users SET username = 'updateduser' WHERE id = 1;

-- DELETE
DELETE FROM users WHERE id = 1;

-- Similar CRUD operations for other tables