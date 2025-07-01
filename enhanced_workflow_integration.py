"""
Enhanced Graph Integration for Multi-AI Development System

This module provides enhanced LangGraph workflows that integrate native A2A communication
with your existing agent architecture while maintaining backward compatibility.
"""

import logging
import time
from typing import Dict, Any, List, Optional
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.runnables import RunnableLambda

from agent_state import AgentState, StateFields
from langgraph_enhanced_a2a import LangGraphEnhancedA2AManager, enhance_existing_workflow
from graph_nodes import (
    # Import existing nodes
    brd_analysis_node,
    tech_stack_recommendation_node,
    system_design_node,
    planning_node,
    phase_iterator_node,
    code_generation_dispatcher_node,
    code_quality_analysis_node,
    phase_completion_node,
    increment_revision_count_node,
    testing_module_node,
    finalize_workflow,
    initialize_workflow_state,
    has_next_phase,
    should_retry_code_generation
)
import monitoring

logger = logging.getLogger(__name__)

class EnhancedWorkflowBuilder:
    """Builder for creating enhanced workflows with A2A communication."""
    
    def __init__(self):
        self.a2a_manager = None
        self.workflow = None
        self.enhancement_config = {
            'enable_cross_validation': True,
            'enable_smart_routing': True,
            'enable_context_sharing': True,
            'enable_error_recovery': True,
            'enable_concurrent_validation': False,  # Conservative default
            'max_retries_per_agent': 3,
            'cross_validation_threshold': 0.7
        }
    
    def configure_enhancements(self, config: Dict[str, Any]) -> 'EnhancedWorkflowBuilder':
        """Configure enhancement options."""
        self.enhancement_config.update(config)
        return self
    
    def create_enhanced_phased_workflow(self) -> StateGraph:
        """Create the enhanced version of your phased workflow."""
        
        workflow = StateGraph(AgentState)
        self.a2a_manager = LangGraphEnhancedA2AManager(workflow)
        
        # Register enhanced nodes with dependencies and validations
        self._add_enhanced_planning_phase(workflow)
        self._add_enhanced_implementation_phase(workflow)
        self._add_enhanced_quality_phase(workflow)
        self._add_enhanced_finalization_phase(workflow)
        
        # Add enhanced edges with dynamic routing
        self._add_enhanced_edges(workflow)
        
        # Configure cross-validation rules
        self._setup_cross_validation_rules()
        
        logger.info(f"Created enhanced phased workflow with config: {self.enhancement_config}")
        return workflow
    
    def _add_enhanced_planning_phase(self, workflow: StateGraph):
        """Add planning phase nodes with enhanced A2A communication."""
        
        # Initialize with enhanced context
        enhanced_init = self.a2a_manager.create_enhanced_node(
            initialize_workflow_state,
            "workflow_initializer",
            dependencies=[],
            validators=["state_structure_validator"]
        )
        
        # BRD Analysis with enhanced output sharing
        enhanced_brd = self.a2a_manager.create_enhanced_node(
            brd_analysis_node,
            "brd_analyst",
            dependencies=[],
            validators=["requirements_validator", "completeness_validator"]
        )
        
        # Tech Stack with BRD dependency
        enhanced_tech_stack = self.a2a_manager.create_enhanced_node(
            tech_stack_recommendation_node,
            "tech_stack_advisor",
            dependencies=["brd_analyst"],
            validators=["tech_stack_validator", "feasibility_validator"]
        )
        
        # System Design with previous dependencies
        enhanced_system_design = self.a2a_manager.create_enhanced_node(
            system_design_node,
            "system_designer",
            dependencies=["brd_analyst", "tech_stack_advisor"],
            validators=["design_validator", "architecture_validator"]
        )
        
        # Planning with all previous context
        enhanced_planning = self.a2a_manager.create_enhanced_node(
            planning_node,
            "plan_compiler",
            dependencies=["brd_analyst", "tech_stack_advisor", "system_designer"],
            validators=["plan_validator", "timeline_validator"]
        )
        
        # Add nodes to workflow
        workflow.add_node(
            "initialize_state_node",
            RunnableLambda(enhanced_init).with_config(
                tags=["Enhanced", "Initialization"],
                metadata={"description": "Enhanced initialization with A2A context setup"}
            )
        )
        
        workflow.add_node(
            "brd_analysis_node",
            RunnableLambda(enhanced_brd).with_config(
                tags=["Enhanced", "Planning", "Analysis"],
                metadata={"description": "Enhanced BRD analysis with cross-validation"}
            )
        )
        
        workflow.add_node(
            "tech_stack_node",
            RunnableLambda(enhanced_tech_stack).with_config(
                tags=["Enhanced", "Planning", "Architecture"],
                metadata={"description": "Enhanced tech stack recommendation with dependency validation"}
            )
        )
        
        workflow.add_node(
            "system_design_node",
            RunnableLambda(enhanced_system_design).with_config(
                tags=["Enhanced", "Planning", "Architecture"],
                metadata={"description": "Enhanced system design with multi-agent context"}
            )
        )
        
        workflow.add_node(
            "planning_node",
            RunnableLambda(enhanced_planning).with_config(
                tags=["Enhanced", "Planning"],
                metadata={"description": "Enhanced planning with comprehensive agent context"}
            )
        )
    
    def _add_enhanced_implementation_phase(self, workflow: StateGraph):
        """Add implementation phase with enhanced coordination."""
        
        # Phase iterator with enhanced context
        enhanced_phase_iterator = self.a2a_manager.create_enhanced_node(
            phase_iterator_node,
            "phase_iterator",
            dependencies=["plan_compiler"],
            validators=["phase_readiness_validator"]
        )
        
        # Code generation with enhanced feedback
        enhanced_code_generation = self.a2a_manager.create_enhanced_node(
            code_generation_dispatcher_node,
            "code_generator",
            dependencies=["phase_iterator", "system_designer"],
            validators=["code_structure_validator", "implementation_validator"]
        )
        
        # Code quality with cross-reference validation
        enhanced_code_quality = self.a2a_manager.create_enhanced_node(
            code_quality_analysis_node,
            "code_quality_reviewer",
            dependencies=["code_generator", "system_designer"],
            validators=["quality_standards_validator", "design_compliance_validator"]
        )
        
        # Phase completion with enhanced state management
        enhanced_phase_completion = self.a2a_manager.create_enhanced_node(
            phase_completion_node,
            "phase_completion_manager",
            dependencies=["code_quality_reviewer"],
            validators=["phase_completion_validator"]
        )
        
        # Revision increment with smart retry logic
        enhanced_revision_increment = self.a2a_manager.create_enhanced_node(
            increment_revision_count_node,
            "revision_manager",
            dependencies=["code_quality_reviewer"],
            validators=["retry_limit_validator"]
        )
        
        # Add implementation nodes
        workflow.add_node(
            "phase_iterator_node",
            RunnableLambda(enhanced_phase_iterator).with_config(
                tags=["Enhanced", "Control Flow"],
                metadata={"description": "Enhanced phase iteration with dependency tracking"}
            )
        )
        
        workflow.add_node(
            "generate_code_node",
            RunnableLambda(enhanced_code_generation).with_config(
                tags=["Enhanced", "Implementation", "Code Generation"],
                metadata={"description": "Enhanced code generation with context sharing"}
            )
        )
        
        workflow.add_node(
            "review_code_node",
            RunnableLambda(enhanced_code_quality).with_config(
                tags=["Enhanced", "Quality Assurance", "Review"],
                metadata={"description": "Enhanced code review with cross-agent validation"}
            )
        )
        
        workflow.add_node(
            "phase_complete_node",
            RunnableLambda(enhanced_phase_completion).with_config(
                tags=["Enhanced", "Control Flow"],
                metadata={"description": "Enhanced phase completion with state validation"}
            )
        )
        
        workflow.add_node(
            "increment_revision_node",
            RunnableLambda(enhanced_revision_increment).with_config(
                tags=["Enhanced", "Control Flow", "Revision"],
                metadata={"description": "Enhanced revision management with smart retry"}
            )
        )
    
    def _add_enhanced_quality_phase(self, workflow: StateGraph):
        """Add quality assurance phase with enhanced validation."""
        
        # Testing with comprehensive context
        enhanced_testing = self.a2a_manager.create_enhanced_node(
            testing_module_node,
            "test_suite_manager",
            dependencies=["code_generator", "system_designer", "plan_compiler"],
            validators=["test_coverage_validator", "test_quality_validator"]
        )
        
        workflow.add_node(
            "testing_module_node",
            RunnableLambda(enhanced_testing).with_config(
                tags=["Enhanced", "Quality Assurance", "Testing"],
                metadata={"description": "Enhanced testing with multi-agent context validation"}
            )
        )
    
    def _add_enhanced_finalization_phase(self, workflow: StateGraph):
        """Add finalization with enhanced reporting."""
        
        # Finalization with comprehensive summary
        enhanced_finalization = self.a2a_manager.create_enhanced_node(
            finalize_workflow,
            "workflow_finalizer",
            dependencies=["test_suite_manager"],
            validators=["completion_validator", "deliverable_validator"]
        )
        
        workflow.add_node(
            "finalize_node",
            RunnableLambda(enhanced_finalization).with_config(
                tags=["Enhanced", "Finalization"],
                metadata={"description": "Enhanced finalization with A2A communication summary"}
            )
        )
    
    def _add_enhanced_edges(self, workflow: StateGraph):
        """Add enhanced edges with dynamic routing."""
        
        # Set entry point
        workflow.set_entry_point("initialize_state_node")
        
        # Planning phase edges
        workflow.add_edge("initialize_state_node", "brd_analysis_node")
        workflow.add_edge("brd_analysis_node", "tech_stack_node")
        workflow.add_edge("tech_stack_node", "system_design_node")
        workflow.add_edge("system_design_node", "planning_node")
        workflow.add_edge("planning_node", "phase_iterator_node")
        
        # Implementation phase with enhanced routing
        enhanced_has_next_phase = self.a2a_manager.create_dynamic_conditional_edge(
            "phase_iterator_node",
            has_next_phase,
            {
                StateFields.NEXT_PHASE: "generate_code_node",
                StateFields.WORKFLOW_COMPLETE: "testing_module_node"
            }
        )
        
        workflow.add_conditional_edges(
            "phase_iterator_node",
            enhanced_has_next_phase,
            {
                StateFields.NEXT_PHASE: "generate_code_node",
                StateFields.WORKFLOW_COMPLETE: "testing_module_node"
            }
        )
        
        # Code generation -> review cycle
        workflow.add_edge("generate_code_node", "review_code_node")
        
        # Enhanced review decision with cross-validation
        enhanced_retry_decision = self.a2a_manager.create_dynamic_conditional_edge(
            "review_code_node",
            should_retry_code_generation,
            {
                StateFields.APPROVE: "phase_complete_node",
                StateFields.REVISE: "increment_revision_node"
            }
        )
        
        workflow.add_conditional_edges(
            "review_code_node",
            enhanced_retry_decision,
            {
                StateFields.APPROVE: "phase_complete_node",
                StateFields.REVISE: "increment_revision_node"
            }
        )
        
        # Revision cycle
        workflow.add_edge("increment_revision_node", "generate_code_node")
        workflow.add_edge("phase_complete_node", "phase_iterator_node")
        
        # Finalization
        workflow.add_edge("testing_module_node", "finalize_node")
        workflow.add_edge("finalize_node", END)
    
    def _setup_cross_validation_rules(self):
        """Setup cross-validation rules between agents."""
        
        if not self.enhancement_config.get('enable_cross_validation'):
            return
        
        # Register validators
        self._register_agent_validators()
        
        # Register cross-validation rules
        self.a2a_manager.register_cross_validation_rule(
            ('brd_analyst', 'tech_stack_advisor'),
            self._validate_brd_tech_alignment
        )
        
        self.a2a_manager.register_cross_validation_rule(
            ('system_designer', 'code_generator'),
            self._validate_design_code_alignment
        )
        
        self.a2a_manager.register_cross_validation_rule(
            ('code_generator', 'code_quality_reviewer'),
            self._validate_code_quality_alignment
        )
        
        self.a2a_manager.register_cross_validation_rule(
            ('plan_compiler', 'phase_iterator'),
            self._validate_plan_execution_alignment
        )
    
    def _register_agent_validators(self):
        """Register individual agent output validators."""
        
        # Requirements validation
        self.a2a_manager.register_agent_validator(
            "requirements_validator",
            lambda result: self._validate_requirements_completeness(result)
        )
        
        # Tech stack validation
        self.a2a_manager.register_agent_validator(
            "tech_stack_validator",
            lambda result: self._validate_tech_stack_feasibility(result)
        )
        
        # Design validation
        self.a2a_manager.register_agent_validator(
            "design_validator",
            lambda result: self._validate_design_completeness(result)
        )
        
        # Code validation
        self.a2a_manager.register_agent_validator(
            "code_structure_validator",
            lambda result: self._validate_code_structure(result)
        )
        
        # Quality validation
        self.a2a_manager.register_agent_validator(
            "quality_standards_validator",
            lambda result: self._validate_quality_standards(result)
        )
    
    def _validate_requirements_completeness(self, result: Dict[str, Any]) -> bool:
        """Validate that requirements analysis is complete."""
        try:
            requirements = result.get('requirements_analysis', {})
            if not requirements:
                return False
            
            # Check for essential requirement categories
            essential_categories = ['functional', 'non_functional', 'technical']
            found_categories = [cat for cat in essential_categories if cat in str(requirements).lower()]
            
            return len(found_categories) >= 2  # At least 2 essential categories
        except Exception:
            return False
    
    def _validate_tech_stack_feasibility(self, result: Dict[str, Any]) -> bool:
        """Validate tech stack feasibility."""
        try:
            tech_stack = result.get('tech_stack_recommendation', {})
            if not tech_stack:
                return False
            
            # Check for essential components
            essential_components = ['backend', 'frontend', 'database']
            found_components = [comp for comp in essential_components if comp in str(tech_stack).lower()]
            
            return len(found_components) >= 2  # At least 2 essential components
        except Exception:
            return False
    
    def _validate_design_completeness(self, result: Dict[str, Any]) -> bool:
        """Validate system design completeness."""
        try:
            design = result.get('system_design', {})
            if not design:
                return False
            
            # Check for design elements
            design_elements = ['architecture', 'components', 'data_flow', 'api']
            found_elements = [elem for elem in design_elements if elem in str(design).lower()]
            
            return len(found_elements) >= 2  # At least 2 design elements
        except Exception:
            return False
    
    def _validate_code_structure(self, result: Dict[str, Any]) -> bool:
        """Validate code structure."""
        try:
            code_result = result.get('code_generation_result', {})
            generated_files = code_result.get('generated_files', {})
            
            return len(generated_files) > 0  # At least some files generated
        except Exception:
            return False
    
    def _validate_quality_standards(self, result: Dict[str, Any]) -> bool:
        """Validate code quality standards."""
        try:
            review = result.get('code_review_feedback', {})
            if not review:
                return False
            
            # Check quality score if available
            quality_score = review.get('quality_score', 0)
            return quality_score >= self.enhancement_config.get('cross_validation_threshold', 0.7)
        except Exception:
            return False
    
    def _validate_brd_tech_alignment(self, brd_result: Dict, tech_result: Dict) -> Dict[str, Any]:
        """Validate alignment between BRD and tech stack."""
        try:
            requirements = brd_result.get('requirements_analysis', {})
            tech_stack = tech_result.get('tech_stack_recommendation', {})
            
            alignment_score = 0.0
            alignment_details = []
            
            # Check scalability alignment
            if 'scalability' in str(requirements).lower():
                if 'scalable' in str(tech_stack).lower():
                    alignment_score += 0.25
                    alignment_details.append("Scalability requirements addressed")
                else:
                    alignment_details.append("Scalability requirements not addressed")
            
            # Check security alignment
            if 'security' in str(requirements).lower():
                if 'security' in str(tech_stack).lower():
                    alignment_score += 0.25
                    alignment_details.append("Security requirements addressed")
                else:
                    alignment_details.append("Security requirements not addressed")
            
            # Check performance alignment
            if 'performance' in str(requirements).lower():
                if 'performance' in str(tech_stack).lower():
                    alignment_score += 0.25
                    alignment_details.append("Performance requirements addressed")
                else:
                    alignment_details.append("Performance requirements not addressed")
            
            # Base alignment for having both components
            if requirements and tech_stack:
                alignment_score += 0.25
            
            return {
                'valid': alignment_score >= self.enhancement_config.get('cross_validation_threshold', 0.7),
                'score': alignment_score,
                'details': alignment_details,
                'timestamp': time.time()
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': str(e),
                'timestamp': time.time()
            }
    
    def _validate_design_code_alignment(self, design_result: Dict, code_result: Dict) -> Dict[str, Any]:
        """Validate alignment between design and code."""
        try:
            design = design_result.get('system_design', {})
            code_files = code_result.get('code_generation_result', {}).get('generated_files', {})
            
            alignment_score = 0.0
            alignment_details = []
            
            # Check component implementation
            components = design.get('components', [])
            if isinstance(components, list):
                implemented_components = 0
                for component in components:
                    component_name = str(component).lower()
                    if any(component_name in file_path.lower() for file_path in code_files.keys()):
                        implemented_components += 1
                        alignment_details.append(f"Component '{component}' implemented")
                    else:
                        alignment_details.append(f"Component '{component}' missing")
                
                if len(components) > 0:
                    alignment_score = implemented_components / len(components)
            else:
                # Fallback: check if any design concepts are in code
                design_concepts = ['api', 'service', 'controller', 'model', 'view']
                found_concepts = 0
                for concept in design_concepts:
                    if concept in str(design).lower() and any(concept in file_path.lower() for file_path in code_files.keys()):
                        found_concepts += 1
                        alignment_details.append(f"Design concept '{concept}' implemented")
                
                alignment_score = found_concepts / len(design_concepts) if design_concepts else 0.0
            
            return {
                'valid': alignment_score >= self.enhancement_config.get('cross_validation_threshold', 0.7),
                'score': alignment_score,
                'details': alignment_details,
                'timestamp': time.time()
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': str(e),
                'timestamp': time.time()
            }
    
    def _validate_code_quality_alignment(self, code_result: Dict, quality_result: Dict) -> Dict[str, Any]:
        """Validate alignment between generated code and quality review."""
        try:
            code_files = code_result.get('code_generation_result', {}).get('generated_files', {})
            quality_feedback = quality_result.get('code_review_feedback', {})
            
            alignment_score = 0.0
            alignment_details = []
            
            # Check if quality review addresses the generated files
            reviewed_files = quality_feedback.get('reviewed_files', [])
            if reviewed_files:
                common_files = set(code_files.keys()) & set(reviewed_files)
                if len(code_files) > 0:
                    coverage = len(common_files) / len(code_files)
                    alignment_score += coverage * 0.5
                    alignment_details.append(f"Quality review covers {len(common_files)}/{len(code_files)} files")
            
            # Check quality score
            quality_score = quality_feedback.get('quality_score', 0)
            if quality_score > 0:
                alignment_score += min(quality_score / 5.0, 0.5)  # Normalize to 0.5 max
                alignment_details.append(f"Quality score: {quality_score}")
            
            # Check for specific feedback
            if quality_feedback.get('suggestions') or quality_feedback.get('issues'):
                alignment_score += 0.2
                alignment_details.append("Specific feedback provided")
            
            return {
                'valid': alignment_score >= self.enhancement_config.get('cross_validation_threshold', 0.7),
                'score': alignment_score,
                'details': alignment_details,
                'timestamp': time.time()
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': str(e),
                'timestamp': time.time()
            }
    
    def _validate_plan_execution_alignment(self, plan_result: Dict, phase_result: Dict) -> Dict[str, Any]:
        """Validate alignment between implementation plan and phase execution."""
        try:
            plan = plan_result.get('implementation_plan', {})
            current_phase = phase_result.get('current_phase_name', '')
            
            alignment_score = 0.0
            alignment_details = []
            
            # Check if current phase matches planned phases
            planned_phases = plan.get('phases', [])
            if isinstance(planned_phases, list):
                phase_names = [str(phase).lower() for phase in planned_phases]
                if current_phase.lower() in phase_names:
                    alignment_score += 0.5
                    alignment_details.append(f"Current phase '{current_phase}' matches plan")
                else:
                    alignment_details.append(f"Current phase '{current_phase}' not in planned phases")
            
            # Check if execution follows planned order
            current_phase_index = phase_result.get('current_phase_index', 0)
            if current_phase_index < len(planned_phases):
                alignment_score += 0.3
                alignment_details.append("Phase execution within planned range")
            
            # Check if timeline is reasonable
            if plan.get('timeline') and phase_result.get('phase_start_time'):
                alignment_score += 0.2
                alignment_details.append("Timeline tracking active")
            
            return {
                'valid': alignment_score >= self.enhancement_config.get('cross_validation_threshold', 0.7),
                'score': alignment_score,
                'details': alignment_details,
                'timestamp': time.time()
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': str(e),
                'timestamp': time.time()
            }
    
    def get_communication_summary(self) -> Dict[str, Any]:
        """Get comprehensive communication summary."""
        if self.a2a_manager:
            return self.a2a_manager.get_communication_summary()
        return {}


