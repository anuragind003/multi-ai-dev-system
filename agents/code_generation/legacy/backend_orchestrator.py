"""
Backend Orchestrator Agent - LLM-Powered with Specialized Agent Coordination
Coordinates specialized agents to generate industry-grade backends with cost optimization.
"""

import json
import os
import time
import asyncio
from typing import Dict, Any, List, Optional, Set
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed

from langchain_core.language_models import BaseLanguageModel
from langchain_core.retrievers import BaseRetriever
from langchain_core.prompts import ChatPromptTemplate

from agents.code_generation.base_code_generator import BaseCodeGeneratorAgent
from agents.code_generation.specialized.core_backend_agent import CoreBackendAgent
from agents.code_generation.specialized.devops_infrastructure_agent import DevOpsInfrastructureAgent
from agents.code_generation.specialized.security_compliance_agent import SecurityComplianceAgent
from agents.code_generation.specialized.documentation_agent import DocumentationAgent
from agents.code_generation.specialized.monitoring_observability_agent import MonitoringObservabilityAgent
from agents.code_generation.specialized.testing_qa_agent import TestingQAAgent
from tools.code_execution_tool import CodeExecutionTool
from message_bus import MessageBus
from models.data_contracts import WorkItem, CodeGenerationOutput, GeneratedFile

import logging
logger = logging.getLogger(__name__)

class ProductionScale(Enum):
    """Production scale levels for backend generation"""
    STARTUP = "startup"
    ENTERPRISE = "enterprise" 
    HYPERSCALE = "hyperscale"

@dataclass
class BackendSpec:
    """Dynamic specification for backend generation"""
    domain: str
    scale: ProductionScale
    language: str
    framework: str
    features: Set[str]
    compliance_requirements: List[str]
    security_level: str
    performance_requirements: Dict[str, Any]

@dataclass
class CostOptimizationConfig:
    """Configuration for API cost optimization"""
    max_parallel_agents: int = 3
    batch_size: int = 5
    token_budget_per_agent: int = 4000
    enable_caching: bool = True
    prioritize_core_components: bool = True

