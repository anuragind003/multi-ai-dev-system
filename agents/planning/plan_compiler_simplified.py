"""
Simplified Plan Compiler Agent.
Directly calls the planning tool without ReAct framework overhead.
Returns WorkItemBacklog format directly instead of complex conversion.
"""

import logging
from typing import Dict, Any, List
import asyncio
from datetime import datetime

from agents.base_agent import BaseAgent
from tools.planning_tools_enhanced import generate_comprehensive_work_item_backlog
from models.data_contracts import WorkItemBacklog

logger = logging.getLogger(__name__)

class PlanCompilerSimplifiedAgent(BaseAgent):
    """
    Simplified Plan Compiler Agent.
    Directly calls the planning tool without ReAct framework overhead.
    Returns simple, usable WorkItemBacklog format.
    """

    def __init__(self, llm=None, **kwargs):
        """
        Initializes the PlanCompilerSimplifiedAgent.
        """
        super().__init__(
            llm=llm,
            agent_name="Plan Compiler Simplified Agent",
            agent_description="Generates comprehensive work item backlog based on system design.",
            **kwargs
        )

        # Store the tool for direct calling
        self.planning_tool = generate_comprehensive_work_item_backlog

        self.log_info("Plan Compiler Simplified Agent initialized successfully")

    def run(self, requirements_analysis: dict, tech_stack_recommendation: dict, system_design: dict, **kwargs) -> Dict[str, Any]:
        """
        Generates a comprehensive work item backlog by directly invoking the tool.
        Returns simplified format that's ready for the workflow iterator.
        """
        self.log_info("Starting plan compilation with simplified agent (synchronous run).")
        
        try:
            # Directly call the planning tool's function to pass the LLM object
            self.log_info("Calling generate_comprehensive_work_item_backlog tool directly (synchronous call)")
            
            backlog_result = self.planning_tool.func(
                requirements_analysis=requirements_analysis,
                tech_stack_recommendation=tech_stack_recommendation,
                system_design=system_design,
                llm=self.llm
            )
            
            # ADD DEBUGGING: Log what the planning tool returned
            self.log_info(f"Planning tool returned result type: {type(backlog_result)}")
            self.log_info(f"Planning tool result keys: {list(backlog_result.keys()) if isinstance(backlog_result, dict) else 'Not a dict'}")
            
            # Standardize return format - keep it simple
            if isinstance(backlog_result, WorkItemBacklog):
                self.log_success("Planning tool executed successfully, converting to dict format.")
                # Convert WorkItemBacklog to dict and create simple structure
                return self._create_simple_plan_format(backlog_result)
                
            elif isinstance(backlog_result, dict) and "error" in backlog_result:
                self.log_error(f"Planning tool returned error: {backlog_result}")
                return self.get_default_response(Exception(backlog_result.get("details", "Unknown planning error")))
                
            else:
                self.log_warning(f"Planning tool returned unexpected result type: {type(backlog_result)}")
                
                # ADD DEBUGGING: More detailed logging for dict results
                if isinstance(backlog_result, dict):
                    self.log_info(f"Dict result has keys: {list(backlog_result.keys())}")
                    if 'work_items' in backlog_result:
                        work_items = backlog_result['work_items']
                        self.log_info(f"Found {len(work_items)} work items directly in result")
                    else:
                        self.log_warning("No 'work_items' key found in dict result")
                
                # Try to handle it anyway
                if isinstance(backlog_result, dict):
                    return self._ensure_dict_format(backlog_result)
                else:
                    return self.get_default_response(Exception(f"Unexpected planning tool result: {str(backlog_result)[:200]}"))
            
        except Exception as e:
            self.log_error(f"Error in synchronous plan compilation: {str(e)}", exc_info=True)
            return self.get_default_response(e)

    def _create_simple_plan_format(self, backlog: WorkItemBacklog) -> Dict[str, Any]:
        """
        Create a simple plan format that the workflow can easily consume.
        No complex conversions - just organize the work items into phases.
        """
        # Convert to dict first
        backlog_dict = backlog.model_dump() if hasattr(backlog, 'model_dump') else backlog
        
        # ADD DEBUGGING: Log the backlog structure
        self.log_info(f"Converting WorkItemBacklog to simple format")
        self.log_info(f"Backlog dict keys: {list(backlog_dict.keys())}")
        
        # Group work items by agent role to create simple phases
        phases_map = {}
        work_items = backlog_dict.get('work_items', [])
        
        # ADD DEBUGGING: Log work items info
        self.log_info(f"Found {len(work_items)} work items in backlog")
        for i, item in enumerate(work_items[:3]):  # Log first 3 items
            if isinstance(item, dict):
                self.log_info(f"Work item {i}: id={item.get('id', 'NO_ID')}, role={item.get('agent_role', 'NO_ROLE')}, desc={item.get('description', 'NO_DESC')[:50]}...")
        
        for item in work_items:
            agent_role = item.get('agent_role', 'general')
            phase_name = self._get_phase_name_from_role(agent_role)
            
            if phase_name not in phases_map:
                phases_map[phase_name] = {
                    "name": phase_name,
                    "description": f"Tasks for {phase_name.lower()} development",
                    "work_items": []
                }
            phases_map[phase_name]["work_items"].append(item)
        
        # Convert phases map to list
        phases = list(phases_map.values())
        
        # ADD DEBUGGING: Log final phases structure
        self.log_info(f"Created {len(phases)} phases from work items")
        for i, phase in enumerate(phases):
            self.log_info(f"Phase {i}: {phase['name']} has {len(phase['work_items'])} work items")
        
        # Create simple plan structure
        plan_output = {
            "summary": backlog_dict.get('summary', 'Implementation plan generated'),
            "phases": phases,
            "total_work_items": len(work_items),
            "metadata": backlog_dict.get('metadata', {}),
            "plan_type": "simplified_workitem_backlog"
        }
        
        self.log_info(f"Created simple plan with {len(phases)} phases and {len(work_items)} work items")
        return plan_output

    def _get_phase_name_from_role(self, agent_role: str) -> str:
        """Convert agent role to a readable phase name."""
        role_to_phase = {
            "backend_developer": "Backend Development",
            "frontend_developer": "Frontend Development", 
            "database_specialist": "Database Setup",
            "devops_specialist": "DevOps & Deployment",
            "testing_specialist": "Testing & QA",
            "architecture_specialist": "Architecture Setup",
            "integration_specialist": "Integration",
            "security_specialist": "Security Implementation",
            "monitoring_specialist": "Monitoring Setup",
            "documentation_specialist": "Documentation"
        }
        return role_to_phase.get(agent_role, "General Development")

    def _ensure_dict_format(self, result: Any) -> Dict[str, Any]:
        """Ensure result is in proper dictionary format for state management."""
        if isinstance(result, dict):
            return result
        elif hasattr(result, 'model_dump'):
            return result.model_dump()
        elif hasattr(result, 'dict'):
            return result.dict()
        else:
            # Convert to string representation and wrap in dict
            try:
                import json
                if isinstance(result, str):
                    return json.loads(result)
                else:
                    return {"content": str(result), "type": type(result).__name__}
            except (json.JSONDecodeError, Exception):
                return {"content": str(result), "type": type(result).__name__}
        
    async def arun(self, requirements_analysis: dict, tech_stack_recommendation: dict, system_design: dict, **kwargs) -> Dict[str, Any]:
        """
        Asynchronously generates a comprehensive work item backlog by delegating to the synchronous run method.
        """
        self.log_info("Asynchronous run method called. Delegating to synchronous run.")
        return await asyncio.to_thread(self.run, requirements_analysis, tech_stack_recommendation, system_design, **kwargs)

    def get_default_response(self, error: Exception) -> Dict[str, Any]:
        """Returns a default, safe response in case of a critical failure."""
        self.log_error(f"Executing default response due to error: {error}", exc_info=True)
        
        # Create a comprehensive default plan with multiple work items
        default_work_items = [
            {
                "id": "DEFAULT-001",
                "description": "Set up basic project structure and configuration",
                "dependencies": [],
                "estimated_time": "3 hours",
                "agent_role": "backend_developer",
                "acceptance_criteria": [
                    "Project directory structure created",
                    "Configuration files added",
                    "Basic dependencies defined",
                    "Initial documentation created"
                ],
                "status": "pending",
                "code_files": ["main.py", "requirements.txt", "config.py", "README.md", ".gitignore"]
            },
            {
                "id": "DEFAULT-002",
                "description": "Implement basic application core and entry point",
                "dependencies": ["DEFAULT-001"],
                "estimated_time": "4 hours",
                "agent_role": "backend_developer", 
                "acceptance_criteria": [
                    "Application entry point created",
                    "Basic routing implemented",
                    "Health check endpoint added",
                    "Error handling implemented"
                ],
                "status": "pending",
                "code_files": ["app.py", "routes.py", "middleware.py", "exceptions.py"]
            },
            {
                "id": "DEFAULT-003",
                "description": "Set up database models and connections",
                "dependencies": ["DEFAULT-001"],
                "estimated_time": "3 hours",
                "agent_role": "database_specialist",
                "acceptance_criteria": [
                    "Database connection established",
                    "Core data models defined",
                    "Migration system configured",
                    "Basic CRUD operations implemented"
                ],
                "status": "pending",
                "code_files": ["models.py", "database.py", "migrations/", "schemas.py"]
            },
            {
                "id": "DEFAULT-004",
                "description": "Create basic frontend application structure",
                "dependencies": ["DEFAULT-002"],
                "estimated_time": "4 hours",
                "agent_role": "frontend_developer",
                "acceptance_criteria": [
                    "Frontend project initialized",
                    "Component structure set up",
                    "API integration layer created",
                    "Basic UI components implemented"
                ],
                "status": "pending",
                "code_files": ["src/App.tsx", "src/components/", "src/services/", "package.json"]
            },
            {
                "id": "DEFAULT-005",
                "description": "Configure deployment and DevOps setup",
                "dependencies": ["DEFAULT-002", "DEFAULT-003"],
                "estimated_time": "2 hours",
                "agent_role": "devops_specialist",
                "acceptance_criteria": [
                    "Docker configuration created",
                    "Environment configuration documented",
                    "Basic deployment scripts added",
                    "Development setup instructions provided"
                ],
                "status": "pending",
                "code_files": ["Dockerfile", "docker-compose.yml", ".env.example", "deploy.sh"]
            },
            {
                "id": "DEFAULT-006",
                "description": "Implement testing framework and basic tests",
                "dependencies": ["DEFAULT-002", "DEFAULT-003", "DEFAULT-004"],
                "estimated_time": "3 hours",
                "agent_role": "testing_specialist",
                "acceptance_criteria": [
                    "Testing framework configured",
                    "Unit tests for core functionality",
                    "Integration tests for API endpoints",
                    "Test coverage reporting set up"
                ],
                "status": "pending",
                "code_files": ["tests/", "pytest.ini", "test_main.py", "test_models.py"]
            }
        ]
        
        # Create phases based on work items
        phases_map = {}
        for item in default_work_items:
            agent_role = item.get('agent_role', 'general')
            phase_name = self._get_phase_name_from_role(agent_role)
            
            if phase_name not in phases_map:
                phases_map[phase_name] = {
                    "name": phase_name,
                    "description": f"Tasks for {phase_name.lower()} development",
                    "work_items": []
                }
            phases_map[phase_name]["work_items"].append(item)
        
        phases = list(phases_map.values())
        
        return {
            "summary": f"Default implementation plan created due to planning error: {str(error)}. This plan provides a comprehensive foundation for project development.",
            "phases": phases,
            "total_work_items": len(default_work_items),
            "metadata": {
                "error": str(error),
                "created_at": datetime.now().isoformat(),
                "plan_type": "default_comprehensive",
                "estimated_total_time": "19 hours",
                "project_complexity": "medium",
                "risk_assessment": {
                    "risks": ["Planning process failed - using comprehensive default plan"]
                }
            },
            "plan_type": "simplified_workitem_backlog",
            "error": str(error)
        }
