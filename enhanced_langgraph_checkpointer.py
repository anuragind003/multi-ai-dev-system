"""
Enhanced LangGraph Checkpointer using Enhanced Memory Manager

Integrates your powerful enhanced memory manager with LangGraph's checkpointing system
to provide persistent, high-performance checkpoint storage with multiple backends.
"""

import json
import logging
import time
import uuid
import asyncio
from typing import Dict, Any, Optional, List, Tuple, Iterator
from langgraph.checkpoint.base import BaseCheckpointSaver, Checkpoint, CheckpointMetadata, CheckpointTuple
from langchain_core.runnables import RunnableConfig
from langchain_core.load import dumpd
from enhanced_memory_manager import EnhancedMemoryManager, MemoryConfig, MemoryBackend

logger = logging.getLogger(__name__)

class EnhancedMemoryCheckpointer(BaseCheckpointSaver):
    """
    LangGraph checkpointer using your Enhanced Memory Manager.
    
    Features:
    - Persistent storage with multiple backends (SQLite, Redis, Hybrid)
    - Fast in-memory caching for hot checkpoints
    - Automatic cleanup and monitoring
    - Thread-safe operations
    - Backward compatibility with LangGraph
    """
    
    def __init__(self, 
                 memory_manager: EnhancedMemoryManager = None,
                 backend_type: str = "hybrid",
                 persistent_dir: str = None):
        """
        Initialize the enhanced checkpointer.
        
        Args:
            memory_manager: Existing memory manager (optional)
            backend_type: "hybrid", "sqlite", "redis", "auto"
            persistent_dir: Directory for persistent storage
        """
        super().__init__()
        
        if memory_manager:
            self.memory = memory_manager
        else:
            # Create new enhanced memory manager
            config = MemoryConfig(
                backend=MemoryBackend(backend_type),
                persistent_dir=persistent_dir or "./output/checkpoints",
                max_memory_mb=500,  # Larger for checkpoints
                enable_monitoring=True,
                auto_cleanup=True
            )
            self.memory = EnhancedMemoryManager(config)
        
        logger.info(f"Enhanced Memory Checkpointer initialized with backend: {self.memory.stats.backend_type}")
    
    def _dump(self, obj: Any) -> bytes:
        """Dump the object to bytes using the new dumpd method."""
        # Use the recommended dumpd function which correctly handles
        # LangChain's serializable objects.
        return json.dumps(dumpd(obj), ensure_ascii=False).encode("utf-8")
    
    def put(self, 
            config: RunnableConfig, 
            checkpoint: Checkpoint) -> RunnableConfig:
        """Save a checkpoint using enhanced memory."""
        try:
            thread_id = config["configurable"]["thread_id"]
            
            checkpoint_bytes = self._dump(checkpoint)
            self.memory.set(thread_id, checkpoint_bytes, context="checkpoints")
            
            return {
                "configurable": {
                    "thread_id": thread_id,
                    "thread_ts": checkpoint["ts"],
                }
            }
            
        except Exception as e:
            logger.error(f"Error saving checkpoint: {e}")
            raise
    
    def get_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        """Get checkpoint tuple using enhanced memory."""
        try:
            thread_id = config["configurable"]["thread_id"]
            checkpoint_bytes = self.memory.get(thread_id, context="checkpoints")

            if checkpoint_bytes is None:
                return None

            # Here we can just use standard json.loads since dumpd creates a simple dict
            checkpoint_dict = json.loads(checkpoint_bytes.decode("utf-8"))
            
            # Manually reconstruct the Checkpoint and CheckpointTuple
            checkpoint = Checkpoint(
                v=checkpoint_dict.get("v", 1),
                ts=checkpoint_dict["ts"],
                channel_values=checkpoint_dict["channel_values"],
                channel_versions=checkpoint_dict["channel_versions"],
                versions_seen=checkpoint_dict["versions_seen"],
            )

            parent_config_dict = checkpoint_dict.get("parent_config")
            parent_config = {"configurable": parent_config_dict.get("configurable", {})} if parent_config_dict else None

            return CheckpointTuple(config, checkpoint, parent_config)
            
        except Exception as e:
            logger.error(f"Error getting checkpoint: {e}")
            return None
    
    def list(self, 
             config: Dict[str, Any], 
             *, 
             filter: Optional[Dict[str, Any]] = None,
             before: Optional[str] = None,
             limit: Optional[int] = None) -> Iterator[CheckpointTuple]:
        """List checkpoints using enhanced memory."""
        try:
            thread_id = config["configurable"]["thread_id"]
            checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
            
            # Build context
            context = f"thread_{thread_id}"
            if checkpoint_ns:
                context = f"thread_{thread_id}_ns_{checkpoint_ns}"
            
            checkpoints = self._list_checkpoints(context)
            
            # Apply filters
            if before:
                checkpoints = [cp for cp in checkpoints if cp["checkpoint"]["id"] < before]
            
            # Sort by timestamp (newest first)
            checkpoints.sort(key=lambda x: x["timestamp"], reverse=True)
            
            # Apply limit
            if limit:
                checkpoints = checkpoints[:limit]
            
            # Yield as CheckpointTuple
            for checkpoint_data in checkpoints:
                yield CheckpointTuple(
                    config=checkpoint_data["config"],
                    checkpoint=checkpoint_data["checkpoint"],
                    metadata=checkpoint_data["metadata"],
                    parent_config=None,
                    pending_writes=[]
                )
                
        except Exception as e:
            logger.error(f"Error listing checkpoints: {e}")
    
    def _list_checkpoints(self, context: str) -> List[Dict[str, Any]]:
        """List all checkpoints for a context."""
        try:
            # Get all checkpoint keys for this context
            keys = self.memory.list_keys(context=context, pattern="checkpoint_*")
            
            checkpoints = []
            for key in keys:
                checkpoint_data = self.memory.get(key, context=context)
                if checkpoint_data:
                    checkpoints.append(checkpoint_data)
            
            return checkpoints
            
        except Exception as e:
            logger.error(f"Error listing checkpoints for context {context}: {e}")
            return []
    
    def delete_thread(self, thread_id: str) -> None:
        """Delete all checkpoints for a thread."""
        try:
            context = f"thread_{thread_id}"
            success = self.memory.clear_context(context)
            
            if success:
                logger.info(f"Deleted all checkpoints for thread {thread_id}")
            else:
                logger.warning(f"Failed to delete checkpoints for thread {thread_id}")
                
        except Exception as e:
            logger.error(f"Error deleting thread {thread_id}: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get checkpointer performance statistics."""
        memory_stats = self.memory.get_stats()
        return {
            "total_checkpoints": memory_stats.total_entries,
            "memory_usage_mb": memory_stats.memory_usage_mb,
            "hit_ratio": memory_stats.hit_ratio,
            "operations_per_second": memory_stats.operations_per_second,
            "backend_type": memory_stats.backend_type,
            "last_cleanup": memory_stats.last_cleanup
        }

    async def aput(self, config: RunnableConfig, checkpoint: Checkpoint) -> RunnableConfig:
        """Async version of put method."""
        return await asyncio.to_thread(self.put, config, checkpoint)

    async def aget_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        """Async version of get_tuple method."""
        return await asyncio.to_thread(self.get_tuple, config)

    def list(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List all checkpoints for a given thread."""
        checkpoints = self.memory.list_checkpoints(config["configurable"]["thread_id"])
        return [{"configurable": {"thread_id": config["configurable"]["thread_id"], "thread_ts": c["checkpoint_id"]}} for c in checkpoints]
        
    async def alist(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Async version of list method."""
        return await asyncio.to_thread(self.list, config)
