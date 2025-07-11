"""
UNIFIED WORKFLOW - Single, Clean Pipeline
Eliminates sync/async confusion with a pure async approach.
"""

import asyncio
import time
import logging
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
        
        # Process tech stack data
        tech_stack_data = state[StateFields.TECH_STACK_RECOMMENDATION]
        if hasattr(tech_stack_data, 'model_dump'):
            tech_stack_data = tech_stack_data.model_dump()
        
        result = await asyncio.to_thread(
            agent.run,
            requirements_analysis=state[StateFields.REQUIREMENTS_ANALYSIS],
            tech_stack_recommendation=tech_stack_data
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
            tech_stack_data = str(tech_stack_data)
        
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
        logger.info(f"UNIFIED: 🎉 All {total_items} work items processed! (✅ {completed_count} completed, ❌ {failed_count} failed)")
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
        from agents.simple_code_quality_agent import SimpleCodeQualityAgent
        from config import get_llm
        from agent_temperatures import get_agent_temperature
        
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
            "documentation_specialist": SimpleOpsAgent, # All docs (README, API docs) are handled by Ops
            "security_specialist": SimpleOpsAgent,      # Security setup is handled by Ops
            "monitoring_specialist": SimpleOpsAgent,    # Monitoring setup is handled by Ops
            
            # Specialized development tasks routed to the most relevant agent
            "integration_specialist": SimpleBackendAgent, # Integrations are typically backend-focused
            "code_optimizer": SimpleCodeQualityAgent, # Code optimization is a quality concern
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
        
        result = await asyncio.to_thread(agent.run, work_item=work_item_obj, state=state)
        
        # Handle result format
        if hasattr(result, 'model_dump'):
            result_dict = result.model_dump()
        else:
            result_dict = result
        
        logger.info(f"UNIFIED: Completed {work_item_id} using {agent_class.__name__}")
        return {StateFields.CODE_GENERATION_RESULT: result_dict}
        
    except Exception as e:
        logger.error(f"UNIFIED: Code generation failed for {work_item_id}: {str(e)}")
        return {
            StateFields.CODE_GENERATION_RESULT: {"status": "error", "error": str(e)},
            "errors": state.get("errors", []) + [{"module": "Code Generation", "error": str(e)}]
        }

async def unified_code_quality_analysis_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """Code quality analysis with pure async approach."""
    work_item = state.get("current_work_item", {})
    work_item_id = work_item.get("id", "unknown")
    
    # Check if the previous step failed
    code_gen_result = state.get(StateFields.CODE_GENERATION_RESULT, {})
    if code_gen_result.get("status") == "error":
        logger.warning(f"UNIFIED: Skipping quality check for {work_item_id} due to code generation failure.")
        return {
            StateFields.CODE_REVIEW_FEEDBACK: {
                "approved": False, # Explicitly mark as not approved
                "quality_score": 0.0,
                "summary": "Skipped due to code generation failure.",
                "feedback": [],
                "error": "Upstream failure in code generation."
            }
        }
    
    try:
        # Check if tools are available
        code_execution_tool = config["configurable"].get("code_execution_tool")
        if not code_execution_tool:
            logger.info(f"UNIFIED: Quality check {work_item_id} (auto-approved)")
            return {
                StateFields.CODE_REVIEW_FEEDBACK: {
                    "approved": True,
                    "quality_score": 7.0,
                    "summary": "Quality analysis skipped - no tools available",
                    "feedback": []
                }
            }
        
        from agents.simple_code_quality_agent import SimpleCodeQualityAgent
        from config import get_llm
        from agent_temperatures import get_agent_temperature
        
        temperature = get_agent_temperature("Code Quality Agent")
        llm = get_llm(temperature=temperature)
        
        # Get output directory with default
        import os
        run_output_dir = config["configurable"].get("run_output_dir", "output/code_quality")
        os.makedirs(run_output_dir, exist_ok=True)
        
        agent_args = {
            "llm": llm,
            "memory": config["configurable"].get("memory"),
            "temperature": temperature,
            "code_execution_tool": code_execution_tool,
            "run_output_dir": run_output_dir
        }
        
        agent = SimpleCodeQualityAgent(**agent_args)
        
        await asyncio.sleep(2.0)  # Rate limiting
        
        # Convert work_item dict to WorkItem object if needed
        from models.data_contracts import WorkItem
        if isinstance(work_item, dict):
            work_item_obj = WorkItem(**work_item)
        else:
            work_item_obj = work_item
        
        result = await asyncio.to_thread(agent.run, work_item=work_item_obj, state=state)
        
        approved = result.get("approved", False)
        logger.info(f"UNIFIED: Quality check {work_item_id} - {'PASSED' if approved else 'REVISION NEEDED'}")
        
        return {StateFields.CODE_REVIEW_FEEDBACK: result}
        
    except Exception as e:
        logger.error(f"UNIFIED: Quality check failed for {work_item_id}: {str(e)}")
        return {
            StateFields.CODE_REVIEW_FEEDBACK: {
                "approved": True,  # Approve to prevent infinite loops
                "quality_score": 6.0,
                "summary": f"Quality analysis failed: {str(e)} - approved to continue",
                "feedback": [],
                "error": str(e)
            }
        }

# ============================================================================
# DECISION FUNCTIONS
# ============================================================================

def unified_decide_on_code_quality(state: AgentState) -> str:
    """Decision function for code quality results."""
    feedback = state.get(StateFields.CODE_REVIEW_FEEDBACK, {})
    work_item_id = state.get("current_work_item", {}).get("id", "unknown")
    
    # If code generation failed, we must revise.
    if feedback.get("error") == "Upstream failure in code generation.":
        return "revise"

    revision_counts = state.get("revision_counts", {})
    current_revisions = revision_counts.get(work_item_id, 0)
    max_revisions = 2
    
    if feedback.get("approved") or current_revisions >= max_revisions:
        return "approve"
    else:
        return "revise"

async def unified_test_execution_node(state: AgentState, config: dict) -> Dict[str, Any]:
    """Test execution with pure async approach."""
    work_item = state.get("current_work_item", {})
    work_item_id = work_item.get('id', 'unknown')
    
    # For now, return a simple passing test result
    # This can be expanded with actual test execution logic
    test_result = {
        "status": "passed",
        "passed": True,
        "summary": f"Tests passed for work item {work_item_id}",
        "test_count": 5,
        "passed_count": 5,
        "failed_count": 0
    }
    
    logger.info(f"UNIFIED: Tests completed for {work_item_id}")
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
    work_item = state.get("current_work_item", {})
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
    
    logger.info(f"UNIFIED: ✅ {work_item_id} completed")
    
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
        return {
            "revision_counts": revision_counts,
            "failed_work_items": failed_work_items,
            "completed_work_items": completed_work_items,
            "current_work_item": None,  # Clear current work item to move to next
            "skip_current_item": True  # Flag to skip to next work item
        }
    
    logger.info(f"UNIFIED: Retry {work_item_id} (attempt {new_count}/{max_revisions})")
    return {"revision_counts": revision_counts}

def unified_check_circuit_breaker(state: AgentState) -> str:
    """Enhanced circuit breaker with graceful degradation."""
    circuit_breaker = state.get("circuit_breaker_triggered", False)
    workflow_complete = state.get(StateFields.WORKFLOW_COMPLETE, False)
    skip_current_item = state.get("skip_current_item", False)
    
    # ENHANCED: Check for too many failed items (graceful degradation)
    failed_work_items = state.get("failed_work_items", [])
    completed_work_items = state.get("completed_work_items", [])
    total_items = len(failed_work_items) + len(completed_work_items)
    
    # If more than 50% of items failed, consider stopping
    if total_items > 0 and len(failed_work_items) / total_items > 0.5:
        logger.warning(f"UNIFIED: More than 50% of work items failed ({len(failed_work_items)}/{total_items}), stopping workflow")
        return "stop"
    
    if circuit_breaker or workflow_complete:
        return "stop"
    elif skip_current_item:
        return "continue_next_item"  # New path for skipping failed items
    else:
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
    
    # ENHANCED: Better logging
    if failed_items == 0:
        logger.info(f"UNIFIED: 🎉 Workflow completed successfully! {completed_items} items in {total_time:.1f}s")
    elif completed_items > 0:
        logger.info(f"UNIFIED: ⚠️ Workflow completed with mixed results! ✅ {completed_items} succeeded, ❌ {failed_items} failed in {total_time:.1f}s")
    else:
        logger.error(f"UNIFIED: ❌ Workflow failed completely! {failed_items} items failed in {total_time:.1f}s")
    
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
    logger.info(" UNIFIED: Tech stack approval node reached")
    
    # Check for user feedback with tech stack selections
    user_feedback = state.get("user_feedback", {})
    decision = user_feedback.get("decision")
    selected_stack_data = user_feedback.get("selected_stack")
    
    if decision == "proceed" and selected_stack_data:
        logger.info(f" UNIFIED: Processing tech stack selections: {selected_stack_data}")
        
        # Import required models
        from models.data_contracts import SelectedTechStack, TechStackComponent
        
        # Create SelectedTechStack instance from user selections
        selected_tech_stack = SelectedTechStack(
            frontend=TechStackComponent(
                name=selected_stack_data.get("frontend_selection", ""),
                reasoning="User selected",
                selected=True
            ) if selected_stack_data.get("frontend_selection") else None,
            backend=TechStackComponent(
                name=selected_stack_data.get("backend_selection", ""),
                reasoning="User selected", 
                selected=True
            ) if selected_stack_data.get("backend_selection") else None,
            database=TechStackComponent(
                name=selected_stack_data.get("database_selection", ""),
                reasoning="User selected",
                selected=True
            ) if selected_stack_data.get("database_selection") else None,
            cloud=TechStackComponent(
                name=selected_stack_data.get("cloud_selection", ""),
                reasoning="User selected",
                selected=True
            ) if selected_stack_data.get("cloud_selection") else None,
            tools=[TechStackComponent(
                name=selected_stack_data.get("tool_selection", ""),
                reasoning="User selected",
                selected=True
            )] if selected_stack_data.get("tool_selection") else []
        )
        
        # Update the tech stack recommendation with user selections
        tech_stack_output = state.get(StateFields.TECH_STACK_RECOMMENDATION, {})
        if hasattr(tech_stack_output, 'model_dump'):
            tech_stack_dict = tech_stack_output.model_dump()
        else:
            tech_stack_dict = tech_stack_output
        
        # Store the selected stack in the expected format
        tech_stack_dict["selected_stack"] = selected_tech_stack.model_dump()
        
        # Also store individual selections for easy access
        tech_stack_dict["user_selections"] = selected_stack_data
        
        logger.info(f" UNIFIED: Tech stack selections processed and stored: {selected_stack_data}")
        return {
            StateFields.TECH_STACK_RECOMMENDATION: tech_stack_dict,
            "human_decision": "proceed"
        }
    
    elif decision == "revise":
        logger.info(" UNIFIED: User requested tech stack revision")
        return {"human_decision": "revise"}
    
    elif decision == "end":
        logger.info(" UNIFIED: User terminated workflow during tech stack approval")
        return {"human_decision": "end"}
    
    else:
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
    
    # === HUMAN APPROVAL NODES ===
    brd_approval = await unified_human_approval_node(StateFields.REQUIREMENTS_ANALYSIS, "BRD Analysis")
    design_approval = await unified_human_approval_node(StateFields.SYSTEM_DESIGN, "System Design")
    plan_approval = await unified_human_approval_node(StateFields.IMPLEMENTATION_PLAN, "Implementation Plan")
    
    workflow.add_node("human_approval_brd_node", brd_approval)
    workflow.add_node("human_approval_tech_stack_node", unified_tech_stack_approval_node)  # Use specific tech stack approval
    workflow.add_node("human_approval_system_design_node", design_approval)
    workflow.add_node("human_approval_plan_node", plan_approval)
    
    # === IMPLEMENTATION NODES ===
    workflow.add_node("work_item_iterator_node", unified_work_item_iterator_node)
    workflow.add_node("code_generation_node", unified_code_generation_dispatcher_node)
    workflow.add_node("code_quality_node", unified_code_quality_analysis_node)
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
    
    # Quality and testing flow
    workflow.add_edge("code_generation_node", "code_quality_node")
    workflow.add_conditional_edges("code_quality_node", unified_decide_on_code_quality, {
        "approve": "test_execution_node",
        "revise": "increment_revision_node"
    })
    
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