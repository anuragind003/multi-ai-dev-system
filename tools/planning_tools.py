"""
Planning tools for the ReAct-based PlanCompilerAgent.
Each tool is focused on a specific planning task to help build the implementation plan.
Enhanced with cross-tool memory management for better data sharing.
"""

import json
from typing import Dict, Any, List, Optional, Union
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from datetime import datetime
import logging
from langchain_core.output_parsers import PydanticOutputParser
from utils.react_tool_wrapper import smart_react_tool

# Enhanced Memory Management for Planning Tools
try:
    from enhanced_memory_manager import create_memory_manager, EnhancedSharedProjectMemory
    ENHANCED_MEMORY_AVAILABLE = True
except ImportError:
    ENHANCED_MEMORY_AVAILABLE = False

# Global enhanced memory instance for cross-tool communication
_tool_memory = None

def get_enhanced_tool_memory():
    """Get or create SHARED enhanced memory for planning tools."""
    global _tool_memory
    if _tool_memory is None and ENHANCED_MEMORY_AVAILABLE:
        try:
            from utils.shared_memory_hub import get_shared_memory_hub
            # Use the GLOBAL shared memory hub to prevent data isolation
            _tool_memory = get_shared_memory_hub()
            logging.info("Using GLOBAL shared memory hub for planning tools")
        except Exception as e:
            logging.warning(f"Failed to get shared memory hub for planning tools: {e}")
            _tool_memory = None
    return _tool_memory

def store_planning_data(key: str, value: Any, description: str = ""):
    """Store planning data in enhanced memory for cross-tool access."""
    memory = get_enhanced_tool_memory()
    if memory:
        try:
            memory.set(key, value, context="cross_tool")
            memory.set(key, value, context="planning_tools")
            logging.info(f"Stored planning data: {key} - {description}")
        except Exception as e:
            logging.warning(f"Failed to store planning data {key}: {e}")

def retrieve_planning_data(key: str, default: Any = None) -> Any:
    """Retrieve planning data from enhanced memory with fallbacks."""
    memory = get_enhanced_tool_memory()
    if memory:
        try:
            # Try different contexts
            for context in ["cross_tool", "planning_tools", "agent_results"]:
                value = memory.get(key, None, context=context)
                if value is not None:
                    logging.info(f"Retrieved planning data: {key} from context: {context}")
                    return value
        except Exception as e:
            logging.warning(f"Failed to retrieve planning data {key}: {e}")
    return default

def get_project_context_from_memory() -> Dict[str, Any]:
    """Get project context from enhanced memory (BRD, tech stack, system design)."""
    context = {}
    
    # Try to get BRD analysis (project analysis)
    brd_analysis = retrieve_planning_data("brd_analysis")
    if not brd_analysis:
        brd_analysis = retrieve_planning_data("project_analysis")
    if not brd_analysis:
        brd_analysis = retrieve_planning_data("requirements_analysis")
    if brd_analysis:
        context["brd_analysis"] = brd_analysis
        
    # Try to get tech stack recommendation
    tech_stack = retrieve_planning_data("tech_stack_recommendation")
    if not tech_stack:
        tech_stack = retrieve_planning_data("tech_stack_analysis")
    if tech_stack:
        context["tech_stack"] = tech_stack
        
    # Try to get system design
    system_design = retrieve_planning_data("system_design")
    if not system_design:
        system_design = retrieve_planning_data("design_analysis")
    if system_design:
        context["system_design"] = system_design
    
    # Also try to get timeline and risk data
    timeline_data = retrieve_planning_data("timeline_estimation")
    if timeline_data:
        context["timeline_estimation"] = timeline_data
        
    risk_data = retrieve_planning_data("risk_assessment")
    if risk_data:
        context["risk_assessment"] = risk_data
    
    return context

# Import Pydantic models from centralized data contracts
from models.data_contracts import (
    # Input models
    ProjectAnalysisSummaryInput,
    MajorSystemComponentsInput,
    ComponentRisksInput,
    DevelopmentPhaseInput,
    PhaseDependencyInput,
    TimelineEstimationInput,
    TechStackAnalysisInput,
    ExampleNewToolInput,
    RiskAssessmentInput,
    ComprehensivePlanInput,
    WrappedToolInput,
    BatchAnalysisInput,
    
    # Output models (new)
    ProjectAnalysisSummaryOutput,
    MajorSystemComponentsOutput,
    MajorSystemComponentOutput,  # Added this import
    ComponentRisksOutput,
    DevelopmentPhaseOutput,
    CurrentPhasesOutput,
    TimelineDetailsOutput,
    PhaseDependencyOutput,    TechStackAnalysisOutput,
    RiskAssessmentOutput,
    ComprehensivePlanOutput,
    
    # Additional models for implementation details
    ImplementationPlan,
    ProjectSummary,
    ResourceAllocation,
    PlanMetadata,
    RiskSeveritySummary
)

# Initialize global storage for phases and dependencies
# These need to be initialized at module level
_phases_store = []
_dependencies_store = []

# Helper to get a configured LLM for tools
def get_tool_llm(temperature=0.0):
    """Get a properly configured LLM for planning tools."""
    from langchain_core.language_models import BaseLanguageModel
    from langchain_core.prompts import ChatPromptTemplate
    import os
    
    # Determine which agent is currently running this tool
    agent_context = os.environ.get("AGENT_CONTEXT", "PlanCompiler Agent")
      # Import the JsonHandler for reliable JSON generation
    from tools.json_handler import JsonHandler
    
    # Get the system LLM and configure it for deterministic output
    from config import get_llm
    llm = get_llm(temperature=temperature)
    
    # For tools that need JSON output, use the strict JSON handler
    if temperature == 0.0:
        llm = JsonHandler.create_strict_json_llm(llm)
        
    # Add tracing context to help with debugging
    llm = llm.bind(
        config={"agent_context": f"{agent_context}:planning_tool"}
    )
    
    return llm

