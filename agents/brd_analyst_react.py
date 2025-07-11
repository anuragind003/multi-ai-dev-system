"""
Streamlined BRD Analyst Agent using consistent patterns and shared utilities.
"""

import logging
import asyncio
from typing import Dict, Any

from agents.base_agent import BaseAgent
from tools.brd_analysis_tools_enhanced import generate_comprehensive_brd_analysis
from models.data_contracts import BRDRequirementsAnalysis
from utils.analysis_tool_utils import create_error_response, log_tool_execution

logger = logging.getLogger(__name__)

class BRDAnalystReActAgent(BaseAgent):
    """
    A streamlined agent specializing in analyzing Business Requirement Documents (BRDs).
    Uses consistent patterns with other analysis agents and standardized error handling.
    """
    def __init__(self, llm=None, **kwargs):
        """
        Initializes the BRDAnalystReActAgent.
        
        Args:
            llm: The language model to use.
            **kwargs: Additional arguments passed to the base class.
        """
        super().__init__(
            llm=llm,
            agent_name="BRD Analyst ReAct Agent",
            agent_description="Analyzes Business Requirements Documents using enhanced tools.",
            **kwargs
        )

    def run(self, raw_brd: str) -> Dict[str, Any]:
        """
        Executes the agent to analyze the provided BRD.

        Args:
            raw_brd: The raw text content of the Business Requirement Document.

        Returns:
            A dictionary containing the structured analysis of the BRD.
        """
        operation_name = "BRD Agent Analysis"
        self.log_info(f"Starting {operation_name}")

        try:
            # Use the enhanced tool with proper LLM passing
            result = generate_comprehensive_brd_analysis.func(
                raw_brd_content=raw_brd,
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
            self.store_memory("last_brd_analysis", result)
            
            # Log success with key metrics
            requirements_count = len(result.get('requirements', []))
            self.log_success(f"BRD analysis completed successfully with {requirements_count} requirements extracted")
            
            return result
                
        except Exception as e:
            self.log_error(f"Failed to execute BRD analysis: {str(e)}")
            return self.get_default_response(e)

    async def arun(self, raw_brd: str) -> Dict[str, Any]:
        """
        Asynchronously executes the agent to analyze the provided BRD.
        This method serves as the async entry point for the agent.
        """
        return await asyncio.to_thread(self.run, raw_brd)

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
        
        return {
            "project_name": "Unknown Project",
            "project_summary": "BRD analysis could not be completed due to an error.",
            "project_goals": [],
            "target_audience": [],
            "business_context": "Analysis failed - manual review required.",
            "requirements": [],
            "functional_requirements": [],
            "non_functional_requirements": [],
            "stakeholders": [],
            "success_criteria": [],
            "constraints": [],
            "assumptions": [],
            "risks": ["BRD analysis tool failure - manual review required"],
            "domain_specific_details": {},
            "quality_assessment": {
                "completeness_score": 0,
                "clarity_score": 0,
                "consistency_score": 0,
                "recommendations": ["Manual BRD review required due to analysis failure"]
            },
            "gap_analysis": {
                "identified_gaps": ["Automated analysis failed"],
                "recommendations_for_completion": ["Perform manual BRD analysis and validation"]
            },
            "error_info": {
                "error_type": "analysis_failure",
                "error_message": str(error) if error else "Unknown error occurred",
                "requires_manual_review": True
            }
        }

    
