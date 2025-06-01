import sqlite3
import json
import os
import threading
import time
from typing import Dict, Any, Optional, List
from contextlib import contextmanager
from collections import defaultdict
import hashlib

class HighPerformanceSharedMemory:
    """Enhanced shared memory with batch operations and performance optimization."""
    
    def __init__(self, run_dir: str = None, batch_size: int = 100):
        if run_dir:
            self.db_path = os.path.join(run_dir, "run_memory.db")
        else:
            self.db_path = "memory.db"
            print("⚠️ Warning: HighPerformanceSharedMemory initialized without run_dir.")
        
        self.batch_size = batch_size
        self._connection_pool = {}
        self._batch_operations = []
        self._last_batch_time = time.time()
        self._batch_lock = threading.Lock()
        self._write_cache = {}
        self._read_cache = {}
        self._cache_ttl = 300  # 5 minutes
        self._cache_timestamps = {}
        
        self._connect_db()
        self._init_db()
        
        # Start background batch processor
        self._batch_thread = threading.Thread(target=self._batch_processor, daemon=True)
        self._batch_thread.start()
    
    def _connect_db(self):
        """Create connection pool for better performance."""
        thread_id = threading.get_ident()
        
        if thread_id not in self._connection_pool:
            self._connection_pool[thread_id] = sqlite3.connect(
                self.db_path,
                timeout=30.0,
                isolation_level=None,  # Autocommit mode
                check_same_thread=False
            )
            
            # Optimize SQLite settings for performance
            conn = self._connection_pool[thread_id]
            conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
            conn.execute("PRAGMA synchronous=NORMAL")  # Faster writes
            conn.execute("PRAGMA cache_size=10000")  # Larger cache
            conn.execute("PRAGMA temp_store=MEMORY")  # In-memory temp tables
        
        return self._connection_pool[thread_id]
    
    def _init_db(self):
        """Initialize database schema with performance optimizations."""
        conn = self._connect_db()
        cursor = conn.cursor()
        
        # Enhanced schema with indexing
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory (
                key TEXT PRIMARY KEY,
                value TEXT,
                value_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                access_count INTEGER DEFAULT 0,
                size_bytes INTEGER,
                checksum TEXT
            )
        """)
        
        # Performance indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_updated_at ON memory(updated_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_access_count ON memory(access_count)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_size ON memory(size_bytes)")
        
        # Agent results table for better organization
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_results (
                agent_name TEXT,
                execution_id TEXT,
                result_data TEXT,
                execution_time REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT,
                PRIMARY KEY (agent_name, execution_id)
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_results_time ON agent_results(created_at)")
        
        conn.commit()
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = self._connect_db()
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            raise e
    
    def set(self, key: str, value: Any, immediate: bool = False):
        """Set value with optional batching for high-performance scenarios."""
        
        # Serialize value
        if isinstance(value, (dict, list)):
            serialized_value = json.dumps(value, ensure_ascii=False)
            value_type = "json"
        else:
            serialized_value = str(value)
            value_type = "string"
        
        # Calculate metadata
        size_bytes = len(serialized_value.encode('utf-8'))
        checksum = hashlib.md5(serialized_value.encode('utf-8')).hexdigest()
        
        # Update caches
        self._write_cache[key] = {
            'value': value,
            'serialized': serialized_value,
            'type': value_type,
            'size': size_bytes,
            'checksum': checksum,
            'timestamp': time.time()
        }
        
        if key in self._read_cache:
            del self._read_cache[key]
        
        if immediate or len(self._batch_operations) >= self.batch_size:
            self._flush_batch()
        else:
            # Add to batch
            with self._batch_lock:
                self._batch_operations.append({
                    'operation': 'set',
                    'key': key,
                    'value': serialized_value,
                    'type': value_type,
                    'size': size_bytes,
                    'checksum': checksum
                })
    
    def get(self, key: str, default=None) -> Any:
        """Get value with intelligent caching."""
        
        # Check write cache first (most recent)
        if key in self._write_cache:
            cache_entry = self._write_cache[key]
            if time.time() - cache_entry['timestamp'] < self._cache_ttl:
                return cache_entry['value']
        
        # Check read cache
        if key in self._read_cache:
            cache_entry = self._read_cache[key]
            if time.time() - cache_entry['timestamp'] < self._cache_ttl:
                return cache_entry['value']
        
        # Fetch from database
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT value, value_type FROM memory WHERE key = ?",
                    (key,)
                )
                result = cursor.fetchone()
                
                if result:
                    value_str, value_type = result
                    
                    # Deserialize
                    if value_type == "json":
                        value = json.loads(value_str)
                    else:
                        value = value_str
                    
                    # Update read cache
                    self._read_cache[key] = {
                        'value': value,
                        'timestamp': time.time()
                    }
                    
                    # Update access count asynchronously
                    with self._batch_lock:
                        self._batch_operations.append({
                            'operation': 'update_access',
                            'key': key
                        })
                    
                    return value
                else:
                    return default
                    
        except Exception as e:
            print(f"⚠️ Error retrieving key '{key}': {e}")
            return default
    
    def batch_set(self, data_dict: Dict[str, Any], immediate: bool = True):
        """Set multiple values in an optimized batch operation."""
        
        for key, value in data_dict.items():
            self.set(key, value, immediate=False)
        
        if immediate:
            self._flush_batch()
    
    def batch_get(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values in a single database operation."""
        
        results = {}
        db_keys = []
        
        # Check caches first
        for key in keys:
            cached_value = None
            
            # Check write cache
            if key in self._write_cache:
                cache_entry = self._write_cache[key]
                if time.time() - cache_entry['timestamp'] < self._cache_ttl:
                    cached_value = cache_entry['value']
            
            # Check read cache
            elif key in self._read_cache:
                cache_entry = self._read_cache[key]
                if time.time() - cache_entry['timestamp'] < self._cache_ttl:
                    cached_value = cache_entry['value']
            
            if cached_value is not None:
                results[key] = cached_value
            else:
                db_keys.append(key)
        
        # Fetch remaining keys from database
        if db_keys:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    # Use parameterized query for multiple keys
                    placeholders = ','.join(['?' for _ in db_keys])
                    cursor.execute(
                        f"SELECT key, value, value_type FROM memory WHERE key IN ({placeholders})",
                        db_keys
                    )
                    
                    for key, value_str, value_type in cursor.fetchall():
                        # Deserialize
                        if value_type == "json":
                            value = json.loads(value_str)
                        else:
                            value = value_str
                        
                        results[key] = value
                        
                        # Update read cache
                        self._read_cache[key] = {
                            'value': value,
                            'timestamp': time.time()
                        }
                        
            except Exception as e:
                print(f"⚠️ Error in batch_get: {e}")
        
        return results
    
    def _flush_batch(self):
        """Flush pending batch operations to database."""
        
        if not self._batch_operations:
            return
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Group operations by type for efficiency
                set_operations = []
                update_operations = []
                
                with self._batch_lock:
                    for op in self._batch_operations:
                        if op['operation'] == 'set':
                            set_operations.append((
                                op['key'], op['value'], op['type'],
                                op['size'], op['checksum']
                            ))
                        elif op['operation'] == 'update_access':
                            update_operations.append((op['key'],))
                    
                    self._batch_operations.clear()
                
                # Execute batch sets
                if set_operations:
                    cursor.executemany("""
                        INSERT OR REPLACE INTO memory 
                        (key, value, value_type, updated_at, size_bytes, checksum)
                        VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?, ?)
                    """, set_operations)
                
                # Execute batch access count updates
                if update_operations:
                    cursor.executemany("""
                        UPDATE memory SET access_count = access_count + 1 
                        WHERE key = ?
                    """, update_operations)
                
                conn.commit()
                self._last_batch_time = time.time()
                
        except Exception as e:
            print(f"⚠️ Error flushing batch operations: {e}")
    
    def _batch_processor(self):
        """Background thread to periodically flush batches."""
        
        while True:
            time.sleep(5)  # Check every 5 seconds
            
            # Flush if batch is old enough or large enough
            if (self._batch_operations and 
                (time.time() - self._last_batch_time > 10 or 
                 len(self._batch_operations) >= self.batch_size)):
                self._flush_batch()
            
            # Clean old cache entries
            self._clean_cache()
    
    def _clean_cache(self):
        """Clean expired cache entries."""
        
        current_time = time.time()
        
        # Clean read cache
        expired_keys = [
            key for key, entry in self._read_cache.items()
            if current_time - entry['timestamp'] > self._cache_ttl
        ]
        
        for key in expired_keys:
            del self._read_cache[key]
        
        # Clean write cache (keep more recent entries)
        expired_keys = [
            key for key, entry in self._write_cache.items()
            if current_time - entry['timestamp'] > self._cache_ttl * 2
        ]
        
        for key in expired_keys:
            del self._write_cache[key]
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Database stats
                cursor.execute("SELECT COUNT(*) FROM memory")
                total_records = cursor.fetchone()[0]
                
                cursor.execute("SELECT SUM(size_bytes) FROM memory")
                total_size = cursor.fetchone()[0] or 0
                
                cursor.execute("SELECT AVG(access_count) FROM memory")
                avg_access = cursor.fetchone()[0] or 0
                
                return {
                    "database": {
                        "total_records": total_records,
                        "total_size_mb": total_size / (1024 * 1024),
                        "average_access_count": round(avg_access, 2)
                    },
                    "cache": {
                        "read_cache_size": len(self._read_cache),
                        "write_cache_size": len(self._write_cache),
                        "pending_batch_operations": len(self._batch_operations)
                    },
                    "performance": {
                        "last_batch_flush": self._last_batch_time,
                        "cache_ttl_seconds": self._cache_ttl,
                        "batch_size": self.batch_size
                    }
                }
                
        except Exception as e:
            return {"error": str(e)}
    
    def close(self):
        """Clean shutdown with batch flush."""
        
        # Flush any pending operations
        self._flush_batch()
        
        # Close all connections
        for conn in self._connection_pool.values():
            try:
                conn.close()
            except Exception as e:
                print(f"⚠️ Error closing connection: {e}")
        
        self._connection_pool.clear()
        print("✅ High-performance shared memory closed successfully")


