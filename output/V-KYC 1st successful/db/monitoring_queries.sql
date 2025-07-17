-- db/monitoring_queries.sql
-- This file contains SQL queries useful for monitoring the health and performance
-- of the PostgreSQL database. These queries help identify bottlenecks,
-- resource usage, and potential issues.

-- =============================================================================
-- 1. ACTIVE CONNECTIONS AND SESSIONS
-- =============================================================================

-- Get current active connections
SELECT
    pid,
    usename,
    datname,
    client_addr,
    application_name,
    backend_start,
    state,
    query_start,
    query
FROM
    pg_stat_activity
WHERE
    state = 'active'
ORDER BY
    query_start ASC;

-- Get all connections, including idle ones
SELECT
    pid,
    usename,
    datname,
    client_addr,
    application_name,
    backend_start,
    state,
    state_change,
    wait_event_type,
    wait_event,
    query_start,
    query
FROM
    pg_stat_activity
ORDER BY
    backend_start DESC;

-- Count connections by state
SELECT
    state,
    COUNT(*) AS connection_count
FROM
    pg_stat_activity
GROUP BY
    state
ORDER BY
    connection_count DESC;

-- =============================================================================
-- 2. LONG-RUNNING QUERIES
-- =============================================================================

-- Identify queries running longer than a threshold (e.g., 5 seconds)
SELECT
    pid,
    usename,
    datname,
    client_addr,
    application_name,
    query_start,
    now() - query_start AS duration,
    state,
    wait_event_type,
    wait_event,
    query
FROM
    pg_stat_activity
WHERE
    state = 'active'
    AND (now() - query_start) > INTERVAL '5 seconds'
ORDER BY
    duration DESC;

-- =============================================================================
-- 3. INDEX USAGE AND EFFICIENCY
-- =============================================================================

-- Get index usage statistics for all tables
SELECT
    relname AS table_name,
    indexrelname AS index_name,
    idx_scan AS index_scans,
    idx_tup_read AS tuples_read_by_index,
    idx_tup_fetch AS tuples_fetched_by_index
FROM
    pg_stat_user_indexes
ORDER BY
    idx_scan DESC;

-- Identify unused indexes (idx_scan = 0)
SELECT
    relname AS table_name,
    indexrelname AS index_name,
    pg_size_pretty(pg_relation_size(idx.indexrelid)) AS index_size
FROM
    pg_stat_user_indexes idx
JOIN
    pg_index i ON i.indexrelid = idx.indexrelid
WHERE
    idx.idx_scan = 0
    AND NOT i.indisunique -- Exclude unique indexes, as they enforce uniqueness
    AND NOT i.indisprimary -- Exclude primary key indexes
ORDER BY
    pg_relation_size(idx.indexrelid) DESC;

-- =============================================================================
-- 4. TABLE BLOAT AND VACUUM STATISTICS
-- =============================================================================

-- Get table statistics (useful for identifying bloat and vacuum needs)
SELECT
    relname AS table_name,
    n_live_tup AS live_tuples,
    n_dead_tup AS dead_tuples,
    last_autovacuum,
    last_autoanalyze,
    autovacuum_count,
    autoanalyze_count
FROM
    pg_stat_user_tables
ORDER BY
    n_dead_tup DESC;

-- Estimate table bloat (requires pg_stat_statements and pgstattuple extension for more accuracy)
-- This is a simplified estimate.
SELECT
    relname AS table_name,
    pg_size_pretty(pg_relation_size(relid)) AS table_size,
    pg_size_pretty(pg_total_relation_size(relid) - pg_relation_size(relid)) AS indexes_size,
    n_dead_tup AS dead_tuples,
    n_live_tup AS live_tuples,
    (n_dead_tup * 100 / (n_live_tup + n_dead_tup + 1)) AS dead_tuple_percentage
FROM
    pg_stat_user_tables
ORDER BY
    dead_tuple_percentage DESC;

-- =============================================================================
-- 5. DISK USAGE
-- =============================================================================

-- Get database size
SELECT
    pg_size_pretty(pg_database_size(current_database())) AS database_size;

-- Get table sizes
SELECT
    relname AS table_name,
    pg_size_pretty(pg_relation_size(relid)) AS table_size,
    pg_size_pretty(pg_total_relation_size(relid)) AS total_size_with_indexes
FROM
    pg_stat_user_tables
ORDER BY
    pg_relation_size(relid) DESC;

-- =============================================================================
-- 6. CACHE HIT RATIO
-- =============================================================================

-- Get cache hit ratio for the entire database
SELECT
    sum(heap_blks_read) AS heap_read,
    sum(heap_blks_hit) AS heap_hit,
    (sum(heap_blks_hit) * 100) / (sum(heap_blks_hit) + sum(heap_blks_read)) AS hit_ratio_percentage
FROM
    pg_statio_user_tables;

-- =============================================================================
-- 7. REPLICATION STATUS (if applicable)
-- =============================================================================

-- Check replication lag (on standby/replica)
-- SELECT
--     pg_last_wal_receive_lsn(),
--     pg_last_wal_replay_lsn(),
--     pg_last_wal_receive_lsn() - pg_last_wal_replay_lsn() AS replication_lag_bytes;

-- Check replication slots (on primary)
-- SELECT * FROM pg_replication_slots;

-- =============================================================================
-- 8. ERROR LOGS (requires access to PostgreSQL logs, not SQL query)
-- =============================================================================
-- Review PostgreSQL server logs for errors, warnings, and critical messages.
-- Location typically defined in postgresql.conf (e.g., log_directory, log_filename).
-- Example: tail -f /var/log/postgresql/postgresql-*.log