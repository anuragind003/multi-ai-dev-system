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
    async_phase_iterator_node,
    async_code_generation_dispatcher_node,
    async_code_quality_analysis_node,
    async_phase_completion_node,
    async_increment_revision_count_node,
    async_testing_module_node,
    async_finalize_workflow,
    
    # Decision functions
    async_has_next_phase,
    async_should_retry_code_generation,
    
    # Add these missing decision functions
    async_decide_on_architecture_quality,
    async_decide_on_database_quality,
    async_decide_on_backend_quality,
    async_decide_on_frontend_quality,
    async_decide_on_integration_quality,
    
    # Quality nodes - add these explicitly 
    async_architecture_quality_node,
    async_database_quality_node,
    async_backend_quality_node,
    async_frontend_quality_node,
    async_integration_quality_node,
    
    # Legacy compatibility functions if needed
    async_architecture_generator_node,
    async_database_generator_node,
    async_backend_generator_node,
    async_frontend_generator_node,
    async_integration_generator_node,
    async_code_optimizer_node,
    async_quality_module,
    async_planning_module,
    async_testing_module,
    async_checkpoint_state,
    async_attempt_recovery,
    human_approval_node,
    decide_after_brd_approval
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

async def create_async_phased_workflow() -> StateGraph:
    """
    Create a phased development workflow with human-in-the-loop approval gates.
    """
    workflow = StateGraph(AgentState)

    # Add state initialization
    workflow.add_node("initialize_state_node", async_initialize_workflow_state)

    # Add agent nodes with a "_node" suffix to avoid state key conflicts
    workflow.add_node("brd_analysis_node", async_brd_analysis_node)
    workflow.add_node("tech_stack_recommendation_node", async_tech_stack_recommendation_node)
    workflow.add_node("human_approval_brd_node", human_approval_node)
    workflow.add_node("system_design_node", async_system_design_node)
    workflow.add_node("planning_node", async_planning_node)
    workflow.add_node("code_generation_node", async_code_generation_dispatcher_node)

    # Define workflow edges using the new node names
    workflow.set_entry_point("initialize_state_node")
    workflow.add_edge("initialize_state_node", "brd_analysis_node")
    
    # REWIRED: Go to human approval after BRD analysis
    workflow.add_edge("brd_analysis_node", "human_approval_brd_node")

    # ADD: Add the conditional logic after human approval
    workflow.add_conditional_edges(
        "human_approval_brd_node",
        decide_after_brd_approval,
        {
            "proceed": "tech_stack_recommendation_node",
            "revise": "brd_analysis_node",
            "end": END
        }
    )
    
    workflow.add_edge("tech_stack_recommendation_node", "system_design_node")
    workflow.add_edge("system_design_node", "planning_node")
    workflow.add_edge("planning_node", "code_generation_node")
    workflow.add_edge("code_generation_node", END)

    return workflow

# Keep the other workflow definitions unchanged for backward compatibility
# async_iterative_workflow, async_basic_workflow, etc. remain as they are...