@smart_react_tool("Get project analysis summary including complexity and challenges")
def get_project_analysis_summary(project_analysis_json):
    """
    Returns a summary of the project analysis, including overall complexity,
    resource needs, and key challenges. Use this to understand the project's constraints.
    Enhanced with automatic data retrieval from memory if input is empty.
    """
    logger = logging.getLogger(__name__)
    logger.info("Tool 'get_project_analysis_summary' called")
    
    try:
        # Enhanced memory retrieval if no input provided
        if not project_analysis_json or project_analysis_json.strip() == "":
            logger.info("No project analysis provided, attempting enhanced memory retrieval")
            
            # Try to get project context from enhanced memory
            project_context = get_project_context_from_memory()
            
            if project_context.get("brd_analysis"):
                logger.info("Using BRD analysis from enhanced memory")
                analysis = project_context["brd_analysis"]
            elif project_context.get("project_analysis"):
                logger.info("Using project analysis from enhanced memory")
                analysis = project_context["project_analysis"]
            else:
                logger.warning("No project analysis found in enhanced memory, using defaults")
                analysis = {
                    "project_complexity": {"overall_complexity_score": 5},
                    "resource_requirements": {"recommended_team_size": 3},
                    "key_challenges": ["Enhanced memory retrieval - limited context available"]
                }
        else:
            # Parse the input JSON
            if isinstance(project_analysis_json, str):
                try:
                    analysis = json.loads(project_analysis_json)
                except json.JSONDecodeError:
                    logger.warning("Invalid JSON input")
                    # Return a valid Pydantic object even for invalid input
                    return ProjectAnalysisSummaryOutput(
                        complexity_score=5,
                        recommended_team_size=3,
                        key_challenges=["Invalid input provided"],
                        summary="Error: Could not parse project analysis JSON"
                    )
            else:
                analysis = project_analysis_json  # Already parsed JSON
        
        # Extract data with fallbacks
        complexity = analysis.get("project_complexity", {}).get("overall_complexity_score", 5)
        
        # Try different paths for team size
        team_size = None
        if "resource_requirements" in analysis:
            team_size = analysis["resource_requirements"].get("recommended_team_size")
        if team_size is None:
            team_size = 3  # Default
        
        # Extract challenges with fallbacks
        challenges = []
        if "key_challenges" in analysis and isinstance(analysis["key_challenges"], list):
            challenges = analysis["key_challenges"][:3]
        
        # Ensure we have actual values
        if not challenges:
            challenges = ["Project complexity management"]
            
        # Create the summary text
        summary = f"Project complexity is {complexity}/10, with a recommended team size of {team_size}. "
        if challenges:
            summary += "Key challenges: " + ", ".join(challenges)
            
        # Store result in enhanced memory for other planning tools
        result = ProjectAnalysisSummaryOutput(
            complexity_score=complexity,
            recommended_team_size=team_size,
            key_challenges=challenges,
            summary=summary
        )
        
        store_planning_data("project_analysis_summary", result.dict(), "Project analysis summary for planning")
            
        # Return the structured output
        return result
        
    except Exception as e:
        logger.error(f"Error in get_project_analysis_summary: {str(e)}", exc_info=True)
        return ProjectAnalysisSummaryOutput(
            complexity_score=5,
            recommended_team_size=3,
            key_challenges=["Error processing project analysis"],
            summary=f"Error summarizing project analysis: {str(e)}"
        )

@smart_react_tool("Extract major system components from system design")
def get_major_system_components(system_design_json):
    """
    Extracts the names of the major system modules or components from the system design document.
    Use this to know which components need to be included in the development phases.
    Enhanced with automatic data retrieval from memory if input is empty.
    """
    logger = logging.getLogger(__name__)
    logger.info("Tool 'get_major_system_components' called")
    
    try:
        # Enhanced memory retrieval if no input provided
        if not system_design_json or system_design_json.strip() == "":
            logger.info("No system design provided, attempting enhanced memory retrieval")
            
            # Try to get project context from enhanced memory
            project_context = get_project_context_from_memory()
            
            if project_context.get("system_design"):
                logger.info("Using system design from enhanced memory")
                design = project_context["system_design"]
            elif project_context.get("design_analysis"):
                logger.info("Using design analysis from enhanced memory")
                design = project_context["design_analysis"]
            else:
                logger.warning("No system design found in enhanced memory, using defaults")
                design = {
                    "modules": [
                        {"name": "Frontend Layer", "category": "ui"},
                        {"name": "Backend API", "category": "api"},
                        {"name": "Database Layer", "category": "data"}
                    ]
                }
        else:
            # Parse the input JSON
            if isinstance(system_design_json, str):
                design = json.loads(system_design_json)
            else:
                design = system_design_json  # Already parsed JSON
        
        # Try different places where components might be stored
        component_objects = []
        
        # First try modules directly
        modules = design.get("modules", [])
        if modules and isinstance(modules, list):
            for module in modules:
                if isinstance(module, dict) and "name" in module:
                    component_objects.append(
                        MajorSystemComponentOutput(
                            name=module["name"],
                            category=module.get("category", None)
                        )
                    )
        
        # If no components found in modules, try architecture_overview
        if not component_objects and "architecture_overview" in design:
            components = design.get("architecture_overview", {}).get("components", [])
            if components and isinstance(components, list):
                for comp in components:
                    if isinstance(comp, dict) and "name" in comp:
                        component_objects.append(
                            MajorSystemComponentOutput(
                                name=comp["name"],
                                category=comp.get("category", None)
                            )
                        )
        
        # If still no components found, try main_modules
        if not component_objects:
            main_modules = design.get("main_modules", [])
            if main_modules and isinstance(main_modules, list):
                for module in main_modules:
                    if isinstance(module, dict) and "name" in module:
                        component_objects.append(
                            MajorSystemComponentOutput(
                                name=module["name"],
                                category=module.get("category", None)
                            )
                        )
        
        # If we still have no components, add a default
        if not component_objects:
            component_objects = [
                MajorSystemComponentOutput(name="Frontend", category="frontend"),
                MajorSystemComponentOutput(name="Backend", category="backend"),
                MajorSystemComponentOutput(name="Database", category="database")
            ]
            
        return MajorSystemComponentsOutput(components=component_objects)
        
    except Exception as e:
        logger.error(f"Error in get_major_system_components: {str(e)}", exc_info=True)
        return MajorSystemComponentsOutput(
            components=[
                MajorSystemComponentOutput(name="Frontend", category="frontend"),
                MajorSystemComponentOutput(name="Backend", category="backend"),
                MajorSystemComponentOutput(name="Database", category="database")
            ]
        )

