"""
Design tools for the ReAct-based SystemDesignerAgent.
Each tool is focused on a single, specific design task.
"""

import json
import os
import logging
from typing import Dict, Any, List, Optional, Union
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from datetime import datetime
from langchain_core.output_parsers import PydanticOutputParser

# Import Pydantic models
from tools.models import (
    # Input models
    ProjectRequirementsSummaryInput,
    ArchitecturePatternSelectionInput,
    SystemComponentsIdentificationInput,
    ComponentStructureDesignInput,
    DataModelDesignInput,
    ApiEndpointsDesignInput,
    SecurityArchitectureDesignInput,
    SystemDesignSynthesisInput,
    DesignQualityEvaluationInput,
    MultipleComponentStructuresDesignInput,
    
    # Output models
    ProjectRequirementsSummaryOutput,
    ArchitecturePatternOutput,
    SystemComponentsOutput,
    ComponentDesignOutput,
    DataModelOutput,
    ApiEndpointsOutput,
    SecurityArchitectureOutput,
    SystemDesignOutput,
    DesignQualityOutput,
    MultipleComponentStructuresOutput
)

# Helper to get a configured LLM for tools
def get_tool_llm(temperature=0.0):
    """
    Gets a pre-configured LLM instance suitable for use within a tool.
    This simplifies tool logic and centralizes LLM creation.
    """
    from config import get_llm
    # The get_llm function from config.py should handle all the setup.
    # We just request an LLM with the desired temperature.
    return get_llm(temperature=temperature)

@tool(args_schema=ProjectRequirementsSummaryInput)
def summarize_project_requirements(brd_analysis_json: str) -> ProjectRequirementsSummaryOutput:
    """
    Analyzes the full requirements analysis JSON and returns a concise summary
    of the project's main goal.
    """
    logger = logging.getLogger(__name__)
    logger.info("Tool 'summarize_project_requirements' called")
    
    try:
        # Parse the input JSON
        brd_data = None
        if isinstance(brd_analysis_json, dict):
            brd_data = brd_analysis_json
        else:
            try:
                brd_data = json.loads(brd_analysis_json)
            except json.JSONDecodeError as e:
                logger.warning(f"Initial JSON parsing failed: {str(e)}")
                # Try extracting with JsonHandler                from tools.json_handler import JsonHandler
                brd_data = JsonHandler.extract_json_from_text(brd_analysis_json)
                
                if not brd_data:
                    logger.error("Could not extract valid JSON from input")
                    return ProjectRequirementsSummaryOutput(
                        project_name="Unknown Project",
                        summary="Error: Invalid input format. Please provide valid JSON.",
                        technical_requirements=["Error: Could not extract requirements"],
                        functional_requirements=["Error: Could not extract requirements"]
                    )

        # Create a Pydantic output parser
        parser = PydanticOutputParser(pydantic_object=ProjectRequirementsSummaryOutput)

        # Create a clean prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert requirements analyst."),
            ("human", 
             "Extract the key project information and requirements from this data:\n\n"
             "Project: {project_name}\n\n"
             "Summary: {project_summary}\n\n"
             "Requirements: \n{requirements}\n\n"
             "Provide a concise, well-organized summary focusing on technical aspects following this format:\n"
             "{format_instructions}")
        ])

        # Format the prompt with the parsed data and get response
        chain = prompt | get_tool_llm(temperature=0.1) | parser
        
        result = chain.invoke({
            "project_name": brd_data.get("project_name", "N/A"),
            "project_summary": brd_data.get("project_summary", "N/A"),
            "requirements": json.dumps(brd_data.get("requirements", []), indent=2),
            "format_instructions": parser.get_format_instructions()
        })
        
        return result

    except Exception as e:
        logger.error(f"Error in summarize_project_requirements: {e}", exc_info=True)
        return ProjectRequirementsSummaryOutput(
            project_name="Error",
            summary=f"Error extracting project requirements: {str(e)}",
            technical_requirements=["Error occurred during extraction"],
            functional_requirements=["Error occurred during extraction"]
        )

