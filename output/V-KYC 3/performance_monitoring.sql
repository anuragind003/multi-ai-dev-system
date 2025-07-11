-- performance_monitoring.sql
-- A collection of SQL queries for monitoring PostgreSQL database performance.
-- These queries help identify bottlenecks, inefficient queries, and resource usage.

-- 1. Active and Idle Connections
-- Shows current connections, their state, and the query they are executing.
SELECT
    pid,
    usename,
    datname,
    client_addr,
    application_name,
    backend_start,
    state,
    state_change,
    query_start,
    query
FROM
    pg_stat_activity
WHERE
    datname = current_database() AND state <> 'idle'
ORDER BY
    query_start DESC;

-- 2. Long-Running Queries
-- Identifies queries that have been running for a long time, potentially blocking others.
SELECT
    pid,
    usename,
    application_name,
    client_addr,
    pg_blocking_pid(pid) AS blocking_pid,
    query_start,
    now() - query_start AS duration,
    state,
    query
FROM
    pg_stat_activity
WHERE
    datname = current_database() AND state = 'active'
ORDER BY
    duration DESC
LIMIT 10;

-- 3. Index Usage Statistics
-- Shows how often indexes are used and if they are effective.
SELECT
    relname AS table_name,
    indexrelname AS index_name,
    idx_scan,       -- Number of index scans
    idx_tup_read,   -- Number of index entries returned by scans
    idx_tup_fetch   -- Number of live table rows fetched by index scans
FROM
    pg_stat_user_indexes
WHERE
    relname IN ('users', 'vkyc_recordings', 'audit_logs')
ORDER BY
    idx_scan DESC;

-- 4. Table Statistics (Scans, Tuples Read/Inserted/Updated/Deleted)
-- Provides insights into table activity and potential bloat.
SELECT
    relname AS table_name,
    pg_size_pretty(pg_relation_size(relid)) AS table_size,
    seq_scan,       -- Number of sequential scans
    idx_scan,       -- Number of index scans
    n_tup_ins,      -- Number of rows inserted
    n_tup_upd,      -- Number of rows updated
    n_tup_del,      -- Number of rows deleted
    n_live_tup,     -- Number of live rows
    n_dead_tup,     -- Number of dead rows (potential bloat)
    last_autovacuum,
    last_autoanalyze
FROM
    pg_stat_user_tables
WHERE
    relname IN ('users', 'vkyc_recordings', 'audit_logs')
ORDER BY
    pg_relation_size(relid) DESC;

-- 5. Cache Hit Ratio
-- Indicates how effectively PostgreSQL is using its shared buffers. High ratio is good.
SELECT
    sum(heap_blks_read) as heap_read,
    sum(heap_blks_hit) as heap_hit,
    (sum(heap_blks_hit) * 100) / (sum(heap_blks_hit) + sum(heap_blks_read)) as ratio
FROM
    pg_statio_user_tables
WHERE
    relname IN ('users', 'vkyc_recordings', 'audit_logs');

-- 6. Disk Usage by Table
-- Shows the disk space consumed by each table, including indexes and TOAST data.
SELECT
    relname AS table_name,
    pg_size_pretty(pg_total_relation_size(relid)) AS total_size,
    pg_size_pretty(pg_relation_size(relid)) AS table_only_size,
    pg_size_pretty(pg_indexes_size(relid)) AS indexes_size,
    pg_size_pretty(pg_relation_size(relid) - pg_relation_size(relid, 'main')) AS toast_size -- Size of TOAST table
FROM
    pg_stat_user_tables
WHERE
    relname IN ('users', 'vkyc_recordings', 'audit_logs')
ORDER BY
    pg_total_relation_size(relid) DESC;

-- 7. Missing Indexes (requires pg_stat_statements extension and configuration)
-- This query is more advanced and requires the `pg_stat_statements` extension to be enabled
-- and configured in `postgresql.conf` (shared_preload_libraries = 'pg_stat_statements').
-- It helps identify queries that are frequently executed but might be slow due to missing indexes.
/*
SELECT
    query,
    calls,
    total_time,
    mean_time,
    rows,
    100.0 * shared_blks_hit / (shared_blks_hit + shared_blks_read) AS hit_ratio,
    temp_blks_read,
    temp_blks_written
FROM
    pg_stat_statements
ORDER BY
    total_time DESC
LIMIT 10;
*/

-- 8. Autovacuum Activity
-- Monitors autovacuum and autoanalyze operations, which are crucial for performance.
SELECT
    relname,
    last_autovacuum,
    last_autoanalyze,
    autovacuum_count,
    autoanalyze_count
FROM
    pg_stat_user_tables
WHERE
    relname IN ('users', 'vkyc_recordings', 'audit_logs')
ORDER BY
    autovacuum_count DESC;

-- 9. Replication Lag (if using replication)
-- For monitoring standby servers in a replication setup.
/*
SELECT
    client_addr,
    usename,
    application_name,
    state,
    sync_state,
    pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn) AS replication_lag_bytes,
    (now() - pg_last_xact_replay_timestamp()) AS replication_lag_time
FROM
    pg_stat_replication;
*/