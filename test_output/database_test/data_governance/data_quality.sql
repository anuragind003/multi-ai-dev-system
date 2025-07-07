-- Data quality checks (example)
-- Check for null values in critical columns
SELECT COUNT(*) FROM users WHERE username IS NULL;
SELECT COUNT(*) FROM products WHERE price IS NULL;

-- Check for duplicate values
SELECT username, COUNT(*) FROM users GROUP BY username HAVING COUNT(*) > 1;