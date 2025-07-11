-- performance_monitoring.sql
-- Collection of SQL queries for monitoring PostgreSQL database performance.
-- These queries help identify bottlenecks, inefficient queries, and resource usage.

-- 1. Active and Long-Running Queries
-- Identifies currently running queries, their duration, and associated users.
SELECT
    pid,
    datname,
    usename,
    application_name,
    client_addr,
    backend_start,
    query_start,
    state,
    wait_event_type,
    wait_event,
    query,
    (EXTRACT(EPOCH FROM (NOW() - query_start)) * 1000)::bigint AS query_duration_ms
FROM
    pg_stat_activity
WHERE
    state = 'active'
ORDER BY
    query_duration_ms DESC;

-- 2. Table Statistics (useful for identifying bloat, scan types)
-- Shows number of sequential scans, index scans, inserts, updates, deletes, and dead tuples.
SELECT
    relname AS table_name,
    pg_size_pretty(pg_relation_size(relid)) AS table_size,
    n_live_tup AS live_tuples,
    n_dead_tup AS dead_tuples,
    n_tup_ins AS inserts,
    n_tup_upd AS updates,
    n_tup_del AS deletes,
    n_seq_scans AS sequential_scans,
    n_idx_scans AS index_scans,
    last_autovacuum,
    last_autoanalyze
FROM
    pg_stat_user_tables
ORDER BY
    pg_relation_size(relid) DESC;

-- 3. Index Usage Statistics
-- Helps identify unused or underutilized indexes, and frequently used ones.
SELECT
    relname AS table_name,
    indexrelname AS index_name,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size,
    idx_scan AS index_scans,
    idx_tup_read AS index_tuples_read,
    idx_tup_fetch AS index_tuples_fetched
FROM
    pg_stat_user_indexes
WHERE
    idx_scan > 0 -- Only show indexes that have been used
ORDER BY
    idx_scan DESC;

-- To find potentially unused indexes (idx_scan = 0)
SELECT
    relname AS table_name,
    indexrelname AS index_name,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM
    pg_stat_user_indexes
WHERE
    idx_scan = 0 AND pg_relation_size(indexrelid) > 8192 -- Exclude very small indexes
ORDER BY
    pg_relation_size(indexrelid) DESC;

-- 4. Cache Hit Ratio (for shared buffers)
-- High hit ratio indicates efficient use of memory.
SELECT
    sum(heap_blks_read) AS heap_read,
    sum(heap_blks_hit) AS heap_hit,
    (sum(heap_blks_hit) * 100) / (sum(heap_blks_hit) + sum(heap_blks_read)) AS hit_ratio_percent
FROM
    pg_statio_user_tables;

-- 5. Database Size
-- Overall size of the database.
SELECT
    pg_database.datname,
    pg_size_pretty(pg_database_size(pg_database.datname)) AS database_size
FROM
    pg_database
WHERE
    pg_database.datname = current_database();

-- 6. Locks
-- Identifies current locks that might be causing blocking issues.
SELECT
    a.datname,
    l.relation::regclass AS locked_table,
    l.mode AS lock_mode,
    l.granted,
    a.usename,
    a.client_addr,
    a.application_name,
    a.query,
    a.query_start,
    pg_blocking_pids(l.pid) AS blocking_pids,
    l.pid AS blocked_pid
FROM
    pg_locks l
JOIN
    pg_stat_activity a ON l.pid = a.pid
WHERE
    l.granted = false
ORDER BY
    a.query_start;

-- 7. Autovacuum Activity
-- Shows current autovacuum/autoanalyze processes.
SELECT
    pid,
    datname,
    relid::regclass AS table_name,
    phase,
    heap_blks_scanned,
    heap_blks_vacuumed,
    index_vacuum_count,
    vacuum_cost_delay,
    vacuum_cost_balance,
    vacuum_shares_lock,
    (EXTRACT(EPOCH FROM (NOW() - query_start)) * 1000)::bigint AS duration_ms
FROM
    pg_stat_progress_vacuum;

-- 8. Statements by Execution Time (requires pg_stat_statements extension)
-- To enable: CREATE EXTENSION pg_stat_statements; in your database.
-- This is crucial for finding the slowest queries.
/*
SELECT
    query,
    calls,
    total_time,
    min_time,
    max_time,
    mean_time,
    stddev_time,
    rows,
    (100.0 * shared_blks_hit / (shared_blks_hit + shared_blks_read)) AS hit_percent
FROM
    pg_stat_statements
ORDER BY
    total_time DESC
LIMIT 10;
*/
-- Note: pg_stat_statements needs to be enabled in postgresql.conf and then created in the database.
-- It provides invaluable insights into query performance.