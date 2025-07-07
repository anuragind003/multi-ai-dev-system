"""
Enhanced Graph Nodes with Recovery Integration
Implements disk-based backup, session timeout extension, state serialization, and recovery
"""

import logging
from typing import Dict, Any, Optional
from graph_nodes import *  # Import all existing nodes
from enhanced_memory_manager_with_recovery import create_enhanced_memory_with_recovery, EnhancedMemoryManagerWithRecovery  # Add this import

logger = logging.getLogger(__name__)

def enhanced_brd_analysis_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """Enhanced BRD analysis with checkpoint creation and recovery"""
    logger.info("Executing enhanced BRD analysis node with recovery")
    
    # Get session info
    session_id = config.get("configurable", {}).get("thread_id", "default_session")
    
    # Get or create enhanced memory manager
    memory = config.get("configurable", {}).get("memory")
    if hasattr(memory, 'start_human_approval'):
        enhanced_memory = memory
    else:
        enhanced_memory = create_enhanced_memory_with_recovery()
        config["configurable"]["memory"] = enhanced_memory
        logger.info("Created enhanced memory manager with recovery")
    
    try:
        # Run standard BRD analysis
        result = brd_analysis_node(state, config)
        
        # Create checkpoint before human approval
        updated_state = {**state, **result}
        checkpoint_id = enhanced_memory.start_human_approval(
            session_id=session_id,
            approval_type="brd_analysis",
            current_state=updated_state
        )
        
        result["checkpoint_id"] = checkpoint_id
        result["recovery_session_id"] = session_id
        
        logger.info(f"BRD analysis completed with checkpoint: {checkpoint_id}")
        return result
        
    except Exception as e:
        logger.error(f"Enhanced BRD analysis failed: {e}")
        # Try to recover from last checkpoint
        checkpoints = enhanced_memory.list_session_checkpoints(session_id)
        if checkpoints:
            logger.info(f"Found {len(checkpoints)} checkpoints for recovery")
        raise

def enhanced_tech_stack_recommendation_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """Enhanced tech stack recommendation with checkpoint creation"""
    logger.info("Executing enhanced tech stack recommendation node")
    
    session_id = config.get("configurable", {}).get("thread_id", "default_session")
    memory = config.get("configurable", {}).get("memory")
    
    try:
        # Run standard tech stack recommendation
        result = tech_stack_recommendation_node(state, config)
        
        # Create checkpoint if we have enhanced memory
        if hasattr(memory, 'start_human_approval'):
            updated_state = {**state, **result}
            checkpoint_id = memory.start_human_approval(
                session_id=session_id,
                approval_type="tech_stack",
                current_state=updated_state
            )
            result["checkpoint_id"] = checkpoint_id
            logger.info(f"Tech stack analysis checkpoint created: {checkpoint_id}")
        
        return result
        
    except Exception as e:
        logger.error(f"Enhanced tech stack recommendation failed: {e}")
        raise

def enhanced_system_design_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """Enhanced system design with checkpoint creation"""
    logger.info("Executing enhanced system design node")
    
    session_id = config.get("configurable", {}).get("thread_id", "default_session")
    memory = config.get("configurable", {}).get("memory")
    
    try:
        # Run standard system design
        result = system_design_node(state, config)
        
        # Create checkpoint if we have enhanced memory
        if hasattr(memory, 'start_human_approval'):
            updated_state = {**state, **result}
            checkpoint_id = memory.start_human_approval(
                session_id=session_id,
                approval_type="system_design",
                current_state=updated_state
            )
            result["checkpoint_id"] = checkpoint_id
            logger.info(f"System design checkpoint created: {checkpoint_id}")
        
        return result
        
    except Exception as e:
        logger.error(f"Enhanced system design failed: {e}")
        raise

def enhanced_plan_generation_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """Enhanced plan generation with checkpoint creation"""
    logger.info("Executing enhanced plan generation node")
    
    session_id = config.get("configurable", {}).get("thread_id", "default_session")
    memory = config.get("configurable", {}).get("memory")
    
    try:
        # Run standard plan generation
        result = plan_generation_node(state, config)
        
        # Create checkpoint if we have enhanced memory
        if hasattr(memory, 'start_human_approval'):
            updated_state = {**state, **result}
            checkpoint_id = memory.start_human_approval(
                session_id=session_id,
                approval_type="plan_compilation",
                current_state=updated_state
            )
            result["checkpoint_id"] = checkpoint_id
            logger.info(f"Plan generation checkpoint created: {checkpoint_id}")
        
        return result
        
    except Exception as e:
        logger.error(f"Enhanced plan generation failed: {e}")
        raise

def enhanced_human_approval_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """Enhanced human approval node with session timeout extension"""
    logger.info("Enhanced human approval node with extended session timeout")
    
    session_id = config.get("configurable", {}).get("thread_id", "default_session")
    memory = config.get("configurable", {}).get("memory")
    
    # Extend session timeout for human approval (4 extra hours)
    if hasattr(memory, 'extend_session_timeout'):
        try:
            memory.extend_session_timeout(session_id, additional_hours=4.0)
            logger.info(f"Extended session timeout by 4 hours for session: {session_id}")
        except Exception as e:
            logger.error(f"Failed to extend session timeout: {e}")
    
    # CRITICAL FIX: Don't use the broken placeholder node
    # Instead, return empty dict - the interrupt should happen via graph interrupts
    logger.warning("Enhanced approval node reached - interrupt should happen via graph configuration")
    return {}

