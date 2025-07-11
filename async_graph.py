"""
Async-compatible LangGraph Workflow Definition.
Uses asyncio patterns for non-blocking operation with LangGraph dev.
"""

from typing import Dict, Any, List, Optional
from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableLambda  # Add this import
import asyncio

from agent_state import AgentState, StateFields
# Import refactored async nodes
from async_graph_nodes import (
    async_initialize_workflow_state,
    async_brd_analysis_node,
    async_tech_stack_recommendation_node,
    async_system_design_node,
    async_planning_node,
    async_work_item_iterator_node_command,  # NEW: Command API version
    async_work_item_iterator_node,  # Keep legacy version for compatibility
    async_code_generation_dispatcher_node,
    async_code_quality_analysis_node,
    async_test_execution_node,
    async_integration_node,
    async_finalize_workflow,
    async_phase_completion_node,
    
    # Import decision functions
    async_decide_on_code_quality,
    async_decide_on_test_results,
    async_decide_on_integration_test_results,
    async_increment_revision_count_node,
    async_mark_work_item_complete_node,
    async_check_circuit_breaker,  # NEW: Circuit breaker function
    
    # Human approval components
    async_make_human_feedback_node,
    async_decide_after_human,
    async_mark_stage_complete_node,
    route_after_completion
)
import monitoring
from platform_config import get_platform_client
from langgraph.checkpoint.memory import MemorySaver

def validate_agent_factory(config: Dict[str, Any]) -> List[str]:
    """Validate the agent factory configuration."""
    issues = []
    
    if "configurable" not in config:
        return ["Missing 'configurable' section in config"]
        
    configurable = config.get("configurable", {})
    
    # Check essential components
    if "llm" not in configurable:
        issues.append("Missing 'llm' in configurable - required for agent creation")
        
    if "temperature_strategy" not in configurable:
        issues.append("Missing 'temperature_strategy' - required for agent temperature optimization")
    
    # Check for common tools
    if "code_execution_tool" not in configurable:
        issues.append("Missing 'code_execution_tool' - recommended for code validation")
    
    if "rag_manager" not in configurable:
        issues.append("Missing 'rag_manager' - recommended for context-aware generation")
    
    return issues

def validate_workflow_configuration(config: Dict[str, Any]) -> List[str]:
    """Validate workflow configuration including temperature management strategy."""
    issues = []
    
    # Check required components in config
    if "configurable" not in config:
        return ["Missing 'configurable' section in config"]
        
    configurable = config.get("configurable", {})
    
    # Check essential components
    required_components = ["llm", "memory", "run_output_dir"]
    for component in required_components:
        if component not in configurable:
            issues.append(f"Missing required component '{component}' in configuration")

    # Check temperature strategy
    if "temperature_strategy" not in configurable:
        issues.append("Missing 'temperature_strategy' in configuration")
    else:
        temp_strategy = configurable.get("temperature_strategy", {})
        essential_agents = [
            "BRD Analyst Agent", 
            "Tech Stack Advisor Agent",
            "System Designer Agent",
            "Code Generation Agent",
            "Code Quality Agent",
            "Test Validation Agent"
        ]
        
        for agent in essential_agents:
            if agent not in temp_strategy:
                issues.append(f"Missing temperature setting for essential agent: {agent}")
    
    # Validate agent factory if provided
    agent_factory_issues = validate_agent_factory(config)
    issues.extend(agent_factory_issues)
    
    return issues

