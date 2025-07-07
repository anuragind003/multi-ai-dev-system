"""
LangGraph Workflow Definition for Multi-AI Development System.
Implements consolidated Generate → Review → Revise cycle with optimized agent architecture.
"""

from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.runnables import RunnableLambda  # Add this import
import logging
import warnings

from agent_state import AgentState, StateFields
from graph_nodes import (
    # Core planning nodes
    brd_analysis_node,
    tech_stack_recommendation_node,
    system_design_node,
    planning_node,
    
    # --- Add Human-in-the-Loop Imports ---
    human_approval_node,
    human_approval_tech_stack_node,
    human_approval_system_design_node,
    human_approval_plan_node,
    decide_after_brd_approval,
    should_request_brd_approval,
    decide_after_tech_stack_approval,
    decide_after_system_design_approval,
    decide_after_plan_approval,
    
    # Phase control nodes
    phase_completion_node,
    increment_revision_count_node,
    
    # Consolidated generator and quality nodes
    code_generation_dispatcher_node,
    code_quality_analysis_node,
    
    # Testing and finalization
    finalize_workflow,
    
    # Decision functions
    has_next_phase,
    decide_on_code_quality,
    
    # Initialization
    initialize_workflow_state,
    
    # Legacy nodes (kept for backward compatibility)
    project_analyzer_node,
    timeline_estimator_node,
    risk_assessor_node,
    plan_compiler_node,
    architecture_generator_node,
    database_generator_node,
    backend_generator_node,
    frontend_generator_node,
    integration_generator_node,
    code_optimizer_node,
    test_case_generation_node,
    test_validation_node,
    architecture_quality_node,
    database_quality_node,
    backend_quality_node,
    frontend_quality_node,
    integration_quality_node,
    
    # Legacy modules (kept for backward compatibility)
    requirements_module,
    design_module,
    planning_module,
    implementation_module,
    testing_module,
    
    # Legacy decision functions
    decide_on_architecture_quality,
    decide_on_database_quality,
    decide_on_backend_quality,
    decide_on_frontend_quality,
    decide_on_integration_quality,
    check_workflow_completion,
    should_retry_tests,
    should_iterate_implementation,
    determine_phase_generators,
    
    # Helper functions
    checkpoint_state,
    phase_dispatcher_node,
    work_item_iterator_node,
    test_execution_node,
    decide_on_test_results
)
import monitoring
from platform_config import get_platform_client
from enhanced_memory_manager import get_project_memory
from enhanced_langgraph_checkpointer import EnhancedMemoryCheckpointer

logger = logging.getLogger(__name__)