@smart_react_tool("Identify risks for system components")
def identify_component_risks(tool_input):
    """
    Identifies potential risks and challenges associated with each system component.
    
    Args:
        tool_input: A ComponentRisksInput object containing system_components and
                   tech_stack information
    """
    logger = logging.getLogger(__name__)
    logger.info("Tool 'identify_component_risks' called")
    try:
        # Extract data from the tool_input
        system_components = tool_input.system_components
        tech_stack = tool_input.tech_stack
        
        # Analyze risks for each component
        risks = []
        
        # Convert system_components to list if it's a string
        if isinstance(system_components, str):
            try:
                components = json.loads(system_components)
            except json.JSONDecodeError:
                components = [system_components]  # Single component
        else:
            components = system_components
            
        # Convert tech_stack to dict if it's a string
        if isinstance(tech_stack, str):
            try:
                tech_data = json.loads(tech_stack)
            except json.JSONDecodeError:
                tech_data = {}
        else:
            tech_data = tech_stack or {}
          # Analyze risks for each component with domain awareness
        domain = _detect_domain_from_components(components)
        
        for component in components:
            component_name = component if isinstance(component, str) else component.get("name", "Unknown")
            
            # Domain-specific risks
            if domain == "healthcare":
                if any(keyword in component_name.lower() for keyword in ['patient', 'medical', 'health']):
                    risks.append(f"HIPAA compliance risk for {component_name}")
                    risks.append(f"Patient data security concerns for {component_name}")
                    risks.append(f"Medical audit trail requirements for {component_name}")
                if any(keyword in component_name.lower() for keyword in ['record', 'data']):
                    risks.append(f"Data retention policy compliance for {component_name}")
            elif domain == "financial":
                if any(keyword in component_name.lower() for keyword in ['transaction', 'payment', 'account']):
                    risks.append(f"PCI-DSS compliance risk for {component_name}")
                    risks.append(f"Financial fraud detection requirements for {component_name}")
                    risks.append(f"Transaction integrity challenges for {component_name}")
                if any(keyword in component_name.lower() for keyword in ['fraud', 'security']):
                    risks.append(f"Real-time fraud monitoring complexity for {component_name}")
            elif domain == "iot":
                if any(keyword in component_name.lower() for keyword in ['device', 'sensor', 'gateway']):
                    risks.append(f"Device connectivity reliability for {component_name}")
                    risks.append(f"Edge computing resource constraints for {component_name}")
                    risks.append(f"IoT security vulnerabilities for {component_name}")
                if any(keyword in component_name.lower() for keyword in ['real-time', 'analytics']):
                    risks.append(f"High-throughput data processing challenges for {component_name}")
            elif domain == "ecommerce":
                if any(keyword in component_name.lower() for keyword in ['catalog', 'product', 'inventory']):
                    risks.append(f"Product data management complexity for {component_name}")
                    risks.append(f"Inventory synchronization challenges for {component_name}")
                if any(keyword in component_name.lower() for keyword in ['payment', 'cart', 'order']):
                    risks.append(f"Payment processing integration risks for {component_name}")
                    risks.append(f"Shopping cart abandonment mitigation for {component_name}")
            
            # Generic component-type risks (fallback)
            if "frontend" in component_name.lower() or "ui" in component_name.lower() or "interface" in component_name.lower():
                risks.append(f"User experience design complexity for {component_name}")
                risks.append(f"Cross-platform compatibility for {component_name}")
            elif "backend" in component_name.lower() or "api" in component_name.lower() or "service" in component_name.lower():
                risks.append(f"API scalability challenges for {component_name}")
                risks.append(f"Service integration complexity for {component_name}")
            elif "database" in component_name.lower() or "data" in component_name.lower():
                risks.append(f"Data migration and schema evolution for {component_name}")
                risks.append(f"Query performance optimization for {component_name}")
            else:
                risks.append(f"Integration complexity for {component_name}")
        
        # Add domain-aware tech stack risks
        if domain == "healthcare":
            if "react" in str(tech_data).lower():
                risks.append("React accessibility compliance for healthcare interfaces")
            if "node" in str(tech_data).lower():
                risks.append("Node.js security hardening for healthcare data")
        elif domain == "financial":
            if "javascript" in str(tech_data).lower():
                risks.append("Client-side security risks for financial applications")
            if any(db in str(tech_data).lower() for db in ['postgresql', 'mysql']):
                risks.append("Database encryption and backup requirements for financial data")
        else:
            # Generic tech risks
            if "react" in str(tech_data).lower():
                risks.append("React learning curve and development timeline impact")
            if "node" in str(tech_data).lower():
                risks.append("Node.js performance optimization and monitoring needs")
            
        return ComponentRisksOutput(risks=risks)
        
    except Exception as e:
        logger.error(f"Error in identify_component_risks: {str(e)}", exc_info=True)
        return ComponentRisksOutput(
            risks=[f"Error identifying risks: {str(e)}"]
        )

@tool(args_schema=DevelopmentPhaseInput)
def create_development_phase(phase_name: str, phase_type: str, tasks: List[str], 
                           duration: str, depends_on: Optional[List[str]] = None) -> str:
    """
    Creates and records a single development phase for the implementation plan.
    Use this tool repeatedly to build the full plan phase by phase.
    """
    global _phases_store
    
    try:
        # Generate a unique phase ID
        phase_id = "P" + str(len(_phases_store) + 1)
        
        # Create the phase object
        phase = {
            "phase_id": phase_id,
            "name": phase_name,
            "type": phase_type,
            "duration": duration,
            "tasks": tasks,
            "dependencies": depends_on or []
        }
        
        # Store the phase
        _phases_store.append(phase)
        
        # Using string concatenation instead of f-strings
        return "Successfully created phase '" + phase_name + "' with ID " + phase_id + ". Total phases: " + str(len(_phases_store))
    except Exception as e:
        return "Error creating development phase: " + str(e)

@tool
def list_current_phases() -> str:
    """
    Lists all phases that have been created so far.
    Use this to check what phases have already been added to the plan.
    """
    global _phases_store
    
    if not _phases_store:
        return "No phases have been created yet."
    
    phase_summary = []
    for phase in _phases_store:
        # Using string concatenation instead of f-strings
        phase_summary.append("ID: " + phase['phase_id'] + " - Name: " + phase['name'] + 
                           " - Type: " + phase['type'] + " - Duration: " + phase['duration'])
        
    return "\n".join(phase_summary)

@tool(args_schema=TimelineEstimationInput)
def get_timeline_estimation(timeline_estimation_json: str) -> str:
    """
    Extracts important timeline details from the timeline estimation document.
    Use this to understand the project duration constraints and milestones.
    """
    try:
        timeline = json.loads(timeline_estimation_json)
        
        # Extract key timeline information
        overall_duration = timeline.get("project_timeline", {}).get("estimated_duration_weeks", "Unknown")
        
        # Try to find phases or milestones
        phases = timeline.get("development_phases", [])
        milestones = timeline.get("key_milestones", [])
        
        # Create a summary using string concatenation
        result = "Overall project duration: " + str(overall_duration) + " weeks\n"
        
        if phases:
            phase_summary = []
            for phase in phases[:3]:  # Show first 3 phases
                name = phase.get("phase_name", "Unnamed phase")
                duration = phase.get("duration_days", "?")
                # Using string concatenation
                phase_summary.append("- " + name + ": " + str(duration) + " days")
            
            result += "Key phases:\n" + "\n".join(phase_summary)
            if len(phases) > 3:
                result += "\n... plus " + str(len(phases) - 3) + " more phases."
                
        if milestones:
            milestone_summary = []
            for milestone in milestones[:3]:  # Show first 3 milestones
                name = milestone.get("name", "Unnamed milestone")
                date = milestone.get("target_date", "?")
                # Using string concatenation
                milestone_summary.append("- " + name + ": " + date)
                
            result += "\nKey milestones:\n" + "\n".join(milestone_summary)
            if len(milestones) > 3:
                result += "\n... plus " + str(len(milestones) - 3) + " more milestones."
                
        return result
    except Exception as e:
        return "Error extracting timeline information: " + str(e)