async def create_async_phased_workflow_command_api() -> StateGraph:
    """
    🚀 ADVANCED: Create a phased development workflow using LangGraph Command API.
    This version uses the Command API for direct routing control, solving state propagation issues.
    """
    workflow = StateGraph(AgentState)

    # Add state initialization
    workflow.add_node("initialize_state_node", async_initialize_workflow_state)

    # --- Agent Nodes ---
    workflow.add_node("brd_analysis_node", async_brd_analysis_node)
    workflow.add_node("tech_stack_recommendation_node", async_tech_stack_recommendation_node)
    workflow.add_node("system_design_node", async_system_design_node)
    workflow.add_node("planning_node", async_planning_node)
    workflow.add_node("code_generation_node", async_code_generation_dispatcher_node)
    
    # 🚀 COMMAND API: Use the advanced Command API iterator
    workflow.add_node("work_item_iterator_node", async_work_item_iterator_node_command)
    
    workflow.add_node("test_execution_node", async_test_execution_node)
    workflow.add_node("phase_completion_node", async_phase_completion_node)
    workflow.add_node("increment_revision_node", async_increment_revision_count_node)
    workflow.add_node("finalize_node", async_finalize_workflow)
    workflow.add_node("code_quality_node", async_code_quality_analysis_node)
    workflow.add_node("async_integration_node", async_integration_node)

    # --- Human Approval Nodes (created by a generic factory) ---
    brd_feedback_node = async_make_human_feedback_node(StateFields.REQUIREMENTS_ANALYSIS, "BRD Analysis")
    tech_stack_feedback_node = async_make_human_feedback_node(StateFields.TECH_STACK_RECOMMENDATION, "Tech Stack Recommendation")
    system_design_feedback_node = async_make_human_feedback_node(StateFields.SYSTEM_DESIGN, "System Design")
    planning_feedback_node = async_make_human_feedback_node(StateFields.IMPLEMENTATION_PLAN, "Implementation Plan")
    code_generation_feedback_node = async_make_human_feedback_node(StateFields.CODE_GENERATION_OUTPUT, "Code Generation")

    workflow.add_node("human_approval_brd_node", RunnableLambda(brd_feedback_node))
    workflow.add_node("human_approval_tech_stack_node", RunnableLambda(tech_stack_feedback_node))
    workflow.add_node("human_approval_system_design_node", RunnableLambda(system_design_feedback_node))
    workflow.add_node("human_approval_plan_node", RunnableLambda(planning_feedback_node))
    workflow.add_node("human_approval_code_node", RunnableLambda(code_generation_feedback_node))

    # --- Generic State Management Nodes ---
    workflow.add_node("mark_stage_complete_node", async_mark_stage_complete_node)

    # === Define Workflow Edges ===
    workflow.set_entry_point("initialize_state_node")
    workflow.add_edge("initialize_state_node", "brd_analysis_node")

    # --- BRD Analysis Approval Gate ---
    workflow.add_edge("brd_analysis_node", "human_approval_brd_node")
    workflow.add_conditional_edges("human_approval_brd_node", async_decide_after_human, {
        "proceed": "tech_stack_recommendation_node",
        "revise": "brd_analysis_node",
        "end": END
    })

    # --- Tech Stack Approval Gate ---
    workflow.add_edge("tech_stack_recommendation_node", "human_approval_tech_stack_node")
    workflow.add_conditional_edges("human_approval_tech_stack_node", async_decide_after_human, {
        "proceed": "system_design_node",
        "revise": "tech_stack_recommendation_node",
        "end": END
    })

    # --- System Design Approval Gate ---
    workflow.add_edge("system_design_node", "human_approval_system_design_node")
    workflow.add_conditional_edges("human_approval_system_design_node", async_decide_after_human, {
        "proceed": "planning_node",
        "revise": "system_design_node",
        "end": END
    })

    # --- Implementation Plan Approval Gate ---
    workflow.add_edge("planning_node", "human_approval_plan_node")
    workflow.add_conditional_edges(
        "human_approval_plan_node",
        async_decide_after_human,
        {
            "proceed": "work_item_iterator_node", # If approved, start the development loop
            "revise": "planning_node",           # If revision is needed, go back to planning
            "end": END
        }
    )

    # 🚀 COMMAND API: Main Development Loop
    # The Command API iterator directly routes to the appropriate node
    # NO conditional edges needed - the Command specifies the next node directly!
    # This completely bypasses the state propagation timing issues.

    # The core self-correction loop: Generate -> Quality -> Test -> Integrate
    workflow.add_edge("code_generation_node", "code_quality_node")

    # After static code quality analysis, decide to proceed or revise.
    workflow.add_conditional_edges("code_quality_node", async_decide_on_code_quality, {
        "approve": "test_execution_node",  # If quality is good, run unit tests
        "revise": "increment_revision_node"   # If not, increment revision and regenerate
    })

    # After running unit tests, decide to proceed or revise.
    workflow.add_conditional_edges("test_execution_node", async_decide_on_test_results, {
        "approve": "async_integration_node", # If tests pass, proceed to integration
        "revise": "increment_revision_node"    # If tests fail, increment and regenerate
    })

    # After integration, check results and proceed to mark the work item as complete.
    workflow.add_conditional_edges("async_integration_node", async_decide_on_integration_test_results, {
        "proceed": "phase_completion_node",
        "proceed_with_warning": "phase_completion_node" # For now, both outcomes lead to completion
    })
    
    # FIXED: After a revision is triggered, check circuit breaker before continuing
    workflow.add_conditional_edges("increment_revision_node", async_check_circuit_breaker, {
        "continue": "code_generation_node",  # Normal case: continue with revision
        "stop": "finalize_node"             # Circuit breaker triggered: stop workflow
    })

    # 🚀 COMMAND API: After a work item is successfully completed, 
    # loop back to the iterator which will use Command API to route directly
    workflow.add_edge("phase_completion_node", "work_item_iterator_node")

    # Finalize the workflow once complete
    workflow.add_edge("finalize_node", END)

    return workflow

