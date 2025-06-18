"""
Tech stack evaluation tools for the ReAct-based TechStackAdvisorAgent.
Each tool is focused on a specific aspect of technology evaluation and selection.
"""

import json
import os
import logging
from typing import Dict, Any, List, Union, Optional
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

# Import Pydantic models
from .models import (
    # Input models
    TechnicalRequirementsSummaryInput,
    BackendEvaluationInput,
    FrontendFrameworkRecommendationInput,
    DatabaseEvaluationInput,
    ArchitecturePatternEvaluationInput,
    TechStackSynthesisInput,
    TechStackRiskAnalysisInput,
    FrontendEvaluationInput,
    
    # Output models (new)
    TechnicalRequirementsSummaryOutput,
    BackendEvaluationOutput,
    FrontendEvaluationOutput,
    DatabaseEvaluationOutput,
    ArchitecturePatternEvaluationOutput,
    TechStackSynthesisOutput,
    TechStackRiskAnalysisOutput,
    
    # Component models
    TechOption,
    ArchitecturePatternOption,
    LibraryTool,
    TechRisk,
    TechCompatibilityIssue
)

# Helper to get a configured LLM for tools (unchanged)
def get_tool_llm(temperature=0.0):
    """Get a properly configured LLM for tech stack tools."""
    from langchain_core.language_models import BaseLanguageModel
    from langchain_core.prompts import ChatPromptTemplate
      # Determine which agent is currently running this tool
    agent_context = os.environ.get("AGENT_CONTEXT", "TechStackAdvisor Agent")
    
    # Import the JsonHandler for reliable JSON generation
    from .json_handler import JsonHandler
    
    # Get the system LLM and configure it for deterministic output
    from config import get_llm
    llm = get_llm(temperature=temperature)
    
    # For tools that need JSON output, use the strict JSON handler
    if temperature == 0.0:
        llm = JsonHandler.create_strict_json_llm(llm)
        
    # Add tracing context to help with debugging
    llm = llm.bind(
        config={"agent_context": f"{agent_context}:tech_stack_tool"}
    )
    
    return llm

