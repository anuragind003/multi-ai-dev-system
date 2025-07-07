"""
Recovery API endpoints for enhanced memory manager
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import logging

from enhanced_memory_manager_with_recovery import EnhancedMemoryManagerWithRecovery, create_enhanced_memory_with_recovery
from enhanced_graph_nodes_with_recovery import recover_workflow_from_checkpoint, list_available_checkpoints, get_session_recovery_info

logger = logging.getLogger(__name__)

# Global enhanced memory manager
_enhanced_memory: Optional[EnhancedMemoryManagerWithRecovery] = None

def get_enhanced_memory() -> EnhancedMemoryManagerWithRecovery:
    """Get or create enhanced memory manager"""
    global _enhanced_memory
    if _enhanced_memory is None:
        _enhanced_memory = create_enhanced_memory_with_recovery()
    return _enhanced_memory

# Request/Response models
class RecoveryRequest(BaseModel):
    checkpoint_id: str

class SessionTimeoutRequest(BaseModel):
    session_id: str
    additional_hours: float

class MemoryStatsResponse(BaseModel):
    cache_size: int
    database_entries: int
    active_sessions: int
    total_checkpoints: int
    cached_sessions: int
    background_tasks: int

class CheckpointInfo(BaseModel):
    checkpoint_id: str
    step_name: str
    created_at: str
    checkpoint_type: str

class SessionRecoveryInfo(BaseModel):
    session_id: str
    available_checkpoints: int
    checkpoints: List[CheckpointInfo]
    memory_stats: Dict[str, Any]
    can_recover: bool
    error: Optional[str] = None

# Create router
recovery_router = APIRouter(prefix="/api/recovery", tags=["recovery"])

@recovery_router.get("/stats", response_model=MemoryStatsResponse)
async def get_memory_stats():
    """Get enhanced memory manager statistics"""
    try:
        enhanced_memory = get_enhanced_memory()
        stats = enhanced_memory.get_memory_stats()
        return MemoryStatsResponse(**stats)
    except Exception as e:
        logger.error(f"Failed to get memory stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@recovery_router.get("/sessions/{session_id}/checkpoints")
async def list_session_checkpoints(session_id: str) -> List[CheckpointInfo]:
    """List all checkpoints for a session"""
    try:
        enhanced_memory = get_enhanced_memory()
        checkpoints = list_available_checkpoints(session_id, enhanced_memory)
        return [CheckpointInfo(**cp) for cp in checkpoints]
    except Exception as e:
        logger.error(f"Failed to list checkpoints for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@recovery_router.get("/sessions/{session_id}/recovery-info", response_model=SessionRecoveryInfo)
async def get_session_recovery_information(session_id: str):
    """Get comprehensive recovery information for a session"""
    try:
        enhanced_memory = get_enhanced_memory()
        recovery_info = get_session_recovery_info(session_id, enhanced_memory)
        
        # Convert checkpoints to proper format
        checkpoints = [CheckpointInfo(**cp) for cp in recovery_info.get("checkpoints", [])]
        
        return SessionRecoveryInfo(
            session_id=recovery_info["session_id"],
            available_checkpoints=recovery_info.get("available_checkpoints", 0),
            checkpoints=checkpoints,
            memory_stats=recovery_info.get("memory_stats", {}),
            can_recover=recovery_info.get("can_recover", False),
            error=recovery_info.get("error")
        )
    except Exception as e:
        logger.error(f"Failed to get recovery info for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@recovery_router.post("/recover")
async def recover_from_checkpoint(request: RecoveryRequest) -> Dict[str, Any]:
    """Recover workflow state from a specific checkpoint"""
    try:
        enhanced_memory = get_enhanced_memory()
        recovery_data = recover_workflow_from_checkpoint(request.checkpoint_id, enhanced_memory)
        
        if recovery_data:
            return {
                "success": True,
                "checkpoint_id": request.checkpoint_id,
                "recovery_data": recovery_data,
                "message": f"Successfully recovered from checkpoint {request.checkpoint_id}"
            }
        else:
            raise HTTPException(
                status_code=404, 
                detail=f"Checkpoint {request.checkpoint_id} not found or recovery failed"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to recover from checkpoint {request.checkpoint_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@recovery_router.post("/sessions/{session_id}/extend-timeout")
async def extend_session_timeout(session_id: str, request: SessionTimeoutRequest):
    """Extend session timeout for long human approval periods"""
    try:
        enhanced_memory = get_enhanced_memory()
        enhanced_memory.extend_session_timeout(session_id, request.additional_hours)
        
        return {
            "success": True,
            "session_id": session_id,
            "additional_hours": request.additional_hours,
            "message": f"Extended session timeout by {request.additional_hours} hours"
        }
    except Exception as e:
        logger.error(f"Failed to extend session timeout for {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@recovery_router.delete("/sessions/{session_id}/checkpoints/{checkpoint_id}")
async def delete_checkpoint(session_id: str, checkpoint_id: str):
    """Delete a specific checkpoint"""
    try:
        enhanced_memory = get_enhanced_memory()
        # Note: Would need to add delete_checkpoint method to enhanced_memory
        # For now, return not implemented
        raise HTTPException(status_code=501, detail="Checkpoint deletion not yet implemented")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete checkpoint {checkpoint_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@recovery_router.post("/backup")
async def create_manual_backup():
    """Create a manual backup of the memory system"""
    try:
        enhanced_memory = get_enhanced_memory()
        enhanced_memory._create_disk_backup()
        
        return {
            "success": True,
            "message": "Manual backup created successfully"
        }
    except Exception as e:
        logger.error(f"Failed to create manual backup: {e}")
        raise HTTPException(status_code=500, detail=str(e))