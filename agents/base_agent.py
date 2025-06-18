"""
Base Agent class for the Multi-AI Development System.
Provides common functionality for all specialized agents.
"""
from typing import Dict, Any, Optional, List, Type
from abc import ABC, abstractmethod
from datetime import datetime
import traceback  # Add missing traceback import
import logging  # Add missing logging import
import os  # Add missing os import
import sys  # Add missing sys import
import time  # Add missing time import
import re  # Add missing re import
import json  # Add missing json import
import copy

# Fix import paths - add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Now import from project root
from langchain_core.language_models import BaseLanguageModel
from langchain_core.retrievers import BaseRetriever
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import JsonOutputParser, PydanticOutputParser
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel  # Add Pydantic import

# Project imports
import monitoring
from agent_temperatures import get_agent_temperature
from message_bus import MessageBus
from tools.json_handler import JsonHandler

# Initialize module-level logger
logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """
    Abstract base class for all AI agents in the system.
    Provides standardized LLM interaction, error handling, and monitoring.
    
    Enhanced with:
    - Adaptive RAG integration with query optimization
    - Multi-stage processing with reasoning
    - Self-reflection and optimization capabilities
    - Improved error recovery with graceful degradation
    - Performance analysis and optimization
    - Pydantic-based structured output generation
    """
    
    def __init__(
        self, 
        llm: BaseLanguageModel, 
        memory, 
        agent_name: str,
        temperature: float = 0.2,
        rag_retriever: Optional[BaseRetriever] = None,
        message_bus: Optional[MessageBus] = None,
        **kwargs
    ):
        self.llm = llm 
        self.memory = memory
        self.agent_name = agent_name
        self.default_temperature = temperature
        self.rag_retriever = rag_retriever
        # Set message_bus from parameter rather than initialize to None
        self.message_bus = message_bus
        
        # Ensure logger is initialized
        import logging
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        
        # Execution tracking
        self.execution_stats = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "total_execution_time": 0.0,
            "last_execution_time": 0.0,
            "last_execution_status": "not_started",
            "average_response_quality": 0.0
        }
        
        # Initialize JSON parser
        self.json_parser = JsonOutputParser()
        
        # Initialize prompt template (will be set by subclasses)
        self.prompt_template = None
        
        # Initialize working memory for complex reasoning
        self.working_memory = {}
        
        # Initialize self-reflection data
        self.reflection_data = {
            "strengths": [],
            "improvement_areas": [],
            "adaptation_history": []
        }
        
        # Add this back - but implement as a separate method in BaseAgent
        self._initialize_specialized_prompts()

    def log_start(self, message: str):
        """Log start of agent execution."""
        monitoring.log_agent_activity(self.agent_name, message, "START")
    
    def log_info(self, message: str):
        """Log informational message."""
        monitoring.log_agent_activity(self.agent_name, message, "INFO")
    def log_success(self, message: str):
        """Log successful completion."""
        monitoring.log_agent_activity(self.agent_name, message, "SUCCESS")
    
    def log_warning(self, message: str, exc_info=None):
        """Log a warning message with optional exception info."""
        monitoring.log_agent_activity(self.agent_name, message, "WARNING")
        if exc_info:
            logging.getLogger(__name__).warning(f"[{self.agent_name}] {message}", exc_info=exc_info)
        else:
            logging.getLogger(__name__).warning(f"[{self.agent_name}] {message}")
    
    def log_error(self, message: str, exc_info=None):
        """Log error message with optional exception info."""
        monitoring.log_agent_activity(self.agent_name, message, "ERROR")
        if exc_info:
            logging.getLogger(__name__).error(f"[{self.agent_name}] {message}", exc_info=exc_info)
    
    # ENHANCED: Improved execution monitoring with context manager
    def execute_with_monitoring(self, func, *args, **kwargs):
        """
        Execute an agent's primary function (e.g., run()) with monitoring,
        error handling, and timing.
        Temperature for LLM calls *within* func should be handled by execute_llm_chain.
        """
        task_start_time = time.time()
        
        # Extract task name if provided, otherwise use function name
        task_name = kwargs.pop('task_name', func.__name__ if hasattr(func, "__name__") else "unnamed_task")

        self.log_start(f"Executing task: {task_name}")
        self.execution_stats["total_executions"] += 1
        
        try:
            # The agent's run() or other function should use execute_llm_chain for LLM calls
            result = func(*args, **kwargs) 
            
            execution_time = time.time() - task_start_time
            self.execution_stats["successful_executions"] += 1
            self.execution_stats["last_execution_status"] = "success"
            self.log_success(f"Task '{task_name}' completed successfully in {execution_time:.2f}s.")

            # Store result in agent's memory if available
            if hasattr(self, "memory") and self.memory is not None:
                try:
                    self.memory.store_agent_result(
                        agent_name=self.agent_name,
                        result=result,
                        execution_time=execution_time,
                        metadata={"task_name": task_name, "status": "success"}
                    )
                except Exception as e:
                    self.log_warning(f"Failed to store agent result for '{task_name}': {e}")
            
            # Optionally perform self-reflection if implemented
            if hasattr(self, "_perform_self_reflection"):
                try:
                    self._perform_self_reflection(task_name, f"Execution of {task_name}", "success", execution_time)
                except Exception as e:
                    self.log_warning(f"Self-reflection failed: {e}")

            return result
            
        except Exception as e:
            execution_time = time.time() - task_start_time
            self.execution_stats["failed_executions"] += 1
            self.execution_stats["last_execution_status"] = "failed"
            tb_str = traceback.format_exc()
            self.log_error(f"Task '{task_name}' failed after {execution_time:.2f}s: {str(e)}\nTraceback: {tb_str}")

            if hasattr(self, "memory") and self.memory is not None:
                try:
                    self.memory.store_agent_result(
                        agent_name=self.agent_name,
                        result={"error": str(e), "task_name": task_name, "status": "failure"},
                        execution_time=execution_time,
                        metadata={"task_name": task_name, "status": "failure", "error_message": str(e)}
                    )
                except Exception as mem_error:
                    self.log_warning(f"Failed to store error result: {mem_error}")
            
            # Optionally perform self-reflection on failure
            if hasattr(self, "_perform_self_reflection"):
                try:
                    self._perform_self_reflection(task_name, f"Execution of {task_name}", "failure", execution_time, error=str(e))
                except Exception as reflect_error:
                    self.log_warning(f"Self-reflection on failure failed: {reflect_error}")

            # Return a default or error response structure
            if hasattr(self, 'get_default_response'):
                return self.get_default_response()
            else:
                return {"status": "error", "error_message": str(e), "task_name": task_name}
        finally:
            self.execution_stats["total_execution_time"] += (time.time() - task_start_time)
            self.execution_stats["last_execution_time"] = (time.time() - task_start_time)
    
    def _categorize_temperature(self, temperature: float) -> str:
        """Categorize temperature according to project guidelines."""
        if temperature <= 0.1:
            return "code_generation"
        elif temperature <= 0.2:
            return "analytical"
        elif temperature <= 0.4:
            return "creative"
        else:
            return "other"
    
    def _get_agent_temperature(self) -> float:
        """Get the temperature setting for this agent based on agent type."""
        # Default temperature mapping based on your guidelines
        temperature_map = {
            "BRD Analyst": 0.3,
            "Tech Stack Advisor": 0.2,
            "System Designer": 0.2,
            "Planning Agent": 0.4,
            "Code Generation Agent": 0.1,
            "Test Case Generator": 0.2,
            "Code Quality Agent": 0.1,
            "Test Validation Agent": 0.1
        }
        
        # Get temperature from map or default to 0.2 for unknown agents
        return temperature_map.get(self.agent_name, 0.2)
    
    # ENHANCED: Improved LLM chain execution with retry and multi-stage processing
    def execute_llm_chain(
        self,
        inputs: Dict[str, Any],
        output_pydantic_model: Optional[Type[BaseModel]] = None,
        max_retries: int = 2,
        additional_llm_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute LLM chain with inputs and return parsed response.
        
        If a Pydantic model is provided via output_pydantic_model, uses structured output parsing
        for more reliable results. Otherwise falls back to legacy string parsing methods.
        
        Args:
            inputs: Input parameters for the chain
            output_pydantic_model: Optional Pydantic model class for structured output parsing
            max_retries: Maximum number of retries on failure
            additional_llm_params: Additional parameters for the LLM (max_tokens, etc)
            
        Returns:
            Dict: Parsed response or default response on failure
        """
        if not self.prompt_template:
            self.log_error(f"Prompt template not initialized for agent {self.agent_name}")
            raise ValueError(f"{self.agent_name} prompt template not initialized")

        # --- STRUCTURED OUTPUT PATH (New) ---
        if output_pydantic_model:
            self.log_info(f"Using structured PydanticOutputParser for {output_pydantic_model.__name__}")
            parser = PydanticOutputParser(pydantic_object=output_pydantic_model)
            
            # Store original template to restore it later if needed
            original_template = self.prompt_template
            
            try:
                # Add format instructions to the prompt
                # Handle different prompt types (PromptTemplate vs ChatPromptTemplate)
                if isinstance(self.prompt_template, ChatPromptTemplate):
                    # For chat templates, we'll add format instructions at the end of system message
                    # or create a new system message with instructions
                    format_instructions = parser.get_format_instructions()
                    messages = self.prompt_template.messages
                    
                    # Find system message or create new one
                    has_system = any(isinstance(m, SystemMessage) for m in messages if hasattr(m, '_message_type'))
                    
                    if has_system:
                        # Modify existing system message
                        new_messages = []
                        for message in messages:
                            if hasattr(message, '_message_type') and isinstance(message, SystemMessage):
                                # Append format instructions to system message
                                content = message.content + "\n\nOUTPUT FORMAT INSTRUCTIONS:\n" + format_instructions
                                new_messages.append(SystemMessage(content=content))
                            else:
                                new_messages.append(message)
                        structured_prompt = ChatPromptTemplate.from_messages(new_messages)
                    else:
                        # Add new system message with format instructions
                        new_messages = [SystemMessage(content=f"OUTPUT FORMAT INSTRUCTIONS:\n{format_instructions}")] + list(messages)
                        structured_prompt = ChatPromptTemplate.from_messages(new_messages)
                else:
                    # For regular prompt templates
                    structured_prompt = original_template.partial(
                        format_instructions=parser.get_format_instructions()
                    )
            except Exception as e:
                self.log_warning(f"Failed to add format instructions to prompt: {e}")
                self.log_info("Continuing with standard Pydantic parsing")
                structured_prompt = original_template
            
            for attempt in range(max_retries + 1):
                try:
                    # Calculate temperature with retry adjustment if needed
                    retry_temp_adjustment = min(0.3, 0.1 * attempt) if attempt > 0 else 0.0
                    adjusted_temp = min(1.0, self.default_temperature + retry_temp_adjustment)
                    
                    # Prepare binding arguments
                    binding_args = {"temperature": adjusted_temp}
                    
                    # Special handling for Gemini models
                    is_gemini = False
                    model_name = "unknown"
                    
                    if hasattr(self.llm, 'model_name') and isinstance(self.llm.model_name, str):
                        model_name = self.llm.model_name.lower()
                        is_gemini = 'gemini' in model_name
                    elif hasattr(self.llm, 'client') and hasattr(self.llm.client, 'model'):
                        model_name = str(getattr(self.llm.client, 'model', '')).lower()
                        is_gemini = 'gemini' in model_name
                    
                    if is_gemini:
                        self.log_info("Configuring Gemini for structured output")
                        generation_config = {
                            "response_mime_type": "application/json",
                            "temperature": adjusted_temp
                        }
                        
                        # Add max tokens if specified
                        if additional_llm_params and "max_tokens" in additional_llm_params:
                            generation_config["max_output_tokens"] = additional_llm_params["max_tokens"]
                            
                        binding_args["generation_config"] = generation_config
                        
                        # For Gemini models, ensure safety settings are BLOCK_NONE
                        if hasattr(self.llm, 'client') and hasattr(self.llm.client, 'safety_settings'):
                            try:
                                from langchain_google_genai import HarmCategory, HarmBlockThreshold
                                safety_settings = {
                                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE
                                }
                                binding_args["safety_settings"] = safety_settings
                            except ImportError:
                                self.log_warning("Could not import HarmCategory/HarmBlockThreshold")
                    
                    # Add any additional parameters
                    if additional_llm_params:
                        filtered_params = {k: v for k, v in additional_llm_params.items() if v is not None}
                        binding_args.update(filtered_params)
                    
                    # Bind parameters to LLM
                    llm_to_invoke = self.llm.bind(**binding_args)
                    
                    # Add retry context if needed
                    current_inputs = inputs.copy()
                    if attempt > 0:
                        current_inputs["_retry_context"] = (
                            f"This is retry attempt {attempt+1}. Previous attempts failed. "
                            f"Please ensure your response follows the required format exactly."
                        )
                    
                    # Setup invoke config for tracing
                    invoke_config = {
                        "run_name": f"{self.agent_name}_structured_chain_attempt_{attempt}",
                        "tags": [self.agent_name, "structured_output"],
                        "agent_context": self.agent_name,
                        "temperature_used": adjusted_temp,
                        "model_name": model_name,
                        "attempt": attempt + 1
                    }
                    
                    # Create and execute the structured chain
                    chain = structured_prompt | llm_to_invoke | parser
                    
                    # Execute the chain and get Pydantic object
                    pydantic_result = chain.invoke(current_inputs, config=invoke_config)
                    
                    self.log_success(f"Successfully parsed structured output on attempt {attempt+1}")
                    
                    # Store success in agent memory if available
                    if hasattr(self, "memory") and self.memory is not None:
                        try:
                            prompt_str = str(structured_prompt.format_messages(**current_inputs)) if hasattr(structured_prompt, "format_messages") else str(structured_prompt.format(**current_inputs))
                            self.memory.store_agent_activity(
                                agent_name=self.agent_name,
                                activity_type="structured_chain_success",
                                prompt=prompt_str,
                                response=pydantic_result.json(),
                                metadata={
                                    "model": output_pydantic_model.__name__,
                                    "attempt": attempt + 1,
                                    "temperature": adjusted_temp
                                }
                            )
                        except Exception as e:
                            self.log_warning(f"Failed to store agent activity: {e}")
                    
                    # Return as dictionary to maintain compatibility
                    return pydantic_result.dict()
                    
                except Exception as e:
                    last_error = str(e)
                    tb_str = traceback.format_exc()
                    self.log_warning(f"Structured output attempt {attempt+1}/{max_retries+1} failed: {last_error}")
                    
                    if attempt >= max_retries:
                        self.log_error(f"Structured chain execution definitively failed after {max_retries+1} attempts.")
                        
                        # Store final failure in memory if available
                        if hasattr(self, "memory") and self.memory is not None:
                            try:
                                prompt_str = str(structured_prompt.format_messages(**inputs)) if hasattr(structured_prompt, "format_messages") else str(structured_prompt.format(**inputs))
                                self.memory.store_agent_activity(
                                    agent_name=self.agent_name,
                                    activity_type="structured_chain_failure",
                                    prompt=prompt_str,
                                    response=f"Error after {attempt+1} attempts: {last_error}",
                                    metadata={
                                        "model": output_pydantic_model.__name__,
                                        "max_retries_reached": True,
                                        "final_error": last_error
                                    }
                                )
                            except Exception as e:
                                self.log_warning(f"Failed to store agent failure activity: {e}")
                        
                        return self.get_default_response()
                    
                    # Wait before retrying
                    time.sleep(1)
            
            # This should not be reached if max_retries is handled correctly
            self.log_error(f"Structured chain execution loop exited unexpectedly")
            return self.get_default_response()

        # --- LEGACY PATH (Original implementation) ---
        else:
            self.log_info("Using legacy string-based JSON parsing")
            retries = 0
            last_error = None

            while retries <= max_retries:
                # Calculate retry temperature adjustment if needed
                retry_temp_adjustment = 0.0
                if retries > 0:
                    self.log_info(f"Retry attempt {retries}/{max_retries} for task. Previous error: {last_error}")
                    # Simple retry temperature adjustment: slightly increase for more "creativity"
                    retry_temp_adjustment = min(0.3, 0.1 * retries)
                    self.log_info(f"Adjusting temperature for retry by +{retry_temp_adjustment:.2f}")

                # Prepare binding arguments
                binding_args = {}
                
                # Only add temperature if we need a retry adjustment
                if retry_temp_adjustment > 0:
                    # Start with default and add adjustment
                    adjusted_temp = min(1.0, self.default_temperature + retry_temp_adjustment)
                    binding_args["temperature"] = adjusted_temp
                
                # ENHANCED: Detect if model is Gemini and add native JSON mode
                is_gemini = False
                model_name = "unknown"
                
                # Check for Gemini model
                if hasattr(self.llm, 'model_name') and isinstance(self.llm.model_name, str):
                    model_name = self.llm.model_name.lower()
                    is_gemini = 'gemini' in model_name
                elif hasattr(self.llm, 'client') and hasattr(self.llm.client, 'model'):
                    model_name = str(getattr(self.llm.client, 'model', '')).lower()
                    is_gemini = 'gemini' in model_name
                    
                self.log_info(f"Detected model: {model_name}")
                
                # ADDED: Configure native JSON mode for Gemini models
                if is_gemini:
                    self.log_info("Enabling native JSON mode for Gemini model")
                    generation_config = {
                        "response_mime_type": "application/json",
                        "temperature": self.default_temperature + retry_temp_adjustment if retry_temp_adjustment > 0 else self.default_temperature
                    }
                    
                    # Add max tokens if specified
                    if additional_llm_params and "max_tokens" in additional_llm_params:
                        generation_config["max_output_tokens"] = additional_llm_params["max_tokens"]
                        
                    binding_args["generation_config"] = generation_config
                    
                    # For Gemini models, ensure safety settings are BLOCK_NONE
                    if hasattr(self.llm, 'client') and hasattr(self.llm.client, 'safety_settings'):
                        self.log_info("Setting BLOCK_NONE safety settings for Gemini")
                        try:
                            from langchain_google_genai import HarmCategory, HarmBlockThreshold
                            safety_settings = {
                                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE
                            }
                            binding_args["safety_settings"] = safety_settings
                        except ImportError:
                            self.log_warning("Could not import HarmCategory/HarmBlockThreshold")
                
                # Add any additional parameters
                if additional_llm_params:
                    # Filter out None values
                    filtered_params = {k: v for k, v in additional_llm_params.items() if v is not None}
                    binding_args.update(filtered_params)
            
            try:
                # Only bind parameters if we have any to bind
                llm_to_invoke = self.llm
                if binding_args:
                    self.log_info(f"Binding parameters to LLM: {binding_args}")
                    llm_to_invoke = self.llm.bind(**binding_args)
                else:
                    self.log_info(f"Using default agent temperature: {self.default_temperature:.2f}")
            
                # Construct the chain
                chain = self.prompt_template | llm_to_invoke
                
                # Add retry context if needed
                current_inputs = inputs.copy()
                if retries > 0 and last_error:
                    current_inputs["_retry_context"] = (
                        f"This is retry attempt {retries}. The previous attempt failed with error: {last_error}. "
                        f"Please carefully review the instructions and output format. Ensure the response is valid JSON."
                    )

                # Store the formatted prompt for potential model escalation
                try:
                    # Get the formatted prompt
                    if hasattr(self.prompt_template, "format_messages"):
                        formatted_prompt = self.prompt_template.format_messages(**current_inputs)
                    else:
                        formatted_prompt = self.prompt_template.format(**current_inputs)
                    
                    # Store it for potential escalation
                    self.last_json_prompt = formatted_prompt
                except Exception as format_error:
                    self.log_warning(f"Failed to store prompt for escalation: {format_error}")

                # LangChain's standard way to pass runtime config to `invoke`
                invoke_config = {
                    "run_name": f"{self.agent_name}_llm_chain_attempt_{retries}",
                    "tags": [self.agent_name, "llm_chain_execution"],
                    "agent_context": self.agent_name,
                    "temperature_used": adjusted_temp if retry_temp_adjustment > 0 else self.default_temperature,
                    "model_name": model_name
                }
                
                # Invoke the chain
                response = chain.invoke(current_inputs, config=invoke_config)
                
                # Process response
                response_content = response.content if hasattr(response, 'content') else str(response)
                
                # ENHANCED: Check for empty response early
                if not response_content or response_content.strip() == "":
                    self.log_warning("Empty response received from LLM")
                    
                    # Try model escalation if we have the JSON handler configured
                    if hasattr(self, "last_json_prompt") and "JsonHandler" in globals():
                        self.log_info("Attempting model escalation for empty response")
                        escalation_result = JsonHandler.auto_escalate_model_for_json(
                            {}, 
                            self.llm,
                            self.last_json_prompt,
                            model_name
                        )
                        
                        if escalation_result and isinstance(escalation_result, dict) and len(escalation_result) > 0:
                            self.log_success("Model escalation returned valid result")
                            return escalation_result
                            
                # Parse the response with fallbacks
                parsed_response = self._parse_response_with_fallbacks(response_content)
                
                # Log success (or parsing issues)
                if "_extraction_note" in parsed_response or "parsing_status" in parsed_response:
                    self.log_warning(f"LLM response parsed with fallbacks. Note: {parsed_response.get('_extraction_note', parsed_response.get('parsing_status'))}")
                else:
                    self.log_info("LLM response successfully parsed.")
                
                # Store activity if memory available
                if hasattr(self, "memory") and self.memory is not None:
                    try:
                        prompt_str = str(self.prompt_template.format_messages(**current_inputs)) if hasattr(self.prompt_template, "format_messages") else str(self.prompt_template.format(**current_inputs))
                        self.memory.store_agent_activity(
                            agent_name=self.agent_name,
                            activity_type="llm_chain_execution_attempt",
                            prompt=prompt_str,
                            response=response_content,
                            metadata={
                                "attempt": retries,
                                "temperature": adjusted_temp if retry_temp_adjustment > 0 else self.default_temperature,
                                "params": additional_llm_params or {},
                                "parsed_successfully": not ("_extraction_note" in parsed_response or "parsing_status" in parsed_response)
                            }
                        )
                    except Exception as e:
                        self.log_warning(f"Failed to store agent activity: {e}")
                        
                return parsed_response
                
            except Exception as e:
                last_error = str(e)
                tb_str = traceback.format_exc()
                self.log_warning(f"LLM chain execution failed on attempt {retries+1}/{max_retries+1}: {last_error}\nTraceback: {tb_str}")
                retries += 1
                
                # Exit loop on max retries
                if retries > max_retries:
                    self.log_error(f"LLM chain execution definitively failed after {max_retries} retries. Last error: {last_error}")
                    # Store final failure activity if memory available
                    if hasattr(self, "memory") and self.memory is not None:
                        try:
                            prompt_str = str(self.prompt_template.format_messages(**inputs)) if hasattr(self.prompt_template, "format_messages") else str(self.prompt_template.format(**inputs))
                            self.memory.store_agent_activity(
                                agent_name=self.agent_name,
                                activity_type="llm_chain_execution_failure",
                                prompt=prompt_str,
                                response=f"Error after {max_retries} retries: {last_error}",
                                metadata={
                                    "max_retries_reached": True,
                                    "params": additional_llm_params or {}
                                }
                            )
                        except Exception as e:
                            self.log_warning(f"Failed to store agent failure activity: {e}")
                            
                    return self.get_default_response()

        # Should not be reached if max_retries is handled correctly
        self.log_error(f"LLM chain execution loop exited unexpectedly")
        return self.get_default_response()
    
    def _parse_response_with_fallbacks(self, response, default_output=None):
        """Parse LLM response with multiple fallback strategies."""
        import re  # Local import for safety
        
        response_text = self._extract_text_content(response)
        
        # ENHANCED DEBUGGING: Log the complete raw response
        log_message = f"RAW LLM RESPONSE for {self.agent_name} (length: {len(response_text)}):\n>>>>\n{response_text}\n<<<<"
        self.logger.info(log_message)
        
        # SPECIAL DEBUGGING for BRD Analyst outputs
        if self.agent_name == "BRD Analyst Agent" and len(response_text) > 1000:
            print(f"='*80\nDEBUGGING RAW OUTPUT ({len(response_text)} chars):\n{response_text[:500]}...\n{'='*80}")
        
        if not response_text or len(response_text.strip()) == 0:
            self.log_warning("Empty response received")
            return default_output if default_output is not None else {}
        
        # Attempt to clean and parse the response
        cleaned_response = self._clean_json_response(response_text)
        
        try:
            parsed_json = json.loads(cleaned_response)
            return parsed_json
        except json.JSONDecodeError as e:
            self.log_warning(f"JSON parsing failed at position {e.pos}: {str(e)}")
            
            # NEW: Track persistent issues in monitoring system
            monitoring.track_json_parse_error(
                agent=self.agent_name,
                error_type="json_decode_error",
                position=e.pos,
                snippet=cleaned_response[max(0, e.pos-10):min(len(cleaned_response), e.pos+10)],
                model_name=getattr(self.llm, 'model_name', 'unknown')
            )
            
            # SPECIFIC WORKAROUND for position 13 issue
            if "12" in str(e.pos) or "13" in str(e.pos):
                try:
                    # Try replacing with space and parsing again
                    patched_text = response_text[:e.pos] + ' ' + response_text[e.pos+1:]
                    return json.loads(self._clean_json_response(patched_text))
                except Exception:
                    pass
    
    def _sanitize_json_response(self, text: str) -> str:
        """Comprehensive sanitization for LLM JSON responses."""
        if not text:
            return "{}"  # Return empty object for empty responses
        
        # Remove any non-printable characters
        text = ''.join(c if c.isprintable() or c in '\n\r\t' else ' ' for c in text)
        
        # Remove any "?1" or similar sequences that might appear
        text = re.sub(r'\?[0-9]+', ' ', text)
        
        # Fix specifically for the position 13 issue if applicable
        if len(text) > 13:
            if text[12] == '?' and text[13].isdigit():
                text = text[:12] + ' ' + text[14:]
    
        return text

    def _clean_json_response(self, response_input) -> str:
        """Extract JSON from various formats in LLM responses."""
        # Get raw text content
        response_text = self._extract_text_content(response_input)
        
        # First sanitize to handle problematic characters
        response_text = self._sanitize_json_response(response_text)
        
        # Try to find JSON within markdown code blocks
        json_block_pattern = r'```(?:json)?\s*([\s\S]*?)```'
        json_matches = re.findall(json_block_pattern, response_text)
        
        if json_matches:
            # Use the first JSON code block found
            response_text = json_matches[0].strip()
        
        # If no code blocks found but we have JSON-like content
        elif '{' in response_text and '}' in response_text:
            # Find the outermost JSON object
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            if start_idx >= 0 and end_idx > start_idx:
                response_text = response_text[start_idx:end_idx]
        
        return response_text

    def _attempt_json_repair(self, malformed_json_input) -> Dict[str, Any]:
        """
        Attempts to repair a malformed JSON string.
        Now handles both string and AIMessage inputs with enhanced repair strategies.
        """
        # Extract content from AIMessage if needed
        malformed_json_text = self._extract_text_content(malformed_json_input)
        
        self.log_info(f"Attempting JSON repair for text of length {len(malformed_json_text)}")
        
        # First try simple repairs
        text = malformed_json_text.strip()
        
        # Fix 1: Remove any leading/trailing text before/after braces/brackets
        if '{' in text:
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1 and end > start:
                text = text[start:end+1]
        elif '[' in text:
            start = text.find('[')
            end = text.rfind(']')
            if start != -1 and end != -1 and end > start:
                text = text[start:end+1]
    
        # Fix 2: Fix common JSON syntax errors
        # Remove trailing commas before closing braces/brackets
        text = re.sub(r',(\s*[}\]])', r'\1', text)
    
        # Fix 3: Fix unquoted property names
        text = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)(\s*:)', r'\1"\2"\3', text)
    
        # Fix 4: Fix single-quoted strings (replace with double quotes)
        # This regex handles escaped single quotes within single-quoted strings
        def replace_single_quotes(match):
            # Replace single-quoted string with double-quoted string
            content = match.group(1).replace('"', '\\"').replace("\\'", "'")
            return f'"{content}"'
            
        text = re.sub(r"'((?:[^'\\]|\\.)*)'", replace_single_quotes, text)
    
        # Fix 5: Handle Python-style True/False/None literals
        text = text.replace('True', 'true').replace('False', 'false').replace('None', 'null')
    
        # Try parsing the repaired text
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            self.log_warning("Basic JSON repair failed, attempting more aggressive repair")
            
        # More aggressive repairs (if the first round failed)
        try:
            # Fix 6: Try to force a valid JSON structure if nothing else worked
            if not text.startswith('{') and not text.startswith('['):
                # Force object structure
                text = '{' + text
            if not text.endswith('}') and not text.endswith(']'):
                # Force closing brace
                text = text + '}'
                
            # Fix 7: Balance braces/brackets (very basic)
            open_braces = text.count('{')
            close_braces = text.count('}')
            open_brackets = text.count('[')
            close_brackets = text.count(']')
            
            # Add missing closing braces/brackets
            if open_braces > close_braces:
                text += '}' * (open_braces - close_braces)
            elif close_braces > open_braces:
                text = '{' + text
                
            # Add missing closing brackets
            if open_brackets > close_brackets:
                text += ']' * (open_brackets - close_brackets)
            
            return json.loads(text)
        except json.JSONDecodeError as e:
            self.log_warning(f"Advanced JSON repair also failed: {e}")
            raise

    def _extract_structured_content(self, text_input) -> Dict[str, Any]:
        """
        Fallback to extract key-value like structures or lists if JSON parsing fails completely.
        Now handles both string and AIMessage inputs.
        """
        # Extract content from AIMessage if needed
        text = self._extract_text_content(text_input)
        
        self.log_info(f"Attempting structured content extraction for: {text[:200]}...")
        result = {}
        lines = text.split('\n')
        current_key = None
        key_value_pairs = {}
        list_items = []

        # Try to extract key-value pairs (e.g., "Key: Value" or "Key = Value")
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            match = re.match(r'^\s*"?([a-zA-Z0-9_ -]+)"?\s*[:=]\s*(.*)', line)
            if match:
                key = match.group(1).strip().lower().replace(' ', '_')
                value = match.group(2).strip()
                # Try to parse value if it looks like a simple type
                if value.lower() == "true": value = True
                elif value.lower() == "false": value = False
                elif value.isdigit(): value = int(value)
                elif value.replace('.', '', 1).isdigit():
                    try: value = float(value)
                    except ValueError: pass # Keep as string
                key_value_pairs[key] = value
            elif re.match(r'^\s*[-*•]\s+', line): # List item
                list_items.append(re.sub(r'^\s*[-*•]\s*', '', line).strip())
        
        if key_value_pairs:
            result.update(key_value_pairs)
        if list_items:
            result["extracted_list_items"] = list_items
        
        if result: # If we found anything
            result["_extraction_note"] = "Fallback extraction from non-JSON response."
            result["parsing_status"] = "partial_extraction"
            self.log_info(f"Extracted {len(result.keys())-2} structured elements.")
        else: # If nothing structured found
            result = {
                "content": text.strip(),
                "parsing_status": "unstructured_extraction",
                "agent": self.agent_name # Assuming self.agent_name is available
            }
            self.log_warning("No structured content found via extraction.")
            
        return result
    
    # ENHANCED: Advanced RAG context retrieval with query optimization
    def get_rag_context(
        self, 
        query: str, 
        task_goal: str = "",
        max_docs: int = 3,
        search_type: str = "similarity",
        search_kwargs: Optional[Dict[str, Any]] = None,
        optimize_query: bool = True
    ) -> str:
        """
        Enhanced RAG context retrieval with query optimization and intelligent formatting.
        
        Args:
            query: Base search query
            task_goal: Description of what the context will be used for
            max_docs: Maximum documents to retrieve
            search_type: Search method (similarity, mmr, etc.)
            search_kwargs: Additional search parameters
            optimize_query: Whether to optimize query using LLM
            
        Returns:
            str: Formatted context from retrieved documents
        """
        if not self.rag_retriever:
            return ""
        
        try:
            # NEW: Optimize query if requested and task goal provided
            if optimize_query and task_goal and len(query.strip()) > 10:
                optimized_queries = self._optimize_rag_queries(query, task_goal)
                
                # If optimization successful, use multiple queries and merge results
                if optimized_queries:
                    self.log_info(f"Using {len(optimized_queries)} optimized queries for RAG retrieval")
                    all_docs = []
                    
                    for i, opt_query in enumerate(optimized_queries):
                        try:
                            # Apply custom search parameters if provided
                            kwargs = {"search_type": search_type}
                            if search_kwargs:
                                kwargs.update(search_kwargs)
                                
                            # Get documents for this query
                            query_docs = self.rag_retriever.invoke(opt_query, **kwargs)
                            
                            # Process results (handle different return types)
                            if isinstance(query_docs, dict) and "documents" in query_docs:
                                all_docs.extend(query_docs["documents"])
                            elif isinstance(query_docs, list):
                                all_docs.extend(query_docs)
                                
                        except Exception as query_error:
                            self.log_warning(f"Error with optimized query {i+1}: {query_error}")
                    
                    # Deduplicate documents (based on content)
                    unique_docs = []
                    seen_content = set()
                    
                    for doc in all_docs:
                        # Create a hash of the first 100 chars to identify similar documents
                        content_hash = hash(doc.page_content[:100]) if hasattr(doc, 'page_content') else hash(str(doc)[:100])
                        
                        if content_hash not in seen_content:
                            unique_docs.append(doc)
                            seen_content.add(content_hash)
                    
                    # If we found documents, format and return context
                    if unique_docs:
                        return self._format_rag_context(unique_docs[:max_docs], task_goal)
            
            # Fallback to standard query if optimization disabled or failed
            kwargs = {"search_type": search_type}
            if search_kwargs:
                kwargs.update(search_kwargs)
                
            docs = self.rag_retriever.invoke(query, **kwargs)
            
            # Process results (handle different return types)
            if isinstance(docs, dict) and "documents" in docs:
                docs_list = docs["documents"]
            elif isinstance(docs, list):
                docs_list = docs
            else:
                self.log_warning(f"Unexpected RAG retriever response format: {type(docs)}")
                return ""
                
            if not docs_list:
                return ""
            
            # Format and return context
            return self._format_rag_context(docs_list[:max_docs], task_goal)
            
        except Exception as e:
            self.log_warning(f"RAG context retrieval failed: {e}")
            return ""
    
    def _optimize_rag_queries(self, original_query: str, task_goal: str) -> List[str]:
        """Optimize RAG queries using LLM to improve retrieval quality."""
        try:
            # Use analytical temperature for query optimization (always low)
            llm_analytical = self.llm.bind(temperature=0.1)
            
            # Generate optimized queries
            prompt = self.query_optimization_template.format(
                original_query=original_query,
                task_goal=task_goal
            )
            
            response = llm_analytical.invoke(prompt)
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Extract queries from response
            queries = []
            query_pattern = r'\d+\.\s*(.*)'
            matches = re.findall(query_pattern, response_text)
            
            if matches:
                # Clean up queries and remove any that are too similar to original
                for match in matches:
                    clean_query = match.strip()
                    queries.append(clean_query)
                    
                self.log_info(f"Generated {len(queries)} optimized RAG queries")
                return queries
            else:
                # Fallback to original query if no matches found
                self.log_warning("Query optimization failed to return valid queries")
                return [original_query]
                
        except Exception as e:
            self.log_warning(f"Query optimization failed: {e}")
            return [original_query]
    
    def _format_rag_context(self, docs: List[Any], task_goal: str) -> str:
        """Format RAG context with intelligent summarization based on task goal."""
        try:
            context_parts = []
            
            # If we have task goal, add it as context header
            if task_goal:
                context_parts.append(f"CONTEXT RELEVANT TO: {task_goal}")
            
            # Process each document
            for i, doc in enumerate(docs, 1):
                # Get document content
                if hasattr(doc, 'page_content'):
                    content = doc.page_content
                else:
                    content = str(doc)
                
                # For very long documents, summarize rather than hard truncate
                if len(content) > 2000:
                    # First 800 chars + middle 400 chars + last 800 chars with markers
                    content = (
                        f"{content[:800]}\n"
                        f"[...content summarized...]\n"
                        f"{content[len(content)//2-200:len(content)//2+200]}\n"
                        f"[...content summarized...]\n"
                        f"{content[-800:]}"
                    )
            
                # Add metadata if available
                metadata_str = ""
                if hasattr(doc, 'metadata') and doc.metadata:
                    useful_metadata = {k: v for k, v in doc.metadata.items() 
                                      if not k.startswith('_') and k not in ['chunk_id', 'embeddings']}
                    
                    if useful_metadata:
                        metadata_str = f"\nSource: {json.dumps(useful_metadata, default=str)}"
                
                # Format document content with metadata
                context_parts.append(f"CONTEXT ITEM {i}:{metadata_str}\n{content}")
            
            # Join all context parts
            return "\n\n".join(context_parts)
            
        except Exception as e:
            self.log_warning(f"Context formatting failed: {e}")
            
            # Fallback to simple formatting
            try:
                simple_contexts = []
                for i, doc in enumerate(docs, 1):
                    content = doc.page_content if hasattr(doc, 'page_content') else str(doc)
                    # Simple truncation if needed in fallback mode
                    if len(content) > 1000:
                        content = f"{content[:1000]}... [truncated]"
                    simple_contexts.append(f"Context {i}: {content}")
                
                return "\n\n".join(simple_contexts)
            except:
                # Ultra-fallback if everything fails
                return "Context retrieval succeeded but formatting failed."
    
    # NEW: Advanced reasoning methods
    def perform_step_by_step_reasoning(self, problem_description: str, context: str = "", 
                                     previous_steps: str = "") -> Dict[str, Any]:
        """
        Perform explicit step-by-step reasoning about a complex problem.
        Uses chain-of-thought prompting with temperature adjustment for better reasoning.
        """
        self.log_info("Performing step-by-step reasoning")
        
        try:
            # Use slightly lower temperature for reasoning (more precise)
            reasoning_temp = max(0.1, self.default_temperature - 0.1)
            llm_reasoning = self.llm.bind(temperature=reasoning_temp)
            
            # Create inputs for reasoning
            inputs = {
                "agent_name": self.agent_name,
                "problem_description": problem_description,
                "context": context or "No additional context provided.",
                "previous_steps": previous_steps or "This is the first reasoning step."
            }
            
            # Execute reasoning chain
            chain = self.reasoning_template | llm_reasoning
            response = chain.invoke(inputs)
            reasoning_text = response.content if hasattr(response, 'content') else str(response)
            
            # Extract key components from reasoning
            steps = self._extract_reasoning_steps(reasoning_text)
            conclusion = self._extract_conclusion(reasoning_text)
            
            # Store in working memory
            self.working_memory["last_reasoning"] = {
                "problem": problem_description,
                "steps": steps,
                "conclusion": conclusion,
                "full_reasoning": reasoning_text,
                "timestamp": datetime.now().isoformat()
            }
            
            # Return structured reasoning result
            return {
                "reasoning_steps": steps,
                "conclusion": conclusion,
                "full_reasoning": reasoning_text
            }
            
        except Exception as e:
            self.log_error(f"Step-by-step reasoning failed: {str(e)}")
            return {
                "reasoning_steps": ["Reasoning process encountered an error"],
                "conclusion": "Could not complete reasoning due to an error",
                "error": str(e)
            }
    
    def _extract_reasoning_steps(self, reasoning_text: str) -> List[str]:
        """Extract distinct reasoning steps from reasoning text."""
        # Try to find numbered steps
        step_pattern = r'(?:^|\n)(?:Step\s*)?(\d+)[\.:\)]\s*([^\n]+)'
        steps = re.findall(step_pattern, reasoning_text, re.IGNORECASE)
        
        if steps:
            return [step[1].strip() for step in steps]
            
        # If no numbered steps, try to extract paragraph breaks as steps
        paragraphs = [p.strip() for p in reasoning_text.split("\n\n") if p.strip()]
        
        # Filter out likely non-step paragraphs (too short or conclusion markers)
        reasoning_paragraphs = [p for p in paragraphs 
                              if len(p) > 30 and not any(marker in p.lower() 
                                                      for marker in ["conclusion", "therefore", "in summary"])]
        
        if reasoning_paragraphs:
            return reasoning_paragraphs
        
        # Fallback: split into sentences
        import re
        sentences = re.split(r'(?<=[.!?])\s+', reasoning_text)
        return [s.strip() for s in sentences if len(s.strip()) > 30]
    
    def _extract_conclusion(self, reasoning_text: str) -> str:
        """Extract conclusion from reasoning text."""
        # Look for explicit conclusion markers
        conclusion_patterns = [
            r'(?:^|\n)(?:Conclusion|Therefore|In summary|Thus|Hence|So)[:\s]+([^\n]+(?:\n[^\n]+)*)',
            r'(?:^|\n)(?:I conclude that|The answer is|Finally)[:\s]+([^\n]+(?:\n[^\n]+)*)'
        ]
        
        for pattern in conclusion_patterns:
            match = re.search(pattern, reasoning_text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # If no explicit conclusion, use the last paragraph
        paragraphs = [p.strip() for p in reasoning_text.split("\n\n") if p.strip()]
        if paragraphs:
            return paragraphs[-1]
            
        # Last resort, use the last sentence
        sentences = re.split(r'(?<=[.!?])\s+', reasoning_text)
        if sentences:
            return sentences[-1].strip()
            
        return "No clear conclusion found"
    
    # NEW: Self-reflection and optimization
    def _perform_self_reflection(self, task_description: str, approach_taken: str,
                           outcome: str, execution_time: float, error: Optional[str] = None) -> None:
        """Perform self-reflection on agent performance to improve future executions."""
        try:
            # Skip if too frequent (limit reflections to avoid overhead)
            now = time.time()
            last_reflection = self.working_memory.get("last_reflection_time", 0)
            
            # Only reflect every 10 minutes max
            if now - last_reflection < 600:  # 600 seconds = 10 minutes
                return
                
            self.working_memory["last_reflection_time"] = now
            
            # Skip detailed reflection for quick successful tasks
            if outcome == "success" and execution_time < 2.0 and not error:
                return
            
            self.log_info("Performing agent self-reflection")
            
            # Use analytical temperature for reflection (always low)
            llm_analytical = self.llm.bind(temperature=0.1)
            
            # Format error information
            error_info = f"Error encountered: {error}" if error else "No errors encountered"
            
            # Prepare context for the template with correct parameter names
            reflection_context = {
                "task_description": task_description,
                "agent_name": self.agent_name,  # Ensure agent_name is correctly passed
                "approach_taken": approach_taken,
                "outcome": outcome,
                "execution_time": f"{execution_time:.2f} seconds",
                "error_info": error_info  # Use error_info instead of error
            }
            
            # Log what's being passed
            self.logger.debug(f"SELF_REFLECT - Template variables: {self.self_reflection_template.input_variables}")
            self.logger.debug(f"SELF_REFLECT - Context: {list(reflection_context.keys())}")

            # Format the prompt with the properly matched context
            prompt = self.self_reflection_template.format(**reflection_context)
            
            # Get reflection insights
            response = llm_analytical.invoke(prompt)
            reflection_text = response.content if hasattr(response, 'content') else str(response)
            
            # Extract insights from reflection
            strengths = self._extract_reflection_points(reflection_text, "went well|strength|positive|successful")
            improvements = self._extract_reflection_points(reflection_text, "improve|enhance|better|fix|issue")
            adaptations = self._extract_reflection_points(reflection_text, "adapt|future|next time|should|would")
            
            # Update reflection data
            if strengths:
                self.reflection_data["strengths"].extend(strengths[:2])  # Limit to avoid accumulation
                self.reflection_data["strengths"] = self.reflection_data["strengths"][-5:]  # Keep only most recent
                
            if improvements:
                self.reflection_data["improvement_areas"].extend(improvements[:2])
                self.reflection_data["improvement_areas"] = self.reflection_data["improvement_areas"][-5:]
                
            if adaptations:
                self.reflection_data["adaptation_history"].append({
                    "task": task_description,
                    "adaptations": adaptations[:3],
                    "timestamp": datetime.now().isoformat()
                })
                self.reflection_data["adaptation_history"] = self.reflection_data["adaptation_history"][-5:]
            
            # Store the full reflection
            self.working_memory["last_reflection"] = {
                "task": task_description,
                "outcome": outcome,
                "reflection": reflection_text,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.log_warning(f"Self-reflection failed: {str(e)}", exc_info=True)
    
    def _extract_reflection_points(self, text: str, pattern_keywords: str) -> List[str]:
        """Extract specific points from reflection text based on keywords."""
        points = []
        
        # Look for bullet points or numbered lists with relevant keywords
        list_pattern = r'(?:^|\n)[•\-*\d+.]\s*(.*?(?:' + pattern_keywords + ').*?)(?=(?:^|\n)[•\-*\d+.]|\Z)'
        matches = re.findall(list_pattern, text, re.IGNORECASE | re.DOTALL)
        if matches:
            points.extend([m.strip() for m in matches])
        
        # Look for sentences with relevant keywords if no bullet points found
        if not points:
            sentence_pattern = r'([^.!?\n]*(?:' + pattern_keywords + ')[^.!?\n]*[.!?])'
            matches = re.findall(sentence_pattern, text, re.IGNORECASE)
            if matches:
                points.extend([m.strip() for m in matches])
        
        return points
    
    def generate_with_temperature(self, prompt: str, temperatures: list) -> dict:
        """Generate responses with multiple temperatures in one batch when possible"""
        # Check if all responses are in cache
        all_cached = True
        cached_responses = {}
        
        for temp in temperatures:
            cached = response_cache.get_cached_response(prompt, temp, self.model_name)
            if cached:
                cached_responses[temp] = cached
            else:
                all_cached = False
        
        # Return all cached responses if available
        if all_cached:
            return cached_responses
        
        # For uncached temperatures, use the lowest temperature and adjust output
        # This saves API calls during testing while maintaining logical distinctions
        base_temp = min(temperatures)
        response = self.llm.bind(temperature=base_temp)(prompt)
        
        # Cache the base response
        response_cache.cache_response(prompt, base_temp, self.model_name, response)
        
        # For testing only: derive higher temperature responses from base response
        results = {base_temp: response}
        for temp in temperatures:
            if temp != base_temp and temp not in cached_responses:
                # During testing, we simulate temperature differences to save API calls
                varied_response = self._simulate_temperature_variation(response, base_temp, temp)
                response_cache.cache_response(prompt, temp, self.model_name, varied_response)
                results[temp] = varied_response
                
        # Add cached responses
        results.update(cached_responses)
        return results
    
    def _simulate_temperature_variation(self, base_response, base_temp, target_temp):
        """For testing only: simulate temperature variation to reduce API calls"""
        # Higher temperature = more variation/creativity
        # This is a very simplified simulation for testing purposes
        if target_temp > base_temp:
            # Add some variation for higher temperatures
            return base_response + f"\n\n[Note: Simulated {target_temp} temperature variation for testing]"
        return base_response
    
    @abstractmethod
    def get_default_response(self) -> Dict[str, Any]:
        """Get default response when agent execution fails."""
        pass
    
    @abstractmethod
    def run(self, *args, **kwargs) -> Dict[str, Any]:
        """Main execution method for the agent."""
        pass

    # Add this new helper method for consistent text extraction

            

    def self_reflect(self, task_description, result, issues_identified="", improvements_made=""):
        """Robust self-reflection handling template variations."""
        try:
            # Create a dictionary with all possible parameters
            all_params = {
                "task_description": task_description,
                "previous_attempt": json.dumps(result, indent=2) if isinstance(result, dict) else str(result),
                "issues_identified": issues_identified,
                "improvements_made": improvements_made,
                # Use agent_name consistently, but provide fallbacks for old templates
                "agent_name": self.agent_name,
                "agent_role": self.agent_name,  # Legacy support
                "role": self.agent_name,        # Legacy support
                "agentt_role": self.agent_name  # Legacy support with typo
            }

            # Detailed diagnostics
            self.logger.info(f"SELF_REFLECT - Agent: {self.agent_name}")
            
            # Debug log the template variables
            self.log_info(f"Self-reflection template input variables: {getattr(self.self_reflection_template, 'input_variables', ['unknown'])}")
            
            # Try using template if available
            try:
                if hasattr(self.self_reflection_template, 'format'):
                    # Only include parameters that are in the template's input_variables
                    if hasattr(self.self_reflection_template, 'input_variables'):
                        valid_context = {
                            k: v for k, v in all_params.items() 
                            if k in self.self_reflection_template.input_variables
                        }
                        # Debug log the keys being used
                        self.log_info(f"Self-reflection using keys: {list(valid_context.keys())}")
                        prompt_with_context = self.self_reflection_template.format(**valid_context)
                    else:
                        prompt_with_context = self.self_reflection_template.format(**all_params)
                else:
                    # Fallback template
                    prompt_with_context = f"""
                    You are {self.agent_name} performing self-reflection.
                    
                    Task: {task_description}
                    
                    Previous attempt: 
                    {all_params['previous_attempt']}
                    
                    Issues identified: {issues_identified}
                    
                    Improvements made: {improvements_made}
                    
                    Analyze the previous attempt and suggest improvements.
                    """
            except Exception as format_error:
                self.log_warning(f"Template formatting failed: {format_error}, using fallback format")
                # Extra fallback if formatting fails
                prompt_with_context = f"You are {self.agent_name}. Review this: {all_params['previous_attempt']}"
    
        # Use analytical temperature for reflection
            reflection_llm = self.llm.bind(temperature=0.1)
            reflection_response = reflection_llm.invoke(prompt_with_context)
            return reflection_response.content if hasattr(reflection_response, 'content') else reflection_response
        except Exception as e:
            self.log_warning(f"Self-reflection failed: {str(e)}")
            return None
    
    def create_strict_json_template(self, stage_name, instructions, example_json):
        """Create a template for strict JSON output."""
        return JsonHandler.create_strict_json_template(stage_name, instructions, example_json)
    
    def create_strict_json_llm(self, max_tokens=4096, model_override=None):
        """Create an LLM configured for strict JSON output."""
        return JsonHandler.create_strict_json_llm(self.llm, max_tokens, model_override)
    
    def parse_json_with_error_tracking(self, response, pydantic_model=None, default_response=None):
        """Parse JSON with robust error handling."""
        return JsonHandler.parse_json_with_error_tracking(
            response, 
            agent_instance=self,
            pydantic_model=pydantic_model, 
            default_response=default_response
        )

    # Add these helper methods to BaseAgent class

    def validate_json_structure(self, json_data: Dict[str, Any], expected_fields: List[str], 
                            optional_fields: List[str] = None) -> Dict[str, Any]:
        """Validate JSON structure against expected fields."""
        return JsonHandler.validate_json_against_schema(json_data, expected_fields, optional_fields)

    def transform_json(self, json_data: Dict[str, Any], mapping: Dict[str, str],
                    default_structure: Dict[str, Any] = None) -> Dict[str, Any]:
        """Transform JSON from one structure to another."""
        return JsonHandler.transform_json_structure(json_data, mapping, default_structure)

    def merge_json(self, primary: Dict[str, Any], secondary: Dict[str, Any],
                override_conflicts: bool = True) -> Dict[str, Any]:
        """Merge two JSON objects with conflict resolution."""
        return JsonHandler.merge_json_objects(primary, secondary, override_conflicts)

    def fix_agent_json(self, json_data: Dict[str, Any]) -> Dict[str, Any]:
        """Fix common JSON issues specific to this agent."""
        return JsonHandler.fix_common_agent_json_issues(self.agent_name, json_data)
    
    # Add these methods for backward compatibility
    def _parse_json_with_robust_fallbacks(self, response_text, default_response=None):
        """Legacy method that delegates to the centralized JsonHandler."""
        return JsonHandler._parse_json_with_robust_fallbacks(
            response_text, 
            default_response=default_response,
            agent_instance=self
        )

    # Add these methods
    def _thoroughly_clean_json(self, text: str) -> str:
        """For backward compatibility - delegates to centralized JsonHandler."""
        return JsonHandler._thoroughly_clean_json(text)
        
    # Add this helper to BaseAgent class
    def _extract_text_content(self, response):
        """Extract text content from various response types."""
        from multi_ai_dev_system.tools.json_handler import JsonHandler
        return JsonHandler._extract_text_content(response)
        
    def _extract_structured_content(self, text: str) -> Dict[str, Any]:
        """For backward compatibility - delegates to centralized JsonHandler."""
        return JsonHandler._extract_structured_content(text)
        
    def _detect_model_provider(self, llm):
        """For backward compatibility - delegates to centralized JsonHandler."""
        return JsonHandler._detect_model_provider(llm)
        
    def _preprocess_json_text(self, text: str) -> str:
        """For backward compatibility - delegates to centralized JsonHandler."""
        return JsonHandler._preprocess_json_text(text)
    

    # In the BaseAgent class, locate the check_template_variables method and modify it:
    def check_template_variables(self, text: str) -> bool:
        """Check for unresolved template variables in generated text."""
        if not text:
            return False
            
        # More precise pattern that only matches standalone template variables
        # not common field names containing "id"
        pattern = r'\{\s*([a-zA-Z][a-zA-Z0-9_]*)\s*\}'
        
        # Find all potential template variables
        matches = re.findall(pattern, text)
        
        if matches:
            # Filter out common field names that are valid in JSON
            suspicious_matches = [
                match for match in matches 
                if match not in ['id', 'name', 'type', 'value'] and len(match) > 2
            ]
            
            if suspicious_matches:
                self.log_warning(f"Detected suspicious template patterns: {suspicious_matches} - rejecting")
                return True
                
        return False

    def _initialize_specialized_prompts(self):
        """Initialize specialized prompt templates used by the BaseAgent class."""
        # Template for self-reflection
        self.self_reflection_template = PromptTemplate(
            input_variables=["task_description", "agent_name", "approach_taken", "outcome", "execution_time", "error_info"],
            template="""You are {agent_name} reflecting on a task you just performed.

TASK: {task_description}

APPROACH: {approach_taken}

OUTCOME: {outcome}
EXECUTION TIME: {execution_time}
{error_info}

Please analyze your performance:
1. What went well in this execution?
2. What could be improved?
3. How would you adapt your approach for future similar tasks?

Provide specific, actionable insights."""
        )
        
        # Template for query optimization for RAG
        self.query_optimization_template = PromptTemplate(
            input_variables=["original_query", "task_goal"],
            template="""Your task is to optimize the following search query to improve document retrieval results.

ORIGINAL QUERY: {original_query}

SEARCH GOAL: {task_goal}

Generate 3 optimized search queries that:
1. Capture different aspects of the original query
2. Use precise terminology relevant to the domain
3. Focus on the core information need

Format your response as a numbered list of queries:
1. [First optimized query]
2. [Second optimized query]
3. [Third optimized query]"""
        )
        
        # Template for step-by-step reasoning
        self.reasoning_template = PromptTemplate(
            input_variables=["agent_name", "problem_description", "context", "previous_steps"],
            template="""You are {agent_name} solving a complex problem through step-by-step reasoning.

PROBLEM: {problem_description}

CONTEXT: {context}

PREVIOUS REASONING: {previous_steps}

Continue the reasoning process by:
1. Breaking down the problem into logical steps
2. Considering multiple perspectives and alternatives
3. Identifying potential constraints and limitations
4. Drawing from relevant principles and knowledge
5. Reaching a well-justified conclusion

Provide your reasoning steps followed by a clear conclusion."""
        )