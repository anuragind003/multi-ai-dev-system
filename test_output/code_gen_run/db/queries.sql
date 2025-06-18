```sql
-- Create record
INSERT INTO "User" DEFAULT VALUES RETURNING id;

-- Retrieve record by ID
SELECT * FROM "User" WHERE id = $1;

-- Update record
UPDATE "User" SET id = id WHERE id = $1;

-- Delete record
DELETE FROM "User" WHERE id = $1;

-- List all records
SELECT * FROM "User";
```