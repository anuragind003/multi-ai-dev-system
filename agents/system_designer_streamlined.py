"""
Streamlined System Designer Agent using a single, consolidated tool.
"""

import logging
import time
import json
from typing import Dict, Any, Optional

from langchain_core.language_models.chat_models import BaseChatModel

from agents.base_agent import BaseAgent
from tools.system_design_tools_enhanced import generate_comprehensive_system_design
from agents.enhanced_react_base import EnhancedReActAgentBase

logger = logging.getLogger(__name__)

class SystemDesignerStreamlinedAgent(EnhancedReActAgentBase):
    """
    A streamlined agent that uses a single, consolidated tool to generate
    a comprehensive system design.
    """
    
    def __init__(self,
                 llm: BaseChatModel,
                 memory,
                 temperature: float,
                 **kwargs):
        
        super().__init__(
            llm=llm,
            memory=memory,
            agent_name="System Designer Agent",
            temperature=temperature,
            **kwargs
        )
        
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self.tools = [generate_comprehensive_system_design]

    def run(self, requirements_analysis: dict, tech_stack_recommendation: dict, **kwargs) -> Dict[str, Any]:
        """
        Generates a comprehensive system design by directly invoking the consolidated tool.
        """
        self.log_info("Starting system design generation.")

        initial_prompt = f"""
        Generate a comprehensive system design based on the provided requirements analysis and tech stack recommendation.
        Your primary goal is to create a detailed system design including architectural components, data flows, API designs, database schemas, security, deployment, monitoring, and scalability strategies.
        You MUST use the 'generate_comprehensive_system_design' tool to perform the analysis and submit your final result.
        Do not provide a 'Final Answer' yourself. The only way to complete this task is by using the 'generate_comprehensive_system_design' tool.

        **Requirements Analysis:**
        ---
        {json.dumps(requirements_analysis, indent=2)}
        ---

        **Tech Stack Recommendation:**
        ---
        {json.dumps(tech_stack_recommendation, indent=2)}
        ---
        """

        # Execute the workflow using the method from the base class
        result = self.execute_enhanced_workflow(initial_input=initial_prompt)

        # Extract the final, structured output from the result
        final_output = self._extract_final_output(result)

        if final_output:
            self.log_success("Successfully extracted final system design.")
            return final_output
        else:
            self.log_error("Failed to extract final system design from the agent's execution.")
            return {"error": "Could not extract the final design from the agent's output."}

    def store_memory(self, key: str, value: Any):
        """Helper to store data in agent's memory."""
        try:
            if hasattr(self, 'memory') and self.memory:
                self.memory.save_to_memory(key, value)
                logger.info(f"Stored '{key}' in agent memory.")
        except Exception as e:
            logger.warning(f"Could not store '{key}' in memory: {e}") 