"""
Pydantic models defining the standardized input and output schemas for all agents.
These models serve as the single source of truth for data contracts between agents.
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

# ======== BRD Analyst Models ========

class RequirementModel(BaseModel):
    """Model for structured requirements extracted from BRD."""
    id: str = Field(description="Unique identifier for requirement")
    title: str = Field(description="Short descriptive title")
    category: str = Field(description="Category (functional, non-functional, business, technical)")
    priority: str = Field(description="Priority level (high, medium, low)")
    description: str = Field(description="Detailed description")
    acceptance_criteria: List[str] = Field(description="Acceptance criteria")
    dependencies: List[str] = Field(description="Dependencies", default_factory=list)
    stakeholders: List[str] = Field(description="Stakeholders", default_factory=list)


class BRDRequirementsAnalysis(BaseModel):
    """Complete analysis of Business Requirements Document."""
    project_name: str = Field(description="Project name")
    project_summary: str = Field(description="Brief project summary")
    project_goals: List[str] = Field(description="Primary goals")
    target_audience: List[str] = Field(description="Target users")
    business_context: str = Field(description="Business context")
    requirements: List[RequirementModel] = Field(description="Structured requirements")
    constraints: List[str] = Field(description="Constraints")
    assumptions: List[str] = Field(description="Key assumptions")
    risks: List[Dict[str, Any]] = Field(description="Identified risks")
    domain_specific_details: Dict[str, Any] = Field(description="Domain-specific information")
    # Add quality assessment and gap analysis fields
    quality_assessment: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Quality assessment metrics and recommendations"
    )
    gap_analysis: Optional[Dict[str, Any]] = Field(
        default_factory=dict, 
        description="Analysis of gaps, ambiguities and implementation risks"
    )


class BrdAnalysisInput(BaseModel):
    """Input schema for BRD Analyst Agent."""
    raw_brd: str = Field(
        description="Raw text content of the Business Requirements Document"
    )
    max_tokens: Optional[int] = Field(
        default=None,
        description="Optional max token limit for analysis"
    )
    focus_areas: Optional[List[str]] = Field(
        default_factory=list,
        description="Optional areas to focus analysis on"
    )

# ======== Code Quality Models ========

class CodeIssue(BaseModel):
    """Model for a specific code issue found during analysis."""
    file: str = Field(description="Path to the file containing the issue")
    issue: str = Field(description="Description of the identified issue")
    severity: str = Field(description="Issue severity (Critical, High, Medium, Low)")
    line_number: Optional[int] = Field(None, description="Line number where the issue occurs")
    fix: Optional[str] = Field(None, description="Suggested fix for the issue")
    
class SecurityVulnerability(BaseModel):
    """Model for security vulnerabilities identified in code."""
    vulnerability_type: str = Field(description="Type of security vulnerability")
    location: str = Field(description="File or component where vulnerability was found")
    description: str = Field(description="Detailed description of the vulnerability")
    severity: str = Field(description="Vulnerability severity (Critical, High, Medium, Low)")
    impact: Optional[str] = Field(None, description="Potential impact if exploited")
    remediation: Optional[str] = Field(None, description="Recommended remediation steps")
    
class CodeStructureAnalysis(BaseModel):
    """Analysis of code structure and organization."""
    organization: str = Field(description="Assessment of codebase organization")
    modularity: str = Field(description="Assessment of code modularity")
    reusability: str = Field(description="Assessment of component reusability")
    coupling_score: Optional[float] = Field(None, description="Score for code coupling (0-10)")
    cohesion_score: Optional[float] = Field(None, description="Score for code cohesion (0-10)")
    improvement_areas: List[str] = Field(default_factory=list, description="Areas for structural improvement")

class CodeStandardsCompliance(BaseModel):
    """Analysis of compliance with coding standards."""
    naming_conventions: str = Field(description="Assessment of naming convention usage")
    documentation: str = Field(description="Assessment of code documentation")
    formatting: str = Field(description="Assessment of code formatting")
    standards_score: Optional[float] = Field(None, description="Overall standards compliance score (0-10)")
    specific_violations: List[str] = Field(default_factory=list, description="Specific standard violations")

class PerformanceAnalysis(BaseModel):
    """Analysis of code performance characteristics."""
    efficiency: str = Field(description="Assessment of code efficiency")
    scalability: str = Field(description="Assessment of code scalability")
    optimization_score: Optional[float] = Field(None, description="Performance optimization score (0-10)")
    optimization_suggestions: List[str] = Field(default_factory=list, description="Suggestions for optimization")

class CodeQualityAnalysisOutput(BaseModel):
    """Comprehensive code quality analysis output."""
    overall_quality_score: float = Field(description="Overall code quality score (0-10)")
    has_critical_issues: bool = Field(description="Whether critical issues were found")
    code_structure_analysis: CodeStructureAnalysis = Field(description="Analysis of code structure")
    code_standards_compliance: CodeStandardsCompliance = Field(description="Analysis of coding standards compliance")
    security_analysis: Dict[str, Any] = Field(description="Security vulnerability analysis")
    performance_analysis: PerformanceAnalysis = Field(description="Performance analysis")
    specific_issues: List[CodeIssue] = Field(default_factory=list, description="List of specific identified issues")
    recommendations: List[str] = Field(default_factory=list, description="Overall recommendations")
    quick_wins: Optional[List[str]] = Field(None, description="Quick and easy improvements")
    prioritized_recommendations: Optional[List[Dict[str, Any]]] = Field(None, description="Prioritized recommendations")
    execution_metrics: Optional[Dict[str, Any]] = Field(None, description="Execution time metrics")
    status: str = Field("success", description="Analysis execution status")

class CodeQualityAnalysisInput(BaseModel):
    """Input for comprehensive code quality analysis."""
    code_generation_result: Dict[str, Any] = Field(description="Result from code generation containing file content")
    tech_stack_recommendation: Dict[str, Any] = Field(description="Technology stack information")
    file_limit: Optional[int] = Field(None, description="Optional limit to number of files to analyze")
    focus_areas: Optional[List[str]] = Field(None, description="Optional specific areas to focus analysis on")

class CodeQualityReviewOutput(BaseModel):
    """Output for code quality review."""
    approved: bool = Field(description="Whether the code passes quality review")
    suggestions: List[str] = Field(description="Improvement suggestions")
    critical_issues: List[Dict[str, Any]] = Field(default_factory=list, description="Critical issues that must be fixed")
    review_score: Optional[float] = Field(None, description="Review score (0-10)")

class CodeQualityReviewInput(BaseModel):
    """Input for code quality review."""
    generated_code: Dict[str, Any] = Field(description="Generated code with file contents")
    tech_stack: Optional[Dict[str, Any]] = Field(None, description="Technology stack information")
    code_type: str = Field("general", description="Type of code being reviewed (backend, frontend, database)")
    review_criteria: Optional[List[str]] = Field(None, description="Optional specific criteria to focus review on")

# ======== Project Analyzer Models ========

class ComplexityFactor(BaseModel):
    """Model for a specific factor contributing to project complexity."""
    factor: str = Field(description="Name of the complexity factor")
    complexity: str = Field(description="Level of complexity (low, medium, high)")
    justification: str = Field(description="Justification for complexity rating")
    score: Optional[int] = Field(None, description="Numeric complexity score (1-10)")

class ComplexityAnalysisOutput(BaseModel):
    """Model for project complexity analysis output."""
    overall_complexity: str = Field(description="Overall complexity level")
    technical_complexity: str = Field(description="Technical complexity level")
    business_complexity: str = Field(description="Business complexity level")
    integration_complexity: str = Field(description="Integration complexity level")
    factors: List[ComplexityFactor] = Field(description="Specific complexity factors")
    complexity_score: Optional[float] = Field(None, description="Overall numeric complexity score (1-10)")

class TeamMember(BaseModel):
    """Model for team composition requirements."""
    role: str = Field(description="Team member role")
    count: int = Field(description="Number of resources needed")
    key_responsibilities: Optional[List[str]] = Field(None, description="Key responsibilities")

class SkillRequirement(BaseModel):
    """Model for skill requirements in project."""
    skill: str = Field(description="Required skill name")
    proficiency: str = Field(description="Required proficiency level")
    justification: Optional[str] = Field(None, description="Why this skill is needed")

class PhaseAllocation(BaseModel):
    """Model for resource allocation by project phase."""
    developer_days: int = Field(description="Developer days required")
    team_composition: Optional[List[Dict[str, Any]]] = Field(None, description="Team composition for phase")
    key_activities: Optional[List[str]] = Field(None, description="Key activities in this phase")

class ResourceAnalysisOutput(BaseModel):
    """Model for project resource analysis output."""
    team_composition: List[TeamMember] = Field(description="Required team composition")
    skills_matrix: List[SkillRequirement] = Field(description="Required skills and proficiency levels")
    phase_allocation: Dict[str, PhaseAllocation] = Field(description="Resource allocation by phase")
    external_dependencies: List[str] = Field(default_factory=list, description="External dependencies or resources")
    total_effort_days: Optional[int] = Field(None, description="Total estimated effort in developer days")
    total_team_size: Optional[int] = Field(None, description="Total team size recommendation")

class DurationEstimates(BaseModel):
    """Model for project duration estimates."""
    best_case: str = Field(description="Best case duration estimate")
    likely_case: str = Field(description="Most likely duration estimate")
    worst_case: str = Field(description="Worst case duration estimate")

class Milestone(BaseModel):
    """Model for project milestone."""
    name: str = Field(description="Milestone name")
    timeline: str = Field(description="Expected timeline (e.g., 'Week 4')")
    deliverables: Optional[List[str]] = Field(None, description="Key deliverables")

class TimelineRisk(BaseModel):
    """Model for risks affecting project timeline."""
    risk: str = Field(description="Timeline risk description")
    impact: str = Field(description="Impact level (Low, Medium, High)")
    mitigation: str = Field(description="Mitigation strategy")

class TimelineFeasibilityOutput(BaseModel):
    """Model for timeline feasibility analysis output."""
    duration_estimates: DurationEstimates = Field(description="Duration estimates")
    key_milestones: List[Milestone] = Field(description="Key project milestones")
    critical_path: List[str] = Field(description="Components on the critical path")
    timeline_risks: List[TimelineRisk] = Field(description="Timeline-related risks")
    optimization_recommendations: Optional[List[str]] = Field(None, description="Timeline optimization recommendations")

class ScopeCoverage(BaseModel):
    """Model for scope coverage assessment."""
    functional_requirements: str = Field(description="Functional requirements coverage")
    non_functional_requirements: str = Field(description="Non-functional requirements coverage")
    completeness_percentage: int = Field(description="Overall completeness percentage")

class ScopeGap(BaseModel):
    """Model for identified scope gap."""
    gap: str = Field(description="Description of the gap")
    severity: str = Field(description="Severity (Low, Medium, High)")
    recommendation: str = Field(description="Recommendation to address the gap")

class ScopeVerificationOutput(BaseModel):
    """Model for scope verification output."""
    scope_coverage: ScopeCoverage = Field(description="Scope coverage assessment")
    identified_gaps: List[ScopeGap] = Field(description="Identified gaps in scope")
    ambiguities: List[str] = Field(description="Ambiguities in requirements or design")
    scope_recommendations: List[str] = Field(description="Recommendations for scope management")

class ExecutiveSummary(BaseModel):
    """Model for executive summary of project analysis."""
    project_complexity: str = Field(description="Project complexity rating")
    resource_needs: str = Field(description="Resource needs summary")
    estimated_duration: str = Field(description="Estimated project duration")
    scope_completeness: str = Field(description="Scope completeness percentage")
    key_finding: str = Field(description="Key finding from analysis")

class RiskWithMitigation(BaseModel):
    """Model for project risk with mitigation strategy."""
    risk: str = Field(description="Risk description")
    mitigation: str = Field(description="Mitigation strategy")

class ResourceRecommendations(BaseModel):
    """Model for resource recommendations."""
    team_size: int = Field(description="Recommended team size")
    expertise_level: str = Field(description="Required expertise level")
    key_skills_needed: List[str] = Field(description="Key skills needed")

class TimelineRecommendation(BaseModel):
    """Model for timeline recommendations."""
    duration: str = Field(description="Recommended project duration")
    phasing: str = Field(description="Recommended project phasing")
    buffer: Optional[str] = Field(None, description="Recommended time buffer")

class ProjectAnalysisOutput(BaseModel):
    """Comprehensive project analysis output model."""
    executive_summary: ExecutiveSummary = Field(description="Executive summary with key findings")
    project_viability: str = Field(description="Overall project viability assessment")
    critical_success_factors: List[str] = Field(description="Critical success factors")
    recommended_approach: str = Field(description="Recommended implementation approach")
    top_risks: List[RiskWithMitigation] = Field(description="Top risks with mitigation strategies")
    resource_recommendations: ResourceRecommendations = Field(description="Resource recommendations")
    timeline_recommendation: TimelineRecommendation = Field(description="Timeline recommendations")
    analysis_metadata: Optional[Dict[str, Any]] = Field(None, description="Analysis metadata")

class ProjectAnalysisInput(BaseModel):
    """Input model for project analysis."""
    requirements_analysis: Dict[str, Any] = Field(description="Analyzed project requirements")
    tech_stack_recommendation: Dict[str, Any] = Field(description="Recommended technology stack")
    system_design: Dict[str, Any] = Field(description="System design specifications")

# ======== Risk Assessor Models ========

class Risk(BaseModel):
    """Model for an identified project risk."""
    risk_id: str = Field(description="Unique identifier for the risk")
    category: str = Field(description="Risk category (Technical, Schedule, Resource, etc.)")
    description: str = Field(description="Detailed description of the risk")
    affected_areas: List[str] = Field(description="Areas of the project affected by this risk")

class RiskIdentificationOutput(BaseModel):
    """Output from the risk identification stage."""
    risks: List[Risk] = Field(description="List of identified risks")
    
class AnalyzedRisk(BaseModel):
    """Model for an analyzed risk with severity and impact assessment."""
    risk_id: str = Field(description="Unique identifier for the risk")
    category: str = Field(description="Risk category")
    description: str = Field(description="Detailed description of the risk")
    severity: str = Field(description="Risk severity (High, Medium, Low)")
    probability: str = Field(description="Risk probability (High, Medium, Low)")
    impact: str = Field(description="Business impact description")
    risk_score: int = Field(description="Numerical risk score (1-10)")
    justification: Optional[str] = Field(None, description="Justification for risk assessment")

class RiskAnalysisOutput(BaseModel):
    """Output from the risk analysis stage."""
    analyzed_risks: List[AnalyzedRisk] = Field(description="List of analyzed risks")

class MitigationStrategy(BaseModel):
    """Model for risk mitigation strategy."""
    risk_id: str = Field(description="Risk ID this strategy applies to")
    preventive_actions: List[str] = Field(description="Actions to prevent risk occurrence")
    detective_measures: List[str] = Field(description="Measures to detect risk early")
    corrective_actions: List[str] = Field(description="Actions to take if risk occurs")
    responsible_role: str = Field(description="Role responsible for this mitigation")
    required_resources: List[str] = Field(description="Resources needed for mitigation")

class MitigationStrategiesOutput(BaseModel):
    """Output from the mitigation strategy stage."""
    mitigation_strategies: List[MitigationStrategy] = Field(description="List of mitigation strategies")

class RiskMatrix(BaseModel):
    """Model for risk matrix categorizing risks by impact and probability."""
    high_impact_high_probability: List[str] = Field(description="Critical risks (high impact, high probability)")
    high_impact_medium_probability: List[str] = Field(description="High impact, medium probability risks")
    high_impact_low_probability: List[str] = Field(description="High impact, low probability risks")
    medium_impact_high_probability: List[str] = Field(description="Medium impact, high probability risks")
    medium_impact_medium_probability: List[str] = Field(description="Medium impact, medium probability risks")
    medium_impact_low_probability: List[str] = Field(description="Medium impact, low probability risks")
    low_impact_high_probability: List[str] = Field(description="Low impact, high probability risks")
    low_impact_medium_probability: List[str] = Field(description="Low impact, medium probability risks")
    low_impact_low_probability: List[str] = Field(description="Lowest priority risks")
    category_criticality: Optional[Dict[str, str]] = Field(None, description="Criticality assessment for each category")

class HighPriorityRisksOutput(BaseModel):
    """Output model for high priority risks extraction."""
    high_priority_risks: List[AnalyzedRisk] = Field(description="List of high priority risks")

class TimelineBudgetImpact(BaseModel):
    """Model for impact on timeline and budget."""
    timeline_delay: str = Field(description="Estimated timeline delay")
    budget_increase: str = Field(description="Estimated budget increase")
    mitigation_efficiency: Optional[str] = Field(None, description="Efficiency of mitigation strategy")

class ContingencyPlan(BaseModel):
    """Model for a contingency plan for a high priority risk."""
    risk_id: str = Field(description="Risk ID this plan applies to")
    trigger_conditions: List[str] = Field(description="Conditions that trigger this contingency plan")
    contingency_actions: List[str] = Field(description="Actions to take when risk occurs")
    required_resources: List[str] = Field(description="Resources needed for contingency execution")
    communication_plan: List[str] = Field(description="Communication plan to stakeholders")
    recovery_steps: List[str] = Field(description="Steps to return to normal operations")
    timeline_budget_impact: TimelineBudgetImpact = Field(description="Impact on timeline and budget")

class ContingencyPlansOutput(BaseModel):
    """Output from the contingency planning stage."""
    contingency_plans: List[ContingencyPlan] = Field(description="List of contingency plans")

class ExecutiveSummaryRisk(BaseModel):
    """Model for risk executive summary."""
    overall_risk_level: str = Field(description="Overall risk level assessment")
    critical_risk_count: int = Field(description="Number of critical risks")
    key_risk_areas: List[str] = Field(description="Key risk areas identified")
    mitigation_readiness: str = Field(description="Mitigation readiness assessment")
    risk_management_recommendation: str = Field(description="Overall risk management recommendation")

class RiskSummary(BaseModel):
    """Summary statistics for identified risks."""
    total_risks: int = Field(description="Total number of risks")
    high_severity: int = Field(description="Number of high severity risks")
    medium_severity: int = Field(description="Number of medium severity risks")
    low_severity: int = Field(description="Number of low severity risks")
    overall_risk_assessment: str = Field(description="Overall risk assessment")

class MonitoringRecommendation(BaseModel):
    """Model for risk monitoring recommendation."""
    risk_area: str = Field(description="Risk area to monitor")
    monitoring_frequency: str = Field(description="Recommended monitoring frequency")
    key_metrics: List[str] = Field(description="Key metrics to track")
    responsible_role: str = Field(description="Role responsible for monitoring")

class RiskAssessmentOutput(BaseModel):
    """Comprehensive risk assessment output model."""
    executive_summary: ExecutiveSummaryRisk = Field(description="Executive summary of risk assessment")
    project_risks: List[AnalyzedRisk] = Field(description="List of all project risks with analysis")
    high_priority_risks: List[str] = Field(description="List of high priority risk IDs")
    risk_summary: RiskSummary = Field(description="Summary statistics for identified risks")
    monitoring_recommendations: List[MonitoringRecommendation] = Field(description="Risk monitoring recommendations")
    assessment_metadata: Optional[Dict[str, Any]] = Field(None, description="Assessment metadata")

class RiskAssessmentInput(BaseModel):
    """Input model for risk assessment."""
    project_analysis: Dict[str, Any] = Field(description="Project analysis data")
    timeline_estimation: Optional[Dict[str, Any]] = Field(None, description="Timeline estimation data")
    requirements_analysis: Optional[Dict[str, Any]] = Field(None, description="Requirements analysis data")
    tech_stack_recommendation: Optional[Dict[str, Any]] = Field(None, description="Tech stack recommendation data")

# ======== Timeline Estimator Models ========

class ProjectPhase(BaseModel):
    """Model for a single project phase."""
    phase_name: str = Field(description="Name of the project phase")
    purpose: str = Field(description="Purpose and objectives of this phase")
    key_activities: List[str] = Field(description="Key activities in this phase")
    dependencies: List[str] = Field(description="Dependencies on other phases", default_factory=list)
    deliverables: List[str] = Field(description="Main deliverables for this phase")
    required_skills: List[str] = Field(description="Required skills for this phase")

class PhaseDecompositionOutput(BaseModel):
    """Output from the phase decomposition stage."""
    phases: List[ProjectPhase] = Field(description="List of project phases")

class PhaseDurationEstimate(BaseModel):
    """Model for phase duration estimate."""
    phase_name: str = Field(description="Name of the project phase")
    duration_days: int = Field(description="Estimated duration in days")
    confidence: str = Field(description="Confidence level (High, Medium, Low)")
    factors: List[str] = Field(description="Factors affecting duration")
    recommended_buffer: str = Field(description="Recommended buffer (percentage or days)")
    resource_requirements: List[str] = Field(description="Required resources for this phase")

class DurationEstimatesOutput(BaseModel):
    """Output from the duration estimation stage."""
    phase_durations: List[PhaseDurationEstimate] = Field(description="Duration estimates for each phase")
    parallel_opportunities: Optional[List[Dict[str, Any]]] = Field(None, description="Opportunities for parallel execution")

class NearCriticalPath(BaseModel):
    """Model for near-critical path."""
    path: List[str] = Field(description="Sequence of phases in this path")
    float_days: int = Field(description="Float/slack days for this path")
    explanation: str = Field(description="Explanation of why this path could become critical")

class MonitoringPoint(BaseModel):
    """Model for critical path monitoring point."""
    phase: str = Field(description="Phase containing this monitoring point")
    milestone: str = Field(description="Milestone or checkpoint")
    reason: str = Field(description="Reason for monitoring")

class CriticalPathOutput(BaseModel):
    """Output from the critical path analysis stage."""
    critical_path: List[str] = Field(description="Sequence of phases in the critical path")
    critical_path_duration: int = Field(description="Duration of the critical path in days")
    critical_path_analysis: Dict[str, Any] = Field(description="Detailed critical path analysis")
    near_critical_paths: Optional[List[NearCriticalPath]] = Field(None, description="Paths that could become critical")
    monitoring_points: Optional[List[MonitoringPoint]] = Field(None, description="Key monitoring points")

class RoleAllocation(BaseModel):
    """Model for role allocation throughout the project."""
    role: str = Field(description="Role name")
    required_count: int = Field(description="Number of resources needed")
    skill_level: str = Field(description="Required skill level")
    allocation_percentage: Dict[str, int] = Field(description="Allocation percentage by phase")

class ResourceAllocationOutput(BaseModel):
    """Output from the resource allocation stage."""
    roles: List[RoleAllocation] = Field(description="Resource roles and allocations")
    resource_constraints: List[str] = Field(description="Resource constraints")
    bottlenecks: List[str] = Field(description="Resource bottlenecks")

class ProjectMilestone(BaseModel):
    """Model for project milestone."""
    name: str = Field(description="Milestone name")
    description: str = Field(description="Milestone description")
    phase_connection: Optional[str] = Field(None, description="Connected phase")
    acceptance_criteria: List[str] = Field(description="Acceptance criteria")
    stakeholders: Optional[List[str]] = Field(None, description="Relevant stakeholders")
    completion_percentage: Optional[int] = Field(None, description="Project completion percentage at milestone")

class MilestonesOutput(BaseModel):
    """Output from the milestone planning stage."""
    milestones: List[ProjectMilestone] = Field(description="Project milestones")

class TimelinePhase(BaseModel):
    """Model for a phase in the final timeline."""
    phase_name: str = Field(description="Name of the project phase")
    duration_days: int = Field(description="Duration in days")
    start_date: str = Field(description="Start date (YYYY-MM-DD)")
    end_date: str = Field(description="End date (YYYY-MM-DD)")
    resources_required: List[str] = Field(description="Required resources")
    dependencies: List[str] = Field(description="Phase dependencies")
    critical_path: bool = Field(description="Whether this phase is on the critical path")

class TimelineMilestone(BaseModel):
    """Model for a milestone in the final timeline."""
    name: str = Field(description="Milestone name")
    date: str = Field(description="Milestone date (YYYY-MM-DD)")
    description: str = Field(description="Milestone description")

class TimelineRisk(BaseModel):
    """Model for timeline risk."""
    risk: str = Field(description="Risk description")
    impact: str = Field(description="Impact level (High, Medium, Low)")
    mitigation: str = Field(description="Risk mitigation strategy")

class VisualizationPhase(BaseModel):
    """Model for timeline visualization phase data."""
    name: str = Field(description="Phase name")
    start: str = Field(description="Start date (YYYY-MM-DD)")
    end: str = Field(description="End date (YYYY-MM-DD)")
    progress: int = Field(description="Current progress percentage")

class VisualizationData(BaseModel):
    """Model for timeline visualization data."""
    phases: List[VisualizationPhase] = Field(description="Phase visualization data")
    milestones: List[Dict[str, str]] = Field(description="Milestone visualization data")

class ProjectTimelineSummary(BaseModel):
    """Model for project timeline summary."""
    start_date: str = Field(description="Project start date (YYYY-MM-DD)")
    end_date: str = Field(description="Project end date (YYYY-MM-DD)")
    estimated_duration_weeks: int = Field(description="Estimated duration in weeks")
    buffer_days: int = Field(description="Buffer days included")
    critical_path_duration: int = Field(description="Critical path duration in days")

class TimelineEstimationOutput(BaseModel):
    """Comprehensive timeline estimation output model."""
    project_timeline: ProjectTimelineSummary = Field(description="Project timeline summary")
    development_phases: List[TimelinePhase] = Field(description="Timeline phases with dates")
    milestones: List[TimelineMilestone] = Field(description="Project milestones with dates")
    timeline_risks: Optional[List[TimelineRisk]] = Field(None, description="Timeline-related risks")
    visualization_data: Optional[VisualizationData] = Field(None, description="Timeline visualization data")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Timeline metadata")

class TimelineEstimationInput(BaseModel):
    """Input model for timeline estimation."""
    project_analysis: Dict[str, Any] = Field(description="Project analysis data")
    requirements_analysis: Dict[str, Any] = Field(description="Requirements analysis data")
    system_design: Dict[str, Any] = Field(description="System design specifications")

# ======== Code Optimization Models ========

class CodeOptimizationResult(BaseModel):
    """Model for code optimization results."""
    optimized_code: str = Field(description="The optimized code content")
    improvements: List[Dict[str, str]] = Field(
        description="List of improvements made", 
        default_factory=list
    )
    summary: str = Field(description="Summary of optimizations performed")
    execution_time: Optional[float] = Field(None, description="Execution time in seconds")
    status: str = Field("success", description="Optimization status (success/error)")
    error: Optional[str] = Field(None, description="Error message if optimization failed")
    file_path: str = Field(description="Path to the file that was optimized")
    language: str = Field(description="Programming language of the file")

class TestValidationOutput(BaseModel):
    """Structured output for the TestValidationAgent."""
    passed: int = Field(description="Number of tests that passed.")
    failed: int = Field(description="Number of tests that failed.")
    skipped: int = Field(description="Number of tests that were skipped.")
    success_rate: float = Field(description="The percentage of tests that passed.")
    coverage_percentage: float = Field(description="The final code coverage percentage.")
    summary: str = Field(description="A high-level summary of the test results.")
    recommendations: List[str] = Field(description="Actionable recommendations for improvement.")
    issues: Optional[List[Dict[str, Any]]] = Field(None, description="Specific issues found in tests.")
    coverage_gaps: Optional[List[Dict[str, Any]]] = Field(None, description="Areas with insufficient test coverage.")
    status: str = Field("success", description="Status of the validation (success or error).")
    execution_time: float = Field(0.0, description="Time taken to execute and analyze tests.")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Timestamp of the validation.")