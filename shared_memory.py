import logging
import os
import sqlite3
import json
import threading
from typing import Dict, Any, Optional, List
from contextlib import contextmanager
from collections import defaultdict
import hashlib
from datetime import datetime

from abc import ABC, abstractmethod

class UnifiedMemoryInterface(ABC):
    """
    Unified interface for all memory operations across agents.
    This provides a consistent API regardless of the underlying storage mechanism.
    """
    
    @abstractmethod
    def store(self, key: str, value: Any, context: Optional[str] = None) -> bool:
        """
        Store data with optional context.
        
        Args:
            key: Unique identifier for the data
            value: Data to store (will be JSON serialized)
            context: Optional context for grouping (e.g., agent name, session)
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def retrieve(self, key: str, context: Optional[str] = None, default: Any = None) -> Any:
        """
        Retrieve data with optional context.
        
        Args:
            key: Unique identifier for the data
            context: Optional context for grouping
            default: Default value if key not found
            
        Returns:
            Retrieved data or default value
        """
        pass
    
    @abstractmethod
    def exists(self, key: str, context: Optional[str] = None) -> bool:
        """
        Check if key exists.
        
        Args:
            key: Unique identifier to check
            context: Optional context for grouping
            
        Returns:
            True if key exists, False otherwise
        """
        pass
    
    @abstractmethod
    def clear_context(self, context: str) -> bool:
        """
        Clear all data for a specific context.
        
        Args:
            context: Context to clear (e.g., agent name, session)
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def list_keys(self, context: Optional[str] = None) -> List[str]:
        """
        List all keys, optionally filtered by context.
        
        Args:
            context: Optional context filter
            
        Returns:
            List of keys
        """
        pass


logger = logging.getLogger(__name__)

# OPTIMIZATION: Unified Memory Interface for consistency across agents
from abc import ABC, abstractmethod

class UnifiedMemoryInterface(ABC):
    """
    Unified interface for all memory operations across agents.
    This ensures consistent memory access patterns and reduces fragmentation.
    """
    
    @abstractmethod
    def store(self, key: str, value: Any, context: Optional[str] = None) -> bool:
        """Store data with optional context namespace."""
        pass
    
    @abstractmethod 
    def retrieve(self, key: str, context: Optional[str] = None, default: Any = None) -> Any:
        """Retrieve data with optional context namespace."""
        pass
    
    @abstractmethod
    def exists(self, key: str, context: Optional[str] = None) -> bool:
        """Check if key exists in optional context."""
        pass
    
    @abstractmethod
    def clear_context(self, context: str) -> bool:
        """Clear all data for a specific context."""
        pass
    
    @abstractmethod
    def list_keys(self, context: Optional[str] = None) -> List[str]:
        """List all keys in optional context."""
        pass