@tool(args_schema=TechnicalRequirementsSummaryInput)
def get_technical_requirements_summary(brd_analysis_json: str) -> TechnicalRequirementsSummaryOutput:
    """
    Analyzes the full requirements and returns a concise summary of only the key
    technical constraints and non-functional requirements.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Tool 'get_technical_requirements_summary' called with input length: {len(brd_analysis_json) if isinstance(brd_analysis_json, str) else 'N/A'}")
    
    # Add debugging info
    if isinstance(brd_analysis_json, str):
        logger.debug(f"Input preview (first 200 chars): {brd_analysis_json[:200]}")
        logger.debug(f"Input preview (last 200 chars): {brd_analysis_json[-200:]}")
    
    try:
        # Parse input more defensively
        brd_data = None
        if isinstance(brd_analysis_json, dict):
            brd_data = brd_analysis_json
        else:
            try:
                # Try direct JSON parsing first
                brd_data = json.loads(brd_analysis_json)
            except json.JSONDecodeError as e:
                logger.warning(f"Initial JSON parsing failed: {str(e)}")
                logger.info(f"Input length: {len(brd_analysis_json)}, error at char: {e.pos}")
                
                # Try extracting with JsonHandler
                try:
                    from .json_handler import JsonHandler
                    brd_data = JsonHandler.extract_json_from_text(brd_analysis_json)
                except ImportError:
                    logger.warning("JsonHandler not available, trying manual extraction")
                    brd_data = None
                
                # If JsonHandler fails, try to fix common JSON issues
                if not brd_data:
                    logger.info("Attempting to fix truncated JSON")
                    try:
                        # Check if the JSON is truncated and try to fix it
                        fixed_json = brd_analysis_json.strip()
                        
                        # Count braces to see if JSON is truncated
                        open_braces = fixed_json.count('{')
                        close_braces = fixed_json.count('}')
                        
                        if open_braces > close_braces:
                            # Add missing closing braces
                            missing_braces = open_braces - close_braces
                            fixed_json += '}' * missing_braces
                            logger.info(f"Added {missing_braces} missing closing braces")
                            
                            brd_data = json.loads(fixed_json)
                        else:
                            # Try parsing just the first complete JSON object
                            brace_count = 0
                            for i, char in enumerate(fixed_json):
                                if char == '{':
                                    brace_count += 1
                                elif char == '}':
                                    brace_count -= 1
                                    if brace_count == 0:
                                        # Found complete JSON object
                                        brd_data = json.loads(fixed_json[:i+1])
                                        logger.info(f"Extracted first complete JSON object (chars 0-{i})")
                                        break
                    except (json.JSONDecodeError, Exception) as fix_error:
                        logger.warning(f"JSON fix attempt failed: {str(fix_error)}")
                        brd_data = None
                
                if not brd_data:
                    logger.error("Could not extract valid JSON from input after all attempts")
                    return TechnicalRequirementsSummaryOutput(
                        summary="Error: Invalid input format. Please provide valid JSON.",
                        performance_requirements=["Unknown due to parsing error"],
                        security_requirements=["Unknown due to parsing error"],
                        technical_constraints=["Unknown due to parsing error"]
                    )
        
        # Create a Pydantic output parser
        parser = PydanticOutputParser(pydantic_object=TechnicalRequirementsSummaryOutput)
        
        # Use a simplified prompt with proper variable placeholders and format instructions
        prompt = ChatPromptTemplate.from_messages([
            ("system", 
             "You are a technical requirements analyst who extracts non-functional requirements "
             "and technical constraints from project data. Provide output in the specified JSON format."),
            ("human", 
             "Extract ONLY the technical constraints and non-functional requirements from this data:\n\n"
             "Project: {project_name}\n\n"
             "Summary: {project_summary}\n\n"
             "Requirements: \n{requirements}\n\n"
             "Focus on performance, security, scalability, integration requirements, and technical constraints."
             "Provide a concise, well-organized summary following this format:\n\n"
             "{format_instructions}")
        ])
          # Extract the required data with better fallbacks
        project_name = brd_data.get('project_name', brd_data.get('title', 'Unknown Project'))
        project_summary = brd_data.get('project_summary', brd_data.get('summary', brd_data.get('description', 'Not provided')))
        
        # Handle requirements in multiple possible formats
        requirements_raw = brd_data.get('requirements', brd_data.get('functional_requirements', []))
        if isinstance(requirements_raw, list):
            requirements = json.dumps(requirements_raw[:10], indent=2)  # Limit to first 10 to avoid token overflow
        elif isinstance(requirements_raw, dict):
            requirements = json.dumps(requirements_raw, indent=2)
        else:
            requirements = str(requirements_raw)[:1000]  # Limit string length
        
        logger.info(f"Extracted data - Project: {project_name}, Summary length: {len(project_summary)}, Requirements length: {len(requirements)}")
        
        # Create and execute the chain: prompt -> llm -> parser
        chain = prompt | get_tool_llm(temperature=0.1) | parser
        
        # Invoke the chain
        result = chain.invoke({
            "project_name": project_name,
            "project_summary": project_summary,
            "requirements": requirements,
            "format_instructions": parser.get_format_instructions()
        })
        
        return result
        
    except Exception as e:
        logger.error(f"Error in get_technical_requirements_summary: {str(e)}", exc_info=True)
        # Return a valid Pydantic object even in case of error
        return TechnicalRequirementsSummaryOutput(
            summary=f"Error extracting technical requirements: {str(e)}",
            performance_requirements=["Error occurred during extraction"],
            security_requirements=["Error occurred during extraction"],
            technical_constraints=["Error occurred during extraction"]
        )

@tool(args_schema=BackendEvaluationInput)
def evaluate_backend_options(requirements_summary: str) -> BackendEvaluationOutput:
    """
    Evaluates and compares several backend technologies based on the project requirements.
    Returns a structured analysis with comparison data and recommendations.
    """
    logger = logging.getLogger(__name__)
    logger.info("Tool 'evaluate_backend_options' called.")
    
    try:
        # Create a Pydantic output parser
        parser = PydanticOutputParser(pydantic_object=BackendEvaluationOutput)
        
        # Create a clean prompt with format instructions
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert solution architect who evaluates backend technology options."),
            ("human", 
             """You are an expert solution architect. Your task is to evaluate backend technology options
based on the provided technical summary. Analyze the summary and provide a ranked list of
2-3 suitable backend technologies.

Here is the technical summary:
{summary}

