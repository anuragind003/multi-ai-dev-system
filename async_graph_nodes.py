"""
Async-compatible versions of LangGraph Node Functions.
Compatible with LangGraph dev and async contexts.
"""

import asyncio
import re
import time
from typing import Dict, Any, Callable, List, Optional, Literal
from contextlib import asynccontextmanager
import os
import uuid
import logging
from agent_state import AgentState, StateFields
import monitoring

# Import refactored node functions
from graph_nodes import (
    # Core planning nodes
    brd_analysis_node,
    tech_stack_recommendation_node,
    system_design_node,
    planning_node,
    
    # Phase control nodes
    work_item_iterator_node,
    phase_completion_node,
    increment_revision_count_node,
    
    # Core implementation nodes
    code_generation_dispatcher_node,
    code_quality_analysis_node,
    test_execution_node,
    integration_node,
    
    # Testing and finalization
    finalize_workflow,
    
    # Edge decision functions
    has_next_phase,
    route_after_work_item_iterator,  # NEW: Import the new routing function
    
    # Add all legacy decision functions to be wrapped
    decide_on_architecture_quality,
    decide_on_database_quality,
    decide_on_backend_quality,
    decide_on_frontend_quality,
    decide_on_integration_quality,
    decide_on_code_quality,
    decide_on_test_results,
    decide_on_integration_test_results,
    
    # Human Approval nodes and decisions
    # human_approval_brd_node, # Removed
    should_request_brd_approval
)

# New: Import interrupt for human-in-the-loop and Command API
from langgraph.types import interrupt, Command
from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableLambda  # Add this import

logger = logging.getLogger(__name__)

@asynccontextmanager
async def async_trace_span(name: str, metadata=None):
    """Async implementation of trace_span for performance monitoring."""
    start_time = time.time()
    span_id = f"span_{int(start_time * 1000)}"
    
    try:
        # Log the start of the operation
        monitoring.log_agent_activity(
            agent_name="Async Workflow", 
            message=f"Starting operation: {name}", 
            level="INFO",
            metadata={
                "span_id": span_id,
                "operation": name,
                **(metadata or {})
            }
        )
        
        # Execute the operation
        yield
        
    except Exception as e:
        # Log error with comprehensive details
        monitoring.log_agent_activity(
            agent_name="Async Workflow",
            message=f"Error in operation {name}: {str(e)}",
            level="ERROR",
            metadata={
                "span_id": span_id,
                "operation": name,
                "execution_time": time.time() - start_time,
                "error": str(e),
                **(metadata or {})
            }
        )
        # Re-raise the exception for proper handling
        raise
        
    finally:
        # Always log completion with performance metrics
        monitoring.log_agent_activity(
            agent_name="Async Workflow",
            message=f"Completed operation: {name}",
            level="INFO",
            metadata={
                "span_id": span_id,
                "operation": name,
                "execution_time": time.time() - start_time,
                **(metadata or {})
            }
        )

def make_async_node(sync_node_func: Callable) -> Callable:
    """
    Convert a node function to async-compatible, handling both sync and async functions,
    with standardized error handling and execution time tracking.
    """
    async def async_node_func(state: AgentState, config: dict) -> Dict[str, Any]:
        func_name = str(sync_node_func.__name__)
        start_time = time.time()
        
        try:
            async with async_trace_span(func_name):
                if asyncio.iscoroutinefunction(sync_node_func):
                    # If the function is already a coroutine, await it directly
                    result = await sync_node_func(state, config)
                else:
                    # Otherwise, run the synchronous function in a separate thread
                    result = await asyncio.to_thread(sync_node_func, state, config)
            
            if isinstance(result, dict):
                if "execution_time" not in result:
                    result["execution_time"] = time.time() - start_time
                    
                logger.info(f"Async node {func_name} completed in {result['execution_time']:.2f}s")
                return result
            else:
                logger.warning(f"Async node {func_name} returned non-dict value: {type(result)}")
                # Return a dictionary with an error to maintain consistency
                return {"error": f"Invalid return type from {func_name}", "original_return_type": str(type(result))}
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Error in async node {func_name}: {str(e)}", exc_info=True)
            
            error_info = {
                "module": "Async Node",
                "function": func_name,
                "error": str(e),
                "error_code": f"ASYNC_{func_name.upper()}_ERROR",
                "timestamp": time.time()
            }
            
            return {
                "error": str(e),
                "execution_time": execution_time,
                "errors": [error_info]
            }
            
    return async_node_func