@tool(args_schema=ArchitecturePatternSelectionInput)
def select_architecture_pattern(requirements_summary: str, tech_stack_json: Optional[str] = "{}") -> ArchitecturePatternOutput:
    """
    Selects the optimal architecture pattern based on requirements summary and optional tech stack.
    """
    logger = logging.getLogger(__name__)
    logger.info("Tool 'select_architecture_pattern' called")
    
    try:        # Parse the tech stack JSON if provided
        tech_stack = None
        if tech_stack_json and tech_stack_json != "{}":
            if isinstance(tech_stack_json, dict):
                tech_stack = tech_stack_json
            else:
                try:
                    tech_stack = json.loads(tech_stack_json)
                except json.JSONDecodeError as e:
                    logger.warning(f"Tech stack JSON parsing failed: {str(e)}")
                    tech_stack = {"note": "Could not parse tech stack"}

        # Create a Pydantic output parser
        parser = PydanticOutputParser(pydantic_object=ArchitecturePatternOutput)

        # Create a clean prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert Software Architect who selects appropriate architecture patterns."),
            ("human", 
             "Select the most appropriate architecture pattern for this project based on these requirements and technology stack.\n\n"
             "REQUIREMENTS: {requirements}\n\n"
             "TECHNOLOGY STACK: {tech_stack}\n\n"
             "Provide your recommendation with a detailed justification following this format:\n"
             "{format_instructions}")
        ])

        # Get LLM, create chain, and execute it
        chain = prompt | get_tool_llm(temperature=0.0) | parser
        
        result = chain.invoke({
            "requirements": requirements_summary,
            "tech_stack": json.dumps(tech_stack, indent=2),
            "format_instructions": parser.get_format_instructions()
        })
        
        return result

    except Exception as e:
        logger.error(f"Error in select_architecture_pattern: {e}", exc_info=True)
        return ArchitecturePatternOutput(
            pattern="Layered Architecture",
            justification=f"Error occurred during pattern selection: {str(e)}. Using Layered Architecture as a fallback as it's versatile.",
            key_benefits=["Clear separation of concerns", "Well-established pattern"],
            potential_drawbacks=["May not be optimal for this specific use case"]
        )

@tool(args_schema=SystemComponentsIdentificationInput)
def identify_system_components(requirements_summary: str, architecture_pattern: str) -> SystemComponentsOutput:
    """
    Identifies the main system components/modules needed based on requirements and architecture.
    """
    logger = logging.getLogger(__name__)
    logger.info("Tool 'identify_system_components' called")
    
    try:
        # Create prompt template with variables
        prompt = ChatPromptTemplate.from_messages([
            ("system", 
             "You are a system designer who identifies core system components. "
             "Always respond with a valid JSON array of component names."),
            ("human", 
             "Based on these project requirements and architecture pattern, "
             "identify only the main system components/modules needed:\n\n"
             "REQUIREMENTS: {requirements}\n\n"
             "ARCHITECTURE PATTERN: {architecture}\n\n"
             "Return ONLY a JSON array of component names. For example: [\"User Management\", \"Reporting Engine\"]")
        ])
        
        # Format the prompt with the variables
        formatted_prompt = prompt.format_prompt(
            requirements=requirements_summary,
            architecture=architecture_pattern
        )
          # Use strict JSON mode for reliable parsing
        from tools.json_handler import JsonHandler
        json_llm = JsonHandler.create_strict_json_llm(get_tool_llm(temperature=0.0))
        
        # Invoke LLM with the formatted prompt
        logger.debug(f"Invoking LLM for component identification with temp=0.0")
        response = json_llm.invoke(formatted_prompt)
        
        # Process response - handle different response types
        if isinstance(response, list):
            return json.dumps(response)
        
        content = response.content if hasattr(response, 'content') else str(response)
        
        # Try explicit JSON extraction as fallback
        components = JsonHandler.extract_json_from_text(content)
        if isinstance(components, list):
            return json.dumps(components)
            
        # Return default if extraction fails
        logger.warning(f"Could not extract valid component list, using default")
        return json.dumps(["Frontend", "Backend", "Database"])

    except Exception as e:
        logger.error(f"Error in identify_system_components: {str(e)}", exc_info=True)
        return json.dumps(["Frontend", "Backend", "Database"])

