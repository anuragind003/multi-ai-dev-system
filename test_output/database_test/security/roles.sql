-- Create roles
CREATE ROLE admin;
CREATE ROLE user;

-- Grant privileges
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO admin;
GRANT SELECT, INSERT, UPDATE ON users TO user;
GRANT SELECT ON products TO user;
GRANT SELECT, INSERT ON orders TO user;
GRANT SELECT, INSERT, UPDATE ON order_items TO user;

-- Add more granular permissions as needed