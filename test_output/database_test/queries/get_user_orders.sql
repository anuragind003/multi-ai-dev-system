-- Query to get all orders for a specific user
SELECT * FROM orders WHERE user_id = $1;