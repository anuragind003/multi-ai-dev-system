-- monitoring_queries.sql
-- Provides SQL queries for monitoring the health and performance of the PostgreSQL database.
-- These queries help identify bottlenecks, resource usage, and potential issues.

-- --- 1. Active Connections and Database Activity ---
SELECT
    datname,
    pid,
    usename,
    application_name,
    client_addr,
    backend_start,
    state,
    state_change,
    wait_event_type,
    wait_event,
    query_start,
    query
FROM
    pg_stat_activity
WHERE
    datname = 'vkyc_db' -- Filter for your specific database
    AND state <> 'idle'
ORDER BY
    query_start DESC;

-- --- 2. Long-Running Queries ---
-- Identify queries that have been running for a long time, potentially blocking others.
SELECT
    pid,
    usename,
    application_name,
    client_addr,
    pg_blocking_pid(pid) AS blocking_pid,
    query_start,
    now() - query_start AS duration,
    state,
    wait_event_type,
    wait_event,
    query
FROM
    pg_stat_activity
WHERE
    datname = 'vkyc_db'
    AND state = 'active'
    AND now() - query_start > INTERVAL '5 seconds' -- Adjust threshold as needed
ORDER BY
    duration DESC;

-- --- 3. Cache Hit Ratio (Buffers) ---
-- Indicates how often data is found in memory (shared buffers) vs. disk. Higher is better.
SELECT
    sum(heap_blks_read) as heap_read,
    sum(heap_blks_hit) as heap_hit,
    (sum(heap_blks_hit) - sum(heap_blks_read)) * 100 / sum(heap_blks_hit) AS ratio
FROM
    pg_statio_user_tables;
-- For specific tables:
SELECT
    relname AS table_name,
    heap_blks_read,
    heap_blks_hit,
    (heap_blks_hit - heap_blks_read) * 100 / heap_blks_hit AS hit_ratio
FROM
    pg_statio_user_tables
WHERE
    relname IN ('users', 'vkyc_recordings', 'audit_logs')
ORDER BY
    hit_ratio DESC;

-- --- 4. Index Usage Statistics ---
-- Identify unused or underused indexes, or frequently used indexes.
SELECT
    relname AS table_name,
    indexrelname AS index_name,
    idx_scan,       -- Number of index scans
    idx_tup_read,   -- Number of index entries returned
    idx_tup_fetch   -- Number of live table rows fetched
FROM
    pg_stat_user_indexes
WHERE
    relname IN ('users', 'vkyc_recordings', 'audit_logs')
ORDER BY
    idx_scan DESC;

-- --- 5. Table and Index Sizes ---
-- Monitor disk space usage for tables and their indexes.
SELECT
    relname AS table_name,
    pg_size_pretty(pg_relation_size(oid)) AS table_size,
    pg_size_pretty(pg_total_relation_size(oid)) AS total_size_with_indexes,
    pg_size_pretty(pg_indexes_size(oid)) AS indexes_size,
    reltuples AS row_count
FROM
    pg_class
WHERE
    relkind = 'r' -- 'r' for relation (table)
    AND relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public') -- Adjust schema if needed
ORDER BY
    pg_total_relation_size(oid) DESC;

-- --- 6. Disk I/O Statistics ---
-- Monitor read/write operations for tables.
SELECT
    relname AS table_name,
    blks_read,  -- Number of disk blocks read from this table
    blks_hit    -- Number of buffer hits (data found in cache)
FROM
    pg_stat_user_tables
WHERE
    relname IN ('users', 'vkyc_recordings', 'audit_logs')
ORDER BY
    blks_read DESC;

-- --- 7. Transaction Statistics ---
-- Monitor commits and rollbacks. High rollback rate might indicate application errors.
SELECT
    datname,
    xact_commit,
    xact_rollback
FROM
    pg_stat_database
WHERE
    datname = 'vkyc_db';

-- --- 8. Replication Status (if applicable) ---
-- For master/replica setups, check replication lag.
-- SELECT
--     client_addr,
--     usename,
--     application_name,
--     state,
--     sync_state,
--     sync_priority,
--     pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn) AS replication_lag_bytes
-- FROM
--     pg_stat_replication;

-- --- 9. Autovacuum Activity ---
-- Check if autovacuum is running and its status.
SELECT
    relname,
    last_autovacuum,
    last_autoanalyze,
    autovacuum_count,
    analyze_count
FROM
    pg_stat_user_tables
WHERE
    relname IN ('users', 'vkyc_recordings', 'audit_logs')
ORDER BY
    autovacuum_count DESC;