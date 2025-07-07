"""
Data Recovery Manager
Handles recovery from corrupted or lost state data
"""

import os
import json
import pickle
import time
import logging
import threading
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)

class RecoveryStrategy(Enum):
    """Recovery strategies for different types of data corruption"""
    LATEST_BACKUP = "latest_backup"
    LATEST_CHECKPOINT = "latest_checkpoint"
    RECONSTRUCT_FROM_LOGS = "reconstruct_from_logs"
    PARTIAL_RECOVERY = "partial_recovery"
    CLEAN_RESTART = "clean_restart"

class DataRecoveryManager:
    """
    Manages recovery from corrupted or lost state data
    
    Features:
    - Multiple recovery strategies
    - Data integrity verification
    - Automatic corruption detection
    - Recovery strategy selection
    - Data reconstruction from logs
    """
    
    def __init__(self, 
                 backup_manager,      # DiskBackupManager instance
                 checkpoint_manager,  # StateCheckpointManager instance
                 memory_manager):     # EnhancedMemoryManager instance
        
        self.backup_manager = backup_manager
        self.checkpoint_manager = checkpoint_manager
        self.memory_manager = memory_manager
        
        logger.info("Data Recovery Manager initialized")
    
    def detect_corruption(self, session_id: str, current_state: Dict[str, Any]) -> bool:
        """
        Detect if the current state appears to be corrupted
        
        Args:
            session_id: Session identifier
            current_state: Current state to check
            
        Returns:
            True if corruption is detected
        """
        try:
            # Check for essential state keys
            essential_keys = [
                "workflow_id", "workflow_start_time", "brd_content"
            ]
            
            missing_keys = [key for key in essential_keys if key not in current_state]
            if missing_keys:
                logger.warning(f"Missing essential state keys: {missing_keys}")
                return True
            
            # Check for data type consistency
            if not isinstance(current_state.get("workflow_start_time"), (int, float)):
                logger.warning("workflow_start_time is not a number")
                return True
            
            # Check for empty or None critical values
            if not current_state.get("brd_content"):
                logger.warning("brd_content is empty or None")
                return True
            
            # Check for reasonable workflow start time (not too old or in future)
            start_time = current_state.get("workflow_start_time", 0)
            current_time = time.time()
            if start_time > current_time or (current_time - start_time) > 86400:  # 24 hours
                logger.warning("workflow_start_time appears invalid")
                return True
            
            # Additional integrity checks can be added here
            
            logger.debug(f"No corruption detected in state for session {session_id}")
            return False
            
        except Exception as e:
            logger.error(f"Error during corruption detection: {e}")
            return True  # Assume corruption if we can't check properly
    
    def recover_state(self, session_id: str, 
                     corrupted_state: Dict[str, Any] = None,
                     strategy: RecoveryStrategy = None) -> Tuple[Dict[str, Any], str]:
        """
        Recover state data using the best available strategy
        
        Args:
            session_id: Session identifier
            corrupted_state: The corrupted state (if available)
            strategy: Preferred recovery strategy
            
        Returns:
            Tuple of (recovered_state, recovery_method_used)
        """
        logger.info(f"Starting state recovery for session {session_id}")
        
        # Determine the best recovery strategy if not specified
        if strategy is None:
            strategy = self._determine_best_strategy(session_id, corrupted_state)
        
        logger.info(f"Using recovery strategy: {strategy.value}")
        
        # Execute recovery strategy
        if strategy == RecoveryStrategy.LATEST_CHECKPOINT:
            return self._recover_from_checkpoint(session_id)
        
        elif strategy == RecoveryStrategy.LATEST_BACKUP:
            return self._recover_from_backup(session_id)
        
        elif strategy == RecoveryStrategy.PARTIAL_RECOVERY:
            return self._partial_recovery(session_id, corrupted_state)
        
        elif strategy == RecoveryStrategy.RECONSTRUCT_FROM_LOGS:
            return self._reconstruct_from_logs(session_id)
        
        elif strategy == RecoveryStrategy.CLEAN_RESTART:
            return self._clean_restart(session_id)
        
        else:
            logger.error(f"Unknown recovery strategy: {strategy}")
            return self._clean_restart(session_id)
    
    def _determine_best_strategy(self, session_id: str, 
                               corrupted_state: Dict[str, Any]) -> RecoveryStrategy:
        """Determine the best recovery strategy for the situation"""
        
        # Check if recent checkpoint exists
        recent_checkpoint = self.checkpoint_manager.get_latest_checkpoint(session_id)
        if recent_checkpoint and (time.time() - recent_checkpoint.timestamp) < 3600:  # 1 hour
            logger.info("Recent checkpoint available, using checkpoint recovery")
            return RecoveryStrategy.LATEST_CHECKPOINT
        
        # Check if recent backup exists
        recent_backup = self.backup_manager.get_latest_backup(session_id)
        if recent_backup:
            logger.info("Backup available, using backup recovery")
            return RecoveryStrategy.LATEST_BACKUP
        
        # Check if partial recovery is possible
        if corrupted_state and len(corrupted_state) > 2:
            logger.info("Partial state available, attempting partial recovery")
            return RecoveryStrategy.PARTIAL_RECOVERY
        
        # Fall back to clean restart
        logger.info("No good recovery options, using clean restart")
        return RecoveryStrategy.CLEAN_RESTART
    
    def _recover_from_checkpoint(self, session_id: str) -> Tuple[Dict[str, Any], str]:
        """Recover from the latest checkpoint"""
        try:
            latest_checkpoint = self.checkpoint_manager.get_latest_checkpoint(session_id)
            
            if not latest_checkpoint:
                logger.warning("No checkpoints available for recovery")
                return self._recover_from_backup(session_id)
            
            recovered_state = self.checkpoint_manager.restore_checkpoint(
                latest_checkpoint.checkpoint_id
            )
            
            if recovered_state:
                logger.info(f"Successfully recovered from checkpoint: {latest_checkpoint.checkpoint_id}")
                return recovered_state, f"checkpoint:{latest_checkpoint.checkpoint_id}"
            else:
                logger.error("Failed to restore from checkpoint")
                return self._recover_from_backup(session_id)
                
        except Exception as e:
            logger.error(f"Error during checkpoint recovery: {e}")
            return self._recover_from_backup(session_id)
    
    def _recover_from_backup(self, session_id: str) -> Tuple[Dict[str, Any], str]:
        """Recover from the latest backup"""
        try:
            latest_backup = self.backup_manager.get_latest_backup(session_id)
            
            if not latest_backup:
                logger.warning("No backups available for recovery")
                return self._clean_restart(session_id)
            
            recovered_state = self.backup_manager.restore_from_backup(latest_backup)
            
            if recovered_state:
                logger.info(f"Successfully recovered from backup: {latest_backup}")
                return recovered_state, f"backup:{latest_backup}"
            else:
                logger.error("Failed to restore from backup")
                return self._clean_restart(session_id)
                
        except Exception as e:
            logger.error(f"Error during backup recovery: {e}")
            return self._clean_restart(session_id)
    
    def _partial_recovery(self, session_id: str, 
                         corrupted_state: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        """Attempt to recover usable parts from corrupted state"""
        try:
            logger.info("Attempting partial recovery from corrupted state")
            
            # Start with a clean base state
            recovered_state = self._create_minimal_state(session_id)
            
            # Try to salvage useful data from corrupted state
            salvageable_keys = [
                "brd_content", "requirements_analysis", "tech_stack_recommendation",
                "system_design", "implementation_plan", "code_generation_result"
            ]
            
            for key in salvageable_keys:
                if key in corrupted_state:
                    try:
                        # Basic validation of the data
                        value = corrupted_state[key]
                        if value is not None and value != "":
                            recovered_state[key] = value
                            logger.debug(f"Salvaged key: {key}")
                    except Exception as e:
                        logger.warning(f"Could not salvage key {key}: {e}")
            
            logger.info(f"Partial recovery completed with {len(recovered_state)} keys")
            return recovered_state, "partial_recovery"
            
        except Exception as e:
            logger.error(f"Error during partial recovery: {e}")
            return self._clean_restart(session_id)
    
    def _reconstruct_from_logs(self, session_id: str) -> Tuple[Dict[str, Any], str]:
        """Attempt to reconstruct state from log files"""
        try:
            logger.info("Attempting to reconstruct state from logs")
            
            # This is a placeholder for log-based reconstruction
            # In a real implementation, you would parse log files to rebuild state
            
            # For now, return clean restart
            logger.warning("Log reconstruction not implemented, falling back to clean restart")
            return self._clean_restart(session_id)
            
        except Exception as e:
            logger.error(f"Error during log reconstruction: {e}")
            return self._clean_restart(session_id)
    
    def _clean_restart(self, session_id: str) -> Tuple[Dict[str, Any], str]:
        """Create a clean initial state for restart"""
        try:
            logger.info("Performing clean restart")
            
            recovered_state = self._create_minimal_state(session_id)
            
            # Add any preserved data from memory
            try:
                preserved_brd = self.memory_manager.get("original_brd_content", context="session")
                if preserved_brd:
                    recovered_state["brd_content"] = preserved_brd
                    logger.info("Recovered original BRD content from memory")
            except Exception as e:
                logger.warning(f"Could not recover BRD content: {e}")
            
            logger.info("Clean restart completed")
            return recovered_state, "clean_restart"
            
        except Exception as e:
            logger.error(f"Error during clean restart: {e}")
            # Return absolute minimal state
            return {
                "workflow_id": f"recovered_{session_id}_{int(time.time())}",
                "workflow_start_time": time.time(),
                "brd_content": "Recovery mode - please provide BRD content",
                "errors": [f"Data recovery error: {str(e)}"]
            }, "emergency_restart"
    
    def _create_minimal_state(self, session_id: str) -> Dict[str, Any]:
        """Create a minimal valid state"""
        return {
            "workflow_id": f"recovered_{session_id}_{int(time.time())}",
            "workflow_start_time": time.time(),
            "current_phase_index": 0,
            "architecture_revision_count": 0,
            "database_revision_count": 0,
            "backend_revision_count": 0,
            "frontend_revision_count": 0,
            "integration_revision_count": 0,
            "errors": [],
            "code_generation_result": {
                "generated_files": {},
                "status": "not_started"
            },
            "recovery_info": {
                "recovered_at": time.time(),
                "recovery_session": session_id,
                "recovery_reason": "data_corruption"
            }
        }
    
    def verify_recovered_state(self, recovered_state: Dict[str, Any]) -> bool:
        """Verify that the recovered state is valid"""
        try:
            # Check essential keys
            essential_keys = ["workflow_id", "workflow_start_time"]
            for key in essential_keys:
                if key not in recovered_state:
                    logger.error(f"Recovered state missing essential key: {key}")
                    return False
            
            # Check data types
            if not isinstance(recovered_state.get("workflow_start_time"), (int, float)):
                logger.error("workflow_start_time is not a number in recovered state")
                return False
            
            logger.info("Recovered state verification passed")
            return True
            
        except Exception as e:
            logger.error(f"Error during state verification: {e}")
            return False