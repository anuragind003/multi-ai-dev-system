"""
LangGraph Workflow Definition for Multi-AI Development System.
ENHANCED: Integrated with AdvancedWorkflowConfig and simplified node structure.
"""

from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from agent_state import AgentState, StateFields
from graph_nodes import (
    brd_analysis_node,
    tech_stack_recommendation_node,
    system_design_node,
    planning_node,
    code_generation_node,
    test_case_generation_node,
    code_quality_analysis_node,
    test_validation_node,
    finalize_workflow,
    should_retry_code_generation,
    should_retry_tests,
    check_workflow_completion
)
import monitoring

def create_basic_workflow() -> StateGraph:
    """Create a basic linear workflow with each agent executed once."""
    
    from agent_state import AgentState
    
    # Create workflow
    workflow = StateGraph(AgentState)
    
    # Add nodes - Use distinct names with _step suffix
    workflow.add_node("brd_analysis_step", brd_analysis_node)
    workflow.add_node("tech_stack_recommendation_step", tech_stack_recommendation_node)  # FIXED
    workflow.add_node("system_design_step", system_design_node)  # FIXED
    workflow.add_node("planning_step", planning_node)  # FIXED
    workflow.add_node("code_generation_step", code_generation_node)  # FIXED
    workflow.add_node("test_case_generation_step", test_case_generation_node)  # FIXED
    workflow.add_node("code_quality_analysis_step", code_quality_analysis_node)  # FIXED
    workflow.add_node("test_validation_step", test_validation_node)  # FIXED
    workflow.add_node("finalize_step", finalize_workflow)  # FIXED
    
    # Define linear flow - update to use new node names
    workflow.set_entry_point("brd_analysis_step")
    workflow.add_edge("brd_analysis_step", "tech_stack_recommendation_step")
    workflow.add_edge("tech_stack_recommendation_step", "system_design_step")
    workflow.add_edge("system_design_step", "planning_step")
    workflow.add_edge("planning_step", "code_generation_step")
    workflow.add_edge("code_generation_step", "test_case_generation_step")
    workflow.add_edge("test_case_generation_step", "code_quality_analysis_step")
    workflow.add_edge("code_quality_analysis_step", "test_validation_step")
    workflow.add_edge("test_validation_step", "finalize_step")
    workflow.add_edge("finalize_step", END)
    
    return workflow

def create_iterative_workflow() -> StateGraph:
    """Create an iterative workflow with retry capabilities for code and tests."""
    from agent_state import AgentState

    workflow = StateGraph(AgentState)

    # Add all nodes
    workflow.add_node("brd_analysis_step", brd_analysis_node)
    workflow.add_node("tech_stack_recommendation_step", tech_stack_recommendation_node)
    workflow.add_node("system_design_step", system_design_node)
    workflow.add_node("planning_step", planning_node)
    workflow.add_node("code_generation_step", code_generation_node)
    workflow.add_node("code_quality_analysis_step", code_quality_analysis_node)
    workflow.add_node("test_case_generation_step", test_case_generation_node)
    workflow.add_node("test_validation_step", test_validation_node)
    workflow.add_node("finalize_step", finalize_workflow)

    workflow.set_entry_point("brd_analysis_step")

    # Core workflow path
    workflow.add_edge("brd_analysis_step", "tech_stack_recommendation_step")
    workflow.add_edge("tech_stack_recommendation_step", "system_design_step")
    workflow.add_edge("system_design_step", "planning_step")
    workflow.add_edge("planning_step", "code_generation_step")
    workflow.add_edge("code_generation_step", "code_quality_analysis_step")  # Quality check after code gen

    # Conditional path for code generation retry
    workflow.add_conditional_edges(
        "code_quality_analysis_step",  # Source node is quality analysis
        should_retry_code_generation,
        {
            "retry_code_generation": "code_generation_step",  # Make sure this key matches
            "continue": "test_case_generation_step"          # Continue workflow
        }
    )

    # Test generation and validation path
    workflow.add_edge("test_case_generation_step", "test_validation_step")
    
    # Conditional path for test validation retry
    workflow.add_conditional_edges(
        "test_validation_step",
        should_retry_tests,
        {
            "retry_tests": "test_case_generation_step",
            "continue": "finalize_step"
        }
    )
    
    workflow.add_edge("finalize_step", END)

    return workflow