@tool(args_schema=ComponentStructureDesignInput)
def design_component_structure(component_name: str, requirements_summary: str) -> ComponentDesignOutput:
    """
    Designs the detailed structure for a specific system component.
    """
    logger = logging.getLogger(__name__)
    logger.info("Tool 'design_component_structure' called")
    
    try:
        # Create a clean prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert Component Designer who always responds in valid JSON."),
            ("human", 
             "Design the detailed structure for this system component:\n\n"
             "COMPONENT NAME: {component}\n\n"
             "PROJECT REQUIREMENTS: {requirements}\n\n"
             "Provide a detailed structure in JSON format including:\n"
             "- The component name\n"
             "- A list of internal sub-components with their responsibilities\n"
             "- Dependencies on other components\n"
             "- Applicable design patterns")
        ])

        # Format the prompt with the data
        formatted_prompt = prompt.format_prompt(
            component=component_name,
            requirements=requirements_summary
        )
        
        # Invoke the LLM with JSON handling
        from tools.json_handler import JsonHandler
        json_llm = JsonHandler.create_strict_json_llm(get_tool_llm(temperature=0.0))
        response = json_llm.invoke(formatted_prompt)
        
        # Process and return the content
        if isinstance(response, dict):
            return json.dumps(response)
            
        content = response.content if hasattr(response, 'content') else str(response)
        
        # Try to extract JSON object
        component_design = JsonHandler.extract_json_from_text(content)
        if isinstance(component_design, dict):
            return json.dumps(component_design)
            
        # Fallback
        fallback = {
            "name": component_name,
            "internal_components": [
                {"name": "Core Logic", "responsibility": "Main functionality of the component"}
            ],
            "dependencies": [],
            "design_patterns": ["Repository", "Factory"]
        }
        return json.dumps(fallback)

    except Exception as e:
        logger.error(f"Error in design_component_structure: {e}", exc_info=True)
        fallback = {
            "name": component_name,
            "internal_components": [
                {"name": "Core Logic", "responsibility": "Main functionality of the component"}
            ],
            "dependencies": [],
            "design_patterns": ["Repository", "Factory"],
            "error": f"Unexpected error: {e}"
        }
        return json.dumps(fallback)

