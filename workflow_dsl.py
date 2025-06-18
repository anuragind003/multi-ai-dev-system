"""
Workflow DSL - Domain-Specific Language for defining custom agent pipelines
"""

import yaml
from typing import Dict, Any, List, Optional, Type
import os
import importlib
import logging
from pathlib import Path

from agents.base_agent import BaseAgent
from message_bus import MessageBus
import monitoring

class WorkflowDSL:
    """
    Domain-Specific Language for defining custom agent pipelines.
    Loads workflow definitions from YAML files and constructs agent pipelines.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.registered_agent_types = {}
        
        # Register built-in agent types
        self._register_default_agents()
    
    def _register_default_agents(self):
        """Register built-in agent types for easy reference in YAML definitions"""
        # Core agents
        self.register_agent_type("BRDAnalyst", "agents.brd_analyst", "BRDAnalystAgent")
        self.register_agent_type("TechStackAdvisor", "agents.tech_stack_advisor", "TechStackAdvisorAgent")
        self.register_agent_type("SystemDesigner", "agents.system_designer", "SystemDesignerAgent")
        
        # Planning agents
        self.register_agent_type("ProjectAnalyzer", "agents.planning.project_analyzer", "ProjectAnalyzerAgent")
        self.register_agent_type("TimelineEstimator", "agents.planning.timeline_estimator", "TimelineEstimatorAgent")
        self.register_agent_type("RiskAssessor", "agents.planning.risk_assessor", "RiskAssessorAgent")
        self.register_agent_type("PlanCompiler", "agents.planning.plan_compiler", "PlanCompilerAgent")
        
        # Code generation agents
        self.register_agent_type("ArchitectureGenerator", "agents.code_generation.architecture_generator", "ArchitectureGeneratorAgent")
        self.register_agent_type("BackendGenerator", "agents.code_generation.backend_generator", "BackendGeneratorAgent")
        self.register_agent_type("FrontendGenerator", "agents.code_generation.frontend_generator", "FrontendGeneratorAgent")
        self.register_agent_type("DatabaseGenerator", "agents.code_generation.database_generator", "DatabaseGeneratorAgent")
        self.register_agent_type("IntegrationGenerator", "agents.code_generation.integration_generator", "IntegrationGeneratorAgent")
        self.register_agent_type("CodeOptimizer", "agents.code_generation.code_optimizer", "CodeOptimizerAgent")
        
    def register_agent_type(self, type_name: str, module_path: str, class_name: str) -> None:
        """
        Register a new agent type for use in workflow definitions
        
        Args:
            type_name: Short name to use in YAML
            module_path: Python module path
            class_name: Class name in the module
        """
        self.registered_agent_types[type_name] = {
            "module_path": module_path,
            "class_name": class_name
        }
        self.logger.debug(f"Registered agent type: {type_name} -> {module_path}.{class_name}")
        
    def load_workflow(self, workflow_file: str) -> Dict[str, Any]:
        """
        Load a workflow configuration from a YAML file
        
        Args:
            workflow_file: Path to YAML workflow definition
            
        Returns:
            Dict containing workflow definition
        """
        if not os.path.exists(workflow_file):
            raise FileNotFoundError(f"Workflow file not found: {workflow_file}")
            
        with open(workflow_file, 'r') as f:
            try:
                workflow_def = yaml.safe_load(f)
                self.logger.info(f"Loaded workflow definition: {workflow_def.get('name', 'unnamed')}")
                
                # Validate workflow structure
                self._validate_workflow(workflow_def)
                
                return workflow_def
            except yaml.YAMLError as e:
                self.logger.error(f"Error parsing workflow YAML: {e}")
                raise ValueError(f"Invalid YAML in workflow file: {e}")
        
    def _validate_workflow(self, workflow_def: Dict[str, Any]) -> None:
        """
        Validate workflow definition structure
        
        Args:
            workflow_def: The workflow definition to validate
            
        Raises:
            ValueError: If the workflow definition is invalid
        """
        required_keys = ["name", "version", "phases"]
        
        for key in required_keys:
            if key not in workflow_def:
                raise ValueError(f"Missing required key in workflow definition: {key}")
                
        for i, phase in enumerate(workflow_def["phases"]):
            if "name" not in phase:
                raise ValueError(f"Phase at index {i} is missing a name")
                
            if "agents" not in phase:
                raise ValueError(f"Phase '{phase.get('name', f'at index {i}')}' is missing agents list")
                
            for j, agent in enumerate(phase["agents"]):
                if "type" not in agent:
                    raise ValueError(f"Agent at index {j} in phase '{phase.get('name')}' is missing type")
                    
                # Validate agent type exists
                agent_type = agent["type"]
                if "." not in agent_type and agent_type not in self.registered_agent_types:
                    self.logger.warning(f"Unknown agent type: {agent_type}")
        
    def build_workflow(self, workflow_def: Dict[str, Any], system_config, message_bus: MessageBus, 
                      output_dir: str, checkpoint_manager) -> Dict[str, Any]:
        """
        Build a workflow from a workflow definition
        
        Args:
            workflow_def: Workflow definition dict
            system_config: System configuration
            message_bus: Shared message bus for agent communication
            output_dir: Output directory for generated files
            checkpoint_manager: Checkpoint manager for state persistence
            
        Returns:
            Dict containing the constructed workflow
        """
        # Initialize workflow components
        workflow = {
            "name": workflow_def["name"],
            "version": workflow_def["version"],
            "description": workflow_def.get("description", ""),
            "phases": []
        }
        
        try:
            # Create phases
            for phase_def in workflow_def["phases"]:
                phase = {
                    "name": phase_def["name"],
                    "agents": [],
                    "checkpoint": phase_def.get("checkpoint", True)
                }
                
                # Create agents for this phase
                for agent_def in phase_def["agents"]:
                    try:
                        # Get agent temperature from definition or use default
                        temperature = agent_def.get("temperature")
                        
                        # Get agent class
                        agent_class = self._import_agent_class(agent_def["type"])
                        
                        # Determine constructor arguments based on agent type
                        kwargs = {
                            "llm": system_config.get_llm(temperature),
                            "memory": system_config.memory,
                            "rag_retriever": system_config.rag_retriever if agent_def.get("use_rag", True) else None
                        }
                        
                        # Add output_dir for code generation agents
                        if "Generator" in agent_def["type"] or "Optimizer" in agent_def["type"]:
                            kwargs["output_dir"] = output_dir
                        
                        agent_instance = agent_class(**kwargs)
                        
                        # Connect agent to message bus
                        agent_instance.set_message_bus(message_bus)
                        
                        # Add agent to phase
                        phase["agents"].append({
                            "instance": agent_instance,
                            "inputs": agent_def.get("inputs", []),
                            "outputs": agent_def.get("outputs", []),
                            "conditions": agent_def.get("conditions", {}),
                            "type": agent_def["type"]
                        })
                        
                        self.logger.info(f"Created agent of type {agent_def['type']} for phase {phase_def['name']}")
                    except Exception as e:
                        self.logger.error(f"Error creating agent of type {agent_def['type']}: {e}")
                        raise
                    
                workflow["phases"].append(phase)
            
            self.logger.info(f"Successfully built workflow '{workflow['name']}' with {len(workflow['phases'])} phases")
            return workflow
            
        except Exception as e:
            self.logger.error(f"Error building workflow: {e}")
            raise
    
    def _import_agent_class(self, agent_type: str) -> Type[BaseAgent]:
        """
        Import an agent class by its type string
        
        Args:
            agent_type: Agent type identifier
            
        Returns:
            Agent class
        """
        # Handle registered types
        if agent_type in self.registered_agent_types:
            module_path = self.registered_agent_types[agent_type]["module_path"]
            class_name = self.registered_agent_types[agent_type]["class_name"]
            
            try:
                module = importlib.import_module(module_path)
                return getattr(module, class_name)
            except (ImportError, AttributeError) as e:
                self.logger.error(f"Error importing {module_path}.{class_name}: {e}")
                raise ImportError(f"Could not import agent type {agent_type}: {e}")
        
        # Handle explicit module.class path
        if "." in agent_type:
            try:
                module_path, class_name = agent_type.rsplit(".", 1)
                module = importlib.import_module(module_path)
                return getattr(module, class_name)
            except (ImportError, AttributeError) as e:
                self.logger.error(f"Error importing {agent_type}: {e}")
                raise ImportError(f"Could not import agent type {agent_type}: {e}")
            
        raise ValueError(f"Unknown agent type: {agent_type}")