def create_phased_workflow() -> StateGraph:
    """
    Create the streamlined phased workflow with a generic
    'Generate -> Review -> Revise' cycle.
    """
    workflow = StateGraph(AgentState)

    # --- 1. Define Nodes with Descriptions --- (added "_node" suffix to avoid state key conflicts)
    workflow.add_node(
        "initialize_state_node", 
        RunnableLambda(initialize_workflow_state).with_config(
            tags=["Initialization"], 
            metadata={"description": "Initializes the state dictionary with default values."}
        )
    )
    workflow.add_node(
        "brd_analysis_node", 
        RunnableLambda(brd_analysis_node).with_config(
            tags=["Planning", "Analysis"], 
            metadata={"description": "Analyzes the Business Requirements Document (BRD) to extract structured requirements."}
        )
    )
    workflow.add_node(
        "human_approval_brd_node",
        RunnableLambda(human_approval_node).with_config(
            tags=["Human Feedback"],
            metadata={"description": "Pauses the workflow to wait for human approval of the BRD analysis."}
        )
    )
    workflow.add_node(
        "tech_stack_node", 
        RunnableLambda(tech_stack_recommendation_node).with_config(
            tags=["Planning", "Architecture"], 
            metadata={"description": "Recommends an optimal technology stack based on the analyzed requirements."}
        )
    )
    workflow.add_node(
        "human_approval_tech_stack_node",
        RunnableLambda(human_approval_tech_stack_node).with_config(
            tags=["Human Feedback"],
            metadata={"description": "Pauses the workflow to wait for human approval of the tech stack recommendation."}
        )
    )
    workflow.add_node(
        "system_design_node", 
        RunnableLambda(system_design_node).with_config(
            tags=["Planning", "Architecture"], 
            metadata={"description": "Creates a high-level system design and architecture."}
        )
    )
    workflow.add_node(
        "human_approval_system_design_node",
        RunnableLambda(human_approval_system_design_node).with_config(
            tags=["Human Feedback"],
            metadata={"description": "Pauses the workflow to wait for human approval of the system design."}
        )
    )
    workflow.add_node(
        "planning_node", 
        RunnableLambda(planning_node).with_config(
            tags=["Planning"],
            metadata={"description": "Compiles all analyses into a detailed, phased implementation plan."}
        )
    )
    workflow.add_node(
        "human_approval_plan_node",
        RunnableLambda(human_approval_plan_node).with_config(
            tags=["Human Feedback"],
            metadata={"description": "Pauses the workflow to wait for human approval of the implementation plan."}
        )
    )
    workflow.add_node(
        "work_item_iterator_node", 
        RunnableLambda(work_item_iterator_node).with_config(
            tags=["Control Flow"],
            metadata={"description": "Iterates through the work item backlog to process the next pending item."}
        )
    )
    workflow.add_node(
        "code_generation_dispatcher_node",
        RunnableLambda(code_generation_dispatcher_node).with_config(
            tags=["Code Generation"],
            metadata={"description": "Dispatches the current work item to the appropriate specialized code generation agent."}
        )
    )
    workflow.add_node(
        "test_execution_node",
        RunnableLambda(test_execution_node).with_config(
            tags=["Testing"],
            metadata={"description": "Executes the unit tests for the generated code to validate correctness."}
        )
    )
    workflow.add_node(
        "phase_completion_node",
        RunnableLambda(phase_completion_node).with_config(
            tags=["Control Flow"],
            metadata={"description": "Marks the current work item as complete and records metrics."}
        )
    )
    workflow.add_node(
        "increment_revision_count_node",
        RunnableLambda(increment_revision_count_node).with_config(
            tags=["Control Flow", "Revision"],
            metadata={"description": "Increments the revision counter for the current phase before retrying generation."}
        )
    )
    workflow.add_node(
        "finalize_node", 
        RunnableLambda(finalize_workflow).with_config(
            tags=["Finalization"],
            metadata={"description": "Compiles final results, generates a summary report, and concludes the workflow."}
        )
    )

    # --- 2. Define Edges ---
    workflow.set_entry_point("initialize_state_node")
    workflow.add_edge("initialize_state_node", "brd_analysis_node")
    
    # workflow.add_edge("brd_analysis_node", "human_approval_brd_node")
    workflow.add_conditional_edges(
        "brd_analysis_node",
        should_request_brd_approval,
        {
            "request_approval": "human_approval_brd_node"
        }
    )

    # --- 3. Define Interrupt Points ---
    workflow.add_interrupt_point("human_approval_brd_node")
    workflow.add_interrupt_point("human_approval_tech_stack_node")
    
    # --- 4. Define Conditional Edges ---
    workflow.add_conditional_edges(
        "human_approval_brd_node",
        decide_after_brd_approval,
        {
            "proceed": "tech_stack_node",
            "revise": "brd_analysis_node",
            "end": END
        }
    )
    workflow.add_conditional_edges(
        "human_approval_tech_stack_node",
        decide_after_tech_stack_approval,
        {
            "proceed": "system_design_node",
            "revise": "tech_stack_node",
            "end": END
        }
    )

    # --- 5. Continue the Main Workflow ---
    workflow.add_edge("tech_stack_node", "human_approval_tech_stack_node")
    workflow.add_edge("system_design_node", "human_approval_system_design_node")
    
    workflow.add_conditional_edges(
        "human_approval_system_design_node",
        decide_after_system_design_approval,
        {
            "proceed": "planning_node",
            "revise": "system_design_node",
            "end": END,
        },
    )

    workflow.add_edge("planning_node", "human_approval_plan_node")

    workflow.add_conditional_edges(
        "human_approval_plan_node",
        decide_after_plan_approval,
        {
            "proceed": "work_item_iterator_node",
            "revise": "planning_node",
            "end": END,
        },
    )
    # --- END OF ADDED STEPS ---

    # This is the main implementation loop
    workflow.add_conditional_edges(
        "work_item_iterator_node",
        has_next_phase,
        {
            StateFields.NEXT_PHASE: "code_generation_dispatcher_node",
            StateFields.WORKFLOW_COMPLETE: "finalize_workflow"
        }
    )
    
    # After generation, run quality analysis
    workflow.add_edge("code_generation_dispatcher_node", "code_quality_analysis_node")

    # After quality analysis, decide whether to test or revise
    workflow.add_conditional_edges(
        "code_quality_analysis_node",
        decide_on_code_quality,
        {
            "proceed_to_testing": "test_execution_node",
            "revise": "increment_revision_count_node"
        }
    )

    # After testing, decide whether to approve or revise
    workflow.add_conditional_edges(
        "test_execution_node",
        decide_on_test_results,
        {
            StateFields.APPROVE: "phase_completion_node",
            StateFields.REVISE: "increment_revision_count_node"
        }
    )
    
    # The self-correction loop (for both quality and testing failures)
    workflow.add_edge("increment_revision_count_node", "code_generation_dispatcher_node")
    
    # After a phase (work item) is completed, go back to the iterator
    workflow.add_edge("phase_completion_node", "work_item_iterator_node")

    # Finalize the workflow once the loop is complete
    workflow.add_edge("finalize_workflow", END)

    return workflow

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