# Create async versions of refactored node functions
async_brd_analysis_node = make_async_node(brd_analysis_node)
async_tech_stack_recommendation_node = make_async_node(tech_stack_recommendation_node)
async_system_design_node = make_async_node(system_design_node)
async_planning_node = make_async_node(planning_node)
# Create a bulletproof async version with emergency fallback support
async def async_code_generation_dispatcher_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """🚀 BULLETPROOF: Code generation dispatcher with emergency state recovery."""
    logger.info("🚀 BULLETPROOF DISPATCHER: Starting with state recovery checks")
    
    # STEP 1: Check primary state location
    current_work_item = state.get("current_work_item")
    logger.info(f"DISPATCHER_DEBUG: Primary state - current_work_item present: {current_work_item is not None}")
    
    # STEP 2: Emergency fallback - check config for persisted state
    emergency_work_item = None
    if config.get("configurable", {}).get("_emergency_current_work_item") is not None:
        emergency_work_item = config["configurable"]["_emergency_current_work_item"]
        logger.info(f"DISPATCHER_DEBUG: Found emergency fallback work item: {emergency_work_item.get('id') if isinstance(emergency_work_item, dict) else emergency_work_item}")
    
    # STEP 3: Determine which work item to use
    if current_work_item is not None:
        logger.info("DISPATCHER_DEBUG: Using work item from primary state")
        work_item_to_use = current_work_item
    elif emergency_work_item is not None:
        logger.warning("DISPATCHER_RECOVERY: Primary state failed! Using emergency fallback")
        # Inject the emergency work item back into state
        state["current_work_item"] = emergency_work_item
        work_item_to_use = emergency_work_item
    else:
        # STEP 4: Complete failure - no work item found anywhere
        logger.error("DISPATCHER_FAILURE: No current_work_item found in primary state OR emergency fallback")
        logger.error(f"DISPATCHER_FAILURE: State keys: {list(state.keys())}")
        logger.error(f"DISPATCHER_FAILURE: Config keys: {list(config.get('configurable', {}).keys())}")
        return {
            StateFields.CODE_GENERATION_RESULT: {
                "status": "error", 
                "error_message": "Complete state propagation failure: no current_work_item in primary state or emergency fallback",
                "debug_info": {
                    "state_keys": list(state.keys()),
                    "config_keys": list(config.get('configurable', {}).keys()),
                    "emergency_fallback_attempted": True
                }
            }
        }
    
    # STEP 5: Success - we have a work item to process
    work_item_id = work_item_to_use.get('id') if isinstance(work_item_to_use, dict) else getattr(work_item_to_use, 'id', 'UNKNOWN')
    logger.info(f"DISPATCHER_SUCCESS: Processing work item: {work_item_id}")
    
    # Call the sync function directly in a thread
    try:
        result = await asyncio.to_thread(code_generation_dispatcher_node, state, config)
        logger.info(f"DISPATCHER_SUCCESS: Code generation completed for work item: {work_item_id}")
        return result
    except Exception as e:
        logger.error(f"DISPATCHER_ERROR: Code generation failed for work item {work_item_id}: {str(e)}", exc_info=True)
        return {
            StateFields.CODE_GENERATION_RESULT: {
                "status": "error", 
                "error_message": str(e),
                "work_item_id": work_item_id
            }
        }
async_code_quality_analysis_node = make_async_node(code_quality_analysis_node)
async_phase_completion_node = make_async_node(phase_completion_node)
async_testing_module_node = make_async_node(test_execution_node)
async_finalize_workflow = make_async_node(finalize_workflow)
async_test_execution_node = make_async_node(test_execution_node)

# Implement increment_revision_count node for async use
async_increment_revision_count_node = make_async_node(increment_revision_count_node)

# New Integration Node Wrapper
async_integration_node = make_async_node(integration_node)

# --- ADVANCED: Command API Work Item Iterator ---

def async_work_item_iterator_node_command(state: AgentState, config: dict) -> Command[Literal["code_generation_node", "finalize_node"]]:
    """
    🚀 BULLETPROOF: Work item iterator using LangGraph Command API with forced state persistence.
    
    This implementation uses multiple strategies to ensure current_work_item propagates correctly:
    1. Direct state mutation (immediate)
    2. Command update parameter (LangGraph standard)
    3. Global state persistence via config (fallback)
    """
    logger.info("🚀 COMMAND API: Executing bulletproof work item iterator")
    
    # Debug: Log current state for debugging
    logger.info(f"COMMAND_DEBUG: Current state keys: {list(state.keys())}")
    logger.info(f"COMMAND_DEBUG: current_work_item in state: {'current_work_item' in state}")
    logger.info(f"COMMAND_DEBUG: workflow_complete: {state.get(StateFields.WORKFLOW_COMPLETE, 'NOT_SET')}")
    
    plan_output = state.get(StateFields.IMPLEMENTATION_PLAN)
    if not plan_output:
        logger.warning("COMMAND_ITERATOR: Implementation plan is missing from the state.")
        # Update state using all strategies
        state["current_work_item"] = None
        state[StateFields.WORKFLOW_COMPLETE] = True
        
        # Also persist in config for emergency fallback
        if "configurable" not in config:
            config["configurable"] = {}
        config["configurable"]["_emergency_current_work_item"] = None
        config["configurable"]["_emergency_workflow_complete"] = True
        
        return Command(
            goto="finalize_node",
            update={
                "current_work_item": None,
                StateFields.WORKFLOW_COMPLETE: True,
                "_iterator_decision": "workflow_complete",
                "_iterator_reason": "No implementation plan found"
            }
        )

    work_items = []
    # Handle both Pydantic model and dict for flexibility
    if hasattr(plan_output, 'plan') and hasattr(plan_output.plan, 'phases'):
        # Pydantic ComprehensiveImplementationPlanOutput
        for phase in plan_output.plan.phases:
            if hasattr(phase, 'work_items'):
                work_items.extend(phase.work_items)
            elif isinstance(phase, dict) and 'work_items' in phase:
                work_items.extend(phase['work_items'])
    elif isinstance(plan_output, dict) and 'plan' in plan_output and 'phases' in plan_output['plan']:
         # Dictionary representation
        for phase in plan_output['plan']['phases']:
            if isinstance(phase, dict) and 'work_items' in phase:
                work_items.extend(phase['work_items'])
            else:
                logger.warning(f"COMMAND_ITERATOR: Unknown phase format: {type(phase)}")
    else:
        logger.warning(f"COMMAND_ITERATOR: Unknown plan format: {type(plan_output)}")

    logger.info(f"COMMAND_ITERATOR: Found {len(work_items)} work items total")
    
    # Get the list of completed work items (now with proper default)
    completed_ids = state.get(StateFields.COMPLETED_WORK_ITEMS, set())
    if not isinstance(completed_ids, set):
        completed_ids = set(completed_ids) if completed_ids else set()
    
    logger.info(f"COMMAND_ITERATOR: Found {len(completed_ids)} completed work items: {completed_ids}")
    
    # Find the next available work item
    next_work_item = None
    for item in work_items:
        item_id = item.get('id') if isinstance(item, dict) else item.id
        item_status = item.get('status', 'pending') if isinstance(item, dict) else getattr(item, 'status', 'pending')
        
        if item_id not in completed_ids and item_status in ['pending', 'in_progress']:
            # Check if dependencies are met
            dependencies = item.get('dependencies', []) if isinstance(item, dict) else getattr(item, 'dependencies', [])
            if all(dep in completed_ids for dep in dependencies):
                next_work_item = item
                break
    
    if next_work_item:
        item_id = next_work_item.get('id') if isinstance(next_work_item, dict) else next_work_item.id
        logger.info(f"COMMAND API: Starting Work Item: {item_id} -> Routing to code_generation_node")
        
        # CRITICAL: Create deep copy to avoid reference issues
        work_item_copy = dict(next_work_item) if isinstance(next_work_item, dict) else next_work_item
        
        logger.info(f"BULLETPROOF: Triple-setting current_work_item to: {item_id}")
        
        # STRATEGY 1: Direct state mutation (immediate effect)
        state["current_work_item"] = work_item_copy
        state[StateFields.WORKFLOW_COMPLETE] = False
        state["_iterator_decision"] = "proceed"
        state["_iterator_reason"] = f"Processing work item {item_id}"
        
        # STRATEGY 2: Persist in config for emergency fallback access
        if "configurable" not in config:
            config["configurable"] = {}
        config["configurable"]["_emergency_current_work_item"] = work_item_copy
        config["configurable"]["_emergency_workflow_complete"] = False
        
        # STRATEGY 3: Command update parameter (LangGraph standard)
        update_dict = {
            "current_work_item": work_item_copy,
            StateFields.WORKFLOW_COMPLETE: False,
            "_iterator_decision": "proceed",
            "_iterator_reason": f"Processing work item {item_id}",
            "_command_api_debug": {
                "work_item_id": item_id,
                "timestamp": time.time(),
                "action": "set_current_work_item",
                "strategies_used": ["direct_mutation", "config_persistence", "command_update"]
            }
        }
        
        logger.info(f"BULLETPROOF: State updated using 3 strategies for work item: {item_id}")
        logger.info(f"BULLETPROOF: Update dict keys: {list(update_dict.keys())}")
        
        return Command(
            goto="code_generation_node",
            update=update_dict
        )
    else:
        logger.info("COMMAND API: All work items complete -> Routing to finalize_node")
        
        # Update state using all strategies for completion
        state["current_work_item"] = None
        state[StateFields.WORKFLOW_COMPLETE] = True
        
        # Also persist in config
        if "configurable" not in config:
            config["configurable"] = {}
        config["configurable"]["_emergency_current_work_item"] = None
        config["configurable"]["_emergency_workflow_complete"] = True
        
        return Command(
            goto="finalize_node",
            update={
                "current_work_item": None,
                StateFields.WORKFLOW_COMPLETE: True,
                "_iterator_decision": "workflow_complete",
                "_iterator_reason": "All work items completed",
                "_command_api_debug": {
                    "action": "workflow_complete",
                    "timestamp": time.time(),
                    "strategies_used": ["direct_mutation", "config_persistence", "command_update"]
                }
            }
        )

