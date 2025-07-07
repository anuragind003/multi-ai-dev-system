"""
Enhanced Memory Manager for Multi-AI Development System

Provides intelligent memory management with multiple backends:
- Fast in-memory cache for hot data
- Persistent SQLite storage for durability 
- Optional Redis backend for distributed scenarios
- File system cache for large objects
- Automatic cleanup and monitoring
"""

import logging
import os
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union, Callable
from enum import Enum
from dataclasses import dataclass
from contextlib import contextmanager
import threading
import json
import pickle
import gzip
import base64
from collections import OrderedDict, defaultdict
from datetime import datetime
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory

logger = logging.getLogger(__name__)

class MemoryBackend(Enum):
    """Available memory backend types."""
    IN_MEMORY = "in_memory"          # Fast dict-based, no persistence
    SQLITE = "sqlite"                # SQLite-based persistence  
    REDIS = "redis"                  # Redis cache (requires redis-py)
    FILESYSTEM = "filesystem"        # File-based cache
    HYBRID = "hybrid"               # Combines multiple backends
    AUTO = "auto"                   # Automatically choose best backend

@dataclass
class MemoryConfig:
    """Configuration for memory management."""
    backend: MemoryBackend = MemoryBackend.SQLITE
    max_memory_mb: int = 100
    max_entries: int = 10000
    ttl_seconds: int = 3600
    enable_compression: bool = False
    enable_monitoring: bool = True
    auto_cleanup: bool = True
    persistent_dir: Optional[str] = None
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

@dataclass 
class MemoryStats:
    """Memory usage statistics."""
    total_entries: int = 0
    memory_usage_mb: float = 0.0
    hit_ratio: float = 0.0
    operations_per_second: float = 0.0
    backend_type: str = ""
    last_cleanup: Optional[float] = None

