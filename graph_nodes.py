"""
LangGraph Node Functions for Multi-AI Development System.
Each node represents a specialized AI agent in the development workflow.
SIMPLIFIED: No decorators - BaseAgent handles all monitoring and tracking.
"""

import time
from typing import Dict, Any

from agent_state import AgentState
from agents.brd_analyst import BRDAnalystAgent
from agents.tech_stack_advisor import TechStackAdvisorAgent
from agents.system_designer import SystemDesignerAgent
from agents.planning_agent import PlanningAgent
from agents.code_generation import CodeGenerationAgent
from agents.test_case_generator import TestCaseGeneratorAgent
from agents.code_quality_agent import CodeQualityAgent
from agents.test_validation_agent import TestValidationAgent
import monitoring

# REMOVED: track_agent_execution decorator - BaseAgent handles all tracking

def brd_analysis_node(state: AgentState, config: dict) -> AgentState:
    """
    SIMPLIFIED: BRD Analysis node without decorator.
    BaseAgent.execute_with_monitoring handles all tracking and error handling.
    """
    start_time = time.time()
    
    # Get dependencies from config
    llm = config["configurable"]["llm"]
    memory = config["configurable"]["memory"] 
    rag_manager = config["configurable"].get("rag_manager")
    
    # Create agent
    agent = BRDAnalystAgent(
        llm=llm, 
        memory=memory, 
        rag_retriever=rag_manager.get_retriever() if rag_manager else None
    )
    
    # Execute with monitoring (BaseAgent handles all tracking)
    result = agent.execute_with_monitoring(
        agent.run,
        state["brd_content"]
    )
    
    # Update state with results
    state["requirements_analysis"] = result
    
    # Update execution tracking in state
    execution_time = time.time() - start_time
    state["agent_execution_times"][agent.agent_name] = execution_time
    
    # Check for errors and update state
    if result.get("project_overview", {}).get("project_name") == "Analysis Failed":
        state["errors"].append({
            "agent": agent.agent_name,
            "error": "BRD analysis failed to extract meaningful requirements",
            "timestamp": time.time()
        })
    
    return state

def tech_stack_recommendation_node(state: AgentState, config: dict) -> AgentState:
    """
    SIMPLIFIED: Tech Stack Recommendation node without decorator.
    """
    start_time = time.time()
    
    # Get dependencies from config
    llm = config["configurable"]["llm"]
    memory = config["configurable"]["memory"]
    rag_manager = config["configurable"].get("rag_manager")
    
    # Create agent
    agent = TechStackAdvisorAgent(
        llm=llm,
        memory=memory,
        rag_retriever=rag_manager.get_retriever() if rag_manager else None
    )
    
    # Execute with monitoring
    result = agent.execute_with_monitoring(
        agent.run,
        state["requirements_analysis"]
    )
    
    # Update state
    state["tech_stack_recommendation"] = result
    
    # Update execution tracking
    execution_time = time.time() - start_time
    state["agent_execution_times"][agent.agent_name] = execution_time
    
    # Check for errors
    if result.get("recommendation_summary") == "Default stack due to analysis error":
        state["errors"].append({
            "agent": agent.agent_name,
            "error": "Tech stack recommendation failed, using defaults",
            "timestamp": time.time()
        })
    
    return state

def system_design_node(state: AgentState, config: dict) -> AgentState:
    """
    SIMPLIFIED: System Design node without decorator.
    """
    start_time = time.time()
    
    # Get dependencies from config
    llm = config["configurable"]["llm"]
    memory = config["configurable"]["memory"]
    rag_manager = config["configurable"].get("rag_manager")
    
    # Create agent
    agent = SystemDesignerAgent(
        llm=llm,
        memory=memory,
        rag_retriever=rag_manager.get_retriever() if rag_manager else None
    )
    
    # Execute with monitoring
    result = agent.execute_with_monitoring(
        agent.run,
        state["requirements_analysis"],
        state["tech_stack_recommendation"]
    )
    
    # Update state
    state["system_design"] = result
    
    # Update execution tracking
    execution_time = time.time() - start_time
    state["agent_execution_times"][agent.agent_name] = execution_time
    
    # Check for errors
    if "generated due to design error" in result.get("architecture_overview", ""):
        state["errors"].append({
            "agent": agent.agent_name,
            "error": "System design failed, using default architecture",
            "timestamp": time.time()
        })
    
    return state