# Keep the original async version for compatibility but prefer the Command API version
async def async_work_item_iterator_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """
    Asynchronous version of the work item iterator.
    Iterate through the work item backlog and set up the current item for execution.
    
    DEFINITIVE FIX 3: This version fixes the state propagation issue by ensuring
    the router gets the correct state through both return values AND state mutation.
    """
    logger.info("LEGACY ITERATOR: Executing ASYNC work item iterator node (FIXED version)")
    
    plan_output = state.get(StateFields.IMPLEMENTATION_PLAN)
    if not plan_output:
        logger.warning("WORK_ITEM_ITERATOR: Implementation plan is missing from the state.")
        # CRITICAL: Both mutate state AND return the values
        state["current_work_item"] = None
        state[StateFields.WORKFLOW_COMPLETE] = True
        state["_routing_decision"] = "workflow_complete"
        return {
            "current_work_item": None, 
            StateFields.WORKFLOW_COMPLETE: True,
            "_routing_decision": "workflow_complete"
        }

    work_items = []
    # CORRECTED PARSING LOGIC: Handle ComprehensiveImplementationPlanOutput structure
    if hasattr(plan_output, 'plan') and hasattr(plan_output.plan, 'phases'):
        # This handles the Pydantic model ComprehensiveImplementationPlanOutput(plan=ImplementationPlan(phases=[...]))
        # Work items are stored within the phases
        for phase in plan_output.plan.phases:
            if isinstance(phase, dict) and 'work_items' in phase:
                work_items.extend(phase['work_items'])
            elif hasattr(phase, 'work_items') and phase.work_items:
                # If phase is a Pydantic model with work_items
                work_items.extend(phase.work_items)
    elif hasattr(plan_output, 'work_items'):
        # This handles the case where the object is the WorkItemBacklog itself
        work_items = plan_output.work_items
    elif isinstance(plan_output, dict):
        # Handle dictionary representations
        plan = plan_output.get("plan", {})
        if "phases" in plan:
            # Extract work items from phases in dictionary format
            for phase in plan["phases"]:
                if isinstance(phase, dict) and 'work_items' in phase:
                    work_items.extend(phase['work_items'])
        elif "work_items" in plan:
            work_items = plan["work_items"]
        elif "work_items" in plan_output:
            work_items = plan_output["work_items"]

    logger.info(f"WORK_ITEM_ITERATOR: Found {len(work_items)} work items total with corrected parsing logic.")
    
    # Debug: Log the structure of work items found
    if work_items:
        logger.info(f"WORK_ITEM_ITERATOR: First work item structure: {list(work_items[0].keys()) if isinstance(work_items[0], dict) else 'Pydantic model'}")
        for i, item in enumerate(work_items[:3]):  # Log first 3 items
            item_id = item.get('id') if isinstance(item, dict) else getattr(item, 'id', 'unknown')
            logger.info(f"WORK_ITEM_ITERATOR: Work item {i+1}: {item_id}")
    else:
        logger.warning(f"WORK_ITEM_ITERATOR: No work items found. Plan output structure: {type(plan_output)}")
        if hasattr(plan_output, 'plan'):
            logger.info(f"WORK_ITEM_ITERATOR: Plan structure: phases={len(plan_output.plan.phases) if hasattr(plan_output.plan, 'phases') else 'N/A'}")
            if hasattr(plan_output.plan, 'phases'):
                for i, phase in enumerate(plan_output.plan.phases):
                    phase_items = phase.get('work_items', []) if isinstance(phase, dict) else getattr(phase, 'work_items', [])
                    logger.info(f"WORK_ITEM_ITERATOR: Phase {i+1} has {len(phase_items)} work items")

    completed_work_items_raw = state.get(StateFields.COMPLETED_WORK_ITEMS, [])
    completed_ids = set()
    if isinstance(completed_work_items_raw, (list, set)):
        for item in completed_work_items_raw:
            # Handle both string IDs and object formats
            if isinstance(item, str):
                # If it's already a string ID, use it directly
                completed_ids.add(item)
            elif isinstance(item, dict) and 'id' in item:
                # If it's a dict with an 'id' key
                completed_ids.add(item['id'])
            elif hasattr(item, 'id'):
                # If it's an object with an 'id' attribute
                completed_ids.add(item.id)
            else:
                # Log unrecognized format but continue
                logger.warning(f"WORK_ITEM_ITERATOR: Unrecognized completed item format: {item}")
    
    logger.info(f"WORK_ITEM_ITERATOR: Found {len(completed_ids)} completed work items: {completed_ids}")

    next_work_item = None
    for item in work_items:
        item_id = item.get('id') if isinstance(item, dict) else item.id
        dependencies = item.get('dependencies', []) if isinstance(item, dict) else getattr(item, 'dependencies', [])
        if item_id not in completed_ids and all(dep in completed_ids for dep in dependencies):
            next_work_item = item
            break
    
    if next_work_item:
        item_id = next_work_item.get('id') if isinstance(next_work_item, dict) else next_work_item.id
        logger.info(f"--- Starting Work Item: {item_id} ---")
        
        # CRITICAL FIX: Create a deep copy to avoid reference issues
        work_item_copy = dict(next_work_item) if isinstance(next_work_item, dict) else next_work_item
        
        # STRATEGY 1: Mutate the state object directly (for immediate access)
        state["current_work_item"] = work_item_copy
        state[StateFields.WORKFLOW_COMPLETE] = False
        state["_routing_decision"] = "proceed"
        
        # STRATEGY 2: Also store in a special key that the router will check
        state["_iterator_work_item"] = work_item_copy
        state["_iterator_complete"] = False
        
        logger.info(f"WORK_ITEM_ITERATOR: FIXED - State updated with work item: {item_id}, routing_decision='proceed'")
        logger.info(f"WORK_ITEM_ITERATOR: FIXED - Also stored in _iterator_work_item for router verification")
        
        # STRATEGY 3: Return comprehensive state updates
        return {
            "current_work_item": work_item_copy,
            StateFields.WORKFLOW_COMPLETE: False,
            "_routing_decision": "proceed",
            "_iterator_work_item": work_item_copy,
            "_iterator_complete": False,
            "_iterator_status": "found_work_item",
            "_iterator_item_id": item_id
        }
    else:
        logger.info("--- All work items complete ---")
        
        # STRATEGY 1: Mutate the state object directly
        state["current_work_item"] = None
        state[StateFields.WORKFLOW_COMPLETE] = True
        state["_routing_decision"] = "workflow_complete"
        
        # STRATEGY 2: Also store in special keys for router
        state["_iterator_work_item"] = None
        state["_iterator_complete"] = True
        
        logger.info("WORK_ITEM_ITERATOR: FIXED - State updated to mark workflow complete.")
        logger.info("WORK_ITEM_ITERATOR: FIXED - Also stored completion status in _iterator_complete")
        
        # STRATEGY 3: Return comprehensive state updates
        return {
            "current_work_item": None,
            StateFields.WORKFLOW_COMPLETE: True,
            "_routing_decision": "workflow_complete",
            "_iterator_work_item": None,
            "_iterator_complete": True,
            "_iterator_status": "all_complete"
        }

