-- seed_data.sql
-- Inserts initial data for development and testing.

-- Insert sample tasks.
INSERT INTO tasks (description, metadata) VALUES
('Grocery Shopping', '{"priority": "high", "due_date": "2024-01-20"}'),
('Book Doctor Appointment', '{"priority": "medium", "due_date": "2024-01-25"}'),
('Prepare Presentation', '{"priority": "high", "due_date": "2024-01-22", "status": "in progress"}');

-- Insert more sample tasks for testing
INSERT INTO tasks (description) VALUES
('Write a blog post'),
('Review code');