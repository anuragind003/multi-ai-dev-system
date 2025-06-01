"""
Agent State Management for Multi-AI Development System.
Defines the centralized state structure using LangGraph's TypedDict.
ENHANCED: Integrated with AdvancedWorkflowConfig for sophisticated configuration management.
"""

from typing import Dict, Any, List, Optional, TypedDict
from typing_extensions import NotRequired
from config import AdvancedWorkflowConfig

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
    current_code_gen_retry: int  # Current code generation retry count
    current_test_retry: int  # Current test retry count
    
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
    workflow_summary: NotRequired[Dict[str, Any]]  # Final workflow summary (added by finalize_workflow)
    
    # ==================== DEBUG AND CONTROL FLAGS ====================
    verbose: bool  # Enable verbose output
    debug: bool  # Enable debug mode

def create_initial_agent_state(
    brd_content: str, 
    workflow_config: AdvancedWorkflowConfig
) -> AgentState:
    """
    ENHANCED: Create initial agent state using AdvancedWorkflowConfig.
    
    This function creates a properly initialized AgentState with all required
    fields populated from the sophisticated configuration system.
    
    Args:
        brd_content: Business Requirements Document content
        workflow_config: Advanced workflow configuration object
        
    Returns:
        AgentState: Properly initialized state dictionary
    """
    import time
    
    # Convert workflow config to dictionary for storage in state
    config_dict = workflow_config.to_dict()
    
    return AgentState(
        # Core input
        brd_content=brd_content,
        
        # Configuration from AdvancedWorkflowConfig
        workflow_config=config_dict,
        quality_threshold=workflow_config.min_quality_score,
        min_success_rate=workflow_config.min_success_rate,
        min_coverage_percentage=workflow_config.min_coverage_percentage,
        max_code_gen_retries=workflow_config.max_code_gen_retries,
        max_test_retries=workflow_config.max_test_retries,
        
        # Retry tracking (initialized)
        current_code_gen_retry=0,
        current_test_retry=0,
        
        # Agent outputs (empty initially, populated by agents)
        requirements_analysis={},
        tech_stack_recommendation={},
        system_design={},
        implementation_plan={},
        code_generation_result={},
        test_files={},
        quality_analysis={},
        test_validation_result={},
        
        # Extracted metrics (conservative defaults)
        overall_quality_score=0.0,
        test_success_rate=0.0,
        code_coverage_percentage=0.0,
        has_critical_issues=True,  # Conservative default
        
        # Workflow metadata
        workflow_start_time=time.time(),
        agent_execution_times={},
        errors=[],
        
        # Debug and control flags
        verbose=workflow_config.verbose_logging,
        debug=workflow_config.debug_mode
    )

def validate_agent_state(state: AgentState) -> List[str]:
    """
    Validate the agent state structure and return any validation errors.
    
    Args:
        state: Agent state to validate
        
    Returns:
        List[str]: List of validation error messages (empty if valid)
    """
    errors = []
    
    # Required string fields
    required_string_fields = ["brd_content"]
    for field in required_string_fields:
        if not isinstance(state.get(field), str) or not state[field].strip():
            errors.append(f"Field '{field}' must be a non-empty string")
    
    # Required numeric fields with ranges
    numeric_validations = [
        ("quality_threshold", 0.0, 10.0),
        ("min_success_rate", 0.0, 1.0),
        ("min_coverage_percentage", 0.0, 100.0),
        ("overall_quality_score", 0.0, 10.0),
        ("test_success_rate", 0.0, 1.0),
        ("code_coverage_percentage", 0.0, 100.0),
    ]
    
    for field, min_val, max_val in numeric_validations:
        value = state.get(field)
        if not isinstance(value, (int, float)):
            errors.append(f"Field '{field}' must be a number")
        elif not (min_val <= value <= max_val):
            errors.append(f"Field '{field}' must be between {min_val} and {max_val}")
    
    # Required integer fields
    required_int_fields = [
        "max_code_gen_retries", "max_test_retries", 
        "current_code_gen_retry", "current_test_retry"
    ]
    for field in required_int_fields:
        value = state.get(field)
        if not isinstance(value, int) or value < 0:
            errors.append(f"Field '{field}' must be a non-negative integer")
    
    # Required dictionary fields
    required_dict_fields = [
        "workflow_config", "requirements_analysis", "tech_stack_recommendation",
        "system_design", "implementation_plan", "code_generation_result",
        "test_files", "quality_analysis", "test_validation_result",
        "agent_execution_times"
    ]
    for field in required_dict_fields:
        if not isinstance(state.get(field), dict):
            errors.append(f"Field '{field}' must be a dictionary")
    
    # Required list field
    if not isinstance(state.get("errors"), list):
        errors.append("Field 'errors' must be a list")
    
    # Required boolean fields
    required_bool_fields = ["has_critical_issues", "verbose", "debug"]
    for field in required_bool_fields:
        if not isinstance(state.get(field), bool):
            errors.append(f"Field '{field}' must be a boolean")
    
    # Workflow start time validation
    if not isinstance(state.get("workflow_start_time"), (int, float)):
        errors.append("Field 'workflow_start_time' must be a timestamp")
    
    return errors