@tool(args_schema=PhaseDependencyInput)
def create_dependency_between_phases(from_phase_id: str, to_phase_id: str, 
                                    dependency_type: str = "finish-to-start") -> str:
    """
    Creates a dependency relationship between two phases.
    """
    global _phases_store, _dependencies_store
    
    try:
        # Validate phase IDs
        valid_ids = [phase["phase_id"] for phase in _phases_store]
        if from_phase_id not in valid_ids:
            return "Error: Phase ID '" + from_phase_id + "' does not exist. Valid IDs are: " + ", ".join(valid_ids)
        if to_phase_id not in valid_ids:
            return "Error: Phase ID '" + to_phase_id + "' does not exist. Valid IDs are: " + ", ".join(valid_ids)
        
        # Create the dependency
        dependency = {
            "from": from_phase_id,
            "to": to_phase_id,
            "type": dependency_type
        }
        
        # Store the dependency
        _dependencies_store.append(dependency)
        
        # Using string concatenation
        return "Successfully created dependency: " + from_phase_id + " → " + to_phase_id + " (" + dependency_type + ")"
    except Exception as e:
        return "Error creating dependency between phases: " + str(e)

@tool
def build_complete_plan() -> str:
    """
    Generates a complete implementation plan JSON object based on all the phases
    and dependencies created so far. Call this when you've finished creating all phases.
    """
    global _phases_store, _dependencies_store
    
    # Check if we have any phases
    if not _phases_store:
        return "Error: No phases have been created yet. Use create_development_phase to add phases first."
    
    # Create the complete plan structure
    complete_plan = {
        "implementation_plan": {
            "project_summary": {
                "title": "Implementation Plan",
                "description": "Generated implementation plan based on project analysis",
                "overall_complexity": "Medium",  # This could be dynamically set
                "estimated_duration": str(len(_phases_store) * 2) + " weeks"  # Simple estimation using string concat
            },
            "development_phases": _phases_store,
            "dependencies": _dependencies_store
        }
    }
    
    # Return the plan as a JSON string
    return json.dumps(complete_plan, indent=2)

@smart_react_tool("Analyze technology stack for development planning")
def analyze_tech_stack(tool_input):
    """
    Analyzes the technology stack to provide insights for implementation planning.
    Use this to understand the technical constraints and requirements.
    
    Args:
        tool_input: A TechStackAnalysisInput object containing tech_stack_json
    """
    logger = logging.getLogger(__name__)
    logger.info("Tool 'analyze_tech_stack' called")
    
    try:
        # Extract tech_stack_json from various input types
        tech_stack_json = ""
        
        if isinstance(tool_input, str):
            logger.info("Received string input - attempting to parse")
            try:
                # Try to parse as JSON with a tech_stack_json field
                parsed = json.loads(tool_input)
                if isinstance(parsed, dict) and "tech_stack_json" in parsed:
                    tech_stack_json = parsed["tech_stack_json"]
                else:
                    # Assume the string itself is the tech stack JSON
                    tech_stack_json = tool_input
            except json.JSONDecodeError:
                logger.warning("Input string is not valid JSON, using as-is")
                tech_stack_json = tool_input
        elif isinstance(tool_input, dict):
            logger.info("Received dict input - extracting tech_stack_json field")
            tech_stack_json = tool_input.get("tech_stack_json", "")
        elif isinstance(tool_input, TechStackAnalysisInput):
            logger.info("Received TechStackAnalysisInput - extracting tech_stack_json field")
            tech_stack_json = tool_input.tech_stack_json
        else:
            logger.warning(f"Received unexpected input type: {type(tool_input)}")
            tech_stack_json = str(tool_input)
        
        # Parse the tech stack JSON
        tech_stack = None
        if isinstance(tech_stack_json, dict):
            tech_stack = tech_stack_json
        else:
            try:
                tech_stack = json.loads(tech_stack_json)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse tech stack JSON: {str(e)}")
                return TechStackAnalysisOutput(
                    summary="Failed to parse tech stack JSON",
                    tech_stack_details="Invalid JSON",
                    implementation_considerations=["Fix the tech stack JSON formatting"]
                )
        
        # Extract key technologies
        backend = tech_stack.get("backend", {})
        frontend = tech_stack.get("frontend", {})
        database = tech_stack.get("database", {})
        
        # Using string concatenation for forming descriptions
        backend_tech = backend.get('language', 'Unknown') + " with " + backend.get('framework', 'Unknown')
        frontend_tech = frontend.get('language', 'Unknown') + " with " + frontend.get('framework', 'Unknown')
        database_tech = database.get("type", "Unknown database")
        
        # Create a summary using string concatenation
        tech_stack_details = f"Backend: {backend_tech}\nFrontend: {frontend_tech}\nDatabase: {database_tech}"
        
        # Add deployment/infrastructure details
        infrastructure_details = ""
        if "infrastructure" in tech_stack:
            infra = tech_stack.get("infrastructure", {})
            infrastructure_details = f"Hosting: {infra.get('hosting', 'Unknown')}\nCI/CD: {infra.get('ci_cd', 'Unknown')}"
            
        # Gather implementation considerations
        considerations = []
        
        # Backend considerations
        if "Node.js" in backend_tech or "Express" in backend_tech:
            considerations.append("Include setup time for Node.js environment and package management")
        elif "Python" in backend_tech:
            considerations.append("Include setup time for Python virtual environments")
            
        # Database considerations
        if "SQL" in database_tech or "Postgres" in database_tech or "MySQL" in database_tech:
            considerations.append("Plan for database schema design and migration scripts")
        elif "Mongo" in database_tech:
            considerations.append("Plan for document schema design and indexes")
            
        # Frontend considerations
        if "React" in frontend_tech:
            considerations.append("Include time for component design and state management")
        elif "Angular" in frontend_tech:
            considerations.append("Plan for module architecture and service design")
            
        # Create proper output model
        return TechStackAnalysisOutput(
            summary=f"{backend_tech} backend, {frontend_tech} frontend, {database_tech}",
            tech_stack_details=tech_stack_details,
            infrastructure_details=infrastructure_details,
            implementation_considerations=considerations
        )
    except Exception as e:
        logger.error(f"Error in analyze_tech_stack: {str(e)}", exc_info=True)
        return TechStackAnalysisOutput(
            summary="Error analyzing tech stack",
            tech_stack_details="",
            implementation_considerations=[f"Error: {str(e)}"]
        )

