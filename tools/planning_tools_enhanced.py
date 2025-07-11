"""
Enhanced, consolidated planning tools to minimize API calls and improve reliability.
"""

import logging
from typing import Dict, Any, Optional
import json

from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_core.language_models.chat_models import BaseChatModel

from models.data_contracts import WorkItemBacklog
from config import get_llm
from .tool_utils import clean_and_parse_json, log_tool_execution, validate_and_convert_pydantic

logger = logging.getLogger(__name__)


class WorkItemBacklogInput(BaseModel):
    """Input schema for the work item backlog generation tool."""
    requirements_analysis: dict = Field(description="The full, structured output from the BRD analysis phase.")
    tech_stack_recommendation: dict = Field(description="The full, structured output from the tech stack recommendation phase.")
    system_design: dict = Field(description="The full, structured output from the system design phase.")
    llm: Optional[BaseChatModel] = Field(None, description="The language model to use for the analysis.")


# --- Utility Functions ---


def _create_default_work_item_backlog(error_msg: str) -> Dict[str, Any]:
    """Create a default work item backlog structure for error cases."""
    return {
        "work_items": [
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
                "description": "Implement core application functionality",
                "dependencies": ["DEFAULT-001"],
                "estimated_time": "4 hours",
                "agent_role": "backend_developer",
                "acceptance_criteria": [
                    "Application entry point created",
                    "Basic API endpoints implemented", 
                    "Request/response handling configured",
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
                "description": "Create frontend application interface",
                "dependencies": ["DEFAULT-002"],
                "estimated_time": "4 hours", 
                "agent_role": "frontend_developer",
                "acceptance_criteria": [
                    "Frontend project initialized",
                    "Component structure created",
                    "API integration implemented",
                    "Basic user interface working"
                ],
                "status": "pending",
                "code_files": ["src/App.tsx", "src/components/", "src/services/api.ts", "package.json"]
            },
            {
                "id": "DEFAULT-005",
                "description": "Configure deployment and operations setup",
                "dependencies": ["DEFAULT-002", "DEFAULT-003"],
                "estimated_time": "2 hours",
                "agent_role": "devops_specialist", 
                "acceptance_criteria": [
                    "Docker configuration created",
                    "Environment variables documented",
                    "Deployment scripts added",
                    "Development setup documented"
                ],
                "status": "pending",
                "code_files": ["Dockerfile", "docker-compose.yml", ".env.example", "deploy.sh"]
            }
        ],
        "summary": f"Default work item backlog created due to error: {error_msg}. This comprehensive plan provides a solid foundation for project development with backend, database, frontend, and DevOps components.",
        "metadata": {
            "error": error_msg,
            "plan_type": "default_comprehensive",
            "estimated_total_time": "16 hours",
            "project_complexity": "medium",
            "total_work_items": 5,
            "risk_assessment": {
                "risks": ["Planning process failed - using comprehensive default plan"],
                "mitigation": "Default plan covers all essential project components"
            }
        },
        "status": "fallback_success"
    }


@tool(args_schema=WorkItemBacklogInput)
def generate_comprehensive_work_item_backlog(requirements_analysis: dict, tech_stack_recommendation: dict, system_design: dict, llm: Optional[BaseChatModel] = None) -> Dict[str, Any]:
    """
    Analyzes project context to generate a detailed backlog of work items.
    
    Args:
        requirements_analysis: The full JSON output from the BRD analysis agent.
        tech_stack_recommendation: The full JSON output from the tech stack recommendation agent.
        system_design: The full JSON output from the system design agent.
        llm: The language model to use for the analysis.
        
    Returns:
        A dictionary containing the work item backlog or error information.
    """
    logger.info("Executing consolidated tool: generate_comprehensive_work_item_backlog")
    
    try:
        llm_instance = llm or get_llm(temperature=0.2)
        
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are an expert technical project manager and system architect. Your task is to create a detailed, step-by-step implementation plan for a new software project by breaking it down into a granular backlog of 'Work Items'.

Your goal is to create a list of tasks so small and specific that a junior developer could pick any one of them up and complete it without further questions.

The output MUST be a raw JSON object that strictly adheres to the `WorkItemBacklog` schema. Do not add any explanatory text, markdown, or any other characters before or after the JSON object.

```json
{schema_definition_here}
```"""),
            ("human", """Please create a complete work item backlog based on this BRD analysis:
{requirements_analysis_json}

This tech stack:
{tech_stack_json}

And this system design:
{system_design_json}
""")
        ])
        
        json_schema = json.dumps(WorkItemBacklog.model_json_schema(), indent=2)
        
        chain = prompt_template | llm_instance

        # Convert Pydantic models to dictionaries if needed
        if hasattr(requirements_analysis, 'model_dump'):
            requirements_analysis = requirements_analysis.model_dump()
        if hasattr(tech_stack_recommendation, 'model_dump'):
            tech_stack_recommendation = tech_stack_recommendation.model_dump()
        if hasattr(system_design, 'model_dump'):
            system_design = system_design.model_dump()
            
        requirements_analysis_json = json.dumps(requirements_analysis, indent=2)
        tech_stack_json = json.dumps(tech_stack_recommendation, indent=2)
        system_design_json = json.dumps(system_design, indent=2)
        
        response_text = chain.invoke({
            "schema_definition_here": json_schema,
            "requirements_analysis_json": requirements_analysis_json,
            "tech_stack_json": tech_stack_json,
            "system_design_json": system_design_json,
        }).content

        # Use centralized JSON parsing
        response_json = clean_and_parse_json(response_text, "work item backlog")
        
        # Try to validate and convert using shared utility
        validated_result = validate_and_convert_pydantic(response_json, WorkItemBacklog, "work item backlog")
        
        work_items_count = len(validated_result.get("work_items", []))
        log_tool_execution("generate_comprehensive_work_item_backlog", success=True, 
                          metadata={"work_items_count": work_items_count,
                                   "has_metadata": bool(validated_result.get("metadata")),
                                   "summary_length": len(validated_result.get("summary", ""))})
        
        return validated_result

    except json.JSONDecodeError as e:
        error_msg = f"Failed to parse LLM output: {e}"
        log_tool_execution("generate_comprehensive_work_item_backlog", success=False, error_msg=error_msg)
        return _create_default_work_item_backlog(error_msg)
        
    except Exception as e:
        error_msg = f"Tool execution error: {str(e)}"
        log_tool_execution("generate_comprehensive_work_item_backlog", success=False, error_msg=error_msg)
        return _create_default_work_item_backlog(error_msg) 