async def create_async_phased_workflow() -> StateGraph:
    """
    Create a phased development workflow with human-in-the-loop approval gates.
    This is the legacy version - prefer create_async_phased_workflow_command_api() for new implementations.
    """
    workflow = StateGraph(AgentState)

    # Add state initialization
    workflow.add_node("initialize_state_node", async_initialize_workflow_state)

    # --- Agent Nodes ---
    workflow.add_node("brd_analysis_node", async_brd_analysis_node)
    workflow.add_node("tech_stack_recommendation_node", async_tech_stack_recommendation_node)
    workflow.add_node("system_design_node", async_system_design_node)
    workflow.add_node("planning_node", async_planning_node)
    workflow.add_node("code_generation_node", async_code_generation_dispatcher_node)
    workflow.add_node("work_item_iterator_node", async_work_item_iterator_node)
    workflow.add_node("test_execution_node", async_test_execution_node)
    workflow.add_node("phase_completion_node", async_phase_completion_node)
    workflow.add_node("increment_revision_node", async_increment_revision_count_node)
    workflow.add_node("finalize_node", async_finalize_workflow)
    workflow.add_node("code_quality_node", async_code_quality_analysis_node)
    workflow.add_node("async_integration_node", async_integration_node)

    # --- Human Approval Nodes (created by a generic factory) ---
    brd_feedback_node = async_make_human_feedback_node(StateFields.REQUIREMENTS_ANALYSIS, "BRD Analysis")
    tech_stack_feedback_node = async_make_human_feedback_node(StateFields.TECH_STACK_RECOMMENDATION, "Tech Stack Recommendation")
    system_design_feedback_node = async_make_human_feedback_node(StateFields.SYSTEM_DESIGN, "System Design")
    planning_feedback_node = async_make_human_feedback_node(StateFields.IMPLEMENTATION_PLAN, "Implementation Plan")
    code_generation_feedback_node = async_make_human_feedback_node(StateFields.CODE_GENERATION_OUTPUT, "Code Generation")

    workflow.add_node("human_approval_brd_node", RunnableLambda(brd_feedback_node))
    workflow.add_node("human_approval_tech_stack_node", RunnableLambda(tech_stack_feedback_node))
    workflow.add_node("human_approval_system_design_node", RunnableLambda(system_design_feedback_node))
    workflow.add_node("human_approval_plan_node", RunnableLambda(planning_feedback_node))
    workflow.add_node("human_approval_code_node", RunnableLambda(code_generation_feedback_node))

    # --- Generic State Management Nodes ---
    workflow.add_node("mark_stage_complete_node", async_mark_stage_complete_node)

    # === Define Workflow Edges ===
    workflow.set_entry_point("initialize_state_node")
    workflow.add_edge("initialize_state_node", "brd_analysis_node")

    # --- BRD Analysis Approval Gate ---
    workflow.add_edge("brd_analysis_node", "human_approval_brd_node")
    workflow.add_conditional_edges("human_approval_brd_node", async_decide_after_human, {
        "proceed": "tech_stack_recommendation_node",
        "revise": "brd_analysis_node",
        "end": END
    })

    # --- Tech Stack Approval Gate ---
    workflow.add_edge("tech_stack_recommendation_node", "human_approval_tech_stack_node")
    workflow.add_conditional_edges("human_approval_tech_stack_node", async_decide_after_human, {
        "proceed": "system_design_node",
        "revise": "tech_stack_recommendation_node",
        "end": END
    })

    # --- System Design Approval Gate ---
    workflow.add_edge("system_design_node", "human_approval_system_design_node")
    workflow.add_conditional_edges("human_approval_system_design_node", async_decide_after_human, {
        "proceed": "planning_node",
        "revise": "system_design_node",
        "end": END
    })

    # --- Implementation Plan Approval Gate ---
    workflow.add_edge("planning_node", "human_approval_plan_node")
    workflow.add_conditional_edges(
        "human_approval_plan_node",
        async_decide_after_human,
        {
            "proceed": "work_item_iterator_node", # If approved, start the development loop
            "revise": "planning_node",           # If revision is needed, go back to planning
            "end": END
        }
    )

    # --- Main Development Loop (Legacy approach with conditional edges) ---
    # Import the sync routing function for compatibility
    from async_graph_nodes import sync_route_after_work_item_iterator
    
    workflow.add_conditional_edges(
        "work_item_iterator_node",
        sync_route_after_work_item_iterator,
        {
            "proceed": "code_generation_node",
            "workflow_complete": "finalize_node"
        }
    )

    # The core self-correction loop: Generate -> Quality -> Test -> Integrate
    workflow.add_edge("code_generation_node", "code_quality_node")

    # After static code quality analysis, decide to proceed or revise.
    workflow.add_conditional_edges("code_quality_node", async_decide_on_code_quality, {
        "approve": "test_execution_node",  # If quality is good, run unit tests
        "revise": "increment_revision_node"   # If not, increment revision and regenerate
    })

    # After running unit tests, decide to proceed or revise.
    workflow.add_conditional_edges("test_execution_node", async_decide_on_test_results, {
        "approve": "async_integration_node", # If tests pass, proceed to integration
        "revise": "increment_revision_node"    # If tests fail, increment and regenerate
    })

    # After integration, check results and proceed to mark the work item as complete.
    workflow.add_conditional_edges("async_integration_node", async_decide_on_integration_test_results, {
        "proceed": "phase_completion_node",
        "proceed_with_warning": "phase_completion_node" # For now, both outcomes lead to completion
    })
    
    # FIXED: After a revision is triggered, check circuit breaker before continuing
    workflow.add_conditional_edges("increment_revision_node", async_check_circuit_breaker, {
        "continue": "code_generation_node",  # Normal case: continue with revision
        "stop": "finalize_node"             # Circuit breaker triggered: stop workflow
    })

    # After a work item is successfully completed, loop back to the iterator for the next one.
    workflow.add_edge("phase_completion_node", "work_item_iterator_node")

    # Finalize the workflow once complete
    workflow.add_edge("finalize_node", END)

    return workflow