# Create legacy workflows using our refactored nodes where possible

def create_basic_workflow() -> StateGraph:
    """Create a basic linear workflow with each agent executed once."""
    
    warnings.warn(
        "The basic workflow is deprecated and will be removed in a future version. "
        "Please use 'phased' workflow for better results.",
        DeprecationWarning,
        stacklevel=2
    )
    
    workflow = StateGraph(AgentState)
    
    # Add state initialization
    workflow.add_node("initialize_state_node", initialize_workflow_state)
    
    # Add nodes - Use consistent _node suffix
    workflow.add_node("brd_analysis_node", brd_analysis_node)
    workflow.add_node("tech_stack_node", tech_stack_recommendation_node)
    workflow.add_node("system_design_node", system_design_node)
    workflow.add_node("planning_node", planning_node)
    
    # Add consolidated code generation node using our dispatcher
    workflow.add_node("code_generation_node", code_generation_dispatcher_node)
    
    # Add consolidated quality review node
    workflow.add_node("quality_review_node", code_quality_analysis_node)
    
    # Testing and finalization
    workflow.add_node("finalize_node", finalize_workflow)
    
    # Define linear flow
    workflow.set_entry_point("initialize_state_node")
    
    # Connect initialization to first step
    workflow.add_edge("initialize_state_node", "brd_analysis_node")
    workflow.add_edge("brd_analysis_node", "tech_stack_node")
    workflow.add_edge("tech_stack_node", "system_design_node")
    workflow.add_edge("system_design_node", "planning_node")
    workflow.add_edge("planning_node", "code_generation_node")
    workflow.add_edge("code_generation_node", "quality_review_node")
    workflow.add_edge("quality_review_node", "test_execution_node")
    workflow.add_edge("test_execution_node", "finalize_node")
    workflow.add_edge("finalize_node", END)
    
    return workflow

