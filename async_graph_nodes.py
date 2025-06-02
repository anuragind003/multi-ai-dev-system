"""
Async-compatible versions of LangGraph Node Functions.
Compatible with LangGraph dev and async contexts.
"""

import asyncio
from typing import Dict, Any, Callable
from contextlib import asynccontextmanager
import time

from agent_state import AgentState
import monitoring
import graph_nodes

@asynccontextmanager
async def async_trace_span(name: str, metadata=None):
    """Async implementation of trace_span."""
    start_time = time.time()
    span_id = f"phase_{int(start_time * 1000)}"
    
    try:
        # Log the start of the phase
        await asyncio.to_thread(
            monitoring.log_agent_activity,
            agent="Phase Iterator", 
            message=f"Starting phase: {name}", 
            level="INFO",
            metadata={
                "span_id": span_id,
                "phase": name,
                **(metadata or {})
            }
        )
        
        # Execute the phase
        yield
        
    except Exception as e:
        # Log error with comprehensive details
        execution_time = time.time() - start_time
        await asyncio.to_thread(
            monitoring.log_agent_activity,
            agent="Phase Iterator",
            message=f"Error in phase {name}: {str(e)}",
            level="ERROR",
            metadata={
                "span_id": span_id,
                "phase": name,
                "execution_time": execution_time,
                "error": str(e),
                **(metadata or {})
            }
        )
        # Re-raise the exception for proper handling
        raise
        
    finally:
        # Always log completion with performance metrics
        execution_time = time.time() - start_time
        await asyncio.to_thread(
            monitoring.log_agent_activity,
            agent="Phase Iterator",
            message=f"Completed phase: {name}",
            level="INFO",
            metadata={
                "span_id": span_id,
                "phase": name,
                "execution_time": execution_time,
                **(metadata or {})
            }
        )

# Wrapper function to make synchronous node functions async compatible
def make_async_node(sync_node_func: Callable) -> Callable:
    """Convert a synchronous node function to async-compatible."""
    async def async_wrapper(state: AgentState, config: dict) -> AgentState:
        # Run the original function in a thread pool to prevent blocking
        return await asyncio.to_thread(sync_node_func, state, config)
    
    # Preserve the original function's name and docstring
    async_wrapper.__name__ = f"async_{sync_node_func.__name__}"
    async_wrapper.__doc__ = f"Async version of {sync_node_func.__name__}:\n\n{sync_node_func.__doc__}"
    
    return async_wrapper

# Create async versions of all node functions
async_brd_analysis_node = make_async_node(graph_nodes.brd_analysis_node)
async_tech_stack_recommendation_node = make_async_node(graph_nodes.tech_stack_recommendation_node)
async_system_design_node = make_async_node(graph_nodes.system_design_node)
async_planning_node = make_async_node(graph_nodes.planning_node)
async_code_generation_node = make_async_node(graph_nodes.code_generation_node)
async_test_case_generation_node = make_async_node(graph_nodes.test_case_generation_node)
async_code_quality_analysis_node = make_async_node(graph_nodes.code_quality_analysis_node)
async_test_validation_node = make_async_node(graph_nodes.test_validation_node)
async_finalize_workflow = make_async_node(graph_nodes.finalize_workflow)

# Special handling for phase_iterator_node due to trace_span usage
async def async_phase_iterator_node(state: AgentState, config: dict) -> AgentState:
    """Async version of phase_iterator_node."""
    async with async_trace_span(name=f"Phase Iterator - {state.get('current_phase_index', 0)}"):
        # Run the original function logic in a thread pool, but without the trace_span
        # That's handled by our async_trace_span above
        
        # This is a simplified version - you'll need to adapt the actual logic from phase_iterator_node
        # Get all phases from implementation plan
        implementation_plan = state.get("implementation_plan", {})
        all_phases = implementation_plan.get("development_phases", [])
        
        if not all_phases:
            await asyncio.to_thread(
                monitoring.log_agent_activity,
                "Phase Iterator", 
                "No phases found in implementation plan", 
                "WARNING"
            )
            return state
        
        # Rest of your logic here, using await asyncio.to_thread for blocking operations
        
        # For now, just run the original function without trace_span
        # This is a simplification - for production, you'd want to reimplement the logic with async
        return await asyncio.to_thread(graph_nodes.phase_iterator_node, state, config)

# Create async versions of decision functions - these are typically lightweight so simple wrapping works
async def async_should_retry_code_generation(state: AgentState) -> str:
    return await asyncio.to_thread(graph_nodes.should_retry_code_generation, state)

async def async_should_retry_tests(state: AgentState) -> str:
    return await asyncio.to_thread(graph_nodes.should_retry_tests, state)

async def async_has_next_phase(state: AgentState) -> str:
    return await asyncio.to_thread(graph_nodes.has_next_phase, state)