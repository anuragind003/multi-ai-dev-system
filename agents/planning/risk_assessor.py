"""
Risk Assessor Agent - Specialized in identifying and assessing project risks
with comprehensive risk categorization and mitigation planning.
"""

import json
import logging
logger = logging.getLogger(__name__)
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.retrievers import BaseRetriever
from langchain_core.output_parsers import PydanticOutputParser

# MODIFIED: Fix import paths - use absolute imports instead of relative imports
import os
import sys
# Add project root to Python path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
from agents.base_agent import BaseAgent
import monitoring
from tools.code_execution_tool import CodeExecutionTool
from message_bus import MessageBus
from agent_temperatures import get_agent_temperature
from multi_ai_dev_system.tools.json_handler import JsonHandler

from agents.models import (
    RiskAssessmentOutput,
    RiskAssessmentInput,
    ExecutiveSummaryRisk,
    RiskSummary,
    AnalyzedRisk,
    MonitoringRecommendation
)

class RiskAssessorAgent(BaseAgent):
    """
    Enhanced Risk Assessor Agent with comprehensive risk analysis capabilities.
    
    This agent performs risk identification, analysis, and mitigation planning,
    providing a complete risk assessment for software development projects.
    
    Uses temperature 0.3 for balanced analytical assessment with creative risk identification.
    """
    
    def __init__(self, llm: BaseLanguageModel, memory, temperature: float = None, rag_retriever: Optional[BaseRetriever] = None):
        # If no specific temperature provided, get from settings
        if temperature is None:
            temperature = get_agent_temperature("Risk Assessor Agent", 0.3)
            
        super().__init__(
            llm=llm,
            memory=memory,
            agent_name="Risk Assessor Agent",
            temperature=temperature,
            rag_retriever=rag_retriever
        )
        
        # Initialize prompt template
        self._initialize_prompt_template()
        
        # Initialize Pydantic output parser
        self.risk_assessment_parser = PydanticOutputParser(pydantic_object=RiskAssessmentOutput)
    
    def _initialize_prompt_template(self):
        """Initialize a comprehensive prompt template for risk assessment with Pydantic format instructions."""
        # Single comprehensive prompt template that covers all risk assessment aspects
        self.prompt_template = ChatPromptTemplate.from_messages([
            SystemMessage(content="""
                You are an Expert Risk Assessment Specialist for software development projects.
                
                Your task is to provide a comprehensive risk assessment based on project analysis, 
                timeline estimation, requirements, and technology stack. Your assessment should be 
                thorough, objective, and actionable, identifying risks across multiple categories.
                
                RISK CATEGORIES TO CONSIDER:
                1. Technical risks: Technology stack, architecture, performance, security
                2. Schedule risks: Timeline feasibility, dependencies, milestone challenges
                3. Resource risks: Skill availability, team expertise, resource constraints
                4. Requirements risks: Requirements clarity, scope creep, changing requirements
                5. External dependency risks: Third-party services, vendors, external systems
                6. Integration risks: System interfaces, data exchange, compatibility issues
                7. Security & compliance risks: Vulnerabilities, data protection, regulations
                8. Operational risks: Deployment, monitoring, maintenance challenges
                
                For EACH risk, assess:
                - Severity (High/Medium/Low)
                - Probability (High/Medium/Low)
                - Business impact
                - Risk score (1-10)
                - Mitigation strategies
                
                Provide your assessment in a structured format following the exact schema provided.
            """),
            HumanMessage(content="""
                Perform a comprehensive risk assessment for this software project:
                
                PROJECT ANALYSIS:
                {project_analysis}
                
                TIMELINE ESTIMATION:
                {timeline_estimation}
                
                REQUIREMENTS ANALYSIS:
                {requirements_analysis}
                
                TECHNOLOGY STACK:
                {tech_stack}
                
                Identify all project risks across multiple categories, analyze their severity and probability,
                prioritize risks, and provide mitigation recommendations.
                
                Follow this exact format:
                {format_instructions}
            """)
        ])
    
    def get_default_response(self) -> Dict[str, Any]:
        """
        Returns a default risk assessment structure if the LLM call fails.
        Creates a valid RiskAssessmentOutput instance.
        """
        # Create default using Pydantic models
        default_assessment = RiskAssessmentOutput(
            executive_summary=ExecutiveSummaryRisk(
                overall_risk_level="Medium",
                critical_risk_count=1,
                key_risk_areas=["Technical", "Schedule", "Resource"],
                mitigation_readiness="Low",
                risk_management_recommendation="Implement risk monitoring and mitigation planning process"
            ),
            project_risks=[
                AnalyzedRisk(
                    risk_id="R001",
                    category="Technical Risk",
                    description="Technology stack complexity may lead to integration issues",
                    severity="Medium",
                    probability="Medium",
                    impact="Potential delays and quality issues in development",
                    risk_score=6,
                    justification="Default risk due to processing error"
                ),
                AnalyzedRisk(
                    risk_id="R002",
                    category="Schedule Risk",
                    description="Timeline may be insufficient for implementation requirements",
                    severity="High",
                    probability="Medium",
                    impact="Project delays and potential scope reduction",
                    risk_score=8,
                    justification="Default risk due to processing error"
                )
            ],
            high_priority_risks=["R002"],
            risk_summary=RiskSummary(
                total_risks=2,
                high_severity=1,
                medium_severity=1,
                low_severity=0,
                overall_risk_assessment="Medium"
            ),
            monitoring_recommendations=[
                MonitoringRecommendation(
                    risk_area="Technical Risks",
                    monitoring_frequency="Weekly",
                    key_metrics=["Integration test results", "Code quality metrics"],
                    responsible_role="Technical Lead"
                ),
                MonitoringRecommendation(
                    risk_area="Schedule Risks",
                    monitoring_frequency="Weekly",
                    key_metrics=["Sprint velocity", "Milestone status"],
                    responsible_role="Project Manager"
                )
            ],
            assessment_metadata={
                "generated_at": datetime.now().isoformat(),
                "generation_method": "default_fallback",
                "confidence_level": "low"
            }
        )
        
        self.log_warning("Using default risk assessment response due to processing failure")
        return default_assessment.dict()
    
    def run(self, project_analysis: Dict[str, Any], 
        timeline_estimation: Dict[str, Any] = None, 
        requirements_analysis: Dict[str, Any] = None,
        tech_stack_recommendation: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute comprehensive risk assessment process in a single step.
        
        Args:
            project_analysis: Project complexity and feasibility analysis
            timeline_estimation: Timeline estimates and milestones
            requirements_analysis: Structured BRD analysis
            tech_stack_recommendation: Technology stack recommendation
            
        Returns:
            Dict containing comprehensive risk assessment
        """
        # Start with log info
        self.log_start(f"Starting comprehensive risk assessment with temperature {self.default_temperature}")
        
        try:
            # Validate input using Pydantic model
            try:
                input_data = RiskAssessmentInput(
                    project_analysis=project_analysis,
                    timeline_estimation=timeline_estimation,
                    requirements_analysis=requirements_analysis,
                    tech_stack_recommendation=tech_stack_recommendation
                )
            except Exception as e:
                self.log_warning(f"Input validation error: {e}, using sanitized input")
                # Create sanitized input if validation fails
                input_data = RiskAssessmentInput(
                    project_analysis=project_analysis if isinstance(project_analysis, dict) else {},
                    timeline_estimation=timeline_estimation if isinstance(timeline_estimation, dict) else None,
                    requirements_analysis=requirements_analysis if isinstance(requirements_analysis, dict) else None,
                    tech_stack_recommendation=tech_stack_recommendation if isinstance(tech_stack_recommendation, dict) else None
                )
            
            # Safely serialize inputs to JSON (with error handling)
            project_analysis_json = "{}"
            timeline_json = "{}"
            requirements_json = "{}"
            tech_stack_json = "{}"
            
            try:
                if isinstance(input_data.project_analysis, dict):
                    project_analysis_json = json.dumps(input_data.project_analysis, indent=2)
            except Exception as e:
                self.log_warning(f"Failed to serialize project analysis: {str(e)}")
                
            try:
                if input_data.timeline_estimation and isinstance(input_data.timeline_estimation, dict):
                    timeline_json = json.dumps(input_data.timeline_estimation, indent=2)
            except Exception as e:
                self.log_warning(f"Failed to serialize timeline estimation: {str(e)}")
                
            try:
                if input_data.requirements_analysis and isinstance(input_data.requirements_analysis, dict):
                    requirements_json = json.dumps(input_data.requirements_analysis, indent=2)
            except Exception as e:
                self.log_warning(f"Failed to serialize requirements analysis: {str(e)}")
                
            try:
                if input_data.tech_stack_recommendation and isinstance(input_data.tech_stack_recommendation, dict):
                    tech_stack_json = json.dumps(input_data.tech_stack_recommendation, indent=2)
            except Exception as e:
                self.log_warning(f"Failed to serialize tech stack recommendation: {str(e)}")
            
            # Execute the LLM chain with Pydantic output model
            risk_assessment = self.execute_llm_chain(
                inputs={
                    "project_analysis": project_analysis_json,
                    "timeline_estimation": timeline_json,
                    "requirements_analysis": requirements_json,
                    "tech_stack": tech_stack_json
                },
                output_pydantic_model=RiskAssessmentOutput,
                additional_llm_params={"max_tokens": 4096}
            )
            
            # Add metadata if not present
            if isinstance(risk_assessment, dict) and "assessment_metadata" not in risk_assessment:
                risk_assessment["assessment_metadata"] = {
                    "generated_at": datetime.now().isoformat(),
                    "assessment_approach": "comprehensive_analysis",
                    "confidence_level": "high"
                }
            
            # Log execution summary
            self.log_execution_summary(risk_assessment)
            
            # Log success
            self.log_success("Comprehensive risk assessment completed successfully with structured output")
            return risk_assessment
            
        except Exception as e:
            self.log_error(f"Risk assessment failed: {str(e)}")
            import traceback
            self.log_error(traceback.format_exc())
            return self.get_default_response()
    
    def log_execution_summary(self, result: Dict[str, Any]) -> None:
        """Log an execution summary of the risk assessment."""
        try:
            # Extract summary metrics
            risk_count = 0
            high_priority_count = 0
            risk_level = "Unknown"
            
            if "project_risks" in result:
                risk_count = len(result["project_risks"])
                
            if "high_priority_risks" in result:
                high_priority_count = len(result["high_priority_risks"])
                
            if "executive_summary" in result and isinstance(result["executive_summary"], dict):
                risk_level = result["executive_summary"].get("overall_risk_level", "Unknown")
                
            # Log summary
            self.log_info(f"──────────────────────────────────────────")
            self.log_info(f"🔍 RISK ASSESSMENT EXECUTION SUMMARY")
            self.log_info(f"──────────────────────────────────────────")
            self.log_info(f"📊 Overall Risk Level: {risk_level}")
            self.log_info(f"🔢 Total Risks Identified: {risk_count}")
            self.log_info(f"⚠️ High Priority Risks: {high_priority_count}")
            
            # Log completion timestamp
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.log_info(f"✅ Assessment Completed: {now}")
            self.log_info(f"──────────────────────────────────────────")
            
        except Exception as e:
            self.log_warning(f"Failed to log execution summary: {e}")
    
    def _extract_domain(self, requirements_analysis: Dict[str, Any]) -> str:
        """Extract project domain from requirements analysis."""
        try:
            if not requirements_analysis:
                return "general software"
                
            # Try direct domain field
            if "domain" in requirements_analysis:
                return requirements_analysis["domain"]
                
            # Try business context
            if "business_context" in requirements_analysis and requirements_analysis["business_context"]:
                # Use first 100 chars of business context for RAG retrieval
                return requirements_analysis["business_context"][:100]
                
            # Try project summary
            if "project_summary" in requirements_analysis and requirements_analysis["project_summary"]:
                return requirements_analysis["project_summary"][:100]
                
            return "general software"
            
        except Exception:
            return "general software"

    def _extract_main_technology(self, tech_stack_recommendation: Dict[str, Any]) -> str:
        """Extract main technology from tech stack recommendation."""
        try:
            if not tech_stack_recommendation:
                return "general technology"
                
            # Try to get the main technology stack
            tech_keywords = []
            
            if "recommended_stack" in tech_stack_recommendation and isinstance(tech_stack_recommendation["recommended_stack"], dict):
                # First try to get backend framework as it's often most relevant for risks
                if "backend" in tech_stack_recommendation["recommended_stack"]:
                    backend = tech_stack_recommendation["recommended_stack"]["backend"]
                    if isinstance(backend, list) and len(backend) > 0:
                        first_tech = backend[0]
                        if isinstance(first_tech, str):
                            tech_keywords.append(first_tech)
                        elif isinstance(first_tech, dict) and "name" in first_tech:
                            tech_keywords.append(first_tech["name"])
                
                # Try to get database 
                if "database" in tech_stack_recommendation["recommended_stack"]:
                    database = tech_stack_recommendation["recommended_stack"]["database"]
                    if isinstance(database, list) and len(database) > 0:
                        first_db = database[0]
                        if isinstance(first_db, str):
                            tech_keywords.append(first_db)
                        elif isinstance(first_db, dict) and "name" in first_db:
                            tech_keywords.append(first_db["name"])
            
            # If we have extracted technologies, join them
            if tech_keywords:
                return ", ".join(tech_keywords)
                
            return "general technology"
            
        except Exception:
            return "general technology"