def create_iterative_workflow(config: Dict[str, Any] = None) -> StateGraph:
    """Create workflow with feedback loops for iteration."""
    
    warnings.warn(
        "The iterative workflow is deprecated and will be removed in a future version. "
        "Please use 'phased' workflow for better results.",
        DeprecationWarning,
        stacklevel=2
    )
    
    workflow = StateGraph(AgentState)
    
    # Add state initialization
    workflow.add_node("initialize_state_node", initialize_workflow_state)
    
    # Add all nodes with specialized agents
    workflow.add_node("brd_analysis_node", brd_analysis_node)
    workflow.add_node("tech_stack_node", tech_stack_recommendation_node)
    workflow.add_node("system_design_node", system_design_node)
    
    # Use planning node
    workflow.add_node("planning_node", planning_node)
    
    # Complete sequence of specialized code generation nodes
    workflow.add_node("architecture_generation_node", architecture_generator_node)
    workflow.add_node("database_generation_node", database_generator_node)
    workflow.add_node("backend_generation_node", backend_generator_node)
    workflow.add_node("frontend_generation_node", frontend_generator_node)
    workflow.add_node("integration_generation_node", integration_generator_node)
    workflow.add_node("code_optimizer_node", code_optimizer_node)
    
    # Quality and testing nodes
    workflow.add_node("quality_review_node", code_quality_analysis_node)
    workflow.add_node("finalize_node", finalize_workflow)

    # Define flow
    workflow.set_entry_point("initialize_state_node")

    # Core workflow path
    workflow.add_edge("initialize_state_node", "brd_analysis_node")
    workflow.add_edge("brd_analysis_node", "tech_stack_node")
    workflow.add_edge("tech_stack_node", "system_design_node")
    workflow.add_edge("system_design_node", "planning_node")
    
    # Code generation flow with full sequence of specialized generators
    workflow.add_edge("planning_node", "architecture_generation_node")
    workflow.add_edge("architecture_generation_node", "database_generation_node")
    workflow.add_edge("database_generation_node", "backend_generation_node")
    workflow.add_edge("backend_generation_node", "frontend_generation_node")
    workflow.add_edge("frontend_generation_node", "integration_generation_node")
    workflow.add_edge("integration_generation_node", "code_optimizer_node")
    workflow.add_edge("code_optimizer_node", "quality_review_node")
    
    # Conditional path for testing - retry entire implementation if needed
    workflow.add_conditional_edges(
        "quality_review_node",
        decide_on_code_quality,
        {
            StateFields.REVISE: "architecture_generation_node",
            StateFields.APPROVE: "test_execution_node"
        }
    )
    
    workflow.add_edge("test_execution_node", "finalize_node")
    workflow.add_edge("finalize_node", END)

    return workflow

def create_modular_workflow() -> StateGraph:
    """
    Create a modular workflow with parallel execution capabilities
    and enhanced error recovery.
    """
    
    warnings.warn(
        "The modular workflow is deprecated and will be removed in a future version. "
        "Please use 'phased' workflow for better results.",
        DeprecationWarning,
        stacklevel=2
    )
    
    workflow = StateGraph(AgentState)
    
    # Add state initialization
    workflow.add_node("initialize_state_node", initialize_workflow_state)
    
    # Define module groups with distinct names
    workflow.add_node("requirements_module_node", requirements_module)
    workflow.add_node("design_module_node", design_module)
    workflow.add_node("implementation_module_node", implementation_module)
    workflow.add_node("quality_module_node", code_quality_analysis_node)
    workflow.add_node("planning_node", planning_node)
    workflow.add_node("finalize_node", finalize_workflow)
    
    # Set entry point to initialization
    workflow.set_entry_point("initialize_state_node")
    
    # Connect initialization to first module
    workflow.add_edge("initialize_state_node", "requirements_module_node")
    
    # Linear flow between major phases
    workflow.add_edge("requirements_module_node", "design_module_node")
    workflow.add_edge("design_module_node", "planning_node")
    workflow.add_edge("planning_node", "implementation_module_node")
    workflow.add_edge("implementation_module_node", "quality_module_node")
    
    # Add conditional edge from quality to implementation for iterations
    workflow.add_conditional_edges(
        "quality_module_node",
        decide_on_code_quality,
        {
            StateFields.REVISE: "implementation_module_node",
            StateFields.APPROVE: "test_execution_node"
        }
    )
    
    workflow.add_edge("test_execution_node", "finalize_node")
    workflow.add_edge("finalize_node", END)
    
    return workflow

