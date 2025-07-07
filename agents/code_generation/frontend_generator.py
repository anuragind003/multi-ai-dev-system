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
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
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
from models.data_contracts import GeneratedFile, CodeGenerationOutput, WorkItem
from tools.code_generation_utils import parse_llm_output_into_files

# Enhanced memory and RAG imports
from enhanced_memory_manager import create_memory_manager, EnhancedSharedProjectMemory
from rag_manager import get_rag_manager

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
        
        # Initialize enhanced memory (inherits from BaseCodeGeneratorAgent -> BaseAgent)
        self._init_enhanced_memory()
        
        # Initialize RAG context
        self.rag_manager = get_rag_manager()
        if self.rag_manager:
            self.logger.info("RAG manager available for enhanced frontend generation")
        else:
            self.logger.warning("RAG manager not available - proceeding with basic frontend generation")
        
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
          # Setup message bus subscriptions
        self._setup_message_subscriptions()
    
    def _initialize_prompt_templates(self):
        """Initialize a single comprehensive prompt template for generating all frontend code."""
        
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
        4. File paths should be relative to project root (e.g., "src/components/App.jsx", not "./src/components/App.jsx")
        5. Generate ALL necessary frontend files for a complete implementation
        
        Files to include:
        - Component files (src/components/...)
        - Pages/screens files (src/pages/... or src/screens/...)
        - State management files (src/store/... or src/context/...)
        - Styling files (src/styles/...)
        - Configuration files (package.json, tsconfig.json if using TypeScript, etc.)
        - Routing configuration
        - Testing setup files (jest.config.js, test utilities)
        - Environment configuration (.env.example, config files)
        - Build and deployment files (Dockerfile, .github/workflows)
        """

        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", 
             """You are a Senior Frontend Architect with 10+ years of experience building production-grade enterprise applications.
             Your task is to generate ENTERPRISE-READY, PRODUCTION-QUALITY frontend code with complete testing and DevOps setup.
             
             **PRODUCTION REQUIREMENTS - MANDATORY:**
             
             🏗️ **ARCHITECTURE & PATTERNS:**
             - Clean Architecture: Separation of concerns, dependency injection
             - SOLID principles: Single responsibility, open/closed, etc.
             - Design Patterns: Observer, Factory, Command, Strategy patterns
             - Micro-frontends ready: Module federation support where applicable
             - Domain-driven design: Feature-based folder structure
             
             🔒 **SECURITY & COMPLIANCE:**
             - CSP (Content Security Policy) headers configuration
             - XSS prevention: Input sanitization, output encoding
             - CSRF protection: Token validation, SameSite cookies
             - Authentication: JWT handling, token refresh, secure storage
             - Authorization: Role-based access control (RBAC)
             - Data validation: Client-side and server-side validation
             - Sensitive data masking in development tools
             
             ⚡ **PERFORMANCE & OPTIMIZATION:**
             - Code splitting: Route-based and component-based lazy loading
             - Tree shaking: Eliminate dead code, optimize bundle size
             - Memoization: React.memo, useMemo, useCallback usage
             - Virtual scrolling: For large lists and tables
             - Image optimization: WebP, lazy loading, responsive images
             - Service workers: Caching strategies, offline functionality
             - Bundle analysis: Webpack Bundle Analyzer integration
             - Core Web Vitals optimization: LCP, FID, CLS metrics
             
             🧪 **TESTING STRATEGY:**
             - Unit tests: Jest + React Testing Library (minimum 80% coverage)
             - Integration tests: Component interaction testing
             - E2E tests: Playwright/Cypress for critical user journeys
             - Visual regression: Storybook + Chromatic integration
             - Performance tests: Lighthouse CI integration
             - Accessibility tests: axe-core integration
             - API mocking: MSW (Mock Service Worker) setup
             
             ♿ **ACCESSIBILITY (WCAG 2.1 AA):**
             - Semantic HTML: Proper headings, landmarks, lists
             - ARIA labels: aria-label, aria-describedby, role attributes
             - Keyboard navigation: Tab order, focus management, shortcuts
             - Screen reader support: Skip links, live regions, descriptions
             - Color contrast: WCAG compliant contrast ratios
             - Focus indicators: Visible focus states for all interactive elements
             - Reduced motion: Respect prefers-reduced-motion media query
             
             📱 **RESPONSIVE & PWA:**
             - Mobile-first design: Progressive enhancement approach
             - Breakpoint system: xs, sm, md, lg, xl, 2xl breakpoints
             - Touch interactions: Gesture support, haptic feedback
             - PWA features: Manifest, service worker, push notifications
             - Offline capability: Cache-first strategies, background sync
             - App-like experience: Install prompts, splash screens
             
             🔄 **STATE MANAGEMENT:**
             - Immutable updates: Proper state mutation prevention
             - Normalized state: Entity-based state structure
             - Async state handling: Loading, error, success states
             - Optimistic updates: Immediate UI feedback
             - State persistence: LocalStorage, SessionStorage integration
             - State debugging: DevTools integration, time-travel debugging
             
             📊 **MONITORING & ANALYTICS:**
             - Error tracking: Sentry integration with error boundaries
             - Performance monitoring: Web Vitals tracking, RUM
             - User analytics: Event tracking, conversion funnels
             - A/B testing: Feature flags integration
             - Real-time monitoring: Health checks, uptime monitoring
             - User session recording: FullStory/LogRocket integration
             
             🚀 **DEVOPS & DEPLOYMENT:**
             - CI/CD pipeline: GitHub Actions/Jenkins integration
             - Environment configuration: Multiple environment support
             - Build optimization: Production vs development builds
             - Static analysis: ESLint, Prettier, TypeScript strict mode
             - Security scanning: npm audit, Snyk integration
             - Performance budgets: Bundle size limits, performance metrics
             - CDN configuration: Asset optimization and caching
             
             **FRAMEWORK-SPECIFIC PRODUCTION PATTERNS:**
             
             🔵 **React Production Patterns:**
             - Error Boundaries: Graceful error handling and recovery
             - Suspense: Loading states and code splitting
             - Context optimization: Prevent unnecessary re-renders
             - Custom hooks: Reusable stateful logic
             - Portal usage: Modals, tooltips, overlays
             - Ref forwarding: Component composition patterns
             - PropTypes/TypeScript: Runtime and compile-time validation
             
             🟢 **Vue.js Production Patterns:**
             - Composition API: Reusable reactive logic
             - Teleport: Portal-like functionality for Vue 3
             - Async components: Dynamic imports and loading states
             - Custom directives: Reusable DOM manipulation
             - Plugin architecture: Modular functionality
             - Pinia stores: Modern state management
             - Vue DevTools: Development and debugging integration
             
             🔴 **Angular Production Patterns:**
             - Change detection: OnPush strategy optimization
             - Dependency injection: Service organization and testing
             - Guards: Route protection and data loading
             - Interceptors: HTTP request/response handling
             - Pipes: Data transformation and performance
             - NgRx: Advanced state management patterns
             - Angular CLI: Build optimization and schematics
             
             Generate ONLY production-ready code with enterprise standards. Include comprehensive error handling,
             proper TypeScript interfaces, extensive testing setup, and modern DevOps integration.
             """
            ),
            ("human", 
             """
             Generate a complete PRODUCTION-READY frontend implementation for the **{project_domain}** domain using 
             **{frontend_framework}** framework with **{frontend_language}** language.

             ## Project Context
             
             DOMAIN: {project_domain}
             SCALE: {project_scale}
             TARGET USERS: {target_users}
             ACCESSIBILITY REQUIREMENTS: {accessibility_requirements}
             
             REQUIREMENTS ANALYSIS:
             {requirements_summary}

             TECH STACK:
             {tech_stack_summary}

             SYSTEM DESIGN:
             {system_design_summary}

             ## Technical Details
             
             Frontend Framework: {frontend_framework}
             Programming Language: {frontend_language}
             Styling Framework: {styling_framework}
             State Management: {state_management}
             Routing Library: {routing_library}
             
             Full Tech Stack:
             {tech_stack_details}
             
             Full System Design:
             {system_design_details}

             ## UI Design Specifications
             {ui_specs}

             ## API Integration Specs
             {api_specs}

             ## Component Architecture
             {component_architecture}

             ## Domain-Specific UI Requirements
             {domain_ui_requirements}

             ## Framework-Specific Best Practices
             {framework_best_practices}

             ## Accessibility and UX Guidelines
             {accessibility_guidelines}

             ## Context and Guidance
             {rag_context}

             {code_review_feedback}

             ## PRODUCTION-READY FILE REQUIREMENTS:

             **MANDATORY FILES TO GENERATE:**

             📦 **Package & Configuration:**
             - package.json (with ALL production dependencies including:
               * zustand (state management)
               * @sentry/react (error tracking)
               * @tanstack/react-query (server state)
               * dompurify (XSS prevention)
               * react-window (virtual scrolling)
               * web-vitals (performance monitoring)
               * @types/dompurify (TypeScript types)
               * react-error-boundary (error boundaries))
             - tsconfig.json (strict TypeScript configuration)
             - .env.example (environment variables template)
             - .eslintrc.js (strict linting rules)
             - .prettier.config.js (code formatting)
             - jest.config.js (testing configuration)
             - tailwind.config.js (if using Tailwind)
             - vite.config.ts / webpack.config.js (build configuration)

             🏗️ **Core Application Structure:**
             - src/main.tsx / src/index.tsx (application entry point)
             - src/App.tsx (main application component with error boundary)
             - src/router/index.tsx (routing configuration)
             - src/types/index.ts (TypeScript type definitions)
             - src/constants/index.ts (application constants)
             - src/config/index.ts (environment configuration)

             🧩 **Component Architecture:**
             - src/components/ui/ (reusable UI components)
             - src/components/layout/ (layout components)
             - src/components/forms/ (form components with validation)
             - src/pages/ (page/route components)
             - src/hooks/ (custom React hooks)
             - src/context/ (React context providers)

             🔄 **State Management:**
             - src/store/index.ts (store configuration)
             - src/store/slices/ (Redux slices or Zustand stores)
             - src/store/middleware.ts (custom middleware)
             - src/services/api.ts (API service layer)
             - src/utils/storage.ts (localStorage/sessionStorage utilities)

             🎨 **Styling & Theming:**
             - src/styles/globals.css (global styles)
             - src/styles/variables.css (CSS custom properties)
             - src/styles/components.css (component-specific styles)
             - src/theme/index.ts (theme configuration)

             🔒 **Security & Utils:**
             - src/utils/auth.ts (authentication utilities)
             - src/utils/validation.ts (form validation schemas)
             - src/utils/sanitize.ts (XSS prevention)
             - src/guards/AuthGuard.tsx (route protection)
             - src/utils/crypto.ts (encryption/decryption utilities)

             🧪 **Testing Setup:**
             - src/test/setup.ts (test configuration)
             - src/test/utils.tsx (testing utilities)
             - src/test/mocks/ (API mocks)
             - src/__tests__/ (component tests)
             - cypress/ or playwright/ (E2E test configuration)

             ⚡ **Performance & PWA:**
             - public/manifest.json (PWA manifest)
             - public/sw.js (service worker)
             - src/utils/performance.ts (performance monitoring)
             - src/utils/lazy.ts (lazy loading utilities)

             🚀 **DevOps & Deployment:**
             - Dockerfile (containerization)
             - .github/workflows/ci.yml (CI/CD pipeline)
             - .dockerignore (Docker ignore file)
             - nginx.conf (production server configuration)

             ## CRITICAL IMPLEMENTATION REQUIREMENTS:

             1. **Use proper React Router Links instead of anchor tags**
             2. **Implement comprehensive TypeScript interfaces**
             3. **Add error boundaries for all route components**
             4. **Include loading states for all async operations**
             5. **Implement proper form validation with error handling**
             6. **Add ARIA labels and semantic HTML for accessibility**
             7. **Include proper meta tags for SEO**
             8. **Implement responsive design with mobile-first approach**
             9. **Add proper error handling for API calls**
             10. **Include environment-based configuration**
             11. **Add comprehensive JSDoc comments**
             12. **Implement proper state management patterns**
             13. **Include performance monitoring and analytics**
             14. **Add proper security headers and CSP**
             15. **Implement offline functionality where applicable**

             ## ENTERPRISE-GRADE ENHANCEMENTS (MANDATORY):

             🚫 **ERROR BOUNDARIES & FAULT TOLERANCE:**
             - React Error Boundary components for each route
             - Global error boundary with fallback UI
             - Error reporting to external services (Sentry)
             - Graceful degradation strategies
             - Recovery mechanisms and retry logic
             - Development vs production error displays

             🔄 **STATE MANAGEMENT (CHOOSE BASED ON COMPLEXITY):**
             - Zustand for simple to medium complexity (preferred)
             - Redux Toolkit for complex applications
             - React Query/TanStack Query for server state
             - Global state for authentication, user preferences
             - Local state optimization with useState, useReducer
             - State persistence to localStorage/sessionStorage

             ⚡ **PERFORMANCE OPTIMIZATION:**
             - React.lazy() for route-based code splitting
             - React.memo for expensive component re-renders
             - useMemo for expensive calculations
             - useCallback for stable function references
             - Virtual scrolling for large lists (react-window)
             - Image lazy loading and optimization
             - Bundle splitting and tree shaking
             - Preloading critical resources

             🔒 **SECURITY IMPLEMENTATION:**
             - Content Security Policy (CSP) headers
             - XSS prevention with DOMPurify
             - CSRF protection tokens
             - Secure authentication flow (JWT with refresh tokens)
             - Input validation and sanitization
             - Secure cookie settings (httpOnly, secure, sameSite)
             - Environment variable security (.env.example)
             - API endpoint security headers

             📊 **MONITORING & ANALYTICS:**
             - Sentry integration for error tracking
             - Google Analytics or custom analytics
             - Performance monitoring (Web Vitals)
             - User session recording (optional)
             - Custom event tracking for business metrics
             - Real User Monitoring (RUM)
             - Error boundary reporting
             - API response time monitoring

             **SPECIFIC FILES TO GENERATE FOR ENHANCEMENTS:**

             🚫 **Error Boundaries:**
             - src/components/error/ErrorBoundary.tsx
             - src/components/error/GlobalErrorBoundary.tsx
             - src/components/error/RouteErrorBoundary.tsx
             - src/components/error/ErrorFallback.tsx
             - src/utils/errorReporting.ts

             🔄 **State Management:**
             - src/store/index.ts (Zustand store setup)
             - src/store/authStore.ts (authentication state)
             - src/store/uiStore.ts (UI state management)
             - src/hooks/useAuthStore.ts
             - src/hooks/usePersistedStore.ts
             - src/utils/storage.ts

             ⚡ **Performance:**
             - src/components/lazy/LazyRoutes.tsx
             - src/components/performance/VirtualList.tsx
             - src/hooks/usePerformanceMonitor.ts
             - src/utils/imageOptimization.ts
             - src/utils/lazyLoading.ts

             🔒 **Security:**
             - src/utils/security.ts (XSS prevention, sanitization)
             - src/components/security/CSPMeta.tsx
             - src/utils/auth.ts (JWT handling, secure storage)
             - src/guards/AuthGuard.tsx
             - src/guards/RoleGuard.tsx
             - public/.htaccess (security headers)

             📊 **Monitoring:**
             - src/utils/monitoring.ts (Sentry setup)
             - src/utils/analytics.ts (GA/custom analytics)
             - src/hooks/usePerformanceMetrics.ts
             - src/utils/webVitals.ts
             - src/components/monitoring/PerformanceMonitor.tsx

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
              # Extract frontend technology details with enhanced domain awareness
            frontend_tech = self._extract_frontend_tech(tech_stack)
            frontend_framework = frontend_tech.get("framework", "React")
            frontend_language = frontend_tech.get("language", "JavaScript")
            styling_framework = frontend_tech.get("css_framework", frontend_tech.get("styling", "CSS"))
            state_management = frontend_tech.get("state_management", "Context API")
            routing_library = frontend_tech.get("routing", "react-router")
            
            # Extract domain and user context
            project_domain = requirements_analysis.get("domain", "general")
            project_scale = requirements_analysis.get("scale", "small")
            target_users = requirements_analysis.get("target_users", "general users")
            
            self.log_info(f"Using frontend stack: {frontend_framework} with {styling_framework}, {state_management}, {routing_library}")
            
            # Generate domain-specific requirements and guidelines
            domain_ui_requirements = self._get_domain_ui_requirements(project_domain, requirements_analysis)
            accessibility_requirements = self._get_accessibility_requirements(project_domain, target_users)
            accessibility_guidelines = self._get_accessibility_guidelines(project_domain)
            framework_best_practices = self._get_frontend_best_practices(frontend_framework, styling_framework, project_domain)
            
            # Create enhanced summaries
            requirements_summary = self._create_requirements_summary(requirements_analysis)
            tech_stack_summary = self._create_tech_stack_summary(frontend_tech)
            system_design_summary = self._create_system_design_summary(system_design)
            
            # Extract UI specifications and API endpoints
            ui_specs = self._extract_ui_specs(system_design)
            api_specs = self._extract_api_specs(system_design, tech_stack)
            component_architecture = self._create_component_architecture(system_design, frontend_framework)
            
            # Get RAG context for frontend development
            rag_context = self._get_frontend_rag_context(frontend_framework, styling_framework, state_management)
            
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
            invoke_config["agent_context"] = f"{self.agent_name}:{frontend_framework}_generation"
            invoke_config["temperature_used"] = adjusted_temp
            invoke_config["is_revision"] = is_revision
            
            # Execute LLM call to generate all frontend artifacts
            self.log_info(f"Generating {frontend_framework} frontend with temperature {adjusted_temp}")
            response = llm_with_temp.invoke(
                self.prompt_template.format(
                    project_domain=project_domain,
                    project_scale=project_scale,
                    target_users=target_users,
                    accessibility_requirements=accessibility_requirements,
                    requirements_summary=requirements_summary,
                    tech_stack_summary=tech_stack_summary,
                    system_design_summary=system_design_summary,
                    tech_stack_details=json.dumps(tech_stack, indent=2),
                    system_design_details=json.dumps(system_design, indent=2),
                    frontend_framework=frontend_framework,
                    frontend_language=frontend_language,
                    styling_framework=styling_framework,
                    state_management=state_management,
                    routing_library=routing_library,
                    ui_specs=json.dumps(ui_specs, indent=2),
                    api_specs=json.dumps(api_specs, indent=2),
                    component_architecture=component_architecture,
                    domain_ui_requirements=domain_ui_requirements,
                    framework_best_practices=framework_best_practices,
                    accessibility_guidelines=accessibility_guidelines,
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
                    "framework": frontend_framework,
                    "is_revision": is_revision,
                    "temperature": adjusted_temp
                }
            )
              # Parse the multi-file output
            parsed_files = parse_llm_output_into_files(content)
            
            # Convert GeneratedFile objects to CodeFile objects
            generated_files = []
            for parsed_file in parsed_files:
                from models.data_contracts import CodeFile
                code_file = CodeFile(
                    file_path=parsed_file.file_path,
                    code=parsed_file.content  # GeneratedFile uses 'content', CodeFile uses 'code'
                )
                generated_files.append(code_file)
            
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
            # Note: CodeFile objects don't have a status attribute - that's on CodeGenerationOutput            # Create structured output
            output = CodeGenerationOutput(
                files=generated_files,
                summary=f"Generated {len(generated_files)} frontend files for {frontend_framework} application",
                status="success" if generated_files else "error",
                metadata={
                    "framework": frontend_framework,
                    "is_revision": is_revision,
                    "state_management": state_management,
                    "styling_approach": styling_framework,
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
                    "framework": frontend_framework,
                    "file_count": len(generated_files),
                    "components_count": components_count,
                    "is_revision": is_revision,
                    "status": "success"
                })
            
            # Store result in enhanced memory for cross-tool access
            self.enhanced_set("frontend_generation_result", output.dict(), context="frontend_generation")
            
            # Convert CodeFile objects to dictionaries for JSON serialization
            serializable_files = []
            for file_obj in generated_files:
                if hasattr(file_obj, 'dict'):
                    # If it's a Pydantic model, use dict() method
                    serializable_files.append(file_obj.dict())
                else:
                    # If it's a regular object, convert manually
                    serializable_files.append({
                        "file_path": getattr(file_obj, 'file_path', 'unknown'),
                        "code": getattr(file_obj, 'code', '')
                    })
            
            self.store_cross_tool_data("frontend_files", serializable_files, f"Frontend files generated with {frontend_framework}")
            
            # Store frontend patterns for reuse
            self.enhanced_set("frontend_patterns", {
                "framework": frontend_framework,
                "components_count": components_count,
                "pages_count": pages_count,
                "state_count": state_count,
                "tech_stack": frontend_tech
            }, context="frontend_patterns")
            
            # Return as dictionary
            return output.dict()
            
        except Exception as e:
            self.log_error(f"Frontend {generation_type} failed: {str(e)}", exc_info=True)            # Return error output using the standardized format
            error_output = CodeGenerationOutput(
                files=self._create_default_frontend_files(
                    frontend_tech if 'frontend_tech' in locals() else self._create_default_tech_stack()
                ),
                summary=f"Error generating frontend code: {str(e)}",
                status="error",                metadata={
                    "error": str(e),
                    "framework": frontend_framework if 'frontend_framework' in locals() else "unknown",
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
        """        # Use a lower temperature for initial code generation (more deterministic)
        initial_temp = max(0.1, min(self.default_temperature, 0.2))
        
        # Use slightly higher temperature for revisions to encourage creative fixes
        revision_temp = max(0.2, min(self.default_temperature + 0.1, 0.3))
        
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
    
    def _create_requirements_summary(self, requirements_analysis: Dict[str, Any]) -> str:
        """
        Create a concise summary of the requirements analysis.
        
        Args:
            requirements_analysis: Requirements analysis data
            
        Returns:
            String summary of requirements
        """
        if not requirements_analysis:
            return "No specific requirements provided"
        
        domain = requirements_analysis.get("domain", "General Application")
        scale = requirements_analysis.get("scale", "small")
        target_users = requirements_analysis.get("target_users", "general users")
        
        functional_reqs = requirements_analysis.get("functional_requirements", [])
        non_functional_reqs = requirements_analysis.get("non_functional_requirements", [])
        
        summary = f"Domain: {domain}, Scale: {scale}, Users: {target_users}"
        
        if functional_reqs:
            summary += f", Features: {len(functional_reqs)} functional requirements"
        
        if non_functional_reqs:
            summary += f", {len(non_functional_reqs)} non-functional requirements"
        
        return summary
    
    def _create_system_design_summary(self, system_design: Dict[str, Any]) -> str:
        """
        Create a concise summary of the system design.
        
        Args:
            system_design: System design data
            
        Returns:
            String summary of system design
        """
        if not system_design:
            return "No system design provided"
        
        architecture = system_design.get("architecture", "Standard")
        ui_section = system_design.get("ui", {})
        
        screens_count = len(ui_section.get("screens", []))
        components_count = len(ui_section.get("components", []))
        
        api_section = system_design.get("api_design", {})
        endpoints_count = len(api_section.get("endpoints", []))
        
        summary = f"Architecture: {architecture}"
        
        if screens_count:
            summary += f", {screens_count} screens"
        
        if components_count:
            summary += f", {components_count} components"
        
        if endpoints_count:
            summary += f", {endpoints_count} API endpoints"
        
        return summary

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
            self.log_warning(f"Error retrieving RAG context: {e}")
            return ""
    
    def _create_default_frontend_files(self, frontend_tech: Dict[str, Any]) -> List:
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
        from models.data_contracts import CodeFile
        generated_files = [
            CodeFile(
                file_path="README.md",
                code=readme_content
            ),
            CodeFile(
                file_path=f"src/App.{jsx_ext}",
                code=app_content
            ),
            CodeFile(
                file_path="src/App.css",
                code=app_css
            ),
            CodeFile(
                file_path=f"src/index.{jsx_ext}",
                code=index_content
            ),
            CodeFile(
                file_path=f"src/components/Header.{jsx_ext}",
                code=header_content
            ),
            CodeFile(
                file_path=f"src/components/Footer.{jsx_ext}",
                code=footer_content
            ),
            CodeFile(
                file_path=f"src/pages/HomePage.{jsx_ext}",
                code=home_page_content
            ),
            CodeFile(
                file_path=f"src/pages/AboutPage.{jsx_ext}",
                code=about_page_content
            ),
            CodeFile(
                file_path="package.json",
                code=package_json
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
        """Create a domain-aware default tech stack when input is invalid."""
        return {
            "frontend": {
                "framework": "React",  # Default but should be overridden by domain analysis
                "language": "JavaScript",
                "styling": "CSS",
                "state_management": "Context API",
                "routing": "react-router",
                "justification": "React chosen as default due to widespread adoption, but production applications should use domain-specific framework selection"
            },
            "note": "This is a generic default stack. Production applications should use domain-specific technology selection."
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
    
    def _setup_message_subscriptions(self) -> None:
        """Set up message bus subscriptions if available"""
        if self.message_bus:
            self.message_bus.subscribe("backend.generated", self._handle_backend_ready)
            self.log_info(f"{self.agent_name} subscribed to backend.generated events")
    
    def _handle_backend_ready(self, message: Dict[str, Any]) -> None:
        """Handle backend generation completion messages"""
        self.log_info("Received backend generation complete event")
        
        payload = message.get("payload", {})
        if payload.get("status") == "success":
            # Store backend API information for use in frontend generation
            if "api_endpoints" in payload:
                self.working_memory["backend_apis"] = payload["api_endpoints"]
                self.log_info(f"Backend APIs ready: {len(payload['api_endpoints'])} endpoints")
            
            if "files" in payload:
                self.working_memory["backend_files"] = payload["files"]
                self.log_info(f"Backend files available: {len(payload['files'])} files")
        else:
            self.log_warning("Backend generation completed with errors")
    
    def _get_domain_ui_requirements(self, domain: str, requirements_analysis: Dict[str, Any]) -> str:
        """Generate domain-specific UI requirements."""
        domain_lower = domain.lower()
        
        # Healthcare domain UI requirements
        if "health" in domain_lower or "medical" in domain_lower:
            return """HEALTHCARE UI REQUIREMENTS:
- WCAG AA compliance for accessibility
- High contrast mode support for visually impaired users
- Patient data privacy indicators and warnings
- Medical form validation with real-time feedback
- Appointment scheduling with calendar integration
- Mobile-responsive design for telemedicine"""
        
        # Financial domain UI requirements
        elif "financ" in domain_lower or "bank" in domain_lower:
            return """FINANCIAL UI REQUIREMENTS:
- Multi-factor authentication UI flows
- Secure transaction confirmation screens
- Real-time fraud alerts and notifications
- Financial data visualization (charts, graphs)
- Transaction history with filtering and search
- Mobile-first responsive design for banking apps"""
        
        # IoT domain UI requirements
        elif "iot" in domain_lower or "sensor" in domain_lower:
            return """IOT UI REQUIREMENTS:
- Real-time device status dashboards
- Interactive device control panels
- Data visualization for sensor readings
- Device grouping and organization
- Mobile-responsive controls for remote access"""
        
        # E-commerce domain UI requirements
        elif "ecommerce" in domain_lower or "retail" in domain_lower:
            return """E-COMMERCE UI REQUIREMENTS:
- Product catalog with filtering and search
- Shopping cart with persistent state
- Checkout flow with progress indicators
- Mobile-optimized shopping experience
- Order tracking and delivery status"""
        
        # Generic UI requirements
        else:
            return """GENERAL UI REQUIREMENTS:
- Responsive design for all screen sizes
- Intuitive navigation and user experience
- Form validation with clear feedback
- Accessible design following WCAG guidelines"""

    def _get_accessibility_requirements(self, domain: str, target_users: str) -> str:
        """Get accessibility requirements based on domain and target users."""
        domain_lower = domain.lower()
        users_lower = target_users.lower()
        
        requirements = ["WCAG 2.1 AA compliance", "Keyboard navigation support", "Screen reader compatibility"]
        
        # High accessibility requirements for healthcare and government
        if any(keyword in domain_lower for keyword in ["health", "medical", "government", "public"]):
            requirements.extend(["WCAG 2.1 AAA compliance", "High contrast mode", "Large text options"])
        
        # Special considerations for elderly users
        if "elderly" in users_lower or "senior" in users_lower:
            requirements.extend(["Large touch targets (44px minimum)", "Simple navigation patterns"])
        
        return ", ".join(requirements)
    
    def _get_accessibility_guidelines(self, domain: str) -> str:
        """Get detailed accessibility guidelines based on domain."""
        domain_lower = domain.lower()
        
        base_guidelines = """ACCESSIBILITY GUIDELINES:
- Use semantic HTML elements for proper structure
- Implement ARIA labels and roles where needed
- Ensure color contrast ratios meet WCAG standards
- Provide alternative text for all images
- Make all interactive elements keyboard accessible
- Include skip navigation links"""
        
        # Enhanced guidelines for sensitive domains
        if any(keyword in domain_lower for keyword in ["health", "medical", "government", "finance"]):
            base_guidelines += """
ENHANCED ACCESSIBILITY (Sensitive Domain):
- Implement voice navigation for hands-free operation
- Support multiple input methods (touch, voice, keyboard)
- Include emergency accessibility features
- Provide multi-language support"""
        
        return base_guidelines

    def _get_frontend_best_practices(self, framework: str, styling: str, domain: str = "") -> str:
        """Get framework-specific best practices with domain awareness and production requirements."""
        framework_lower = framework.lower()
        styling_lower = styling.lower()
        domain_lower = domain.lower()
        
        practices = f"PRODUCTION-READY BEST PRACTICES FOR {framework.upper()}:\n\n"
        
        # React best practices
        if "react" in framework_lower:
            practices += """🔵 REACT PRODUCTION PATTERNS:

**Architecture & Performance:**
- Use functional components with hooks exclusively
- Implement React.memo, useMemo, and useCallback for optimization
- Use React.lazy() and Suspense for code splitting
- Implement proper error boundaries for fault tolerance
- Use React.Fragment to avoid unnecessary DOM elements
- Follow container/presentation component pattern

**State Management:**
- Use Context API for simple state, Redux Toolkit for complex state
- Implement proper immutable updates with Immer
- Use custom hooks for reusable stateful logic
- Normalize state shape for better performance
- Implement proper loading and error states

**Security & Validation:**
- Use react-hook-form with zod/yup for form validation
- Sanitize user inputs to prevent XSS attacks
- Implement proper authentication guards
- Use environment variables for sensitive configuration
- Implement proper CSRF protection

**Testing:**
- Write unit tests with React Testing Library
- Use MSW for API mocking in tests
- Implement integration tests for user flows
- Add accessibility testing with jest-axe
- Maintain minimum 80% test coverage

**DevOps & Build:**
- Use TypeScript strict mode for better type safety
- Implement proper ESLint and Prettier configuration
- Use Husky for pre-commit hooks
- Bundle analysis with webpack-bundle-analyzer
- Implement proper CI/CD with automated testing"""
        
        # Vue.js best practices
        elif "vue" in framework_lower:
            practices += """🟢 VUE.JS PRODUCTION PATTERNS:

**Architecture & Performance:**
- Use Composition API over Options API for better code organization
- Implement proper reactive state management with Pinia
- Use defineAsyncComponent for lazy loading
- Implement proper error handling with errorCaptured hook
- Use provide/inject for dependency injection
- Follow Vue 3 style guide conventions

**State Management:**
- Use Pinia for centralized state management
- Implement proper state normalization
- Use computed properties for derived state
- Implement proper async state handling
- Use watchers sparingly and clean them up

**Security & Validation:**
- Use VeeValidate for comprehensive form validation
- Implement proper XSS prevention with v-html sanitization
- Use Vue meta for SEO and security headers
- Implement proper authentication middleware
- Validate props with proper TypeScript interfaces

**Testing:**
- Write component tests with Vue Test Utils
- Use Vitest for fast unit testing
- Implement E2E tests with Cypress
- Add accessibility testing with vue-axe
- Test composables and utilities separately

**DevOps & Build:**
- Use Vite for fast development and build
- Implement proper TypeScript configuration
- Use Vue DevTools for debugging
- Implement proper deployment with Docker
- Use Vue CLI for consistent project structure"""
        
        # Angular best practices
        elif "angular" in framework_lower:
            practices += """🔴 ANGULAR PRODUCTION PATTERNS:

**Architecture & Performance:**
- Use OnPush change detection strategy
- Implement proper dependency injection hierarchy
- Use Angular modules for feature organization
- Implement lazy loading for route modules
- Use trackBy functions in *ngFor loops
- Follow Angular style guide strictly

**State Management:**
- Use NgRx for complex state management
- Implement proper actions, reducers, and effects
- Use selectors for state queries
- Implement proper error handling in effects
- Use NgRx Entity for normalized state

**Security & Validation:**
- Use reactive forms with custom validators
- Implement proper HTTP interceptors
- Use Angular guards for route protection
- Implement proper CSRF protection
- Validate all inputs on both client and server

**Testing:**
- Write unit tests with Jasmine and Karma
- Use Angular Testing Utilities
- Implement E2E tests with Protractor or Cypress
- Mock services and HTTP calls properly
- Test components, services, and guards

**DevOps & Build:**
- Use Angular CLI for consistent builds
- Implement proper environment configuration
- Use Angular Universal for SSR
- Implement proper PWA features
- Use Angular DevKit for custom schematics"""
        
        # Svelte best practices
        elif "svelte" in framework_lower:
            practices += """🟠 SVELTE PRODUCTION PATTERNS:

**Architecture & Performance:**
- Use Svelte stores for state management
- Implement proper reactive statements
- Use component composition patterns
- Implement lazy loading with dynamic imports
- Use proper component lifecycle methods
- Follow Svelte conventions for reactivity

**State Management:**
- Use Svelte stores for global state
- Implement proper store subscriptions
- Use derived stores for computed values
- Implement proper async store patterns
- Clean up store subscriptions properly

**Security & Validation:**
- Implement proper form validation
- Sanitize user inputs properly
- Use CSP headers for XSS prevention
- Implement proper authentication flows
- Validate all data inputs

**Testing:**
- Write component tests with @testing-library/svelte
- Use Jest for unit testing
- Implement E2E tests with Playwright
- Test stores and utilities separately
- Mock external dependencies properly

**DevOps & Build:**
- Use SvelteKit for full-stack applications
- Implement proper TypeScript support
- Use Vite for fast development
- Implement proper deployment strategies
- Use Svelte DevTools for debugging"""
        
        # Add styling framework specific practices
        practices += f"\n\n🎨 STYLING BEST PRACTICES FOR {styling.upper()}:\n"
        
        if "tailwind" in styling_lower:
            practices += """- Use Tailwind CSS utility classes for consistent design
- Implement custom design tokens in tailwind.config.js
- Use @apply directive for component-specific styles
- Implement responsive design with Tailwind breakpoints
- Use Tailwind plugins for additional functionality
- Implement proper purging for production builds"""
        
        elif "bootstrap" in styling_lower:
            practices += """- Use Bootstrap grid system for responsive layouts
- Customize Bootstrap variables for brand consistency
- Use Bootstrap components with proper accessibility
- Implement proper spacing and typography scales
- Use Bootstrap utilities for quick styling
- Avoid overriding Bootstrap classes unnecessarily"""
        
        elif "material" in styling_lower or "mui" in styling_lower:
            practices += """- Use Material-UI theme customization
- Implement proper component variants
- Use Material Design principles consistently
- Implement proper elevation and spacing
- Use Material icons and typography
- Follow Material Design accessibility guidelines"""
        
        # Add domain-specific practices
        if domain_lower:
            practices += f"\n\n🏢 DOMAIN-SPECIFIC PRACTICES FOR {domain.upper()}:\n"
            
            if "health" in domain_lower or "medical" in domain_lower:
                practices += """- Implement HIPAA-compliant UI patterns
- Use proper medical form validations
- Implement emergency contact features
- Use high contrast modes for accessibility
- Implement proper patient data masking
- Add medical workflow optimizations"""
            
            elif "financ" in domain_lower or "bank" in domain_lower:
                practices += """- Implement PCI-DSS compliant UI patterns
- Use secure payment form components
- Implement proper fraud detection UI
- Add financial data visualization components
- Use proper currency formatting
- Implement secure session management"""
            
            elif "ecommerce" in domain_lower:
                practices += """- Implement proper product catalog UI
- Use shopping cart state management
- Implement checkout flow optimization
- Add inventory management displays
- Use proper pricing and discount displays
- Implement order tracking interfaces"""
        
        # Add general production requirements
        practices += """\n\n⚡ GENERAL PRODUCTION REQUIREMENTS:

**Performance:**
- Implement proper code splitting and lazy loading
- Use image optimization (WebP, lazy loading)
- Implement proper caching strategies
- Monitor Core Web Vitals (LCP, FID, CLS)
- Use service workers for offline functionality
- Implement proper bundle optimization

**Security:**
- Implement proper CSP headers
- Use HTTPS in production
- Implement proper authentication and authorization
- Sanitize all user inputs
- Use environment variables for secrets
- Implement proper error handling without exposing sensitive data

**Accessibility:**
- Follow WCAG 2.1 AA guidelines
- Use semantic HTML elements
- Implement proper ARIA labels
- Ensure keyboard navigation
- Test with screen readers
- Maintain proper color contrast ratios

**SEO & Meta:**
- Implement proper meta tags
- Use structured data where applicable
- Implement proper Open Graph tags
- Use proper heading hierarchy
- Implement breadcrumb navigation
- Add proper sitemap and robots.txt

**Monitoring & Analytics:**
- Implement error tracking (Sentry)
- Add performance monitoring (Web Vitals)
- Use proper analytics tracking
- Implement user session recording
- Add A/B testing capabilities
- Monitor conversion funnels"""
        
        return practices

    def _create_component_architecture(self, system_design: Dict[str, Any], framework: str) -> str:
        """Create component architecture based on system design and framework."""
        architecture = f"COMPONENT ARCHITECTURE FOR {framework.upper()}:\n\n"
        
        # Extract components from system design
        components = system_design.get("ui", {}).get("components", [])
        screens = system_design.get("ui", {}).get("screens", [])
        
        if components:
            architecture += "REUSABLE COMPONENTS:\n"
            for component in components[:5]:  # Limit to avoid too much content
                if isinstance(component, dict):
                    name = component.get("name", "UnnamedComponent")
                    description = component.get("description", "No description")
                    architecture += f"- {name}: {description}\n"
            architecture += "\n"
        
        if screens:
            architecture += "SCREEN/PAGE COMPONENTS:\n"
            for screen in screens[:5]:  # Limit to avoid too much content
                if isinstance(screen, dict):
                    name = screen.get("name", "UnnamedScreen")
                    description = screen.get("description", "No description")
                    architecture += f"- {name}: {description}\n"
            architecture += "\n"
        
        # Add framework-specific architectural patterns
        if "react" in framework.lower():
            architecture += "REACT ARCHITECTURE PATTERNS:\n- Container/Presentational component pattern\n- Custom hooks for business logic"
        elif "vue" in framework.lower():
            architecture += "VUE ARCHITECTURE PATTERNS:\n- Single-file component structure\n- Composition API for logic organization"
        elif "angular" in framework.lower():
            architecture += "ANGULAR ARCHITECTURE PATTERNS:\n- Feature module organization\n- Smart/dumb component pattern"
        
        return architecture

    def _create_prompt_template(self) -> PromptTemplate:
        """Creates the prompt template for the agent."""
        prompt_string = """
        You are a world-class frontend developer specializing in modern JavaScript frameworks.
        Your task is to write clean, component-based, and well-documented frontend code.
        You must follow all instructions, including file paths and component names, precisely.

        {rag_context}

        **Technology Stack:**
        - Framework: {framework}
        - CSS Framework: {css_framework}
        - Testing Framework: {testing_framework}

        **Work Item:**
        - Description: {work_item_description}
        - File Path: {file_path}
        - Example Snippet (for reference):
        ```
        {example_code_snippet}
        ```

        **Instructions:**
        1.  Generate the complete code for the file specified in `File Path`.
        2.  You MUST also generate the corresponding unit tests.
        3.  Format your response clearly, separating the implementation code and test code with the specified tags.

        **Output Format:**
        Provide your response in the following format, and do not include any other text or explanations.

        [CODE]
        ```javascript
        // Your generated frontend code here
        ```
        [/CODE]

        [TESTS]
        ```javascript
        // Your generated unit tests here
        ```
        [/TESTS]
        """
        return PromptTemplate(
            template=prompt_string,
            input_variables=[
                "work_item_description",
                "file_path",
                "framework",
                "css_framework",
                "testing_framework",
                "example_code_snippet",
                "rag_context"
            ],
        )

    async def _generate_code(self, llm, invoke_config, work_item: WorkItem, tech_stack: dict) -> dict:
        """
        Generates frontend code and tests for a given work item asynchronously.
        """
        prompt_template = self._create_prompt_template()
        chain = prompt_template | llm

        query = f"Task: {work_item.description}\nFile to be created/modified: {work_item.file_path}"
        rag_context = self._get_rag_context(query)
        
        logger.info(f"Running FrontendGeneratorAgent for work item: {work_item.description}")

        try:
            result = await chain.ainvoke({
                "work_item_description": work_item.description,
                "file_path": work_item.file_path,
                "framework": tech_stack.get("frontend_framework", "React"),
                "css_framework": tech_stack.get("css_framework", "Tailwind CSS"),
                "testing_framework": tech_stack.get("frontend_testing_framework", "Jest"),
                "example_code_snippet": work_item.example or "No example provided.",
                "rag_context": rag_context
            })

            logger.info(f"FrontendGeneratorAgent completed for work item: {work_item.description}")
            
            parsed_output = self._parse_output(result.content)
            files = self._create_files_from_parsed_output(parsed_output, work_item)

            return CodeGenerationOutput(
                files=files,
                summary=f"Successfully generated frontend code and tests for: {work_item.description}"
            ).dict()
            
        except Exception as e:
            logger.error(f"Error running FrontendGeneratorAgent: {e}", exc_info=True)
            return self.get_default_response()
            
    def _parse_output(self, llm_output: str) -> dict:
        """Parses the LLM's output to extract the implementation and test code."""
        code = llm_output.split("[CODE]")[1].split("[/CODE]")[0].strip()
        test_code = llm_output.split("[TESTS]")[1].split("[/TESTS]")[0].strip()

        code = code.replace("```javascript", "").replace("```", "").strip()
        test_code = test_code.replace("```javascript", "").replace("```", "").strip()
        
        return {"code": code, "test_code": test_code}

    def _create_files_from_parsed_output(self, parsed_output: dict, work_item: WorkItem) -> list[GeneratedFile]:
        """Creates a list of GeneratedFile objects from the parsed LLM output."""
        files = []
        
        if parsed_output.get("code"):
            files.append(GeneratedFile(file_path=work_item.file_path, content=parsed_output["code"]))
        
        if parsed_output.get("test_code"):
            test_file_path = self._get_test_file_path(work_item.file_path)
            files.append(GeneratedFile(file_path=test_file_path, content=parsed_output["test_code"]))
            
        return files

    def _get_test_file_path(self, file_path_str: str) -> str:
        """Derives a conventional test file path from a source file path."""
        p = Path(file_path_str)
        parts = list(p.parts)
        
        try:
            src_index = parts.index('src')
            parts[src_index] = 'tests'
        except ValueError:
            parts.insert(0, 'tests')
            
        filename = f"test_{p.stem}{p.suffix}" # e.g., test_App.vue
        new_path = Path(*parts[:-1]) / filename
        return str(new_path)