def create_modular_workflow() -> StateGraph:
    """
    Create a modular workflow with parallel execution capabilities
    and enhanced error recovery.
    """
    
    from agent_state import AgentState
    
    # Create workflow
    workflow = StateGraph(AgentState)
    
    # Define module groups with distinct names
    # Requirements phase
    workflow.add_node("requirements_module_step", requirements_module)  # FIXED
    
    # Design phase
    workflow.add_node("design_module_step", design_module)  # FIXED
    
    # Implementation phase
    workflow.add_node("implementation_module_step", implementation_module)  # FIXED
    
    # Quality phase
    workflow.add_node("quality_module_step", quality_module)  # FIXED
    
    # Finalization
    workflow.add_node("finalize_step", finalize_workflow)  # FIXED
    
    # Set up the flow
    workflow.set_entry_point("requirements_module_step")
    
    # Linear flow between major phases
    workflow.add_edge("requirements_module_step", "design_module_step")
    workflow.add_edge("design_module_step", "implementation_module_step")
    workflow.add_edge("implementation_module_step", "quality_module_step")
    
    # Add conditional edge from quality to implementation for iterations
    workflow.add_conditional_edges(
        "quality_module_step",
        should_iterate_implementation,
        {
            "iterate": "implementation_module_step",
            "finalize": "finalize_step"
        }
    )
    
    workflow.add_edge("finalize_step", END)
    
    return workflow

def create_resumable_workflow() -> StateGraph:
    """
    Create a workflow that can be interrupted and resumed.
    Based on the iterative workflow with checkpointing.
    """
    # Get base iterative workflow
    workflow = create_iterative_workflow()
    
    # Add checkpointing logic to each step (via conditional edges or node wrappers)
    # This could be more complex in a real implementation
    
    return workflow

def get_workflow(workflow_type: str = "iterative") -> StateGraph:
    """
    ENHANCED: Factory function to get the specified workflow type with clean compilation logic.
    
    Args:
        workflow_type: Type of workflow ("basic", "iterative", "modular", "resumable")
        
    Returns:
        StateGraph: Compiled workflow graph
        
    Raises:
        ValueError: If workflow_type is not supported
    """
    
    workflow_factories = {
        "basic": create_basic_workflow,
        "iterative": create_iterative_workflow,
        "modular": create_modular_workflow,
        "resumable": create_resumable_workflow
    }
    
    if workflow_type not in workflow_factories:
        available_types = ", ".join(workflow_factories.keys())
        raise ValueError(f"Unsupported workflow type: {workflow_type}. Available types: {available_types}")
    
    try:
        monitoring.log_agent_activity("Workflow Builder", f"Building {workflow_type} workflow", "START")
        
        # Create the workflow (all factories return uncompiled StateGraph)
        workflow_graph = workflow_factories[workflow_type]()
        
        # FIXED: Clean compilation logic - single compilation point
        if workflow_type == "resumable":
            # Compile with memory saver for resumable workflows
            memory = MemorySaver()
            compiled_workflow = workflow_graph.compile(checkpointer=memory)
            monitoring.log_agent_activity("Workflow Builder", "Added checkpoint support for resumable workflow", "INFO")
        else:
            # Standard compilation for other workflow types
            compiled_workflow = workflow_graph.compile()
        
        monitoring.log_agent_activity("Workflow Builder", f"Successfully built {workflow_type} workflow", "SUCCESS")
        
        return compiled_workflow
        
    except Exception as e:
        monitoring.log_agent_activity("Workflow Builder", f"Failed to build {workflow_type} workflow: {e}", "ERROR")
        raise

def validate_workflow_configuration(workflow_type: str, config: Dict[str, Any]) -> List[str]:
    """
    NEW: Validate workflow configuration and return any issues.
    
    Args:
        workflow_type: Type of workflow to validate
        config: Configuration dictionary
        
    Returns:
        List[str]: List of validation issues (empty if valid)
    """
    issues = []
    
    # Check required components in config
    required_components = ["llm", "memory"]
    optional_components = ["rag_manager", "code_execution_tool", "run_output_dir"]
    
    configurable = config.get("configurable", {})
    
    for component in required_components:
        if component not in configurable or configurable[component] is None:
            issues.append(f"Required component '{component}' missing or None in workflow config")
    
    # Workflow-specific validations
    if workflow_type in ["iterative", "modular"] and "code_execution_tool" not in configurable:
        issues.append(f"Workflow type '{workflow_type}' requires 'code_execution_tool' for quality analysis")
    
    if workflow_type == "resumable" and "memory" not in configurable:
        issues.append("Resumable workflow requires memory configuration for checkpoints")
    
    return issues