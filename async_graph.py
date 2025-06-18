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
    async_attempt_recovery
)
import monitoring
from platform_config import get_platform_client

async def create_async_phased_workflow() -> StateGraph:
    """
    The definitive, refactored, async-compatible phased workflow with a generic
    'Generate -> Review -> Revise' cycle. Now with descriptive node metadata for LangGraph Studio.
    """
    workflow = StateGraph(AgentState)

    # --- 1. Define Nodes with Descriptions --- (added "_node" suffix to avoid state key conflicts)
    workflow.add_node(
        "initialize_state_node", 
        RunnableLambda(async_initialize_workflow_state).with_config(
            tags=["Initialization"], 
            metadata={"description": "Initializes the state dictionary with default values."}
        )
    )
    workflow.add_node(
        "brd_analysis_node", 
        RunnableLambda(async_brd_analysis_node).with_config(
            tags=["Planning", "Analysis"], 
            metadata={"description": "Analyzes the Business Requirements Document (BRD) to extract structured requirements."}
        )
    )
    workflow.add_node(
        "tech_stack_node", 
        RunnableLambda(async_tech_stack_recommendation_node).with_config(
            tags=["Planning", "Architecture"], 
            metadata={"description": "Recommends an optimal technology stack based on the analyzed requirements."}
        )
    )
    workflow.add_node(
        "system_design_node", 
        RunnableLambda(async_system_design_node).with_config(
            tags=["Planning", "Architecture"], 
            metadata={"description": "Creates a high-level system design and architecture."}
        )
    )
    workflow.add_node(
        "planning_node", 
        RunnableLambda(async_planning_node).with_config(
            tags=["Planning"],
            metadata={"description": "Compiles all analyses into a detailed, phased implementation plan."}
        )
    )
    workflow.add_node(
        "phase_iterator_node", 
        RunnableLambda(async_phase_iterator_node).with_config(
            tags=["Control Flow"],
            metadata={"description": "Sets the context for the current implementation phase or completes the workflow."}
        )
    )
    workflow.add_node(
        "generate_code_node", 
        RunnableLambda(async_code_generation_dispatcher_node).with_config(
            tags=["Implementation", "Code Generation"],
            metadata={"description": "Dispatches to the correct code generator (Backend, Frontend, etc.) based on the current phase."}
        )
    )
    workflow.add_node(
        "review_code_node", 
        RunnableLambda(async_code_quality_analysis_node).with_config(
            tags=["Quality Assurance", "Review"],
            metadata={"description": "Reviews the newly generated code for quality, bugs, and adherence to standards."}
        )
    )
    workflow.add_node(
        "increment_revision_node",
        RunnableLambda(async_increment_revision_count_node).with_config(
            tags=["Control Flow", "Revision"],
            metadata={"description": "Increments the revision counter for the current phase before retrying generation."}
        )
    )
    workflow.add_node(
        "phase_complete_node", 
        RunnableLambda(async_phase_completion_node).with_config(
            tags=["Control Flow"],
            metadata={"description": "Marks the current phase as complete and prepares for the next iteration."}
        )
    )
    workflow.add_node(
        "testing_module_node", 
        RunnableLambda(async_testing_module_node).with_config(
            tags=["Quality Assurance", "Testing"],
            metadata={"description": "Generates and runs a full suite of tests (unit, integration) against the generated codebase."}
        )
    )
    workflow.add_node(
        "finalize_node", 
        RunnableLambda(async_finalize_workflow).with_config(
            tags=["Finalization"],
            metadata={"description": "Compiles final results, generates a summary report, and concludes the workflow."}
        )
    )

    # --- 2. Define Edges --- (updated references to match new node names)
    workflow.set_entry_point("initialize_state_node")
    
    # Planning Phase
    workflow.add_edge("initialize_state_node", "brd_analysis_node")
    workflow.add_edge("brd_analysis_node", "tech_stack_node")
    workflow.add_edge("tech_stack_node", "system_design_node")
    workflow.add_edge("system_design_node", "planning_node")
    workflow.add_edge("planning_node", "phase_iterator_node")

    # Phased Implementation Loop
    workflow.add_conditional_edges(
        "phase_iterator_node",
        async_has_next_phase,
        {
            StateFields.NEXT_PHASE: "generate_code_node",
            StateFields.WORKFLOW_COMPLETE: "testing_module_node"
        }
    )
    
    # The 'Generate -> Review -> Revise' Cycle
    workflow.add_edge("generate_code_node", "review_code_node")
    workflow.add_conditional_edges(
        "review_code_node",
        async_should_retry_code_generation,
        {
            StateFields.APPROVE: "phase_complete_node",
            StateFields.REVISE: "increment_revision_node"
        }
    )
    
    # Increment revision count before going back to generate code
    workflow.add_edge("increment_revision_node", "generate_code_node")
    
    # After a phase is approved, go to the next phase
    workflow.add_edge("phase_complete_node", "phase_iterator_node")

    # Finalization
    workflow.add_edge("testing_module_node", "finalize_node")
    workflow.add_edge("finalize_node", END)

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
            "retry_code_generation": "architecture_generation_node",
            "continue": "testing_module_node"
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
            "retry_code_generation": "architecture_generation_node",
            "continue": "testing_module_node"
        }
    )
    
    workflow.add_edge("testing_module_node", "finalize_node")
    workflow.add_edge("finalize_node", END)
    
    return workflow

