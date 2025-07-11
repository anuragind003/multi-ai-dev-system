"""
Architecture Generator Agent - Specialized in generating project structure and architectural foundation code
with deterministic, consistent output focused on best practices and framework conventions.
"""

import json
import os
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path

# Ensure correct import paths
from langchain_core.language_models import BaseLanguageModel
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.retrievers import BaseRetriever

# MODIFIED: Fix import paths - use absolute imports instead of relative imports
import os
import sys
import time
from datetime import datetime
# Add project root to Python path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import base class and utilities
from agents.code_generation.base_code_generator import BaseCodeGeneratorAgent
import monitoring
from tools.code_execution_tool import CodeExecutionTool
from tools.json_handler import JsonHandler
from message_bus import MessageBus
import logging
from models.data_contracts import GeneratedFile, CodeGenerationOutput, WorkItem
from tools.code_generation_utils import parse_llm_output_into_files

# Setup logger
logger = logging.getLogger(__name__)

# Enhanced Memory Management for Architecture Generation
try:
    from enhanced_memory_manager import create_memory_manager, EnhancedSharedProjectMemory
    ENHANCED_MEMORY_AVAILABLE = True
except ImportError:
    ENHANCED_MEMORY_AVAILABLE = False

# RAG Manager for Architecture Generation
try:
    from rag_manager import get_rag_manager
    RAG_MANAGER_AVAILABLE = True
except ImportError:
    RAG_MANAGER_AVAILABLE = False

