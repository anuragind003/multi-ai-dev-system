-- Up migration
CREATE INDEX idx_users_username ON users (username);
CREATE INDEX idx_products_name ON products (name);
CREATE INDEX idx_orders_user_id ON orders (user_id);
CREATE INDEX idx_order_items_order_id ON order_items (order_id);
CREATE INDEX idx_order_items_product_id ON order_items (product_id);

-- Down migration
DROP INDEX idx_users_username;
DROP INDEX idx_products_name;
DROP INDEX idx_orders_user_id;
DROP INDEX idx_order_items_order_id;
DROP INDEX idx_order_items_product_id;