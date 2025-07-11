-- performance_monitoring_queries.sql
-- SQL queries for monitoring PostgreSQL database performance.

-- 1. Long-running Queries
-- Identifies queries that are currently running and taking a long time.
SELECT
    pid,
    datname,
    usename,
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
    AND now() - query_start > INTERVAL '5 seconds' -- Adjust threshold as needed
ORDER BY
    duration DESC;

-- 2. Index Usage Statistics
-- Shows how often indexes are used and if they are effective.
SELECT
    relname AS table_name,
    indexrelname AS index_name,
    idx_scan,       -- Number of index scans
    idx_tup_read,   -- Number of index entries returned
    idx_tup_fetch,  -- Number of live table rows fetched
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size,
    pg_size_pretty(pg_relation_size(relid)) AS table_size
FROM
    pg_stat_user_indexes
WHERE
    schemaname = 'public' -- Or your specific schema
ORDER BY
    idx_scan DESC;

-- 3. Unused Indexes (Potential candidates for removal)
-- Indexes with very low or zero scan count might be redundant.
SELECT
    s.relname AS table_name,
    s.indexrelname AS index_name,
    pg_size_pretty(pg_relation_size(s.indexrelid)) AS index_size,
    s.idx_scan,
    pg_get_indexdef(s.indexrelid) AS index_definition
FROM
    pg_stat_user_indexes s
JOIN
    pg_index i ON s.indexrelid = i.indexrelid
WHERE
    s.idx_scan = 0
    AND NOT i.indisunique -- Exclude unique indexes, as they enforce uniqueness
    AND NOT i.indisprimary -- Exclude primary key indexes
ORDER BY
    pg_relation_size(s.indexrelid) DESC;

-- 4. Table Bloat and Vacuum Statistics
-- Helps identify tables that need vacuuming or reindexing due to bloat.
SELECT
    relname AS table_name,
    n_live_tup,     -- Number of live rows
    n_dead_tup,     -- Number of dead rows (to be vacuumed)
    last_autovacuum,
    last_autoanalyze,
    pg_size_pretty(pg_relation_size(relid)) AS table_size,
    pg_size_pretty(pg_total_relation_size(relid)) AS total_size_with_indexes
FROM
    pg_stat_user_tables
WHERE
    schemaname = 'public'
ORDER BY
    n_dead_tup DESC;

-- 5. Cache Hit Ratio
-- Indicates how often data is found in memory (shared buffers) vs. disk.
-- A high hit ratio (e.g., > 99%) is desirable.
SELECT
    sum(heap_blks_read) AS heap_read,
    sum(heap_blks_hit) AS heap_hit,
    (sum(heap_blks_hit) * 100) / (sum(heap_blks_hit) + sum(heap_blks_read)) AS hit_ratio_percent
FROM
    pg_statio_user_tables;

-- 6. Disk Usage by Table
-- Shows disk space consumed by each table, ordered by size.
SELECT
    relname AS table_name,
    pg_size_pretty(pg_relation_size(relid)) AS table_size,
    pg_size_pretty(pg_total_relation_size(relid)) AS total_size_with_indexes
FROM
    pg_stat_user_tables
ORDER BY
    pg_relation_size(relid) DESC;

-- 7. Connections and Active Sessions
-- Overview of current connections and their states.
SELECT
    datname,
    usename,
    client_addr,
    state,
    count(*) AS num_connections
FROM
    pg_stat_activity
GROUP BY
    datname, usename, client_addr, state
ORDER BY
    num_connections DESC;