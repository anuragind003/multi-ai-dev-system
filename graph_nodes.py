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
import shutil  # New import for file operations

from utils.websocket_callback import create_websocket_callback

_AGENT_CACHE = {}  # Module-level cache for agents

# Module-level cache for BRD analysis (fallback if llm_cache is not available)
_LAST_BRD_ANALYSIS = None

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
from agents.brd_analyst_react import BRDAnalystReActAgent  # Simplified BRD Analyst (no ReAct)
from agents.tech_stack_advisor_simplified import TechStackAdvisorSimplifiedAgent
from agents.system_designer_simplified import SystemDesignerSimplifiedAgent
from agents.planning.plan_compiler_simplified import PlanCompilerSimplifiedAgent
from agents.code_quality_agent import CodeQualityAgent
# NOTE: CodeOptimizerAgent removed - not needed in unified workflow

# Import standardized human approval model
from models.human_approval import ApprovalPayload

# Import data contracts
from models.data_contracts import ComprehensiveTechStackOutput

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
    if "rag_manager" in config["configurable"]:
        rag_manager = config["configurable"].get("rag_manager")
        if rag_manager:
            agent_args["rag_retriever"] = rag_manager.get_retriever()
            
    # Add output directory if the agent accepts it and it's available
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

    # Remove 'verbose' if present, as create_json_chat_agent no longer accepts it
    agent_args.pop("verbose", None)

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
    """Parse the BRD to extract requirements and convert to a structured format."""
    logger.info("Executing BRD analysis node with streamlined agent")
    
    # The new agent is more efficient and doesn't need complex skipping logic.
    agent = create_agent_with_temperature(BRDAnalystReActAgent, "BRD Analyst Agent", config)
    
    # The streamlined agent now directly calls the tool and returns the structured data
    summary_output = agent.run(raw_brd=state[StateFields.BRD_CONTENT])

    # Debug: Log the raw output from the agent
    logger.info(f"Raw agent output type: {type(summary_output)}")
    logger.info(f"Raw agent output keys: {list(summary_output.keys()) if isinstance(summary_output, dict) else 'Not a dict'}")

    # Store in shared memory
    memory_hub = config.get("configurable", {}).get("memory_hub")
    if memory_hub:
        memory_hub.set('brd_analysis', summary_output, context='brd_analysis')

    # The streamlined agent returns the tool output directly
    if isinstance(summary_output, dict):
        if "error" in summary_output:
            # Handle error case
            logger.error(f"BRD analysis failed: {summary_output}")
            requirements_analysis = {}
        else:
            # The output should be the direct BRDRequirementsAnalysis structure
            requirements_analysis = summary_output
            logger.info("Using direct tool output as requirements analysis")
    else:
        # Fallback for unexpected output format
        logger.warning(f"Unexpected BRD analysis output format: {type(summary_output)}")
        requirements_analysis = {}

    logger.info(f"Final requirements_analysis keys: {list(requirements_analysis.keys()) if isinstance(requirements_analysis, dict) else 'Not a dict'}")
    if isinstance(requirements_analysis, dict):
        func_reqs = requirements_analysis.get('functional_requirements', [])
        non_func_reqs = requirements_analysis.get('non_functional_requirements', [])
        logger.info(f"Functional requirements count: {len(func_reqs)}")
        logger.info(f"Non-functional requirements count: {len(non_func_reqs)}")
        if func_reqs:
            logger.info(f"First functional requirement: {func_reqs[0]}")

    logger.info(f"BRD analysis result structure: {list(requirements_analysis.keys()) if isinstance(requirements_analysis, dict) else 'Not a dict'}")

    return {
        StateFields.REQUIREMENTS_ANALYSIS: requirements_analysis,
    }

def tech_stack_recommendation_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """Recommend appropriate technology stack based on the requirements."""
    logger.info("Executing tech stack recommendation node with simplified agent")
    
    agent = create_agent_with_temperature(TechStackAdvisorSimplifiedAgent, "Tech Stack Advisor Agent", config)
    
    # Pause to respect API rate limits before executing the agent
    time.sleep(config.get("api_call_delay_seconds", 4.0))
    logger.info(f"Pausing for {config.get('api_call_delay_seconds', 4.0)} seconds to respect API rate limits...")
    
    try:
        result = agent.run(raw_brd=state[StateFields.BRD_CONTENT], requirements_analysis=state[StateFields.REQUIREMENTS_ANALYSIS])
        
        logger.info(f"Tech stack agent returned result type: {type(result)}")
        if isinstance(result, dict):
            logger.info(f"Tech stack result keys: {list(result.keys())}")
            # Check for errors
            if "error" in result:
                logger.error(f"Tech stack agent returned error: {result}")
                return {StateFields.TECH_STACK_RECOMMENDATION: result}
            else:
                logger.info("Tech stack agent completed successfully, propagating result")
                return {StateFields.TECH_STACK_RECOMMENDATION: result}
        elif hasattr(result, 'model_dump'):
            # Handle Pydantic models (like ComprehensiveTechStackOutput) by converting to dict
            logger.info(f"Converting {type(result).__name__} to dictionary using model_dump()")
            result_dict = result.model_dump()
            logger.info(f"Converted tech stack result keys: {list(result_dict.keys())}")
            return {StateFields.TECH_STACK_RECOMMENDATION: result_dict}
        else:
            logger.warning(f"Tech stack agent returned non-dict, non-Pydantic result: {type(result)}")
            return {StateFields.TECH_STACK_RECOMMENDATION: {"tech_stack_result": result}}
            
    except Exception as e:
        logger.error(f"Error in tech stack recommendation node: {str(e)}", exc_info=True)
        return {StateFields.TECH_STACK_RECOMMENDATION: {
            "error": "node_execution_error",
            "details": str(e)
        }}

