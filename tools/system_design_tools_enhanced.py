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
    """
    logger.info("Executing consolidated tool: generate_comprehensive_system_design")

    try:
        llm_instance = llm or get_llm(temperature=0.2)

        # --- Extract single tech stack recommendation (simplified approach) ---
        logger.info(f"Tech stack recommendation type: {type(tech_stack_recommendation)}")
        logger.info(f"Tech stack recommendation keys: {list(tech_stack_recommendation.keys()) if isinstance(tech_stack_recommendation, dict) else 'Not a dict'}")
        
        final_tech_stack = {}
        
        try:
            # Use direct field extraction (new simple format from tech stack tool)
            if isinstance(tech_stack_recommendation, dict):
                # Check if it's in the simple format first (strings directly as values)
                if tech_stack_recommendation.get("frontend") and isinstance(tech_stack_recommendation.get("frontend"), str):
                    final_tech_stack = {
                        "frontend": tech_stack_recommendation.get("frontend", "React"),
                        "backend": tech_stack_recommendation.get("backend", "Node.js with Express.js"),
                        "database": tech_stack_recommendation.get("database", "PostgreSQL"),
                        "architecture": tech_stack_recommendation.get("architecture", "Microservices Architecture"),
                        "cloud": tech_stack_recommendation.get("cloud", "AWS")
                    }
                    logger.info(f"Using simple format tech stack: {final_tech_stack}")
                
                # Check if it's in the complex format (objects with name/reasoning structure)
                elif tech_stack_recommendation.get("frontend", {}).get("name"):
                    # Direct fields with name/reasoning structure
                    final_tech_stack = {
                        "frontend": tech_stack_recommendation.get("frontend", {}).get("name", "React"),
                        "backend": tech_stack_recommendation.get("backend", {}).get("name", "Node.js with Express.js"),
                        "database": tech_stack_recommendation.get("database", {}).get("name", "PostgreSQL"),
                        "architecture": tech_stack_recommendation.get("architecture", {}).get("name", "Microservices Architecture"),
                        "cloud": tech_stack_recommendation.get("cloud", {}).get("name", "AWS")
                    }
                    logger.info(f"Using direct tech stack recommendations: {final_tech_stack}")
        except Exception as tech_stack_error:
            logger.error(f"Error extracting tech stack: {str(tech_stack_error)}")
            logger.error(f"Tech stack error type: {type(tech_stack_error)}")
            raise tech_stack_error
        
        # Emergency fallback if no valid data found
        if not final_tech_stack or not any(final_tech_stack.values()):
            logger.warning("No valid tech stack data found, using emergency fallback")
            final_tech_stack = {
                "frontend": "React",
                "backend": "Node.js with Express.js", 
                "database": "PostgreSQL",
                "architecture": "Microservices Architecture",
                "cloud": "AWS"
            }
        
        logger.info(f"Final tech stack for system design: {final_tech_stack}")

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

        # Create simplified inputs - with debugging
        logger.info(f"Requirements analysis type: {type(requirements_analysis)}")
        logger.info(f"Requirements analysis keys: {list(requirements_analysis.keys()) if isinstance(requirements_analysis, dict) else 'Not a dict'}")
        
        if isinstance(requirements_analysis, dict):
            logger.info("About to call requirements_analysis.get('project_summary')")
            requirements_summary = requirements_analysis.get("project_summary", "Web application project")
            logger.info(f"Successfully got requirements_summary: {requirements_summary[:100]}...")
        else:
            logger.warning(f"Requirements analysis is not a dict (type: {type(requirements_analysis)}), using fallback")
            requirements_summary = "Web application project"
            
        if len(requirements_summary) > 1000:
            requirements_summary = requirements_summary[:1000] + "..."
        
        # Convert tech stack to simple string format
        logger.info("About to call json.dumps on final_tech_stack")
        selected_tech_stack = json.dumps(final_tech_stack, indent=2)
        logger.info(f"Successfully converted tech stack to JSON string")
        
        logger.info("About to call _safe_llm_invoke")
        
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

        logger.info("LLM invocation completed, about to parse JSON")
        logger.info(f"Response text type: {type(response_text)}")
        logger.info(f"Response text length: {len(response_text) if response_text else 'None'}")

        # Use centralized JSON parsing with try-catch for debugging
        try:
            response_json = clean_and_parse_json(response_text, "system design")
            logger.info("JSON parsing succeeded")
        except Exception as parse_error:
            logger.error(f"JSON parsing failed: {str(parse_error)}")
            logger.error(f"Parse error type: {type(parse_error)}")
            raise parse_error
        
        logger.info("JSON parsing completed, about to call log_tool_execution")
        logger.info(f"Response JSON type: {type(response_json)}")
        logger.info(f"Response JSON keys: {list(response_json.keys()) if isinstance(response_json, dict) else 'Not a dict'}")
        
        # Safe metadata extraction
        try:
            components_count = len(response_json.get("components", [])) if isinstance(response_json, dict) else 0
            has_data_model = bool(response_json.get("data_model")) if isinstance(response_json, dict) else False
            
            api_endpoints = response_json.get("api_endpoints", {}) if isinstance(response_json, dict) else {}
            api_endpoints_count = len(api_endpoints.get("endpoints", [])) if isinstance(api_endpoints, dict) else 0
            
            log_tool_execution("generate_comprehensive_system_design", success=True, 
                              metadata={"components_count": components_count,
                                       "has_data_model": has_data_model,
                                       "api_endpoints_count": api_endpoints_count})
        except Exception as metadata_error:
            logger.warning(f"Error extracting metadata: {metadata_error}")
            log_tool_execution("generate_comprehensive_system_design", success=True, 
                              metadata={"metadata_extraction_error": str(metadata_error)})
        
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