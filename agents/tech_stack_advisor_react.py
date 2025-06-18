"""
ReAct-based Tech Stack Advisor Agent for Multi-AI Development System.
Uses reasoning and tool-execution loop for more flexible technology recommendations.
"""

import json
import logging
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

# Import tech stack tools
from tools.tech_stack_tools import (
    get_technical_requirements_summary,
    evaluate_backend_options,
    evaluate_frontend_options,
    evaluate_database_options,
    evaluate_architecture_patterns,
    synthesize_tech_stack,
    analyze_tech_stack_risks
)

# Import Pydantic models for output validation
from tools.models import TechStackSynthesisOutput

# Add these imports to the top of the file
from langchain import hub
from langchain.agents import create_json_chat_agent, AgentExecutor
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.agents import AgentAction, AgentFinish

class TechStackAdvisorReActAgent(BaseAgent):
    """
    ReAct-based Tech Stack Advisor Agent that uses reasoning and tool-execution 
    to dynamically evaluate and recommend technology choices.
    
    This agent can:
    1. Focus on the most critical requirements first
    2. Dynamically choose what to evaluate based on requirements
    3. Make more explicit trade-off decisions
    4. Consider compatibility between technology choices
    """
    
    def __init__(self, 
                 llm: BaseLanguageModel, 
                 memory, 
                 temperature: float = None,
                 rag_retriever: Optional[BaseRetriever] = None,
                 message_bus=None):
        
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
        
        # Initialize the ReAct agent and tools
        self._init_agent()
    
    def _create_safe_synthesize_tech_stack_tool(self):
        """Create a wrapped version of synthesize_tech_stack that ensures all parameters are present."""
        from functools import wraps
        from tools.models import TechStackSynthesisOutput
        
        @wraps(synthesize_tech_stack)
        def safe_synthesize_tech_stack(
            backend_recommendation: str = None, 
            frontend_recommendation: str = None, 
            database_recommendation: str = None, 
            architecture_recommendation: str = None
        ) -> TechStackSynthesisOutput:
            """Safely synthesizes tech stack ensuring all required parameters are present."""
            self.log_info("Called safe_synthesize_tech_stack wrapper")
            
            # Use default values if any required parameters are missing
            if not backend_recommendation:
                self.log_warning("Missing backend_recommendation in synthesize_tech_stack, using default value")
                backend_recommendation = "Node.js with Express for reliable server-side capabilities"
                
            if not frontend_recommendation:
                self.log_warning("Missing frontend_recommendation in synthesize_tech_stack, using default value")
                frontend_recommendation = "React for component-based UI development"
                
            if not database_recommendation:
                self.log_warning("Missing database_recommendation in synthesize_tech_stack, using default value")
                database_recommendation = "PostgreSQL for reliable data storage"
                
                # Forward to actual implementation
            self.log_info(f"Calling synthesize_tech_stack with validated parameters: backend={bool(backend_recommendation)}, frontend={bool(frontend_recommendation)}, database={bool(database_recommendation)}")
            # Use invoke instead of direct function call
            result = synthesize_tech_stack.invoke({
                "backend_recommendation": backend_recommendation,
                "frontend_recommendation": frontend_recommendation,
                "database_recommendation": database_recommendation,
                "architecture_recommendation": architecture_recommendation or ""
            })
            
            return result
            
        # Update the tool metadata to match the original
        safe_synthesize_tech_stack.name = synthesize_tech_stack.name
        safe_synthesize_tech_stack.description = synthesize_tech_stack.description
        safe_synthesize_tech_stack.args_schema = synthesize_tech_stack.args_schema
        
        return safe_synthesize_tech_stack
    
    def _init_agent(self):
        """Initialize the ReAct agent with the necessary tools."""
        # Create the list of tools the agent can use - convert them to proper Tool objects
        from langchain_core.tools import Tool
        
        # Make sure all tools are properly wrapped as Tool objects
        self.tools = [
            # Use each tool directly since they should already be decorated with @tool
            get_technical_requirements_summary,
            evaluate_backend_options,
            evaluate_frontend_options,
            evaluate_database_options,
            evaluate_architecture_patterns,
            self._create_safe_synthesize_tech_stack_tool(),
            analyze_tech_stack_risks
        ]
        
        # Pull the default ReAct JSON chat prompt from the hub
        self.react_prompt = hub.pull("hwchase17/react-chat-json")
        
        # Update the system message for better guidance on large JSON handling
        messages = self.react_prompt.messages
        for i, message in enumerate(messages):
            if hasattr(message, 'role') and message.role == "system":
                system_message = """You are an expert Technology Stack Advisor specializing in selecting optimal technology stacks for software projects.
Your goal is to recommend a comprehensive and justified technology stack by analyzing requirements and evaluating trade-offs.

APPROACH:
1. First understand the technical requirements
2. Evaluate options for backend, frontend, and database technologies  
3. Consider how these choices work together
4. Recommend an architecture pattern that fits the technologies and requirements
5. Synthesize everything into a comprehensive technology stack
6. Analyze potential risks and challenges

IMPORTANT: The tools now return structured Pydantic objects instead of JSON strings.
This means you can directly access specific fields from the tool responses.

Follow this process to make your recommendation:
1. Start by getting a summary of the technical requirements
2. Based on these requirements, decide which aspect is most critical to evaluate first
3. Evaluate technology options for each component
4. Consider how your choices work together and recommend an appropriate architecture pattern
5. Synthesize your choices into a comprehensive tech stack
6. Analyze potential risks and challenges with your recommended stack"""
                messages[i] = SystemMessage(content=system_message)
                break

    def run(self, brd_analysis: Dict[str, Any], project_context: str = "") -> Dict[str, Any]:
        """
        Generate technology stack recommendations using the ReAct framework.
        
        Args:
            brd_analysis: Analyzed business requirements document
            project_context: Additional context about the project
            
        Returns:
            Comprehensive technology stack recommendation
        """
        self.log_start("Starting ReAct-based tech stack recommendation")
        
        try:
            # Store the BRD analysis in an instance variable for tool access
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
            
            # Create the executor separately
            agent_executor = AgentExecutor(
                agent=agent,
                tools=tools_list,
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
            
            # Convert BRD analysis to a JSON string for the tool
            brd_json = json.dumps(brd_analysis)
            
            # Prepare simplified input that INCLUDES the brd_json
            formatted_context = f"""
            Your goal is to recommend a comprehensive technology stack for this project.
            
            Project context: {project_context}
            Project name: {brd_analysis.get('project_name', 'Unknown Project')}
            
            Here is the full BRD Analysis data you need to work with:
            --- BRD ANALYSIS START ---
            {brd_json}
            --- BRD ANALYSIS END ---
            
            Follow these steps in order:
            1. Start by using get_technical_requirements_summary with the BRD analysis JSON provided above.
            2. Based on requirements, evaluate backend, frontend, and database options
            3. Based on these technology choices, recommend an architecture pattern
            4. Analyze potential risks and challenges in your chosen stack
            5. As your FINAL action, use synthesize_tech_stack to create the complete recommendation
            """
            
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
                        # Check for required fields
                        missing = []
                        if 'backend_recommendation' not in tool_args or not tool_args['backend_recommendation']:
                            missing.append('backend_recommendation')
                        if 'frontend_recommendation' not in tool_args or not tool_args['frontend_recommendation']:
                            missing.append('frontend_recommendation')
                        if 'database_recommendation' not in tool_args or not tool_args['database_recommendation']:
                            missing.append('database_recommendation')
                        
                        if missing:
                            self.log_warning(f"Missing required fields for synthesize_tech_stack: {', '.join(missing)}")
            
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
                self.log_success("ReAct tech stack recommendation created successfully with structured output")
                return final_dict
            
            # Fallback: Parse the final answer if we couldn't find the synthesize_tech_stack result
            self.log_warning("Could not find synthesize_tech_stack with Pydantic output. Falling back to final answer parsing.")
            final_tech_stack = self._extract_tech_stack_from_output(result["output"])
            final_tech_stack["recommendation_metadata"] = {
                "recommendation_approach": "react_agent_fallback",
                "generated_at": datetime.now().isoformat(),
                "tool_calls": len(result.get("intermediate_steps", [])),
                "project_context": project_context if project_context else "None provided"
            }
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
                try:
                    return json.loads(potential_json.group(1))
                except:
                    pass
            
            self.log_warning("Could not extract JSON from agent output")
            return self.get_default_response()
            
        except Exception as e:
            self.log_warning(f"Error extracting tech stack from output: {str(e)}")
            return self.get_default_response()
    
    def get_default_response(self) -> Dict[str, Any]:
        """Return a default tech stack when recommendation generation fails."""
        current_time = datetime.now().isoformat()
        return {
            "backend": {
                "language": "Python",
                "framework": "FastAPI",
                "reasoning": "Reliable choice for modern web applications"
            },
            "frontend": {
                "language": "JavaScript",
                "framework": "React",
                "reasoning": "Popular framework with strong ecosystem"
            },
            "database": {
                "type": "PostgreSQL",
                "reasoning": "Versatile relational database with strong ACID support"
            },
            "architecture_pattern": "Layered Architecture",
            "deployment_environment": {
                "platform": "Cloud (AWS)",
                "containerization": "Docker"
            },
            "key_libraries_tools": [
                {"name": "Redis", "purpose": "Caching"},
                {"name": "Jest", "purpose": "Frontend testing"},
                {"name": "Pytest", "purpose": "Backend testing"}
            ],
            "estimated_complexity": "Medium",
            "recommendation_metadata": {
                "recommendation_approach": "default_fallback",
                "generated_at": current_time,
                "note": "This is a default recommendation generated due to an error"
            }
        }