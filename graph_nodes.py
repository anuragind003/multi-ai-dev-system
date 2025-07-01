"""
LangGraph Node Functions for Multi-AI Development System.
Each node represents a specialized AI agent in the development workflow.
"""

import time
import inspect
import traceback
import logging
import uuid
import monitoring
import json
from pathlib import Path
from typing import Dict, Any, Optional, Generator, Callable, TypedDict, List, Union
from contextlib import contextmanager
from functools import partial  # Add this import for partial function application
from config import get_llm, get_system_config
from agent_temperatures import get_agent_temperature
from agent_state import AgentState, StateFields
from datetime import datetime
import os  # New import for environment variable check

_AGENT_CACHE = {}  # Module-level cache for agents

@contextmanager
def start_trace_span(name: str, metadata: Optional[Dict[str, Any]] = None) -> Generator[None, None, None]:
    """
    Custom implementation to replace missing LangChain function.
    
    Provides tracing functionality for phases in workflow execution
    with comprehensive error handling and monitoring integration.
    
    Args:
        name: The name of the phase/span to be traced
        metadata: Optional metadata associated with the span
    
    Yields:
        None: Context manager pattern
    """
    start_time = time.time()
    span_id = f"phase_{int(start_time * 1000)}"
    
    try:
        # Log the start of the phase
        monitoring.log_agent_activity(
            agent_name="Phase Iterator", 
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
        monitoring.log_agent_activity(
            agent_name="Phase Iterator",
            message=f"Error in phase {name}: {str(e)}",
            level="ERROR",
            metadata={
                "span_id": span_id,
                "phase": name,
                "execution_time": time.time() - start_time,
                "error_traceback": traceback.format_exc(),
                **(metadata or {})
            }
        )
        # Re-raise the exception for proper handling
        raise
        
    finally:
        # Always log completion with performance metrics
        monitoring.log_agent_activity(
            agent_name="Phase Iterator",
            message=f"Completed phase: {name}",
            level="INFO",
            metadata={
                "span_id": span_id,
                "phase": name,
                "execution_time": time.time() - start_time,
                **(metadata or {})
            }
        )

# Import agent classes
from agents.brd_analyst import BRDAnalystAgent  # Keep original for backward compatibility
from agents.brd_analyst_react import BRDAnalystReActAgent  # New ReAct-based BRD Analyst
from agents.tech_stack_advisor_react import TechStackAdvisorReActAgent
from agents.system_designer_react import SystemDesignerReActAgent

from agents.planning.plan_compiler_react import PlanCompilerReActAgent
from agents.code_generation.architecture_generator import ArchitectureGeneratorAgent
from agents.code_generation.database_generator import DatabaseGeneratorAgent
from agents.code_generation.backend_orchestrator import BackendOrchestratorAgent
from agents.code_generation.frontend_generator import FrontendGeneratorAgent
from agents.code_generation.integration_generator import IntegrationGeneratorAgent
from agents.code_generation.code_optimizer import CodeOptimizerAgent
from agents.test_case_generator import TestCaseGeneratorAgent
from agents.code_quality_agent import CodeQualityAgent
from agents.test_validation_agent import TestValidationAgent

logger = logging.getLogger(__name__)

# --- Helper Functions ---

def create_agent_with_temperature(agent_class, agent_name_key: str, config: Dict[str, Any], **additional_kwargs):
    """Create an agent with appropriate temperature settings."""
    from agent_temperatures import get_agent_temperature
    from config import get_llm

    # Get the agent's conceptual temperature
    temperature = get_agent_temperature(agent_name_key)
    logger.info(f"Creating {agent_name_key} with temperature={temperature}")

    # Get global LLM-specific kwargs if any
    global_llm_kwargs = config["configurable"].get("global_llm_specific_kwargs", {})    # Create a dedicated LLM instance for this agent
    llm = get_llm(temperature=temperature, llm_specific_kwargs=global_llm_kwargs)

    # Build the initialization arguments - handle different temperature parameter names
    agent_args = {
        "llm": llm,
        "memory": config["configurable"].get("memory"),
    }
    
    # Add temperature parameter based on what the agent expects
    if "default_temperature" in agent_class.__init__.__code__.co_varnames:
        agent_args["default_temperature"] = temperature
    else:
        agent_args["temperature"] = temperature

    # Add RAG retriever if the agent accepts it and it's available
    if "rag_retriever" in agent_class.__init__.__code__.co_varnames and "rag_manager" in config["configurable"]:
        agent_args["rag_retriever"] = config["configurable"].get("rag_manager").get_retriever()    # Add output directory if the agent accepts it and it's available
    if "output_dir" in agent_class.__init__.__code__.co_varnames and "run_output_dir" in config["configurable"]:
        agent_args["output_dir"] = config["configurable"]["run_output_dir"]
    elif "run_output_dir" in agent_class.__init__.__code__.co_varnames and "run_output_dir" in config["configurable"]:
        agent_args["run_output_dir"] = config["configurable"]["run_output_dir"]

    # Add code execution tool if the agent accepts it and it's available
    if "code_execution_tool" in agent_class.__init__.__code__.co_varnames and "code_execution_tool" in config["configurable"]:
        agent_args["code_execution_tool"] = config["configurable"]["code_execution_tool"]

    # Add message bus if available
    if "message_bus" in agent_class.__init__.__code__.co_varnames and "message_bus" in config["configurable"]:
        agent_args["message_bus"] = config["configurable"]["message_bus"]    # Add any additional kwargs
    agent_args.update(additional_kwargs)

    # Create and return the agent instance
    agent_instance = agent_class(**agent_args)
      # --- UPDATED DELAY ---
    # Add a substantial delay to prevent hitting API rate limits (15 requests/minute = 1 request every 4 seconds)
    logger.info("Pausing for 4.0 seconds to respect API rate limits...")
    time.sleep(4.0)  # Increased from 1.5 to 4.0 seconds to strictly enforce the limit
    # --- END OF CHANGE ---
    
    return agent_instance

# --- Planning & Analysis Nodes ---

def brd_analysis_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """Parse the BRD to extract requirements and convert to a structured format.
    Uses the ReAct-based BRD Analyst for improved accuracy and reasoning."""
    logger.info("Executing BRD analysis node")
    
    # Use the new ReAct-based agent
    agent = create_agent_with_temperature(BRDAnalystReActAgent, "BRD Analyst Agent", config)
    
    # Get session_id from config if available for WebSocket monitoring
    session_id = config.get("session_id")
    requirements = agent.run(state[StateFields.BRD_CONTENT], session_id=session_id)
    
    return {StateFields.REQUIREMENTS_ANALYSIS: requirements}

def tech_stack_recommendation_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """Recommend appropriate technology stack based on the requirements."""
    logger.info("Executing tech stack recommendation node")
    
    agent = create_agent_with_temperature(TechStackAdvisorReActAgent, "Tech Stack Advisor Agent", config)
    
    # Get session_id from config if available for WebSocket monitoring
    session_id = config.get("session_id")
    tech_stack = agent.run(state[StateFields.REQUIREMENTS_ANALYSIS], session_id=session_id)
    
    return {StateFields.TECH_STACK_RECOMMENDATION: tech_stack}

def system_design_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """Create a comprehensive system design based on requirements and tech stack."""
    logger.info("Executing system design node")
    
    agent = create_agent_with_temperature(SystemDesignerReActAgent, "System Designer Agent", config)
    system_design = agent.run(
        state[StateFields.REQUIREMENTS_ANALYSIS], 
        state[StateFields.TECH_STACK_RECOMMENDATION]
    )
    
    return {StateFields.SYSTEM_DESIGN: system_design}

def planning_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """Create an implementation plan with development phases."""
    logger.info("Executing planning node")
    
    agent = create_agent_with_temperature(PlanCompilerReActAgent, "Plan Compiler Agent", config)
    
    # Extract required inputs with defaults for missing elements
    project_analysis = state.get("project_analysis", {})
    system_design = state[StateFields.SYSTEM_DESIGN]
    timeline_estimation = state.get("timeline_estimation", {})
    risk_assessment = state.get("risk_assessment", {})
    
    implementation_plan = agent.run(
        project_analysis=project_analysis,
        system_design=system_design,
        timeline_estimation=timeline_estimation,
        risk_assessment=risk_assessment
    )
    
    return {StateFields.IMPLEMENTATION_PLAN: implementation_plan}

# --- Phased Loop Nodes ---

def phase_iterator_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """Iterate through implementation phases and set up the current phase context."""
    logger.info("Executing phase iterator node")
    
    # Get implementation plan - check both top level and nested structure
    plan = state.get(StateFields.IMPLEMENTATION_PLAN, {})
    
    # Try to get phases from nested structure first (ComprehensivePlanOutput format)
    if "implementation_plan" in plan:
        nested_plan = plan["implementation_plan"]
        phases = nested_plan.get("development_phases", [])
        logger.info(f"Found nested implementation plan with {len(phases)} phases")
    else:
        # Fallback to direct structure
        phases = plan.get("development_phases", [])
        logger.info(f"Found direct implementation plan with {len(phases)} phases")
    
    current_index = state.get(StateFields.CURRENT_PHASE_INDEX, 0)
    
    # Check if we have phases to process
    if not phases:
        logger.warning(f"No development phases found in implementation plan. Plan structure: {list(plan.keys())}")
        logger.info(f"Plan content preview: {str(plan)[:200]}...")
        return {"is_complete": True}
    
    # Get the current phase if available
    if current_index < len(phases):
        current_phase = phases[current_index]
        phase_name = current_phase.get("name", f"Phase {current_index + 1}")
        phase_type = current_phase.get("type", "unknown").lower()
        
        logger.info(f"--- Starting Phase {current_index + 1}/{len(phases)}: {phase_name} ({phase_type}) ---")
        
        # Prepare phase context
        return {
            StateFields.CURRENT_PHASE_NAME: phase_name,
            StateFields.CURRENT_PHASE_TYPE: phase_type,
            "current_phase_details": current_phase,
            "current_phase_start_time": time.time(),
            StateFields.REVISION_COUNTS: state.get(StateFields.REVISION_COUNTS, {})  # Carry over revision counts
        }
    else:
        logger.info("--- All implementation phases complete ---")
        return {"is_complete": True}

def code_generation_dispatcher_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """Route to appropriate code generator based on current phase type."""
    phase_type = state.get(StateFields.CURRENT_PHASE_TYPE, "unknown").lower()
    phase_name = state.get(StateFields.CURRENT_PHASE_NAME, "Unknown Phase")
    
    logger.info(f"Dispatching to code generator for phase type: '{phase_type}' (Phase: {phase_name})")

    # Map phase types to generator agents
    generator_map = {
        "architecture": ArchitectureGeneratorAgent,
        "setup": ArchitectureGeneratorAgent,
        "database": DatabaseGeneratorAgent,
        "data": DatabaseGeneratorAgent,
        "backend": BackendOrchestratorAgent,  # Use new orchestrator for industrial backend
        "api": BackendOrchestratorAgent,     # Use orchestrator for API generation
        "server": BackendOrchestratorAgent,  # Use orchestrator for server generation
        "frontend": FrontendGeneratorAgent,
        "ui": FrontendGeneratorAgent,
        "client": FrontendGeneratorAgent,
        "integration": IntegrationGeneratorAgent,
        "connect": IntegrationGeneratorAgent,
        "optimization": CodeOptimizerAgent,
        "refactor": CodeOptimizerAgent,
        # Default to backend orchestrator if type is unclear
        "implementation": BackendOrchestratorAgent,
    }
    
    agent_class = generator_map.get(phase_type, BackendOrchestratorAgent)
    
    agent = create_agent_with_temperature(agent_class, f"{agent_class.__name__}", config)
    
    # Check if we're processing a revision
    revision_counts = state.get(StateFields.REVISION_COUNTS, {})
    current_revisions = revision_counts.get(phase_type, 0)
    is_revision = current_revisions > 0
    
    # Prepare inputs for the generator
    inputs = {
        "requirements_analysis": state.get(StateFields.REQUIREMENTS_ANALYSIS, {}),
        "tech_stack_recommendation": state.get(StateFields.TECH_STACK_RECOMMENDATION, {}),
        "system_design": state.get(StateFields.SYSTEM_DESIGN, {}),
        "implementation_plan": state.get(StateFields.IMPLEMENTATION_PLAN, {}),
        "phase_name": phase_name,
        "phase_type": phase_type,
        "is_revision": is_revision
    }
    
    # Add existing code generation result if available
    if StateFields.CODE_GENERATION_RESULT in state:
        inputs["code_generation_result"] = state[StateFields.CODE_GENERATION_RESULT]
    
    # Add feedback if this is a revision
    if is_revision and StateFields.CODE_REVIEW_FEEDBACK in state:
        inputs["code_review_feedback"] = state[StateFields.CODE_REVIEW_FEEDBACK]
        logger.info(f"Including code review feedback for revision #{current_revisions}")
    
    # Run the agent with all inputs
    result = agent.run(**inputs)
    
    return {StateFields.CODE_GENERATION_RESULT: result}

def code_quality_analysis_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """Analyze code quality and provide feedback for improvements."""
    phase_type = state.get(StateFields.CURRENT_PHASE_TYPE, "general")
    phase_name = state.get(StateFields.CURRENT_PHASE_NAME, "Unknown Phase")
    
    logger.info(f"Executing code quality review for '{phase_type}' code in phase '{phase_name}'")

    # Create quality agent
    agent = create_agent_with_temperature(CodeQualityAgent, "Code Quality Agent", config)
    
    # Run quality analysis
    review_result = agent.run(
        generated_code=state[StateFields.CODE_GENERATION_RESULT],
        tech_stack=state[StateFields.TECH_STACK_RECOMMENDATION],
        code_type=phase_type
    )
    
    # Log key metrics
    approved = "APPROVED" if review_result.get("approved", False) else "NEEDS REVISION"
    critical_issues = len(review_result.get("critical_issues", []))
    suggestions = len(review_result.get("suggestions", []))
    
    logger.info(f"Code review result: {approved} with {critical_issues} critical issues and {suggestions} suggestions")
    
    return {StateFields.CODE_REVIEW_FEEDBACK: review_result}

def phase_completion_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """Complete the current phase and prepare for the next one."""
    current_index = state.get(StateFields.CURRENT_PHASE_INDEX, 0)
    phase_name = state.get(StateFields.CURRENT_PHASE_NAME, f"Phase {current_index}")
    phase_type = state.get(StateFields.CURRENT_PHASE_TYPE, "unknown")
    
    # Calculate phase duration if possible
    phase_start_time = state.get("current_phase_start_time", time.time())
    phase_duration = time.time() - phase_start_time
    
    logger.info(f"Completing phase '{phase_name}' ({phase_type}) - Duration: {phase_duration:.2f}s")
    
    # Create return state
    result = {
        StateFields.CURRENT_PHASE_INDEX: current_index + 1,
        "completed_phases": state.get("completed_phases", []) + [phase_name]
    }
    
    # Track phase execution time
    if "phase_execution_times" not in state:
        result["phase_execution_times"] = {}
    else:
        result["phase_execution_times"] = state["phase_execution_times"].copy()
    
    result["phase_execution_times"][phase_name] = phase_duration
    
    return result

def increment_revision_count_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """Increment the revision count for the current phase type."""
    phase_type = state.get(StateFields.CURRENT_PHASE_TYPE, "unknown")
    
    # Get current revision counts
    revision_counts = state.get(StateFields.REVISION_COUNTS, {}).copy()
    
    # Increment count for current phase
    current_count = revision_counts.get(phase_type, 0)
    revision_counts[phase_type] = current_count + 1
    
    logger.info(f"Incrementing revision count for '{phase_type}' to {current_count + 1}")
    
    return {StateFields.REVISION_COUNTS: revision_counts}

# --- Testing Nodes ---

def testing_module_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """Execute test generation and validation as a single logical step."""
    logger.info("Executing comprehensive testing module")
    
    # Create the agents
    test_gen_agent = create_agent_with_temperature(TestCaseGeneratorAgent, "Test Case Generator Agent", config)
    test_val_agent = create_agent_with_temperature(TestValidationAgent, "Test Validation Agent", config)

    # Generate tests
    test_gen_result = test_gen_agent.run(
        code_generation_result=state[StateFields.CODE_GENERATION_RESULT],
        brd_analysis=state.get(StateFields.REQUIREMENTS_ANALYSIS, {}),
        tech_stack_recommendation=state.get(StateFields.TECH_STACK_RECOMMENDATION, {})
    )
    
    # Validate test results are stored properly
    if not test_gen_result:
        logger.warning("Test generation failed or produced no output")
        test_result = {"status": "error", "message": "Test generation failed"}
        return {"test_generation_result": test_result, StateFields.TEST_VALIDATION_RESULT: {}}
    
    # Log test generation metrics
    test_count = len(test_gen_result.get("generated_files", []))
    logger.info(f"Generated {test_count} test files")
    
    # Run validation on the generated tests
    project_dir = config["configurable"]["run_output_dir"]
    validation_result = test_val_agent.run(project_dir=project_dir)
    
    # Log validation metrics
    passed = validation_result.get("passed", 0)
    failed = validation_result.get("failed", 0)
    success_rate = validation_result.get("success_rate", 0)
    coverage = validation_result.get("coverage_percentage", 0)
    
    logger.info(f"Test validation: {passed} passed, {failed} failed, {success_rate}% success rate, {coverage}% coverage")

    return {
        "test_generation_result": test_gen_result,
        StateFields.TEST_VALIDATION_RESULT: validation_result
    }

def finalize_workflow(state: AgentState, config: dict) -> Dict[str, Any]:
    """Create final workflow summary and consolidate results."""
    logger.info("--- Finalizing Workflow ---")
    
    # Calculate total execution time
    start_time = state.get("workflow_start_time", 0)
    total_execution_time = time.time() - start_time if start_time > 0 else 0
    
    # Get key metrics
    phases_completed = len(state.get("completed_phases", []))
    file_count = len(state.get(StateFields.CODE_GENERATION_RESULT, {}).get("generated_files", {}))
    test_results = state.get(StateFields.TEST_VALIDATION_RESULT, {})
    error_count = len(state.get("errors", []))
    
    # Create summary
    summary = {
        "status": "complete" if error_count == 0 else "complete_with_errors",
        "total_execution_time": total_execution_time,
        "phases_completed": phases_completed,
        "files_generated": file_count,
        "test_success_rate": test_results.get("success_rate", 0),
        "code_coverage": test_results.get("coverage_percentage", 0),
        "error_count": error_count,
        "completion_time": time.time()
    }
    
    logger.info(f"Workflow completed in {total_execution_time:.2f}s with {file_count} files generated")
    
    return {StateFields.WORKFLOW_SUMMARY: summary, "workflow_status": "completed"}

# --- Conditional Edge Functions ---

def has_next_phase(state: AgentState) -> str:
    """Check if there are more development phases to process."""
    plan = state.get(StateFields.IMPLEMENTATION_PLAN, {})
    
    # Try to get phases from nested structure first (ComprehensivePlanOutput format)
    if "implementation_plan" in plan:
        nested_plan = plan["implementation_plan"]
        phases = nested_plan.get("development_phases", [])
    else:
        # Fallback to direct structure
        phases = plan.get("development_phases", [])
    
    current_index = state.get(StateFields.CURRENT_PHASE_INDEX, 0)
    
    if current_index < len(phases):
        next_phase = phases[current_index].get("name", f"Phase {current_index + 1}")
        logger.info(f"Next phase available: {next_phase}")
        return StateFields.NEXT_PHASE
    else:
        logger.info("No more phases available")
        return StateFields.WORKFLOW_COMPLETE

def should_retry_code_generation(state: AgentState) -> str:
    """Decide whether to approve code or request revisions."""
    feedback = state.get(StateFields.CODE_REVIEW_FEEDBACK, {})
    approved = feedback.get("approved", False)
    
    phase_type = state.get(StateFields.CURRENT_PHASE_TYPE, "unknown")
    revision_counts = state.get(StateFields.REVISION_COUNTS, {})
    current_revisions = revision_counts.get(phase_type, 0)
    max_revisions = 2
    
    # Check if code is approved
    if approved:
        logger.info(f"Code for phase type '{phase_type}' approved")
        return StateFields.APPROVE
    
    # Check if max revisions reached
    if current_revisions >= max_revisions:
        logger.warning(f"Max revisions ({max_revisions}) reached for phase type '{phase_type}'. Continuing despite issues.")
        return StateFields.APPROVE
    
    # Request revision
    logger.info(f"Code for phase type '{phase_type}' needs revision (attempt {current_revisions + 1}/{max_revisions})")
    return StateFields.REVISE

def decide_on_architecture_quality(state: AgentState) -> str:
    """Decide whether to approve architecture or request revisions."""
    quality_analysis = state.get(StateFields.ARCHITECTURE_QUALITY_ANALYSIS, {})
    revision_count = state.get(StateFields.ARCHITECTURE_REVISION_COUNT, 0)
    
    # Extract approval status
    approved = quality_analysis.get("approved", False)
    
    # Check if max revisions reached (prevent infinite loops)
    if revision_count >= 2:  # Max 2 revisions
        logger = logging.getLogger(__name__)
        logger.warning(f"Max architecture revisions reached ({revision_count}). Continuing workflow.")
        return "approve"
        
    # Decision based on approval status
    if approved:
        logger = logging.getLogger(__name__)
        logger.info("Architecture approved by quality review")
        return "approve"
    else:
        # Increment revision count in state
        state[StateFields.ARCHITECTURE_REVISION_COUNT] = revision_count + 1
        
        logger = logging.getLogger(__name__)
        logger.info(f"Architecture needs revision (attempt {revision_count + 1})")
        return "revise"

def decide_on_database_quality(state: AgentState) -> str:
    """Decide whether to approve database schema or request revisions."""
    quality_analysis = state.get(StateFields.DATABASE_QUALITY_ANALYSIS, {})
    revision_count = state.get(StateFields.DATABASE_REVISION_COUNT, 0)
    
    # Extract approval status
    approved = quality_analysis.get("approved", False)
    
    # Check if max revisions reached
    if revision_count >= 2:  # Max 2 revisions
        logger = logging.getLogger(__name__)
        logger.warning(f"Max database revisions reached ({revision_count}). Continuing workflow.")
        return "approve"
        
    # Decision based on approval status
    if approved:
        logger = logging.getLogger(__name__)
        logger.info("Database schema approved by quality review")
        return "approve"
    else:
        # Increment revision count in state
        state[StateFields.DATABASE_REVISION_COUNT] = revision_count + 1
        
        logger = logging.getLogger(__name__)
        logger.info(f"Database schema needs revision (attempt {revision_count + 1})")
        return "revise"

def decide_on_backend_quality(state: AgentState) -> str:
    """Decide whether to approve backend code or request revisions."""
    quality_analysis = state.get(StateFields.BACKEND_QUALITY_ANALYSIS, {})
    revision_count = state.get(StateFields.BACKEND_REVISION_COUNT, 0)
    
    # Extract approval status
    approved = quality_analysis.get("approved", False)
    
    # Check if max revisions reached
    if revision_count >= 2:  # Max 2 revisions
        logger = logging.getLogger(__name__)
        logger.warning(f"Max backend revisions reached ({revision_count}). Continuing workflow.")
        return "approve"
        
    # Decision based on approval status
    if approved:
        logger = logging.getLogger(__name__)
        logger.info("Backend code approved by quality review")
        return "approve"
    else:
        # Increment revision count in state
        state[StateFields.BACKEND_REVISION_COUNT] = revision_count + 1
        
        logger = logging.getLogger(__name__)
        logger.info(f"Backend code needs revision (attempt {revision_count + 1})")
        return "revise"

def decide_on_frontend_quality(state: AgentState) -> str:
    """Decide whether to approve frontend code or request revisions."""
    quality_analysis = state.get(StateFields.FRONTEND_QUALITY_ANALYSIS, {})
    revision_count = state.get(StateFields.FRONTEND_REVISION_COUNT, 0)
    
    # Extract approval status
    approved = quality_analysis.get("approved", False)
    
    # Check if max revisions reached
    if revision_count >= 2:  # Max 2 revisions
        logger = logging.getLogger(__name__)
        logger.warning(f"Max frontend revisions reached ({revision_count}). Continuing workflow.")
        return "approve"
        
    # Decision based on approval status
    if approved:
        logger = logging.getLogger(__name__)
        logger.info("Frontend code approved by quality review")
        return "approve"
    else:
        # Increment revision count in state
        state[StateFields.FRONTEND_REVISION_COUNT] = revision_count + 1
        
        logger = logging.getLogger(__name__)
        logger.info(f"Frontend code needs revision (attempt {revision_count + 1})")
        return "revise"

def decide_on_integration_quality(state: AgentState) -> str:
    """Decide whether to approve integration code or request revisions."""
    quality_analysis = state.get(StateFields.INTEGRATION_QUALITY_ANALYSIS, {})
    revision_count = state.get(StateFields.INTEGRATION_REVISION_COUNT, 0)
    
    # Extract approval status
    approved = quality_analysis.get("approved", False)
    
    # Check if max revisions reached
    if revision_count >= 2:  # Max 2 revisions
        logger = logging.getLogger(__name__)
        logger.warning(f"Max integration revisions reached ({revision_count}). Continuing workflow.")
        return "approve"
        
    # Decision based on approval status
    if approved:
        logger = logging.getLogger(__name__)
        logger.info("Integration code approved by quality review")
        return "approve"
    else:
        # Increment revision count in state
        state[StateFields.INTEGRATION_REVISION_COUNT] = revision_count + 1
        
        logger = logging.getLogger(__name__)
        logger.info(f"Integration code needs revision (attempt {revision_count + 1})")
        return "revise"

def initialize_workflow_state(state: AgentState) -> AgentState:
    """
    Initialize essential state keys at the beginning of the workflow.
    
    This function ensures that all commonly used state keys are initialized
    with appropriate default values, preventing KeyError exceptions when
    these keys are accessed later in the workflow.
    
    Args:
        state: Current workflow state (may be empty or partially initialized)
        
    Returns:
        State with all essential keys initialized
    """
    logger = logging.getLogger(__name__)
    logger.info("Initializing essential workflow state keys")
    
    # Create a new state object to avoid modifying the original
    initialized_state = state.copy()
    
    # Initialize workflow metadata
    if "workflow_id" not in initialized_state:
        initialized_state["workflow_id"] = f"workflow_{int(time.time())}"
    
    if "workflow_start_time" not in initialized_state:
        initialized_state["workflow_start_time"] = time.time()
    
    # Initialize code generation structure
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
    
    # Initialize revision counters for code components
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
    
    # Return the initialized state
    return initialized_state

# --- Legacy Compatibility Functions ---

def project_analyzer_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """Legacy compatibility function that maps to planning_node."""
    logger.info("Using project_analyzer_node (legacy compatibility)")
    return planning_node(state, config)

def timeline_estimator_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """Legacy compatibility function that maps to planning_node."""
    logger.info("Using timeline_estimator_node (legacy compatibility)")
    return planning_node(state, config)

def risk_assessor_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """Legacy compatibility function that maps to planning_node."""
    logger.info("Using risk_assessor_node (legacy compatibility)")
    return planning_node(state, config)

def plan_compiler_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """Legacy compatibility function that maps to planning_node."""
    logger.info("Using plan_compiler_node (legacy compatibility)")
    return planning_node(state, config)

def test_case_generation_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """Legacy compatibility function that maps to testing_module_node."""
    logger.info("Using test_case_generation_node (legacy compatibility)")
    return testing_module_node(state, config)

def test_validation_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """Legacy compatibility function that maps to testing_module_node."""
    logger.info("Using test_validation_node (legacy compatibility)")
    return testing_module_node(state, config)

# Legacy quality nodes that map to code_quality_analysis_node
def architecture_quality_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """Legacy compatibility function that maps to code_quality_analysis_node."""
    logger.info("Using architecture_quality_node (legacy compatibility)")
    return code_quality_analysis_node(state, config)

def database_quality_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """Legacy compatibility function that maps to code_quality_analysis_node."""
    logger.info("Using database_quality_node (legacy compatibility)")
    return code_quality_analysis_node(state, config)

def backend_quality_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """Legacy compatibility function that maps to code_quality_analysis_node."""
    logger.info("Using backend_quality_node (legacy compatibility)")
    return code_quality_analysis_node(state, config)

def frontend_quality_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """Legacy compatibility function that maps to code_quality_analysis_node."""
    logger.info("Using frontend_quality_node (legacy compatibility)")
    return code_quality_analysis_node(state, config)

def integration_quality_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """Legacy compatibility function that maps to code_quality_analysis_node."""
    logger.info("Using integration_quality_node (legacy compatibility)")
    return code_quality_analysis_node(state, config)

# Legacy module nodes
def requirements_module(state: AgentState, config: dict) -> Dict[str, Any]:
    """Legacy module that combines BRD analysis and tech stack recommendation."""
    logger.info("Using requirements_module (legacy compatibility)")
    brd_result = brd_analysis_node(state, config)
    # Update state with BRD analysis result
    updated_state = {**state, **brd_result}
    tech_result = tech_stack_recommendation_node(updated_state, config)
    return {**brd_result, **tech_result}

def design_module(state: AgentState, config: dict) -> Dict[str, Any]:
    """Legacy module that maps to system_design_node."""
    logger.info("Using design_module (legacy compatibility)")
    return system_design_node(state, config)

def planning_module(state: AgentState, config: dict) -> Dict[str, Any]:
    """Legacy module that maps to planning_node."""
    logger.info("Using planning_module (legacy compatibility)")
    return planning_node(state, config)

def implementation_module(state: AgentState, config: dict) -> Dict[str, Any]:
    """Legacy module that maps to code_generation_dispatcher_node."""
    logger.info("Using implementation_module (legacy compatibility)")
    return code_generation_dispatcher_node(state, config)

def testing_module(state: AgentState, config: dict) -> Dict[str, Any]:
    """Legacy module that maps to testing_module_node."""
    logger.info("Using testing_module (legacy compatibility)")
    return testing_module_node(state, config)

# Legacy decision functions
def check_workflow_completion(state: AgentState) -> str:
    """Legacy decision function that always returns 'continue'."""
    logger.info("Using check_workflow_completion (legacy compatibility)")
    return "continue"

def should_retry_tests(state: AgentState) -> str:
    """Legacy decision function for test retry logic."""
    logger.info("Using should_retry_tests (legacy compatibility)")
    test_results = state.get(StateFields.TEST_VALIDATION_RESULT, {})
    success_rate = test_results.get("success_rate", 0)
    retry_count = state.get("current_test_retry", 0)
    
    if success_rate < 70 and retry_count < 2:
        state["current_test_retry"] = retry_count + 1
        logger.info(f"Tests success rate {success_rate}% is below threshold. Retrying tests.")
        return "retry_tests"
    return "continue"

def should_iterate_implementation(state: AgentState) -> str:
    """Legacy decision function that maps to should_retry_code_generation."""
    logger.info("Using should_iterate_implementation (legacy compatibility)")
    return should_retry_code_generation(state)

def determine_phase_generators(state: AgentState) -> str:
    """Legacy decision function that maps to has_next_phase."""
    logger.info("Using determine_phase_generators (legacy compatibility)")
    return has_next_phase(state)

# Helper functions
def checkpoint_state(state: AgentState, config: dict) -> Dict[str, Any]:
    """Create a checkpoint from the current state."""
    logger.info("Creating checkpoint of workflow state")
    checkpoint_id = f"checkpoint_{int(time.time())}"
    
    # Simply pass through with minimal checkpoint metadata
    return {
        "checkpoint_created": True,
        "checkpoint_id": checkpoint_id,
        "checkpoint_timestamp": time.time()
    }

def phase_dispatcher_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """Legacy function that maps to phase_iterator_node."""
    logger.info("Using phase_dispatcher_node (legacy compatibility)")
    return phase_iterator_node(state, config)

# --- Specialized Generator Node Functions ---

def architecture_generator_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """
    Legacy generator node for architecture code. Maps to dispatcher.
    """
    logger.info("Using architecture_generator_node (legacy compatibility)")
    
    # Set phase type to architecture
    state_with_phase = state.copy()
    state_with_phase[StateFields.CURRENT_PHASE_TYPE] = "architecture"
    state_with_phase[StateFields.CURRENT_PHASE_NAME] = "Architecture Generation"
    
    # Call dispatcher with the modified state
    return code_generation_dispatcher_node(state_with_phase, config)

def database_generator_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """
    Legacy generator node for database code. Maps to dispatcher.
    """
    logger.info("Using database_generator_node (legacy compatibility)")
    
    # Set phase type to database
    state_with_phase = state.copy()
    state_with_phase[StateFields.CURRENT_PHASE_TYPE] = "database"
    state_with_phase[StateFields.CURRENT_PHASE_NAME] = "Database Generation"
    
    # Call dispatcher with the modified state
    return code_generation_dispatcher_node(state_with_phase, config)

def backend_generator_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """
    Legacy generator node for backend code. Maps to dispatcher.
    """
    logger.info("Using backend_generator_node (legacy compatibility)")
    
    # Set phase type to backend
    state_with_phase = state.copy()
    state_with_phase[StateFields.CURRENT_PHASE_TYPE] = "backend"
    state_with_phase[StateFields.CURRENT_PHASE_NAME] = "Backend Generation"
    
    # Call dispatcher with the modified state
    return code_generation_dispatcher_node(state_with_phase, config)

def frontend_generator_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """
    Legacy generator node for frontend code. Maps to dispatcher.
    """
    logger.info("Using frontend_generator_node (legacy compatibility)")
    
    # Set phase type to frontend
    state_with_phase = state.copy()
    state_with_phase[StateFields.CURRENT_PHASE_TYPE] = "frontend"
    state_with_phase[StateFields.CURRENT_PHASE_NAME] = "Frontend Generation"
    
    # Call dispatcher with the modified state
    return code_generation_dispatcher_node(state_with_phase, config)

def integration_generator_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """
    Legacy generator node for integration code. Maps to dispatcher.
    """
    logger.info("Using integration_generator_node (legacy compatibility)")
    
    # Set phase type to integration
    state_with_phase = state.copy()
    state_with_phase[StateFields.CURRENT_PHASE_TYPE] = "integration"
    state_with_phase[StateFields.CURRENT_PHASE_NAME] = "Integration Generation"
    
    # Call dispatcher with the modified state
    return code_generation_dispatcher_node(state_with_phase, config)

def code_optimizer_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """
    Legacy generator node for code optimization. Maps to dispatcher.
    """
    logger.info("Using code_optimizer_node (legacy compatibility)")
    
    # Set phase type to optimization
    state_with_phase = state.copy()
    state_with_phase[StateFields.CURRENT_PHASE_TYPE] = "optimization"
    state_with_phase[StateFields.CURRENT_PHASE_NAME] = "Code Optimization"
    
    # Call dispatcher with the modified state
    return code_generation_dispatcher_node(state_with_phase, config)

# Enhanced LangGraph-based node functions for better reliability
# End of graph_nodes.py

