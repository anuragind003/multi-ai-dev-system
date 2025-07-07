"""
Simplified System Designer Agent.
Directly calls the system design tool without ReAct framework overhead.
"""

import logging
import json
from typing import Dict, Any
import asyncio

from agents.base_agent import BaseAgent
from tools.system_design_tools_enhanced import generate_comprehensive_system_design

logger = logging.getLogger(__name__)

class SystemDesignerSimplifiedAgent(BaseAgent):
    """
    Simplified System Designer Agent.
    Directly calls the system design tool without ReAct framework overhead.
    """

    def __init__(self, llm=None, **kwargs):
        """
        Initializes the SystemDesignerSimplifiedAgent.
        """
        super().__init__(
            llm=llm,
            agent_name="System Designer Simplified Agent",
            agent_description="Generates comprehensive system design based on requirements and tech stack.",
            **kwargs
        )

        # Store the tool for direct calling
        self.system_design_tool = generate_comprehensive_system_design

        self.log_info("System Designer Simplified Agent initialized successfully")

    def run(self, requirements_analysis: dict, tech_stack_recommendation: dict, **kwargs) -> Dict[str, Any]:
        """
        Generates a comprehensive system design by directly invoking the tool.
        This is the synchronous implementation.
        """
        self.log_info("Starting system design generation with simplified agent (synchronous run).")
        
        try:
            # Directly call the system design tool
            self.log_info("Calling generate_comprehensive_system_design tool directly (synchronous call)")
            
            result = self.system_design_tool.invoke({
                "requirements_analysis": requirements_analysis,
                "tech_stack_recommendation": tech_stack_recommendation
            })
            
            self.log_info(f"System design tool returned result type: {type(result)}")
            if isinstance(result, dict):
                self.log_info(f"System design tool result keys: {list(result.keys())}")
                # Check for error in result
                if "error" in result:
                    self.log_error(f"System design tool returned error: {result}")
                    return result
                else:
                    self.log_success("System design tool executed successfully")
                    return result
            else:
                self.log_info(f"System design tool result (first 200 chars): {str(result)[:200]}")
                return {"system_design_result": result}
            
        except Exception as e:
            self.log_error(f"Error in synchronous system design generation: {str(e)}", exc_info=True)
            return {
                "error": "system_design_error",
                "details": str(e)
            }

    async def arun(self, requirements_analysis: dict, tech_stack_recommendation: dict, **kwargs) -> Dict[str, Any]:
        """
        Asynchronously generates a comprehensive system design by delegating to the synchronous run method.
        """
        self.log_info("Asynchronous run method called. Delegating to synchronous run.")
        return await asyncio.to_thread(self.run, requirements_analysis, tech_stack_recommendation, **kwargs)

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
        self.log_error(f"Executing default response due to error: {error}", exc_info=True)
        return {
            "status": "error",
            "message": f"A critical error occurred: {error}",
            "system_design": {}
        }
