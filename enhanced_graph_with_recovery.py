"""
Enhanced Graph with Recovery Integration
Uses enhanced nodes with disk-based persistence and recovery mechanisms
"""

from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.runnables import RunnableLambda

from agent_state import AgentState, StateFields
from enhanced_memory_manager_with_recovery import create_enhanced_memory_with_recovery, get_enhanced_memory_manager
from async_graph import create_async_phased_workflow
import logging

logger = logging.getLogger(__name__)

# Recovery utilities
def create_recovery_enabled_config(session_id: str, enhanced_memory) -> Dict[str, Any]:
    """Create configuration with enhanced memory for recovery"""
    return {
        "configurable": {
            "thread_id": session_id,
            "memory": enhanced_memory,
            "checkpoint_ns": session_id,
            "recovery_enabled": True
        }
    }

async def initialize_workflow_with_recovery(session_id: str) -> dict:
    """
    Initializes the phased development workflow with recovery capabilities
    using the pre-configured asynchronous graph.
    """
    memory_manager = get_enhanced_memory_manager()
    
    # Create the async workflow
    compiled_graph = await create_async_phased_workflow()
    
    # Compile with the enhanced memory manager
    final_graph = compiled_graph.compile(
        checkpointer=memory_manager,
        interrupt_before=[
            "human_approval_brd_node",  # CRITICAL FIX: Add BRD approval to interrupt list
            "human_approval_tech_stack_node", 
            "human_approval_system_design_node",
            "human_approval_plan_node"
        ]
    )
    
    # Create recovery-enabled configuration
    config = {
        "configurable": {
            "thread_id": session_id,
            "memory": memory_manager,
            "checkpoint_ns": session_id,
            "recovery_enabled": True
        }
    }

    logger.info(f"Initialized ASYNC workflow with recovery for session: {session_id}")
    
    return {
        "graph": final_graph, 
        "enhanced_memory": memory_manager,
        "config": config
    }