class HighPerformanceSharedMemory(UnifiedMemoryInterface):
    """Enhanced shared memory with batch operations and performance optimization."""
    
    def __init__(self, run_dir: str = None, batch_size: int = 100):
        """Initialize the shared memory system.
        
        Args:
            run_dir: Directory to store the SQLite database
            batch_size: Number of operations to batch before committing
        """
        self.run_dir = run_dir  # Store run_dir as an instance attribute
        self.batch_size = batch_size
        self.db_path = os.path.join(run_dir, "memory.db") if run_dir else ":memory:"
        self._connection_pool = {}
        self._update_batch = []
        self._batch_count = 0
        self._lock = threading.RLock()
        self.logger = self._setup_logger()
        self._connect_db()
    
    def _setup_logger(self):
        """Set up a logger for the shared memory system."""
        logger = logging.getLogger(f"SharedMemory_{id(self)}")
        if not logger.handlers:
            logger.setLevel(logging.DEBUG)
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger
    
    def _connect_db(self):
        """Connect to the SQLite database, ensuring the directory exists."""
        thread_id = threading.get_ident()
        if thread_id in self._connection_pool:
            return
        
        # Ensure the run directory exists if specified
        if self.run_dir:
            os.makedirs(self.run_dir, exist_ok=True)
        
        try:
            self._connection_pool[thread_id] = sqlite3.connect(
                self.db_path, check_same_thread=False
            )
            self._initialize_db_schema()
            self.logger.debug(f"Established new database connection for thread {thread_id}")
        except sqlite3.Error as e:
            self.logger.error(f"Database connection error: {e}")
            # Create a fallback in-memory database if file access fails
            self.logger.warning("Using in-memory database as fallback")
            self._connection_pool[thread_id] = sqlite3.connect(
                ":memory:", check_same_thread=False
            )
            self._initialize_db_schema()
    
    def _initialize_db_schema(self):
        """Initialize the database schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Create key-value store table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS key_value_store (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # Create agent results table for tracking agent outputs
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL,
                result TEXT NOT NULL,
                execution_time REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # Index for faster agent result lookups
            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_agent_name 
            ON agent_results(agent_name)
            """)
            
            # Add agent_activities table for tracking agent activities
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL,
                activity_type TEXT NOT NULL,
                prompt TEXT,
                response TEXT,
                metadata TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # Index for faster agent activity lookups
            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_activity_agent_name 
            ON agent_activities(agent_name)
            """)
            
            conn.commit()
    
    def _get_connection(self):
        """Get a database connection for the current thread."""
        thread_id = threading.get_ident()
        if thread_id not in self._connection_pool:
            self._connect_db()
        return self._connection_pool[thread_id]
    
    def _get_cursor(self):
        """Get a cursor for the current thread's connection."""
        return self._get_connection().cursor()
    
    @contextmanager
    def transaction(self):
        """Context manager for database transactions."""
        conn = self._get_connection()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Transaction error: {e}")
            raise
    
    def set(self, key: str, value: Any, immediate: bool = False):
        """Set a value in the shared memory.
        
        Args:
            key: The key to store the value under
            value: The value to store (will be JSON serialized)
            immediate: Whether to commit immediately or batch
        """
        serialized_value = json.dumps(value)
        with self._lock:
            if immediate:
                cursor = self._get_cursor()
                cursor.execute(
                    """INSERT OR REPLACE INTO key_value_store (key, value, updated_at) 
                       VALUES (?, ?, CURRENT_TIMESTAMP)""", 
                    (key, serialized_value)
                )
                self._get_connection().commit()
            else:
                self._update_batch.append((key, serialized_value))
                self._batch_count += 1
                
                if self._batch_count >= self.batch_size:
                    self._flush_batch()
    
    def _flush_batch(self):
        """Flush the batch of updates to the database."""
        if not self._update_batch:
            return
            
        with self._lock:
            try:
                cursor = self._get_cursor()
                for key, value in self._update_batch:
                    cursor.execute(
                        """INSERT OR REPLACE INTO key_value_store (key, value, updated_at) 
                           VALUES (?, ?, CURRENT_TIMESTAMP)""", 
                        (key, value)
                    )
                self._get_connection().commit()
                self._update_batch.clear()
                self._batch_count = 0
            except Exception as e:
                self.logger.error(f"Batch flush error: {e}")
                self._fallback_individual_commits()
    
    def _fallback_individual_commits(self):
        """Fallback to individual commits if batch fails."""
        for key, value in self._update_batch:
            try:
                cursor = self._get_cursor()
                cursor.execute(
                    """INSERT OR REPLACE INTO key_value_store (key, value, updated_at) 
                       VALUES (?, ?, CURRENT_TIMESTAMP)""", 
                    (key, value)
                )
                self._get_connection().commit()
            except Exception as e:
                self.logger.error(f"Individual commit error for key '{key}': {e}")
        
        self._update_batch.clear()
        self._batch_count = 0
    
    def get(self, key: str, default=None) -> Any:
        """Get a value from shared memory.
        
        Args:
            key: The key to retrieve
            default: Default value if key doesn't exist
            
        Returns:
            The deserialized value or default if not found
        """
        # Flush any pending writes to ensure we get the latest value
        self._flush_batch()
        
        cursor = self._get_cursor()
        cursor.execute("SELECT value FROM key_value_store WHERE key = ?", (key,))
        row = cursor.fetchone()
        
        if row:
            try:
                return json.loads(row[0])
            except json.JSONDecodeError as e:
                self.logger.error(f"JSON decode error for key '{key}': {e}")
                return default
        return default
    
    def delete(self, key: str):
        """Delete a key from shared memory."""
        with self._lock:
            cursor = self._get_cursor()
            cursor.execute("DELETE FROM key_value_store WHERE key = ?", (key,))
            self._get_connection().commit()
    
    def list_keys(self, prefix: str = "") -> List[str]:
        """List all keys with optional prefix filtering."""
        cursor = self._get_cursor()
        if prefix:
            cursor.execute("SELECT key FROM key_value_store WHERE key LIKE ?", (f"{prefix}%",))
        else:
            cursor.execute("SELECT key FROM key_value_store")
        
        return [row[0] for row in cursor.fetchall()]
    
    def clear(self):
        """Clear all data from shared memory."""
        with self._lock:
            cursor = self._get_cursor()
            cursor.execute("DELETE FROM key_value_store")
            cursor.execute("DELETE FROM agent_results")
            cursor.execute("DELETE FROM agent_activities")
            self._get_connection().commit()
    
    def close(self):
        """Close all database connections."""
        with self._lock:
            for conn in self._connection_pool.values():
                conn.close()
            self._connection_pool.clear()
            self.logger.debug("All database connections closed")    # Unified Memory Interface Implementation
    
    def store(self, key: str, value: Any, context: Optional[str] = None) -> bool:
        """Store data with optional context using unified interface."""
        try:
            full_key = f"{context}:{key}" if context else key
            self.set(full_key, value)
            return True
        except Exception as e:
            self.logger.error(f"Failed to store {full_key}: {e}")
            return False
    
    def retrieve(self, key: str, context: Optional[str] = None, default: Any = None) -> Any:
        """Retrieve data with optional context using unified interface."""
        try:
            full_key = f"{context}:{key}" if context else key
            return self.get(full_key, default)
        except Exception as e:
            self.logger.error(f"Failed to retrieve {full_key}: {e}")
            return default
    
    def exists(self, key: str, context: Optional[str] = None) -> bool:
        """Check if key exists using unified interface."""
        try:
            full_key = f"{context}:{key}" if context else key
            return self.has_key(full_key)
        except Exception as e:
            self.logger.error(f"Failed to check existence of {full_key}: {e}")
            return False
    
    def has_key(self, key: str) -> bool:
        """Check if a key exists in the store."""
        cursor = self._get_cursor()
        cursor.execute("SELECT 1 FROM key_value_store WHERE key = ? LIMIT 1", (key,))
        return cursor.fetchone() is not None
    
    def clear_context(self, context: str) -> bool:
        """Clear all data for a specific context."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM key_value_store WHERE key LIKE ?", (f"{context}:%",))
                conn.commit()
                deleted_count = cursor.rowcount
                self.logger.info(f"Cleared {deleted_count} keys for context: {context}")
                return True
        except Exception as e:
            self.logger.error(f"Failed to clear context {context}: {e}")
            return False
    
    def list_keys(self, context: Optional[str] = None) -> List[str]:
        """List all keys, optionally filtered by context."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                if context:
                    cursor.execute("SELECT key FROM key_value_store WHERE key LIKE ?", (f"{context}:%",))
                    # Strip context prefix from results
                    keys = [row[0][len(context)+1:] for row in cursor.fetchall()]
                else:
                    cursor.execute("SELECT key FROM key_value_store")
                    keys = [row[0] for row in cursor.fetchall()]
                return keys
        except Exception as e:
            self.logger.error(f"Failed to list keys for context {context}: {e}")
            return []