async def create_async_resumable_workflow() -> StateGraph:
    """
    Create an async-compatible workflow that can be interrupted and resumed.
    Based on the async iterative workflow with checkpointing.
    """
    workflow = StateGraph(AgentState)
    
    # Add state initialization node first
    workflow.add_node("initialize_state_node", async_initialize_workflow_state)
    
    # Add all nodes with specialized agents
    workflow.add_node("brd_analysis_node", async_brd_analysis_node)
    workflow.add_node("checkpoint_after_brd", async_checkpoint_state)
    workflow.add_node("tech_stack_recommendation_node", async_tech_stack_recommendation_node)
    workflow.add_node("checkpoint_after_tech_stack", async_checkpoint_state)
    workflow.add_node("system_design_node", async_system_design_node)
    workflow.add_node("checkpoint_after_system_design", async_checkpoint_state)
    
    # Use consolidated planning module
    workflow.add_node("planning_module_node", async_planning_module)
    workflow.add_node("checkpoint_after_planning", async_checkpoint_state)
    
    # Recovery node
    workflow.add_node("recovery_node", async_attempt_recovery)
    
    # Complete sequence of specialized code generation nodes
    workflow.add_node("architecture_generation_node", async_architecture_generator_node)
    workflow.add_node("database_generation_node", async_database_generator_node)
    workflow.add_node("backend_generation_node", async_backend_generator_node)
    workflow.add_node("frontend_generation_node", async_frontend_generator_node)
    workflow.add_node("integration_generation_node", async_integration_generator_node)
    workflow.add_node("code_optimizer_node", async_code_optimizer_node)
    workflow.add_node("checkpoint_after_implementation", async_checkpoint_state)
    
    # Testing and quality modules
    workflow.add_node("quality_module_node", async_quality_module)
    workflow.add_node("testing_module_node", async_testing_module)
    workflow.add_node("finalize_node", async_finalize_workflow)

    # Define flow - REQUIRED: Set entry point first
    workflow.set_entry_point("brd_analysis_node")

    # Core workflow path with checkpoints
    workflow.add_edge("brd_analysis_node", "checkpoint_after_brd")
    workflow.add_edge("checkpoint_after_brd", "tech_stack_recommendation_node")
    workflow.add_edge("tech_stack_recommendation_node", "checkpoint_after_tech_stack")
    workflow.add_edge("checkpoint_after_tech_stack", "system_design_node")
    workflow.add_edge("system_design_node", "checkpoint_after_system_design")
    workflow.add_edge("checkpoint_after_system_design", "planning_module_node")
    workflow.add_edge("planning_module_node", "checkpoint_after_planning")
    
    # Code generation flow
    workflow.add_edge("checkpoint_after_planning", "architecture_generation_node")
    workflow.add_edge("architecture_generation_node", "database_generation_node")
    workflow.add_edge("database_generation_node", "backend_generation_node")
    workflow.add_edge("backend_generation_node", "frontend_generation_node")
    workflow.add_edge("frontend_generation_node", "integration_generation_node")
    workflow.add_edge("integration_generation_node", "code_optimizer_node")
    workflow.add_edge("code_optimizer_node", "checkpoint_after_implementation")
    
    # Quality and testing path
    workflow.add_edge("checkpoint_after_implementation", "quality_module_node")
    workflow.add_conditional_edges(
        "quality_module_node",
        async_should_retry_code_generation,
        {
            "retry_code_generation": "architecture_generation_node",
            "continue": "testing_module_node"
        }
    )

    workflow.add_edge("testing_module_node", "finalize_node")
    workflow.add_edge("finalize_node", END)

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

# Helper function for async workflow routing
async def get_async_workflow(workflow_type: str) -> StateGraph:
    """Get async workflow based on type."""
    workflow_factories = {
        "basic": create_async_basic_workflow,
        "iterative": create_async_iterative_workflow,
        "phased": create_async_phased_workflow,
        "modular": create_async_modular_workflow,
        "resumable": create_async_resumable_workflow,
        "implementation": create_async_implementation_workflow
    }
    
    if workflow_type not in workflow_factories:
        raise ValueError(f"Unknown workflow type: {workflow_type}")
    
    return await workflow_factories[workflow_type]()