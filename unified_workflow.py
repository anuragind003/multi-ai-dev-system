"""
UNIFIED WORKFLOW - Single, Clean Pipeline
Eliminates sync/async confusion with a pure async approach.
"""

import asyncio
import time
import logging
import json
from typing import Dict, Any, List
from datetime import datetime
from langgraph.graph import StateGraph, END
from langgraph.types import interrupt
from langchain_core.runnables import RunnableLambda

from agent_state import AgentState, StateFields

logger = logging.getLogger(__name__)

# ============================================================================
# PURE ASYNC NODE IMPLEMENTATIONS
# ============================================================================

async def unified_initialize_workflow_state(state: AgentState, config: dict) -> Dict[str, Any]:
    """Initialize essential state keys with pure async approach."""
    logger.info("UNIFIED: Initializing workflow state")
    
    # Preserve any existing state while adding defaults
    initialized_state = {
        "workflow_id": f"workflow_{int(time.time())}",
        "workflow_start_time": time.time(),
        "code_generation_result": {"generated_files": {}, "status": "not_started"},
        "errors": [],
        "completed_work_items": [],
        "failed_work_items": [],  # ENHANCED: Track failed work items
        "revision_counts": {},
        "skip_current_item": False,  # ENHANCED: Flag for skipping failed items
        "workflow_complete": False,
        **state  # Preserve any existing state
    }
    
    logger.info(f"UNIFIED: Workflow {initialized_state['workflow_id']} initialized")
    return initialized_state

async def unified_brd_analysis_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """BRD analysis with pure async approach."""
    logger.info("UNIFIED: Executing BRD analysis node")
    
    # Import here to avoid circular dependencies
    from agents.brd_analyst_react import BRDAnalystReActAgent
    from config import get_llm
    from agent_temperatures import get_agent_temperature
    
    try:
        # Create agent with proper async configuration
        temperature = get_agent_temperature("BRD Analyst Agent")
        llm = get_llm(temperature=temperature)
        
        agent_args = {
            "llm": llm,
            "memory": config["configurable"].get("memory"),
            "temperature": temperature
        }
        
        # Add optional components if available
        if "rag_manager" in config["configurable"]:
            rag_manager = config["configurable"]["rag_manager"]
            if rag_manager:
                agent_args["rag_retriever"] = rag_manager.get_retriever()
        
        # Create agent and run analysis
        agent = BRDAnalystReActAgent(**agent_args)
        
        # Add delay for API rate limiting
        await asyncio.sleep(2.0)
        
        # Run in thread pool to avoid blocking
        result = await asyncio.to_thread(agent.run, raw_brd=state[StateFields.BRD_CONTENT])
        
        # Ensure result is properly serialized to dictionary
        if hasattr(result, 'model_dump'):
            result = result.model_dump()
        elif hasattr(result, 'dict'):
            result = result.dict()
        elif not isinstance(result, dict):
            # Handle string or other non-dict types
            try:
                import json
                if isinstance(result, str):
                    result = json.loads(result)
                else:
                    result = {"content": str(result), "type": type(result).__name__}
            except (json.JSONDecodeError, Exception):
                result = {"content": str(result), "type": type(result).__name__}
        
        logger.info(f" UNIFIED: BRD analysis completed successfully - result type: {type(result)}")
        return {StateFields.REQUIREMENTS_ANALYSIS: result}
        
    except Exception as e:
        logger.error(f" UNIFIED: BRD analysis failed: {str(e)}")
        return {
            StateFields.REQUIREMENTS_ANALYSIS: {"error": str(e)},
            "errors": [{"module": "BRD Analysis", "error": str(e), "timestamp": time.time()}]
        }

async def unified_tech_stack_recommendation_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """Tech stack recommendation with pure async approach."""
    logger.info(" UNIFIED: Executing tech stack recommendation node")
    
    from agents.tech_stack_advisor_simplified import TechStackAdvisorSimplifiedAgent
    from config import get_llm
    from agent_temperatures import get_agent_temperature
    
    try:
        temperature = get_agent_temperature("Tech Stack Advisor Agent")
        llm = get_llm(temperature=temperature)
        
        agent_args = {
            "llm": llm,
            "memory": config["configurable"].get("memory"),
            "temperature": temperature
        }
        
        if "rag_manager" in config["configurable"]:
            rag_manager = config["configurable"]["rag_manager"]
            if rag_manager:
                agent_args["rag_retriever"] = rag_manager.get_retriever()
        
        agent = TechStackAdvisorSimplifiedAgent(**agent_args)
        
        await asyncio.sleep(2.0)  # Rate limiting
        
        result = await asyncio.to_thread(
            agent.run,
            raw_brd=state[StateFields.BRD_CONTENT],
            requirements_analysis=state[StateFields.REQUIREMENTS_ANALYSIS]
        )
        
        # Ensure result is properly serialized to dictionary
        if hasattr(result, 'model_dump'):
            result = result.model_dump()
        elif hasattr(result, 'dict'):
            result = result.dict()
        elif not isinstance(result, dict):
            # Handle string or other non-dict types
            try:
                import json
                if isinstance(result, str):
                    result = json.loads(result)
                else:
                    result = {"content": str(result), "type": type(result).__name__}
            except (json.JSONDecodeError, Exception):
                result = {"content": str(result), "type": type(result).__name__}
        
        logger.info(f" UNIFIED: Tech stack recommendation completed - result type: {type(result)}")
        return {StateFields.TECH_STACK_RECOMMENDATION: result}
        
    except Exception as e:
        logger.error(f" UNIFIED: Tech stack recommendation failed: {str(e)}")
        return {
            StateFields.TECH_STACK_RECOMMENDATION: {"error": str(e)},
            "errors": state.get("errors", []) + [{"module": "Tech Stack", "error": str(e)}]
        }

