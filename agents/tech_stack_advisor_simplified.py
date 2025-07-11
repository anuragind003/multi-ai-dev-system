"""
Simplified Tech Stack Advisor Agent using consistent patterns and shared utilities.
"""

import logging
import asyncio
from typing import Dict, Any

from agents.base_agent import BaseAgent
from tools.tech_stack_tools_enhanced import generate_comprehensive_tech_stack
from models.data_contracts import ComprehensiveTechStackOutput, TechStackComponent, ArchitecturePatternOption, TechStackSynthesisOutput
from utils.analysis_tool_utils import create_error_response, log_tool_execution

logger = logging.getLogger(__name__)

class TechStackAdvisorSimplifiedAgent(BaseAgent):
    """
    Simplified Tech Stack Advisor Agent using consistent patterns with other analysis agents.
    Provides technology stack recommendations based on BRD analysis.
    """

    def __init__(self, llm=None, **kwargs):
        """
        Initializes the TechStackAdvisorSimplifiedAgent.
        """
        super().__init__(
            llm=llm,
            agent_name="Tech Stack Advisor Simplified Agent",
            agent_description="Recommends technology stack based on BRD analysis using enhanced tools.",
            **kwargs
        )

    def run(self, raw_brd: str, requirements_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the agent to recommend a technology stack.

        Args:
            raw_brd: The raw text content of the BRD.
            requirements_analysis: A dictionary containing the structured analysis of the BRD.

        Returns:
            A dictionary containing the recommended technology stack.
        """
        operation_name = "Tech Stack Analysis"
        self.log_info(f"Starting {operation_name}")
        
        try:
            # Use the enhanced tool with proper LLM passing
            result = generate_comprehensive_tech_stack.func(
                brd_analysis=requirements_analysis,
                llm=self.llm
            )
            
            # Check for tool-level errors
            if isinstance(result, dict) and "error" in result:
                self.log_error(f"Tool returned error: {result}")
                return self.get_default_response(Exception(result.get("details", "Tool execution failed")))
            
            # Validate result structure
            if not isinstance(result, dict):
                self.log_error(f"Tool returned unexpected type: {type(result)}")
                return self.get_default_response(Exception("Invalid tool response format"))
            
            # Store successful result in memory
            self.store_memory("last_tech_stack_analysis", result)
            
            # Log success with key metrics
            options_count = sum([
                len(result.get('frontend_options', [])),
                len(result.get('backend_options', [])),
                len(result.get('database_options', [])),
                len(result.get('architecture_options', []))
            ])
            self.log_success(f"Tech stack analysis completed successfully with {options_count} total technology options")
            
            return result
            
        except Exception as e:
            self.log_error(f"Error in tech stack analysis: {str(e)}", exc_info=True)
            return self.get_default_response(e)

    async def arun(self, raw_brd: str, requirements_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Asynchronously executes the agent to recommend a technology stack.
        This method serves as the async entry point for the agent.

        Args:
            raw_brd: The raw text content of the BRD.
            requirements_analysis: A dictionary containing the structured analysis of the BRD.

        Returns:
            A dictionary containing the recommended technology stack.
        """
        return await asyncio.to_thread(self.run, raw_brd, requirements_analysis)

    def store_memory(self, key: str, value: Any):
        """Helper to store data in agent's memory with enhanced capabilities."""
        try:
            # Use enhanced memory if available
            if hasattr(self, '_enhanced_memory') and self._enhanced_memory:
                self.enhanced_set(key, value, context=self.agent_name)
            elif hasattr(self, 'memory') and self.memory:
                if hasattr(self.memory, 'save_to_memory'):
                    self.memory.save_to_memory(key, value)
                elif hasattr(self.memory, 'set'):
                    self.memory.set(key, value)
            self.log_info(f"Stored '{key}' in agent memory")
        except Exception as e:
            self.log_warning(f"Could not store '{key}' in memory: {e}")

    def get_default_response(self, error: Exception = None) -> Dict[str, Any]:
        """Returns a default, safe response in case of a critical failure."""
        if error:
            self.log_error(f"Executing default response due to error: {error}", exc_info=True)
        
        # Create minimal but valid tech stack structure
        default_frontend = {
            "name": "React",
            "language": "TypeScript",
            "reasoning": "Default frontend framework for failed analysis."
        }
        default_backend = {
            "name": "FastAPI",
            "language": "Python",
            "reasoning": "Default backend framework for failed analysis."
        }
        default_database = {
            "name": "PostgreSQL",
            "reasoning": "Default relational database for failed analysis."
        }
        default_architecture = {
            "pattern": "Microservices",
            "scalability_score": 7.0,
            "maintainability_score": 6.0,
            "development_speed_score": 5.0,
            "overall_score": 6.0,
            "reasoning": "Default architecture pattern for failed analysis."
        }
        
        return {
            "frontend_options": [default_frontend],
            "backend_options": [default_backend],
            "database_options": [default_database],
            "cloud_options": [],
            "architecture_options": [default_architecture],
            "tool_options": [],
            "risks": [{
                "category": "Analysis Failure",
                "description": "Automated tech stack analysis failed - manual review required",
                "severity": "High",
                "likelihood": "Certain",
                "mitigation": "Perform manual technology selection and validation"
            }],
            "synthesis": {
                "backend": {
                    "technology": "Python with FastAPI",
                    "justification": "Default backend choice due to analysis failure"
                },
                "frontend": {
                    "technology": "TypeScript with React", 
                    "justification": "Default frontend choice due to analysis failure"
                },
                "database": {
                    "technology": "PostgreSQL",
                    "justification": "Default database choice due to analysis failure"
                },
                "architecture_pattern": "Microservices",
                "deployment_environment": {
                    "platform": "Cloud",
                    "reasoning": "Default cloud deployment"
                },
                "key_libraries_tools": [
                    {"name": "Git", "purpose": "Version control"},
                    {"name": "Docker", "purpose": "Containerization"},
                    {"name": "CI/CD", "purpose": "Automated deployment"}
                ],
                "estimated_complexity": "Medium"
            },
            "error_info": {
                "error_type": "analysis_failure",
                "error_message": str(error) if error else "Unknown error occurred",
                "requires_manual_review": True
            }
        }
