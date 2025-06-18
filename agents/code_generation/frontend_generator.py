"""
Frontend Generator Agent - Specialized in generating frontend code including UI components, 
pages, state management, and styling following the framework conventions.
"""

import json
import os
import time
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from datetime import datetime

# Ensure correct import paths
from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import ChatPromptTemplate
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
from message_bus import MessageBus
import logging
from agents.code_generation.models import GeneratedFile, CodeGenerationOutput
from tools.code_generation_utils import parse_llm_output_into_files

# Setup logger
logger = logging.getLogger(__name__)

class FrontendGeneratorAgent(BaseCodeGeneratorAgent):
    """
    Specialized Frontend Generator Agent that creates a complete frontend codebase
    in a single step including components, pages, state management, and styling.
    """
    
    def __init__(self, llm: BaseLanguageModel, memory, 
                 temperature: float,
                 output_dir: str, 
                 code_execution_tool: Optional[CodeExecutionTool] = None,
                 rag_retriever: Optional[BaseRetriever] = None,
                 message_bus: Optional[MessageBus] = None):
        """Initialize Frontend Generator Agent."""
        
        # Call super().__init__ with all required parameters
        super().__init__(
            llm=llm,
            memory=memory,
            agent_name="Frontend Generator Agent",
            temperature=temperature,
            output_dir=output_dir,
            code_execution_tool=code_execution_tool,
            rag_retriever=rag_retriever,
            message_bus=message_bus
        )
        
        # Initialize comprehensive prompt template
        self._initialize_prompt_templates()
        
        # Maximum tokens for generation
        self.max_tokens = 8192
        
        # Maximum context limits
        self.max_context_chars = {
            "rag": 1500,
            "ui_design": 2000,
            "related_components": 1000,
            "api_specs": 1200
        }
        
        # Maximum examples to include
        self.max_examples = {
            "components": 3,
            "pages": 2,
            "api_endpoints": 5
        }
    
    def _initialize_prompt_templates(self):
        """Initialize a single comprehensive prompt template for generating all frontend code."""
        
        multi_file_format = """
        CRITICAL OUTPUT FORMAT:
        You MUST provide your response as a single block of text. For each file you generate, 
        you MUST use the following format:

        ### FILE: path/to/your/file.ext

        ```filetype
        // The full content of the file goes here.
        ```

        Continue this pattern for all files you need to create. Your output should include:
        1. Component files (src/components/...)
        2. Pages/screens files (src/pages/... or src/screens/...)
        3. State management files (src/store/... or src/context/...)
        4. Styling files (src/styles/...)
        5. Configuration files (package.json, tsconfig.json if using TypeScript, etc.)
        6. Routing configuration

        Each file should be complete, well-structured, and follow best practices for the chosen framework.
        """

        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", 
             "You are an expert frontend developer specializing in modern JavaScript/TypeScript frameworks. "
             "Your task is to generate a complete frontend codebase according to the specified technical "
             "requirements and design specifications. You will create well-structured, production-ready "
             "code following best practices and architectural patterns appropriate for the chosen framework."
            ),
            ("human", 
             """
             Generate a complete frontend codebase for the following specifications:

             ## Tech Stack
             {tech_stack_summary}

             ## UI Design Specifications
             {ui_specs}

             ## API Integration
             {api_specs}

             ## System Design Overview
             {system_design_overview}

             ## Requirements
             Generate a complete frontend application including:
             
             1. All UI components (reusable components and page-specific components)
             2. Page/screen components with proper layouts
             3. State management implementation ({state_management})
             4. Styling using {styling_approach}
             5. Routing configuration with {routing_library}
             6. Configuration files (package.json, etc.)

             ## Best Practices to Follow
             - Use proper folder structure and organization
             - Implement responsive design
             - Follow accessibility standards (WCAG)
             - Include error handling and loading states
             - Use proper TypeScript types if applicable
             - Add meaningful comments for complex logic

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
        Generate complete frontend codebase in a single step.
        
        Args:
            llm: Language model to use for generation
            invoke_config: Configuration for LLM invocation
            **kwargs: Additional arguments including requirements_analysis, tech_stack, system_design, etc.
            
        Returns:
            Dictionary conforming to the CodeGenerationOutput model
        """
        self.log_info("Starting comprehensive frontend code generation")
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
            
            # Extract frontend technology details
            frontend_tech = self._extract_frontend_tech(tech_stack)
            framework = frontend_tech.get("framework", "React")
            styling_approach = frontend_tech.get("css_framework", frontend_tech.get("styling", "CSS"))
            state_management = frontend_tech.get("state_management", "Context API")
            routing_library = frontend_tech.get("routing", "react-router")
            
            self.log_info(f"Using frontend stack: {framework} with {styling_approach}, {state_management}, {routing_library}")
            
            # Create concise tech stack summary
            tech_stack_summary = self._create_tech_stack_summary(frontend_tech)
            
            # Extract UI specifications and API endpoints
            ui_specs = self._extract_ui_specs(system_design)
            api_specs = self._extract_api_specs(system_design, tech_stack)
            
            # Create system design overview
            system_design_overview = self._create_system_design_overview(system_design)
            
            # Get RAG context for frontend development
            rag_context = self._get_frontend_rag_context(framework, styling_approach, state_management)
            
            # Format UI specs for the prompt
            ui_specs_formatted = json.dumps(ui_specs, indent=2)
            api_specs_formatted = json.dumps(api_specs, indent=2)
            
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
            
            # Set temperature - slightly higher if revision to encourage creative fixes
            adjusted_temp = self._get_adjusted_temperature(is_revision)
            
            # Use binding pattern for temperature
            llm_with_temp = llm.bind(
                temperature=adjusted_temp,
                max_tokens=self.max_tokens
            )
            
            # Add monitoring context
            invoke_config["agent_context"] = f"{self.agent_name}:{framework}_generation"
            invoke_config["temperature_used"] = adjusted_temp
            invoke_config["is_revision"] = is_revision
            
            # Execute LLM call to generate all frontend artifacts
            self.log_info(f"Generating {framework} frontend with temperature {adjusted_temp}")
            response = llm_with_temp.invoke(
                self.prompt_template.format(
                    tech_stack_summary=tech_stack_summary,
                    ui_specs=ui_specs_formatted,
                    api_specs=api_specs_formatted,
                    system_design_overview=system_design_overview,
                    state_management=state_management,
                    styling_approach=styling_approach,
                    routing_library=routing_library,
                    rag_context=rag_context,
                    code_review_feedback=code_review_section
                ),
                config=invoke_config
            )
            
            # Extract content from response
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Store the activity
            self.memory.store_agent_activity(
                agent_name=self.agent_name,
                activity_type=f"frontend_{generation_type}",
                prompt=str(self.prompt_template),
                response=content[:1000] + "..." if len(content) > 1000 else content,
                metadata={
                    "framework": framework,
                    "is_revision": is_revision,
                    "temperature": adjusted_temp
                }
            )
            
            # Parse the multi-file output
            generated_files = parse_llm_output_into_files(content)
            
            # If parsing fails, create some basic files
            if not generated_files:
                self.log_warning("Failed to parse multi-file output, generating default files")
                generated_files = self._create_default_frontend_files(frontend_tech)
            
            # Categorize files by type
            components_count = len([f for f in generated_files if "/components/" in f.file_path])
            pages_count = len([f for f in generated_files if "/pages/" in f.file_path or "/screens/" in f.file_path])
            state_count = len([f for f in generated_files if "/store/" in f.file_path or "/context/" in f.file_path])
            style_count = len([f for f in generated_files if "/styles/" in f.file_path or f.file_path.endswith((".css", ".scss"))])
            config_count = len([f for f in generated_files if f.file_path in ["package.json", "tsconfig.json", ".env", "webpack.config.js"]])
            
            # Set all files to success status (validation could be added later)
            for f in generated_files:
                if f.status == "generated":
                    f.status = "success"
            
            # Create structured output
            output = CodeGenerationOutput(
                generated_files=generated_files,
                summary=f"Generated {len(generated_files)} frontend files for {framework} application",
                status="success" if generated_files else "error",
                metadata={
                    "framework": framework,
                    "is_revision": is_revision,
                    "state_management": state_management,
                    "styling_approach": styling_approach,
                    "routing_library": routing_library,
                    "file_counts": {
                        "components": components_count,
                        "pages": pages_count,
                        "state": state_count,
                        "styles": style_count,
                        "config": config_count,
                        "total": len(generated_files)
                    },
                    "agent": self.agent_name,
                    "temperature_used": adjusted_temp,
                    "execution_time": time.time() - start_time
                }
            )
            
            # Log success message
            self.log_success(
                f"Frontend {generation_type} complete: {len(generated_files)} files generated "
                f"({components_count} components, {pages_count} pages, {state_count} state files)"
            )
            
            # Publish event if message bus is available
            if self.message_bus:
                self.message_bus.publish("frontend.generated", {
                    "framework": framework,
                    "file_count": len(generated_files),
                    "components_count": components_count,
                    "is_revision": is_revision,
                    "status": "success"
                })
            
            # Return as dictionary
            return output.dict()
            
        except Exception as e:
            self.log_error(f"Frontend {generation_type} failed: {str(e)}", exc_info=True)
            # Return error output using the standardized format
            error_output = CodeGenerationOutput(
                generated_files=self._create_default_frontend_files(
                    frontend_tech if 'frontend_tech' in locals() else self._create_default_tech_stack()
                ),
                summary=f"Error generating frontend code: {str(e)}",
                status="error",
                metadata={
                    "error": str(e),
                    "framework": framework if 'framework' in locals() else "unknown",
                    "agent": self.agent_name,
                    "timestamp": datetime.now().isoformat()
                }
            )
            return error_output.dict()
    
    def _get_adjusted_temperature(self, is_revision: bool) -> float:
        """
        Adjust temperature based on whether this is initial generation or revision.
        
        Args:
            is_revision: Whether this is a revision based on feedback
            
        Returns:
            Adjusted temperature value
        """
        # Use a lower temperature for initial code generation (more deterministic)
        initial_temp = max(0.1, min(self.temperature, 0.2))
        
        # Use slightly higher temperature for revisions to encourage creative fixes
        revision_temp = max(0.2, min(self.temperature + 0.1, 0.3))
        
        return revision_temp if is_revision else initial_temp
    
    def _extract_frontend_tech(self, tech_stack: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract frontend technology details from tech stack with robust validation.
        
        Args:
            tech_stack: The technology stack dictionary
            
        Returns:
            Frontend technology details with safe defaults
        """
        # Default values
        frontend_tech = {
            "language": "JavaScript",
            "framework": "React",
            "typescript": False,
            "css_framework": "None",
            "state_management": "Context API",
            "routing": "react-router"
        }
        
        try:
            # Validate tech_stack
            if not tech_stack or not isinstance(tech_stack, dict):
                self.log_warning("Invalid tech stack - using default frontend technologies")
                return frontend_tech
                
            # Extract from tech stack if available
            if "frontend" in tech_stack:
                frontend = tech_stack["frontend"]
                
                # Handle frontend as either dict, list, or string
                if isinstance(frontend, dict):
                    # Direct field extraction
                    if "framework" in frontend:
                        frontend_tech["framework"] = frontend["framework"]
                    if "language" in frontend:
                        frontend_tech["language"] = frontend["language"]
                    if "typescript" in frontend:
                        frontend_tech["typescript"] = bool(frontend["typescript"])
                    if "css_framework" in frontend:
                        frontend_tech["css_framework"] = frontend["css_framework"]
                    if "styling" in frontend:
                        frontend_tech["styling"] = frontend["styling"]
                    if "state_management" in frontend:
                        frontend_tech["state_management"] = frontend["state_management"]
                    if "routing" in frontend:
                        frontend_tech["routing"] = frontend["routing"]
                elif isinstance(frontend, list) and len(frontend) > 0:
                    # Extract from first item in list
                    first_item = frontend[0]
                    if isinstance(first_item, dict):
                        frontend_tech["framework"] = first_item.get("name", "React")
                    elif isinstance(first_item, str):
                        frontend_tech["framework"] = first_item
                elif isinstance(frontend, str):
                    frontend_tech["framework"] = frontend
                    
            # Additional check: if language is TypeScript, set typescript flag
            if frontend_tech["language"].lower() == "typescript":
                frontend_tech["typescript"] = True
                    
            self.log_info(f"Frontend tech: {frontend_tech['framework']} with {frontend_tech['language']}")
            return frontend_tech
            
        except Exception as e:
            self.log_warning(f"Error extracting frontend tech: {str(e)} - using defaults")
            return frontend_tech
    
    def _extract_ui_specs(self, system_design: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract UI specifications from system design with robust validation.
        
        Args:
            system_design: The system design dictionary
            
        Returns:
            UI specifications with safe defaults
        """
        # Default values
        ui_specs = {
            "screens": [],
            "components": [],
            "theme": {
                "colors": {
                    "primary": "#007bff",
                    "secondary": "#6c757d",
                    "background": "#ffffff",
                    "text": "#212529"
                },
                "typography": {
                    "fontFamily": "Arial, sans-serif"
                }
            },
            "user_roles": []
        }
        
        try:
            # Validate system_design
            if not system_design or not isinstance(system_design, dict):
                self.log_warning("Invalid system design - using default UI specs")
                # Infer minimal components and screens
                ui_specs["screens"] = [
                    {"name": "Home", "type": "screen", "description": "Homepage", "components": ["Header", "Footer"]}
                ]
                ui_specs["components"] = [
                    {"name": "Header", "type": "basic", "description": "Site header", "props": []},
                    {"name": "Footer", "type": "basic", "description": "Site footer", "props": []}
                ]
                return ui_specs
                
            # Extract from system design if available
            ui_section = None
            
            # Try multiple possible locations for UI specs
            if "ui" in system_design and isinstance(system_design["ui"], dict):
                ui_section = system_design["ui"]
            elif "frontend" in system_design and isinstance(system_design["frontend"], dict):
                ui_section = system_design["frontend"]
            elif "ui_design" in system_design and isinstance(system_design["ui_design"], dict):
                ui_section = system_design["ui_design"]
            
            # Extract data if we found a valid UI section
            if ui_section:
                # Extract screens with validation
                if "screens" in ui_section and isinstance(ui_section["screens"], list):
                    ui_specs["screens"] = ui_section["screens"]
                
                # Extract components with validation
                if "components" in ui_section and isinstance(ui_section["components"], list):
                    ui_specs["components"] = ui_section["components"]
                
                # Extract theme with validation
                if "theme" in ui_section and isinstance(ui_section["theme"], dict):
                    ui_specs["theme"] = ui_section["theme"]
                
                # Extract user roles with validation
                if "user_roles" in ui_section and isinstance(ui_section["user_roles"], list):
                    ui_specs["user_roles"] = ui_section["user_roles"]
            
            # If no screens defined, try to infer from other sections
            if not ui_specs["screens"]:
                ui_specs["screens"] = self._infer_screens_from_system_design(system_design)
            
            # If no components defined, create some basic ones
            if not ui_specs["components"]:
                ui_specs["components"] = self._infer_components_from_screens(ui_specs["screens"])
            
            return ui_specs
            
        except Exception as e:
            self.log_warning(f"Error extracting UI specs: {str(e)} - using defaults")
            # Return default UI specs with minimal components
            ui_specs["screens"] = [
                {"name": "Home", "type": "screen", "description": "Homepage", "components": ["Header", "Footer"]}
            ]
            ui_specs["components"] = [
                {"name": "Header", "type": "basic", "description": "Site header", "props": []},
                {"name": "Footer", "type": "basic", "description": "Site footer", "props": []}
            ]
            return ui_specs
    
    def _extract_api_specs(self, system_design: Dict[str, Any], tech_stack: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract API specifications from system design for frontend integration.
        
        Args:
            system_design: System design specification
            tech_stack: Technology stack information
            
        Returns:
            Dictionary containing API endpoint information with safe defaults
        """
        # Default API specs structure
        api_specs = {
            "base_url": "http://localhost:3000/api",
            "endpoints": [],
            "auth_required": False,
            "auth_type": "none"
        }
        
        try:
            # Validate inputs
            if not system_design or not isinstance(system_design, dict):
                self.log_warning("Invalid system design for API extraction - using default API specs")
                return api_specs
                
            # Extract base URL from system design
            if "api" in system_design:
                api_section = system_design["api"]
                if isinstance(api_section, dict) and "base_url" in api_section:
                    api_specs["base_url"] = api_section["base_url"]
            
            # Extract API endpoints from system design
            endpoints = []
            
            # Try different possible locations for endpoints
            if "api" in system_design and isinstance(system_design["api"], dict):
                api_section = system_design["api"]
                if "endpoints" in api_section and isinstance(api_section["endpoints"], list):
                    endpoints = api_section["endpoints"]
            elif "endpoints" in system_design and isinstance(system_design["endpoints"], list):
                endpoints = system_design["endpoints"]
                
            # Validate each endpoint
            valid_endpoints = []
            for endpoint in endpoints:
                if isinstance(endpoint, dict) and "path" in endpoint:
                    valid_endpoints.append(endpoint)
                    
            api_specs["endpoints"] = valid_endpoints
            
            # If no endpoints are explicitly defined, try to infer from system entities
            if not api_specs["endpoints"] and "entities" in system_design:
                entities = system_design["entities"]
                if isinstance(entities, dict):
                    inferred_endpoints = []
                    
                    for entity_name, entity_data in entities.items():
                        # Create CRUD endpoints for each entity
                        inferred_endpoints.extend([
                            {
                                "path": f"/{entity_name.lower()}",
                                "method": "GET",
                                "description": f"Get all {entity_name} records",
                                "auth_required": True
                            },
                            {
                                "path": f"/{entity_name.lower()}/{{id}}",
                                "method": "GET", 
                                "description": f"Get {entity_name} by ID",
                                "auth_required": True
                            },
                            {
                                "path": f"/{entity_name.lower()}",
                                "method": "POST",
                                "description": f"Create new {entity_name}",
                                "auth_required": True
                            },
                            {
                                "path": f"/{entity_name.lower()}/{{id}}",
                                "method": "PUT",
                                "description": f"Update {entity_name}",
                                "auth_required": True
                            },
                            {
                                "path": f"/{entity_name.lower()}/{{id}}",
                                "method": "DELETE",
                                "description": f"Delete {entity_name}",
                                "auth_required": True
                            }
                        ])
                    
                    api_specs["endpoints"] = inferred_endpoints
            
            # Determine auth requirements
            if "auth" in system_design:
                auth_info = system_design["auth"]
                api_specs["auth_required"] = True
                
                if isinstance(auth_info, dict) and "type" in auth_info:
                    api_specs["auth_type"] = auth_info["type"]
                else:
                    api_specs["auth_type"] = "jwt"
            
            # Limit number of endpoints to avoid token overload
            max_endpoints = getattr(self, "max_examples", {}).get("api_endpoints", 5)
            if len(api_specs["endpoints"]) > max_endpoints:
                api_specs["endpoints"] = api_specs["endpoints"][:max_endpoints]
                api_specs["note"] = f"Limited to {max_endpoints} endpoints for demonstration"
            
            return api_specs
            
        except Exception as e:
            self.log_warning(f"Error extracting API specs: {str(e)} - using defaults")
            # Add minimal default endpoints
            api_specs["endpoints"] = [
                {
                    "path": "/users",
                    "method": "GET",
                    "description": "Get all users",
                    "auth_required": True
                },
                {
                    "path": "/users/{id}",
                    "method": "GET",
                    "description": "Get user by ID",
                    "auth_required": True
                }
            ]
            return api_specs
    
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
            
            # Extract main components and features
            components = []
            features = []
            
            # Try to find components and features in various locations
            if "components" in system_design:
                comps = system_design["components"]
                if isinstance(comps, list):
                    for comp in comps:
                        if isinstance(comp, dict) and "name" in comp:
                            components.append(f"- {comp['name']}: {comp.get('description', '')}")
                elif isinstance(comps, dict):
                    for name, details in comps.items():
                        if isinstance(details, dict) and "description" in details:
                            components.append(f"- {name}: {details['description']}")
                        else:
                            components.append(f"- {name}")
            
            # Check for features section
            if "features" in system_design:
                feats = system_design["features"]
                if isinstance(feats, list):
                    for feat in feats:
                        if isinstance(feat, dict) and "name" in feat:
                            features.append(f"- {feat['name']}: {feat.get('description', '')}")
                        elif isinstance(feat, str):
                            features.append(f"- {feat}")
                elif isinstance(feats, dict):
                    for name, details in feats.items():
                        features.append(f"- {name}")
            
            # Add components and features to overview
            if components:
                overview.append("Main Components:")
                overview.extend(components)
            
            if features:
                overview.append("Key Features:")
                overview.extend(features)
            
            # Extract user roles if available
            user_roles = []
            if "user_roles" in system_design:
                roles = system_design["user_roles"]
                if isinstance(roles, list):
                    for role in roles:
                        if isinstance(role, dict) and "name" in role:
                            user_roles.append(f"- {role['name']}")
                        elif isinstance(role, str):
                            user_roles.append(f"- {role}")
            
            if user_roles:
                overview.append("User Roles:")
                overview.extend(user_roles)
            
            # Fallback if no overview created
            if not overview:
                return "Standard web application with frontend, backend and database components."
                
            return "\n".join(overview)
            
        except Exception as e:
            self.log_warning(f"Error creating system design overview: {e}")
            return "Standard web application with frontend, backend and database components."
    
    def _create_tech_stack_summary(self, frontend_tech: Dict[str, Any]) -> str:
        """
        Create a concise summary of the frontend tech stack.
        
        Args:
            frontend_tech: Frontend technology details
            
        Returns:
            String summary of tech stack
        """
        if not frontend_tech:
            return "React with JavaScript"
        
        framework = frontend_tech.get("framework", "React")
        language = "TypeScript" if frontend_tech.get("typescript", False) else frontend_tech.get("language", "JavaScript")
        state = frontend_tech.get("state_management", "Context API")
        styling = frontend_tech.get("css_framework", frontend_tech.get("styling", "CSS"))
        routing = frontend_tech.get("routing", "react-router")
        
        return f"{framework} with {language}, {state} for state management, {styling} for styling, and {routing} for routing"
    
    def _get_frontend_rag_context(self, framework: str, styling: str, state_management: str) -> str:
        """
        Get RAG context for frontend development.
        
        Args:
            framework: Frontend framework name
            styling: Styling approach
            state_management: State management library
            
        Returns:
            RAG context string for frontend development
        """
        if not self.rag_retriever:
            return ""
        
        try:
            # Create targeted queries for better RAG results
            queries = [
                f"{framework} best practices project structure",
                f"{state_management} with {framework} implementation",
                f"{styling} styling patterns for {framework}"
            ]
            
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
            self.log_warning(f"Error retrieving RAG context: {e}")
            return ""
    
    def _create_default_frontend_files(self, frontend_tech: Dict[str, Any]) -> List[GeneratedFile]:
        """
        Create default frontend files when generation fails.
        
        Args:
            frontend_tech: Frontend technology details
            
        Returns:
            List of GeneratedFile objects with default content
        """
        framework = frontend_tech.get("framework", "").lower()
        is_typescript = frontend_tech.get("typescript", False)
        
        # File extension based on language
        jsx_ext = "tsx" if is_typescript else "jsx"
        js_ext = "ts" if is_typescript else "js"
        
        # Default README content
        readme_content = f"""# Frontend Application

## Technology Stack
- Framework: {frontend_tech.get('framework', 'React')}
- Language: {frontend_tech.get('language', 'JavaScript')}{'with TypeScript' if is_typescript else ''}
- State Management: {frontend_tech.get('state_management', 'Context API')}
- Styling: {frontend_tech.get('css_framework', frontend_tech.get('styling', 'CSS'))}
- Routing: {frontend_tech.get('routing', 'react-router')}

## Getting Started
1. Install dependencies: `npm install`
2. Start development server: `npm start`
3. Build for production: `npm run build`

## Project Structure
- src/components: Reusable UI components
- src/pages: Page components
- src/styles: Styling files
- src/store: State management
"""
        
        # Create basic app component based on framework
        app_content = ""
        if framework == "react" or framework == "preact":
            app_content = f"""import React from 'react';
import {{ BrowserRouter, Routes, Route }} from 'react-router-dom';
import './App.css';
import Header from './components/Header';
import Footer from './components/Footer';
import HomePage from './pages/HomePage';
import AboutPage from './pages/AboutPage';

function App() {{
  return (
    <div className="App">
      <BrowserRouter>
        <Header />
        <main>
          <Routes>
            <Route path="/" element={{<HomePage />}} />
            <Route path="/about" element={{<AboutPage />}} />
            <Route path="*" element={{<div>Page not found</div>}} />
          </Routes>
        </main>
        <Footer />
      </BrowserRouter>
    </div>
  );
}}

export default App;
"""
        elif framework == "vue":
            app_content = """<template>
  <div id="app">
    <Header />
    <router-view />
    <Footer />
  </div>
</template>

<script>
import Header from './components/Header.vue'
import Footer from './components/Footer.vue'

export default {
  name: 'App',
  components: {
    Header,
    Footer
  }
}
</script>

<style>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: #2c3e50;
  margin-top: 60px;
}
</style>
"""
        elif framework == "angular":
            app_content = """import { Component } from '@angular/core';

@Component({
  selector: 'app-root',
  template: `
    <app-header></app-header>
    <main>
      <router-outlet></router-outlet>
    </main>
    <app-footer></app-footer>
  `,
  styles: []
})
export class AppComponent {
  title = 'frontend-app';
}
"""
        else:
            # Default to React-like syntax
            app_content = """import React from 'react';
import './App.css';

function App() {
  return (
    <div className="App">
      <header>
        <h1>My Application</h1>
      </header>
      <main>
        <p>Welcome to the application!</p>
      </main>
      <footer>
        <p>© 2025</p>
      </footer>
    </div>
  );
}

export default App;
"""
        
        # Basic CSS
        app_css = """/* App styles */
.App {
  text-align: center;
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

header {
  margin-bottom: 20px;
}

main {
  min-height: 400px;
}

footer {
  margin-top: 40px;
  padding-top: 10px;
  border-top: 1px solid #eee;
  font-size: 0.8em;
}
"""
        
        # Basic index file
        index_content = """import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
"""
        if framework == "vue":
            index_content = """import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import store from './store'

createApp(App)
  .use(router)
  .use(store)
  .mount('#app')
"""
        
        # Basic component files
        header_content = """import React from 'react';

function Header() {
  return (
    <header>
      <h1>My Application</h1>
      <nav>
        <ul>
          <li><a href="/">Home</a></li>
          <li><a href="/about">About</a></li>
        </ul>
      </nav>
    </header>
  );
}

export default Header;
"""
        footer_content = """import React from 'react';

function Footer() {
  return (
    <footer>
      <p>© 2025 My Application. All rights reserved.</p>
    </footer>
  );
}

export default Footer;
"""
        
        # Simple home page
        home_page_content = """import React from 'react';

function HomePage() {
  return (
    <div className="home-page">
      <h2>Welcome to the Application</h2>
      <p>This is the home page of the application.</p>
    </div>
  );
}

export default HomePage;
"""
        
        # Simple about page
        about_page_content = """import React from 'react';

function AboutPage() {
  return (
    <div className="about-page">
      <h2>About Us</h2>
      <p>This is the about page of the application.</p>
    </div>
  );
}

export default AboutPage;
"""
        
        # Package.json content
        package_json = """{
  "name": "frontend-app",
  "version": "0.1.0",
  "private": true,
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.8.0",
    "react-scripts": "5.0.1"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test",
    "eject": "react-scripts eject"
  },
  "eslintConfig": {
    "extends": [
      "react-app",
      "react-app/jest"
    ]
  },
  "browserslist": {
    "production": [
      ">0.2%",
      "not dead",
      "not op_mini all"
    ],
    "development": [
      "last 1 chrome version",
      "last 1 firefox version",
      "last 1 safari version"
    ]
  }
}
"""
        
        # Create default files
        generated_files = [
            GeneratedFile(
                file_path="README.md",
                content=readme_content,
                purpose="Project documentation",
                status="generated"
            ),
            GeneratedFile(
                file_path=f"src/App.{jsx_ext}",
                content=app_content,
                purpose="Main application component",
                status="generated"
            ),
            GeneratedFile(
                file_path="src/App.css",
                content=app_css,
                purpose="Application styles",
                status="generated"
            ),
            GeneratedFile(
                file_path=f"src/index.{jsx_ext}",
                content=index_content,
                purpose="Application entry point",
                status="generated"
            ),
            GeneratedFile(
                file_path=f"src/components/Header.{jsx_ext}",
                content=header_content,
                purpose="Header component",
                status="generated"
            ),
            GeneratedFile(
                file_path=f"src/components/Footer.{jsx_ext}",
                content=footer_content,
                purpose="Footer component",
                status="generated"
            ),
            GeneratedFile(
                file_path=f"src/pages/HomePage.{jsx_ext}",
                content=home_page_content,
                purpose="Home page component",
                status="generated"
            ),
            GeneratedFile(
                file_path=f"src/pages/AboutPage.{jsx_ext}",
                content=about_page_content,
                purpose="About page component",
                status="generated"
            ),
            GeneratedFile(
                file_path="package.json",
                content=package_json,
                purpose="Package configuration",
                status="generated"
            )
        ]
        
        return generated_files
    
    def _infer_screens_from_system_design(self, system_design: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Infer UI screens from system design when not explicitly defined.
        
        Args:
            system_design: System design specifications
            
        Returns:
            List of inferred screen components
        """
        inferred_screens = []
        
        # Common screens for any application
        inferred_screens.append({
            "name": "Home",
            "type": "screen",
            "description": "Main landing page",
            "components": ["Header", "Footer", "MainContent"]
        })
        
        inferred_screens.append({
            "name": "About",
            "type": "screen",
            "description": "About page",
            "components": ["Header", "Footer", "AboutContent"]
        })
        
        # Add authentication screens if auth is mentioned
        if "auth" in str(system_design).lower():
            inferred_screens.append({
                "name": "Login",
                "type": "screen",
                "description": "User authentication screen",
                "components": ["LoginForm"]
            })
            
            inferred_screens.append({
                "name": "Register",
                "type": "screen",
                "description": "New user registration screen",
                "components": ["RegistrationForm"]
            })
        
        # Add screens based on entities
        if "entities" in system_design:
            entities = system_design["entities"]
            if isinstance(entities, dict):
                for entity_name, entity_data in entities.items():
                    # Create list screen
                    inferred_screens.append({
                        "name": f"{entity_name}List",
                        "type": "screen",
                        "description": f"List view of all {entity_name} records",
                        "components": ["DataTable", "SearchFilter", "Pagination"]
                    })
                    
                    # Create detail screen
                    inferred_screens.append({
                        "name": f"{entity_name}Detail",
                        "type": "screen",
                        "description": f"Detailed view of a single {entity_name} record",
                        "components": ["DetailView", "ActionButtons"]
                    })
                    
                    # Create edit/create screen
                    inferred_screens.append({
                        "name": f"{entity_name}Form",
                        "type": "screen",
                        "description": f"Create or edit a {entity_name} record",
                        "components": ["Form", "FormFields", "SubmitButton"]
                    })
            elif isinstance(entities, list):
                for entity in entities:
                    if isinstance(entity, dict) and "name" in entity:
                        entity_name = entity["name"]
                        # Create same set of screens
                        inferred_screens.append({
                            "name": f"{entity_name}List",
                            "type": "screen",
                            "description": f"List view of all {entity_name} records",
                            "components": ["DataTable", "SearchFilter", "Pagination"]
                        })
                        
                        inferred_screens.append({
                            "name": f"{entity_name}Detail",
                            "type": "screen",
                            "description": f"Detailed view of a single {entity_name} record",
                            "components": ["DetailView", "ActionButtons"]
                        })
                        
                        inferred_screens.append({
                            "name": f"{entity_name}Form",
                            "type": "screen",
                            "description": f"Create or edit a {entity_name} record",
                            "components": ["Form", "FormFields", "SubmitButton"]
                        })
        
        return inferred_screens

    def _infer_components_from_screens(self, screens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Create basic component list from screens when not explicitly defined.
        
        Args:
            screens: List of screen definitions
            
        Returns:
            List of inferred components
        """
        # Collect all component names referenced in screens
        component_names = set()
        for screen in screens:
            components = screen.get("components", [])
            if isinstance(components, list):
                component_names.update(components)
        
        # Create basic component definitions
        inferred_components = []
        
        # Standard components that most UIs will need
        standard_components = [
            {
                "name": "Header",
                "type": "basic",
                "description": "Application header with logo and navigation",
                "props": []
            },
            {
                "name": "Footer",
                "type": "basic",
                "description": "Application footer",
                "props": []
            },
            {
                "name": "MainContent",
                "type": "basic",
                "description": "Main content area",
                "props": []
            },
            {
                "name": "AboutContent",
                "type": "basic",
                "description": "About page content",
                "props": []
            }
        ]
        
        # Add standard components first
        for component in standard_components:
            if component["name"] in component_names:
                inferred_components.append(component)
                component_names.remove(component["name"])
        
        # Create definitions for remaining component names
        for name in component_names:
            # Infer component type and description based on name
            component_type = "basic"
            description = f"{name} component"
            props = []
            
            # Handle special cases
            if "Form" in name:
                component_type = "form"
                description = f"{name} form component for data entry"
                props = [{"name": "onSubmit", "type": "function", "description": "Form submission handler", "required": True}]
            elif "Table" in name or "List" in name or "Grid" in name:
                component_type = "data-display"
                description = f"{name} component for displaying data collections"
                props = [{"name": "data", "type": "array", "description": "Data to display", "required": True}]
            elif "Button" in name:
                component_type = "interactive"
                description = f"{name} interactive button component"
                props = [{"name": "onClick", "type": "function", "description": "Click handler", "required": True}]
            elif "Card" in name:
                component_type = "layout"
                description = f"{name} card layout component"
                props = [{"name": "children", "type": "node", "description": "Card content", "required": True}]
            
            inferred_components.append({
                "name": name,
                "type": component_type,
                "description": description,
                "props": props
            })
        
        return inferred_components
    
    def _create_default_tech_stack(self) -> Dict[str, Any]:
        """Create a default tech stack when input is invalid."""
        return {
            "frontend": {
                "framework": "React",
                "language": "JavaScript",
                "styling": "CSS",
                "state_management": "Context API",
                "routing": "react-router"
            }
        }

    def _create_default_system_design(self) -> Dict[str, Any]:
        """Create a default system design when input is invalid."""
        return {
            "ui": {
                "screens": [
                    {
                        "name": "Home",
                        "type": "screen",
                        "description": "Main landing page",
                        "components": ["Header", "Footer", "MainContent"]
                    },
                    {
                        "name": "About",
                        "type": "screen",
                        "description": "About page",
                        "components": ["Header", "Footer", "AboutContent"]
                    }
                ],
                "components": [
                    {
                        "name": "Header",
                        "type": "basic",
                        "description": "Application header with navigation",
                        "props": []
                    },
                    {
                        "name": "Footer",
                        "type": "basic",
                        "description": "Application footer",
                        "props": []
                    },
                    {
                        "name": "MainContent",
                        "type": "basic",
                        "description": "Main content area",
                        "props": []
                    },
                    {
                        "name": "AboutContent",
                        "type": "basic",
                        "description": "About page content",
                        "props": []
                    }
                ],
                "theme": {
                    "colors": {
                        "primary": "#007bff",
                        "secondary": "#6c757d",
                        "background": "#ffffff",
                        "text": "#212529"
                    },
                    "typography": {
                        "fontFamily": "Arial, sans-serif"
                    }
                }
            }
        }