class SharedProjectMemory(HighPerformanceSharedMemory):
    """
    Compatibility wrapper for main.py import.
    
    This class provides a project-specific interface around HighPerformanceSharedMemory
    with additional methods tailored for the Multi-AI Development System workflow.
    """
    
    def __init__(self, run_dir: str = None):
        """Initialize with project-specific defaults."""
        super().__init__(run_dir=run_dir, batch_size=50)  # Smaller batch size for responsiveness
        
        # Project-specific initialization
        self._agent_results = {}
        self._execution_metadata = {}
        
        # Removed print statement to avoid I/O errors
        # SharedProjectMemory initialized successfully
    
    def store_agent_result(self, agent_name, result, execution_time=None, metadata=None, prompt=None, response=None):
        """Store agent execution result with extended metadata.
        
        Args:
            agent_name: Name of the agent
            result: Result produced by the agent
            execution_time: Time taken for execution (optional)
            metadata: Additional metadata about the execution (optional)
            prompt: The prompt sent to the agent (optional)
            response: Raw response from the agent (optional)
        """
        from datetime import datetime
        import logging
        
        try:
            # Create record
            record = {
                "agent": agent_name,
                "timestamp": datetime.now().isoformat(),
                "result": result
            }
            
            # Add optional fields if provided
            if execution_time is not None:
                record["execution_time"] = execution_time
            if metadata is not None:
                record["metadata"] = metadata
            if prompt is not None:
                record["prompt"] = prompt
            if response is not None:
                record["response"] = response
                
            # Store in database
            self._store_record("agent_results", record)
            
        except Exception as e:
            logging.error(f"Error storing agent result: {e}")
    
    def get_agent_result(self, agent_name: str, default=None) -> Dict[str, Any]:
        """Get the latest result for a specific agent."""
        # Try memory cache first
        if agent_name in self._agent_results:
            return self._agent_results[agent_name]
        
        # Otherwise query from database
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT result FROM agent_results 
                   WHERE agent_name = ? 
                   ORDER BY created_at DESC LIMIT 1""",
                (agent_name,)
            )
            row = cursor.fetchone()
            
            if row:
                try:
                    result = json.loads(row[0])
                    # Update cache
                    self._agent_results[agent_name] = result
                    return result
                except json.JSONDecodeError:
                    return default
        
        return default
    
    def get_all_agent_results(self) -> Dict[str, Any]:
        """Get all stored agent results."""
        results = {}
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT agent_name, result FROM agent_results
                   GROUP BY agent_name
                   HAVING created_at = MAX(created_at)"""
            )
            
            for agent_name, result_json in cursor.fetchall():
                try:
                    results[agent_name] = json.loads(result_json)
                except json.JSONDecodeError:
                    results[agent_name] = {"error": "Failed to parse result"}
        
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
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for agents."""
        stats = {}
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT agent_name, 
                          AVG(execution_time) as avg_time,
                          MIN(execution_time) as min_time,
                          MAX(execution_time) as max_time,
                          COUNT(*) as run_count
                   FROM agent_results
                   GROUP BY agent_name"""
            )
            
            for agent_name, avg_time, min_time, max_time, run_count in cursor.fetchall():
                stats[agent_name] = {
                    "avg_execution_time": avg_time,
                    "min_execution_time": min_time,
                    "max_execution_time": max_time,
                    "run_count": run_count
                }
        
        return stats
    
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
    
    def store_agent_activity(self, agent_name: str, activity_type: str, prompt: str, response: str, metadata: dict = None):
        """Store agent activity in the database."""
        if metadata is None:
            metadata = {}
        
        try:
            # Get database connection for current thread
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Insert the activity
            cursor.execute(
                """
                INSERT INTO agent_activities 
                (agent_name, activity_type, prompt, response, metadata, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
                """, 
                (agent_name, activity_type, prompt, response, json.dumps(metadata), datetime.now().isoformat())
            )
            conn.commit()
            
            # Use self.logger instead of self.log
            if hasattr(self, 'logger'):
                self.logger.debug(f"Stored {activity_type} activity for agent {agent_name}")
            return cursor.lastrowid
        except Exception as e:
            # Use self.logger instead of self.log
            if hasattr(self, 'logger'):
                self.logger.error(f"Error storing agent activity: {e}")
            else:
                # Removed print statement to avoid I/O errors
                pass
            return None
    
    def _store_record(self, collection_name, record):
        """Store a record in the specified collection.
        
        Args:
            collection_name: Name of the collection to store record in
            record: The record to store
        """
        try:
            import json
            import os
            from datetime import datetime
            
            # Ensure records directory exists
            records_dir = os.path.join(self.run_dir, "records")
            os.makedirs(records_dir, exist_ok=True)
            
            # Create collection directory if it doesn't exist
            collection_dir = os.path.join(records_dir, collection_name)
            os.makedirs(collection_dir, exist_ok=True)
            
            # Generate a unique filename based on timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"{timestamp}.json"
            filepath = os.path.join(collection_dir, filename)
            
            # Write record to file
            with open(filepath, 'w') as f:
                json.dump(record, f, indent=2, default=str)
        except Exception as e:
            import logging
            logging.error(f"Error storing record: {e}")