async def async_mark_work_item_complete_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """Mark the current work item as complete."""
    logger.info("Executing ASYNC mark_work_item_complete_node")
    
    current_work_item = state.get("current_work_item")
    if not current_work_item:
        logger.warning("MARK_WORK_ITEM_COMPLETE: No current work item to mark as complete.")
        return {}

    item_id = current_work_item.get('id') if isinstance(current_work_item, dict) else current_work_item.id
    logger.info(f"MARK_WORK_ITEM_COMPLETE: Marking work item '{item_id}' as complete.")

    completed_work_items = state.get(StateFields.COMPLETED_WORK_ITEMS, set())
    completed_work_items.add(item_id)

    logger.info(f"MARK_WORK_ITEM_COMPLETE: Updated completed work items: {completed_work_items}")

    # Update the state with the new completed work items
    return {
        StateFields.COMPLETED_WORK_ITEMS: completed_work_items,
        "current_work_item": None, # Reset current work item after completion
        "human_decision": None,
        "revision_feedback": None,
        "resume_from_approval": False,
    }

# Legacy sync routing function (still needed for compatibility)
def sync_route_after_work_item_iterator(state: AgentState) -> str:
    """
    Synchronous routing function for LangGraph conditional edges.
    DEPRECATED: This can cause state propagation issues when used with async nodes.
    Prefer async_route_after_work_item_iterator.
    """
    # This logic is now handled by the async version
    return async_route_after_work_item_iterator_sync_wrapper(state)


async def async_route_after_work_item_iterator(state: AgentState) -> str:
    """
    Asynchronous routing function that checks the '_routing_decision'
    set explicitly by the async_work_item_iterator_node to decide the next step.
    This is the reliable way to route after an async node.
    """
    # The iterator node now directly mutates the state, so this router
    # will have the most up-to-date information.
    routing_decision = state.get("_routing_decision", "workflow_complete")
    logger.info(f"ASYNC_ROUTER: Routing decision: '{routing_decision}'")
    
    if routing_decision == "proceed":
        return "proceed"
    else:
        return "workflow_complete"

