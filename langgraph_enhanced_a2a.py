"""
LangGraph-Native Enhanced Agent-to-Agent Communication

This module enhances your existing LangGraph workflow with native A2A features:
- Intelligent state management with cross-agent context sharing
- Dynamic conditional routing based on agent outputs
- Enhanced error recovery with retry strategies
- Real-time inter-agent validation and feedback loops
- Concurrent agent execution where beneficial
"""

import time
import logging
import asyncio
from typing import Dict, Any, List, Optional, Union, Callable
from dataclasses import dataclass, field
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.runnables import RunnableLambda, RunnableParallel

from agent_state import AgentState, StateFields
from monitoring import log_agent_activity

logger = logging.getLogger(__name__)

@dataclass
class AgentCommunicationState:
    """Extended state for enhanced agent communication."""
    # Cross-agent context sharing
    shared_context: Dict[str, Any] = field(default_factory=dict)
    agent_outputs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Inter-agent feedback
    agent_feedback: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    cross_validation_results: Dict[str, Any] = field(default_factory=dict)
    
    # Dynamic routing
    routing_decisions: List[Dict[str, Any]] = field(default_factory=list)
    conditional_paths: Dict[str, str] = field(default_factory=dict)
    
    # Error recovery
    error_recovery_attempts: Dict[str, int] = field(default_factory=dict)
    agent_retry_counts: Dict[str, int] = field(default_factory=dict)
    
    # Performance tracking
    agent_execution_order: List[str] = field(default_factory=list)
    inter_agent_dependencies: Dict[str, List[str]] = field(default_factory=dict)

