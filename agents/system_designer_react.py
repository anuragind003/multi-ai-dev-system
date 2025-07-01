"""
Enhanced ReAct-based System Designer Agent with Hybrid Validation and API Token Optimization.
Uses reasoning and tool-execution loop to create comprehensive system designs.
"""

from datetime import datetime
import json
import logging
import time
from typing import Dict, Any, List, Optional, Tuple

# Core dependencies
from langchain import hub
from langchain_core.language_models import BaseLanguageModel
from langchain_core.retrievers import BaseRetriever
from langchain_core.tools import Tool
from langchain_core.messages import SystemMessage
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain.agents import AgentExecutor, create_json_chat_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory

# Local imports
from models.data_contracts import (
    ProjectRequirementsSummaryOutput,
    ArchitecturePatternOutput,
    SystemComponentsOutput,
    ComponentDesignOutput,
    DataModelOutput,
    ApiEndpointsOutput,
    SecurityArchitectureOutput,
    SystemDesignOutput,
    DesignQualityOutput,
    MultipleComponentStructuresOutput
)
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

# Import design tools
from tools.design_tools import (
    summarize_project_requirements,
    select_architecture_pattern,
    identify_system_components,
    design_component_structure,
    design_data_model,
    design_api_endpoints,
    design_security_architecture,
    synthesize_system_design,
    evaluate_design_quality,
    design_multiple_component_structures
)

from utils.safe_console_callback_handler import SafeConsoleCallbackHandler, create_detailed_callback

logger = logging.getLogger(__name__)

