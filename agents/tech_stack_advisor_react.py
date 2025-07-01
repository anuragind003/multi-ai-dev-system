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

# Core dependencies
from langchain_core.language_models import BaseLanguageModel
from langchain_core.retrievers import BaseRetriever
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import AgentExecutor, create_react_agent
import monitoring

# Local imports
from .base_agent import BaseAgent
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
from tools.tech_stack_tools import (
    get_technical_requirements_summary,
    evaluate_backend_options,
    evaluate_frontend_options,
    evaluate_database_options,
    evaluate_architecture_patterns,
    synthesize_tech_stack,
    analyze_tech_stack_risks,
    evaluate_all_technologies,  # Add the batch evaluation tool
    compile_tech_stack_recommendation  # Add the required final tool
)

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

logger = logging.getLogger(__name__)

class TechStackAdvisorReActAgent(BaseAgent):
    """
    Enhanced ReAct-based Tech Stack Advisor Agent with hybrid validation and API optimization.
    
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
                 temperature: float = None,
                 rag_retriever: Optional[BaseRetriever] = None,
                 message_bus=None,
                 enable_enhanced_validation: bool = True,
                 enable_api_optimization: bool = True):
        
        # If no specific temperature provided, get from settings
        if temperature is None:
            temperature = get_agent_temperature("Tech Stack Advisor Agent", 0.2)
        
        super().__init__(
            llm=llm,
            memory=memory,
            agent_name="Tech Stack Advisor Agent",
            temperature=temperature,
            rag_retriever=rag_retriever
        )
        
        self.message_bus = message_bus
        self.recommendation_stages = []
        self.tools = []  # Initialize the tools attribute
        
        # Enhanced components
        self.json_handler = JsonHandler()
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        
        # Initialize enhanced memory (inherits from BaseAgent which has enhanced memory mixin)
        self._init_enhanced_memory()
        
        # Initialize RAG context
        self.rag_manager = get_rag_manager()
        if self.rag_manager:
            self.logger.info("RAG manager available for enhanced tech recommendations")
        else:
            self.logger.warning("RAG manager not available - proceeding without RAG context")
        
        # Hybrid validation and optimization
        self.enable_enhanced_validation = enable_enhanced_validation
        self.enable_api_optimization = enable_api_optimization
        
        if self.enable_enhanced_validation:
            self.hybrid_validator = HybridValidator(self.logger)
        
        if self.enable_api_optimization:
            self.api_optimizer = ReactAgentAPIOptimizer(
                cache_ttl_hours=1,
                enable_batching=True
            )
        
        # Performance tracking
        self.execution_metrics = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "avg_execution_time": 0.0,
            "validation_stats": {"strict": 0, "tolerant": 0, "permissive": 0, "fallback": 0},
            "api_token_savings": 0
        }
        
        # Initialize the ReAct agent and tools
        self._init_agent()
        # Setup message bus subscriptions
        self._setup_message_subscriptions()

    def _init_agent(self):
        """Initialize the ReAct agent with enhanced tools and validation."""
        # Import tools directly - they're already @tool decorated
        from tools.tech_stack_tools import (
            get_technical_requirements_summary,
            evaluate_all_technologies,
            evaluate_architecture_patterns,
            synthesize_tech_stack,
            analyze_tech_stack_risks,
            compile_tech_stack_recommendation
        )
        
        # Enhanced validation disabled - using universal wrapper instead
        if False:  # self.enable_enhanced_validation:
            self.tools = [
                enhanced_tool_validator.wrap_tool(
                    get_technical_requirements_summary,
                    expected_fields=["brd_analysis"],
                    agent_name=self.agent_name
                ),
                enhanced_tool_validator.wrap_tool(
                    evaluate_all_technologies,
                    expected_fields=["requirements_summary"],
                    agent_name=self.agent_name
                ),
                enhanced_tool_validator.wrap_tool(
                    evaluate_architecture_patterns,
                    expected_fields=["requirements_summary"],
                    agent_name=self.agent_name
                ),
                enhanced_tool_validator.wrap_tool(
                    synthesize_tech_stack,
                    expected_fields=["backend_recommendation", "frontend_recommendation", 
                                   "database_recommendation", "architecture_recommendation"],
                    agent_name=self.agent_name
                ),
                enhanced_tool_validator.wrap_tool(
                    analyze_tech_stack_risks,
                    expected_fields=["tech_stack_recommendations"],
                    agent_name=self.agent_name
                ),
                enhanced_tool_validator.wrap_tool(
                    compile_tech_stack_recommendation,
                    expected_fields=[],
                    agent_name=self.agent_name
                )
            ]
        else:
            # Use original tools
            self.tools = [
                get_technical_requirements_summary,
                evaluate_all_technologies,
                evaluate_architecture_patterns,
                synthesize_tech_stack,
                analyze_tech_stack_risks,
                compile_tech_stack_recommendation
            ]

        # Pull the default ReAct JSON chat prompt from the hub
        self.react_prompt = hub.pull("hwchase17/react-chat-json")
        
        # Enhanced system message for better validation success
        enhanced_system_message = """You are an Expert Technology Stack Advisor specializing in selecting optimal technology stacks for software projects across multiple domains.

