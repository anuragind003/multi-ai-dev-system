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
from models.data_contracts import ComprehensiveSystemDesignOutput

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
            # Directly call the system design tool's function to pass the LLM object
            self.log_info("Calling generate_comprehensive_system_design tool directly (synchronous call)")
            
            result = self.system_design_tool.func(
                requirements_analysis=requirements_analysis,
                tech_stack_recommendation=tech_stack_recommendation,
                llm=self.llm
            )
            
            self.log_info(f"System design tool returned result type: {type(result)}")
            
            # Standardize return format
            if isinstance(result, dict):
                # Check for error in result
                if "error" in result:
                    self.log_error(f"System design tool returned error: {result}")
                    return self.get_default_response(Exception(result.get("details", "Unknown system design error")))
                else:
                    self.log_success("System design tool executed successfully")
                    # Ensure result is properly serialized to dictionary for state management
                    return self._ensure_dict_format(result)
            else:
                # Handle ComprehensiveSystemDesignOutput objects
                if hasattr(result, 'model_dump'):
                    serialized_result = result.model_dump()
                    self.log_success("System design completed and serialized")
                    return serialized_result
                else:
                    self.log_warning(f"Unexpected result type: {type(result)}")
                    return {"system_design_result": str(result), "type": type(result).__name__}
            
        except Exception as e:
            self.log_error(f"Error in synchronous system design generation: {str(e)}", exc_info=True)
            return self.get_default_response(e)

    def _ensure_dict_format(self, result: Any) -> Dict[str, Any]:
        """Ensure result is in proper dictionary format for state management."""
        if isinstance(result, dict):
            return result
        elif hasattr(result, 'model_dump'):
            return result.model_dump()
        elif hasattr(result, 'dict'):
            return result.dict()
        else:
            # Convert to string representation and wrap in dict
            try:
                import json
                if isinstance(result, str):
                    return json.loads(result)
                else:
                    return {"content": str(result), "type": type(result).__name__}
            except (json.JSONDecodeError, Exception):
                return {"content": str(result), "type": type(result).__name__}

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
            "error": str(error),
            "status": "error",
            "architecture": {
                "pattern": "Monolithic",
                "justification": "Default fallback due to planning error"
            },
            "components": [],
            "data_model": {"schema_type": "relational", "tables": []},
            "api_endpoints": {"style": "REST", "endpoints": []},
            "security": {"authentication_method": "JWT"},
            "data_flow": "Data flow analysis failed due to planning error"
        }