def planning_node(state: AgentState, config: dict) -> AgentState:
    """
    SIMPLIFIED: Planning node without decorator.
    """
    start_time = time.time()
    
    # Get dependencies from config
    llm = config["configurable"]["llm"]
    memory = config["configurable"]["memory"]
    rag_manager = config["configurable"].get("rag_manager")
    
    # Create agent
    agent = PlanningAgent(
        llm=llm,
        memory=memory,
        rag_retriever=rag_manager.get_retriever() if rag_manager else None
    )
    
    # Execute with monitoring
    result = agent.execute_with_monitoring(
        agent.run,
        state["requirements_analysis"],
        state["tech_stack_recommendation"],
        state["system_design"]
    )
    
    # Update state
    state["implementation_plan"] = result
    
    # Update execution tracking
    execution_time = time.time() - start_time
    state["agent_execution_times"][agent.agent_name] = execution_time
    
    # Check for errors
    if result.get("summary") == "Planning failed due to unexpected error":
        state["errors"].append({
            "agent": agent.agent_name,
            "error": "Implementation planning failed",
            "timestamp": time.time()
        })
    
    return state

def code_generation_node(state: AgentState, config: dict) -> AgentState:
    """Code Generation node handling structured response format."""
    start_time = time.time()
    
    # Get dependencies from config
    llm = config["configurable"]["llm"]
    memory = config["configurable"]["memory"] 
    code_execution_tool = config["configurable"]["code_execution_tool"]
    run_output_dir = config["configurable"]["run_output_dir"]
    rag_manager = config["configurable"].get("rag_manager")
    
    # FIXED: Create agent with correct constructor parameters
    agent = CodeGenerationAgent(
        llm=llm,
        memory=memory,
        output_dir=run_output_dir,  # FIXED: Use output_dir parameter name
        code_execution_tool=code_execution_tool,
        rag_retriever=rag_manager.get_retriever() if rag_manager else None
    )
    
    # Execute with monitoring
    result = agent.execute_with_monitoring(
        agent.run,
        state["requirements_analysis"],
        state["tech_stack_recommendation"], 
        state["system_design"],
        state["implementation_plan"]
    )
    
    # Handle structured response format
    state["code_generation_result"] = result
    
    # Update execution tracking
    execution_time = time.time() - start_time
    state["agent_execution_times"][agent.agent_name] = execution_time
    
    # Check for errors using structured response
    if result.get("status") == "error" or result.get("file_count", 0) == 0:
        state["errors"].append({
            "agent": agent.agent_name,
            "error": result.get("summary", "Code generation failed"),
            "timestamp": time.time()
        })
    
    return state

def test_case_generation_node(state: AgentState, config: dict) -> AgentState:
    """Test Case Generation node with correct parameter signature."""
    start_time = time.time()
    
    # Get dependencies from config
    llm = config["configurable"]["llm"]
    memory = config["configurable"]["memory"]
    run_output_dir = config["configurable"]["run_output_dir"]
    rag_manager = config["configurable"].get("rag_manager")
    
    # FIXED: Create agent with correct constructor parameters
    agent = TestCaseGeneratorAgent(
        llm=llm,
        memory=memory,
        output_dir=run_output_dir,  # FIXED: Use output_dir parameter name
        rag_retriever=rag_manager.get_retriever() if rag_manager else None
    )
    
    # FIXED: Pass parameters in correct order matching TestCaseGeneratorAgent.run signature:
    # run(self, code_generation_result: dict, brd_analysis: dict, tech_stack_recommendation: dict)
    result = agent.execute_with_monitoring(
        agent.run,
        state["code_generation_result"],          # code_generation_result (structured response)
        state["requirements_analysis"],           # brd_analysis
        state["tech_stack_recommendation"]        # tech_stack_recommendation
    )
    
    # Handle structured response format
    state["test_files"] = result
    
    # Update execution tracking
    execution_time = time.time() - start_time
    state["agent_execution_times"][agent.agent_name] = execution_time
    
    # Check for errors using structured response
    if result.get("status") == "error" or result.get("test_count", 0) == 0:
        state["errors"].append({
            "agent": agent.agent_name,
            "error": result.get("summary", "Test generation failed"),
            "timestamp": time.time()
        })
    
    return state