Provide your evaluation following this format:
{format_instructions}
""")
        ])

        # Get the LLM and create the chain
        llm = get_tool_llm(temperature=0.1)
        chain = prompt | llm | parser
        
        # Execute the chain
        logger.info("Invoking LLM for backend evaluation")
        result = chain.invoke({
            "summary": requirements_summary,
            "format_instructions": parser.get_format_instructions()
        })
        
        return result
        
    except Exception as e:
        logger.error(f"Error in evaluate_backend_options: {str(e)}", exc_info=True)
        # Return a valid Pydantic object even in case of error
        return BackendEvaluationOutput(
            backend_options=[
                TechOption(
                    name="Node.js",
                    framework="Express",
                    performance_score=8,
                    scalability_score=7,
                    developer_productivity=9,
                    overall_score=8,
                    reasoning="Well-suited for web applications with good ecosystem"
                ),
                TechOption(
                    name="Python",
                    framework="FastAPI",
                    performance_score=7,
                    scalability_score=8,
                    developer_productivity=8,
                    overall_score=7.5,
                    reasoning="Good for rapid development with strong typing support"
                )
            ],
            recommendation=TechOption(
                name="Node.js",
                framework="Express",
                overall_score=8,
                reasoning="Best balance of performance and developer productivity"
            )
        )

@tool(args_schema=FrontendFrameworkRecommendationInput)
def recommend_frontend_framework(requirements: str, user_experience_focus: Optional[str] = "Standard user experience with focus on usability and performance") -> FrontendEvaluationOutput:
    """Recommends frontend frameworks based on project requirements."""
    logger = logging.getLogger(__name__)
    logger.info("Tool 'recommend_frontend_framework' called")
    
    try:
        # Create a Pydantic output parser
        parser = PydanticOutputParser(pydantic_object=FrontendEvaluationOutput)
        
        # Create the prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a frontend technology expert."),
            ("human", 
             "Based on the following project requirements and UX focus, recommend "
             "2-3 frontend frameworks with justifications:\n\n"
             "PROJECT REQUIREMENTS: {requirements}\n\n"
             "UX FOCUS: {ux_focus}\n\n"
             "Format your response according to these instructions:\n"
             "{format_instructions}")
        ])
        
        # Get the LLM and create the chain
        llm = get_tool_llm(temperature=0.1)
        chain = prompt | llm | parser
        
        # Execute the chain
        result = chain.invoke({
            "requirements": requirements,
            "ux_focus": user_experience_focus,
            "format_instructions": parser.get_format_instructions()
        })
        
        return result
        
    except Exception as e:
        logger.error(f"Error in recommend_frontend_framework: {str(e)}", exc_info=True)
        # Return a valid Pydantic object even in case of error
        return FrontendEvaluationOutput(
            frontend_options=[
                TechOption(
                    name="React",
                    framework="React",
                    overall_score=9,
                    reasoning="Industry standard with extensive ecosystem"
                ),
                TechOption(
                    name="Vue.js",
                    framework="Vue.js",
                    overall_score=8,
                    reasoning="Easy learning curve with good performance"
                )
            ],
            recommendation=TechOption(
                name="React",
                framework="React",
                overall_score=9,
                reasoning="Best suited for complex UI requirements with strong ecosystem"
            )
        )

@tool(args_schema=DatabaseEvaluationInput)
def evaluate_database_options(technical_requirements: str) -> DatabaseEvaluationOutput:
    """Evaluates and recommends database technologies based on requirements."""
    logger = logging.getLogger(__name__)
    logger.info("Tool 'evaluate_database_options' called")
    
    try:
        # Create a Pydantic output parser
        parser = PydanticOutputParser(pydantic_object=DatabaseEvaluationOutput)
        
        # Create the prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a database technology expert."),
            ("human", 
             "Based on these requirements, recommend database options:\n\n"
             "{requirements}\n\n"
             "Format your response according to these instructions:\n"
             "{format_instructions}")
        ])
        
        # Get the LLM and create the chain
        llm = get_tool_llm(temperature=0.0)
        chain = prompt | llm | parser
        
        # Execute the chain
        result = chain.invoke({
            "requirements": technical_requirements,
            "format_instructions": parser.get_format_instructions()
        })
        
        return result
        
    except Exception as e:
        logger.error(f"Error in evaluate_database_options: {str(e)}", exc_info=True)
        # Return a valid Pydantic object even in case of error
        return DatabaseEvaluationOutput(
            database_options=[
                TechOption(
                    name="PostgreSQL",
                    framework=None,
                    performance_score=8,
                    scalability_score=8,
                    overall_score=7.8,
                    reasoning="Robust ACID-compliant database with excellent stability"
                ),
                TechOption(
                    name="MongoDB",
                    framework=None,
                    performance_score=7,
                    scalability_score=9,
                    overall_score=8.2,
                    reasoning="Flexible schema design with good horizontal scaling"
                )
            ],
            recommendation=TechOption(
                name="PostgreSQL",
                framework=None,
                overall_score=7.8,
                reasoning="Best balance of performance, reliability, and feature set"
            )
        )

@tool(args_schema=ArchitecturePatternEvaluationInput)
def evaluate_architecture_patterns(
    requirements_summary: str, 
    backend: str = "", 
    database: str = "", 
    frontend: str = ""
) -> ArchitecturePatternEvaluationOutput:
    """
    Evaluates architecture patterns based on the project requirements and selected technologies.
    """
    logger = logging.getLogger(__name__)
    logger.info("Tool 'evaluate_architecture_patterns' called.")
    
    try:
        # Create a Pydantic output parser
        parser = PydanticOutputParser(pydantic_object=ArchitecturePatternEvaluationOutput)
        
        # Build technology stack context
        tech_stack = ""
        if backend or database or frontend:
            tech_stack = "Technology Selections:"
            if backend:
                tech_stack += f"\n- Backend: {backend}"
            if database:
                tech_stack += f"\n- Database: {database}"
            if frontend:
                tech_stack += f"\n- Frontend: {frontend}"
        
        # Create the prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an architecture expert."),
            ("human", 
             """You are an architecture expert. Your task is to evaluate architecture patterns
