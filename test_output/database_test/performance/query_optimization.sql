-- Example query optimization: Use EXPLAIN ANALYZE to analyze query performance
EXPLAIN ANALYZE SELECT * FROM products WHERE price > 100;

-- Example: Create covering index to improve query performance
CREATE INDEX idx_products_price_name ON products (price, name);