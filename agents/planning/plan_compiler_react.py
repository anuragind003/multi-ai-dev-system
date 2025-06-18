"""
ReAct-based Plan Compiler Agent for Multi-AI Development System.
Uses reasoning and tool-execution loop for more flexible and robust implementation planning.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from langchain_core.language_models import BaseLanguageModel
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain.agents import AgentExecutor, create_json_chat_agent
from langchain_core.runnables.history import RunnableWithMessageHistory

# Import the prompt hub to get the standard ReAct prompt
from langchain import hub

from agents.base_agent import BaseAgent
from tools.json_handler import JsonHandler

# Import models for the wrapped tools
from tools.models import (
    # Input models
    ProjectAnalysisSummaryInput,
    MajorSystemComponentsInput,
    TimelineEstimationInput,
    RiskAssessmentInput,
    ComprehensivePlanInput,
    WrappedToolInput,
    
    # NEW: Output models
    ProjectAnalysisSummaryOutput,
    MajorSystemComponentsOutput,
    TimelineDetailsOutput,
    RiskAssessmentOutput,
    ComprehensivePlanOutput,
    
    # Fallback plan models
    ImplementationPlan,
    ProjectSummary,
    DevelopmentPhaseOutput,
    ResourceAllocation,
    PlanMetadata
)

class PlanCompilerReActAgent(BaseAgent):
    """
    ReAct-based Plan Compiler Agent for synthesizing comprehensive project plans.
    Combines project analysis, system design, and risk assessment into a cohesive plan.
    """
    
    def __init__(
        self,
        llm: BaseLanguageModel,
        memory,
        default_temperature: float = 0.2,
        agent_name: str = "Plan Compiler Agent"
    ):
        """Initialize the Plan Compiler Agent with LLM and configuration."""
        super().__init__(llm=llm, memory=memory, temperature=default_temperature, agent_name=agent_name)
        self.tools = []  # Will be initialized during run()
    
    # Update the run method to handle Pydantic objects
    def run(self, 
        project_analysis: Dict[str, Any], 
        system_design: Dict[str, Any],
        timeline_estimation: Dict[str, Any],
        risk_assessment: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate comprehensive project plan using the ReAct framework.
        
        Args:
            project_analysis: Analyzed project feasibility and requirements
            system_design: System architecture and components
            timeline_estimation: Project timeline and milestones
            risk_assessment: Risk analysis and mitigation strategies
            
        Returns:
            Comprehensive project plan
        """
        self.log_start("Starting ReAct-based plan compilation")
          # Store references for tool access
        self._stored_project_analysis = project_analysis
        self._stored_system_design = system_design
        self._stored_timeline_estimation = timeline_estimation
        self._stored_risk_assessment = risk_assessment
        
        try:
            # Create wrapped tools that automatically inject the stored data
            self.tools = self._create_wrapped_tools()
            
            # Use the standard ReAct prompt from the hub
            prompt = hub.pull("hwchase17/react-chat-json")
            
            # Customize the system message with our specific instructions
            system_message = """You are an expert Plan Compiler specializing in creating 
    comprehensive project plans based on analysis, design, and risk assessment.

    APPROACH:
    1. First understand the project analysis summary
    2. Extract major system components from the system design
    3. Understand the timeline estimation
    4. Review the risk assessment
    5. Synthesize all inputs into a comprehensive project plan
    6. Include resource allocation recommendations

    IMPORTANT: The tools now return structured Pydantic objects instead of JSON strings.
    This means you can directly access specific fields from the tool responses.

    The wrapped tools automatically access the stored data, so you can simply call them with minimal input:
    - get_project_analysis_summary_wrapped
    - get_major_system_components_wrapped
    - get_timeline_estimation_wrapped
    - get_risk_assessment_wrapped
    - compile_comprehensive_plan_wrapped"""
            
            # Replace the system message in the prompt
            messages = prompt.messages
            messages[0] = SystemMessage(content=system_message)
            modified_prompt = ChatPromptTemplate.from_messages(messages)
            
            # Create the agent with standard temperature binding
            llm_with_temp = self.llm.bind(temperature=self.default_temperature)
            agent = create_json_chat_agent(
                llm=llm_with_temp,
                tools=self.tools,
                prompt=modified_prompt
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
            Your goal is to create a comprehensive project plan.
            
            Project name: {project_analysis.get('project_name', 'Unknown Project')}
            
            Follow these steps in order:
            1. Start by using get_project_analysis_summary_wrapped to understand the project complexity
            2. Extract the major system components using get_major_system_components_wrapped
            3. Get the timeline estimation using get_timeline_estimation_wrapped
            4. Review the risk assessment using get_risk_assessment_wrapped
            5. As your FINAL action, synthesize all inputs into a comprehensive project plan using
            compile_comprehensive_plan_wrapped
            """
            
            # Invoke the agent with the context
            result = agent_with_chat_history.invoke(
                {"input": formatted_context.strip()},
                config={"configurable": {"session_id": "plan_compiler_session"}}
            )
            
            # Extract final result from intermediate steps with Pydantic support
            final_result_obj = None
            if "intermediate_steps" in result:
                for action, observation in reversed(result["intermediate_steps"]):
                    # Get the tool name
                    tool_name = getattr(action, "tool", "")
                    
                    # Check for the compile_comprehensive_plan_wrapped tool which produces our final output
                    if tool_name == "compile_comprehensive_plan_wrapped":
                        self.log_info("Found compile_comprehensive_plan_wrapped tool output. Using as final result.")
                        
                        # Check if observation is a Pydantic object
                        if isinstance(observation, ComprehensivePlanOutput):
                            self.log_success("Found ComprehensivePlanOutput from compile_comprehensive_plan_wrapped")
                            final_result_obj = observation
                            break
                        elif hasattr(observation, "dict") and callable(getattr(observation, "dict")):
                            self.log_success("Found Pydantic-like object with dict method")
                            final_result_obj = observation
                            break
                        elif isinstance(observation, dict):
                            self.log_info("Found dictionary output from compile_comprehensive_plan_wrapped")
                            final_result_obj = observation
                            break
                        elif isinstance(observation, str):
                            try:
                                final_result_obj = json.loads(observation)
                                self.log_info("Parsed JSON string from compile_comprehensive_plan_wrapped")
                                break
                            except json.JSONDecodeError:
                                self.log_warning("Failed to parse compile_comprehensive_plan output as JSON")
            
            # If we found a valid result object
            if final_result_obj:
                # Convert Pydantic to dictionary if needed
                if hasattr(final_result_obj, "dict") and callable(getattr(final_result_obj, "dict")):
                    plan = final_result_obj.dict()
                else:
                    plan = final_result_obj
                    
                # Add metadata if it doesn't exist
                if "plan_metadata" not in plan:
                    plan["plan_metadata"] = {
                        "generation_approach": "react_agent_structured",
                        "generated_at": datetime.now().isoformat(),
                        "tool_calls": len(result.get("intermediate_steps", [])),
                        "project_name": project_analysis.get("project_name", "Unknown")
                    }
                self.log_success("ReAct-based plan compilation created successfully with structured output")
                return plan
              # Fallback: Try to extract plan from final answer
            self.log_warning("Could not find compile_comprehensive_plan_wrapped with Pydantic output. Trying to parse final answer.")
            try:
                plan = JsonHandler.extract_json_from_text(result["output"])
                if isinstance(plan, dict):
                    plan["plan_metadata"] = {
                        "generation_approach": "react_agent_fallback",
                        "generated_at": datetime.now().isoformat(),
                        "tool_calls": len(result.get("intermediate_steps", [])),
                        "project_name": project_analysis.get("project_name", "Unknown")
                    }
                    return plan
            except Exception as e:
                self.log_warning(f"Failed to extract JSON from final answer: {str(e)}")
                # Continue to the default response
        except Exception as e:
            self.log_error(f"Error during plan compilation: {str(e)}")
            # Continue to the default response
        
        self.log_warning("Using default response as fallback")
        return self.get_default_response()

    def _create_wrapped_tools(self):
        """Create wrapped versions of tools that automatically inject data."""
        wrapped_tools = []
        
        # Import planning tools
        from tools.planning_tools import (
            get_project_analysis_summary,
            get_major_system_components,
            get_timeline_estimation,
            get_risk_assessment,
            compile_comprehensive_plan
        )        # Create wrapped version of get_project_analysis_summary
        @tool(args_schema=WrappedToolInput)
        def get_project_analysis_summary_wrapped(analyze: Optional[bool] = True, additional_context: Optional[str] = "") -> str:
            """
            Retrieves a summary of the project analysis including feasibility, 
            complexity, and recommended approach.
            """
            logger = logging.getLogger(__name__)
            logger.info("Calling wrapped get_project_analysis_summary tool")
            
            # Handle empty string or None for analyze parameter
            if analyze is None or (isinstance(analyze, str) and not analyze):
                analyze = True
            # Convert string to boolean if it's a non-empty string
            elif isinstance(analyze, str):
                analyze = analyze.lower() in ['true', '1', 'yes', 't', 'y']
            
            if hasattr(self, '_stored_project_analysis'):
                analysis_json = json.dumps(self._stored_project_analysis)
                # Pass the data to the original tool using the correct argument name
                return get_project_analysis_summary(project_analysis_json=analysis_json)
            else:
                return "Error: Project analysis not available"          # Create wrapped version of get_major_system_components
        @tool(args_schema=WrappedToolInput)
        def get_major_system_components_wrapped(analyze: Optional[bool] = True, additional_context: Optional[str] = "") -> str:
            """
            Extracts major system components from the system design.
            """
            logger = logging.getLogger(__name__)
            logger.info("Calling wrapped get_major_system_components tool")
            
            # Handle empty string or None for analyze parameter
            if analyze is None or (isinstance(analyze, str) and not analyze):
                analyze = True
            # Convert string to boolean if it's a non-empty string
            elif isinstance(analyze, str):
                analyze = analyze.lower() in ['true', '1', 'yes', 't', 'y']
            
            if hasattr(self, '_stored_system_design'):
                # Make sure system_design is properly serialized as JSON
                if isinstance(self._stored_system_design, dict):
                    system_design_json = json.dumps(self._stored_system_design)
                    return get_major_system_components(system_design_json=system_design_json)
                else:
                    logger.warning(f"System design is not a dictionary: {type(self._stored_system_design)}")
                    # Try to parse it if it's a string
                    if isinstance(self._stored_system_design, str):
                        try:
                            parsed_design = json.loads(self._stored_system_design)
                            return get_major_system_components(system_design_json=json.dumps(parsed_design))
                        except json.JSONDecodeError:
                            return "Error: System design is not valid JSON"
                    return f"Error: System design has invalid format: {type(self._stored_system_design)}"
            else:
                return "Error: System design not available"          # Create wrapped version of get_timeline_estimation
        @tool(args_schema=WrappedToolInput)
        def get_timeline_estimation_wrapped(analyze: Optional[bool] = True, additional_context: Optional[str] = "") -> str:
            """
            Retrieves timeline estimation including phases, milestones, and critical path.
            """
            logger = logging.getLogger(__name__)
            logger.info("Calling wrapped get_timeline_estimation tool")
            
            # Handle empty string or None for analyze parameter
            if analyze is None or (isinstance(analyze, str) and not analyze):
                analyze = True
            # Convert string to boolean if it's a non-empty string
            elif isinstance(analyze, str):
                analyze = analyze.lower() in ['true', '1', 'yes', 't', 'y']
            
            if hasattr(self, '_stored_timeline_estimation'):
                timeline_json = json.dumps(self._stored_timeline_estimation)
                return get_timeline_estimation(timeline_estimation_json=timeline_json)
            else:
                return "Error: Timeline estimation not available"          # Create wrapped version of get_risk_assessment
        @tool(args_schema=WrappedToolInput)
        def get_risk_assessment_wrapped(analyze: Optional[bool] = True, additional_context: Optional[str] = "") -> str:
            """
            Retrieves risk assessment including identified risks, 
            their severity, and mitigation strategies.
            """
            logger = logging.getLogger(__name__)
            logger.info("Calling wrapped get_risk_assessment tool")
            
            # Handle empty string or None for analyze parameter
            if analyze is None or (isinstance(analyze, str) and not analyze):
                analyze = True
            # Convert string to boolean if it's a non-empty string
            elif isinstance(analyze, str):
                analyze = analyze.lower() in ['true', '1', 'yes', 't', 'y']
            
            if hasattr(self, '_stored_risk_assessment'):
                risk_json = json.dumps(self._stored_risk_assessment)
                return get_risk_assessment(risk_assessment_json=risk_json)
            else:
                return "Error: Risk assessment not available"          # Create wrapped version of compile_comprehensive_plan
        @tool(args_schema=WrappedToolInput)
        def compile_comprehensive_plan_wrapped(analyze: Optional[bool] = True, additional_context: Optional[str] = "") -> ComprehensivePlanOutput:
            """
            Compiles a comprehensive project plan based on analysis, design, 
            timeline, and risk assessment.
            """
            logger = logging.getLogger(__name__)
            logger.info("Calling wrapped compile_comprehensive_plan tool")
            
            # Handle empty string or None for analyze parameter
            if analyze is None or (isinstance(analyze, str) and not analyze):
                analyze = True
            # Convert string to boolean if it's a non-empty string
            elif isinstance(analyze, str):
                analyze = analyze.lower() in ['true', '1', 'yes', 't', 'y']
            
            if all(hasattr(self, attr) for attr in [
                '_stored_project_analysis', 
                '_stored_system_design', 
                '_stored_timeline_estimation', 
                '_stored_risk_assessment'
            ]):
                try:
                    # Call the original tool with combined data
                    return compile_comprehensive_plan(
                        project_analysis=self._stored_project_analysis,
                        system_design=self._stored_system_design,
                        timeline_estimation=self._stored_timeline_estimation,
                        risk_assessment=self._stored_risk_assessment
                    )
                except Exception as e:
                    logger.error(f"Error in wrapped compile_comprehensive_plan: {str(e)}")
                    
                    # Create a fallback plan
                    fallback_plan = ImplementationPlan(
                        project_summary=ProjectSummary(
                            title="Fallback Implementation Plan",
                            description=f"Generated due to error: {str(e)}",
                            overall_complexity="Medium",
                            estimated_duration="12 weeks"
                        ),
                        development_phases=[
                            DevelopmentPhaseOutput(
                                phase_id="P1",
                                name="Project Setup",
                                type="setup",
                                duration="1 week",
                                tasks=["Repository initialization"],
                                dependencies=[]
                            ),
                            # ... add more phases
                        ],
                        dependencies=[
                            {"from": "P1", "to": "P2", "type": "finish-to-start"}
                        ],
                        resource_allocation=ResourceAllocation(
                            recommended_team_size=5,
                            key_roles=["Project Manager", "Developers"]
                        ),
                        metadata=PlanMetadata(
                            generated_at=datetime.now().isoformat(),
                            generation_method="fallback_due_to_error"
                        )
                    )
                    
                    return ComprehensivePlanOutput(implementation_plan=fallback_plan)
            else:
                logger.error("Missing required inputs for comprehensive plan")
                
                # Create a minimal error plan
                error_plan = ImplementationPlan(
                    project_summary=ProjectSummary(
                        title="Error Implementation Plan",
                        description="Missing required inputs",
                        overall_complexity="Unknown",
                        estimated_duration="Unknown"
                    ),
                    development_phases=[],
                    dependencies=[],
                    resource_allocation=ResourceAllocation(
                        recommended_team_size=0,
                        key_roles=[]
                    ),
                    metadata=PlanMetadata(
                        generated_at=datetime.now().isoformat(),
                        generation_method="error_response"
                    )
                )
                
                return ComprehensivePlanOutput(implementation_plan=error_plan)
        
        # Add wrapped tools
        wrapped_tools.append(get_project_analysis_summary_wrapped)
        wrapped_tools.append(get_major_system_components_wrapped)
        wrapped_tools.append(get_timeline_estimation_wrapped)
        wrapped_tools.append(get_risk_assessment_wrapped)
        wrapped_tools.append(compile_comprehensive_plan_wrapped)
        
        # Log total tools registered
        logger = logging.getLogger(__name__)
        logger.info(f"Total planning tools registered: {len(wrapped_tools)}")
        
        return wrapped_tools

    def get_default_response(self) -> Dict[str, Any]:
        """Get a default project plan response for fallback."""
        current_time = datetime.now().isoformat()
        
        return {
            "implementation_plan": {
                "project_summary": {
                    "title": "Default Implementation Plan",
                    "description": "Generated due to error in plan compilation",
                    "overall_complexity": "Medium",
                    "estimated_duration": "12 weeks"
                },
                "development_phases": [
                    {
                        "name": "Project Setup Phase",
                        "type": "setup",
                        "phase_id": "P1",
                        "duration": "1 week",
                        "tasks": ["Repository initialization", "Environment configuration", "Project structure setup"]
                    },
                    {
                        "name": "Backend Development Phase",
                        "type": "backend",
                        "phase_id": "P2", 
                        "duration": "4 weeks",
                        "tasks": ["Database implementation", "API development", "Core business logic"]
                    },
                    {
                        "name": "Frontend Development Phase",
                        "type": "frontend",
                        "phase_id": "P3",
                        "duration": "4 weeks",
                        "tasks": ["UI component development", "State management", "API integration"]
                    },
                    {
                        "name": "Testing & Refinement Phase",
                        "type": "testing",
                        "phase_id": "P4",
                        "duration": "2 weeks",
                        "tasks": ["Unit testing", "Integration testing", "Bug fixing"]
                    }
                ],
                "dependencies": [
                    {"from": "P1", "to": "P2", "type": "finish-to-start"},
                    {"from": "P2", "to": "P3", "type": "start-to-start", "delay": "1 week"},
                    {"from": "P2", "to": "P4", "type": "finish-to-start"},
                    {"from": "P3", "to": "P4", "type": "finish-to-start"}
                ],
                "metadata": {
                    "generated_at": current_time,
                    "generation_method": "default_fallback",
                    "status": "auto-generated fallback plan"
                }
            }
        }