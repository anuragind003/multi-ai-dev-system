-- PostgreSQL encryption configuration (requires pgcrypto extension)
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Example of encrypting a column (requires appropriate key management)
ALTER TABLE users ALTER COLUMN password TYPE BYTEA USING pg_crypto.encrypt(password, 'your_encryption_key');