-- Archive old orders
DELETE FROM orders WHERE created_at < NOW() - INTERVAL '1 year';