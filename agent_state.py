"""
Agent State Management for Multi-AI Development System.
Defines the centralized state structure using LangGraph's TypedDict.
ENHANCED: Integrated with AdvancedWorkflowConfig for sophisticated configuration management.
"""

from typing import Dict, Any, List, Optional, TypedDict, Union
# Remove NotRequired import - we'll use a different approach
from config import AdvancedWorkflowConfig
import time

class AgentState(TypedDict):
    """
    ENHANCED: Centralized state structure for the Multi-AI Development System workflow.
    Now fully integrated with AdvancedWorkflowConfig for consistent configuration management.
    
    This TypedDict defines the complete state that flows through all agent nodes
    in the LangGraph workflow, ensuring type safety and consistency.
    """
    
    # ==================== CORE INPUTS ====================
    brd_content: str  # STANDARDIZED: Business Requirements Document content
    
    # ==================== CONFIGURATION (from AdvancedWorkflowConfig) ====================
    workflow_config: Dict[str, Any]  # Complete workflow configuration dictionary
    
    # Quality thresholds (extracted from workflow_config for easy access)
    quality_threshold: float  # Minimum code quality score (0-10)
    min_success_rate: float  # Minimum test success rate (0.0-1.0)
    min_coverage_percentage: float  # Minimum code coverage percentage
    
    # Retry configuration
    max_code_gen_retries: int  # Maximum code generation retries
    max_test_retries: int  # Maximum test generation retries
    
    # Phase tracking for phased workflow
    current_code_gen_retry: int  # Current code generation retry count
    current_test_retry: int  # Current test retry count
    
    # ==================== PHASE TRACKING ====================
    current_phase_index: int  # Index of current phase in development_phases
    completed_phases: List[str]  # List of completed phase IDs
    phase_code_results: Dict[str, Dict[str, Any]]  # Phase ID -> code generation result
    phase_execution_times: Dict[str, float]  # Phase ID -> execution time
    
    # ==================== AGENT OUTPUTS ====================
    # All agent outputs use STANDARDIZED field names
    requirements_analysis: Dict[str, Any]  # From BRD Analyst Agent
    tech_stack_recommendation: Dict[str, Any]  # From Tech Stack Advisor Agent
    system_design: Dict[str, Any]  # From System Designer Agent
    implementation_plan: Dict[str, Any]  # From Planning Agent
    code_generation_result: Dict[str, Any]  # From Code Generation Agent
    test_files: Dict[str, Any]  # STANDARDIZED: From Test Case Generator Agent
    quality_analysis: Dict[str, Any]  # STANDARDIZED: From Code Quality Agent
    test_validation_result: Dict[str, Any]  # STANDARDIZED: From Test Validation Agent
    
    # ==================== EXTRACTED METRICS ====================
    # High-level metrics extracted from agent outputs for decision making
    overall_quality_score: float  # Extracted from quality_analysis
    test_success_rate: float  # Extracted from test_validation_result (as decimal 0.0-1.0)
    code_coverage_percentage: float  # Extracted from test_validation_result
    has_critical_issues: bool  # Extracted from quality_analysis
    
    # ==================== WORKFLOW METADATA ====================
    workflow_start_time: float  # Timestamp when workflow started
    agent_execution_times: Dict[str, float]  # Agent name -> execution time mapping
    errors: List[Dict[str, Any]]  # List of errors encountered during execution
    
    # ==================== OPTIONAL WORKFLOW SUMMARY ====================
    # Instead of NotRequired, use Dict or None for optional fields
    workflow_summary: Dict[str, Any]  # Final workflow summary (added by finalize_workflow)
    
    # ==================== DEBUG AND CONTROL FLAGS ====================
    verbose: bool  # Enable verbose output
    debug: bool  # Enable debug mode