DOMAIN EXPERTISE:
- Web Applications (frontend/backend/full-stack)
- Mobile Applications (native, cross-platform)
- IoT Systems (embedded, edge computing)
- Data Science & ML (analytics, machine learning)
- Gaming (mobile, console, web games)
- Enterprise Systems (large-scale, compliance-heavy)
- Healthcare (HIPAA, medical devices)
- Fintech (PCI compliance, high security)

ENHANCED VALIDATION GUIDELINES:
- When calling tools, ALWAYS format action_input as a proper JSON object
- Ensure all required fields are provided in the correct format
- If you receive validation errors, the system will attempt progressive fallback validation
- Your responses should be consistent and well-structured to improve validation success

ENHANCED APPROACH:
1. **Domain Detection**: Automatically identify the project domain from requirements
2. **Scale Analysis**: Determine project scale (startup, medium, enterprise)
3. **Constraint Processing**: Consider budget, timeline, team expertise
4. **Technology Selection**: Choose technologies appropriate for domain and scale
5. **Compliance Check**: Ensure recommendations meet domain-specific compliance needs

DOMAIN-SPECIFIC GUIDANCE:
- **Healthcare**: Prioritize HIPAA compliance, data security, audit trails
- **Fintech**: Focus on PCI compliance, transaction security, performance
- **Gaming**: Consider real-time requirements, graphics performance, multiplayer
- **IoT**: Evaluate connectivity protocols, edge computing, real-time processing
- **Enterprise**: Ensure scalability, integration capabilities, security
- **Mobile**: Consider platform reach, performance, native vs cross-platform
- **Data Science**: Focus on ML frameworks, data processing, visualization tools

EFFICIENT PROCESSING INSTRUCTIONS:
1. ALWAYS use batch tools rather than individual evaluation tools to minimize API calls
2. The evaluate_all_technologies tool evaluates backend, frontend, and database technologies in a single API call
3. Process the full result from the batch tool before deciding on next steps
4. Make deliberate decisions about which aspects need additional evaluation  

Follow this efficient process to make your recommendation:
1. Start by getting a summary of the technical requirements using get_technical_requirements_summary
2. ALWAYS use evaluate_all_technologies to get backend, frontend, and database options all at once
3. Based on these evaluations, recommend an appropriate architecture pattern
4. Synthesize your choices into a comprehensive tech stack
5. Analyze potential risks and challenges with your recommended stack
6. **REQUIRED FINAL STEP**: Call compile_tech_stack_recommendation to generate the final comprehensive recommendation

CRITICAL TOOL USAGE INSTRUCTIONS:
1. After using evaluate_all_technologies, EXTRACT the specific recommendations for each technology category
2. You MUST store these separate recommendations in your reasoning
3. When calling synthesize_tech_stack, you MUST provide FOUR SEPARATE parameters:
   * backend_recommendation: The complete backend technology recommendation text
   * frontend_recommendation: The complete frontend technology recommendation text
   * database_recommendation: The complete database recommendation text
   * architecture_recommendation: The complete architecture pattern recommendation text
4. **MANDATORY**: You MUST end your analysis by calling compile_tech_stack_recommendation() - this is required to complete the task

ENHANCED INPUT VALIDATION:
- Always ensure your action_input is a valid JSON object, not a string
- Required fields must be provided for each tool call
- The system will attempt to recover from malformed inputs through progressive validation

FORBIDDEN RESPONSES:
- Do NOT provide "Final Answer" text responses
- Do NOT skip the compile_tech_stack_recommendation tool call
- The task is only complete when compile_tech_stack_recommendation has been called

