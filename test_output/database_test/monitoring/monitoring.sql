-- Queries for monitoring database performance
-- Example: Slow query log analysis
SELECT query, calls, total_time, avg_time
FROM pg_stat_statements
ORDER BY total_time DESC
LIMIT 10;

-- Example: Resource utilization
SELECT * FROM pg_stat_database;