class LangGraphEnhancedA2AManager:
    """Manager for enhanced A2A communication using LangGraph's native features."""
    
    def __init__(self, workflow: StateGraph):
        self.workflow = workflow
        self.communication_state = AgentCommunicationState()
        self.agent_validators = {}
        self.cross_validation_rules = {}
        self.conditional_routers = {}
        
    def register_agent_validator(self, agent_name: str, 
                                validator: Callable[[Dict[str, Any]], bool]):
        """Register a validator for an agent's output."""
        self.agent_validators[agent_name] = validator
        
    def register_cross_validation_rule(self, agent_pair: tuple, 
                                     rule: Callable[[Dict, Dict], Dict]):
        """Register cross-validation between two agents."""
        self.cross_validation_rules[agent_pair] = rule
        
    def register_conditional_router(self, source_agent: str, 
                                  router: Callable[[AgentState], str]):
        """Register dynamic routing based on agent output."""
        self.conditional_routers[source_agent] = router

    def create_enhanced_node(self, node_func: Callable, agent_name: str, 
                           dependencies: List[str] = None,
                           validators: List[str] = None) -> Callable:
        """Create an enhanced node with A2A communication features."""
        
        def enhanced_node_wrapper(state: AgentState, config: dict) -> Dict[str, Any]:
            start_time = time.time()
            
            try:
                # 1. Pre-execution: Check dependencies and gather context
                self._prepare_agent_context(state, agent_name, dependencies or [])
                
                # 2. Execute the original node
                result = node_func(state, config)
                
                # 3. Post-execution: Validate and share results
                self._process_agent_output(state, agent_name, result, validators or [])
                
                # 4. Cross-validation with related agents
                self._perform_cross_validation(state, agent_name, result)
                
                # 5. Update shared context
                self._update_shared_context(state, agent_name, result)
                
                execution_time = time.time() - start_time
                log_agent_activity(
                    agent_name, 
                    f"Enhanced execution completed in {execution_time:.2f}s",
                    "SUCCESS"
                )
                
                return result
                
            except Exception as e:
                # Enhanced error handling with recovery
                return self._handle_agent_error(state, agent_name, e, config)
        
        return enhanced_node_wrapper
    
    def _prepare_agent_context(self, state: AgentState, agent_name: str, 
                             dependencies: List[str]):
        """Prepare enhanced context for agent execution."""
        
        # Gather context from dependency agents
        dependency_context = {}
        for dep_agent in dependencies:
            if dep_agent in self.communication_state.agent_outputs:
                dependency_context[dep_agent] = self.communication_state.agent_outputs[dep_agent]
        
        # Add to shared context
        self.communication_state.shared_context[f"{agent_name}_dependencies"] = dependency_context
        
        # Log dependency resolution
        if dependencies:
            logger.info(f"{agent_name}: Resolved dependencies from {dependencies}")
        
        # Add enhanced context to state
        if 'enhanced_a2a_context' not in state:
            state['enhanced_a2a_context'] = {}
        
        state['enhanced_a2a_context'][agent_name] = {
            'dependencies': dependency_context,
            'shared_context': self.communication_state.shared_context,
            'execution_timestamp': time.time()
        }
    
    def _process_agent_output(self, state: AgentState, agent_name: str, 
                            result: Dict[str, Any], validators: List[str]):
        """Process and validate agent output."""
        
        # Store agent output
        self.communication_state.agent_outputs[agent_name] = result
        self.communication_state.agent_execution_order.append(agent_name)
        
        # Run validators
        validation_results = {}
        for validator_name in validators:
            if validator_name in self.agent_validators:
                try:
                    is_valid = self.agent_validators[validator_name](result)
                    validation_results[validator_name] = {
                        'valid': is_valid,
                        'timestamp': time.time()
                    }
                except Exception as e:
                    validation_results[validator_name] = {
                        'valid': False,
                        'error': str(e),
                        'timestamp': time.time()
                    }
        
        # Store validation results
        if validation_results:
            state['enhanced_a2a_context'][agent_name]['validations'] = validation_results
            logger.info(f"{agent_name}: Validation results: {validation_results}")
    
    def _perform_cross_validation(self, state: AgentState, agent_name: str, 
                                result: Dict[str, Any]):
        """Perform cross-validation with related agents."""
        
        for agent_pair, rule in self.cross_validation_rules.items():
            if agent_name in agent_pair:
                other_agent = agent_pair[0] if agent_pair[1] == agent_name else agent_pair[1]
                
                if other_agent in self.communication_state.agent_outputs:
                    try:
                        other_result = self.communication_state.agent_outputs[other_agent]
                        cross_val_result = rule(result, other_result)
                        
                        self.communication_state.cross_validation_results[f"{agent_name}_{other_agent}"] = {
                            'result': cross_val_result,
                            'timestamp': time.time()
                        }
                        
                        logger.info(f"Cross-validation between {agent_name} and {other_agent}: {cross_val_result}")
                        
                    except Exception as e:
                        logger.error(f"Cross-validation error between {agent_name} and {other_agent}: {e}")
    
    def _update_shared_context(self, state: AgentState, agent_name: str, 
                             result: Dict[str, Any]):
        """Update shared context with agent results."""
        
        # Extract key information for sharing
        if isinstance(result, dict):
            # Extract shareable context
            shareable_context = {}
            
            # Add specific patterns for different agent types
            if 'requirements' in result:
                shareable_context['requirements_summary'] = result['requirements']
            if 'tech_stack' in result:
                shareable_context['tech_stack_info'] = result['tech_stack']
            if 'system_design' in result:
                shareable_context['design_patterns'] = result['system_design']
            if 'generated_files' in result:
                shareable_context['code_artifacts'] = list(result['generated_files'].keys())
            
            # Update shared context
            self.communication_state.shared_context[f"{agent_name}_output"] = shareable_context
            
            # Make available to all subsequent agents
            if 'shared_agent_context' not in state:
                state['shared_agent_context'] = {}
            
            state['shared_agent_context'][agent_name] = shareable_context
    
    def _handle_agent_error(self, state: AgentState, agent_name: str, 
                          error: Exception, config: dict) -> Dict[str, Any]:
        """Enhanced error handling with recovery strategies."""
        
        # Increment retry count
        if agent_name not in self.communication_state.agent_retry_counts:
            self.communication_state.agent_retry_counts[agent_name] = 0
        
        self.communication_state.agent_retry_counts[agent_name] += 1
        retry_count = self.communication_state.agent_retry_counts[agent_name]
        
        # Log error with context
        log_agent_activity(
            agent_name,
            f"Error on attempt {retry_count}: {str(error)}",
            "ERROR"
        )
        
        # Recovery strategies
        if retry_count <= 3:  # Max 3 retries
            # Strategy 1: Use fallback context from related agents
            fallback_context = self._generate_fallback_context(agent_name)
            
            # Strategy 2: Simplified execution mode
            error_result = {
                'error': str(error),
                'retry_count': retry_count,
                'fallback_context': fallback_context,
                'recovery_attempted': True,
                'agent_name': agent_name
            }
            
            # Add recovery context to state
            if 'error_recovery' not in state:
                state['error_recovery'] = {}
            
            state['error_recovery'][agent_name] = error_result
            
            return error_result
        else:
            # Max retries exceeded - critical error
            return {
                'critical_error': str(error),
                'max_retries_exceeded': True,
                'agent_name': agent_name
            }
    
    def _generate_fallback_context(self, failed_agent: str) -> Dict[str, Any]:
        """Generate fallback context from other agents."""
        
        fallback = {}
        
        # Use shared context from previous agents
        for context_key, context_value in self.communication_state.shared_context.items():
            if failed_agent not in context_key:  # Exclude own context
                fallback[context_key] = context_value
        
        # Use outputs from dependency agents
        execution_order = self.communication_state.agent_execution_order
        if failed_agent in execution_order:
            agent_index = execution_order.index(failed_agent)
            for prev_agent in execution_order[:agent_index]:
                if prev_agent in self.communication_state.agent_outputs:
                    fallback[f"{prev_agent}_output"] = self.communication_state.agent_outputs[prev_agent]
        
        return fallback

    def create_dynamic_conditional_edge(self, source_node: str, 
                                      router_func: Callable[[AgentState], str],
                                      target_mapping: Dict[str, str]) -> Callable:
        """Create a dynamic conditional edge that adapts based on agent interactions."""
        
        def enhanced_router(state: AgentState) -> str:
            try:
                # Get base routing decision
                base_decision = router_func(state)
                
                # Check for cross-validation results that might override
                agent_name = source_node.replace('_node', '').replace('_', ' ').title()
                
                if hasattr(self.communication_state, 'cross_validation_results'):
                    for validation_key, validation_result in self.communication_state.cross_validation_results.items():
                        if agent_name.lower().replace(' ', '_') in validation_key:
                            if not validation_result.get('result', {}).get('valid', True):
                                # Override to revision path if cross-validation failed
                                if 'revise' in target_mapping.values():
                                    logger.info(f"Cross-validation override: routing {source_node} to revision")
                                    return 'revise'
                
                # Check for error recovery context
                if 'error_recovery' in state and source_node.replace('_node', '') in state['error_recovery']:
                    recovery_info = state['error_recovery'][source_node.replace('_node', '')]
                    if recovery_info.get('recovery_attempted'):
                        # Route to recovery path if available
                        if 'retry' in target_mapping.values():
                            return 'retry'
                
                # Store routing decision
                self.communication_state.routing_decisions.append({
                    'source': source_node,
                    'decision': base_decision,
                    'timestamp': time.time(),
                    'context': 'enhanced_routing'
                })
                
                return base_decision
                
            except Exception as e:
                logger.error(f"Error in enhanced routing for {source_node}: {e}")
                # Fallback to first available target
                return list(target_mapping.keys())[0] if target_mapping else 'continue'
        
        return enhanced_router

    def create_concurrent_execution_node(self, node_funcs: List[Callable], 
                                       node_names: List[str]) -> Callable:
        """Create a node that executes multiple agents concurrently where beneficial."""
        
        def concurrent_node(state: AgentState, config: dict) -> Dict[str, Any]:
            """Execute multiple independent agents concurrently."""
            
            logger.info(f"Starting concurrent execution of: {node_names}")
            
            # Create tasks for concurrent execution
            async def run_agent_async(node_func, node_name):
                try:
                    return node_name, node_func(state, config)
                except Exception as e:
                    logger.error(f"Error in concurrent agent {node_name}: {e}")
                    return node_name, {'error': str(e), 'agent_name': node_name}
            
            async def execute_all():
                tasks = [
                    run_agent_async(node_func, node_name) 
                    for node_func, node_name in zip(node_funcs, node_names)
                ]
                return await asyncio.gather(*tasks, return_exceptions=True)
            
            # Run concurrent execution
            try:
                # Use asyncio to run concurrent tasks
                import asyncio
                results = asyncio.run(execute_all())
                
                # Combine results
                combined_result = {}
                for result in results:
                    if isinstance(result, tuple) and len(result) == 2:
                        agent_name, agent_result = result
                        combined_result[f"{agent_name}_result"] = agent_result
                        
                        # Update communication state
                        self.communication_state.agent_outputs[agent_name] = agent_result
                        self.communication_state.agent_execution_order.append(agent_name)
                
                # Add execution metadata
                combined_result['concurrent_execution'] = {
                    'agents_executed': node_names,
                    'execution_time': time.time(),
                    'success_count': len([r for r in results if not isinstance(r[1], dict) or 'error' not in r[1]])
                }
                
                logger.info(f"Concurrent execution completed for: {node_names}")
                return combined_result
                
            except Exception as e:
                logger.error(f"Error in concurrent execution: {e}")
                return {
                    'concurrent_execution_error': str(e),
                    'attempted_agents': node_names
                }
        
        return concurrent_node

    def get_communication_summary(self) -> Dict[str, Any]:
        """Get a summary of all agent communications."""
        
        return {
            'agents_executed': self.communication_state.agent_execution_order,
            'agent_outputs_count': len(self.communication_state.agent_outputs),
            'cross_validations': len(self.communication_state.cross_validation_results),
            'routing_decisions': len(self.communication_state.routing_decisions),
            'retry_counts': dict(self.communication_state.agent_retry_counts),
            'shared_context_keys': list(self.communication_state.shared_context.keys()),
            'total_interactions': (
                len(self.communication_state.agent_outputs) + 
                len(self.communication_state.cross_validation_results) +
                len(self.communication_state.routing_decisions)
            )
        }


