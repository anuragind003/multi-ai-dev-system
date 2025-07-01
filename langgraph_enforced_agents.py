"""
LangGraph-Based Agent Implementation with Enforced Tool Usage

This module implements a LangGraph-native approach to enforce tool usage
for all agents, eliminating "Final Answer" completions and ensuring
structured, tool-based outputs.

Key Features:
- Enforced tool usage through state validation
- Automatic retry mechanisms for non-tool outputs
- Structured output validation
- Performance monitoring and logging
"""

import logging
import time
import json
from typing import Dict, Any, List, Optional, Union, Callable, TypedDict
from dataclasses import dataclass, field
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.runnables import RunnableLambda
from langchain_core.language_models import BaseLanguageModel
from langchain_core.tools import BaseTool
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate

import monitoring
from agent_state import AgentState, StateFields
from config import get_llm
from models.data_contracts import BRDRequirementsAnalysis, TechStackSynthesisOutput

logger = logging.getLogger(__name__)

class ToolEnforcedState(TypedDict):
    """Extended state for tool-enforced agent execution."""
    # Input/Output
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    
    # Tool execution tracking
    tool_calls_made: List[Dict[str, Any]]
    required_tools: List[str]
    tool_outputs: Dict[str, Any]
    
    # Retry logic
    retry_count: int
    max_retries: int
    last_error: Optional[str]
    
    # Validation
    output_validated: bool
    validation_errors: List[str]
    
    # Agent context
    agent_name: str
    session_id: str