def system_design_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """Create a comprehensive system design based on requirements and tech stack."""
    logger.info("Executing system design node with streamlined agent")
    
    agent = create_agent_with_temperature(SystemDesignerSimplifiedAgent, "System Designer Agent", config)

    # Pause to respect API rate limits
    time.sleep(config.get("api_call_delay_seconds", 4.0))
    logger.info(f"Pausing for {config.get('api_call_delay_seconds', 4.0)} seconds to respect API rate limits...")

    # Retrieve the tech stack recommendation, which is now a ComprehensiveTechStackOutput
    tech_stack_output_raw = state[StateFields.TECH_STACK_RECOMMENDATION]
    
    # Attempt to parse into the Pydantic model for robust access
    try:
        tech_stack_output = ComprehensiveTechStackOutput(**tech_stack_output_raw)
    except Exception as e:
        logger.error(f"Failed to parse tech_stack_recommendation into ComprehensiveTechStackOutput in system_design_node: {e}", exc_info=True)
        tech_stack_output = ComprehensiveTechStackOutput() # Fallback to empty model

    # Extract the selected stack, if available, otherwise pass the raw recommendation
    selected_tech_stack_for_agent = tech_stack_output.selected_stack.model_dump() if tech_stack_output.selected_stack else tech_stack_output.model_dump()

    result = agent.run(
        requirements_analysis=state[StateFields.REQUIREMENTS_ANALYSIS],
        tech_stack_recommendation=selected_tech_stack_for_agent
    )
    
    return {StateFields.SYSTEM_DESIGN: result}

def planning_node(state: AgentState, config: dict) -> Dict[str, Any]:
    logger.info("Executing planning node with streamlined agent")
    agent = create_agent_with_temperature(PlanCompilerSimplifiedAgent, "Plan Compiler Agent", config)

    # Pause to respect API rate limits
    time.sleep(config.get("api_call_delay_seconds", 4.0))
    logger.info(f"Pausing for {config.get('api_call_delay_seconds', 4.0)} seconds to respect API rate limits...")

    # Ensure tech stack recommendation is properly serializable
    tech_stack_data = state["tech_stack_recommendation"]
    if hasattr(tech_stack_data, 'model_dump'):
        tech_stack_data = tech_stack_data.model_dump()
    elif not isinstance(tech_stack_data, dict):
        logger.warning(f"Tech stack data is not serializable: {type(tech_stack_data)}, converting to string")
        tech_stack_data = str(tech_stack_data)

    result = agent.run(
        requirements_analysis=state["requirements_analysis"],
        tech_stack_recommendation=tech_stack_data,
        system_design=state["system_design"]
    )
    return {StateFields.IMPLEMENTATION_PLAN: result}

# --- Phased Loop Nodes ---

