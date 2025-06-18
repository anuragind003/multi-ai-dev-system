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
    should_retry_code_generation
)

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

# Initialization node to set up the state properly
async def async_initialize_workflow_state(state: AgentState, config: dict) -> Dict[str, Any]:
    """Initialize the workflow state with required fields."""
    logger.info("Initializing workflow state")
    
    try:
        # Generate a workflow ID if not present
        workflow_id = state.get(StateFields.WORKFLOW_ID, str(uuid.uuid4()))
        
        # Create initial state update
        state_update = {
            StateFields.WORKFLOW_ID: workflow_id,
            StateFields.WORKFLOW_START_TIME: time.time(),
            StateFields.WORKFLOW_STATUS: "initializing",
            StateFields.CURRENT_PHASE_INDEX: 0,
            StateFields.REVISION_COUNTS: {},
            StateFields.ERRORS: []
        }
        
        # Initialize code_generation_result if not present
        if StateFields.CODE_GENERATION_RESULT not in state:
            state_update[StateFields.CODE_GENERATION_RESULT] = {
                "generated_files": [],
                "status": "not_started",
                "timestamp": time.time()
            }
            
        # Log successful initialization
        logger.info(f"Workflow {workflow_id} initialized successfully")
        return state_update
        
    except Exception as e:
        logger.error(f"Failed to initialize workflow state: {str(e)}")
        
        # Return minimal state with error
        return {
            StateFields.WORKFLOW_ID: str(uuid.uuid4()),
            StateFields.WORKFLOW_STATUS: "error",
            StateFields.ERRORS: [{
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

# Replace these recursive decision functions:

# Legacy quality decision functions
async def async_decide_on_architecture_quality(state: AgentState) -> str:
    """Maps to the unified should_retry_code_generation decision"""
    # Fix recursive call by using the standard retry function instead
    return await async_should_retry_code_generation(state)

async def async_decide_on_database_quality(state: AgentState) -> str:
    """Maps to the unified should_retry_code_generation decision"""
    return await async_should_retry_code_generation(state)

async def async_decide_on_backend_quality(state: AgentState) -> str:
    """Maps to the unified should_retry_code_generation decision"""
    return await async_should_retry_code_generation(state)

async def async_decide_on_frontend_quality(state: AgentState) -> str:
    """Maps to the unified should_retry_code_generation decision"""
    return await async_should_retry_code_generation(state)

async def async_decide_on_integration_quality(state: AgentState) -> str:
    """Maps to the unified should_retry_code_generation decision"""
    return await async_should_retry_code_generation(state)