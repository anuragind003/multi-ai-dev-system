# filepath: c:\d drive\Anurag\L&T\multi_ai_dev_system\agents\planning\plan_compiler.py
"""
Plan Compiler Agent - Combines outputs from specialized planning agents into a cohesive implementation plan
with detailed phase planning, file structure generation, and dependency mapping.
"""

import json
import copy  # Add this missing import
import time
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from langchain_core.language_models import BaseLanguageModel
from langchain_core.retrievers import BaseRetriever
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage

from agents.base_agent import BaseAgent
import monitoring
from agent_temperatures import get_agent_temperature

# MODIFIED: Fix import paths - use absolute imports instead of relative imports
import os
import sys
# Add project root to Python path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
from tools.code_execution_tool import CodeExecutionTool  # Changed from ...tools
from message_bus import MessageBus  # Changed from ...message_bus

class PlanCompilerAgent(BaseAgent):
    """
    Enhanced Plan Compiler Agent that integrates outputs from specialized planning agents 
    into a comprehensive implementation plan with detailed file structure and dependency mapping.
    
    This agent acts as the coordinator for the planning phase by:
    1. Compiling and harmonizing outputs from multiple specialized planning agents
    2. Creating a detailed phase-based implementation plan with file-level granularity
    3. Mapping dependencies between components and phases
    4. Aligning risks with mitigation strategies across phases
    5. Generating implementation guidelines based on tech stack and system design
    
    Uses temperature 0.3 for balanced integration of analytical inputs with creative planning.
    """
    
    def __init__(self, llm: BaseLanguageModel, memory, temperature: float, rag_retriever: Optional[BaseRetriever] = None):
        """Initialize the Plan Compiler Agent."""
        # FIXED: Use the exact key name as in agent_temperatures.py
        default_temp = get_agent_temperature("Plan Compiler Agent")  # Match key exactly
        
        # Initialize the base agent
        super().__init__(
            llm=llm,
            memory=memory,
            agent_name="Plan Compiler Agent",
            temperature=temperature,
            rag_retriever=rag_retriever
        )
        
        # Initialize specialized prompt templates
        self._initialize_prompt_templates()

        # ADDED: Initialize JSON examples
        self._initialize_json_examples()
        
        # Tracking for compilation steps
        self.compilation_stages = []

    def _initialize_json_examples(self):
        """Initialize JSON examples for various agent operations."""
        self.json_examples = {
            "implementation_plan": {
                "project_summary": {
                    "title": "Example Project",
                    "description": "A software project example",
                    "overall_complexity": "7/10",
                    "estimated_duration": "12 weeks"
                },
                "development_phases": [
                    {
                        "name": "Requirements Analysis",
                        "type": "setup",
                        "phase_id": "P1",
                        "duration": "1 week",
                        "tasks": ["Repository setup", "Environment configuration"]
                    },
                    {
                        "name": "Backend Development",
                        "type": "backend",
                        "phase_id": "P2",
                        "duration": "3 weeks",
                        "tasks": ["API implementation", "Database setup"]
                    },
                    {
                        "name": "Frontend Development",
                        "type": "frontend",
                        "phase_id": "P3",
                        "duration": "3 weeks",
                        "tasks": ["UI components", "API integration"]
                    },
                    {
                        "name": "Testing & Deployment",
                        "type": "testing",
                        "phase_id": "P4",
                        "duration": "2 weeks",
                        "tasks": ["Testing", "Deployment preparation"]
                    }
                ],
                "dependencies": [
                    {"from": "P1", "to": "P2", "type": "finish-to-start"},
                    {"from": "P2", "to": "P3", "type": "start-to-start", "delay": "1 week"},
                    {"from": "P2", "to": "P4", "type": "finish-to-start"},
                    {"from": "P3", "to": "P4", "type": "finish-to-start"}
                ]
            }
        }
        
    def _initialize_prompt_templates(self):
        """Initialize specialized prompt templates for the various compilation stages."""
        # Import JsonHandler at initialization
        from multi_ai_dev_system.tools.json_handler import JsonHandler
        self.json_handler = JsonHandler
        
        # Main plan compilation template - converted to use strict JSON template
        self.plan_compilation_prompt = self.json_handler.create_strict_json_template(
            "Implementation Plan Compilation",
            """You are a specialized Implementation Plan Compiler AI for software projects.
            
            Your task is to compile a comprehensive implementation plan by integrating:
            1. Project complexity analysis
            2. Timeline estimation
            3. Risk assessment
            
            # Project Complexity Analysis
            {complexity_analysis}
            
            # Timeline Estimation
            {project_timeline}
            
            # Risk Assessment
            {risk_assessment}
            
            # Requirements Analysis (if available)
            {requirements_analysis}
            
            # Tech Stack Recommendation (if available)
            {tech_stack_recommendation}
            
            # System Design (if available)
            {system_design}
            
            Based on these inputs, create a comprehensive implementation plan that organizes the work into logical phases,
            addresses identified risks, and provides a clear roadmap for development.""",
            # Example JSON structure
            """{
                "implementation_plan": {
                    "project_summary": {
                        "title": "Example Project",
                        "description": "A software project example",
                        "overall_complexity": "7/10",
                        "estimated_duration": "12 weeks"
                    },
                    "phases": [
                        {
                            "phase_id": "P1",
                            "phase_name": "Requirements Analysis",
                            "description": "Validate and refine requirements",
                            "start_date": "2025-07-01",
                            "end_date": "2025-07-15",
                            "estimated_days": 10,
                            "key_deliverables": ["Requirements document"],
                            "key_risks": ["R001"],
                            "files_to_implement": [
                                {
                                    "file_path": "docs/requirements.md",
                                    "description": "Requirements documentation",
                                    "dependencies": [],
                                    "priority": "High"
                                }
                            ],
                            "completion_criteria": ["Requirements signed off"]
                        }
                    ]
                }
            }"""
        )
        
        # File structure generation template
        self.file_structure_prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""
                You are a specialized Software Project File Structure Generator.
                
                Your task is to generate a detailed file structure for a software project based on:
                1) The technology stack recommendations
                2) The system design
                3) The implementation phases
                
                Be comprehensive and practical, following best practices for the specified tech stack.
            """),
            HumanMessage(content="""
                Generate a detailed file structure for this software project:
                
                ## Technology Stack
                {tech_stack}
                
                ## System Design
                {system_design}
                
                ## Implementation Phases
                {implementation_phases}
                
                Please provide a JSON response with file paths organized by phase, including:
                1. Full file paths following conventions for the tech stack
                2. Brief description of each file's purpose
                3. Dependencies between files
                4. Priority level (High/Medium/Low)
                
                Format your response as:
                ```json
                {
                  "file_structure": {
                    "P1": [
                      {
                        "file_path": "path/to/file.ext",
                        "description": "Purpose of this file",
                        "dependencies": ["path/to/dependency.ext"],
                        "priority": "High"
                      }
                    ],
                    "P2": [
                      ...
                    ]
                  }
                }
                ```
                
                Include ALL files needed for a complete implementation, including configuration files, 
                documentation, and test files.
            """)
        ])
        
        # Dependency mapping template
        self.dependency_mapping_prompt = PromptTemplate.from_template(
            """You are an expert Software Architecture and Dependency Mapper.
            
            Your task is to identify and map all dependencies between phases and files in the implementation plan.
            
            # Phases
            {phases}
            
            # Files
            {files}
            
            Create a comprehensive dependency map that identifies:
            1. Dependencies between phases
            2. Dependencies between files across phases
            3. Critical path dependencies that could affect the project timeline
            
            Format your response as JSON:
            ```json
            {
                "phase_dependencies": [
                    {
                        "from_phase": "<phase_id>",
                        "to_phase": "<phase_id>",
                        "dependency_type": "<type: strict|soft|optional>",
                        "description": "<dependency description>"
                    }
                ],
                "file_dependencies": [
                    {
                        "from_file": "<file path>",
                        "to_file": "<file path>",
                        "dependency_type": "<type: import|reference|data|configuration>",
                        "cross_phase": true/false,
                        "critical_path": true/false
                    }
                ],
                "critical_path": ["<phase_id>", "<phase_id>", "<phase_id>"]
            }
            ```
            
            Be thorough in identifying all dependencies, especially those that cross phase boundaries.
            """
        )
        
        # Risk alignment template
        self.risk_alignment_prompt = PromptTemplate.from_template(
            """You are a Risk Management Specialist for software projects.
            
            Your task is to align identified risks with implementation phases and develop mitigation strategies.
            
            # Risks
            {risks}
            
            # Phases
            {phases}
            
            Create a risk management plan that:
            1. Maps each risk to the phase(s) where it is most relevant
            2. Develops specific mitigation strategies for each risk
            3. Identifies contingency plans for high-severity risks
            
            Format your response as JSON:
            ```json
            {
                "risk_mitigation_strategies": [
                    {
                        "risk_id": "<risk_id>",
                        "risk_description": "<brief description from original risk>",
                        "severity": "<High/Medium/Low>",
                        "phase_implementation": ["<phase_id>", "<phase_id>"],
                        "mitigation_strategy": "<detailed mitigation strategy>",
                        "contingency_plan": "<what to do if risk materializes>",
                        "owner": "<role responsible for this risk>"
                    }
                ],
                "high_priority_risks": ["<risk_id>", "<risk_id>"],
                "risk_monitoring": {
                    "<phase_id>": ["<monitoring activity>", "<monitoring activity>"]
                }
            }
            ```
            
            Be specific in your mitigation strategies and ensure they are actionable within the project context.
            """
        )
        
        # Guidelines compilation template
        self.guidelines_prompt = PromptTemplate.from_template(
            """You are a Software Development Guidelines Specialist.
            
            Your task is to create comprehensive implementation guidelines based on the project requirements, 
            tech stack, and system design.
            
            # Tech Stack
            {tech_stack}
            
            # System Design
            {system_design}
            
            # Implementation Plan
            {implementation_plan}
            
            Create detailed implementation guidelines that cover:
            1. Coding standards specific to the tech stack
            2. Testing approach and test coverage requirements
            3. Code review process
            4. Key technical decisions that should be followed
            5. Quality gates for each development phase
            6. Deployment strategy
            
            Format your response as JSON:
            ```json
            {
                "implementation_guidelines": {
                    "coding_standards": ["<specific standard>", "<specific standard>"],
                    "testing_approach": {
                        "strategy": "<overall testing strategy>",
                        "coverage_requirements": "<min test coverage>",
                        "test_frameworks": ["<framework>", "<framework>"],
                        "test_types": ["<type>", "<type>"]
                    },
                    "review_process": {
                        "methodology": "<review methodology>",
                        "standards": ["<standard>", "<standard>"],
                        "tools": ["<tool>", "<tool>"]
                    },
                    "key_technical_decisions": ["<decision>", "<decision>"],
                    "quality_gates": [
                        {
                            "phase": "<phase_id>",
                            "gates": ["<quality gate>", "<quality gate>"]
                        }
                    ],
                    "deployment_strategy": {
                        "approach": "<approach>",
                        "environments": ["<env>", "<env>"],
                        "automation": "<level of automation>",
                        "rollback_strategy": "<strategy>"
                    }
                }
            }
            ```
            
            Make sure the guidelines are specific to the technology stack and align with modern best practices.
            """
        )
    
    def compile_implementation_plan(self, 
                              complexity_analysis: Dict[str, Any], 
                              project_timeline: Dict[str, Any], 
                              risk_assessment: Dict[str, Any],
                              requirements_analysis: Dict[str, Any] = None,
                              tech_stack_recommendation: Dict[str, Any] = None,
                              system_design: Dict[str, Any] = None) -> Dict[str, Any]:
        """Compile a complete implementation plan."""
        with monitoring.agent_trace_span(self.agent_name, "compile_implementation_plan"):
            try:
                # Initialize compilation tracking
                self.compilation_stages = []
                
                # Step 1: Create base plan with proper nesting structure
                self.log_info("Stage 1: Creating base implementation plan")
                base_plan = self._create_base_plan(complexity_analysis, project_timeline)
                self.compilation_stages.append({"stage": "base_plan", "result": base_plan})
                
                # Validate base plan structure before proceeding
                if not self._is_valid_base_plan(base_plan):
                    self.log_warning("Base plan invalid, returning without enhancements")
                    # FIXED: Ensure proper structure with implementation_plan key
                    return {"implementation_plan": {
                        "development_phases": [],
                        "status": "fallback",
                        "error": "Invalid base plan structure"
                    }}
                
                # Step 2: Enhance with requirements analysis
                if requirements_analysis:
                    self.log_info("Stage 2: Enhancing with requirements analysis")
                    req_enhanced_plan = self._enhance_with_requirements(base_plan, requirements_analysis)
                    self.compilation_stages.append({"stage": "requirements", "result": req_enhanced_plan})
                else:
                    self.log_info("Skipping requirements enhancement - missing requirements analysis")
                    req_enhanced_plan = base_plan
                
                # Step 3: Enhance with risk assessment
                self.log_info("Stage 3: Enhancing with risk assessment")
                risk_enhanced_plan = self._enhance_with_risks(req_enhanced_plan, risk_assessment)
                self.compilation_stages.append({"stage": "risks", "result": risk_enhanced_plan})
                
                # Step 4: Generate development phases
                self.log_info("Stage 4: Generating development phases")
                phases_plan = self._generate_development_phases(risk_enhanced_plan, complexity_analysis)
                self.compilation_stages.append({"stage": "phases", "result": phases_plan})
                
                # Step 5: Generate implementation guidelines (if tech stack and system design available)
                if tech_stack_recommendation and system_design:
                    self.log_info("Stage 5: Generating implementation guidelines")
                    final_plan = self._generate_guidelines(
                        phases_plan, 
                        tech_stack_recommendation, 
                        system_design
                    )
                    self.compilation_stages.append({"stage": "guidelines", "result": final_plan})
                else:
                    self.log_info("Skipping guidelines generation - missing tech stack or system design")
                    final_plan = phases_plan
                
                # CRITICAL FIX: Ensure final_plan has implementation_plan key
                if "implementation_plan" not in final_plan:
                    # Nest the current content under implementation_plan key
                    final_plan = {"implementation_plan": final_plan}
                
                # Validate final plan with proper structure
                self._validate_implementation_plan(final_plan)
                
                # Add metadata
                final_plan["implementation_plan"]["metadata"] = {
                    "generated_at": datetime.now().isoformat(),
                    "compilation_stages": len(self.compilation_stages),
                    "completeness_level": "comprehensive" if len(self.compilation_stages) >= 4 else "basic"
                }
                
                # Publish result if message bus is available
                if self.message_bus:
                    try:
                        self.message_bus.publish("implementation_plan_created", final_plan)
                    except Exception as e:
                        self.log_warning(f"Failed to publish implementation plan to message bus: {e}")
                
                return final_plan
                
            except Exception as e:
                self.log_error(f"Implementation plan compilation failed: {str(e)}")
                # Provide a minimal fallback result with proper structure
                return {"implementation_plan": {
                    "development_phases": [
                        {"name": "Emergency Phase", "type": "implementation", "tasks": ["Project initialization"]}
                    ],
                    "status": "error",
                    "error": str(e)
                }}
    
    def _generate_base_plan(self, complexity_analysis, project_timeline, risk_assessment, 
                requirements_analysis=None, tech_stack_recommendation=None, 
                system_design=None):
        """Generate base implementation plan using structured JSON prompt."""
        try:
            # Start with default temperature for initial planning
            temperature_for_planning = self.default_temperature
            binding_args = {"temperature": temperature_for_planning}
            
            # Bind LLM with configured temperature
            llm_with_temp = self.llm.bind(**binding_args)
            
            # Add context for monitoring
            invoke_config = {
                "agent_context": f"{self.agent_name}:base_plan_generation",
                "temperature_used": temperature_for_planning
            }
            
            # Create structured instruction content
            instruction_content = f"""Generate a comprehensive implementation plan based on:
# Project Complexity Analysis
{json.dumps(complexity_analysis, indent=2)}
# Timeline Estimation
{json.dumps(project_timeline, indent=2)}
# Risk Assessment
{json.dumps(risk_assessment, indent=2)}
# Requirements Analysis (if available)
{json.dumps(requirements_analysis, indent=2) if requirements_analysis else "{}"}
# Tech Stack Recommendation (if available)
{json.dumps(tech_stack_recommendation, indent=2) if tech_stack_recommendation else "{}"}
# System Design (if available)
{json.dumps(system_design, indent=2) if system_design else "{}"}"""

            # Use JSON example from stored templates
            example_json = self.json_examples["implementation_plan"]
            
            # FIXED: Use SystemMessage and HumanMessage directly instead of
            # create_strict_json_template which returns a list that can't use .format()
            system_message = SystemMessage(content=f"""You are a specialized Implementation Plan Compiler AI.
                Create a detailed implementation plan in the exact JSON format shown in the example below.
                Ensure all phase IDs are unique and all dependencies reference valid phase IDs.
                Follow the exact JSON structure from the example.
                
                Example JSON format:
                {json.dumps(example_json, indent=2)}""")
        
            human_message = HumanMessage(content=instruction_content)

            # Create a list of messages for the chat model
            messages = [system_message, human_message]

            # Store prompt for potential model escalation
            self.last_json_prompt = messages

            # Invoke LLM with structured messages
            response = llm_with_temp.invoke(messages, config=invoke_config)
            
            # Parse response with robust error tracking
            result = self.parse_json_with_error_tracking(
                response,
                default_response=self._get_default_implementation_plan()
            )
            
            return result
            
        except Exception as e:
            self.log_warning(f"Base plan generation failed: {str(e)}")
            return self._get_default_implementation_plan()
    
    def _enhance_file_structure(self, 
                          base_plan: Dict[str, Any],
                          tech_stack: Dict[str, Any],
                          system_design: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance the plan with detailed file structure"""
        try:
            # Create a copy of the base plan to avoid modifying the original
            enhanced_plan = self._deep_copy_dict(base_plan)
            
            # Extract implementation phases for file structure generation
            implementation_phases = []
            if "implementation_plan" in enhanced_plan and "phases" in enhanced_plan["implementation_plan"]:
                for phase in enhanced_plan["implementation_plan"]["phases"]:
                    implementation_phases.append({
                        "phase_id": phase.get("phase_id", ""),
                        "phase_name": phase.get("phase_name", ""),
                        "description": phase.get("description", ""),
                        "key_deliverables": phase.get("key_deliverables", [])
                    })
            
            # Use binding_args pattern for consistent temperature handling
            # Use slightly lower temperature for more deterministic file structure
            binding_args = {"temperature": 0.2}
            llm_with_temp = self.llm.bind(**binding_args)
            
            # Add context for monitoring
            invoke_config = {
                "agent_context": f"{self.agent_name}:file_structure_generation",
                "temperature_used": binding_args["temperature"],
                "model_name": getattr(self.llm, "model_name", "unknown")
            }
            
            # Execute LLM chain with monitoring config
            response = llm_with_temp.invoke(
                self.file_structure_prompt.format(
                    tech_stack=json.dumps(tech_stack, indent=2),
                    system_design=json.dumps(system_design, indent=2),
                    implementation_phases=json.dumps(implementation_phases, indent=2)
                ),
                config=invoke_config
            )
            
            # Store the activity with temperature metadata
            self.memory.store_agent_activity(
                agent_name=self.agent_name,
                activity_type="file_structure_generation",
                prompt=str(self.file_structure_prompt),
                response=response.content if hasattr(response, 'content') else str(response),
                metadata={"temperature": binding_args["temperature"]}  # Use binding_args for consistency
            )
            
            # Extract JSON from LLM response
            file_structure = self.parse_llm_response(response.content if hasattr(response, 'content') else str(response))
            
            # Update file structure in the plan
            if "file_structure" in file_structure and isinstance(file_structure["file_structure"], dict):
                # Map files to phases
                for phase_id, files in file_structure["file_structure"].items():
                    # Find the matching phase in the plan
                    for i, phase in enumerate(enhanced_plan["implementation_plan"]["phases"]):
                        if phase.get("phase_id") == phase_id:
                            enhanced_plan["implementation_plan"]["phases"][i]["files_to_implement"] = files
                            break
                    
                    self.log_info(f"Enhanced plan with detailed file structure for {len(file_structure['file_structure'])} phases")
            
            return enhanced_plan
            
        except Exception as e:
            self.log_warning(f"File structure enhancement failed: {e}")
            return base_plan
    
    def _enhance_dependencies(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance plan with comprehensive dependency mapping"""
        try:
            # Create a copy of the plan to avoid modifying the original
            enhanced_plan = self._deep_copy_dict(plan)
            
            # Extract phases and files for dependency mapping
            phases = []
            files = []
            
            if "implementation_plan" in enhanced_plan and "phases" in enhanced_plan["implementation_plan"]:
                phases = enhanced_plan["implementation_plan"]["phases"]
                
                # Collect files from all phases
                for phase in phases:
                    if "files_to_implement" in phase and isinstance(phase["files_to_implement"], list):
                        for file in phase["files_to_implement"]:
                            file_with_phase = file.copy()
                            file_with_phase["phase_id"] = phase.get("phase_id", "")
                            files.append(file_with_phase)
        
            # Only proceed if we have phases and files
            if not phases or not files:
                self.log_warning("Not enough data for dependency mapping")
                return plan
            
            # Use binding_args pattern for consistent temperature handling
            # Use analytical temperature for dependency mapping
            binding_args = {"temperature": 0.2}
            llm_with_temp = self.llm.bind(**binding_args)
            
            # Add context for monitoring
            invoke_config = {
                "agent_context": f"{self.agent_name}:dependency_mapping",
                "temperature_used": binding_args["temperature"],
                "model_name": getattr(self.llm, "model_name", "unknown")
            }
            
            # Execute LLM chain with monitoring config
            response = llm_with_temp.invoke(
                self.dependency_mapping_prompt.format(
                    phases=json.dumps(phases, indent=2),
                    files=json.dumps(files, indent=2)
                ),
                config=invoke_config
            )
            
            # Store the activity with temperature metadata
            self.memory.store_agent_activity(
                agent_name=self.agent_name,
                activity_type="dependency_mapping",
                prompt=str(self.dependency_mapping_prompt),
                response=response.content if hasattr(response, 'content') else str(response),
                metadata={"temperature": binding_args["temperature"]}  # Use binding_args for consistency
            )
            
            # Extract JSON from LLM response
            dependency_map = self.parse_llm_response(response.content if hasattr(response, 'content') else str(response))
            
            # Update dependencies in the plan
            if "phase_dependencies" in dependency_map:
                enhanced_plan["implementation_plan"]["dependencies"] = dependency_map["phase_dependencies"]
            
            # Update critical path if available
            if "critical_path" in dependency_map:
                enhanced_plan["implementation_plan"]["critical_path"] = dependency_map["critical_path"]
            
            # Store file dependencies for reference
            if "file_dependencies" in dependency_map:
                if "detailed_dependencies" not in enhanced_plan["implementation_plan"]:
                    enhanced_plan["implementation_plan"]["detailed_dependencies"] = {}
                enhanced_plan["implementation_plan"]["detailed_dependencies"]["file_dependencies"] = dependency_map["file_dependencies"]
            
            self.log_info("Enhanced plan with comprehensive dependency mapping")
            return enhanced_plan
        
        except Exception as e:
            self.log_warning(f"Dependency enhancement failed: {e}")
            return plan
    
    def _align_risks_with_phases(self, plan: Dict[str, Any], risk_assessment: Dict[str, Any]) -> Dict[str, Any]:
        """Align risks with phases and create mitigation strategies"""
        try:
            # Create a copy of the plan to avoid modifying the original
            enhanced_plan = self._deep_copy_dict(plan)
            
            # Extract phases and risks for alignment
            phases = []
            risks = []
            
            if "implementation_plan" in enhanced_plan and "phases" in enhanced_plan["implementation_plan"]:
                phases = enhanced_plan["implementation_plan"]["phases"]
            
            # Extract risks from risk assessment
            if "project_risks" in risk_assessment:
                risks = risk_assessment["project_risks"]
            elif "risks" in risk_assessment:
                risks = risk_assessment["risks"]
            
            # Only proceed if we have phases and risks
            if not phases or not risks:
                self.log_warning("Not enough data for risk alignment")
                return plan
            
            # Use binding_args pattern for consistent temperature handling
            binding_args = {"temperature": 0.3}
            llm_with_temp = self.llm.bind(**binding_args)
            
            # Add context for monitoring
            invoke_config = {
                "agent_context": f"{self.agent_name}:risk_alignment",
                "temperature_used": binding_args["temperature"],
                "model_name": getattr(self.llm, "model_name", "unknown")
            }
            
            # Execute LLM chain with monitoring config
            response = llm_with_temp.invoke(
                self.risk_alignment_prompt.format(
                    phases=json.dumps(phases, indent=2),
                    risks=json.dumps(risks, indent=2)
                ),
                config=invoke_config
            )
            
            # Store the activity with temperature metadata
            self.memory.store_agent_activity(
                agent_name=self.agent_name,
                activity_type="risk_alignment",
                prompt=str(self.risk_alignment_prompt),
                response=response.content if hasattr(response, 'content') else str(response),
                metadata={"temperature": binding_args["temperature"]}  # Use binding_args for consistency
            )
            
            # Extract JSON from LLM response
            risk_plan = self.parse_llm_response(response.content if hasattr(response, 'content') else str(response))
            
            # Update risk mitigation strategies in the plan
            if "risk_mitigation_strategies" in risk_plan:
                enhanced_plan["implementation_plan"]["risk_mitigation_strategies"] = risk_plan["risk_mitigation_strategies"]
            
            # Add high priority risks if available
            if "high_priority_risks" in risk_plan:
                enhanced_plan["implementation_plan"]["high_priority_risks"] = risk_plan["high_priority_risks"]
            
            # Add risk monitoring plan if available
            if "risk_monitoring" in risk_plan:
                enhanced_plan["implementation_plan"]["risk_monitoring"] = risk_plan["risk_monitoring"]
            
            self.log_info("Enhanced plan with risk alignment and mitigation strategies")
            return enhanced_plan
            
        except Exception as e:
            self.log_warning(f"Risk alignment failed: {e}")
            return plan
    
    def _generate_guidelines(self, 
                       plan: Dict[str, Any],
                       tech_stack: Dict[str, Any],
                       system_design: Dict[str, Any]) -> Dict[str, Any]:
        """Generate detailed implementation guidelines"""
        try:
            # Create a copy of the plan to avoid modifying the original
            enhanced_plan = self._deep_copy_dict(plan)
            
            # Extract implementation plan for guidelines generation
            implementation_plan = {}
            if "implementation_plan" in enhanced_plan:
                implementation_plan = enhanced_plan["implementation_plan"]
            
            # Use binding_args pattern for consistent temperature handling
            # Use balanced temperature for guidelines
            binding_args = {"temperature": 0.3}
            llm_with_temp = self.llm.bind(**binding_args)
            
            # Add context for monitoring
            invoke_config = {
                "agent_context": f"{self.agent_name}:guidelines_generation",
                "temperature_used": binding_args["temperature"],
                "model_name": getattr(self.llm, "model_name", "unknown")
            }
            
            # Execute LLM chain with monitoring config
            response = llm_with_temp.invoke(
                self.guidelines_prompt.format(
                    tech_stack=json.dumps(tech_stack, indent=2),
                    system_design=json.dumps(system_design, indent=2),
                    implementation_plan=json.dumps(implementation_plan, indent=2)
                ),
                config=invoke_config
            )
            
            # Store the activity with temperature metadata
            self.memory.store_agent_activity(
                agent_name=self.agent_name,
                activity_type="guidelines_generation",
                prompt=str(self.guidelines_prompt),
                response=response.content if hasattr(response, 'content') else str(response),
                metadata={"temperature": binding_args["temperature"]}  # Use binding_args for consistency
            )
            
            # Extract JSON from LLM response
            guidelines = self.parse_llm_response(response.content if hasattr(response, 'content') else str(response))
            
            # Update implementation guidelines in the plan
            if "implementation_guidelines" in guidelines:
                enhanced_plan["implementation_guidelines"] = guidelines["implementation_guidelines"]
            
            self.log_info("Enhanced plan with detailed implementation guidelines")
            return enhanced_plan
            
        except Exception as e:
            self.log_warning(f"Guidelines generation failed: {e}")
            return plan
    
    def _deep_copy_dict(self, d: Dict[str, Any]) -> Dict[str, Any]:
        """Create a deep copy of a dictionary"""
        return json.loads(json.dumps(d))
    
    def _is_valid_base_plan(self, plan: Dict[str, Any]) -> bool:
        """Check if base plan has required structure for enhancement"""
        if not isinstance(plan, dict):
            self.log_warning("Base plan is not a dictionary")
            return False
        
        # ENHANCED: Look for implementation_plan OR directly check for development_phases
        if "implementation_plan" not in plan and "development_phases" not in plan:
            self.log_warning("Missing implementation_plan or development_phases in base plan")
            return False
        
        # Check the nested structure if implementation_plan exists
        if "implementation_plan" in plan:
            if not isinstance(plan["implementation_plan"], dict):
                self.log_warning("implementation_plan is not a dictionary")
                return False
            
            # Look for phases in implementation_plan
            has_phases = False
            if "phases" in plan["implementation_plan"] and plan["implementation_plan"]["phases"]:
                has_phases = True
            elif "development_phases" in plan["implementation_plan"] and plan["implementation_plan"]["development_phases"]:
                has_phases = True
            
            if not has_phases:
                self.log_warning("No phases or development_phases found in implementation_plan")
                return False
        # If we have direct development_phases at the root level
        elif "development_phases" in plan and not plan["development_phases"]:
            self.log_warning("Empty development_phases list")
            return False
        
        # Log structure for debugging
        self.log_info(f"Valid base plan with keys: {list(plan.keys())}")
        return True
    
    def _validate_implementation_plan(self, plan: Dict[str, Any]) -> None:
        """Validate the implementation plan has required fields and sensible data"""
        if "implementation_plan" not in plan:
            raise ValueError("Missing 'implementation_plan' key in compiled plan")
        
        if "phases" not in plan["implementation_plan"]:
            raise ValueError("Missing 'phases' in implementation plan")
        
        if not plan["implementation_plan"]["phases"]:
            raise ValueError("Implementation plan contains no phases")
            
        # Check phase IDs are unique
        phase_ids = [phase.get("phase_id") for phase in plan["implementation_plan"]["phases"] if "phase_id" in phase]
        if len(phase_ids) != len(set(phase_ids)):
            self.log_warning("Implementation plan contains duplicate phase IDs")
        
        # Check if all dependencies reference valid phases
        if "dependencies" in plan["implementation_plan"]:
            for dep in plan["implementation_plan"]["dependencies"]:
                from_phase = dep.get("from_phase")
                to_phase = dep.get("to_phase")
                
                if from_phase and from_phase not in phase_ids:
                    self.log_warning(f"Dependency references non-existent phase ID: {from_phase}")
                
                if to_phase and to_phase not in phase_ids:
                    self.log_warning(f"Dependency references non-existent phase ID: {to_phase}")

    def get_enhanced_default_response(self, 
                                error: str = "",
                                complexity_analysis: Dict[str, Any] = None,
                                project_timeline: Dict[str, Any] = None) -> Dict[str, Any]:
        """Return enhanced default response when processing fails, using available data"""
        default_plan = {
            "implementation_plan": {
                "project_summary": {
                    "title": "Error in Plan Compilation",
                    "description": f"Implementation plan compilation failed: {error}",
                    "overall_complexity": "Unknown",
                    "estimated_duration": "Unknown"
                },
                "phases": [  # Make sure we have this structure
                    {
                        "phase_id": "P1",
                        "phase_name": "Project Setup",
                        "description": "Setup project structure and repositories",
                        "estimated_days": 5,
                        "key_deliverables": ["Project structure", "Environment setup"],
                        "key_risks": [],
                        "files_to_implement": [],
                        "completion_criteria": ["Repository initialized"]
                    },
                    {
                        "phase_id": "P2",
                        "phase_name": "Backend Development",
                        "description": "Implement backend services and APIs",
                        "estimated_days": 15,
                        "key_deliverables": ["API implementation", "Database setup"],
                        "key_risks": [],
                        "files_to_implement": [],
                        "completion_criteria": ["API endpoints functional"]
                    },
                    {
                        "phase_id": "P3",
                        "phase_name": "Frontend Development",
                        "description": "Implement user interface components",
                        "estimated_days": 15,
                        "key_deliverables": ["UI components", "Integration with API"],
                        "key_risks": [],
                        "files_to_implement": [],
                        "completion_criteria": ["UI functional"]
                    },
                    {
                        "phase_id": "P4",
                        "phase_name": "Testing and Deployment",
                        "description": "Test and deploy application",
                        "estimated_days": 10,
                        "key_deliverables": ["Test cases", "Deployment setup"],
                        "key_risks": [],
                        "files_to_implement": [],
                        "completion_criteria": ["All tests pass"]
                    }
                ]
            },
            "development_phases": [  # IMPORTANT: Add this to ensure compatibility
                {
                    "name": "Project Setup",
                    "type": "setup",
                    "duration": "1 week",
                    "tasks": ["Repository setup", "Environment configuration"]
                },
                {
                    "name": "Backend Development",
                    "type": "backend",
                    "duration": "3 weeks",
                    "tasks": ["API implementation", "Database setup"]
                },
                {
                    "name": "Frontend Development",
                    "type": "frontend",
                    "duration": "3 weeks",
                    "tasks": ["UI components", "API integration"]
                },
                {
                    "name": "Testing & Deployment",
                    "type": "testing",
                    "duration": "2 weeks",
                    "tasks": ["Testing", "Deployment preparation"]
                }
            ],
            "error": error
        }
        
        # Enhance with data from complexity analysis if available
        if complexity_analysis:
            try:
                # Extract complexity score
                if "project_complexity" in complexity_analysis:
                    score = complexity_analysis["project_complexity"].get("overall_complexity_score", "Unknown")
                    default_plan["implementation_plan"]["project_summary"]["overall_complexity"] = score
                
                # Extract resource requirements
                if "resource_requirements" in complexity_analysis:
                    resources = complexity_analysis["resource_requirements"]
                    default_plan["implementation_plan"]["resource_allocation"] = {
                        "recommended_team_size": resources.get("recommended_team_size", 3),
                        "specialized_skills_required": resources.get("specialized_skills_required", [])
                    }
            except:
                pass
        
        # Enhance with data from project timeline if available
        if project_timeline:
            try:
                # Extract timeline data
                if "project_timeline" in project_timeline:
                    timeline = project_timeline["project_timeline"]
                    default_plan["implementation_plan"]["project_summary"]["estimated_duration"] = timeline.get("estimated_duration_weeks", "Unknown")
                
                # Extract phases if available
                if "development_phases" in project_timeline and len(project_timeline["development_phases"]) > 0:
                    default_phases = []
                    for i, phase in enumerate(project_timeline["development_phases"]):
                        default_phases.append({
                            "phase_id": f"P{i+1}",
                            "phase_name": phase.get("phase_name", f"Phase {i+1}"),
                            "description": phase.get("description", "No description available"),
                            "estimated_days": phase.get("duration_days", 15),
                            "key_deliverables": [],
                            "key_risks": [],
                            "files_to_implement": [],
                            "completion_criteria": []
                        })
                    default_plan["implementation_plan"]["phases"] = default_phases
            except:
                pass
        
        return default_plan
    
    def parse_llm_response(self, text: str) -> Dict[str, Any]:
        """Parse and clean the LLM response using the centralized JsonHandler"""
        # Use parent class implementation for consistent handling
        return super().parse_json_with_error_tracking(
            text,
            default_response={}
        )

    def get_default_response(self) -> Dict[str, Any]:
        """Returns a default implementation plan when compilation fails."""
        return {
            "status": "error",
            "message": f"An error occurred in {self.agent_name}.",
            "implementation_plan": {
                "development_phases": [
                    {
                        "name": "Phase 1: Project Setup",
                        "type": "setup",
                        "duration": "1 week",
                        "tasks": ["Repository setup", "Environment configuration"]
                    },
                    {
                        "name": "Phase 2: Core Development",
                        "type": "development",
                        "duration": "6 weeks",
                        "tasks": ["Implement core functionality"]
                    },
                    {
                        "name": "Phase 3: Testing & Deployment",
                        "type": "testing",
                        "duration": "2 weeks",
                        "tasks": ["Testing", "Deployment preparation"]
                    }
                ],
                "task_breakdown": [],
                "dependencies": []
            }
        }

    def run(self, project_analysis: Dict[str, Any], 
            timeline_estimation: Dict[str, Any], 
            risk_assessment: Dict[str, Any],
            requirements_analysis: Dict[str, Any] = None,
            tech_stack_recommendation: Dict[str, Any] = None,
            system_design: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Main execution method required by the node functions.
        """
        # Simply use the agent_trace_span without passing temperature
        with monitoring.agent_trace_span(self.agent_name, "plan_compilation"):
            self.log_info(f"Starting implementation plan compilation with temperature {self.default_temperature}")
            
            try:
                # Execute with full context if available
                return self.compile_implementation_plan(
                    project_analysis,
                    timeline_estimation,
                    risk_assessment,
                    requirements_analysis,
                    tech_stack_recommendation,
                    system_design
                )
            except Exception as e:
                self.log_error(f"Plan compilation failed: {str(e)}")
                return self.get_enhanced_default_response(
                    error=str(e),
                    complexity_analysis=project_analysis,
                    project_timeline=timeline_estimation
                )

    def _get_default_implementation_plan(self):
        """Create minimal default implementation plan when generation fails."""
        current_time = datetime.now().strftime("%Y-%m-%d")
        return {
            "project_summary": {
                "title": "Default Implementation Plan",
                "description": "Generated due to error in plan compilation",
                "overall_complexity": "Medium",
                "estimated_duration": "12 weeks"
            },
            "development_phases": [  # Using the exact field name expected by phase_iterator
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
            "generation_date": current_time,
            "status": "auto-generated fallback plan"
        }