def create_resumable_workflow(config: Dict[str, Any] = None) -> StateGraph:
    """
    Create a workflow that can be interrupted and resumed using Enhanced Memory Manager.
    Based on the phased workflow with persistent checkpointing.
    """
    
    # Create phased workflow as base
    workflow = create_phased_workflow()
    
    # Use enhanced memory manager instead of basic MemorySaver
    run_dir = config.get("run_dir") if config else None
    memory_manager = get_project_memory(run_dir)
    
    # Create enhanced checkpointer
    enhanced_checkpointer = EnhancedMemoryCheckpointer(
        memory_manager=memory_manager,
        backend_type="hybrid",  # Fast cache + persistent storage
        persistent_dir=run_dir
    )
    
    logger.info("Created resumable workflow with Enhanced Memory checkpointing")
    
    return workflow

def create_implementation_workflow() -> StateGraph:
    """Create a workflow specifically for code implementation with quality feedback loops."""
    
    warnings.warn(
        "The implementation workflow is deprecated and will be removed in a future version. "
        "Please use 'phased' workflow for better results.",
        DeprecationWarning,
        stacklevel=2
    )
    
    workflow = StateGraph(AgentState)
    
    # Add state initialization
    workflow.add_node("initialize_state_node", initialize_workflow_state)
    
    # Add code generation nodes
    workflow.add_node("architecture_generation_node", architecture_generator_node)
    workflow.add_node("architecture_quality_node", architecture_quality_node)
    workflow.add_node("database_generation_node", database_generator_node)
    workflow.add_node("database_quality_node", database_quality_node)
    workflow.add_node("backend_generation_node", backend_generator_node)
    workflow.add_node("backend_quality_node", backend_quality_node)
    workflow.add_node("frontend_generation_node", frontend_generator_node)
    workflow.add_node("frontend_quality_node", frontend_quality_node)
    workflow.add_node("integration_generation_node", integration_generator_node)
    workflow.add_node("integration_quality_node", integration_quality_node)
    workflow.add_node("code_optimization_node", code_optimizer_node)
    
    # Set entry point to initialization
    workflow.set_entry_point("initialize_state_node")
    
    # Connect initialization to first step
    workflow.add_edge("initialize_state_node", "architecture_generation_node")
    
    # Architecture feedback loop
    workflow.add_edge("architecture_generation_node", "architecture_quality_node")
    workflow.add_conditional_edges(
        "architecture_quality_node", 
        decide_on_architecture_quality,
        {
            "approve": "database_generation_node",
            "revise": "architecture_generation_node"
        }
    )
    
    # Database feedback loop
    workflow.add_edge("database_generation_node", "database_quality_node")
    workflow.add_conditional_edges(
        "database_quality_node",
        decide_on_database_quality,
        {
            "approve": "backend_generation_node",
            "revise": "database_generation_node" 
        }
    )
    
    # Backend feedback loop
    workflow.add_edge("backend_generation_node", "backend_quality_node")
    workflow.add_conditional_edges(
        "backend_quality_node",
        decide_on_backend_quality,
        {
            "approve": "frontend_generation_node",
            "revise": "backend_generation_node"
        }
    )
    
    # Frontend feedback loop
    workflow.add_edge("frontend_generation_node", "frontend_quality_node")
    workflow.add_conditional_edges(
        "frontend_quality_node",
        decide_on_frontend_quality,
        {
            "approve": "integration_generation_node",
            "revise": "frontend_generation_node"
        }
    )
    
    # Integration feedback loop
    workflow.add_edge("integration_generation_node", "integration_quality_node")
    workflow.add_conditional_edges(
        "integration_quality_node",
        decide_on_integration_quality,
        {
            "approve": "code_optimization_node",
            "revise": "integration_generation_node"
        }
    )
    
    # Final step
    workflow.add_edge("code_optimization_node", END)
    
    return workflow