async def create_async_iterative_workflow() -> StateGraph:
    """Create an async-compatible iterative workflow with enhanced error handling."""
    workflow = StateGraph(AgentState)
    
    # Add state initialization node first
    workflow.add_node("initialize_state_node", async_initialize_workflow_state)
    
    # Add all nodes with specialized agents
    workflow.add_node("brd_analysis_node", async_brd_analysis_node)
    workflow.add_node("tech_stack_node", async_tech_stack_recommendation_node)
    workflow.add_node("system_design_node", async_system_design_node)
    
    # Consolidated planning module
    workflow.add_node("planning_module_node", async_planning_module)
    
    # Add recovery nodes
    workflow.add_node("implementation_recovery_node", async_attempt_recovery)
    workflow.add_node("generation_checkpoint_node", async_checkpoint_state)
    
    # Complete sequence of specialized code generation nodes
    workflow.add_node("architecture_generation_node", async_architecture_generator_node)
    workflow.add_node("database_generation_node", async_database_generator_node)
    workflow.add_node("backend_generation_node", async_backend_generator_node)
    workflow.add_node("frontend_generation_node", async_frontend_generator_node)
    workflow.add_node("integration_generation_node", async_integration_generator_node)
    workflow.add_node("code_optimizer_node", async_code_optimizer_node)
    
    # Consolidated testing and quality modules
    workflow.add_node("quality_module_node", async_quality_module)
    workflow.add_node("testing_module_node", async_testing_module)
    workflow.add_node("finalize_node", async_finalize_workflow)

    # Define flow - REQUIRED: Set entry point first
    workflow.set_entry_point("initialize_state_node")

    # Core workflow path with checkpoints
    workflow.add_edge("initialize_state_node", "brd_analysis_node")
    workflow.add_edge("brd_analysis_node", "tech_stack_node")
    workflow.add_edge("tech_stack_node", "system_design_node")
    workflow.add_edge("system_design_node", "planning_module_node")
    
    # Add checkpoint after planning
    workflow.add_edge("planning_module_node", "generation_checkpoint_node")
    workflow.add_edge("generation_checkpoint_node", "architecture_generation_node")
    
    # Code generation flow with full sequence of specialized generators
    workflow.add_edge("architecture_generation_node", "database_generation_node")
    workflow.add_edge("database_generation_node", "backend_generation_node")
    workflow.add_edge("backend_generation_node", "frontend_generation_node")
    workflow.add_edge("frontend_generation_node", "integration_generation_node")
    workflow.add_edge("integration_generation_node", "code_optimizer_node")
    
    # Connect to quality module
    workflow.add_edge("code_optimizer_node", "quality_module_node")
    
    # Use StateFields for consistent control flow
    workflow.add_conditional_edges(
        "quality_module_node",
        async_should_retry_code_generation,
        {
            StateFields.REVISE: "architecture_generation_node",
            StateFields.APPROVE: "testing_module_node"
        }
    )

    # Connect directly to finalize after testing module
    workflow.add_edge("testing_module_node", "finalize_node")
    workflow.add_edge("finalize_node", END)

    return workflow

async def create_async_basic_workflow() -> StateGraph:
    """Create an async-compatible basic linear workflow with each agent executed once."""
    workflow = StateGraph(AgentState)
    
    # Add state initialization node first
    workflow.add_node("initialize_state_node", async_initialize_workflow_state)
    
    # Add nodes
    workflow.add_node("brd_analysis_node", async_brd_analysis_node)
    workflow.add_node("tech_stack_node", async_tech_stack_recommendation_node)
    workflow.add_node("system_design_node", async_system_design_node)
    workflow.add_node("planning_module_node", async_planning_module)
    
    # Specialized code generation nodes
    workflow.add_node("architecture_generation_node", async_architecture_generator_node)
    workflow.add_node("database_generation_node", async_database_generator_node)
    workflow.add_node("backend_generation_node", async_backend_generator_node)
    workflow.add_node("frontend_generation_node", async_frontend_generator_node)
    workflow.add_node("integration_generation_node", async_integration_generator_node)
    workflow.add_node("code_optimizer_node", async_code_optimizer_node)
    
    # Testing and finalization
    workflow.add_node("testing_module_node", async_testing_module)
    workflow.add_node("finalize_node", async_finalize_workflow)
    
    # Define linear flow
    workflow.set_entry_point("initialize_state_node")
    
    # Connect initialization to first step
    workflow.add_edge("initialize_state_node", "brd_analysis_node")
    
    # Rest of the edges remain unchanged
    workflow.add_edge("brd_analysis_node", "tech_stack_node")
    workflow.add_edge("tech_stack_node", "system_design_node")
    workflow.add_edge("system_design_node", "planning_module_node")
    workflow.add_edge("planning_module_node", "architecture_generation_node")
    workflow.add_edge("architecture_generation_node", "database_generation_node")
    workflow.add_edge("database_generation_node", "backend_generation_node")
    workflow.add_edge("backend_generation_node", "frontend_generation_node")
    workflow.add_edge("frontend_generation_node", "integration_generation_node")
    workflow.add_edge("integration_generation_node", "code_optimizer_node")
    workflow.add_edge("code_optimizer_node", "testing_module_node")
    workflow.add_edge("testing_module_node", "finalize_node")
    workflow.add_edge("finalize_node", END)
    
    return workflow