class LangGraphToolEnforcedAgent:
    """
    Base class for LangGraph agents with enforced tool usage.
    
    This class ensures that agents MUST use tools to produce outputs
    and cannot return "Final Answer" text responses.
    """
    
    def __init__(self,
                 name: str,
                 llm: BaseLanguageModel,
                 tools: List[BaseTool],
                 required_tools: List[str],
                 temperature: float = 0.1,
                 max_retries: int = 3):
        """
        Initialize the tool-enforced agent.
        
        Args:
            name: Agent name for logging
            llm: Language model instance
            tools: List of available tools
            required_tools: List of tool names that MUST be called
            temperature: LLM temperature
            max_retries: Maximum retry attempts
        """
        self.name = name
        self.llm = llm.bind(temperature=temperature)
        self.tools = {tool.name: tool for tool in tools}
        self.required_tools = required_tools
        self.max_retries = max_retries
        
        # Create the workflow graph
        self.workflow = self._create_workflow()
        
    def _create_workflow(self) -> StateGraph:
        """Create the LangGraph workflow for tool-enforced execution."""
        workflow = StateGraph(ToolEnforcedState)
        
        # Add nodes
        workflow.add_node("initialize", self._initialize_node)
        workflow.add_node("plan_execution", self._plan_execution_node)
        workflow.add_node("execute_tools", self._execute_tools_node)
        workflow.add_node("validate_output", self._validate_output_node)
        workflow.add_node("retry_execution", self._retry_execution_node)
        workflow.add_node("finalize", self._finalize_node)
        
        # Set entry point
        workflow.set_entry_point("initialize")
        
        # Add edges
        workflow.add_edge("initialize", "plan_execution")
        workflow.add_edge("plan_execution", "execute_tools")
        workflow.add_conditional_edges(
            "execute_tools",
            self._check_tool_execution,
            {
                "success": "validate_output",
                "retry": "retry_execution",
                "failed": "finalize"
            }
        )
        workflow.add_conditional_edges(
            "validate_output",
            self._check_validation,
            {
                "valid": "finalize",
                "invalid": "retry_execution",
                "failed": "finalize"
            }
        )
        workflow.add_edge("retry_execution", "plan_execution")
        workflow.add_edge("finalize", END)
        
        return workflow
    
    def _initialize_node(self, state: ToolEnforcedState) -> ToolEnforcedState:
        """Initialize the execution state."""
        monitoring.log_agent_activity(
            agent_name=self.name,
            message="Initializing tool-enforced execution",
            level="INFO"
        )
        
        state.update({
            "tool_calls_made": [],
            "required_tools": self.required_tools.copy(),
            "tool_outputs": {},
            "retry_count": 0,
            "max_retries": self.max_retries,
            "last_error": None,
            "output_validated": False,
            "validation_errors": [],
            "agent_name": self.name,
            "session_id": f"{self.name}_{int(time.time())}"
        })
        
        return state
    
    def _plan_execution_node(self, state: ToolEnforcedState) -> ToolEnforcedState:
        """Plan the tool execution strategy."""
        monitoring.log_agent_activity(
            agent_name=self.name,
            message=f"Planning execution for required tools: {state['required_tools']}",
            level="INFO"
        )
        
        # Create a planning prompt
        planning_prompt = self._create_planning_prompt(state)
        
        try:
            # Get the execution plan from the LLM
            response = self.llm.invoke([
                SystemMessage(content=planning_prompt),
                HumanMessage(content=json.dumps(state["input_data"], indent=2))
            ])
            
            # Extract tool planning from response
            state["execution_plan"] = response.content
            
        except Exception as e:
            state["last_error"] = f"Planning failed: {str(e)}"
            monitoring.log_agent_activity(
                agent_name=self.name,
                message=f"Planning failed: {str(e)}",
                level="ERROR"
            )
        
        return state
    
    def _execute_tools_node(self, state: ToolEnforcedState) -> ToolEnforcedState:
        """Execute the required tools sequentially."""
        monitoring.log_agent_activity(
            agent_name=self.name,
            message="Executing required tools",
            level="INFO"
        )
        
        # Create execution prompt with tool descriptions
        execution_prompt = self._create_execution_prompt(state)
        
        try:
            # Bind tools to the LLM
            llm_with_tools = self.llm.bind_tools(list(self.tools.values()))
            
            # Execute with tool binding
            response = llm_with_tools.invoke([
                SystemMessage(content=execution_prompt),
                HumanMessage(content=json.dumps(state["input_data"], indent=2))
            ])
            
            # Process tool calls
            if hasattr(response, 'tool_calls') and response.tool_calls:
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    
                    if tool_name in self.tools:
                        try:
                            # Execute the tool
                            tool_result = self.tools[tool_name].invoke(tool_args)
                            
                            # Record the tool call
                            state["tool_calls_made"].append({
                                "tool": tool_name,
                                "args": tool_args,
                                "result": tool_result,
                                "timestamp": time.time()
                            })
                            
                            # Store output
                            state["tool_outputs"][tool_name] = tool_result
                            
                            # Remove from required tools
                            if tool_name in state["required_tools"]:
                                state["required_tools"].remove(tool_name)
                                
                        except Exception as e:
                            state["last_error"] = f"Tool {tool_name} failed: {str(e)}"
                            monitoring.log_agent_activity(
                                agent_name=self.name,
                                message=f"Tool {tool_name} failed: {str(e)}",
                                level="ERROR"
                            )
            else:
                state["last_error"] = "No tool calls made - agent returned text response"
                
        except Exception as e:
            state["last_error"] = f"Tool execution failed: {str(e)}"
            monitoring.log_agent_activity(
                agent_name=self.name,
                message=f"Tool execution failed: {str(e)}",
                level="ERROR"
            )
        
        return state
    
    def _validate_output_node(self, state: ToolEnforcedState) -> ToolEnforcedState:
        """Validate that all required tools were called and outputs are valid."""
        monitoring.log_agent_activity(
            agent_name=self.name,
            message="Validating tool outputs",
            level="INFO"
        )
        
        validation_errors = []
        
        # Check if all required tools were called
        if state["required_tools"]:
            validation_errors.append(f"Missing required tools: {state['required_tools']}")
        
        # Validate individual tool outputs
        for tool_name, output in state["tool_outputs"].items():
            if not self._validate_tool_output(tool_name, output):
                validation_errors.append(f"Invalid output from tool {tool_name}")
        
        state["validation_errors"] = validation_errors
        state["output_validated"] = len(validation_errors) == 0
        
        if state["output_validated"]:
            # Compile final output
            state["output_data"] = self._compile_final_output(state)
            monitoring.log_agent_activity(
                agent_name=self.name,
                message="Output validation successful",
                level="INFO"
            )
        else:
            monitoring.log_agent_activity(
                agent_name=self.name,
                message=f"Output validation failed: {validation_errors}",
                level="WARNING"
            )
        
        return state
    
    def _retry_execution_node(self, state: ToolEnforcedState) -> ToolEnforcedState:
        """Handle retry logic for failed executions."""
        state["retry_count"] += 1
        
        monitoring.log_agent_activity(
            agent_name=self.name,
            message=f"Retrying execution (attempt {state['retry_count']}/{state['max_retries']})",
            level="WARNING"
        )
        
        # Reset some state for retry
        state["tool_calls_made"] = []
        state["tool_outputs"] = {}
        state["required_tools"] = self.required_tools.copy()
        state["validation_errors"] = []
        
        return state
    
    def _finalize_node(self, state: ToolEnforcedState) -> ToolEnforcedState:
        """Finalize the execution and prepare final output."""
        if state["output_validated"]:
            monitoring.log_agent_activity(
                agent_name=self.name,
                message="Execution completed successfully",
                level="INFO"
            )
        else:
            monitoring.log_agent_activity(
                agent_name=self.name,
                message=f"Execution failed after {state['retry_count']} retries",
                level="ERROR"
            )
            
            # Create fallback output
            state["output_data"] = self._create_fallback_output(state)
        
        return state
    
    def _check_tool_execution(self, state: ToolEnforcedState) -> str:
        """Check if tool execution was successful."""
        if state["last_error"]:
            if state["retry_count"] >= state["max_retries"]:
                return "failed"
            return "retry"
        
        if not state["required_tools"]:
            return "success"
        
        if state["retry_count"] >= state["max_retries"]:
            return "failed"
        
        return "retry"
    
    def _check_validation(self, state: ToolEnforcedState) -> str:
        """Check if output validation passed."""
        if state["output_validated"]:
            return "valid"
        
        if state["retry_count"] >= state["max_retries"]:
            return "failed"
        
        return "invalid"
    
    def _create_planning_prompt(self, state: ToolEnforcedState) -> str:
        """Create the planning prompt for tool execution."""
        return f"""You are {self.name}, a specialized AI agent. You MUST use the following tools to complete your task:

REQUIRED TOOLS: {', '.join(state['required_tools'])}

AVAILABLE TOOLS:
{self._format_tool_descriptions()}

Your task is to plan how you will use these tools to analyze the input data.
You MUST call ALL required tools - no exceptions.
Do not provide text-based "Final Answer" responses.

Planning Guidelines:
1. Understand what each required tool does
2. Plan the order of tool execution
3. Consider dependencies between tools
4. Ensure comprehensive analysis

Current attempt: {state['retry_count'] + 1}/{state['max_retries']}
"""
    
    def _create_execution_prompt(self, state: ToolEnforcedState) -> str:
        """Create the execution prompt with tool enforcement."""
        return f"""You are {self.name}, a specialized AI agent. You MUST use tools to complete your task.

CRITICAL REQUIREMENTS:
1. You MUST call ALL of these required tools: {', '.join(state['required_tools'])}
2. You CANNOT provide text-based responses or "Final Answer"
3. Every piece of information must come from tool calls
4. Use the tools in a logical order

AVAILABLE TOOLS:
{self._format_tool_descriptions()}

TASK: Analyze the provided input data using ALL required tools.

Remember: Your output will ONLY be accepted if you call all required tools.
Any text-based response will be rejected and trigger a retry.

Current attempt: {state['retry_count'] + 1}/{state['max_retries']}
"""
    
    def _format_tool_descriptions(self) -> str:
        """Format tool descriptions for the prompt."""
        descriptions = []
        for tool_name, tool in self.tools.items():
            descriptions.append(f"- {tool_name}: {tool.description}")
        return "\n".join(descriptions)
    
    def _validate_tool_output(self, tool_name: str, output: Any) -> bool:
        """Validate the output from a specific tool."""
        # Override in subclasses for specific validation logic
        return output is not None
    
    def _compile_final_output(self, state: ToolEnforcedState) -> Dict[str, Any]:
        """Compile the final output from all tool results."""
        # Override in subclasses for specific compilation logic
        return state["tool_outputs"]
    
    def _create_fallback_output(self, state: ToolEnforcedState) -> Dict[str, Any]:
        """Create a fallback output when execution fails."""
        # Override in subclasses for specific fallback logic
        return {
            "error": "Tool execution failed",
            "partial_results": state["tool_outputs"],
            "errors": state["validation_errors"]
        }
    
    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent with tool enforcement."""
        initial_state = ToolEnforcedState(
            input_data=input_data,
            output_data={}
        )
        
        # Create a memory saver for checkpointing
        memory = MemorySaver()
        
        # Compile and run the workflow
        app = self.workflow.compile(checkpointer=memory)
        
        # Execute the workflow
        config = {"configurable": {"thread_id": f"{self.name}_{int(time.time())}"}}
        result = app.invoke(initial_state, config=config)
        
        return result["output_data"]


class BRDAnalystToolEnforcedAgent(LangGraphToolEnforcedAgent):
    """BRD Analyst agent with enforced tool usage."""
    
    def __init__(self, llm: BaseLanguageModel, tools: List[BaseTool]):
        super().__init__(
            name="BRD_Analyst",
            llm=llm,
            tools=tools,
            required_tools=["compile_final_brd_analysis"],
            temperature=0.3,
            max_retries=3
        )
    
    def _validate_tool_output(self, tool_name: str, output: Any) -> bool:
        """Validate BRD analysis output."""
        if tool_name == "compile_final_brd_analysis":
            if isinstance(output, dict):
                required_fields = ["functional_requirements", "non_functional_requirements", 
                                 "business_objectives", "technical_constraints"]
                return all(field in output for field in required_fields)
        return super()._validate_tool_output(tool_name, output)
    
    def _compile_final_output(self, state: ToolEnforcedState) -> Dict[str, Any]:
        """Compile BRD analysis output."""
        brd_analysis = state["tool_outputs"].get("compile_final_brd_analysis", {})
        
        # Ensure it conforms to the expected schema
        return {
            "analysis": brd_analysis,
            "metadata": {
                "agent": self.name,
                "tools_used": list(state["tool_outputs"].keys()),
                "execution_time": sum(
                    call.get("execution_time", 0) 
                    for call in state["tool_calls_made"]
                )
            }
        }


class TechStackAdvisorToolEnforcedAgent(LangGraphToolEnforcedAgent):
    """Tech Stack Advisor agent with enforced tool usage."""
    
    def __init__(self, llm: BaseLanguageModel, tools: List[BaseTool]):
        super().__init__(
            name="Tech_Stack_Advisor",
            llm=llm,
            tools=tools,
            required_tools=["compile_tech_stack_recommendation"],
            temperature=0.2,
            max_retries=3
        )
    
    def _validate_tool_output(self, tool_name: str, output: Any) -> bool:
        """Validate tech stack recommendation output."""
        if tool_name == "compile_tech_stack_recommendation":
            if isinstance(output, dict):
                required_fields = ["recommended_stack", "justification", "alternatives"]
                return all(field in output for field in required_fields)
        return super()._validate_tool_output(tool_name, output)


def create_tool_enforced_workflow() -> StateGraph:
    """Create a complete workflow with tool-enforced agents."""
    workflow = StateGraph(AgentState)
    
    # Add tool-enforced agent nodes
    workflow.add_node("brd_analysis_enforced", create_brd_analyst_enforced_node)
    workflow.add_node("tech_stack_enforced", create_tech_stack_enforced_node)
    
    # Set up the workflow
    workflow.set_entry_point("brd_analysis_enforced")
    workflow.add_edge("brd_analysis_enforced", "tech_stack_enforced")
    workflow.add_edge("tech_stack_enforced", END)
    
    return workflow


def create_brd_analyst_enforced_node(state: AgentState) -> AgentState:
    """Create a BRD analyst node with enforced tool usage."""
    from tools.enhanced_brd_analysis_tools import get_enhanced_brd_analysis_tools
    
    llm = get_llm()
    tools = get_enhanced_brd_analysis_tools()
    
    agent = BRDAnalystToolEnforcedAgent(llm, tools)
    
    # Run the agent
    result = agent.run({"brd_content": state.get("brd_content", "")})
    
    # Update state
    state["brd_analysis"] = result
    state["current_phase"] = "tech_stack_recommendation"
    
    return state


def create_tech_stack_enforced_node(state: AgentState) -> AgentState:
    """Create a tech stack advisor node with enforced tool usage."""
    from tools.tech_stack_tools import get_tech_stack_tools
    
    llm = get_llm()
    tools = get_tech_stack_tools()
    
    agent = TechStackAdvisorToolEnforcedAgent(llm, tools)
    
    # Run the agent
    result = agent.run({
        "brd_analysis": state.get("brd_analysis", {}),
        "requirements": state.get("requirements", {})
    })
    
    # Update state
    state["tech_stack_recommendation"] = result
    state["current_phase"] = "system_design"
    
    return state


# Example usage function
def demonstrate_tool_enforcement():
    """Demonstrate the tool-enforced workflow."""
    workflow = create_tool_enforced_workflow()
    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory)
    
    # Initial state
    initial_state = {
        "brd_content": "Sample BRD content...",
        "current_phase": "brd_analysis"
    }
    
    # Run the workflow
    config = {"configurable": {"thread_id": "demo_session"}}
    result = app.invoke(initial_state, config=config)
    
    return result
