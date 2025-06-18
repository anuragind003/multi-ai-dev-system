"""
Agent state definitions for Multi-AI Development System.
Uses TypedDict for structural typing of workflow state.
"""

from typing import Dict, Any, TypedDict, Optional, List
from enum import Enum
import uuid
import time

# Define the agent state as a regular TypedDict (no annotations)
class AgentState(TypedDict, total=False):
    """
    The definitive, refactored state for the LangGraph workflow. It is designed to be lean
    and work with the new structured agent outputs.
    """
    # === Core Inputs & High-Level Plans (Set once at the beginning) ===
    brd_content: str
    workflow_config: Dict[str, Any]
    requirements_analysis: Dict[str, Any]
    tech_stack_recommendation: Dict[str, Any]
    system_design: Dict[str, Any]
    implementation_plan: Dict[str, Any]

    # === Consolidated Results for the Main "Generate -> Review" Loop ===
    # Holds the CodeGenerationOutput from the most recent generator agent
    code_generation_result: Dict[str, Any] 
    
    # Holds the CodeQualityReviewOutput from the quality agent
    # This serves as the input for the revision decision and the feedback for the generator.
    code_review_feedback: Optional[Dict[str, Any]]

    # Holds the final TestValidationOutput
    test_validation_result: Dict[str, Any]    # === Phase Iteration Control ===
    current_phase_name: Optional[str]
    current_phase_type: Optional[str]
    current_phase_index: int
    revision_counts: Dict[str, int] # Tracks revisions per phase, e.g., {'backend': 1}
    
    # Individual component revision counters
    architecture_revision_count: int
    database_revision_count: int
    backend_revision_count: int
    frontend_revision_count: int
    integration_revision_count: int# === Final Output & Metadata ===
    errors: List[Dict[str, Any]]
    workflow_summary: Dict[str, Any]
    workflow_id: str
    workflow_start_time: float
    workflow_status: str
    temperature_strategy: Dict[str, float]  # Added temperature strategy field

def create_initial_agent_state(
    brd_content: str, 
    workflow_config: Dict[str, Any]
) -> AgentState:
    """
    Create initial state for the workflow with minimal required fields.
    
    Args:
        brd_content: Business Requirements Document content
        workflow_config: Workflow configuration dictionary
        
    Returns:
        AgentState: Initial state for the workflow
    """
    return AgentState(
        # Core inputs
        brd_content=brd_content,
        workflow_config=workflow_config,
        
        # Initialize empty results
        requirements_analysis={},
        tech_stack_recommendation={},
        system_design={},
        implementation_plan={},
        code_generation_result={"generated_files": []},
        code_review_feedback=None,
        test_validation_result={},
        
        # Phase control
        current_phase_index=0,
        current_phase_name=None,
        current_phase_type=None,
        revision_counts={},
        
        # Metadata
        workflow_id=str(uuid.uuid4()),
        workflow_start_time=time.time(),
        workflow_status="initializing",
        errors=[],
        workflow_summary={}
    )


def validate_agent_state(state: AgentState) -> List[str]:
    """Validate agent state and return list of issues."""
    issues = []
    
    # Check required fields
    required_fields = ["brd_content", "workflow_config"]
    for field in required_fields:
        if field not in state or not state[field]:
            issues.append(f"Missing required field: {field}")
    
    # Check that quality thresholds are valid
    quality_threshold = state.get("quality_threshold", 0.0)
    if not (0 <= quality_threshold <= 10):
        issues.append(f"Invalid quality threshold: {quality_threshold}, must be between 0 and 10")
        
    min_success_rate = state.get("min_success_rate", 0.0) 
    if not (0 <= min_success_rate <= 1):
        issues.append(f"Invalid min success rate: {min_success_rate}, must be between 0 and 1")
    
    # Check that retry counters don't exceed limits
    max_code_gen_retries = state.get("max_code_gen_retries", 3)
    current_code_gen_retry = state.get("current_code_gen_retry", 0)
    if current_code_gen_retry > max_code_gen_retries:
        issues.append(f"Code generation retry count ({current_code_gen_retry}) exceeds limit ({max_code_gen_retries})")
        
    return issues