def code_quality_analysis_node(state: AgentState, config: dict) -> AgentState:
    """
    SIMPLIFIED: Code Quality Analysis node without decorator.
    """
    start_time = time.time()
    
    # Get dependencies from config
    llm = config["configurable"]["llm"]
    memory = config["configurable"]["memory"]
    code_execution_tool = config["configurable"]["code_execution_tool"]
    run_output_dir = config["configurable"]["run_output_dir"]
    rag_manager = config["configurable"].get("rag_manager")  # Get rag_manager
    
    # FIXED: Create agent with all required parameters
    agent = CodeQualityAgent(
        llm=llm,
        memory=memory,
        code_execution_tool=code_execution_tool,
        run_output_dir=run_output_dir,  # Add run_output_dir to constructor
        rag_retriever=rag_manager.get_retriever() if rag_manager else None  # Add rag_retriever
    )
    
    # FIXED: Execute with monitoring, passing correct parameters to match agent.run signature
    result = agent.execute_with_monitoring(
        agent.run,
        state["code_generation_result"],  # Pass code_generation_result as first parameter
        state["tech_stack_recommendation"]  # Pass tech_stack_recommendation as second parameter
    )
    
    # Update state with standardized field name
    state["quality_analysis"] = result
    
    # ENHANCED: Extract high-level metrics for decision making
    state["overall_quality_score"] = result.get("overall_quality_score", 0.0)
    state["has_critical_issues"] = result.get("has_critical_issues", True)
    
    # Update execution tracking
    execution_time = time.time() - start_time
    state["agent_execution_times"][agent.agent_name] = execution_time
    
    # Check for errors
    if result.get("summary") == "Quality analysis failed due to unexpected error":
        state["errors"].append({
            "agent": agent.agent_name,
            "error": "Code quality analysis failed",
            "timestamp": time.time()
        })
    
    return state

def test_validation_node(state: AgentState, config: dict) -> AgentState:
    """
    SIMPLIFIED: Test Validation node without decorator.
    """
    start_time = time.time()
    
    # Get dependencies from config
    llm = config["configurable"]["llm"]
    memory = config["configurable"]["memory"]
    code_execution_tool = config["configurable"]["code_execution_tool"]
    run_output_dir = config["configurable"]["run_output_dir"]
    rag_manager = config["configurable"].get("rag_manager")  # ADDED: Get rag_manager if needed
    
    # FIXED: Create agent with all required parameters
    agent = TestValidationAgent(
        llm=llm,
        memory=memory,
        code_execution_tool=code_execution_tool,
        # NOTE: Based on TestValidationAgent constructor in test_validation_agent.py,
        # it doesn't appear to need rag_retriever parameter, but if it does, 
        # it should be added here similar to other agents
    )
    
    # Execute with monitoring - assumes TestValidationAgent.run takes project_dir as parameter
    result = agent.execute_with_monitoring(
        agent.run,
        run_output_dir  # This is correct if TestValidationAgent.run expects project_dir as first parameter
    )
    
    # Update state with standardized field name
    state["test_validation_result"] = result
    
    # ENHANCED: Extract high-level metrics for decision making
    state["test_success_rate"] = result.get("test_success_rate", 0.0) / 100.0  # Convert percentage to decimal
    state["code_coverage_percentage"] = result.get("coverage_percentage", 0.0)
    
    # Update execution tracking
    execution_time = time.time() - start_time
    state["agent_execution_times"][agent.agent_name] = execution_time
    
    # Check for errors
    if result.get("overall_assessment") == "Unacceptable":
        state["errors"].append({
            "agent": agent.agent_name,
            "error": "Test validation assessment is unacceptable",
            "timestamp": time.time()
        })
    
    return state