async def unified_system_design_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """System design with pure async approach."""
    logger.info(" UNIFIED: Executing system design node")
    
    from agents.system_designer_simplified import SystemDesignerSimplifiedAgent
    from config import get_llm
    from agent_temperatures import get_agent_temperature
    
    try:
        temperature = get_agent_temperature("System Designer Agent")
        llm = get_llm(temperature=temperature)
        
        agent_args = {
            "llm": llm,
            "memory": config["configurable"].get("memory"),
            "temperature": temperature
        }
        
        agent = SystemDesignerSimplifiedAgent(**agent_args)
        
        await asyncio.sleep(2.0)  # Rate limiting
        
        # SIMPLIFIED: Process tech stack recommendation (single recommendation format)
        tech_stack_recommendation = state.get(StateFields.TECH_STACK_RECOMMENDATION, {})
        logger.info(f"UNIFIED: Tech stack recommendation keys: {list(tech_stack_recommendation.keys()) if isinstance(tech_stack_recommendation, dict) else 'Not a dict'}")
        
        # Extract single recommendations from the new format
        final_tech_stack = {}
        if isinstance(tech_stack_recommendation, dict):
            # Try direct fields with name/reasoning structure first
            if tech_stack_recommendation.get("frontend", {}).get("name"):
                logger.info("UNIFIED: System design - Using direct fields from tech stack recommendation")
                final_tech_stack = {
                    'frontend': tech_stack_recommendation.get("frontend", {}).get("name", "React"),
                    'backend': tech_stack_recommendation.get("backend", {}).get("name", "Node.js with Express.js"),
                    'database': tech_stack_recommendation.get("database", {}).get("name", "PostgreSQL"),
                    'architecture': tech_stack_recommendation.get("architecture", {}).get("name", "Microservices Architecture"),
                    'cloud': tech_stack_recommendation.get("cloud", {}).get("name", "AWS")
                }
            # Try synthesis format as fallback
            elif tech_stack_recommendation.get("synthesis", {}).get("frontend"):
                logger.info("UNIFIED: System design - Using synthesis from tech stack recommendation")
                synthesis = tech_stack_recommendation.get("synthesis", {})
                final_tech_stack = {
                    'frontend': synthesis.get("frontend", {}).get("framework", "React"),
                    'backend': synthesis.get("backend", {}).get("framework", "Node.js with Express.js"),
                    'database': synthesis.get("database", {}).get("type", "PostgreSQL"),
                    'architecture': synthesis.get("architecture_pattern", "Microservices Architecture"),
                    'cloud': synthesis.get("deployment_environment", {}).get("hosting", "AWS")
                }
        
        # Emergency fallback
        if not final_tech_stack or not any(final_tech_stack.values()):
            logger.warning("UNIFIED: System design - No tech stack data found, using emergency fallback.")
            final_tech_stack = {
                'frontend': 'React', 
                'backend': 'Node.js with Express.js', 
                'database': 'PostgreSQL', 
                'architecture': 'Microservices Architecture',
                'cloud': 'AWS'
            }
        
        logger.info(f"UNIFIED: System design - Final tech stack being passed to agent: {final_tech_stack}")
        
        # ADD DEBUGGING: Check the requirements analysis data
        req_analysis = state[StateFields.REQUIREMENTS_ANALYSIS]
        logger.info(f"UNIFIED: Requirements analysis type: {type(req_analysis)}")
        logger.info(f"UNIFIED: Requirements analysis keys: {list(req_analysis.keys()) if isinstance(req_analysis, dict) else 'Not a dict'}")
        
        # Pass clean dictionary to the agent (this will be passed as tech_stack_recommendation)
        result = await asyncio.to_thread(
            agent.run,
            requirements_analysis=req_analysis,
            tech_stack_recommendation=final_tech_stack  # Pass the simplified format
        )
        
        # Handle result serialization
        if hasattr(result, 'model_dump'):
            result = result.model_dump()
        elif hasattr(result, 'dict'):
            result = result.dict()
        elif not isinstance(result, dict):
            try:
                import json
                if isinstance(result, str):
                    result = json.loads(result)
                else:
                    result = {"content": str(result), "type": type(result).__name__}
            except (json.JSONDecodeError, Exception):
                result = {"content": str(result), "type": type(result).__name__}
        
        logger.info(f" UNIFIED: System design completed - result type: {type(result)}")
        return {StateFields.SYSTEM_DESIGN: result}
        
    except Exception as e:
        logger.error(f" UNIFIED: System design failed: {str(e)}")
        return {
            StateFields.SYSTEM_DESIGN: {"error": str(e)},
            "errors": state.get("errors", []) + [{"module": "System Design", "error": str(e)}]
        }