@tool(args_schema=ExampleNewToolInput)
def example_new_tool(requirement: str) -> str:
    """An example of how to properly implement a new tool with ChatPromptTemplate."""
    try:
        llm = get_tool_llm(temperature=0.2)
        
        # IMPROVED: Use template variables instead of string concatenation
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a planning expert. Analyze the provided requirement."),
            ("user", "Analyze this requirement: {requirement}")  # Template variable
        ])
        
        # CRITICAL FIX: Format the prompt with proper variables before invoking
        formatted_prompt = prompt.format_prompt(requirement=requirement)
        response = llm.invoke(formatted_prompt)
        return response.content
    except Exception as e:
        return f"Error in example_new_tool: {str(e)}"

@tool(args_schema=RiskAssessmentInput)
def get_risk_assessment(risk_assessment_json: str) -> RiskAssessmentOutput:
    """
    Analyzes the risk assessment document and extracts key risks and mitigation strategies.
    Use this to understand project risks that need to be addressed in the planning.
    
    Args:
        risk_assessment_json: JSON string containing the risk assessment document
    """
    logger = logging.getLogger(__name__)
    logger.info("Tool 'get_risk_assessment' called")
    
    try:
        # Parse the input JSON
        risk_data = None
        if isinstance(risk_assessment_json, dict):
            risk_data = risk_assessment_json
        else:
            try:
                risk_data = json.loads(risk_assessment_json)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse risk assessment JSON: {str(e)}")
                return RiskAssessmentOutput(
                    total_risks=0,
                    severity_breakdown=RiskSeveritySummary(high=0, medium=0, low=0),
                    top_risks=[{"description": f"Error: {str(e)}", "severity": "high", "mitigation": "Fix JSON format"}],
                    summary=f"Error: Could not parse risk assessment JSON: {str(e)}"
                )
            
        # Extract risks with multiple fallback paths
        risks = risk_data.get("risks", [])
        if not risks:
            risks = risk_data.get("project_risks", [])
        if not risks:
            risks = risk_data.get("risk_assessment", {}).get("risks", [])
              # Count risks by severity
        severity_count = {"high": 0, "medium": 0, "low": 0}
        for risk in risks:
            # Handle case where risk might be a string instead of dict
            if isinstance(risk, str):
                severity_count["medium"] += 1  # Default to medium for string risks
            else:
                severity = risk.get("severity", "").lower()
                if severity in severity_count:
                    severity_count[severity] += 1
                
        # Extract top risks (highest severity first)
        top_risks = []
        for severity in ["high", "medium"]:
            for risk in risks:
                if isinstance(risk, str):
                    # Handle string risks
                    if severity == "medium":  # Add string risks as medium severity
                        top_risks.append({
                            "description": risk,
                            "severity": "medium",
                            "mitigation": "No mitigation provided"
                        })
                        if len(top_risks) >= 3:
                            break
                else:
                    # Handle dict risks
                    if risk.get("severity", "").lower() == severity:
                        top_risks.append({
                            "description": risk.get("description", "Unnamed risk"),
                            "severity": risk.get("severity", "Unknown"),
                            "mitigation": risk.get("mitigation", "No mitigation provided")
                        })
                        if len(top_risks) >= 3:
                            break
            if len(top_risks) >= 3:
                break
                
        # Create summary
        summary = f"Risk Assessment: {len(risks)} total risks identified. "
        summary += f"Severity breakdown: {severity_count['high']} high, "
        summary += f"{severity_count['medium']} medium, {severity_count['low']} low."
            
        return RiskAssessmentOutput(
            total_risks=len(risks),
            severity_breakdown=RiskSeveritySummary(
                high=severity_count["high"],
                medium=severity_count["medium"],
                low=severity_count["low"]
            ),
            top_risks=top_risks,
            summary=summary
        )
        
    except Exception as e:
        logger.error(f"Error in get_risk_assessment: {str(e)}", exc_info=True)
        return RiskAssessmentOutput(
            total_risks=0,
            severity_breakdown=RiskSeveritySummary(high=0, medium=0, low=0),
            top_risks=[{"description": f"Error: {str(e)}", "severity": "Unknown", "mitigation": "Fix input data"}],
            summary=f"Error extracting risk assessment: {str(e)}"
        )