def finalize_workflow(state: AgentState, config: dict) -> AgentState:
    """
    SIMPLIFIED: Finalize workflow and create summary.
    """
    start_time = time.time()
    
    monitoring.log_agent_activity("Workflow Finalizer", "Creating final workflow summary", "START")
    
    try:
        # Calculate total execution time
        total_execution_time = time.time() - state["workflow_start_time"]
        
        # Get final metrics
        final_quality_score = state.get("overall_quality_score", 0.0)
        final_test_success_rate = state.get("test_success_rate", 0.0)
        final_coverage_percentage = state.get("code_coverage_percentage", 0.0)
        
        # Determine overall status
        has_critical_issues = state.get("has_critical_issues", True)
        errors_count = len(state.get("errors", []))
        
        if errors_count == 0 and not has_critical_issues and final_quality_score >= 6.0:
            status = "completed_successfully"
        elif errors_count > 0 or has_critical_issues:
            status = "completed_with_issues"
        else:
            status = "completed_with_warnings"
        
        # Create comprehensive workflow summary
        workflow_summary = {
            "status": status,
            "total_execution_time": total_execution_time,
            "agent_execution_times": state.get("agent_execution_times", {}),
            "final_quality_score": final_quality_score,
            "final_test_success_rate": final_test_success_rate,
            "final_coverage_percentage": final_coverage_percentage,
            "total_errors": errors_count,
            "has_critical_issues": has_critical_issues,
            "summary": f"Workflow {status} in {total_execution_time:.2f}s with {errors_count} errors"
        }
        
        state["workflow_summary"] = workflow_summary
        
        monitoring.log_agent_activity(
            "Workflow Finalizer", 
            f"Workflow finalized: {status} in {total_execution_time:.2f}s", 
            "SUCCESS"
        )
        
    except Exception as e:
        monitoring.log_agent_activity(
            "Workflow Finalizer", 
            f"Failed to create workflow summary: {e}", 
            "ERROR"
        )
        
        # Create minimal summary on error
        state["workflow_summary"] = {
            "status": "error",
            "total_execution_time": time.time() - state["workflow_start_time"],
            "error": str(e)
        }
    
    return state

# ENHANCED: Decision functions using extracted metrics from graph_nodes.py
def should_retry_code_generation(state: AgentState) -> str:
    """
    ENHANCED: Decision function using extracted metrics and dynamic configuration.
    No hardcoded thresholds - uses state configuration.
    """
    # Get configuration from state
    quality_threshold = state.get("quality_threshold", 6.0)
    max_retries = state.get("max_code_gen_retries", 3)
    current_retry = state.get("current_code_gen_retry", 0)
    
    # Use extracted metrics from code quality analysis
    overall_quality_score = state.get("overall_quality_score", 0.0)
    has_critical_issues = state.get("has_critical_issues", True)
    
    monitoring.log_agent_activity(
        "Retry Decision", 
        f"Code generation retry check: quality={overall_quality_score}, "
        f"critical_issues={has_critical_issues}, retry={current_retry}/{max_retries}",
        "INFO"
    )
    
    # Check if we should retry
    should_retry = (
        (overall_quality_score < quality_threshold or has_critical_issues) and 
        current_retry < max_retries
    )
    
    if should_retry:
        monitoring.log_agent_activity("Retry Decision", 
            f"Code generation retry check: quality={quality_score}, critical_issues={has_critical_issues}, retry={current_retry}/{max_retries}", "INFO")
        return "retry_code_generation"  # CHANGE THIS FROM "retry_code" to "retry_code_generation"
    else:
        if current_retry >= max_retries:
            monitoring.log_agent_activity("Retry Decision", 
                f"Max retries reached ({max_retries}), continuing despite quality issues", "WARNING")
        return "continue"

def should_retry_tests(state: AgentState) -> str:
    """
    ENHANCED: Decision function for test retry using extracted metrics.
    """
    # Get configuration from state
    min_success_rate = state.get("min_success_rate", 0.7)
    min_coverage = state.get("min_coverage_percentage", 60.0)
    max_retries = state.get("max_test_retries", 2)
    current_retry = state.get("current_test_retry", 0)
    
    # Use extracted metrics from test validation
    test_success_rate = state.get("test_success_rate", 0.0)
    coverage_percentage = state.get("code_coverage_percentage", 0.0)
    
    monitoring.log_agent_activity(
        "Test Retry Decision", 
        f"Test retry check: success_rate={test_success_rate:.2%}, "
        f"coverage={coverage_percentage}%, retry={current_retry}/{max_retries}",
        "INFO"
    )
    
    # Check if we should retry
    should_retry = (
        (test_success_rate < min_success_rate or coverage_percentage < min_coverage) and 
        current_retry < max_retries
    )
    
    if should_retry:
        # Increment retry counter
        state["current_test_retry"] = current_retry + 1
        monitoring.log_agent_activity(
            "Test Retry Decision", 
            f"Retrying test generation (attempt {state['current_test_retry']})",
            "INFO"
        )
        return "retry_tests"
    else:
        monitoring.log_agent_activity(
            "Test Retry Decision", 
            "Proceeding to code quality analysis",
            "INFO"
        )
        return "continue"