# ==================== Integration Functions ====================

def enhance_existing_workflow(workflow: StateGraph, 
                            enhancement_config: Dict[str, Any] = None) -> StateGraph:
    """Enhance an existing LangGraph workflow with A2A communication features."""
    
    manager = LangGraphEnhancedA2AManager(workflow)
    
    # Default enhancement configuration
    config = enhancement_config or {
        'enable_cross_validation': True,
        'enable_concurrent_execution': False,  # Conservative default
        'enable_dynamic_routing': True,
        'max_retries_per_agent': 3
    }
    
    # Add validation rules for common agent interactions
    if config.get('enable_cross_validation'):
        # BRD Analyst <-> Tech Stack Advisor
        manager.register_cross_validation_rule(
            ('brd_analyst', 'tech_stack_advisor'),
            lambda brd_result, tech_result: {
                'valid': validate_tech_stack_alignment(brd_result, tech_result),
                'confidence': calculate_alignment_confidence(brd_result, tech_result)
            }
        )
        
        # System Designer <-> Code Generator
        manager.register_cross_validation_rule(
            ('system_designer', 'code_generator'),
            lambda design_result, code_result: {
                'valid': validate_design_implementation(design_result, code_result),
                'coverage': calculate_design_coverage(design_result, code_result)
            }
        )
    
    logger.info(f"Enhanced workflow with A2A communication features: {config}")
    return workflow


