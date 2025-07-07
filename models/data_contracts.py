from pydantic import BaseModel, Field, model_validator, field_validator
from typing import List, Optional, Dict, Any, Union, ClassVar, Type
from datetime import datetime
import json

# --- Core Data Contract Models ---

class Requirement(BaseModel):
    id: str = Field(..., description="Unique identifier for the requirement")
    description: str = Field(..., description="Detailed description of the business requirement")
    category: str = Field(..., description="Functional or Non-Functional")
    priority: int = Field(..., description="Priority of the requirement (e.g., 1-5)")

class BRDAnalysisOutput(BaseModel):
    requirements: List[Requirement] = Field(..., description="List of structured requirements")
    summary: str = Field(..., description="High-level summary of the BRD")

class TechStackComponent(BaseModel):
    """A generic container for a technology recommendation in the tech stack."""
    name: str = Field(description="Name of the core technology or framework (e.g., 'React', 'Node.js', 'PostgreSQL').")
    language: Optional[str] = Field(None, description="The primary programming language, if applicable (e.g., 'Python', 'JavaScript').")
    reasoning: str = Field(description="Justification for why this component was chosen for the project.")
    key_libraries: Optional[List[str]] = Field(default_factory=list, description="A list of key libraries or tools that complement this component.")
    pros: Optional[List[str]] = Field(default_factory=list, description="List of advantages for this tech component.")
    cons: Optional[List[str]] = Field(default_factory=list, description="List of disadvantages for this tech component.")
    selected: bool = Field(False, description="Indicates if this component was selected by the user.")

class TechOption(BaseModel):
    name: str = Field(..., description="Name of the technology/framework")
    reason: str = Field(..., description="Justification for choosing this technology")
    category: str = Field(..., description="e.g., Frontend, Backend, Database")

class TechStackOutput(BaseModel):
    recommendations: List[TechOption] = Field(..., description="List of recommended technologies")
    summary: str = Field(..., description="Overall summary of the technology stack choices")

class DatabaseSchema(BaseModel):
    table_name: str = Field(..., description="Name of the database table")
    columns: Dict[str, str] = Field(..., description="Column names and their data types")
    relations: Optional[List[str]] = Field(None, description="Relationships with other tables")

class SystemDesignOutput(BaseModel):
    architecture: str = Field(..., description="High-level architecture (e.g., Microservices, Monolith)")
    database_schema: List[DatabaseSchema] = Field(..., description="Schema for the database")
    api_endpoints: List[str] = Field(..., description="List of proposed API endpoints")

class Task(BaseModel):
    id: str = Field(..., description="Unique identifier for the task")
    description: str = Field(..., description="Description of the development task")
    dependencies: List[str] = Field([], description="List of task IDs this task depends on")
    estimated_time: str = Field(..., description="Estimated time to complete the task (e.g., '2 days')")

class DevelopmentPlanOutput(BaseModel):
    tasks: List[Task] = Field(..., description="List of development tasks")
    timeline: str = Field(..., description="Proposed project timeline")

class CodeFile(BaseModel):
    file_path: str = Field(..., description="The full path to the file, including the filename and extension.")
    code: str = Field(..., description="The complete source code for the file.")

class GeneratedFile(BaseModel):
    """Model for a generated code file with additional metadata."""
    file_path: str = Field(..., description="The full path to the file, including the filename and extension.")
    content: str = Field(..., description="The complete content for the file.")
    purpose: Optional[str] = Field(None, description="The purpose or description of this file.")
    status: Optional[str] = Field("generated", description="Status of the file generation (e.g., 'generated', 'modified', 'error').")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata about the file.")

class CodeGenerationOutput(BaseModel):
    files: List[CodeFile] = Field(..., description="A list of generated code files.")
    summary: str = Field(..., description="A summary of the generated code and its structure.")
    status: str = Field(default="success", description="Status of the code generation (success, error, partial).")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata about the generation process.")

class CodeQualityAnalysisInput(BaseModel):
    """Input schema for code quality analysis."""
    code_generation_result: Dict[str, Any] = Field(
        description="The result of code generation containing files to analyze"
    )
    tech_stack_recommendation: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Technology stack recommendations to consider during analysis"
    )
    analysis_type: Optional[str] = Field(
        default="comprehensive",
        description="Type of analysis to perform (comprehensive, security, performance)"
    )
    
    model_config = {
        "extra": "allow",  # Allow extra fields for flexibility
        "arbitrary_types_allowed": True  # Allow more flexible typing
    }

class CodeQualityAnalysisOutput(BaseModel):
    """Output schema for code quality analysis."""
    overall_quality_score: float = Field(
        description="Overall code quality score from 0-10"
    )
    specific_issues: List[Dict[str, Any]] = Field(
        description="List of specific issues found in the code",
        default_factory=list
    )
    recommendations: List[str] = Field(
        description="Recommendations for improving code quality",
        default_factory=list
    )
    security_analysis: Dict[str, Any] = Field(
        description="Security-specific analysis results",
        default_factory=dict
    )
    performance_analysis: Dict[str, Any] = Field(
        description="Performance-specific analysis results",
        default_factory=dict
    )
    execution_metrics: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Metrics about the execution of the analysis"
    )
    status: str = Field(
        default="success",
        description="Status of the analysis (success, error, partial)"
    )
    
    model_config = {
        "extra": "allow",  # Allow extra fields for flexibility
        "arbitrary_types_allowed": True  # Allow more flexible typing
    }

class CodeIssue(BaseModel):
    """Model for a code quality issue."""
    file_path: str = Field(description="Path to the file containing the issue")
    line_numbers: Optional[List[int]] = Field(default=None, description="Line numbers where the issue occurs")
    issue_type: str = Field(description="Type of issue (e.g., 'security', 'performance', 'style')")
    severity: str = Field(description="Severity of the issue (e.g., 'critical', 'high', 'medium', 'low')")
    description: str = Field(description="Description of the issue")
    recommendation: str = Field(description="Recommendation to fix the issue")
    code_snippet: Optional[str] = Field(default=None, description="Relevant code snippet")

class SecurityVulnerability(BaseModel):
    """Model for a security vulnerability."""
    file_path: str = Field(description="Path to the file containing the vulnerability")
    vulnerability_type: str = Field(description="Type of vulnerability (e.g., 'SQL Injection', 'XSS')")
    severity: str = Field(description="Severity of the vulnerability (e.g., 'critical', 'high', 'medium', 'low')")
    description: str = Field(description="Description of the vulnerability")
    impact: str = Field(description="Potential impact of the vulnerability")
    recommendation: str = Field(description="Recommendation to fix the vulnerability")
    cwe_id: Optional[str] = Field(default=None, description="Common Weakness Enumeration ID if applicable")
    line_numbers: Optional[List[int]] = Field(default=None, description="Line numbers where the vulnerability occurs")

class CodeQualityReviewInput(BaseModel):
    """Input schema for code quality review."""
    code_files: Dict[str, str] = Field(
        description="Dictionary of file paths to code content"
    )
    tech_stack: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Technology stack information"
    )
    code_type: Optional[str] = Field(
        default="general",
        description="Type of code (e.g., 'backend', 'frontend', 'database')"
    )
    focus_areas: Optional[List[str]] = Field(
        default=None,
        description="Specific areas to focus on during review"
    )
    
    model_config = {
        "extra": "allow",  # Allow extra fields for flexibility
        "arbitrary_types_allowed": True  # Allow more flexible typing
    }

