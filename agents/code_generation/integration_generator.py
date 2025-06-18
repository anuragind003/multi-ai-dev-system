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
from agents.code_generation.models import GeneratedFile, CodeGenerationOutput
from tools.code_generation_utils import parse_llm_output_into_files

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

        Continue this pattern for all files you need to create. For each integration service, generate:
        1. Main service integration code (connectors, API clients)
        2. Adapter classes that provide clean interfaces
        3. Configuration files with secure parameter handling
        4. Example usage files showing how to use each integration
        """

        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", 
             "You are an expert integration developer specializing in connecting systems to external services. "
             "You excel at writing clean, robust integration code that follows best practices for security, "
             "error handling, and maintainability. You create well-structured code that abstracts away the "
             "complexity of external services behind clean interfaces."
            ),
            ("human", 
             """
             Generate complete integration code for the following external services:
             
             ## Integration Points
             {integration_points_json}
             
             ## Tech Stack
             {tech_stack_summary}
             
             ## Architecture Information
             Architecture Pattern: {architecture_pattern}
             Backend Framework: {backend_framework}
             Backend Language: {backend_language}
             
             ## Integration Requirements
             {integration_requirements}
             
             ## Best Practices
             - Include proper error handling and retries
             - Implement secure authentication
             - Add comprehensive logging
             - Handle rate limiting
             - Abstract complexity behind clean interfaces
             - Make code testable with proper dependency injection
             - Use configuration for all external parameters
             - Securely handle sensitive values like API keys
             - Implement proper timeouts
             
             {rag_context}
             
             {code_review_feedback}
             
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
        
        try:
            # Validate inputs with defaults
            if not isinstance(tech_stack, dict):
                self.log_warning("Invalid tech stack - using default")
                tech_stack = self._create_default_tech_stack()
                
            if not isinstance(system_design, dict):
                self.log_warning("Invalid system design - using default")
                system_design = self._create_default_system_design()
            
            # Extract integration points
            integration_points = self._extract_integration_points(system_design)
            
            if not integration_points:
                self.log_warning("No integration points found in system design - using defaults")
                integration_points = self._create_default_integration_points()
            
            # Get tech stack details
            backend_tech = self._extract_backend_tech(tech_stack)
            backend_language = backend_tech.get("language", "python")
            backend_framework = backend_tech.get("framework", "flask")
            architecture_pattern = tech_stack.get("architecture_pattern", "MVC")
            
            # Create tech stack summary
            tech_stack_summary = self._create_tech_stack_summary(tech_stack)
            
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
            self.log_info(f"Generating integration code with temperature {adjusted_temp}")
            response = llm_with_temp.invoke(
                self.prompt_template.format(
                    integration_points_json=integration_points_json,
                    tech_stack_summary=tech_stack_summary,
                    architecture_pattern=architecture_pattern,
                    backend_framework=backend_framework,
                    backend_language=backend_language,
                    integration_requirements=integration_requirements,
                    rag_context=rag_context,
                    code_review_feedback=code_review_section
                ),
                config=invoke_config
            )
            
            # Extract content from response
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Log abbreviated version of the content for debug purposes
            self.log_debug(f"LLM response (abbreviated): {content[:300]}...")
            
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
            service_files_count = len([f for f in generated_files if "/services/" in f.file_path or "/integrations/" in f.file_path])
            adapter_files_count = len([f for f in generated_files if "/adapters/" in f.file_path])
            config_files_count = len([f for f in generated_files if "/config/" in f.file_path or f.file_path.endswith(".env")])
            
            # Create directories first before saving files
            self._create_directories_from_files(generated_files)
            
            # Create structured output
            output = CodeGenerationOutput(
                generated_files=generated_files,
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
            
            # Return as dictionary
            return output.dict()
            
        except Exception as e:
            self.log_error(f"Integration {generation_type} failed: {str(e)}", exc_info=True)
            # Return error output using the standardized format
            
            # Handle the case where integration_points might not be in locals()
            # (i.e., an error occurred before it was defined)
            local_integration_points = (
                integration_points if 'integration_points' in locals() 
                else self._create_default_integration_points()
            )
            
            # Handle the case where backend_language/framework might not be in locals()
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
            return self._create_default_integration_points()
    
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
                    docs = self.rag_retriever.get_relevant_documents(query)
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
    
    def _create_default_integration_points(self) -> List[Dict[str, Any]]:
        """
        Create default integration points when none are found.
        
        Returns:
            List of default integration point dictionaries
        """
        return [
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
        ]
    
    def _create_default_integration_files(self, 
                                      integration_points: List[Dict[str, Any]],
                                      backend_language: str,
                                      backend_framework: str) -> List[GeneratedFile]:
        """
        Create default integration files when generation fails.
        
        Args:
            integration_points: List of integration points
            backend_language: Backend language name
            backend_framework: Backend framework name
            
        Returns:
            List of GeneratedFile objects with default content
        """
        default_files = []
        
        if not integration_points:
            integration_points = self._create_default_integration_points()
        
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
            
            default_files.append(GeneratedFile(
                file_path=f"src/integrations/services/{service_slug}_service.{ext}",
                content=service_content,
                purpose=f"{service_name} integration service",
                status="generated"
            ))
            
            # Create adapter file
            adapter_content = self._create_default_adapter_content(
                service_name, integration, backend_language, ext, comment)
            
            default_files.append(GeneratedFile(
                file_path=f"src/integrations/adapters/{service_slug}_adapter.{ext}",
                content=adapter_content,
                purpose=f"{service_name} adapter class",
                status="generated"
            ))
            
            # Create config file
            config_content = self._create_default_config_content(
                service_name, integration, backend_language, backend_framework)
            
            config_ext = self._get_config_extension(backend_framework)
            default_files.append(GeneratedFile(
                file_path=f"src/config/{service_slug}_config.{config_ext}",
                content=config_content,
                purpose=f"{service_name} configuration",
                status="generated"
            ))
            
            # Create example usage file
            example_content = self._create_default_example_content(
                service_name, integration, backend_language, ext, comment)
            
            default_files.append(GeneratedFile(
                file_path=f"src/examples/{service_slug}_example.{ext}",
                content=example_content,
                purpose=f"{service_name} usage example",
                status="generated"
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