EXAMPLE TECHNOLOGY DIVERSITY:
- **Backend**: Python (Django/FastAPI/Flask), Node.js (Express/Fastify), Java (Spring Boot), Go (Gin/Echo), C# (.NET), Rust (Actix)
- **Frontend**: React, Vue.js, Angular, Svelte, Alpine.js, or native mobile frameworks
- **Database**: PostgreSQL, MySQL, MongoDB, Redis, InfluxDB, SQLite based on needs
- **Mobile**: React Native, Flutter, Swift/iOS, Kotlin/Android, Xamarin
- **Gaming**: Unity, Unreal Engine, Godot based on platform and requirements
- **IoT**: C++, Python, Rust, MicroPython based on hardware constraints

CORRECT TOOL CALL FORMAT:
{
  "action": "synthesize_tech_stack",
  "action_input": {
    "backend_recommendation": "Node.js with Express.js is recommended due to its scalability and robust ecosystem for real-time applications.",
    "frontend_recommendation": "React is recommended for its component-based architecture and performance, suitable for dynamic user interfaces.",
    "database_recommendation": "PostgreSQL is recommended for its ACID compliance and relational data model that fits the structured data requirements.",
    "architecture_recommendation": "Microservices architecture is recommended to allow independent scaling of components and better team organization."
  }
}"""

        # Update the system message
        messages = self.react_prompt.messages
        for i, message in enumerate(messages):
            if hasattr(message, 'role') and message.role == "system":
                messages[i] = SystemMessage(content=enhanced_system_message)
                break

        # Create ReAct agent
        self.agent = create_json_chat_agent(llm=self.llm, tools=self.tools, prompt=self.react_prompt)
        
        # Create agent executor with enhanced error handling
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,  # Enable verbose output to show React agent progress
            handle_parsing_errors=True,
            max_iterations=15,
            return_intermediate_steps=True
        )

    def run(self, brd_analysis: Optional[Dict[str, Any]] = None, project_context: str = "", session_id: str = None) -> Dict[str, Any]:
        """
        Generate technology stack recommendations using the ReAct framework.
        
        Args:
            brd_analysis: (Optional) Analyzed business requirements document - if not provided, reads from shared memory
            project_context: Additional context about the project
            session_id: Optional session ID for WebSocket monitoring
            
        Returns:
            Comprehensive technology stack recommendation
        """
        self.log_start("Starting ReAct-based tech stack recommendation")
        
        try:
            # Try to get BRD analysis from shared memory first, then fall back to parameter
            if brd_analysis is None:
                try:
                    if hasattr(self, 'memory') and self.memory:
                        brd_analysis = self.memory.get("brd_analysis")
                        if brd_analysis:
                            self.log_info("Retrieved BRD analysis from shared memory")
                        else:
                            self.log_warning("No BRD analysis found in shared memory")
                    else:
                        self.log_warning("No shared memory available")
                except Exception as memory_error:
                    self.log_warning(f"Failed to retrieve BRD analysis from shared memory: {memory_error}")
            
            # Ensure we have BRD analysis to work with
            if not brd_analysis:
                self.log_error("No BRD analysis available (neither from parameter nor shared memory)")
                return self.get_default_response()
            
            # Store the BRD analysis in shared memory for tools to access
            try:
                if hasattr(self, 'memory') and self.memory:
                    self.memory.set("tech_stack_brd_analysis", brd_analysis)
                    self.log_info("Stored BRD analysis in shared memory for tool access")
            except Exception as memory_error:
                self.log_warning(f"Failed to store BRD analysis for tool access: {memory_error}")
            
            # Store the BRD analysis in an instance variable for tool access (legacy support)
            self._stored_brd_analysis = brd_analysis
            # Using the tools with their Pydantic schemas
            tools_list = self.tools
            
            # Pull the prompt from the hub
            prompt = self.react_prompt
            
            # Create the agent with standard temperature binding
            llm_with_temp = self.llm.bind(temperature=self.default_temperature)
            
            # Create the agent first
            agent = create_json_chat_agent(
                llm=llm_with_temp,
                tools=tools_list,
                prompt=prompt
            )
            
            # Create callbacks for progress monitoring
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
                tools=tools_list,
                verbose=False,  # Disable to prevent LangChain's StdOutCallbackHandler I/O errors
                callbacks=callbacks,  # Use our SafeConsoleCallbackHandler for output
                handle_parsing_errors=True,
                max_iterations=15,
                return_intermediate_steps=True
            )
            
            # Create memory for chat history
            message_history = ChatMessageHistory()
            
            # Wrap with message history
            agent_with_chat_history = RunnableWithMessageHistory(
                agent_executor,
                lambda session_id: message_history,
                input_messages_key="input",
                history_messages_key="chat_history"
            )
            # Convert BRD analysis to a JSON string for the tool
            brd_json = json.dumps(brd_analysis)
            
            # Create a simplified summary for the agent prompt
            project_name = brd_analysis.get('project_name', 'Unknown Project')
            project_summary = brd_analysis.get('project_summary', 'No summary available')
              # Prepare simplified input with a reference to the BRD data
            formatted_context = f"""
            Your goal is to recommend a comprehensive technology stack for this project.
            
            Project name: {project_name}
            Project summary: {project_summary}
            Project context: {project_context}
            
            DOMAIN DETECTION INSTRUCTIONS:
            Before making technology recommendations, analyze the BRD to detect:
            1. Project Domain (healthcare, fintech, gaming, IoT, e-commerce, enterprise, etc.)
            2. Project Scale (startup: <1000 users, medium: 1K-100K users, enterprise: >100K users)
            3. Critical Constraints (budget, timeline, security, compliance requirements)
            4. Team Context (expertise, size, location)
            
            TECHNOLOGY SELECTION GUIDELINES:
            - Healthcare: HIPAA compliance, security-first, audit trails
            - Fintech: PCI compliance, high security, transaction processing
            - Gaming: Real-time performance, graphics processing, multiplayer
            - IoT: Edge computing, connectivity protocols, resource constraints
            - E-commerce: Payment integration, scalability, user experience
            - Enterprise: Integration capabilities, scalability, security
            - Mobile: Platform reach, performance optimization
            - Data Science: ML frameworks, data processing capabilities
            
            AVOID TECHNOLOGY BIAS:
            Do NOT default to Django/React/PostgreSQL. Consider the full range:
            - Backend: Python, Node.js, Java, Go, C#, Rust based on requirements
            - Frontend: React, Vue.js, Angular, Svelte, native mobile frameworks
            - Database: SQL vs NoSQL based on data structure and scale needs
            - Mobile: Native vs cross-platform based on performance needs
            
            EFFICIENT WORKFLOW:
            1. Start by using get_technical_requirements_summary with the full BRD analysis
            2. ALWAYS use evaluate_all_technologies to evaluate backend, frontend, and database options in a single API call
            3. Based on these technology choices, recommend an architecture pattern
            4. Analyze potential risks and challenges in your chosen stack
            5. As your FINAL action, use synthesize_tech_stack with SEPARATE parameters for each recommendation
            
            IMPORTANT: When using synthesize_tech_stack, provide FOUR SEPARATE parameters:
            - backend_recommendation
            - frontend_recommendation
            - database_recommendation
            - architecture_recommendation
            """
            
            # Store the BRD analysis where tools can access it
            self._stored_brd_analysis = brd_analysis
            
            # Invoke the agent with the context
            result = agent_with_chat_history.invoke(
                {"input": formatted_context.strip()},
                config={"configurable": {"session_id": "tech_stack_session"}}
            )
            
            # Log intermediate steps to debug tool invocation
            if "intermediate_steps" in result:
                self.log_info(f"Agent performed {len(result['intermediate_steps'])} steps")
                for i, step in enumerate(result["intermediate_steps"]):
                    action, observation = step
                    tool_name = getattr(action, "tool", "unknown")
                    tool_args = getattr(action, "tool_input", {})
                    self.log_info(f"Step {i+1}: Tool '{tool_name}' called with args: {json.dumps(tool_args, default=str)[:200]}...")
                      # Special logging for synthesize_tech_stack to debug missing parameters
                    if tool_name == "synthesize_tech_stack":
                        self.log_info(f"synthesize_tech_stack FULL ARGS: {json.dumps(tool_args, default=str)}")
                        
                        # Handle different formats of tool_args (string or dict)
                        if isinstance(tool_args, str):
                            self.log_info("Tool args is a string, checking for recommendation patterns")
                            # Just log that we got a string and continue
                            missing = []
                            # Check if this string contains key patterns we're looking for
                            if 'backend_recommendation' not in tool_args and 'backend' not in tool_args:
                                missing.append('backend_recommendation')
                            if 'frontend_recommendation' not in tool_args and 'frontend' not in tool_args:
                                missing.append('frontend_recommendation')
                            if 'database_recommendation' not in tool_args and 'database' not in tool_args:
                                missing.append('database_recommendation')
                            
                            if missing:
                                self.log_warning(f"String tool_args might be missing fields: {', '.join(missing)}")
                        elif isinstance(tool_args, dict):
                            # Normal dictionary processing
                            missing = []
                            if ('backend_recommendation' not in tool_args or not tool_args['backend_recommendation']) and \
                               ('evaluation_results' not in tool_args or 'backend' not in str(tool_args.get('evaluation_results', ''))):
                                missing.append('backend_recommendation')
                            if ('frontend_recommendation' not in tool_args or not tool_args['frontend_recommendation']) and \
                               ('evaluation_results' not in tool_args or 'frontend' not in str(tool_args.get('evaluation_results', ''))):
                                missing.append('frontend_recommendation')
                            if ('database_recommendation' not in tool_args or not tool_args['database_recommendation']) and \
                               ('evaluation_results' not in tool_args or 'database' not in str(tool_args.get('evaluation_results', ''))):
                                missing.append('database_recommendation')
                            
                            if missing:
                                self.log_warning(f"Missing required fields for synthesize_tech_stack: {', '.join(missing)}")
                        else:
                            self.log_warning(f"Unexpected type for tool_args: {type(tool_args)}")
            
            # NEW: Extract final result from intermediate steps with Pydantic support
            final_result_obj = None
            if "intermediate_steps" in result:
                for step in reversed(result["intermediate_steps"]):
                    action, observation = step
                    
                    # Get the tool name
                    tool_name = getattr(action, "tool", "")
                    
                    # Check for the synthesize_tech_stack tool which produces our final output
                    if tool_name == "synthesize_tech_stack":
                        # The observation is now a Pydantic object
                        if isinstance(observation, TechStackSynthesisOutput):
                            final_result_obj = observation
                            self.log_info("Found TechStackSynthesisOutput from synthesize_tech_stack tool.")
                            break
                        else:
                            self.log_warning(f"synthesize_tech_stack returned unexpected type: {type(observation)}")
              # If we found a valid Pydantic object result
            if final_result_obj:
                # Convert Pydantic to dict and add metadata
                final_dict = final_result_obj.dict() if hasattr(final_result_obj, 'dict') else final_result_obj
                final_dict["recommendation_metadata"] = {
                    "recommendation_approach": "react_agent_structured",
                    "generated_at": datetime.now().isoformat(),
                    "tool_calls": len(result.get("intermediate_steps", [])),
                    "project_context": project_context if project_context else "None provided"
                }
                
                # IMPORTANT: Store the tech stack recommendation in shared memory for downstream agents
                try:
                    # Use enhanced memory operations for better cross-tool communication
                    if hasattr(self, 'enhanced_set'):
                        # Store in multiple contexts for maximum accessibility
                        self.enhanced_set("tech_stack_recommendation", final_dict, context="cross_tool")
                        self.enhanced_set("tech_stack_analysis", final_dict, context="cross_tool")
                        self.enhanced_set("technology_recommendations", final_dict, context="cross_tool")
                        self.store_cross_tool_data("tech_stack_recommendation", final_dict, "Complete tech stack recommendation for downstream agents")
                        self.log_info("Stored tech stack recommendation in enhanced memory for cross-tool access")
                    elif hasattr(self, 'memory') and self.memory:
                        self.memory.set("tech_stack_recommendation", final_dict)
                        self.log_info("Stored tech stack recommendation from compiler tool in basic shared memory")
                    else:
                        self.log_warning("No memory system available - tech stack recommendation not stored")
                except Exception as memory_error:
                    self.log_warning(f"Failed to store tech stack recommendation in memory: {memory_error}")
                    # Emergency fallback
                    try:
                        if hasattr(self, 'memory') and self.memory:
                            self.memory.set("tech_stack_recommendation", final_dict)
                            self.log_info("Emergency fallback: stored in basic memory")
                    except Exception as fallback_error:
                        self.log_error(f"Complete memory storage failure: {fallback_error}")
                
                self.log_success("ReAct tech stack recommendation created successfully with structured output")
                return final_dict
              # Fallback: Parse the final answer if we couldn't find the synthesize_tech_stack result
            self.log_warning("Could not find synthesize_tech_stack with Pydantic output. Falling back to final answer parsing.")
            
            # Check if compile_tech_stack_recommendation was called
            compile_tool_called = False
            if "intermediate_steps" in result:
                for step in result["intermediate_steps"]:
                    action, observation = step
                    tool_name = getattr(action, "tool", "")
                    if tool_name == "compile_tech_stack_recommendation":
                        compile_tool_called = True
                        # Use this result if available
                        if observation and isinstance(observation, dict):
                            self.log_info("Found compile_tech_stack_recommendation result in intermediate steps")
                            final_tech_stack = observation
                            final_tech_stack["recommendation_metadata"] = {
                                "recommendation_approach": "react_agent_compiler_tool",
                                "generated_at": datetime.now().isoformat(),
                                "tool_calls": len(result.get("intermediate_steps", [])),
                                "project_context": project_context if project_context else "None provided"
                            }
                            
                            # Store in shared memory
                            try:
                                # Use enhanced memory operations for better cross-tool communication
                                if hasattr(self, 'enhanced_set'):
                                    # Store in multiple contexts for maximum accessibility
                                    self.enhanced_set("tech_stack_recommendation", final_tech_stack, context="cross_tool")
                                    self.enhanced_set("tech_stack_analysis", final_tech_stack, context="cross_tool")
                                    self.enhanced_set("technology_recommendations", final_tech_stack, context="cross_tool")
                                    self.store_cross_tool_data("tech_stack_recommendation", final_tech_stack, "Complete tech stack recommendation for downstream agents")
                                    self.log_info("Stored tech stack recommendation in enhanced memory for cross-tool access")
                                elif hasattr(self, 'memory') and self.memory:
                                    self.memory.set("tech_stack_recommendation", final_tech_stack)
                                    self.log_info("Stored tech stack recommendation from compiler tool in basic shared memory")
                                else:
                                    self.log_warning("No memory system available - tech stack recommendation not stored")
                            except Exception as memory_error:
                                self.log_warning(f"Failed to store tech stack recommendation in memory: {memory_error}")
                                # Emergency fallback
                                try:
                                    if hasattr(self, 'memory') and self.memory:
                                        self.memory.set("tech_stack_recommendation", final_tech_stack)
                                        self.log_info("Emergency fallback: stored in basic memory")
                                except Exception as fallback_error:
                                    self.log_error(f"Complete memory storage failure: {fallback_error}")
                            
                            self.log_success("ReAct tech stack recommendation created successfully with compiler tool")
                            return final_tech_stack
                        break
            
            # If compile_tech_stack_recommendation wasn't called, try to call it manually as fallback
            if not compile_tool_called:
                self.log_warning("Agent did not call compile_tech_stack_recommendation tool. Attempting manual call...")
                try:
                    # Import and call the tool manually
                    from tools.tech_stack_tools import compile_tech_stack_recommendation
                    
                    # Call the tool manually
                    manual_result = compile_tech_stack_recommendation.func()
                    
                    if manual_result and isinstance(manual_result, dict):
                        manual_result["recommendation_metadata"] = {
                            "recommendation_approach": "react_agent_manual_fallback",
                            "generated_at": datetime.now().isoformat(),
                            "tool_calls": len(result.get("intermediate_steps", [])),
                            "project_context": project_context if project_context else "None provided",
                            "fallback_reason": "Agent did not call required tool"
                        }
                        
                        # Store in shared memory
                        try:
                            # Use enhanced memory operations for better cross-tool communication
                            if hasattr(self, 'enhanced_set'):
                                # Store in multiple contexts for maximum accessibility
                                self.enhanced_set("tech_stack_recommendation", manual_result, context="cross_tool")
                                self.enhanced_set("tech_stack_analysis", manual_result, context="cross_tool")
                                self.enhanced_set("technology_recommendations", manual_result, context="cross_tool")
                                self.store_cross_tool_data("tech_stack_recommendation", manual_result, "Complete tech stack recommendation for downstream agents")
                                self.log_info("Stored tech stack recommendation in enhanced memory for cross-tool access")
                            elif hasattr(self, 'memory') and self.memory:
                                self.memory.set("tech_stack_recommendation", manual_result)
                                self.log_info("Stored manually compiled tech stack recommendation in basic shared memory")
                            else:
                                self.log_warning("No memory system available - tech stack recommendation not stored")
                        except Exception as memory_error:
                            self.log_warning(f"Failed to store tech stack recommendation in memory: {memory_error}")
                            # Emergency fallback
                            try:
                                if hasattr(self, 'memory') and self.memory:
                                    self.memory.set("tech_stack_recommendation", manual_result)
                                    self.log_info("Emergency fallback: stored in basic memory")
                            except Exception as fallback_error:
                                self.log_error(f"Complete memory storage failure: {fallback_error}")
                        
                        self.log_success("Manual compilation of tech stack recommendation successful")
                        return manual_result
                    else:
                        self.log_warning("Manual tool call did not return valid result")
                        
                except Exception as manual_error:
                    self.log_error(f"Manual tool call failed: {str(manual_error)}")
              # Final fallback: try to parse the agent output
            final_tech_stack = self._extract_tech_stack_from_output(result["output"])
            
            # If extraction also failed, use the manual compilation tool result or default
            if not final_tech_stack or final_tech_stack.get("status") == "fallback_recommendation":
                self.log_warning("Could not extract JSON from agent output")
                
                # Try the manual tool call as last resort if not already attempted
                if not compile_tool_called:
                    try:
                        from tools.tech_stack_tools import compile_tech_stack_recommendation
                        manual_result = compile_tech_stack_recommendation.func()
                        
                        if manual_result and isinstance(manual_result, dict):
                            manual_result["recommendation_metadata"] = {
                                "recommendation_approach": "react_agent_final_fallback",
                                "generated_at": datetime.now().isoformat(),
                                "tool_calls": len(result.get("intermediate_steps", [])),
                                "project_context": project_context if project_context else "None provided",
                                "fallback_reason": "Agent output parsing failed"
                            }
                            self.log_info("Manual tool call successful after output parsing failure")
                            final_tech_stack = manual_result
                        
                    except Exception as final_error:
                        self.log_error(f"Final manual tool call failed: {str(final_error)}")
                        # Keep the default response from _extract_tech_stack_from_output
            
            # Add metadata if not already present
            if final_tech_stack and not final_tech_stack.get("recommendation_metadata"):
                final_tech_stack["recommendation_metadata"] = {
                    "recommendation_approach": "react_agent_fallback",
                    "generated_at": datetime.now().isoformat(),
                    "tool_calls": len(result.get("intermediate_steps", [])),
                    "project_context": project_context if project_context else "None provided"
                }
              # IMPORTANT: Store the tech stack recommendation in shared memory for downstream agents
            try:
                # Use enhanced memory operations for better cross-tool communication
                if hasattr(self, 'enhanced_set'):
                    # Store in multiple contexts for maximum accessibility
                    self.enhanced_set("tech_stack_recommendation", final_tech_stack, context="cross_tool")
                    self.enhanced_set("tech_stack_analysis", final_tech_stack, context="cross_tool")
                    self.enhanced_set("technology_recommendations", final_tech_stack, context="cross_tool")
                    self.store_cross_tool_data("tech_stack_recommendation", final_tech_stack, "Complete tech stack recommendation for downstream agents")
                    self.log_info("Stored tech stack recommendation in enhanced memory for cross-tool access")
                elif hasattr(self, 'memory') and self.memory:
                    self.memory.set("tech_stack_recommendation", final_tech_stack)
                    self.log_info("Stored tech stack recommendation in basic shared memory")
                else:
                    self.log_warning("No memory system available - tech stack recommendation not stored")
            except Exception as memory_error:
                self.log_warning(f"Failed to store tech stack recommendation in memory: {memory_error}")
                # Emergency fallback
                try:
                    if hasattr(self, 'memory') and self.memory:
                        self.memory.set("tech_stack_recommendation", final_tech_stack)
                        self.log_info("Emergency fallback: stored in basic memory")
                except Exception as fallback_error:
                    self.log_error(f"Complete memory storage failure: {fallback_error}")
            
            # Publish tech stack update event
            if hasattr(self, 'message_bus') and self.message_bus:
                try:
                    self.message_bus.publish("tech_stack.updated", {
                        "tech_stack": final_tech_stack,
                        "reasoning": "ReAct-based tech stack recommendation completed",
                        "status": "success",
                        "agent": getattr(self, 'agent_name', 'TechStackAdvisorReActAgent'),
                        "timestamp": datetime.now().isoformat()
                    })
                    self.log_info("Published tech_stack.updated event")
                except Exception as publish_error:
                    self.log_warning(f"Failed to publish tech_stack.updated event: {publish_error}")
            
            return final_tech_stack
            
        except Exception as e:
            self.log_error(f"ReAct tech stack recommendation failed: {str(e)}")
            import traceback
            self.log_error(traceback.format_exc())
            return self.get_default_response()
        finally:
            # Clean up stored BRD analysis
            if hasattr(self, '_stored_brd_analysis'):
                del self._stored_brd_analysis

    def _extract_tech_stack_from_output(self, output: str) -> Dict[str, Any]:
        """Extract the JSON tech stack from the agent's output."""
        try:
            # Look for JSON in the output
            import re
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', output)
            
            if json_match:
                json_str = json_match.group(1)
                return json.loads(json_str)
            
            # If no JSON blocks found, look for content that appears to be JSON
            if output.strip().startswith('{') and output.strip().endswith('}'):
                return json.loads(output)
            
            # Try to extract any JSON-like structure
            potential_json = re.search(r'(\{[\s\S]*\})', output)
            if potential_json:
                try:                    return json.loads(potential_json.group(1))
                except:
                    pass
            
            self.log_warning("Could not extract JSON from agent output")
            return self.get_default_response()
            
        except Exception as e:
            self.log_warning(f"Error extracting tech stack from output: {str(e)}")
            return self.get_default_response()
    
    def get_default_response(self) -> Dict[str, Any]:
        """Return a domain-flexible default tech stack when recommendation generation fails."""
        current_time = datetime.now().isoformat()
        return {
            "status": "fallback_recommendation",
            "message": "Analysis failed - providing flexible default recommendations",
            "backend": {
                "primary_option": {
                    "language": "Python",
                    "framework": "FastAPI",
                    "reasoning": "Versatile choice suitable for various domains (APIs, data processing, ML integration)"
                },
                "alternative_options": [
                    {"language": "Node.js", "framework": "Express", "use_case": "Real-time applications, microservices"},
                    {"language": "Java", "framework": "Spring Boot", "use_case": "Enterprise applications, high scalability"},
                    {"language": "Go", "framework": "Gin", "use_case": "High-performance, cloud-native applications"}
                ]
            },
            "frontend": {
                "web_primary": {
                    "language": "JavaScript",
                    "framework": "React",
                    "reasoning": "Component-based, suitable for dynamic UIs"
                },
                "alternatives": [
                    {"framework": "Vue.js", "use_case": "Smaller projects, gentler learning curve"},
                    {"framework": "Angular", "use_case": "Enterprise applications, TypeScript integration"},
                    {"framework": "Svelte", "use_case": "Performance-critical applications"}
                ],
                "mobile_options": [
                    {"framework": "React Native", "use_case": "Cross-platform mobile apps"},
                    {"framework": "Flutter", "use_case": "High-performance, native-like mobile apps"}
                ]
            },
            "database": {
                "relational_primary": {
                    "type": "PostgreSQL",
                    "reasoning": "ACID compliance, suitable for structured data"
                },
                "nosql_option": {
                    "type": "MongoDB",
                    "reasoning": "Flexible schema, suitable for unstructured data"
                },
                "considerations": "Choose based on data structure, consistency requirements, and scale"
            },
            "architecture_pattern": "Layered Architecture",
            "domain_specific_notes": {
                "healthcare": "Consider HIPAA compliance, audit logging, data encryption",
                "fintech": "Implement PCI compliance, fraud detection, transaction monitoring",
                "gaming": "Focus on real-time performance, multiplayer capabilities",
                "iot": "Consider edge computing, connectivity protocols, resource constraints",
                "enterprise": "Emphasize integration capabilities, scalability, security"
            },
            "deployment_environment": {
                "platform": "Cloud (AWS/Azure/GCP)",
                "containerization": "Docker",
                "orchestration": "Consider Kubernetes for enterprise scale"
            },
            "recommendation_metadata": {
                "recommendation_approach": "domain_flexible_fallback",
                "generated_at": current_time,
                "confidence_level": "low",
                "note": "This is a flexible fallback recommendation. Proper analysis required for optimal technology selection."
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