def enhanced_human_approval_brd_node(state: AgentState) -> Dict[str, Any]:
    """Enhanced BRD human approval with timeout extension"""
    return enhanced_human_approval_node(state, {"configurable": {"thread_id": "brd_approval"}})

def enhanced_human_approval_tech_node(state: AgentState) -> Dict[str, Any]:
    """Enhanced tech stack human approval with timeout extension"""
    return enhanced_human_approval_node(state, {"configurable": {"thread_id": "tech_approval"}})

def enhanced_human_approval_design_node(state: AgentState) -> Dict[str, Any]:
    """Enhanced system design human approval with timeout extension"""
    return enhanced_human_approval_node(state, {"configurable": {"thread_id": "design_approval"}})

def enhanced_human_approval_plan_node(state: AgentState) -> Dict[str, Any]:
    """Enhanced plan compilation human approval with timeout extension"""
    return enhanced_human_approval_node(state, {"configurable": {"thread_id": "plan_approval"}})

def enhanced_decide_after_approval(state: AgentState, config: dict) -> str:
    """Enhanced decision function with recovery support"""
    session_id = config.get("configurable", {}).get("thread_id", "default_session")
    memory = config.get("configurable", {}).get("memory")
    
    # Get decision from multiple possible locations for compatibility
    decision = (
        state.get("human_decision") or 
        state.get("decision") or 
        state.get("human_feedback", {}).get("decision", "reject")
    )
    
    if isinstance(decision, str):
        decision = decision.lower()
    
    logger.info(f"Enhanced approval decision for {session_id}: {decision}")
    
    # End human approval if proceeding
    if decision in ["approve", "proceed", "continue"] and hasattr(memory, 'end_human_approval'):
        try:
            memory.end_human_approval(session_id, state)
            logger.info(f"Ended human approval for session: {session_id}")
        except Exception as e:
            logger.error(f"Failed to end human approval: {e}")
    
    # Handle all decision types properly
    if decision in ["approve", "proceed", "continue"]:
        return "proceed"
    elif decision in ["revise", "reject", "request_revision"]:
        return "revise"
    elif decision in ["end", "terminate", "stop"]:
        return "terminate"
    else:
        logger.warning(f"Unknown decision '{decision}', defaulting to revise")
        return "revise"

# Decision functions for each approval type
def enhanced_decide_after_brd_approval(state: AgentState) -> str:
    """Enhanced BRD approval decision with recovery"""
    config = {"configurable": {"thread_id": "brd_approval"}}
    return enhanced_decide_after_approval(state, config)

def enhanced_decide_after_tech_approval(state: AgentState) -> str:
    """Enhanced tech stack approval decision with recovery"""
    config = {"configurable": {"thread_id": "tech_approval"}}
    return enhanced_decide_after_approval(state, config)

def enhanced_decide_after_design_approval(state: AgentState) -> str:
    """Enhanced system design approval decision with recovery"""
    config = {"configurable": {"thread_id": "design_approval"}}
    return enhanced_decide_after_approval(state, config)

def enhanced_decide_after_plan_approval(state: AgentState) -> str:
    """Enhanced plan compilation approval decision with recovery"""
    config = {"configurable": {"thread_id": "plan_approval"}}
    return enhanced_decide_after_approval(state, config)

def recover_workflow_from_checkpoint(checkpoint_id: str, enhanced_memory: EnhancedMemoryManagerWithRecovery) -> Optional[Dict[str, Any]]:
    """Recover a workflow from a specific checkpoint"""
    try:
        recovery_data = enhanced_memory.recover_from_checkpoint(checkpoint_id)
        if recovery_data:
            logger.info(f"Successfully recovered workflow from checkpoint: {checkpoint_id}")
            return recovery_data
        else:
            logger.error(f"Failed to recover from checkpoint: {checkpoint_id}")
            return None
    except Exception as e:
        logger.error(f"Recovery failed for checkpoint {checkpoint_id}: {e}")
        return None

def list_available_checkpoints(session_id: str, enhanced_memory: EnhancedMemoryManagerWithRecovery) -> List[Dict[str, Any]]:
    """List all available checkpoints for a session"""
    try:
        checkpoints = enhanced_memory.list_session_checkpoints(session_id)
        logger.info(f"Found {len(checkpoints)} checkpoints for session {session_id}")
        return checkpoints
    except Exception as e:
        logger.error(f"Failed to list checkpoints for session {session_id}: {e}")
        return []

def get_session_recovery_info(session_id: str, enhanced_memory: EnhancedMemoryManagerWithRecovery) -> Dict[str, Any]:
    """Get comprehensive recovery information for a session"""
    try:
        checkpoints = enhanced_memory.list_session_checkpoints(session_id)
        stats = enhanced_memory.get_memory_stats()
        
        return {
            "session_id": session_id,
            "available_checkpoints": len(checkpoints),
            "checkpoints": checkpoints,
            "memory_stats": stats,
            "can_recover": len(checkpoints) > 0
        }
    except Exception as e:
        logger.error(f"Failed to get recovery info for session {session_id}: {e}")
        return {"session_id": session_id, "can_recover": False, "error": str(e)}