@smart_react_tool("Compile comprehensive development plan from all inputs")
def compile_comprehensive_plan(project_analysis=None, system_design=None, timeline_estimation=None, risk_assessment=None):
    """
    Compiles a comprehensive project implementation plan based on all analysis documents.
    Returns a complete implementation plan with phases, dependencies, and resource allocation.
    
    Args:
        project_analysis: Project analysis data (dict or JSON string)
        system_design: System design data (dict or JSON string)
        timeline_estimation: Timeline estimation data (dict or JSON string)
        risk_assessment: Risk assessment data (dict or JSON string)
    """
    logger = logging.getLogger(__name__)
    logger.info("Tool 'compile_comprehensive_plan' called")
    
    try:        # Parse string inputs to dictionaries if needed
        def parse_input(data: Union[Dict[str, Any], str, None]) -> Dict[str, Any]:
            if data is None:
                return {}
            elif isinstance(data, str):
                if data.strip() == "":
                    return {}
                try:
                    return json.loads(data)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse JSON string: {data[:100]}...")
                    return {}
            elif isinstance(data, dict):
                return data
            else:
                return {}
        
        # Parse all inputs
        project_analysis_dict = parse_input(project_analysis)
        system_design_dict = parse_input(system_design)
        timeline_estimation_dict = parse_input(timeline_estimation)
        risk_assessment_dict = parse_input(risk_assessment)
        
        # Use the parsed parameters
        project_analysis = project_analysis_dict
        system_design = system_design_dict
        timeline_estimation = timeline_estimation_dict
        risk_assessment = risk_assessment_dict
        
        # Extract project name
        project_name = project_analysis.get("project_name", "Unnamed Project")
        
        # Extract system components
        components = []
        if "architecture_overview" in system_design:
            arch_components = system_design.get("architecture_overview", {}).get("components", [])
            components = [comp.get("name") for comp in arch_components if "name" in comp]
        elif "modules" in system_design:
            components = system_design.get("modules", [])
            if isinstance(components, list) and components and isinstance(components[0], dict):
                components = [comp.get("name") for comp in components if "name" in comp]
                
        if not components:
            # Try development_phases as a source for components
            phases = system_design.get("development_phases", [])
            if phases:
                components = []
                for phase in phases:
                    components.extend(phase.get("tasks", []))        # Create domain-aware development phases
        domain = _detect_domain_from_components(components) if components else "generic"
        phases = _generate_domain_specific_phases(domain, components)
        
        # Extract risk mitigation tasks
        risk_tasks = []
        risks = risk_assessment.get("risks", [])
        if risks:
            for risk in risks:
                # Handle case where risk might be a string instead of dict
                if isinstance(risk, str):
                    # For string risks, add generic mitigation task
                    risk_tasks.append(f"Mitigate risk: {risk}")
                else:
                    # For dict risks, check severity and extract mitigation
                    if risk.get("severity", "").lower() == "high":
                        mitigation = risk.get("mitigation", "")
                        if mitigation:
                            risk_tasks.append(mitigation)
        
        # Add risk mitigation phase if needed
        if risk_tasks:
            next_phase_id = f"P{len(phases) + 1}"
            phases.append(DevelopmentPhaseOutput(
                phase_id=next_phase_id,
                name="Risk Mitigation",
                type="risk_mitigation",
                duration=_get_domain_duration(domain, "risk_mitigation"),
                tasks=risk_tasks[:5],  # Limit to 5 tasks
                dependencies=[phases[-1].phase_id] if phases else []
            ))
        
        # Create dependencies between phases
        dependencies = []
        for i in range(1, len(phases)):
            dependencies.append({
                "from": phases[i-1].phase_id,
                "to": phases[i].phase_id,
                "type": "finish-to-start"
            })
        
        # Calculate total duration (simple sum of phase durations)
        total_duration_weeks = 0
        for phase in phases:
            duration = phase.duration
            if "week" in duration:
                try:
                    weeks = int(duration.split()[0])
                    total_duration_weeks += weeks
                except ValueError:
                    pass        
        # Create overall plan as a dictionary to avoid complex Pydantic model issues
        implementation_plan_dict = {
            "project_summary": {
                "title": project_name + " Implementation Plan",
                "description": "Comprehensive implementation plan based on project analysis and design",
                "overall_complexity": project_analysis.get("project_complexity", {}).get("complexity_level", "Medium"),
                "estimated_duration": str(total_duration_weeks) + " weeks"
            },
            "development_phases": [phase.dict() if hasattr(phase, 'dict') else phase for phase in phases],
            "dependencies": dependencies,
            "resource_allocation": {
                "recommended_team_size": project_analysis.get("resource_requirements", {}).get("recommended_team_size", 5),
                "key_roles": [
                    "Project Manager", 
                    "Tech Lead",
                    "Backend Developer",
                    "Frontend Developer", 
                    "QA Engineer"
                ]
            },
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "generation_method": "comprehensive_synthesis"
            }
        }
        
        return ComprehensivePlanOutput(implementation_plan=implementation_plan_dict)
        
    except Exception as e:
        logger.error(f"Error in compile_comprehensive_plan: {str(e)}", exc_info=True)        
        # Create a minimal fallback plan as a dictionary
        fallback_plan_dict = {
            "project_summary": {
                "title": "Fallback Implementation Plan",
                "description": "Generated due to error in plan compilation",
                "overall_complexity": "Medium",
                "estimated_duration": "12 weeks"
            },
            "development_phases": [
                {
                    "phase_id": "P1",
                    "name": "Project Setup",
                    "type": "setup",
                    "duration": "1 week",
                    "tasks": ["Repository initialization"],
                    "dependencies": []
                },
                {
                    "phase_id": "P2",
                    "name": "Development",
                    "type": "development",
                    "duration": "10 weeks",
                    "tasks": ["Full development cycle"],
                    "dependencies": ["P1"]
                },
                {
                    "phase_id": "P3",
                    "name": "Testing",
                    "type": "testing",
                    "duration": "1 week",
                    "tasks": ["Testing and QA"],
                    "dependencies": ["P2"]
                }
            ],
            "dependencies": [
                {"from": "P1", "to": "P2", "type": "finish-to-start"},
                {"from": "P2", "to": "P3", "type": "finish-to-start"}
            ],
            "resource_allocation": {
                "recommended_team_size": 5,
                "key_roles": ["Project Manager", "Developers", "QA Engineer"]
            },
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "generation_method": "fallback_due_to_error"
            }
        }
        
        return ComprehensivePlanOutput(implementation_plan=fallback_plan_dict)



@tool
def batch_analyze_planning_inputs(
    project_analysis_json: Optional[str] = "",
    system_design_json: Optional[str] = "",
    timeline_estimation_json: Optional[str] = "",
    risk_assessment_json: Optional[str] = ""
) -> Dict[str, Any]:
    """
    Performs a batch analysis of project analysis, system components, timeline, and risks in a single call.
    This is more efficient than calling each analysis tool separately.
    
    Args:
        project_analysis_json: JSON string containing project analysis data        system_design_json: JSON string containing system design data
        timeline_estimation_json: JSON string containing timeline estimation data
        risk_assessment_json: JSON string containing risk assessment data
    """
    logger = logging.getLogger(__name__)
    logger.info("Tool 'batch_analyze_planning_inputs' called for efficient planning analysis")
    
    try:
        # If no inputs provided, try to get data from enhanced memory
        if not any([project_analysis_json, system_design_json, timeline_estimation_json, risk_assessment_json]):
            logger.info("No inputs provided to batch tool, attempting enhanced memory retrieval")
            project_context = get_project_context_from_memory()
            
            if project_context:
                project_analysis_json = json.dumps(project_context.get("brd_analysis", {})) if project_context.get("brd_analysis") else ""
                system_design_json = json.dumps(project_context.get("system_design", {})) if project_context.get("system_design") else ""
                timeline_estimation_json = json.dumps(project_context.get("timeline_estimation", {})) if project_context.get("timeline_estimation") else ""
                risk_assessment_json = json.dumps(project_context.get("risk_assessment", {})) if project_context.get("risk_assessment") else ""
                logger.info("Retrieved project data from enhanced memory for batch analysis")
        
        # Proceed with batch analysis using the extracted fields
        results = {}
        
        # Call each analysis tool with the provided JSON and gather results
        if project_analysis_json and project_analysis_json.strip():
            project_analysis = get_project_analysis_summary.invoke({"project_analysis_json": project_analysis_json})
            results["project_analysis_summary"] = project_analysis.dict() if hasattr(project_analysis, "dict") else project_analysis
            
        if system_design_json and system_design_json.strip():
            components = get_major_system_components.invoke({"system_design_json": system_design_json})
            results["major_system_components"] = components.dict() if hasattr(components, "dict") else components
            
        if timeline_estimation_json and timeline_estimation_json.strip():
            timeline = get_timeline_estimation.invoke({"timeline_estimation_json": timeline_estimation_json})
            results["timeline_estimation"] = timeline
            
        if risk_assessment_json and risk_assessment_json.strip():
            risks = get_risk_assessment.invoke({"risk_assessment_json": risk_assessment_json})
            results["risk_assessment"] = risks.dict() if hasattr(risks, "dict") else risks
        
        logger.info(f"Successfully analyzed {len(results)} planning components in batch mode")
        return results
        
    except Exception as e:
        logger.error(f"Error in batch_analyze_planning_inputs: {str(e)}", exc_info=True)
        return {
            "error": str(e),
            "project_analysis_summary": {},
            "major_system_components": {},
            "timeline_estimation": {},
            "risk_assessment": {}
        }