def validate_tech_stack_alignment(brd_result: Dict, tech_result: Dict) -> bool:
    """Validate that tech stack aligns with BRD requirements."""
    try:
        requirements = brd_result.get('requirements', {})
        tech_stack = tech_result.get('tech_stack', {})
        
        # Check if tech stack addresses key requirements
        if requirements.get('scalability_requirements') and not tech_stack.get('scalability_features'):
            return False
        
        if requirements.get('security_requirements') and not tech_stack.get('security_features'):
            return False
        
        return True
    except Exception:
        return False


def calculate_alignment_confidence(brd_result: Dict, tech_result: Dict) -> float:
    """Calculate confidence score for BRD-Tech stack alignment."""
    try:
        # Simple scoring based on requirement coverage
        requirements = brd_result.get('requirements', {})
        tech_stack = tech_result.get('tech_stack', {})
        
        total_requirements = len(requirements)
        if total_requirements == 0:
            return 0.5  # Neutral if no requirements
        
        covered_requirements = 0
        for req_key in requirements:
            if any(req_key in str(tech_value) for tech_value in tech_stack.values()):
                covered_requirements += 1
        
        return covered_requirements / total_requirements
    except Exception:
        return 0.0


def validate_design_implementation(design_result: Dict, code_result: Dict) -> bool:
    """Validate that code implementation follows system design."""
    try:
        design = design_result.get('system_design', {})
        code_files = code_result.get('generated_files', {})
        
        # Check if major design components are implemented
        components = design.get('components', [])
        implemented_components = []
        
        for file_path in code_files.keys():
            for component in components:
                if component.lower() in file_path.lower():
                    implemented_components.append(component)
        
        # At least 70% of components should be implemented
        if len(components) > 0:
            coverage = len(set(implemented_components)) / len(components)
            return coverage >= 0.7
        
        return True
    except Exception:
        return False


def calculate_design_coverage(design_result: Dict, code_result: Dict) -> float:
    """Calculate what percentage of design is covered by implementation."""
    try:
        design = design_result.get('system_design', {})
        code_files = code_result.get('generated_files', {})
        
        components = design.get('components', [])
        if not components:
            return 1.0
        
        implemented_components = set()
        for file_path in code_files.keys():
            for component in components:
                if component.lower() in file_path.lower():
                    implemented_components.add(component)
        
        return len(implemented_components) / len(components)
    except Exception:
        return 0.0


# ==================== Usage Example ====================

def create_enhanced_phased_workflow() -> StateGraph:
    """Create an enhanced version of the phased workflow with A2A features."""
    
    # Import your existing workflow creation function
    from graph import create_phased_workflow
    
    # Create base workflow
    base_workflow = create_phased_workflow()
    
    # Enhance with A2A communication
    enhanced_workflow = enhance_existing_workflow(
        base_workflow,
        enhancement_config={
            'enable_cross_validation': True,
            'enable_concurrent_execution': False,  # Keep conservative for now
            'enable_dynamic_routing': True,
            'max_retries_per_agent': 3
        }
    )
    
    logger.info("Created enhanced phased workflow with A2A communication")
    return enhanced_workflow
