"""
ReAct-based System Designer Agent for Multi-AI Development System.
Uses reasoning and tool-execution loop to create comprehensive system designs.
"""

from datetime import datetime
import json
import logging
from typing import Dict, Any, List, Optional, Tuple

# Core dependencies
from langchain_core.language_models import BaseLanguageModel
from langchain_core.tools import tool, Tool
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
# Fix: Use langchain.memory instead of langchain_hub
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain.agents import AgentExecutor, create_json_chat_agent
# Remove this line: from langchain_hub import hub
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory

# Local imports
from agents.base_agent import BaseAgent
from tools.json_handler import JsonHandler
from agent_temperatures import get_agent_temperature

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

# Import Pydantic models for wrapped tools
from tools.models import (
    ProjectRequirementsSummaryInput,
    ArchitecturePatternSelectionInput,
    SystemComponentsIdentificationInput,
    SystemDesignSynthesisInput,
    SystemDesignOutput
)

class SystemDesignerReActAgent(BaseAgent):
    """
    ReAct-based System Designer Agent for generating detailed system architecture and design.
    Uses reasoning and tool-execution loop for comprehensive system design.
    """
    
    def __init__(
        self,
        llm: BaseLanguageModel,
        memory,
        temperature: float = None,
        rag_retriever = None,
        message_bus = None
    ):
        """Initialize the System Designer Agent with LLM and configuration."""
        # If no specific temperature provided, get from settings
        if temperature is None:
            temperature = get_agent_temperature("System Designer Agent", 0.2)
            
        super().__init__(
            llm=llm,
            memory=memory,
            agent_name="System Designer Agent",
            temperature=temperature,
            rag_retriever=rag_retriever
        )
        
        self.message_bus = message_bus
        self._init_agent()
    
    def _init_agent(self):
        """Initialize the ReAct agent with the necessary tools."""
        # Create the list of tools the agent can use - will be populated in run()
        self.tools = []
        
        # Create a local implementation of the ReAct JSON chat prompt instead of using hub
        system_message = """You are an expert System Designer specializing in creating 
software architectures and system designs for applications.

APPROACH:
1. First understand the project requirements
2. Select an architecture pattern that fits the requirements
3. Identify the main system components
4. Design each component in detail
5. Create a data model
6. Design API endpoints if needed
7. Design security measures
8. Synthesize all designs into a comprehensive system design
9. Evaluate the quality of your design

IMPORTANT: With the new Pydantic-based tools, you no longer need to format your inputs as JSON.
Simply provide the required parameters directly to each tool. The system will handle validation automatically.

Follow this process:
1. Start by summarizing the project requirements
2. Select an architecture pattern based on the requirements
3. Identify the main system components
4. For each component, design its structure in detail
5. Create a data model
6. Design API endpoints
7. Design security architecture
8. Synthesize all designs into a comprehensive system design
9. Evaluate the quality of your design"""

        human_message = "I need your help with a system design task."
          # Create our own react prompt template that includes the required variables
        self.react_prompt = ChatPromptTemplate.from_messages([
            ("system", system_message + """

You have access to the following tools:
{tools}

Use a json blob to specify a tool by providing an action key (tool name) and an action_input key (tool input).

Valid "action" values: "Final Answer" or {tool_names}

Provide only ONE action per $JSON_BLOB, as shown:

```
{{
  "action": $TOOL_NAME,
  "action_input": $INPUT
}}
```

Follow this format:

Question: input question to answer
Thought: consider previous and subsequent steps
Action:
```
$JSON_BLOB
```
Observation: action result
... (repeat Thought/Action/Observation as needed)
Thought: I now know the final answer
Action:
```
{{
  "action": "Final Answer",
  "action_input": "Final response to human"
}}
```"""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])

    def run(self, brd_analysis: Dict[str, Any], tech_stack_recommendation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate system design using the ReAct framework.
        
        Args:
            brd_analysis: Analyzed business requirements document
            tech_stack_recommendation: Recommended technology stack
            
        Returns:
            Comprehensive system design
        """
        self.log_start("Starting ReAct-based system design")
        
        try:
            # Store the analysis and tech stack in instance variables for tool access
            self._stored_brd_analysis = brd_analysis
            self._stored_tech_stack = tech_stack_recommendation
            
            # Create wrapped tools that automatically inject the BRD data
            self.tools = self._create_wrapped_tools()
            
            # Create the agent with standard temperature binding
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
                verbose=True,
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
            
            # Prepare simplified input that doesn't include the massive JSON
            formatted_context = f"""
            Your goal is to create a comprehensive system design for this project.
            
            Project name: {brd_analysis.get('project_name', 'Unknown Project')}
            
            Follow these steps in order:
            1. Start by using summarize_project_requirements_wrapped with a simple action input like {{"analyze": true}}
            2. Based on requirements and the tech stack, select an appropriate architecture pattern
            3. Identify the main system components
            4. Design each component's structure in detail
            5. Design the data model based on the recommended database technology
            6. Design the API endpoints
            7. Design the security architecture
            8. As your FINAL action, synthesize all designs into a comprehensive system design
            """
            
            # Invoke the agent with the context
            result = agent_with_chat_history.invoke(
                {"input": formatted_context.strip()},
                config={"configurable": {"session_id": "system_design_session"}}
            )
            
            # Extract result from intermediate steps
            final_result_obj = None
            if "intermediate_steps" in result:
                for action, observation in reversed(result["intermediate_steps"]):
                    if hasattr(action, "tool") and action.tool == "synthesize_system_design_wrapped":
                        self.log_info("Found synthesize_system_design_wrapped tool output. Using as final result.")
                        
                        # NEW: Check if observation is a Pydantic object
                        if isinstance(observation, SystemDesignOutput):
                            self.log_success("Found structured Pydantic output from synthesize_system_design_wrapped")
                            final_result_obj = observation
                            break
                        elif hasattr(observation, "dict") and callable(getattr(observation, "dict")):
                            self.log_success("Found Pydantic-like object with dict method")
                            final_result_obj = observation
                            break
                        elif isinstance(observation, dict):
                            self.log_info("Found dictionary output from synthesize_system_design_wrapped")
                            final_result_obj = observation
                            break
                        elif isinstance(observation, str):
                            try:
                                final_result_obj = json.loads(observation)
                                self.log_info("Parsed JSON string from synthesize_system_design_wrapped")
                                break
                            except json.JSONDecodeError:
                                self.log_warning("Failed to parse synthesize_system_design output as JSON")
        
            # Use synthesis output or fallback to final answer
            if final_result_obj:
                # Convert Pydantic object to dict if needed
                if hasattr(final_result_obj, "dict") and callable(getattr(final_result_obj, "dict")):
                    system_design = final_result_obj.dict()
                else:
                    system_design = final_result_obj
                    
                # Add metadata
                system_design["design_metadata"] = {
                    "design_approach": "react_agent_structured",
                    "generated_at": datetime.now().isoformat(),
                    "tool_calls": len(result.get("intermediate_steps", [])),
                    "brd_project_name": brd_analysis.get("project_name", "Unknown")
                }
                self.log_success("ReAct-based system design created successfully with structured output")
                return system_design
            
            # Fallback: Try to extract system design from final answer
            self.log_warning("Could not find synthesize_system_design tool output. Trying to parse final answer.")
            try:
                system_design = JsonHandler.extract_json_from_text(result["output"])
                if isinstance(system_design, dict):
                    system_design["design_metadata"] = {
                        "design_approach": "react_agent_fallback",
                        "generated_at": datetime.now().isoformat(),
                        "tool_calls": len(result.get("intermediate_steps", [])),
                        "brd_project_name": brd_analysis.get("project_name", "Unknown")
                    }
                    return system_design
            except Exception as e:
                self.log_warning(f"Failed to extract JSON from final answer: {str(e)}")
            
            # Ultimate fallback
            return self.get_default_response()
                
        except Exception as e:
            self.log_error(f"ReAct-based system design failed: {str(e)}")
            import traceback
            self.log_error(traceback.format_exc())
            return self.get_default_response()
        finally:
            # Clean up stored data
            if hasattr(self, '_stored_brd_analysis'):
                del self._stored_brd_analysis
            if hasattr(self, '_stored_tech_stack'):
                del self._stored_tech_stack

    def _create_wrapped_tools(self):
        """Create wrapped versions of tools that automatically inject data."""
        wrapped_tools = []
          # Create a wrapped version of summarize_project_requirements
        @tool(args_schema=ProjectRequirementsSummaryInput)
        def summarize_project_requirements_wrapped(brd_analysis_json: Optional[str] = None) -> str:
            """
            Analyzes requirements from the BRD and returns a concise summary.
            The BRD analysis is automatically provided by the system.
            """
            logger = logging.getLogger(__name__)
            logger.info("Calling wrapped summarize_project_requirements tool")

            if not hasattr(self, '_stored_brd_analysis'):
                logger.error("Error: _stored_brd_analysis not found in agent state.")
                return "Error: BRD analysis data is not available to the tool."
            
            # The tool expects a JSON string, so we dump the stored dict
            brd_json_string = json.dumps(self._stored_brd_analysis)

            # The imported tool is 'summarize_project_requirements' from 'tools.design_tools'
            # We must call it by passing a dictionary that matches its input schema.
            # The schema expects a single key: 'brd_analysis_json'.
            tool_input = {"brd_analysis_json": brd_json_string}
            
            # Use the tool's invoke method for robustness
            return summarize_project_requirements.invoke(tool_input)
          # Create a wrapped version of select_architecture_pattern
        @tool(args_schema=ArchitecturePatternSelectionInput)
        def select_architecture_pattern_wrapped(requirements_summary: str, tech_stack_json: str = None) -> str:
            """
            Selects the optimal architecture pattern based on requirements and tech stack.
            Tech stack is automatically provided by the system if not specified.
            """
            logger = logging.getLogger(__name__)
            logger.info("Calling wrapped select_architecture_pattern tool")
            
            # Use the stored tech stack if none provided
            if not tech_stack_json and hasattr(self, '_stored_tech_stack'):
                tech_stack_json = json.dumps(self._stored_tech_stack)
            
            # Use invoke instead of direct function call
            return select_architecture_pattern.invoke({
                "requirements_summary": requirements_summary,
                "tech_stack_json": tech_stack_json or "{}"
            })
                  # Create a wrapped version of identify_system_components
        @tool(args_schema=SystemComponentsIdentificationInput)
        def identify_system_components_wrapped(requirements_summary: str, architecture_pattern: str) -> str:
            """
            Identifies the main components needed for the system based on requirements.
            """
            logger = logging.getLogger(__name__)
            logger.info("Calling wrapped identify_system_components tool")
            
            # Use invoke instead of direct function call
            return identify_system_components.invoke({
                "requirements_summary": requirements_summary,
                "architecture_pattern": architecture_pattern
            })          # Create a wrapped version of synthesize_system_design
        @tool(args_schema=SystemDesignSynthesisInput)
        def synthesize_system_design_wrapped(
            architecture_pattern: str,
            components: str,
            data_model: str,
            api_design: str = "",
            security_architecture: str = ""
        ) -> SystemDesignOutput:
            """
            Synthesizes all design components into a comprehensive system design.
            The BRD analysis and tech stack are automatically provided by the system.
            """
            logger = logging.getLogger(__name__)
            logger.info("Calling wrapped synthesize_system_design tool")
            
            # Check if required data is available
            if hasattr(self, '_stored_brd_analysis') and hasattr(self, '_stored_tech_stack'):
                try:
                    # Get the tool
                    from tools.design_tools import synthesize_system_design
                    
                    # Use invoke instead of direct function call to properly handle the tool schema
                    return synthesize_system_design.invoke({
                        "architecture_pattern": architecture_pattern,
                        "components": components,
                        "data_model": data_model,
                        "api_design": api_design,
                        "security_architecture": security_architecture
                    })
                    
                except Exception as e:
                    logger.error(f"Error in wrapped synthesize_system_design: {str(e)}")
                    # Return a fallback Pydantic object
                    return SystemDesignOutput(
                        architecture_overview={
                            "pattern": "Error Recovery Pattern",
                            "description": f"Error occurred: {str(e)}"
                        },
                        modules=[{"name": "Frontend"}, {"name": "Backend"}, {"name": "Database"}],
                        metadata={"error": str(e), "is_fallback": True}
                    )
            else:
                # Return a fallback for missing data
                return SystemDesignOutput(
                    architecture_overview={
                        "pattern": "Default Architecture",
                        "description": "Missing required data (BRD or tech stack)"
                    },
                    modules=[{"name": "Frontend"}, {"name": "Backend"}, {"name": "Database"}],
                    metadata={"error": "Missing required data", "is_fallback": True}
                )
        
        # Add wrapped versions of key tools
        wrapped_tools.append(summarize_project_requirements_wrapped)
        wrapped_tools.append(select_architecture_pattern_wrapped)
        wrapped_tools.append(identify_system_components_wrapped)
        wrapped_tools.append(synthesize_system_design_wrapped)
        
        # Add original versions of other tools
        wrapped_tools.append(design_component_structure)
        wrapped_tools.append(design_multiple_component_structures)
        wrapped_tools.append(design_data_model)
        wrapped_tools.append(design_api_endpoints)
        wrapped_tools.append(design_security_architecture)
        wrapped_tools.append(evaluate_design_quality)
        
        return wrapped_tools

    def get_default_response(self) -> Dict[str, Any]:
        """Get a default system design response for fallback."""
        current_time = datetime.now().isoformat()
        
        return {
            "architecture_pattern": "Model-View-Controller (MVC)",
            "system_components": [
                {
                    "name": "User Authentication",
                    "description": "Handles user registration, login, and session management",
                    "technologies": ["JWT", "bcrypt"]
                },
                {
                    "name": "Task Management",
                    "description": "Core business logic for task operations",
                    "technologies": ["REST API", "Database ORM"]
                },
                {
                    "name": "User Interface",
                    "description": "Frontend components for user interaction",
                    "technologies": ["HTML", "CSS", "JavaScript"]
                }
            ],
            "data_model": {
                "entities": [
                    {
                        "name": "User",
                        "attributes": ["id", "email", "password_hash", "created_at"]
                    },
                    {
                        "name": "Task",
                        "attributes": ["id", "user_id", "title", "description", "status", "due_date", "created_at"]
                    }
                ],
                "relationships": [
                    {
                        "type": "one-to-many",
                        "description": "One User has many Tasks"
                    }
                ]
            },
            "api_endpoints": [
                {
                    "path": "/api/auth/register",
                    "method": "POST",
                    "description": "Register new user"
                },
                {
                    "path": "/api/auth/login",
                    "method": "POST",
                    "description": "User login"
                },
                {
                    "path": "/api/tasks",
                    "method": "GET",
                    "description": "Get all tasks for authenticated user"
                }
            ],
            "security_architecture": {
                "authentication": "JWT token-based authentication",
                "authorization": "Role-based access control",
                "data_protection": "Password hashing with bcrypt"
            },
            "design_metadata": {
                "design_approach": "default_fallback",
                "generated_at": current_time,
                "reason": "Agent execution failed, using default design"
            }
        }