"""Documentation Agent for generating comprehensive project documentation."""

import os
import time
from typing import Dict, Any, List, Set, Optional

from langchain_core.language_models import BaseLanguageModel
from langchain_core.retrievers import BaseRetriever
from langchain_core.prompts import ChatPromptTemplate

from agents.code_generation.base_code_generator import BaseCodeGeneratorAgent
from tools.code_execution_tool import CodeExecutionTool
from message_bus import MessageBus
from models.data_contracts import CodeGenerationOutput, GeneratedFile, WorkItem
from tools.code_generation_utils import parse_llm_output_into_files

import logging
logger = logging.getLogger(__name__)

class DocumentationAgent(BaseCodeGeneratorAgent):
    """Documentation Agent for comprehensive project documentation."""
    
    def __init__(self, 
                 llm: BaseLanguageModel, 
                 memory, 
                 temperature: float, 
                 output_dir: str, 
                 code_execution_tool: CodeExecutionTool, 
                 rag_retriever: Optional[BaseRetriever] = None, 
                 message_bus: Optional[MessageBus] = None):
        super().__init__(
            llm=llm,
            memory=memory,
            agent_name="Documentation Agent",
            temperature=temperature,
            output_dir=output_dir,
            code_execution_tool=code_execution_tool,
            rag_retriever=rag_retriever,
            message_bus=message_bus
        )
        logger.info("Documentation Agent initialized")
        self._initialize_prompt_templates()

    async def arun(self, **kwargs: Any) -> Any:
        """Asynchronous run method for the agent."""
        # This method can be implemented with asynchronous logic if needed.
        # For now, we'll delegate to the synchronous run method.
        import asyncio
        return await asyncio.to_thread(self.run, **kwargs)

    def _generate_code(self, llm, invoke_config: Dict, **kwargs) -> Dict[str, Any]:
        """Implementation of the abstract method from base class."""
        # This agent's logic is primarily in the `run` method, which acts
        # based on the work item. We can adapt the old `generate_documentation`
        # method to fit this structure.
        
        work_item = kwargs.get('work_item')
        state = kwargs.get('state')

        if work_item and state:
            return self.run(work_item, state)
        else:
            # Fallback to old behavior if called directly without new context
            domain = kwargs.get('domain', 'General')
            language = kwargs.get('language', 'Python')
            framework = kwargs.get('framework', 'FastAPI')
            scale = kwargs.get('scale', 'enterprise')
            features = set(kwargs.get('features', []))
            return self.generate_documentation(domain, language, framework, scale, features)
    
    def run(self, work_item: WorkItem, state: Dict[str, Any]) -> CodeGenerationOutput:
        """
        Generates documentation for a single work item.
        """
        logger.info(f"DocumentationAgent starting work item: {work_item.id}")

        # The description will tell us what kind of doc to generate.
        # This is a simple routing mechanism. A more advanced one could use an LLM call.
        description = work_item.description.lower()
        
        # Consolidate context from state
        tech_stack = state.get("tech_stack_recommendation", {})
        language = tech_stack.get("language", "python")
        framework = tech_stack.get("backend_framework", "fastapi")
        domain = tech_stack.get("project_domain", "general")
        features = set(tech_stack.get("features", []))
        scale = state.get("system_design", {}).get("scale", "enterprise")

        doc_files = []
        doc_dir = "docs"
        os.makedirs(os.path.join(self.output_dir, doc_dir), exist_ok=True)

        if "readme" in description:
            content = self._get_readme_content(domain, language, framework, features)
            doc_files.append(GeneratedFile(file_path="README.md", content=content, purpose="Project README"))
        elif "api" in description:
            content = self._get_api_docs(domain)
            doc_files.append(GeneratedFile(file_path=os.path.join(doc_dir, "API.md"), content=content, purpose="API Documentation"))
        elif "deployment" in description:
            content = self._get_deployment_docs(language, framework)
            doc_files.append(GeneratedFile(file_path=os.path.join(doc_dir, "DEPLOYMENT.md"), content=content, purpose="Deployment Guide"))
        elif "architecture" in description:
            content = self._get_architecture_docs(domain, scale)
            doc_files.append(GeneratedFile(file_path=os.path.join(doc_dir, "ARCHITECTURE.md"), content=content, purpose="Architecture Overview"))
        else:
            # Fallback for generic documentation tasks
            logger.warning(f"Could not determine specific doc type for '{work_item.description}'. Generating generic project overview.")
            content = self._get_readme_content(domain, language, framework, features)
            doc_files.append(GeneratedFile(file_path=os.path.join(doc_dir, "PROJECT_OVERVIEW.md"), content=content, purpose="Project Overview"))

        # Save files to disk
        self._save_files(doc_files)
        
        return CodeGenerationOutput(
            generated_files=doc_files,
            summary=f"Generated {len(doc_files)} documentation file(s) for work item {work_item.id}."
        )

    def generate_documentation(self, domain: str, language: str, framework: str, scale: str, features: Set[str]) -> Dict[str, Any]:
        """DEPRECATED: This method is part of the old, phase-based workflow."""
        logger.warning("generate_documentation is deprecated. Use the `run` method with a work item instead.")
        start_time = time.time()
        
        try:
            logger.info(f"Generating documentation for {domain}")
            
            # Generate content using LLM-powered helper methods
            readme_content = self._get_readme_content(domain, language, framework, features)
            api_docs_content = self._get_api_docs(domain)
            deployment_docs_content = self._get_deployment_docs(language, framework)
            architecture_docs_content = self._get_architecture_docs(domain, scale)

            files = [
                {
                    "name": "README.md",
                    "path": "README.md",
                    "content": readme_content,
                    "type": "documentation"
                },
                {
                    "name": "API.md", 
                    "path": "docs/API.md",
                    "content": api_docs_content,
                    "type": "documentation"
                },
                {
                    "name": "DEPLOYMENT.md",
                    "path": "docs/DEPLOYMENT.md", 
                    "content": deployment_docs_content,
                    "type": "documentation"
                },
                {
                    "name": "ARCHITECTURE.md",
                    "path": "docs/ARCHITECTURE.md",
                    "content": architecture_docs_content,
                    "type": "documentation"
                }
            ]
            
            saved_files = []
            for file_info in files:
                file_path = os.path.join(self.output_dir, file_info["path"])
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(file_info["content"])
                
                saved_files.append({
                    "name": file_info["name"],
                    "path": file_info["path"],
                    "type": file_info["type"],
                    "size": len(file_info["content"])
                })
            
            execution_time = time.time() - start_time
            
            return {
                "status": "success",
                "files": saved_files,
                "execution_time": execution_time,
                "summary": {
                    "files_count": len(saved_files),
                    "doc_types": ["readme", "api", "deployment", "architecture"]
                }
            }
            
        except Exception as e:
            logger.error(f"Documentation generation failed: {str(e)}")
            return {"status": "error", "error": str(e), "execution_time": time.time() - start_time}
    
    def _initialize_prompt_templates(self):
        """Initialize LLM prompt templates for documentation generation."""

        self.readme_prompt = ChatPromptTemplate.from_messages([
            ("system", 
             "You are an expert technical writer specializing in creating comprehensive, "
             "professional README documentation for enterprise software projects. "
             "Generate clear, structured, and actionable documentation that follows "
             "industry best practices."),
            
            ("human",
             "Generate a comprehensive README.md file for a {domain} application "
             "built with {language} and {framework}.\n\n"
             
             "**Project Details:**\n"
             "- Domain: {domain}\n"
             "- Language: {language}\n"
             "- Framework: {framework}\n"
             "- Features: {features}\n\n"
             
             "**Requirements:**\n"
             "- Include installation and setup instructions\n"
             "- Add development workflow\n"
             "- Include API documentation links\n"
             "- Add deployment instructions\n"
             "- Include contributing guidelines\n"
             "- Make it professional and comprehensive\n"
             "- Use proper markdown formatting\n\n"
             
             "Generate ONLY the README content without any explanations.")
        ])
        
        self.api_docs_prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You are an expert API documentation specialist. Generate comprehensive, "
             "professional API documentation that follows OpenAPI/REST standards and "
             "includes practical examples for developers."),
            
            ("human",
             "Generate comprehensive API documentation for a {domain} application.\n\n"
             
             "**Requirements:**\n"
             "- Include authentication methods\n"
             "- Document common CRUD endpoints\n"
             "- Provide request/response examples\n"
             "- Include error handling documentation\n"
             "- Add pagination and filtering examples\n"
             "- Use proper HTTP status codes\n"
             "- Make it developer-friendly with clear examples\n\n"
             
             "Generate ONLY the API documentation content in markdown format.")
        ])
        
        self.deployment_prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You are an expert DevOps engineer specializing in production deployments. "
             "Generate comprehensive deployment documentation that covers multiple "
             "deployment scenarios and follows industry best practices."),
            
            ("human",
             "Generate comprehensive deployment documentation for a {language} application "
             "using {framework}.\n\n"
             
             "**Requirements:**\n"
             "- Include Docker deployment instructions\n"
             "- Add Kubernetes deployment guidelines\n"
             "- Cover environment configuration\n"
             "- Include monitoring and logging setup\n"
             "- Add security considerations\n"
             "- Include scaling and performance tips\n"
             "- Provide troubleshooting guide\n\n"
             
             "Generate ONLY the deployment documentation in markdown format.")
        ])
        
        self.architecture_docs_prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You are an expert software architect and technical writer. Generate comprehensive "
             "architecture documentation that clearly explains the system's design, components, "
             "and interactions, following best practices for clarity and detail."
            ),
            ("human",
             "Generate comprehensive architecture documentation for a {domain} application at {scale} scale.\n\n"
             "**Requirements:**\n"
             "- Describe the overall architecture pattern and its rationale.\n"
             "- Detail the key components and their responsibilities.\n"
             "- Explain data flow and interactions between components.\n"
             "- Include considerations for scalability, security, and reliability.\n"
             "- Provide a high-level system diagram description (e.g., using Mermaid syntax or textual description).\n"
             "- Discuss technology choices and their justification.\n"
             "- Make it professional and easy to understand.\n\n"
             "Generate ONLY the architecture documentation content in markdown format."
            )
        ])

    def _get_readme_content(self, domain: str, language: str, framework: str, features: Set[str]) -> str:
        """Generate README.md content using LLM instead of hardcoded template."""
        
        try:
            features_list = ', '.join(sorted(features))
            response = self.llm.invoke(self.readme_prompt.format_messages(
                domain=domain,
                language=language,
                framework=framework,
                features=features_list
            ))
            return response.content
        except Exception as e:
            logger.warning(f"LLM README generation failed, using fallback: {str(e)}")
            # Fallback to simplified template
            features_list = ', '.join(sorted(features))
            return f"""# {domain} Application\n\nEnterprise-grade {domain.lower()} application built with {language} and {framework}.\n\n## Features\n\n{features_list}\n\n## Quick Start\n\n### Installation\n```bash\npip install -r requirements.txt\n```\n\n### Development\n```bash\npython main.py\n```\n\n## Documentation\n\n- [API Documentation](docs/API.md)\n- [Deployment Guide](docs/DEPLOYMENT.md)\n- [Architecture Overview](docs/ARCHITECTURE.md)\n\n## License\n\nMIT License\n"""
    
    def _get_api_docs(self, domain: str) -> str:
        """Generate API documentation using LLM instead of hardcoded template."""
        
        try:
            response = self.llm.invoke(self.api_docs_prompt.format_messages(domain=domain))
            return response.content
        except Exception as e:
            logger.warning(f"LLM API docs generation failed, using fallback: {str(e)}")
            # Fallback to basic template
            return f"""# {domain} API Documentation\n\n## Authentication\n\nUse Bearer token authentication:\n```\nAuthorization: Bearer <your-token>\n```\n\n## Endpoints\n\n### Authentication\n- POST /api/auth/register - Register new user\n- POST /api/auth/login - User login\n\n### Core Resources\n- GET /api/items - List items\n- POST /api/items - Create item\n- GET /api/items/{{id}} - Get item by ID\n- PUT /api/items/{{id}} - Update item\n- DELETE /api/items/{{id}} - Delete item\n\n## Response Format\n\nAll responses follow this format:\n```json\n{{\n  \"status\": \"success|error\",\n  \"data\": {{}},\n  \"message\": \"Description\"\n}}\n```\n"""
    
    def _get_deployment_docs(self, language: str, framework: str) -> str:
        """Generate deployment documentation using LLM instead of hardcoded template."""
        
        try:
            response = self.llm.invoke(self.deployment_prompt.format_messages(
                language=language,
                framework=framework
            ))
            return response.content
        except Exception as e:
            logger.warning(f"LLM deployment docs generation failed, using fallback: {str(e)}")
            # Fallback to basic template
            return f"""# Deployment Guide\n\n## Docker Deployment\n\n```bash\ndocker build -t {language.lower()}-{framework.lower()}-app .\ndocker run -p 8000:8000 {language.lower()}-{framework.lower()}-app\n```\n\n## Kubernetes\n\n```bash\nkubectl apply -f kubernetes/\n```\n"""
    
    def _get_architecture_docs(self, domain: str, scale: str) -> str:
        """Generate architecture documentation using LLM instead of hardcoded template."""
        try:
            response = self.llm.invoke(self.architecture_docs_prompt.format_messages(
                domain=domain,
                scale=scale
            ))
            return response.content
        except Exception as e:
            logger.warning(f"LLM architecture docs generation failed, using fallback: {str(e)}")
            # Fallback to basic template
            return f"""# {domain} Application Architecture Overview\n\n## Overview\n\nThis document provides a high-level overview of the {domain} application's architecture, designed to operate at {scale} scale.\n\n## Key Components\n\n- **Frontend**: User interface layer.\n- **Backend API**: Core business logic and data access.\n- **Database**: Persistent data storage.\n\n## Data Flow\n\nUsers interact with the Frontend, which communicates with the Backend API. The Backend API interacts with the Database.\n\n## Scalability Considerations\n\n- Designed for horizontal scaling of backend services.\n- Database read replicas and sharding for data scalability.\n\n## Security Considerations\n\n- API authentication and authorization.\n- Data encryption at rest and in transit.\n\n## System Diagram (Conceptual)\n\n```mermaid\ngraph TD;\n    A[User] --> B(Frontend);\n    B --> C(Backend API);\n    C --> D[Database];\n```\n\n""" 