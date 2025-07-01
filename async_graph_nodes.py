"""
Async-compatible versions of LangGraph Node Functions.
Compatible with LangGraph dev and async contexts.
"""

import asyncio
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
    phase_iterator_node,
    phase_completion_node,
    increment_revision_count_node,
    
    # Core implementation nodes
    code_generation_dispatcher_node,
    code_quality_analysis_node,
    
    # Testing and finalization
    testing_module_node,
    finalize_workflow,
    
    # Edge decision functions
    has_next_phase,
    should_retry_code_generation,
    
    # Add all legacy decision functions to be wrapped
    decide_on_architecture_quality,
    decide_on_database_quality,
    decide_on_backend_quality,
    decide_on_frontend_quality,
    decide_on_integration_quality
)
# New: Import interrupt for human-in-the-loop
from langgraph.types import interrupt

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

# Wrapper function to make synchronous node functions async compatible
def make_async_node(sync_node_func: Callable) -> Callable:
    """
    Convert a synchronous node function to async-compatible with standardized
    error handling and execution time tracking.
    """
    async def async_node_func(state: AgentState, config: dict) -> Dict[str, Any]:
        # Get function name for logging
        func_name = sync_node_func.__name__
        start_time = time.time()
        
        try:
            # Execute the sync node function in a thread pool
            async with async_trace_span(func_name):
                result = await asyncio.to_thread(sync_node_func, state, config)
            
            # Track execution time in return value if it's a dictionary
            if isinstance(result, dict):
                if "execution_time" not in result:
                    result["execution_time"] = time.time() - start_time
                    
                logger.info(f"Async node {func_name} completed in {result['execution_time']:.2f}s")
                return result
            else:
                logger.warning(f"Async node {func_name} returned non-dict value: {type(result)}")
                return {"error": f"Invalid return type from {func_name}"}
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Error in async node {func_name}: {str(e)}")
            
            # Create error information
            error_info = {
                "module": "Async Node",
                "function": func_name,
                "error": str(e),
                "error_code": f"ASYNC_{func_name.upper()}_ERROR",
                "timestamp": time.time()
            }
            
            # Return minimal error information to avoid breaking workflow
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
async_phase_iterator_node = make_async_node(phase_iterator_node)
async_code_generation_dispatcher_node = make_async_node(code_generation_dispatcher_node)
async_code_quality_analysis_node = make_async_node(code_quality_analysis_node)
async_phase_completion_node = make_async_node(phase_completion_node)
async_testing_module_node = make_async_node(testing_module_node)
async_finalize_workflow = make_async_node(finalize_workflow)

# Implement increment_revision_count node for async use
async_increment_revision_count_node = make_async_node(increment_revision_count_node)

# Create async versions of decision functions
async def async_has_next_phase(state: AgentState) -> str:
    """Async wrapper for has_next_phase decision function."""
    return await asyncio.to_thread(has_next_phase, state)

async def async_should_retry_code_generation(state: AgentState) -> str:
    """Async wrapper for should_retry_code_generation decision function."""
    return await asyncio.to_thread(should_retry_code_generation, state)

# New: Human-in-the-loop node
async def human_approval_node(state: AgentState) -> dict:
    """
    Pauses the workflow to wait for human approval.
    This node uses langgraph.types.interrupt to halt execution.
    The frontend will catch this interruption and prompt the user.
    """
    logger.info("--- Human Approval: Waiting for review of BRD Analysis ---")
    
    # The `interrupt` function will pause the graph here.
    # The content passed to `interrupt` will be sent to the frontend.
    # We are including the BRD analysis output for the user to review.
    brd_analysis_output = state.get("requirements_analysis", {"error": "BRD analysis not found in state."})
    
    user_decision = interrupt(
        {
            "message": "Please review the BRD Analysis. Do you approve?",
            "details": brd_analysis_output,
            "options": ["approve", "reject", "edit"],
        }
    )

    logger.info(f"--- Human decision received: {user_decision} ---")

    return {"human_decision": user_decision}

def decide_after_brd_approval(state: AgentState) -> str:
    """
    Determines the next step based on the human's decision on the BRD analysis.

    - If 'approve', proceed to the next phase (tech stack).
    - If 'reject' or 'edit', loop back to revise the BRD analysis.
    - Otherwise, end the workflow.
    """
    human_decision = state.get("human_decision", "reject").lower()
    logger.info(f"Routing based on human decision: '{human_decision}'")

    if human_decision == "approve":
        return "proceed"
    elif human_decision in ["reject", "edit"]:
        logger.info("Decision is to revise. Looping back to BRD Analysis.")
        return "revise"
    else:
        logger.warning(f"Unknown human decision '{human_decision}' received. Ending workflow for safety.")
        return "end"

