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
from models.data_contracts import GeneratedFile, CodeGenerationOutput, CodeFile, WorkItem
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
             - Metrics collection (latency, errors, throughput)
             - Real-time alerting rules and thresholds
             - Health check endpoints and status reporting
             - Business metrics tracking and dashboards
             - Structured logging with correlation IDs
             
             ### 5. **PERFORMANCE & SCALABILITY**
             - Async/await implementations for all I/O operations
             - Connection pooling and keep-alive management
             - Caching layers with TTL and invalidation
             - Rate limiting and throttling controls
             - Batch processing and bulk operation support
             - Resource optimization and memory management
             
             ### 6. **TESTING & VALIDATION**
             - Comprehensive unit tests with mocking frameworks
             - Integration tests with test doubles/fakes
             - Contract testing with API specification validation
             - Load testing and performance benchmarking
             - Chaos engineering and fault injection tests
             - Security penetration testing scenarios
             
             ### 7. **DEVOPS & DEPLOYMENT**
             - Docker containerization with multi-stage builds
             - Kubernetes deployment manifests with health checks
             - Infrastructure as Code (Terraform/Helm charts)
             - CI/CD pipeline configuration files
             - Environment-specific configuration management
             - Blue-green deployment and rollback procedures
             
             ### 8. **DOCUMENTATION & SPECIFICATIONS**
             - OpenAPI/Swagger specifications for all endpoints
             - Integration guides and troubleshooting documentation
             - Architecture decision records (ADRs)
             - Runbooks for operational procedures
             - API usage examples and best practices
             - Security and compliance documentation
             
             ## Domain-Specific Requirements
             {domain_integration_requirements}
             
             ## Scale & Performance Considerations
             {scale_integration_considerations}
             
             ## Security & Compliance Requirements
             {security_compliance_requirements}
             
             ## Integration Requirements
             {integration_requirements}
             
             ## Best Practices Context
             {rag_context}
             
             {code_review_feedback}
             
             ## OUTPUT REQUIREMENTS
             Generate a MINIMUM of 15+ files per integration service covering all enterprise requirements above.
             Include proper file organization with directories for different concerns (services/, security/, 
             monitoring/, testing/, deployment/, etc.). Each file must be production-ready with comprehensive 
             error handling, logging, and documentation.\n\n
             
             Follow this multi-file format EXACTLY:
             {format_instructions}
             """
            )
        ])
        
        self.prompt_template = self.prompt_template.partial(format_instructions=multi_file_format)
    
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
              # Convert GeneratedFile objects to CodeFile objects
            code_files = [
                CodeFile(
                    file_path=gf.file_path,
                    code=gf.content
                ) for gf in generated_files
            ]
            
            # Categorize files by type for metadata
            service_files_count = len([f for f in code_files if "/services/" in f.file_path or "/integrations/" in f.file_path])
            adapter_files_count = len([f for f in code_files if "/adapters/" in f.file_path])
            config_files_count = len([f for f in code_files if "/config/" in f.file_path or f.file_path.endswith(".env")])
            
            # Create directories first before saving files
            self._create_directories_from_files(generated_files)
            
            # Create structured output
            output = CodeGenerationOutput(
                files=code_files,                summary=f"Generated {len(code_files)} integration files for {len(integration_points)} external services",
                status="success" if code_files else "error",
                metadata={
                    "integration_points": [ip["name"] for ip in integration_points],
                    "file_counts": {
                        "service_files": service_files_count,
                        "adapter_files": adapter_files_count,
                        "config_files": config_files_count,
                        "total": len(code_files)
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
            self.enhanced_set("integration_generation_result", output.dict(), context="integration_generation")
            
            # Convert CodeFile objects to dictionaries before storing to avoid JSON serialization errors
            integration_files_dict = [
                {
                    "file_path": cf.file_path,
                    "code": cf.code,
                    "file_type": "integration"
                } for cf in code_files
            ]
            self.store_cross_tool_data("integration_files", integration_files_dict, f"Integration files for {len(integration_points)} services")
            
            # Store integration patterns for reuse
            self.enhanced_set("integration_patterns", {
                "integration_points": integration_points,
                "backend_language": backend_language,
                "backend_framework": backend_framework,
                "domain": domain,
                "scale": scale,
                "total_services": len(integration_points)
            }, context="integration_patterns")
            
            # Return as dictionary
            return output.dict()
            
        except Exception as e:
            self.log_error(f"Integration {generation_type} failed: {str(e)}", exc_info=True)
            # Return error output using the standardized format
            
            # Handle the case where integration_points might not be in locals()
            # (i.e., an error occurred before it was defined)
            local_integration_points = (
                integration_points if 'integration_points' in locals() 
                else self._create_default_integration_points(domain, scale)
            )
              # Handle the case where backend_language/framework might not be in locals()
            local_backend_language = backend_language if 'backend_language' in locals() else "python"
            local_backend_framework = backend_framework if 'backend_framework' in locals() else "flask"
            
            error_output = CodeGenerationOutput(
                files=self._create_default_integration_files(
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
            return error_output.dict()
    
    # --- Helper methods for integration generation ---
    
    def _create_directories_from_files(self, generated_files: List[GeneratedFile]) -> None:
        """
        Create all necessary directories based on file paths.
        
        Args:
            generated_files: List of file dictionaries to create directories for
        """
        directories = set()
        
        for file_data in generated_files:
            dir_path = os.path.dirname(file_data.file_path)
            
            if dir_path:
                directories.add(dir_path)
        
        # Create all unique directories
        for directory in directories:
            try:
                full_path = os.path.join(self.output_dir, directory)
                os.makedirs(full_path, exist_ok=True)
                self.log_info(f"Created directory: {directory}")
            except Exception as e:
                self.log_error(f"Failed to create directory {directory}: {str(e)}")
    
    def _extract_integration_points(self, system_design: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract and normalize integration points from system design.
        
        Args:
            system_design: System design dictionary
            
        Returns:
            List of normalized integration point dictionaries
        """
        try:
            # Check for explicit integration_points section
            integration_points = []
            if "integration_points" in system_design and isinstance(system_design["integration_points"], list):
                integration_points = system_design["integration_points"]
            
            # If not found, check alternative locations
            if not integration_points:
                # Check external_services section if present
                if "external_services" in system_design and isinstance(system_design["external_services"], list):
                    external_services = system_design["external_services"]
                    for service in external_services:
                        if isinstance(service, dict):
                            integration_points.append({
                                "name": service.get("name", "Unknown Service"),
                                "type": service.get("type", "REST API"),
                                "purpose": service.get("purpose", "Data exchange"),
                                "requirements": service.get("requirements", "Standard integration")
                            })
                
                # Check api_integrations section if present
                elif "api_integrations" in system_design and isinstance(system_design["api_integrations"], list):
                    api_integrations = system_design["api_integrations"]
                    for api in api_integrations:
                        if isinstance(api, dict):
                            integration_points.append({
                                "name": api.get("name", "Unknown API"),
                                "type": api.get("type", "REST API"),
                                "purpose": api.get("purpose", "API integration"),
                                "requirements": api.get("requirements", "Standard integration")
                            })
            
            # Normalize each integration point
            normalized_points = []
            for point in integration_points:
                if isinstance(point, dict):
                    normalized_point = {
                        "name": point.get("name", "Unknown Service"),
                        "type": point.get("type", "REST API"),
                        "purpose": point.get("purpose", "Data exchange"),
                        "requirements": point.get("requirements", "Standard integration")
                    }
                    normalized_points.append(normalized_point)
            
            # Limit number of integration points to avoid token overload
            max_points = self.max_examples.get("integration_points", 5)
            if len(normalized_points) > max_points:
                self.log_warning(f"Limiting integration points from {len(normalized_points)} to {max_points}")
                normalized_points = normalized_points[:max_points]
            
            return normalized_points
            
        except Exception as e:
            self.log_warning(f"Error extracting integration points: {str(e)}")
            return self._create_default_integration_points("General", "Small")
    
    def _extract_backend_tech(self, tech_stack: Dict[str, Any]) -> Dict[str, str]:
        """
        Extract backend technology details from tech stack.
        
        Args:
            tech_stack: Technology stack dictionary
            
        Returns:
            Dictionary with backend language and framework
        """
        backend_tech = {
            "language": "python",
            "framework": "flask"
        }
        
        try:
            if "backend" in tech_stack:
                backend = tech_stack["backend"]
                if isinstance(backend, dict):
                    if "language" in backend:
                        backend_tech["language"] = backend["language"].lower()
                    if "framework" in backend:
                        backend_tech["framework"] = backend["framework"].lower()
                elif isinstance(backend, list) and len(backend) > 0:
                    first_backend = backend[0]
                    if isinstance(first_backend, dict):
                        if "language" in first_backend:
                            backend_tech["language"] = first_backend["language"].lower()
                        if "name" in first_backend or "framework" in first_backend:
                            framework = first_backend.get("name", first_backend.get("framework", "flask"))
                            backend_tech["framework"] = framework.lower()
            
            return backend_tech
            
        except Exception as e:
            self.log_warning(f"Error extracting backend tech: {str(e)}")
            return backend_tech
    
    def _create_tech_stack_summary(self, tech_stack: Dict[str, Any]) -> str:
        """
        Create a concise summary of the tech stack.
        
        Args:
            tech_stack: Technology stack dictionary
            
        Returns:
            String summary of the tech stack
        """
        if not tech_stack or not isinstance(tech_stack, dict):
            return "Python Flask backend with React frontend"
        
        try:
            # Extract backend info
            backend_tech = self._extract_backend_tech(tech_stack)
            backend_language = backend_tech.get("language", "python").capitalize()
            backend_framework = backend_tech.get("framework", "flask").capitalize()
            
            # Extract frontend info
            frontend_framework = "Unknown"
            if "frontend" in tech_stack:
                frontend = tech_stack["frontend"]
                if isinstance(frontend, dict):
                    frontend_framework = frontend.get("framework", frontend.get("name", "React"))
                elif isinstance(frontend, list) and len(frontend) > 0:
                    first_frontend = frontend[0]
                    if isinstance(first_frontend, dict):
                        frontend_framework = first_frontend.get("name", first_frontend.get("framework", "React"))
                    elif isinstance(first_frontend, str):
                        frontend_framework = first_frontend
                elif isinstance(frontend, str):
                    frontend_framework = frontend
            
            # Extract architecture pattern
            architecture = tech_stack.get("architecture_pattern", "MVC")
            
            return f"{backend_language} {backend_framework} backend with {frontend_framework} frontend using {architecture} architecture"
            
        except Exception as e:
            self.log_warning(f"Error creating tech stack summary: {str(e)}")
            return "Python Flask backend with React frontend"
    
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
    def _create_default_integration_points(self, domain: str = "General", scale: str = "Small") -> List[Dict[str, Any]]:
        """
        Create domain and scale-aware default integration points when none are found.
        
        Args:
            domain: Application domain
            scale: Expected scale
            
        Returns:
            List of default integration point dictionaries
        """
        # Domain-specific integration patterns
        domain_integrations = {
            "Healthcare": [
                {
                    "name": "EHR System Integration",
                    "type": "HL7 FHIR API",
                    "purpose": "Exchange patient health records",
                    "requirements": "HIPAA-compliant data exchange with audit logging"
                },
                {
                    "name": "Payment Gateway",
                    "type": "REST API",
                    "purpose": "Process healthcare payments",
                    "requirements": "PCI DSS compliant payment processing with encryption"
                },
                {
                    "name": "Insurance Claims API",
                    "type": "EDI/REST API",
                    "purpose": "Submit and track insurance claims",
                    "requirements": "HIPAA-compliant claims processing with status tracking"
                }
            ],
            "Finance": [
                {
                    "name": "Banking API Integration",
                    "type": "REST API",
                    "purpose": "Account verification and transactions",
                    "requirements": "PCI DSS and banking regulation compliant with fraud detection"
                },
                {
                    "name": "Credit Scoring Service",
                    "type": "REST API",
                    "purpose": "Credit risk assessment",
                    "requirements": "Real-time credit scoring with secure data transmission"
                },
                {
                    "name": "Regulatory Reporting API",
                    "type": "REST API",
                    "purpose": "Submit regulatory reports",
                    "requirements": "SOX compliant reporting with audit trails"
                }
            ],
            "E-commerce": [
                {
                    "name": "Payment Gateway",
                    "type": "REST API",
                    "purpose": "Process customer payments",
                    "requirements": "PCI DSS compliant with multiple payment methods"
                },
                {
                    "name": "Shipping Integration",
                    "type": "REST API",
                    "purpose": "Calculate shipping and track packages",
                    "requirements": "Real-time shipping rates and tracking updates"
                },
                {
                    "name": "Inventory Management",
                    "type": "REST API",
                    "purpose": "Sync product inventory",
                    "requirements": "Real-time inventory updates with backorder handling"
                }
            ],
            "Government": [
                {
                    "name": "Citizen Identity API",
                    "type": "REST API",
                    "purpose": "Verify citizen identity",
                    "requirements": "FISMA compliant identity verification with privacy controls"
                },
                {
                    "name": "Document Management",
                    "type": "REST API",
                    "purpose": "Store and retrieve official documents",
                    "requirements": "Section 508 accessible with digital signature support"
                }
            ]
        }
        
        # Get domain-specific integrations or default
        integrations = domain_integrations.get(domain, [
            {
                "name": "Payment Gateway",
                "type": "REST API",
                "purpose": "Process payments",
                "requirements": "Standard payment processing with error handling"
            },
            {
                "name": "Email Service",
                "type": "REST API",
                "purpose": "Send notifications",
                "requirements": "Email sending with templates and tracking"
            }
        ])
        
        # Add scale-specific integrations
        if scale in ["Large", "Enterprise"]:
            integrations.extend([
                {
                    "name": "Message Queue Integration",
                    "type": "Message Queue",
                    "purpose": "Asynchronous processing",
                    "requirements": "High-throughput message processing with retry mechanisms"
                },
                {
                    "name": "Analytics Integration",
                    "type": "REST API",
                    "purpose": "Business intelligence and reporting",
                    "requirements": "Real-time analytics with data aggregation"
                }
            ])
        
        return integrations
    
    def _create_default_integration_files(self, 
                                      integration_points: List[Dict[str, Any]],
                                      backend_language: str,
                                      backend_framework: str) -> List[CodeFile]:
        """
        Create default integration files when generation fails.
        
        Args:
            integration_points: List of integration points
            backend_language: Backend language name
            backend_framework: Backend framework name
            
        Returns:
            List of CodeFile objects with default content
        """
        default_files = []
        
        if not integration_points:
            integration_points = self._create_default_integration_points("General", "Small")
        
        for integration in integration_points:
            service_name = integration.get("name", "DefaultService")
            service_slug = service_name.lower().replace(" ", "_").replace("-", "_")
              # Determine file extension based on language
            if backend_language.lower() in ["python", "py"]:
                ext = "py"
                comment = "#"
            elif backend_language.lower() in ["javascript", "js", "typescript", "ts"]:
                ext = "js" if backend_language.lower() in ["javascript", "js"] else "ts"
                comment = "//"
            elif backend_language.lower() in ["java"]:
                ext = "java"
                comment = "//"
            else:
                ext = "txt"
                comment = "#"
            
            # Create service client file
            service_content = self._create_default_service_content(
                service_name, integration, backend_language, ext, comment)
            
            default_files.append(CodeFile(
                file_path=f"src/integrations/services/{service_slug}_service.{ext}",
                code=service_content
            ))
              # Create adapter file
            adapter_content = self._create_default_adapter_content(
                service_name, integration, backend_language, ext, comment)
            
            default_files.append(CodeFile(
                file_path=f"src/integrations/adapters/{service_slug}_adapter.{ext}",
                code=adapter_content
            ))
            
            # Create config file
            config_content = self._create_default_config_content(
                service_name, integration, backend_language, backend_framework)
            
            config_ext = self._get_config_extension(backend_framework)
            default_files.append(CodeFile(
                file_path=f"src/config/{service_slug}_config.{config_ext}",
                code=config_content
            ))
            
            # Create example usage file
            example_content = self._create_default_example_content(
                service_name, integration, backend_language, ext, comment)
            
            default_files.append(CodeFile(
                file_path=f"src/examples/{service_slug}_example.{ext}",
                code=example_content
            ))
        
        return default_files
    
    def _create_default_service_content(self, 
                                 service_name: str, 
                                 integration: Dict[str, Any],
                                 language: str,
                                 ext: str,
                                 comment: str) -> str:
        """
        Create default service client content.
        
        Args:
            service_name: Integration service name
            integration: Integration point dictionary
            language: Programming language
            ext: File extension
            comment: Comment symbol for the language
            
        Returns:
            Default service client content
        """
        service_type = integration.get("type", "REST API")
        purpose = integration.get("purpose", "External integration")
        
        if language.lower() in ["python", "py"]:
            return f"""{comment} {service_name} Integration Service
    {comment} Purpose: {purpose}
    {comment} Type: {service_type}
    {comment} Generated by Integration Generator Agent (default template)

    import requests
    import logging
    import time
    import os
    from typing import Dict, Any, Optional

    logger = logging.getLogger(__name__)

    class {service_name.replace(' ', '')}Service:
        \"\"\"
        Client for {service_name} integration. 
        Handles API communication and error handling.
        \"\"\"
        
        def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
            \"\"\"
            Initialize the {service_name} service client.
            
            Args:
                api_key: API key for authentication (defaults to environment variable)
                base_url: Base URL for API (defaults to environment variable)
            \"\"\"
            self.api_key = api_key or os.environ.get('{service_name.upper().replace(' ', '_')}_API_KEY')
            self.base_url = base_url or os.environ.get('{service_name.upper().replace(' ', '_')}_URL', 'https://api.example.com')
            self.session = requests.Session()
            self.max_retries = 3
            
            if not self.api_key:
                logger.warning("{service_name} API key not provided")
        
        def _handle_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
            \"\"\"
            Handle API request with error handling and retries.
            
            Args:
                method: HTTP method
                endpoint: API endpoint
                **kwargs: Additional request parameters
                
            Returns:
                Response data
            \"\"\"
            url = f"{{self.base_url}}/{{endpoint.lstrip('/')}}"
            headers = kwargs.get('headers', {{}})
            headers['Authorization'] = f'Bearer {{self.api_key}}'
            headers['Content-Type'] = 'application/json'
            kwargs['headers'] = headers
            
            retries = 0
            while retries < self.max_retries:
                try:
                    response = self.session.request(method, url, **kwargs)
                    response.raise_for_status()
                    return response.json()
                except requests.exceptions.RequestException as e:
                    retries += 1
                    if retries >= self.max_retries:
                        logger.error(f"Failed request to {service_name} API: {{e}}")
                        raise
                    logger.warning(f"Retrying {service_name} API request ({{retries}}/{{self.max_retries}})")
                    time.sleep(1)
        
        def get_data(self, resource_id: str) -> Dict[str, Any]:
            \"\"\"
            Get data from {service_name}.
            
            Args:
                resource_id: ID of the resource to fetch
                
            Returns:
                Resource data
            \"\"\"
            return self._handle_request('GET', f'resource/{{resource_id}}')
        
        def create_resource(self, data: Dict[str, Any]) -> Dict[str, Any]:
            \"\"\"
            Create a new resource in {service_name}.
            
            Args:
                data: Resource data
                
            Returns:
                Created resource data
            \"\"\"
            return self._handle_request('POST', 'resource', json=data)
    """
        elif language.lower() in ["javascript", "js", "typescript", "ts"]:
            return f"""{comment} {service_name} Integration Service
    {comment} Purpose: {purpose}
    {comment} Type: {service_type}
    {comment} Generated by Integration Generator Agent (default template)

    import axios from 'axios';

    class {service_name.replace(' ', '')}Service {{
    constructor(apiKey = process.env.{service_name.toUpperCase().replace(' ', '_')}_API_KEY,
                baseUrl = process.env.{service_name.toUpperCase().replace(' ', '_')}_URL || 'https://api.example.com') {{
        this.apiKey = apiKey;
        this.baseUrl = baseUrl;
        this.maxRetries = 3;
        
        this.client = axios.create({{
        baseURL: this.baseUrl,
        headers: {{
            'Authorization': `Bearer ${{this.apiKey}}`,
            'Content-Type': 'application/json'
        }}
        }});
        
        // Add response interceptor for error handling
        this.client.interceptors.response.use(
        response => response,
        error => this.handleError(error)
        );
    }}
    
    async handleError(error) {{
        if (error.response) {{
        console.error(`{service_name} API Error: ${{error.response.status}} ${{error.response.statusText}}`);
        throw error;
        }} else if (error.request) {{
        console.error(`{service_name} API Request Error: No response received`);
        throw error;
        }} else {{
        console.error(`{service_name} API Error: ${{error.message}}`);
        throw error;
        }}
    }}
    
    async getData(resourceId) {{
        try {{
        const response = await this.client.get(`/resource/${{resourceId}}`);
        return response.data;
        }} catch (error) {{
        console.error(`Error fetching data from {service_name}: ${{error.message}}`);
        throw error;
        }}
    }}
    
    async createResource(data) {{
        try {{
        const response = await this.client.post('/resource', data);
        return response.data;
        }} catch (error) {{
        console.error(`Error creating resource in {service_name}: ${{error.message}}`);
        throw error;
        }}
    }}
    }}

    export default {service_name.replace(' ', '')}Service;
    """
        else:
            return f"{comment} Default {service_name} Integration Service\n{comment} Purpose: {purpose}\n{comment} Type: {service_type}\n"
    
    def _create_default_adapter_content(self, 
                                 service_name: str, 
                                 integration: Dict[str, Any],
                                 language: str,
                                 ext: str,
                                 comment: str) -> str:
        """
        Create default adapter class content.
        
        Args:
            service_name: Integration service name
            integration: Integration point dictionary
            language: Programming language
            ext: File extension
            comment: Comment symbol for the language
            
        Returns:
            Default adapter class content
        """
        service_type = integration.get("type", "REST API")
        purpose = integration.get("purpose", "External integration")
        
        if language.lower() in ["python", "py"]:
            return f"""{comment} {service_name} Adapter
    {comment} Purpose: {purpose}
    {comment} Type: {service_type}
    {comment} Generated by Integration Generator Agent (default template)

    from typing import Dict, Any, List, Optional
    from .services.{service_name.lower().replace(' ', '_')}_service import {service_name.replace(' ', '')}Service

    class {service_name.replace(' ', '')}Adapter:
        \"\"\"
        Adapter for {service_name} integration.
        Provides a clean interface to the application for {service_name} operations.
        \"\"\"
        
        def __init__(self, service: Optional[{service_name.replace(' ', '')}Service] = None):
            \"\"\"
            Initialize the adapter with an optional service instance.
            
            Args:
                service: Optional service instance for dependency injection
            \"\"\"
            self.service = service or {service_name.replace(' ', '')}Service()
        
        def get_resource(self, resource_id: str) -> Dict[str, Any]:
            \"\"\"
            Get a resource by ID with standardized format.
            
            Args:
                resource_id: Resource ID
                
            Returns:
                Standardized resource data
            \"\"\"
            try:
                raw_data = self.service.get_data(resource_id)
                return {{
                    "success": True,
                    "data": self._format_resource(raw_data),
                    "error": None
                }}
            except Exception as e:
                # Log and standardize error response
                return {{
                    "success": False,
                    "error": str(e),
                    "data": None
                }}
        
        def create_resource(self, resource_data: Dict[str, Any]) -> Dict[str, Any]:
            \"\"\"
            Create a new resource with standardized format.
            
            Args:
                resource_data: Resource data to create
                
            Returns:
                Standardized creation result
            \"\"\"
            try:
                # Validate data first
                self._validate_resource_data(resource_data)
                
                # Transform data to API format
                api_data = self._transform_to_api_format(resource_data)
                
                # Call service
                result = self.service.create_resource(api_data)
                
                return {{
                    "success": True,
                    "data": self._format_resource(result),
                    "error": None
                }}
            except ValueError as e:
                return {{
                    "success": False,
                    "error": f"Validation error: {{str(e)}}",
                    "data": None
                }}
            except Exception as e:
                return {{
                    "success": False,
                    "error": f"Error creating resource: {{str(e)}}",
                    "data": None
                }}
        
        def _format_resource(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
            \"\"\"
            Format raw API response to standardized format.
            
            Args:
                raw_data: Raw API response
                
            Returns:
                Standardized data format
            \"\"\"
            # Implement transformation logic here
            return {{
                "id": raw_data.get("id"),
                "name": raw_data.get("name"),
                "status": raw_data.get("status"),
                # Add more fields as needed
                "created_at": raw_data.get("created_at"),
                "raw_data": raw_data  # Include raw data for reference
            }}
        
        def _validate_resource_data(self, data: Dict[str, Any]) -> None:
            \"\"\"
            Validate resource data before sending to API.
            
            Args:
                data: Resource data to validate
                
            Raises:
                ValueError: If validation fails
            \"\"\"
            required_fields = ["name"]
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Missing required field: {{field}}")
        
        def _transform_to_api_format(self, data: Dict[str, Any]) -> Dict[str, Any]:
            \"\"\"
            Transform application data to API format.
            
            Args:
                data: Application data
                
            Returns:
                API-formatted data
            \"\"\"
            # Implement transformation logic here
            return {{
                "name": data.get("name"),
                # Transform other fields as needed
            }}
    """
        elif language.lower() in ["javascript", "js", "typescript", "ts"]:
            return f"""{comment} {service_name} Adapter
    {comment} Purpose: {purpose}
    {comment} Type: {service_type}
    {comment} Generated by Integration Generator Agent (default template)

    import {service_name.replace(' ', '')}Service from './services/{service_name.toLowerCase().replace(' ', '_')}_service';

    class {service_name.replace(' ', '')}Adapter {{
    constructor(service = null) {{
        this.service = service || new {service_name.replace(' ', '')}Service();
    }}
    
    /**
    * Get a resource by ID with standardized format
    * 
    * @param {{string}} resourceId - Resource ID
    * @returns {{Promise<Object>}} Standardized resource data
    */
    async getResource(resourceId) {{
        try {{
        const rawData = await this.service.getData(resourceId);
        return {{
            success: true,
            data: this._formatResource(rawData),
            error: null
        }};
        }} catch (error) {{
        console.error(`Error in {service_name} adapter: ${{error.message}}`);
        return {{
            success: false,
            data: null,
            error: error.message
        }};
        }}
    }}
    
    /**
    * Create a new resource with standardized format
    * 
    * @param {{Object}} resourceData - Resource data to create
    * @returns {{Promise<Object>}} Standardized creation result
    */
    async createResource(resourceData) {{
        try {{
        // Validate data first
        this._validateResourceData(resourceData);
        
        // Transform data to API format
        const apiData = this._transformToApiFormat(resourceData);
        
        // Call service
        const result = await this.service.createResource(apiData);
        
        return {{
            success: true,
            data: this._formatResource(result),
            error: null
        }};
        }} catch (error) {{
        return {{
            success: false,
            data: null,
            error: error.message
        }};
        }}
    }}
    
    /**
    * Format raw API response to standardized format
    * 
    * @private
    * @param {{Object}} rawData - Raw API response
    * @returns {{Object}} Standardized data format
    */
    _formatResource(rawData) {{
        return {{
        id: rawData.id,
        name: rawData.name,
        status: rawData.status,
        createdAt: rawData.created_at || rawData.createdAt,
        rawData: rawData // Include raw data for reference
        }};
    }}
    
    /**
    * Validate resource data before sending to API
    * 
    * @private
    * @param {{Object}} data - Resource data to validate
    * @throws {{Error}} If validation fails
    */
    _validateResourceData(data) {{
        const requiredFields = ['name'];
        for (const field of requiredFields) {{
        if (!(field in data)) {{
            throw new Error(`Missing required field: ${{field}}`);
        }}
        }}
    }}
    
    /**
    * Transform application data to API format
    * 
    * @private
    * @param {{Object}} data - Application data
    * @returns {{Object}} API-formatted data
    */
    _transformToApiFormat(data) {{
        return {{
        name: data.name,
        // Transform other fields as needed
        }};
    }}
    }}

    export default {service_name.replace(' ', '')}Adapter;
    """
        else:
            return f"{comment} Default {service_name} Adapter\n{comment} Purpose: {purpose}\n{comment} Type: {service_type}\n"
        
    def _create_default_config_content(self, 
                                    service_name: str, 
                                    integration: Dict[str, Any],
                                    language: str,
                                    framework: str) -> str:
        """
        Create default configuration content.
        
        Args:
            service_name: Integration service name
            integration: Integration point dictionary
            language: Programming language
            framework: Backend framework
            
        Returns:
            Default configuration content
        """
        service_type = integration.get("type", "REST API")
        purpose = integration.get("purpose", "External integration")
        service_slug = service_name.upper().replace(" ", "_")
        
        if language.lower() in ["python", "py"]:
            if framework.lower() in ["django", "flask"]:
                return f"""# {service_name} Configuration
# Purpose: {purpose}
# Type: {service_type}
# Generated by Integration Generator Agent (default template)

# API Connection
{service_slug}_API_KEY = "your_api_key_here"  # Should be stored in environment variable
{service_slug}_URL = "https://api.example.com/v1"
{service_slug}_TIMEOUT = 30  # Request timeout in seconds

# Request Configuration
{service_slug}_MAX_RETRIES = 3
{service_slug}_RETRY_DELAY = 1  # Delay between retries in seconds
{service_slug}_USER_AGENT = "YourApp/1.0"

# Rate Limiting
{service_slug}_RATE_LIMIT_REQUESTS = 100
{service_slug}_RATE_LIMIT_PERIOD = 60  # Period in seconds

# Logging
{service_slug}_LOG_LEVEL = "INFO"

# Cache Configuration
{service_slug}_CACHE_ENABLED = True
{service_slug}_CACHE_TTL = 300  # Time to live in seconds
"""
            else:
                return f"""# {service_name} Configuration
# Purpose: {purpose}
# Type: {service_type}
# Generated by Integration Generator Agent (default template)

# Example .env configuration

{service_slug}_API_KEY=your_api_key_here
{service_slug}_URL=https://api.example.com/v1
{service_slug}_TIMEOUT=30
{service_slug}_MAX_RETRIES=3
{service_slug}_RETRY_DELAY=1
{service_slug}_RATE_LIMIT_REQUESTS=100
{service_slug}_RATE_LIMIT_PERIOD=60
{service_slug}_LOG_LEVEL=INFO
{service_slug}_CACHE_ENABLED=true
{service_slug}_CACHE_TTL=300
"""
        elif language.lower() in ["javascript", "js", "typescript", "ts"]:
            if framework.lower() in ["express", "nestjs", "node"]:
                return f"""/**
 * {service_name} Configuration
 * Purpose: {purpose}
 * Type: {service_type}
 * Generated by Integration Generator Agent (default template)
 */

module.exports = {{
  apiKey: process.env.{service_slug}_API_KEY || 'your_api_key_here',
  baseUrl: process.env.{service_slug}_URL || 'https://api.example.com/v1',
  timeout: parseInt(process.env.{service_slug}_TIMEOUT || '30', 10),
  
  // Request configuration
  maxRetries: parseInt(process.env.{service_slug}_MAX_RETRIES || '3', 10),
  retryDelay: parseInt(process.env.{service_slug}_RETRY_DELAY || '1', 10),
  userAgent: process.env.{service_slug}_USER_AGENT || 'YourApp/1.0',
  
  // Rate limiting
  rateLimit: {{
    requests: parseInt(process.env.{service_slug}_RATE_LIMIT_REQUESTS || '100', 10),
    period: parseInt(process.env.{service_slug}_RATE_LIMIT_PERIOD || '60', 10)
  }},
  
  // Logging
  logLevel: process.env.{service_slug}_LOG_LEVEL || 'info',
  
  // Cache configuration
  cache: {{
    enabled: process.env.{service_slug}_CACHE_ENABLED === 'true',
    ttl: parseInt(process.env.{service_slug}_CACHE_TTL || '300', 10)
  }}
}};
"""
            else:
                return f"""// {service_name} Configuration
// Purpose: {purpose}
// Type: {service_type}
// Generated by Integration Generator Agent (default template)

// Example .env configuration

{service_slug}_API_KEY=your_api_key_here
{service_slug}_URL=https://api.example.com/v1
{service_slug}_TIMEOUT=30
{service_slug}_MAX_RETRIES=3
{service_slug}_RETRY_DELAY=1
{service_slug}_RATE_LIMIT_REQUESTS=100
{service_slug}_RATE_LIMIT_PERIOD=60
{service_slug}_LOG_LEVEL=info
{service_slug}_CACHE_ENABLED=true
{service_slug}_CACHE_TTL=300
"""
        else:
            return f"# Default {service_name} Configuration\n# Purpose: {purpose}\n# Type: {service_type}\n"
    
    def _create_default_example_content(self, 
                                 service_name: str, 
                                 integration: Dict[str, Any],
                                 language: str,
                                 ext: str,
                                 comment: str) -> str:
        """
        Create default example usage content.
        
        Args:
            service_name: Integration service name
            integration: Integration point dictionary
            language: Programming language
            ext: File extension
            comment: Comment symbol for the language
            
        Returns:
            Default example usage content
        """
        service_type = integration.get("type", "REST API")
        purpose = integration.get("purpose", "External integration")
        
        if language.lower() in ["python", "py"]:
            return f"""{comment} {service_name} Example Usage
    {comment} Purpose: {purpose}
    {comment} Type: {service_type}
    {comment} Generated by Integration Generator Agent (default template)

    from integrations.adapters.{service_name.lower().replace(' ', '_')}_adapter import {service_name.replace(' ', '')}Adapter

    def demonstrate_{service_name.lower().replace(' ', '_')}_integration():
        \"\"\"
        Demonstrate {service_name} integration usage.
        \"\"\"
        adapter = {service_name.replace(' ', '')}Adapter()
        
        # Example: Get a resource
        resource_id = "example-resource-id"
        print(f"Fetching resource {{resource_id}} from {service_name}...")
        result = adapter.get_resource(resource_id)
        
        if result["success"]:
            print(f"Successfully fetched resource: {{result['data']['name']}}")
        else:
            print(f"Failed to fetch resource: {{result['error']}}")
        
        # Example: Create a resource
        new_resource = {{
            "name": "Example Resource",
            "description": "This is an example resource created via the {service_name} adapter"
        }}
        
        print(f"Creating new resource in {service_name}...")
        create_result = adapter.create_resource(new_resource)
        
        if create_result["success"]:
            print(f"Successfully created resource: {{create_result['data']['id']}}")
        else:
            print(f"Failed to create resource: {{create_result['error']}}")

    if __name__ == "__main__":
        demonstrate_{service_name.lower().replace(' ', '_')}_integration()
    """
        elif language.lower() in ["javascript", "js", "typescript", "ts"]:
            return f"""{comment} {service_name} Example Usage
    {comment} Purpose: {purpose}
    {comment} Type: {service_type}
    {comment} Generated by Integration Generator Agent (default template)

    import {service_name.replace(' ', '')}Adapter from '../integrations/adapters/{service_name.toLowerCase().replace(' ', '_')}_adapter';

    /**
    * Demonstrate {service_name} integration usage
    */
    async function demonstrate{service_name.replace(' ', '')}Integration() {{
    const adapter = new {service_name.replace(' ', '')}Adapter();
    
    // Example: Get a resource
    const resourceId = 'example-resource-id';
    console.log(`Fetching resource ${{resourceId}} from {service_name}...`);
    
    try {{
        const result = await adapter.getResource(resourceId);
        
        if (result.success) {{
        console.log(`Successfully fetched resource: ${{result.data.name}}`);
        }} else {{
        console.log(`Failed to fetch resource: ${{result.error}}`);
        }}
        
        // Example: Create a resource
        const newResource = {{
        name: 'Example Resource',
        description: 'This is an example resource created via the {service_name} adapter'
        }};
        
        console.log(`Creating new resource in {service_name}...`);
        const createResult = await adapter.createResource(newResource);
        
        if (createResult.success) {{
        console.log(`Successfully created resource: ${{createResult.data.id}}`);
        }} else {{
        console.log(`Failed to create resource: ${{createResult.error}}`);
        }}
    }} catch (error) {{
        console.error(`Error in {service_name} integration example: ${{error.message}}`);
    }}
    }}

    // Execute the example
    demonstrate{service_name.replace(' ', '')}Integration().catch(error => {{
    console.error(`Unhandled error in example: ${{error.message}}`);
    }});
    """
        else:
            return f"{comment} Default {service_name} Example Usage\n{comment} Purpose: {purpose}\n{comment} Type: {service_type}\n"
    
    def _setup_message_subscriptions(self) -> None:
        """Set up message bus subscriptions if available"""
        if self.message_bus:
            self.message_bus.subscribe("backend.generated", self._handle_backend_ready)
            self.message_bus.subscribe("frontend.generated", self._handle_frontend_ready)
            self.log_info(f"{self.agent_name} subscribed to backend.generated and frontend.generated events")
    
    def _handle_backend_ready(self, message: Dict[str, Any]) -> None:
        """Handle backend generation completion messages"""
        self.log_info("Received backend generation complete event")
        
        payload = message.get("payload", {})
        if payload.get("status") == "success":
            # Store backend API information for integration generation
            if "api_endpoints" in payload:
                self.working_memory["backend_apis"] = payload["api_endpoints"]
                self.log_info(f"Backend APIs ready for integration: {len(payload['api_endpoints'])} endpoints")
            
            if "files" in payload:
                self.working_memory["backend_files"] = payload["files"]
    
    def _handle_frontend_ready(self, message: Dict[str, Any]) -> None:
        """Handle frontend generation completion messages"""
        self.log_info("Received frontend generation complete event")
        
        payload = message.get("payload", {})
        if payload.get("status") == "success":
            # Store frontend component information for integration
            if "files" in payload:
                self.working_memory["frontend_files"] = payload["files"]
                self.log_info(f"Frontend files ready for integration: {len(payload['files'])} files")
                
            # Check if we have both backend and frontend ready
            if "backend_apis" in self.working_memory and "frontend_files" in self.working_memory:
                self.log_info("Both backend and frontend are ready - integration can proceed")


    def _extract_domain(self, requirements_analysis: Dict, tech_stack: Dict, system_design: Dict) -> str:
        """Extract domain information from requirements analysis."""
        try:
            # Try requirements analysis first
            if requirements_analysis and isinstance(requirements_analysis, dict):
                domain = requirements_analysis.get("domain") or requirements_analysis.get("industry")
                if domain:
                    return domain
                    
                # Check for business requirements
                business_reqs = requirements_analysis.get("business_requirements", {})
                if isinstance(business_reqs, dict) and "domain" in business_reqs:
                    return business_reqs["domain"]
            
            # Try system design
            if system_design and isinstance(system_design, dict):
                domain = system_design.get("domain") or system_design.get("industry")
                if domain:
                    return domain
            
            # Try tech stack
            if tech_stack and isinstance(tech_stack, dict):
                domain = tech_stack.get("domain") or tech_stack.get("industry")
                if domain:
                    return domain
            
            return "General"
            
        except Exception as e:
            self.log_warning(f"Error extracting domain: {e}")
            return "General"

    def _extract_scale(self, requirements_analysis: Dict, system_design: Dict) -> str:
        """Extract scale information from requirements analysis and system design."""
        try:
            # Try requirements analysis
            if requirements_analysis and isinstance(requirements_analysis, dict):
                scale = requirements_analysis.get("scale") or requirements_analysis.get("expected_load")
                if scale:
                    return self._normalize_scale(scale)
                    
                # Check non-functional requirements
                nfr = requirements_analysis.get("non_functional_requirements", {})
                if isinstance(nfr, dict):
                    scale = nfr.get("scalability") or nfr.get("performance", {}).get("expected_load")
                    if scale:
                        return self._normalize_scale(scale)
            
            # Try system design
            if system_design and isinstance(system_design, dict):
                scale = system_design.get("scale") or system_design.get("expected_scale")
                if scale:
                    return self._normalize_scale(scale)
            
            return "Small"
            
        except Exception as e:
            self.log_warning(f"Error extracting scale: {e}")
            return "Small"

    def _extract_compliance_requirements(self, requirements_analysis: Dict, system_design: Dict) -> str:
        """Extract compliance requirements from requirements analysis and system design."""
        try:
            compliance_list = []
            
            # Try requirements analysis
            if requirements_analysis and isinstance(requirements_analysis, dict):
                compliance = requirements_analysis.get("compliance_requirements", [])
                if isinstance(compliance, list):
                    compliance_list.extend(compliance)
                elif isinstance(compliance, str):
                    compliance_list.append(compliance)
                    
                # Check regulatory requirements
                regulatory = requirements_analysis.get("regulatory_requirements", [])
                if isinstance(regulatory, list):
                    compliance_list.extend(regulatory)
                elif isinstance(regulatory, str):
                    compliance_list.append(regulatory)
            
            # Try system design
            if system_design and isinstance(system_design, dict):
                compliance = system_design.get("compliance", [])
                if isinstance(compliance, list):
                    compliance_list.extend(compliance)
                elif isinstance(compliance, str):
                    compliance_list.append(compliance)
            
            return ", ".join(set(compliance_list)) if compliance_list else "None"
            
        except Exception as e:
            self.log_warning(f"Error extracting compliance requirements: {e}")
            return "None"

    def _normalize_scale(self, scale: str) -> str:
        """Normalize scale values to standard terms."""
        if not isinstance(scale, str):
            scale = str(scale)
            
        scale_lower = scale.lower()
        
        if any(term in scale_lower for term in ["small", "startup", "prototype", "poc"]):
            return "Small"
        elif any(term in scale_lower for term in ["medium", "moderate", "growing"]):
            return "Medium"
        elif any(term in scale_lower for term in ["large", "high", "enterprise"]):
            return "Large"
        elif any(term in scale_lower for term in ["massive", "global", "enterprise-scale"]):
            return "Enterprise"
        else:
            return "Small"  # Default

    def _get_domain_integration_requirements(self, domain: str, integration_points: List[Dict]) -> str:
        """Get domain-specific integration requirements."""
        requirements = {
            "Healthcare": [
                "HIPAA-compliant data transmission and storage",
                "HL7 FHIR standard compatibility for health data exchange",
                "Patient consent management and audit logging",
                "Secure PHI (Protected Health Information) handling"
            ],
            "Finance": [
                "PCI DSS compliance for payment card data",
                "SOX compliance for financial reporting",
                "Real-time fraud detection and prevention",
                "Secure API authentication with multi-factor authentication"
            ],
            "E-commerce": [
                "PCI DSS payment processing security",
                "Real-time inventory synchronization",
                "Order fulfillment and shipping integrations",
                "Customer data protection and privacy"
            ],
            "Government": [
                "FISMA security controls implementation",
                "Section 508 accessibility compliance",
                "Freedom of Information Act (FOIA) compliance",
                "Citizen identity verification systems"
            ]
        }
        
        domain_reqs = requirements.get(domain, [
            "Standard API security with authentication",
            "Data validation and error handling",
            "Rate limiting and throttling",
            "Comprehensive logging and monitoring"
        ])
        
        return "\n".join([f"- {req}" for req in domain_reqs])

    def _get_scale_integration_considerations(self, scale: str, integration_points: List[Dict]) -> str:
        """Get scale-specific integration considerations."""
        considerations = {
            "Small": [
                "Simple REST API integrations with basic retry logic",
                "Synchronous processing for most operations",
                "Basic error handling and logging"
            ],
            "Medium": [
                "Asynchronous processing for non-critical operations",
                "Connection pooling and resource management",
                "Circuit breaker patterns for external service failures"
            ],
            "Large": [
                "Event-driven architecture with message queues",
                "Distributed caching and data consistency patterns",
                "Advanced circuit breakers and bulkhead patterns"
            ],
            "Enterprise": [
                "Enterprise service bus (ESB) integration patterns",
                "Saga patterns for distributed transactions",
                "Advanced monitoring and observability"
            ]
        }
        
        scale_items = considerations.get(scale, considerations["Small"])
        return "\n".join([f"- {item}" for item in scale_items])

    def _get_security_compliance_requirements(self, compliance_requirements: str, domain: str) -> str:
        """Get security and compliance-specific integration requirements."""
        security_reqs = []
        
        # Domain-specific security requirements
        domain_security = {
            "Healthcare": [
                "End-to-end encryption for all PHI transmissions",
                "Audit logging for all data access and modifications",
                "Role-based access controls with minimum necessary principle"
            ],
            "Finance": [
                "Tokenization of sensitive financial data",
                "Real-time transaction monitoring and fraud detection",
                "Secure multi-party authentication protocols"
            ],
            "Government": [
                "FIPS 140-2 compliant cryptographic modules",
                "Multi-factor authentication for all access",
                "Audit trails for all citizen data interactions"
            ]
        }
        
        if domain in domain_security:
            security_reqs.extend(domain_security[domain])
        
        # Compliance-specific requirements
        if compliance_requirements and compliance_requirements != "None":
            if "GDPR" in compliance_requirements:
                security_reqs.extend([
                    "Data minimization and purpose limitation",
                    "Consent management and withdrawal mechanisms"
                ])
            if "HIPAA" in compliance_requirements:
                security_reqs.extend([
                    "Business Associate Agreement (BAA) compliance",
                    "Breach notification and incident response"
                ])
            if "PCI DSS" in compliance_requirements:
                security_reqs.extend([
                    "Secure payment card data transmission",
                    "Regular vulnerability scanning and testing"
                ])
        
        # General security requirements if none specified
        if not security_reqs:
            security_reqs = [
                "TLS 1.3 encryption for all API communications",
                "OAuth 2.0 or API key authentication",
                "Input validation and sanitization",
                "Rate limiting and DDoS protection"
            ]
        
        return "\n".join([f"- {req}" for req in security_reqs])
    
    def _get_config_extension(self, backend_framework: str) -> str:
        """Get appropriate configuration file extension based on backend framework."""
        framework_extensions = {
            "django": "py",
            "flask": "py", 
            "fastapi": "py",
            "express": "js",
            "nestjs": "js",
            "spring": "properties",
            "laravel": "php",
            "rails": "rb",
            "gin": "yaml",
            "echo": "yaml"
        }
        
        # Default to json for unknown frameworks
        return framework_extensions.get(backend_framework.lower(), "json")
    
    def _create_default_tech_stack(self) -> Dict[str, Any]:
        """Create default tech stack when input is invalid."""
        return {
            "backend": {
                "language": "Python",
                "framework": "FastAPI"
            },
            "frontend": {
                "framework": "React",
                "language": "TypeScript"
            },
            "database": {
                "type": "postgresql",
                "version": "14"
            },
            "integrations": {
                "payment": "Stripe",
                "email": "SendGrid"
            }
        }
    
    def _create_default_system_design(self) -> Dict[str, Any]:
        """Create default system design when input is invalid."""
        return {
            "architecture": "Microservices",
            "integration_points": [
                {
                    "name": "Payment Gateway",
                    "type": "REST API",
                    "purpose": "Process payments",
                    "requirements": "Secure payment processing"
                },
                {
                    "name": "Email Service",
                    "type": "REST API", 
                    "purpose": "Send notifications",
                    "requirements": "Reliable email delivery"
                }
            ]
        }

    def run(self, work_item: WorkItem, state: Dict[str, Any]) -> CodeGenerationOutput:
        """
        Generates DevOps/integration artifacts for a single work item.
        """
        logger.info(f"IntegrationGenerator starting work item: {work_item.id} - {work_item.description}")

        prompt = self._create_work_item_prompt(work_item, state)
        
        response = self.llm.invoke(prompt)
        content = response.content if hasattr(response, 'content') else str(response)

        generated_files = parse_llm_output_into_files(content)

        return CodeGenerationOutput(
            generated_files=[FileOutput(**f) for f in generated_files],
            summary=f"Generated {len(generated_files)} files for integration work item {work_item.id}."
        )

    def _create_work_item_prompt(self, work_item: WorkItem, state: Dict[str, Any]) -> str:
        # We can provide the whole state as context, but let's summarize for the prompt
        tech_stack_summary = json.dumps(state.get("tech_stack_recommendation", {}), indent=2)
        system_design_summary = json.dumps(state.get("system_design", {}), indent=2)

        return f"""
        You are a senior DevOps engineer specializing in CI/CD, containerization, and cloud infrastructure.
        Your task is to implement a single work item related to project integration and deployment.

        **System Context:**
        - Tech Stack:
        ```json
        {tech_stack_summary}
        ```
        - System Design:
        ```json
        {system_design_summary}
        ```

        **Current Work Item: {work_item.id}**
        - **Description:** {work_item.description}
        - **Acceptance Criteria:**
        {chr(10).join(f'  - {c}' for c in work_item.acceptance_criteria)}
        
        **Instructions:**
        1. Write the necessary files (e.g., Dockerfile, docker-compose.yml, .github/workflows/ci.yml) to implement THIS work item.
        2. Adhere to all acceptance criteria.
        3. If the work item involves a script (like a build script), also generate a simple validation script (e.g., a shell script that runs the build script and checks for an exit code).
        4. Your output must be in the multi-file format.

        CRITICAL OUTPUT FORMAT - FOLLOW EXACTLY:
        ### FILE: path/to/your/file.yml
        ```yaml
        # CI/CD Pipeline or Docker Compose content here
        ```

        ### FILE: path/to/your/Dockerfile
        ```dockerfile
        # Dockerfile content here
        ```
        """