def async_route_after_work_item_iterator_sync_wrapper(state: AgentState) -> str:
    """
    ENHANCED: Sync wrapper that should NOT be called when using sync nodes.
    This is a compatibility shim that will attempt to fix async/sync mismatch issues.
    """
    # CRITICAL DEBUG: Log all state information for troubleshooting
    logger.error(f"CRITICAL WARNING: async_route_after_work_item_iterator_sync_wrapper called!")
    logger.error(f"This suggests wrong workflow type or async/sync node mismatch.")
    logger.error(f"State keys: {list(state.keys())}")
    
    # Check multiple state locations for reliability
    decision = state.get("_routing_decision", "workflow_complete")
    current_work_item = state.get("current_work_item")
    workflow_complete = state.get(StateFields.WORKFLOW_COMPLETE, False)
    
    # NEW: Check additional state keys set by the fixed iterator
    iterator_work_item = state.get("_iterator_work_item")
    iterator_complete = state.get("_iterator_complete", False)
    iterator_status = state.get("_iterator_status", "unknown")
    
    logger.info(f"SYNC_WRAPPER_ROUTER_FIXED: _routing_decision='{decision}', has_work_item={bool(current_work_item)}, workflow_complete={workflow_complete}")
    logger.info(f"SYNC_WRAPPER_ROUTER_FIXED: iterator_work_item={bool(iterator_work_item)}, iterator_complete={iterator_complete}, iterator_status='{iterator_status}'")
    
    # CRITICAL FIX: Try to check if we have a current_work_item in the returned state
    # Since the async iterator mutates state directly, check the state object itself
    
    # ENHANCED LOGIC: Use multiple checks for reliability
    
    # Check 1: Direct iterator status (most reliable)
    if iterator_status == "found_work_item" and iterator_work_item is not None:
        logger.info(f"SYNC_WRAPPER_ROUTER_FIXED: Iterator found work item - routing to 'proceed'")
        return "proceed"
    
    # Check 2: Iterator completion status
    if iterator_status == "all_complete" or iterator_complete:
        logger.info(f"SYNC_WRAPPER_ROUTER_FIXED: Iterator marked complete - routing to 'workflow_complete'")
        return "workflow_complete"
    
    # Check 3: Original logic as fallback
    if current_work_item is not None and not workflow_complete:
        work_item_id = current_work_item.get('id', 'UNKNOWN') if isinstance(current_work_item, dict) else 'NON_DICT'
        logger.info(f"SYNC_WRAPPER_ROUTER_FIXED: Found work item '{work_item_id}' in main state - routing to 'proceed'")
        return "proceed"
    elif decision == "proceed":
        logger.info(f"SYNC_WRAPPER_ROUTER_FIXED: Decision is 'proceed' - routing to 'proceed' (trusting async iterator)")
        return "proceed"
    
    # Check 4: Additional fallback using iterator_work_item
    if iterator_work_item is not None and not iterator_complete:
        logger.info(f"SYNC_WRAPPER_ROUTER_FIXED: Found work item in iterator state - routing to 'proceed'")
        return "proceed"
    
    # Check 5: EMERGENCY FALLBACK - if this is the first call after plan approval and we don't see complete workflow
    if not workflow_complete and decision != "workflow_complete":
        plan_output = state.get(StateFields.IMPLEMENTATION_PLAN)
        if plan_output:
            logger.warning(f"EMERGENCY_FALLBACK: Implementation plan exists but no work item set - forcing 'proceed' to prevent premature finalization")
            return "proceed"
    
    # Default: Complete workflow
    logger.info(f"SYNC_WRAPPER_ROUTER_FIXED: No work item found in any state location - routing to 'workflow_complete'")
    return "workflow_complete"

# Create async versions of decision functions
async def async_has_next_phase(state: AgentState) -> str:
    """Async wrapper for has_next_phase decision function."""
    return await asyncio.to_thread(has_next_phase, state)

async def async_should_retry_code_generation(state: AgentState) -> str:
    """Async wrapper for should_retry_code_generation decision function."""
    return await asyncio.to_thread(decide_on_code_quality, state) # Mapped to new function

async def async_decide_on_code_quality(state: AgentState) -> str:
    """Async wrapper for the code quality decision."""
    return await asyncio.to_thread(decide_on_code_quality, state)

async def async_decide_on_test_results(state: AgentState) -> str:
    """Async wrapper for the unit test results decision."""
    return await asyncio.to_thread(decide_on_test_results, state)

async def async_decide_on_integration_test_results(state: AgentState) -> str:
    """Async wrapper for the integration test results decision."""
    return await asyncio.to_thread(decide_on_integration_test_results, state)

# Add async wrappers for legacy decision functions
async_decide_on_architecture_quality = make_async_node(decide_on_architecture_quality)
async_decide_on_database_quality = make_async_node(decide_on_database_quality)
async_decide_on_backend_quality = make_async_node(decide_on_backend_quality)
async_decide_on_frontend_quality = make_async_node(decide_on_frontend_quality)
async_decide_on_integration_quality = make_async_node(decide_on_integration_quality)

