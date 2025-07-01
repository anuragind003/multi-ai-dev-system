"""
Enhanced BRD Analyst ReAct Agent with Hybrid Validation and API Token Optimization

Uses a step-by-step reasoning and acting approach with:
- 3-layer hybrid validation system
- API token usage optimization
- Enhanced error recovery
- Performance tracking and caching
"""

import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
import json

from langchain import hub
from langchain.agents import AgentExecutor, create_json_chat_agent
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.retrievers import BaseRetriever
from langchain_core.tools import BaseTool
from langchain.agents.format_scratchpad import format_to_openai_function_messages
from langchain.agents.output_parsers import OpenAIFunctionsAgentOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
import monitoring
from langchain.callbacks.base import BaseCallbackHandler
import sys
from utils.windows_safe_console import safe_print

# Local imports
from models.data_contracts import BRDRequirementsAnalysis
from agents.base_agent import BaseAgent
from tools.json_handler import JsonHandler
from utils.safe_console_callback_handler import SafeConsoleCallbackHandler

# Enhanced memory and RAG imports
from enhanced_memory_manager import create_memory_manager, EnhancedSharedProjectMemory
from rag_manager import get_rag_manager

# Enhanced imports for hybrid validation and optimization
from utils.hybrid_validator import HybridValidator, HybridValidationResult
from utils.enhanced_tool_validator import enhanced_tool_validator
from tools.enhanced_brd_analysis_tools import initialize_enhanced_brd_tools, get_enhanced_brd_analysis_tools

logger = logging.getLogger(__name__)

# SafeConsoleCallbackHandler is now imported from utils