@tool(args_schema=DataModelDesignInput)
def design_data_model(requirements_summary: str, components: str, database_technology: str) -> DataModelOutput:
    """
    Designs a complete data model for the system including entities, relationships and schema.
    """
    logger = logging.getLogger(__name__)
    logger.info("Tool 'design_data_model' called")

    try:
        # Safely handle components which could be a string or list
        components_data = components
        if isinstance(components, str):
            try:
                components_data = json.loads(components)
            except json.JSONDecodeError:
                components_data = [components]
                
        # Create a clean prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert Database Designer who always responds in valid JSON."),
            ("human", 
             "Design a complete data model based on these requirements and components:\n\n"
             "REQUIREMENTS: {requirements}\n\n"
             "COMPONENTS: {components}\n\n"
             "DATABASE TECHNOLOGY: {database}\n\n"
             "For SQL databases, include tables, fields, data types, and relationships.\n"
             "For NoSQL databases, include collections, document structures, and relationships.\n\n"
             "Return a JSON object with schema_type and tables/collections.")
        ])
                
        formatted_prompt = prompt.format_prompt(
            requirements=requirements_summary,
            components=json.dumps(components_data),
            database=database_technology
        )
        
        # Invoke the LLM with JSON handling
        from tools.json_handler import JsonHandler
        json_llm = JsonHandler.create_strict_json_llm(get_tool_llm(temperature=0.0))
        response = json_llm.invoke(formatted_prompt)
        
        # Process and return the content
        if isinstance(response, dict):
            return json.dumps(response)
            
        content = response.content if hasattr(response, 'content') else str(response)
        
        # Try to extract JSON object
        data_model = JsonHandler.extract_json_from_text(content)
        if isinstance(data_model, dict):
            return json.dumps(data_model)
            
        # Fallback
        fallback = {
            "schema_type": database_technology,
            "tables": [
                {
                    "name": "users",
                    "purpose": "Stores user information",
                    "fields": [
                        {"name": "id", "type": "int", "constraints": ["primary key", "auto-increment"]},
                        {"name": "username", "type": "varchar(50)", "constraints": ["not null", "unique"]}
                    ],
                    "relationships": []
                }
            ]
        }
        return json.dumps(fallback)

    except Exception as e:
        logger.error(f"Error in design_data_model: {e}", exc_info=True)
        fallback = {
            "schema_type": database_technology,
            "tables": [
                {
                    "name": "users",
                    "purpose": "Stores user information",
                    "fields": [
                        {"name": "id", "type": "int", "constraints": ["primary key"]},
                        {"name": "username", "type": "varchar(50)", "constraints": ["not null"]}
                    ]
                }
            ],
            "error": f"Unexpected error: {e}"
        }
        return json.dumps(fallback)

@tool(args_schema=ApiEndpointsDesignInput)
def design_api_endpoints(requirements_summary: str, components: str) -> ApiEndpointsOutput:
    """
    Designs the API endpoints for the system.
    """
    logger = logging.getLogger(__name__)
    logger.info("Tool 'design_api_endpoints' called")
    
    try:
        # Safely handle components which could be a string or list
        components_data = components
        if isinstance(components, str):
            try:
                components_data = json.loads(components)
            except json.JSONDecodeError:
                components_data = [components]
                
        # Create a clean prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert API Designer who always responds in valid JSON."),
            ("human", 
             "Design the API endpoints for this system based on these requirements and components:\n\n"
             "REQUIREMENTS: {requirements}\n\n"
             "COMPONENTS: {components}\n\n"
             "Return a JSON object describing the API including style (REST/GraphQL), base URL, authentication method, "
             "and a list of endpoints with their methods, paths, parameters, and response types.")
        ])
                
        formatted_prompt = prompt.format_prompt(
            requirements=requirements_summary,
            components=json.dumps(components_data)
        )
        
        # Invoke the LLM with JSON handling
        from tools.json_handler import JsonHandler
        json_llm = JsonHandler.create_strict_json_llm(get_tool_llm(temperature=0.0))
        response = json_llm.invoke(formatted_prompt)
        
        # Process and return the content
        if isinstance(response, dict):
            return json.dumps(response)
            
        content = response.content if hasattr(response, 'content') else str(response)
        
        # Try to extract JSON object
        api_design = JsonHandler.extract_json_from_text(content)
        if isinstance(api_design, dict):
            return json.dumps(api_design)
            
        # Fallback
        fallback = {
            "style": "REST",
            "base_url": "/api/v1",
            "authentication": "JWT",
            "endpoints": [
                {
                    "method": "GET",
                    "path": "/users",
                    "purpose": "List all users",
                    "parameters": [],
                    "response": {"type": "array of users"},
                    "authentication_required": True
                }
            ]
        }
        return json.dumps(fallback)

    except Exception as e:
        logger.error(f"Error in design_api_endpoints: {e}", exc_info=True)
        fallback = {
            "style": "REST",
            "base_url": "/api/v1",
            "authentication": "JWT",
            "endpoints": [
                {
                    "method": "GET",
                    "path": "/users",
                    "purpose": "List all users"
                }
            ],
            "error": f"Unexpected error: {e}"
        }
        return json.dumps(fallback)