def work_item_iterator_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """Iterate through the work item backlog and set up the current item for execution."""
    logger.info("Executing work item iterator node")
    
    plan_output = state.get(StateFields.IMPLEMENTATION_PLAN, {})
    logger.info(f"WORK_ITEM_ITERATOR: Plan output type: {type(plan_output)}")
    
    # Handle ComprehensiveImplementationPlanOutput properly
    work_items = []
    if hasattr(plan_output, 'plan'):
        # This is a ComprehensiveImplementationPlanOutput Pydantic model
        implementation_plan = plan_output.plan
        if hasattr(implementation_plan, 'phases'):
            # Extract work items from phases - this is the correct structure
            for phase in implementation_plan.phases:
                if isinstance(phase, dict) and 'work_items' in phase:
                    work_items.extend(phase['work_items'])
                elif hasattr(phase, 'work_items') and phase.work_items:
                    work_items.extend(phase.work_items)
        # Add a fallback to check for work_items directly on the plan (shouldn't happen with current structure)
        elif hasattr(implementation_plan, 'work_items') and implementation_plan.work_items:
            work_items = implementation_plan.work_items
            
        # Check if this might be a WorkItemBacklog wrapped in the plan_output
        if not work_items and hasattr(plan_output, 'work_items'):
            logger.info("Found work_items directly on plan_output (WorkItemBacklog format)")
            work_items = plan_output.work_items
            
    elif isinstance(plan_output, dict):
        # Handle dictionary format (legacy or converted)
        plan = plan_output.get("plan", {})
        if isinstance(plan, dict) and "phases" in plan:
            # Extract work items from phases in dictionary format
            for phase in plan["phases"]:
                if isinstance(phase, dict) and 'work_items' in phase:
                    work_items.extend(phase['work_items'])
        elif "work_items" in plan_output:
            work_items = plan_output["work_items"]
        # Check if this is a WorkItemBacklog structure at the root level
        elif "work_items" in plan:
            work_items = plan["work_items"]
    
    logger.info(f"WORK_ITEM_ITERATOR: Found {len(work_items)} work items total")
    
    # Debug: Log the structure of work items found
    if work_items:
        logger.info(f"WORK_ITEM_ITERATOR: First work item structure: {list(work_items[0].keys()) if isinstance(work_items[0], dict) else 'Pydantic model'}")
        for i, item in enumerate(work_items[:3]):  # Log first 3 items
            item_id = item.get('id') if isinstance(item, dict) else getattr(item, 'id', 'unknown')
            logger.info(f"WORK_ITEM_ITERATOR: Work item {i+1}: {item_id}")
    else:
        logger.warning(f"WORK_ITEM_ITERATOR: No work items found. Plan output structure: {type(plan_output)}")
        if hasattr(plan_output, 'plan'):
            logger.info(f"WORK_ITEM_ITERATOR: Plan structure: phases={len(plan_output.plan.phases) if hasattr(plan_output.plan, 'phases') else 'N/A'}")
            if hasattr(plan_output.plan, 'phases'):
                for i, phase in enumerate(plan_output.plan.phases):
                    phase_items = phase.get('work_items', []) if isinstance(phase, dict) else getattr(phase, 'work_items', [])
                    logger.info(f"WORK_ITEM_ITERATOR: Phase {i+1} has {len(phase_items)} work items")
    
    if not work_items:
        logger.warning(f"No work items found in the implementation plan. Plan structure: {type(plan_output)} with attributes: {dir(plan_output) if hasattr(plan_output, '__dict__') else 'N/A'}")
        # Signal completion
        return {
            StateFields.WORKFLOW_COMPLETE: True
        }

    completed_work_items = state.get(StateFields.COMPLETED_WORK_ITEMS, [])
    completed_ids = set()
    
    # FIXED: Handle both string IDs and object formats like the async version
    if isinstance(completed_work_items, (list, set)):
        for item in completed_work_items:
            # Handle both string IDs and object formats
            if isinstance(item, str):
                # If it's already a string ID, use it directly
                completed_ids.add(item)
            elif isinstance(item, dict) and 'id' in item:
                # If it's a dict with an 'id' key
                completed_ids.add(item['id'])
            elif hasattr(item, 'id'):
                # If it's an object with an 'id' attribute
                completed_ids.add(item.id)
            else:
                # Log unrecognized format but continue
                logger.warning(f"WORK_ITEM_ITERATOR: Unrecognized completed item format: {item}")
    
    logger.info(f"WORK_ITEM_ITERATOR: Found {len(completed_ids)} completed work items: {completed_ids}")

    # Find the next pending work item whose dependencies are met
    next_work_item = None
    for item in work_items:
        # Handle both dict and Pydantic model formats
        item_id = item['id'] if isinstance(item, dict) else item.id
        item_status = item.get('status', 'pending') if isinstance(item, dict) else getattr(item, 'status', 'pending')
        item_dependencies = item.get('dependencies', []) if isinstance(item, dict) else getattr(item, 'dependencies', [])
        
        if item_id not in completed_ids and item_status == 'pending':
            # Check if all dependencies are met
            if all(dep_id in completed_ids for dep_id in item_dependencies):
                next_work_item = item
                break
    
    if next_work_item:
        work_item_id = next_work_item['id'] if isinstance(next_work_item, dict) else next_work_item.id
        agent_role = next_work_item.get('agent_role', 'unknown') if isinstance(next_work_item, dict) else getattr(next_work_item, 'agent_role', 'unknown')
        description = next_work_item.get('description', '') if isinstance(next_work_item, dict) else getattr(next_work_item, 'description', '')
        
        logger.info(f"--- Starting Work Item: {work_item_id} ({agent_role}) ---")
        logger.info(f"Description: {description}")

        # Convert Pydantic model to dict if needed
        work_item_dict = next_work_item if isinstance(next_work_item, dict) else next_work_item.model_dump()

        # CRITICAL FIX: Store work item in state and indicate there's work to do
        result = {
            "current_work_item": work_item_dict,
            "current_work_item_start_time": time.time(),
            "_routing_decision": "proceed"  # Explicit routing signal
        }
        logger.info(f"WORK_ITEM_ITERATOR: Returning state update with current_work_item: {work_item_dict.get('id', 'UNKNOWN_ID')}, routing_decision='proceed'")
        return result
    else:
        logger.info("WORK_ITEM_ITERATOR: No next work item found")
        # Check if all items are complete
        if len(completed_ids) == len(work_items):
            logger.info("WORK_ITEM_ITERATOR: All work items complete - signaling workflow completion")
            return {
                StateFields.WORKFLOW_COMPLETE: True,
                "_routing_decision": "workflow_complete"  # Explicit routing signal
            }
        else:
            logger.error(f"WORK_ITEM_ITERATOR: Deadlock detected - {len(completed_ids)}/{len(work_items)} items complete but no pending items have dependencies met.")
            # This is an error state, we should probably stop the workflow
            return {
                StateFields.WORKFLOW_COMPLETE: True, 
                "error": "dependency_deadlock",
                "_routing_decision": "workflow_complete"  # Explicit routing signal
            }