async def create_async_modular_workflow() -> StateGraph:
    """Create an async-compatible modular workflow with module-based execution."""
    workflow = StateGraph(AgentState)
    
    # Add state initialization node first
    workflow.add_node("initialize_state_node", async_initialize_workflow_state)
    
    # Define module groups
    # Define requirements phase (BRD analysis & tech stack)
    workflow.add_node("requirements_module", async_brd_analysis_node)
    
    # Design phase
    workflow.add_node("design_module", async_system_design_node)
    
    # Planning phase
    workflow.add_node("planning_module_node", async_planning_module)
    
    # Implementation phase nodes
    workflow.add_node("architecture_generation_node", async_architecture_generator_node)
    workflow.add_node("database_generation_node", async_database_generator_node)
    workflow.add_node("backend_generation_node", async_backend_generator_node)
    workflow.add_node("frontend_generation_node", async_frontend_generator_node)
    workflow.add_node("integration_generation_node", async_integration_generator_node)
    workflow.add_node("code_optimizer_node", async_code_optimizer_node)
    
    # Quality phase
    workflow.add_node("quality_module_node", async_quality_module)
    
    # Testing phase
    workflow.add_node("testing_module_node", async_testing_module)
    
    # Finalization
    workflow.add_node("finalize_node", async_finalize_workflow)
    
    # Set up the flow
    workflow.set_entry_point("initialize_state_node")
    
    # Connect initialization to first step
    workflow.add_edge("initialize_state_node", "requirements_module")
    
    # Linear flow between major phases
    workflow.add_edge("requirements_module", "design_module")
    workflow.add_edge("design_module", "planning_module_node")
    workflow.add_edge("planning_module_node", "architecture_generation_node")
    workflow.add_edge("architecture_generation_node", "database_generation_node")
    workflow.add_edge("database_generation_node", "backend_generation_node")
    workflow.add_edge("backend_generation_node", "frontend_generation_node")
    workflow.add_edge("frontend_generation_node", "integration_generation_node")
    workflow.add_edge("integration_generation_node", "code_optimizer_node")
    workflow.add_edge("code_optimizer_node", "quality_module_node")
    
    # Add conditional edge from quality to implementation or testing
    workflow.add_conditional_edges(
        "quality_module_node",
        async_should_retry_code_generation,
        {
            StateFields.REVISE: "architecture_generation_node",
            StateFields.APPROVE: "testing_module_node"
        }
    )
    
    workflow.add_edge("testing_module_node", "finalize_node")
    workflow.add_edge("finalize_node", END)
    
    return workflow

async def create_async_resumable_workflow() -> StateGraph:
    """
    Create an async-compatible workflow that can be interrupted and resumed.
    Based on the async phased workflow with checkpointing.
    """
    # Create the async phased workflow as the base
    workflow = await create_async_phased_workflow()
    
    # The checkpointer is added during compilation in the main script
    # This function just needs to return the base graph
    return workflow