class CodeQualityReviewOutput(BaseModel):
    """Output schema for code quality review."""
    overall_score: float = Field(
        description="Overall code quality score from 0-10"
    )
    has_critical_issues: bool = Field(
        description="Whether the code has critical issues that must be fixed"
    )
    code_structure_analysis: Dict[str, Any] = Field(
        description="Analysis of code structure and organization",
        default_factory=dict
    )
    code_standards_compliance: Dict[str, Any] = Field(
        description="Compliance with coding standards",
        default_factory=dict
    )
    critical_issues: List[Dict[str, Any]] = Field(
        description="Critical issues that must be fixed",
        default_factory=list
    )
    important_recommendations: List[Dict[str, Any]] = Field(
        description="Important recommendations for improvement",
        default_factory=list
    )
    minor_suggestions: List[Dict[str, Any]] = Field(
        description="Minor suggestions for improvement",
        default_factory=list
    )
    
    model_config = {
        "extra": "allow",  # Allow extra fields for flexibility
        "arbitrary_types_allowed": True  # Allow more flexible typing
    }

class TestCase(BaseModel):
    id: str = Field(..., description="Unique identifier for the test case")
    description: str = Field(..., description="Description of what the test case covers")
    steps: List[str] = Field(..., description="Steps to execute the test")
    expected_result: str = Field(..., description="The expected outcome")

class TestPlanOutput(BaseModel):
    test_cases: List[TestCase] = Field(..., description="List of test cases")

class QualityAnalysisOutput(BaseModel):
    linting_report: str = Field(..., description="Report from the linting tool")
    code_complexity: str = Field(..., description="Analysis of code complexity")
    suggestions: List[str] = Field(..., description="Suggestions for improvement")

class TestResult(BaseModel):
    test_case_id: str = Field(..., description="ID of the executed test case")
    passed: bool = Field(..., description="Whether the test passed or failed")
    output: str = Field(..., description="Output from the test execution")

class TestValidationOutput(BaseModel):
    results: List[TestResult] = Field(..., description="List of test results")
    coverage: float = Field(..., description="Code coverage percentage")
    summary: str = Field(..., description="Summary of the test validation phase")

class MajorSystemComponent(BaseModel):
    name: str = Field(..., description="The name of the major system component.")
    description: str = Field(..., description="A detailed description of the component's purpose and functionality.")

class MajorSystemComponentOutput(BaseModel):
    components: List[MajorSystemComponent] = Field(..., description="A list of the major system components identified from the BRD.")

class QualityAssessment(BaseModel):
    """Assessment of BRD quality metrics."""
    clarity_score: float = Field(description="Clarity score from 1-10")
    completeness_score: float = Field(description="Completeness score from 1-10")
    consistency_score: float = Field(description="Consistency score from 1-10")
    recommendations: List[str] = Field(description="Recommendations to improve BRD quality", default_factory=list)

class GapAnalysis(BaseModel):
    """Analysis of gaps in the BRD."""
    identified_gaps: List[str] = Field(description="Specific gaps or missing information identified", default_factory=list)
    recommendations_for_completion: List[str] = Field(description="Recommendations to address the gaps", default_factory=list)

class BRDRequirementsAnalysis(BaseModel):
    """Comprehensive BRD analysis output model with structured requirements and metadata."""
    project_name: str = Field(description="Name of the project extracted from the BRD")
    project_summary: str = Field(description="Summary of the project's purpose and scope")
    project_goals: List[str] = Field(description="List of project goals extracted from the BRD", default_factory=list)
    target_audience: List[str] = Field(description="List of target users or audience for the project", default_factory=list)
    business_context: str = Field(description="Business context and background information")
    requirements: List[Dict[str, Any]] = Field(description="List of structured requirements extracted from the BRD", default_factory=list)
    functional_requirements: List[str] = Field(description="List of functional requirements extracted from the BRD", default_factory=list)
    non_functional_requirements: List[str] = Field(description="List of non-functional requirements extracted from the BRD", default_factory=list)
    stakeholders: List[str] = Field(description="List of project stakeholders", default_factory=list)
    success_criteria: List[str] = Field(description="List of success criteria for the project", default_factory=list)
    constraints: List[str] = Field(description="List of constraints identified in the BRD", default_factory=list)
    assumptions: List[str] = Field(description="List of assumptions identified in the BRD", default_factory=list)
    risks: List[str] = Field(description="List of risks identified in the BRD", default_factory=list)
    domain_specific_details: Dict[str, Any] = Field(description="Domain-specific details and requirements", default_factory=dict)
    quality_assessment: Optional[QualityAssessment] = Field(description="Assessment of BRD quality metrics", default=None)
    gap_analysis: Optional[GapAnalysis] = Field(description="Analysis of gaps in the BRD", default=None)
    
    model_config = {
        "extra": "allow",  # Allow extra fields for flexibility
        "arbitrary_types_allowed": True  # Allow more flexible typing
    }

class LibraryTool(BaseModel):
    """A library or tool recommended for the tech stack."""
    name: str = Field(description="Name of the library or tool")
    purpose: str = Field(description="Purpose or function of the library/tool in the project")

class TechStackSynthesisOutput(BaseModel):
    """Comprehensive technology stack recommendation."""
    backend: Dict[str, str] = Field(description="Backend technology choices (language, framework, reasoning)")
    frontend: Dict[str, str] = Field(description="Frontend technology choices (language, framework, reasoning)")
    database: Dict[str, str] = Field(description="Database technology choice (type, reasoning)")
    architecture_pattern: str = Field(description="Recommended architecture pattern")
    deployment_environment: Dict[str, str] = Field(description="Deployment environment recommendations")
    key_libraries_tools: List[LibraryTool] = Field(description="Key libraries and tools recommended for the project")
    estimated_complexity: str = Field(description="Estimated complexity level (Low/Medium/High)")
    
    @classmethod
    def create_from_recommendations(cls, backend_rec, frontend_rec, database_rec, architecture_rec):
        """Helper method to create a TechStackSynthesisOutput from individual recommendations."""
        # Extract backend info
        backend_info = {
            "language": backend_rec.get("recommendation", {}).get("name", "Unknown"),
            "framework": backend_rec.get("recommendation", {}).get("framework", "Generic"),
            "reasoning": backend_rec.get("recommendation", {}).get("reasoning", "No specific reasoning provided")
        }
        
        # Extract frontend info
        frontend_info = {
            "language": "JavaScript/TypeScript",  # Typically JS/TS for frontend
            "framework": frontend_rec.get("recommendation", {}).get("name", "Unknown"),
            "reasoning": frontend_rec.get("recommendation", {}).get("reasoning", "No specific reasoning provided")
        }
        
        # Extract database info
        database_info = {
            "type": database_rec.get("recommendation", {}).get("name", "Unknown"),
            "reasoning": database_rec.get("recommendation", {}).get("reasoning", "No specific reasoning provided")
        }
        
        # Extract architecture pattern
        arch_pattern = architecture_rec.get("recommendation", {}).get("pattern", "Layered Architecture")
        
        # Create default libraries/tools if none provided
        libraries = []
        
        return cls(
            backend=backend_info,
            frontend=frontend_info,
            database=database_info,
            architecture_pattern=arch_pattern,
            deployment_environment={"hosting": "Cloud-based", "ci_cd": "GitHub Actions"},
            key_libraries_tools=libraries,
            estimated_complexity="Medium"  # Default to medium if not specified
        )

