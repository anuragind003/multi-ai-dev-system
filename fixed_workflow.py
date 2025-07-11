"""
SIMPLIFIED WORKFLOW - ONE CONSISTENT APPROACH
This file creates a single, working workflow that fixes the state propagation issue.
"""

import time
import logging
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableLambda

from agent_state import AgentState, StateFields

# Import ALL nodes as sync versions to avoid confusion
from graph_nodes import (
    initialize_workflow_state,
    brd_analysis_node,
    tech_stack_recommendation_node,
    system_design_node,
    planning_node,
    work_item_iterator_node,  # SYNC version - this is key!
    route_after_work_item_iterator,  # SYNC router - this is key!
    code_generation_dispatcher_node,
    code_quality_analysis_node,
    test_execution_node,
    integration_node,
    phase_completion_node,
    increment_revision_count_node,
    finalize_workflow,
    
    # Decision functions
    decide_on_code_quality,
    decide_on_test_results,
    decide_on_integration_test_results,
    check_circuit_breaker,
    
    # Human approval
    make_human_feedback_node,
    decide_after_human,
    mark_stage_complete_node,
)

logger = logging.getLogger(__name__)

async def create_fixed_workflow() -> StateGraph:
    """
    SIMPLIFIED WORKFLOW: All sync nodes, consistent state propagation.
    This eliminates the async/sync mixing that was causing state issues.
    """
    logger.info("Creating FIXED workflow with all sync nodes for consistent state propagation")
    
    workflow = StateGraph(AgentState)

    # Add state initialization
    workflow.add_node("initialize_state_node", initialize_workflow_state)

    # --- Agent Nodes (ALL SYNC) ---
    workflow.add_node("brd_analysis_node", brd_analysis_node)
    workflow.add_node("tech_stack_recommendation_node", tech_stack_recommendation_node)
    workflow.add_node("system_design_node", system_design_node)
    workflow.add_node("planning_node", planning_node)
    
    # --- KEY FIX: Use sync work item iterator with sync router ---
    workflow.add_node("work_item_iterator_node", work_item_iterator_node)  # SYNC
    
    workflow.add_node("code_generation_node", code_generation_dispatcher_node)
    workflow.add_node("code_quality_node", code_quality_analysis_node)
    workflow.add_node("test_execution_node", test_execution_node)
    workflow.add_node("integration_node", integration_node)
    workflow.add_node("phase_completion_node", phase_completion_node)
    workflow.add_node("increment_revision_node", increment_revision_count_node)
    workflow.add_node("finalize_node", finalize_workflow)

    # --- Human Approval Nodes ---
    brd_feedback_node = make_human_feedback_node(StateFields.REQUIREMENTS_ANALYSIS, "BRD Analysis")
    tech_stack_feedback_node = make_human_feedback_node(StateFields.TECH_STACK_RECOMMENDATION, "Tech Stack Recommendation")
    system_design_feedback_node = make_human_feedback_node(StateFields.SYSTEM_DESIGN, "System Design")
    planning_feedback_node = make_human_feedback_node(StateFields.IMPLEMENTATION_PLAN, "Implementation Plan")

    workflow.add_node("human_approval_brd_node", RunnableLambda(brd_feedback_node))
    workflow.add_node("human_approval_tech_stack_node", RunnableLambda(tech_stack_feedback_node))
    workflow.add_node("human_approval_system_design_node", RunnableLambda(system_design_feedback_node))
    workflow.add_node("human_approval_plan_node", RunnableLambda(planning_feedback_node))

    # === EDGES ===
    workflow.set_entry_point("initialize_state_node")
    
    # Planning flow
    workflow.add_edge("initialize_state_node", "brd_analysis_node")
    workflow.add_edge("brd_analysis_node", "human_approval_brd_node")
    
    workflow.add_conditional_edges("human_approval_brd_node", decide_after_human, {
        "proceed": "tech_stack_recommendation_node",
        "revise": "brd_analysis_node",
        "end": END
    })
    
    workflow.add_edge("tech_stack_recommendation_node", "human_approval_tech_stack_node")
    workflow.add_conditional_edges("human_approval_tech_stack_node", decide_after_human, {
        "proceed": "system_design_node",
        "revise": "tech_stack_recommendation_node",
        "end": END
    })
    
    workflow.add_edge("system_design_node", "human_approval_system_design_node")
    workflow.add_conditional_edges("human_approval_system_design_node", decide_after_human, {
        "proceed": "planning_node",
        "revise": "system_design_node",
        "end": END
    })
    
    workflow.add_edge("planning_node", "human_approval_plan_node")
    workflow.add_conditional_edges("human_approval_plan_node", decide_after_human, {
        "proceed": "work_item_iterator_node",
        "revise": "planning_node",
        "end": END
    })

    # === IMPLEMENTATION LOOP (ALL SYNC) ===
    workflow.add_conditional_edges(
        "work_item_iterator_node",
        route_after_work_item_iterator,  # SYNC router with SYNC iterator
        {
            "proceed": "code_generation_node",
            "workflow_complete": "finalize_node"
        }
    )
    
    # Quality assurance flow
    workflow.add_edge("code_generation_node", "code_quality_node")
    workflow.add_conditional_edges("code_quality_node", decide_on_code_quality, {
        "approve": "test_execution_node",
        "revise": "increment_revision_node"
    })
    
    # Testing flow
    workflow.add_conditional_edges("test_execution_node", decide_on_test_results, {
        "approve": "integration_node",
        "revise": "increment_revision_node"
    })
    
    # Integration flow
    workflow.add_conditional_edges("integration_node", decide_on_integration_test_results, {
        "proceed": "phase_completion_node",
        "proceed_with_warning": "phase_completion_node"
    })
    
    # Revision handling with circuit breaker
    workflow.add_conditional_edges("increment_revision_node", check_circuit_breaker, {
        "continue": "code_generation_node",
        "stop": "finalize_node"
    })
    
    # Loop back to iterator after completion
    workflow.add_edge("phase_completion_node", "work_item_iterator_node")
    
    # End
    workflow.add_edge("finalize_node", END)

    logger.info("FIXED workflow created successfully with all sync nodes")
    return workflow

# Make this the default workflow
async def get_fixed_workflow() -> StateGraph:
    """Get the fixed workflow that solves the state propagation issue."""
    return await create_fixed_workflow()
