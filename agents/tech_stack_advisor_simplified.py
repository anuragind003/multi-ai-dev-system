"""
Simplified Tech Stack Advisor Agent.
Directly calls the tech stack analysis tool without ReAct framework overhead.
"""

import logging
import asyncio
from typing import Dict, Any

# Local imports
from agents.base_agent import BaseAgent
from tools.tech_stack_tools_enhanced import generate_comprehensive_tech_stack, fix_field_mappings
from models.data_contracts import TechStackComponent, ArchitecturePatternOption, TechRisk, TechStackSynthesisOutput, SelectedTechStack, ComprehensiveTechStackOutput

logger = logging.getLogger(__name__)

class TechStackAdvisorSimplifiedAgent(BaseAgent):
    """
    Simplified Tech Stack Advisor Agent.
    Directly calls the BRD analysis tool without ReAct framework overhead.
    """

    def __init__(self, llm=None, **kwargs):
        """
        Initializes the TechStackAdvisorSimplifiedAgent.
        """
        super().__init__(
            llm=llm,
            agent_name="Tech Stack Advisor Simplified Agent",
            agent_description="Recommends technology stack based on BRD analysis.",
            **kwargs
        )

        # Store the tool for direct calling
        self.tech_stack_tool = generate_comprehensive_tech_stack

        self.log_info("Tech Stack Advisor Simplified Agent initialized successfully")

    def run(self, raw_brd: str, requirements_analysis: Dict[str, Any]) -> ComprehensiveTechStackOutput:
        """
        Executes the agent to recommend a technology stack.

        Args:
            raw_brd: The raw text content of the BRD.
            requirements_analysis: A dictionary containing the structured analysis of the BRD.

        Returns:
            A ComprehensiveTechStackOutput object containing the recommended technology stack.
        """
        self.log_info("Starting tech stack recommendation with simplified agent.")
        
        try:
            # Directly call the tech stack analysis tool - no ReAct framework needed
            self.log_info("Calling generate_comprehensive_tech_stack tool directly")
            
            # Call the tool with the BRD analysis
            result = self.tech_stack_tool.invoke({
                "brd_analysis": requirements_analysis
            })
            
            self.log_info(f"Tech stack tool returned result type: {type(result)}")
            if isinstance(result, dict):
                self.log_info(f"Tech stack tool result keys: {list(result.keys())}")
                # Check for error in result
                if "error" in result:
                    self.log_error(f"Tech stack tool returned error: {result}")
                    # Return a default response with error details
                    return self.get_default_response(Exception(result.get("details", "Unknown error from tool")))
                else:
                    self.log_success("Tech stack tool executed successfully")
                    
                    # Apply field mapping fixes before validation
                    try:
                        fixed_result = fix_field_mappings(result)
                        return ComprehensiveTechStackOutput(**fixed_result)
                    except Exception as validation_error:
                        self.log_error(f"Validation error after field mapping: {validation_error}")
                        # Try the original result as a last resort
                        try:
                            return ComprehensiveTechStackOutput(**result)
                        except Exception as final_error:
                            self.log_error(f"Final validation failed: {final_error}")
                            return self.get_default_response(final_error)
            else:
                self.log_info(f"Tech stack tool returned unexpected result type: {type(result)}. Attempting to wrap as default response.")
                return self.get_default_response(Exception(f"Unexpected tech stack tool result: {str(result)[:200]}"))
            
        except Exception as e:
            self.log_error(f"Error in tech stack analysis: {str(e)}", exc_info=True)
            return self.get_default_response(e)

    async def arun(self, raw_brd: str, requirements_analysis: Dict[str, Any]) -> ComprehensiveTechStackOutput:
        """
        Asynchronously executes the agent to recommend a technology stack.
        This method serves as the async entry point for the agent.

        Args:
            raw_brd: The raw text content of the BRD.
            requirements_analysis: A dictionary containing the structured analysis of the BRD.

        Returns:
            A ComprehensiveTechStackOutput object containing the recommended technology stack.
        """
        return await asyncio.to_thread(self.run, raw_brd, requirements_analysis)

    def get_default_response(self, error: Exception) -> ComprehensiveTechStackOutput:
        """Returns a default, safe response in case of a critical failure."""
        self.log_error(f"Executing default response due to error: {error}", exc_info=True)
        # Return a valid, but empty/error-state ComprehensiveTechStackOutput
        default_frontend = TechStackComponent(name="React", language="TypeScript", reasoning="Default frontend framework.")
        default_backend = TechStackComponent(name="FastAPI", language="Python", reasoning="Default backend framework.")
        default_database = TechStackComponent(name="PostgreSQL", reasoning="Default relational database.")
        default_architecture = ArchitecturePatternOption(
            pattern="Microservices", 
            scalability_score=7.0,
            maintainability_score=6.0,
            development_speed_score=5.0,
            overall_score=6.0,
            reasoning="Default architecture pattern with moderate complexity and good scalability."
        )
        
        return ComprehensiveTechStackOutput(
            frontend_options=[default_frontend],
            backend_options=[default_backend],
            database_options=[default_database],
            cloud_options=[],
            architecture_options=[default_architecture],
            tool_options=[],
            risks=[],
            synthesis=TechStackSynthesisOutput(backend={}, frontend={}, database={}, architecture_pattern="Microservices", deployment_environment={}, key_libraries_tools=[], estimated_complexity="Medium") # Provide a minimal synthesis
        )
