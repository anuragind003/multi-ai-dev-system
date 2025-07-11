"""
Simple Sequential Async Workflow - No Command API Issues
Uses reliable conditional edges instead of Command API for state management.
"""

from typing import Dict, Any
from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableLambda
from agent_state import AgentState, StateFields

# Import the working async nodes (without Command API)
from async_graph_nodes import (
    async_initialize_workflow_state,
    async_brd_analysis_node,
    async_tech_stack_recommendation_node,
    async_system_design_node,
    async_planning_node,
    async_work_item_iterator_node_command,  # Use the Command API version to fix state propagation
    async_work_item_iterator_node,  # Keep legacy version for compatibility
    async_code_generation_dispatcher_node,
    async_code_quality_analysis_node,
    async_test_execution_node,
    async_integration_node,
    async_finalize_workflow,
    async_phase_completion_node,
    async_increment_revision_count_node,
    async_check_circuit_breaker,
    
    # Decision functions
    async_decide_on_code_quality,
    async_decide_on_test_results,
    async_decide_on_integration_test_results,
    async_route_after_work_item_iterator_sync_wrapper, # Use the synchronous wrapper
    
    # Human approval
    async_make_human_feedback_node,
    async_decide_after_human,
    async_mark_stage_complete_node,
)

# Import the SYNC work item iterator to fix state propagation issues
from graph_nodes import work_item_iterator_node, route_after_work_item_iterator

async def create_simple_sequential_workflow() -> StateGraph:
    """
    🚀 SIMPLE & RELIABLE: Sequential workflow with no Command API complexity.
    
    This approach:
    1. Uses proven conditional edges instead of Command API
    2. Maintains clear state propagation 
    3. Eliminates timing issues
    4. Provides better debugging visibility
    """
    workflow = StateGraph(AgentState)

    # === NODES ===
    workflow.add_node("initialize_state_node", async_initialize_workflow_state)
    
    # Planning phase
    workflow.add_node("brd_analysis_node", async_brd_analysis_node)
    workflow.add_node("tech_stack_recommendation_node", async_tech_stack_recommendation_node)
    workflow.add_node("system_design_node", async_system_design_node)
    workflow.add_node("planning_node", async_planning_node)
    
    # Human approval nodes
    brd_feedback_node = async_make_human_feedback_node(StateFields.REQUIREMENTS_ANALYSIS, "BRD Analysis")
    tech_stack_feedback_node = async_make_human_feedback_node(StateFields.TECH_STACK_RECOMMENDATION, "Tech Stack Recommendation")
    system_design_feedback_node = async_make_human_feedback_node(StateFields.SYSTEM_DESIGN, "System Design")
    planning_feedback_node = async_make_human_feedback_node(StateFields.IMPLEMENTATION_PLAN, "Implementation Plan")

    workflow.add_node("human_approval_brd_node", RunnableLambda(brd_feedback_node))
    workflow.add_node("human_approval_tech_stack_node", RunnableLambda(tech_stack_feedback_node))
    workflow.add_node("human_approval_system_design_node", RunnableLambda(system_design_feedback_node))
    workflow.add_node("human_approval_plan_node", RunnableLambda(planning_feedback_node))
    
    # Implementation loop nodes
    workflow.add_node("work_item_iterator_node", work_item_iterator_node)  # SYNC VERSION - FIXES STATE PROPAGATION
    workflow.add_node("code_generation_node", async_code_generation_dispatcher_node)
    workflow.add_node("code_quality_node", async_code_quality_analysis_node)
    workflow.add_node("test_execution_node", async_test_execution_node)
    workflow.add_node("integration_node", async_integration_node)
    workflow.add_node("phase_completion_node", async_phase_completion_node)
    workflow.add_node("increment_revision_node", async_increment_revision_count_node)
    workflow.add_node("finalize_node", async_finalize_workflow)

    # === EDGES ===
    workflow.set_entry_point("initialize_state_node")
    
    # Planning flow
    workflow.add_edge("initialize_state_node", "brd_analysis_node")
    workflow.add_edge("brd_analysis_node", "human_approval_brd_node")
    
    workflow.add_conditional_edges("human_approval_brd_node", async_decide_after_human, {
        "proceed": "tech_stack_recommendation_node",
        "revise": "brd_analysis_node",
        "end": END
    })
    
    workflow.add_edge("tech_stack_recommendation_node", "human_approval_tech_stack_node")
    workflow.add_conditional_edges("human_approval_tech_stack_node", async_decide_after_human, {
        "proceed": "system_design_node",
        "revise": "tech_stack_recommendation_node",
        "end": END
    })
    
    workflow.add_edge("system_design_node", "human_approval_system_design_node")
    workflow.add_conditional_edges("human_approval_system_design_node", async_decide_after_human, {
        "proceed": "planning_node",
        "revise": "system_design_node",
        "end": END
    })
    
    workflow.add_edge("planning_node", "human_approval_plan_node")
    workflow.add_conditional_edges("human_approval_plan_node", async_decide_after_human, {
        "proceed": "work_item_iterator_node",
        "revise": "planning_node",
        "end": END
    })

    # === IMPLEMENTATION LOOP ===
    # Key: Use the SYNC routing function that matches the SYNC iterator
    workflow.add_conditional_edges(
        "work_item_iterator_node",
        route_after_work_item_iterator, # Use the SYNC router with SYNC iterator
        {
            "proceed": "code_generation_node",
            "workflow_complete": "finalize_node"
        }
    )
    
    # Quality assurance flow
    workflow.add_edge("code_generation_node", "code_quality_node")
    workflow.add_conditional_edges("code_quality_node", async_decide_on_code_quality, {
        "approve": "test_execution_node",
        "revise": "increment_revision_node"
    })
    
    # Testing flow
    workflow.add_conditional_edges("test_execution_node", async_decide_on_test_results, {
        "approve": "integration_node",
        "revise": "increment_revision_node"
    })
    
    # Integration flow
    workflow.add_conditional_edges("integration_node", async_decide_on_integration_test_results, {
        "proceed": "phase_completion_node",
        "proceed_with_warning": "phase_completion_node"
    })
    
    # Revision handling with circuit breaker
    workflow.add_conditional_edges("increment_revision_node", async_check_circuit_breaker, {
        "continue": "code_generation_node",
        "stop": "finalize_node"
    })
    
    # Loop back to iterator after completion
    workflow.add_edge("phase_completion_node", "work_item_iterator_node")
    
    # End
    workflow.add_edge("finalize_node", END)

    return workflow 