def code_generation_dispatcher_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """Route to appropriate code generator based on the current work item's agent role."""
    
    # DEBUG: Add detailed state logging
    logger.info(f"DISPATCHER_DEBUG: Received state with keys: {list(state.keys())}")
    logger.info(f"DISPATCHER_DEBUG: current_work_item present: {'current_work_item' in state}")
    logger.info(f"DISPATCHER_DEBUG: current_work_item value: {state.get('current_work_item', 'NOT_FOUND')}")
    logger.info(f"DISPATCHER_DEBUG: _command_api_debug: {state.get('_command_api_debug', 'NOT_FOUND')}")
    
    work_item = state.get("current_work_item")
    if not work_item:
        logger.error("Dispatcher called without a current_work_item in the state.")
        logger.error(f"DISPATCHER_DEBUG: Full state dump: {dict(state)}")
        return {StateFields.CODE_GENERATION_RESULT: {"status": "error", "error_message": "No work item provided to dispatcher."}}

    agent_role = work_item.get('agent_role', "unknown").lower()
    work_item_id = work_item.get('id', "Unknown Work Item")
    
    logger.info(f"Dispatching to code generator for agent role: '{agent_role}' (Work Item: {work_item_id})")

    # Map agent roles to generator agents
    generator_map = {
        "architecture_specialist": ArchitectureGeneratorAgent,
        "database_specialist": DatabaseGeneratorAgent,
        "backend_developer": BackendOrchestratorAgent,
        "frontend_developer": FrontendGeneratorAgent,
        # 'devops_specialist' and 'code_optimizer' can be added back once they are refactored
    }
    
    agent_class = generator_map.get(agent_role)
    
    if not agent_class:
        error_msg = f"No agent found for role '{agent_role}'. Cannot proceed with work item."
        logger.error(error_msg)
        # It's better to stop and report an error than to default to a random agent.
        return {StateFields.CODE_GENERATION_RESULT: {"status": "error", "error_message": error_msg}}

    # Create the specialized agent instance
    agent = create_agent_with_temperature(agent_class, f"{agent_class.__name__}", config)
    
    # The new agent interface is simpler: just pass the work item and the full state.
    # The agent itself is responsible for extracting what it needs.
    result = agent.run(work_item=work_item, state=state)
    
    # The agent's run method should return a CodeGenerationOutput object,
    # which we can convert to a dict for the state.
    return {StateFields.CODE_GENERATION_RESULT: result.model_dump()}

def code_quality_analysis_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """Analyze code quality and provide feedback for improvements."""
    work_item = state.get("current_work_item", {})
    work_item_id = work_item.get("id", "Unknown Work Item")
    
    logger.info(f"Executing code quality review for work item '{work_item_id}'")

    # Check if required tools are available for CodeQualityAgent
    code_execution_tool = config["configurable"].get("code_execution_tool")
    run_output_dir = config["configurable"].get("run_output_dir")
    
    if not code_execution_tool or not run_output_dir:
        logger.warning(f"CodeQualityAgent tools missing - code_execution_tool: {bool(code_execution_tool)}, run_output_dir: {bool(run_output_dir)}")
        logger.warning("Falling back to basic quality analysis without automated tools")
        
        # Return a basic approval result to prevent infinite loops
        return {
            StateFields.CODE_REVIEW_FEEDBACK: {
                "approved": True,
                "feedback": [],
                "quality_score": 7.0,
                "summary": "Quality analysis skipped due to missing tools - proceeding with approval",
                "automated_checks_skipped": True,
                "tool_availability": {
                    "code_execution_tool": bool(code_execution_tool),
                    "run_output_dir": bool(run_output_dir)
                }
            }
        }

    try:
        agent = create_agent_with_temperature(CodeQualityAgent, "Code Quality Agent", config)
        
        # The new agent run method takes the work item and the full state
        review_result = agent.run(work_item=work_item, state=state)
        
        approved = review_result.get("approved", False)
        feedback_items = len(review_result.get("feedback", []))
        
        logger.info(f"Code review result: {'APPROVED' if approved else 'NEEDS REVISION'} with {feedback_items} feedback items.")
        
        return {StateFields.CODE_REVIEW_FEEDBACK: review_result}
        
    except Exception as e:
        logger.error(f"Code quality analysis failed for work item '{work_item_id}': {str(e)}", exc_info=True)
        
        # Return a fallback approval to prevent infinite loops
        return {
            StateFields.CODE_REVIEW_FEEDBACK: {
                "approved": True,
                "feedback": [],
                "quality_score": 6.0,
                "summary": f"Quality analysis failed: {str(e)} - proceeding with approval to prevent infinite loop",
                "error_occurred": True,
                "error_details": str(e)
            }
        }