# --- System Design Output Models (more detailed) ---
# These are placed here to ensure they are defined before ComprehensiveSystemDesignOutput
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
    technologies: List[str] = Field(default_factory=list, description="Key technologies used in this component")
    dependencies: List[str] = Field(default_factory=list, description="Other components this component depends on")
    responsibilities: List[str] = Field(default_factory=list, description="Key responsibilities of this component")
    design_patterns: List[str] = Field(default_factory=list, description="Design patterns applied to this component")

class InternalSubComponent(BaseModel):
    """Model for an internal sub-component of a system component."""
    name: str = Field(description="Name of the internal sub-component")
    responsibility: str = Field(description="Main responsibility of this sub-component")
    technologies: List[str] = Field(default_factory=list, description="Technologies used by this sub-component")

    @classmethod
    def model_validate(cls, obj, *args, **kwargs):
        # Allow direct string input, converting it to a dict for validation
        if isinstance(obj, str):
            obj = {"name": obj, "responsibility": f"Handles {obj} related logic"}
        
        # If it's a dict but 'responsibility' is missing, try to infer or set default
        if isinstance(obj, dict) and "responsibility" not in obj:
            obj["responsibility"] = f"Manages {obj.get('name', 'unknown')} functionality"
        
        return super().model_validate(obj, *args, **kwargs)

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
        description="List of design patterns applied to this component",
        default_factory=list
    )
    
    @classmethod
    def model_validate(cls, obj, *args, **kwargs):
        # Custom validation logic to handle cases where 'internal_components' might be a string
        if isinstance(obj, dict) and 'internal_components' in obj and isinstance(obj['internal_components'], str):
            try:
                # Attempt to parse the string as JSON
                obj['internal_components'] = json.loads(obj['internal_components'])
            except json.JSONDecodeError:
                # If it's not valid JSON, treat it as a single component name
                obj['internal_components'] = [{'name': obj['internal_components'], 'responsibility': f"Handles {obj['internal_components']} logic"}]
        
        # Ensure that each item in internal_components is a dict suitable for InternalSubComponent
        if isinstance(obj, dict) and 'internal_components' in obj and isinstance(obj['internal_components'], list):
            obj['internal_components'] = [
                item if isinstance(item, dict) else {'name': item, 'responsibility': f"Handles {item} logic"} 
                for item in obj['internal_components']
            ]
            
        return super().model_validate(obj, *args, **kwargs)

class TableField(BaseModel):
    """Model for a field in a database table."""
    name: str = Field(description="Name of the field")
    type: str = Field(description="Data type of the field")
    constraints: List[str] = Field(default_factory=list, description="Constraints on the field (e.g., 'PRIMARY KEY', 'NOT NULL', 'UNIQUE')")
    description: Optional[str] = Field(None, description="Description of the field's purpose")

class DatabaseTable(BaseModel):
    """Model for a database table."""
    name: str = Field(description="Name of the table")
    purpose: str = Field(description="Purpose of this table in the system")
    fields: List[TableField] = Field(
        description="Fields in this table",
        default_factory=list
    )
    relationships: List[Dict[str, str]] = Field(
        description="Relationships with other tables (e.g., [{'type': 'one-to-many', 'target_table': 'users', 'on': 'user_id'}])",
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
        description="Overall relationships between main entities, if not covered by table-specific relationships",
        default_factory=list
    )
    justification: Optional[str] = Field(None, description="Justification for the chosen data model schema type.")

class ApiEndpoint(BaseModel):
    """Model for a single API endpoint."""
    method: str = Field(description="HTTP method (GET, POST, etc.)")
    path: str = Field(description="URL path for the endpoint")
    purpose: str = Field(description="Purpose of this endpoint")
    parameters: List[Dict[str, str]] = Field(
        description="Parameters accepted by this endpoint (name, type, description)",
        default_factory=list
    )
    response: Dict[str, Any] = Field(
        description="Expected response structure and examples",
        default_factory=dict
    )
    authentication_required: bool = Field(description="Whether authentication is required for this endpoint")
    rate_limiting_applied: bool = Field(default=False, description="Whether rate limiting is applied to this endpoint")

class ApiEndpointsOutput(BaseModel):
    """Output schema for API endpoints design."""
    style: str = Field(description="API style (REST, GraphQL, etc.)")
    base_url: str = Field(description="Base URL for the API")
    authentication: str = Field(description="Authentication method (e.g., OAuth2, JWT, API Key)")
    endpoints: List[ApiEndpoint] = Field(
        description="List of designed API endpoints",
        default_factory=list
    )
    error_handling: str = Field(description="General error handling strategy for the API")
    rate_limiting_strategy: Optional[str] = Field(None, description="Overall rate limiting strategy for the API")

class SecurityMeasure(BaseModel):
    """Model for a security measure."""
    category: str = Field(description="Category of the security measure (e.g., 'Authentication', 'Authorization', 'Data Protection', 'Input Validation')")
    implementation: str = Field(description="Details on how this security measure will be implemented")
    mitigation: Optional[str] = Field(None, description="What specific threat this measure mitigates")
    priority: str = Field(default="Medium", description="Priority of this security measure (High, Medium, Low)")

class SecurityArchitectureOutput(BaseModel):
    """Output schema for security architecture design."""
    authentication_method: str = Field(description="The primary authentication method used (e.g., 'OAuth 2.0', 'JWT', 'API Keys', 'Session-based')")
    authorization_strategy: str = Field(description="The authorization strategy (e.g., 'RBAC', 'ABAC', 'ACLs')")
    data_encryption: Dict[str, str] = Field(
        description="Details on data encryption at rest and in transit",
        default_factory=dict
    )
    security_measures: List[SecurityMeasure] = Field(
        description="List of key security measures and controls to be implemented",
        default_factory=list
    )
    vulnerability_mitigation_strategies: List[str] = Field(default_factory=list, description="General strategies for mitigating common web vulnerabilities (e.g., XSS, SQL Injection)")
    compliance_standards: List[str] = Field(default_factory=list, description="Relevant compliance standards (e.g., GDPR, HIPAA, PCI DSS)")

class DevelopmentPhaseModel(BaseModel):
    """Model for a development phase."""
    name: str = Field(description="Name of the phase")
    description: str = Field(description="Description of what happens in this phase")
    priority: str = Field(description="Priority of this phase (High, Medium, Low)")
    dependencies: List[str] = Field(
        description="Phases that must be completed before this one",
        default_factory=list
    )
    tasks: List[str] = Field(
        description="Key tasks within this phase",
        default_factory=list
    )
    estimated_duration: str = Field(description="Estimated duration for this phase (e.g., '2 weeks', '3 days')")

