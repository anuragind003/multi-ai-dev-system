"""
Enhanced, consolidated system design generation tool to minimize API calls and improve reliability.
"""

import logging
from typing import Dict, Any, Union
import json
import re

from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_core.language_models.chat_models import BaseChatModel

from config import get_llm
from models.data_contracts import ComprehensiveSystemDesignOutput
from .tool_utils import clean_and_parse_json, log_tool_execution

logger = logging.getLogger(__name__)

# --- Pydantic Model for the Consolidated Tool Output ---

class ComprehensiveSystemDesignInput(BaseModel):
    """Input schema for the comprehensive system design generation tool."""
    requirements_analysis: dict = Field(description="The full, structured output from the BRD analysis phase.")
    tech_stack_recommendation: dict = Field(description="The full, structured output from the tech stack recommendation phase.")
    llm: BaseChatModel = Field(None, description="The language model to use for the analysis.")

# --- Utility Functions ---

def _create_default_system_design(error_msg: str) -> Dict[str, Any]:
    """Create a default system design structure for error cases."""
    return {
        "status": "error",
        "error": error_msg,
        "architecture": {
            "pattern": "Monolithic",
            "justification": "Default fallback due to system design error"
        },
        "components": [],
        "data_model": {
            "schema_type": "relational",
            "tables": []
        },
        "api_endpoints": {
            "style": "REST",
            "base_url": "/api",
            "authentication": "JWT",
            "endpoints": []
        },
        "security": {
            "authentication_method": "JWT",
            "authorization_strategy": "RBAC",
            "data_encryption": {}
        },
        "scalability_and_performance": {},
        "deployment_strategy": {},
        "monitoring_and_logging": {},
        "error_handling_strategy": "Basic error handling with logging",
        "development_phases_overview": [],
        "key_risks": ["System design generation failed"],
        "design_justification": f"Default system design created due to error: {error_msg}",
        "data_flow": "Data flow analysis failed due to system design error"
    }

def _safe_llm_invoke(llm_instance, prompt_template, inputs: dict, operation_name: str) -> str:
    """Safe LLM invocation with detailed error handling and logging."""
    try:
        logger.info(f"[{operation_name}] Starting LLM invocation")
        
        # Log prompt size for debugging
        prompt_str = str(prompt_template.format(**inputs))
        logger.info(f"[{operation_name}] Prompt size: {len(prompt_str)} characters")
        
        # Create chain and invoke
        chain = prompt_template | llm_instance
        response = chain.invoke(inputs)
        
        # Extract content safely
        response_text = ""
        if hasattr(response, 'content'):
            response_text = response.content
        elif isinstance(response, str):
            response_text = response
        else:
            response_text = str(response)
        
        logger.info(f"[{operation_name}] LLM response length: {len(response_text)} characters")
        
        # Check for empty response
        if not response_text or len(response_text.strip()) == 0:
            raise ValueError("LLM returned empty response")
        
        return response_text
        
    except Exception as e:
        logger.error(f"[{operation_name}] LLM invocation failed: {str(e)}")
        raise e

# --- The New, Consolidated Tool ---

@tool(args_schema=ComprehensiveSystemDesignInput)
def generate_comprehensive_system_design(requirements_analysis: dict, tech_stack_recommendation: dict, llm: BaseChatModel = None) -> Dict[str, Any]:
    """
    Analyzes requirements and tech stack to generate a complete, well-reasoned system design
    in a single, efficient operation.
    This tool covers architectural components, data flows, API designs, database schemas,
    security, deployment, monitoring, and scalability strategies.
    
    Args:
        requirements_analysis: The full JSON output from the BRD analysis agent.
        tech_stack_recommendation: The full JSON output from the tech stack recommendation agent.
        llm: The language model to use for the analysis.
        
    Returns:
        A dictionary containing the full, structured system design or error information.
    """
    logger.info("Executing consolidated tool: generate_comprehensive_system_design")

    try:
        llm_instance = llm or get_llm(temperature=0.2)

        # Simplified prompt that focuses on essential system design elements
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are a world-class System Architect. Create a comprehensive system design as a JSON object.

CRITICAL REQUIREMENTS:
1. Return ONLY a valid JSON object - no markdown, no explanations, no extra text
2. Start with {{ and end with }}
3. Use the user's selected technologies from the tech stack
4. Include all required fields

