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
import base64
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple, Iterator, AsyncIterator
from langgraph.checkpoint.base import BaseCheckpointSaver, Checkpoint, CheckpointMetadata, CheckpointTuple
from langchain_core.runnables import RunnableConfig
from langchain_core.load import dumpd
from enhanced_memory_manager import EnhancedMemoryManager, MemoryConfig, MemoryBackend

logger = logging.getLogger(__name__)

# Custom JSON encoder/decoder for bytes
class BytesEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, bytes):
            return {"__bytes__": True, "value": base64.b64encode(obj).decode('utf-8')}
        return super().default(obj)

def bytes_decoder(dct):
    if "__bytes__" in dct:
        return base64.b64decode(dct["value"])
    return dct

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
    
    def _dump(self, obj: Any) -> str:
        """Dump the object to a JSON string using the new dumpd method."""
        # Use the recommended dumpd function which correctly handles
        # LangChain's serializable objects.
        return json.dumps(dumpd(obj), ensure_ascii=False, cls=BytesEncoder)
    
    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
    ) -> RunnableConfig:
        """Save a checkpoint and its metadata using enhanced memory."""
        try:
            thread_id = config["configurable"]["thread_id"]
            
            # Ensure metadata has required fields
            if "step" not in metadata:
                metadata["step"] = 0
            
            # Combine checkpoint and metadata for atomic storage
            saved_data = {"checkpoint": checkpoint, "metadata": metadata}
            
            data_str = self._dump(saved_data)
            self.memory.set(thread_id, data_str, context="checkpoints")
            
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
            data_str = self.memory.get(thread_id, context="checkpoints")

            if data_str is None:
                return None

            saved_data = json.loads(data_str, object_hook=bytes_decoder)
            
            checkpoint_dict = saved_data["checkpoint"]
            metadata = saved_data.get("metadata")

            # Manually reconstruct the Checkpoint and CheckpointTuple
            checkpoint = Checkpoint(
                v=checkpoint_dict.get("v", 1),
                ts=checkpoint_dict["ts"],
                channel_values=checkpoint_dict["channel_values"],
                channel_versions=checkpoint_dict["channel_versions"],
                versions_seen=checkpoint_dict["versions_seen"],
            )
            # The 'id' is crucial for resuming, but not part of the base Checkpoint TypedDict.
            # We need to add it back in manually.
            if "id" in checkpoint_dict:
                checkpoint["id"] = checkpoint_dict["id"]
            # Also preserve other fields like 'pending_sends' that LangGraph expects.
            if "pending_sends" in checkpoint_dict:
                checkpoint["pending_sends"] = checkpoint_dict["pending_sends"]

            parent_config_dict = checkpoint_dict.get("parent_config")
            parent_config = (
                {"configurable": parent_config_dict.get("configurable", {})}
                if parent_config_dict
                else None
            )

            return CheckpointTuple(config, checkpoint, metadata, parent_config)
            
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

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        *args, **kwargs
    ) -> RunnableConfig:
        """Async version of put method."""
        return await asyncio.to_thread(self.put, config, checkpoint, metadata)

    async def aget_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        """Async version of get_tuple method."""
        return await asyncio.to_thread(self.get_tuple, config)

    async def aput_writes(
        self, config: RunnableConfig, writes: List[Tuple[str, Any]], task_id: str
    ) -> RunnableConfig:
        """Async version of put_writes method to update a checkpoint."""
        checkpoint_tuple = await self.aget_tuple(config)

        if checkpoint_tuple:
            checkpoint = checkpoint_tuple.checkpoint
            metadata = checkpoint_tuple.metadata or {}
        else:
            checkpoint = Checkpoint(
                v=1,
                ts=datetime.now(timezone.utc).isoformat(),
                channel_values={},
                channel_versions={},
                versions_seen={},
            )
            metadata = {}

        # Apply writes to the checkpoint
        for channel, value in writes:
            checkpoint["channel_values"][channel] = value
        
        # Update metadata
        metadata["source"] = "update"
        metadata["writes"] = {chan: val for chan, val in writes}
        metadata["task_id"] = task_id
        if "step" not in metadata:
            metadata["step"] = 0

        return await self.aput(config, checkpoint, metadata)

    async def alist(
        self,
        config: RunnableConfig,
        *,
        filter: Optional[Dict[str, Any]] = None,
        before: Optional[RunnableConfig] = None,
        limit: Optional[int] = None,
    ) -> AsyncIterator[CheckpointTuple]:
        """Async version of list method."""
        # This is a simplified async wrapper.
        loop = asyncio.get_event_loop()
        iterator = await loop.run_in_executor(
            None, self.list, config, filter=filter, before=before, limit=limit
        )
        for item in iterator:
            yield item
