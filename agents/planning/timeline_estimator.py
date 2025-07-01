"""
Timeline Estimator Agent - Specialized in creating accurate timeline estimates
for software development projects with phase-based planning, critical path analysis,
resource allocation, and dependency management.
"""

import json
import logging
logger = logging.getLogger(__name__)
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from langchain_core.language_models import BaseLanguageModel
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.retrievers import BaseRetriever

# Import JsonHandler for robust JSON handling
from tools.json_handler import JsonHandler

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
from enhanced_memory_manager import create_memory_manager, EnhancedSharedProjectMemory
from rag_manager import get_rag_manager
from models.data_contracts import (
    TimelineEstimationOutput,
    TimelineEstimationInput
)

class TimelineEstimatorAgent(BaseAgent):
    """
    Enhanced Timeline Estimation Agent with comprehensive project scheduling capabilities.
    
    This agent analyzes project requirements, complexity, and system design to create:
    1. Detailed development phases with accurate duration estimates
    2. Critical path analysis with dependency mapping
    3. Resource allocation planning across project timeline
    4. Milestone identification and scheduling
    5. Risk-adjusted timelines with appropriate buffers
    
    Uses temperature 0.4 for balanced planning with creative insights.
    """
    
    def __init__(self, llm: BaseLanguageModel, memory, temperature: float = None, rag_retriever: Optional[BaseRetriever] = None):
        # If no specific temperature provided, get from settings
        if temperature is None:
            temperature = get_agent_temperature("Timeline Estimator Agent", 0.4)
            
        # Initialize base agent with the passed temperature
        super().__init__(
            llm=llm,
            memory=memory,
            agent_name="Timeline Estimator Agent",
            temperature=temperature,
            rag_retriever=rag_retriever
        )
        
        # Initialize enhanced memory
        self._init_enhanced_memory()

        # Initialize RAG context
        self.rag_manager = get_rag_manager()
        if self.rag_manager:
            self.logger.info("RAG manager available for timeline estimation patterns")
        else:
            self.logger.warning("RAG manager not available")
        
        # Initialize single comprehensive prompt template
        self._initialize_prompt_templates()
        
        # Initialize Pydantic output parser for final timeline validation
        self.timeline_parser = PydanticOutputParser(pydantic_object=TimelineEstimationOutput)
    
    def _initialize_prompt_templates(self):
        """Initialize a comprehensive prompt template for timeline estimation with Pydantic format instructions."""
        # Single comprehensive prompt template that covers all timeline estimation aspects
        self.prompt_template = ChatPromptTemplate.from_messages([
            SystemMessage(content="""
                You are an Expert Project Timeline Planner specializing in software development projects.
                
                Your task is to create a comprehensive project timeline estimation based on project analysis,
                requirements, and system design. The timeline should include development phases, 
                durations, dependencies, critical path analysis, resource allocation, and milestones.
                
                APPROACH:
                1. Break down the project into logical phases based on the system design
                2. Estimate realistic durations for each phase
                3. Identify phase dependencies and the critical path
                4. Determine resource requirements across phases
                5. Set meaningful project milestones
                6. Create a complete timeline with start and end dates
                
                KEY CONSIDERATIONS:
                - Phase dependencies and constraints
                - Technical complexity and implementation challenges
                - Resource availability and scheduling
                - Risk factors and appropriate buffers
                - Business priorities and stakeholder expectations
                
                Provide your timeline estimation in a structured format following the exact schema provided.
            """),
            HumanMessage(content="""
                Create a comprehensive project timeline estimation based on:
                
                PROJECT ANALYSIS:
                {project_analysis}
                
                REQUIREMENTS ANALYSIS:
                {requirements_analysis}
                
                SYSTEM DESIGN:
                {system_design}
                
                Starting today, create a complete timeline that includes:
                
                1. Project timeline overview (start date, end date, duration, buffer)
                2. Development phases with dates, durations, and dependencies
                3. Key milestones throughout the project
                4. Timeline risks that could impact the schedule
                5. Visualization data for timeline representation
                
                The output should account for realistic development pace, dependencies between components,
                and appropriate buffers for risk mitigation.
                
                Follow this exact format:
                {format_instructions}
            """)
        ])
    
    def get_default_response(self) -> Dict[str, Any]:
        """
        Returns a default timeline estimation response if the LLM call fails.
        Creates a valid TimelineEstimationOutput object.
        """
        # Generate default dates from current date
        current_date = datetime.now()
        start_date = current_date.strftime("%Y-%m-%d")
        end_date = (current_date + timedelta(days=60)).strftime("%Y-%m-%d")
        
        # Create default using Pydantic models
        default_timeline = TimelineEstimationOutput(
            project_timeline={
                "start_date": start_date,
                "end_date": end_date,
                "estimated_duration_weeks": 8,
                "buffer_days": 10,
                "critical_path_duration": 45
            },
            development_phases=[
                {
                    "phase_name": "Requirements Validation",
                    "duration_days": 5,
                    "start_date": start_date,
                    "end_date": (current_date + timedelta(days=5)).strftime("%Y-%m-%d"),
                    "resources_required": ["Business Analyst", "Project Manager"],
                    "dependencies": [],
                    "critical_path": True
                },
                {
                    "phase_name": "Architecture & Design",
                    "duration_days": 10,
                    "start_date": (current_date + timedelta(days=5)).strftime("%Y-%m-%d"),
                    "end_date": (current_date + timedelta(days=15)).strftime("%Y-%m-%d"),
                    "resources_required": ["Solution Architect", "Tech Lead"],
                    "dependencies": ["Requirements Validation"],
                    "critical_path": True
                },
                {
                    "phase_name": "Development",
                    "duration_days": 30,
                    "start_date": (current_date + timedelta(days=15)).strftime("%Y-%m-%d"),
                    "end_date": (current_date + timedelta(days=45)).strftime("%Y-%m-%d"),
                    "resources_required": ["Backend Developer", "Frontend Developer", "Database Developer"],
                    "dependencies": ["Architecture & Design"],
                    "critical_path": True
                },
                {
                    "phase_name": "Testing",
                    "duration_days": 10,
                    "start_date": (current_date + timedelta(days=45)).strftime("%Y-%m-%d"),
                    "end_date": (current_date + timedelta(days=55)).strftime("%Y-%m-%d"),
                    "resources_required": ["QA Engineer"],
                    "dependencies": ["Development"],
                    "critical_path": True
                },
                {
                    "phase_name": "Deployment",
                    "duration_days": 5,
                    "start_date": (current_date + timedelta(days=55)).strftime("%Y-%m-%d"),
                    "end_date": end_date,
                    "resources_required": ["DevOps Engineer", "System Administrator"],
                    "dependencies": ["Testing"],
                    "critical_path": True
                }
            ],
            milestones=[
                {
                    "name": "Project Start",
                    "date": start_date,
                    "description": "Project kickoff"
                },
                {
                    "name": "Design Approval",
                    "date": (current_date + timedelta(days=15)).strftime("%Y-%m-%d"),
                    "description": "Architecture and design approved"
                },
                {
                    "name": "Development Complete",
                    "date": (current_date + timedelta(days=45)).strftime("%Y-%m-%d"),
                    "description": "All development tasks completed"
                },
                {
                    "name": "Testing Complete",
                    "date": (current_date + timedelta(days=55)).strftime("%Y-%m-%d"),
                    "description": "All testing completed and defects fixed"
                },
                {
                    "name": "Project Delivered",
                    "date": end_date,
                    "description": "Project deployed to production"
                }
            ],
            timeline_risks=[
                {
                    "risk": "Resource unavailability",
                    "impact": "High",
                    "mitigation": "Secure resources in advance"
                },
                {
                    "risk": "Scope creep",
                    "impact": "Medium",
                    "mitigation": "Implement formal change control process"
                },
                {
                    "risk": "Technical challenges",
                    "impact": "Medium",
                    "mitigation": "Allocate additional buffer time for complex components"
                }
            ],
            metadata={
                "generated_at": datetime.now().isoformat(),
                "generation_method": "default_fallback",
                "confidence_level": "low"
            }
        )
        
        self.log_warning("Using default timeline estimation response due to processing failure")
        return default_timeline.dict()
    
    def run(self, project_analysis: Dict[str, Any], 
            requirements_analysis: Dict[str, Any], 
            system_design: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate comprehensive timeline estimation in a single step using structured output.
        Uses temperature 0.4 for balanced planning with creative insights.
        
        Args:
            project_analysis: The project complexity and scope analysis
            requirements_analysis: The structured requirements analysis
            system_design: The system design specifications
            
        Returns:
            Dict containing comprehensive timeline estimation with phases and milestones
        """
        self.log_start(f"Starting comprehensive timeline estimation with temperature {self.default_temperature}")
        
        try:
            # Validate input using Pydantic model
            try:
                input_data = TimelineEstimationInput(
                    project_analysis=project_analysis,
                    requirements_analysis=requirements_analysis,
                    system_design=system_design
                )
            except Exception as e:
                self.log_warning(f"Input validation error: {e}, using sanitized input")
                # Create sanitized input if validation fails
                input_data = TimelineEstimationInput(
                    project_analysis=project_analysis if isinstance(project_analysis, dict) else {},
                    requirements_analysis=requirements_analysis if isinstance(requirements_analysis, dict) else {},
                    system_design=system_design if isinstance(system_design, dict) else {}
                )
            
            # Safely serialize inputs to JSON (with error handling)
            project_analysis_json = "{}"
            requirements_json = "{}"
            system_design_json = "{}"
            
            try:
                if isinstance(input_data.project_analysis, dict):
                    project_analysis_json = json.dumps(input_data.project_analysis, indent=2)
            except Exception as e:
                self.log_warning(f"Failed to serialize project analysis: {str(e)}")
                
            try:
                if isinstance(input_data.requirements_analysis, dict):
                    requirements_json = json.dumps(input_data.requirements_analysis, indent=2)
            except Exception as e:
                self.log_warning(f"Failed to serialize requirements analysis: {str(e)}")
                
            try:
                if isinstance(input_data.system_design, dict):
                    system_design_json = json.dumps(input_data.system_design, indent=2)
            except Exception as e:
                self.log_warning(f"Failed to serialize system design: {str(e)}")
            
            # Get RAG context if available
            rag_context = ""
            if self.rag_retriever:
                domain = self._extract_domain(input_data.requirements_analysis)
                query = f"software development timeline estimation for {domain} projects"
                rag_context = self.get_rag_context(query)
                if rag_context:
                    self.log_info(f"Retrieved RAG context for timeline estimation in {domain} domain")
            
            # Execute the LLM chain with Pydantic output model
            timeline_estimation = self.execute_llm_chain(
                inputs={
                    "project_analysis": project_analysis_json,
                    "requirements_analysis": requirements_json,
                    "system_design": system_design_json
                },
                output_pydantic_model=TimelineEstimationOutput,
                additional_llm_params={"max_tokens": 4096}  # Timeline can be complex
            )
            
            # Add metadata if not present
            if isinstance(timeline_estimation, dict) and "metadata" not in timeline_estimation:
                timeline_estimation["metadata"] = {
                    "generated_at": datetime.now().isoformat(),
                    "estimation_approach": "comprehensive_single_step",
                    "confidence_level": "high"
                }
            
            # Store timeline estimation results in enhanced memory
            if isinstance(timeline_estimation, dict):
                timeline_summary = {
                    "estimated_duration_weeks": timeline_estimation.get("project_timeline", {}).get("estimated_duration_weeks", 0),
                    "total_phases": len(timeline_estimation.get("development_phases", [])),
                    "critical_path_duration": timeline_estimation.get("project_timeline", {}).get("critical_path_duration", 0),
                    "milestones_count": len(timeline_estimation.get("milestones", [])),
                    "estimation_timestamp": datetime.now().isoformat()
                }
                self.enhanced_set("timeline_estimation_summary", timeline_summary, context="timeline_estimation")
                self.store_cross_tool_data("timeline_estimation_results", timeline_estimation, 
                                         "Comprehensive timeline estimation results for project planning")
            
            # Log execution summary
            self.log_execution_summary(timeline_estimation)
            
            # Log success
            self.log_success("Comprehensive timeline estimation completed successfully with structured output")
            return timeline_estimation
            
        except Exception as e:
            self.log_error(f"Timeline estimation failed: {str(e)}")
            import traceback
            self.log_error(traceback.format_exc())
            return self.get_default_response()
    
    def _extract_domain(self, requirements_analysis: Dict[str, Any]) -> str:
        """Extract domain from requirements analysis."""
        domain = "software development"
        
        try:
            if not requirements_analysis:
                return domain
                
            # Try direct domain field
            if "domain" in requirements_analysis:
                return requirements_analysis["domain"]
                
            # Try project_overview.domain
            if "project_overview" in requirements_analysis:
                overview = requirements_analysis["project_overview"]
                if isinstance(overview, dict):
                    domain = overview.get("domain", overview.get("industry", domain))
                elif isinstance(overview, str) and overview:
                    domain = overview.split()[0]  # Simple approach - just first word
            
            # Try business_context
            if "business_context" in requirements_analysis and requirements_analysis["business_context"]:
                # Use first 100 chars of business context for RAG retrieval
                return requirements_analysis["business_context"][:100]
                
            # Try project_summary
            if "project_summary" in requirements_analysis and requirements_analysis["project_summary"]:
                return requirements_analysis["project_summary"][:100]
                
            return domain
            
        except Exception:
            return domain
    
    def log_execution_summary(self, result: Dict[str, Any]) -> None:
        """Log detailed execution summary for timeline estimation."""
        try:
            # Extract key metrics
            timeline = result.get("project_timeline", {})
            total_duration = timeline.get("estimated_duration_weeks", 0)
            total_phases = len(result.get("development_phases", []))
            critical_path = timeline.get("critical_path_duration", 0)
            milestones = len(result.get("milestones", []))
            risks = len(result.get("timeline_risks", []))
            
            # Log summary
            self.log_info(f"──────────────────────────────────────────")
            self.log_info(f"📅 TIMELINE ESTIMATION SUMMARY")
            self.log_info(f"──────────────────────────────────────────")
            self.log_info(f"🕒 Total Duration: {total_duration} weeks")
            self.log_info(f"🔄 Development Phases: {total_phases}")
            self.log_info(f"⚡️ Critical Path: {critical_path} days")
            self.log_info(f"🎯 Milestones: {milestones}")
            self.log_info(f"⚠️ Timeline Risks: {risks}")
            
            # Log start and end dates
            if "start_date" in timeline and "end_date" in timeline:
                self.log_info(f"📅 Project Timeline: {timeline['start_date']} to {timeline['end_date']}")
            
            # Log completion timestamp
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.log_info(f"✅ Estimation Completed: {now}")
            self.log_info(f"──────────────────────────────────────────")
            
        except Exception as e:
            self.log_warning(f"Failed to log execution summary: {e}")