# Add async wrappers for legacy decision functions
async_decide_on_architecture_quality = make_async_node(decide_on_architecture_quality)
async_decide_on_database_quality = make_async_node(decide_on_database_quality)
async_decide_on_backend_quality = make_async_node(decide_on_backend_quality)
async_decide_on_frontend_quality = make_async_node(decide_on_frontend_quality)
async_decide_on_integration_quality = make_async_node(decide_on_integration_quality)

# Initialization node to set up the state properly
async def async_initialize_workflow_state(state: AgentState, config: dict) -> Dict[str, Any]:
    """
    Initialize essential state keys at the beginning of the workflow.
    
    This function ensures that all commonly used state keys are initialized
    with appropriate default values, preventing KeyError exceptions when
    these keys are accessed later in the workflow.
    
    Args:
        state: Current workflow state (may be empty or partially initialized)
        config: Configuration dictionary (unused but required for compatibility)
        
    Returns:
        State update dictionary with all essential keys initialized
    """
    logger.info("Initializing essential workflow state keys")
    
    try:
        # Create a new state object to avoid modifying the original
        initialized_state = state.copy()
        
        # Initialize workflow metadata using consistent field names
        if "workflow_id" not in initialized_state:
            initialized_state["workflow_id"] = f"workflow_{int(time.time())}"
        
        if "workflow_start_time" not in initialized_state:
            initialized_state["workflow_start_time"] = time.time()
        
        # Initialize code generation structure to match sync version
        if "code_generation_result" not in initialized_state:
            initialized_state["code_generation_result"] = {
                "generated_files": {},
                "status": "not_started",
                "generation_metrics": {}
            }
        elif "generated_files" not in initialized_state["code_generation_result"]:
            initialized_state["code_generation_result"]["generated_files"] = {}
        
        # Initialize error tracking
        if "errors" not in initialized_state:
            initialized_state["errors"] = []
        
        # Initialize execution timing structures
        if "agent_execution_times" not in initialized_state:
            initialized_state["agent_execution_times"] = {}
        
        if "module_execution_times" not in initialized_state:
            initialized_state["module_execution_times"] = {}
        
        # Initialize phase tracking
        if "current_phase_index" not in initialized_state:
            initialized_state["current_phase_index"] = 0
        
        # Initialize revision counters for code components (matching sync version)
        revision_counter_keys = [
            StateFields.ARCHITECTURE_REVISION_COUNT,
            StateFields.DATABASE_REVISION_COUNT, 
            StateFields.BACKEND_REVISION_COUNT,
            StateFields.FRONTEND_REVISION_COUNT,
            StateFields.INTEGRATION_REVISION_COUNT
        ]
        
        for key in revision_counter_keys:
            if key not in initialized_state:
                initialized_state[key] = 0
        
        # Initialize counters for retry decision points
        if "current_code_gen_retry" not in initialized_state:
            initialized_state["current_code_gen_retry"] = 0
            
        if "current_test_retry" not in initialized_state:
            initialized_state["current_test_retry"] = 0
            
        if "current_implementation_iteration" not in initialized_state:
            initialized_state["current_implementation_iteration"] = 0
        
        # Initialize thresholds for decision functions
        if "min_quality_score" not in initialized_state:
            initialized_state["min_quality_score"] = 3.0
            
        if "min_success_rate" not in initialized_state:
            initialized_state["min_success_rate"] = 0.7
            
        if "min_coverage_percentage" not in initialized_state:
            initialized_state["min_coverage_percentage"] = 60.0
            
        if "max_code_gen_retries" not in initialized_state:
            initialized_state["max_code_gen_retries"] = 3
            
        if "max_test_retries" not in initialized_state:
            initialized_state["max_test_retries"] = 2
            
        if "max_implementation_iterations" not in initialized_state:
            initialized_state["max_implementation_iterations"] = 2
        
        # Initialize completed steps tracking
        if "completed_stages" not in initialized_state:
            initialized_state["completed_stages"] = []
        
        # Log successful initialization
        logger.info(f"Workflow {initialized_state['workflow_id']} initialized successfully")
        return initialized_state
        
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
async_test_case_generation_node = async_testing_module_node
async_test_validation_node = async_testing_module_node

# Quality nodes
async_architecture_quality_node = async_code_quality_analysis_node
async_database_quality_node = async_code_quality_analysis_node
async_backend_quality_node = async_code_quality_analysis_node
async_frontend_quality_node = async_code_quality_analysis_node
async_integration_quality_node = async_code_quality_analysis_node

# Legacy phase functions
async_phase_dispatcher_node = async_phase_iterator_node

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
    return await async_testing_module_node(state, config)

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