Required JSON structure:
{{
    "architecture": {{
        "pattern": "string - architecture pattern name",
        "justification": "string - why this pattern was chosen"
    }},
    "components": [
        {{
            "name": "string - component name",
            "description": "string - component purpose",
            "category": "string - frontend/backend/database/etc",
            "technologies": ["array of tech names"],
            "responsibilities": ["array of responsibilities"]
        }}
    ],
    "data_model": {{
        "schema_type": "relational",
        "tables": [
            {{
                "name": "string - table name",
                "purpose": "string - table purpose",
                "fields": [
                    {{
                        "name": "string - field name",
                        "type": "string - data type",
                        "constraints": ["array of constraints"]
                    }}
                ]
            }}
        ]
    }},
    "api_endpoints": {{
        "style": "REST",
        "base_url": "/api",
        "authentication": "JWT",
        "endpoints": [
            {{
                "method": "GET/POST/PUT/DELETE",
                "path": "/endpoint/path",
                "purpose": "string - endpoint purpose",
                "authentication_required": true/false
            }}
        ]
    }},
    "security": {{
        "authentication_method": "JWT",
        "authorization_strategy": "RBAC",
        "data_encryption": {{
            "at_rest": "encryption method",
            "in_transit": "TLS 1.3"
        }}
    }},
    "scalability_and_performance": {{
        "caching_strategy": "Redis/Memcached",
        "load_balancing": "Application Load Balancer",
        "database_scaling": "Read replicas"
    }},
    "deployment_strategy": {{
        "containerization": "Docker",
        "orchestration": "Kubernetes/Docker Compose",
        "ci_cd": "GitLab CI/GitHub Actions"
    }},
    "monitoring_and_logging": {{
        "application_monitoring": "Prometheus + Grafana",
        "logging": "ELK Stack",
        "alerting": "PagerDuty/Slack"
    }},
    "error_handling_strategy": "string - overall error handling approach",
    "development_phases_overview": [
        {{
            "name": "phase name",
            "description": "phase description",
            "estimated_duration": "time estimate"
        }}
    ],
    "key_risks": ["array of risk descriptions"],
    "design_justification": "string - overall design justification",
    "data_flow": "string - description of how data flows through the system"
}}"""),
            ("human", """Create a system design based on these inputs:

PROJECT REQUIREMENTS:
{requirements_summary}

USER SELECTED TECH STACK:
{selected_tech_stack}

Return only the JSON object with no additional text.""")
        ])

        # --- Prioritize selected_stack and user_selections ---
        selected_stack = tech_stack_recommendation.get("selected_stack", {})
        user_selections = tech_stack_recommendation.get("user_selections", {})
        
        # Use selected stack if available, otherwise fall back to original recommendation
        if selected_stack:
            final_tech_stack = selected_stack
            logger.info(f"Using user-selected tech stack: {final_tech_stack}")
        elif user_selections:
            final_tech_stack = user_selections
            logger.info(f"Using user selections: {final_tech_stack}")
        else:
            # Fallback: extract synthesis from tech stack recommendation
            synthesis = tech_stack_recommendation.get("synthesis", {})
            if synthesis:
                final_tech_stack = {
                    "frontend": synthesis.get("frontend", {}).get("technology", "React"),
                    "backend": synthesis.get("backend", {}).get("technology", "Node.js"),
                    "database": synthesis.get("database", {}).get("technology", "PostgreSQL"),
                    "architecture": synthesis.get("architecture_pattern", "Microservices")
                }
            else:
                final_tech_stack = {
                    "frontend": "React",
                    "backend": "Node.js", 
                    "database": "PostgreSQL",
                    "architecture": "Microservices"
                }
            logger.info(f"Using fallback tech stack: {final_tech_stack}")
        
        logger.info(f"Final tech stack for system design: {final_tech_stack}")

        # Create simplified inputs
        requirements_summary = requirements_analysis.get("project_summary", "Web application project")
        if len(requirements_summary) > 1000:
            requirements_summary = requirements_summary[:1000] + "..."
        
        # Convert tech stack to simple string format
        selected_tech_stack = json.dumps(final_tech_stack, indent=2)
        
        # Use safe LLM invocation
        response_text = _safe_llm_invoke(
            llm_instance=llm_instance,
            prompt_template=prompt_template,
            inputs={
                "requirements_summary": requirements_summary,
                "selected_tech_stack": selected_tech_stack
            },
            operation_name="generate_comprehensive_system_design"
        )

        # Use centralized JSON parsing
        response_json = clean_and_parse_json(response_text, "system design")
        
        log_tool_execution("generate_comprehensive_system_design", success=True, 
                          metadata={"components_count": len(response_json.get("components", [])),
                                   "has_data_model": bool(response_json.get("data_model")),
                                   "api_endpoints_count": len(response_json.get("api_endpoints", {}).get("endpoints", []))})
        return response_json

    except json.JSONDecodeError as e:
        error_msg = f"Failed to parse LLM output: {e}"
        logger.error(f"JSON parsing failed. Response might be empty or malformed.")
        log_tool_execution("generate_comprehensive_system_design", success=False, error_msg=error_msg)
        return _create_default_system_design(error_msg)
        
    except Exception as e:
        error_msg = f"Tool execution error: {str(e)}"
        logger.error(f"System design tool failed: {error_msg}")
        log_tool_execution("generate_comprehensive_system_design", success=False, error_msg=error_msg)
        return _create_default_system_design(error_msg) 