def _get_domain_specific_components(domain: str) -> List[MajorSystemComponentOutput]:
    """
    Returns domain-specific default components instead of generic Frontend/Backend/Database.
    
    Args:
        domain: The detected project domain
        
    Returns:
        List of domain-appropriate system components
    """
    if domain == "healthcare":
        return [
            MajorSystemComponentOutput(name="Patient Management Service", category="core"),
            MajorSystemComponentOutput(name="Medical Records System", category="data"),
            MajorSystemComponentOutput(name="Compliance & Audit Module", category="security"),
            MajorSystemComponentOutput(name="Healthcare Provider Interface", category="frontend")
        ]
    elif domain == "financial":
        return [
            MajorSystemComponentOutput(name="Account Management Service", category="core"),
            MajorSystemComponentOutput(name="Transaction Processing Engine", category="core"),
            MajorSystemComponentOutput(name="Fraud Detection System", category="security"),
            MajorSystemComponentOutput(name="Financial Dashboard", category="frontend"),
            MajorSystemComponentOutput(name="Compliance Reporting Module", category="reporting")
        ]
    elif domain == "iot":
        return [
            MajorSystemComponentOutput(name="Device Management Gateway", category="gateway"),
            MajorSystemComponentOutput(name="Data Collection Service", category="data"),
            MajorSystemComponentOutput(name="Real-time Analytics Engine", category="analytics"),
            MajorSystemComponentOutput(name="Device Monitoring Dashboard", category="frontend"),
            MajorSystemComponentOutput(name="Event Processing System", category="processing")
        ]
    elif domain == "ecommerce":
        return [
            MajorSystemComponentOutput(name="Product Catalog Service", category="core"),
            MajorSystemComponentOutput(name="Shopping Cart Manager", category="core"),
            MajorSystemComponentOutput(name="Order Processing System", category="processing"),
            MajorSystemComponentOutput(name="Payment Gateway Integration", category="payment"),
            MajorSystemComponentOutput(name="Customer Portal", category="frontend")
        ]
    else:
        # Generic fallback - still better than Frontend/Backend/Database
        return [
            MajorSystemComponentOutput(name="User Management Service", category="core"),
            MajorSystemComponentOutput(name="Business Logic Engine", category="core"),
            MajorSystemComponentOutput(name="Data Access Layer", category="data"),
            MajorSystemComponentOutput(name="User Interface", category="frontend")
        ]

def _detect_domain_from_components(components: List) -> str:
    """
    Detects the project domain based on component names.
    
    Args:
        components: List of system components
        
    Returns:
        Detected domain (healthcare, financial, iot, ecommerce, or generic)
    """
    try:
        # Convert components to a single string for analysis
        component_text = ""
        for component in components:
            if isinstance(component, str):
                component_text += component.lower() + " "
            elif isinstance(component, dict):
                component_text += component.get("name", "").lower() + " "
                
        # Domain detection based on keywords
        if any(keyword in component_text for keyword in ['patient', 'medical', 'health', 'compliance', 'hipaa']):
            return "healthcare"
        elif any(keyword in component_text for keyword in ['account', 'transaction', 'payment', 'fraud', 'financial']):
            return "financial"
        elif any(keyword in component_text for keyword in ['device', 'sensor', 'gateway', 'iot', 'real-time', 'analytics']):
            return "iot"
        elif any(keyword in component_text for keyword in ['product', 'catalog', 'cart', 'order', 'ecommerce', 'shopping']):
            return "ecommerce"
        else:
            return "generic"
    except Exception:
        return "generic"

def _generate_domain_specific_phases(domain: str, components: List) -> List[DevelopmentPhaseOutput]:
    """
    Generates domain-specific development phases with appropriate durations.
    
    Args:
        domain: The detected project domain
        components: List of system components
        
    Returns:
        List of domain-appropriate development phases
    """
    phases = []
    
    # Phase 1: Project Setup (universal)
    phases.append(DevelopmentPhaseOutput(
        phase_id="P1",
        name="Project Setup",
        type="setup",
        duration=_get_domain_duration(domain, "setup"),
        tasks=[
            "Repository initialization",
            "Environment setup",
            "Project structure configuration",
            "CI/CD pipeline configuration"
        ] + _get_domain_setup_tasks(domain),
        dependencies=[]
    ))
    
    # Phase 2: Architecture Implementation
    phases.append(DevelopmentPhaseOutput(
        phase_id="P2",
        name="Architecture Implementation",
        type="architecture",
        duration=_get_domain_duration(domain, "architecture"),
        tasks=[
            "Core architectural patterns implementation",
            "System infrastructure configuration"
        ] + _get_domain_architecture_tasks(domain),
        dependencies=["P1"]
    ))
    
    # Phase 3: Domain-specific Core Development
    core_phase_name = _get_domain_core_phase_name(domain)
    phases.append(DevelopmentPhaseOutput(
        phase_id="P3",
        name=core_phase_name,
        type="core_development",
        duration=_get_domain_duration(domain, "core"),
        tasks=_get_domain_core_tasks(domain, components),
        dependencies=["P2"]
    ))
    
    # Phase 4: Integration & Testing
    phases.append(DevelopmentPhaseOutput(
        phase_id="P4",
        name="Integration and Testing",
        type="integration",
        duration=_get_domain_duration(domain, "integration"),
        tasks=[
            "System integration",
            "End-to-end testing",
            "Performance optimization"
        ] + _get_domain_testing_tasks(domain),
        dependencies=["P3"]
    ))
    
    # Phase 5: Domain-specific Compliance/Security (if needed)
    if domain in ["healthcare", "financial"]:
        phases.append(DevelopmentPhaseOutput(
            phase_id="P5",
            name=_get_compliance_phase_name(domain),
            type="compliance",
            duration=_get_domain_duration(domain, "compliance"),
            tasks=_get_compliance_tasks(domain),
            dependencies=["P4"]
        ))
    
    return phases