class ArchitectureGeneratorAgent(BaseCodeGeneratorAgent):
    """
    Specialized Architecture Generator Agent with comprehensive project structure generation,
    configuration file creation, and architectural foundation implementation.
    """
    
    def __init__(self, llm: BaseLanguageModel, memory, temperature: float, output_dir: str, 
                 code_execution_tool: CodeExecutionTool,
                 rag_retriever: Optional[BaseRetriever] = None,
                 message_bus=None):
        
        # Fixed: Proper call to superclass constructor with all required parameters
        super().__init__(
            llm=llm,
            memory=memory,
            agent_name="Architecture Generator Agent",
            temperature=temperature,
            output_dir=output_dir,
            code_execution_tool=code_execution_tool,
            rag_retriever=rag_retriever,
            message_bus=message_bus
        )
        
        # Initialize specialized prompt template
        self._initialize_prompt_templates()
        
        # Initialize RAG context
        self.rag_manager = get_rag_manager() if RAG_MANAGER_AVAILABLE else None
        if self.rag_manager:
            self.logger.info("RAG manager available for enhanced architecture generation")
        else:
            self.logger.warning("RAG manager not available - proceeding without RAG context")
        
        # Setup message bus subscriptions
        self._setup_message_subscriptions()
        
        # Maximum tokens for generation
        self.max_tokens = 8192        
        # Maximum RAG documents to retrieve per query
        self.max_rag_docs = 3
    
    async def arun(self, **kwargs: Any) -> Any:
        """Asynchronous run method required by base class."""
        import asyncio
        work_item = kwargs.get('work_item')
        state = kwargs.get('state', {})
        
        if work_item and state:
            return await asyncio.to_thread(self.run, work_item, state)
        else:
            # Fallback for other argument patterns
            return await asyncio.to_thread(lambda: self.run(**kwargs))
        
    def run(self, work_item: WorkItem, state: Dict[str, Any]) -> CodeGenerationOutput:
        """
        Standardized run method for architecture code generation.
        
        Args:
            work_item: The specific work item to process
            state: The current workflow state containing context
            
        Returns:
            CodeGenerationOutput: Structured architecture code generation results
        """
        logger.info(f"ArchitectureGeneratorAgent processing work item: {work_item.id}")
        
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
                    summary=result.get('summary', f'Generated architecture code for work item {work_item.id}'),
                    status=result.get('status', 'success'),
                    metadata=result.get('metadata', {})
                )
            
            return result
            
        except Exception as e:
            logger.error(f"ArchitectureGeneratorAgent failed for {work_item.id}: {str(e)}")
            return CodeGenerationOutput(
                generated_files=[],
                summary=f"Architecture code generation failed for {work_item.id}: {str(e)}",
                status="error",
                metadata={"error": str(e)}
            )
        
    def _initialize_prompt_templates(self):
        """
        Initialize a single comprehensive prompt template for generating all architecture artifacts.
        """
        multi_file_format = """
        CRITICAL OUTPUT FORMAT - FOLLOW EXACTLY:
        You MUST provide your response as a single block of text with multiple files using this EXACT format:

        ### FILE: filename.ext
        ```filetype
        // Full content of the file goes here
        // Do not include any other text or explanations outside the content
        ```

        ### FILE: another_file.ext
        ```filetype
        // Full content of the second file goes here
        ```

        IMPORTANT RULES:
        1. Start each file with exactly "### FILE: " followed by the relative file path
        2. Use ONLY "filetype" as the code block language identifier  
        3. Do NOT include explanations, comments, or other text between files
        4. File paths should be relative to project root (e.g., "src/main.py", not "./src/main.py")
        5. Generate ALL necessary files for a complete project setup
        
        Files to include:
        - Configuration files (.gitignore, requirements.txt, package.json, etc.)
        - Project setup files (README.md, CONTRIBUTING.md)
        - Base architectural files for the chosen framework
        - Docker configuration (Dockerfile, docker-compose.yml) if applicable
        - Build/deployment configuration files
        """

        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system",
             "You are an expert enterprise software architect specializing in PRODUCTION-READY, "
             "ENTERPRISE-GRADE project architectures with comprehensive DevOps, security, monitoring, "
             "and operational excellence. You create complete architectural foundations that are "
             "immediately deployable to production environments with enterprise security, compliance, "
             "and scalability built-in.\n\n"
             
             "**MANDATORY ENTERPRISE ARCHITECTURE REQUIREMENTS:**\n"
             "You MUST include ALL of the following in every project architecture:\n\n"
             
             "1. **PROJECT STRUCTURE & ORGANIZATION:**\n"
             "   - Clean architecture with proper separation of concerns\n"
             "   - Domain-driven design (DDD) structure where appropriate\n"
             "   - Microservices or modular monolith organization\n"
             "   - Shared libraries and common utilities structure\n"
             "   - Environment-specific configuration management\n"
             "   - Proper package and namespace organization\n"
             "   - Code generation and scaffolding tools\n\n"
             
             "2. **DEVOPS & INFRASTRUCTURE:**\n"
             "   - Complete CI/CD pipeline configurations\n"
             "   - Multi-environment deployment strategies\n"
             "   - Infrastructure as Code (Terraform, CloudFormation)\n"
             "   - Container orchestration (Docker, Kubernetes)\n"
             "   - Service mesh configuration (Istio, Linkerd)\n"
             "   - Load balancing and reverse proxy setup\n"
             "   - Blue-green and canary deployment configs\n\n"
             
             "3. **SECURITY & COMPLIANCE:**\n"
             "   - Security scanning and vulnerability management\n"
             "   - Secret management and encryption at rest/transit\n"
             "   - Authentication and authorization frameworks\n"
             "   - API security and rate limiting configurations\n"
             "   - Compliance validation and audit trails\n"
             "   - Network security and firewall rules\n"
             "   - Data protection and privacy controls\n\n"
             
             "4. **MONITORING & OBSERVABILITY:**\n"
             "   - Comprehensive logging framework setup\n"
             "   - Distributed tracing and metrics collection\n"
             "   - Application performance monitoring (APM)\n"
             "   - Business metrics and KPI dashboards\n"
             "   - Alerting and notification systems\n"
             "   - Health checks and status endpoints\n"
             "   - Error tracking and debugging tools\n\n"
             
             "5. **TESTING & QUALITY:**\n"
             "   - Multi-level testing strategy (unit, integration, e2e)\n"
             "   - Test automation and CI integration\n"
             "   - Code quality and static analysis tools\n"
             "   - Performance and load testing frameworks\n"
             "   - Security testing and penetration testing\n"
             "   - Contract testing and API validation\n"
             "   - Chaos engineering and fault injection\n\n"
             
             "6. **DOCUMENTATION & STANDARDS:**\n"
             "   - Comprehensive technical documentation\n"
             "   - API documentation with OpenAPI/Swagger\n"
             "   - Architecture decision records (ADRs)\n"
             "   - Coding standards and style guides\n"
             "   - Runbooks and operational procedures\n"
             "   - Onboarding and development guides\n"
             "   - Disaster recovery and business continuity\n\n"
             
             "Generate enterprise-grade project architectures that provide a complete foundation "
             "for production-ready applications with operational excellence built-in."),
            ("human",
             "Generate a COMPLETE ENTERPRISE-GRADE project architecture that serves as the foundation "
             "for a production-ready application. This must include comprehensive DevOps, security, "
             "monitoring, and operational excellence built into the architectural foundation.\n\n"
             
             "## Project Context\n"
             "Domain: {domain}\n"
             "Scale: {scale}\n"
             "Compliance Requirements: {compliance_requirements}\n"
             "Tech Stack: {tech_stack_summary}\n"
             "Architecture Pattern: {architecture_pattern}\n\n"
             "System Design Overview: {system_design_overview}\n\n"
             "Full Tech Stack Details:\n{tech_stack_details}\n\n"
             "Full System Design:\n{system_design}\n\n"
             
             "## MANDATORY ENTERPRISE ARCHITECTURE REQUIREMENTS\n"
             "You MUST generate ALL of the following categories of files:\n\n"
             
             "### 1. **PROJECT STRUCTURE & FOUNDATION**\n"
             "   - Clean architecture directory structure with proper separation\n"
             "   - Domain-driven design layout for complex domains\n"
             "   - Shared libraries and utilities organization\n"
             "   - Environment-specific configuration structure\n"
             "   - Package/namespace organization files\n"
             "   - Code generation and scaffolding templates\n\n"
             
             "### 2. **DEVOPS & INFRASTRUCTURE**\n"
             "   - Complete CI/CD pipeline configurations (GitHub Actions, GitLab CI)\n"
             "   - Multi-environment deployment scripts (dev, staging, prod)\n"
             "   - Infrastructure as Code templates (Terraform, CloudFormation)\n"
             "   - Container orchestration configs (Docker, Kubernetes manifests)\n"
             "   - Service mesh configurations (Istio, Linkerd)\n"
             "   - Load balancer and reverse proxy configurations\n"
             "   - Blue-green and canary deployment configurations\n\n"
             
             "### 3. **SECURITY & COMPLIANCE**\n"
             "   - Security scanning and SAST/DAST configurations\n"
             "   - Secret management and vault configurations\n"
             "   - Authentication and authorization framework setup\n"
             "   - API security policies and rate limiting configs\n"
             "   - Compliance validation scripts and audit configurations\n"
             "   - Network security policies and firewall rules\n"
             "   - Data protection and encryption configurations\n\n"
             
             "### 4. **MONITORING & OBSERVABILITY**\n"
             "   - Comprehensive logging framework configurations\n"
             "   - Distributed tracing setup (Jaeger, Zipkin)\n"
             "   - Metrics collection and monitoring (Prometheus, Grafana)\n"
             "   - Application performance monitoring integration\n"
             "   - Business metrics and KPI dashboard configurations\n"
             "   - Alerting and notification system setup\n"
             "   - Health check endpoints and status monitoring\n\n"
             
             "### 5. **TESTING & QUALITY ASSURANCE**\n"
             "   - Multi-level testing framework setup (unit, integration, e2e)\n"
             "   - Test automation and CI integration configurations\n"
             "   - Code quality and static analysis tool configs\n"
             "   - Performance and load testing framework setup\n"
             "   - Security testing and penetration testing configs\n"
             "   - Contract testing and API validation setup\n"
             "   - Chaos engineering and fault injection configurations\n\n"
             
             "### 6. **DOCUMENTATION & STANDARDS**\n"
             "   - Comprehensive technical documentation templates\n"
             "   - API documentation with OpenAPI/Swagger setup\n"
             "   - Architecture decision records (ADR) templates\n"
             "   - Coding standards and style guide configurations\n"
             "   - Operational runbooks and procedure templates\n"
             "   - Developer onboarding and setup guides\n"
             "   - Disaster recovery and business continuity plans\n\n"
             
             "### 7. **BUILD & DEPENDENCY MANAGEMENT**\n"
             "   - Build system configurations with optimization\n"
             "   - Dependency management with security scanning\n"
             "   - Package registry and artifact management\n"
             "   - Version management and semantic versioning\n"
             "   - Release automation and changelog generation\n"
             "   - Environment-specific build configurations\n"
             "   - Performance optimization and bundling configs\n\n"
             
             "## Domain-Specific Requirements\n"
             "{domain_requirements}\n\n"
             
             "## Scale & Performance Considerations\n"
             "{scale_considerations}\n\n"
             
             "## Security & Compliance Requirements\n"
             "{security_compliance_requirements}\n\n"
             
             "## Best Practices & Context\n"
             "{rag_context}\n\n"
             
             "{code_review_feedback}\n\n"
             
             "## OUTPUT REQUIREMENTS\n"
             "Generate a MINIMUM of 25+ files covering all enterprise architecture requirements above.\n"
             "Include proper directory structure with clear separation of concerns. Each configuration\n"
             "file must be production-ready with comprehensive settings and documentation.\n\n"
             
             "Follow this multi-file output format EXACTLY:\n{format_instructions}")
        ])
        
        self.prompt_template = self.prompt_template.partial(format_instructions=multi_file_format)

    def _generate_code(self, llm: BaseLanguageModel, 
                      invoke_config: Dict, 
                      **kwargs) -> Dict[str, Any]:
        """
        Generate complete project architecture in a single step.
        
        Args:
            llm: Language model to use for generation
            invoke_config: Configuration for LLM invocation
            **kwargs: Additional arguments including requirements_analysis, tech_stack, system_design, etc.
            
        Returns:
            Dictionary conforming to the CodeGenerationOutput model
        """
        self.log_info("Starting comprehensive architecture generation")
        start_time = time.time()
        
        # Extract required inputs with validation
        tech_stack = kwargs.get('tech_stack', {})
        system_design = kwargs.get('system_design', {})
        requirements_analysis = kwargs.get('requirements_analysis', {})
        implementation_plan = kwargs.get('implementation_plan', {})
        code_review_feedback = kwargs.get('code_review_feedback')
          # Track if this is a revision based on feedback
        is_revision = code_review_feedback is not None
        generation_type = "revision" if is_revision else "initial generation"
        
        try:
            # Validate inputs with defaults
            if not isinstance(tech_stack, dict):
                self.log_warning("Invalid tech stack - using default")
                # Extract domain first to create appropriate default
                temp_domain = self._extract_domain(requirements_analysis, {}, system_design)
                tech_stack = self._create_default_tech_stack(temp_domain)
                
            if not isinstance(system_design, dict):
                self.log_warning("Invalid system design - using default")
                # Use extracted domain for appropriate default
                system_design = self._create_default_system_design(domain)
            
            # Extract key information from inputs
            domain = self._extract_domain(requirements_analysis, tech_stack, system_design)
            scale = self._extract_scale(requirements_analysis, system_design)
            compliance_requirements = self._extract_compliance_requirements(requirements_analysis, system_design)
            
            tech_stack_summary = self._create_tech_stack_summary(tech_stack)
            architecture_pattern = tech_stack.get("architecture_pattern", "Layered")
            if not architecture_pattern:
                architecture_pattern = self._determine_architecture_pattern(tech_stack, system_design, domain, scale)
            
            # Create domain-aware content
            domain_requirements = self._get_domain_specific_requirements(domain, scale)
            scale_considerations = self._get_scale_considerations(scale, domain)
            security_compliance_requirements = self._get_security_compliance_requirements(compliance_requirements, domain)
            
            # Create concise system design overview
            system_design_overview = self._create_system_design_overview(system_design)
            
            # Get RAG context for architectural best practices with domain and scale awareness
            rag_context = self._get_architecture_rag_context(tech_stack_summary, architecture_pattern, domain, scale)
            
            # Format technical details for prompt
            tech_stack_details = json.dumps(tech_stack, indent=2)
            pruned_system_design = json.dumps(self._prune_system_design(system_design), indent=2)
            
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
              # Set a slightly lower temperature for architecture generation (deterministic)
            adjusted_temp = max(0.1, min(self.default_temperature, 0.2))
            
            # Use binding pattern for temperature
            llm_with_temp = llm.bind(
                temperature=adjusted_temp,
                max_tokens=self.max_tokens
            )
            
            # Add monitoring context
            invoke_config["agent_context"] = f"{self.agent_name}:{architecture_pattern}"
            invoke_config["temperature_used"] = adjusted_temp
            invoke_config["is_revision"] = is_revision
              # Execute LLM call to generate all architecture artifacts
            self.log_info(f"Generating {architecture_pattern} architecture for {domain} domain at {scale} scale")
            response = llm_with_temp.invoke(
                self.prompt_template.format(
                    domain=domain,
                    scale=scale,
                    compliance_requirements=compliance_requirements,
                    tech_stack_summary=tech_stack_summary,
                    architecture_pattern=architecture_pattern,
                    system_design_overview=system_design_overview,
                    tech_stack_details=tech_stack_details,
                    system_design=pruned_system_design,
                    domain_requirements=domain_requirements,
                    scale_considerations=scale_considerations,
                    security_compliance_requirements=security_compliance_requirements,
                    rag_context=rag_context,
                    code_review_feedback=code_review_section
                ),
                config=invoke_config
            )
              # Extract content from response
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Log abbreviated version of the content for debug purposes
            self.log_info(f"LLM response (abbreviated): {content[:500]}...")
            
            # DEBUG: Save the full LLM output to a debug file for analysis
            debug_file_path = os.path.join(self.output_dir, "debug_llm_output.txt")
            try:
                with open(debug_file_path, 'w', encoding='utf-8') as debug_file:
                    debug_file.write(content)
                self.log_info(f"Full LLM output saved to: {debug_file_path}")
            except Exception as debug_error:
                self.log_warning(f"Could not save debug output: {debug_error}")
            
            # Parse the multi-file output
            parsed_files = parse_llm_output_into_files(content)
            
            # Use GeneratedFile objects directly
            generated_files = []
            for parsed_file in parsed_files:

                code_file = GeneratedFile(
                    file_path=parsed_file.file_path,
                    content=parsed_file.content
                )
                generated_files.append(code_file)
            
            # Handle case where parsing fails
            if not generated_files:
                self.log_warning("Failed to parse multi-file output, generating default files")                # Generate default README and other essential files
                generated_files = self._create_default_architecture_files(
                    tech_stack_summary, architecture_pattern, domain, scale
                )
            
            # Create directories first before saving files
            self._create_directories_from_files(generated_files)
              # Create structured output
            output = CodeGenerationOutput(
                files=generated_files,
                summary=f"Generated {len(generated_files)} architecture files for {architecture_pattern} pattern",
                status="success" if generated_files else "error",
                metadata={
                    "tech_stack": tech_stack_summary,
                    "architecture_pattern": architecture_pattern,
                    "is_revision": is_revision,
                    "generation_type": generation_type,
                    "file_count": len(generated_files),
                    "agent": self.agent_name,
                    "temperature_used": adjusted_temp,
                    "execution_time": time.time() - start_time
                }
            )
              # Store successful architecture patterns in enhanced memory
            if generated_files:
                self._store_architecture_patterns(domain, tech_stack_summary, architecture_pattern, 
                                                 [{"path": f.file_path} for f in generated_files])
            
            # Log success message
            self.log_success(
                f"Architecture {generation_type} complete: {len(generated_files)} files generated"
            )
            
            # Publish architecture generation completion event
            if self.message_bus:
                self.message_bus.publish("architecture.generated", {
                    "files": [f.file_path for f in generated_files],
                    "architecture_pattern": architecture_pattern,
                    "tech_stack": tech_stack_summary,
                    "status": "success",
                    "file_count": len(generated_files),
                    "agent": self.agent_name,
                    "timestamp": datetime.now().isoformat()
                })
                self.log_info(f"Published architecture.generated event with {len(generated_files)} files")
            
            # Return as dictionary
            return output.dict()
            
        except Exception as e:
            self.log_error(f"Architecture generation failed: {str(e)}", exc_info=True)
            # Return error output using the standardized format
            error_output = CodeGenerationOutput(
                files=self._create_default_architecture_files(
                    tech_stack_summary if 'tech_stack_summary' in locals() else "Default Stack",
                    architecture_pattern if 'architecture_pattern' in locals() else "Layered",
                    domain if 'domain' in locals() else "General",
                    scale if 'scale' in locals() else "Small"
                ),
                summary=f"Error generating architecture code: {str(e)}"
            )
            return error_output.dict()
    
    # --- Helper methods for architecture generation ---
    
    def _create_directories_from_files(self, generated_files: List[Dict]) -> None:
        """
        Create all necessary directories based on file paths.
        
        Args:
            generated_files: List of file dictionaries to create directories for
        """
        directories = set()
        
        for file_data in generated_files:
            if not isinstance(file_data, dict) or "file_path" not in file_data:
                continue
                
            file_path = file_data["file_path"]
            dir_path = os.path.dirname(file_path)
            
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
    
    def _create_system_design_overview(self, system_design: Dict[str, Any]) -> str:
        """
        Create a concise overview of the system design.
        
        Args:
            system_design: Complete system design dictionary
            
        Returns:
            String containing a concise system design overview
        """
        overview = []
        
        try:
            # Try to extract high-level description
            if "description" in system_design:
                overview.append(system_design["description"])
            
            # Try to extract architecture description
            if "architecture" in system_design:
                arch = system_design["architecture"]
                if isinstance(arch, dict) and "description" in arch:
                    overview.append(f"Architecture: {arch['description']}")
            
            # Extract main components
            components = []
            if "components" in system_design:
                comps = system_design["components"]
                if isinstance(comps, dict):
                    for name, details in comps.items():
                        if isinstance(details, dict) and "description" in details:
                            components.append(f"- {name}: {details['description']}")
                        else:
                            components.append(f"- {name}")
                elif isinstance(comps, list):
                    for comp in comps:
                        if isinstance(comp, dict) and "name" in comp:
                            desc = comp.get("description", "")
                            components.append(f"- {comp['name']}: {desc}")
            
            if components:
                overview.append("Main Components:")
                overview.extend(components)
            
            # Fallback if no overview created
            if not overview:
                return "Standard web application with frontend, backend and database components."
                
            return "\n".join(overview)            
        except Exception as e:
            self.log_warning(f"Error creating system design overview: {e}")
            return "Standard web application with frontend, backend and database components."
    
    def _determine_architecture_pattern(self, tech_stack: Dict, system_design: Dict, 
                                       domain: str = "General", scale: str = "Small") -> str:
        """
        Determine the appropriate architecture pattern based on domain, scale, and technology stack.
        
        Args:
            tech_stack: Technology stack details
            system_design: System design details
            domain: Application domain (e.g., Healthcare, Finance, E-commerce)
            scale: Expected scale (Small, Medium, Large, Enterprise)
            
        Returns:
            String containing the determined architecture pattern
        """
        # Start with domain-influenced patterns
        pattern = self._get_domain_preferred_pattern(domain)
        
        # Scale-based pattern adjustments
        if scale in ["Large", "Enterprise"]:
            if pattern in ["MVC", "MVT"]:
                pattern = "Microservices"
            elif pattern == "Layered":
                pattern = "Hexagonal"
        elif scale == "Medium":
            if pattern == "Monolithic":
                pattern = "Modular Monolith"
        
        try:
            # Check for explicit pattern in system design
            if "architecture" in system_design:
                arch = system_design["architecture"]
                if isinstance(arch, dict):
                    if "pattern" in arch:
                        return arch["pattern"]
                    if "type" in arch:
                        return arch["type"]
                    if "style" in arch:
                        return arch["style"]
            
            # Infer from technology stack
            backend = None
            if "backend" in tech_stack:
                backend = tech_stack["backend"]
                if isinstance(backend, list) and len(backend) > 0:
                    backend = backend[0]
                
            # If backend is a dictionary, get the name/framework
            if isinstance(backend, dict):
                if "framework" in backend:
                    backend_name = backend["framework"]
                elif "name" in backend:
                    backend_name = backend["name"]
                else:
                    backend_name = None
            else:
                backend_name = str(backend) if backend else None
            
            # Map common frameworks to their typical architecture patterns
            if backend_name:
                backend_name = backend_name.lower()
                if "express" in backend_name or "node" in backend_name:
                    pattern = "MVC" if "mvc" in backend_name else "REST API"
                elif "django" in backend_name:
                    pattern = "MVT"
                elif "flask" in backend_name:
                    pattern = "MVC"
                elif "spring" in backend_name:
                    pattern = "Layered" if "boot" in backend_name else "Hexagonal"
                elif "rails" in backend_name:
                    pattern = "MVC"
                elif "laravel" in backend_name:
                    pattern = "MVC"
                elif "asp.net" in backend_name:
                    pattern = "MVC" if "mvc" in backend_name else "Layered"
                elif "react" in backend_name and "native" not in backend_name:
                    pattern = "Component-Based"
                
        except Exception as e:
            self.log_warning(f"Error determining architecture pattern: {e}")
        
        return pattern
    
    def _get_architecture_rag_context(self, tech_stack_summary: str, architecture_pattern: str, 
                                     domain: str = "General", scale: str = "Small") -> str:
        """
        Get comprehensive RAG context for domain-specific architecture implementation.
        
        Args:
            tech_stack_summary: Summary of the technology stack
            architecture_pattern: The architecture pattern name
            domain: Project domain (Healthcare, Fintech, etc.)
            scale: Project scale (Small, Medium, Large, Enterprise)
            
        Returns:
            RAG context string for architecture best practices
        """
        if not self.rag_retriever:
            return ""
            
        try:
            # Domain-specific architecture queries
            domain_queries = self._get_domain_specific_rag_queries(domain, tech_stack_summary, architecture_pattern)
            
            # Scale-specific architecture queries  
            scale_queries = self._get_scale_specific_rag_queries(scale, tech_stack_summary, architecture_pattern)
            
            # General architecture queries
            general_queries = [
                f"{tech_stack_summary} project structure {architecture_pattern}",
                f"{architecture_pattern} architecture best practices",
                f"{tech_stack_summary} configuration files setup",
                f"{tech_stack_summary} deployment configuration",
                f"{architecture_pattern} security implementation patterns"
            ]
            
            # Combine all queries with prioritization
            all_queries = domain_queries + scale_queries + general_queries
            
            combined_context = []
            for i, query in enumerate(all_queries[:8]):  # Limit to 8 queries for performance
                try:
                    docs = self.rag_retriever.invoke(query)
                    if docs:
                        # Take fewer docs for domain/scale queries (higher priority)
                        max_docs = 2 if i < len(domain_queries) + len(scale_queries) else 1
                        context = "\n\n".join([doc.page_content for doc in docs[:max_docs]])
                        combined_context.append(f"## {query.title()}\n{context}")
                except Exception as e:
                    self.log_warning(f"Error retrieving RAG for '{query}': {e}")
            
            # Try to get data from enhanced memory as additional context
            memory_context = self._get_architecture_memory_context(domain, tech_stack_summary)
            if memory_context:
                combined_context.append(f"## Previous Architecture Patterns\n{memory_context}")
            
            return "\n\n".join(combined_context)
            
        except Exception as e:
            self.log_warning(f"Error retrieving RAG context: {e}")
            return ""
    
    def _get_domain_specific_rag_queries(self, domain: str, tech_stack: str, pattern: str) -> List[str]:
        """Generate domain-specific RAG queries for architecture patterns."""
        domain_lower = domain.lower()
        
        base_queries = [
            f"{domain} {tech_stack} architecture patterns",
            f"{domain} software architecture best practices",
            f"{pattern} architecture for {domain} applications"
        ]
        
        # Healthcare-specific queries
        if "health" in domain_lower or "medical" in domain_lower:
            return base_queries + [
                f"HIPAA compliant {tech_stack} architecture",
                f"healthcare software security architecture patterns",
                f"medical data architecture {pattern} implementation",
                f"healthcare microservices security patterns"
            ]
        
        # Financial services queries
        elif "financ" in domain_lower or "bank" in domain_lower or "fintech" in domain_lower:
            return base_queries + [
                f"PCI DSS compliant {tech_stack} architecture", 
                f"financial services security architecture patterns",
                f"banking software {pattern} implementation",
                f"fraud detection architecture patterns"
            ]
        
        # E-commerce queries
        elif "ecommerce" in domain_lower or "retail" in domain_lower:
            return base_queries + [
                f"scalable ecommerce {tech_stack} architecture",
                f"high traffic retail architecture patterns",
                f"payment processing architecture {pattern}",
                f"inventory management system architecture"
            ]
        
        # IoT queries
        elif "iot" in domain_lower or "sensor" in domain_lower:
            return base_queries + [
                f"IoT device management architecture {tech_stack}",
                f"edge computing architecture patterns",
                f"real-time data processing {pattern} architecture",
                f"IoT security architecture best practices"
            ]
        
        # Gaming queries
        elif "game" in domain_lower or "gaming" in domain_lower:
            return base_queries + [
                f"real-time gaming architecture {tech_stack}",
                f"multiplayer game server architecture",
                f"game backend {pattern} implementation",
                f"low-latency gaming architecture patterns"
            ]
        
        # Enterprise queries
        elif "enterprise" in domain_lower or "erp" in domain_lower:
            return base_queries + [
                f"enterprise {tech_stack} architecture patterns",
                f"scalable enterprise software architecture",
                f"enterprise integration {pattern} patterns",
                f"enterprise security architecture frameworks"
            ]
        
        return base_queries
    
    def _get_scale_specific_rag_queries(self, scale: str, tech_stack: str, pattern: str) -> List[str]:
        """Generate scale-specific RAG queries for architecture patterns."""
        scale_lower = scale.lower()
        
        if "small" in scale_lower or "startup" in scale_lower:
            return [
                f"startup {tech_stack} architecture minimal setup",
                f"small scale {pattern} architecture implementation",
                f"cost-effective {tech_stack} deployment patterns"
            ]
        elif "medium" in scale_lower:
            return [
                f"medium scale {tech_stack} architecture patterns",
                f"scalable {pattern} architecture for growing applications",
                f"load balancing {tech_stack} architecture setup"
            ]
        elif "large" in scale_lower or "enterprise" in scale_lower:
            return [
                f"large scale {tech_stack} architecture patterns",
                f"enterprise {pattern} architecture implementation",
                f"highly available {tech_stack} deployment patterns",
                f"microservices {tech_stack} architecture at scale"
            ]
        
        return []
    
    def _get_architecture_memory_context(self, domain: str, tech_stack: str) -> str:
        """Get architecture context from enhanced memory."""
        if not ENHANCED_MEMORY_AVAILABLE:
            return ""
            
        try:
            from utils.shared_memory_hub import get_shared_memory_hub
            memory = get_shared_memory_hub()
            
            # Try to get previous architecture patterns for this domain/tech stack
            contexts = []
            
            memory_keys = [
                f"architecture_patterns_{domain.lower()}",
                f"tech_stack_patterns_{tech_stack.lower()}",
                "successful_architecture_patterns",
                "architecture_best_practices"
            ]
            
            for key in memory_keys:
                value = memory.get(key, None, context="architecture_patterns")
                if value:
                    contexts.append(f"**{key.replace('_', ' ').title()}:**\n{value}")
            
            return "\n\n".join(contexts) if contexts else ""
            
        except Exception as e:
            self.log_warning(f"Error retrieving architecture memory context: {e}")
            return ""
    
    def _store_architecture_patterns(self, domain: str, tech_stack: str, architecture_pattern: str, 
                                   generated_files: List[Dict]) -> None:
        """Store successful architecture patterns in enhanced memory for future reference."""
        if not ENHANCED_MEMORY_AVAILABLE:
            return
            
        try:
            from utils.shared_memory_hub import get_shared_memory_hub
            memory = get_shared_memory_hub()
            
            # Store domain-specific patterns
            domain_key = f"architecture_patterns_{domain.lower()}"
            domain_pattern = {
                "tech_stack": tech_stack,
                "architecture_pattern": architecture_pattern,
                "file_structure": [f["path"] for f in generated_files],
                "timestamp": datetime.now().isoformat(),
                "success": True
            }
            
            memory.set(domain_key, domain_pattern, context="architecture_patterns")
            
            # Store tech stack specific patterns
            tech_key = f"tech_stack_patterns_{tech_stack.lower().replace(' ', '_')}"
            tech_pattern = {
                "domain": domain,
                "architecture_pattern": architecture_pattern,
                "file_count": len(generated_files),
                "timestamp": datetime.now().isoformat()
            }
            
            memory.set(tech_key, tech_pattern, context="architecture_patterns")
            
            self.log_info(f"Stored architecture patterns for domain: {domain}, tech_stack: {tech_stack}")
            
        except Exception as e:
            self.log_warning(f"Error storing architecture patterns: {e}")
    
    def _create_tech_stack_summary(self, tech_stack: Dict[str, Any]) -> str:
        """Create a concise summary of the tech stack"""
        if not tech_stack:
            return "Default web application stack"
            
        components = []
        
        # Extract frontend
        if "frontend" in tech_stack:
            frontend = tech_stack["frontend"]
            if isinstance(frontend, dict) and "selection" in frontend:
                components.append(f"{frontend['selection']} (frontend)")
            elif isinstance(frontend, str):
                components.append(f"{frontend} (frontend)")
            elif isinstance(frontend, list) and len(frontend) > 0:
                first_item = frontend[0]
                if isinstance(first_item, dict) and "name" in first_item:
                    components.append(f"{first_item['name']} (frontend)")
                elif isinstance(first_item, str):
                    components.append(f"{first_item} (frontend)")
        
        # Extract backend
        if "backend" in tech_stack:
            backend = tech_stack["backend"]
            if isinstance(backend, dict) and "selection" in backend:
                components.append(f"{backend['selection']} (backend)")
            elif isinstance(backend, str):
                components.append(f"{backend} (backend)")
            elif isinstance(backend, list) and len(backend) > 0:
                first_item = backend[0]
                if isinstance(first_item, dict) and "name" in first_item:
                    components.append(f"{first_item['name']} (backend)")
                elif isinstance(first_item, str):
                    components.append(f"{first_item} (backend)")
        
        # Extract database
        if "database" in tech_stack:
            database = tech_stack["database"]
            if isinstance(database, dict) and "selection" in database:
                components.append(f"{database['selection']} (database)")
            elif isinstance(database, dict) and "type" in database:
                components.append(f"{database['type']} (database)")
            elif isinstance(database, str):
                components.append(f"{database} (database)")
            elif isinstance(database, list) and len(database) > 0:
                first_item = database[0]
                if isinstance(first_item, dict) and "name" in first_item:
                    components.append(f"{first_item['name']} (database)")
                elif isinstance(first_item, str):
                    components.append(f"{first_item} (database)")
                
        if not components:
            return "Default web application stack"
            
        return ", ".join(components)
    
    def _prune_system_design(self, system_design: Dict[str, Any], focus: str = "architecture") -> Dict[str, Any]:
        """Prune system design to focus on architecture-relevant aspects."""
        keys_to_keep = [
            "architecture",
            "components",
            "modules",
            "api_design",
            "description",
            "project_requirements"
        ]
        
        pruned_design = {}
        
        for key in keys_to_keep:
            if key in system_design:
                pruned_design[key] = system_design[key]
        
        return pruned_design
    
    def _prune_tech_stack(self, tech_stack: Dict[str, Any]) -> Dict[str, Any]:
        """Prune tech stack to focus on architecture-relevant aspects."""
        if not isinstance(tech_stack, dict):
            return {}
            
        # Keep all top-level keys but remove verbose details
        pruned_stack = {}
        
        for key, value in tech_stack.items():
            if isinstance(value, dict) and "reasoning" in value:
                # Remove verbose reasoning
                pruned_value = value.copy()
                pruned_value.pop("reasoning", None)
                pruned_stack[key] = pruned_value
            else:
                pruned_stack[key] = value
                
        return pruned_stack
    def _create_default_tech_stack(self, domain: str = "General") -> Dict:
        """Create a domain-aware default tech stack when none is provided"""
        # Domain-specific default stacks
        domain_stacks = {
            "Healthcare": {
                "frontend": {"selection": "React"},
                "backend": {"selection": "Node.js"},
                "database": {"selection": "PostgreSQL"},  # Better for HIPAA compliance
                "architecture_pattern": "Hexagonal"
            },
            "Finance": {
                "frontend": {"selection": "React"},
                "backend": {"selection": "Java Spring Boot"},
                "database": {"selection": "PostgreSQL"},
                "architecture_pattern": "Hexagonal"
            },
            "E-commerce": {
                "frontend": {"selection": "React"},
                "backend": {"selection": "Node.js"},
                "database": {"selection": "MongoDB"},
                "architecture_pattern": "Microservices"
            },
            "Government": {
                "frontend": {"selection": "React"},
                "backend": {"selection": "Java Spring Boot"},
                "database": {"selection": "PostgreSQL"},
                "architecture_pattern": "Layered"
            }
        }
        
        return domain_stacks.get(domain, {
            "frontend": {"selection": "React"},
            "backend": {"selection": "Node.js"},
            "database": {"selection": "MongoDB"},
            "architecture_pattern": "MVC"
        })
    def _create_default_system_design(self, domain: str = "General") -> Dict:
        """Create a domain-aware default system design when none is provided"""
        # Domain-specific design patterns
        domain_designs = {
            "Healthcare": {
                "architecture": {
                    "description": "HIPAA-compliant healthcare application architecture",
                    "components": {
                        "frontend": {"description": "Patient portal and clinical interface"},
                        "backend": {"description": "Secure healthcare API with audit logging"},
                        "database": {"description": "Encrypted patient data storage"}
                    }
                }
            },
            "Finance": {
                "architecture": {
                    "description": "PCI DSS-compliant financial services architecture",
                    "components": {
                        "frontend": {"description": "Secure financial dashboard"},
                        "backend": {"description": "Transaction processing API with fraud detection"},
                        "database": {"description": "Encrypted financial data storage"}
                    }
                }
            },
            "E-commerce": {
                "architecture": {
                    "description": "Scalable e-commerce platform architecture",
                    "components": {
                        "frontend": {"description": "Customer-facing storefront"},
                        "backend": {"description": "Product and order management API"},
                        "database": {"description": "Product catalog and customer data"}
                    }
                }
            }
        }
        
        return domain_designs.get(domain, {
            "architecture": {
                "description": "Default MVC architecture",
                "components": {
                    "frontend": {"description": "React frontend"},
                    "backend": {"description": "Node.js API server"},
                    "database": {"description": "MongoDB data storage"}
                }
            }
        })
    
    # --- Enhanced helper methods for domain, scale, and compliance awareness ---
    
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
    
    def _get_domain_preferred_pattern(self, domain: str) -> str:
        """Get the preferred architecture pattern for a specific domain."""
        domain_patterns = {
            "Healthcare": "Hexagonal",  # Clean architecture for complex business rules
            "Finance": "Hexagonal",     # Security and compliance focus
            "Banking": "Hexagonal",     # Strict security requirements
            "E-commerce": "Microservices",  # High traffic, scalability needs
            "Social Media": "Microservices",  # Scale and real-time features
            "Gaming": "Event-Driven",   # Real-time events and state management
            "IoT": "Event-Driven",      # Event processing and data streams
            "Analytics": "Layered",     # Data processing pipelines
            "Education": "MVC",         # Standard web application patterns
            "Content Management": "MVC", # Traditional web application
            "Enterprise": "Layered",    # Traditional enterprise patterns
            "Government": "Layered",    # Compliance and audit requirements
            "Manufacturing": "Layered", # Integration with existing systems
            "Logistics": "Microservices", # Complex workflows and integrations
            "Real Estate": "MVC",       # Standard business applications
            "Travel": "Microservices",  # Integration with multiple services
            "Media": "Event-Driven",    # Content processing and streaming
            "Telecommunications": "Microservices"  # High throughput and reliability
        }
        
        return domain_patterns.get(domain, "Layered")
    
    def _get_domain_specific_requirements(self, domain: str, scale: str) -> str:
        """Get domain-specific architectural requirements."""
        requirements = {
            "Healthcare": [
                "HIPAA compliance architecture",
                "Patient data encryption and access controls",
                "Audit logging for all patient data access",
                "Secure API endpoints with authentication",
                "Data backup and disaster recovery plans"
            ],
            "Finance": [
                "PCI DSS compliance for payment processing",
                "SOX compliance for financial reporting",
                "Real-time fraud detection systems",
                "Secure transaction processing",
                "Regulatory reporting capabilities"
            ],
            "Banking": [
                "Banking regulation compliance (Basel III, PSD2)",
                "Multi-factor authentication systems",
                "Transaction monitoring and reporting",
                "Anti-money laundering (AML) controls",
                "Know Your Customer (KYC) integration"
            ],
            "E-commerce": [
                "High-availability payment processing",
                "Inventory management systems",
                "Product catalog and search optimization",
                "Order management and fulfillment",
                "Customer analytics and personalization"
            ],
            "Education": [
                "FERPA compliance for student records",
                "Learning management system integration",
                "Grade management and reporting",
                "Student portal and communication tools",
                "Content delivery and streaming"
            ],
            "Government": [
                "Section 508 accessibility compliance",
                "FISMA security controls",
                "Public records management",
                "Citizen portal and services",
                "Transparent audit and reporting"
            ]
        }
        
        domain_reqs = requirements.get(domain, [
            "Standard web application security",
            "User authentication and authorization",
            "Data validation and sanitization",
            "Error handling and logging",
            "Performance monitoring"
        ])
        
        # Add scale-specific requirements
        if scale in ["Large", "Enterprise"]:
            domain_reqs.extend([
                "Load balancing and auto-scaling",
                "Distributed caching systems",
                "Multi-region deployment support",
                "Advanced monitoring and alerting"
            ])
        
        return "\n".join([f"- {req}" for req in domain_reqs])
    
    def _get_scale_considerations(self, scale: str, domain: str) -> str:
        """Get scale-specific architectural considerations."""
        considerations = {
            "Small": [
                "Monolithic or modular monolith architecture",
                "Single database with connection pooling",
                "Basic caching (in-memory or Redis)",
                "Simple deployment (single server or container)",
                "Basic monitoring and logging"
            ],
            "Medium": [
                "Modular monolith or microservices for key components",
                "Database read replicas and optimization",
                "Distributed caching with Redis/Memcached",
                "Container orchestration (Docker Swarm/Kubernetes)",
                "Enhanced monitoring with metrics and alerts"
            ],
            "Large": [
                "Microservices architecture with API gateway",
                "Database sharding and distributed systems",
                "Multi-tier caching strategy",
                "Kubernetes with auto-scaling",
                "Comprehensive observability (metrics, traces, logs)"
            ],
            "Enterprise": [
                "Event-driven microservices architecture",
                "Multi-region database deployment",
                "Content delivery network (CDN)",
                "Multi-cloud deployment strategy",
                "Advanced security and compliance monitoring"
            ]
        }
        
        scale_items = considerations.get(scale, considerations["Small"])
        return "\n".join([f"- {item}" for item in scale_items])
    
    def _get_security_compliance_requirements(self, compliance_requirements: str, domain: str) -> str:
        """Get security and compliance-specific requirements."""
        security_reqs = []
        
        # Domain-specific security requirements
        domain_security = {
            "Healthcare": [
                "HIPAA-compliant data encryption",
                "PHI access controls and audit trails",
                "Secure communication protocols"
            ],
            "Finance": [
                "PCI DSS payment security",
                "SOX financial controls",
                "Real-time fraud monitoring"
            ],
            "Banking": [
                "Banking-grade encryption",
                "Multi-factor authentication",
                "Transaction integrity controls"
            ],
            "Government": [
                "FISMA security controls",
                "Section 508 accessibility",
                "Public transparency requirements"
            ]
        }
        
        if domain in domain_security:
            security_reqs.extend(domain_security[domain])
        
        # Compliance-specific requirements
        if compliance_requirements and compliance_requirements != "None":
            if "GDPR" in compliance_requirements:
                security_reqs.extend([
                    "GDPR data protection controls",
                    "Right to be forgotten implementation",
                    "Consent management systems"
                ])
            if "HIPAA" in compliance_requirements:
                security_reqs.extend([
                    "HIPAA technical safeguards",
                    "Minimum necessary access controls",
                    "Breach notification systems"
                ])
            if "PCI DSS" in compliance_requirements:
                security_reqs.extend([
                    "PCI DSS network security",
                    "Cardholder data protection",
                    "Regular security testing"
                ])
            if "SOX" in compliance_requirements:
                security_reqs.extend([
                    "SOX IT general controls",
                    "Change management controls",
                    "Financial reporting security"
                ])
        
        # General security requirements if none specified
        if not security_reqs:
            security_reqs = [
                "Authentication and authorization systems",
                "Data encryption at rest and in transit",
                "Input validation and sanitization",
                "Security headers and CORS configuration",
                "Regular security updates and patching"
            ]
        
        return "\n".join([f"- {req}" for req in security_reqs])
    
    def _create_default_architecture_files(self, tech_stack_summary: str, architecture_pattern: str, 
                                          domain: str = "General", scale: str = "Small") -> List[Dict]:
        """
        Create domain and scale-aware default architecture files when generation fails.
        
        Args:
            tech_stack_summary: Summary of the technology stack
            architecture_pattern: The architecture pattern
            domain: Application domain
            scale: Expected scale
            
        Returns:
            List of GeneratedFile dictionaries with default content
        """
        readme_content = f"""# {domain} Application

## Technology Stack
{tech_stack_summary}

## Architecture
{architecture_pattern} Architecture

## Domain
{domain} - {scale} Scale

## Setup Instructions
1. Clone this repository
2. Install dependencies
3. Configure environment variables
4. Set up {domain.lower()}-specific configurations
5. Run the application

## Project Structure
- src/: Main source code
- config/: Configuration files
- docs/: Documentation
- tests/: Test files
- docker/: Container configurations

## {domain} Domain Considerations
- Domain-specific security requirements
- Compliance and regulatory considerations
- Scale-appropriate architecture patterns

## Development Workflow
1. Follow {domain.lower()}-specific coding standards
2. Implement required security controls
3. Test for scale and performance requirements
4. Deploy using {scale.lower()}-appropriate infrastructure

Generated by Architecture Generator Agent (domain-aware template)
"""

        # Domain-specific gitignore additions
        domain_ignores = {
            "Healthcare": [
                "# Healthcare-specific",
                "*.phi",
                "patient_data/",
                "hipaa_logs/"
            ],
            "Finance": [
                "# Finance-specific", 
                "*.fin",
                "transaction_logs/",
                "pci_data/"
            ],
            "Government": [
                "# Government-specific",
                "*.classified",
                "citizen_data/",
                "fisma_logs/"
            ]
        }
        
        gitignore_content = """# Dependencies
node_modules/
.pnp/
.pnp.js
venv/
__pycache__/
*.py[cod]

# Environment
.env
.env.local
.env.development.local
.env.test.local
.env.production.local

# Build output
dist/
build/
out/
.next/
.nuxt/
.cache/

# Logs
logs/
*.log
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Editor directories and files
.idea/
.vscode/
*.swp
*.swo
*~
.DS_Store

# Security
*.key
*.pem
secrets/
"""
        
        # Add domain-specific ignores
        if domain in domain_ignores:
            gitignore_content += "\n" + "\n".join(domain_ignores[domain])
        
        return [
            GeneratedFile(
                file_path="README.md",
                content=readme_content
            ),
            GeneratedFile(
                file_path=".gitignore",
                content=gitignore_content
            )
        ]
    
    def _setup_message_subscriptions(self) -> None:
        """Set up message bus subscriptions if available"""
        if self.message_bus:
            self.message_bus.subscribe("system.design.complete", self._handle_system_design_complete)
            self.log_info(f"{self.agent_name} subscribed to system.design.complete events")
    
    def _handle_system_design_complete(self, message: Dict[str, Any]) -> None:
        """Handle system design completion messages"""
        self.log_info("Received system design complete event")
        
        payload = message.get("payload", {})
        if payload.get("status") == "success":
            # Store system design for architecture generation
            if "design" in payload:
                self.working_memory["system_design"] = payload["design"]
                self.log_info(f"System design ready for architecture generation: {payload.get('architecture_pattern', 'Unknown pattern')}")
            
            if "components_count" in payload:
                self.log_info(f"Ready to generate architecture for {payload['components_count']} components")
        else:
            self.log_warning("System design completed with errors")