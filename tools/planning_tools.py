"""
Planning tools for the ReAct-based PlanCompilerAgent.
Each tool is focused on a specific planning task to help build the implementation plan.
"""

import json
from typing import Dict, Any, List, Optional, Union
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from datetime import datetime
import logging
from langchain_core.output_parsers import PydanticOutputParser

# Import Pydantic models
from tools.models import (
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
    
    # Output models (new)
    ProjectAnalysisSummaryOutput,
    MajorSystemComponentsOutput,
    ComponentRisksOutput,
    DevelopmentPhaseOutput,
    CurrentPhasesOutput,
    TimelineDetailsOutput,
    PhaseDependencyOutput,
    TechStackAnalysisOutput,
    RiskAssessmentOutput,
    ComprehensivePlanOutput
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
    from multi_ai_dev_system.tools.json_handler import JsonHandler
    
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

@tool(args_schema=ProjectAnalysisSummaryInput)
def get_project_analysis_summary(project_analysis_json: str) -> ProjectAnalysisSummaryOutput:
    """
    Returns a summary of the project analysis, including overall complexity,
    resource needs, and key challenges. Use this to understand the project's constraints.
    """
    logger = logging.getLogger(__name__)
    logger.info("Tool 'get_project_analysis_summary' called")
    
    try:
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
            
        # Return the structured output
        return ProjectAnalysisSummaryOutput(
            complexity_score=complexity,
            recommended_team_size=team_size,
            key_challenges=challenges,
            summary=summary
        )
        
    except Exception as e:
        logger.error(f"Error in get_project_analysis_summary: {str(e)}", exc_info=True)
        return ProjectAnalysisSummaryOutput(
            complexity_score=5,
            recommended_team_size=3,
            key_challenges=["Error processing project analysis"],
            summary=f"Error summarizing project analysis: {str(e)}"
        )

@tool(args_schema=MajorSystemComponentsInput)
def get_major_system_components(system_design_json: str) -> MajorSystemComponentsOutput:
    """
    Extracts the names of the major system modules or components from the system design document.
    Use this to know which components need to be included in the development phases.
    """
    logger = logging.getLogger(__name__)
    logger.info("Tool 'get_major_system_components' called")
    
    try:
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

@tool(args_schema=ComponentRisksInput)
def get_risks_for_component(component_name: str, risk_assessment_json: str) -> Union[List[str], str]:
    """
    Finds and lists specific risks associated with a given system component.
    Returns a list of risks, or an error message string if extraction fails.
    """
    try:
        # Parse the risk assessment JSON
        risks_data = json.loads(risk_assessment_json)
        
        # Try different possible structures for risks
        all_risks = risks_data.get("risks", [])
        if not all_risks:
            all_risks = risks_data.get("project_risks", [])
            
        # Search for risks related to the component
        component_risks = []
        for risk in all_risks:
            # Check if risk area/category/description contains the component name
            risk_area = risk.get("area", "").lower()
            risk_category = risk.get("category", "").lower()
            risk_desc = risk.get("description", "").lower()
            
            component_lower = component_name.lower()
            
            if (component_lower in risk_area or 
                component_lower in risk_category or 
                component_lower in risk_desc):
                component_risks.append(risk.get("description", "Unnamed risk"))
                
        return component_risks if component_risks else ["No specific risks identified for this component"]
    except json.JSONDecodeError:
        return ["Error: Invalid JSON input. Please provide a valid JSON with component_name and risk_assessment_json fields."]
    except Exception as e:
        # Return error using list
        return ["Error: Could not extract risks for component. Error details: " + str(e)]

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

@tool(args_schema=TechStackAnalysisInput)
def analyze_tech_stack(tech_stack_json: str) -> str:
    """
    Analyzes the technology stack to provide insights for implementation planning.
    Use this to understand the technical constraints and requirements.
    """
    try:
        tech_stack = json.loads(tech_stack_json)
        
        # Extract key technologies
        backend = tech_stack.get("backend", {})
        frontend = tech_stack.get("frontend", {})
        database = tech_stack.get("database", {})
        
        # Using string concatenation for forming descriptions
        backend_tech = backend.get('language', 'Unknown') + " with " + backend.get('framework', 'Unknown')
        frontend_tech = frontend.get('language', 'Unknown') + " with " + frontend.get('framework', 'Unknown')
        database_tech = database.get("type", "Unknown database")
        
        # Create a summary using string concatenation
        result = "Tech Stack Summary:\n"
        result += "- Backend: " + backend_tech + "\n"
        result += "- Frontend: " + frontend_tech + "\n"
        result += "- Database: " + database_tech + "\n"
        
        # Add deployment/infrastructure if available
        if "infrastructure" in tech_stack:
            infra = tech_stack.get("infrastructure", {})
            result += "- Hosting: " + infra.get('hosting', 'Unknown') + "\n"
            result += "- CI/CD: " + infra.get('ci_cd', 'Unknown') + "\n"
            
        # Add implementation considerations
        result += "\nImplementation considerations:\n"
        
        # Backend considerations
        if "Node.js" in backend_tech or "Express" in backend_tech:
            result += "- Include setup time for Node.js environment and package management\n"
        elif "Python" in backend_tech:
            result += "- Include setup time for Python virtual environments\n"
            
        # Database considerations
        if "SQL" in database_tech or "Postgres" in database_tech or "MySQL" in database_tech:
            result += "- Plan for database schema design and migration scripts\n"
        elif "Mongo" in database_tech:
            result += "- Plan for document schema design and indexes\n"
            
        # Frontend considerations
        if "React" in frontend_tech:
            result += "- Include time for component design and state management\n"
        elif "Angular" in frontend_tech:
            result += "- Plan for module architecture and service design\n"
            
        return result
    except Exception as e:
        return "Error analyzing tech stack: " + str(e)

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
    """
    logger = logging.getLogger(__name__)
    logger.info("Tool 'get_risk_assessment' called")
    
    try:
        # Parse the input JSON
        if isinstance(risk_assessment_json, str):
            risk_data = json.loads(risk_assessment_json)
        else:
            risk_data = risk_assessment_json  # Already parsed JSON
            
        # Extract risks with multiple fallback paths
        risks = risk_data.get("risks", [])
        if not risks:
            risks = risk_data.get("project_risks", [])
        if not risks:
            risks = risk_data.get("risk_assessment", {}).get("risks", [])
            
        # Count risks by severity
        severity_count = {"high": 0, "medium": 0, "low": 0}
        for risk in risks:
            severity = risk.get("severity", "").lower()
            if severity in severity_count:
                severity_count[severity] += 1
                
        # Extract top risks (highest severity first)
        top_risks = []
        for severity in ["high", "medium"]:
            for risk in risks:
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

@tool(args_schema=ComprehensivePlanInput)
def compile_comprehensive_plan(project_analysis: Dict[str, Any], system_design: Dict[str, Any], 
                             timeline_estimation: Dict[str, Any], risk_assessment: Dict[str, Any]) -> ComprehensivePlanOutput:
    """
    Compiles a comprehensive project implementation plan based on all analysis documents.
    Returns a complete implementation plan with phases, dependencies, and resource allocation.
    """
    logger = logging.getLogger(__name__)
    logger.info("Tool 'compile_comprehensive_plan' called")
    
    try:
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
                    components.extend(phase.get("tasks", []))
        
        # Create standard development phases
        phases = []
        
        # Setup Phase
        phases.append(DevelopmentPhaseOutput(
            phase_id="P1",
            name="Project Setup",
            type="setup",
            duration="1 week",
            tasks=[
                "Repository initialization",
                "Environment setup",
                "Project structure configuration",
                "CI/CD pipeline configuration"
            ],
            dependencies=[]
        ))
        
        # Architecture Phase
        phases.append(DevelopmentPhaseOutput(
            phase_id="P2",
            name="Architecture Implementation",
            type="architecture",
            duration="2 weeks",
            tasks=[
                "Project architecture setup",
                "Core architectural patterns implementation",
                "System infrastructure configuration"
            ],
            dependencies=["P1"]
        ))
        
        # Database Phase
        phases.append(DevelopmentPhaseOutput(
            phase_id="P3",
            name="Database Implementation",
            type="database",
            duration="2 weeks",
            tasks=[
                "Database schema design",
                "Data models implementation",
                "Migration scripts creation",
                "Database access layer development"
            ],
            dependencies=["P2"]
        ))
        
        # Backend Phase
        backend_tasks = ["API endpoints development", "Business logic implementation", "Authentication setup"]
        if components:
            # Add component-specific backend tasks
            for component in components[:3]:  # Limit to first 3 components
                backend_tasks.append(component + " backend implementation")
                
        phases.append(DevelopmentPhaseOutput(
            phase_id="P4",
            name="Backend Development",
            type="backend",
            duration="3 weeks",
            tasks=backend_tasks,
            dependencies=["P3"]
        ))
        
        # Frontend Phase
        frontend_tasks = ["UI component development", "State management implementation", "API integration"]
        if components:
            # Add component-specific frontend tasks
            for component in components[:3]:  # Limit to first 3 components
                frontend_tasks.append(component + " frontend implementation")
                
        phases.append(DevelopmentPhaseOutput(
            phase_id="P5",
            name="Frontend Development",
            type="frontend",
            duration="3 weeks",
            tasks=frontend_tasks,
            dependencies=["P4"]
        ))
        
        # Integration Phase
        phases.append(DevelopmentPhaseOutput(
            phase_id="P6",
            name="Integration and Testing",
            type="integration",
            duration="2 weeks",
            tasks=[
                "Backend-Frontend integration",
                "End-to-end testing",
                "Performance optimization",
                "Bug fixes"
            ],
            dependencies=["P4", "P5"]
        ))
        
        # Extract risk mitigation tasks
        risk_tasks = []
        risks = risk_assessment.get("risks", [])
        if risks:
            for risk in risks:
                if risk.get("severity", "").lower() == "high":
                    mitigation = risk.get("mitigation", "")
                    if mitigation:
                        risk_tasks.append(mitigation)
        
        # Add risk mitigation phase if needed
        if risk_tasks:
            phases.append(DevelopmentPhaseOutput(
                phase_id="P7",
                name="Risk Mitigation",
                type="risk_mitigation",
                duration="2 weeks",
                tasks=risk_tasks[:5],  # Limit to 5 tasks
                dependencies=["P6"]
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
        
        # Create overall plan
        implementation_plan = ImplementationPlan(
            project_summary=ProjectSummary(
                title=project_name + " Implementation Plan",
                description="Comprehensive implementation plan based on project analysis and design",
                overall_complexity=project_analysis.get("project_complexity", {}).get("complexity_level", "Medium"),
                estimated_duration=str(total_duration_weeks) + " weeks"
            ),
            development_phases=phases,
            dependencies=dependencies,
            resource_allocation=ResourceAllocation(
                recommended_team_size=project_analysis.get("resource_requirements", {}).get("recommended_team_size", 5),
                key_roles=[
                    "Project Manager", 
                    "Tech Lead",
                    "Backend Developer",
                    "Frontend Developer", 
                    "QA Engineer"
                ]
            ),
            metadata=PlanMetadata(
                generated_at=datetime.now().isoformat(),
                generation_method="comprehensive_synthesis"
            )
        )
        
        return ComprehensivePlanOutput(implementation_plan=implementation_plan)
        
    except Exception as e:
        logger.error(f"Error in compile_comprehensive_plan: {str(e)}", exc_info=True)
        
        # Create a minimal fallback plan
        fallback_plan = ImplementationPlan(
            project_summary=ProjectSummary(
                title="Fallback Implementation Plan",
                description="Generated due to error in plan compilation",
                overall_complexity="Medium",
                estimated_duration="12 weeks"
            ),
            development_phases=[
                DevelopmentPhaseOutput(
                    phase_id="P1",
                    name="Project Setup",
                    type="setup",
                    duration="1 week",
                    tasks=["Repository initialization"],
                    dependencies=[]
                ),
                DevelopmentPhaseOutput(
                    phase_id="P2",
                    name="Development",
                    type="development",
                    duration="10 weeks",
                    tasks=["Full development cycle"],
                    dependencies=["P1"]
                ),
                DevelopmentPhaseOutput(
                    phase_id="P3",
                    name="Testing",
                    type="testing",
                    duration="1 week",
                    tasks=["Testing and QA"],
                    dependencies=["P2"]
                )
            ],
            dependencies=[
                {"from": "P1", "to": "P2", "type": "finish-to-start"},
                {"from": "P2", "to": "P3", "type": "finish-to-start"}
            ],
            resource_allocation=ResourceAllocation(
                recommended_team_size=5,
                key_roles=["Project Manager", "Developers", "QA Engineer"]
            ),
            metadata=PlanMetadata(
                generated_at=datetime.now().isoformat(),
                generation_method="fallback_due_to_error"
            )
        )
        
        return ComprehensivePlanOutput(implementation_plan=fallback_plan)