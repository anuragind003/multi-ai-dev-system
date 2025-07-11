"""
Streamlined Plan Compiler Agent using a single, consolidated tool.
"""

import logging
import time
from typing import Dict, Any, Optional

from langchain_core.language_models.chat_models import BaseChatModel

from agents.base_agent import BaseAgent
from tools.planning_tools_enhanced import generate_comprehensive_work_item_backlog
from models.data_contracts import WorkItemBacklog
from agents.enhanced_react_base import EnhancedReActAgentBase

logger = logging.getLogger(__name__)

class PlanCompilerStreamlinedAgent(EnhancedReActAgentBase):
    """
    A streamlined agent that uses a single, consolidated tool to generate
    a comprehensive work item backlog.
    """
    
    def __init__(self,
                 llm: BaseChatModel,
                 memory,
                 temperature: float,
                 **kwargs):
        
        super().__init__(
            llm=llm,
            memory=memory,
            agent_name="Plan Compiler Agent",
            temperature=temperature,
            **kwargs
        )
        
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self.tools = [generate_comprehensive_work_item_backlog]

    def run(self, requirements_analysis: dict, tech_stack_recommendation: dict, system_design: dict, **kwargs) -> Dict[str, Any]:
        """
        Generates a comprehensive work item backlog by directly invoking the consolidated tool.
        """
        self.log_info("Starting plan compilation.")

        initial_prompt = f"""
        Generate a comprehensive work item backlog based on the provided requirements analysis, tech stack recommendation, and system design.
        Your primary goal is to create a detailed, step-by-step implementation plan for a new software project by breaking it down into a granular backlog of 'Work Items'.
        You MUST use the 'generate_comprehensive_work_item_backlog' tool to perform the analysis and submit your final result.
        Do not provide a 'Final Answer' yourself. The only way to complete this task is by using the 'generate_comprehensive_work_item_backlog' tool.

        **Requirements Analysis:**
        ---
        {requirements_analysis}
        ---

        **Tech Stack Recommendation:**
        ---
        {tech_stack_recommendation}
        ---

        **System Design:**
        ---
        {system_design}
        ---
        """
        
        # Execute the workflow using the method from the base class
        result = self.execute_enhanced_workflow(initial_input=initial_prompt)

        # Extract the final, structured output from the result
        final_output = self._extract_final_output(result)

        if final_output:
            self.log_success("Successfully extracted final work item backlog.")
            return final_output
        else:
            self.log_error("Failed to extract final work item backlog from the agent's execution.")
            return {"error": "Could not extract the final plan from the agent's output."}

    def store_memory(self, key: str, value: Any):
        """Helper to store data in agent's memory."""
        try:
            if hasattr(self, 'memory') and self.memory:
                self.memory.save_to_memory(key, value)
                logger.info(f"Stored '{key}' in agent memory.")
        except Exception as e:
            logger.warning(f"Could not store '{key}' in memory: {e}")

    async def arun(self, *args, **kwargs):
        # This is a placeholder for asynchronous execution.
        # In this streamlined agent, we delegate to the synchronous run method.
        return self.run(*args, **kwargs)

    def get_default_response(self) -> Dict[str, Any]:
        """
        Returns a default or fallback response for the agent.
        """
        return {
            "tasks": [],
            "timeline": "N/A",
            "summary": "Default plan response due to an error or incomplete processing."
        } 