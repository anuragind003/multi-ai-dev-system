-- performance_monitoring_queries.sql
-- Provides queries for monitoring database performance.

-- Query to identify slow queries (queries taking longer than a specified threshold).
-- Adjust the 'execution_time' threshold as needed.
SELECT
  pid,
  now() - query_start AS duration,
  usename,
  client_addr,
  application_name,
  query
FROM
  pg_stat_activity
WHERE
  query != '<IDLE>'
  AND now() - query_start > interval '5 seconds'  -- Adjust the threshold as needed
ORDER BY
  now() - query_start DESC;

-- Query to check index usage.
SELECT
  relname AS table_name,
  indexrelname AS index_name,
  idx_scan,
  idx_tup_read,
  idx_tup_fetch
FROM
  pg_stat_all_indexes
WHERE
  schemaname = 'public'  -- Or your schema name
  AND idx_scan > 0  -- Show only indexes that have been scanned
ORDER BY
  idx_scan DESC,
  idx_tup_read DESC;

-- Query to monitor table bloat (potential for performance degradation).
SELECT
  schemaname,
  tablename,
  (n_live_tup + n_dead_tup) AS approximate_row_count,
  n_dead_tup,
  n_live_tup,
  (n_dead_tup::float / (n_live_tup + n_dead_tup)) * 100 AS percent_dead
FROM
  pg_stat_all_tables
WHERE
  schemaname = 'public'  -- Or your schema name
  AND n_live_tup + n_dead_tup > 1000  -- Filter out small tables
ORDER BY
  percent_dead DESC;

-- Query to check for lock contention.
SELECT
  pid,
  now() - query_start AS duration,
  usename,
  query,
  waiting
FROM
  pg_stat_activity
WHERE
  waiting = true;

-- Query to monitor cache hit ratio (important for performance).
SELECT
  sum(blks_hit) * 100.0 / sum(blks_hit + blks_read) AS cache_hit_ratio
FROM
  pg_stat_database;