def test_execution_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """
    Execute the generated tests for the current work item and return the results.
    This node forms the core of the self-correction loop.
    """
    work_item = state.get("current_work_item", {})
    work_item_id = work_item.get('id', "Unknown Work Item")
    logger.info(f"Executing tests for work item: {work_item_id}")

    code_gen_result = state.get(StateFields.CODE_GENERATION_RESULT, {})
    generated_files = code_gen_result.get("generated_files", [])

    if not generated_files:
        logger.warning(f"No files generated for work item {work_item_id}. Skipping test execution.")
        return {StateFields.TEST_VALIDATION_RESULT: {"status": "skipped", "message": "No files to test."}}

    code_execution_tool = config["configurable"].get("code_execution_tool")
    if not code_execution_tool:
        logger.error("CodeExecutionTool not found in config. Cannot run tests.")
        return {StateFields.TEST_VALIDATION_RESULT: {"status": "error", "message": "CodeExecutionTool is not configured."}}

    # Write files to the execution directory
    try:
        for file_info in generated_files:
            file_path = Path(code_execution_tool.work_dir) / file_info['path']
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(file_info['content'])
        logger.info(f"Wrote {len(generated_files)} files to {code_execution_tool.work_dir} for testing.")
    except Exception as e:
        logger.error(f"Failed to write files for testing: {e}")
        return {StateFields.TEST_VALIDATION_RESULT: {"status": "error", "message": f"File write error: {e}"}}

    # Determine the test command based on the framework
    tech_stack = state.get(StateFields.TECH_STACK_RECOMMENDATION, {})
    frontend_framework = tech_stack.get("frontend_framework", "").lower()
    backend_framework = tech_stack.get("backend_framework", "").lower()
    
    test_command = "pytest" # Default to pytest for python backends
    if "react" in frontend_framework or "vue" in frontend_framework:
        # A more robust solution would be to check for package.json and install first
        test_command = "npm install && npm test"
    
    logger.info(f"Running test command: '{test_command}'")
    
    # Execute the tests
    exec_result = code_execution_tool.run(command=test_command, timeout_seconds=300)

    # Process the results
    passed = exec_result.get("return_code", 1) == 0
    test_report = {
        "status": "passed" if passed else "failed",
        "stdout": exec_result.get("stdout"),
        "stderr": exec_result.get("stderr"),
        "passed": passed,
        "summary": "Tests passed successfully." if passed else "Tests failed. See logs for details."
    }

    logger.info(f"Test execution for {work_item_id} finished with status: {test_report['status']}")
    
    return {StateFields.TEST_VALIDATION_RESULT: test_report}

def decide_on_code_quality(state: AgentState) -> str:
    """
    Decision function that checks the code quality review and decides whether to
    proceed to testing or request revisions.
    """
    feedback = state.get(StateFields.CODE_REVIEW_FEEDBACK, {})
    work_item_id = state.get("current_work_item", {}).get("id", "unknown")
    revision_counts = state.get(StateFields.REVISION_COUNTS, {})
    current_revisions = revision_counts.get(work_item_id, 0)
    max_revisions = 2

    if feedback.get("approved"):
        logger.info(f"Code quality for work item '{work_item_id}' approved. Proceeding to testing.")
        return "approve"
        
    if current_revisions >= max_revisions:
        logger.warning(f"Max revisions ({max_revisions}) reached for work item '{work_item_id}'. Proceeding despite quality issues.")
        return "approve"

    logger.info(f"Code quality for work item '{work_item_id}' needs revision.")
    return "revise"

def decide_on_test_results(state: AgentState) -> str:
    """
    Decision function that checks the test execution results and decides whether to
    approve the work item or request revisions.
    """
    test_result = state.get(StateFields.TEST_VALIDATION_RESULT, {})
    work_item_id = state.get("current_work_item", {}).get("id", "unknown")
    
    revision_counts = state.get(StateFields.REVISION_COUNTS, {})
    current_revisions = revision_counts.get(work_item_id, 0)
    max_revisions = 2

    if test_result.get("passed"):
        logger.info(f"Tests passed for work item '{work_item_id}'. Approving.")
        return StateFields.APPROVE

    if current_revisions >= max_revisions:
        logger.warning(f"Max revisions ({max_revisions}) reached for work item '{work_item_id}'. Approving despite test failures.")
        return StateFields.APPROVE

    logger.info(f"Tests failed for work item '{work_item_id}'. Requesting revision (attempt {current_revisions + 1}/{max_revisions}).")
    return StateFields.REVISE

def phase_completion_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """Complete the current work item and prepare for the next one."""
    work_item = state.get("current_work_item", {})
    work_item_id = work_item.get("id", "Unknown Work Item")
    
    # Mark the work item as complete
    completed_work_items = state.get("completed_work_items", [])
    updated_work_item = {**work_item, "status": "completed"}
    completed_work_items.append(updated_work_item)
    
    # Calculate duration
    start_time = state.get("current_work_item_start_time", time.time())
    duration = time.time() - start_time
    
    logger.info(f"Completing Work Item '{work_item_id}' - Duration: {duration:.2f}s")
    
    # Create return state
    result = {
        "completed_work_items": completed_work_items,
    }
    
    # Track execution time
    execution_times = state.get("work_item_execution_times", {})
    execution_times[work_item_id] = duration
    result["work_item_execution_times"] = execution_times
    
    return result

