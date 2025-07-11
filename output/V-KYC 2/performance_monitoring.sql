-- performance_monitoring.sql
-- SQL queries for monitoring PostgreSQL database performance.
-- These queries help identify bottlenecks, inefficient queries, and resource usage.

-- 1. Long-Running Queries
-- Identifies queries that are currently running for a long time, which might indicate
-- inefficient queries or blocking issues.
SELECT
    pid,
    usename,
    datname,
    client_addr,
    application_name,
    backend_start,
    state,
    query_start,
    now() - query_start AS duration,
    wait_event_type,
    wait_event,
    query
FROM
    pg_stat_activity
WHERE
    state = 'active'
    AND usename <> 'postgres' -- Exclude postgres internal processes
    AND now() - query_start > INTERVAL '10 seconds' -- Adjust threshold as needed
ORDER BY
    duration DESC;

-- 2. Cache Hit Ratio
-- Shows how effectively PostgreSQL is using its shared buffers. A high ratio (e.g., > 99%)
-- indicates good caching; lower values might suggest insufficient memory or poor indexing.
SELECT
    sum(heap_blks_read) as heap_read,
    sum(heap_blks_hit) as heap_hit,
    (sum(heap_blks_hit) - sum(heap_blks_read)) / sum(heap_blks_hit) AS ratio,
    (sum(heap_blks_hit) * 100) / (sum(heap_blks_hit) + sum(heap_blks_read)) AS hit_ratio_percent
FROM
    pg_statio_user_tables;

-- 3. Index Usage Statistics
-- Identifies indexes that are heavily used (idx_scan) or rarely used (potential candidates for removal).
SELECT
    relname AS table_name,
    indexrelname AS index_name,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM
    pg_stat_user_indexes
ORDER BY
    idx_scan DESC;

-- 4. Table and Index Sizes
-- Helps monitor database growth and identify large tables/indexes that might need optimization.
SELECT
    relname AS table_name,
    pg_size_pretty(pg_relation_size(oid)) AS table_size,
    pg_size_pretty(pg_total_relation_size(oid)) AS total_size,
    pg_size_pretty(pg_indexes_size(oid)) AS indexes_size,
    reltuples AS row_count
FROM
    pg_class
WHERE
    relkind = 'r' -- 'r' for relation (table)
    AND relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public') -- Only public schema
ORDER BY
    pg_total_relation_size(oid) DESC;

-- 5. Autovacuum Activity
-- Checks the last time tables were vacuumed or analyzed, which is crucial for performance
-- (prevents table bloat, updates statistics for query planner).
SELECT
    relname AS table_name,
    last_vacuum,
    last_autovacuum,
    last_analyze,
    last_autoanalyze,
    vacuum_count,
    autovacuum_count,
    analyze_count,
    autoanalyze_count
FROM
    pg_stat_user_tables
ORDER BY
    last_autovacuum DESC NULLS LAST;

-- 6. Disk I/O Statistics
-- Provides insights into read/write operations on tables and indexes.
SELECT
    relname AS table_name,
    heap_blks_read,
    heap_blks_hit,
    idx_blks_read,
    idx_blks_hit,
    toast_blks_read,
    toast_blks_hit,
    tidx_blks_read,
    tidx_blks_hit
FROM
    pg_statio_user_tables
ORDER BY
    (heap_blks_read + idx_blks_read) DESC;

-- 7. Missing Indexes (Potential candidates)
-- This is a heuristic. It looks for sequential scans on tables that are frequently updated.
-- A high seq_scan count on a large table often indicates a missing index.
SELECT
    relname AS table_name,
    seq_scan,
    idx_scan,
    seq_tup_read,
    idx_tup_fetch,
    n_tup_ins,
    n_tup_upd,
    n_tup_del
FROM
    pg_stat_user_tables
WHERE
    seq_scan > 0 -- Has had sequential scans
    AND reltuples > 1000 -- Only consider larger tables
ORDER BY
    seq_scan DESC;

-- 8. Database Size
-- Overall size of the database.
SELECT
    pg_size_pretty(pg_database_size(current_database())) AS database_size;

-- 9. Connection Count
-- Number of active connections, useful for monitoring connection limits.
SELECT
    count(*) AS total_connections,
    sum(CASE WHEN state = 'active' THEN 1 ELSE 0 END) AS active_connections,
    sum(CASE WHEN state = 'idle in transaction' THEN 1 ELSE 0 END) AS idle_in_transaction,
    sum(CASE WHEN state = 'idle' THEN 1 ELSE 0 END) AS idle_connections
FROM
    pg_stat_activity;