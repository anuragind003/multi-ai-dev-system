-- performance_monitoring_queries.sql
-- SQL queries for monitoring PostgreSQL database performance.

-- 1. Active and Idle Connections
SELECT
    datname,
    usename,
    client_addr,
    state,
    backend_type,
    COUNT(*) AS connection_count
FROM pg_stat_activity
GROUP BY datname, usename, client_addr, state, backend_type
ORDER BY connection_count DESC;

-- 2. Currently Running Queries (Long-running queries)
SELECT
    pid,
    datname,
    usename,
    client_addr,
    application_name,
    backend_start,
    query_start,
    state_change,
    state,
    wait_event_type,
    wait_event,
    query,
    (NOW() - query_start) AS duration
FROM pg_stat_activity
WHERE state = 'active'
AND (NOW() - query_start) > INTERVAL '5 seconds' -- Adjust threshold as needed
ORDER BY duration DESC;

-- 3. Table Sizes (Top 10 largest tables)
SELECT
    relname AS table_name,
    pg_size_pretty(pg_relation_size(oid)) AS data_size,
    pg_size_pretty(pg_total_relation_size(oid) - pg_relation_size(oid)) AS index_size,
    pg_size_pretty(pg_total_relation_size(oid)) AS total_size
FROM pg_class
WHERE relkind = 'r' -- 'r' for relation (table)
AND relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public') -- Only public schema
ORDER BY pg_total_relation_size(oid) DESC
LIMIT 10;

-- 4. Index Usage Statistics (Top 10 least used indexes)
-- Helps identify potentially unused or inefficient indexes
SELECT
    s.relname AS table_name,
    s.indexrelname AS index_name,
    pg_size_pretty(pg_relation_size(s.indexrelid)) AS index_size,
    s.idx_scan AS index_scans,
    s.idx_tup_read AS tuples_read_by_index,
    s.idx_tup_fetch AS tuples_fetched_by_index
FROM pg_stat_user_indexes s
JOIN pg_index i ON s.indexrelid = i.indexrelid
WHERE s.schemaname = 'public'
AND s.idx_scan = 0 -- Indexes that have never been used
ORDER BY pg_relation_size(s.indexrelid) DESC; -- Order by size to see large unused indexes

-- 5. Cache Hit Ratio for Database
-- A high hit ratio (e.g., > 99%) indicates efficient use of shared buffers.
SELECT
    sum(blks_read) AS total_blocks_read,
    sum(blks_hit) AS total_blocks_hit,
    (sum(blks_hit) * 100) / sum(blks_read) AS hit_ratio_percent
FROM pg_stat_database
WHERE datname = current_database();

-- 6. Table Scan Statistics (Sequential vs. Index Scans)
-- High seq_scan count on large tables might indicate missing indexes.
SELECT
    relname AS table_name,
    seq_scan,
    idx_scan,
    seq_tup_read,
    idx_tup_fetch
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY seq_scan DESC
LIMIT 10;

-- 7. Dead Tuples and Vacuum Activity
-- High n_dead_tup indicates need for VACUUM/AUTOVACUUM.
SELECT
    relname AS table_name,
    n_live_tup AS live_tuples,
    n_dead_tup AS dead_tuples,
    last_autovacuum,
    last_autoanalyze
FROM pg_stat_user_tables
WHERE schemaname = 'public'
AND n_dead_tup > 0
ORDER BY n_dead_tup DESC
LIMIT 10;

-- 8. Replication Status (if applicable)
-- For monitoring standby servers in a replication setup.
-- SELECT
--     pid,
--     usename,
--     application_name,
--     client_addr,
--     state,
--     sync_state,
--     sync_priority,
--     pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn) AS lag_bytes
-- FROM pg_stat_replication;

-- 9. Disk Usage by Tablespace (if custom tablespaces are used)
-- SELECT
--     spcname AS tablespace_name,
--     pg_size_pretty(pg_tablespace_size(oid)) AS tablespace_size
-- FROM pg_tablespace;

-- 10. Database Size
SELECT
    pg_database.datname,
    pg_size_pretty(pg_database_size(pg_database.datname)) AS database_size
FROM pg_database
WHERE pg_database.datname = current_database();