# ADD THE MISSING CLASS: Compatibility wrapper for main.py
class SharedProjectMemory(HighPerformanceSharedMemory):
    """
    ADDED: Compatibility wrapper for main.py import.
    
    This class provides a project-specific interface around HighPerformanceSharedMemory
    with additional methods tailored for the Multi-AI Development System workflow.
    """
    
    def __init__(self, run_dir: str = None):
        """Initialize with project-specific defaults."""
        super().__init__(run_dir=run_dir, batch_size=50)  # Smaller batch size for responsiveness
        
        # Project-specific initialization
        self._agent_results = {}
        self._execution_metadata = {}
        
        print(f"✅ SharedProjectMemory initialized (DB: {self.db_path})")
    
    def store_agent_result(self, agent_name: str, result: Dict[str, Any], execution_time: float = 0.0):
        """Store agent execution result with metadata."""
        
        execution_id = f"{agent_name}_{int(time.time())}"
        
        # Store in main memory
        self.set(f"agent_result:{agent_name}", result, immediate=True)
        
        # Store in agent results table for history
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO agent_results 
                    (agent_name, execution_id, result_data, execution_time, metadata)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    agent_name,
                    execution_id,
                    json.dumps(result, ensure_ascii=False),
                    execution_time,
                    json.dumps({"timestamp": time.time(), "status": "completed"})
                ))
                conn.commit()
                
        except Exception as e:
            print(f"⚠️ Error storing agent result for {agent_name}: {e}")
    
    def get_agent_result(self, agent_name: str, default=None) -> Dict[str, Any]:
        """Get the latest result for a specific agent."""
        return self.get(f"agent_result:{agent_name}", default)
    
    def get_all_agent_results(self) -> Dict[str, Any]:
        """Get all stored agent results."""
        
        results = {}
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT agent_name, result_data, execution_time, created_at
                    FROM agent_results 
                    ORDER BY created_at DESC
                """)
                
                for agent_name, result_data, execution_time, created_at in cursor.fetchall():
                    if agent_name not in results:  # Get most recent result
                        try:
                            results[agent_name] = {
                                "result": json.loads(result_data),
                                "execution_time": execution_time,
                                "created_at": created_at
                            }
                        except json.JSONDecodeError:
                            continue
                            
        except Exception as e:
            print(f"⚠️ Error retrieving all agent results: {e}")
        
        return results
    
    def store_workflow_state(self, state: Dict[str, Any]):
        """Store the complete workflow state."""
        self.set("workflow_state", state, immediate=True)
    
    def get_workflow_state(self) -> Dict[str, Any]:
        """Get the current workflow state."""
        return self.get("workflow_state", {})
    
    def store_execution_metadata(self, metadata: Dict[str, Any]):
        """Store execution metadata like timestamps, configuration, etc."""
        self.set("execution_metadata", metadata, immediate=True)
    
    def get_execution_metadata(self) -> Dict[str, Any]:
        """Get execution metadata."""
        return self.get("execution_metadata", {})
    
    def clear_agent_results(self):
        """Clear all agent results (useful for new runs)."""
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Clear agent results table
                cursor.execute("DELETE FROM agent_results")
                
                # Clear agent result keys from memory
                cursor.execute("DELETE FROM memory WHERE key LIKE 'agent_result:%'")
                
                conn.commit()
                print("✅ Agent results cleared")
                
        except Exception as e:
            print(f"⚠️ Error clearing agent results: {e}")
    
    def get_project_summary(self) -> Dict[str, Any]:
        """Get a summary of the project execution state."""
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Count agent results
                cursor.execute("SELECT COUNT(DISTINCT agent_name) FROM agent_results")
                completed_agents = cursor.fetchone()[0]
                
                # Get total execution time
                cursor.execute("SELECT SUM(execution_time) FROM agent_results")
                total_execution_time = cursor.fetchone()[0] or 0.0
                
                # Get latest activity
                cursor.execute("""
                    SELECT agent_name, created_at 
                    FROM agent_results 
                    ORDER BY created_at DESC 
                    LIMIT 1
                """)
                latest_result = cursor.fetchone()
                
                return {
                    "completed_agents": completed_agents,
                    "total_execution_time": total_execution_time,
                    "latest_agent": latest_result[0] if latest_result else None,
                    "latest_activity": latest_result[1] if latest_result else None,
                    "performance_stats": self.get_performance_stats()
                }
                
        except Exception as e:
            return {"error": str(e)}
    
    def __repr__(self):
        """String representation for debugging."""
        stats = self.get_performance_stats()
        return f"SharedProjectMemory(records={stats.get('database', {}).get('total_records', 0)}, db={self.db_path})"


# Backward compatibility alias
ProjectMemory = SharedProjectMemory