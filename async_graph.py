"""
Async-compatible LangGraph Workflow Definition.
Uses asyncio patterns for non-blocking operation with LangGraph dev.
"""

from typing import Dict, Any, List, Optional
from langgraph.graph import StateGraph, END
import asyncio

from agent_state import AgentState
from async_graph_nodes import (
    async_brd_analysis_node,
    async_tech_stack_recommendation_node,
    async_system_design_node,
    async_planning_node,
    async_code_generation_node,
    async_test_case_generation_node,
    async_code_quality_analysis_node,
    async_test_validation_node,
    async_finalize_workflow,
    async_phase_iterator_node,
    # Add other async nodes
    async_should_retry_code_generation,
    async_should_retry_tests,
    async_has_next_phase
)

async def create_async_phased_workflow(platform_enabled=False) -> StateGraph:
    """Create an async-compatible phased workflow."""
    workflow = StateGraph(AgentState)
    
    # Add all nodes with async versions
    workflow.add_node("brd_analysis_step", async_brd_analysis_node)
    workflow.add_node("tech_stack_recommendation_step", async_tech_stack_recommendation_node)
    workflow.add_node("system_design_step", async_system_design_node)
    workflow.add_node("planning_step", async_planning_node)
    
    # Phase-based code generation nodes
    workflow.add_node("phase_iterator", async_phase_iterator_node)
    workflow.add_node("phase_code_generation", async_code_generation_node)
    workflow.add_node("phase_quality_analysis", async_code_quality_analysis_node)
    workflow.add_node("phase_completion", async_code_generation_node)  # Using code_gen as placeholder
    
    # Testing and finalization
    workflow.add_node("test_case_generation_step", async_test_case_generation_node)
    workflow.add_node("test_validation_step", async_test_validation_node)
    workflow.add_node("finalize_step", async_finalize_workflow)
    
    # Add passthrough node for phase iteration decision
    workflow.add_node("phase_iteration_decision", lambda x: x)  # Simple passthrough node
    
    workflow.set_entry_point("brd_analysis_step")
    
    # Setup main workflow flow
    workflow.add_edge("brd_analysis_step", "tech_stack_recommendation_step")
    workflow.add_edge("tech_stack_recommendation_step", "system_design_step")
    workflow.add_edge("system_design_step", "planning_step")
    
    # Phase iteration flow
    workflow.add_edge("planning_step", "phase_iterator")
    workflow.add_edge("phase_iterator", "phase_code_generation")
    workflow.add_edge("phase_code_generation", "phase_quality_analysis")
    
    # Conditional flow for code generation retry
    workflow.add_conditional_edges(
        "phase_quality_analysis",
        async_should_retry_code_generation,
        {
            "retry_code_generation": "phase_code_generation",
            "continue": "phase_completion"
        }
    )
    
    # Phase completion leads to either next phase or test generation
    workflow.add_edge("phase_completion", "phase_iteration_decision")
    workflow.add_conditional_edges(
        "phase_iteration_decision",
        async_has_next_phase,
        {
            "next_phase": "phase_iterator",
            "complete": "test_case_generation_step"
        }
    )
    
    # Testing workflow
    workflow.add_edge("test_case_generation_step", "test_validation_step")
    workflow.add_conditional_edges(
        "test_validation_step",
        async_should_retry_tests,
        {
            "retry_tests": "test_case_generation_step",
            "continue": "finalize_step"
        }
    )
    
    workflow.add_edge("finalize_step", END)
    
    return workflow