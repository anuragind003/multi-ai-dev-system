"""
DevOps Infrastructure Agent - LLM-Powered Specialized Agent
Focuses on infrastructure and deployment using intelligent LLM reasoning with token optimization.
"""

import json
import os
import time
from typing import Dict, Any, List, Optional, Set
from pathlib import Path

from langchain_core.language_models import BaseLanguageModel
from langchain_core.retrievers import BaseRetriever
from langchain_core.prompts import ChatPromptTemplate

from agents.code_generation.base_code_generator import BaseCodeGeneratorAgent
from tools.code_execution_tool import CodeExecutionTool
from message_bus import MessageBus
from tools.code_generation_utils import parse_llm_output_into_files
from models.data_contracts import WorkItem, CodeGenerationOutput, GeneratedFile

import logging
logger = logging.getLogger(__name__)

class DevOpsInfrastructureAgent(BaseCodeGeneratorAgent):
    """
    LLM-Powered DevOps Infrastructure Agent - Specialized for deployment infrastructure
    
    Uses intelligent LLM generation with token optimization for:
    - Docker containerization (Dockerfile, docker-compose)
    - Kubernetes manifests (deployments, services, ingress)
    - CI/CD pipelines (GitHub Actions, GitLab CI)
    - Performance optimization (nginx, load balancers)
    - Infrastructure automation scripts
    """
    
    def __init__(self, 
                 llm: BaseLanguageModel, 
                 memory, 
                 temperature: float,
                 output_dir: str, 
                 code_execution_tool: CodeExecutionTool,
                 rag_retriever: Optional[BaseRetriever] = None,
                 message_bus: Optional[MessageBus] = None):
        """Initialize LLM-Powered DevOps Infrastructure Agent."""
        
        super().__init__(
            llm=llm,
            memory=memory,
            agent_name="DevOps Infrastructure Agent",
            temperature=temperature,
            output_dir=output_dir,
            code_execution_tool=code_execution_tool,
            rag_retriever=rag_retriever,
            message_bus=message_bus
        )
        
        # Token optimization settings
        self.max_tokens_per_batch = 4000
        self.max_files_per_batch = 3
        self.context_compression_ratio = 0.7
        
        self._initialize_devops_prompts()
        logger.info("LLM-Powered DevOps Infrastructure Agent initialized with token optimization")

    async def arun(self, **kwargs: Any) -> Any:
        """Asynchronous run method for the agent."""
        # This method can be implemented with asynchronous logic if needed.
        # For now, we'll delegate to the synchronous run method.
        import asyncio
        return await asyncio.to_thread(self.run, **kwargs)
    
    def _initialize_devops_prompts(self):
        """Initialize LLM prompt templates for DevOps infrastructure generation."""
        
        self.devops_generation_template = ChatPromptTemplate.from_messages([
            ("system",
             "You are an expert DevOps engineer specializing in CLOUD-NATIVE INFRASTRUCTURE "
             "and ENTERPRISE DEPLOYMENT. You generate production-ready, scalable infrastructure "
             "that follows industry best practices for security, performance, and reliability.\n\n"
             
             "**DEVOPS EXPERTISE:**\n"
             "- Container orchestration (Docker, Kubernetes)\n"
             "- CI/CD pipeline automation\n"
             "- Infrastructure as Code (Terraform, CloudFormation)\n"
             "- Cloud-native patterns (AWS, GCP, Azure)\n"
             "- Performance optimization and monitoring\n"
             "- Security and compliance automation\n"
             "- Disaster recovery and backup strategies\n\n"
             
             "**MANDATORY INFRASTRUCTURE COMPONENTS:**\n"
             "Generate ALL of the following infrastructure components:\n\n"
             
             "1. **CONTAINERIZATION:**\n"
             "   - Multi-stage Dockerfiles for optimization\n"
             "   - Docker Compose for local development\n"
             "   - Health checks and security hardening\n"
             "   - Resource limits and optimization\n"
             "   - Multi-architecture support\n\n"
             
             "2. **KUBERNETES ORCHESTRATION:**\n"
             "   - Production-ready deployments with rolling updates\n"
             "   - Service mesh integration (Istio, Linkerd)\n"
             "   - Horizontal Pod Autoscaling (HPA)\n"
             "   - Resource quotas and limits\n"
             "   - Ingress controllers and load balancing\n"
             "   - Persistent storage and stateful sets\n"
             "   - Security policies and RBAC\n\n"
             
             "3. **CI/CD AUTOMATION:**\n"
             "   - Multi-stage pipeline with testing\n"
             "   - Security scanning and vulnerability assessment\n"
             "   - Automated deployment with rollback\n"
             "   - Environment promotion strategies\n"
             "   - Infrastructure testing and validation\n"
             "   - Performance and load testing\n"
             "   - Compliance and audit automation\n\n"
             
             "4. **MONITORING & OBSERVABILITY:**\n"
             "   - Prometheus metrics collection\n"
             "   - Grafana dashboards and alerting\n"
             "   - Distributed tracing (Jaeger, Zipkin)\n"
             "   - Centralized logging (ELK stack)\n"
             "   - Application performance monitoring\n"
             "   - Infrastructure health checks\n"
             "   - Business metrics and SLIs/SLOs\n\n"
             
             "5. **SECURITY & COMPLIANCE:**\n"
             "   - Secrets management (HashiCorp Vault, AWS Secrets Manager)\n"
             "   - Network policies and security groups\n"
             "   - Container security scanning\n"
             "   - Compliance automation (SOX, HIPAA, PCI-DSS)\n"
             "   - Identity and access management\n"
             "   - Audit logging and monitoring\n\n"
             
             "**SCALE-SPECIFIC PATTERNS:**\n"
             "- Startup: Simple containerization, basic CI/CD, cost optimization\n"
             "- Enterprise: Multi-cluster, advanced monitoring, security hardening\n"
             "- Hyperscale: Auto-scaling, global distribution, performance optimization\n\n"
             
             "Generate enterprise-grade infrastructure that provides comprehensive "
             "deployment, monitoring, and operational excellence."),
            
            ("human",
             "Generate {component_type} infrastructure for a **{domain}** application "
             "using **{framework}** ({language}) at **{scale}** scale with "
             "**{deployment_targets}** deployment targets.\n\n"
             
             "**Project Context:**\n"
             "- Domain: {domain}\n"
             "- Language: {language}\n"
             "- Framework: {framework}\n"
             "- Scale: {scale}\n"
             "- Deployment Targets: {deployment_targets}\n"
             "- Features: {features}\n\n"
             
             "**COMPONENT SPECIFICATIONS:**\n"
             "{component_specifications}\n\n"
             
             "**SCALE REQUIREMENTS:**\n"
             "{scale_requirements}\n\n"
             
             "**DEPLOYMENT PATTERNS:**\n"
             "{deployment_patterns}\n\n"
             
             "**SECURITY & COMPLIANCE:**\n"
             "{security_requirements}\n\n"
             
             "Generate production-ready infrastructure files with comprehensive "
             "configuration, security hardening, and operational excellence. "
             "Include proper error handling, monitoring, and documentation.")
        ])
        
        # New prompt for generating scale-specific requirements
        self.scale_requirements_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert in defining infrastructure requirements based on production scale.