class BRDAnalystReActAgent(BaseAgent):
    """
    Enhanced ReAct-based agent for analyzing Business Requirements Documents.
    
    Features:
    - 3-layer hybrid validation for all inputs/outputs
    - API token optimization with caching
    - Enhanced error recovery and resilience
    - Performance tracking and metrics
    - Robust tool input processing for ReAct agents
    """
    
    def __init__(self,
                 llm: BaseLanguageModel,
                 memory,
                 temperature: float,
                 rag_retriever: Optional[BaseRetriever] = None,
                 message_bus=None,
                 enable_enhanced_validation: bool = True,
                 enable_api_optimization: bool = True):
        
        super().__init__(
            llm=llm,
            memory=memory,
            agent_name="BRD Analyst ReAct Agent",
            temperature=temperature,
            rag_retriever=rag_retriever,
            message_bus=message_bus
        )
        
        # Enhanced components
        self.json_handler = JsonHandler()
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        
        # Initialize enhanced memory (inherits from BaseAgent which has enhanced memory mixin)
        self._init_enhanced_memory()
        
        # Initialize RAG context
        self.rag_manager = get_rag_manager()
        if self.rag_manager:
            self.logger.info("RAG manager available for enhanced analysis")
        else:
            self.logger.warning("RAG manager not available - proceeding without RAG context")
        
        # Hybrid validation and optimization
        self.enable_enhanced_validation = enable_enhanced_validation
        self.enable_api_optimization = enable_api_optimization
        
        if self.enable_enhanced_validation:
            self.hybrid_validator = HybridValidator(self.logger)
        
        # Performance tracking
        self.execution_metrics = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "avg_execution_time": 0.0,
            "validation_stats": {"strict": 0, "tolerant": 0, "permissive": 0, "fallback": 0},
            "api_token_savings": 0
        }
        
        self._init_agent()
    
    def _get_react_prompt(self):
        """Initializes the enhanced ReAct agent's prompt with validation guidance."""
        prompt = hub.pull("hwchase17/react-chat-json")
        
        enhanced_system_message = """You are an Enhanced Business Requirements Document (BRD) Analyst with advanced validation and optimization capabilities.

CORE PRINCIPLES:
1. You can ONLY communicate through the available tools
2. You are FORBIDDEN from providing "Final Answer" responses
3. Your ONLY way to finish tasks is by calling the designated completion tool
4. All tool calls are automatically validated using a 3-layer hybrid system

ENHANCED VALIDATION SYSTEM:
- Your inputs are automatically processed through STRICT → TOLERANT → PERMISSIVE → FALLBACK validation
- Provide well-structured JSON inputs to achieve STRICT validation (highest confidence)
- The system will auto-correct malformed inputs when possible
- Tool calls are cached to optimize API token usage

MANDATORY WORKFLOW (API Optimized):
Step 1: Call read_brd_document (cached after first call)
Step 2: Call extract_multiple_sections with ALL required sections in ONE call:
   Format: {"section_titles": ["Project Overview", "Requirements", "Goals", "Constraints", "Assumptions"]}
Step 3: Call identify_requirements_from_text with the requirements text
Step 4: Call compile_final_brd_analysis with ALL extracted data

API EFFICIENCY GUIDELINES:
- Batch operations when possible (use extract_multiple_sections instead of individual calls)
- Provide complete, structured inputs to minimize retries
- Use consistent JSON formatting for tool parameters
- The system automatically caches results to reduce redundant API calls

INPUT FORMAT REQUIREMENTS:
- Always use proper JSON format for tool inputs
- Ensure all required fields are present
- Use consistent naming and structure
- Example: {"section_titles": ["Requirements", "Goals"]} NOT ["Requirements", "Goals"]

ERROR RECOVERY:
- If a tool call fails validation, the system provides detailed feedback
- Analyze the validation error and retry with corrected input
- Never abandon the task - the validation system will help guide you to success

Your responses benefit from intelligent caching and validation - aim for structured, complete inputs."""

        for message in prompt.messages:
            if isinstance(message, SystemMessage):
                message.content = enhanced_system_message
                break
        return prompt
    
    def _init_agent(self):
        """Initialize the ReAct agent's prompt and tool definitions."""
        # This will be populated in the run() method before execution
        self.tools = []
        
        # Get the improved prompt with token efficiency instructions
        self.react_prompt = self._get_react_prompt()

    def run(self, raw_brd: str, session_id: str = None) -> Dict[str, Any]:
        """
        Enhanced BRD analysis with hybrid validation and API optimization.

        Args:
            raw_brd: The raw text content of the BRD.
            session_id: Optional session ID for WebSocket monitoring.

        Returns:
            A dictionary conforming to the BRDRequirementsAnalysis schema with validation metadata.
        """
        self.log_start(f"Starting enhanced ReAct-based BRD analysis (content length: {len(raw_brd)})")
        start_time = time.time()
        
        # Update execution metrics
        self.execution_metrics["total_executions"] += 1
        
        try:
            # Enhanced BRD content validation
            if len(raw_brd) < 100:
                self.log_warning(f"BRD content is suspiciously short ({len(raw_brd)} chars). This may affect analysis quality.")
            
            # Store BRD content in enhanced memory for cross-tool access
            self.enhanced_set("raw_brd_content", raw_brd, context="brd_analysis")
            self.store_cross_tool_data("brd_content", raw_brd, "Raw BRD content for analysis")
            
            # Check for cached analysis first (if API optimization is enabled)
            if self.enable_api_optimization:
                cache_key = f"brd_analysis_{hash(raw_brd[:500])}"  # Hash first 500 chars
                cached_result = self._get_cached_analysis(cache_key)
                if cached_result:
                    self.log_info("Using cached BRD analysis - API tokens saved!")
                    self.execution_metrics["api_token_savings"] += 1
                    # Store cached result in enhanced memory too
                    self.enhanced_set("brd_analysis_result", cached_result, context="brd_analysis")
                    self.store_cross_tool_data("brd_analysis", cached_result, "Cached BRD analysis result")
                    return cached_result
            
            # Initialize the enhanced BRD tools with validation
            initialize_enhanced_brd_tools(llm=self.llm, brd_content=raw_brd)
            
            # Get enhanced tools (already include validation)
            self.tools = get_enhanced_brd_analysis_tools()
            
            # Create the agent with enhanced configuration
            agent = create_json_chat_agent(
                llm=self.llm.bind(temperature=self.default_temperature),
                tools=self.tools,
                prompt=self.react_prompt
            )            # Create the AgentExecutor with callback handler for monitoring
            callbacks = []
            
            # Add our enhanced console callback for detailed progress monitoring
            from utils.safe_console_callback_handler import create_detailed_callback
            callbacks.append(create_detailed_callback(max_output_length=3000))  # Show full tool outputs
            
            # Add WebSocket callback if session_id is provided
            if session_id:
                try:
                    from multi_ai_dev_system.utils.websocket_callback import create_websocket_callback
                    websocket_callback = create_websocket_callback(session_id, self.agent_name)
                    callbacks.append(websocket_callback)
                except ImportError:
                    self.log_warning("WebSocket callback not available, using console callback only")
            
            self.log_info("Console output enabled: You will see detailed tool inputs and outputs")
            
            agent_executor = AgentExecutor(
                agent=agent,
                tools=self.tools,
                verbose=False,  # Disable to prevent LangChain's StdOutCallbackHandler I/O errors
                callbacks=callbacks,  # Use our SafeConsoleCallbackHandler for output
                handle_parsing_errors=True,
                max_iterations=20,  # Increase iterations
                return_intermediate_steps=True,
                early_stopping_method="force"  # Force the agent to continue until tool calls are complete
            )

            # Set up chat history
            message_history = ChatMessageHistory()
            agent_with_chat_history = RunnableWithMessageHistory(
                agent_executor,
                lambda session_id: message_history,
                input_messages_key="input",
                history_messages_key="chat_history"
            )            # Provide a clear initial input to kick off the agent's reasoning process
            initial_input = """Analyze the Business Requirements Document (BRD) by following these EXACT steps:

STEP 1: Call read_brd_document to get the BRD content
STEP 2: Call extract_multiple_sections with ["Project Overview", "Requirements", "Goals", "Constraints", "Assumptions"]  
STEP 3: Call identify_requirements_from_text on the requirements section
STEP 4: If any sections are missing (Goals, Constraints, Assumptions, etc.), call fill_missing_brd_sections to generate them intelligently
STEP 5: Call compile_final_brd_analysis with all extracted and generated data

CRITICAL DATA MAPPING FOR STEP 5:
When calling compile_final_brd_analysis, you MUST map the extracted sections to the correct field names:
- "Project Overview" section → use for "project_summary" field
- Extracted project title/name → use for "project_name" field  
- "Requirements" section → process into structured "requirements" array
- "Goals" section → use for "project_goals" field
- "Constraints" section → use for "constraints" field
- "Assumptions" section → use for "assumptions" field

DO NOT pass raw section data like {"Project Overview": "text"} - instead map it properly to the expected fields.

IMPORTANT NOTES:
- The system can intelligently fill missing sections like Goals, Constraints, Assumptions, and Risks using AI
- If you find sections are missing, use the fill_missing_brd_sections tool to generate appropriate content
- Always aim for a complete BRD analysis even if the original document is incomplete
- The compile_final_brd_analysis tool will automatically extract project name from BRD content if not provided

CRITICAL: You MUST call compile_final_brd_analysis as your FINAL action. DO NOT provide a "Final Answer" - this will cause failure!

Start with step 1 now."""
            
            # Wrap the execution with proper monitoring
            with monitoring.agent_trace_span(self.agent_name, "react_brd_analysis"):
                # Invoke the agent
                result = agent_with_chat_history.invoke(
                    {"input": initial_input},
                    config={"configurable": {"session_id": "brd_analysis_session"}}
                )
            
            # The final answer should be the result of the `compile_final_brd_analysis` tool.
            # We extract it from the intermediate steps.
            final_analysis = None
            if "intermediate_steps" in result:
                for action, observation in reversed(result["intermediate_steps"]):
                    if action.tool == "compile_final_brd_analysis":
                        try:
                            final_analysis = self.json_handler.extract_json_from_text(observation)
                            break
                        except Exception as e:
                            self.log_warning(f"Failed to parse compile_final_brd_analysis output: {str(e)}")
              # If we couldn't find it in the intermediate steps, try the final output
            if not final_analysis and "output" in result:
                try:
                    # Check if the output mentions not calling the tool
                    output_text = result["output"]
                    if "compile_final_brd_analysis" not in output_text:
                        self.log_warning("Agent did not call compile_final_brd_analysis tool. Attempting manual call...")
                        # Try to extract information from the agent's final text and manually call the tool
                        final_analysis = self._extract_analysis_from_text(output_text)
                    else:
                        final_analysis = self.json_handler.extract_json_from_text(result["output"])
                except Exception as e:
                    self.log_warning(f"Failed to parse agent output as JSON: {str(e)}")
            
            if final_analysis:
                # Log execution time and completion
                duration = time.time() - start_time
                self.log_success(f"ReAct BRD analysis completed in {duration:.2f}s.")
                
                # Cache the result if API optimization is enabled
                if self.enable_api_optimization:
                    self._cache_analysis(cache_key, final_analysis)
                
                # Store result in enhanced memory for cross-tool access
                self.enhanced_set("brd_analysis_result", final_analysis, context="brd_analysis")
                self.store_cross_tool_data("brd_analysis", final_analysis, "BRD analysis result for other agents")
                
                # Update success metrics
                self.execution_metrics["successful_executions"] += 1
                self._update_validation_stats(final_analysis)
                
                # Save to memory
                if self.memory:
                    self.memory.store_agent_activity(
                        agent_name=self.agent_name,
                        activity_type="brd_analysis",
                        prompt="[BRD Analysis]",
                        response=f"Project: {final_analysis.get('project_name', 'Unknown')}",
                        metadata={"execution_time": duration, "requirements_count": len(final_analysis.get("requirements", []))}
                    )
                    
                    # IMPORTANT: Store the BRD analysis in shared memory for downstream agents
                    try:
                        # Use enhanced memory operations for better cross-tool communication
                        if hasattr(self, 'enhanced_set'):
                            # Store in multiple contexts for maximum accessibility
                            self.enhanced_set("brd_analysis", final_analysis, context="cross_tool")
                            self.enhanced_set("requirements_analysis", final_analysis, context="cross_tool")
                            self.enhanced_set("project_requirements", final_analysis, context="cross_tool")
                            self.store_cross_tool_data("brd_analysis", final_analysis, "Complete BRD analysis for downstream agents")
                            self.log_info("Stored BRD analysis in enhanced memory for cross-tool access")
                        else:
                            # Fallback to basic memory
                            self.memory.set("brd_analysis", final_analysis)
                            self.log_info("Stored BRD analysis in basic shared memory")
                    except Exception as memory_error:
                        self.log_warning(f"Failed to store BRD analysis in memory: {memory_error}")
                        # Emergency fallback - try basic memory
                        try:
                            if hasattr(self, 'memory') and self.memory:
                                self.memory.set("brd_analysis", final_analysis)
                                self.log_info("Emergency fallback: stored in basic memory")
                        except Exception as fallback_error:
                            self.log_error(f"Complete memory storage failure: {fallback_error}")
                  # Log analyzed project name
                self.log_info(f"Analyzed project: '{final_analysis.get('project_name', 'Unknown')}'")
                self.log_info(f"Requirements extracted: {len(final_analysis.get('requirements', []))}")
                
                # Publish BRD analysis completion event
                if hasattr(self, 'message_bus') and self.message_bus:
                    try:
                        self.message_bus.publish("brd.analysis.complete", {
                            "project_name": final_analysis.get('project_name', 'Unknown'),
                            "requirements_count": len(final_analysis.get('requirements', [])),
                            "analysis": final_analysis,
                            "status": "success",
                            "agent": getattr(self, 'agent_name', 'BRDAnalystReActAgent'),
                            "timestamp": datetime.now().isoformat()
                        })
                        self.log_info("Published brd.analysis.complete event")
                    except Exception as publish_error:
                        self.log_warning(f"Failed to publish brd.analysis.complete event: {publish_error}")
                
                return final_analysis
            else:
                self.log_warning("ReAct agent finished without producing a valid JSON output. Using fallback.")
                return self.get_default_response()

        except Exception as e:
            self.logger.error(f"A critical error occurred during ReAct BRD analysis: {str(e)}", exc_info=True)
            return self.get_default_response()
    
    def _process_agent_output(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the ReAct agent output to extract the final BRD analysis.
        
        Args:
            response: The raw response from the AgentExecutor
            
        Returns:
            A dictionary conforming to the BRDRequirementsAnalysis schema
        """
        # Check for intermediate steps
        intermediate_steps = response.get("intermediate_steps", [])
        
        # Try to find the final completed analysis result in the steps
        final_result = response.get("output", "")
        
        # Check if any step used compile_final_brd_analysis which should have the complete result
        for step in reversed(intermediate_steps):  # Start from the end to get the latest
            action, observation = step
            tool_name = action.tool if hasattr(action, "tool") else str(action)
            
            if "compile_final_brd_analysis" in tool_name:
                try:
                    # This should be our complete analysis
                    json_result = self.json_handler.extract_json_from_text(observation)
                    if json_result:
                        self.log_info("Found final BRD analysis in compile_final_brd_analysis step")
                        return json_result
                except Exception as e:
                    self.log_warning(f"Error extracting JSON from compile_final_brd_analysis: {str(e)}")
        
        # If we couldn't find it in the steps, try to extract from the final output
        try:
            json_result = self.json_handler.extract_json_from_text(final_result)
            if json_result:
                self.log_info("Found final BRD analysis in agent's output")
                return json_result
        except Exception as e:
            self.log_warning(f"Error extracting JSON from final output: {str(e)}")
        
        # If we still don't have a valid result, validate with Pydantic and return what we have
        try:
            # Check if response.output is a string that could be JSON
            if isinstance(response.get("output"), str):
                json_result = self.json_handler.extract_json_from_text(response["output"])
                if json_result:
                    # Validate with Pydantic model
                    validated_result = BRDRequirementsAnalysis(**json_result)
                    self.log_info("Validated output with Pydantic model")
                    return validated_result.dict()
        except Exception as e:
            self.log_error(f"Error validating output with Pydantic: {str(e)}")
        
        # If all else fails, return a default response
        self.log_warning("Could not extract valid BRD analysis result, returning default response")
        return self.get_default_response()
    
    def get_default_response(self) -> Dict[str, Any]:
        """
        Returns a default, Pydantic-validated response structure when analysis fails.
        """
        # Create a response that clearly indicates this is a fallback
        default_response = BRDRequirementsAnalysis(
            project_name="Analysis Failed - Please check logs",
            project_summary="No summary available - BRD analysis failed. Please check the logs for details.",
            project_goals=["Rerun BRD analysis to extract actual goals."],
            target_audience=["Unknown - Analysis failed"],
            business_context="Business context could not be determined due to analysis failure.",
            requirements=[],
            constraints=["Analysis failed. Please check logs and rerun."],
            assumptions=[],
            risks=[],
            domain_specific_details={},  # Add this field
            quality_assessment={
                "completeness_score": 0, 
                "clarity_score": 0,
                "consistency_score": 0, 
                "testability_score": 0,
                "overall_quality_score": 0, 
                "improvement_recommendations": ["Rerun analysis after checking logs."]
            },
            gap_analysis={
                "missing_information": ["Complete analysis failed. Please check logs."],
                "ambiguities": [],
                "inconsistencies": [],
                "implementation_risks": []
            }
        )
        self.log_warning("Using default BRD analysis response due to processing failure.")
        return default_response.dict()
    
    def _extract_analysis_from_text(self, text: str) -> Dict[str, Any]:
        """
        Extract BRD analysis information from agent text when it doesn't call the compile_final_brd_analysis tool.
        
        Args:
            text: The agent's text output
            
        Returns:
            A dictionary with extracted analysis information
        """
        self.log_info("Attempting to extract analysis from agent text output")
        
        try:
            # Use the LLM to convert the text into structured format
            conversion_prompt = f"""Convert the following BRD analysis text into a structured JSON format that matches the BRDRequirementsAnalysis schema:

TEXT TO CONVERT:
{text}

Convert this into a JSON object with these fields:
- project_name: string
- project_summary: string  
- project_goals: array of strings
- target_audience: array of strings
- business_context: string
- requirements: array of requirement objects with id, title, description, category, priority
- constraints: array of strings
- assumptions: array of strings
- risks: array of strings
- domain_specific_details: object
- quality_assessment: object with scores and recommendations
- gap_analysis: object with missing_information, ambiguities, etc.

Return ONLY the JSON object:"""

            response = self.llm.bind(temperature=0.1).invoke(conversion_prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Try to extract JSON from the response
            json_result = self.json_handler.extract_json_from_text(content)
            if json_result:
                self.log_info("Successfully extracted analysis from text using LLM conversion")
                return json_result
                
        except Exception as e:
            self.log_warning(f"LLM conversion failed: {str(e)}")
        
        # Fallback: create a basic structure from the text
        return {
            "project_name": "Extracted from Agent Output",
            "project_summary": text[:500] + "..." if len(text) > 500 else text,
            "project_goals": [],
            "target_audience": [],
            "business_context": "Extracted from agent analysis",
            "requirements": [],
            "constraints": [],
            "assumptions": [],
            "risks": [],
            "domain_specific_details": {},
            "quality_assessment": {
                "completeness_score": 5,
                "clarity_score": 5,
                "consistency_score": 5,
                "testability_score": 5,
                "overall_quality_score": 5,
                "improvement_recommendations": ["Agent did not use proper tool - manual extraction performed"]
            },
            "gap_analysis": {
                "missing_information": ["Agent did not call compile_final_brd_analysis tool"],
                "ambiguities": [],
                "inconsistencies": [],
                "implementation_risks": []
            }
        }
    
    def _enhance_tools_with_validation(self, tools: List[callable]) -> List[callable]:
        """Enhance tools with hybrid validation wrappers."""
        enhanced_tools = []
        
        for tool in tools:
            tool_name = getattr(tool, 'name', tool.__name__)
            
            # Define expected fields for each tool
            expected_fields = self._get_expected_fields_for_tool(tool_name)
            
            # Create enhanced version with validation
            enhanced_tool = enhanced_tool_validator.create_validated_tool(
                tool_function=tool,
                tool_name=f"BRD:{tool_name}",
                required_fields=expected_fields,
                enable_caching=self.enable_api_optimization,
                max_retries=2
            )
            
            enhanced_tools.append(enhanced_tool)
        
        self.log_info(f"Enhanced {len(enhanced_tools)} tools with hybrid validation")
        return enhanced_tools
    
    def _get_expected_fields_for_tool(self, tool_name: str) -> List[str]:
        """Get expected fields for each tool based on its function."""
        field_mapping = {
            "extract_multiple_sections": ["section_titles"],
            "extract_text_section": ["section_title"],
            "identify_requirements_from_text": ["text"],
            "summarize_section": ["section_text"],
            "compile_final_brd_analysis": []  # All fields optional with defaults
        }
        
        return field_mapping.get(tool_name, [])
    
    def _get_cached_analysis(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached analysis result if available."""
        # Simple in-memory cache (could be enhanced with persistent storage)
        if not hasattr(self, '_analysis_cache'):
            self._analysis_cache = {}
        
        cached_entry = self._analysis_cache.get(cache_key)
        if cached_entry:
            cache_time, result = cached_entry
            # Cache valid for 1 hour
            if time.time() - cache_time < 3600:
                return result
            else:
                del self._analysis_cache[cache_key]
        
        return None
    
    def _cache_analysis(self, cache_key: str, result: Dict[str, Any]) -> None:
        """Cache analysis result with timestamp."""
        if not hasattr(self, '_analysis_cache'):
            self._analysis_cache = {}
        
        self._analysis_cache[cache_key] = (time.time(), result)
        
        # Limit cache size
        if len(self._analysis_cache) > 10:
            # Remove oldest entry
            oldest_key = min(self._analysis_cache.keys(), 
                           key=lambda k: self._analysis_cache[k][0])
            del self._analysis_cache[oldest_key]
    
    def _update_validation_stats(self, result: Dict[str, Any]) -> None:
        """Update validation statistics from result metadata."""
        if "_validation_metadata" in result:
            metadata = result["_validation_metadata"]
            level_used = metadata.get("level_used", "unknown")
            
            if level_used in self.execution_metrics["validation_stats"]:
                self.execution_metrics["validation_stats"][level_used] += 1
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics for this agent."""
        total_exec = self.execution_metrics["total_executions"]
        
        if total_exec == 0:
            return {"message": "No executions recorded yet"}
        
        success_rate = (self.execution_metrics["successful_executions"] / total_exec) * 100
        
        # Get tool-level metrics
        tool_report = enhanced_tool_validator.get_tool_performance_report()
        brd_tools = {k: v for k, v in tool_report.get("tools", {}).items() 
                    if k.startswith("BRD:")}
        
        return {
            "agent_name": self.agent_name,
            "execution_summary": {
                "total_executions": total_exec,
                "successful_executions": self.execution_metrics["successful_executions"],
                "failed_executions": self.execution_metrics["failed_executions"],
                "success_rate": f"{success_rate:.1f}%",
                "avg_execution_time": f"{self.execution_metrics['avg_execution_time']:.2f}s"
            },
            "validation_distribution": self.execution_metrics["validation_stats"],
            "api_optimization": {
                "caching_enabled": self.enable_api_optimization,
                "cache_hits": self.execution_metrics["api_token_savings"],
                "estimated_token_savings": self.execution_metrics["api_token_savings"] * 1000  # Estimate
            },
            "tool_performance": brd_tools,
            "recommendations": self._generate_performance_recommendations()
        }
    
    def _generate_performance_recommendations(self) -> List[str]:
        """Generate performance improvement recommendations."""
        recommendations = []
        
        total_exec = self.execution_metrics["total_executions"]
        if total_exec == 0:
            return ["No data available for recommendations"]
        
        success_rate = (self.execution_metrics["successful_executions"] / total_exec) * 100
        
        if success_rate < 90:
            recommendations.append("Consider reviewing BRD input quality to improve success rate")
        
        validation_stats = self.execution_metrics["validation_stats"]
        total_validations = sum(validation_stats.values())
        
        if total_validations > 0:
            strict_rate = validation_stats.get("strict", 0) / total_validations
            if strict_rate < 0.7:
                recommendations.append("Improve input formatting to achieve more strict validations")
        
        if self.execution_metrics["api_token_savings"] < total_exec * 0.1:
            recommendations.append("Enable caching to improve API token efficiency")
        
        return recommendations or ["Performance looks good - no specific recommendations"]
    
    def clear_cache(self) -> None:
        """Clear the agent's cache."""
        if hasattr(self, '_analysis_cache'):
            self._analysis_cache.clear()
        enhanced_tool_validator.clear_cache()
        self.log_info("Agent cache cleared")
    
    def reset_metrics(self) -> None:
        """Reset performance metrics."""
        self.execution_metrics = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "avg_execution_time": 0.0,
            "validation_stats": {"strict": 0, "tolerant": 0, "permissive": 0, "fallback": 0},
            "api_token_savings": 0
        }
        self.log_info("Agent metrics reset")
