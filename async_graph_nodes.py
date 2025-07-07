"""
Async-compatible versions of LangGraph Node Functions.
Compatible with LangGraph dev and async contexts.
"""

import asyncio
import re
from typing import Dict, Any, Callable, List, Optional
from contextlib import asynccontextmanager
import time
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
# New: Import interrupt for human-in-the-loop
from langgraph.types import interrupt
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
async_work_item_iterator_node = make_async_node(work_item_iterator_node)
async_code_generation_dispatcher_node = make_async_node(code_generation_dispatcher_node)
async_code_quality_analysis_node = make_async_node(code_quality_analysis_node)
async_phase_completion_node = make_async_node(phase_completion_node)
async_testing_module_node = make_async_node(test_execution_node)
async_finalize_workflow = make_async_node(finalize_workflow)
async_test_execution_node = make_async_node(test_execution_node)

# Implement increment_revision_count node for async use
async_increment_revision_count_node = make_async_node(increment_revision_count_node)

# New Integration Node Wrapper
async_integration_node = make_async_node(integration_node)

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

# Note: Legacy quality decision functions are created via make_async_node() above
# and map to the sync versions for consistent behavior

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
        logger.info(f"Decision '{human_decision}' → Routing to 'proceed' for workflow continuation.")
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

# --- ASYNC Human-in-the-Loop Nodes ---

# Remove the @traceable decorator if it's not defined or imported.
# @traceable(name="Async Human Approval BRD")
# async def human_approval_brd_node(state: AgentState) -> dict:
#     """
#     Human approval node for BRD analysis.
#     This node will interrupt the workflow for human approval.
#     """
#     logger.info("Async BRD analysis approval node reached.")
#     # This node primarily acts as a placeholder for the interrupt,
#     # which is configured in the graph definition.
#     return {}

# The following human approval nodes from graph_nodes.py are now
# replaced by the generic make_async_human_feedback_node factory.
# However, for clarity, I'm keeping their async wrappers for now,
# though they might be refactored further.

async_human_approval_brd_node = async_make_human_feedback_node(StateFields.REQUIREMENTS_ANALYSIS, "BRD Analysis")

async_human_approval_tech_stack_node = make_async_human_feedback_node(StateFields.TECH_STACK_RECOMMENDATION, "Tech Stack Recommendation")

async_human_approval_system_design_node = make_async_human_feedback_node(StateFields.SYSTEM_DESIGN, "System Design")

async_human_approval_plan_node = make_async_human_feedback_node(StateFields.IMPLEMENTATION_PLAN, "Implementation Plan")