def increment_revision_count_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """Increment the revision count for the current work item."""
    revision_counts = state.get(StateFields.REVISION_COUNTS, {}).copy()
    
    work_item = state.get("current_work_item")
    if not work_item:
        logger.warning("CIRCUIT BREAKER: increment_revision_count_node called without current_work_item - stopping infinite loop")
        return {
            StateFields.REVISION_COUNTS: revision_counts,
            "circuit_breaker_triggered": True,
            StateFields.WORKFLOW_COMPLETE: True
        }
    
    work_item_id = work_item.get('id', "Unknown Work Item") if isinstance(work_item, dict) else work_item.id
    
    current_count = revision_counts.get(work_item_id, 0)
    new_count = current_count + 1
    revision_counts[work_item_id] = new_count
    
    # CIRCUIT BREAKER: If we hit too many revisions, force completion
    MAX_REVISIONS_GLOBAL = 10  # Global safety limit
    if new_count >= MAX_REVISIONS_GLOBAL:
        logger.error(f"CIRCUIT BREAKER: Work item '{work_item_id}' hit {MAX_REVISIONS_GLOBAL} revisions - forcing completion to prevent infinite loop")
        return {
            StateFields.REVISION_COUNTS: revision_counts,
            "circuit_breaker_triggered": True,
            StateFields.WORKFLOW_COMPLETE: True,
            "current_work_item": None
        }
    
    logger.info(f"Incrementing revision count for work item '{work_item_id}' to {new_count}")
    
    return {
        StateFields.REVISION_COUNTS: revision_counts
    }

def integration_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """
    Merge the work item's code into the main project and run integration tests.
    This simulates a CI/CD integration step.
    """
    work_item = state.get("current_work_item", {})
    work_item_id = work_item.get('id', "Unknown Work Item")
    logger.info(f"--- Running Integration Step for Work Item: {work_item_id} ---")

    code_gen_result = state.get(StateFields.CODE_GENERATION_RESULT, {})
    generated_files = code_gen_result.get("generated_files", [])

    if not generated_files:
        logger.warning(f"No files generated for work item {work_item_id}. Skipping integration.")
        return {
            StateFields.INTEGRATION_TEST_RESULT: {
                "status": "skipped",
                "message": "No files to merge or test.",
                "passed": True  # Skipped is considered a pass
            }
        }

    code_execution_tool = config["configurable"].get("code_execution_tool")
    final_project_dir = config["configurable"].get("run_output_dir")

    if not code_execution_tool or not final_project_dir:
        msg = "CodeExecutionTool or run_output_dir not configured. Cannot run integration step."
        logger.error(msg)
        return {
            StateFields.INTEGRATION_TEST_RESULT: {
                "status": "error", "message": msg, "passed": False
            }
        }

    temp_work_dir = Path(code_execution_tool.work_dir)
    final_project_path = Path(final_project_dir)

    # 1. Merge files from the temp sandbox to the final project directory
    try:
        for file_info in generated_files:
            source_path = temp_work_dir / file_info['path']
            destination_path = final_project_path / file_info['path']
            
            if source_path.exists():
                destination_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, destination_path)
                logger.info(f"Merged file: {destination_path}")
            else:
                logger.warning(f"Source file not found in sandbox, cannot merge: {source_path}")
    except Exception as e:
        msg = f"Failed to merge files into project: {e}"
        logger.error(msg)
        return {StateFields.INTEGRATION_TEST_RESULT: {"status": "error", "message": msg, "passed": False}}

    # 2. Run integration tests in the main project directory
    logger.info(f"Running integration tests in final project directory: {final_project_dir}")
    # Determine the test command based on the framework
    tech_stack = state.get(StateFields.TECH_STACK_RECOMMENDATION, {})
    frontend_framework = tech_stack.get("frontend_framework", "").lower()
    
    test_command = "pytest" # Default to pytest
    if "react" in frontend_framework or "vue" in frontend_framework:
        test_command = "npm install && npm test"
        
    # Execute tests in the final project directory, not the sandbox
    exec_result = code_execution_tool.run(command=test_command, working_directory=str(final_project_path))

    passed = exec_result.get("return_code", 1) == 0
    test_report = {
        "status": "passed" if passed else "failed",
        "stdout": exec_result.get("stdout"),
        "stderr": exec_result.get("stderr"),
        "passed": passed,
        "summary": "Integration tests passed." if passed else "Integration tests failed."
    }

    logger.info(f"Integration test for {work_item_id} finished with status: {test_report['status']}")
    
    return {StateFields.INTEGRATION_TEST_RESULT: test_report}

def decide_on_integration_test_results(state: AgentState) -> str:
    """
    Decision function that checks the integration test results.
    For now, it logs failures but proceeds. In the future, this could trigger a rollback or a new work item.
    """
    test_result = state.get(StateFields.INTEGRATION_TEST_RESULT, {})
    work_item_id = state.get("current_work_item", {}).get("id", "unknown")
    
    if test_result.get("passed"):
        logger.info(f"Integration tests passed for work item '{work_item_id}'. Proceeding.")
        return "proceed"
    else:
        logger.error(f"CRITICAL: Integration tests failed after merging work item '{work_item_id}'.")
        logger.error(f"Stderr: {test_result.get('stderr')}")
        # In a more advanced system, this could trigger a rollback or a new high-priority bug ticket.
        # For now, we log the failure and proceed.
        return "proceed_with_warning"