Your task is to describe the key infrastructure requirements for a given production scale.
Focus on aspects like environment setup, monitoring, security, disaster recovery, and distribution.
Output a concise, comma-separated string of requirements.
"""),
            ("human", """Describe the infrastructure requirements for a **{scale}** scale application.
Context:
- Domain: {domain}
- Language: {language}
- Framework: {framework}
- Features: {features}

Provide the infrastructure requirements.""")
        ])
        
        # New prompt for generating deployment patterns
        self.deployment_patterns_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert in defining deployment patterns for various targets.
Your task is to describe the key deployment patterns for the given deployment targets.
Focus on aspects like containerization, orchestration, and cloud-specific services.
Output a concise, comma-separated string of deployment patterns.
"""),
            ("human", """Describe the deployment patterns for an application targeting **{deployment_targets}**.
Context:
- Domain: {domain}
- Language: {language}
- Framework: {framework}
- Scale: {scale}
- Features: {features}

Provide the deployment patterns.""")
        ])
        
        # New prompt for generating security requirements
        self.security_requirements_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert in defining security and compliance requirements for software applications.
Your task is to describe the key security requirements for a given domain and production scale.
Focus on aspects like data protection, access control, compliance standards (e.g., HIPAA, GDPR, PCI-DSS), and common vulnerabilities.
Output a concise, comma-separated string of security requirements.
"""),
            ("human", """Describe the security requirements for a **{domain}** application at **{scale}** scale.
Context:
- Language: {language}
- Framework: {framework}
- Features: {features}
- Compliance Requirements: {compliance_requirements}

