-- performance_monitoring.sql
-- SQL queries for monitoring PostgreSQL database performance and health.

-- 1. Active and Idle Connections
-- Identify active queries, idle connections, and their duration.
SELECT
    pid,
    datname,
    usename,
    application_name,
    client_addr,
    backend_start,
    state,
    state_change,
    query_start,
    query,
    wait_event_type,
    wait_event
FROM
    pg_stat_activity
WHERE
    datname = current_database()
ORDER BY
    query_start DESC;

-- 2. Long-Running Queries
-- Find queries that have been running for a long time, potentially blocking others.
SELECT
    pid,
    usename,
    application_name,
    client_addr,
    pg_blocking_pids(pid) AS blocking_pids,
    query_start,
    now() - query_start AS query_duration,
    state,
    query
FROM
    pg_stat_activity
WHERE
    state = 'active' AND
    now() - query_start > INTERVAL '5 seconds' -- Adjust threshold as needed
ORDER BY
    query_duration DESC;

-- 3. Table Sizes and Disk Usage
-- Get estimated size of tables and their indexes.
SELECT
    relname AS table_name,
    pg_size_pretty(pg_relation_size(oid)) AS table_size,
    pg_size_pretty(pg_total_relation_size(oid)) AS total_size_with_indexes,
    reltuples AS row_count
FROM
    pg_class
WHERE
    relkind = 'r' AND relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
ORDER BY
    pg_total_relation_size(oid) DESC;

-- 4. Index Usage Statistics
-- Identify unused or rarely used indexes, or heavily used indexes.
SELECT
    s.relname AS table_name,
    s.indexrelname AS index_name,
    pg_size_pretty(pg_relation_size(s.indexrelid)) AS index_size,
    s.idx_scan AS index_scans,
    s.idx_tup_read AS index_tuples_read,
    s.idx_tup_fetch AS index_tuples_fetched
FROM
    pg_stat_user_indexes s
JOIN
    pg_index i ON s.indexrelid = i.indexrelid
WHERE
    s.relname IN ('users', 'vkyc_recordings', 'audit_logs') -- Focus on our tables
ORDER BY
    s.idx_scan ASC; -- Order by least used to find candidates for removal

-- 5. Cache Hit Ratio
-- Check efficiency of shared buffers. A high hit ratio (e.g., > 99%) is desirable.
SELECT
    sum(heap_blks_read) AS heap_read,
    sum(heap_blks_hit) AS heap_hit,
    (sum(heap_blks_hit) - sum(heap_blks_read)) * 100 / sum(heap_blks_hit) AS ratio
FROM
    pg_statio_user_tables;

-- 6. Table Scan Statistics (Sequential vs. Index Scans)
-- Identify tables that are frequently undergoing sequential scans, which can be slow.
SELECT
    relname AS table_name,
    seq_scan AS sequential_scans,
    idx_scan AS index_scans,
    seq_tup_read AS sequential_tuples_read,
    idx_tup_fetch AS index_tuples_fetched
FROM
    pg_stat_user_tables
WHERE
    relname IN ('users', 'vkyc_recordings', 'audit_logs')
ORDER BY
    seq_scan DESC;

-- 7. Blocking Queries
-- Identify queries that are currently holding locks and blocking other queries.
SELECT
    blocking_locks.pid AS blocking_pid,
    blocking_activity.usename AS blocking_user,
    blocking_activity.query AS blocking_query,
    blocked_locks.pid AS blocked_pid,
    blocked_activity.usename AS blocked_user,
    blocked_activity.query AS blocked_query,
    blocked_activity.wait_event_type,
    blocked_activity.wait_event
FROM
    pg_catalog.pg_locks AS blocking_locks
JOIN
    pg_catalog.pg_stat_activity AS blocking_activity ON blocking_activity.pid = blocking_locks.pid
JOIN
    pg_catalog.pg_locks AS blocked_locks ON blocked_locks.locktype = blocking_locks.locktype
    AND blocked_locks.database IS NOT DISTINCT FROM blocking_locks.database
    AND blocked_locks.relation IS NOT DISTINCT FROM blocking_locks.relation
    AND blocked_locks.page IS NOT DISTINCT FROM blocking_locks.page
    AND blocked_locks.tuple IS NOT DISTINCT FROM blocking_locks.tuple
    AND blocked_locks.transactionid IS NOT DISTINCT FROM blocking_locks.transactionid
    AND blocked_locks.classid IS NOT DISTINCT FROM blocking_locks.classid
    AND blocked_locks.objid IS NOT DISTINCT FROM blocking_locks.objid
    AND blocked_locks.objsubid IS NOT DISTINCT FROM blocking_locks.objsubid
    AND blocked_locks.pid != blocking_locks.pid
JOIN
    pg_catalog.pg_stat_activity AS blocked_activity ON blocked_activity.pid = blocked_locks.pid
WHERE
    NOT blocking_locks.granted;

-- 8. Database Configuration Parameters
-- Review important configuration settings that impact performance.
SELECT name, setting, unit, short_desc
FROM pg_settings
WHERE category IN ('Connections and Authentication', 'Resource Usage (Memory)', 'Resource Usage (Disk)', 'Write Ahead Log', 'Query Planning')
ORDER BY category, name;