"""
Core Backend Agent - LLM-Powered Specialized Agent
Focuses on generating core backend components using intelligent LLM reasoning.
"""

import json
import os
import time
from typing import Dict, Any, List, Optional, Set
from pathlib import Path

from langchain_core.language_models import BaseLanguageModel
from langchain_core.retrievers import BaseRetriever
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate

from agents.code_generation.base_code_generator import BaseCodeGeneratorAgent
from tools.code_execution_tool import CodeExecutionTool
from message_bus import MessageBus
from tools.code_generation_utils import parse_llm_output_into_files
from models.data_contracts import CodeGenerationOutput, WorkItem, GeneratedFile

import logging
logger = logging.getLogger(__name__)

class CoreBackendAgent(BaseCodeGeneratorAgent):
    """
    LLM-Powered Core Backend Agent - Specialized for fundamental backend components
    
    Uses intelligent LLM generation for:
    - Data Models (User, Product, Order, etc.)
    - API Controllers (CRUD operations, routing)
    - Business Services (business logic layer)
    - Basic Configuration (database, settings)
    - Authentication & Authorization basics
    """
    
    def __init__(self, 
                 llm: BaseLanguageModel, 
                 memory, 
                 temperature: float,
                 output_dir: str, 
                 code_execution_tool: CodeExecutionTool,
                 rag_retriever: Optional[BaseRetriever] = None,
                 message_bus: Optional[MessageBus] = None):
        """Initialize LLM-Powered Core Backend Agent."""
        
        super().__init__(
            llm=llm,
            memory=memory,
            agent_name="Core Backend Agent",
            temperature=temperature,
            output_dir=output_dir,
            code_execution_tool=code_execution_tool,
            rag_retriever=rag_retriever,
            message_bus=message_bus
        )
        
        self._initialize_core_prompts()
        logger.info("LLM-Powered Core Backend Agent initialized")

    async def arun(self, **kwargs: Any) -> Any:
        """Asynchronous run method for the agent."""
        # This method can be implemented with asynchronous logic if needed.
        # For now, we'll delegate to the synchronous run method.
        import asyncio
        return await asyncio.to_thread(self.run, **kwargs)

    def run(self, work_item: WorkItem, state: Dict[str, Any]) -> CodeGenerationOutput:
        """
        Main execution method for the CoreBackendAgent.
        
        Args:
            work_item: The specific work item to process
            state: The current workflow state containing context
            
        Returns:
            CodeGenerationOutput: Structured code generation results
        """
        try:
            logger.info(f"Running CoreBackendAgent for work item: {work_item.description}")
            
            # Defensive handling of state parameter
            if isinstance(state, str):
                logger.warning(f"State parameter is a string instead of dict: {state}")
                state = {}  # Use empty dict as fallback
            elif state is None:
                logger.warning("State parameter is None, using empty dict")
                state = {}
            elif not isinstance(state, dict):
                logger.warning(f"State parameter is unexpected type {type(state)}, converting to dict")
                try:
                    state = dict(state) if hasattr(state, '__iter__') else {}
                except:
                    state = {}
            
            # Extract context from state
            tech_stack = state.get('tech_stack_recommendation', {})
            system_design = state.get('system_design', {})
            requirements_analysis = state.get('requirements_analysis', {})

            # Extract parameters for comprehensive generation
            language = tech_stack.get('backend_language', 'Python')
            framework = tech_stack.get('backend_framework', 'FastAPI')
            
            # Extract features from requirements analysis (simplified)
            features = set(item.get('feature') for item in requirements_analysis.get('functional_requirements', []))
            if not features:
                features = {"user_management", "basic_api"} # Fallback

            # Call the comprehensive backend generation method
            result = self.generate_comprehensive_backend(
                domain=work_item.description, # Use description as domain
                language=language,
                framework=framework,
                features=features,
                scale="enterprise" # Default scale
            )
            
            # Ensure we return a CodeGenerationOutput
            if isinstance(result, dict) and result.get("status") == "success":
                # Safe conversion of file dicts to GeneratedFile objects
                generated_files = []
                for file_data in result.get('files', []):
                    try:
                        if isinstance(file_data, GeneratedFile):
                            # Already a GeneratedFile object
                            generated_files.append(file_data)
                        elif isinstance(file_data, dict):
                            # Dictionary - convert to GeneratedFile
                            # Ensure required fields exist with defaults
                            file_dict = {
                                'file_path': file_data.get('path', file_data.get('file_path', 'unknown.py')),
                                'content': file_data.get('content', ''),
                                **{k: v for k, v in file_data.items() if k not in ['path']}  # Keep other fields
                            }
                            generated_files.append(GeneratedFile(**file_dict))
                        else:
                            logger.warning(f"Unexpected file_data type: {type(file_data)}")
                    except Exception as e:
                        logger.warning(f"Failed to convert file_data to GeneratedFile: {e}")
                        # Create a fallback GeneratedFile
                        generated_files.append(GeneratedFile(
                            file_path=str(file_data.get('path', 'error.txt') if hasattr(file_data, 'get') else 'error.txt'),
                            content=f"Error converting file: {str(e)}"
                        ))
                
                # Save files to disk
                self._save_files(generated_files)
                
                return CodeGenerationOutput(
                    generated_files=generated_files,
                    summary=result.get('summary', {}).get('summary', f"Generated {len(generated_files)} files."),
                    status="success",
                    metadata=result.get('summary', {})
                )
            else:
                 # Handle generation failure
                error_msg = result.get('error', 'Unknown error during backend generation')
                self.log_error(f"CoreBackendAgent failed: {error_msg}")
                return CodeGenerationOutput(
                    generated_files=[],
                    summary=f"Error: {error_msg}",
                    status="error"
                )

        except Exception as e:
            self.log_error(f"Error in CoreBackendAgent.run: {str(e)}")
            return CodeGenerationOutput(
                generated_files=[],
                summary=f"Error: {str(e)}",
                status="error"
            )
    
    def _initialize_core_prompts(self):
        """Initialize LLM prompt templates for core backend generation."""
        
        multi_file_format = """
        CRITICAL OUTPUT FORMAT - FOLLOW EXACTLY:
        You MUST provide your response as a single block with multiple files using this EXACT format:

        ### FILE: filename.ext
        ```filetype
        // Complete file content here
        ```

        ### FILE: another_file.ext
        ```filetype
        // Complete file content here
        ```

        RULES:
        1. Start each file with exactly "### FILE: " followed by the relative path
        2. Use ONLY "filetype" as the code block language identifier
        3. Generate ALL core backend files
        4. Focus ONLY on core functionality (12-15 files)
        """
        
        self.core_generation_template = ChatPromptTemplate.from_messages([
            ("system",
             "You are an expert backend developer specializing in CORE BACKEND COMPONENTS. "
             "You generate production-ready, enterprise-grade core backend systems with "
             "clean architecture, proper separation of concerns, and industry best practices.\n\n"
             
             "**CORE BACKEND FOCUS - MANDATORY:**\n"
             "Generate EXACTLY these core backend components:\n\n"
             
             "1. **APPLICATION ENTRY POINT:**\n"
             "   - Main application file with framework setup\n"
             "   - Route registration and middleware configuration\n"
             "   - Error handling and logging setup\n"
             "   - Application lifecycle management\n\n"
             
             "2. **CONFIGURATION MANAGEMENT:**\n"
             "   - Environment-based configuration\n"
             "   - Database connection configuration\n"
             "   - Application settings and constants\n"
             "   - Security configuration (JWT, CORS, etc.)\n\n"
             
             "3. **DATA MODELS & SCHEMAS:**\n"
             "   - Domain entity models with relationships\n"
             "   - Input/output validation schemas\n"
             "   - Database ORM/ODM model definitions\n"
             "   - Data transformation utilities\n\n"
             
             "4. **API CONTROLLERS & ROUTES:**\n"
             "   - RESTful API endpoint definitions\n"
             "   - CRUD operations for all entities\n"
             "   - Request/response handling\n"
             "   - Input validation and error handling\n\n"
             
             "5. **BUSINESS SERVICES:**\n"
             "   - Business logic layer implementation\n"
             "   - Service classes for domain operations\n"
             "   - Data access layer abstraction\n"
             "   - External service integrations\n\n"
             
             "6. **AUTHENTICATION & AUTHORIZATION:**\n"
             "   - User authentication mechanisms\n"
             "   - JWT token handling\n"
             "   - Authorization middleware\n"
             "   - Session management\n\n"
             
             "**FRAMEWORK-SPECIFIC PATTERNS:**\n"
             "- FastAPI: Use APIRouter, Pydantic models, dependency injection\n"
             "- Django: Use Django REST Framework, serializers, ViewSets\n"
             "- Express: Use Router, middleware, async/await patterns\n"
             "- Spring Boot: Use @RestController, @Service, @Repository\n\n"
             
             "**DOMAIN INTELLIGENCE:**\n"
             "- E-commerce: Product, Order, Cart, Payment, Customer models\n"
             "- Healthcare: Patient, Appointment, Medical Record, Provider models\n"
             "- Financial: Account, Transaction, Payment, User, Audit models\n"
             "- IoT: Device, Sensor, Reading, Configuration, Alert models\n\n"
             
             "Generate 12-15 core files that form the foundation of a production backend."),
            
            ("human",
             "Generate CORE BACKEND COMPONENTS for a **{domain}** application using **{framework}** ({language}).\n\n"
             
             "**Project Context:**\n"
             "- Domain: {domain}\n"
             "- Language: {language}\n"
             "- Framework: {framework}\n"
             "- Scale: {scale}\n"
             "- Security Level: {security_level}\n"
             "- Core Features: {features}\n\n"
             
             "**MANDATORY CORE FILES (12-15 files):**\n"
             "1. Main application entry point\n"
             "2. Database configuration\n"
             "3. Application settings/config\n"
             "4. Domain models (User, {domain_models})\n"
             "5. API controllers for all entities\n"
             "6. Business service layer\n"
             "7. Authentication middleware\n"
             "8. Dependencies/requirements file\n"
             "9. Environment configuration example\n\n"
             
             "**DOMAIN-SPECIFIC REQUIREMENTS:**\n"
             "{domain_requirements}\n\n"
             
             "**FRAMEWORK PATTERNS:**\n"
             "{framework_patterns}\n\n"
             
             "Generate production-ready core backend with proper error handling, "
             "logging, validation, and {framework} best practices. Focus ONLY on "
             "core functionality - no DevOps, monitoring, or advanced infrastructure.")
        ])
    
    def generate_comprehensive_backend(self, 
                                     domain: str,
                                     language: str,
                                     framework: str,
                                     features: Set[str],
                                     scale: str = "enterprise") -> Dict[str, Any]:
        """Generate comprehensive core backend components using LLM."""
        
        start_time = time.time()
        
        try:
            logger.info(f"Generating LLM-powered core backend for {domain} ({language}/{framework})")
            
            # Prepare intelligent context
            domain_models = self._get_domain_models(domain)
            domain_requirements = self._get_domain_requirements(domain)
            framework_patterns = self._get_framework_patterns(framework)
            
            # Create LLM prompt
            prompt_input = {
                "domain": domain,
                "language": language,
                "framework": framework,
                "scale": scale,
                "security_level": "medium",
                "features": ", ".join(sorted(features)),
                "domain_models": ", ".join(domain_models),
                "domain_requirements": domain_requirements,
                "framework_patterns": framework_patterns
            }
            
            # Generate using LLM
            response = self.core_generation_template.invoke(prompt_input)
            
            # Parse LLM output into files
            parsed_files = parse_llm_output_into_files(
                response.content if hasattr(response, 'content') else str(response)
            )
            
            # Ensure minimum file count
            if len(parsed_files) < 8:
                logger.warning(f"LLM generated only {len(parsed_files)} files, using fallback")
                fallback_files = self._create_fallback_core_files(language, framework, domain)
                # Convert fallback dict format to GeneratedFile objects
                for file_info in fallback_files:
                    parsed_files.append(GeneratedFile(
                        file_path=file_info["path"],
                        content=file_info["content"],
                        purpose=file_info.get("type", "core"),
                        status="generated"
                    ))
            
            # Save files to output directory and prepare return format
            saved_files = []
            for generated_file in parsed_files:
                file_path = os.path.join(self.output_dir, generated_file.file_path)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(generated_file.content)
                
                # Convert GeneratedFile to dict format for return value
                saved_files.append({
                    "name": os.path.basename(generated_file.file_path),
                    "path": generated_file.file_path,
                    "content": generated_file.content,  # Include content for later use
                    "type": generated_file.purpose or "core",
                    "size": len(generated_file.content)
                })
            
            execution_time = time.time() - start_time
            
            logger.info(f"LLM-powered core backend generated: {len(saved_files)} files in {execution_time:.1f}s")
            
            return {
                "status": "success",
                "files": saved_files,
                "execution_time": execution_time,
                "summary": {
                    "language": language,
                    "framework": framework,
                    "domain": domain,
                    "files_count": len(saved_files),
                    "features": list(features),
                    "generation_method": "llm_powered"
                }
            }
            
        except Exception as e:
            logger.error(f"LLM-powered core backend generation failed: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "execution_time": time.time() - start_time
            }
    
    def _get_domain_models(self, domain: str) -> List[str]:
        """Get domain-specific model names."""
        domain_models = {
            "E-commerce": ["Product", "Order", "Cart", "Payment", "Customer", "Category"],
            "Healthcare": ["Patient", "Appointment", "MedicalRecord", "Provider", "Prescription"],
            "Financial": ["Account", "Transaction", "Payment", "Audit", "Report"],
            "IoT": ["Device", "Sensor", "Reading", "Configuration", "Alert"],
            "General": ["User", "Profile", "Settings", "Notification"]
        }
        return domain_models.get(domain, domain_models["General"])
    
    def _get_domain_requirements(self, domain: str) -> str:
        """Get domain-specific requirements."""
        requirements = {
            "E-commerce": "Product catalog management, inventory tracking, order processing, payment integration, customer management",
            "Healthcare": "Patient data management (HIPAA compliant), appointment scheduling, medical record keeping, provider management",
            "Financial": "Account management, transaction processing, payment handling, audit logging, compliance reporting",
            "IoT": "Device management, sensor data collection, real-time monitoring, configuration management, alerting",
            "General": "User management, authentication, data persistence, API endpoints, business logic"
        }
        return requirements.get(domain, requirements["General"])
    
    def _get_framework_patterns(self, framework: str) -> str:
        """Get framework-specific implementation patterns."""
        patterns = {
            "FastAPI": "Use APIRouter for modular routing, Pydantic models for validation, dependency injection for services",
            "Django": "Use Django REST Framework ViewSets, serializers for validation, class-based views",
            "Express": "Use Express Router, middleware for authentication, async/await for database operations",
            "Spring Boot": "Use @RestController for APIs, @Service for business logic, @Repository for data access"
        }
        return patterns.get(framework, "Follow framework best practices and conventions")
    
    def _create_fallback_core_files(self, language: str, framework: str, domain: str) -> List[Dict[str, Any]]:
        """Create minimal fallback core files if LLM generation is insufficient, using LLM."""
        
        files_to_generate = [
            {
                "name": "main",
                "path": "main",
                "type": "application",
                "description": f"Main application entry point for {domain} backend.",
                "additional_details": f"Generate a basic main application file for a {language} {framework} backend. Include a simple print statement or a basic server startup for demonstration."
            },
            {
                "name": "config",
                "path": "config/config",
                "type": "config",
                "description": f"Basic configuration file for {domain} backend.",
                "additional_details": f"Generate a basic configuration file for a {language} {framework} backend. Include a placeholder for DATABASE_URL and any other essential settings."
            }
        ]
        
        generated_files = []
        for file_info in files_to_generate:
            prompt_input = {
                "domain": domain,
                "language": language,
                "framework": framework,
                "scale": "startup", # Fallback usually for simpler scale
                "security_level": "low",
                "features": "basic",
                "domain_models": "",
                "domain_requirements": "",
                "framework_patterns": "",
                "file_name": file_info["name"],
                "file_type": file_info["type"],
                "file_path": file_info["path"],
                "description": file_info["description"],
                "additional_details": file_info["additional_details"]
            }
            # Use a simplified prompt for fallback generation if core_generation_template is too complex
            # For now, will use core_generation_template but with very specific instructions
            chain = self.core_generation_template | self.llm # Re-using the main prompt, but with very specific instructions
            response = chain.invoke(prompt_input)
            
            generated_content = self._extract_code_from_response(response.content if hasattr(response, 'content') else str(response))
            
            file_ext = self._get_file_extension(language)
            
            generated_files.append({
                "name": f"{file_info['name']}.{file_ext}",
                "path": f"{file_info['path']}.{file_ext}",
                "content": generated_content,
                "type": file_info["type"]
            })
            
        return generated_files

    def _generate_code(self, llm, invoke_config, work_item: WorkItem, tech_stack: dict, system_design: dict = None, requirements_analysis: dict = None, **kwargs) -> dict:
        """
        Generates backend code and tests for a given work item.
        This method is called by the `run` method of the base class.
        """
        prompt_template = self._create_prompt_template()
        chain = prompt_template | llm

        logger.info(f"Running CoreBackendAgent for work item: {work_item.description}")

        query = f"Task: {work_item.description}\nFile to be created/modified: {work_item.file_path}"
        rag_context = self._get_rag_context(query)

        try:
            result = chain.invoke({
                "work_item_description": work_item.description,
                "file_path": work_item.file_path,
                "language": tech_stack.get("backend_language", "Python"),
                "database_management_system": tech_stack.get("database", "PostgreSQL"),
                "api_documentation_tool": tech_stack.get("api_documentation_tool", "Swagger"),
                "example_code_snippet": work_item.example or "No example provided.",
                "rag_context": rag_context
            })
            
            logger.info(f"CoreBackendAgent completed for work item: {work_item.description}")
            
            parsed_output = self._parse_output(result.content)
            files = self._create_files_from_parsed_output(parsed_output)

            return CodeGenerationOutput(
                generated_files=files,
                summary=f"Successfully generated backend code and tests for: {work_item.description}"
            ).model_dump()

        except Exception as e:
            logger.error(f"[Core Backend Agent] Error in _generate_code: {e}", exc_info=True)
            return self.get_default_response()
            
    def _parse_output(self, llm_output: str) -> dict:
        """Parses the LLM's output to extract the implementation and test code."""
        # This is a simplified parser. A more robust implementation would handle
        # multiple files and more complex structures.
        generated_files = parse_llm_output_into_files(llm_output)
        
        # Convert GeneratedFile objects to dict format for compatibility
        files_as_dicts = []
        for generated_file in generated_files:
            files_as_dicts.append({
                "file_path": generated_file.file_path,
                "content": generated_file.content,
                "purpose": generated_file.purpose or "Generated file",
                "status": generated_file.status or "success"
            })
        
        return {"files": files_as_dicts}

    def _create_files_from_parsed_output(self, parsed_output: dict) -> list[GeneratedFile]:
        """Creates a list of GeneratedFile objects from the parsed LLM output."""
        generated_files = []
        
        files_data = parsed_output.get("files", [])
        if not isinstance(files_data, list):
            self.log_warning("Parsed output 'files' is not a list, attempting to recover.")
            files_data = []

        for file_data in files_data:
            try:
                if isinstance(file_data, GeneratedFile):
                    # Already a GeneratedFile object
                    generated_files.append(file_data)
                elif isinstance(file_data, dict):
                    # Dictionary - convert to GeneratedFile
                    # Ensure required fields exist with defaults
                    file_dict = {
                        'file_path': file_data.get('path', file_data.get('file_path', 'unknown.py')),
                        'content': file_data.get('content', ''),
                        **{k: v for k, v in file_data.items() if k not in ['path']}  # Keep other fields
                    }
                    generated_files.append(GeneratedFile(**file_dict))
                elif hasattr(file_data, 'file_path') and hasattr(file_data, 'content'):
                    # Object with file_path and content attributes
                    generated_files.append(GeneratedFile(
                        file_path=file_data.file_path,
                        content=file_data.content
                    ))
                else:
                    logger.warning(f"Unexpected file_data type: {type(file_data)}")
                    # Create a fallback GeneratedFile
                    generated_files.append(GeneratedFile(
                        file_path='error.txt',
                        content=f"Error: unexpected file data type {type(file_data)}"
                    ))
            except Exception as e:
                logger.warning(f"Failed to convert file_data to GeneratedFile: {e}")
                # Create a fallback GeneratedFile
                generated_files.append(GeneratedFile(
                    file_path='error.txt',
                    content=f"Error converting file: {str(e)}"
                ))

        return generated_files

    def _get_test_file_path(self, file_path_str: str) -> str:
        """Derives a conventional test file path from a source file path."""
        p = Path(file_path_str)
        parts = list(p.parts)
        
        # Replace 'src' with 'tests' if it exists
        try:
            src_index = parts.index('src')
            parts[src_index] = 'tests'
        except ValueError:
            # If 'src' is not in the path, insert 'tests' at the beginning
            parts.insert(0, 'tests')
            
        # Add 'test_' prefix to the filename
        filename = f"test_{p.name}"
        
        # Reassemble the path
        new_path = Path(*parts[:-1]) / filename
        return str(new_path)

    def _create_prompt_template(self) -> PromptTemplate:
        """Creates the prompt template for the agent."""
        prompt_string = """
        You are a world-class backend developer. Your task is to write clean, efficient, and well-documented backend code based on the provided requirements and technology stack.
        You must follow all instructions, including file paths and function names, precisely.
        The code you generate will be part of a larger project. Ensure it is modular and integrates well.

        {rag_context}

        **Technology Stack:**
        - Language: {language}
        - Database Management System: {database_management_system}
        - API Documentation Tool: {api_documentation_tool}

        **Work Item:**
        - Description: {work_item_description}
        - File Path: {file_path}
        - Example Snippet (for reference):
        ```
        {example_code_snippet}
        ```

        **Instructions:**
        1.  Generate the complete code for the file specified in `File Path`. Do NOT just generate a snippet.
        2.  You MUST also generate the corresponding unit tests for the code you write. The tests should be complete and runnable.
        3.  Format your response clearly, separating the implementation code and the test code with the specified tags.

        **Output Format:**
        Provide your response in the following format, and do not include any other text, explanations, or markdown formatting outside of the specified tags.

        [CODE]
        ```python
        # Your generated backend code here
        ```
        [/CODE]

        [TESTS]
        ```python
        # Your generated unit tests here
        ```
        [/TESTS]
        """
        return PromptTemplate(
            template=prompt_string,
            input_variables=[
                "work_item_description",
                "file_path",
                "language",
                "database_management_system",
                "api_documentation_tool",
                "example_code_snippet",
                "rag_context"
            ],
        )

    def _get_rag_context(self, query: str) -> str:
        """
        Retrieves RAG context for the given query.
        """
        # This method needs to be implemented based on the specific RAG system
        # For now, we'll use a placeholder implementation
        return f"RAG context for query: {query}"

    def _get_file_extension(self, language: str) -> str:
        """
        Retrieves the file extension for the given language.
        """
        # This method needs to be implemented based on the specific file extensions for each language
        # For now, we'll use a placeholder implementation
        return "py" if language.lower() == "python" else "java" if language.lower() == "java" else "js" if language.lower() == "javascript" else "ts" if language.lower() == "typescript" else "cpp" if language.lower() == "c++" else "cs" if language.lower() == "c#" else "rb" if language.lower() == "ruby" else "go" if language.lower() == "golang" else "php" if language.lower() == "php" else "html" if language.lower() == "html" else "css" if language.lower() == "css" else "sql" if language.lower() == "sql" else "sh" if language.lower() == "shell" else "md" if language.lower() == "markdown" else "txt"

    def _extract_code_from_response(self, response: str) -> str:
        """
        Extracts code from the LLM response.
        """
        # This method needs to be implemented based on the specific format of the LLM response
        # For now, we'll use a placeholder implementation
        return response.strip() 