def check_workflow_completion(state: AgentState) -> str:
    """
    ENHANCED: Final workflow completion check using extracted metrics.
    """
    # Get configuration
    quality_threshold = state.get("quality_threshold", 6.0)
    min_success_rate = state.get("min_success_rate", 0.7)
    min_coverage = state.get("min_coverage_percentage", 60.0)
    
    # Get extracted metrics
    overall_quality_score = state.get("overall_quality_score", 0.0)
    test_success_rate = state.get("test_success_rate", 0.0)
    coverage_percentage = state.get("code_coverage_percentage", 0.0)
    has_critical_issues = state.get("has_critical_issues", True)
    errors_count = len(state.get("errors", []))
    
    monitoring.log_agent_activity(
        "Completion Check", 
        f"Final check: quality={overall_quality_score}, success_rate={test_success_rate:.2%}, "
        f"coverage={coverage_percentage}%, critical_issues={has_critical_issues}, errors={errors_count}",
        "INFO"
    )
    
    # Determine completion status
    quality_acceptable = overall_quality_score >= quality_threshold and not has_critical_issues
    tests_acceptable = test_success_rate >= min_success_rate and coverage_percentage >= min_coverage
    
    if quality_acceptable and tests_acceptable and errors_count == 0:
        monitoring.log_agent_activity("Completion Check", "Workflow completed successfully", "SUCCESS")
        return "complete"
    elif errors_count > 5 or overall_quality_score < 3.0:  # Severe failure threshold
        monitoring.log_agent_activity("Completion Check", "Workflow failed with severe issues", "ERROR")
        return "failed"
    else:
        monitoring.log_agent_activity("Completion Check", "Workflow needs iteration", "WARNING")
        return "needs_iteration"

# ============= MODULE FUNCTION STUBS FOR MODULAR WORKFLOW =============
# These are placeholders for future implementation of modular workflow components

def requirements_module(state: AgentState, config: dict) -> AgentState:
    """
    PLACEHOLDER: Requirements module that combines BRD analysis and tech stack recommendation.
    
    This module will be implemented in a future version to handle the requirements phase
    of the development process in a modular workflow.
    """
    monitoring.log_agent_activity("Requirements Module", "Module not yet implemented", "WARNING")
    
    # For now, just call the individual nodes sequentially
    state = brd_analysis_node(state, config)
    state = tech_stack_recommendation_node(state, config)
    
    return state


def design_module(state: AgentState, config: dict) -> AgentState:
    """
    PLACEHOLDER: Design module that handles system design and planning.
    
    This module will be implemented in a future version to handle the design phase
    of the development process in a modular workflow.
    """
    monitoring.log_agent_activity("Design Module", "Module not yet implemented", "WARNING")
    
    # For now, just call the individual nodes sequentially
    state = system_design_node(state, config)
    state = planning_node(state, config)
    
    return state


def implementation_module(state: AgentState, config: dict) -> AgentState:
    """
    PLACEHOLDER: Implementation module that handles code generation and testing.
    
    This module will be implemented in a future version to handle the implementation phase
    of the development process in a modular workflow.
    """
    monitoring.log_agent_activity("Implementation Module", "Module not yet implemented", "WARNING")
    
    # For now, just call the individual nodes sequentially
    state = code_generation_node(state, config)
    state = test_case_generation_node(state, config)
    
    return state


def quality_module(state: AgentState, config: dict) -> AgentState:
    """
    PLACEHOLDER: Quality module that handles code quality analysis and test validation.
    
    This module will be implemented in a future version to handle the quality assessment phase
    of the development process in a modular workflow.
    """
    monitoring.log_agent_activity("Quality Module", "Module not yet implemented", "WARNING")
    
    # For now, just call the individual nodes sequentially
    state = code_quality_analysis_node(state, config)
    state = test_validation_node(state, config)
    
    return state


def should_iterate_implementation(state: AgentState) -> str:
    """
    PLACEHOLDER: Decision function to determine if implementation needs another iteration.
    
    This function will be implemented in a future version to make decisions about iteration
    needs in a modular workflow.
    """
    # For now, a simple implementation based on quality score and test success
    quality_threshold = state.get("quality_threshold", 6.0)
    min_success_rate = state.get("min_success_rate", 0.7)
    
    overall_quality_score = state.get("overall_quality_score", 0.0)
    test_success_rate = state.get("test_success_rate", 0.0)
    
    monitoring.log_agent_activity(
        "Implementation Iteration Decision", 
        f"Quality: {overall_quality_score}, Test success: {test_success_rate:.2%}", 
        "INFO"
    )
    
    # If either quality or tests are below threshold, iterate
    if overall_quality_score < quality_threshold or test_success_rate < min_success_rate:
        return "iterate"
    else:
        return "finalize"