async def create_async_implementation_workflow() -> StateGraph:
    """Create an async workflow specifically for code implementation with quality feedback loops."""
    workflow = StateGraph(AgentState)
    
    # Add state initialization node first
    workflow.add_node("initialize_state_node", async_initialize_workflow_state)
    
    # Add code generation nodes
    workflow.add_node("architecture_generation", async_architecture_generator_node)
    workflow.add_node("architecture_quality", async_architecture_quality_node)
    workflow.add_node("database_generation", async_database_generator_node)
    workflow.add_node("database_quality", async_database_quality_node)
    workflow.add_node("backend_generation", async_backend_generator_node)
    workflow.add_node("backend_quality", async_backend_quality_node)
    workflow.add_node("frontend_generation", async_frontend_generator_node)
    workflow.add_node("frontend_quality", async_frontend_quality_node)
    workflow.add_node("integration_generation", async_integration_generator_node)
    workflow.add_node("integration_quality", async_integration_quality_node)
    workflow.add_node("code_optimization", async_code_optimizer_node)
    
    # Set entry point to initialization
    workflow.set_entry_point("initialize_state_node")
    
    # Connect initialization to first step
    workflow.add_edge("initialize_state_node", "architecture_generation")
    
    # Architecture feedback loop
    workflow.add_edge("architecture_generation", "architecture_quality")
    workflow.add_conditional_edges(
        "architecture_quality", 
        async_decide_on_architecture_quality,
        {
            "approve": "database_generation",
            "revise": "architecture_generation"
        }
    )
    
    # Database feedback loop
    workflow.add_edge("database_generation", "database_quality")
    workflow.add_conditional_edges(
        "database_quality",
        async_decide_on_database_quality,
        {
            "approve": "backend_generation",
            "revise": "database_generation" 
        }
    )
    
    # Backend feedback loop
    workflow.add_edge("backend_generation", "backend_quality")
    workflow.add_conditional_edges(
        "backend_quality",
        async_decide_on_backend_quality,
        {
            "approve": "frontend_generation",
            "revise": "backend_generation"
        }
    )
    
    # Frontend feedback loop
    workflow.add_edge("frontend_generation", "frontend_quality")
    workflow.add_conditional_edges(
        "frontend_quality",
        async_decide_on_frontend_quality,
        {
            "approve": "integration_generation",
            "revise": "frontend_generation"
        }
    )
    
    # Integration feedback loop
    workflow.add_edge("integration_generation", "integration_quality")
    workflow.add_conditional_edges(
        "integration_quality",
        async_decide_on_integration_quality,
        {
            "approve": "code_optimization",
            "revise": "integration_generation"
        }
    )
    
    # Final step
    workflow.add_edge("code_optimization", END)
    
    return workflow

async def create_async_enhanced_phased_workflow() -> StateGraph:
    """
    Create an enhanced, async-compatible phased workflow.
    This version will use standard nodes until enhanced async nodes are implemented.
    The "enhanced" aspect comes from configuration passed during invocation.
    """
    return await create_async_phased_workflow()

async def get_async_workflow(workflow_type: str) -> StateGraph:
    """Get async workflow based on type. Returns an uncompiled graph."""
    workflow_factories = {
        "basic": create_async_basic_workflow,
        "iterative": create_async_iterative_workflow,
        "phased": create_async_phased_workflow,
        "enhanced": create_async_enhanced_phased_workflow,
        "modular": create_async_modular_workflow,
        "resumable": create_async_resumable_workflow,
        "implementation": create_async_implementation_workflow
    }
    
    if workflow_type not in workflow_factories:
        raise ValueError(f"Unknown workflow type: {workflow_type}")
    
    # Add warnings for deprecated workflow types
    if workflow_type in ["basic", "iterative", "modular", "implementation"]:
        import warnings
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Async workflow type '{workflow_type}' is deprecated. Consider using 'phased' workflow.")
        
    try:
        monitoring.log_agent_activity("Async Workflow Builder", f"Building {workflow_type} async workflow", "START")
        
        # Create the workflow
        workflow_graph = await workflow_factories[workflow_type]()
        
        # Set recursion limit directly on graph object
        if hasattr(workflow_graph, "set_recursion_limit"):
            workflow_graph.set_recursion_limit(50)  # Increase from 25 to 50
        elif hasattr(workflow_graph, "recursion_limit"):
            workflow_graph.recursion_limit = 50  # Increase from 25 to 50
        
        monitoring.log_agent_activity("Async Workflow Builder", f"Successfully created {workflow_type} async workflow definition", "SUCCESS")
        
        # Return the uncompiled graph. Compilation will happen at the point of use.
        return workflow_graph
        
    except Exception as e:
        monitoring.log_agent_activity("Async Workflow Builder", f"Failed to build {workflow_type} async workflow: {str(e)}", "ERROR")
        raise

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