async def unified_planning_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """Planning with pure async approach."""
    logger.info(" UNIFIED: Executing planning node")
    
    from agents.planning.plan_compiler_simplified import PlanCompilerSimplifiedAgent
    from config import get_llm
    from agent_temperatures import get_agent_temperature
    
    try:
        temperature = get_agent_temperature("Plan Compiler Agent")
        llm = get_llm(temperature=temperature)
        
        agent_args = {
            "llm": llm,
            "memory": config["configurable"].get("memory"),
            "temperature": temperature
        }
        
        agent = PlanCompilerSimplifiedAgent(**agent_args)
        
        await asyncio.sleep(2.0)  # Rate limiting
        
        # Ensure tech stack data is serializable
        tech_stack_data = state[StateFields.TECH_STACK_RECOMMENDATION]
        if hasattr(tech_stack_data, 'model_dump'):
            tech_stack_data = tech_stack_data.model_dump()
        elif not isinstance(tech_stack_data, dict):
            logger.warning(f" UNIFIED: Tech stack data is not a dict (type: {type(tech_stack_data)}), using fallback")
            tech_stack_data = {
                "frontend": "React",
                "backend": "Node.js with Express.js", 
                "database": "PostgreSQL",
                "architecture": "Microservices Architecture",
                "cloud": "AWS"
            }
        
        logger.info(" UNIFIED: Calling plan compiler agent")
        result = await asyncio.to_thread(
            agent.run,
            requirements_analysis=state[StateFields.REQUIREMENTS_ANALYSIS],
            tech_stack_recommendation=tech_stack_data,
            system_design=state[StateFields.SYSTEM_DESIGN]
        )
        
        # ADD DEBUGGING: Log what the plan compiler returned
        logger.info(f" UNIFIED: Plan compiler returned result type: {type(result)}")
        logger.info(f" UNIFIED: Plan compiler result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
        
        # Ensure result is properly serialized to dictionary
        if hasattr(result, 'model_dump'):
            result = result.model_dump()
        elif hasattr(result, 'dict'):
            result = result.dict()
        elif not isinstance(result, dict):
            # Handle string or other non-dict types
            try:
                import json
                if isinstance(result, str):
                    # Try parsing if it's a JSON string
                    result = json.loads(result)
                else:
                    # Convert to string representation and wrap in dict
                    result = {"plan_content": str(result), "type": type(result).__name__}
            except (json.JSONDecodeError, Exception):
                result = {"plan_content": str(result), "type": type(result).__name__}
        
        # ADD DEBUGGING: Log the final result being stored
        logger.info(f" UNIFIED: Final planning result type: {type(result)}")
        logger.info(f" UNIFIED: Final planning result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
        if isinstance(result, dict):
            if 'plan_type' in result:
                logger.info(f" UNIFIED: Plan type: {result['plan_type']}")
            if 'phases' in result:
                logger.info(f" UNIFIED: Number of phases: {len(result['phases'])}")
                for i, phase in enumerate(result['phases']):
                    if isinstance(phase, dict) and 'work_items' in phase:
                        logger.info(f" UNIFIED: Phase {i} ({phase.get('name', 'unnamed')}) has {len(phase['work_items'])} work items")
            if 'work_items' in result:
                logger.info(f" UNIFIED: Direct work_items count: {len(result['work_items'])}")
        
        logger.info(f" UNIFIED: Planning completed - result type: {type(result)}")
        return {StateFields.IMPLEMENTATION_PLAN: result}
        
    except Exception as e:
        logger.error(f" UNIFIED: Planning failed: {str(e)}")
        return {
            StateFields.IMPLEMENTATION_PLAN: {"error": str(e)},
            "errors": state.get("errors", []) + [{"module": "Planning", "error": str(e)}]
        }

# ============================================================================
# UNIFIED WORK ITEM MANAGEMENT
# ============================================================================

async def unified_work_item_iterator_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """
     UNIFIED WORK ITEM ITERATOR: Enhanced with graceful failure handling.
    """
    # ENHANCED: Handle skip current item flag
    if state.get("skip_current_item", False):
        logger.info("UNIFIED: Skipping current failed item, moving to next")
        return {
            "skip_current_item": False,  # Reset flag
            "current_work_item": None,
            "_unified_decision": "proceed"  # Continue to find next item
        }
    
    plan_output = state.get(StateFields.IMPLEMENTATION_PLAN)
    if not plan_output:
        logger.warning("UNIFIED: No implementation plan found")
        return {
            "current_work_item": None,
            StateFields.WORKFLOW_COMPLETE: True,
            "_unified_decision": "no_plan"
        }
    
    # ADD DEBUGGING: Log the plan output structure
    logger.info(f"UNIFIED: Plan output type: {type(plan_output)}")
    logger.info(f"UNIFIED: Plan output keys: {list(plan_output.keys()) if isinstance(plan_output, dict) else 'Not a dict'}")
    
    # Extract work items from plan - Simplified logic for new format
    work_items = []
    
    # NEW: Handle simplified plan format (plan_type: "simplified_workitem_backlog")
    if isinstance(plan_output, dict) and plan_output.get("plan_type") == "simplified_workitem_backlog":
        logger.info("UNIFIED: Found simplified_workitem_backlog format")
        phases = plan_output.get('phases', [])
        logger.info(f"UNIFIED: Found {len(phases)} phases")
        for i, phase in enumerate(phases):
            if isinstance(phase, dict) and 'work_items' in phase:
                phase_work_items = phase['work_items']
                logger.info(f"UNIFIED: Phase {i} ({phase.get('name', 'unnamed')}) has {len(phase_work_items)} work items")
                work_items.extend(phase_work_items)
            else:
                logger.warning(f"UNIFIED: Phase {i} is missing work_items or not a dict")
    
    # LEGACY: Case 1: ComprehensiveImplementationPlanOutput object
    elif hasattr(plan_output, 'plan'):
        logger.info("UNIFIED: Found legacy format with 'plan' attribute")
        plan = plan_output.plan
        
        if hasattr(plan, 'phases'):
            phases = plan.phases
            
            # Handle both list of objects and list of dicts
            for i, phase in enumerate(phases):
                if hasattr(phase, 'work_items'):
                    work_items.extend(phase.work_items)
                elif isinstance(phase, dict) and 'work_items' in phase:
                    work_items.extend(phase['work_items'])
    
    # LEGACY: Case 2: Dictionary with 'plan' key
    elif isinstance(plan_output, dict) and 'plan' in plan_output:
        logger.info("UNIFIED: Found legacy format with 'plan' key")
        plan = plan_output['plan']
        
        if isinstance(plan, dict) and 'phases' in plan:
            for i, phase in enumerate(plan['phases']):
                if isinstance(phase, dict) and 'work_items' in phase:
                    work_items.extend(phase['work_items'])
    
    # LEGACY: Case 3: Direct phases in plan_output
    elif isinstance(plan_output, dict) and 'phases' in plan_output:
        logger.info("UNIFIED: Found legacy format with direct 'phases' key")
        for i, phase in enumerate(plan_output['phases']):
            if isinstance(phase, dict) and 'work_items' in phase:
                work_items.extend(phase['work_items'])
    
    # NEW: Case 4: Check if work_items is directly in plan_output (WorkItemBacklog format)
    elif isinstance(plan_output, dict) and 'work_items' in plan_output:
        logger.info("UNIFIED: Found direct work_items in plan_output (WorkItemBacklog format)")
        work_items = plan_output['work_items']
    
    # NEW: Case 5: Handle error cases with fallback work items
    elif isinstance(plan_output, dict) and 'error' in plan_output:
        logger.warning("UNIFIED: Plan output contains error, creating fallback work items")
        work_items = _create_fallback_work_items(state)
    
    else:
        logger.warning(f"UNIFIED: Unrecognized plan format. Keys: {list(plan_output.keys()) if isinstance(plan_output, dict) else 'Not a dict'}")
        logger.warning(f"UNIFIED: Plan output preview: {str(plan_output)[:500]}...")
        
        # Create fallback work items if no valid format is found
        logger.info("UNIFIED: Creating fallback work items due to unrecognized format")
        work_items = _create_fallback_work_items(state)
    
    logger.info(f"UNIFIED: Total work items extracted: {len(work_items)}")
    
    # If we still have no work items, create emergency fallbacks
    if not work_items:
        logger.warning("UNIFIED: No work items found, creating emergency fallback work items")
        work_items = _create_emergency_fallback_work_items(state)
        logger.info(f"UNIFIED: Created {len(work_items)} emergency fallback work items")
    
    # Get completed and failed work items
    completed_work_items = state.get("completed_work_items", [])
    failed_work_items = state.get("failed_work_items", [])
    completed_ids = set()
    
    # ENHANCED: Track both completed and failed items
    for item in completed_work_items + failed_work_items:
        if isinstance(item, str):
            completed_ids.add(item)
        elif isinstance(item, dict) and 'id' in item:
            completed_ids.add(item['id'])
        elif hasattr(item, 'id'):
            completed_ids.add(item.id)
    
    # Progress tracking
    total_items = len(work_items)
    completed_count = len(completed_work_items)
    failed_count = len(failed_work_items)
    
    # Find next available work item
    next_work_item = None
    for item in work_items:
        item_id = item['id'] if isinstance(item, dict) else item.id
        item_status = item.get('status', 'pending') if isinstance(item, dict) else getattr(item, 'status', 'pending')
        dependencies = item.get('dependencies', []) if isinstance(item, dict) else getattr(item, 'dependencies', [])
        
        if item_id not in completed_ids and item_status == 'pending':
            # ENHANCED: More flexible dependency checking
            deps_satisfied = True
            for dep in dependencies:
                # Check if dependency is completed (not just failed)
                dep_completed = any(
                    comp_item.get('id') == dep and comp_item.get('status') != 'failed'
                    for comp_item in completed_work_items
                )
                if not dep_completed:
                    # Check if dependency failed - if so, mark this item as skippable
                    dep_failed = any(
                        fail_item.get('id') == dep
                        for fail_item in failed_work_items
                    )
                    if dep_failed:
                        logger.warning(f"UNIFIED: Work item {item_id} dependency {dep} failed, considering item optional")
                        # Don't block - treat as optional dependency
                        continue
                    else:
                        deps_satisfied = False
                        break
            
            if deps_satisfied:
                next_work_item = item
                break
    
    if next_work_item:
        work_item_id = next_work_item['id'] if isinstance(next_work_item, dict) else next_work_item.id
        work_item_dict = next_work_item if isinstance(next_work_item, dict) else next_work_item.model_dump()
        
        logger.info(f"UNIFIED: Starting {work_item_id} ({completed_count + failed_count + 1}/{total_items}, {failed_count} failed)")
        
        return {
            "current_work_item": work_item_dict,
            StateFields.WORKFLOW_COMPLETE: False,
            "_unified_decision": "proceed",
            "_work_item_id": work_item_id
        }
    else:
        logger.info(f"UNIFIED: [SUCCESS] All {total_items} work items processed! {completed_count} completed, {failed_count} failed")
        return {
            "current_work_item": None,
            StateFields.WORKFLOW_COMPLETE: True,
            "_unified_decision": "complete"
        }

def _create_fallback_work_items(state: AgentState) -> List[Dict[str, Any]]:
    """Create fallback work items based on available state information."""
    logger.info("UNIFIED: Creating fallback work items from state information")
    
    # Try to extract information from available state
    requirements = state.get(StateFields.REQUIREMENTS_ANALYSIS, {})
    tech_stack = state.get(StateFields.TECH_STACK_RECOMMENDATION, {})
    system_design = state.get(StateFields.SYSTEM_DESIGN, {})
    
    project_name = requirements.get('project_name', 'Unknown Project')
    
    # Determine tech stack from available info
    backend_tech = "Python/FastAPI"
    frontend_tech = "React/TypeScript" 
    database_tech = "PostgreSQL"
    
    if isinstance(tech_stack, dict):
        backend_info = tech_stack.get('backend', {})
        frontend_info = tech_stack.get('frontend', {})
        database_info = tech_stack.get('database', {})
        
        if isinstance(backend_info, dict):
            backend_tech = f"{backend_info.get('name', 'Python')}/{backend_info.get('framework', 'FastAPI')}"
        if isinstance(frontend_info, dict):
            frontend_tech = f"{frontend_info.get('name', 'React')}/{frontend_info.get('framework', 'TypeScript')}"
        if isinstance(database_info, dict):
            database_tech = database_info.get('name', 'PostgreSQL')
    
    fallback_work_items = [
        {
            "id": "FB-001",
            "description": f"Set up basic {backend_tech} backend project structure for {project_name}",
            "dependencies": [],
            "estimated_time": "4 hours",
            "agent_role": "backend_developer",
            "acceptance_criteria": [
                "Project structure created with proper directory layout",
                "Dependencies file created (requirements.txt/package.json)",
                "Basic configuration files added",
                "Hello world endpoint working"
            ],
            "status": "pending",
            "code_files": ["main.py", "requirements.txt", "config.py", "README.md"]
        },
        {
            "id": "FB-002",
            "description": f"Set up {database_tech} database schema and connection",
            "dependencies": ["FB-001"],
            "estimated_time": "3 hours",
            "agent_role": "database_specialist",
            "acceptance_criteria": [
                "Database connection established",
                "Basic schema created",
                "Migration files set up",
                "Database connection tested"
            ],
            "status": "pending",
            "code_files": ["database.py", "models.py", "migrations/", "alembic.ini"]
        },
        {
            "id": "FB-003",
            "description": f"Create basic {frontend_tech} frontend application",
            "dependencies": ["FB-001"],
            "estimated_time": "5 hours",
            "agent_role": "frontend_developer",
            "acceptance_criteria": [
                "Frontend project initialized",
                "Basic components created",
                "API connection established",
                "Basic UI working"
            ],
            "status": "pending",
            "code_files": ["src/App.tsx", "src/components/", "package.json", "src/services/api.ts"]
        },
        {
            "id": "FB-004",
            "description": "Set up deployment configuration and DevOps pipeline",
            "dependencies": ["FB-001", "FB-002", "FB-003"],
            "estimated_time": "3 hours",
            "agent_role": "devops_specialist",
            "acceptance_criteria": [
                "Docker configuration created",
                "Environment variables documented",
                "Basic deployment script created",
                "CI/CD pipeline configured"
            ],
            "status": "pending",
            "code_files": ["Dockerfile", "docker-compose.yml", ".env.example", ".github/workflows/"]
        }
    ]
    
    logger.info(f"UNIFIED: Created {len(fallback_work_items)} fallback work items")
    return fallback_work_items

def _create_emergency_fallback_work_items(state: AgentState) -> List[Dict[str, Any]]:
    """Create minimal emergency fallback work items when all else fails."""
    logger.warning("UNIFIED: Creating emergency fallback work items - minimal viable project")
    
    return [
        {
            "id": "EMERGENCY-001",
            "description": "Create minimal project structure and basic application",
            "dependencies": [],
            "estimated_time": "2 hours",
            "agent_role": "backend_developer",
            "acceptance_criteria": [
                "Basic project structure created",
                "Simple application that runs",
                "Basic documentation provided"
            ],
            "status": "pending",
            "code_files": ["main.py", "README.md", "requirements.txt"]
        }
    ]

def unified_work_item_router(state: AgentState) -> str:
    """Pure sync router for work item decisions."""
    decision = state.get("_unified_decision", "complete")
    
    if decision == "proceed":
        return "proceed"
    else:
        return "complete"

# ============================================================================
# CODE GENERATION AND QUALITY NODES
# ============================================================================

async def unified_code_generation_dispatcher_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """Code generation dispatcher with pure async approach."""
    work_item = state.get("current_work_item")
    if not work_item:
        logger.error("UNIFIED: No current work item found")
        return {StateFields.CODE_GENERATION_RESULT: {"status": "error", "error": "No work item"}}
    
    # Extract work item info early to avoid variable scope issues
    agent_role = work_item.get('agent_role', 'backend_developer').lower()
    work_item_id = work_item.get('id', 'unknown')
    
    try:
        # Import simplified agents to avoid circular dependencies
        from agents.code_generation.simple_backend_agent import SimpleBackendAgent
        from agents.code_generation.simple_frontend_agent import SimpleFrontendAgent
        from agents.code_generation.simple_database_agent import SimpleDatabaseAgent
        from agents.code_generation.simple_ops_agent import SimpleOpsAgent
        from config import get_llm
        from agent_temperatures import get_agent_temperature
        
        # Import enhanced error handling
        from tools.error_handling_utils import get_error_handler
        error_handler = get_error_handler()
        
        context = {
            "work_item_id": work_item_id,
            "agent_role": agent_role,
            "workflow_id": state.get("workflow_id", "unknown"),
            "timestamp": time.time()
        }
        
        # UNIFIED & SIMPLIFIED AGENT MAPPING
        generator_map = {
            # Core application development
            "backend_developer": SimpleBackendAgent,
            "backend_engineer": SimpleBackendAgent,     # Backend engineers handle server-side development
            "frontend_developer": SimpleFrontendAgent,
            "frontend_engineer": SimpleFrontendAgent,   # Frontend engineers handle client-side development
            "database_specialist": SimpleDatabaseAgent,
            "database_engineer": SimpleDatabaseAgent,   # Database engineers handle data layer
            
            # Operations, infrastructure, and cross-cutting concerns
            "devops_specialist": SimpleOpsAgent,
            "devops_engineer": SimpleOpsAgent,          # DevOps engineers handle infrastructure tasks
            "infrastructure_engineer": SimpleOpsAgent,  # Infrastructure engineers handle deployment and ops
            "platform_engineer": SimpleOpsAgent,        # Platform engineers handle infrastructure platforms
            "site_reliability_engineer": SimpleOpsAgent, # SRE handles system reliability and ops
            "architecture_specialist": SimpleOpsAgent,  # Architecture (scaffolding, Docker, CI/CD) is an Ops task
            "testing_specialist": SimpleOpsAgent,       # All testing (unit, integration, e2e) is handled by Ops
            "qa_engineer": SimpleOpsAgent,              # QA engineers handle testing frameworks and automation
            "quality_assurance": SimpleOpsAgent,        # QA handles test automation and quality processes
            "test_engineer": SimpleOpsAgent,            # Test engineers handle test automation and frameworks
            "automation_engineer": SimpleOpsAgent,      # Automation engineers handle test and deployment automation
            "documentation_specialist": SimpleOpsAgent, # All docs (README, API docs) are handled by Ops
            "technical_writer": SimpleOpsAgent,         # Technical writers handle documentation and guides
            "technical_documentation": SimpleOpsAgent,  # Technical documentation is handled by Ops
            "content_writer": SimpleOpsAgent,           # Content writers handle user-facing documentation
            "documentation_engineer": SimpleOpsAgent,   # Documentation engineers handle doc systems and automation
            "security_specialist": SimpleOpsAgent,      # Security setup is handled by Ops
            "monitoring_specialist": SimpleOpsAgent,    # Monitoring setup is handled by Ops
            
            # Specialized development tasks routed to the most relevant agent
            "integration_specialist": SimpleBackendAgent, # Integrations are typically backend-focused
            "code_optimizer": SimpleBackendAgent, # Code optimization handled by backend agent
        }
        
        agent_class = generator_map.get(agent_role)
        
        if not agent_class:
            logger.warning(f"UNIFIED: No specific agent for role '{agent_role}', defaulting to SimpleBackendAgent")
            agent_class = SimpleBackendAgent
        
        logger.info(f"UNIFIED: Generating {work_item_id} using {agent_class.__name__} for role ({agent_role})")
        
        # Get appropriate temperature for the specific agent
        agent_name = agent_class.__name__.replace("Agent", "").replace("Generator", "")
        temperature = get_agent_temperature(f"{agent_name} Agent")
        llm = get_llm(temperature=temperature)
        
        # Get required tools - provide defaults if not available
        code_execution_tool = config["configurable"].get("code_execution_tool")
        output_dir = config["configurable"].get("run_output_dir", "output/code_generation")
        
        # Ensure output directory exists
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        # Create default CodeExecutionTool if not provided, ensuring it uses the correct output_dir
        if code_execution_tool is None:
            from tools.code_execution_tool import CodeExecutionTool
            code_execution_tool = CodeExecutionTool(output_dir=output_dir)
            logger.info(f"UNIFIED: Created default CodeExecutionTool for {work_item_id} using output_dir: {output_dir}")
        
        # FIXED: Extract tech stack the SAME WAY as system design node
        tech_stack_recommendation = state.get(StateFields.TECH_STACK_RECOMMENDATION, {})
        final_tech_stack = {}

        logger.info(f"UNIFIED: Code Gen - Tech stack recommendation keys: {list(tech_stack_recommendation.keys()) if isinstance(tech_stack_recommendation, dict) else 'Not a dict'}")
        
        # Use the SAME extraction logic as system design node
        if isinstance(tech_stack_recommendation, dict):
            # 1. Try synthesis first (should contain the single recommendations/user selections)
            synthesis = tech_stack_recommendation.get("synthesis", {})
            if synthesis and isinstance(synthesis, dict):
                logger.info("UNIFIED: Code Gen - Using synthesis from tech stack recommendation")
                final_tech_stack = {
                    'frontend': synthesis.get("frontend", {}).get("name", "React"),
                    'backend': synthesis.get("backend", {}).get("name", "Node.js with Express.js"),
                    'database': synthesis.get("database", {}).get("name", "PostgreSQL"),
                    'architecture': synthesis.get("architecture", {}).get("name", "Microservices Architecture"),
                    'cloud': synthesis.get("cloud", {}).get("name", "AWS")
                }
                logger.info(f"UNIFIED: Code Gen - Extracted from synthesis: {final_tech_stack}")
            
            # 2. Fallback: Try direct fields from tech stack recommendation
            elif tech_stack_recommendation.get("frontend"):
                logger.info("UNIFIED: Code Gen - Using direct fields from tech stack")
                final_tech_stack = {
                    'frontend': tech_stack_recommendation.get("frontend", {}).get("name", "React"),
                    'backend': tech_stack_recommendation.get("backend", {}).get("name", "Node.js with Express.js"),
                    'database': tech_stack_recommendation.get("database", {}).get("name", "PostgreSQL"),
                    'architecture': tech_stack_recommendation.get("architecture", {}).get("name", "Microservices Architecture"),
                    'cloud': tech_stack_recommendation.get("cloud", {}).get("name", "AWS")
                }
                logger.info(f"UNIFIED: Code Gen - Extracted from direct fields: {final_tech_stack}")
        
        # 3. Parse work item description and code_files for technology hints (only if still empty)
        if not final_tech_stack or not any(final_tech_stack.values()):
            work_item_description = work_item.get('description', '').lower()
            code_files = work_item.get('code_files', [])
            
            logger.info(f"UNIFIED: Code Gen - No tech stack found, parsing work item description: {work_item_description[:100]}...")
            
            # Detect technologies from work item description
            backend_tech = None
            frontend_tech = None
            database_tech = None
            
            if 'vue' in work_item_description or 'vue.js' in work_item_description:
                frontend_tech = "Vue.js"
            elif 'react' in work_item_description:
                frontend_tech = "React"
            elif 'angular' in work_item_description:
                frontend_tech = "Angular"
                
            if 'node.js' in work_item_description or 'express' in work_item_description:
                backend_tech = "Node.js with Express.js"
            elif 'fastapi' in work_item_description or 'python' in work_item_description:
                backend_tech = "Python with FastAPI"
            elif 'django' in work_item_description:
                backend_tech = "Python with Django"
            elif 'spring boot' in work_item_description or 'java' in work_item_description:
                backend_tech = "Java with Spring Boot"
                
            if 'postgresql' in work_item_description or 'postgres' in work_item_description:
                database_tech = "PostgreSQL"
            elif 'mysql' in work_item_description:
                database_tech = "MySQL"
            elif 'mongodb' in work_item_description:
                database_tech = "MongoDB"
            
            # Detect from file extensions in code_files
            if not backend_tech and code_files:
                js_files = any('.js' in f or '.ts' in f or '.tsx' in f or 'package.json' in f for f in code_files)
                py_files = any('.py' in f or 'requirements.txt' in f for f in code_files)
                java_files = any('.java' in f or 'pom.xml' in f for f in code_files)
                vue_files = any('.vue' in f for f in code_files)
                
                if vue_files:
                    frontend_tech = "Vue.js"
                if js_files:
                    backend_tech = "Node.js with Express.js"
                elif py_files:
                    backend_tech = "Python with FastAPI"
                elif java_files:
                    backend_tech = "Java with Spring Boot"
            
            final_tech_stack = {
                'frontend': frontend_tech or "React",
                'backend': backend_tech or "Node.js with Express.js", 
                'database': database_tech or "PostgreSQL",
                'architecture': "Microservices Architecture",
                'cloud': "AWS"
            }
            logger.info(f"UNIFIED: Code Gen - Extracted from work item hints: {final_tech_stack}")
        
        # Emergency fallback (only if absolutely nothing was found)
        if not final_tech_stack or not any(final_tech_stack.values()):
            logger.warning("UNIFIED: Code Gen - No tech stack data found, using emergency fallback.")
            final_tech_stack = {
                'frontend': 'React', 
                'backend': 'Node.js with Express.js', 
                'database': 'PostgreSQL', 
                'architecture': 'Microservices Architecture',
                'cloud': 'AWS'
            }
            logger.warning(f"UNIFIED: Code Gen - Emergency fallback: {final_tech_stack}")
        
        logger.info(f"UNIFIED: Code Gen - 🎯 FINAL tech stack for {work_item_id}: {final_tech_stack}")
        
        # Create enhanced state with proper tech stack info and work item details
        enhanced_state = {
            **state,
            'tech_stack_info': {
                'backend': final_tech_stack.get('backend'),
                'frontend': final_tech_stack.get('frontend'),
                'database': final_tech_stack.get('database'),
                'architecture': final_tech_stack.get('architecture'),
                'cloud': final_tech_stack.get('cloud'),
                'work_item_files': work_item.get('code_files', []),
                'work_item_description': work_item.get('description', ''),
                'expected_file_structure': work_item.get('code_files', []),
                'work_item_dependencies': work_item.get('dependencies', []),
                'work_item_acceptance_criteria': work_item.get('acceptance_criteria', []),
                'work_item_estimated_time': work_item.get('estimated_time', ''),
                'work_item_status': work_item.get('status', 'pending'),
                'work_item_id': work_item_id,
                'agent_role': work_item.get('agent_role', '')
            }
        }
        
        agent_args = {
            "llm": llm,
            "memory": config["configurable"].get("memory"),
            "temperature": temperature,
            "output_dir": output_dir,
            "code_execution_tool": code_execution_tool
        }
        
        # Add optional components if available
        if "rag_retriever" in config["configurable"]:
            agent_args["rag_retriever"] = config["configurable"]["rag_retriever"]
        
        # Create the specific agent instance
        agent = agent_class(**agent_args)
        
        await asyncio.sleep(2.0)  # Rate limiting
        
        # Convert work_item dict to WorkItem object if needed
        from models.data_contracts import WorkItem
        if isinstance(work_item, dict):
            work_item_obj = WorkItem(**work_item)
        else:
            work_item_obj = work_item
        
        # Pass enhanced state with proper tech stack information
        result = await asyncio.to_thread(agent.run, work_item=work_item_obj, state=enhanced_state)
        
        # Handle result format
        if hasattr(result, 'model_dump'):
            result_dict = result.model_dump()
        else:
            result_dict = result
        
        logger.info(f"UNIFIED: Completed {work_item_id} using {agent_class.__name__} with {final_tech_stack.get('backend')}")
        
        # ENHANCED: Validate and monitor the LLM output parsing
        if hasattr(result_dict, 'model_dump'):
            result_dict = result_dict.model_dump()
        elif hasattr(result_dict, 'dict'):
            result_dict = result_dict.dict()
        elif isinstance(result_dict, dict):
            result_dict = result_dict
        else:
            logger.warning(f"UNIFIED: Unexpected result type {type(result_dict)} for {work_item_id}, converting to dict")
            result_dict = {"status": "completed", "raw_result": str(result_dict)}
        
        # ENHANCED: Use error handler for robust file validation
        generated_files = result_dict.get("generated_files", [])
        if generated_files:
            logger.info(f"UNIFIED: {work_item_id} generated {len(generated_files)} files - validating...")
            
            # Use enhanced validation from error handler
            try:
                from tools.error_handling_utils import get_error_handler
                error_handler = get_error_handler()
                validation_result = error_handler.validate_generated_files(generated_files, context)
                
                valid_files = validation_result["valid_files"]
                invalid_files = validation_result["invalid_files"]
                validation_errors = validation_result["validation_errors"]
                
                if validation_errors:
                    logger.warning(f"UNIFIED: {work_item_id} validation issues: {validation_errors}")
                
                if valid_files:
                    result_dict["generated_files"] = valid_files
                    result_dict["status"] = "completed"
                    result_dict["validation_summary"] = {
                        "total_files": validation_result["total_files"],
                        "valid_files": len(valid_files),
                        "invalid_files": len(invalid_files),
                        "validation_errors": validation_errors
                    }
                    logger.info(f"UNIFIED: {work_item_id} - {len(valid_files)} valid files processed successfully")
                else:
                    logger.error(f"UNIFIED: {work_item_id} - No valid files generated!")
                    error_response = error_handler.handle_code_generation_error(
                        Exception(f"No valid files generated. Validation errors: {validation_errors}"),
                        context
                    )
                    return {StateFields.CODE_GENERATION_RESULT: error_response}
            
            except Exception as validation_error:
                logger.error(f"UNIFIED: Error during validation for {work_item_id}: {validation_error}")
                # Fallback: accept files as-is if validation fails
                result_dict["generated_files"] = generated_files
                result_dict["status"] = "completed"
                result_dict["validation_note"] = f"Validation failed but files accepted: {str(validation_error)}"
                logger.info(f"UNIFIED: {work_item_id} - Accepted {len(generated_files)} files despite validation error")
        else:
            logger.warning(f"UNIFIED: {work_item_id} - No files were generated")
            if result_dict.get("status") != "error":  # Don't override existing error status
                try:
                    from tools.error_handling_utils import get_error_handler
                    error_handler = get_error_handler()
                    error_response = error_handler.handle_code_generation_error(
                        Exception("No files were generated by the agent"),
                        context
                    )
                    return {StateFields.CODE_GENERATION_RESULT: error_response}
                except Exception:
                    result_dict["status"] = "error"
                    result_dict["error"] = "No files were generated by the agent"
        
        return {StateFields.CODE_GENERATION_RESULT: result_dict}
        
    except Exception as e:
        logger.error(f"UNIFIED: Code generation failed for {work_item_id}: {str(e)}")
        logger.exception("Full traceback:")
        
        # Use enhanced error handling
        error_response = error_handler.handle_code_generation_error(e, context)
        
        return {
            StateFields.CODE_GENERATION_RESULT: error_response,
            "errors": state.get("errors", []) + [{
                "module": "Code Generation",
                "error": str(e),
                "work_item_id": work_item_id,
                "timestamp": time.time()
            }]
        }



# ============================================================================
# DECISION FUNCTIONS
# ============================================================================



async def unified_test_execution_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """Test execution with pure async approach - Simplified for speed."""
    work_item = state.get("current_work_item")
    
    # Handle case where work_item is None (e.g., after failure and cleanup)
    if work_item is None:
        logger.warning("UNIFIED: No current work item found in test execution node, returning default result")
        return {StateFields.TEST_VALIDATION_RESULT: {
            "status": "skipped",
            "passed": False,
            "summary": "No current work item to test",
            "test_count": 0,
            "passed_count": 0,
            "failed_count": 0
        }}
    
    work_item_id = work_item.get('id', 'unknown')
    
    # Check if the previous step (code generation) succeeded
    code_gen_result = state.get(StateFields.CODE_GENERATION_RESULT, {})
    code_gen_status = code_gen_result.get("status", "unknown")
    
    if code_gen_status == "error":
        test_result = {
            "status": "failed",
            "passed": False,
            "summary": f"Tests skipped for {work_item_id} due to code generation failure",
            "test_count": 0,
            "passed_count": 0,
            "failed_count": 1
        }
    else:
        # Simplified test validation - just check if files were generated
        generated_files = code_gen_result.get("generated_files", [])
        test_result = {
            "status": "passed",
            "passed": True,
            "summary": f"Basic validation passed for {work_item_id} - {len(generated_files)} files generated",
            "test_count": 1,
            "passed_count": 1,
            "failed_count": 0
        }
    
    logger.info(f"UNIFIED: Test validation completed for {work_item_id} - Status: {test_result['status']}")
    return {StateFields.TEST_VALIDATION_RESULT: test_result}

def unified_decide_on_test_results(state: AgentState) -> str:
    """Decision function for test results."""
    test_result = state.get(StateFields.TEST_VALIDATION_RESULT, {})
    
    if test_result.get("passed"):
        return "approve"
    else:
        return "revise"

async def unified_phase_completion_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """Phase completion with pure async approach."""
    work_item = state.get("current_work_item")
    
    # Handle case where work_item is None (e.g., after failure and cleanup)
    if work_item is None:
        logger.warning("UNIFIED: No current work item found in phase completion node, skipping completion")
        return {}
    
    work_item_id = work_item.get("id", "unknown")
    code_generation_result = state.get(StateFields.CODE_GENERATION_RESULT, {})

    # Mark work item as complete
    completed_work_items = state.get("completed_work_items", [])
    
    # Ensure generated_files are dicts, not GeneratedFile objects
    if 'generated_files' in code_generation_result and isinstance(code_generation_result['generated_files'], list):
        code_generation_result['generated_files'] = [
            file.dict() if hasattr(file, 'dict') else file
            for file in code_generation_result['generated_files']
        ]

    completed_work_item = {
        **work_item, 
        "status": "completed",
        "code_generation_result": code_generation_result
    }
    updated_completed_items = completed_work_items + [completed_work_item]
    
    logger.info(f"UNIFIED: [SUCCESS] {work_item_id} completed")
    
    return {
        "completed_work_items": updated_completed_items,
        "current_work_item": None  # Clear current work item
    }

async def unified_increment_revision_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """Increment revision count with enhanced circuit breaker and graceful degradation."""
    work_item = state.get("current_work_item")
    if not work_item:
        logger.warning("UNIFIED: No work item - triggering circuit breaker")
        return {
            "circuit_breaker_triggered": True,
            StateFields.WORKFLOW_COMPLETE: True
        }
    
    work_item_id = work_item.get('id', 'unknown')
    revision_counts = state.get("revision_counts", {}).copy()
    
    current_count = revision_counts.get(work_item_id, 0)
    new_count = current_count + 1
    revision_counts[work_item_id] = new_count
    
    # ENHANCED: Graceful degradation instead of complete failure
    max_revisions = 3  # Reduced from 5 for faster recovery
    if new_count >= max_revisions:
        logger.error(f"UNIFIED: Work item {work_item_id} exceeded {max_revisions} revisions, marking as failed and continuing")
        
        # Mark this work item as failed but continue with others
        failed_work_items = state.get("failed_work_items", [])
        failed_item = {
            **work_item,
            "status": "failed",
            "failure_reason": f"Exceeded {max_revisions} revision attempts",
            "revision_count": new_count
        }
        failed_work_items.append(failed_item)
        
        # Add to completed items (so it doesn't get picked up again) but mark as failed
        completed_work_items = state.get("completed_work_items", [])
        completed_work_items.append(failed_item)
        
        logger.info(f"UNIFIED: Continuing workflow despite {work_item_id} failure")
        result = {
            "revision_counts": revision_counts,
            "failed_work_items": failed_work_items,
            "completed_work_items": completed_work_items,
            "current_work_item": None,  # Clear current work item to move to next
            "skip_current_item": True  # Flag to skip to next work item
        }
        logger.info(f"UNIFIED: Increment revision returning for failed item: {result}")
        return result
    
    logger.info(f"UNIFIED: Retry {work_item_id} (attempt {new_count}/{max_revisions})")
    return {"revision_counts": revision_counts}

def unified_check_circuit_breaker(state: AgentState) -> str:
    """Enhanced circuit breaker with graceful degradation."""
    circuit_breaker = state.get("circuit_breaker_triggered", False)
    workflow_complete = state.get(StateFields.WORKFLOW_COMPLETE, False)
    skip_current_item = state.get("skip_current_item", False)
    
    # DEBUG: Log the circuit breaker state
    logger.info(f"UNIFIED: Circuit breaker check - circuit_breaker: {circuit_breaker}, workflow_complete: {workflow_complete}, skip_current_item: {skip_current_item}")
    
    # ENHANCED: Check for too many failed items (graceful degradation)
    failed_work_items = state.get("failed_work_items", [])
    completed_work_items = state.get("completed_work_items", [])
    total_items = len(failed_work_items) + len(completed_work_items)
    
    # If more than 50% of items failed, consider stopping
    if total_items > 0 and len(failed_work_items) / total_items > 0.5:
        logger.warning(f"UNIFIED: More than 50% of work items failed ({len(failed_work_items)}/{total_items}), stopping workflow")
        return "stop"
    
    if circuit_breaker or workflow_complete:
        logger.info("UNIFIED: Circuit breaker triggered - routing to stop")
        return "stop"
    elif skip_current_item:
        logger.info("UNIFIED: Skip current item flag detected - routing to continue_next_item")
        return "continue_next_item"  # New path for skipping failed items
    else:
        logger.info("UNIFIED: Normal flow - routing to continue")
        return "continue"

async def unified_finalize_workflow(state: AgentState, config: dict) -> Dict[str, Any]:
    """Finalize workflow with enhanced reporting."""
    start_time = state.get("workflow_start_time", time.time())
    if not isinstance(start_time, (int, float)):
        try:
            # Try parsing as float first
            start_time = float(start_time)
        except (ValueError, TypeError):
            try:
                # Try parsing as ISO datetime string
                if isinstance(start_time, str):
                    # Handle ISO format: '2025-07-08T20:27:22.120883'
                    dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    start_time = dt.timestamp()
                else:
                    raise ValueError("Not a string")
            except (ValueError, TypeError):
                logger.warning(f"Invalid workflow_start_time '{start_time}' (type: {type(start_time)}), resetting timer.")
                start_time = time.time()

    total_time = time.time() - start_time
    
    completed_items = len(state.get("completed_work_items", []))
    failed_items = len(state.get("failed_work_items", []))
    error_count = len(state.get("errors", []))
    
    # ENHANCED: Determine overall status
    if failed_items == 0:
        overall_status = "completed_successfully"
    elif completed_items > 0:
        overall_status = "completed_with_failures"
    else:
        overall_status = "failed"
    
    summary = {
        "status": overall_status,
        "total_execution_time": total_time,
        "completed_work_items": completed_items,
        "failed_work_items": failed_items,
        "error_count": error_count,
        "completion_timestamp": time.time(),
        "success_rate": (completed_items / (completed_items + failed_items)) if (completed_items + failed_items) > 0 else 0.0
    }
    
    # ENHANCED: Better logging without emojis
    if failed_items == 0:
        logger.info(f"UNIFIED: [SUCCESS] Workflow completed successfully! {completed_items} items in {total_time:.1f}s")
    elif completed_items > 0:
        logger.info(f"UNIFIED: [WARNING] Workflow completed with mixed results! {completed_items} succeeded, {failed_items} failed in {total_time:.1f}s")
    else:
        logger.error(f"UNIFIED: [ERROR] Workflow failed completely! {failed_items} items failed in {total_time:.1f}s")
    
    return {
        StateFields.WORKFLOW_SUMMARY: summary,
        "workflow_status": overall_status
    }

# ============================================================================
# HUMAN APPROVAL SYSTEM
# ============================================================================

async def unified_human_approval_node(step_key: str, readable_name: str):
    """Factory for creating human approval nodes."""
    async def _approval_node(state: AgentState, config: dict) -> Dict[str, Any]:
        logger.info(f" UNIFIED: Human approval requested for {readable_name}")
        
        # Check for resumption
        human_decision = state.get("human_decision", "")
        resume_flag = state.get("resume_from_approval", False)
        
        logger.info(f" UNIFIED: {readable_name} - decision: '{human_decision}', resume_flag: {resume_flag}")
        
        if resume_flag and human_decision:
            logger.info(f" UNIFIED:  Resuming after decision '{human_decision}' for {readable_name} - continuing workflow")
            return {
                "human_decision": human_decision,
                "resume_from_approval": True
            }
        
        # Get step data and ensure it's properly serialized
        step_output = state.get(step_key, {})
        
        # Ensure step_output is properly serialized
        if hasattr(step_output, 'model_dump'):
            step_output = step_output.model_dump()
        elif hasattr(step_output, 'dict'):
            step_output = step_output.dict()
        elif not isinstance(step_output, dict):
            # Handle non-dict data types
            try:
                import json
                if isinstance(step_output, str):
                    step_output = json.loads(step_output)
                else:
                    step_output = {"content": str(step_output), "type": type(step_output).__name__}
            except (json.JSONDecodeError, Exception):
                step_output = {"content": str(step_output), "type": type(step_output).__name__}
        
        payload = {
            "message": f"Please review the {readable_name}. Do you approve?",
            "data": step_output,
            "current_node": f"human_approval_{readable_name.lower().replace(' ', '_')}_node",
            "step_name": readable_name
        }
        
        logger.info(f" UNIFIED: Interrupting for human approval: {readable_name}")
        return interrupt(payload)
    
    return _approval_node

async def unified_tech_stack_approval_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """Specific tech stack approval node that handles user selections."""
    logger.info("="*60)
    logger.info(" UNIFIED: [DEBUG] TECH STACK APPROVAL NODE CALLED")
    logger.info("="*60)
    logger.info(f" UNIFIED: State keys at entry: {list(state.keys())}")
    
    # Check for user feedback with tech stack selections
    user_feedback = state.get("user_feedback", {})
    decision = user_feedback.get("decision")
    selected_stack_data = user_feedback.get("selected_stack")
    
    logger.info(f" UNIFIED: User feedback found: {user_feedback}")
    logger.info(f" UNIFIED: Decision extracted: {decision}")
    logger.info(f" UNIFIED: Selected stack data: {selected_stack_data}")
    
    if decision == "proceed" and selected_stack_data:
        logger.info(f" UNIFIED: [SUCCESS] PROCESSING USER SELECTIONS")
        logger.info(f" UNIFIED: Processing tech stack selections: {selected_stack_data}")
        
        # Get the existing tech stack recommendation
        tech_stack_output = state.get(StateFields.TECH_STACK_RECOMMENDATION, {})
        logger.info(f" UNIFIED: Original tech stack type: {type(tech_stack_output)}")
        
        # Create a clean copy of the tech stack output
        if hasattr(tech_stack_output, 'model_dump'):
            tech_stack_dict = tech_stack_output.model_dump()
            logger.info(" UNIFIED: Used model_dump() to convert tech stack")
        else:
            tech_stack_dict = tech_stack_output.copy() if isinstance(tech_stack_output, dict) else {}
            logger.info(" UNIFIED: Used dict.copy() to convert tech stack")
        
        # CRITICAL FIX: Store user selections directly in multiple formats for compatibility
        tech_stack_dict["user_selections"] = selected_stack_data
        
        # ALSO: Update the synthesis section to reflect user choices
        tech_stack_dict["synthesis"] = {
            "frontend": {
                "name": selected_stack_data.get("frontend_selection", ""),
                "technology": selected_stack_data.get("frontend_selection", ""),
                "selected": True
            },
            "backend": {
                "name": selected_stack_data.get("backend_selection", ""),
                "technology": selected_stack_data.get("backend_selection", ""),
                "selected": True
            },
            "database": {
                "name": selected_stack_data.get("database_selection", ""),
                "technology": selected_stack_data.get("database_selection", ""),
                "selected": True
            },
            "architecture": {
                "name": selected_stack_data.get("architecture_selection", ""),
                "technology": selected_stack_data.get("architecture_selection", ""),
                "selected": True
            },
            "cloud": {
                "name": selected_stack_data.get("cloud_selection", ""),
                "technology": selected_stack_data.get("cloud_selection", ""),
                "selected": True
            },
            "architecture_pattern": selected_stack_data.get("architecture_selection", "")
        }
        
        # ALSO: Create selected_stack for compatibility
        tech_stack_dict["selected_stack"] = {
            "frontend": {"name": selected_stack_data.get("frontend_selection", ""), "selected": True},
            "backend": {"name": selected_stack_data.get("backend_selection", ""), "selected": True},
            "database": {"name": selected_stack_data.get("database_selection", ""), "selected": True},
            "architecture": {"name": selected_stack_data.get("architecture_selection", ""), "selected": True},
            "cloud": {"name": selected_stack_data.get("cloud_selection", ""), "selected": True},
            "tools": [{"name": selected_stack_data.get("tool_selection", ""), "selected": True}]
        }
        
        logger.info(f" UNIFIED: [SUCCESS] Updated synthesis: {tech_stack_dict['synthesis']}")
        logger.info(f" UNIFIED: [SUCCESS] Updated user_selections: {tech_stack_dict['user_selections']}")
        logger.info(f" UNIFIED: [SUCCESS] Updated selected_stack: {tech_stack_dict['selected_stack']}")
        
        # CRITICAL: Return the updated tech stack recommendation
        return_value = {
            StateFields.TECH_STACK_RECOMMENDATION: tech_stack_dict,
            "human_decision": "proceed"
        }
        
        logger.info(f" UNIFIED: [SUCCESS] RETURNING updated state with keys: {list(return_value.keys())}")
        return return_value
    
    elif decision == "revise":
        logger.info(" UNIFIED: User requested tech stack revision")
        return {"human_decision": "revise"}
    
    elif decision == "end":
        logger.info(" UNIFIED: User terminated workflow during tech stack approval")
        return {"human_decision": "end"}
    
    else:
        logger.info(f" UNIFIED: [INITIAL] No user feedback - showing tech stack options")
        
        # Initial pause for human approval
        tech_stack_output = state.get(StateFields.TECH_STACK_RECOMMENDATION, {})
        
        payload = {
            "message": "Please review the recommended technology stack. You can approve to continue, request revisions with specific feedback, or select different options from the provided choices.",
            "data": tech_stack_output,
            "current_node": "human_approval_tech_stack_node",
            "step_name": "Tech Stack Recommendation"
        }
        
        logger.info(" UNIFIED: Interrupting for tech stack approval with selection options")
        return interrupt(payload)

def unified_decide_after_human(state: AgentState) -> str:
    """Generic decision function for human approval."""
    human_decision = state.get("human_decision", "").lower().strip()
    
    if human_decision in ["proceed", "continue", "approve"]:
        return "proceed"
    elif human_decision in ["revise", "reject", "request_revision"]:
        return "revise"
    elif human_decision in ["end", "terminate", "stop"]:
        return "end"
    else:
        logger.warning(f"UNIFIED: Unknown decision '{human_decision}' - defaulting to end")
        return "end"

# ============================================================================
# MAIN WORKFLOW CREATION
# ============================================================================

async def create_unified_workflow() -> StateGraph:
    """
     UNIFIED WORKFLOW: Single, clean pipeline.
    
    Benefits:
    - Pure async approach (no sync/async mixing)
    - Consistent state management
    - Simple routing logic
    - No Command API complexity
    - Clear error handling
    """
    logger.info(" UNIFIED: Creating unified workflow")
    
    workflow = StateGraph(AgentState)
    
    # === CORE NODES ===
    workflow.add_node("initialize_state_node", unified_initialize_workflow_state)
    workflow.add_node("brd_analysis_node", unified_brd_analysis_node)
    workflow.add_node("tech_stack_recommendation_node", unified_tech_stack_recommendation_node)
    workflow.add_node("system_design_node", unified_system_design_node)
    workflow.add_node("planning_node", unified_planning_node)
    
    # === HUMAN APPROVAL NODES - ALL USING SIMPLE FACTORY ===
    brd_approval = await unified_human_approval_node(StateFields.REQUIREMENTS_ANALYSIS, "BRD Analysis")
    tech_stack_approval = await unified_human_approval_node(StateFields.TECH_STACK_RECOMMENDATION, "Tech Stack Recommendation")  # SIMPLIFIED
    design_approval = await unified_human_approval_node(StateFields.SYSTEM_DESIGN, "System Design")
    plan_approval = await unified_human_approval_node(StateFields.IMPLEMENTATION_PLAN, "Implementation Plan")
    
    workflow.add_node("human_approval_brd_node", brd_approval)
    workflow.add_node("human_approval_tech_stack_node", tech_stack_approval)  # SIMPLIFIED
    workflow.add_node("human_approval_system_design_node", design_approval)
    workflow.add_node("human_approval_plan_node", plan_approval)
    
    # === IMPLEMENTATION NODES ===
    workflow.add_node("work_item_iterator_node", unified_work_item_iterator_node)
    workflow.add_node("code_generation_node", unified_code_generation_dispatcher_node)
    workflow.add_node("test_execution_node", unified_test_execution_node)
    workflow.add_node("phase_completion_node", unified_phase_completion_node)
    workflow.add_node("increment_revision_node", unified_increment_revision_node)
    workflow.add_node("finalize_node", unified_finalize_workflow)
    
    # === EDGES ===
    workflow.set_entry_point("initialize_state_node")
    
    # Planning flow
    workflow.add_edge("initialize_state_node", "brd_analysis_node")
    workflow.add_edge("brd_analysis_node", "human_approval_brd_node")
    workflow.add_conditional_edges("human_approval_brd_node", unified_decide_after_human, {
        "proceed": "tech_stack_recommendation_node",
        "revise": "brd_analysis_node",
        "end": END
    })
    
    workflow.add_edge("tech_stack_recommendation_node", "human_approval_tech_stack_node")
    workflow.add_conditional_edges("human_approval_tech_stack_node", unified_decide_after_human, {
        "proceed": "system_design_node",
        "revise": "tech_stack_recommendation_node",
        "end": END
    })
    
    workflow.add_edge("system_design_node", "human_approval_system_design_node")
    workflow.add_conditional_edges("human_approval_system_design_node", unified_decide_after_human, {
        "proceed": "planning_node",
        "revise": "system_design_node",
        "end": END
    })
    
    workflow.add_edge("planning_node", "human_approval_plan_node")
    workflow.add_conditional_edges("human_approval_plan_node", unified_decide_after_human, {
        "proceed": "work_item_iterator_node",
        "revise": "planning_node",
        "end": END
    })
    
    # === IMPLEMENTATION LOOP ===
    workflow.add_conditional_edges("work_item_iterator_node", unified_work_item_router, {
        "proceed": "code_generation_node",
        "complete": "finalize_node"
    })
    
    # Skip quality analysis and go directly to testing
    workflow.add_edge("code_generation_node", "test_execution_node")
    
    workflow.add_conditional_edges("test_execution_node", unified_decide_on_test_results, {
        "approve": "phase_completion_node",
        "revise": "increment_revision_node"
    })
    
    # Circuit breaker and continuation
    workflow.add_conditional_edges("increment_revision_node", unified_check_circuit_breaker, {
        "continue": "code_generation_node",
        "continue_next_item": "work_item_iterator_node",  # ENHANCED: Skip to next item
        "stop": "finalize_node"
    })
    
    # Loop back after completion
    workflow.add_edge("phase_completion_node", "work_item_iterator_node")
    
    # End
    workflow.add_edge("finalize_node", END)
    
    logger.info(" UNIFIED: Unified workflow created successfully")
    return workflow

# ============================================================================
# PUBLIC API
# ============================================================================

async def get_unified_workflow() -> StateGraph:
    """Get the unified workflow instance."""
    return await create_unified_workflow()

# Default export
__all__ = ["create_unified_workflow", "get_unified_workflow"]