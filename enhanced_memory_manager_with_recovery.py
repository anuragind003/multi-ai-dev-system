"""
Enhanced Memory Manager with Full Recovery Capabilities
Integrates disk backup, session timeout management, checkpoints, and recovery
"""

import time
import logging
import asyncio
import os
import shutil
from typing import Dict, Any, Optional, List, Sequence, AsyncIterator, Iterator
from enhanced_memory_manager import EnhancedMemoryManager, MemoryConfig
from disk_backup_manager import DiskBackupManager
from session_timeout_manager import SessionTimeoutManager
from state_checkpoint_manager import StateCheckpointManager, CheckpointInfo
from data_recovery_manager import DataRecoveryManager, RecoveryStrategy
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import CheckpointTuple, Checkpoint, CheckpointMetadata

logger = logging.getLogger(__name__)

_memory_manager_instance: Optional["EnhancedMemoryManagerWithRecovery"] = None

class EnhancedMemoryManagerWithRecovery(EnhancedMemoryManager):
    """
    Enhanced Memory Manager with full recovery capabilities
    
    Adds:
    - Disk-based backup for server restart survival
    - Session timeout extension for human approvals
    - State checkpoints before critical operations
    - Data recovery mechanisms
    """
    
    def __init__(self, config: MemoryConfig = None, 
                 backup_dir: str = "./backups",
                 checkpoint_dir: str = "./checkpoints"):
        
        # Initialize base memory manager
        super().__init__(config)
        
        # Initialize recovery components
        self.backup_manager = DiskBackupManager(
            backup_dir=backup_dir,
            max_backups=100,
            backup_interval_seconds=300  # 5 minutes
        )
        
        self.session_manager = SessionTimeoutManager(
            default_timeout=3600,        # 1 hour
            approval_timeout=7200,       # 2 hours for approvals
            max_approval_timeout=86400   # 24 hours max
        )
        
        self.checkpoint_manager = StateCheckpointManager(
            checkpoint_dir=checkpoint_dir,
            max_checkpoints_per_session=20
        )
        
        self.recovery_manager = DataRecoveryManager(
            backup_manager=self.backup_manager,
            checkpoint_manager=self.checkpoint_manager,
            memory_manager=self
        )
        
        # Set up callbacks
        self.session_manager.timeout_warning_callback = self._handle_timeout_warning
        self.session_manager.session_expired_callback = self._handle_session_expired
        
        logger.info("Enhanced Memory Manager with Recovery initialized")
    
    def create_session(self, session_id: str, initial_state: Dict[str, Any] = None) -> str:
        """
        Create a new session with backup and timeout management
        
        Args:
            session_id: Session identifier
            initial_state: Initial state data
            
        Returns:
            Session ID
        """
        # Create session with normal timeout
        session_info = self.session_manager.create_session(session_id, False)
        
        # Store initial state if provided
        if initial_state:
            self.set("workflow_state", initial_state, context=session_id)
            
            # Create initial backup
            self.backup_manager.create_full_backup(session_id, initial_state)
            
            # Store original BRD content for recovery
            if "brd_content" in initial_state:
                self.set("original_brd_content", initial_state["brd_content"], context="session")
        
        logger.info(f"Session created with recovery support: {session_id}")
        return session_id
    
    def start_human_approval(self, session_id: str, approval_type: str, 
                           current_state: Dict[str, Any]) -> str:
        """
        Start human approval process with extended timeout and checkpoint
        
        Args:
            session_id: Session identifier
            approval_type: Type of approval (brd, tech_stack, system_design, plan)
            current_state: Current workflow state
            
        Returns:
            Checkpoint ID created
        """
        # Create pre-approval checkpoint
        checkpoint_id = self.checkpoint_manager.create_pre_approval_checkpoint(
            session_id=session_id,
            state=current_state,
            approval_type=approval_type,
            workflow_step=f"{approval_type}_approval"
        )
        
        # Transition session to approval mode with extended timeout
        self.session_manager.start_human_approval(session_id, approval_type)
        
        # Create backup
        self.backup_manager.create_full_backup(session_id, current_state)
        
        logger.info(f"Human approval started: {session_id} ({approval_type}) - Checkpoint: {checkpoint_id}")
        return checkpoint_id
    
    def end_human_approval(self, session_id: str, updated_state: Dict[str, Any]):
        """
        End human approval and return to normal timeout
        
        Args:
            session_id: Session identifier  
            updated_state: Updated state after approval
        """
        # Return to normal timeout
        self.session_manager.end_human_approval(session_id)
        
        # Update state
        self.set("workflow_state", updated_state, context=session_id)
        
        # Create backup with updated state
        self.backup_manager.create_full_backup(session_id, updated_state)
        
        logger.info(f"Human approval ended: {session_id}")
    
    def extend_session_timeout(self, session_id: str, additional_hours: int = 2) -> bool:
        """
        Extend session timeout (useful for long approval processes)
        
        Args:
            session_id: Session identifier
            additional_hours: Additional hours to add
            
        Returns:
            True if successful
        """
        additional_seconds = additional_hours * 3600
        return self.session_manager.extend_session_timeout(session_id, additional_seconds)
    
    def recover_session(self, session_id: str, 
                       strategy: RecoveryStrategy = None) -> Dict[str, Any]:
        """
        Recover a corrupted or lost session
        
        Args:
            session_id: Session identifier
            strategy: Preferred recovery strategy
            
        Returns:
            Recovered state data
        """
        logger.info(f"Starting session recovery: {session_id}")
        
        # Try to get current state
        current_state = self.get("workflow_state", context=session_id)
        
        # Check for corruption
        if current_state:
            is_corrupted = self.recovery_manager.detect_corruption(session_id, current_state)
            if not is_corrupted:
                logger.info("Session state appears healthy, no recovery needed")
                return current_state
        
        # Perform recovery
        recovered_state, recovery_method = self.recovery_manager.recover_state(
            session_id, current_state, strategy
        )
        
        # Verify recovered state
        if not self.recovery_manager.verify_recovered_state(recovered_state):
            logger.error("Recovered state failed verification")
            # Try alternative recovery
            recovered_state, recovery_method = self.recovery_manager.recover_state(
                session_id, None, RecoveryStrategy.CLEAN_RESTART
            )
        
        # Store recovered state
        self.set("workflow_state", recovered_state, context=session_id)
        
        # Create backup of recovered state
        self.backup_manager.create_full_backup(session_id, recovered_state)
        
        logger.info(f"Session recovery completed: {session_id} using {recovery_method}")
        return recovered_state
    
    def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """
        Get comprehensive status information for a session
        
        Args:
            session_id: Session identifier
            
        Returns:
            Status information dictionary
        """
        session_info = self.session_manager.get_session_info(session_id)
        time_remaining = self.session_manager.get_time_remaining(session_id)
        
        # Get backup information
        latest_backup = self.backup_manager.get_latest_backup(session_id)
        backup_count = len(self.backup_manager.list_backups(session_id))
        
        # Get checkpoint information
        latest_checkpoint = self.checkpoint_manager.get_latest_checkpoint(session_id)
        checkpoint_count = len(self.checkpoint_manager.list_checkpoints(session_id))
        
        status = {
            "session_active": self.session_manager.is_session_active(session_id),
            "time_remaining_seconds": time_remaining,
            "session_info": session_info.__dict__ if session_info else None,
            "backup_info": {
                "latest_backup": latest_backup,
                "total_backups": backup_count
            },
            "checkpoint_info": {
                "latest_checkpoint": latest_checkpoint.__dict__ if latest_checkpoint else None,
                "total_checkpoints": checkpoint_count
            }
        }
        
        return status
    
    def get_active_sessions(self) -> List[str]:
        """Returns a list of active session IDs from the session manager."""
        if hasattr(self.session_manager, 'get_active_sessions'):
            return self.session_manager.get_active_sessions()
        if hasattr(self.session_manager, 'sessions') and isinstance(self.session_manager.sessions, dict):
            return list(self.session_manager.sessions.keys())
        logger.warning("Could not determine active sessions from session manager.")
        return []

    def _create_disk_backup(self):
        """Creates a disk backup of all active session states."""
        active_sessions = self.get_active_sessions()
        if not active_sessions:
            logger.info("No active sessions found to back up.")
            return

        logger.info(f"Performing disk backup for {len(active_sessions)} session(s).")
        success_count = 0
        for session_id in active_sessions:
            state = self.get("workflow_state", context=session_id)
            if state:
                try:
                    self.backup_manager.create_full_backup(session_id, state)
                    success_count += 1
                except Exception as e:
                    logger.error(f"Failed to create backup for session {session_id}: {e}")
            else:
                logger.warning(f"No workflow state found for session {session_id} during global backup.")
        logger.info(f"Disk backup process completed. Successfully backed up {success_count}/{len(active_sessions)} sessions.")
    
    def get_memory_stats(self):
        """Get memory stats for monitoring"""
        return {
            "keys_count": len(self.list_keys()),
            "backend_type": self.stats.backend_type,
            "recovery_enabled": True,
            "sessions": self.get_active_sessions()
        }
    
    def _handle_timeout_warning(self, session_id: str, remaining_seconds: int):
        """Handle session timeout warnings"""
        logger.warning(f"Session timeout warning: {session_id} ({remaining_seconds}s remaining)")
        
        # Could notify frontend here via WebSocket
        # or send email notifications
    
    def _handle_session_expired(self, session_id: str, session_info):
        """Handle expired sessions"""
        logger.info(f"Session expired: {session_id}")
        
        # Create final backup before cleanup
        try:
            final_state = self.get("workflow_state", context=session_id)
            if final_state:
                self.backup_manager.create_full_backup(session_id, final_state)
        except Exception as e:
            logger.error(f"Failed to create final backup for expired session: {e}")
    
    def cleanup_resources(self):
        """Clean up resources and stop background threads"""
        try:
            self.backup_manager.stop_backup_thread()
            self.session_manager.stop_cleanup_thread()
            logger.info("Enhanced Memory Manager resources cleaned up")
        except Exception as e:
            logger.error(f"Error during resource cleanup: {e}")
    
    def get_recovery_stats(self) -> Dict[str, Any]:
        """Get statistics about recovery system performance"""
        stats = {
            "memory_stats": self.get_stats().__dict__,
            "session_stats": self.session_manager.get_stats(),
            "backup_stats": {
                "total_backups": self.backup_manager.backup_count,
                "last_backup_time": self.backup_manager.last_backup_time
            }
        }
        return stats

    def get_next_version(self, config: RunnableConfig, current_version: Optional[int] = None) -> int:
        """Gets the next version for a checkpoint, using a timestamp."""
        return int(time.time() * 1_000_000)

    def get(self, *args, **kwargs) -> Optional[Checkpoint]:
        """
        Dispatcher for the get method.
        
        This method checks the arguments to decide whether to call the
        checkpointer's get method or the memory manager's get method.
        """
        # If 'config' is in kwargs, it's likely a checkpointer call
        if 'config' in kwargs:
            return self._checkpointer_get(kwargs['config'])
        # If the first arg is a dict with 'configurable', it's also a checkpointer call
        if args and isinstance(args[0], dict) and 'configurable' in args[0]:
            return self._checkpointer_get(args[0])
        
        # Otherwise, assume it's a call to the base memory manager's get
        return super().get(*args, **kwargs)

    def _checkpointer_get(self, config: RunnableConfig) -> Optional[Checkpoint]:
        """Loads a checkpoint from the underlying state manager."""
        checkpoint_tuple = self.get_tuple(config)
        return checkpoint_tuple.checkpoint if checkpoint_tuple else None

    def get_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        """Loads a checkpoint tuple from the underlying state manager."""
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ts = config["configurable"].get("thread_ts")

        checkpoint_info: Optional[CheckpointInfo] = None
        if checkpoint_ts:
            checkpoint_info = self.checkpoint_manager.get_checkpoint(checkpoint_ts)
        else:
            checkpoint_info = self.checkpoint_manager.get_latest_checkpoint(thread_id)

        if checkpoint_info:
            checkpoint = self.checkpoint_manager.restore_checkpoint(checkpoint_info.checkpoint_id)
            if checkpoint:
                parent_config = None
                if parent_ts := checkpoint.get("parent_ts"):
                    parent_config = {"configurable": {"thread_id": thread_id, "thread_ts": parent_ts}}

                return CheckpointTuple(
                    config={"configurable": {"thread_id": thread_id, "thread_ts": checkpoint_info.checkpoint_id}},
                    checkpoint=checkpoint,
                    metadata=checkpoint.get("metadata", {}),
                    parent_config=parent_config,
                )
        return None

    def list(self, config: RunnableConfig, *, filter: Optional[dict[str, Any]] = None, before: Optional[RunnableConfig] = None, limit: Optional[int] = None) -> Iterator[CheckpointTuple]:
        """Lists all checkpoints for a given session."""
        thread_id = config["configurable"]["thread_id"]
        checkpoint_infos = self.checkpoint_manager.list_checkpoints(thread_id)

        checkpoint_infos.sort(key=lambda info: info.timestamp, reverse=True)

        if before:
            before_checkpoint_id = before["configurable"]["thread_ts"]
            before_info = self.checkpoint_manager.get_checkpoint(before_checkpoint_id)
            if before_info:
                before_ts_float = before_info.timestamp
                checkpoint_infos = [info for info in checkpoint_infos if info.timestamp < before_ts_float]
            else:
                # If the 'before' checkpoint is not found, no checkpoints are before it.
                checkpoint_infos = []

        if limit is not None:
            checkpoint_infos = checkpoint_infos[:limit]

        for info in checkpoint_infos:
            checkpoint = self.checkpoint_manager.restore_checkpoint(info.checkpoint_id)
            if checkpoint:
                parent_config = None
                if parent_ts := checkpoint.get("parent_ts"):
                    parent_config = {"configurable": {"thread_id": thread_id, "thread_ts": parent_ts}}

                if filter:
                    metadata = checkpoint.get("metadata", {})
                    if not all(metadata.get(k) == v for k, v in filter.items()):
                        continue

                yield CheckpointTuple(
                    config={"configurable": {"thread_id": thread_id, "thread_ts": info.checkpoint_id}},
                    checkpoint=checkpoint,
                    metadata=checkpoint.get("metadata", {}),
                    parent_config=parent_config,
                )

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: Any,
    ) -> RunnableConfig:
        """Saves a checkpoint to the underlying state manager."""
        thread_id = config["configurable"]["thread_id"]
        checkpoint_id = checkpoint["id"]
        
        full_checkpoint = {**checkpoint, "metadata": metadata}
        if config["configurable"].get("thread_ts"):
            full_checkpoint["parent_ts"] = config["configurable"]["thread_ts"]

        self.checkpoint_manager.save_checkpoint(
            session_id=thread_id,
            checkpoint_id=str(checkpoint_id),
            state=full_checkpoint,
            workflow_step="langgraph_put",
        )
        return {"configurable": {"thread_id": thread_id, "thread_ts": checkpoint_id}}

    def put_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
    ) -> None:
        """Logs intermediate writes; does not persist them."""
        thread_id = config["configurable"]["thread_id"]
        logger.debug(f"WRITES for thread {thread_id} task {task_id}: {writes}")

    def delete_thread(self, config: RunnableConfig) -> None:
        """Deletes all checkpoints for a given thread."""
        thread_id = config["configurable"]["thread_id"]
        checkpoint_infos = self.checkpoint_manager.list_checkpoints(thread_id)
        if not checkpoint_infos:
            logger.info(f"No checkpoints found to delete for thread_id: {thread_id}")
            return

        deleted_count = 0
        for info in checkpoint_infos:
            if self.checkpoint_manager.delete_checkpoint(info.checkpoint_id):
                deleted_count += 1
        
        logger.info(f"Deleted {deleted_count}/{len(checkpoint_infos)} checkpoints for thread_id: {thread_id}")

    def list_session_checkpoints(self, session_id: str) -> List[CheckpointInfo]:
        """Lists all checkpoints for a given session."""
        return self.checkpoint_manager.list_checkpoints(session_id)

    # -- Checkpointer Implementation (Async) --

    async def aget(self, *args, **kwargs) -> Optional[Checkpoint]:
        """Asynchronously dispatches the get method call."""
        # This simple dispatch should work for async as well,
        # as we are just passing the arguments along.
        if 'config' in kwargs:
            return await self._acheckpointer_get(kwargs['config'])
        if args and isinstance(args[0], dict) and 'configurable' in args[0]:
            return await self._acheckpointer_get(args[0])

        # The base class's `aget` doesn't exist, so we can't call super().aget
        # We assume async calls with this signature are not for the base memory manager
        # If they were, we would need to implement an async get in the base class.
        logger.warning("aget called with non-checkpointer arguments, but base class has no aget. Returning None.")
        return None

    async def _acheckpointer_get(self, config: RunnableConfig) -> Optional[Checkpoint]:
        """Loads a checkpoint asynchronously."""
        return await asyncio.to_thread(self._checkpointer_get, config)

    async def aget_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        """Loads a checkpoint tuple asynchronously."""
        return await asyncio.to_thread(self.get_tuple, config)

    async def alist(self, config: RunnableConfig, *, filter: Optional[dict[str, Any]] = None, before: Optional[RunnableConfig] = None, limit: Optional[int] = None) -> AsyncIterator[CheckpointTuple]:
        """Lists all checkpoints for a given session asynchronously."""
        sync_iterator = self.list(config, filter=filter, before=before, limit=limit)
        
        def get_next(it):
            try:
                return next(it)
            except StopIteration:
                return None

        loop = asyncio.get_running_loop()
        while True:
            item = await loop.run_in_executor(None, get_next, sync_iterator)
            if item is None:
                break
            yield item

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: Any,
    ) -> RunnableConfig:
        """Saves a checkpoint to the underlying state manager asynchronously."""
        return await asyncio.to_thread(self.put, config, checkpoint, metadata, new_versions)

    async def aput_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
    ) -> None:
        """Stores intermediate writes asynchronously."""
        await asyncio.to_thread(self.put_writes, config, writes, task_id)

    async def adelete_thread(self, config: RunnableConfig) -> None:
        """Deletes all checkpoints for a given thread asynchronously."""
        await asyncio.to_thread(self.delete_thread, config)

def get_enhanced_memory_manager() -> "EnhancedMemoryManagerWithRecovery":
    """
    Singleton accessor for the EnhancedMemoryManagerWithRecovery.
    This ensures a single instance is used throughout the application.
    """
    global _memory_manager_instance
    if _memory_manager_instance is None:
        logger.info("Creating a new global instance of EnhancedMemoryManagerWithRecovery.")
        _memory_manager_instance = create_enhanced_memory_with_recovery()
    return _memory_manager_instance

# Factory function for easy creation
def create_enhanced_memory_with_recovery(config: MemoryConfig = None,
                                       backup_dir: str = "./backups",
                                       checkpoint_dir: str = "./checkpoints") -> EnhancedMemoryManagerWithRecovery:
    """
    Factory function to create Enhanced Memory Manager with Recovery
    
    Args:
        config: Memory configuration
        backup_dir: Directory for backups
        checkpoint_dir: Directory for checkpoints
        
    Returns:
        Configured EnhancedMemoryManagerWithRecovery instance
    """
    return EnhancedMemoryManagerWithRecovery(config, backup_dir, checkpoint_dir)