# Initialization node to set up the state properly
async def async_initialize_workflow_state(state: AgentState, config: dict) -> Dict[str, Any]:
    """
    Initialize essential state keys at the beginning of the workflow, preserving
    any keys passed in during resumption (like approval flags).
    """
    logger.info("Initializing essential workflow state keys")
    logger.info(f"INITIALIZE_STATE_NODE: Received state with keys: {list(state.keys())}")
    logger.info(f"INITIALIZE_STATE_NODE: skip_brd_analysis from input state: {state.get('skip_brd_analysis')}")

    try:
        # Start with a fresh dictionary for defaults
        initial_state = {}

        # Initialize workflow metadata using consistent field names
        initial_state["workflow_id"] = state.get("workflow_id", f"workflow_{int(time.time())}")
        initial_state["workflow_start_time"] = state.get("workflow_start_time", time.time())

        # Initialize code generation structure
        initial_state["code_generation_result"] = state.get("code_generation_result", {
            "generated_files": {},
            "status": "not_started",
            "generation_metrics": {}
        })

        # Initialize error tracking
        initial_state["errors"] = state.get("errors", [])

        # Initialize execution timing structures
        initial_state["agent_execution_times"] = state.get("agent_execution_times", {})
        initial_state["module_execution_times"] = state.get("module_execution_times", {})

        # Initialize phase tracking
        initial_state["current_phase_index"] = state.get("current_phase_index", 0)

        # Initialize revision counters
        revision_counter_keys = [
            StateFields.ARCHITECTURE_REVISION_COUNT,
            StateFields.DATABASE_REVISION_COUNT,
            StateFields.BACKEND_REVISION_COUNT,
            StateFields.FRONTEND_REVISION_COUNT,
            StateFields.INTEGRATION_REVISION_COUNT
        ]
        for key in revision_counter_keys:
            initial_state[key] = state.get(key, 0)

        # Initialize retry counters
        initial_state["current_code_gen_retry"] = state.get("current_code_gen_retry", 0)
        initial_state["current_test_retry"] = state.get("current_test_retry", 0)
        initial_state["current_implementation_iteration"] = state.get("current_implementation_iteration", 0)

        # Initialize thresholds
        initial_state["min_quality_score"] = state.get("min_quality_score", 3.0)
        initial_state["min_success_rate"] = state.get("min_success_rate", 0.7)
        initial_state["min_coverage_percentage"] = state.get("min_coverage_percentage", 60.0)
        initial_state["max_code_gen_retries"] = state.get("max_code_gen_retries", 3)
        initial_state["max_test_retries"] = state.get("max_test_retries", 2)
        initial_state["max_implementation_iterations"] = state.get("max_implementation_iterations", 2)

        # Initialize completed stages tracking
        initial_state["completed_stages"] = state.get("completed_stages", [])

        # CRITICAL FIX: Merge the original state into the initial state.
        # This preserves any flags passed during resumption (e.g., skip_brd_analysis).
        # The initial_state provides the defaults, and the incoming state overwrites them.
        final_state = {**initial_state, **state}

        logger.info(f"Workflow {final_state['workflow_id']} initialized successfully")
        logger.info(f"INITIALIZE_STATE_NODE: Returning state with keys: {list(final_state.keys())}")
        logger.info(f"INITIALIZE_STATE_NODE: skip_brd_analysis in output state: {final_state.get('skip_brd_analysis')}")
        return final_state

    except Exception as e:
        logger.error(f"Failed to initialize workflow state: {str(e)}")
        
        # Return minimal state with error (fallback)
        return {
            "workflow_id": f"workflow_{int(time.time())}",
            "workflow_start_time": time.time(),
            "errors": [{
                "module": "Initialization",
                "function": "async_initialize_workflow_state",
                "error": str(e),
                "timestamp": time.time()
            }]
        }

# Add temperature binding context manager
@asynccontextmanager
async def with_temperature(config: dict, temp: float):
    """
    Context manager for temperature binding in async context.
    
    Args:
        config: Configuration dictionary containing LLM
        temp: Temperature to use for binding (0.1-0.4)
        
    Yields:
        None: Context manager handles LLM replacement and restoration
    """
    if "configurable" not in config or "llm" not in config["configurable"]:
        yield
        return
        
    llm = config["configurable"]["llm"]
    original_llm = llm
    
    try:
        # Apply temperature binding
        config["configurable"]["llm"] = llm.bind(temperature=temp)
        logger.info(f"Bound temperature to {temp}")
        yield
    finally:
        # Always restore the original LLM no matter what happens
        config["configurable"]["llm"] = original_llm
        logger.info(f"Restored original LLM configuration")

# For backward compatibility, provide mappings to legacy node functions
# Each of these will just point to the updated, refactored implementations
async_project_analyzer_node = async_planning_node
async_timeline_estimator_node = async_planning_node
async_risk_assessor_node = async_planning_node
async_plan_compiler_node = async_planning_node

# Old specialized generator nodes now point to the dispatcher
async_architecture_generator_node = async_code_generation_dispatcher_node
async_database_generator_node = async_code_generation_dispatcher_node
async_backend_generator_node = async_code_generation_dispatcher_node
async_frontend_generator_node = async_code_generation_dispatcher_node
async_integration_generator_node = async_code_generation_dispatcher_node
async_code_optimizer_node = async_code_generation_dispatcher_node

# Testing nodes
async_test_case_generation_node = async_test_execution_node
async_test_validation_node = async_test_execution_node

# Quality nodes
async_architecture_quality_node = async_code_quality_analysis_node
async_database_quality_node = async_code_quality_analysis_node
async_backend_quality_node = async_code_quality_analysis_node
async_frontend_quality_node = async_code_quality_analysis_node
async_integration_quality_node = async_code_quality_analysis_node

# Legacy phase functions
async_phase_dispatcher_node = async_work_item_iterator_node

# Legacy decision functions that map to our new ones
async def async_determine_phase_generators(state: AgentState) -> str:
    """Legacy decision function that now maps to has_next_phase"""
    return await async_has_next_phase(state)

async def async_should_retry_tests(state: AgentState) -> str:
    """Legacy test retry decision function - defaults to 'continue'"""
    return "continue"  # In our new model, test retries are handled differently

# Legacy modules that map to our core functions
async def async_testing_module(state: AgentState, config: dict) -> Dict[str, Any]:
    """Legacy testing module - maps to testing_module_node"""
    return await async_test_execution_node(state, config)

async def async_planning_module(state: AgentState, config: dict) -> Dict[str, Any]:
    """Legacy planning module - maps to planning_node"""
    return await async_planning_node(state, config)

