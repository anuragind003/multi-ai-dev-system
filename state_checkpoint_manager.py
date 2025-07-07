"""
State Serialization Checkpoint Manager
Creates checkpoints before human approval pauses
"""

import os
import json
import pickle
import time
import hashlib
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class CheckpointInfo:
    """Information about a state checkpoint"""
    checkpoint_id: str
    session_id: str
    workflow_step: str
    timestamp: float
    data_hash: str
    size_bytes: int
    approval_type: str
    compressed: bool

class StateCheckpointManager:
    """
    Manages state serialization checkpoints before human approval pauses
    
    Features:
    - Automatic checkpoint creation before human approvals
    - State integrity verification
    - Fast checkpoint recovery
    - Checkpoint metadata tracking
    """
    
    def __init__(self, checkpoint_dir: str = "./checkpoints", 
                 max_checkpoints_per_session: int = 10,
                 enable_compression: bool = True):
        
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_checkpoints_per_session = max_checkpoints_per_session
        self.enable_compression = enable_compression
        
        logger.info(f"State Checkpoint Manager initialized: {checkpoint_dir}")
    
    def save_checkpoint(self, session_id: str, checkpoint_id: str, state: Dict[str, Any], workflow_step: str, approval_type: str = "auto") -> str:
        """
        Saves a generic checkpoint.

        Args:
            session_id: Session identifier.
            checkpoint_id: Unique ID for the checkpoint (e.g., from langgraph's thread_ts).
            state: Current workflow state.
            workflow_step: The step in the workflow.
            approval_type: Optional approval type.

        Returns:
            The checkpoint ID.
        """
        try:
            # Serialize state data
            if self.enable_compression:
                import gzip
                serialized_data = gzip.compress(pickle.dumps(state))
            else:
                serialized_data = pickle.dumps(state)

            # Create checkpoint file
            checkpoint_path = self.checkpoint_dir / f"{checkpoint_id}.checkpoint"
            with open(checkpoint_path, 'wb') as f:
                f.write(serialized_data)
            
            # Create checkpoint metadata
            data_hash = hashlib.sha256(serialized_data).hexdigest()
            checkpoint_info = CheckpointInfo(
                checkpoint_id=checkpoint_id,
                session_id=session_id,
                workflow_step=workflow_step,
                timestamp=time.time(),
                data_hash=data_hash,
                size_bytes=len(serialized_data),
                approval_type=approval_type,
                compressed=self.enable_compression
            )
            
            self._save_checkpoint_metadata(checkpoint_info)
            self._cleanup_old_checkpoints(session_id)
            
            logger.info(f"Saved checkpoint: {checkpoint_id}")
            return checkpoint_id
            
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
            raise
    
    def create_pre_approval_checkpoint(self, session_id: str, state: Dict[str, Any], 
                                     approval_type: str, workflow_step: str) -> str:
        """
        Create a checkpoint before human approval
        
        Args:
            session_id: Session identifier
            state: Current workflow state
            approval_type: Type of approval (brd, tech_stack, system_design, plan)
            workflow_step: Current workflow step name
            
        Returns:
            Checkpoint ID
        """
        timestamp = time.time()
        checkpoint_id = f"pre_approval_{approval_type}_{session_id}_{int(timestamp)}"
        
        return self.save_checkpoint(
            session_id=session_id,
            checkpoint_id=checkpoint_id,
            state=state,
            workflow_step=workflow_step,
            approval_type=approval_type
        )
    
    def restore_checkpoint(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """
        Restore state from a checkpoint
        
        Args:
            checkpoint_id: ID of checkpoint to restore
            
        Returns:
            Restored state data or None if failed
        """
        try:
            checkpoint_path = self.checkpoint_dir / f"{checkpoint_id}.checkpoint"
            
            if not checkpoint_path.exists():
                logger.error(f"Checkpoint file not found: {checkpoint_path}")
                return None
            
            # Load checkpoint metadata for verification
            metadata = self._load_checkpoint_metadata(checkpoint_id)
            
            # Load checkpoint data
            with open(checkpoint_path, 'rb') as f:
                serialized_data = f.read()
            
            # Verify data integrity
            if metadata:
                data_hash = hashlib.sha256(serialized_data).hexdigest()
                if data_hash != metadata.data_hash:
                    logger.error(f"Checkpoint data integrity check failed: {checkpoint_id}")
                    return None
            
            # Deserialize state
            if metadata and metadata.compressed:
                import gzip
                state = pickle.loads(gzip.decompress(serialized_data))
            else:
                state = pickle.loads(serialized_data)
            
            logger.info(f"Successfully restored checkpoint: {checkpoint_id}")
            return state
            
        except Exception as e:
            logger.error(f"Failed to restore checkpoint {checkpoint_id}: {e}")
            return None
    
    def list_checkpoints(self, session_id: str = None) -> List[CheckpointInfo]:
        """
        List available checkpoints, optionally filtered by session
        
        Args:
            session_id: Optional session filter
            
        Returns:
            List of CheckpointInfo objects
        """
        checkpoints = []
        
        try:
            for metadata_file in self.checkpoint_dir.glob("*.metadata"):
                metadata = self._load_metadata_from_file(metadata_file)
                if metadata:
                    if session_id is None or metadata.session_id == session_id:
                        checkpoints.append(metadata)
            
            # Sort by timestamp (newest first)
            checkpoints.sort(key=lambda c: c.timestamp, reverse=True)
            return checkpoints
            
        except Exception as e:
            logger.error(f"Failed to list checkpoints: {e}")
            return []
    
    def get_checkpoint(self, checkpoint_id: str) -> Optional[CheckpointInfo]:
        """
        Gets a specific checkpoint's metadata by its ID.

        Args:
            checkpoint_id: The ID of the checkpoint to retrieve.

        Returns:
            CheckpointInfo if found, else None.
        """
        try:
            metadata_path = self.checkpoint_dir / f"{checkpoint_id}.metadata"
            if metadata_path.exists():
                return self._load_metadata_from_file(metadata_path)
            else:
                logger.warning(f"Checkpoint metadata not found for id: {checkpoint_id}")
                return None
        except Exception as e:
            logger.error(f"Failed to get checkpoint {checkpoint_id}: {e}")
            return None

    def get_latest_checkpoint(self, session_id: str, approval_type: str = None) -> Optional[CheckpointInfo]:
        """
        Get the latest checkpoint for a session
        
        Args:
            session_id: Session identifier
            approval_type: Optional approval type filter
            
        Returns:
            Latest CheckpointInfo or None
        """
        checkpoints = self.list_checkpoints(session_id)
        
        if approval_type:
            checkpoints = [c for c in checkpoints if c.approval_type == approval_type]
        
        return checkpoints[0] if checkpoints else None
    
    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """
        Delete a specific checkpoint
        
        Args:
            checkpoint_id: ID of checkpoint to delete
            
        Returns:
            True if successful
        """
        try:
            # Remove checkpoint file
            checkpoint_path = self.checkpoint_dir / f"{checkpoint_id}.checkpoint"
            if checkpoint_path.exists():
                checkpoint_path.unlink()
            
            # Remove metadata file
            metadata_path = self.checkpoint_dir / f"{checkpoint_id}.metadata"
            if metadata_path.exists():
                metadata_path.unlink()
            
            logger.info(f"Checkpoint deleted: {checkpoint_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete checkpoint {checkpoint_id}: {e}")
            return False
    
    def _save_checkpoint_metadata(self, checkpoint_info: CheckpointInfo):
        """Save checkpoint metadata"""
        metadata_path = self.checkpoint_dir / f"{checkpoint_info.checkpoint_id}.metadata"
        
        with open(metadata_path, 'w') as f:
            json.dump(asdict(checkpoint_info), f, indent=2)
    
    def _load_checkpoint_metadata(self, checkpoint_id: str) -> Optional[CheckpointInfo]:
        """Load checkpoint metadata"""
        metadata_path = self.checkpoint_dir / f"{checkpoint_id}.metadata"
        return self._load_metadata_from_file(metadata_path)
    
    def _load_metadata_from_file(self, metadata_path: Path) -> Optional[CheckpointInfo]:
        """Load checkpoint metadata from file"""
        try:
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    data = json.load(f)
                return CheckpointInfo(**data)
        except Exception as e:
            logger.error(f"Failed to load metadata from {metadata_path}: {e}")
        return None
    
    def _cleanup_old_checkpoints(self, session_id: str):
        """Remove old checkpoints for a session to stay within limit"""
        try:
            checkpoints = self.list_checkpoints(session_id)
            
            if len(checkpoints) > self.max_checkpoints_per_session:
                # Keep the newest checkpoints, remove the oldest
                to_remove = checkpoints[self.max_checkpoints_per_session:]
                
                for checkpoint in to_remove:
                    self.delete_checkpoint(checkpoint.checkpoint_id)
                
                logger.debug(f"Cleaned up {len(to_remove)} old checkpoints for session {session_id}")
                
        except Exception as e:
            logger.error(f"Failed to cleanup old checkpoints: {e}")