class BackendOrchestratorAgent(BaseCodeGeneratorAgent):
    """
    Enhanced Backend Orchestrator Agent with Specialized Agent Coordination
    
    Features:
    - Delegates to specialized agents for modular generation
    - Implements cost optimization through batching and parallel processing
    - Provides intelligent coordination between agents
    - Maintains industrial-grade backend quality
    """
    
    def __init__(self, 
                 llm: BaseLanguageModel, 
                 memory, 
                 temperature: float,
                 output_dir: str, 
                 code_execution_tool: CodeExecutionTool,
                 rag_retriever: Optional[BaseRetriever] = None,
                 message_bus: Optional[MessageBus] = None,
                 cost_optimization: Optional[CostOptimizationConfig] = None):
        """Initialize Enhanced Backend Orchestrator with specialized agents."""
        
        super().__init__(
            llm=llm,
            memory=memory,
            agent_name="Backend Orchestrator Agent",
            temperature=temperature,
            output_dir=output_dir,
            code_execution_tool=code_execution_tool,
            rag_retriever=rag_retriever,
            message_bus=message_bus
        )
        
        # Cost optimization configuration
        self.cost_config = cost_optimization or CostOptimizationConfig()
        
        # Initialize specialized agents
        self._initialize_specialized_agents()
        
        # Token usage tracking
        self.token_usage = {
            "total_tokens": 0,
            "agent_breakdown": {},
            "cost_savings": {
                "parallel_processing": 0,
                "batching": 0,
                "caching": 0
            }
        }
        
        logger.info("Enhanced Backend Orchestrator initialized with specialized agents and cost optimization")
    
    async def arun(self, **kwargs) -> CodeGenerationOutput:
        """Async version of run method."""
        # Delegate to synchronous run method using asyncio.to_thread
        return await asyncio.to_thread(self.run, **kwargs)
    
    def _initialize_specialized_agents(self):
        """Initialize all specialized agents for backend generation."""
        
        # Core Backend Agent - Most important, highest priority
        self.core_agent = CoreBackendAgent(
            llm=self.llm,
            memory=self.memory,
            temperature=self.default_temperature,
            output_dir=self.output_dir,
            code_execution_tool=self.code_execution_tool,
            rag_retriever=self.rag_retriever,
            message_bus=self.message_bus
        )
        
        # DevOps Infrastructure Agent - High priority for production
        self.devops_agent = DevOpsInfrastructureAgent(
            llm=self.llm,
            memory=self.memory,
            temperature=self.default_temperature,
            output_dir=self.output_dir,
            code_execution_tool=self.code_execution_tool,
            rag_retriever=self.rag_retriever,
            message_bus=self.message_bus
        )
        
        # Security Compliance Agent - Critical for enterprise
        self.security_agent = SecurityComplianceAgent(
            llm=self.llm,
            memory=self.memory,
            temperature=self.default_temperature,
            output_dir=self.output_dir,
            code_execution_tool=self.code_execution_tool,
            rag_retriever=self.rag_retriever,
            message_bus=self.message_bus
        )
        
        # Documentation Agent - Important for maintainability
        self.documentation_agent = DocumentationAgent(
            llm=self.llm,
            memory=self.memory,
            temperature=self.default_temperature,
            output_dir=self.output_dir,
            code_execution_tool=self.code_execution_tool,
            rag_retriever=self.rag_retriever,
            message_bus=self.message_bus
        )
        
        # Monitoring Agent - Important for production
        self.monitoring_agent = MonitoringObservabilityAgent(
            llm=self.llm,
            memory=self.memory,
            temperature=self.default_temperature,
            output_dir=self.output_dir,
            code_execution_tool=self.code_execution_tool,
            rag_retriever=self.rag_retriever,
            message_bus=self.message_bus
        )
        
        # Testing Agent - Important for quality
        self.testing_agent = TestingQAAgent(
            llm=self.llm,
            memory=self.memory,
            temperature=self.default_temperature,
            output_dir=self.output_dir,
            code_execution_tool=self.code_execution_tool,
            rag_retriever=self.rag_retriever,
            message_bus=self.message_bus
        )
    
    def run(self, work_item: WorkItem, state: Dict[str, Any]) -> CodeGenerationOutput:
        """
        Executes a single work item by delegating to core and testing agents.

        This method adapts the orchestrator to the new WorkItem-based workflow.
        """
        logger.info(f"Backend Orchestrator starting work item: {work_item.id} - {work_item.description}")

        # 1. Generate the core implementation code
        logger.info(f"[{work_item.id}] Delegating implementation to CoreBackendAgent...")
        # CoreBackendAgent.run() now uses standard signature: work_item, state
        core_output = self.core_agent.run(work_item, state)
        
        # 2. Generate the unit tests for the implementation
        logger.info(f"[{work_item.id}] Delegating testing to TestingQAAgent...")
        # Update state with generated code for testing agent
        updated_state = state.copy()
        updated_state["code_generation_result"] = {"generated_files": core_output.generated_files}

        # TestingQAAgent.run() now uses standard signature: work_item, state
        testing_output = self.testing_agent.run(work_item, updated_state)

        # 3. Combine the results
        combined_files = core_output.generated_files + testing_output.generated_files
        
        logger.info(f"[{work_item.id}] Completed. Generated {len(core_output.generated_files)} implementation files and {len(testing_output.generated_files)} test files.")

        return CodeGenerationOutput(
            generated_files=combined_files,
            summary=f"Completed work item {work_item.id}. Generated {len(combined_files)} total files (implementation and tests)."
        )

    # All of the old complex orchestrator logic below can now be removed or deprecated,
    # as the new workflow graph handles the high-level planning. The methods _create_dynamic_specification,
    # _determine_scale_intelligently, etc., are no longer needed. I am leaving them here
    # for now but they are not called from the new `run` method.
    
    def generate_backend(self, 
                        tech_stack: Dict[str, Any], 
                        system_design: Dict[str, Any], 
                        requirements_analysis: Dict[str, Any],
                        **kwargs) -> Dict[str, Any]:
        """
        Generate comprehensive backend using specialized agents with cost optimization.
        """
        start_time = time.time()
        
        try:
            logger.info(" Starting Enhanced Backend Generation with Specialized Agents")
            
            # Phase 1: Create Dynamic Backend Specification
            spec = self._create_dynamic_specification(
                tech_stack, system_design, requirements_analysis, **kwargs
            )
            
            # Phase 2: Plan Agent Coordination with Cost Optimization
            agent_plan = self._create_cost_optimized_agent_plan(spec)
            
            # Phase 3: Execute Agents in Optimized Batches
            all_files = []
            total_tokens_used = 0
            
            for batch in agent_plan["batches"]:
                batch_files, batch_tokens = self._execute_agent_batch(batch, spec)
                all_files.extend(batch_files)
                total_tokens_used += batch_tokens
                
                # Log progress and cost tracking
                logger.info(f" Completed batch: {batch['name']} - Files: {len(batch_files)}, Tokens: {batch_tokens}")
            
            # Phase 4: Consolidate and Organize Results
            organized_output = self._organize_industrial_structure(all_files, spec)
            
            execution_time = time.time() - start_time
            
            # Calculate cost savings
            cost_savings = self._calculate_cost_savings(total_tokens_used, len(agent_plan["batches"]))
            
            result = {
                "status": "success",
                "execution_time": execution_time,
                "files": organized_output["files"],
                "backend_specification": {
                    "domain": spec.domain,
                    "scale": spec.scale.value,
                    "language": spec.language,
                    "framework": spec.framework,
                    "features": list(spec.features),
                    "security_level": spec.security_level,
                    "compliance": spec.compliance_requirements,
                    "performance_requirements": spec.performance_requirements
                },
                "cost_optimization": {
                    "total_tokens_used": total_tokens_used,
                    "parallel_batches": len(agent_plan["batches"]),
                    "agents_used": len([agent for batch in agent_plan["batches"] for agent in batch["agents"]]),
                    "estimated_cost_savings": cost_savings,
                    "optimization_strategy": "specialized_agent_coordination"
                },
                "summary": {
                    "total_files": len(organized_output["files"]),
                    "core_files": len([f for f in organized_output["files"] if "/core/" in f.get("path", "")]),
                    "infrastructure_files": len([f for f in organized_output["files"] if "/infrastructure/" in f.get("path", "")]),
                    "security_files": len([f for f in organized_output["files"] if "/security/" in f.get("path", "")]),
                    "documentation_files": len([f for f in organized_output["files"] if "/docs/" in f.get("path", "")]),
                    "generation_method": "specialized_agent_coordination",
                    "quality_level": "industrial_grade"
                }
            }
            
            # CRITICAL: Save files to disk (this was missing!)
            files_to_save = organized_output["files"]
            if files_to_save:
                logger.info(f"Saving {len(files_to_save)} backend files to disk at: {self.output_dir}")
                
                # Convert file format if needed for _save_files method
                formatted_files = []
                for file_item in files_to_save:
                    if isinstance(file_item, dict):
                        # Convert dict to object-like structure for _save_files
                        from models.data_contracts import GeneratedFile
                        try:
                            formatted_files.append(GeneratedFile(
                                file_path=file_item.get('path', file_item.get('file_path', 'unknown.py')),
                                content=file_item.get('content', file_item.get('code', ''))
                            ))
                        except Exception as e:
                            logger.warning(f"Failed to format file {file_item.get('path', 'unknown')}: {e}")
                    else:
                        formatted_files.append(file_item)
                
                self._save_files(formatted_files)
            else:
                logger.warning("No files to save to disk")
            
            logger.info(f" Backend generation completed successfully in {execution_time:.2f}s")
            logger.info(f" Cost optimization saved approximately {cost_savings['percentage']:.1f}% in API costs")
            
            return result
            
        except Exception as e:
            logger.error(f" Backend generation failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "execution_time": time.time() - start_time,
                "files": []
            }
    
    def _create_dynamic_specification(self, 
                                    tech_stack: Dict[str, Any],
                                    system_design: Dict[str, Any], 
                                    requirements_analysis: Dict[str, Any],
                                    **kwargs) -> BackendSpec:
        """Create dynamic backend specification based on analysis."""
        
        # Extract information intelligently
        domain = self._extract_domain_intelligently(requirements_analysis, system_design)
        language = tech_stack.get("backend", {}).get("language", "Python")
        framework = tech_stack.get("backend", {}).get("framework", "FastAPI")
        
        # Determine scale and features intelligently
        scale = self._determine_scale_intelligently(requirements_analysis, system_design)
        features = self._extract_features_intelligently(tech_stack, system_design, requirements_analysis)
        
        # Extract requirements
        security_level = self._determine_security_level_intelligently(domain, requirements_analysis)
        compliance_requirements = self._extract_compliance_intelligently(domain, requirements_analysis)
        performance_requirements = self._extract_performance_requirements_intelligently(requirements_analysis, scale)
        
        return BackendSpec(
            domain=domain,
            scale=scale,
            language=language,
            framework=framework,
            features=features,
            compliance_requirements=compliance_requirements,
            security_level=security_level,
            performance_requirements=performance_requirements
        )
    
    def _determine_scale_intelligently(self, requirements_analysis: Dict, system_design: Dict) -> ProductionScale:
        """Determine scale based on performance requirements and system design."""
        performance = requirements_analysis.get("extracted_requirements", {}).get("non_functional_requirements", {})
        
        # Look for scale indicators
        concurrent_users = 0
        for req in performance:
            if "concurrent users" in req.lower():
                try:
                    num_str = ''.join(filter(str.isdigit, req))
                    concurrent_users = int(num_str) if num_str else 0
                    break
                except ValueError:
                    pass

        if concurrent_users > 100000:
            return ProductionScale.HYPERSCALE
        elif concurrent_users > 10000:
            return ProductionScale.ENTERPRISE
        else:
            return ProductionScale.STARTUP
    
    def _extract_features_intelligently(self, tech_stack: Dict, system_design: Dict, requirements_analysis: Dict) -> Set[str]:
        """Extract required features based on requirements and design."""
        features = set()
        
        # Base features
        features.update(["api", "database", "logging", "error_handling", "validation"])
        
        # Add features based on functional requirements
        functional_reqs = str(requirements_analysis.get("extracted_requirements", {}).get("functional_requirements", [])).lower()
        
        if "user registration" in functional_reqs or "authentication" in functional_reqs:
            features.add("authentication")
        if "product catalog" in functional_reqs or "inventory management" in functional_reqs:
            features.add("product_management")
        if "shopping cart" in functional_reqs or "checkout process" in functional_reqs:
            features.add("cart_and_checkout")
        if "order management" in functional_reqs:
            features.add("order_management")
        if "payment processing" in functional_reqs:
            features.add("payment_processing")
        if "user profile" in functional_reqs:
            features.add("user_profile")
        if "reviews and ratings" in functional_reqs:
            features.add("reviews_and_ratings")

        # Add features based on non-functional requirements
        non_functional_reqs = str(requirements_analysis.get("extracted_requirements", {}).get("non_functional_requirements", [])).lower()
        if "gdpr compliance" in non_functional_reqs:
            features.add("gdpr_compliance")
        if "pci dss compliance" in non_functional_reqs:
            features.add("pci_dss_compliance")
        if "99.9% system availability" in non_functional_reqs or "response time under" in non_functional_reqs:
            features.add("performance_monitoring")
        if "mobile responsive design" in non_functional_reqs:
            features.add("responsive_ui")
        
        # Add features based on business requirements
        business_reqs = str(requirements_analysis.get("extracted_requirements", {}).get("business_requirements", [])).lower()
        if "multi-vendor marketplace" in business_reqs:
            features.add("multi_vendor")
        if "analytics and reporting" in business_reqs:
            features.add("analytics_and_reporting")
        
        return features
    
    # Required methods for base class compatibility
    def _determine_security_level_intelligently(self, domain: str, requirements: Dict) -> str:
        """Determine security level based on domain and requirements."""
        high_security_domains = ["Healthcare", "Financial", "Government"]
        if domain in high_security_domains:
            return "high"
        return "medium"
    
    def _extract_compliance_intelligently(self, domain: str, requirements: Dict) -> List[str]:
        """Extract compliance requirements based on domain."""
        compliance_map = {
            "Healthcare": ["HIPAA", "HITECH"],
            "Financial": ["SOX", "PCI-DSS", "GDPR"],
            "E-commerce": ["GDPR", "CCPA"]
        }
        extracted_reqs = requirements.get("extracted_requirements", {}).get("non_functional_requirements", [])
        
        # Extract compliance from requirements analysis
        found_compliance = []
        for req in extracted_reqs:
            if "gdpr" in req.lower():
                found_compliance.append("GDPR")
            if "hipaa" in req.lower():
                found_compliance.append("HIPAA")
            if "pci dss" in req.lower():
                found_compliance.append("PCI-DSS")
            if "sox" in req.lower():
                found_compliance.append("SOX")
        
        # Combine with domain-based
        domain_compliance = compliance_map.get(domain, [])
        return list(set(found_compliance + domain_compliance))
    
    def _extract_performance_requirements_intelligently(self, requirements: Dict, scale: ProductionScale) -> Dict[str, Any]:
        """Extract performance requirements based on scale."""
        base_reqs = {
            "response_time": "200ms",
            "throughput": "1000 rps", 
            "availability": "99.9%"
        }
        
        if scale == ProductionScale.HYPERSCALE:
            base_reqs.update({
                "response_time": "50ms",
                "throughput": "10000 rps",
                "availability": "99.99%"
            })
        elif scale == ProductionScale.ENTERPRISE:
            base_reqs.update({
                "response_time": "100ms", 
                "throughput": "5000 rps",
                "availability": "99.95%"
            })
        
        return base_reqs
    
    def _generate_code(self, llm, invoke_config: Dict, **kwargs) -> Dict[str, Any]:
        """Implementation of the abstract method from base class."""
        return self.generate_backend(**kwargs) 