def create_enhanced_phased_workflow() -> StateGraph:
    """
    Create an enhanced phased workflow using LangGraph enforced agents.
    This version guarantees tool usage and eliminates JSON parsing errors.
    
    Note: This currently uses standard nodes since enhanced nodes are not yet implemented.
    """
    workflow = StateGraph(AgentState)

    # TODO: Implement enhanced nodes with guaranteed tool usage
    # For now, use standard nodes

    # --- 1. Define Nodes with Enhanced Agents ---
    workflow.add_node(
        "initialize_state_node", 
        RunnableLambda(initialize_workflow_state).with_config(
            tags=["Initialization"], 
            metadata={"description": "Initializes the state dictionary with default values."}
        )
    )
    workflow.add_node(
        "brd_analysis_node", 
        RunnableLambda(brd_analysis_node).with_config(
            tags=["Planning", "Analysis", "Enhanced"], 
            metadata={"description": "Standard BRD analysis with enhanced configuration."}
        )
    )
    workflow.add_node(
        "tech_stack_node", 
        RunnableLambda(tech_stack_recommendation_node).with_config(
            tags=["Planning", "Architecture", "Enhanced"], 
            metadata={"description": "Standard tech stack recommendation with enhanced configuration."}
        )
    )
    workflow.add_node(
        "system_design_node", 
        RunnableLambda(system_design_node).with_config(
            tags=["Planning", "Architecture"], 
            metadata={"description": "Creates a high-level system design and architecture."}
        )
    )
    workflow.add_node(
        "planning_node", 
        RunnableLambda(planning_node).with_config(
            tags=["Planning"], 
            metadata={"description": "Creates comprehensive implementation plan with development phases."}
        )
    )
    workflow.add_node(
        "work_item_iterator_node", 
        RunnableLambda(work_item_iterator_node).with_config(
            tags=["Control"], 
            metadata={"description": "Manages phase iteration and tracks current generation phase."}
        )
    )
    workflow.add_node(
        "code_generation_dispatcher_node", 
        RunnableLambda(code_generation_dispatcher_node).with_config(
            tags=["Code Generation"], 
            metadata={"description": "Orchestrates code generation across all modules (database, backend, frontend, etc.)."}
        )
    )
    workflow.add_node(
        "code_quality_analysis_node",
        RunnableLambda(code_quality_analysis_node).with_config(
            tags=["Code Quality"],
            metadata={"description": "Performs static analysis on generated code for quality and security."}
        )
    )
    workflow.add_node(
        "phase_completion_node", 
        RunnableLambda(phase_completion_node).with_config(
            tags=["Control"], 
            metadata={"description": "Handles phase completion and prepares for next phase or finalization."}
        )
    )
    workflow.add_node(
        "increment_revision_count_node", 
        RunnableLambda(increment_revision_count_node).with_config(
            tags=["Control"], 
            metadata={"description": "Increments revision count for iterative improvement cycles."}
        )
    )
    workflow.add_node(
        "finalize_workflow", 
        RunnableLambda(finalize_workflow).with_config(
            tags=["Finalization"], 
            metadata={"description": "Finalizes the workflow and prepares final deliverables."}
        )
    )

    # --- 2. Define Entry Point ---
    workflow.set_entry_point("initialize_state_node")

    # --- 3. Define Edges (same as standard workflow) ---
    workflow.add_edge("initialize_state_node", "brd_analysis_node")
    workflow.add_edge("brd_analysis_node", "tech_stack_node")
    workflow.add_edge("tech_stack_node", "system_design_node")
    workflow.add_edge("system_design_node", "planning_node")
    workflow.add_edge("planning_node", "work_item_iterator_node")
    workflow.add_edge("work_item_iterator_node", "code_generation_dispatcher_node")
    workflow.add_edge("code_generation_dispatcher_node", "code_quality_analysis_node")
    
    # Conditional edge for code quality
    workflow.add_conditional_edges(
        "code_quality_analysis_node",
        decide_on_code_quality,
        {
            "retry": "increment_revision_count_node",
            "continue": "phase_completion_node"
        }
    )
    
    workflow.add_edge("increment_revision_count_node", "code_generation_dispatcher_node")
    
    # Conditional edge for phase completion
    workflow.add_conditional_edges(
        "phase_completion_node",
        has_next_phase,
        {
            "continue": "work_item_iterator_node",
            "finalize": "test_execution_node"
        }
    )
    
    workflow.add_edge("test_execution_node", "finalize_workflow")
    workflow.add_edge("finalize_workflow", END)
    
    return workflow

