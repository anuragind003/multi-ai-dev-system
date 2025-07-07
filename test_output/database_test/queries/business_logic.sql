-- Example business logic query: Get total revenue for a specific period
SELECT SUM(p.price * oi.quantity) AS total_revenue
FROM products p
JOIN order_items oi ON p.id = oi.product_id
JOIN orders o ON oi.order_id = o.id
WHERE o.created_at BETWEEN '2024-01-01' AND '2024-01-31';