class CodeQualityDimensionScore(BaseModel):
    """Model for a design quality dimension score."""
    score: float = Field(description="Score from 1-10")
    justification: str = Field(description="Justification for this score")

class DesignQualityOutput(BaseModel):
    """Output schema for design quality evaluation."""
    overall_score: float = Field(description="Overall design quality score from 1-10")
    dimension_scores: Dict[str, CodeQualityDimensionScore] = Field(
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

class ComprehensiveSystemDesignOutput(BaseModel):
    """
    A comprehensive, single-object output for the system design phase.
    """
    architecture: ArchitecturePatternOutput = Field(description="The selected architecture pattern and justification.")
    components: List[SystemComponentOutput] = Field(description="A list of all identified system components and their details.")
    data_model: DataModelOutput = Field(description="The complete database schema design.")
    api_endpoints: ApiEndpointsOutput = Field(description="The full set of designed API endpoints.")
    security: SecurityArchitectureOutput = Field(description="A summary of the security architecture.")
    scalability_and_performance: Dict[str, Any] = Field(default_factory=dict, description="Strategies for scalability and performance.")
    deployment_strategy: Dict[str, Any] = Field(default_factory=dict, description="The proposed deployment strategy and environment.")
    monitoring_and_logging: Dict[str, Any] = Field(default_factory=dict, description="Monitoring and logging strategies.")
    error_handling_strategy: str = Field(description="Overall error handling strategy for the system.")
    development_phases_overview: List[DevelopmentPhaseModel] = Field(default_factory=list, description="An overview of the development phases derived from the design.")
    key_risks: List[str] = Field(default_factory=list, description="Key risks identified in the system design.")
    design_justification: str = Field(description="Overall justification for the chosen design decisions.")
    data_flow: str = Field(default="", description="A description of the main data flow through the system.") # Added data_flow field

class MultipleComponentStructuresOutput(BaseModel):
    """Output schema for designing multiple component structures."""
    designed_components: List[ComponentDesignOutput] = Field(
        description="List of designed components",
        default_factory=list
    )

# --- Planning Tool Input Models ---
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
    project_analysis: Union[Dict[str, Any], str] = Field(
        default_factory=dict,
        description="Project analysis data (dict or JSON string)"
    )
    system_design: Union[Dict[str, Any], str] = Field(
        default_factory=dict,
        description="System design data (dict or JSON string)"
    )
    timeline_estimation: Union[Dict[str, Any], str] = Field(
        default_factory=dict,
        description="Timeline estimation data (dict or JSON string)"
    )
    risk_assessment: Union[Dict[str, Any], str] = Field(
        default_factory=dict,
        description="Risk assessment data (dict or JSON string)"
    )

class WrappedToolInput(BaseModel):
    """Generic input schema for wrapped tools."""
    analyze: Optional[bool] = Field(
        default=True,
        description="Whether to analyze the inputs"
    )
    additional_context: Optional[str] = Field(
        default="",
        description="Optional additional context for the analysis"
    )

# --- Planning Tool Output Models ---
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

class ComprehensivePlanOutput(BaseModel):
    """Output schema for comprehensive plan compilation."""
    implementation_plan: Dict[str, Any] = Field(
        description="The complete implementation plan"
    )

# --- System Design Tool Input Models ---
class ProjectRequirementsSummaryInput(BaseModel):
    """Input schema for summarizing project requirements."""
    brd_analysis_json: Union[str, dict, None] = Field(
        default=None,
        description="BRD analysis data - can be a JSON string, dictionary, or None (will be injected by the system if not provided)."
    )
    project_name: Optional[str] = Field(
        default=None,
        description="Optional project name parameter that might be passed by ReAct agents"
    )
    requirements_summary: Optional[str] = Field(
        default=None,
        description="Optional requirements summary that might be passed by ReAct agents"
    )
    
    model_config = {
        "extra": "allow",  # Allow extra fields which enables flexible input handling from ReAct agents
        "arbitrary_types_allowed": True  # Allow more flexible typing
    }
    
    @model_validator(mode='before')
    @classmethod
    def parse_json_input(cls, data):
        """Handle the case where the entire input might be a JSON string."""
        if isinstance(data, dict) and 'brd_analysis_json' in data:
            brd = data['brd_analysis_json']
            if isinstance(brd, str) and '{' in brd and '}' in brd and len(brd) > 50:
                try:
                    parsed = json.loads(brd)
                    if isinstance(parsed, dict):
                        # Merge the parsed values with the original data
                        for key, value in parsed.items():
                            if key not in data or data[key] is None:
                                data[key] = value
                except Exception:
                    # If parsing fails, use the original data
                    pass
        return data

class ArchitecturePatternSelectionInput(BaseModel):
    """Input schema for selecting an architecture pattern."""
    requirements_summary: str = Field(
        description="A summary of the project's technical requirements"
    )
    tech_stack_json: Optional[Union[str, dict]] = Field(
        default="{}",
        description="JSON string or dict containing the recommended technology stack (optional, defaults to empty)"
    )

class SystemComponentsIdentificationInput(BaseModel):
    """Input schema for identifying system components."""
    requirements_summary: str = Field(
        description="Summary of technical requirements that influence system components"
    )
    architecture_pattern: Optional[str] = Field(
        default="",
        description="The selected architecture pattern"
    )

class ComponentStructureDesignInput(BaseModel):
    """Input schema for designing a component structure."""
    component_name: Union[str, dict] = Field(
        description="Name of the component to design, or JSON string/dict containing both component_name and requirements_summary"
    )
    requirements_summary: Optional[str] = Field(
        default=None,
        description="A summary of the project's technical requirements (optional if component_name contains both fields)"
    )

class MultipleComponentStructuresDesignInput(BaseModel):
    """Input schema for designing multiple component structures."""
    component_names: Union[List[str], str, Dict[str, Any]] = Field(
        description="List of component names to design or a JSON string that contains component names"
    )    
    requirements_summary: Optional[str] = Field(
        default=None,
        description="A summary of the project's technical requirements"
    )
    
    model_config = {
        "arbitrary_types_allowed": True
    }
    
    @classmethod
    def model_validate(cls, obj, *args, **kwargs):
        """Handle various input formats for component_names."""
        try:
            return super().model_validate(obj, *args, **kwargs)
        except Exception as e:
            # Special handling for JSON strings and other formats
            if isinstance(obj, str):
                try:
                    data = json.loads(obj)
                    if isinstance(data, dict) and "component_names" in data:
                        return cls(
                            component_names=data["component_names"],
                            requirements_summary=data.get("requirements_summary")
                        )
                except:
                    pass
            return cls(component_names=obj, requirements_summary=None)
            
    @field_validator('component_names')
    def validate_component_names(cls, v):
        """Ensure component_names can be processed regardless of input format."""
        if isinstance(v, str):
            try:
                # Try to parse as JSON if it's a string
                parsed = json.loads(v)
                if isinstance(parsed, dict) and "component_names" in parsed:
                    return parsed["component_names"]
                elif isinstance(parsed, list):
                    return parsed
                return [v]  # If all else fails, treat as a single component name
            except json.JSONDecodeError:
                return [v]  # Not valid JSON, treat as single component name
        elif isinstance(v, dict) and "component_names" in v:
            return v["component_names"]
        return v

class DataModelDesignInput(BaseModel):
    """Input schema for designing a data model."""
    requirements_summary: str = Field(
        default="",
        description="A summary of the project's technical requirements"
    )
    components: Union[str, List[str]] = Field(
        default="[]",
        description="JSON string containing system components or a list of component names"
    )
    database_technology: str = Field(
        default="SQL Database",
        description="The selected database technology (e.g., 'PostgreSQL', 'MongoDB')"
    )
    
    @model_validator(mode='before')
    @classmethod
    def parse_json_input(cls, data):
        """Handle the case where the entire input might be a JSON string in the first field."""
        if isinstance(data, dict) and 'requirements_summary' in data:
            req = data['requirements_summary']
            if isinstance(req, str) and '{' in req and '}' in req and len(req) > 50:
                try:
                    parsed = json.loads(req)
                    if isinstance(parsed, dict) and 'requirements_summary' in parsed:
                        # Replace with the parsed values
                        data = parsed
                except Exception:
                    # If parsing fails, use the original data
                    pass
                    
        # Convert components list to JSON string if needed
        if isinstance(data, dict) and 'components' in data and isinstance(data['components'], list):
            try:
                data['components'] = json.dumps(data['components'])
            except Exception:
                # If conversion fails, keep the original value
                pass
                    
        return data
        
    @field_validator('components')
    @classmethod
    def validate_components(cls, v):
        """Convert components to the expected string format if needed."""
        if isinstance(v, list):
            return json.dumps(v)
        return v

class ApiEndpointsDesignInput(BaseModel):
    """Input schema for designing API endpoints."""
    requirements_summary: str = Field(
        default="",
        description="A summary of the project's technical requirements"
    )
    components: Union[str, List[str]] = Field(
        default="[]",
        description="JSON string containing system components or a list of component names"
    )
    
    @model_validator(mode='before')
    @classmethod
    def parse_json_input(cls, data):
        """Handle the case where the entire input might be a JSON string in the first field."""
        if isinstance(data, dict) and 'requirements_summary' in data:
            req = data['requirements_summary']
            if isinstance(req, str) and '{' in req and '}' in req and len(req) > 50:
                try:
                    parsed = json.loads(req)
                    if isinstance(parsed, dict):
                        # Check if this parsed object has our expected fields
                        if any(key in parsed for key in ['requirements_summary', 'components']):
                            # Replace with the parsed values
                            data = parsed
                except Exception:
                    # If parsing fails, use the original data
                    pass
                    
        # Check for alternative field names for components
        if isinstance(data, dict) and 'components' not in data:
            for alt_field in ['requirements', 'system_components', 'component_list']:
                if alt_field in data and data[alt_field]:
                    data['components'] = data[alt_field]
                    break
                    
        return data
        
    @field_validator('components')
    @classmethod
    def validate_components(cls, v):
        """Convert components to the expected string format if needed."""
        if isinstance(v, list):
            return json.dumps(v)
        return v

class SecurityArchitectureDesignInput(BaseModel):
    """Input schema for designing security architecture."""
    requirements_summary: str = Field(
        description="A summary of the project's technical requirements"
    )
    architecture_pattern: Optional[str] = Field(
        default="Generic Architecture",
        description="The chosen architecture pattern (optional)"
    )

class SystemDesignSynthesisInput(BaseModel):
    """Input schema for synthesizing a comprehensive system design."""
    architecture_pattern: str = Field(
        description="The selected architecture pattern for the system"
    )
    components: Optional[str] = Field(
        default="[]",
        description="JSON string or list containing the system components"
    )
    data_model: Optional[str] = Field(
        default="{}",
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

# --- System Design Tool Output Models (more detailed) ---
# The ComprehensiveSystemDesignOutput and its dependencies were moved earlier in the file.

# Tech stack tool input models
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

class ArchitectureEvaluationInput(BaseModel):
    """Input schema for evaluating architecture patterns."""
    requirements_summary: str = Field(
        description="A summary of the project's technical requirements"
    )
    backend: Optional[Union[str, Dict[str, Any]]] = Field(
        default="", 
        description="Selected backend technology (can be string or dict with name/framework)"
    )
    database: Optional[Union[str, Dict[str, Any]]] = Field(
        default="", 
        description="Selected database technology (can be string or dict with name/framework)"
    )
    frontend: Optional[Union[str, Dict[str, Any]]] = Field(
        default="", 
        description="Selected frontend technology (can be string or dict with name/framework)"
    )

class TechStackInput(BaseModel):
    """Input schema for tech stack tools."""
    backend: Optional[str] = Field(
        default=None,
        description="The backend technology choice"
    )
    frontend: Optional[str] = Field(
        default=None,
        description="The frontend technology choice"
    )
    database: Optional[str] = Field(
        default=None,
        description="The database technology choice"
    )
    architecture_pattern: Optional[str] = Field(
        default=None,
        description="The architecture pattern choice"
    )
    requirements_summary: Optional[str] = Field(
        default=None,
        description="Summary of technical requirements that influence technology choices"
    )

class TechStackSynthesisInput(BaseModel):
    """Input schema for synthesizing a complete technology stack."""
    evaluation_results: Union[Dict[str, Any], str] = Field(
        default_factory=dict,
        description="The full JSON object or JSON string returned by the 'evaluate_all_technologies' tool, containing backend, frontend, and database evaluations"
    )
    architecture_recommendation: Union[Dict[str, Any], str] = Field(
        default_factory=dict,
        description="The JSON object or JSON string returned by the 'evaluate_architecture_patterns' tool"
    )
    combined_input: Optional[str] = Field(
        None,
        description="Alternative field for when all recommendations are provided in a single string"    )
    
    # Add these fields to handle the agent-style format with _recommendation fields
    backend_recommendation: Optional[Union[Dict[str, Any], str]] = Field(
        None,
        description="The backend technology recommendation"
    )
    frontend_recommendation: Optional[Union[Dict[str, Any], str]] = Field(
        None,
        description="The frontend technology recommendation"
    )
    database_recommendation: Optional[Union[Dict[str, Any], str]] = Field(
        None,
        description="The database technology recommendation"
    )
    
    class Config:
        extra = "allow"  # Allow extra fields which enables flexible input handling
        arbitrary_types_allowed = True  # Allow more flexible typing
    
    def __init__(self, **data):
        # Import logging first to avoid undefined reference
        import logging
        logger = logging.getLogger(__name__)
        
        # Special handling for various input cases
        try:
            # Case 1: Single string parameter that might be JSON
            if len(data) == 1 and isinstance(next(iter(data.values())), str):
                key, value = next(iter(data.items()))
                if key != "combined_input":  # Only process if not already using combined_input
                    logger.info(f"TechStackSynthesisInput init: Processing single string parameter with key {key}")
                    validated = self.validate_input({key: value})
                    super().__init__(**validated)
                    return
            
            # Case 2: Direct _recommendation fields provided
            if any(key.endswith('_recommendation') for key in data.keys()):
                logger.info("Found *_recommendation fields directly in input")
                validated = self.validate_input(data)
                super().__init__(**validated)
                return
                    
            # Default init for all other cases
            super().__init__(**data)
        except Exception as e:
            logger.error(f"Error in TechStackSynthesisInput.__init__: {str(e)}")
            # Fallback to basic initialization with defaults
            super().__init__(
                evaluation_results={"backend": {}, "frontend": {}, "database": {}},
                architecture_recommendation={"recommendation": {"pattern": "Layered Architecture"}}
            )
    
    @classmethod
    def validate_input(cls, tool_input: Any) -> Dict[str, Any]:
        """
        Additional validation method to handle string JSON input and various formats.
        
        Args:
            tool_input: The input to validate, which could be a string, dict, or other format
            
        Returns:
            Dict containing properly structured evaluation_results and architecture_recommendation
        """
        import json
        import logging
        import re
        import traceback
        
        logger = logging.getLogger(__name__)
        
        # Default values to return in case of parsing errors
        default_return = {
            "evaluation_results": {"backend": {}, "frontend": {}, "database": {}},
            "architecture_recommendation": {"recommendation": {"pattern": "Layered Architecture"}}
        }
        
        # Handle empty input
        if not tool_input:
            logger.error("Empty tool_input provided to TechStackSynthesisInput.validate_input")
            return default_return
            
        # Log the input type for debugging
        logger.info(f"TechStackSynthesisInput.validate_input called with input type: {type(tool_input)}")
        if isinstance(tool_input, dict):
            logger.info(f"Input dict keys: {list(tool_input.keys())}")
        elif isinstance(tool_input, str):
            logger.info(f"Input string preview: {tool_input[:100]}...")
            
        # Check for *_recommendation fields directly in the input dictionary
        if isinstance(tool_input, dict) and any(k.endswith('_recommendation') for k in tool_input.keys()):
            logger.info("Found *_recommendation fields directly in input dictionary")
            result = {
                "evaluation_results": {
                    "backend": tool_input.get("backend_recommendation", {}),
                    "frontend": tool_input.get("frontend_recommendation", {}),
                    "database": tool_input.get("database_recommendation", {})
                },
                "architecture_recommendation": tool_input.get("architecture_recommendation", 
                                                           {"recommendation": {"pattern": "Layered Architecture"}})
            }
            return result
            
        # Case 1: Special handling for combined_input field which holds all recommendations in one string
        if "combined_input" in tool_input and tool_input["combined_input"]:
            logger.info("Processing combined_input field with comprehensive recommendations")
            combined_input_str = tool_input["combined_input"]
            
            try:
                # Extract JSON if it's embedded in the string
                if not combined_input_str.strip().startswith("{"):
                    match = re.search(r'\{.*\}', combined_input_str, re.DOTALL)
                    if match:
                        extracted = match.group(0)
                        logger.info(f"Extracted JSON from combined_input: {extracted[:100]}...")
                        combined_input_str = extracted
                
                # Try to parse the JSON
                parsed_json = json.loads(combined_input_str)
                logger.info(f"Successfully parsed combined_input JSON: {list(parsed_json.keys()) if isinstance(parsed_json, dict) else 'not a dict'}")
                
                # Handle case where all recommendations are in one JSON object
                if isinstance(parsed_json, dict) and any(k.endswith('_recommendation') for k in parsed_json.keys()):
                    result = {
                        "evaluation_results": {
                            "backend": parsed_json.get("backend_recommendation", {}),
                            "frontend": parsed_json.get("frontend_recommendation", {}),
                            "database": parsed_json.get("database_recommendation", {})
                        },
                        "architecture_recommendation": parsed_json.get("architecture_recommendation", {})
                    }
                    logger.info("Reconstructed input structure from combined_input recommendations JSON")
                    return result
                return {"evaluation_results": parsed_json, "architecture_recommendation": {"recommendation": {"pattern": "Layered Architecture"}}}
            except Exception as e:
                logger.error(f"Failed to process combined_input: {str(e)}")
                logger.error(traceback.format_exc())
        
        # Case 2: If we got a string for the whole input, try to parse it as JSON
        if isinstance(tool_input, str):
            logger.info(f"Got string as tool_input: {tool_input[:100]}...")
            
            # Special case: Check for the error case where an entire JSON object with recommendations is passed
            # This is the format seen in the error: '{"backend_recommendation"...attern": "Monolithic"}}'
            if "recommendation" in tool_input and "{" in tool_input and "}" in tool_input:
                logger.info("Detected potential complete tech stack recommendation in string format")
                # Extract the JSON structure
                if not tool_input.strip().startswith("{"):
                    # Try to extract JSON from the string
                    match = re.search(r'\{.*\}', tool_input, re.DOTALL)
                    if match:
                        extracted = match.group(0)
                        logger.info(f"Extracted JSON from string: {extracted[:100]}...")
                        tool_input = extracted
                
                try:
                    parsed_json = json.loads(tool_input)
                    logger.info(f"Successfully parsed tech stack JSON: {list(parsed_json.keys()) if isinstance(parsed_json, dict) else 'not a dict'}")
                    
                    # Handle case where all recommendations are in one JSON object
                    if isinstance(parsed_json, dict) and any(k.endswith('_recommendation') for k in parsed_json.keys()):
                        result = {
                            "evaluation_results": {
                                "backend": parsed_json.get("backend_recommendation", {}),
                                "frontend": parsed_json.get("frontend_recommendation", {}),
                                "database": parsed_json.get("database_recommendation", {})
                            },
                            "architecture_recommendation": parsed_json.get("architecture_recommendation", {})
                        }
                        logger.info("Reconstructed input structure from combined recommendations JSON")
                        return result
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse tech stack string as JSON: {e}")
            
            # Special case: the input is already a formatted dictionary-like string but not JSON
            if "{" in tool_input and "}" in tool_input and ":" in tool_input and not tool_input.strip().startswith("{"):
                logger.info("Input appears to be a non-JSON dict-like string, attempting to extract")
                # Try to extract dictionary-like content between curly braces
                match = re.search(r'\{.*\}', tool_input, re.DOTALL)
                if match:
                    extracted = match.group(0)
                    logger.info(f"Extracted potential JSON: {extracted[:100]}...")
                    tool_input = extracted
            
            try:
                parsed_input = json.loads(tool_input)
                logger.info(f"Successfully parsed JSON with keys: {list(parsed_input.keys()) if isinstance(parsed_input, dict) else 'not a dict'}")
                
                # Case 1.1: The parsed input has our expected fields
                if "evaluation_results" in parsed_input and "architecture_recommendation" in parsed_input:
                    return parsed_input
                
                # Case 1.2: The parsed input might have backend_recommendation, frontend_recommendation, etc.
                if any(key.endswith('_recommendation') for key in parsed_input.keys()):
                    result = {
                        "evaluation_results": {
                            "backend": parsed_input.get("backend_recommendation", {}),
                            "frontend": parsed_input.get("frontend_recommendation", {}),
                            "database": parsed_input.get("database_recommendation", {})
                        },
                        "architecture_recommendation": parsed_input.get("architecture_recommendation", {})
                    }
                    logger.info("Reconstructed input from *_recommendation fields")
                    return result
                
                # Case 1.3: Generic fallback - build a new structure
                return {
                    "evaluation_results": parsed_input,
                    "architecture_recommendation": {"recommendation": {"pattern": "Layered Architecture"}}
                }
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse tool_input as JSON: {str(e)}")
                return default_return
        
        # Case 2: Dictionary with evaluation_results as a string
        if isinstance(tool_input, dict):
            result = {}
            
            # Process evaluation_results
            eval_results = tool_input.get("evaluation_results")
            if isinstance(eval_results, str):
                try:
                    result["evaluation_results"] = json.loads(eval_results)
                except json.JSONDecodeError:
                    result["evaluation_results"] = {"backend": {}, "frontend": {}, "database": {}}
            else:
                result["evaluation_results"] = eval_results or {"backend": {}, "frontend": {}, "database": {}}
            
            # Process architecture_recommendation
            arch_rec = tool_input.get("architecture_recommendation")
            if isinstance(arch_rec, str):
                try:
                    result["architecture_recommendation"] = json.loads(arch_rec)
                except json.JSONDecodeError:
                    result["architecture_recommendation"] = {"recommendation": {"pattern": "Layered Architecture"}}
            else:
                result["architecture_recommendation"] = arch_rec or {"recommendation": {"pattern": "Layered Architecture"}}
            
            return result
        
        # Case 3: Fallback
        logger.warning(f"Unexpected tool_input type: {type(tool_input)}")
        return default_return

class FrontendEvaluationInput(BaseModel):
    """Input schema for evaluating frontend technology options."""
    requirements: str = Field(
        description="The requirements relevant to frontend development"
    )
    user_experience: Optional[str] = Field(
        default="Standard user experience with focus on usability and performance",
        description="The UX priorities and focus areas for the project"
    )

class BatchTechnologyEvaluationInput(BaseModel):
    """Input schema for batch technology evaluation to minimize API calls."""
    requirements_summary: str = Field(
        description="A summary of the project's technical requirements that influence technology choices"
    )
    evaluate_backend: bool = Field(
        default=True,
        description="Whether to evaluate backend technologies"
    )
    evaluate_frontend: bool = Field(
        default=True,
        description="Whether to evaluate frontend technologies"
    )
    evaluate_database: bool = Field(
        default=True,
        description="Whether to evaluate database technologies"
    )
    ux_focus: Optional[Union[str, List[str], bool]] = Field(
        default=None,
        description="User experience focus for frontend evaluation"
    )
    evaluation_flags: Optional[List[str]] = Field(
        default_factory=list,
        description="Additional evaluation flags or preferences"
    )
    
    @field_validator('ux_focus')
    @classmethod
    def convert_ux_focus_to_string(cls, v):
        """Convert ux_focus list to string if needed."""
        if v is None:
            return None
        elif isinstance(v, bool):
            # Convert boolean to string representation
            return "Standard user experience" if v else None
        elif isinstance(v, list):
            if v:  # Non-empty list
                return ", ".join(str(item) for item in v)
            else:  # Empty list
                return None
        elif isinstance(v, str):
            return v
        else:
            return str(v)

# Tech stack tool output models
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

class TechStackRiskAnalysisInput(BaseModel):
    """Input schema for technology stack risk analysis."""
    tech_stack_json: str = Field(
        description="JSON representation of the proposed technology stack"
    )
    requirements_summary: Optional[str] = Field(
        default="Standard web application requirements with focus on reliability and security.",
        description="Summary of technical requirements"
    )

class ImplementationPlan(BaseModel):
    """Comprehensive implementation plan model."""
    project_summary: Dict[str, Any] = Field(
        description="Project summary information including title, description, complexity"
    )
    phases: List[Dict[str, Any]] = Field(
        description="List of development phases with tasks, durations, and dependencies"
    )
    resource_allocation: List[Dict[str, Any]] = Field(
        description="Resource allocation across the project phases"
    )
    risks_and_mitigations: List[Dict[str, Any]] = Field(
        description="Identified risks and their mitigation strategies",
        default_factory=list
    )
    timeline: Dict[str, Any] = Field(
        description="Project timeline with milestones and key dates"
    )
    tech_stack: Dict[str, Any] = Field(
        description="Technology stack to be used in the implementation",
        default_factory=dict
    )
    metadata: Dict[str, Any] = Field(
        description="Metadata about the plan including version and generation date",
        default_factory=dict
    )
    
    model_config = {
        "extra": "allow",  # Allow extra fields for flexibility
        "arbitrary_types_allowed": True  # Allow more flexible typing
    }

class ProjectSummary(BaseModel):
    """Model for project summary section in implementation plans."""
    title: str = Field(description="Project title")
    description: str = Field(description="Brief project description")
    overall_complexity: str = Field(description="Complexity assessment (e.g., '7/10')")
    estimated_duration: str = Field(description="Estimated project duration (e.g., '12 weeks')")
    key_challenges: Optional[List[str]] = Field(default_factory=list, description="Key challenges identified for the project")
    success_criteria: Optional[List[str]] = Field(default_factory=list, description="Success criteria for the project")

class ResourceAllocation(BaseModel):
    """Model for resource allocation in implementation plans."""
    role: str = Field(description="Role name (e.g., 'Backend Developer')")
    count: int = Field(description="Number of resources needed")
    estimated_time_allocation: str = Field(description="Time allocation (e.g., '100%', 'part-time')")
    phases: List[str] = Field(description="Phases where this resource is needed")
    skills_required: List[str] = Field(default_factory=list, description="Required skills for this role")

class PlanMetadata(BaseModel):
    """Metadata for implementation plans."""
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Timestamp when plan was generated")
    version: str = Field(default="1.0", description="Plan version")
    author: str = Field(default="Multi-AI Dev System", description="Author of the plan")
    tags: Optional[List[str]] = Field(default_factory=list, description="Tags for categorization")
    notes: Optional[str] = Field(default=None, description="Additional notes about the plan")

class BatchAnalysisInput(BaseModel):
    """Input schema for batch analysis operations."""
    analysis_type: str = Field(
        description="Type of analysis to perform (e.g., 'requirements', 'technical', 'risk')"
    )
    data_sources: List[Dict[str, Any]] = Field(
        description="List of data sources to analyze",
        default_factory=list
    )
    analysis_parameters: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Parameters for the analysis process"
    )
    batch_size: Optional[int] = Field(
        default=10,
        description="Size of each batch for processing"
    )
    
    model_config = {
        "extra": "allow",
        "arbitrary_types_allowed": True
    }

# Missing data contracts for planning agents

class ExecutiveSummary(BaseModel):
    """Executive summary for project analysis."""
    project_complexity: str = Field(description="Project complexity score (e.g., '7/10')")
    resource_needs: str = Field(description="Resource needs description (e.g., '3-5 team members')")
    estimated_duration: str = Field(description="Estimated project duration (e.g., '12 weeks')")
    scope_completeness: str = Field(description="Scope completeness assessment (e.g., '70%')")
    key_finding: str = Field(description="Key finding or insight from the analysis")

class ProjectAnalysisInput(BaseModel):
    """Input schema for project analysis."""
    requirements_analysis: Dict[str, Any] = Field(description="Requirements analysis data")
    tech_stack_recommendation: Dict[str, Any] = Field(description="Technology stack recommendation")
    system_design: Dict[str, Any] = Field(description="System design specifications")

class ProjectAnalysisOutput(BaseModel):
    """Output schema for project analysis."""
    executive_summary: ExecutiveSummary = Field(description="Executive summary of the analysis")
    project_viability: str = Field(description="Project viability assessment")
    critical_success_factors: List[str] = Field(description="Critical success factors", default_factory=list)
    recommended_approach: str = Field(description="Recommended implementation approach")
    top_risks: List[Dict[str, str]] = Field(description="Top risks and mitigations", default_factory=list)
    resource_recommendations: Dict[str, Any] = Field(description="Resource recommendations", default_factory=dict)
    timeline_recommendation: Dict[str, str] = Field(description="Timeline recommendations", default_factory=dict)
    analysis_metadata: Dict[str, Any] = Field(description="Analysis metadata", default_factory=dict)

class ExecutiveSummaryRisk(BaseModel):
    """Executive summary for risk assessment."""
    overall_risk_level: str = Field(description="Overall risk level (High/Medium/Low)")
    critical_risk_count: int = Field(description="Number of critical risks")
    key_risk_areas: List[str] = Field(description="Key risk areas", default_factory=list)
    mitigation_readiness: str = Field(description="Mitigation readiness level")
    risk_management_recommendation: str = Field(description="Risk management recommendation")

class AnalyzedRisk(BaseModel):
    """Model for an analyzed risk."""
    risk_id: str = Field(description="Unique risk identifier")
    category: str = Field(description="Risk category")
    description: str = Field(description="Risk description")
    severity: str = Field(description="Risk severity (High/Medium/Low)")
    probability: str = Field(description="Risk probability (High/Medium/Low)")
    impact: str = Field(description="Risk impact description")
    risk_score: int = Field(description="Risk score (1-10)")
    justification: str = Field(description="Justification for the risk assessment")

class RiskSummary(BaseModel):
    """Summary of risks identified."""
    total_risks: int = Field(description="Total number of risks")
    high_severity: int = Field(description="Number of high severity risks")
    medium_severity: int = Field(description="Number of medium severity risks")
    low_severity: int = Field(description="Number of low severity risks")
    overall_risk_assessment: str = Field(description="Overall risk assessment")

class MonitoringRecommendation(BaseModel):
    """Risk monitoring recommendation."""
    risk_area: str = Field(description="Risk area to monitor")
    monitoring_frequency: str = Field(description="Monitoring frequency")
    key_metrics: List[str] = Field(description="Key metrics to monitor", default_factory=list)
    responsible_role: str = Field(description="Responsible role for monitoring")

class TimelineEstimationOutput(BaseModel):
    """Complete timeline estimation output."""
    project_timeline: Dict[str, Any] = Field(description="Project timeline overview", default_factory=dict)
    development_phases: List[Dict[str, Any]] = Field(description="Development phases", default_factory=list)
    milestones: List[Dict[str, Any]] = Field(description="Project milestones", default_factory=list)
    timeline_risks: List[Dict[str, Any]] = Field(description="Timeline risks", default_factory=list)
    metadata: Dict[str, Any] = Field(description="Timeline metadata", default_factory=dict)

class ComprehensiveImplementationPlanOutput(BaseModel):
    """
    A comprehensive, single-object output for the implementation planning phase.
    """
    plan: ImplementationPlan = Field(description="The detailed implementation plan.")
    summary: str = Field(description="A high-level summary of the plan.")
    metadata: PlanMetadata = Field(description="Metadata about the plan generation.")

class DevelopmentPhase(BaseModel):
    name: str = Field(description="The name of the development phase (e.g., Backend API, Frontend UI).")
    description: str = Field(description="A detailed description of what will be built in this phase.")
    deliverables: List[str] = Field(description="A list of specific outcomes or files to be produced.")
    estimated_duration_hours: float = Field(default=0.0, description="Estimated time in hours to complete the phase.")

class WorkItem(BaseModel):
    """A single, actionable work item for a specialist agent."""
    id: str = Field(description="A unique identifier for the work item (e.g., 'BE-001', 'FE-001').")
    description: str = Field(description="A clear and concise description of the task for a developer agent.")
    dependencies: List[str] = Field(default_factory=list, description="A list of other work item IDs that must be completed first.")
    estimated_time: str = Field(..., description="Estimated time to complete the work item (e.g., '2 hours', '1 day').") # Added estimated_time
    agent_role: str = Field(description="The role of the specialist agent required (e.g., 'backend_developer', 'frontend_developer', 'database_specialist').")
    acceptance_criteria: List[str] = Field(description="A checklist of criteria that must be met for the task to be considered complete. Used to guide unit test generation.")
    status: str = Field(default="pending", description="The current status of the work item (e.g., pending, in_progress, completed, failed).")
    code_files: List[str] = Field(default_factory=list, description="A list of file paths that are expected to be created or modified by this work item.")

class WorkItemBacklog(BaseModel):
    """A comprehensive backlog of work items representing the entire project plan."""
    work_items: List[WorkItem] = Field(description="The full list of work items required to complete the project.")
    summary: str = Field(description="A high-level summary of the project's development plan and strategy.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata about the plan, such as estimated total time, risk assessment, etc.")

# New model to store the selected tech stack by the user
class SelectedTechStack(BaseModel):
    frontend: Optional[TechStackComponent] = Field(None, description="The user's selected frontend technology.")
    backend: Optional[TechStackComponent] = Field(None, description="The user's selected backend technology.")
    database: Optional[TechStackComponent] = Field(None, description="The user's selected database technology.")
    cloud: Optional[TechStackComponent] = Field(None, description="The user's selected cloud platform.")
    architecture: Optional[ArchitecturePatternOption] = Field(None, description="The user's selected architecture pattern.")
    tools: Optional[List[TechStackComponent]] = Field(default_factory=list, description="The user's selected additional tools.")
    risks: Optional[List[TechRisk]] = Field(default_factory=list, description="Risks associated with the selected stack.")

class ComprehensiveTechStackOutput(BaseModel):
    """
    Defines the complete, structured output for the comprehensive tech stack recommendation.
    This ensures a predictable and reliable response from the LLM.
    """
    frontend_options: List[TechStackComponent] = Field(default_factory=list, description="Ranked options for frontend frameworks and languages.")
    backend_options: List[TechStackComponent] = Field(default_factory=list, description="Ranked options for backend frameworks and languages.")
    database_options: List[TechStackComponent] = Field(default_factory=list, description="Ranked options for database technologies.")
    cloud_options: List[TechStackComponent] = Field(default_factory=list, description="Ranked options for cloud platforms.")
    architecture_options: List[ArchitecturePatternOption] = Field(default_factory=list, description="Ranked options for architecture patterns.")
    tool_options: List[TechStackComponent] = Field(default_factory=list, description="Ranked options for additional tools.")
    risks: List[TechRisk] = Field(default_factory=list, description="Potential risks associated with the recommended stack.")
    synthesis: Optional[TechStackSynthesisOutput] = Field(None, description="The initial synthesized tech stack recommendation (can be null if options are provided). ")
    selected_stack: Optional[SelectedTechStack] = Field(None, description="The user's final selection of the tech stack components.")
