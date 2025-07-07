-- Test queries to validate database integrity and functionality
-- Example: Check referential integrity
SELECT * FROM order_items WHERE order_id NOT IN (SELECT id FROM orders);