def create_initial_agent_state(
    brd_content: str, 
    workflow_config: AdvancedWorkflowConfig
) -> AgentState:
    """
    ENHANCED: Create initial state for the workflow using AdvancedWorkflowConfig.
    
    Args:
        brd_content: Business Requirements Document content
        workflow_config: Advanced workflow configuration object
        
    Returns:
        AgentState: Initial state for the workflow
    """
    return AgentState(
        # Core inputs
        brd_content=brd_content,
        
        # Configuration
        workflow_config=workflow_config.to_dict(),
        quality_threshold=workflow_config.min_quality_score,  # FIXED: Use min_quality_score instead of quality_threshold
        min_success_rate=workflow_config.min_success_rate,
        min_coverage_percentage=workflow_config.min_coverage_percentage,  # FIXED: Use min_coverage_percentage instead of min_coverage
        max_code_gen_retries=workflow_config.max_code_gen_retries,
        max_test_retries=workflow_config.max_test_retries,
        
        # Initialize retry counters
        current_code_gen_retry=0,
        current_test_retry=0,
        
        # Phase tracking for phased code generation
        current_phase_index=0,
        completed_phases=[],
        phase_code_results={},
        phase_execution_times={},
        
        # Agent results
        requirements_analysis={},
        tech_stack_recommendation={},
        system_design={},
        implementation_plan={},
        code_generation_result={},
        test_files={},
        quality_analysis={},
        test_validation_result={},
        
        # Metrics
        overall_quality_score=0.0,
        test_success_rate=0.0,
        code_coverage_percentage=0.0,
        has_critical_issues=True,
        
        # Workflow tracking
        workflow_start_time=time.time(),
        agent_execution_times={},
        errors=[],
        
        # Initialize workflow_summary with empty dict (no longer NotRequired)
        workflow_summary={},
        
        # Logging
        verbose=workflow_config.verbose_logging,
        debug=workflow_config.debug_mode
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
    
    # Get workflow completion metrics
    errors_count = len(state.get("errors", []))
    
    # Get completed agents (approximate by checking non-empty results)
    agent_results = {
        "BRD Analysis": bool(state.get("requirements_analysis")),
        "Tech Stack": bool(state.get("tech_stack_recommendation")),
        "System Design": bool(state.get("system_design")),
        "Planning": bool(state.get("implementation_plan")),
        "Code Generation": bool(state.get("code_generation_result")), 
        "Quality Analysis": bool(state.get("quality_analysis")),
        "Tests": bool(state.get("test_files")),
        "Test Validation": bool(state.get("test_validation_result"))
    }
    
    completed_agents = sum(1 for agent, completed in agent_results.items() if completed)
    total_agents = len(agent_results)
    
    # Create elapsed time string
    elapsed_time = time.time() - state.get("workflow_start_time", time.time())
    elapsed_str = f"{elapsed_time:.2f}s"
    
    # Get phase information for phased workflow
    current_phase = state.get("current_phase_index", 0)
    total_phases = len(state.get("implementation_plan", {}).get("development_phases", []))
    
    return {
        "completed_agents": f"{completed_agents}/{total_agents}",
        "current_phase": f"{current_phase}/{total_phases}" if total_phases > 0 else "N/A",
        "elapsed_time": elapsed_str,
        "errors_count": errors_count,
        "quality_score": state.get("overall_quality_score", 0.0),
        "test_success": f"{state.get('test_success_rate', 0.0) * 100:.1f}%",
        "has_critical_issues": state.get("has_critical_issues", True),
    }

# Type aliases for better code readability
WorkflowState = AgentState
StateDict = Dict[str, Any]

# Constants for state field names (to avoid typos and ensure consistency)
class StateFields:
    """Constants for AgentState field names to ensure consistency across the codebase."""
    
    # Core inputs
    BRD_CONTENT = "brd_content"
    
    # Configuration
    WORKFLOW_CONFIG = "workflow_config"
    QUALITY_THRESHOLD = "quality_threshold"
    MIN_SUCCESS_RATE = "min_success_rate"
    MIN_COVERAGE = "min_coverage_percentage"
    MAX_CODE_GEN_RETRIES = "max_code_gen_retries"
    MAX_TEST_RETRIES = "max_test_retries"
    
    # Retry counters
    CURRENT_CODE_GEN_RETRY = "current_code_gen_retries"
    CURRENT_TEST_RETRY = "current_test_retry"
    
    # Phase tracking
    CURRENT_PHASE_INDEX = "current_phase_index"
    COMPLETED_PHASES = "completed_phases"
    PHASE_CODE_RESULTS = "phase_code_results"
    PHASE_EXECUTION_TIMES = "phase_execution_times"
    
    # Agent results
    REQUIREMENTS_ANALYSIS = "requirements_analysis"
    TECH_STACK_RECOMMENDATION = "tech_stack_recommendation"
    SYSTEM_DESIGN = "system_design"
    IMPLEMENTATION_PLAN = "implementation_plan"
    CODE_GENERATION_RESULT = "code_generation_result"
    TEST_FILES = "test_files"
    QUALITY_ANALYSIS = "quality_analysis"
    TEST_VALIDATION_RESULT = "test_validation_result"
    
    # Extracted metrics
    OVERALL_QUALITY_SCORE = "overall_quality_score"
    TEST_SUCCESS_RATE = "test_success_rate"
    CODE_COVERAGE_PERCENTAGE = "code_coverage_percentage"
    HAS_CRITICAL_ISSUES = "has_critical_issues"
    
    # Workflow tracking
    WORKFLOW_START_TIME = "workflow_start_time"
    AGENT_EXECUTION_TIMES = "agent_execution_times"
    ERRORS = "errors"
    
    # Optional workflow summary
    WORKFLOW_SUMMARY = "workflow_summary"
    
    # Debug and control flags
    VERBOSE = "verbose"
    DEBUG = "debug"