@tool(args_schema=SecurityArchitectureDesignInput)
def design_security_architecture(requirements_summary: str, architecture_pattern: str) -> SecurityArchitectureOutput:
    """
    Designs the security architecture for the system.
    """
    logger = logging.getLogger(__name__)
    logger.info("Tool 'design_security_architecture' called")
    
    try:
        # Create a clean prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert Security Architect who always responds in valid JSON."),
            ("human", 
             "Design a comprehensive security architecture based on these requirements and architecture pattern:\n\n"
             "REQUIREMENTS: {requirements}\n\n"
             "ARCHITECTURE PATTERN: {architecture}\n\n"
             "Return a JSON object describing the security architecture including authentication method, "
             "authorization strategy, data encryption methods, and security measures.")
        ])

        # Format the prompt with the data
        formatted_prompt = prompt.format_prompt(
            requirements=requirements_summary,
            architecture=architecture_pattern
        )
        
        # Invoke the LLM with JSON handling
        from tools.json_handler import JsonHandler
        json_llm = JsonHandler.create_strict_json_llm(get_tool_llm(temperature=0.0))
        response = json_llm.invoke(formatted_prompt)
        
        # Process and return the content
        if isinstance(response, dict):
            return json.dumps(response)
            
        content = response.content if hasattr(response, 'content') else str(response)
        
        # Try to extract JSON object
        security_architecture = JsonHandler.extract_json_from_text(content)
        if isinstance(security_architecture, dict):
            return json.dumps(security_architecture)
            
        # Fallback
        fallback = {
            "authentication_method": "JWT with OAuth2",
            "authorization_strategy": "Role-based access control",
            "data_encryption": {
                "in_transit": "TLS 1.3",
                "at_rest": "AES-256"
            },
            "security_measures": [
                {
                    "category": "Input validation",
                    "implementation": "Server-side validation",
                    "mitigation": "Prevents injection attacks"
                }
            ]
        }
        return json.dumps(fallback)

    except Exception as e:
        logger.error(f"Error in design_security_architecture: {e}", exc_info=True)
        fallback = {
            "authentication_method": "JWT",
            "authorization_strategy": "RBAC",
            "data_encryption": {
                "in_transit": "TLS",
                "at_rest": "AES-256"
            },
            "security_measures": [
                {
                    "category": "Input validation",
                    "implementation": "Server-side validation"
                }
            ],
            "error": f"Unexpected error: {e}"
        }
        return json.dumps(fallback)

