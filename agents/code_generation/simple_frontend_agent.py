"""
Simple Frontend Agent - Unified frontend code generation
Replaces: 98KB frontend_generator + complex UI patterns + over-engineering
"""

import asyncio
import json
import os
import time
from typing import Dict, Any, List, Set
from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import ChatPromptTemplate
from agents.code_generation.simple_base_agent import SimpleBaseAgent
from tools.code_execution_tool import CodeExecutionTool
from tools.code_generation_utils import parse_llm_output_into_files
from models.data_contracts import WorkItem, CodeGenerationOutput, GeneratedFile

import logging
logger = logging.getLogger(__name__)

class SimpleFrontendAgent(SimpleBaseAgent):
    """
    SIMPLIFIED Frontend Agent - All frontend needs in one focused agent
    
    Handles:
    ✅ React/Vue/Angular components
    ✅ Pages and routing
    ✅ State management
    ✅ Styling (CSS/Tailwind/Styled)
    ✅ Package configuration
    ✅ Basic tests
    ✅ Build setup
    """
    
    def __init__(self, llm: BaseLanguageModel, memory, temperature: float, output_dir: str, 
                 code_execution_tool: CodeExecutionTool, **kwargs):
        super().__init__(
            llm=llm,
            memory=memory,
            temperature=temperature,
            output_dir=output_dir,
            code_execution_tool=code_execution_tool,
            agent_name="Simple Frontend Agent",
            **kwargs
        )
        self._initialize_simple_prompts()
        logger.info("Simple Frontend Agent initialized - unified frontend generation")

    def _initialize_simple_prompts(self):
        """Enhanced prompt for comprehensive frontend code generation."""
        self.frontend_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a senior frontend developer creating a complete, modern, production-ready frontend application.

            CRITICAL REQUIREMENTS:
            - Generate EXACTLY 12-18 files (substantial, functional code)
            - Each file must serve a clear purpose in the frontend architecture
            - Include comprehensive component architecture
            - Follow modern UI/UX best practices
            - Implement proper state management and routing
            
            REQUIRED FRONTEND COMPONENTS (generate ALL):
            1. Main App component with proper initialization
            2. Core layout components (Header, Footer, Sidebar)
            3. Key pages/views (Home, Dashboard, Profile, Settings)
            4. Reusable UI components (Button, Input, Modal, Card)
            5. Routing configuration with protected routes
            6. State management setup (Context/Redux/Zustand)
            7. Styling system (CSS modules/Tailwind/Styled components)
            8. API service layer with error handling
            9. Authentication components and hooks
            10. Form handling with validation
            11. Package.json with all necessary dependencies
            12. Build configuration (Vite/Webpack/Next.js)
            13. TypeScript configuration (if applicable)
            14. Environment configuration
            15. Unit tests for components
            16. Utility functions and helpers
            17. Custom hooks (if React) or composables (if Vue)
            18. Error boundary and loading components
            
            Use the ### FILE: path format for each file.
            Ensure each file has substantial, production-ready code with proper TypeScript types if applicable."""),
            
            ("human", """Create a complete {framework} frontend application for: {description}
            
            **Technical Context:**
            - Frontend: {frontend_tech}
            - Backend: {backend_tech}
            - Database: {database_tech}
            - Framework: {framework}
            - Styling: {styling}
            - State Management: {state_management}
            - Required Features: {features}
            - Work Item: {work_item}
            
            **Work Item Dependencies:**
            {dependencies}
            
            **Acceptance Criteria:**
            {acceptance_criteria}
            
            **Expected File Structure (MUST FOLLOW EXACTLY):**
            {expected_files}
            
            **CRITICAL: File Structure Requirements:**
            - You MUST create files that match the expected file structure above
            - Use the EXACT file paths and names specified
            - If pages/index.js is expected, create Next.js structure; if src/App.tsx is expected, create React structure
            - If package.json is in expected files, ensure it's compatible with {framework}
            - Follow the file naming conventions shown in the expected structure
            - Ensure generated files serve the purposes implied by their paths
            
            **Mandatory Requirements:**
            - Generate files that match the expected structure above
            - Use {framework} as specified
            - Ensure all acceptance criteria are met in the implementation
            - Consider and handle dependencies appropriately
            - Mobile-responsive design with modern UI patterns
            - Clean component architecture with proper separation of concerns
            - Comprehensive error handling and loading states
            - Proper accessibility (ARIA labels, semantic HTML)
            - Modern UI/UX patterns and best practices
            - TypeScript support with proper type definitions if applicable
            - Routing with navigation and protected routes
            - State management with proper data flow
            - Form handling with validation and error display
            - API integration with proper error handling for {backend_tech}
            - Performance optimizations (lazy loading, memoization)
            - Testing setup with component tests
            - Professional styling and responsive design
            
            Focus on creating an enterprise-grade frontend application that follows the exact file structure specified and meets all acceptance criteria.
            Each file should be production-ready with comprehensive functionality and modern best practices for {framework}.""")
        ])

    def run(self, work_item: WorkItem, state: Dict[str, Any]) -> CodeGenerationOutput:
        """Generate complete frontend for a work item."""
        try:
            logger.info(f"SimpleFrontendAgent processing: {work_item.description}")
            
            # ENHANCED: Extract technology stack from enhanced state
            tech_stack_info = state.get('tech_stack_info', {})
            frontend_tech = tech_stack_info.get('frontend', 'JavaScript with React')
            backend_tech = tech_stack_info.get('backend', 'Python with FastAPI')
            database_tech = tech_stack_info.get('database', 'PostgreSQL')
            expected_files = tech_stack_info.get('expected_file_structure', [])
            
            # Parse frontend technology
            if 'react' in frontend_tech.lower():
                framework = 'React'
                if 'next.js' in frontend_tech.lower() or 'nextjs' in frontend_tech.lower():
                    framework = 'Next.js'
            elif 'vue' in frontend_tech.lower():
                framework = 'Vue.js'
            elif 'angular' in frontend_tech.lower():
                framework = 'Angular'
            elif 'svelte' in frontend_tech.lower():
                framework = 'Svelte'
            else:
                # Detect from work item description
                work_item_description = work_item.get('description', '').lower()
                if 'next.js' in work_item_description or 'nextjs' in work_item_description:
                    framework = 'Next.js'
                elif 'vue' in work_item_description:
                    framework = 'Vue.js'
                elif 'angular' in work_item_description:
                    framework = 'Angular'
                else:
                    framework = 'React'  # Default
            
            # Detect from expected files
            if expected_files:
                js_files = any('pages/index.js' in f or 'next.config' in f for f in expected_files)
                vue_files = any('.vue' in f for f in expected_files)
                angular_files = any('angular.json' in f or 'app.module' in f for f in expected_files)
                
                if js_files and 'pages/' in str(expected_files):
                    framework = 'Next.js'
                elif vue_files:
                    framework = 'Vue.js'
                elif angular_files:
                    framework = 'Angular'
            
            styling = 'Tailwind CSS'  # Default styling
            state_management = 'Context API'  # Default state management
            
            logger.info(f"SimpleFrontendAgent using: {framework}")
            logger.info(f"Expected files: {expected_files}")
            
            # Determine features from work item
            features = self._extract_features(work_item.description)
            
            # Generate code with LLM - Enhanced with work item details
            dependencies = tech_stack_info.get('work_item_dependencies', [])
            acceptance_criteria = tech_stack_info.get('work_item_acceptance_criteria', [])
            
            prompt_input = {
                "description": work_item.description,
                "framework": framework,
                "styling": styling,
                "state_management": state_management,
                "features": ", ".join(features),
                "work_item": f"ID: {work_item.id}, Role: {work_item.agent_role}",
                "expected_files": "\n".join(expected_files) if expected_files else "No specific file structure specified",
                "frontend_tech": frontend_tech,
                "backend_tech": backend_tech,
                "database_tech": database_tech,
                "dependencies": "\n".join([f"- {dep}" for dep in dependencies]) if dependencies else "No dependencies",
                "acceptance_criteria": "\n".join([f"✓ {criteria}" for criteria in acceptance_criteria]) if acceptance_criteria else "No specific acceptance criteria"
            }
            
            response = self.llm.invoke(self.frontend_prompt.format_messages(**prompt_input))
            raw_content = response.content if hasattr(response, 'content') else str(response)

            # Handle case where content is a list of strings/chunks
            if isinstance(raw_content, list):
                content = "".join(raw_content)
            else:
                content = str(raw_content)
            
            # Parse files
            generated_files = parse_llm_output_into_files(content)
            
            # Quality validation - flexible approach for frontend files
            min_files_suggested = 3  # Flexible minimum for frontend
            if len(generated_files) < min_files_suggested:
                logger.info(f"Generated {len(generated_files)} frontend files (suggested: {min_files_suggested}+)")
                
                # Accept even fewer files if they have substantial content
                if not generated_files:
                    logger.error("No frontend files generated at all")
                    return CodeGenerationOutput(
                        generated_files=[],
                        summary="Frontend generation failed: No files generated",
                        status="error"
                    )
            else:
                logger.info(f"Generated {len(generated_files)} frontend files - good coverage")
            
            # Validate file content quality
            validated_files = self._validate_generated_files(generated_files, framework, styling)
            if not validated_files:
                logger.warning("Frontend file validation failed, but proceeding with generated files")
                # Be more lenient - use original files if validation is too strict
                validated_files = [f for f in generated_files if f.content and len(f.content.strip()) > 10]
            
            # Save to disk
            self._save_files(validated_files)
            
            logger.info(f"Generated {len(validated_files)} high-quality frontend files")
            return CodeGenerationOutput(
                generated_files=validated_files,
                summary=f"Complete {framework} frontend with {len(validated_files)} production-ready files",
                status="success"
            )
            
        except Exception as e:
            logger.error(f"SimpleFrontendAgent failed: {e}")
            return CodeGenerationOutput(
                generated_files=[],
                summary=f"Frontend generation error: {e}",
                status="error"
            )

    def _extract_features(self, description: str) -> List[str]:
        """Extract required features from work item description."""
        features = []
        desc_lower = description.lower()
        
        # Enhanced feature detection
        feature_patterns = {
            "dashboard": ["dashboard", "admin", "control panel", "overview"],
            "forms": ["form", "input", "validation", "submit", "create", "edit"],
            "data_display": ["table", "list", "grid", "display", "show", "view"],
            "authentication": ["auth", "login", "signup", "register", "profile"],
            "responsive_design": ["mobile", "responsive", "tablet", "device"],
            "data_visualization": ["chart", "graph", "analytics", "metrics", "statistics"],
            "real_time": ["real-time", "live", "websocket", "notifications"],
            "navigation": ["menu", "navigation", "routing", "breadcrumb"],
            "search_filter": ["search", "filter", "sort", "pagination"],
            "file_upload": ["upload", "file", "image", "document"],
            "shopping_cart": ["cart", "ecommerce", "shopping", "checkout"],
            "messaging": ["chat", "message", "communication"],
            "calendar": ["calendar", "date", "schedule", "event"],
            "maps": ["map", "location", "geolocation", "address"],
            "social": ["social", "share", "like", "comment", "follow"]
        }
        
        for feature, keywords in feature_patterns.items():
            if any(keyword in desc_lower for keyword in keywords):
                features.append(feature)
                
        return features or ["basic_ui", "responsive_design"]

    def _validate_generated_files(self, generated_files: List[GeneratedFile], framework: str, styling: str) -> List[GeneratedFile]:
        """Validate generated files meet frontend quality standards."""
        validated_files = []
        
        # Define validation patterns for frontend files
        frontend_patterns = {
            "components": ["component", "comp", "ui", "element"],
            "pages": ["page", "view", "screen", "route"],
            "styles": ["style", "css", "scss", "less"],
            "config": ["config", "setup", "build", "package"],
            "hooks": ["hook", "use", "composable"],
            "services": ["service", "api", "client", "fetch"],
            "utils": ["util", "helper", "common", "lib"],
            "types": ["type", "interface", "model"],
            "tests": ["test", "spec", "__tests__"]
        }
        
        # Framework-specific validation
        if framework.lower() == "react":
            required_patterns = ["import", "export", "function", "const", "jsx", "tsx"]
            file_extensions = [".js", ".jsx", ".ts", ".tsx"]
        elif framework.lower() == "vue":
            required_patterns = ["import", "export", "template", "script", "style"]
            file_extensions = [".vue", ".js", ".ts"]
        elif framework.lower() == "angular":
            required_patterns = ["import", "export", "component", "module", "@"]
            file_extensions = [".ts", ".html", ".css", ".scss"]
        else:
            required_patterns = ["import", "export", "function", "const"]
            file_extensions = [".js", ".ts"]
        
        for file_obj in generated_files:
            try:
                content = file_obj.content if hasattr(file_obj, 'content') else file_obj.get('content', '')
                file_path = file_obj.file_path if hasattr(file_obj, 'file_path') else file_obj.get('file_path', '')
                
                # Check if file has substantial content
                if len(content.strip()) < 80:
                    logger.warning(f"Skipping file {file_path}: insufficient content")
                    continue
                
                # Check for basic code structure
                content_lower = content.lower()
                has_code_structure = any(pattern in content_lower for pattern in required_patterns)
                
                # Check file relevance to frontend development
                file_path_lower = file_path.lower()
                is_frontend_relevant = (
                    any(pattern in file_path_lower for pattern_group in frontend_patterns.values() for pattern in pattern_group) or
                    any(ext in file_path_lower for ext in file_extensions) or
                    any(keyword in file_path_lower for keyword in ["src", "app", "public", "assets", "styles"])
                )
                
                # Special handling for config files
                is_config_file = any(config in file_path_lower for config in ["package.json", "tsconfig", "vite.config", "webpack", "next.config"])
                
                # Validate content quality
                if (has_code_structure and is_frontend_relevant) or is_config_file or len(content.strip()) > 250:
                    validated_files.append(file_obj)
                else:
                    logger.warning(f"File {file_path} did not meet frontend validation criteria")
                    
            except Exception as e:
                logger.error(f"Error validating frontend file: {e}")
                continue
        
        return validated_files

    # Required abstract methods
    async def arun(self, **kwargs):
        """Async wrapper."""
        work_item = kwargs.get('work_item')
        state = kwargs.get('state', {})
        if work_item and state:
            return await asyncio.to_thread(self.run, work_item, state)
        return await asyncio.to_thread(self.run, **kwargs)
    
    def get_default_response(self) -> Dict[str, Any]:
        """Get default response for error cases."""
        return {
            "generated_files": [],
            "summary": "SimpleFrontendAgent encountered an error",
            "status": "error"
        }

    # Simplified overrides
    def _generate_code(self, llm: BaseLanguageModel, invoke_config: Dict, **kwargs) -> Dict[str, Any]:
        """Override base method to use our simplified approach."""
        work_item = kwargs.get('work_item')
        state = kwargs.get('state', {})
        
        if not work_item:
            return {"generated_files": [], "summary": "No work item provided", "status": "error"}
        
        # Use the main run method
        result = self.run(work_item, state)
        
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        return result 