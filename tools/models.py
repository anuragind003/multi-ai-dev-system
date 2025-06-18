"""
Pydantic models for structured tool inputs across the multi-AI development system.
These models serve as the single source of truth for data contracts between agents and tools.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


# Tech Stack Tool Models
class TechnicalRequirementsSummaryInput(BaseModel):
    """Input schema for getting a summary of technical requirements from BRD analysis."""
    brd_analysis_json: str = Field(
        description="JSON string containing the BRD analysis with project requirements"
    )


class BackendEvaluationInput(BaseModel):
    """Input schema for evaluating backend technology options."""
    requirements_summary: str = Field(
        description="A concise summary of the project's technical requirements"
    )


class FrontendFrameworkRecommendationInput(BaseModel):
    """Input schema for recommending frontend frameworks."""
    requirements: str = Field(
        description="The requirements relevant to frontend development"
    )
    user_experience_focus: Optional[str] = Field(
        default="Standard user experience with focus on usability and performance",
        description="The UX priorities and focus areas for the project"
    )


class DatabaseEvaluationInput(BaseModel):
    """Input schema for evaluating database options."""
    technical_requirements: str = Field(
        description="Technical requirements relevant to data storage and management"
    )


class ArchitecturePatternEvaluationInput(BaseModel):
    """Input schema for evaluating architecture patterns."""
    requirements_summary: str = Field(
        description="A summary of the project's technical requirements"
    )
    backend: Optional[str] = Field(
        default="", 
        description="Selected backend technology (if already chosen)"
    )
    database: Optional[str] = Field(
        default="", 
        description="Selected database technology (if already chosen)"
    )
    frontend: Optional[str] = Field(
        default="", 
        description="Selected frontend technology (if already chosen)"
    )


class TechStackSynthesisInput(BaseModel):
    """Input schema for synthesizing a complete technology stack."""
    backend_recommendation: str = Field(
        description="The recommended backend technology with justification"
    )
    frontend_recommendation: str = Field(
        description="The recommended frontend technology with justification"
    )
    database_recommendation: str = Field(
        description="The recommended database technology with justification"
    )
    architecture_recommendation: Optional[str] = Field(
        default="",
        description="The recommended architecture pattern (if available)"
    )


class TechStackRiskAnalysisInput(BaseModel):
    """Input schema for analyzing risks in a technology stack."""
    tech_stack_json: str = Field(
        description="JSON representation of the complete technology stack"
    )
    requirements_summary: str = Field(
        description="Summary of the project's requirements for context"
    )


class FrontendEvaluationInput(BaseModel):
    """Input schema for evaluating frontend technology options."""
    requirements: str = Field(
        description="The requirements relevant to frontend development"
    )
    user_experience: Optional[str] = Field(
        default="Standard user experience with focus on usability and performance",
        description="The UX priorities and focus areas for the project"
    )


# System Design Tool Models
class ProjectRequirementsSummaryInput(BaseModel):
    """Input schema for summarizing project requirements."""
    brd_analysis_json: Optional[str] = Field(
        default=None,  # Make it optional
        description="JSON string containing the BRD analysis with project requirements. This is optional and will be injected by the system if not provided."
    )


class ArchitecturePatternSelectionInput(BaseModel):
    """Input schema for selecting an architecture pattern."""
    requirements_summary: str = Field(
        description="A summary of the project's technical requirements"
    )
    tech_stack_json: Optional[str] = Field(
        default="{}",
        description="JSON string containing the recommended technology stack (optional, defaults to empty)"
    )


class SystemComponentsIdentificationInput(BaseModel):
    """Input schema for identifying system components."""
    requirements_summary: str = Field(
        description="A summary of the project's technical requirements"
    )
    architecture_pattern: str = Field(
        description="The chosen architecture pattern, e.g., 'Microservices' or 'Layered Architecture'"
    )


class ComponentStructureDesignInput(BaseModel):
    """Input schema for designing a component structure."""
    component_name: str = Field(
        description="Name of the component to design"
    )
    requirements_summary: str = Field(
        description="A summary of the project's technical requirements"
    )


class DataModelDesignInput(BaseModel):
    """Input schema for designing a data model."""
    requirements_summary: str = Field(
        description="A summary of the project's technical requirements"
    )
    components: str = Field(
        description="JSON string containing system components"
    )
    database_technology: str = Field(
        description="The selected database technology (e.g., 'PostgreSQL', 'MongoDB')"
    )


class ApiEndpointsDesignInput(BaseModel):
    """Input schema for designing API endpoints."""
    requirements_summary: str = Field(
        description="A summary of the project's technical requirements"
    )
    components: str = Field(
        description="JSON string containing system components"
    )


class SecurityArchitectureDesignInput(BaseModel):
    """Input schema for designing security architecture."""
    requirements_summary: str = Field(
        description="A summary of the project's technical requirements"
    )
    architecture_pattern: str = Field(
        description="The chosen architecture pattern"
    )


class SystemDesignSynthesisInput(BaseModel):
    """Input schema for synthesizing a comprehensive system design."""
    architecture_pattern: str = Field(
        description="The selected architecture pattern for the system"
    )
    components: str = Field(
        description="JSON string or list containing the system components"
    )
    data_model: str = Field(
        description="JSON string or dict containing the data model design"
    )
    api_design: Optional[str] = Field(
        default="",
        description="JSON string or dict containing the API endpoints design"
    )
    security_architecture: Optional[str] = Field(
        default="",
        description="JSON string or dict containing the security architecture"
    )


class DesignQualityEvaluationInput(BaseModel):
    """Input schema for evaluating design quality."""
    system_design: str = Field(
        description="JSON string containing the complete system design"
    )


class MultipleComponentStructuresDesignInput(BaseModel):
    """Input schema for designing multiple component structures."""
    component_names: List[str] = Field(
        description="List of component names to design"
    )
    requirements_summary: str = Field(
        description="A summary of the project's technical requirements"
    )


# Planning Tool Models
class ProjectAnalysisSummaryInput(BaseModel):
    """Input schema for getting a summary of project analysis."""
    project_analysis_json: str = Field(
        description="JSON string containing the project analysis with complexity and resource needs"
    )


class MajorSystemComponentsInput(BaseModel):
    """Input schema for extracting major system components."""
    system_design_json: str = Field(
        description="JSON string containing the system design document"
    )


class ComponentRisksInput(BaseModel):
    """Input schema for finding risks associated with a specific component."""
    component_name: str = Field(
        description="Name of the component to find risks for"
    )
    risk_assessment_json: str = Field(
        description="JSON string containing the risk assessment document"
    )


class DevelopmentPhaseInput(BaseModel):
    """Input schema for creating a development phase."""
    phase_name: str = Field(
        description="Name of the development phase"
    )
    phase_type: str = Field(
        description="Type of the phase (setup, backend, frontend, etc.)"
    )
    tasks: List[str] = Field(
        description="List of tasks to be completed in this phase"
    )
    duration: str = Field(
        description="Duration of the phase (e.g., '2 weeks')"
    )
    depends_on: Optional[List[str]] = Field(
        default=None,
        description="List of phase names this phase depends on"
    )


class PhaseDependencyInput(BaseModel):
    """Input schema for creating a dependency between phases."""
    from_phase_id: str = Field(
        description="ID of the phase that must finish first"
    )
    to_phase_id: str = Field(
        description="ID of the phase that depends on the first phase"
    )
    dependency_type: Optional[str] = Field(
        default="finish-to-start",
        description="Type of dependency (finish-to-start, start-to-start, etc.)"
    )


class TimelineEstimationInput(BaseModel):
    """Input schema for extracting timeline details."""
    timeline_estimation_json: str = Field(
        description="JSON string containing the timeline estimation document"
    )


class TechStackAnalysisInput(BaseModel):
    """Input schema for analyzing technology stack."""
    tech_stack_json: str = Field(
        description="JSON string containing the technology stack document"
    )


class ExampleNewToolInput(BaseModel):
    """Input schema for the example new tool."""
    requirement: str = Field(
        description="The requirement to analyze"
    )


class RiskAssessmentInput(BaseModel):
    """Input schema for analyzing risk assessment."""
    risk_assessment_json: str = Field(
        description="JSON string containing the risk assessment document"
    )


class ComprehensivePlanInput(BaseModel):
    """Input schema for compiling a comprehensive project plan."""
    project_analysis: Dict[str, Any] = Field(
        description="Project analysis data"
    )
    system_design: Dict[str, Any] = Field(
        description="System design data"
    )
    timeline_estimation: Dict[str, Any] = Field(
        description="Timeline estimation data"
    )
    risk_assessment: Dict[str, Any] = Field(
        description="Risk assessment data"
    )


class WrappedToolInput(BaseModel):
    """Input schema for wrapped tools that automatically inject stored data."""
    analyze: Optional[bool] = Field(
        default=True,
        description="Whether to analyze the data (always true for wrapped tools)"
    )
    additional_context: Optional[str] = Field(
        default="",
        description="Any additional context to consider"
    )


# NEW: Tech Stack Tool Output Models
class TechnicalRequirementsSummaryOutput(BaseModel):
    """Output schema for technical requirements summary."""
    performance_requirements: List[str] = Field(
        description="Performance-related requirements extracted from the BRD",
        default_factory=list
    )
    security_requirements: List[str] = Field(
        description="Security-related requirements extracted from the BRD",
        default_factory=list
    )
    scalability_requirements: List[str] = Field(
        description="Scalability-related requirements extracted from the BRD",
        default_factory=list
    )
    integration_requirements: List[str] = Field(
        description="Integration-related requirements extracted from the BRD",
        default_factory=list
    )
    technical_constraints: List[str] = Field(
        description="Technical constraints identified from the BRD",
        default_factory=list
    )
    summary: str = Field(
        description="A concise summary of the technical requirements"
    )

class TechOption(BaseModel):
    """A single technology option evaluated by a tool."""
    name: str = Field(
        description="The name of the technology, e.g., 'Python' or 'PostgreSQL'"
    )
    framework: Optional[str] = Field(
        None, 
        description="The specific framework, e.g., 'FastAPI' or 'React'"
    )
    performance_score: Optional[float] = Field(
        None,
        description="Performance score from 1-10"
    )
    scalability_score: Optional[float] = Field(
        None,
        description="Scalability score from 1-10"
    )
    developer_productivity: Optional[float] = Field(
        None,
        description="Developer productivity score from 1-10"
    )
    overall_score: float = Field(
        description="An overall score from 1-10 for its suitability"
    )
    reasoning: str = Field(
        description="Justification for the score and its relevance"
    )

class BackendEvaluationOutput(BaseModel):
    """Structured output for backend technology evaluation."""
    backend_options: List[TechOption] = Field(
        description="A list of evaluated backend technology options"
    )
    recommendation: TechOption = Field(
        description="The single recommended backend technology from the list"
    )

class FrontendEvaluationOutput(BaseModel):
    """Structured output for frontend technology evaluation."""
    frontend_options: List[TechOption] = Field(
        description="A list of evaluated frontend framework options"
    )
    recommendation: TechOption = Field(
        description="The single recommended frontend framework from the list"
    )

class DatabaseEvaluationOutput(BaseModel):
    """Structured output for database technology evaluation."""
    database_options: List[TechOption] = Field(
        description="A list of evaluated database technology options"
    )
    recommendation: TechOption = Field(
        description="The single recommended database technology from the list"
    )

class ArchitecturePatternOption(BaseModel):
    """A single architecture pattern option."""
    pattern: str = Field(
        description="The name of the architecture pattern"
    )
    scalability_score: float = Field(
        description="Scalability score from 1-10"
    )
    maintainability_score: float = Field(
        description="Maintainability score from 1-10"
    )
    development_speed_score: float = Field(
        description="Development speed score from 1-10"
    )
    overall_score: float = Field(
        description="Overall suitability score from 1-10"
    )
    reasoning: str = Field(
        description="Justification for the scores and pattern's suitability"
    )

class ArchitecturePatternEvaluationOutput(BaseModel):
    """Structured output for architecture pattern evaluation."""
    architecture_options: List[ArchitecturePatternOption] = Field(
        description="A list of evaluated architecture pattern options"
    )
    recommendation: Dict[str, str] = Field(
        description="The recommended architecture pattern with reasoning"
    )

class LibraryTool(BaseModel):
    """A library or tool recommended for the tech stack."""
    name: str = Field(
        description="Name of the library or tool"
    )
    purpose: str = Field(
        description="Purpose or function of the library/tool in the project"
    )

class TechStackSynthesisOutput(BaseModel):
    """Comprehensive technology stack recommendation."""
    backend: Dict[str, str] = Field(
        description="Backend technology choices (language, framework, reasoning)"
    )
    frontend: Dict[str, str] = Field(
        description="Frontend technology choices (language, framework, reasoning)"
    )
    database: Dict[str, str] = Field(
        description="Database technology choice (type, reasoning)"
    )
    architecture_pattern: str = Field(
        description="Recommended architecture pattern"
    )
    deployment_environment: Dict[str, str] = Field(
        description="Deployment environment recommendations"
    )
    key_libraries_tools: List[LibraryTool] = Field(
        description="Key libraries and tools recommended for the project"
    )
    estimated_complexity: str = Field(
        description="Estimated complexity level (Low/Medium/High)"
    )

class TechCompatibilityIssue(BaseModel):
    """Potential compatibility issue between tech stack components."""
    components: List[str] = Field(
        description="List of affected components"
    )
    potential_issue: str = Field(
        description="Description of the potential compatibility issue"
    )
    solution: str = Field(
        description="Recommended solution to address the issue"
    )

class TechRisk(BaseModel):
    """Risk associated with the technology stack."""
    category: str = Field(
        description="Risk category"
    )
    description: str = Field(
        description="Detailed description of the risk"
    )
    severity: str = Field(
        description="Risk severity (High/Medium/Low)"
    )
    likelihood: str = Field(
        description="Risk likelihood (High/Medium/Low)"
    )
    mitigation: str = Field(
        description="Recommended risk mitigation strategy"
    )

class TechStackRiskAnalysisOutput(BaseModel):
    """Structured risk analysis for a technology stack."""
    risks: List[TechRisk] = Field(
        description="List of identified risks"
    )
    technology_compatibility_issues: List[TechCompatibilityIssue] = Field(
        description="List of potential compatibility issues between components"
    )

# System Design Output Models
class ProjectRequirementsSummaryOutput(BaseModel):
    """Output schema for project requirements summary."""
    project_name: str = Field(description="The name of the project")
    summary: str = Field(description="A concise summary of the project's main goals and requirements")
    technical_requirements: List[str] = Field(
        description="List of key technical requirements extracted from the BRD",
        default_factory=list
    )
    functional_requirements: List[str] = Field(
        description="List of key functional requirements extracted from the BRD",
        default_factory=list
    )
    constraints: List[str] = Field(
        description="List of identified constraints for the project",
        default_factory=list
    )

class ArchitecturePatternOutput(BaseModel):
    """Output schema for architecture pattern selection."""
    pattern: str = Field(description="The selected architecture pattern name")
    justification: str = Field(description="Detailed justification for selecting this pattern")
    key_benefits: List[str] = Field(
        description="Key benefits of the selected pattern for this project",
        default_factory=list
    )
    potential_drawbacks: List[str] = Field(
        description="Potential drawbacks or challenges of the selected pattern",
        default_factory=list
    )

class SystemComponentOutput(BaseModel):
    """Model for a single system component."""
    name: str = Field(description="Name of the system component")
    description: Optional[str] = Field(None, description="Brief description of the component's purpose")
    category: Optional[str] = Field(None, description="Category of the component (frontend, backend, etc.)")

class SystemComponentsOutput(BaseModel):
    """Output schema for system components identification."""
    components: List[SystemComponentOutput] = Field(
        description="List of identified system components",
        default_factory=list
    )

class InternalSubComponent(BaseModel):
    """Model for an internal sub-component of a system component."""
    name: str = Field(description="Name of the internal sub-component")
    responsibility: str = Field(description="Main responsibility of this sub-component")

class ComponentDesignOutput(BaseModel):
    """Output schema for component structure design."""
    name: str = Field(description="Name of the component")
    responsibilities: List[str] = Field(
        description="List of main responsibilities of the component",
        default_factory=list
    )
    internal_components: List[InternalSubComponent] = Field(
        description="List of internal sub-components",
        default_factory=list
    )
    dependencies: List[str] = Field(
        description="List of other components this component depends on",
        default_factory=list
    )
    design_patterns: List[str] = Field(
        description="List of design patterns applicable to this component",
        default_factory=list
    )

class TableField(BaseModel):
    """Model for a field in a database table."""
    name: str = Field(description="Name of the field")
    type: str = Field(description="Data type of the field")
    constraints: List[str] = Field(
        description="Constraints applied to this field",
        default_factory=list
    )

class DatabaseTable(BaseModel):
    """Model for a database table."""
    name: str = Field(description="Name of the table")
    purpose: str = Field(description="Purpose of this table in the system")
    fields: List[TableField] = Field(
        description="Fields in this table",
        default_factory=list
    )
    relationships: List[Dict[str, str]] = Field(
        description="Relationships with other tables",
        default_factory=list
    )

class DataModelOutput(BaseModel):
    """Output schema for data model design."""
    schema_type: str = Field(description="Type of database schema (relational, document, etc.)")
    tables: List[DatabaseTable] = Field(
        description="Tables or collections in the data model",
        default_factory=list
    )
    relationships: List[Dict[str, str]] = Field(
        description="Relationships between tables or collections",
        default_factory=list
    )

class ApiEndpoint(BaseModel):
    """Model for a single API endpoint."""
    method: str = Field(description="HTTP method (GET, POST, etc.)")
    path: str = Field(description="URL path for the endpoint")
    purpose: str = Field(description="Purpose of this endpoint")
    parameters: List[Dict[str, str]] = Field(
        description="Parameters accepted by this endpoint",
        default_factory=list
    )
    response: Dict[str, Any] = Field(
        description="Response structure",
        default_factory=dict
    )
    authentication_required: bool = Field(description="Whether authentication is required")

class ApiEndpointsOutput(BaseModel):
    """Output schema for API endpoints design."""
    style: str = Field(description="API style (REST, GraphQL, etc.)")
    base_url: str = Field(description="Base URL for the API")
    authentication: str = Field(description="Authentication method")
    endpoints: List[ApiEndpoint] = Field(
        description="List of API endpoints",
        default_factory=list
    )

class SecurityMeasure(BaseModel):
    """Model for a security measure."""
    category: str = Field(description="Category of the security measure")
    implementation: str = Field(description="Implementation details")
    mitigation: Optional[str] = Field(None, description="What threat this measure mitigates")

class SecurityArchitectureOutput(BaseModel):
    """Output schema for security architecture design."""
    authentication_method: str = Field(description="Authentication method used")
    authorization_strategy: str = Field(description="Authorization strategy")
    data_encryption: Dict[str, str] = Field(
        description="Data encryption methods",
        default_factory=dict
    )
    security_measures: List[SecurityMeasure] = Field(
        description="List of security measures",
        default_factory=list
    )

class DevelopmentPhase(BaseModel):
    """Model for a development phase."""
    name: str = Field(description="Name of the phase")
    description: str = Field(description="Description of what happens in this phase")
    priority: str = Field(description="Priority of this phase (High, Medium, Low)")
    dependencies: List[str] = Field(
        description="Phases that must be completed before this one",
        default_factory=list
    )
    tasks: List[str] = Field(
        description="Tasks to be completed in this phase",
        default_factory=list
    )

class SystemDesignOutput(BaseModel):
    """Output schema for comprehensive system design."""
    architecture_overview: Dict[str, str] = Field(
        description="Overview of the architecture pattern and approach",
        default_factory=dict
    )
    modules: List[Dict[str, Any]] = Field(
        description="List of system modules/components with details",
        default_factory=list
    )
    data_model: Dict[str, Any] = Field(
        description="Data model details",
        default_factory=dict
    )
    api_design: Dict[str, Any] = Field(
        description="API design details",
        default_factory=dict
    )
    security_architecture: Dict[str, Any] = Field(
        description="Security architecture details",
        default_factory=dict
    )
    integration_points: List[str] = Field(
        description="Integration points in the system",
        default_factory=list
    )
    deployment_architecture: Dict[str, Any] = Field(
        description="Deployment architecture details",
        default_factory=dict
    )
    development_phases: List[DevelopmentPhase] = Field(
        description="Planned development phases",
        default_factory=list
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Metadata about the design generation"
    )

class DesignQualityDimensionScore(BaseModel):
    """Model for a design quality dimension score."""
    score: float = Field(description="Score from 1-10")
    justification: str = Field(description="Justification for this score")

class DesignQualityOutput(BaseModel):
    """Output schema for design quality evaluation."""
    overall_score: float = Field(description="Overall design quality score from 1-10")
    dimension_scores: Dict[str, DesignQualityDimensionScore] = Field(
        description="Scores for individual dimensions",
        default_factory=dict
    )
    strengths: List[str] = Field(
        description="Strengths of the design",
        default_factory=list
    )
    improvement_opportunities: List[Dict[str, str]] = Field(
        description="Opportunities for improvement",
        default_factory=list
    )

class MultipleComponentStructuresOutput(BaseModel):
    """Output schema for designing multiple component structures."""
    designed_components: List[ComponentDesignOutput] = Field(
        description="List of designed components",
        default_factory=list
    )


# Planning Tool Output Models
class ProjectAnalysisSummaryOutput(BaseModel):
    """Output schema for project analysis summary."""
    complexity_score: int = Field(
        description="Project complexity score from 1-10"
    )
    recommended_team_size: int = Field(
        description="Recommended team size for the project"
    )
    key_challenges: List[str] = Field(
        description="List of key challenges for the project",
        default_factory=list
    )
    summary: str = Field(
        description="Concise summary of the project analysis"
    )

class MajorSystemComponentOutput(BaseModel):
    """Model for a single system component."""
    name: str = Field(
        description="Name of the system component"
    )
    category: Optional[str] = Field(
        None,
        description="Category of the component (frontend, backend, etc.)"
    )

class MajorSystemComponentsOutput(BaseModel):
    """Output schema for major system components extraction."""
    components: List[MajorSystemComponentOutput] = Field(
        description="List of major system components",
        default_factory=list
    )

class ComponentRiskOutput(BaseModel):
    """Model for a risk associated with a specific component."""
    description: str = Field(
        description="Description of the risk"
    )
    severity: Optional[str] = Field(
        None,
        description="Severity level (High, Medium, Low)"
    )
    mitigation: Optional[str] = Field(
        None,
        description="Proposed mitigation strategy"
    )

class ComponentRisksOutput(BaseModel):
    """Output schema for component risks extraction."""
    component_name: str = Field(
        description="Name of the component these risks apply to"
    )
    risks: List[ComponentRiskOutput] = Field(
        description="List of risks associated with this component",
        default_factory=list
    )

class DevelopmentPhaseOutput(BaseModel):
    """Output schema for development phase creation."""
    phase_id: str = Field(
        description="Unique identifier for the phase"
    )
    name: str = Field(
        description="Name of the development phase"
    )
    type: str = Field(
        description="Type of phase (setup, backend, frontend, etc.)"
    )
    duration: str = Field(
        description="Duration estimate for the phase"
    )
    tasks: List[str] = Field(
        description="Tasks included in this phase",
        default_factory=list
    )
    dependencies: List[str] = Field(
        description="IDs of phases this phase depends on",
        default_factory=list
    )

class CurrentPhasesOutput(BaseModel):
    """Output schema for listing current development phases."""
    phases: List[DevelopmentPhaseOutput] = Field(
        description="List of development phases created so far",
        default_factory=list
    )

class TimelineDetailsOutput(BaseModel):
    """Output schema for timeline details extraction."""
    overall_duration_weeks: int = Field(
        description="Overall project duration in weeks"
    )
    key_phases: List[Dict[str, str]] = Field(
        description="List of key phases with durations",
        default_factory=list
    )
    key_milestones: List[Dict[str, str]] = Field(
        description="List of key milestones with dates",
        default_factory=list
    )
    summary: str = Field(
        description="Concise summary of the timeline estimation"
    )

class PhaseDependencyOutput(BaseModel):
    """Output schema for phase dependency creation."""
    from_phase_id: str = Field(
        description="ID of the phase that must finish first"
    )
    to_phase_id: str = Field(
        description="ID of the phase that depends on the first phase"
    )
    dependency_type: str = Field(
        description="Type of dependency (finish-to-start, start-to-start, etc.)"
    )
    success: bool = Field(
        description="Whether the dependency was created successfully"
    )

class TechStackAnalysisOutput(BaseModel):
    """Output schema for tech stack analysis."""
    backend_tech: str = Field(
        description="Backend technology stack"
    )
    frontend_tech: str = Field(
        description="Frontend technology stack"
    )
    database_tech: str = Field(
        description="Database technology"
    )
    deployment_infrastructure: Optional[Dict[str, str]] = Field(
        None,
        description="Deployment and infrastructure details"
    )
    implementation_considerations: List[str] = Field(
        description="Implementation considerations based on the tech stack",
        default_factory=list
    )
    summary: str = Field(
        description="Concise summary of the tech stack analysis"
    )

class RiskSeveritySummary(BaseModel):
    """Model for risk severity summary counts."""
    high: int = Field(
        description="Number of high severity risks"
    )
    medium: int = Field(
        description="Number of medium severity risks"
    )
    low: int = Field(
        description="Number of low severity risks"
    )

class RiskAssessmentOutput(BaseModel):
    """Output schema for risk assessment summary."""
    total_risks: int = Field(
        description="Total number of risks identified"
    )
    severity_breakdown: RiskSeveritySummary = Field(
        description="Breakdown of risks by severity"
    )
    top_risks: List[Dict[str, str]] = Field(
        description="Top risks that need to be addressed",
        default_factory=list
    )
    summary: str = Field(
        description="Concise summary of the risk assessment"
    )

class ProjectSummary(BaseModel):
    """Model for project summary within an implementation plan."""
    title: str = Field(
        description="Title of the implementation plan"
    )
    description: str = Field(
        description="Description of the implementation plan"
    )
    overall_complexity: str = Field(
        description="Overall complexity level (Low, Medium, High)"
    )
    estimated_duration: str = Field(
        description="Estimated duration of the entire project"
    )

class ResourceAllocation(BaseModel):
    """Model for resource allocation within an implementation plan."""
    recommended_team_size: int = Field(
        description="Recommended number of team members"
    )
    key_roles: List[str] = Field(
        description="List of key roles needed for the project",
        default_factory=list
    )

class PlanMetadata(BaseModel):
    """Model for implementation plan metadata."""
    generated_at: str = Field(
        description="Timestamp when the plan was generated"
    )
    generation_method: str = Field(
        description="Method used to generate the plan"
    )

class ImplementationPlan(BaseModel):
    """Model for the complete implementation plan."""
    project_summary: ProjectSummary = Field(
        description="Summary of the project and plan"
    )
    development_phases: List[DevelopmentPhaseOutput] = Field(
        description="List of development phases",
        default_factory=list
    )
    dependencies: List[Dict[str, str]] = Field(
        description="List of dependencies between phases",
        default_factory=list
    )
    resource_allocation: ResourceAllocation = Field(
        description="Resource allocation details"
    )
    metadata: PlanMetadata = Field(
        description="Metadata about the plan generation"
    )

class ComprehensivePlanOutput(BaseModel):
    """Output schema for comprehensive plan compilation."""
    implementation_plan: ImplementationPlan = Field(
        description="The complete implementation plan"
    )