"""
Enhanced ReAct Agent Base Class with Hybrid Validation and API Token Optimization

This module provides an enhanced base class for ReAct agents with:
- 3-layer hybrid validation system
- API token usage optimization
- Comprehensive performance tracking
- Enhanced error recovery and resilience
"""

import logging
import time
import json
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from dataclasses import dataclass, field

from langchain_core.language_models import BaseLanguageModel
from langchain_core.retrievers import BaseRetriever
from langchain_core.messages import SystemMessage, HumanMessage
from langchain import hub
from langchain.agents import AgentExecutor, create_json_chat_agent
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

from .base_agent import BaseAgent
from utils.hybrid_validator import HybridValidator, HybridValidationResult
from utils.enhanced_tool_validator import enhanced_tool_validator
from tools.json_handler import JsonHandler
import monitoring
from utils.safe_console_callback_handler import SafeConsoleCallbackHandler, create_detailed_callback

# Enhanced memory and RAG imports
from enhanced_memory_manager import create_memory_manager, EnhancedSharedProjectMemory
from rag_manager import get_rag_manager

logger = logging.getLogger(__name__)

@dataclass
class ReactAgentMetrics:
    """Performance metrics for ReAct agents."""
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    avg_execution_time: float = 0.0
    total_api_calls: int = 0
    total_tool_calls: int = 0
    validation_successes: Dict[str, int] = field(default_factory=lambda: {
        "strict": 0, "tolerant": 0, "permissive": 0, "fallback": 0
    })
    api_token_usage: int = 0
    cache_hit_rate: float = 0.0
    
    def update_execution(self, success: bool, execution_time: float, api_calls: int = 0, tool_calls: int = 0):
        """Update metrics for an agent execution."""
        self.total_executions += 1
        if success:
            self.successful_executions += 1
        else:
            self.failed_executions += 1
        
        # Update average execution time
        total_time = self.avg_execution_time * (self.total_executions - 1) + execution_time
        self.avg_execution_time = total_time / self.total_executions
        
        self.total_api_calls += api_calls
        self.total_tool_calls += tool_calls
    
    def get_success_rate(self) -> float:
        """Get success rate as percentage."""
        if self.total_executions == 0:
            return 0.0
        return (self.successful_executions / self.total_executions) * 100
    
    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary."""
        return {
            "executions": {
                "total": self.total_executions,
                "successful": self.successful_executions,
                "failed": self.failed_executions,
                "success_rate": f"{self.get_success_rate():.1f}%"
            },
            "performance": {
                "avg_execution_time": f"{self.avg_execution_time:.2f}s",
                "total_api_calls": self.total_api_calls,
                "total_tool_calls": self.total_tool_calls,
                "api_tokens_used": self.api_token_usage
            },
            "validation": {
                "distribution": self.validation_successes,
                "cache_hit_rate": f"{self.cache_hit_rate:.1f}%"
            }
        }

class EnhancedReActAgentBase(BaseAgent):
    """
    Enhanced base class for ReAct agents with hybrid validation and API optimization.
    
    Features:
    - 3-layer hybrid validation for all inputs/outputs
    - API token usage optimization with caching
    - Comprehensive performance tracking
    - Enhanced error recovery mechanisms
    - Automatic tool validation wrapping
    """
    
    def __init__(self,
                 llm: BaseLanguageModel,
                 memory,
                 agent_name: str,
                 temperature: float,
                 rag_retriever: Optional[BaseRetriever] = None,
                 message_bus=None,
                 enable_caching: bool = True,
                 max_iterations: int = 15,
                 enable_performance_tracking: bool = True):
        
        super().__init__(
            llm=llm,
            memory=memory,
            agent_name=agent_name,
            temperature=temperature,
            rag_retriever=rag_retriever,
            message_bus=message_bus
        )
        
        # Initialize enhanced memory (inherits from BaseAgent which has enhanced memory mixin)
        self._init_enhanced_memory()
        
        # Initialize RAG context
        self.rag_manager = get_rag_manager()
        if self.rag_manager:
            self.logger.info("RAG manager available for enhanced React processing")
        else:
            self.logger.warning("RAG manager not available - proceeding with basic React processing")
        
        # Enhanced validation and optimization components
        self.hybrid_validator = HybridValidator(self.logger)
        self.json_handler = JsonHandler()
        self.enable_caching = enable_caching
        self.max_iterations = max_iterations
        self.enable_performance_tracking = enable_performance_tracking
        
        # Performance tracking
        if self.enable_performance_tracking:
            self.metrics = ReactAgentMetrics()
        else:
            self.metrics = None
        
        # Agent configuration
        self.tools = []
        self.react_prompt = None
        self.agent_executor = None
        
        # Initialize enhanced components
        self._setup_enhanced_agent()
    
    def _setup_enhanced_agent(self):
        """Setup enhanced agent components."""
        try:
            # Get the ReAct prompt from hub
            self.react_prompt = hub.pull("hwchase17/react-chat-json")
            
            # Enhance the system message for better validation and token efficiency
            self._enhance_system_prompt()
            
            self.log_info(f"Enhanced ReAct agent '{self.agent_name}' initialized successfully")
            
        except Exception as e:
            self.log_error(f"Failed to setup enhanced agent: {str(e)}")
            raise
    
    def _enhance_system_prompt(self):
        """Enhance the system prompt for better validation and API efficiency."""
        enhanced_system_content = f"""