async def async_quality_module(state: AgentState, config: dict) -> Dict[str, Any]:
    """Legacy quality module - maps to code_quality_analysis_node"""
    return await async_code_quality_analysis_node(state, config)

async def async_implementation_module(state: AgentState, config: dict) -> Dict[str, Any]:
    """Legacy implementation module - maps to code_generation_dispatcher_node"""
    return await async_code_generation_dispatcher_node(state, config)

# Legacy checkpoint and recovery functions (simplified)
async def async_checkpoint_state(state: AgentState, config: dict) -> Dict[str, Any]:
    """Create a checkpoint from the current state."""
    logger.info("Creating checkpoint of current workflow state")
    
    # Simply pass through with minimal checkpoint metadata
    return {
        "checkpoint_created": time.time(),
        "checkpoint_id": f"checkpoint_{int(time.time())}"
    }

async def async_attempt_recovery(state: AgentState, config: dict) -> Dict[str, Any]:
    """Attempt recovery from error state."""
    logger.info("Attempting recovery from error state")
    
    # For now, just continue with current state and log the attempt
    return {
        "recovery_attempted": True,
        "recovery_timestamp": time.time()
    }

# --- New: Generic async human-feedback node factory ---

def make_async_human_feedback_node(step_key: str, readable_name: str):
    """
    Factory to create a generic human feedback node for any step.
    This node will interrupt for human approval ONLY if a decision has not
    already been made (e.g., on workflow resumption).
    """
    async def _human_feedback_node(state: AgentState, config: dict) -> Dict[str, Any]:
        """Pauses the workflow and sends a notification for human review, unless resuming."""
        logger.info(f"--- Checking for Human Approval: {readable_name} ---")

        # --- Generic Resumption Check ---
        human_decision = state.get("human_decision", "")
        resume_from_approval = state.get("resume_from_approval", False)

        if resume_from_approval and human_decision:
            logger.info(f"✅ Resuming after human decision ('{human_decision}') for {readable_name}. Skipping interrupt.")
            # Pass the decision along so the router can use it immediately.
            # No state change is performed here, just passing data to the next node.
            return {
                "human_decision": human_decision,
                "resume_from_approval": True # Keep this flag for the router
            }
        # --- End Resumption Check ---

        logger.info(f"--- Interrupting for Human Approval: {readable_name} ---")
        
        # Set the current approval stage so the router knows where we are.
        approval_stage = readable_name.lower().replace(' ', '_').replace('-', '_')
        
        # DEBUG: Log the state keys and step_key for debugging
        logger.info(f"DEBUG: Available state keys: {list(state.keys())}")
        logger.info(f"DEBUG: Looking for step_key: '{step_key}' (type: {type(step_key)})")
        
        # CRITICAL FIX: Handle both enum and string step_key formats
        # Convert StateFields enum to its string value for state lookup
        lookup_key = step_key.value if hasattr(step_key, 'value') else str(step_key)
        logger.info(f"DEBUG: Using lookup_key: '{lookup_key}' for state access")
        
        step_output = state.get(step_key, None)  # Try enum key first
        if step_output is None and lookup_key != str(step_key):
            step_output = state.get(lookup_key, None)  # Try string key as fallback
        
        # If still no data, create a meaningful error structure
        if step_output is None:
            step_output = {
                "error": f"Data for {readable_name} not found in state",
                "available_keys": list(state.keys()),
                "searched_for": [str(step_key), lookup_key],
                "step_name": readable_name
            }
            logger.error(f"DEBUG: No data found for {readable_name} - searched keys: {[str(step_key), lookup_key]}")
        else:
            logger.info(f"DEBUG: Found step_output with keys: {list(step_output.keys()) if isinstance(step_output, dict) else 'not a dict'}")
        
        # Ensure step_output is always a dict for payload consistency
        if not isinstance(step_output, dict):
            step_output = {"data": step_output, "type": type(step_output).__name__}
        
        # Create a comprehensive payload for the frontend
        payload = {
            "message": f"Please review the {readable_name}. Do you approve?",
            "details": step_output,
            "current_node": f"human_approval_{approval_stage}_node",
            "approval_type": approval_stage,
            "step_name": readable_name,
            "current_approval_stage": approval_stage,
            # Add debug info to help troubleshoot
            "debug_info": {
                "step_key_original": str(step_key),
                "lookup_key_used": lookup_key,
                "state_keys_available": list(state.keys()),
                "data_found": step_output is not None and "error" not in step_output
            }
        }
        
        # Add step-specific data mapping for frontend compatibility
        # The key in the 'data' dict should match the 'approval_type'
        payload['data'] = {approval_stage: step_output}

        logger.info(f"Created human feedback payload for {readable_name} with keys: {list(payload.keys())}")
        logger.info(f"DEBUG: Payload details keys: {list(payload['details'].keys()) if isinstance(payload['details'], dict) else 'not a dict'}")
        logger.info(f"DEBUG: Payload data structure valid: {approval_stage in payload['data']}")
        
        # The 'interrupt' function MUST BE RETURNED to pause the graph.
        try:
            interrupt_result = interrupt(payload)
            logger.info(f"DEBUG: Interrupt created successfully for {readable_name}")
            return interrupt_result
        except Exception as interrupt_error:
            logger.error(f"DEBUG: Failed to create interrupt for {readable_name}: {interrupt_error}")
            # In case of interrupt failure, return the payload as a regular dict
            # This will allow the workflow to continue but won't pause for approval
            logger.warning(f"DEBUG: Falling back to non-interrupt mode for {readable_name}")
            return {"interrupt_payload": payload, "interrupt_failed": True}

    return _human_feedback_node

# Provide a more generic alias so other modules don't have to import the long name
async_make_human_feedback_node = make_async_human_feedback_node

# --- New: Generic router that handles all human approval decisions ---

