"""
Project Analyzer Agent - Specialized in analyzing project requirements and complexity
to provide insights for project planning and resource allocation.
"""

import json
import logging
logger = logging.getLogger(__name__)
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from langchain_core.language_models import BaseLanguageModel
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.retrievers import BaseRetriever

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
from agents.models import (
    ProjectAnalysisInput,
    ProjectAnalysisOutput,
    ExecutiveSummary
)

class ProjectAnalyzerAgent(BaseAgent):
    """
    Enhanced Project Analyzer Agent with comprehensive project analysis capabilities.
    
    This agent analyzes project requirements, system design, and tech stack to:
    1. Determine overall project complexity and factors affecting it
    2. Identify resource requirements and specialized skills needed
    3. Analyze implementation considerations and critical path components
    4. Assess risks and provide mitigation strategies
    5. Evaluate feasibility and constraints
    
    Uses temperature 0.3 for balanced analytical and creative insights.
    """
    
    def __init__(self, llm: BaseLanguageModel, memory, temperature: float, rag_retriever: Optional[BaseRetriever] = None):
        # If no specific temperature provided, get from settings
        if temperature is None:
            temperature = get_agent_temperature("Project Analyzer Agent", 0.3)
            
        super().__init__(
            llm=llm,
            memory=memory,
            agent_name="Project Analyzer Agent",
            temperature=temperature,
            rag_retriever=rag_retriever
        )
        
        # Initialize single comprehensive prompt template
        self._initialize_prompt_templates()
        
        # Initialize Pydantic output parser for final result validation
        self.analysis_parser = PydanticOutputParser(pydantic_object=ProjectAnalysisOutput)
    
    def _initialize_prompt_templates(self):
        """Initialize a comprehensive prompt template for project analysis with Pydantic format instructions."""
        # Single comprehensive prompt template that covers all analysis aspects
        self.prompt_template = ChatPromptTemplate.from_messages([
            SystemMessage(content="""
                You are a Senior Project Analysis Expert specializing in software development projects.
                
                Your task is to provide a comprehensive analysis of the project based on requirements, 
                tech stack recommendations, and system design. Your analysis should be thorough, 
                objective, and actionable, covering all key aspects of project planning.
                
                Provide your analysis in a structured format following the exact schema provided.
            """),
            HumanMessage(content="""
                Analyze the following project information and provide a comprehensive project assessment:
                
                REQUIREMENTS ANALYSIS:
                {requirements_analysis}
                
                TECH STACK RECOMMENDATION:
                {tech_stack_recommendation}
                
                SYSTEM DESIGN:
                {system_design}
                
                Provide a comprehensive project analysis that includes:
                
                1. Executive summary with key project parameters
                2. Project viability assessment
                3. Critical success factors
                4. Recommended implementation approach
                5. Top risks requiring mitigation
                6. Resource recommendations (team size, expertise levels, key skills)
                7. Timeline recommendations (duration, phasing, buffer)
                
                Follow this exact format:
                {format_instructions}
            """)
        ])
    
    def get_default_response(self) -> Dict[str, Any]:
        """
        Returns a default response structure if the LLM call fails.
        Creates a valid ProjectAnalysisOutput instance.
        """
        # Create default using Pydantic models
        default_analysis = ProjectAnalysisOutput(
            executive_summary=ExecutiveSummary(
                project_complexity="5/10",
                resource_needs="3-5 team members",
                estimated_duration="12 weeks",
                scope_completeness="70%",
                key_finding="Default project analysis due to processing error"
            ),
            project_viability="Medium",
            critical_success_factors=[
                "Clear requirements documentation",
                "Technical expertise in chosen stack",
                "Regular stakeholder communication"
            ],
            recommended_approach="Agile with two-week sprints",
            top_risks=[
                {"risk": "Scope uncertainty", "mitigation": "Iterative development with frequent validation"},
                {"risk": "Technical complexity", "mitigation": "Early prototyping of complex components"}
            ],
            resource_recommendations={
                "team_size": 4,
                "expertise_level": "Mid-level to senior",
                "key_skills_needed": ["Backend Development", "Database Design", "Frontend Development"]
            },
            timeline_recommendation={
                "duration": "12 weeks",
                "phasing": "4 phases with 2-week sprints",
                "buffer": "2 weeks (20%) contingency recommended"
            },
            analysis_metadata={
                "generated_at": datetime.now().isoformat(),
                "generation_method": "default_fallback",
                "confidence_level": "low"
            }
        )
        
        self.log_warning("Using default project analysis response due to processing failure")
        return default_analysis.dict()
    
    def run(self, requirements_analysis: Dict[str, Any], 
            tech_stack_recommendation: Dict[str, Any],
            system_design: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute comprehensive project analysis to determine complexity, resource needs, 
        and implementation approach using a single LLM call with structured output.
        
        Args:
            requirements_analysis: The structured requirements analysis
            tech_stack_recommendation: The recommended technology stack
            system_design: The system design specifications
            
        Returns:
            Dict containing comprehensive project analysis
        """
        # Start analysis process
        self.log_start(f"Starting comprehensive project analysis with temperature {self.default_temperature}")
        
        try:
            # Validate input using Pydantic model
            try:
                input_data = ProjectAnalysisInput(
                    requirements_analysis=requirements_analysis,
                    tech_stack_recommendation=tech_stack_recommendation,
                    system_design=system_design
                )
            except Exception as e:
                self.log_warning(f"Input validation error: {e}, using sanitized input")
                # Create sanitized input if validation fails
                input_data = ProjectAnalysisInput(
                    requirements_analysis=requirements_analysis if isinstance(requirements_analysis, dict) else {},
                    tech_stack_recommendation=tech_stack_recommendation if isinstance(tech_stack_recommendation, dict) else {},
                    system_design=system_design if isinstance(system_design, dict) else {}
                )
            
            # Safely serialize inputs to JSON (with error handling)
            req_json = "{}"
            tech_json = "{}"
            design_json = "{}"
            
            try:
                if isinstance(input_data.requirements_analysis, dict):
                    req_json = json.dumps(input_data.requirements_analysis, indent=2)
            except Exception as e:
                self.log_warning(f"Failed to serialize requirements analysis: {str(e)}")
                
            try:
                if isinstance(input_data.tech_stack_recommendation, dict):
                    tech_json = json.dumps(input_data.tech_stack_recommendation, indent=2)
            except Exception as e:
                self.log_warning(f"Failed to serialize tech stack: {str(e)}")
                
            try:
                if isinstance(input_data.system_design, dict):
                    design_json = json.dumps(input_data.system_design, indent=2)
            except Exception as e:
                self.log_warning(f"Failed to serialize system design: {str(e)}")
            
            # Execute the LLM chain with Pydantic output model
            final_analysis = self.execute_llm_chain(
                inputs={
                    "requirements_analysis": req_json,
                    "tech_stack_recommendation": tech_json,
                    "system_design": design_json
                },
                output_pydantic_model=ProjectAnalysisOutput,
                additional_llm_params={"max_tokens": 4096}
            )
            
            # Add metadata if not present
            if isinstance(final_analysis, dict) and "analysis_metadata" not in final_analysis:
                final_analysis["analysis_metadata"] = {
                    "generated_at": datetime.now().isoformat(),
                    "analysis_approach": "comprehensive project assessment",
                    "confidence_level": "high"
                }
                
            # Log success
            self.log_success("Comprehensive project analysis completed successfully with structured output")
            return final_analysis
            
        except Exception as e:
            self.log_error(f"Project analysis failed: {str(e)}")
            import traceback
            self.log_error(traceback.format_exc())
            return self.get_default_response()