You are an enhanced {self.agent_name} with strict output requirements and efficient processing capabilities.

CRITICAL OUTPUT REQUIREMENTS:
1. You MUST use tools to communicate and complete your analysis
2. You are FORBIDDEN from providing "Final Answer" responses
3. Your ONLY way to finish tasks is by calling the designated completion tool
4. All tool calls must use properly structured JSON inputs

EFFICIENCY GUIDELINES:
1. Minimize API calls by batching operations when possible
2. Use cached results when available (you'll be notified of cache hits)
3. Process large amounts of data in single tool calls rather than multiple smaller calls
4. Prefer batch evaluation tools over individual assessment tools

VALIDATION REQUIREMENTS:
1. Always provide complete, structured data to tools
2. Ensure all required fields are present in tool inputs
3. Use consistent naming and formatting for all parameters
4. If unsure about input format, err on the side of providing more structured data

ERROR RECOVERY:
1. If a tool call fails due to validation issues, analyze the error and retry with corrected input
2. Never abandon the task - always find an alternative approach
3. Use fallback strategies when primary approaches fail

Your responses will be automatically validated using a 3-layer system:
- STRICT: Exact format matching (preferred)
- TOLERANT: Format cleaning and type coercion
- PERMISSIVE: Schema-guided extraction
- FALLBACK: Best-effort extraction

Aim for STRICT validation by providing well-structured tool inputs.
        """
        
        # Update the system message in the prompt
        for message in self.react_prompt.messages:
            if isinstance(message, SystemMessage):
                message.content = enhanced_system_content
                break
    
    def create_enhanced_tools(self, tool_functions: List[callable]) -> List[callable]:
        """
        Create enhanced versions of tools with validation and optimization.
        
        Args:
            tool_functions: List of tool functions to enhance
            
        Returns:
            List of enhanced tool functions
        """
        enhanced_tools = []
        
        for tool_func in tool_functions:
            tool_name = getattr(tool_func, 'name', tool_func.__name__)
            
            # Wrap tool with enhanced validation
            enhanced_tool = enhanced_tool_validator.create_validated_tool(
                tool_function=tool_func,
                tool_name=f"{self.agent_name}:{tool_name}",
                enable_caching=self.enable_caching,
                max_retries=2
            )
            
            enhanced_tools.append(enhanced_tool)
            
        self.log_info(f"Enhanced {len(enhanced_tools)} tools for {self.agent_name}")
        return enhanced_tools
    
    def create_agent_executor(self, tools: List[callable]) -> AgentExecutor:
        """
        Create an optimized AgentExecutor with enhanced settings.
        
        Args:
            tools: List of tool functions
            
        Returns:
            Configured AgentExecutor
        """
        # Create the agent with temperature binding
        agent = create_json_chat_agent(
            llm=self.llm.bind(temperature=self.default_temperature),
            tools=tools,
            prompt=self.react_prompt,
            verbose=False,  # Disable verbose to prevent I/O errors
            callbacks=[create_detailed_callback(max_output_length=3000)],  # Show full tool outputs
        )
        
        # Create enhanced executor
        agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=False,  # Reduce verbosity for token efficiency
            handle_parsing_errors=True,
            max_iterations=self.max_iterations,
            return_intermediate_steps=True,
            early_stopping_method="force"
        )
        
        return agent_executor
    
    def execute_enhanced_workflow(self, 
                                 initial_input: str,
                                 session_id: Optional[str] = None,
                                 context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute the ReAct workflow with enhanced validation and tracking.
        
        Args:
            initial_input: The initial input prompt for the agent
            session_id: Optional session ID for chat history
            context: Additional context information
            
        Returns:
            Enhanced result with validation metadata and performance metrics
        """
        if not self.agent_executor:
            raise RuntimeError("Agent executor not initialized. Call setup_agent_executor first.")
        
        start_time = time.time()
        session_id = session_id or f"{self.agent_name}_{int(time.time())}"
        
        try:
            # Setup chat history
            message_history = ChatMessageHistory()
            agent_with_history = RunnableWithMessageHistory(
                self.agent_executor,
                lambda sid: message_history,
                input_messages_key="input",
                history_messages_key="chat_history"
            )
            
            # Execute with monitoring
            with monitoring.agent_trace_span(self.agent_name, "enhanced_react_execution"):
                result = agent_with_history.invoke(
                    {"input": initial_input},
                    config={"configurable": {"session_id": session_id}}
                )
            
            # Process and validate the result
            processed_result = self._process_agent_result(result, start_time)
            
            # Publish completion message
            if hasattr(self, 'message_bus') and self.message_bus:
                self.message_bus.publish(f"{self.agent_name.lower().replace(' ', '_')}.execution.complete", {
                    "agent": self.agent_name,
                    "session_id": session_id,
                    "status": "completed" if processed_result.get("success", False) else "failed",
                    "execution_time": time.time() - start_time,
                    "result": processed_result
                })
            
            # Update metrics
            if self.metrics:
                execution_time = time.time() - start_time
                api_calls = self._count_api_calls(result)
                tool_calls = self._count_tool_calls(result)
                self.metrics.update_execution(True, execution_time, api_calls, tool_calls)
            
            # Store result in enhanced memory for cross-tool access
            self.enhanced_set("react_workflow_result", processed_result, context="react_execution")
            
            # Store execution metadata for analysis
            execution_metadata = {
                "agent_name": self.agent_name,
                "execution_time": time.time() - start_time,
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "success": True
            }
            self.store_cross_tool_data(f"react_execution_{session_id}", execution_metadata, f"React execution metadata for {self.agent_name}")
            
            # Store final output if available for other agents to use
            if final_output := self._extract_final_output(result):
                self.store_cross_tool_data(f"react_final_output_{session_id}", final_output, f"Final output from {self.agent_name} React execution")
            
            self.log_success(f"Enhanced workflow completed successfully in {time.time() - start_time:.2f}s")
            return processed_result
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            if self.metrics:
                self.metrics.update_execution(False, execution_time)
            
            self.log_error(f"Enhanced workflow failed: {str(e)}")
            
            return {
                "error": str(e),
                "agent_name": self.agent_name,
                "execution_time": execution_time,
                "timestamp": datetime.now().isoformat()
            }
    
    def _process_agent_result(self, result: Dict[str, Any], start_time: float) -> Dict[str, Any]:
        """Process and enhance the agent execution result."""
        processed_result = result.copy()
        
        # Add execution metadata
        processed_result["_enhanced_metadata"] = {
            "agent_name": self.agent_name,
            "execution_time": time.time() - start_time,
            "timestamp": datetime.now().isoformat(),
            "validation_enabled": True,
            "caching_enabled": self.enable_caching
        }
        
        # Extract final output from intermediate steps
        final_output = self._extract_final_output(result)
        if final_output:
            processed_result["final_output"] = final_output
        
        # Add tool performance summary
        if "intermediate_steps" in result:
            tool_summary = self._analyze_tool_performance(result["intermediate_steps"])
            processed_result["_tool_performance"] = tool_summary
        
        return processed_result
    
    def _extract_final_output(self, result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract the final output from agent execution result."""
        if "intermediate_steps" in result:
            # Look for the final tool call output
            for action, observation in reversed(result["intermediate_steps"]):
                if hasattr(action, 'tool') and 'compile' in action.tool.lower():
                    try:
                        return self.json_handler.extract_json_from_text(observation)
                    except Exception as e:
                        self.log_warning(f"Failed to parse final output: {str(e)}")
        
        # Try to extract from final output
        if "output" in result:
            try:
                return self.json_handler.extract_json_from_text(result["output"])
            except Exception:
                pass
        
        return None
    
    def _analyze_tool_performance(self, intermediate_steps: List[tuple]) -> Dict[str, Any]:
        """Analyze tool performance from intermediate steps."""
        tool_calls = {}
        
        for action, observation in intermediate_steps:
            tool_name = getattr(action, 'tool', 'unknown')
            
            if tool_name not in tool_calls:
                tool_calls[tool_name] = {
                    "calls": 0,
                    "successes": 0,
                    "failures": 0
                }
            
            tool_calls[tool_name]["calls"] += 1
            
            # Check if call was successful (no error in observation)
            if isinstance(observation, str) and "error" not in observation.lower():
                tool_calls[tool_name]["successes"] += 1
            else:
                tool_calls[tool_name]["failures"] += 1
        
        return {
            "total_tools_used": len(tool_calls),
            "total_tool_calls": sum(t["calls"] for t in tool_calls.values()),
            "tool_breakdown": tool_calls
        }
    
    def _count_api_calls(self, result: Dict[str, Any]) -> int:
        """Estimate API calls from result."""
        # Simple estimation based on intermediate steps
        if "intermediate_steps" in result:
            return len(result["intermediate_steps"]) + 1  # +1 for initial call
        return 1
    
    def _count_tool_calls(self, result: Dict[str, Any]) -> int:
        """Count tool calls from result."""
        if "intermediate_steps" in result:
            return len(result["intermediate_steps"])
        return 0
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report for this agent."""
        if not self.metrics:
            return {"message": "Performance tracking not enabled"}
        
        agent_metrics = self.metrics.get_summary()
        
        # Add tool-level metrics
        tool_report = enhanced_tool_validator.get_tool_performance_report()
        agent_tools = {k: v for k, v in tool_report.get("tools", {}).items() 
                      if k.startswith(f"{self.agent_name}:")}
        
        return {
            "agent_name": self.agent_name,
            "agent_metrics": agent_metrics,
            "tool_metrics": agent_tools,
            "validation_stats": self.hybrid_validator.get_validation_stats(),
            "recommendations": self._generate_performance_recommendations()
        }
    
    def _generate_performance_recommendations(self) -> List[str]:
        """Generate performance improvement recommendations."""
        recommendations = []
        
        if not self.metrics:
            return ["Enable performance tracking for detailed recommendations"]
        
        success_rate = self.metrics.get_success_rate()
        avg_time = self.metrics.avg_execution_time
        
        if success_rate < 90:
            recommendations.append("Consider reviewing tool input formats to improve success rate")
        
        if avg_time > 30:
            recommendations.append("Consider enabling more aggressive caching to reduce execution time")
        
        if self.metrics.total_api_calls > self.metrics.total_tool_calls * 2:
            recommendations.append("API calls seem high - review for optimization opportunities")
        
        # Check validation distribution
        validation_total = sum(self.metrics.validation_successes.values())
        if validation_total > 0:
            strict_rate = self.metrics.validation_successes["strict"] / validation_total
            if strict_rate < 0.5:
                recommendations.append("Improve prompt engineering to achieve more strict validations")
        
        return recommendations or ["Performance looks good - no specific recommendations"]
    
    def clear_cache(self):
        """Clear the agent's response cache."""
        enhanced_tool_validator.clear_cache()
        self.log_info("Agent cache cleared")
    
    def reset_metrics(self):
        """Reset performance metrics."""
        if self.metrics:
            self.metrics = ReactAgentMetrics()
            enhanced_tool_validator.reset_metrics()
            self.log_info("Agent metrics reset") 