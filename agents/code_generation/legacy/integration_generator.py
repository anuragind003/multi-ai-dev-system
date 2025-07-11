"""
Integration Generator Agent - Specialized in generating integration code for external services
using a comprehensive, multi-file approach.
"""

import json
import os
import sys
import time
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

# Ensure correct import paths
from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.retrievers import BaseRetriever

# Add project root to Python path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import base class and utilities
from agents.code_generation.base_code_generator import BaseCodeGeneratorAgent
import monitoring
from tools.code_execution_tool import CodeExecutionTool
from message_bus import MessageBus
from models.data_contracts import GeneratedFile, CodeGenerationOutput, WorkItem
from tools.code_generation_utils import parse_llm_output_into_files

# Enhanced memory and RAG imports
from enhanced_memory_manager import create_memory_manager, EnhancedSharedProjectMemory
from rag_manager import get_rag_manager

# Setup logger
logger = logging.getLogger(__name__)

class IntegrationGeneratorAgent(BaseCodeGeneratorAgent):
    """
    Specialized Integration Generator Agent that creates complete integration code
    for external services in a single step, including service connectors, adapters, and configs.
    """
    
    def __init__(self, llm: BaseLanguageModel, memory, 
                 temperature: float = 0.1,
                 output_dir: str = "./output/integrations", 
                 code_execution_tool: Optional[CodeExecutionTool] = None,
                 rag_retriever: Optional[BaseRetriever] = None,
                 message_bus: Optional[MessageBus] = None):
        """Initialize Integration Generator Agent."""
        
        # Call super().__init__ with all required parameters
        super().__init__(
            llm=llm,
            memory=memory,
            agent_name="Integration Generator Agent",
            temperature=temperature,
            output_dir=output_dir,
            code_execution_tool=code_execution_tool,
            rag_retriever=rag_retriever,
            message_bus=message_bus
        )
        
        # Initialize enhanced memory (inherits from BaseCodeGeneratorAgent -> BaseAgent)
        self._init_enhanced_memory()
        
        # Initialize RAG context
        self.rag_manager = get_rag_manager()
        if self.rag_manager:
            self.logger.info("RAG manager available for enhanced integration generation")
        else:
            self.logger.warning("RAG manager not available - proceeding with basic integration generation")
        
        # Initialize single comprehensive prompt template
        self._initialize_prompt_templates()
        
        # Maximum tokens for generation
        self.max_tokens = 8192
        
        # Maximum context limits
        self.max_context_chars = {
            "rag": 2000,
            "integration_requirements": 1000,
            "system_design": 1500
        }
          # Maximum examples to include
        self.max_examples = {
            "integration_points": 5,
            "rag_docs": {
                "low": 2,
                "medium": 3, 
                "high": 4
            }
        }
        
        # Setup message bus subscriptions
        self._setup_message_subscriptions()
    
    def run(self, work_item: WorkItem, state: Dict[str, Any]) -> CodeGenerationOutput:
        """
        Standardized run method for integration code generation.
        
        Args:
            work_item: The specific work item to process
            state: The current workflow state containing context
            
        Returns:
            CodeGenerationOutput: Structured integration code generation results
        """
        logger.info(f"IntegrationGeneratorAgent processing work item: {work_item.id}")
        
        try:
            # Extract context from state
            tech_stack = state.get('tech_stack_recommendation', {})
            system_design = state.get('system_design', {})
            requirements_analysis = state.get('requirements_analysis', {})
            
            # Call the specialized _generate_code method with standardized parameters
            result = self._generate_code(
                llm=self.llm,
                invoke_config={"temperature": self.temperature},
                work_item=work_item,
                tech_stack=tech_stack,
                system_design=system_design,
                requirements_analysis=requirements_analysis,
                state=state
            )
            
            # Convert to CodeGenerationOutput if needed
            if isinstance(result, dict):
                generated_files = result.get('generated_files', [])
                
                # Save files to disk
                self._save_files(generated_files)
                
                return CodeGenerationOutput(
                    generated_files=generated_files,
                    summary=result.get('summary', f'Generated integration code for work item {work_item.id}'),
                    status=result.get('status', 'success'),
                    metadata=result.get('metadata', {})
                )
            
            return result
            
        except Exception as e:
            logger.error(f"IntegrationGeneratorAgent failed for {work_item.id}: {str(e)}")
            return CodeGenerationOutput(
                generated_files=[],
                summary=f"Integration code generation failed for {work_item.id}: {str(e)}",
                status="error",
                metadata={"error": str(e)}
            )
    
    async def arun(self, **kwargs: Any) -> Any:
        return self._generate_code(self.llm, {}, **kwargs)
 
    def _initialize_prompt_templates(self):
        """Initialize a single comprehensive prompt template for generating all integration code."""
        
        multi_file_format = """
        CRITICAL OUTPUT FORMAT:
        You MUST provide your response as a single block of text. For each file you generate, 
        you MUST use the following format:

        ### FILE: path/to/your/file.ext

        ```filetype
        // The full content of the file goes here.
        ```

        Continue this pattern for all files you need to create. For ENTERPRISE-GRADE integrations, generate:
        1. Main service integration code (connectors, API clients)
        2. Adapter classes that provide clean interfaces
        3. Configuration files with secure parameter handling
        4. Example usage files showing how to use each integration
        5. Security and authentication modules
        6. Monitoring and observability components
        7. Error handling and resilience patterns
        8. Testing and validation frameworks
        9. DevOps and deployment configurations
        10. Documentation and API specifications
        """

        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", 
             "You are an expert enterprise integration architect specializing in PRODUCTION-READY, ENTERPRISE-GRADE "
             "system integrations. You create comprehensive integration solutions with advanced security, monitoring, "
             "resilience, and operational excellence that are immediately deployable to production environments.\n\n"
             
             "**MANDATORY ENTERPRISE INTEGRATION REQUIREMENTS:**\n"
             "You MUST include ALL of the following in every integration implementation:\n\n"
             
             "1. **SECURITY & AUTHENTICATION:**\n"
             "   - Multi-layered authentication (OAuth 2.0, API keys, JWTs)\n"
             "   - Certificate-based mutual TLS (mTLS) authentication\n"
             "   - API key rotation and secret management\n"
             "   - Request signing and payload encryption\n"
             "   - IP whitelisting and geo-blocking capabilities\n"
             "   - Security headers and OWASP compliance\n"
             "   - Audit logging for all API interactions\n\n"
             
             "2. **RESILIENCE & RELIABILITY:**\n"
             "   - Circuit breaker patterns with configurable thresholds\n"
             "   - Exponential backoff retry mechanisms\n"
             "   - Bulkhead isolation for service failures\n"
             "   - Timeout management and deadline propagation\n"
             "   - Graceful degradation strategies\n"
             "   - Dead letter queues for failed operations\n"
             "   - Health checks and service discovery\n\n"
             
             "3. **MONITORING & OBSERVABILITY:**\n"
             "   - Distributed tracing with correlation IDs\n"
             "   - Comprehensive metrics collection (RED/USE)\n"
             "   - Real-time alerting and anomaly detection\n"
             "   - Performance monitoring and SLA tracking\n"
             "   - Business metrics and KPI dashboards\n"
             "   - Log aggregation and structured logging\n"
             "   - Integration health and dependency mapping\n\n"
             
             "4. **PERFORMANCE & SCALABILITY:**\n"
             "   - Connection pooling and resource management\n"
             "   - Async/await patterns for I/O operations\n"
             "   - Caching strategies (Redis, in-memory)\n"
             "   - Rate limiting and throttling controls\n"
             "   - Load balancing and failover mechanisms\n"
             "   - Batch processing and bulk operations\n"
             "   - Resource optimization and garbage collection\n\n"
             
             "5. **DATA GOVERNANCE & COMPLIANCE:**\n"
             "   - Data validation and schema enforcement\n"
             "   - PII detection and data masking\n"
             "   - GDPR/CCPA compliance mechanisms\n"
             "   - Data lineage tracking and audit trails\n"
             "   - Encryption at rest and in transit\n"
             "   - Data retention and purging policies\n"
             "   - Compliance reporting and validation\n\n"
             
             "6. **TESTING & VALIDATION:**\n"
             "   - Unit tests with mocking and stubbing\n"
             "   - Integration tests with real/fake services\n"
             "   - Contract testing (Pact, OpenAPI)\n"
             "   - Load testing and stress testing\n"
             "   - Chaos engineering and fault injection\n"
             "   - Performance benchmarking\n"
             "   - Security penetration testing\n\n"
             
             "7. **DEVOPS & DEPLOYMENT:**\n"
             "   - Infrastructure as Code (Terraform, Helm)\n"
             "   - CI/CD pipeline integration\n"
             "   - Blue-green deployment strategies\n"
             "   - Feature flags and canary releases\n"
             "   - Environment configuration management\n"
             "   - Container orchestration (Kubernetes)\n"
             "   - Service mesh integration (Istio, Linkerd)\n\n"
             
             "Generate enterprise-grade integration solutions that are immediately deployable to production "
             "with comprehensive security, monitoring, and operational excellence built-in."
            ),
            ("human", 
             """
             Generate a COMPLETE ENTERPRISE-GRADE integration implementation for all external services listed below. 
             This must be immediately deployable to production with enterprise security, monitoring, resilience, 
             and operational excellence.\n\n
             
             ## Domain Context
             Domain: {domain}
             Scale: {scale}
             Compliance Requirements: {compliance_requirements}
             
             ## Integration Services
             {integration_points_json}
             
             ## Technical Architecture
             {tech_stack_summary}
             Architecture Pattern: {architecture_pattern}
             Backend Framework: {backend_framework}
             Backend Language: {backend_language}
             
             ## MANDATORY ENTERPRISE REQUIREMENTS
             You MUST generate ALL of the following categories for EACH integration service:\n\n
             
             ### 1. **CORE INTEGRATION SERVICES**
             - Main service clients with full API coverage
             - Clean adapter interfaces with domain abstractions
             - Service factory patterns for dependency injection
             - Configuration management with environment-specific settings
             - Connection pooling and resource management
             
             ### 2. **SECURITY & AUTHENTICATION**
             - Multi-factor authentication implementations
             - OAuth 2.0/JWT token management with refresh
             - API key rotation and secret management
             - Request signing and payload encryption
             - Security header injection and validation
             - Audit logging for all integration calls
             
             ### 3. **RESILIENCE & RELIABILITY**
             - Circuit breaker implementations with hystrix patterns
             - Exponential backoff retry mechanisms
             - Bulkhead isolation for service failures
             - Timeout management and deadline propagation
             - Dead letter queues for failed operations
             - Graceful degradation and fallback strategies
             
             ### 4. **MONITORING & OBSERVABILITY**
             - Distributed tracing with OpenTelemetry integration
             - Comprehensive metrics (RED/USE)
             - Real-time alerting and anomaly detection
             - Performance monitoring and SLA tracking
             
             ### 5. **DATA GOVERNANCE & COMPLIANCE**
             - Data validation and schema enforcement
             - PII detection and data masking
             - GDPR/CCPA compliance mechanisms
             
             ### 6. **TESTING & VALIDATION**
             - Unit, integration, and contract tests
             - Load and performance testing
             - Security penetration testing
             
             ### 7. **DEVOPS & DEPLOYMENT**
             - Infrastructure as Code (IaC)
             - CI/CD pipeline integration
             - Blue-green/canary deployment strategies
             
             ## Context from RAG (similar projects or best practices):
             {rag_context}
             
             ## Integration Requirements
             {integration_requirements}
             
             ## Domain-Specific Integration Requirements
             {domain_integration_requirements}
             
             ## Scale-Specific Integration Considerations
             {scale_integration_considerations}
             
             ## Security and Compliance Requirements
             {security_compliance_requirements}
             
             {code_review_feedback}
             
             Please generate the complete, enterprise-grade integration code now.
             """
             )
        ])
    
    def _generate_code(self, llm: BaseLanguageModel, 
                      invoke_config: Dict, 
                      **kwargs) -> Dict[str, Any]:
        """
        Generate complete integration code in a single step.
        
        Args:
            llm: Language model to use for generation
            invoke_config: Configuration for LLM invocation
            **kwargs: Additional arguments including requirements_analysis, tech_stack, system_design, etc.
            
        Returns:
            Dictionary conforming to the CodeGenerationOutput model
        """
        self.log_info("Starting comprehensive integration code generation")
        start_time = time.time()
        
        # Extract required inputs with validation
        tech_stack = kwargs.get('tech_stack', {})
        system_design = kwargs.get('system_design', {})
        requirements_analysis = kwargs.get('requirements_analysis', {})
        code_review_feedback = kwargs.get('code_review_feedback')
        
        # Track if this is a revision based on feedback
        is_revision = code_review_feedback is not None
        generation_type = "revision" if is_revision else "initial generation"
        
        try:            # Validate inputs with defaults
            if not isinstance(tech_stack, dict):
                self.log_warning("Invalid tech stack - using default")
                tech_stack = self._create_default_tech_stack()
                
            if not isinstance(system_design, dict):
                self.log_warning("Invalid system design - using default")
                system_design = self._create_default_system_design()
            
            # Extract domain, scale, and compliance information
            domain = self._extract_domain(requirements_analysis, tech_stack, system_design)
            scale = self._extract_scale(requirements_analysis, system_design)
            compliance_requirements = self._extract_compliance_requirements(requirements_analysis, system_design)
            
            # Extract integration points
            integration_points = self._extract_integration_points(system_design)
            
            if not integration_points:
                self.log_warning("No integration points found in system design - using defaults")
                integration_points = self._create_default_integration_points(domain, scale)
            
            # Get tech stack details
            backend_tech = self._extract_backend_tech(tech_stack)
            backend_language = backend_tech.get("language", "python")
            backend_framework = backend_tech.get("framework", "flask")
            architecture_pattern = tech_stack.get("architecture_pattern", "MVC")
              # Create tech stack summary
            tech_stack_summary = self._create_tech_stack_summary(tech_stack)
            
            # Create domain-aware integration requirements
            domain_integration_requirements = self._get_domain_integration_requirements(domain, integration_points)
            scale_integration_considerations = self._get_scale_integration_considerations(scale, integration_points)
            security_compliance_requirements = self._get_security_compliance_requirements(compliance_requirements, domain)
            
            # Create integration requirements summary
            integration_requirements = self._create_integration_requirements_summary(
                requirements_analysis, integration_points)
            
            # Estimate overall complexity for temperature adjustment
            complexity = self._estimate_overall_complexity(integration_points)
            
            # Get RAG context for integration best practices
            rag_context = self._get_integration_rag_context(backend_language, backend_framework, integration_points)
            
            # Prepare integration points for the prompt (convert to JSON)
            integration_points_json = json.dumps(integration_points, indent=2)
            
            # Prepare code review feedback section if available
            code_review_section = ""
            if is_revision and isinstance(code_review_feedback, dict):
                code_review_section = "## Code Review Feedback to Address\n"
                
                if "critical_issues" in code_review_feedback:
                    code_review_section += "Critical Issues:\n"
                    for issue in code_review_feedback.get("critical_issues", []):
                        if isinstance(issue, dict):
                            code_review_section += f"- {issue.get('issue', '')}\n"
                            if issue.get('fix'):
                                code_review_section += f"  Suggested fix: {issue['fix']}\n"
                
                if "suggestions" in code_review_feedback:
                    code_review_section += "Suggestions:\n"
                    for suggestion in code_review_feedback.get("suggestions", []):
                        code_review_section += f"- {suggestion}\n"
            
            # Set temperature - slightly lower for integration code (deterministic)
            adjusted_temp = self._get_complexity_based_temperature(complexity, is_revision)
            
            # Use binding pattern for temperature
            llm_with_temp = llm.bind(
                temperature=adjusted_temp,
                max_tokens=self.max_tokens
            )
            
            # Add monitoring context
            invoke_config = invoke_config.copy()  # Create a copy to avoid modifying the original
            invoke_config["agent_context"] = f"{self.agent_name}:{complexity}_complexity"
            invoke_config["temperature_used"] = adjusted_temp
            invoke_config["is_revision"] = is_revision
              # Execute LLM call to generate all integration artifacts
            self.log_info(f"Generating integration code for {domain} domain at {scale} scale")
            response = llm_with_temp.invoke(
                self.prompt_template.format(
                    domain=domain,
                    scale=scale,
                    compliance_requirements=compliance_requirements,
                    integration_points_json=integration_points_json,
                    tech_stack_summary=tech_stack_summary,
                    architecture_pattern=architecture_pattern,
                    backend_framework=backend_framework,
                    backend_language=backend_language,
                    domain_integration_requirements=domain_integration_requirements,
                    scale_integration_considerations=scale_integration_considerations,
                    security_compliance_requirements=security_compliance_requirements,
                    integration_requirements=integration_requirements,
                    rag_context=rag_context,
                    code_review_feedback=code_review_section
                ),
                config=invoke_config
            )
            
            # Extract content from response
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Log abbreviated version of the content for debug purposes
            self.logger.debug(f"LLM response (abbreviated): {content[:300]}...")
            
            # Store the activity
            if self.memory:
                self.memory.store_agent_activity(
                    agent_name=self.agent_name,
                    activity_type=f"integration_{generation_type}",
                    prompt=str(self.prompt_template),
                    response=content[:1000] + "..." if len(content) > 1000 else content,
                    metadata={
                        "integration_count": len(integration_points),
                        "complexity": complexity,
                        "is_revision": is_revision,
                        "temperature": adjusted_temp
                    }
                )
              # Parse the multi-file output
            generated_files = parse_llm_output_into_files(content)
            
            # Handle case where parsing fails
            if not generated_files:
                self.log_warning("Failed to parse multi-file output, generating default files")
                # Generate default files for each integration point
                generated_files = self._create_default_integration_files(
                    integration_points, backend_language, backend_framework
                )
            
            # Categorize files by type for metadata
            service_files_count = len([f for f in generated_files if "/services/" in f['path'] or "/integrations/" in f['path']])
            adapter_files_count = len([f for f in generated_files if "/adapters/" in f['path']])
            config_files_count = len([f for f in generated_files if "/config/" in f['path'] or f['path'].endswith(".env")])
            
            # Create directories first before saving files
            self._create_directories_from_files(generated_files)

            # Create structured output
            output = CodeGenerationOutput(
                generated_files=[GeneratedFile(**f) for f in generated_files],
                summary=f"Generated {len(generated_files)} integration files for {len(integration_points)} external services",
                status="success" if generated_files else "error",
                metadata={
                    "integration_points": [ip["name"] for ip in integration_points],
                    "file_counts": {
                        "service_files": service_files_count,
                        "adapter_files": adapter_files_count,
                        "config_files": config_files_count,
                        "total": len(generated_files)
                    },
                    "complexity": complexity,
                    "is_revision": is_revision,
                    "backend_language": backend_language,
                    "backend_framework": backend_framework,
                    "agent": self.agent_name,
                    "temperature_used": adjusted_temp,
                    "execution_time": time.time() - start_time
                }
            )
            
            # Log success message
            self.log_success(
                f"Integration {generation_type} complete: {len(generated_files)} files generated "
                f"for {len(integration_points)} services"
            )
              # Publish event if message bus is available
            if self.message_bus:
                self.message_bus.publish("integration.generated", {
                    "integration_count": len(integration_points),
                    "file_count": len(generated_files),
                    "complexity": complexity,
                    "is_revision": is_revision,
                    "status": "success"
                })
                
                # Signal that complete code generation phase is done
                self.message_bus.publish("code_generation.complete", {
                    "phase": "integration_complete",
                    "total_files": len(generated_files),
                    "integration_services": len(integration_points),
                    "status": "success",
                    "agent": self.agent_name,
                    "timestamp": datetime.now().isoformat()
                })
                self.log_info("Published code_generation.complete event - code generation phase finished")
            
            # Store result in enhanced memory for cross-tool access
            self.enhanced_set("integration_generation_result", output.model_dump(), context="integration_generation")
            
            # Convert GeneratedFile objects to dictionaries before storing to avoid JSON serialization errors
            integration_files_dict = [
                {
                    "file_path": cf.file_path,
                    "content": cf.content,
                    "file_type": "integration"
                } for cf in output.generated_files
            ]
            self.enhanced_set("integration_files", integration_files_dict, context="integration_files")
            
            return output.model_dump()
            
        except Exception as e:
            self.log_error(f"Error in integration code generation: {e}", exc_info=True)
            
            # Create default local variables to prevent UnboundLocalError
            local_integration_points = integration_points if 'integration_points' in locals() else []
            local_backend_language = backend_language if 'backend_language' in locals() else "python"
            local_backend_framework = backend_framework if 'backend_framework' in locals() else "flask"

            error_output = CodeGenerationOutput(
                generated_files=self._create_default_integration_files(
                    local_integration_points,
                    local_backend_language,
                    local_backend_framework
                ),
                summary=f"Error generating integration code: {str(e)}",
                status="error",
                metadata={
                    "error": str(e),
                    "agent": self.agent_name,
                    "timestamp": datetime.now().isoformat()
                }
            )
            return error_output.model_dump()
    
    def _create_integration_requirements_summary(self, 
                                              requirements_analysis: Dict[str, Any],
                                              integration_points: List[Dict[str, Any]]) -> str:
        """
        Create a concise summary of integration requirements.
        
        Args:
            requirements_analysis: Requirements analysis dictionary
            integration_points: List of integration points
            
        Returns:
            String summary of integration requirements
        """
        try:
            # Extract integration-specific requirements from requirements analysis
            integration_reqs = []
            
            if isinstance(requirements_analysis, dict):
                # Look for integration requirements in various places
                if "integration_requirements" in requirements_analysis:
                    reqs = requirements_analysis["integration_requirements"]
                    if isinstance(reqs, list):
                        integration_reqs.extend(reqs)
                    elif isinstance(reqs, str):
                        integration_reqs.append(reqs)
                
                # Check functional requirements for integration-related items
                if "functional_requirements" in requirements_analysis:
                    func_reqs = requirements_analysis["functional_requirements"]
                    if isinstance(func_reqs, list):
                        for req in func_reqs:
                            if isinstance(req, str) and any(kw in req.lower() for kw in ["integration", "external", "api", "service", "third-party"]):
                                integration_reqs.append(req)
            
            # Add requirements from each integration point
            for point in integration_points:
                if "requirements" in point and point["requirements"]:
                    integration_reqs.append(f"{point['name']}: {point['requirements']}")
            
            # If no specific requirements were found, create generic ones
            if not integration_reqs:
                integration_reqs = [
                    "All integrations must implement proper error handling and logging",
                    "Authentication credentials must be stored securely",
                    "All integrations must handle rate limiting and retries",
                    "Timeouts should be implemented for all external calls"
                ]
            
            # Format as a nice summary
            return "Integration Requirements:\n" + "\n".join(f"- {req}" for req in integration_reqs)
            
        except Exception as e:
            self.log_warning(f"Error creating integration requirements summary: {str(e)}")
            return "Integration Requirements:\n- Implement proper error handling\n- Store credentials securely\n- Handle rate limiting"
    
    def _get_integration_rag_context(self, 
                                  backend_language: str,
                                  backend_framework: str,
                                  integration_points: List[Dict[str, Any]]) -> str:
        """
        Get RAG context for integration best practices.
        
        Args:
            backend_language: Backend language name
            backend_framework: Backend framework name
            integration_points: List of integration points
            
        Returns:
            RAG context string for integration best practices
        """
        if not self.rag_retriever:
            return ""
        
        try:
            # Create targeted queries for better RAG results
            queries = [
                f"{backend_language} {backend_framework} external service integration patterns",
                "API client error handling and retry best practices"
            ]
              # Add queries for specific integration types - avoid duplicates
            integration_types = set(point.get("type", "REST API") for point in integration_points)
            for integration_type in integration_types:
                queries.append(f"{integration_type} integration in {backend_language}")
            
            combined_context = []
            for query in queries:
                try:
                    docs = self.rag_retriever.invoke(query)
                    if docs:
                        context = "\n\n".join([doc.page_content for doc in docs[:2]])  # Just get top 2 results
                        if context:
                            combined_context.append(f"## {query.title()}\n{context}")
                except Exception as e:
                    self.log_warning(f"Error retrieving RAG for '{query}': {e}")
            
            if combined_context:
                return "\n\nBest Practices References:\n" + "\n\n".join(combined_context)
            else:
                return ""
            
        except Exception as e:
            self.log_warning(f"Error retrieving RAG context: {str(e)}")
            return ""
    
    def _estimate_overall_complexity(self, integration_points: List[Dict[str, Any]]) -> str:
        """
        Estimate the overall complexity of all integrations.
        
        Args:
            integration_points: List of integration points
            
        Returns:
            Complexity level ("low", "medium", "high")
        """
        if not integration_points:
            return "low"
            
        try:
            # Count complexity indicators
            complexity_indicators = {
                "high": ["oauth", "real-time", "streaming", "webhook", "bidirectional", "graphql", "websocket"],
                "medium": ["authentication", "rate limiting", "pagination", "transformation", "validation"]
            }
            
            # Start with points based on count of integrations
            complexity_score = min(len(integration_points), 3)
            
            for point in integration_points:
                requirements = point.get("requirements", "").lower()
                service_type = point.get("type", "").lower()
                
                # Check for high complexity indicators
                for indicator in complexity_indicators["high"]:
                    if indicator in requirements or indicator in service_type:
                        complexity_score += 2
                
                # Check for medium complexity indicators
                for indicator in complexity_indicators["medium"]:
                    if indicator in requirements or indicator in service_type:
                        complexity_score += 1
            
            # Determine complexity level
            if complexity_score <= 3:
                return "low"
            elif complexity_score <= 7:
                return "medium"
            else:
                return "high"
            
        except Exception as e:
            self.log_warning(f"Error estimating integration complexity: {str(e)}")
            return "medium"  # Default to medium complexity
    
    def _get_complexity_based_temperature(self, complexity: str, is_revision: bool) -> float:
        """
        Adjust temperature based on complexity and whether this is a revision.
        
        The temperature adjustment follows these principles:
        - Base temperature is 0.1 (good for deterministic code generation)
        - High complexity adds 0.05 (more creativity for complex integrations)
        - Low complexity subtracts 0.02 (more deterministic for simple cases)
        - Revisions add 0.03 (to encourage different approaches when fixing issues)
        - Final temperature is clamped to range [0.05, 0.2] for code generation
        
        Args:
            complexity: Complexity level ("low", "medium", "high")
            is_revision: Whether this is a revision based on feedback
            
        Returns:
            Adjusted temperature value between 0.05 and 0.2
        """
        # Base temperature - keep low for deterministic code generation
        base_temp = 0.1
        
        # Adjust based on complexity
        if complexity == "high":
            base_temp += 0.05  # Slightly more creative for complex integrations
        elif complexity == "low":
            base_temp -= 0.02  # Even more deterministic for simple integrations
            
        # If this is a revision, increase slightly to encourage different approaches
        if is_revision:
            base_temp += 0.03
            
        # Ensure temperature stays in reasonable range (0.05-0.2 is good for code generation)
        return max(0.05, min(base_temp, 0.2)) 