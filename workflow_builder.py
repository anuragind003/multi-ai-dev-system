"""
Workflow Builder for Multi-AI Development System

DEPRECATED: This module is deprecated in favor of LangGraph-based workflow orchestration.
Please use graph.py for defining workflows.

This module builds different types of workflows with specialized agents and components.
Enhanced to support message-based architecture and checkpointing.
"""

import warnings
warnings.warn(
    "workflow_builder.py is deprecated. Please use graph.py and LangGraph for workflow orchestration.",
    DeprecationWarning,
    stacklevel=2
)

import os
import logging
from typing import Dict, Any, List, Optional

# Import agent classes
from agents.brd_analyst import BRDAnalystAgent
from agents.tech_stack_advisor import TechStackAdvisorAgent
from agents.system_designer import SystemDesignerAgent
from agents.planning.project_analyzer import ProjectAnalyzerAgent
from agents.planning.timeline_estimator import TimelineEstimatorAgent
from agents.planning.risk_assessor import RiskAssessorAgent
from agents.planning.plan_compiler import PlanCompilerAgent
from agents.code_generation.architecture_generator import ArchitectureGeneratorAgent
from agents.code_generation.backend_generator import BackendGeneratorAgent
from agents.code_generation.frontend_generator import FrontendGeneratorAgent
from agents.code_generation.database_generator import DatabaseGeneratorAgent
from agents.code_generation.integration_generator import IntegrationGeneratorAgent
from agents.code_quality_agent import CodeQualityAgent
from agents.test_case_generator import TestCaseGeneratorAgent
from agents.testing_agent import TestingAgent
from agents.documentation_agent import DocumentationAgent

logger = logging.getLogger(__name__)

class WorkflowPhase:
    """Represents a phase in the development workflow"""
    
    def __init__(self, name: str, checkpoint: bool = True):
        self.name = name
        self.agents = []
        self.checkpoint = checkpoint
    
    def add_agent(self, agent: Any, input_mappings: Dict[str, str] = None, output_mappings: Dict[str, str] = None):
        """Add an agent to this phase with input/output mappings"""
        self.agents.append({
            "agent": agent,
            "input_mappings": input_mappings or {},
            "output_mappings": output_mappings or {}
        })
        return self

class Workflow:
    """Represents a complete multi-agent workflow"""
    
    def __init__(self, name: str, components: Dict[str, Any]):
        self.name = name
        self.phases = []
        self.agents = {}
        self.components = components
        self.checkpoint_handler = None
    
    def add_phase(self, phase: WorkflowPhase):
        """Add a phase to the workflow"""
        self.phases.append(phase)
        
        # Register agents
        for agent_config in phase.agents:
            agent = agent_config["agent"]
            self.agents[agent.agent_name] = agent
        
        return self
    
    def register_checkpoint_handler(self, handler_func):
        """Register function for creating checkpoints"""
        self.checkpoint_handler = handler_func
    
    def run(self, brd_content: str) -> Dict[str, Any]:
        """Execute the workflow with all phases"""
        state = {
            "brd_content": brd_content,
            "workflow_id": self.components["workflow_id"],
            "output_dir": self.components["output_dir"],
            "environment": self.components["config"].environment,
            "last_phase": None,
            "checkpoints": []
        }
        
        logger.info(f"Starting workflow: {self.name}")
        
        # Execute each phase
        for phase in self.phases:
            try:
                logger.info(f"Starting phase: {phase.name}")
                state["current_phase"] = phase.name
                
                # Execute each agent in the phase
                for agent_config in phase.agents:
                    agent = agent_config["agent"]
                    input_mappings = agent_config["input_mappings"]
                    output_mappings = agent_config["output_mappings"]
                    
                    logger.info(f"Executing agent: {agent.agent_name}")
                    
                    # Prepare agent inputs
                    agent_inputs = {}
                    for agent_input, state_key in input_mappings.items():
                        if state_key in state:
                            agent_inputs[agent_input] = state[state_key]
                        else:
                            logger.warning(f"Missing required state key: {state_key}")
                    
                    # Run agent
                    agent_result = agent.run(**agent_inputs)
                    
                    # Store agent results in state
                    for result_key, state_key in output_mappings.items():
                        if result_key in agent_result:
                            state[state_key] = agent_result[result_key]
                        else:
                            logger.warning(f"Missing expected result key: {result_key}")
                    
                    # Store full result under agent name
                    state[f"{agent.agent_name}_result"] = agent_result
                    state["last_agent"] = agent.agent_name
                
                # Create checkpoint if enabled
                if phase.checkpoint and self.checkpoint_handler:
                    state = self.checkpoint_handler(state, phase.name)
                
                state["last_phase"] = phase.name
                logger.info(f"Completed phase: {phase.name}")
                
            except Exception as e:
                logger.error(f"Error in phase {phase.name}: {e}")
                state["error"] = f"Phase {phase.name} failed: {str(e)}"
                break
        
        logger.info("Workflow completed")
        if "error" in state:
            return {
                "status": "error",
                "message": state["error"],
                "output_dir": self.components["output_dir"]
            }
        else:
            return {
                "status": "success",
                "output_dir": self.components["output_dir"],
                "phases_completed": state.get("last_phase", "None")
            }


