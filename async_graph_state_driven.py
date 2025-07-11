"""
State-Driven Pipeline - Explicit State Management
Uses a dedicated state manager to handle work item transitions explicitly.
"""

from typing import Dict, Any
from langgraph.graph import StateGraph, END
from agent_state import AgentState, StateFields
import logging

logger = logging.getLogger(__name__)

# Import async nodes
from async_graph_nodes import (
    async_initialize_workflow_state,
    async_brd_analysis_node,
    async_tech_stack_recommendation_node,
    async_system_design_node,
    async_planning_node,
    async_code_generation_dispatcher_node,
    async_code_quality_analysis_node,
    async_test_execution_node,
    async_integration_node,
    async_finalize_workflow,
    async_phase_completion_node,
    async_increment_revision_count_node,
    
    # Decision functions
    async_decide_on_code_quality,
    async_decide_on_test_results,
    async_decide_on_integration_test_results,
    
    # Human approval
    async_make_human_feedback_node,
    async_decide_after_human,
)

async def state_manager_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """
    🎯 DEDICATED STATE MANAGER: Explicitly manages work item state transitions.
    
    This node is responsible for:
    1. Loading the next work item
    2. Ensuring state consistency
    3. Managing workflow completion
    4. Providing explicit debugging
    """
    logger.info("🎯 STATE_MANAGER: Starting explicit state management")
    
    # Get current workflow state
    plan_output = state.get(StateFields.IMPLEMENTATION_PLAN)
    if not plan_output:
        logger.warning("STATE_MANAGER: No implementation plan found - completing workflow")
        return {
            "current_work_item": None,
            StateFields.WORKFLOW_COMPLETE: True,
            "_state_manager_action": "workflow_complete_no_plan"
        }
    
    # Extract work items 
    work_items = []
    if hasattr(plan_output, 'plan') and hasattr(plan_output.plan, 'phases'):
        for phase in plan_output.plan.phases:
            if hasattr(phase, 'work_items'):
                work_items.extend(phase.work_items)
    elif isinstance(plan_output, dict) and 'plan' in plan_output:
        plan = plan_output['plan']
        if 'phases' in plan:
            for phase in plan['phases']:
                if 'work_items' in phase:
                    work_items.extend(phase['work_items'])
    
    logger.info(f"STATE_MANAGER: Found {len(work_items)} total work items")
    
    # Get completed work items
    completed_work_items = state.get("completed_work_items", [])
    completed_ids = {item['id'] if isinstance(item, dict) else item.id for item in completed_work_items}
    logger.info(f"STATE_MANAGER: {len(completed_ids)} work items completed: {completed_ids}")
    
    # Find next work item with dependencies satisfied
    next_work_item = None
    for item in work_items:
        item_id = item['id'] if isinstance(item, dict) else item.id
        item_status = item.get('status', 'pending') if isinstance(item, dict) else getattr(item, 'status', 'pending')
        dependencies = item.get('dependencies', []) if isinstance(item, dict) else getattr(item, 'dependencies', [])
        
        if item_id not in completed_ids and item_status == 'pending':
            if all(dep in completed_ids for dep in dependencies):
                next_work_item = item
                break
    
    if next_work_item:
        work_item_id = next_work_item['id'] if isinstance(next_work_item, dict) else next_work_item.id
        work_item_dict = next_work_item if isinstance(next_work_item, dict) else next_work_item.model_dump()
        
        logger.info(f"STATE_MANAGER: ✅ Next work item selected: {work_item_id}")
        
        return {
            "current_work_item": work_item_dict,
            StateFields.WORKFLOW_COMPLETE: False,
            "_state_manager_action": "work_item_selected",
            "_selected_work_item_id": work_item_id,
            "_state_manager_debug": {
                "total_work_items": len(work_items),
                "completed_count": len(completed_ids),
                "selected_work_item": work_item_id
            }
        }
    else:
        logger.info("STATE_MANAGER: ✅ All work items completed - finishing workflow")
        return {
            "current_work_item": None,
            StateFields.WORKFLOW_COMPLETE: True,
            "_state_manager_action": "workflow_complete_all_done",
            "_state_manager_debug": {
                "total_work_items": len(work_items),
                "completed_count": len(completed_ids),
                "all_completed": True
            }
        }

def state_manager_router(state: AgentState) -> str:
    """Router for state manager decisions"""
    action = state.get("_state_manager_action", "unknown")
    logger.info(f"STATE_MANAGER_ROUTER: Action = {action}")
    
    if action == "work_item_selected":
        return "proceed_to_generation"
    elif action in ["workflow_complete_no_plan", "workflow_complete_all_done"]:
        return "complete_workflow"
    else:
        logger.warning(f"STATE_MANAGER_ROUTER: Unknown action '{action}' - defaulting to complete")
        return "complete_workflow"

async def create_state_driven_workflow() -> StateGraph:
    """
    🎯 STATE-DRIVEN: Workflow with explicit state management.
    
    Benefits:
    1. Clear state transitions
    2. Explicit debugging
    3. No Command API complexity
    4. Deterministic behavior
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

    workflow.add_node("human_approval_brd_node", brd_feedback_node)
    workflow.add_node("human_approval_tech_stack_node", tech_stack_feedback_node)
    workflow.add_node("human_approval_system_design_node", system_design_feedback_node)
    workflow.add_node("human_approval_plan_node", planning_feedback_node)
    
    # 🎯 KEY: Dedicated state manager
    workflow.add_node("state_manager_node", state_manager_node)
    
    # Implementation nodes
    workflow.add_node("code_generation_node", async_code_generation_dispatcher_node)
    workflow.add_node("code_quality_node", async_code_quality_analysis_node)
    workflow.add_node("test_execution_node", async_test_execution_node)
    workflow.add_node("integration_node", async_integration_node)
    workflow.add_node("phase_completion_node", async_phase_completion_node)
    workflow.add_node("increment_revision_node", async_increment_revision_count_node)
    workflow.add_node("finalize_node", async_finalize_workflow)

    # === EDGES ===
    workflow.set_entry_point("initialize_state_node")
    
    # Planning flow (same as before)
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
        "proceed": "state_manager_node",  # Go to state manager!
        "revise": "planning_node",
        "end": END
    })

    # === STATE-DRIVEN IMPLEMENTATION LOOP ===
    
    # State manager routes work
    workflow.add_conditional_edges("state_manager_node", state_manager_router, {
        "proceed_to_generation": "code_generation_node",
        "complete_workflow": "finalize_node"
    })
    
    # Standard generation flow
    workflow.add_edge("code_generation_node", "code_quality_node")
    workflow.add_conditional_edges("code_quality_node", async_decide_on_code_quality, {
        "approve": "test_execution_node",
        "revise": "increment_revision_node"
    })
    
    workflow.add_conditional_edges("test_execution_node", async_decide_on_test_results, {
        "approve": "integration_node",
        "revise": "increment_revision_node"
    })
    
    workflow.add_conditional_edges("integration_node", async_decide_on_integration_test_results, {
        "proceed": "phase_completion_node",
        "proceed_with_warning": "phase_completion_node"
    })
    
    # After revision, go back to generation (not state manager)
    workflow.add_edge("increment_revision_node", "code_generation_node")
    
    # After completion, go back to state manager for next work item
    workflow.add_edge("phase_completion_node", "state_manager_node")
    
    # End
    workflow.add_edge("finalize_node", END)

    return workflow 