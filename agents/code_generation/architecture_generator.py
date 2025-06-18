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
from agents.code_generation.models import GeneratedFile, CodeGenerationOutput
from tools.code_generation_utils import parse_llm_output_into_files

# Setup logger
logger = logging.getLogger(__name__)

class ArchitectureGeneratorAgent(BaseCodeGeneratorAgent):
    """
    Specialized Architecture Generator Agent with comprehensive project structure generation,
    configuration file creation, and architectural foundation implementation.
    """
    
    def __init__(self, llm: BaseLanguageModel, memory, temperature: float, output_dir: str, 
                 code_execution_tool: CodeExecutionTool,
                 rag_retriever: Optional[BaseRetriever] = None):
        
        # Fixed: Proper call to superclass constructor with all required parameters
        super().__init__(
            llm=llm,
            memory=memory,
            agent_name="Architecture Generator Agent",
            temperature=temperature,
            output_dir=output_dir,
            code_execution_tool=code_execution_tool,
            rag_retriever=rag_retriever,
            message_bus=None
        )
        
        # Initialize specialized prompt template
        self._initialize_prompt_templates()
        
        # Maximum tokens for generation
        self.max_tokens = 8192
        
        # Maximum RAG documents to retrieve per query
        self.max_rag_docs = 3
        
    def _initialize_prompt_templates(self):
        """
        Initialize a single comprehensive prompt template for generating all architecture artifacts.
        """
        multi_file_format = """
        CRITICAL OUTPUT FORMAT:
        You MUST provide your response as a single block of text. For each file you generate, 
        you MUST use the following format:

        ### FILE: path/to/your/file.ext
        ```filetype
        # The full content of the file goes here
        ```

        Continue this pattern for all files you need to create. Files should include:
        1. Configuration files (.gitignore, package.json, requirements.txt, etc.)
        2. Project setup files (README.md, CONTRIBUTING.md, etc.)
        3. Base architectural files for the chosen framework/pattern
        4. Docker configuration if applicable
        5. Build configuration files
        """

        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system",
             "You are an expert software architect who specializes in creating project structures, "
             "configuration files, and architectural foundation code. You must create a complete "
             "project architecture that follows best practices for the chosen technology stack "
             "and architectural pattern. Your output should be production-ready, well-structured, "
             "and include all necessary configuration files and documentation."),
            ("human",
             "Generate a complete project architecture with all necessary configuration files and base structure.\n\n"
             
             "## Project Context\n"
             "Tech Stack: {tech_stack_summary}\n"
             "Architecture Pattern: {architecture_pattern}\n\n"
             "System Design Overview: {system_design_overview}\n\n"
             "Full Tech Stack Details:\n{tech_stack_details}\n\n"
             "Full System Design:\n{system_design}\n\n"
             
             "## Requirements\n"
             "1. Project Structure: Create a complete directory structure based on best practices for this tech stack.\n"
             "2. Configuration Files: Generate all necessary configuration files (package.json, requirements.txt, etc.).\n"
             "3. Documentation: Create README.md and other documentation files.\n"
             "4. Build Configuration: Include build scripts and configuration.\n"
             "5. Docker Setup: Create Dockerfile and docker-compose.yml if applicable.\n"
             "6. Base Architecture: Set up the foundational architectural files.\n\n"
             
             "## Best Practices\n"
             "{rag_context}\n\n"
             
             "{code_review_feedback}\n\n"
             
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
                tech_stack = self._create_default_tech_stack()
                
            if not isinstance(system_design, dict):
                self.log_warning("Invalid system design - using default")
                system_design = self._create_default_system_design()
            
            # Extract key information from inputs
            tech_stack_summary = self._create_tech_stack_summary(tech_stack)
            architecture_pattern = tech_stack.get("architecture_pattern", "Layered")
            if not architecture_pattern:
                architecture_pattern = self._determine_architecture_pattern(tech_stack, system_design)
            
            # Create concise system design overview
            system_design_overview = self._create_system_design_overview(system_design)
            
            # Get RAG context for architectural best practices
            rag_context = self._get_architecture_rag_context(tech_stack_summary, architecture_pattern)
            
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
            adjusted_temp = max(0.1, min(self.temperature, 0.2))
            
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
            self.log_info(f"Generating {architecture_pattern} architecture with temperature {adjusted_temp}")
            response = llm_with_temp.invoke(
                self.prompt_template.format(
                    tech_stack_summary=tech_stack_summary,
                    architecture_pattern=architecture_pattern,
                    system_design_overview=system_design_overview,
                    tech_stack_details=tech_stack_details,
                    system_design=pruned_system_design,
                    rag_context=rag_context,
                    code_review_feedback=code_review_section
                ),
                config=invoke_config
            )
            
            # Extract content from response
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Log abbreviated version of the content for debug purposes
            self.log_debug(f"LLM response (abbreviated): {content[:500]}...")
            
            # Parse the multi-file output
            generated_files = parse_llm_output_into_files(content)
            
            # Handle case where parsing fails
            if not generated_files:
                self.log_warning("Failed to parse multi-file output, generating default files")
                # Generate default README and other essential files
                generated_files = self._create_default_architecture_files(
                    tech_stack_summary, architecture_pattern
                )
            
            # Create directories first before saving files
            self._create_directories_from_files(generated_files)
            
            # Create structured output
            output = CodeGenerationOutput(
                generated_files=generated_files,
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
            
            # Log success message
            self.log_success(
                f"Architecture {generation_type} complete: {len(generated_files)} files generated"
            )
            
            # Return as dictionary
            return output.dict()
            
        except Exception as e:
            self.log_error(f"Architecture generation failed: {str(e)}", exc_info=True)
            # Return error output using the standardized format
            error_output = CodeGenerationOutput(
                generated_files=self._create_default_architecture_files(
                    tech_stack_summary if 'tech_stack_summary' in locals() else "Default Stack",
                    architecture_pattern if 'architecture_pattern' in locals() else "Layered"
                ),
                summary=f"Error generating architecture code: {str(e)}",
                status="error",
                metadata={
                    "error": str(e),
                    "agent": self.agent_name,
                    "timestamp": datetime.now().isoformat()
                }
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
    
    def _determine_architecture_pattern(self, tech_stack: Dict, system_design: Dict) -> str:
        """
        Determine the appropriate architecture pattern if not explicitly specified.
        
        Args:
            tech_stack: Technology stack details
            system_design: System design details
            
        Returns:
            String containing the determined architecture pattern
        """
        # Default architecture pattern
        pattern = "Layered"
        
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
    
    def _get_architecture_rag_context(self, tech_stack_summary: str, architecture_pattern: str) -> str:
        """
        Get RAG context specific to architecture implementation.
        
        Args:
            tech_stack_summary: Summary of the technology stack
            architecture_pattern: The architecture pattern name
            
        Returns:
            RAG context string for architecture best practices
        """
        if not self.rag_retriever:
            return ""
            
        try:
            # Create targeted queries for better RAG results
            queries = [
                f"{tech_stack_summary} project structure {architecture_pattern}",
                f"{architecture_pattern} architecture best practices",
                f"{tech_stack_summary} configuration files"
            ]
            
            combined_context = []
            for query in queries:
                try:
                    docs = self.rag_retriever.get_relevant_documents(query)
                    if docs:
                        context = "\n\n".join([doc.page_content for doc in docs[:self.max_rag_docs]])
                        combined_context.append(f"# {query.title()}\n{context}")
                except Exception as e:
                    self.log_warning(f"Error retrieving RAG for '{query}': {e}")
            
            return "\n\n".join(combined_context)
            
        except Exception as e:
            self.log_warning(f"Error retrieving RAG context: {e}")
            return ""
    
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
    
    def _create_default_tech_stack(self) -> Dict:
        """Create a default tech stack when none is provided"""
        return {
            "frontend": {"selection": "React"},
            "backend": {"selection": "Node.js"},
            "database": {"selection": "MongoDB"},
            "architecture_pattern": "MVC"
        }
        
    def _create_default_system_design(self) -> Dict:
        """Create a default system design when none is provided"""
        return {
            "architecture": {
                "description": "Default MVC architecture",
                "components": {
                    "frontend": {"description": "React frontend"},
                    "backend": {"description": "Node.js API server"},
                    "database": {"description": "MongoDB data storage"}
                }
            }
        }
    
    def _create_default_architecture_files(self, tech_stack_summary: str, architecture_pattern: str) -> List[Dict]:
        """
        Create default architecture files when generation fails.
        
        Args:
            tech_stack_summary: Summary of the technology stack
            architecture_pattern: The architecture pattern
            
        Returns:
            List of GeneratedFile dictionaries with default content
        """
        readme_content = f"""# Project Overview

## Technology Stack
{tech_stack_summary}

## Architecture
{architecture_pattern}

## Setup Instructions
1. Clone this repository
2. Install dependencies
3. Configure environment variables
4. Run the application

## Project Structure
- src/: Main source code
- docs/: Documentation
- tests/: Test files

## Development Workflow
TBD

Generated by Architecture Generator Agent (default template)
"""

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
"""

        return [
            GeneratedFile(
                file_path="README.md",
                content=readme_content,
                purpose="Project documentation",
                status="generated"
            ),
            GeneratedFile(
                file_path=".gitignore",
                content=gitignore_content,
                purpose="Git ignore configuration",
                status="generated"
            )
        ]