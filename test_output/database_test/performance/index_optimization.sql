-- Covering index for common query
CREATE INDEX idx_orders_user_id_created_at_status ON orders (user_id, created_at, status);