Provide the security requirements."""
            )
        ])
        
        # New prompt for generating CI/CD specifications
        self.cicd_specs_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert in defining CI/CD pipeline specifications.
Your task is to describe the key CI/CD specifications for an application based on its language, framework, and scale.
Focus on aspects like multi-stage pipelines, security scanning, automated deployment, environment promotion, infrastructure testing, performance testing, and compliance automation.
Output a concise, comma-separated string of specifications.
"""),
            ("human", """Describe the CI/CD specifications for a **{language}** application using **{framework}** at **{scale}** scale.

Provide the CI/CD specifications."""
            )
        ])
        
        # New prompt for generating monitoring specifications
        self.monitoring_specs_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert in defining monitoring and observability specifications.
Your task is to describe the key monitoring specifications for an application based on its domain and scale.
Focus on aspects like Prometheus metrics, Grafana dashboards and alerting, distributed tracing, centralized logging, application performance monitoring, infrastructure health checks, and business metrics/SLIs/SLOs.
Output a concise, comma-separated string of specifications.
"""),
            ("human", """Describe the monitoring specifications for a **{domain}** application at **{scale}** scale.

Provide the monitoring specifications."""
            )
        ])
    
    def generate_devops_infrastructure(self, 
                                     domain: str,
                                     language: str,
                                     framework: str,
                                     scale: str,
                                     deployment_targets: List[str],
                                     features: Set[str]) -> Dict[str, Any]:
        """Generate comprehensive DevOps infrastructure using LLM with token optimization."""
        
        start_time = time.time()
        
        try:
            logger.info(f"Generating LLM-powered DevOps infrastructure for {domain} ({scale} scale)")
            
            # Prepare intelligent context
            scale_requirements = self._get_scale_requirements(scale)
            deployment_patterns = self._get_deployment_patterns(deployment_targets)
            security_requirements = self._get_security_requirements(domain, scale)
            
            # Batch infrastructure components for token optimization
            infrastructure_components = self._create_infrastructure_batches(
                domain, language, framework, scale, deployment_targets, features
            )
            
            # Generate infrastructure in optimized batches
            all_files = []
            total_tokens_used = 0
            
            for batch in infrastructure_components:
                try:
                    batch_files, tokens_used = self._generate_infrastructure_batch(batch, {
                        "domain": domain,
                        "language": language,
                        "framework": framework,
                        "scale": scale,
                        "deployment_targets": ", ".join(deployment_targets),
                        "features": ", ".join(sorted(features)),
                        "scale_requirements": scale_requirements,
                        "deployment_patterns": deployment_patterns,
                        "security_requirements": security_requirements
                    })
                    
                    all_files.extend(batch_files)
                    total_tokens_used += tokens_used
                    
                except Exception as e:
                    logger.warning(f"Failed to generate batch {batch['name']}: {str(e)}")
            
            # Save files to output directory
            saved_files = []
            for file_info in all_files:
                file_path = os.path.join(self.output_dir, file_info["path"])
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(file_info["content"])
                
                saved_files.append({
                    "name": file_info["name"],
                    "path": file_info["path"],
                    "type": file_info.get("type", "infrastructure"),
                    "size": len(file_info["content"])
                })
            
            execution_time = time.time() - start_time
            
            logger.info(f"LLM-powered DevOps infrastructure generated: {len(saved_files)} files in {execution_time:.1f}s (tokens: {total_tokens_used})")
            
            return {
                "status": "success",
                "files": saved_files,
                "execution_time": execution_time,
                "total_tokens_used": total_tokens_used,
                "summary": {
                    "language": language,
                    "framework": framework,
                    "domain": domain,
                    "scale": scale,
                    "deployment_targets": deployment_targets,
                    "files_count": len(saved_files),
                    "components": ["docker", "kubernetes", "ci_cd", "monitoring"],
                    "generation_method": "llm_powered_batched",
                    "token_optimization": "enabled"
                }
            }
            
        except Exception as e:
            logger.error(f"LLM-powered DevOps infrastructure generation failed: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "execution_time": time.time() - start_time
            }
    
    def _create_infrastructure_batches(self, domain: str, language: str, framework: str, 
                                     scale: str, deployment_targets: List[str], features: Set[str]) -> List[Dict[str, Any]]:
        """Create optimized batches of infrastructure components for token efficiency."""
        
        batches = []
        
        # Batch 1: Containerization (Docker)
        batches.append({
            "name": "containerization",
            "component_type": "containerization",
            "component_specifications": self._get_containerization_specs(language, framework, scale),
            "files": ["Dockerfile", "docker-compose.yml", ".dockerignore"]
        })
        
        # Batch 2: Kubernetes orchestration
        if "kubernetes" in deployment_targets or "k8s" in deployment_targets:
            batches.append({
                "name": "kubernetes",
                "component_type": "kubernetes_orchestration", 
                "component_specifications": self._get_kubernetes_specs(domain, scale),
                "files": ["deployment.yaml", "service.yaml", "ingress.yaml", "configmap.yaml"]
            })
        
        # Batch 3: CI/CD automation
        batches.append({
            "name": "ci_cd",
            "component_type": "ci_cd_automation",
            "component_specifications": self._get_cicd_specs(language, framework, scale),
            "files": [".github/workflows/ci-cd.yml", "scripts/deploy.sh", "scripts/rollback.sh"]
        })
        
        # Batch 4: Monitoring and observability
        if scale in ["enterprise", "hyperscale"]:
            batches.append({
                "name": "monitoring",
                "component_type": "monitoring_observability",
                "component_specifications": self._get_monitoring_specs(domain, scale),
                "files": ["monitoring/prometheus.yml", "monitoring/grafana-dashboards.yml", "monitoring/alerting.yml"]
            })
        
        return batches
    
    def _generate_infrastructure_batch(self, batch: Dict[str, Any], context: Dict[str, Any]) -> tuple[List[Dict[str, Any]], int]:
        """Generate a batch of infrastructure files using LLM with token tracking."""
        
        # Compress context for token optimization
        compressed_context = self._compress_context_for_batch(context, batch)
        
        # Create prompt with batch-specific specifications
        prompt_input = {
            **compressed_context,
            "component_type": batch["component_type"],
            "component_specifications": batch["component_specifications"]
        }
        
        # Generate using LLM with token tracking
        response = self.devops_generation_template.invoke(prompt_input)
        
        # Parse LLM output into files
        parsed_files = parse_llm_output_into_files(
            response.content if hasattr(response, 'content') else str(response)
        )
        
        # Estimate tokens used (rough approximation)
        estimated_tokens = len(str(prompt_input)) // 4 + len(response.content) // 4
        
        # Add batch metadata to files
        for file_info in parsed_files:
            file_info["batch"] = batch["name"]
            file_info["generation_method"] = "llm_powered_batched"
        
        return parsed_files, estimated_tokens
    
    def _compress_context_for_batch(self, context: Dict[str, Any], batch: Dict[str, Any]) -> Dict[str, Any]:
        """Compress context to reduce token usage while maintaining essential information."""
        
        compressed = {}
        
        # Essential context (always include)
        compressed["domain"] = context["domain"]
        compressed["language"] = context["language"]
        compressed["framework"] = context["framework"]
        compressed["scale"] = context["scale"]
        
        # Batch-specific context (optimized)
        if batch["name"] == "containerization":
            compressed["deployment_targets"] = "container"
            compressed["features"] = context["features"][:100]  # Truncate if too long
        elif batch["name"] == "kubernetes":
            compressed["deployment_targets"] = "kubernetes"
            compressed["scale_requirements"] = context["scale_requirements"][:200]
        elif batch["name"] == "ci_cd":
            compressed["deployment_targets"] = context["deployment_targets"][:50]
            compressed["security_requirements"] = context["security_requirements"][:150]
        elif batch["name"] == "monitoring":
            compressed["scale_requirements"] = context["scale_requirements"]
            compressed["deployment_patterns"] = context["deployment_patterns"][:100]
        
        return compressed
    
    def _get_scale_requirements(self, scale: str) -> str:
        """Get scale-specific infrastructure requirements."""
        requirements = {
            "startup": "Basic containerization, simple CI/CD, cost optimization, single environment",
            "enterprise": "Multi-environment, advanced monitoring, security hardening, disaster recovery",
            "hyperscale": "Auto-scaling, global distribution, performance optimization, multi-region"
        }
        return requirements.get(scale, requirements["startup"])
    
    def _get_deployment_patterns(self, deployment_targets: List[str]) -> str:
        """Get deployment target-specific patterns using LLM."""
        prompt_context = {
            "domain": "general",
            "language": "general",
            "framework": "general",
            "scale": "general",
            "features": "scalability, reliability",
            "deployment_targets": ", ".join(deployment_targets)
        }
        chain = self.deployment_patterns_prompt | self.llm
        response = chain.invoke(prompt_context)
        return response.content if hasattr(response, 'content') else str(response)
    
    def _get_security_requirements(self, domain: str, scale: str) -> str:
        """Get security requirements based on domain and scale using LLM."""
        prompt_context = {
            "domain": domain,
            "language": "general",
            "framework": "general",
            "scale": scale,
            "features": "authentication, data_protection",
            "compliance_requirements": ", ".join(self._extract_compliance_requirements(domain))
        }
        chain = self.security_requirements_prompt | self.llm
        response = chain.invoke(prompt_context)
        return response.content if hasattr(response, 'content') else str(response)
    
    def _extract_compliance_requirements(self, domain: str) -> List[str]:
        """Extract compliance requirements based on domain.
        This is a placeholder and can be expanded with more sophisticated logic.
        """
        compliance_map = {
            "Healthcare": ["HIPAA", "HITECH"],
            "Financial": ["SOX", "PCI-DSS", "GDPR"],
            "E-commerce": ["GDPR", "CCPA"]
        }
        return compliance_map.get(domain, [])
    
    def _get_containerization_specs(self, language: str, framework: str, scale: str) -> str:
        """Get containerization specifications."""
        specs = f"Multi-stage Dockerfile for {language}/{framework}, "
        
        if scale == "startup":
            specs += "optimized for cost and simplicity"
        elif scale == "enterprise":
            specs += "with security hardening, health checks, resource limits"
        elif scale == "hyperscale":
            specs += "with performance optimization, multi-architecture support"
        
        return specs
    
    def _get_kubernetes_specs(self, domain: str, scale: str) -> str:
        """Get Kubernetes specifications."""
        specs = f"Production-ready K8s manifests for {domain} with "
        
        if scale == "startup":
            specs += "basic deployment and service"
        elif scale == "enterprise":
            specs += "HPA, ingress, configmaps, secrets management"
        elif scale == "hyperscale":
            specs += "advanced scaling, service mesh, monitoring integration"
        
        return specs
    
    def _get_cicd_specs(self, language: str, framework: str, scale: str) -> str:
        """Get CI/CD specifications using LLM."""
        prompt_context = {
            "language": language,
            "framework": framework,
            "scale": scale
        }
        chain = self.cicd_specs_prompt | self.llm
        response = chain.invoke(prompt_context)
        return response.content if hasattr(response, 'content') else str(response)
    
    def _get_monitoring_specs(self, domain: str, scale: str) -> str:
        """Get monitoring specifications using LLM."""
        prompt_context = {
            "domain": domain,
            "scale": scale
        }
        chain = self.monitoring_specs_prompt | self.llm
        response = chain.invoke(prompt_context)
        return response.content if hasattr(response, 'content') else str(response)
    
    def _generate_code(self, llm, invoke_config: Dict, **kwargs) -> Dict[str, Any]:
        """Implementation of the abstract method from base class."""
        # Extract parameters
        domain = kwargs.get('domain', 'General')
        language = kwargs.get('language', 'Python')
        framework = kwargs.get('framework', 'FastAPI')
        scale = kwargs.get('scale', 'enterprise')
        deployment_targets = kwargs.get('deployment_targets', ['docker'])
        features = kwargs.get('features', set())
        
        return self.generate_devops_infrastructure(
            domain, language, framework, scale, deployment_targets, features
        )

    def run(self, work_item: WorkItem, state: Dict[str, Any]) -> CodeGenerationOutput:
        """
        Generates DevOps infrastructure files for a single work item.
        """
        logger.info(f"DevOpsInfrastructureAgent starting work item: {work_item.id}")

        prompt = self._create_work_item_prompt(work_item, state)
        response = self.llm.invoke(prompt)
        content = response.content if hasattr(response, 'content') else str(response)
        generated_files = parse_llm_output_into_files(content)
        
        # Convert to GeneratedFile objects for saving
        generated_file_objects = [GeneratedFile(**f) for f in generated_files]
        
        # Save files to disk
        self._save_files(generated_file_objects)

        return CodeGenerationOutput(
            generated_files=[FileOutput(**f) for f in generated_files],
            summary=f"Generated {len(generated_files)} DevOps files for work item {work_item.id}."
        )

    def _create_work_item_prompt(self, work_item: WorkItem, state: Dict[str, Any]) -> str:
        tech_stack_summary = json.dumps(state.get("tech_stack_recommendation", {}), indent=2)

        return f"""
        You are a senior DevOps engineer. Your task is to create the infrastructure-as-code files described in the work item.

        **Work Item: {work_item.id}**
        - **Description:** {work_item.description}
        - **Acceptance Criteria:**
        {chr(10).join(f'  - {c}' for c in work_item.acceptance_criteria)}

        **System Context:**
        - Tech Stack: {tech_stack_summary}

        **Instructions:**
        - Create the files necessary to satisfy the work item (e.g., Dockerfile, CI/CD pipeline, etc.).
        - Use the multi-file output format.

        CRITICAL OUTPUT FORMAT - FOLLOW EXACTLY:
        ### FILE: path/to/your/file.yml
        ```yaml
        # File content here
        ```
        """ 