def get_state_summary(state: AgentState) -> Dict[str, Any]:
    """
    Get a summary of the current agent state for monitoring and debugging.
    
    Args:
        state: Agent state to summarize
        
    Returns:
        Dict[str, Any]: Summary information
    """
    import time
    
    # Calculate workflow progress
    total_agents = 8  # Number of main agents in the workflow
    completed_agents = sum(1 for key in [
        "requirements_analysis", "tech_stack_recommendation", "system_design",
        "implementation_plan", "code_generation_result", "test_files",
        "quality_analysis", "test_validation_result"
    ] if state.get(key))
    
    progress_percentage = (completed_agents / total_agents) * 100
    
    # Get current execution time
    current_time = time.time()
    elapsed_time = current_time - state.get("workflow_start_time", current_time)
    
    return {
        "workflow_progress": {
            "completed_agents": completed_agents,
            "total_agents": total_agents,
            "progress_percentage": progress_percentage,
            "elapsed_time": elapsed_time
        },
        "current_metrics": {
            "quality_score": state.get("overall_quality_score", 0.0),
            "test_success_rate": state.get("test_success_rate", 0.0),
            "coverage_percentage": state.get("code_coverage_percentage", 0.0),
            "has_critical_issues": state.get("has_critical_issues", True)
        },
        "retry_status": {
            "code_gen_retries": f"{state.get('current_code_gen_retry', 0)}/{state.get('max_code_gen_retries', 0)}",
            "test_retries": f"{state.get('current_test_retry', 0)}/{state.get('max_test_retries', 0)}"
        },
        "errors_count": len(state.get("errors", [])),
        "configuration": {
            "environment": state.get("workflow_config", {}).get("environment", "unknown"),
            "quality_threshold": state.get("quality_threshold", 0.0),
            "debug_mode": state.get("debug", False)
        }
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
    MIN_COVERAGE_PERCENTAGE = "min_coverage_percentage"
    
    # Retry tracking
    MAX_CODE_GEN_RETRIES = "max_code_gen_retries"
    MAX_TEST_RETRIES = "max_test_retries"
    CURRENT_CODE_GEN_RETRY = "current_code_gen_retry"  # FIXED: Changed from "current_code_gen_retries" to match AgentState field
    CURRENT_TEST_RETRY = "current_test_retry"
    
    # Agent outputs (STANDARDIZED names)
    REQUIREMENTS_ANALYSIS = "requirements_analysis"
    TECH_STACK_RECOMMENDATION = "tech_stack_recommendation"
    SYSTEM_DESIGN = "system_design"
    IMPLEMENTATION_PLAN = "implementation_plan"
    CODE_GENERATION_RESULT = "code_generation_result"
    TEST_FILES = "test_files"  # STANDARDIZED
    QUALITY_ANALYSIS = "quality_analysis"  # STANDARDIZED
    TEST_VALIDATION_RESULT = "test_validation_result"  # STANDARDIZED
    
    # Extracted metrics
    OVERALL_QUALITY_SCORE = "overall_quality_score"
    TEST_SUCCESS_RATE = "test_success_rate"
    CODE_COVERAGE_PERCENTAGE = "code_coverage_percentage"
    HAS_CRITICAL_ISSUES = "has_critical_issues"
    
    # Workflow metadata
    WORKFLOW_START_TIME = "workflow_start_time"
    AGENT_EXECUTION_TIMES = "agent_execution_times"
    ERRORS = "errors"
    WORKFLOW_SUMMARY = "workflow_summary"
    
    # Control flags
    VERBOSE = "verbose"
    DEBUG = "debug"