def get_workflow(workflow_type: str = "enhanced", platform_enabled: bool = False) -> StateGraph:
    """Get a workflow graph based on type with proper configuration."""
    
    workflow_factories = {
        "basic": create_basic_workflow,
        "iterative": create_iterative_workflow,
        "phased": create_phased_workflow,
        "enhanced": create_enhanced_phased_workflow,
        "modular": create_modular_workflow,
        "resumable": create_resumable_workflow,
        "implementation": create_implementation_workflow
    }
    
    if workflow_type not in workflow_factories:
        raise ValueError(f"Unknown workflow type: {workflow_type}. Available: {list(workflow_factories.keys())}")
        
    try:
        monitoring.log_agent_activity("Workflow Builder", f"Building {workflow_type} workflow", "START")
        
        # Create the workflow
        workflow_graph = workflow_factories[workflow_type]()
        
        # --- Configure Checkpointer and Interrupts ---
        compile_kwargs = {}
        
        # Use a standard memory checkpointer for all workflows
        memory_checkpointer = MemorySaver()
        compile_kwargs["checkpointer"] = memory_checkpointer

        # Add the human approval interrupts for the workflows that use them
        if workflow_type in ["phased", "enhanced", "resumable", "modular", "iterative"]:
             compile_kwargs["interrupt_before"] = [
                 "human_approval_brd_node",
                 "human_approval_tech_stack_node", 
                 "human_approval_system_design_node",
                 "human_approval_plan_node"
             ]
             monitoring.log_agent_activity("Workflow Builder", "Enabled Human-in-the-Loop for all major phases", "INFO")

        # Compile with the dynamic configuration
        compiled_workflow = workflow_graph.compile(**compile_kwargs)
        
        monitoring.log_agent_activity("Workflow Builder", f"Successfully built {workflow_type} workflow", "SUCCESS")
        
        return compiled_workflow
        
    except Exception as e:
        monitoring.log_agent_activity("Workflow Builder", f"Failed to build {workflow_type} workflow: {str(e)}", "ERROR")
        raise

def _initialize_workflow_components(workflow: StateGraph):
    """
    DEPRECATED: This function is no longer used and will be removed in a future version.
    
    Components are now initialized externally in main.py or serve_chain.py and passed
    via config["configurable"] to workflow.invoke().
    """
    warnings.warn(
        "The _initialize_workflow_components function is deprecated and will be removed. "
        "Components should be initialized externally and passed via config['configurable'].",
        DeprecationWarning,
        stacklevel=2
    )
    # Empty implementation - components should be initialized externally
    pass