@tool(args_schema=SystemDesignSynthesisInput)
def synthesize_system_design(
    architecture_pattern: str,
    components: str,
    data_model: str,
    api_design: str = "",
    security_architecture: str = ""
) -> SystemDesignOutput:
    """
    Synthesizes all design components into a comprehensive system design.
    """
    logger = logging.getLogger(__name__)
    logger.info("Tool 'synthesize_system_design' called")
    
    try:
        # Parse inputs if they're JSON strings
        components_data = components if isinstance(components, list) else json.loads(components) if isinstance(components, str) else []
        data_model_data = data_model if isinstance(data_model, dict) else json.loads(data_model) if isinstance(data_model, str) else {}
        api_design_data = api_design if isinstance(api_design, dict) else json.loads(api_design) if isinstance(api_design, str) else {}
        security_architecture_data = security_architecture if isinstance(security_architecture, dict) else json.loads(security_architecture) if isinstance(security_architecture, str) else {}
        
        # Create the prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert system architect tasked with synthesizing design components into a cohesive system design."),
            ("human", 
             """Synthesize the following design components into a comprehensive system design:
             
             ARCHITECTURE PATTERN: {architecture_pattern}
             
             COMPONENTS: {components}
             
             DATA MODEL: {data_model}
             
             API ENDPOINTS: {api_design}
             
             SECURITY ARCHITECTURE: {security_architecture}
             
             Create a comprehensive, integrated system design that combines all these elements cohesively.""")
        ])
        
        # Create a Pydantic output parser
        parser = PydanticOutputParser(pydantic_object=SystemDesignOutput)
        
        # Get the LLM and create the chain
        llm = get_tool_llm(temperature=0.0)
        chain = prompt | llm | parser
        
        # Execute the chain
        result = chain.invoke({
            "architecture_pattern": architecture_pattern,
            "components": json.dumps(components_data) if isinstance(components_data, list) else components,
            "data_model": json.dumps(data_model_data) if isinstance(data_model_data, dict) else data_model,
            "api_design": json.dumps(api_design_data) if isinstance(api_design_data, dict) else api_design,
            "security_architecture": json.dumps(security_architecture_data) if isinstance(security_architecture_data, dict) else security_architecture
        })
        
        return result
        
    except Exception as e:
        logger.error(f"Error in synthesize_system_design: {str(e)}", exc_info=True)
        # Return a valid Pydantic object even in case of error
        return SystemDesignOutput(
            architecture_overview={
                "pattern": "Error Recovery Architecture",
                "description": f"Error occurred while synthesizing system design: {str(e)}"
            },
            modules=[{"name": "Error Module", "description": "Generated due to error in system design synthesis"}],
            data_model={"entities": []},
            api_endpoints=[],
            security_measures=[],
            deployment_considerations={},
            metadata={"error": True, "error_message": str(e)}
        )

@tool(args_schema=DesignQualityEvaluationInput)
def evaluate_design_quality(system_design: str) -> str:
    """
    Evaluates the quality of the system design and identifies improvement areas.
    """
    logger = logging.getLogger(__name__)
    logger.info("Tool 'evaluate_design_quality' called")
    
    try:
        # Parse the system design
        design_data = None
        if isinstance(system_design, dict):
            design_data = system_design
        else:
            try:
                design_data = json.loads(system_design)
            except json.JSONDecodeError:
                from tools.json_handler import JsonHandler
                design_data = JsonHandler.extract_json_from_text(system_design)
                if not design_data:
                    return json.dumps({
                        "overall_score": 0,
                        "error": "Could not parse system design JSON"
                    })

        # Create a clean prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert Architecture Reviewer who always responds in valid JSON."),
            ("human", 
             "Evaluate the quality of this system design and identify areas for improvement:\n\n"
             "{design}\n\n"
             "Return a JSON object with an overall score, dimension scores (modularity, scalability, "
             "security, maintainability), strengths, and improvement opportunities.")
        ])

        # Format the prompt
        formatted_prompt = prompt.format_prompt(design=json.dumps(design_data, indent=2))
        
        # Invoke the LLM with JSON handling
        from tools.json_handler import JsonHandler
        json_llm = JsonHandler.create_strict_json_llm(get_tool_llm(temperature=0.1))
        response = json_llm.invoke(formatted_prompt)
        
        # Process and return the content
        if isinstance(response, dict):
            return json.dumps(response)
            
        content = response.content if hasattr(response, 'content') else str(response)
        
        # Try to extract JSON object
        evaluation = JsonHandler.extract_json_from_text(content)
        if isinstance(evaluation, dict):
            return json.dumps(evaluation)
            
        # Fallback
        fallback = {
            "overall_score": 7.5,
            "dimension_scores": {
                "modularity": 7,
                "scalability": 8,
                "security": 7,
                "maintainability": 8
            },
            "strengths": ["Clear separation of concerns", "Good security measures"],
            "improvement_opportunities": [
                {
                    "area": "Error handling",
                    "suggestion": "Implement more comprehensive error handling",
                    "impact": "medium"
                }
            ]
        }
        return json.dumps(fallback)

    except Exception as e:
        logger.error(f"Error in evaluate_design_quality: {e}", exc_info=True)
        fallback = {
            "overall_score": 5.0,
            "dimension_scores": {
                "modularity": 5,
                "scalability": 5,
                "security": 5,
                "maintainability": 5
            },
            "strengths": ["Cannot evaluate due to error"],
            "improvement_opportunities": [
                {
                    "area": "Error handling",
                    "suggestion": "Resolve system design evaluation error",
                    "impact": "high"
                }
            ],
            "error": f"Unexpected error: {e}"
        }
        return json.dumps(fallback)