class EnhancedMemoryManager:
    """
    Intelligent memory manager with multiple backends and auto-optimization.
    
    Features:
    - Multiple storage backends (in-memory, SQLite, Redis, filesystem)
    - Intelligent caching with LRU eviction
    - Automatic compression for large objects
    - Memory monitoring and statistics
    - Cross-agent data persistence
    - Automatic cleanup policies
    """
    
    def __init__(self, config: MemoryConfig = None):
        self.config = config or MemoryConfig()
        self.stats = MemoryStats()
        self._lock = threading.RLock()
        
        # Initialize backends
        self._backends = {}
        self._primary_backend = None
        self._cache_backend = None
        
        # Monitoring
        self._operation_count = 0
        self._start_time = time.time()
        self._hit_count = 0
        self._miss_count = 0
        
        # Initialize the memory system
        self._initialize_backends()
        
        # Start monitoring and cleanup threads if enabled
        if self.config.enable_monitoring:
            self._start_monitoring()
        if self.config.auto_cleanup:
            self._start_cleanup_thread()
            
        logger.info(f"Enhanced Memory Manager initialized with backend: {self.config.backend}")
    
    def _initialize_backends(self):
        """Initialize the appropriate memory backends based on configuration."""
        backend_type = self.config.backend
        
        if backend_type == MemoryBackend.AUTO:
            backend_type = self._choose_optimal_backend()
            
        if backend_type == MemoryBackend.IN_MEMORY:
            self._primary_backend = InMemoryBackend(self.config)
            
        elif backend_type == MemoryBackend.SQLITE:
            self._primary_backend = SQLiteBackend(self.config)
            
        elif backend_type == MemoryBackend.REDIS:
            self._primary_backend = RedisBackend(self.config)
            
        elif backend_type == MemoryBackend.FILESYSTEM:
            self._primary_backend = FileSystemBackend(self.config)
            
        elif backend_type == MemoryBackend.HYBRID:
            # Use in-memory for hot data + SQLite for persistence
            self._cache_backend = InMemoryBackend(self.config)
            self._primary_backend = SQLiteBackend(self.config)
            
        self.stats.backend_type = str(backend_type)
    
    def _choose_optimal_backend(self) -> MemoryBackend:
        """Automatically choose the best backend for current environment."""
        try:
            # Check if Redis is available
            import redis
            redis_client = redis.Redis(
                host=self.config.redis_host, 
                port=self.config.redis_port, 
                db=self.config.redis_db
            )
            redis_client.ping()
            logger.info("Redis detected - using Redis backend for optimal performance")
            return MemoryBackend.REDIS
        except:
            logger.info("Redis not available - using SQLite backend")
            return MemoryBackend.SQLITE
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None, context: Optional[str] = None) -> bool:
        """
        Store a value with optional TTL and context.
        
        Args:
            key: Unique identifier for the data
            value: Data to store
            ttl: Time to live in seconds (None = use default)
            context: Optional context for grouping (e.g., agent name)
            
        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            try:
                # Handle context namespacing
                storage_key = f"{context}:{key}" if context else key
                
                # Use hybrid strategy if available
                if self._cache_backend and self._primary_backend:
                    # Store in cache for fast access
                    self._cache_backend.set(storage_key, value, ttl)
                    # Store in persistent backend
                    success = self._primary_backend.set(storage_key, value, ttl)
                else:
                    success = self._primary_backend.set(storage_key, value, ttl)
                
                if success:
                    self._operation_count += 1
                    self.stats.total_entries += 1
                    
                # Log failed memory operation - DISABLED to keep terminal clean
                # try:
                #     from enhanced_logging_system import log_memory_operation
                #     log_memory_operation(
                #         operation="set",
                #         key=key,
                #         context=context or "default",
                #         backend=self.stats.backend_type,
                #         success=False,
                #         metadata={"ttl": ttl, "error": str(e)}
                #     )
                # except ImportError:
                #     pass
                    
                return success
                
            except Exception as e:
                logger.error(f"Error storing key '{key}': {e}")
                # Log failed memory operation - DISABLED to keep terminal clean
                # try:
                #     from enhanced_logging_system import log_memory_operation
                #     log_memory_operation(
                #         operation="set",
                #         key=key,
                #         context=context or "default",
                #         backend=self.stats.backend_type,
                #         success=False,
                #         metadata={"ttl": ttl, "error": str(e)}
                #     )
                # except ImportError:
                #     pass
                return False
    
    def store(self, key: str, value: Any, ttl: Optional[int] = None, context: Optional[str] = None) -> bool:
        """
        Alias for set() method to maintain backward compatibility.
        
        Args:
            key: Unique identifier for the data
            value: Data to store
            ttl: Time to live in seconds (None = use default)
            context: Optional context for grouping (e.g., agent name)
            
        Returns:
            True if successful, False otherwise
        """
        return self.set(key, value, ttl, context)
    
    def get(self, key: str, default: Any = None, context: Optional[str] = None) -> Any:
        """
        Retrieve a value by key.
        
        Args:
            key: Unique identifier for the data
            default: Default value if key not found
            context: Optional context for grouping
            
        Returns:
            Retrieved data or default value
        """
        with self._lock:
            try:
                # Handle context namespacing
                storage_key = f"{context}:{key}" if context else key
                
                # Try cache first if using hybrid
                if self._cache_backend:
                    value = self._cache_backend.get(storage_key, None)
                    if value is not None:
                        self._hit_count += 1
                        return value
                    # Cache miss - try primary backend
                    value = self._primary_backend.get(storage_key, default)
                    if value != default:
                        # Populate cache for next time
                        self._cache_backend.set(storage_key, value)
                        self._miss_count += 1
                    return value
                else:
                    value = self._primary_backend.get(storage_key, default)
                    if value != default:
                        self._hit_count += 1
                    else:
                        self._miss_count += 1
                    return value
                    
            except Exception as e:
                logger.error(f"Error retrieving key '{key}': {e}")
                return default
    
    def delete(self, key: str, context: Optional[str] = None) -> bool:
        """Delete a key from all backends."""
        with self._lock:
            storage_key = f"{context}:{key}" if context else key
            success = True
            
            if self._cache_backend:
                success &= self._cache_backend.delete(storage_key)
            if self._primary_backend:
                success &= self._primary_backend.delete(storage_key)
                
            if success:
                self.stats.total_entries = max(0, self.stats.total_entries - 1)
            return success
    
    def exists(self, key: str, context: Optional[str] = None) -> bool:
        """Check if a key exists in memory."""
        storage_key = f"{context}:{key}" if context else key
        
        if self._cache_backend and self._cache_backend.exists(storage_key):
            return True
        return self._primary_backend.exists(storage_key) if self._primary_backend else False
    
    def list_keys(self, context: Optional[str] = None, pattern: Optional[str] = None) -> List[str]:
        """List all keys, optionally filtered by context and pattern."""
        keys = set()
        
        if self._primary_backend:
            keys.update(self._primary_backend.list_keys(context, pattern))
        if self._cache_backend:
            keys.update(self._cache_backend.list_keys(context, pattern))
            
        return list(keys)
    
    def clear_context(self, context: str) -> bool:
        """Clear all data for a specific context."""
        success = True
        if self._cache_backend:
            success &= self._cache_backend.clear_context(context)
        if self._primary_backend:
            success &= self._primary_backend.clear_context(context)
        return success
    
    def get_stats(self) -> MemoryStats:
        """Get current memory statistics."""
        with self._lock:
            # Update calculated stats
            total_ops = self._hit_count + self._miss_count
            self.stats.hit_ratio = self._hit_count / max(1, total_ops)
            
            elapsed = time.time() - self._start_time
            self.stats.operations_per_second = self._operation_count / max(1, elapsed)
            
            # Get memory usage from primary backend
            if hasattr(self._primary_backend, 'get_memory_usage'):
                self.stats.memory_usage_mb = self._primary_backend.get_memory_usage()
                
            return self.stats
    
    def optimize(self):
        """Perform optimization operations like cleanup and defragmentation."""
        logger.info("Starting memory optimization...")
        
        # Clean expired entries
        if hasattr(self._primary_backend, 'cleanup_expired'):
            self._primary_backend.cleanup_expired()
        if self._cache_backend and hasattr(self._cache_backend, 'cleanup_expired'):
            self._cache_backend.cleanup_expired()
            
        # Update last cleanup time
        self.stats.last_cleanup = time.time()
        
        logger.info("Memory optimization completed")
    
    def _start_monitoring(self):
        """Start background monitoring thread."""
        def monitor():
            while True:
                time.sleep(60)  # Update stats every minute
                try:
                    self.get_stats()
                    logger.debug(f"Memory stats: {self.stats}")
                except Exception as e:
                    logger.error(f"Error in monitoring thread: {e}")
        
        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()
    
    def _start_cleanup_thread(self):
        """Start background cleanup thread."""
        def cleanup():
            while True:
                time.sleep(3600)  # Cleanup every hour
                try:
                    self.optimize()
                except Exception as e:
                    logger.error(f"Error in cleanup thread: {e}")
        
        cleanup_thread = threading.Thread(target=cleanup, daemon=True)
        cleanup_thread.start()

    def get_chat_history_for_session(self, session_id: str) -> BaseChatMessageHistory:
        """
        Retrieves or creates a chat message history for a given session.
        This is required for integration with LangChain's RunnableWithMessageHistory.
        """
        with self._lock:
            context = "chat_history"
            history = self.get(session_id, default=None, context=context)
            if history is None:
                history = ChatMessageHistory()
                self.set(session_id, history, context=context)
            return history

    def store_agent_activity(self, agent_name: str, activity_type: str, prompt: str = "", response: str = "", metadata: dict = None):
        """
        Store a record of agent activity.
        
        Args:
            agent_name: Name of the agent
            activity_type: Type of activity (e.g., 'brd_analysis', 'code_generation')
            prompt: The prompt given to the agent
            response: The agent's response
            metadata: Additional structured data
        """
        try:
            timestamp = datetime.now().isoformat()
            activity_record = {
                "timestamp": timestamp,
                "agent_name": agent_name,
                "activity_type": activity_type,
                "prompt": prompt,
                "response": response,
                "metadata": metadata or {}
            }
            
            # Use a unique key for each activity record
            # IMPORTANT: Added timestamp to key to ensure uniqueness
            activity_key = f"activity_{agent_name}_{activity_type}_{timestamp}"
            
            # Store in a dedicated context for agent activity
            self.set(
                activity_key,
                activity_record,
                context="agent_activity"
            )
            
        except Exception as e:
            logger.error(f"Error storing agent activity: {e}")

# Backend Implementations

class MemoryBackendInterface(ABC):
    """Interface for memory backends."""
    
    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        pass
    
    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        pass
    
    @abstractmethod
    def exists(self, key: str) -> bool:
        pass
    
    @abstractmethod
    def list_keys(self, context: Optional[str] = None, pattern: Optional[str] = None) -> List[str]:
        pass
    
    @abstractmethod
    def clear_context(self, context: str) -> bool:
        pass

class InMemoryBackend(MemoryBackendInterface):
    """Fast in-memory backend using Python dictionaries."""
    
    def __init__(self, config: MemoryConfig):
        self.config = config
        self._data = OrderedDict()
        self._expiry = {}
        self._lock = threading.RLock()
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        with self._lock:
            self._data[key] = value
            if ttl:
                self._expiry[key] = time.time() + ttl
            # LRU eviction
            if len(self._data) > self.config.max_entries:
                oldest_key = next(iter(self._data))
                del self._data[oldest_key]
                self._expiry.pop(oldest_key, None)
            return True
    
    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            # Check expiry
            if key in self._expiry and time.time() > self._expiry[key]:
                del self._data[key]
                del self._expiry[key]
                return default
            return self._data.get(key, default)
    
    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._data:
                del self._data[key]
                self._expiry.pop(key, None)
                return True
            return False
    
    def exists(self, key: str) -> bool:
        return self.get(key, None) is not None
    
    def list_keys(self, context: Optional[str] = None, pattern: Optional[str] = None) -> List[str]:
        keys = list(self._data.keys())
        if context:
            keys = [k for k in keys if k.startswith(f"{context}:")]
        if pattern:
            import fnmatch
            keys = [k for k in keys if fnmatch.fnmatch(k, pattern)]
        return keys
    
    def clear_context(self, context: str) -> bool:
        with self._lock:
            keys_to_delete = [k for k in self._data.keys() if k.startswith(f"{context}:")]
            for key in keys_to_delete:
                del self._data[key]
                self._expiry.pop(key, None)
            return True

class SQLiteBackend(MemoryBackendInterface):
    """SQLite-based persistent backend."""
    
    def __init__(self, config: MemoryConfig):
        self.config = config
        from shared_memory import SharedProjectMemory
        run_dir = config.persistent_dir or "./output/memory"
        self._memory = SharedProjectMemory(run_dir=run_dir)
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        try:
            # Use pickle for robust serialization, then encode to base64
            # to ensure the data is a JSON-serializable string.
            serialized_value = pickle.dumps(value)
            encoded_value = base64.b64encode(serialized_value).decode('utf-8')
            self._memory.set(key, encoded_value, immediate=True)
            return True
        except Exception as e:
            logger.error(f"SQLite backend error on set: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        stored_value = self._memory.get(key, None)
        if stored_value is None:
            return default
        
        try:
            # Handle new format: base64-encoded string
            if isinstance(stored_value, str):
                decoded_bytes = base64.b64decode(stored_value.encode('utf-8'))
                return pickle.loads(decoded_bytes)
            
            # Handle potential old format: raw bytes
            if isinstance(stored_value, bytes):
                return pickle.loads(stored_value)

            # If it's neither, we can't deserialize it.
            logger.warning(f"Cannot deserialize memory value for key '{key}' of type {type(stored_value)}")
            return stored_value
        except Exception as e:
            logger.error(f"Failed to deserialize value for key '{key}': {e}")
            return default
    
    def delete(self, key: str) -> bool:
        try:
            self._memory.delete(key)
            return True
        except:
            return False
    
    def exists(self, key: str) -> bool:
        return self._memory.get(key, None) is not None
    
    def list_keys(self, context: Optional[str] = None, pattern: Optional[str] = None) -> List[str]:
        all_keys = self._memory.list_keys()
        if context:
            all_keys = [k for k in all_keys if k.startswith(f"{context}:")]
        if pattern:
            import fnmatch
            all_keys = [k for k in all_keys if fnmatch.fnmatch(k, pattern)]
        return all_keys
    
    def clear_context(self, context: str) -> bool:
        try:
            keys_to_delete = self.list_keys(context=context)
            for key in keys_to_delete:
                self.delete(key)
            return True
        except:
            return False

class RedisBackend(MemoryBackendInterface):
    """Redis-based high-performance backend."""
    
    def __init__(self, config: MemoryConfig):
        self.config = config
        try:
            import redis
            self._redis = redis.Redis(
                host=config.redis_host,
                port=config.redis_port,
                db=config.redis_db,
                decode_responses=False
            )
            # Test connection
            self._redis.ping()
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            raise RuntimeError("Redis backend initialization failed")
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        try:
            serialized = pickle.dumps(value)
            if ttl:
                return self._redis.setex(key, ttl, serialized)
            else:
                return self._redis.set(key, serialized)
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        try:
            value = self._redis.get(key)
            if value is None:
                return default
            return pickle.loads(value)
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return default
    
    def delete(self, key: str) -> bool:
        try:
            return bool(self._redis.delete(key))
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        try:
            return bool(self._redis.exists(key))
        except:
            return False
    
    def list_keys(self, context: Optional[str] = None, pattern: Optional[str] = None) -> List[str]:
        try:
            search_pattern = "*"
            if context and pattern:
                search_pattern = f"{context}:{pattern}"
            elif context:
                search_pattern = f"{context}:*"
            elif pattern:
                search_pattern = pattern
            
            keys = self._redis.keys(search_pattern)
            return [k.decode() if isinstance(k, bytes) else k for k in keys]
        except:
            return []
    
    def clear_context(self, context: str) -> bool:
        try:
            keys = self.list_keys(context=context)
            if keys:
                return bool(self._redis.delete(*keys))
            return True
        except:
            return False

class FileSystemBackend(MemoryBackendInterface):
    """File system-based backend for large objects."""
    
    def __init__(self, config: MemoryConfig):
        self.config = config
        try:
            from cachelib import FileSystemCache
            cache_dir = config.persistent_dir or "./cache"
            self._fs_cache = FileSystemCache(
                cache_dir=cache_dir,
                threshold=config.max_entries,
                default_timeout=config.ttl_seconds
            )
        except ImportError:
            raise RuntimeError("cachelib required for FileSystem backend")
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        try:
            timeout = ttl or self.config.ttl_seconds
            return self._fs_cache.set(key, value, timeout=timeout)
        except Exception as e:
            logger.error(f"FileSystem set error: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        value = self._fs_cache.get(key)
        return value if value is not None else default
    
    def delete(self, key: str) -> bool:
        return self._fs_cache.delete(key)
    
    def exists(self, key: str) -> bool:
        return self._fs_cache.get(key) is not None
    
    def list_keys(self, context: Optional[str] = None, pattern: Optional[str] = None) -> List[str]:
        # FileSystemCache doesn't provide key listing, so return empty list
        return []
    
    def clear_context(self, context: str) -> bool:
        # Not efficiently supported by FileSystemCache
        return False

# Convenience Functions for Easy Migration

def create_memory_manager(backend_type: str = "auto", **config_kwargs) -> EnhancedMemoryManager:
    """
    Factory function to create a memory manager with sensible defaults.
    
    Args:
        backend_type: Type of backend ("auto", "sqlite", "redis", "in_memory", "filesystem", "hybrid")
        **config_kwargs: Additional configuration options
        
    Returns:
        Configured EnhancedMemoryManager instance
    """
    config = MemoryConfig(
        backend=MemoryBackend(backend_type),
        **config_kwargs
    )
    return EnhancedMemoryManager(config)

def get_project_memory(run_dir: str = None) -> EnhancedMemoryManager:
    """Get a memory manager configured for project use."""
    return create_memory_manager(
        backend_type="hybrid",
        persistent_dir=run_dir,
        max_memory_mb=200,
        enable_monitoring=True,
        auto_cleanup=True
    )

# Backward Compatibility
def SharedProjectMemoryEnhanced(run_dir: str = None, **kwargs):
    """Drop-in replacement for SharedProjectMemory with enhancements."""
    return get_project_memory(run_dir)

class EnhancedSharedProjectMemory:
    """
    Enhanced version of SharedProjectMemory with better performance and features.
    
    This is a DROP-IN REPLACEMENT for SharedProjectMemory that:
    - Keeps all the same methods and behavior
    - Adds high-performance caching
    - Provides better cross-tool communication
    - Maintains full backward compatibility
    
    Usage:
        # Instead of: memory = SharedProjectMemory(run_dir)
        memory = EnhancedSharedProjectMemory(run_dir)
        
        # Everything else works exactly the same!
        memory.set("key", "value")
        memory.store_agent_result("agent", result)
    """
    
    def __init__(self, run_dir: str = None, backend_type: str = "hybrid"):
        """
        Initialize enhanced shared project memory.
        
        Args:
            run_dir: Directory for persistent storage (same as original)
            backend_type: "hybrid" (recommended), "sqlite", "redis", "auto"
        """
        self.run_dir = run_dir
        self.backend_type = backend_type  # Store for easy access
        
        # Create enhanced memory manager
        config = MemoryConfig(
            backend=MemoryBackend(backend_type),
            persistent_dir=run_dir,
            max_memory_mb=200,
            enable_monitoring=True,
            auto_cleanup=True
        )
        self._enhanced_memory = EnhancedMemoryManager(config)
        
        # Keep original SharedProjectMemory for compatibility
        from shared_memory import SharedProjectMemory
        self._original_memory = SharedProjectMemory(run_dir=run_dir)
        
        # Removed print statement to avoid I/O errors
        # Enhanced SharedProjectMemory initialized successfully
    
    def set(self, key: str, value: Any, immediate: bool = False, context: str = None, ttl: int = None) -> None:
        """Set a value (enhanced with caching and context support)."""
        success = False
        try:
            # Handle context parameter for compatibility with agent calls
            if context:
                # Store with context in enhanced memory
                self._enhanced_memory.set(key, value, context=context, ttl=ttl)
                # Store with context prefix in original memory for compatibility
                contextualized_key = f"{context}:{key}"
                self._original_memory.set(contextualized_key, value, immediate=immediate)
            else:
                # Store without context (backward compatibility)
                self._enhanced_memory.set(key, value, context="project", ttl=ttl)
                self._original_memory.set(key, value, immediate=immediate)
            success = True
        except Exception as e:
            success = False
            
            # Log memory operation for flow visibility - DISABLED to keep terminal clean
            # try:
            #     from enhanced_logging_system import log_memory_operation
            #     log_memory_operation(
            #         operation="set",
            #         key=key,
            #         context=context or "default",
            #         backend=self.backend_type,
            #         success=success,
            #         metadata={"ttl": ttl, "immediate": immediate}
            #     )
            # except ImportError:
            #     pass  # Logging system not available
    
    def get(self, key: str, default: Any = None, context: str = None) -> Any:
        """Get a value (enhanced with caching and context support)."""
        if context:
            # Try enhanced first with context
            value = self._enhanced_memory.get(key, None, context=context)
            if value is not None:
                return value
            # Fallback to original with context prefix
            contextualized_key = f"{context}:{key}"
            return self._original_memory.get(contextualized_key, default)
        else:
            # Try enhanced first (faster), fallback to original
            value = self._enhanced_memory.get(key, None, context="project")
            if value is not None:
                return value
            return self._original_memory.get(key, default)
    
    def store_agent_result(self, agent_name: str, result: Any, execution_time: float = None, **kwargs):
        """
        Stores the result of an agent's execution.

        Args:
            agent_name (str): The name of the agent.
            result (Any): The result to be stored.
            execution_time (float, optional): The execution time. Defaults to None.
        """
        key = f"agent_result_{agent_name}"
        data = {
            "result": result,
            "timestamp": datetime.now().isoformat(),
            "execution_time": execution_time,
            **kwargs
        }
        self.set(key, data, context="agent_results")
        
    def store_agent_activity(self, agent_name: str, activity_type: str, prompt: str = "", response: str = "", metadata: dict = None):
        """
        Store a record of agent activity.
        
        Args:
            agent_name: Name of the agent
            activity_type: Type of activity (e.g., 'brd_analysis', 'code_generation')
            prompt: The prompt given to the agent
            response: The agent's response
            metadata: Additional structured data
        """
        # This method is now redundant because it's in the parent EnhancedMemoryManager.
        # We can either remove it or keep it for full backward compatibility.
        # For now, let's delegate to the main implementation.
        self._enhanced_memory.store_agent_activity(agent_name, activity_type, prompt, response, metadata)

    def get_agent_result(self, agent_name: str, default=None):
        """
        Retrieves the result of a specific agent.

        Args:
            agent_name (str): The name of the agent.
            default (Any, optional): The default value to return if the agent result is not found. Defaults to None.

        Returns:
            The result of the agent, or the default value if the agent result is not found.
        """
        key = f"agent_result_{agent_name}"
        value = self.get(key, default, context="agent_results")
        if value is not None:
            return value["result"]
        return default
    
    def get_all_agent_results(self):
        """Get all agent results (same as original)."""
        return self._original_memory.get_all_agent_results()
    
    def store_workflow_state(self, state: Dict[str, Any]):
        """Store workflow state (enhanced)."""
        self._enhanced_memory.set("workflow_state", state, context="project")
        self._original_memory.store_workflow_state(state)
    
    def get_workflow_state(self) -> Dict[str, Any]:
        """Get workflow state (enhanced)."""
        value = self._enhanced_memory.get("workflow_state", None, context="project")
        if value is not None:
            return value
        return self._original_memory.get_workflow_state()
    
    def get_chat_history_for_session(self, session_id: str) -> BaseChatMessageHistory:
        """
        Retrieves or creates a chat message history for a given session.
        This delegates to the underlying EnhancedMemoryManager and is required
        for integration with LangChain's RunnableWithMessageHistory.
        """
        return self._enhanced_memory.get_chat_history_for_session(session_id)
    
    def get_performance_stats(self):
        """Get performance stats (enhanced with new metrics)."""
        original_stats = self._original_memory.get_performance_stats()
        enhanced_stats = self._enhanced_memory.get_stats()
        
        # Combine both statistics
        return {
            **original_stats,
            "enhanced_memory": {
                "hit_ratio": enhanced_stats.hit_ratio,
                "operations_per_second": enhanced_stats.operations_per_second,
                "memory_usage_mb": enhanced_stats.memory_usage_mb,
                "backend_type": enhanced_stats.backend_type
            }
        }
    
    # Backward compatibility properties
    @property 
    def db_path(self):
        """Backward compatibility."""
        return self._original_memory.db_path
    
    def close(self):
        """Close connections."""
        if hasattr(self._original_memory, 'close'):
            self._original_memory.close()

# Easy migration function
def upgrade_shared_project_memory(run_dir: str = None, backend_type: str = "hybrid"):
    """
    Upgrade your existing SharedProjectMemory to the enhanced version.
    
    Usage:
        # Instead of: memory = SharedProjectMemory(run_dir)
        memory = upgrade_shared_project_memory(run_dir)
        
        # Everything else works exactly the same!
        memory.set("key", "value")
        memory.store_agent_result("agent", result)
    """
    return EnhancedSharedProjectMemory(run_dir=run_dir, backend_type=backend_type) 