based on the provided requirements and technology selections.

Technical Requirements: {requirements}
{tech_stack}

Provide your evaluation according to these instructions:
{format_instructions}""")
        ])
        
        # Get the LLM and create the chain
        llm = get_tool_llm(temperature=0.0)
        chain = prompt | llm | parser
        
        # Execute the chain
        result = chain.invoke({
            "requirements": requirements_summary,
            "tech_stack": tech_stack,
            "format_instructions": parser.get_format_instructions()
        })
        
        return result
        
    except Exception as e:
        logger.error(f"Error in evaluate_architecture_patterns: {str(e)}", exc_info=True)
        # Return a valid Pydantic object even in case of error
        return ArchitecturePatternEvaluationOutput(
            architecture_options=[
                ArchitecturePatternOption(
                    pattern="Microservices",
                    scalability_score=9,
                    maintainability_score=7,
                    development_speed_score=6,
                    overall_score=7.5,
                    reasoning="Excellent scalability and separation of concerns"
                ),
                ArchitecturePatternOption(
                    pattern="Monolithic MVC",
                    scalability_score=6,
                    maintainability_score=8,
                    development_speed_score=9,
                    overall_score=7.5,
                    reasoning="Faster initial development and simpler deployment"
                )
            ],
            recommendation={
                "pattern": "Monolithic MVC",
                "reasoning": "Best suited for the project scale and complexity"
            }
        )

@tool(args_schema=TechStackSynthesisInput)
def synthesize_tech_stack(
    backend_recommendation: str, 
    frontend_recommendation: str, 
    database_recommendation: str, 
    architecture_recommendation: str = ""
) -> TechStackSynthesisOutput:
    """
    Combines all technology recommendations into a comprehensive tech stack.
    Use this as your final step after all evaluations are complete.
    """
    logger = logging.getLogger(__name__)
    logger.info("Tool 'synthesize_tech_stack' called.")
    
    try:
        # Create a Pydantic output parser
        parser = PydanticOutputParser(pydantic_object=TechStackSynthesisOutput)
        
        # Add architecture section if available
        arch_rec = ""
        if architecture_recommendation:
            arch_rec = f"\nArchitecture Recommendation:\n{architecture_recommendation}"
        
        # Create the prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a technology stack architect."),
            ("human", 
             """You are a technology stack architect. Your task is to synthesize individual technology 
recommendations into a comprehensive tech stack.

Technology Recommendations:

Backend Recommendation:
{backend_rec}

Frontend Recommendation:
{frontend_rec}

Database Recommendation:
{database_rec}
{arch_rec}