def build_workflow(workflow_type: str, components: Dict[str, Any], config: Any) -> Workflow:
    """
    Build a workflow based on the specified type.
    Supports standard, phased, or iterative workflows.
    """
    llm = components["llm"]
    memory = components["memory"]
    message_bus = components["message_bus"]
    rag_retriever = components["rag_manager"].get_retriever()
    output_dir = components["output_dir"]
    code_execution_tool = components["code_execution_tool"]
    
    # Initialize common agents
    brd_analyst = BRDAnalystAgent(llm=llm, memory=memory, rag_retriever=rag_retriever)
    tech_stack_advisor = TechStackAdvisorAgent(llm=llm, memory=memory, rag_retriever=rag_retriever)
    system_designer = SystemDesignerAgent(llm=llm, memory=memory, rag_retriever=rag_retriever)
    
    # Connect agents to message bus
    for agent in [brd_analyst, tech_stack_advisor, system_designer]:
        agent.set_message_bus(message_bus)
    
    if workflow_type == "standard":
        # Standard monolithic workflow
        workflow = Workflow("Standard Workflow", components)
        
        # Use traditional planning agent for standard workflow
        from agents.planning_agent import PlanningAgent
        from agents.code_generation import CodeGenerationAgent
        
        planning_agent = PlanningAgent(llm=llm, memory=memory, rag_retriever=rag_retriever)
        code_generation_agent = CodeGenerationAgent(
            llm=llm, 
            memory=memory, 
            output_dir=output_dir,
            code_execution_tool=code_execution_tool,
            rag_retriever=rag_retriever
        )
        
        # Connect agents to message bus
        planning_agent.set_message_bus(message_bus)
        code_generation_agent.set_message_bus(message_bus)
        
        # Create testing and quality agents
        test_case_generator = TestCaseGeneratorAgent(
            llm=llm, memory=memory, output_dir=output_dir, rag_retriever=rag_retriever
        )
        code_quality_agent = CodeQualityAgent(
            llm=llm, memory=memory, code_execution_tool=code_execution_tool, 
            run_output_dir=output_dir, rag_retriever=rag_retriever
        )
        testing_agent = TestingAgent(
            llm=llm, memory=memory, code_execution_tool=code_execution_tool, 
            output_dir=output_dir, rag_retriever=rag_retriever
        )
        
        # Connect agents to message bus
        test_case_generator.set_message_bus(message_bus)
        code_quality_agent.set_message_bus(message_bus)
        testing_agent.set_message_bus(message_bus)
        
        # Create documentation agent
        documentation_agent = DocumentationAgent(
            llm=llm, memory=memory, output_dir=output_dir, rag_retriever=rag_retriever
        )
        documentation_agent.set_message_bus(message_bus)
        
        # Create and add phases
        requirements_phase = WorkflowPhase("requirements_analysis")
        requirements_phase.add_agent(
            brd_analyst,
            input_mappings={"brd_content": "brd_content"},
            output_mappings={"brd_analysis": "brd_analysis"}
        )
        
        design_phase = WorkflowPhase("design")
        design_phase.add_agent(
            tech_stack_advisor,
            input_mappings={"brd_analysis": "brd_analysis"},
            output_mappings={"tech_stack": "tech_stack_recommendation"}
        ).add_agent(
            system_designer,
            input_mappings={
                "brd_analysis": "brd_analysis",
                "tech_stack": "tech_stack_recommendation"
            },
            output_mappings={"system_design": "system_design"}
        )
        
        planning_phase = WorkflowPhase("planning")
        planning_phase.add_agent(
            planning_agent,
            input_mappings={
                "brd_analysis": "brd_analysis",
                "tech_stack_recommendation": "tech_stack_recommendation",
                "system_design": "system_design"
            },
            output_mappings={"implementation_plan": "implementation_plan"}
        )
        
        implementation_phase = WorkflowPhase("implementation")
        implementation_phase.add_agent(
            code_generation_agent,
            input_mappings={
                "brd_analysis": "brd_analysis",
                "tech_stack_recommendation": "tech_stack_recommendation",
                "system_design": "system_design",
                "implementation_plan": "implementation_plan"
            },
            output_mappings={
                "generated_files": "generated_files",
                "status": "code_generation_status"
            }
        )
        
        testing_phase = WorkflowPhase("testing")
        testing_phase.add_agent(
            test_case_generator,
            input_mappings={
                "brd_analysis": "brd_analysis",
                "system_design": "system_design",
                "implementation_plan": "implementation_plan",
                "generated_files": "generated_files"
            },
            output_mappings={"test_cases": "test_cases"}
        ).add_agent(
            code_quality_agent,
            input_mappings={
                "generated_files": "generated_files",
                "tech_stack_recommendation": "tech_stack_recommendation"
            },
            output_mappings={"quality_report": "quality_report"}
        ).add_agent(
            testing_agent,
            input_mappings={
                "test_cases": "test_cases",
                "generated_files": "generated_files"
            },
            output_mappings={"test_results": "test_results"}
        )
        
        documentation_phase = WorkflowPhase("documentation")
        documentation_phase.add_agent(
            documentation_agent,
            input_mappings={
                "brd_analysis": "brd_analysis", 
                "system_design": "system_design",
                "implementation_plan": "implementation_plan",
                "generated_files": "generated_files",
                "quality_report": "quality_report",
                "test_results": "test_results"
            },
            output_mappings={"documentation_files": "documentation_files"}
        )
        
        # Add phases to workflow
        workflow.add_phase(requirements_phase)
        workflow.add_phase(design_phase)
        workflow.add_phase(planning_phase)
        workflow.add_phase(implementation_phase)
        workflow.add_phase(testing_phase)
        workflow.add_phase(documentation_phase)
        
    elif workflow_type == "phased":
        # Phased workflow with specialized planning and code generation agents
        workflow = Workflow("Phased Development Workflow", components)
        
        # Initialize specialized planning agents
        project_analyzer = ProjectAnalyzerAgent(llm=llm, memory=memory, rag_retriever=rag_retriever)
        timeline_estimator = TimelineEstimatorAgent(llm=llm, memory=memory, rag_retriever=rag_retriever)
        risk_assessor = RiskAssessorAgent(llm=llm, memory=memory, rag_retriever=rag_retriever)
        plan_compiler = PlanCompilerAgent(llm=llm, memory=memory, rag_retriever=rag_retriever)
        
        # Initialize specialized code generation agents
        architecture_generator = ArchitectureGeneratorAgent(
            llm=llm, memory=memory, output_dir=output_dir, rag_retriever=rag_retriever
        )
        backend_generator = BackendGeneratorAgent(
            llm=llm, memory=memory, output_dir=output_dir, rag_retriever=rag_retriever
        )
        frontend_generator = FrontendGeneratorAgent(
            llm=llm, memory=memory, output_dir=output_dir, rag_retriever=rag_retriever
        )
        database_generator = DatabaseGeneratorAgent(
            llm=llm, memory=memory, output_dir=output_dir, rag_retriever=rag_retriever
        )
        integration_generator = IntegrationGeneratorAgent(
            llm=llm, memory=memory, output_dir=output_dir, rag_retriever=rag_retriever
        )
        
        # Connect specialized agents to message bus
        for agent in [project_analyzer, timeline_estimator, risk_assessor, plan_compiler,
                      architecture_generator, backend_generator, frontend_generator,
                      database_generator, integration_generator]:
            agent.set_message_bus(message_bus)
        
        # Create testing and quality agents
        test_case_generator = TestCaseGeneratorAgent(
            llm=llm, memory=memory, output_dir=output_dir, rag_retriever=rag_retriever
        )
        code_quality_agent = CodeQualityAgent(
            llm=llm, memory=memory, code_execution_tool=code_execution_tool, 
            run_output_dir=output_dir, rag_retriever=rag_retriever
        )
        testing_agent = TestingAgent(
            llm=llm, memory=memory, code_execution_tool=code_execution_tool, 
            output_dir=output_dir, rag_retriever=rag_retriever
        )
        
        # Connect agents to message bus
        test_case_generator.set_message_bus(message_bus)
        code_quality_agent.set_message_bus(message_bus)
        testing_agent.set_message_bus(message_bus)
        
        # Create documentation agent
        documentation_agent = DocumentationAgent(
            llm=llm, memory=memory, output_dir=output_dir, rag_retriever=rag_retriever
        )
        documentation_agent.set_message_bus(message_bus)
        
        # Create and add phases
        requirements_phase = WorkflowPhase("requirements_analysis")
        requirements_phase.add_agent(
            brd_analyst,
            input_mappings={"brd_content": "brd_content"},
            output_mappings={"brd_analysis": "brd_analysis"}
        )
        
        design_phase = WorkflowPhase("design")
        design_phase.add_agent(
            tech_stack_advisor,
            input_mappings={"brd_analysis": "brd_analysis"},
            output_mappings={"tech_stack": "tech_stack_recommendation"}
        ).add_agent(
            system_designer,
            input_mappings={
                "brd_analysis": "brd_analysis",
                "tech_stack": "tech_stack_recommendation"
            },
            output_mappings={"system_design": "system_design"}
        )
        
        # Advanced planning phase with specialized agents
        planning_phase = WorkflowPhase("planning")
        planning_phase.add_agent(
            project_analyzer,
            input_mappings={
                "brd_analysis": "brd_analysis",
                "system_design": "system_design"
            },
            output_mappings={"complexity_analysis": "complexity_analysis"}
        ).add_agent(
            timeline_estimator,
            input_mappings={
                "complexity_analysis": "complexity_analysis",
                "tech_stack": "tech_stack_recommendation"
            },
            output_mappings={"project_timeline": "project_timeline"}
        ).add_agent(
            risk_assessor,
            input_mappings={
                "brd_analysis": "brd_analysis",
                "tech_stack": "tech_stack_recommendation",
                "complexity_analysis": "complexity_analysis"
            },
            output_mappings={"risk_assessment": "risk_assessment"}
        ).add_agent(
            plan_compiler,
            input_mappings={
                "complexity_analysis": "complexity_analysis",
                "project_timeline": "project_timeline",
                "risk_assessment": "risk_assessment"
            },
            output_mappings={"implementation_plan": "implementation_plan"}
        )
        
        # Phase 1: Project structure and architecture
        phase1_implementation = WorkflowPhase("phase1_implementation")
        phase1_implementation.add_agent(
            architecture_generator,
            input_mappings={
                "system_design": "system_design",
                "tech_stack": "tech_stack_recommendation",
                "implementation_plan": "implementation_plan"
            },
            output_mappings={
                "generated_files": "p1_generated_files",
                "project_structure": "project_structure"
            }
        ).add_agent(
            code_quality_agent,
            input_mappings={
                "generated_files": "p1_generated_files",
                "tech_stack_recommendation": "tech_stack_recommendation"
            },
            output_mappings={"quality_report": "p1_quality_report"}
        )
        
        # Phase 2: Database and models
        phase2_implementation = WorkflowPhase("phase2_implementation")
        phase2_implementation.add_agent(
            database_generator,
            input_mappings={
                "system_design": "system_design",
                "project_structure": "project_structure",
                "implementation_plan": "implementation_plan"
            },
            output_mappings={"generated_files": "p2_generated_files"}
        ).add_agent(
            code_quality_agent,
            input_mappings={
                "generated_files": "p2_generated_files",
                "tech_stack_recommendation": "tech_stack_recommendation"
            },
            output_mappings={"quality_report": "p2_quality_report"}
        )
        
        # Phase 3: Backend development
        phase3_implementation = WorkflowPhase("phase3_implementation")
        phase3_implementation.add_agent(
            backend_generator,
            input_mappings={
                "system_design": "system_design",
                "project_structure": "project_structure",
                "implementation_plan": "implementation_plan",
                "p2_generated_files": "p2_generated_files"  # Depends on database implementation
            },
            output_mappings={"generated_files": "p3_generated_files"}
        ).add_agent(
            code_quality_agent,
            input_mappings={
                "generated_files": "p3_generated_files",
                "tech_stack_recommendation": "tech_stack_recommendation"
            },
            output_mappings={"quality_report": "p3_quality_report"}
        )
        
        # Phase 4: Frontend development
        phase4_implementation = WorkflowPhase("phase4_implementation")
        phase4_implementation.add_agent(
            frontend_generator,
            input_mappings={
                "system_design": "system_design",
                "project_structure": "project_structure",
                "implementation_plan": "implementation_plan",
                "p3_generated_files": "p3_generated_files"  # Depends on backend APIs
            },
            output_mappings={"generated_files": "p4_generated_files"}
        ).add_agent(
            code_quality_agent,
            input_mappings={
                "generated_files": "p4_generated_files",
                "tech_stack_recommendation": "tech_stack_recommendation"
            },
            output_mappings={"quality_report": "p4_quality_report"}
        )
        
        # Phase 5: Integrations
        phase5_implementation = WorkflowPhase("phase5_implementation")
        phase5_implementation.add_agent(
            integration_generator,
            input_mappings={
                "system_design": "system_design",
                "project_structure": "project_structure",
                "implementation_plan": "implementation_plan",
                "p3_generated_files": "p3_generated_files",
                "p4_generated_files": "p4_generated_files"
            },
            output_mappings={"generated_files": "p5_generated_files"}
        ).add_agent(
            code_quality_agent,
            input_mappings={
                "generated_files": "p5_generated_files",
                "tech_stack_recommendation": "tech_stack_recommendation"
            },
            output_mappings={"quality_report": "p5_quality_report"}
        )
        
        # Merge all generated files
        def merge_generated_files(state):
            all_files = {}
            for phase_prefix in ["p1", "p2", "p3", "p4", "p5"]:
                phase_files = state.get(f"{phase_prefix}_generated_files", {})
                all_files.update(phase_files)
            state["generated_files"] = all_files
            return state
        
        # Testing phase
        testing_phase = WorkflowPhase("testing")
        testing_phase.add_agent(
            test_case_generator,
            input_mappings={
                "brd_analysis": "brd_analysis",
                "system_design": "system_design",
                "implementation_plan": "implementation_plan",
                "generated_files": "generated_files"
            },
            output_mappings={"test_cases": "test_cases"}
        ).add_agent(
            testing_agent,
            input_mappings={
                "test_cases": "test_cases",
                "generated_files": "generated_files"
            },
            output_mappings={"test_results": "test_results"}
        )
        
        # Documentation phase
        documentation_phase = WorkflowPhase("documentation")
        documentation_phase.add_agent(
            documentation_agent,
            input_mappings={
                "brd_analysis": "brd_analysis", 
                "system_design": "system_design",
                "implementation_plan": "implementation_plan",
                "generated_files": "generated_files",
                "test_results": "test_results"
            },
            output_mappings={"documentation_files": "documentation_files"}
        )
        
        # Add phases to workflow
        workflow.add_phase(requirements_phase)
        workflow.add_phase(design_phase)
        workflow.add_phase(planning_phase)
        workflow.add_phase(phase1_implementation)
        workflow.add_phase(phase2_implementation)
        workflow.add_phase(phase3_implementation)
        workflow.add_phase(phase4_implementation)
        workflow.add_phase(phase5_implementation)
        # Add merge step
        workflow.merge_phase = merge_generated_files
        workflow.add_phase(testing_phase)
        workflow.add_phase(documentation_phase)
        
    else:
        # Default to standard workflow
        logger.warning(f"Unknown workflow type: {workflow_type}, defaulting to standard")
        return build_workflow("standard", components, config)
    
    logger.info(f"Successfully built {workflow_type} workflow")
    return workflow