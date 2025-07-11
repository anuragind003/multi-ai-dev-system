"""
Microservice-Style Pipeline - Independent Work Item Processing
Each work item is processed as an independent workflow execution.
"""

from typing import Dict, Any, List
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
    
    # Decision functions
    async_decide_on_code_quality,
    async_decide_on_test_results,
    async_decide_on_integration_test_results,
    
    # Human approval
    async_make_human_feedback_node,
    async_decide_after_human,
)

async def work_item_processor_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """
    🔄 WORK ITEM PROCESSOR: Processes work items in batch mode.
    
    This approach:
    1. Gets all work items that are ready to process
    2. Processes them one by one independently
    3. No state propagation issues between work items
    4. Clear progress tracking
    """
    logger.info(" WORK_ITEM_PROCESSOR: Starting batch work item processing")
    
    plan_output = state.get(StateFields.IMPLEMENTATION_PLAN)
    if not plan_output:
        logger.warning("WORK_ITEM_PROCESSOR: No implementation plan found")
        return {StateFields.WORKFLOW_COMPLETE: True}
    
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
    
    # Get completed work items
    completed_work_items = state.get("completed_work_items", [])
    completed_ids = {item['id'] if isinstance(item, dict) else item.id for item in completed_work_items}
    
    # Find all ready work items (dependencies satisfied)
    ready_work_items = []
    for item in work_items:
        item_id = item['id'] if isinstance(item, dict) else item.id
        item_status = item.get('status', 'pending') if isinstance(item, dict) else getattr(item, 'status', 'pending')
        dependencies = item.get('dependencies', []) if isinstance(item, dict) else getattr(item, 'dependencies', [])
        
        if item_id not in completed_ids and item_status == 'pending':
            if all(dep in completed_ids for dep in dependencies):
                ready_work_items.append(item)
    
    logger.info(f"WORK_ITEM_PROCESSOR: {len(ready_work_items)} work items ready for processing")
    
    if not ready_work_items:
        if len(completed_ids) == len(work_items):
            logger.info("WORK_ITEM_PROCESSOR: All work items completed!")
            return {StateFields.WORKFLOW_COMPLETE: True}
        else:
            logger.warning("WORK_ITEM_PROCESSOR: No ready work items but some remain - dependency deadlock?")
            return {StateFields.WORKFLOW_COMPLETE: True, "error": "dependency_deadlock"}
    
    # Process work items in parallel batches or sequentially
    work_item_results = []
    updated_completed_items = list(completed_work_items)
    
    for work_item in ready_work_items:
        work_item_id = work_item['id'] if isinstance(work_item, dict) else work_item.id
        logger.info(f"WORK_ITEM_PROCESSOR: Processing work item {work_item_id}")
        
        # Create isolated state for this work item
        work_item_state = state.copy()
        work_item_dict = work_item if isinstance(work_item, dict) else work_item.model_dump()
        work_item_state["current_work_item"] = work_item_dict
        
        # Process through the generation pipeline
        try:
            # Generate code
            gen_result = await async_code_generation_dispatcher_node(work_item_state, config)
            work_item_state.update(gen_result)
            
            # Quality check
            quality_result = await async_code_quality_analysis_node(work_item_state, config)
            work_item_state.update(quality_result)
            
            # If quality approved, run tests
            quality_decision = await async_decide_on_code_quality(work_item_state)
            if quality_decision == "approve":
                test_result = await async_test_execution_node(work_item_state, config)
                work_item_state.update(test_result)
                
                # If tests pass, run integration
                test_decision = await async_decide_on_test_results(work_item_state)
                if test_decision == "approve":
                    integration_result = await async_integration_node(work_item_state, config)
                    work_item_state.update(integration_result)
            
            # Mark as completed
            completed_work_item = {**work_item_dict, "status": "completed"}
            updated_completed_items.append(completed_work_item)
            
            work_item_results.append({
                "work_item_id": work_item_id,
                "status": "completed",
                "generation_result": gen_result.get(StateFields.CODE_GENERATION_RESULT, {}),
                "quality_result": quality_result.get(StateFields.CODE_REVIEW_FEEDBACK, {}),
            })
            
            logger.info(f"WORK_ITEM_PROCESSOR:  Completed work item {work_item_id}")
            
        except Exception as e:
            logger.error(f"WORK_ITEM_PROCESSOR:  Failed work item {work_item_id}: {str(e)}")
            work_item_results.append({
                "work_item_id": work_item_id,
                "status": "failed",
                "error": str(e)
            })
    
    # Update state with results
    total_completed = len(updated_completed_items)
    total_work_items = len(work_items)
    
    logger.info(f"WORK_ITEM_PROCESSOR: Batch complete - {total_completed}/{total_work_items} work items finished")
    
    return {
        "completed_work_items": updated_completed_items,
        "work_item_batch_results": work_item_results,
        "batch_processed_count": len(ready_work_items),
        StateFields.WORKFLOW_COMPLETE: total_completed >= total_work_items,
        "_processor_action": "batch_completed" if total_completed >= total_work_items else "continue_processing"
    }

def work_item_processor_router(state: AgentState) -> str:
    """Router for work item processor"""
    action = state.get("_processor_action", "unknown")
    workflow_complete = state.get(StateFields.WORKFLOW_COMPLETE, False)
    
    logger.info(f"WORK_ITEM_PROCESSOR_ROUTER: action={action}, complete={workflow_complete}")
    
    if workflow_complete or action == "batch_completed":
        return "complete_workflow"
    else:
        return "continue_processing"

async def create_microservice_workflow() -> StateGraph:
    """
    🔄 MICROSERVICE: Independent work item processing workflow.
    
    Benefits:
    1. No state propagation between work items
    2. Parallel processing capability
    3. Isolation of failures
    4. Simple debugging
    5. Batch processing efficiency
    """
    workflow = StateGraph(AgentState)

    # === NODES ===
    workflow.add_node("initialize_state_node", async_initialize_workflow_state)
    
    # Planning phase (same as other workflows)
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
    
    # 🔄 KEY: Work item processor (replaces individual nodes)
    workflow.add_node("work_item_processor_node", work_item_processor_node)
    
    # Finalization
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
        "proceed": "work_item_processor_node",  # Go directly to processor!
        "revise": "planning_node",
        "end": END
    })

    # === MICROSERVICE PROCESSING ===
    
    # Processor handles all work items and loops until done
    workflow.add_conditional_edges("work_item_processor_node", work_item_processor_router, {
        "continue_processing": "work_item_processor_node",  # Loop back
        "complete_workflow": "finalize_node"
    })
    
    # End
    workflow.add_edge("finalize_node", END)

    return workflow 