def async_decide_after_human(state: AgentState) -> str:
    """
    Generic decision function for all human approval nodes.
    Routes based on human decision: proceed, revise, or end.
    This function should NOT modify state.
    """
    # Look for human_decision in multiple possible locations
    human_decision = state.get("human_decision", state.get("decision", "end"))
    
    # Enhanced logging for debugging
    logger.info(f"=== GENERIC HUMAN APPROVAL DECISION ROUTING ===")
    logger.info(f"Available state keys: {list(state.keys())}")
    logger.info(f"Raw human_decision value: {repr(human_decision)} (type: {type(human_decision)})")
    
    # Handle different types and normalize to string
    if human_decision is None:
        human_decision = "end"
    else:
        human_decision = str(human_decision).lower().strip()
    
    logger.info(f"Normalized human decision: '{human_decision}'")
    
    # Check for resume_from_approval flag
    resume_flag = state.get("resume_from_approval", False)
    logger.info(f"Resume from approval flag: {resume_flag}")
    
    # Handle all decision types properly
    if human_decision in ["proceed", "continue", "approve"]:
        logger.info(f"Decision '{human_decision}' -> Routing to 'proceed' for workflow continuation.")
        return "proceed"
    elif human_decision in ["revise", "reject", "request_revision"]:
        logger.info(f"Decision '{human_decision}' → Routing to 'revise' for revision request.")
        return "revise"
    elif human_decision in ["end", "terminate", "stop"]:
        logger.info(f"Decision '{human_decision}' → Routing to 'end' for workflow termination.")
        return "end"
    else:
        logger.warning(f"Unknown human decision '{human_decision}' received from state. Available state keys: {list(state.keys())}")
        logger.warning(f"Full state dump for debugging: {dict(state)}")
        logger.warning(f"Routing to 'end' due to unrecognized decision.")
        return "end"
# --- New: Generic Node to Mark Stage as Complete ---

async def async_mark_stage_complete_node(state: AgentState) -> Dict[str, Any]:
    """
    Generic node to mark a stage as complete after human approval and
    reset resumption flags so the next approval node will interrupt correctly.
    """
    # The stage name was set by the human_approval_node before interrupting.
    current_stage = state.get("current_approval_stage", "unknown")
    if current_stage == "unknown":
        logger.warning("Could not determine current stage to mark as complete.")
        return {}

    completed_stages = state.get("completed_stages", [])
    if current_stage not in completed_stages:
        completed_stages.append(current_stage)

    logger.info(f"Marking stage '{current_stage}' as complete.")
    
    # Return state updates. CRITICAL: Reset the flags.
    return {
        "completed_stages": completed_stages,
        "human_decision": None,
        "revision_feedback": None,
        "resume_from_approval": False,
    }

# --- New: Generic Router to direct workflow after a stage is marked complete ---
def route_after_completion(state: AgentState) -> str:
    """
    Reads the 'current_approval_stage' from the state to determine
    which stage was just completed, and routes to the next one.
    """
    last_completed_stage = state.get("current_approval_stage", "unknown")
    logger.info(f"Routing after completion of stage: '{last_completed_stage}'")

    routing_map = {
        "brd_analysis": "tech_stack_recommendation_node",
        "tech_stack_recommendation": "system_design_node",
        "system_design": "planning_node",
        "implementation_plan": "code_generation_node",
        "code_generation": END  # Or a final validation step
    }

    next_node = routing_map.get(last_completed_stage)

    if next_node:
        logger.info(f"Proceeding to next stage: '{next_node}'")
        return next_node
    else:
        logger.error(f"Unknown stage '{last_completed_stage}' completed. Ending workflow.")
        return END

# --- End State Update Nodes ---

# --- Existing decision functions continue below ---

async def async_increment_revision_node(state: AgentState, config: dict) -> Dict[str, Any]:
    return await asyncio.to_thread(increment_revision_count_node, state, config)

async def async_integration_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """Async wrapper for the integration_node."""
    return await asyncio.to_thread(integration_node, state, config)

async def async_check_circuit_breaker(state: AgentState) -> str:
    """
    Check circuit breaker conditions after increment_revision_node.
    Prevents infinite loops by checking for circuit breaker triggers and workflow completion flags.
    """
    # Check if circuit breaker was triggered
    circuit_breaker_triggered = state.get("circuit_breaker_triggered", False)
    workflow_complete = state.get(StateFields.WORKFLOW_COMPLETE, False)
    
    # Additional safety check: if no current_work_item and we're in a revision cycle, stop
    current_work_item = state.get("current_work_item")
    
    logger.info(f"CIRCUIT_BREAKER_CHECK: triggered={circuit_breaker_triggered}, workflow_complete={workflow_complete}, has_work_item={bool(current_work_item)}")
    
    if circuit_breaker_triggered or workflow_complete:
        logger.warning("CIRCUIT BREAKER: Stopping workflow due to circuit breaker or completion flag")
        return "stop"
    
    if not current_work_item:
        logger.warning("CIRCUIT BREAKER: No current_work_item found - likely Command API routing issue. Stopping to prevent infinite loop.")
        return "stop"
    
    # Normal case: continue with revision
    logger.info("CIRCUIT_BREAKER_CHECK: All checks passed - continuing with revision")
    return "continue"

# --- ASYNC Human-in-the-Loop Nodes ---

# The following human approval nodes from graph_nodes.py are now
# replaced by the generic make_async_human_feedback_node factory.
# However, for clarity, I'm keeping their async wrappers for now,
# though they might be refactored further.

async_human_approval_brd_node = async_make_human_feedback_node(StateFields.REQUIREMENTS_ANALYSIS, "BRD Analysis")

async_human_approval_tech_stack_node = make_async_human_feedback_node(StateFields.TECH_STACK_RECOMMENDATION, "Tech Stack Recommendation")

async_human_approval_system_design_node = make_async_human_feedback_node(StateFields.SYSTEM_DESIGN, "System Design")

async_human_approval_plan_node = make_async_human_feedback_node(StateFields.IMPLEMENTATION_PLAN, "Implementation Plan")