def get_state_summary(state: AgentState) -> Dict[str, Any]:
    """Get a summary of the current state for display or logging."""
    
    # Count errors
    errors_count = len(state.get("errors", []))
    
    # Calculate progress
    total_phases = len(state.get("implementation_plan", {}).get("development_phases", []))
    current_phase = state.get("current_phase_index", 0)
    phase_progress = f"{current_phase}/{total_phases}" if total_phases > 0 else "N/A"
    
    # Get current phase information
    current_phase_name = state.get("current_phase_name", "Not started")
    current_phase_type = state.get("current_phase_type", "")
    
    # Get revision information
    revision_counts = state.get("revision_counts", {})
    current_revision = revision_counts.get(current_phase_name, 0) if current_phase_name else 0
    
    # Calculate elapsed time
    elapsed_time = time.time() - state.get("workflow_start_time", time.time())
    elapsed_str = f"{elapsed_time:.2f}s"
    
    # Get test validation metrics if available
    test_metrics = state.get("test_validation_result", {})
    test_success_rate = test_metrics.get("success_rate", 0.0) 
    code_coverage = test_metrics.get("coverage_percentage", 0.0)
    
    # Get quality metrics if available
    quality_metrics = state.get("code_review_feedback", {})
    quality_score = quality_metrics.get("overall_score", 0.0) if quality_metrics else 0.0
    critical_issues = quality_metrics.get("critical_issues", []) if quality_metrics else []
    
    return {
        "workflow_id": state.get("workflow_id", "unknown"),
        "workflow_status": state.get("workflow_status", "unknown"),
        "phase_progress": phase_progress,
        "current_phase": current_phase_name,
        "phase_type": current_phase_type,
        "revision_count": current_revision,
        "elapsed_time": elapsed_str,
        "errors_count": errors_count,
        "quality_score": quality_score,
        "test_success_rate": f"{test_success_rate:.1f}%",
        "code_coverage": f"{code_coverage:.1f}%",
        "critical_issues": len(critical_issues)
    }

# Type aliases for better code readability
WorkflowState = AgentState
StateDict = Dict[str, Any]

# Constants for state field names (to avoid typos and ensure consistency)
class StateFields(str, Enum):
    """Constants for AgentState field names to ensure consistency across the codebase."""
    
    # Core Inputs & Plans
    BRD_CONTENT = "brd_content"
    WORKFLOW_CONFIG = "workflow_config"
    REQUIREMENTS_ANALYSIS = "requirements_analysis"
    TECH_STACK_RECOMMENDATION = "tech_stack_recommendation"
    SYSTEM_DESIGN = "system_design"
    IMPLEMENTATION_PLAN = "implementation_plan"

    # Consolidated Loop Results
    CODE_GENERATION_RESULT = "code_generation_result"
    CODE_REVIEW_FEEDBACK = "code_review_feedback" # Renamed from quality_analysis for clarity
    TEST_VALIDATION_RESULT = "test_validation_result"
      # Phase Control
    CURRENT_PHASE_NAME = "current_phase_name"
    CURRENT_PHASE_TYPE = "current_phase_type"
    CURRENT_PHASE_INDEX = "current_phase_index"
    REVISION_COUNTS = "revision_counts"
    
    # Individual component revision counters
    ARCHITECTURE_REVISION_COUNT = "architecture_revision_count"
    DATABASE_REVISION_COUNT = "database_revision_count"
    BACKEND_REVISION_COUNT = "backend_revision_count"
    FRONTEND_REVISION_COUNT = "frontend_revision_count"
    INTEGRATION_REVISION_COUNT = "integration_revision_count"
      # Final Output & Metadata
    ERRORS = "errors"
    WORKFLOW_SUMMARY = "workflow_summary"
    WORKFLOW_ID = "workflow_id"
    WORKFLOW_START_TIME = "workflow_start_time"
    WORKFLOW_STATUS = "workflow_status"
    TEMPERATURE_STRATEGY = "temperature_strategy"  # Added temperature strategy field
    
    # Conditional Edge Outcomes (for clarity in the graph definition)
    NEXT_PHASE = "next_phase"
    WORKFLOW_COMPLETE = "workflow_complete"
    APPROVE = "approve"
    REVISE = "revise"
