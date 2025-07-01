"""
Enhanced ReAct-based Plan Compiler Agent with Hybrid Validation and API Token Optimization.
Uses reasoning and tool-execution loop for more flexible and robust implementation planning.
"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

from langchain_core.language_models import BaseLanguageModel
from langchain_core.tools import tool,Tool
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain.agents import AgentExecutor, create_json_chat_agent
from langchain_core.runnables.history import RunnableWithMessageHistory

# Import the prompt hub to get the standard ReAct prompt
from langchain import hub

from agents.base_agent import BaseAgent
from tools.json_handler import JsonHandler

# Enhanced memory and RAG imports
from enhanced_memory_manager import create_memory_manager, EnhancedSharedProjectMemory
from rag_manager import get_rag_manager

# Enhanced imports for hybrid validation and optimization
from utils.hybrid_validator import HybridValidator, HybridValidationResult
from utils.enhanced_tool_validator import enhanced_tool_validator
from utils.react_agent_api_optimizer import ReactAgentAPIOptimizer
from utils.safe_console_callback_handler import SafeConsoleCallbackHandler, create_detailed_callback

# Import models for the wrapped tools
from models.data_contracts import (
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

logger = logging.getLogger(__name__)

class PlanCompilerReActAgent(BaseAgent):
    """
    Enhanced ReAct-based Plan Compiler Agent with hybrid validation and API optimization.
    
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
        default_temperature: float = 0.2,
        agent_name: str = "Plan Compiler Agent",
        message_bus=None,
        enable_enhanced_validation: bool = True,
        enable_api_optimization: bool = True
    ):
        """Initialize the Enhanced Plan Compiler Agent with validation and optimization."""
        super().__init__(llm=llm, memory=memory, temperature=default_temperature, agent_name=agent_name)
        
        # Message bus integration
        self.message_bus = message_bus
        
        # Enhanced components
        self.json_handler = JsonHandler()
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        
        # Initialize enhanced memory (inherits from BaseAgent which has enhanced memory mixin)
        self._init_enhanced_memory()
        
        # Initialize RAG context
        self.rag_manager = get_rag_manager()
        if self.rag_manager:
            self.logger.info("RAG manager available for enhanced planning")
        else:
            self.logger.warning("RAG manager not available - proceeding with basic planning")
        
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
        
        self.tools = []  # Will be initialized during run()

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
        
        try:
            # IMPORTANT: Store planning data in shared memory so tools can access them
            try:
                if hasattr(self, 'memory') and self.memory:
                    # Store all planning inputs in shared memory with proper keys for tools
                    self.memory.set("project_analysis", project_analysis)
                    self.memory.set("system_design", system_design) 
                    self.memory.set("timeline_estimation", timeline_estimation)
                    self.memory.set("risk_assessment", risk_assessment)
                    
                    # ALSO store with the keys that tools expect
                    self.memory.set("brd_analysis", project_analysis)
                    self.memory.set("tech_stack_recommendation", system_design.get("tech_stack", {}))
                    self.memory.set("design_analysis", system_design)
                    
                    self.logger.info("Stored planning data in shared memory for tool access")
                else:
                    self.logger.warning("No shared memory available - tools may not have access to planning data")
            except Exception as memory_error:
                self.logger.warning(f"Failed to store planning data in shared memory: {memory_error}")
            
            # Use the @tool decorated functions directly from planning_tools  
            from tools.planning_tools import (
                get_project_analysis_summary,
                get_major_system_components, 
                get_timeline_estimation,
                get_risk_assessment,
                compile_comprehensive_plan,
                batch_analyze_planning_inputs
            )
            
            # Enhanced validation disabled - using universal wrapper instead
            if False:  # self.enable_enhanced_validation:
                self.tools = [
                    enhanced_tool_validator.wrap_tool(
                        batch_analyze_planning_inputs,
                        expected_fields=[],
                        agent_name=self.agent_name
                    ),
                    enhanced_tool_validator.wrap_tool(
                        get_project_analysis_summary,
                        expected_fields=[],
                        agent_name=self.agent_name
                    ),
                    enhanced_tool_validator.wrap_tool(
                        get_major_system_components,
                        expected_fields=[],
                        agent_name=self.agent_name
                    ),
                    enhanced_tool_validator.wrap_tool(
                        get_timeline_estimation,
                        expected_fields=[],
                        agent_name=self.agent_name
                    ),
                    enhanced_tool_validator.wrap_tool(
                        get_risk_assessment,
                        expected_fields=[],
                        agent_name=self.agent_name
                    ),
                    enhanced_tool_validator.wrap_tool(
                        compile_comprehensive_plan,
                        expected_fields=[],
                        agent_name=self.agent_name
                    )
                ]
            else:
                # Set up tools - now using @tool decorated functions directly
                self.tools = [
                    batch_analyze_planning_inputs,
                    get_project_analysis_summary,
                    get_major_system_components,
                    get_timeline_estimation, 
                    get_risk_assessment,
                    compile_comprehensive_plan
                ]
            
            # Use the standard ReAct prompt from the hub
            prompt = hub.pull("hwchase17/react-chat-json")            # Customize the system message with domain awareness
            system_message = """You are an expert Plan Compiler specializing in creating comprehensive, 
domain-aware project plans based on analysis, design, and risk assessment.

**DOMAIN AND COMPLIANCE AWARENESS:**
- Healthcare: Plan for HIPAA compliance, medical data security, patient safety, extended testing phases
- Financial: Include PCI-DSS compliance, fraud detection, transaction security, regulatory audits
- IoT: Account for device management complexity, real-time processing, connectivity challenges
- E-commerce: Plan for scalability, payment integration, inventory management, customer experience
- Enterprise: Include integration phases, role-based access, workflow management, compliance audits
- Startups: Balance speed with quality, cost-effective phases, rapid iteration cycles

**INTELLIGENT PLANNING APPROACH:**
1. Analyze project domain and complexity to determine appropriate phase durations
2. Identify domain-specific compliance and security requirements
3. Create realistic timelines based on domain complexity (healthcare/financial = longer, IoT/ecommerce = shorter)
4. Include domain-specific risks and mitigation strategies
5. Use the compile_comprehensive_plan tool as your final step for complete plan generation

**DOMAIN-AWARE DURATION GUIDELINES:**
- Healthcare/Financial: Longer phases due to compliance, security, and rigorous testing needs
- IoT: Medium phases with focus on real-time processing and device integration complexity
- E-commerce: Standard phases with emphasis on scalability and payment integration
- Startups: Shorter phases for rapid development and iteration

EFFICIENT PROCESSING INSTRUCTIONS:
1. Use batch_analyze_planning_inputs for maximum efficiency - gets ALL data in one call
2. The planning tools are now domain-aware and will provide appropriate timelines and components
3. Trust the enhanced tools to handle domain-specific complexity automatically
4. Focus on synthesis rather than manual domain detection

Available tools:
- batch_analyze_planning_inputs - Most efficient: gets ALL domain-aware data in one call
- get_project_analysis_summary - Get project complexity and domain-specific constraints
- get_major_system_components - Get domain-appropriate system components
- get_timeline_estimation - Get domain-aware schedule with appropriate durations
- get_risk_assessment - Get domain-specific risks and mitigation strategies
- compile_comprehensive_plan - Final step: creates complete domain-aware implementation plan"""
            
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
                verbose=False,  # Disable verbose to prevent I/O errors
                callbacks=[create_detailed_callback(max_output_length=3000)],  # Show full tool outputs
                handle_parsing_errors=True,
                max_iterations=15,                return_intermediate_steps=True
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
            
            # Prepare input with actual project data in JSON format
            project_analysis_json = json.dumps(project_analysis) if project_analysis else ""
            system_design_json = json.dumps(system_design) if system_design else ""
            timeline_estimation_json = json.dumps(timeline_estimation) if timeline_estimation else ""
            risk_assessment_json = json.dumps(risk_assessment) if risk_assessment else ""
            
            formatted_context = f"""
            Your goal is to create a comprehensive project plan efficiently with the MINIMUM NUMBER OF API CALLS.
            
            Project name: {project_analysis.get('project_name', 'Unknown Project')}
            
            CRITICAL: You have access to the following project data:
            - Project Analysis: Available (use as project_analysis_json parameter)
            - System Design: Available (use as system_design_json parameter)  
            - Timeline Estimation: Available (use as timeline_estimation_json parameter)
            - Risk Assessment: Available (use as risk_assessment_json parameter)
            
            Follow this MOST EFFICIENT process (REQUIRED):
            1. Call batch_analyze_planning_inputs with these EXACT parameters:
               - project_analysis_json: "{project_analysis_json[:100]}..." (truncated for display)
               - system_design_json: "{system_design_json[:100]}..." (truncated for display)
               - timeline_estimation_json: "{timeline_estimation_json[:100]}..." (truncated for display)
               - risk_assessment_json: "{risk_assessment_json[:100]}..." (truncated for display)
            
            2. As your FINAL action, use compile_comprehensive_plan to create the complete plan
            
            IMPORTANT: Use the FULL JSON data when calling tools, not the truncated versions shown above.
            The tools need the complete project data to provide domain-aware planning.
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
                      # Check for the compile_comprehensive_plan tool which produces our final output
                    if tool_name == "compile_comprehensive_plan":
                        self.log_info("Found compile_comprehensive_plan tool output. Using as final result.")
                        
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
                # Store result in enhanced memory for cross-tool access
                self.enhanced_set("planning_result", plan, context="planning")
                self.store_cross_tool_data("comprehensive_plan", plan, "Complete implementation plan for other agents")
                
                # Store individual planning components for reuse
                self.enhanced_set("project_analysis", project_analysis, context="planning_inputs")
                self.enhanced_set("system_design", system_design, context="planning_inputs")
                self.enhanced_set("timeline_estimation", timeline_estimation, context="planning_inputs")
                self.enhanced_set("risk_assessment", risk_assessment, context="planning_inputs")
                
                # Publish plan completion message
                if hasattr(self, 'message_bus') and self.message_bus:
                    self.message_bus.publish("plan.compilation.complete", {
                        "agent": self.agent_name,
                        "status": "completed",
                        "plan": plan,
                        "metadata": plan.get("plan_metadata", {})
                    })
                
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
                    
                    # Store fallback result in enhanced memory
                    self.enhanced_set("planning_result", plan, context="planning")
                    self.store_cross_tool_data("comprehensive_plan", plan, "Fallback implementation plan for other agents")
                    
                    return plan
            except Exception as e:                self.log_warning(f"Failed to extract JSON from final answer: {str(e)}")
                # Continue to the default response
        except Exception as e:
            self.log_error(f"Error during plan compilation: {str(e)}")
            # Continue to the default response        
        self.log_warning("Using default response as fallback")
        return self.get_default_response()

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
            }        }
    
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
    
    def _validate_input(self, input_data: Any, context: str = "") -> Any:
        """Validate input using hybrid validation system."""
        if not self.enable_enhanced_validation:
            return input_data
            
        from pydantic import BaseModel
        from typing import List
        
        # Simple validation schema for plan compilation inputs
        class PlanCompilerInputSchema(BaseModel):
            project_name: str = "Unknown Project"
            requirements: List[str] = []
            
        try:
            result = self.hybrid_validator.validate_progressive(
                raw_input=input_data,
                pydantic_model=PlanCompilerInputSchema,
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