# --- Human-in-the-Loop Nodes (Restored) ---

def human_approval_node(state: AgentState) -> dict:
    """
    A placeholder node where the workflow pauses for human approval.
    This is for BRD analysis approval. The actual interruption happens *before* this node is executed.
    """
    logger.info("Human approval node reached. The workflow should have paused before this.")
    return {}

def human_approval_tech_stack_node(state: AgentState) -> dict:
    """Pauses the workflow to wait for human approval of the tech stack recommendation.
    Upon approval, integrates the selected tech stack into the workflow state.
    """
    logger.info("Executing human_approval_tech_stack_node.")
    
    # Retrieve the raw tech stack recommendation from the state
    tech_stack_recommendation_raw = state.get(StateFields.TECH_STACK_RECOMMENDATION, {})
    
    # Convert to Pydantic model for easier access and validation
    try:
        tech_stack_output = ComprehensiveTechStackOutput(**tech_stack_recommendation_raw)
    except Exception as e:
        logger.error(f"Failed to parse tech_stack_recommendation into ComprehensiveTechStackOutput in human_approval_tech_stack_node: {e}", exc_info=True)
        tech_stack_output = ComprehensiveTechStackOutput() # Fallback to empty model

    # Extract feedback if available
    user_feedback = state.get(StateFields.USER_FEEDBACK, {})
    decision = user_feedback.get("decision")
    selected_stack_data = user_feedback.get("selected_stack")

    if decision == "proceed" and selected_stack_data:
        logger.info(f"Human approved tech stack with selections: {selected_stack_data}")
        
        # Create a SelectedTechStack instance from the feedback data
        selected_tech_stack = SelectedTechStack(
            frontend_selection=selected_stack_data.get("frontend_selection"),
            backend_selection=selected_stack_data.get("backend_selection"),
            database_selection=selected_stack_data.get("database_selection"),
            cloud_selection=selected_stack_data.get("cloud_selection"),
            architecture_selection=selected_stack_data.get("architecture_selection"),
            tool_selection=selected_stack_data.get("tool_selection")
        )
        
        # Update the tech_stack_output with the user's selection
        tech_stack_output.selected_stack = selected_tech_stack
        
        # Update the state with the modified ComprehensiveTechStackOutput
        return {StateFields.TECH_STACK_RECOMMENDATION: tech_stack_output.model_dump() }
    
    elif decision == "revise":
        logger.info("Human requested revision for tech stack.")
        # No changes to tech_stack_recommendation needed, agent will re-run.
        return {}
    
    elif decision == "end":
        logger.info("Human terminated workflow during tech stack approval.")
        return {}

    else:
        # Initial pause or unexpected decision
        logger.info(f"Pausing for human approval for tech stack. Decision: {decision}")
        return {
            StateFields.HUMAN_APPROVAL_REQUEST: ApprovalPayload(
                step_name="tech_stack_recommendation",
                display_name="Technology Stack Recommendation",
                data=tech_stack_output.model_dump(), # Send the full output with options
                instructions="Please review the recommended technology stack. You can approve to continue, request revisions with specific feedback, or select different options from the provided choices.",
                is_revision=False,
                previous_feedback=None
            ).model_dump()
        }

def human_approval_system_design_node(state: AgentState) -> dict:
    """
    Human approval node for system design.
    The actual interruption happens *before* this node is executed.
    """
    logger.info("System design approval node reached. The workflow should have paused before this.")
    return {}

def human_approval_plan_node(state: AgentState) -> dict:
    """
    Human approval node for implementation plan.
    The actual interruption happens *before* this node is executed.
    """
    logger.info("Implementation plan approval node reached. The workflow should have paused before this.")
    return {}

def should_request_brd_approval(state: AgentState) -> str:
    """
    Decision function to always trigger human approval for BRD analysis.
    This allows the 'interrupt_before' to work correctly in non-async workflows.
    """
    logger.info("Decision: Should request BRD approval? -> Yes")
    return "request_approval"

def decide_after_brd_approval(state: AgentState) -> str:
    """
    Determines the next step after a human has reviewed the BRD analysis.
    Reads 'human_feedback' from the state, injected by the API.
    """
    human_feedback = state.get("human_feedback", {})
    decision = human_feedback.get("decision") if isinstance(human_feedback, dict) else human_feedback
    logger.info(f"BRD Decision point: Received human feedback -> '{decision}'")

    if decision == "proceed":
        return "proceed"
    elif decision == "revise":
        return "revise"
    elif decision == "end":
        return "end"
    
    logger.warning(f"Unknown or missing human_feedback: '{decision}'. Ending workflow.")
    return "end"

def decide_after_tech_stack_approval(state: AgentState) -> str:
    """
    Determines the next step after a human has reviewed the tech stack recommendation.
    """
    human_feedback = state.get("human_feedback", {})
    decision = human_feedback.get("decision") if isinstance(human_feedback, dict) else human_feedback
    logger.info(f"Tech Stack Decision point: Received human feedback -> '{decision}'")

    if decision == "proceed":
        return "proceed"
    elif decision == "revise":
        return "revise"
    elif decision == "end":
        return "end"
    
    logger.warning(f"Unknown or missing human_feedback: '{decision}'. Ending workflow.")
    return "end"

