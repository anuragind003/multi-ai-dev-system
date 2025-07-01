-- Check for invalid product prices
SELECT * FROM products WHERE price < 0;

-- Check for orders with missing user IDs
SELECT * FROM orders WHERE user_id IS NULL;