Provide your comprehensive tech stack according to these instructions:
{format_instructions}""")
        ])
        
        # Get the LLM and create the chain
        llm = get_tool_llm(temperature=0.0)
        chain = prompt | llm | parser
        
        # Execute the chain
        result = chain.invoke({
            "backend_rec": backend_recommendation,
            "frontend_rec": frontend_recommendation,
            "database_rec": database_recommendation,
            "arch_rec": arch_rec,
            "format_instructions": parser.get_format_instructions()
        })
        
        return result
        
    except Exception as e:
        logger.error(f"Error in synthesize_tech_stack: {str(e)}", exc_info=True)
        # Return a valid Pydantic object even in case of error
        default_libraries = [
            LibraryTool(name="Jest", purpose="Testing framework"),
            LibraryTool(name="Webpack", purpose="Module bundler"),
            LibraryTool(name="Sequelize", purpose="ORM for database interactions")
        ]
        
        return TechStackSynthesisOutput(
            backend={
                "language": "JavaScript",
                "framework": "Node.js/Express",
                "reasoning": "Well-suited for web applications with good ecosystem"
            },
            frontend={
                "language": "JavaScript",
                "framework": "React",
                "reasoning": "Popular, well-supported library with strong ecosystem"
            },
            database={
                "type": "PostgreSQL",
                "reasoning": "Reliable relational database with excellent feature set"
            },
            architecture_pattern="MVC with REST API",
            deployment_environment={
                "platform": "Cloud (AWS)",
                "containerization": "Docker"
            },
            key_libraries_tools=default_libraries,
            estimated_complexity="Medium"
        )

@tool(args_schema=TechStackRiskAnalysisInput)
def analyze_tech_stack_risks(
    tech_stack_json: str, 
    requirements_summary: str
) -> TechStackRiskAnalysisOutput:
    """
    Analyzes potential risks and challenges in the selected technology stack.
    Use this after synthesizing the tech stack to identify potential issues.
    """
    logger = logging.getLogger(__name__)
    logger.info("Tool 'analyze_tech_stack_risks' called.")
    
    try:
        # Create a Pydantic output parser
        parser = PydanticOutputParser(pydantic_object=TechStackRiskAnalysisOutput)
        
        # Create the prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a technology risk analyst."),
            ("human", 
             """You are a technology risk analyst. Your task is to evaluate potential risks, challenges,
and compatibility issues in the proposed technology stack.

Tech Stack:
{tech_stack}

Project Requirements:
{requirements}

Provide your risk analysis according to these instructions:
{format_instructions}""")
        ])
        
        # Get the LLM and create the chain
        llm = get_tool_llm(temperature=0.1)
        chain = prompt | llm | parser
        
        # Execute the chain
        result = chain.invoke({
            "tech_stack": tech_stack_json,
            "requirements": requirements_summary,
            "format_instructions": parser.get_format_instructions()
        })
        
        return result
        
    except Exception as e:
        logger.error(f"Error in analyze_tech_stack_risks: {str(e)}", exc_info=True)
        # Return a valid Pydantic object even in case of error
        return TechStackRiskAnalysisOutput(
            risks=[
                TechRisk(
                    category="Technology Adoption",
                    description="Team may need time to adapt to the selected stack",
                    severity="Medium",
                    likelihood="Medium",
                    mitigation="Provide training and documentation"
                ),
                TechRisk(
                    category="Scalability",
                    description="Solution may face challenges with very high user loads",
                    severity="Medium",
                    likelihood="Low",
                    mitigation="Implement caching and horizontal scaling"
                )
            ],
            technology_compatibility_issues=[
                TechCompatibilityIssue(
                    components=["Frontend", "Backend"],
                    potential_issue="API integration challenges",
                    solution="Establish clear API contracts early"
                )
            ]
        )

@tool(args_schema=FrontendEvaluationInput)
def evaluate_frontend_options(requirements: str, user_experience: Optional[str] = "Standard user experience with focus on usability and performance") -> FrontendEvaluationOutput:
    """Evaluates frontend framework options based on requirements and user experience focus."""
    logger = logging.getLogger(__name__)
    logger.info("Tool 'evaluate_frontend_options' called")
    
    try:
        # Create a Pydantic output parser
        parser = PydanticOutputParser(pydantic_object=FrontendEvaluationOutput)
        
        # Create the prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a frontend technology specialist."),
            ("human", 
             """Evaluate frontend framework options for a project with these requirements: {requirements}

The user experience focus is: {ux_focus}

Provide a detailed analysis with pros and cons of at least 3 modern frontend frameworks according to these instructions:
{format_instructions}""")
        ])
        
        # Get the LLM and create the chain
        llm = get_tool_llm(temperature=0.2)
        chain = prompt | llm | parser
        
        # Execute the chain
        result = chain.invoke({
            "requirements": requirements,
            "ux_focus": user_experience,
            "format_instructions": parser.get_format_instructions()
        })
        
        return result
        
    except Exception as e:
        logger.error(f"Error in evaluate_frontend_options: {e}", exc_info=True)
        # Return a valid Pydantic object even in case of error
        return FrontendEvaluationOutput(
            frontend_options=[
                TechOption(
                    name="React",
                    framework="React",
                    overall_score=9.0,
                    reasoning="Industry standard with extensive ecosystem"
                ),
                TechOption(
                    name="Vue.js",
                    framework="Vue.js",
                    overall_score=8.0,
                    reasoning="Easy learning curve with good performance"
                ),
                TechOption(
                    name="Angular",
                    framework="Angular",
                    overall_score=7.5,
                    reasoning="Complete framework with strong enterprise features"
                )
            ],
            recommendation=TechOption(
                name="React",
                framework="React",
                overall_score=9.0,
                reasoning="Best suited for most web application needs"
            )
        )