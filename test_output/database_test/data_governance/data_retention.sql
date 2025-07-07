-- Data retention policy (example)
-- Delete old audit logs
DELETE FROM audit_log WHERE timestamp < NOW() - INTERVAL '3 months';