async def get_async_workflow(workflow_type: str) -> StateGraph:
    """
    Factory function to get a specific async workflow graph.
    Now uses the FIXED workflow that solves state propagation issues.
    """
    if workflow_type in ["phased", "resumable", "iterative", "basic", "modular", "implementation", "enhanced"]:
        # 🚀 Use the FIXED workflow that solves state propagation issues
        from fixed_workflow import get_fixed_workflow
        return await get_fixed_workflow()
    elif workflow_type == "state_driven":
        # Alternative: State-driven approach
        from async_graph_state_driven import create_state_driven_workflow
        return await create_state_driven_workflow()
    elif workflow_type == "command_api":
        # Keep Command API version for debugging/comparison
        return await create_async_phased_workflow_command_api()
    elif workflow_type == "legacy":
        # Legacy version for compatibility
        return await create_async_phased_workflow()
    elif workflow_type == "simple":
        # Keep the simple workflow for comparison
        from async_graph_simple import create_simple_sequential_workflow
        return await create_simple_sequential_workflow()
    else:
        raise ValueError(f"Unknown workflow type: {workflow_type}")

# Deprecated initialization function for consistency with sync version
def _initialize_async_workflow_components(workflow: StateGraph):
    """
    DEPRECATED: This function is no longer used and will be removed in a future version.
    
    Components are now initialized externally in main.py or serve_chain.py and passed
    via config["configurable"] to workflow.invoke().
    """
    import warnings
    warnings.warn(
        "The _initialize_async_workflow_components function is deprecated and will be removed. "
        "Components should be initialized externally and passed via config['configurable'].",
        DeprecationWarning,
        stacklevel=2
    )
    # Empty implementation - components should be initialized externally
    pass

# New: Conditional edge for human approval
async def check_human_approval(state: AgentState) -> str:
    """Routes based on the human_decision field."""
    decision = state.get("human_decision", "reject")
    if decision == "approve":
        return "continue"
    else:
        # For now, we'll just end the workflow on rejection or edit.
        # Later, we can add more complex logic (e.g., go to a revision node).
        return "end"