@tool(args_schema=MultipleComponentStructuresDesignInput)
def design_multiple_component_structures(component_names: List[str], requirements_summary: str) -> str:
    """
    Designs the detailed structure for multiple system components in a single batch operation.
    """
    logger = logging.getLogger(__name__)
    logger.info("Tool 'design_multiple_component_structures' called")
    
    try:
        # Early return if no components to design
        if not component_names:
            logger.warning("No component names provided.")
            return json.dumps({
                "designed_components": [],
                "message": "No component names provided."
            })

        # Create a clean prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert software architect who always responds in valid, structured JSON."),
            ("human", 
             "For EACH component name in the provided list, design its detailed internal structure:\n\n"
             "COMPONENT NAMES: {components}\n\n"
             "PROJECT REQUIREMENTS: {requirements}\n\n"
             "You MUST respond with a single, valid JSON object. The root key must be \"designed_components\", "
             "which is a list of objects. Each object must represent one of the input components.")
        ])

        # Format the prompt with the data
        formatted_prompt = prompt.format_prompt(
            components=json.dumps(component_names),
            requirements=requirements_summary
        )
        
        # Invoke the LLM with JSON handling
        from tools.json_handler import JsonHandler
        json_llm = JsonHandler.create_strict_json_llm(get_tool_llm(temperature=0.0))
        response = json_llm.invoke(formatted_prompt)
        
        # Process and return the content
        if isinstance(response, dict) and "designed_components" in response:
            return json.dumps(response)
            
        # Try to correct the structure if the response is a dict but missing the wrapper
        if isinstance(response, dict) and len(response) > 0 and "designed_components" not in response:
            corrected = {"designed_components": []}
            # Try to find component objects at the root level
            for key, value in response.items():
                if isinstance(value, dict) and "name" in value:
                    corrected["designed_components"].append(value)
            if corrected["designed_components"]:
                return json.dumps(corrected)
        
        # Try to handle response as string content
        content = response.content if hasattr(response, 'content') else str(response)
        
        # Try to extract JSON from response
        parsed_response = JsonHandler.extract_json_from_text(content)
        
        if isinstance(parsed_response, dict) and "designed_components" in parsed_response:
            return json.dumps(parsed_response)
        
        # Try to correct structure if components are at root level
        if isinstance(parsed_response, list):
            return json.dumps({"designed_components": parsed_response})
        
        # Fallback
        fallback_components = []
        for name in component_names:
            fallback_components.append({
                "name": name,
                "responsibilities": ["Main functionality of " + name],
                "internal_components": [
                    {"name": "Core", "responsibility": "Main business logic"}
                ],
                "dependencies": [],
                "design_patterns": ["Repository", "Factory"]
            })
            
        return json.dumps({
            "designed_components": fallback_components
        })

    except Exception as e:
        logger.error(f"Error in design_multiple_component_structures: {e}", exc_info=True)
        return json.dumps({
            "error": f"Unexpected error: {e}",
            "designed_components": [
                {
                    "name": "Default Component",
                    "responsibilities": ["Main functionality"],
                    "internal_components": [
                        {"name": "Core", "responsibility": "Main business logic"}
                    ],
                    "dependencies": [],
                    "design_patterns": ["Repository"]
                }
            ]
        })