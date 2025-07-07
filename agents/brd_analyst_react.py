"""
Streamlined BRD Analyst Agent using direct tool execution for efficiency.
"""

import logging
import asyncio
from typing import Dict, Any

from agents.base_agent import BaseAgent

# Import THE ONLY tool this agent will use
from tools.brd_analysis_tools_enhanced import generate_comprehensive_brd_analysis

logger = logging.getLogger(__name__)

class BRDAnalystReActAgent(BaseAgent):
    """
    A streamlined agent specializing in analyzing Business Requirement Documents (BRDs).
    Directly calls the BRD analysis tool without ReAct framework overhead.
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
            agent_description="Analyzes Business Requirements Documents directly.",
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
        self.log_info("Starting BRD analysis with direct tool execution.")

        try:
            # Directly call the BRD analysis tool - no ReAct framework needed
            result = generate_comprehensive_brd_analysis.invoke({"raw_brd_content": raw_brd})
            
            if isinstance(result, dict):
                if "error" in result:
                    self.log_error(f"BRD analysis tool returned error: {result}")
                    return {"error": "BRD analysis failed", "details": result}
                else:
                    self.log_success("Successfully completed BRD analysis.")
                    self.log_info(f"Analysis result keys: {list(result.keys())}")
                    return result
            else:
                self.log_error(f"Unexpected result type from BRD analysis tool: {type(result)}")
                return {"error": "Unexpected result format from BRD analysis tool"}
                
        except Exception as e:
            self.log_error(f"Failed to execute BRD analysis: {str(e)}")
            return {"error": "BRD analysis execution failed", "details": str(e)}

    async def arun(self, raw_brd: str) -> Dict[str, Any]:
        """
        Asynchronously executes the agent to analyze the provided BRD.
        This method serves as the async entry point for the agent.
        """
        return await asyncio.to_thread(self.run, raw_brd)

    def store_memory(self, key: str, value: Any):
        """Helper to store data in agent's memory."""
        try:
            if hasattr(self, 'memory') and self.memory:
                self.memory.save_to_memory(key, value)
                logger.info(f"Stored '{key}' in agent memory.")
        except Exception as e:
            logger.warning(f"Could not store '{key}' in memory: {e}")

    def get_default_response(self, error: Exception) -> Dict[str, Any]:
        """Returns a default, safe response in case of a critical failure."""
        logger.error(f"Executing default response due to error: {error}", exc_info=True)
        return {
            "status": "error",
            "message": f"A critical error occurred: {error}",
            "requirements_analysis": {}
        }

    