# Backward compatibility alias
ProjectMemory = SharedProjectMemory

class SharedMemory:
    """
    Legacy in-memory state management for the multi-agent system.
    
    NOTE: This provides a simpler in-memory dictionary-based implementation
    that doesn't require SQLite or persistence. Consider using
    SharedProjectMemory for new code that needs persistence and better
    performance at scale.
    """
    
    def __init__(self):
        """Initialize shared memory store."""
        self._memory: Dict[str, Any] = {}
        self._history: List[Dict[str, Any]] = []
        logger.info("SharedMemory initialized")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from shared memory."""
        return self._memory.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a value in shared memory."""
        self._memory[key] = value
        # Record change in history
        self._history.append({
            "action": "set",
            "key": key,
            "value_type": type(value).__name__
        })
        logger.debug(f"Memory updated: {key}")
    
    def update(self, data: Dict[str, Any]) -> None:
        """Update multiple values in shared memory."""
        self._memory.update(data)
        self._history.append({
            "action": "update",
            "keys": list(data.keys())
        })
        logger.debug(f"Memory batch updated with {len(data)} keys")
    
    def delete(self, key: str) -> None:
        """Delete a key from shared memory."""
        if key in self._memory:
            del self._memory[key]
            self._history.append({
                "action": "delete",
                "key": key
            })
            logger.debug(f"Memory key deleted: {key}")
    
    def clear(self) -> None:
        """Clear all shared memory."""
        self._memory = {}
        self._history.append({
            "action": "clear"
        })
        logger.debug("Memory cleared")
    
    def get_all(self) -> Dict[str, Any]:
        """Get all memory contents."""
        return self._memory.copy()
    
    def get_history(self) -> List[Dict[str, Any]]:
        """Get memory operation history."""
        return self._history.copy()
    
    def save_to_disk(self, filepath: str) -> None:
        """Save memory state to disk."""
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w') as f:
                json.dump(self._memory, f, indent=2, default=str)
            logger.info(f"Memory saved to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save memory to disk: {str(e)}")
    
    def load_from_disk(self, filepath: str) -> bool:
        """Load memory state from disk."""
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    self._memory = json.load(f)
                logger.info(f"Memory loaded from {filepath}")
                return True
            else:
                logger.warning(f"Memory file not found: {filepath}")
                return False
        except Exception as e:
            logger.error(f"Failed to load memory from disk: {str(e)}")
            return False
    
    def store_agent_activity(self, agent_name: str, activity_type: str, prompt: str, response: str, metadata: dict = None):
        """Store agent activity (simplified version for in-memory storage)."""
        if metadata is None:
            metadata = {}
        
        activity_record = {
            "agent_name": agent_name,
            "activity_type": activity_type,
            "prompt": prompt,
            "response": response,
            "metadata": metadata,
            "timestamp": datetime.now().isoformat()
        }
        
        # Store in memory under agent activities
        if "agent_activities" not in self._memory:
            self._memory["agent_activities"] = []
        
        self._memory["agent_activities"].append(activity_record)
        
        # Record in history
        self._history.append({
            "action": "store_agent_activity",
            "agent_name": agent_name,
            "activity_type": activity_type
        })
        
        logger.debug(f"Stored activity for agent {agent_name}: {activity_type}")