def _get_domain_duration(domain: str, phase_type: str) -> str:
    """
    Returns domain-appropriate durations for different phases.
    
    Args:
        domain: Project domain
        phase_type: Type of development phase
        
    Returns:
        Duration string (e.g., "2 weeks")
    """
    duration_matrix = {
        "healthcare": {
            "setup": "2 weeks",  # Extra time for compliance setup
            "architecture": "3 weeks",  # Complex security architecture
            "core": "5 weeks",  # Complex medical workflows
            "integration": "3 weeks",  # Extensive testing
            "compliance": "3 weeks",  # HIPAA compliance
            "risk_mitigation": "2 weeks"
        },
        "financial": {
            "setup": "2 weeks",  # Security-focused setup
            "architecture": "4 weeks",  # High-security architecture
            "core": "6 weeks",  # Complex financial logic
            "integration": "4 weeks",  # Rigorous testing
            "compliance": "4 weeks",  # PCI-DSS compliance
            "risk_mitigation": "3 weeks"
        },
        "iot": {
            "setup": "1 week",  # Simple setup
            "architecture": "2 weeks",  # Event-driven architecture
            "core": "4 weeks",  # Device management complexity
            "integration": "3 weeks",  # Hardware-software integration
            "risk_mitigation": "2 weeks"
        },
        "ecommerce": {
            "setup": "1 week",  # Standard setup
            "architecture": "2 weeks",  # Scalable architecture
            "core": "4 weeks",  # Product and order management
            "integration": "2 weeks",  # Payment integration
            "risk_mitigation": "1 week"
        },
        "generic": {
            "setup": "1 week",
            "architecture": "2 weeks",
            "core": "3 weeks",
            "integration": "2 weeks",
            "risk_mitigation": "1 week"
        }
    }
    
    return duration_matrix.get(domain, duration_matrix["generic"]).get(phase_type, "2 weeks")

def _get_domain_setup_tasks(domain: str) -> List[str]:
    """Returns domain-specific setup tasks."""
    if domain == "healthcare":
        return ["HIPAA compliance setup", "Security audit framework", "Medical data encryption setup"]
    elif domain == "financial":
        return ["PCI-DSS compliance setup", "Financial security framework", "Fraud detection infrastructure"]
    elif domain == "iot":
        return ["Device connectivity framework", "Edge computing setup", "IoT security protocols"]
    elif domain == "ecommerce":
        return ["Payment gateway setup", "Inventory management framework", "E-commerce platform configuration"]
    else:
        return ["Basic security setup", "Standard authentication framework"]

def _get_domain_architecture_tasks(domain: str) -> List[str]:
    """Returns domain-specific architecture tasks."""
    if domain == "healthcare":
        return ["Patient data security architecture", "Medical workflow design", "Audit trail implementation"]
    elif domain == "financial":
        return ["Transaction security architecture", "Financial data protection", "Regulatory compliance design"]
    elif domain == "iot":
        return ["Device management architecture", "Real-time data processing design", "Edge computing implementation"]
    elif domain == "ecommerce":
        return ["Scalable product catalog design", "Payment processing architecture", "Order management system"]
    else:
        return ["Standard business logic architecture", "User management design"]

def _get_domain_core_phase_name(domain: str) -> str:
    """Returns domain-specific core phase name."""
    if domain == "healthcare":
        return "Medical System Development"
    elif domain == "financial":
        return "Financial Services Development"
    elif domain == "iot":
        return "IoT Platform Development"
    elif domain == "ecommerce":
        return "E-commerce Platform Development"
    else:
        return "Core System Development"

def _get_domain_core_tasks(domain: str, components: List) -> List[str]:
    """Returns domain-specific core development tasks."""
    base_tasks = []
    
    if domain == "healthcare":
        base_tasks = [
            "Patient management system implementation",
            "Medical records database development",
            "Healthcare provider interface creation",
            "Medical data validation and processing"
        ]
    elif domain == "financial":
        base_tasks = [
            "Account management system development",
            "Transaction processing engine implementation",
            "Financial dashboard creation",
            "Payment integration and validation"
        ]
    elif domain == "iot":
        base_tasks = [
            "Device gateway implementation",
            "Real-time data processing development",
            "Analytics engine creation",
            "Device monitoring interface"
        ]
    elif domain == "ecommerce":
        base_tasks = [
            "Product catalog system development",
            "Shopping cart implementation",
            "Order processing system creation",
            "Customer portal development"
        ]
    else:
        base_tasks = [
            "Core business logic implementation",
            "User interface development",
            "Database operations implementation",
            "API endpoints creation"
        ]
    
    # Add component-specific tasks
    if components:
        for component in components[:3]:  # Limit to first 3 components
            comp_name = component if isinstance(component, str) else component.get("name", "Unknown")
            base_tasks.append(f"{comp_name} implementation")
    
    return base_tasks

def _get_domain_testing_tasks(domain: str) -> List[str]:
    """Returns domain-specific testing tasks."""
    if domain == "healthcare":
        return ["HIPAA compliance testing", "Medical data integrity testing", "Patient safety validation"]
    elif domain == "financial":
        return ["PCI-DSS compliance testing", "Transaction integrity testing", "Financial fraud detection testing"]
    elif domain == "iot":
        return ["Device connectivity testing", "Real-time performance testing", "IoT security validation"]
    elif domain == "ecommerce":
        return ["Payment processing testing", "Load testing for peak traffic", "E-commerce workflow validation"]
    else:
        return ["User acceptance testing", "Security testing", "Performance validation"]

def _get_compliance_phase_name(domain: str) -> str:
    """Returns domain-specific compliance phase name."""
    if domain == "healthcare":
        return "HIPAA Compliance & Security Audit"
    elif domain == "financial":
        return "PCI-DSS Compliance & Financial Audit"
    else:
        return "Compliance & Security Audit"

def _get_compliance_tasks(domain: str) -> List[str]:
    """Returns domain-specific compliance tasks."""
    if domain == "healthcare":
        return [
            "HIPAA compliance audit",
            "Patient data encryption verification",
            "Medical audit trail validation",
            "Healthcare security penetration testing",
            "Regulatory compliance documentation"
        ]
    elif domain == "financial":
        return [
            "PCI-DSS compliance assessment",
            "Financial data security audit",
            "Transaction integrity validation",
            "Financial regulatory compliance review",
            "Security controls documentation"
        ]
    else:
        return [
            "General security audit",
            "Data protection compliance",
            "Security documentation review"
        ]