# ==================== Factory Functions ====================

def create_enhanced_workflow(workflow_type: str = "phased", 
                           enhancement_config: Dict[str, Any] = None) -> StateGraph:
    """Factory function to create enhanced workflows."""
    
    builder = EnhancedWorkflowBuilder()
    
    if enhancement_config:
        builder.configure_enhancements(enhancement_config)
    
    if workflow_type == "phased":
        return builder.create_enhanced_phased_workflow()
    else:
        # Fallback to enhancing existing workflow
        from graph import get_workflow
        base_workflow = get_workflow(workflow_type)
        return enhance_existing_workflow(base_workflow, enhancement_config)


def get_default_enhancement_config() -> Dict[str, Any]:
    """Get default enhancement configuration."""
    return {
        'enable_cross_validation': True,
        'enable_smart_routing': True,
        'enable_context_sharing': True,
        'enable_error_recovery': True,
        'enable_concurrent_validation': False,
        'max_retries_per_agent': 3,
        'cross_validation_threshold': 0.7,
        'timeout_seconds': 300,
        'log_level': 'INFO'
    }


def get_conservative_enhancement_config() -> Dict[str, Any]:
    """Get conservative enhancement configuration for production."""
    return {
        'enable_cross_validation': True,
        'enable_smart_routing': False,  # Conservative
        'enable_context_sharing': True,
        'enable_error_recovery': True,
        'enable_concurrent_validation': False,
        'max_retries_per_agent': 2,  # Conservative
        'cross_validation_threshold': 0.6,  # Lower threshold
        'timeout_seconds': 180,
        'log_level': 'WARNING'
    }


def get_aggressive_enhancement_config() -> Dict[str, Any]:
    """Get aggressive enhancement configuration for development/testing."""
    return {
        'enable_cross_validation': True,
        'enable_smart_routing': True,
        'enable_context_sharing': True,
        'enable_error_recovery': True,
        'enable_concurrent_validation': True,  # Aggressive
        'max_retries_per_agent': 5,  # More retries
        'cross_validation_threshold': 0.8,  # Higher standards
        'timeout_seconds': 600,
        'log_level': 'DEBUG'
    }