def decide_after_system_design_approval(state: AgentState) -> str:
    """
    Determines the next step after a human has reviewed the system design.
    """
    human_feedback = state.get("human_feedback", {})
    decision = human_feedback.get("decision") if isinstance(human_feedback, dict) else human_feedback
    logger.info(f"System Design Decision point: Received human feedback -> '{decision}'")

    if decision == "proceed":
        return "proceed"
    elif decision == "revise":
        return "revise"
    elif decision == "end":
        return "end"
    
    logger.warning(f"Unknown or missing human_feedback: '{decision}'. Ending workflow.")
    return "end"

def decide_after_plan_approval(state: AgentState) -> str:
    """
    Determines the next step after a human has reviewed the implementation plan.
    """
    human_feedback = state.get("human_feedback", {})
    decision = human_feedback.get("decision") if isinstance(human_feedback, dict) else human_feedback
    logger.info(f"Plan Decision point: Received human feedback -> '{decision}'")

    if decision == "proceed":
        return "proceed"
    elif decision == "revise":
        return "revise"
    elif decision == "end":
        return "end"
    
    logger.warning(f"Unknown or missing human_feedback: '{decision}'. Ending workflow.")
    return "end"

# --- Finalization Node ---

def finalize_workflow(state: AgentState, config: dict) -> Dict[str, Any]:
    """Create final workflow summary and consolidate results."""
    logger.info("--- Finalizing Workflow ---")
    
    # Calculate total execution time - ensure start_time is numeric
    start_time = state.get("workflow_start_time", 0)
    try:
        # Convert to float if it's a string to handle type mismatches
        start_time = float(start_time) if start_time else 0
    except (ValueError, TypeError):
        logger.warning(f"Invalid workflow_start_time value: {start_time}. Using 0.")
        start_time = 0
    
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
    """
    Decision function that checks if there is another work item to process.
    """
    workflow_complete = state.get(StateFields.WORKFLOW_COMPLETE, False)
    current_work_item = state.get("current_work_item")
    
    logger.info(f"HAS_NEXT_PHASE: workflow_complete={workflow_complete}, has_current_work_item={current_work_item is not None}")
    
    if workflow_complete:
        logger.info("HAS_NEXT_PHASE: Workflow marked as complete - routing to finalize")
        return "workflow_complete"
    elif current_work_item:
        item_id = current_work_item.get('id', 'UNKNOWN_ID') if isinstance(current_work_item, dict) else 'UNKNOWN_TYPE'
        logger.info(f"HAS_NEXT_PHASE: Found work item '{item_id}' - proceeding to next phase")
        return "proceed"
    else:
        logger.warning("HAS_NEXT_PHASE: No work item found and workflow not marked complete - assuming completion")
        return "workflow_complete"

def route_after_work_item_iterator(state: AgentState) -> str:
    """
    Decision function that routes based on work item availability and completion status.
    FIXED: This now checks the actual state values that are available in conditional edges.
    """
    # Check if workflow is complete first
    workflow_complete = state.get(StateFields.WORKFLOW_COMPLETE, False)
    current_work_item = state.get("current_work_item")
    
    logger.info(f"ROUTE_AFTER_ITERATOR: workflow_complete={workflow_complete}, has_current_work_item={current_work_item is not None}")
    
    if workflow_complete:
        logger.info("ROUTE_AFTER_ITERATOR: Workflow marked as complete - routing to finalize")
        return "workflow_complete"
    elif current_work_item:
        item_id = current_work_item.get('id', 'UNKNOWN_ID') if isinstance(current_work_item, dict) else 'UNKNOWN_TYPE'
        logger.info(f"ROUTE_AFTER_ITERATOR: Found work item '{item_id}' - proceeding to code generation")
        return "proceed"
    else:
        logger.warning("ROUTE_AFTER_ITERATOR: No work item found and workflow not marked complete - assuming completion")
        return "workflow_complete"

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
    """Legacy compatibility function that maps to test_execution_node."""
    logger.info("Using test_case_generation_node (legacy compatibility)")
    return test_execution_node(state, config)

def test_validation_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """Legacy compatibility function that maps to test_execution_node."""
    logger.info("Using test_validation_node (legacy compatibility)")
    return test_execution_node(state, config)

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
    """Legacy module that maps to test_execution_node."""
    logger.info("Using testing_module (legacy compatibility)")
    return test_execution_node(state, config)

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
    """DEPRECATED: Decide whether to iterate on the implementation phase."""
    return "continue" if state.get("should_iterate") else "end"

def determine_phase_generators(state: AgentState) -> str:
    """DEPRECATED: Determine which generators to run for the current phase."""
    return state.get("current_phase", "end")

# Helper functions
def checkpoint_state(state: AgentState, config: dict) -> Dict[str, Any]:
    """Save the current state to a checkpoint."""
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
    return work_item_iterator_node(state, config)

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

# End of graph_nodes.py

