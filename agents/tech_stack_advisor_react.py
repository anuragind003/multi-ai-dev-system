"""
Enhanced ReAct-based Tech Stack Advisor Agent with Hybrid Validation and API Token Optimization.
Uses reasoning and tool-execution loop for more flexible technology recommendations.
"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from functools import partial
import asyncio

# Core dependencies
from langchain_core.language_models import BaseLanguageModel
from langchain_core.retrievers import BaseRetriever
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import AgentExecutor, create_react_agent
import monitoring

# Local imports
from agents.base_agent import BaseAgent
from tools.json_handler import JsonHandler
from agent_temperatures import get_agent_temperature

# Enhanced memory and RAG imports
from enhanced_memory_manager import create_memory_manager, EnhancedSharedProjectMemory
from rag_manager import get_rag_manager

# Enhanced imports for hybrid validation and optimization
from utils.hybrid_validator import HybridValidator, HybridValidationResult
from utils.enhanced_tool_validator import enhanced_tool_validator
from utils.react_agent_api_optimizer import ReactAgentAPIOptimizer

# Import tech stack tools

# Import Pydantic models for output validation
from models.data_contracts import TechStackSynthesisOutput

# Add these imports to the top of the file
from langchain import hub
from langchain.agents import create_json_chat_agent, AgentExecutor
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.tools import Tool  # Add this import
from utils.safe_console_callback_handler import SafeConsoleCallbackHandler

# Import THE ONLY tool this agent will use
from tools.tech_stack_tools_enhanced import generate_comprehensive_tech_stack

from agents.enhanced_react_base import EnhancedReActAgentBase

logger = logging.getLogger(__name__)

class TechStackAdvisorReActAgent(EnhancedReActAgentBase):
    """
    A ReAct-based agent specializing in recommending a technology stack based on
    BRD analysis and requirements.
    """

    def __init__(self, 
                 llm: BaseLanguageModel, 
                 memory,
                 **kwargs):
        """
        Initializes the TechStackAdvisorReActAgent.

        Args:
            llm: The language model to use.
            memory: The memory instance for the agent.
            **kwargs: Additional arguments passed to the base class.
        """
        super().__init__(
            llm=llm,
            memory=memory,
            agent_name="Tech Stack Advisor ReAct Agent",
            **kwargs
        )
        
        # Define the tools specific to this agent
        tools = [generate_comprehensive_tech_stack]
        self.tools = self.create_enhanced_tools(tools)
        
        # Create the agent executor using the base class method
        self.agent_executor = self.create_agent_executor(self.tools)

    def run(self, raw_brd: str, requirements_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the agent to recommend a technology stack.

        Args:
            raw_brd: The raw text content of the BRD.
            requirements_analysis: A dictionary containing the structured analysis of the BRD.

        Returns:
            A dictionary containing the recommended technology stack.
        """
        self.log_info("Starting tech stack recommendation with ReAct agent.")

        # Prepare the structured input for the initial prompt
        requirements_str = "\n".join(
            f"- {category}: {', '.join(reqs)}" 
            for category, reqs in requirements_analysis.items()
        )

        initial_prompt = f"""
        Analyze the following business requirements to recommend a full technology stack.
        Your primary goal is to select the most appropriate technologies for the backend, frontend, and database.
        You MUST use the 'generate_comprehensive_tech_stack' tool to perform the analysis and submit your final result.
        Do not provide a 'Final Answer' yourself. The only way to complete this task is by using the 'generate_comprehensive_tech_stack' tool.

        **Original BRD:**
        ---
        {raw_brd}
        ---

        **Structured Requirements:**
        ---
        {requirements_str}
        ---
        """

        # Execute the workflow using the method from the base class
        result = self.execute_enhanced_workflow(initial_input=initial_prompt)

        # Extract the final, structured output from the result
        final_output = self._extract_final_output(result)

        if final_output:
            self.log_success("Successfully extracted final tech stack recommendation.")
            return final_output
        else:
            self.log_error("Failed to extract final tech stack recommendation from the agent's execution.")
            return {"error": "Could not extract the final recommendation from the agent's output."}

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
        """Helper to store data in agent's memory."""
        try:
            if hasattr(self, 'memory') and self.memory:
                self.memory.save_to_memory(key, value)
                logger.info(f"Stored '{key}' in agent memory.")
        except Exception as e:
            logger.warning(f"Could not store '{key}' in memory: {e}")

    def get_default_response(self, error: Exception) -> Dict[str, Any]:
        """Provides a fallback response when the agent encounters a critical error."""
        logger.error(f"Executing default response due to error: {error}", exc_info=True)
        return {
            "status": "error",
            "message": f"A critical error occurred: {error}",
            "tech_stack_recommendation": {
                "frontend": {"technology": "React", "language": "TypeScript"},
                "backend": {"technology": "Python", "language": "Python"},
                "database": {"technology": "PostgreSQL"},
                "justification": "A default, highly flexible stack suitable for general web applications was provided due to an internal error."
            }
        }

    def _setup_message_subscriptions(self) -> None:
        """Set up message bus subscriptions if available"""
        if self.message_bus:
            self.message_bus.subscribe("brd.analysis.complete", self._handle_brd_analysis_complete)
            self.log_info(f"{self.agent_name} subscribed to brd.analysis.complete events")
    
    def _handle_brd_analysis_complete(self, message: Dict[str, Any]) -> None:
        """Handle BRD analysis completion messages"""
        self.log_info("Received BRD analysis complete event")
        
        payload = message.get("payload", {})
        if payload.get("status") == "success":
            # Store BRD analysis for tech stack recommendation
            if "analysis" in payload:
                self.working_memory["brd_analysis"] = payload["analysis"]
                self.log_info(f"BRD analysis ready for tech stack recommendation: {payload.get('project_name', 'Unknown project')}")
            
            if "requirements_count" in payload:
                self.log_info(f"Ready to process {payload['requirements_count']} requirements for tech stack recommendation")
        else:
            self.log_warning("BRD analysis completed with errors")
    
    def _validate_input(self, input_data: Any, context: str = "") -> Any:
        """Validate input using hybrid validation system."""
        if not self.enable_enhanced_validation:
            return input_data
            
        from pydantic import BaseModel
        from typing import List
        
        # Simple validation schema for tech stack inputs
        class TechStackInputSchema(BaseModel):
            project_name: str = "Unknown Project"
            requirements: List[str] = []
            
        try:
            result = self.hybrid_validator.validate_progressive(
                raw_input=input_data,
                pydantic_model=TechStackInputSchema,
                required_fields=["project_name"],
                context=context
            )
            return result
        except Exception as e:
            self.logger.warning(f"Input validation failed: {e}")
            # Return a mock successful result for fallback
            from utils.hybrid_validator import HybridValidationResult, ValidationLevel
            return HybridValidationResult(
                success=True,
                data=input_data,
                confidence_score=0.3,
                level_used=ValidationLevel.FALLBACK,
                errors=[],
                warnings=[f"Validation failed: {e}"],
                processing_notes=["Fallback validation used due to error"]
            )
    
    def _update_execution_metrics(self, success: bool, execution_time: float):
        """Update execution performance metrics."""
        if success:
            self.execution_metrics["successful_executions"] += 1
        else:
            self.execution_metrics["failed_executions"] += 1
        
        # Update average execution time
        total_executions = self.execution_metrics["total_executions"]
        current_avg = self.execution_metrics["avg_execution_time"]
        self.execution_metrics["avg_execution_time"] = (
            (current_avg * (total_executions - 1) + execution_time) / total_executions
        )
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics for this agent."""
        total = self.execution_metrics["total_executions"]
        if total == 0:
            return {"message": "No executions recorded yet"}
        
        success_rate = (self.execution_metrics["successful_executions"] / total) * 100
        
        metrics = {
            "agent_name": self.agent_name,
            "execution_summary": {
                "total_executions": total,
                "successful_executions": self.execution_metrics["successful_executions"],
                "failed_executions": self.execution_metrics["failed_executions"],
                "success_rate": f"{success_rate:.1f}%",
                "avg_execution_time": f"{self.execution_metrics['avg_execution_time']:.2f}s"
            },
            "validation_distribution": self.execution_metrics["validation_stats"],
            "api_optimization": {
                "cache_hits": self.execution_metrics["api_token_savings"],
                "optimization_enabled": self.enable_api_optimization
            },
            "enhanced_features": {
                "validation_enabled": self.enable_enhanced_validation,
                "api_optimization_enabled": self.enable_api_optimization
            }
        }
        
        # Add tool-level metrics if available
        if hasattr(self, 'enhanced_tool_validator'):
            tool_report = enhanced_tool_validator.get_tool_performance_report()
            agent_tools = {k: v for k, v in tool_report.get("tools", {}).items() 
                          if k.startswith(f"{self.agent_name}:")}
            metrics["tool_performance"] = agent_tools
        
        # Add validation statistics if available
        if self.enable_enhanced_validation and hasattr(self, 'hybrid_validator'):
            validation_stats = self.hybrid_validator.get_validation_stats()
            metrics["validation_performance"] = validation_stats
        
        return metrics

    def _init_enhanced_memory(self):
        """Initializes the enhanced shared memory for the agent."""
        try:
            # ... existing code ...
            pass
        except Exception as e:
            self.logger.error(f"Failed to initialize enhanced memory: {e}")