class SystemDesignerReActAgent(BaseAgent):
    """
    Enhanced ReAct-based System Designer Agent with hybrid validation and API optimization.
    
    Features:
    - 3-layer hybrid validation for all inputs/outputs
    - API token optimization with caching
    - Enhanced error recovery and resilience
    - Performance tracking and metrics
    - Robust tool input processing for ReAct agents
    """
    
    def __init__(
        self,
        llm: BaseLanguageModel,
        memory,
        temperature: float = None,
        rag_retriever: Optional[BaseRetriever] = None,
        message_bus = None,
        enable_enhanced_validation: bool = True,
        enable_api_optimization: bool = True
    ):
        """Initialize the Enhanced System Designer Agent with validation and optimization."""
        # If no specific temperature provided, get from settings
        if temperature is None:
            temperature = get_agent_temperature("System Designer Agent")
            
        super().__init__(
            llm=llm,
            memory=memory,
            agent_name="System Designer Agent",
            temperature=temperature,
            rag_retriever=rag_retriever,
            message_bus=message_bus
        )
        
        self.message_bus = message_bus
        
        # Enhanced components
        self.json_handler = JsonHandler()
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        
        # Initialize enhanced memory (inherits from BaseAgent which has enhanced memory mixin)
        self._init_enhanced_memory()
        
        # Initialize RAG context
        self.rag_manager = get_rag_manager()
        if self.rag_manager:
            self.logger.info("RAG manager available for enhanced system design")
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
        
        self._init_agent()
        
    def _get_react_prompt(self):
        """Initializes the ReAct agent's prompt with token efficiency instructions."""
        prompt = hub.pull("hwchase17/react-chat-json")        
        new_system_message = """You are an expert System Designer specializing in creating 
    software architectures and system designs for ANY APPLICATION DOMAIN with STRICT API CALL EFFICIENCY.
    
    **DOMAIN AND SCALE AWARENESS:**
    - Healthcare: Consider HIPAA/GDPR compliance, data sensitivity, audit trails, availability requirements
    - Financial/FinTech: Emphasize security, compliance (PCI-DSS, SOX), transaction integrity, fraud detection
    - IoT/Edge: Focus on resource constraints, real-time processing, connectivity, device management
    - E-commerce: Consider scalability, payment processing, inventory management, user experience
    - Enterprise: Emphasize integration capabilities, role-based access, workflow management
    - Startups/MVPs: Balance simplicity with growth potential, cost-effectiveness
    - Large-scale: Prioritize microservices, caching, load balancing, data partitioning
    - Real-time: Focus on event-driven architecture, streaming, low latency designs

    APPROACH WITH MINIMAL API CALLS:
    1. First understand the project requirements (1 call)
    2. Select an architecture pattern that fits the requirements (1 call) - REMEMBER THIS RESULT!
    3. Identify the main system components (1 call) - REMEMBER THIS RESULT!
    4. Use the BATCH TOOL 'design_multiple_component_structures' to design ALL components at once (1 call)
    DO NOT design components one by one - use the batch tool to avoid API rate limits
    5. Create a data model (1 call)
    6. Design API endpoints if needed (1 call)
    7. Design security architecture (1 call) - USE THE ARCHITECTURE PATTERN FROM STEP 2!
    8. Synthesize all designs into a comprehensive system design (1 call)
    9. Evaluate the quality of your design (1 call)

    🔴 CRITICAL: MAINTAIN STATE BETWEEN TOOL CALLS!
    - Step 1 gives you a requirements_summary - PASS THIS to ALL subsequent tools that need it
    - Step 2 gives you an architecture pattern (e.g., "Microservices") - USE THIS in Step 7
    - Step 3 gives you component names - USE THESE in subsequent steps
    - Step 4 gives you component designs - USE THESE in later steps
    - Always reference previous tool results when they are required parameters!
    
    EXAMPLE: After calling summarize_project_requirements, extract the summary and use it:
    ```json
    {
    "action": "design_multiple_component_structures",
    "action_input": {
        "component_names": ["User Interface", "API Gateway"],
        "requirements_summary": "USER MANAGEMENT SYSTEM WITH AUTHENTICATION AND ROLE-BASED ACCESS"
    }
    }
    ```

    IMPORTANT API EFFICIENCY INSTRUCTIONS:
    1. ALWAYS use the batch tool 'design_multiple_component_structures' to design ALL components at once
    2. DO NOT design components individually - this wastes API calls and triggers rate limits
    3. When designing API endpoints, do all of them in a single call 
    4. Extract only the information needed for each specific task
    5. Keep JSON handling efficient - don't repeat large objects in your thinking    **CRITICAL JSON FORMAT FOR TOOL CALLS:**
    When calling tools, the action_input MUST be a JSON object, NOT a string. Use this EXACT format:
    
    CORRECT (action_input is an object):
    ```json
    {
    "action": "summarize_project_requirements",
    "action_input": {
        "brd_analysis_json": null
    }
    }
    ```
    
    WRONG (action_input is a string - THIS WILL FAIL):
    ```json
    {
    "action": "summarize_project_requirements", 
    "action_input": "{\"brd_analysis_json\": null}"
    }
    ```
    
    **CRITICAL: action_input must ALWAYS be a JSON object {}, NEVER a string!**
    **NOTE: Tools will access complex data from shared memory, so you can use simple values or null.**

    **CRITICAL TOOL USAGE FOR BATCH DESIGN:**
    When you use the `design_multiple_component_structures` tool, format your `action_input` as a clean JSON object:
    ```json
    {
    "action": "design_multiple_component_structures",
    "action_input": {
        "component_names": ["User Interface", "API Gateway", "Authentication Service", "Database Layer"],
        "requirements_summary": "The project requires a secure user management system with role-based access control."
    }
    }
    ```
    
    🔴 CRITICAL: ALWAYS pass the requirements_summary from your first tool call to ALL subsequent tools!    **Example of CORRECT batch tool call:**
    ```json
    {
    "action": "design_multiple_component_structures",
    "action_input": {
        "component_names": ["User Interface", "API Gateway", "Authentication Service", "Database Layer"],
        "requirements_summary": "System requirements from previous tool call"
    }
    }    **CRITICAL TOOL VALIDATIONS - READ CAREFULLY:**
    1. When using `design_data_model` tool, you MUST provide ALL THREE required parameters:
       - requirements_summary: A string with the requirements
       - components: A JSON string containing the system components (must use json.dumps() on array)
       - database_technology: The database technology to use (e.g., "PostgreSQL", "MongoDB")
       
       NOTE: If you pass your parameters as a JSON object to the first parameter, 
       the system will attempt to extract the individual parameters, but it's
       better to pass them separately as shown in the example below.
       
    2. When using `design_api_endpoints` tool, provide BOTH required parameters:
       - requirements_summary: A string with the requirements
       - components: A JSON string array of component names
       
       **Example of CORRECT API endpoints tool call:**
       ```json
       {
       "action": "design_api_endpoints",
       "action_input": {
           "requirements_summary": "System requirements from previous tool",
           "components": "Component list from previous tool"
       }
       }
       ```
      
    **EXAMPLE OF CORRECT data model tool call:**
    ```json
    {
    "action": "design_data_model",
    "action_input": {
        "requirements_summary": "System requirements from previous tool",
        "components": "Component list from previous tool",
        "database_technology": "PostgreSQL"
    }
    }
    ```
    
    **⚠️ CRITICAL REQUIREMENT - DO NOT SKIP ANY PARAMETER:**
    Before creating a data model, first identify components and the database technology, then ALWAYS include:
    1. requirements_summary - A string with requirements
    2. components - A JSON string array of component names 
    3. database_technology - A string specifying database type
    
    ❌ INCORRECT (missing parameters - will cause error):
    ```json
    {
    "action": "design_data_model",
    "action_input": {
        "requirements_summary": "The system requires storing tasks with descriptions and timestamps"
        // MISSING components and database_technology - THIS WILL FAIL!
    }
    }
    ```
      **CRITICAL TOOL USAGE FOR SECURITY ARCHITECTURE DESIGN:**
    
    🔴 MANDATORY REQUIREMENT: You MUST maintain state between tool calls!
    
    When you use the `design_security_architecture` tool, you MUST ALWAYS pass the architecture pattern from the previous `select_architecture_pattern` result. 
    
    STEP-BY-STEP PROCESS:
    1. First call `select_architecture_pattern` and remember the result (e.g., "Microservices")
    2. When calling `design_security_architecture`, use that exact pattern value:
    
    ```json
    {
    "action": "design_security_architecture",
    "action_input": {
        "requirements_summary": "System requirements from previous tool",
        "architecture_pattern": "Architecture pattern from select_architecture_pattern tool"
    }
    }
    ```
    
    ❌ CRITICAL ERROR - This will cause the tool to use "Generic Architecture" default:
    ```json
    {
    "action": "design_security_architecture",
    "action_input": {
        "requirements_summary": "System requirements from previous tool"
        // MISSING architecture_pattern - SYSTEM WILL FAIL TO USE YOUR SELECTED PATTERN!
    }
    }
    ```
    
    ⚠️ IMPORTANT: Always refer back to previous tool results and extract the values you need for subsequent tools."""

        for message in prompt.messages:
            if isinstance(message, SystemMessage):
                message.content = new_system_message
                break
        return prompt
        
    def _init_agent(self):
        """Initialize the ReAct agent with properly formatted Tool objects."""
        # This will be populated in the run() method before execution
        self.tools = []
        
        # Get the improved prompt with token efficiency instructions
        self.react_prompt = self._get_react_prompt()
        
    def run(self, brd_analysis: Dict[str, Any], tech_stack_recommendation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate system design using the ReAct framework.
        
        Args:
            brd_analysis: Analyzed business requirements document
            tech_stack_recommendation: Recommended technology stack
            
        Returns:
            Comprehensive system design        """
        self.log_start("Starting ReAct-based system design")
        
        try:
            # Store the analysis and tech stack in instance variables for tool access
            self._stored_brd_analysis = brd_analysis
            self._stored_tech_stack = tech_stack_recommendation
            
            # IMPORTANT: Store requirements in shared memory so tools can access them
            try:
                # Use enhanced memory operations for better cross-tool communication
                if hasattr(self, 'enhanced_set'):
                    # Store BRD analysis and tech stack in enhanced memory with multiple contexts
                    self.enhanced_set("brd_analysis", brd_analysis, context="cross_tool")
                    self.enhanced_set("tech_stack_recommendation", tech_stack_recommendation, context="cross_tool")
                    
                    # Extract and store requirements summary for tool access
                    requirements_summary = self._extract_requirements_summary(brd_analysis, tech_stack_recommendation)
                    self.enhanced_set("requirements_summary", requirements_summary, context="cross_tool")
                    self.enhanced_set("project_requirements", requirements_summary, context="cross_tool")
                    
                    # Store with cross-tool data method for better discoverability
                    self.store_cross_tool_data("requirements_summary", requirements_summary, "Project requirements summary for design tools")
                    self.store_cross_tool_data("brd_analysis", brd_analysis, "Complete BRD analysis for design tools")
                    self.store_cross_tool_data("tech_stack_recommendation", tech_stack_recommendation, "Tech stack recommendation for design tools")
                    
                    self.logger.info("Stored requirements and analysis data in enhanced memory for cross-tool access")
                    
                elif hasattr(self, 'memory') and self.memory:
                    # Fallback to basic memory
                    self.memory.set("brd_analysis", brd_analysis)
                    self.memory.set("tech_stack_recommendation", tech_stack_recommendation)
                    
                    # Extract and store a requirements summary for tool access
                    requirements_summary = self._extract_requirements_summary(brd_analysis, tech_stack_recommendation)
                    self.memory.set("requirements_summary", requirements_summary)
                    self.memory.set("project_requirements", requirements_summary)
                    
                    # Also try to store in persistent memory for cross-tool access
                    try:
                        from enhanced_memory_manager import EnhancedSharedProjectMemory as SharedProjectMemory
                        persistent_memory = SharedProjectMemory(memory_type='persistent')
                        persistent_memory.set("requirements_summary", requirements_summary)
                        persistent_memory.set("project_requirements", requirements_summary)
                        self.logger.info("Stored requirements in both agent memory and persistent shared memory")
                    except Exception as persistent_error:
                        self.logger.warning(f"Failed to store in persistent memory: {persistent_error}")
                        self.logger.info("Stored requirements in basic agent memory only")
                else:
                    self.logger.warning("No memory system available - tools may not have access to requirements")
            except Exception as memory_error:
                self.logger.warning(f"Failed to store requirements in memory: {memory_error}")
                # Emergency fallback
                try:
                    if hasattr(self, 'memory') and self.memory:
                        requirements_summary = self._extract_requirements_summary(brd_analysis, tech_stack_recommendation)
                        self.memory.set("requirements_summary", requirements_summary)
                        self.logger.info("Emergency fallback: stored basic requirements summary")
                except Exception as fallback_error:
                    self.logger.error(f"Complete memory storage failure: {fallback_error}")
            
            # Enhanced validation disabled - using universal wrapper instead
            if False:  # self.enable_enhanced_validation:
                self.tools = [
                    enhanced_tool_validator.wrap_tool(
                        summarize_project_requirements,
                        expected_fields=["brd_analysis_json"],
                        agent_name=self.agent_name
                    ),
                    enhanced_tool_validator.wrap_tool(
                        select_architecture_pattern,
                        expected_fields=["requirements_summary"],
                        agent_name=self.agent_name
                    ),
                    enhanced_tool_validator.wrap_tool(
                        identify_system_components,
                        expected_fields=["requirements_summary"],
                        agent_name=self.agent_name
                    ),
                    design_component_structure,  # Keep one for compatibility
                    enhanced_tool_validator.wrap_tool(
                        design_multiple_component_structures,
                        expected_fields=["component_names", "requirements_summary"],
                        agent_name=self.agent_name
                    ),
                    enhanced_tool_validator.wrap_tool(
                        design_data_model,
                        expected_fields=["requirements_summary", "components", "database_technology"],
                        agent_name=self.agent_name
                    ),
                    enhanced_tool_validator.wrap_tool(
                        design_api_endpoints,
                        expected_fields=["requirements_summary", "components"],
                        agent_name=self.agent_name
                    ),
                    enhanced_tool_validator.wrap_tool(
                        design_security_architecture,
                        expected_fields=["requirements_summary", "architecture_pattern"],
                        agent_name=self.agent_name
                    ),
                    enhanced_tool_validator.wrap_tool(
                        synthesize_system_design,
                        expected_fields=["requirements_summary"],
                        agent_name=self.agent_name
                    ),
                    enhanced_tool_validator.wrap_tool(
                        evaluate_design_quality,
                        expected_fields=["system_design"],
                        agent_name=self.agent_name
                    )
                ]
            else:
                # Use the @tool decorated functions directly without wrapping them in Tool objects
                # This prevents double-wrapping issues that cause parameter mapping problems
                self.tools = [
                    summarize_project_requirements,
                    select_architecture_pattern,
                    identify_system_components,
                    design_component_structure,
                    design_multiple_component_structures,
                    design_data_model,
                    design_api_endpoints,
                    design_security_architecture,
                    synthesize_system_design,
                    evaluate_design_quality
                ]
            
            # Create the agent with temperature binding
            llm_with_temp = self.llm.bind(temperature=self.default_temperature)
            agent = create_json_chat_agent(
                llm=llm_with_temp,
                tools=self.tools,
                prompt=self.react_prompt
            )
            
            # Create the executor with return_intermediate_steps set to True
            agent_executor = AgentExecutor(
                agent=agent,
                tools=self.tools,
                verbose=False,  # Disable to avoid I/O errors
                handle_parsing_errors=True,
                max_iterations=15,
                return_intermediate_steps=True,
                callbacks=[create_detailed_callback(max_output_length=3000)]  # Show full tool outputs
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
            
            # Create simplified context that won't confuse the LLM with nested JSON
            project_name = brd_analysis.get('project_name', 'Unknown Project')
            backend_framework = tech_stack_recommendation.get('backend', {}).get('framework', 'N/A')
            frontend_framework = tech_stack_recommendation.get('frontend', {}).get('framework', 'N/A')

            # Create a clear instruction for the agent with proper JSON formatting examples
            formatted_context = f"""
            You need to create a complete system design for the project: '{project_name}'.

            KEY DATA AVAILABLE:
            - Project Name: {project_name}
            - Backend Framework: {backend_framework}
            - Frontend Framework: {frontend_framework}

            CRITICAL JSON FORMAT RULES:
            1. action_input must ALWAYS be a JSON object {{}}, NEVER a string!
            2. Use this EXACT format for all tool calls:

            CORRECT format example:
            {{
                "action": "summarize_project_requirements",
                "action_input": {{
                    "brd_analysis_json": "placeholder_for_brd_data"
                }}
            }}

            WRONG format (DO NOT USE):
            {{
                "action": "summarize_project_requirements",
                "action_input": "{{\"brd_analysis_json\": \"data\"}}"
            }}

            Follow your step-by-step process:
            1. Call summarize_project_requirements first (the tool will access BRD data from memory)
            2. Then continue with the other tools systematically
            3. Always use action_input as a JSON object, not a string
            
            Start with the first tool call now. The BRD analysis data is available in memory.
            """

            # Pass the input with clear instructions
            result = agent_with_chat_history.invoke(
                {
                    "input": formatted_context.strip()
                },
                config={"configurable": {"session_id": "system_design_session", "agent_context": self.agent_name}}
            )
            
            # Extract final result from intermediate steps - look for synthesize_system_design
            if "intermediate_steps" in result:
                for step in reversed(result["intermediate_steps"]):
                    action, observation = step
                    
                    # Get the tool name
                    tool_name = getattr(action, "tool", "")
                    
                    if tool_name == "synthesize_system_design":
                        try:
                            # The observation may be a JSON string or a dict
                            if isinstance(observation, dict):
                                final_design = observation
                            elif isinstance(observation, str):
                                # Try to parse JSON
                                final_design = json.loads(observation)
                            else:
                                # If it's an object with a dict method (Pydantic)
                                final_design = observation.dict() if hasattr(observation, 'dict') else observation
                                
                            self.log_info("Found final system design from synthesize_system_design tool.")
                            
                            # Add metadata
                            final_design["metadata"] = {
                                "design_approach": "react_agent_structured",
                                "generated_at": datetime.now().isoformat(),
                                "tool_calls": len(result.get("intermediate_steps", [])),
                            }
                            
                            self.log_success("ReAct system design created successfully")
                            return final_design
                        except Exception as e:
                            self.log_error(f"Error processing synthesize_system_design result: {str(e)}")
            
            # If we couldn't find the final design in the tools, try extract from the output
            self.log_warning("Could not find synthesize_system_design output. Falling back to final answer parsing.")
            
            # Try to extract JSON from the final output
            json_handler = JsonHandler()
            try:
                final_design = json_handler.extract_json_from_text(result["output"])
                if final_design:
                    # Add metadata
                    final_design["metadata"] = {
                        "design_approach": "react_agent_fallback",
                        "generated_at": datetime.now().isoformat(),
                        "tool_calls": len(result.get("intermediate_steps", [])),
                    }
                    
                    # Publish system design completion event
                    if hasattr(self, 'message_bus') and self.message_bus:
                        try:
                            self.message_bus.publish("system.design.complete", {
                                "design": final_design,
                                "architecture_pattern": final_design.get("architecture", {}).get("pattern", "Unknown"),
                                "components_count": len(final_design.get("architecture", {}).get("components", {})),
                                "status": "success",
                                "agent": getattr(self, 'agent_name', 'SystemDesignerReActAgent'),
                                "timestamp": datetime.now().isoformat()
                            })
                            self.log_info("Published system.design.complete event")
                        except Exception as publish_error:
                            self.log_warning(f"Failed to publish system.design.complete event: {publish_error}")
                    
                    return final_design
            except Exception as e:
                self.log_error(f"Error extracting JSON from output: {str(e)}")
              
            # Last resort - use default response
            return self.get_default_response()
            
        except Exception as e:
            self.log_error(f"ReAct system design generation failed: {str(e)}")
            import traceback
            self.log_error(traceback.format_exc())
            return self.get_default_response()
        finally:
            # Clean up stored data
            if hasattr(self, '_stored_brd_analysis'):
                del self._stored_brd_analysis
            if hasattr(self, '_stored_tech_stack'):
                del self._stored_tech_stack
    
    def get_default_response(self) -> Dict[str, Any]:
        """Return a default system design when generation fails."""
        current_time = datetime.now().isoformat()
        return {
            "system_name": "Default System Design",
            "architecture_pattern": "Layered Architecture",
            "components": [
                {
                    "name": "Frontend Layer",
                    "description": "User interface components",
                    "subcomponents": ["User Interface", "UI Logic"]
                },
                {
                    "name": "Application Layer",
                    "description": "Business logic and application processing",
                    "subcomponents": ["Services", "Controllers"]
                },
                {
                    "name": "Data Layer",
                    "description": "Data access and storage",
                    "subcomponents": ["Data Access Objects", "Repositories"]
                }
            ],
            "data_model": {
                "entities": [
                    {
                        "name": "User",
                        "attributes": ["id", "username", "email"],
                        "relationships": []
                    },
                    {
                        "name": "Resource",
                        "attributes": ["id", "name", "description"],
                        "relationships": []
                    }
                ]
            },
            "api_endpoints": [
                {
                    "path": "/api/v1/users",
                    "method": "GET",
                    "description": "Get all users"
                },
                {
                    "path": "/api/v1/resources",
                    "method": "GET",
                    "description": "Get all resources"
                }
            ],
            "security_architecture": {
                "authentication": "JWT-based authentication",
                "authorization": "Role-based access control",
                "data_protection": "Encryption at rest and in transit"
            },
            "metadata": {
                "design_approach": "default_fallback",
                "generated_at": current_time,
                "note": "This is a default system design generated due to an error"
            }
        }
    
    def _extract_requirements_summary(self, brd_analysis: Dict[str, Any], tech_stack: Dict[str, Any]) -> str:
        """Extract a concise requirements summary for tool access."""
        try:
            summary_parts = []
            
            # Extract from BRD analysis
            if isinstance(brd_analysis, dict):
                if "functional_requirements" in brd_analysis:
                    summary_parts.append(f"Functional Requirements: {brd_analysis['functional_requirements']}")
                if "non_functional_requirements" in brd_analysis:
                    summary_parts.append(f"Non-functional Requirements: {brd_analysis['non_functional_requirements']}")
                if "technical_requirements" in brd_analysis:
                    summary_parts.append(f"Technical Requirements: {brd_analysis['technical_requirements']}")
                if "project_summary" in brd_analysis:
                    summary_parts.append(f"Project Summary: {brd_analysis['project_summary']}")
            
            # Extract from tech stack
            if isinstance(tech_stack, dict):
                if "recommended_stack" in tech_stack:
                    summary_parts.append(f"Technology Stack: {tech_stack['recommended_stack']}")
                if "rationale" in tech_stack:
                    summary_parts.append(f"Stack Rationale: {tech_stack['rationale']}")
            
            # Create the summary
            if summary_parts:
                return " | ".join(summary_parts)
            else:
                return f"System requirements based on BRD analysis and {tech_stack.get('primary_language', 'modern')} technology stack"
                
        except Exception as e:
            self.logger.warning(f"Error extracting requirements summary: {e}")
            return "System requirements extracted from business requirements document"
    
    def _validate_input(self, input_data: Any, context: str = "") -> Any:
        """Validate input using hybrid validation system."""
        if not self.enable_enhanced_validation:
            return input_data
            
        from pydantic import BaseModel
        from typing import List
        
        # Simple validation schema for system design inputs
        class SystemDesignInputSchema(BaseModel):
            project_name: str = "Unknown Project"
            requirements: List[str] = []
            
        try:
            result = self.hybrid_validator.validate_progressive(
                raw_input=input_data,
                pydantic_model=SystemDesignInputSchema,
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
