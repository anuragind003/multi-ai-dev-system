import json
import os
import re
from typing import Dict, Any, List, Optional, Tuple
from langchain_core.language_models import BaseLanguageModel
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.retrievers import BaseRetriever
import monitoring
from .base_agent import BaseAgent

class TestCaseGeneratorAgent(BaseAgent):
    """Enhanced Test Case Generator Agent with multi-stage generation, specialized test frameworks,
    and intelligent test coverage analysis."""
    
    def __init__(self, llm: BaseLanguageModel, memory, output_dir: str, rag_retriever: Optional[BaseRetriever] = None):
        super().__init__(
            llm=llm,
            memory=memory,
            agent_name="TestCaseGeneratorAgent",
            temperature=0.2,  # Balanced creativity for test scenarios
            rag_retriever=rag_retriever
        )
        self.output_dir = output_dir
        
        # Initialize main prompt template
        self.prompt_template = PromptTemplate(
            template="""
            You are an expert Test Engineer and Software Quality Assurance specialist.
            Your task is to generate comprehensive test cases for the project based on the BRD analysis, system design, generated code files, and chosen technology stack.

            **Context:**
            - **BRD Analysis:** {brd_analysis}
            - **Tech Stack:** {tech_stack}
            - **Generated Code Files:** {code_files_summary}

            **RAG Context (relevant existing code/tests):**
            {rag_context}

            **Instructions:**
            Generate comprehensive test cases covering:
            1. **Unit Tests:** Test individual functions/methods in isolation
            2. **Integration Tests:** Test component interactions and API endpoints
            3. **Functional Tests:** Test business logic and user workflows
            4. **Edge Case Tests:** Test boundary conditions and error scenarios
            5. **Performance Tests:** Basic load and stress testing (if applicable)

            Create test files appropriate for the chosen tech stack and framework.
            Include setup/teardown, mock data, and assertions.

            **Output Requirements:**
            Generate a JSON object with test files:
            {{
                "tests/test_file1.py": "# Test file content here",
                "tests/test_file2.py": "# Another test file content"
            }}

            Output ONLY the JSON object with test file contents.
            """,
            input_variables=["brd_analysis", "tech_stack", "code_files_summary", "rag_context"]
        )
        
        # Framework-specific test templates
        self.framework_templates = {
            "pytest": self._create_pytest_template(),
            "jest": self._create_jest_template(),
            "junit": self._create_junit_template(),
            "mocha": self._create_mocha_template(),
            "django": self._create_django_test_template(),
        }
        
        # Test strategy analysis template
        self.test_strategy_template = PromptTemplate(
            template="""
            You are a Lead Test Strategist for software quality assurance.
            Analyze the provided code and requirements to develop a comprehensive test strategy.

            **Project Requirements:**
            {brd_summary}

            **Tech Stack:**
            {tech_stack}

            **Code Files Overview:**
            {code_files_summary}
            
            **Test Strategy Instructions:**
            Create a detailed test strategy that includes:
            1. Test coverage priorities (what to test first and most extensively)
            2. Recommended test types distribution (% unit tests vs integration vs functional vs UI)
            3. Critical user flows that require end-to-end testing
            4. Areas requiring security-focused testing
            5. Performance testing requirements
            6. Test environment needs

            Return your analysis as a JSON object with the following structure:
            {
                "test_coverage_priorities": [
                    {"area": "description", "priority": "high|medium|low", "rationale": "explanation"}
                ],
                "test_distribution": {
                    "unit_tests": percentage,
                    "integration_tests": percentage,
                    "functional_tests": percentage,
                    "ui_tests": percentage,
                    "security_tests": percentage,
                    "performance_tests": percentage
                },
                "critical_user_flows": [
                    {"flow_name": "name", "description": "description", "priority": "high|medium|low"}
                ],
                "security_testing_areas": [
                    {"area": "description", "risk_level": "high|medium|low", "testing_approach": "approach"}
                ],
                "performance_testing_requirements": [
                    {"type": "load|stress|endurance", "threshold": "description", "critical": boolean}
                ],
                "test_environment_requirements": [
                    {"requirement": "description", "purpose": "explanation"}
                ]
            }
            """,
            input_variables=["brd_summary", "tech_stack", "code_files_summary"]
        )
        
        # Test coverage analysis template
        self.test_coverage_template = PromptTemplate(
            template="""
            You are an expert in test coverage analysis.
            Analyze the provided code files to identify areas that need comprehensive testing.

            **Code Files:**
            {code_content}
            
            **Analysis Instructions:**
            Identify the following test-critical elements:
            1. Complex functions (high cyclomatic complexity)
            2. Functions with many branches/conditionals
            3. Error-prone areas (e.g., file operations, network calls)
            4. Security-sensitive operations
            5. Core business logic
            6. Public API endpoints
            7. Database interactions

            Return your analysis as a JSON object with the following structure:
            {
                "test_coverage_targets": [
                    {
                        "file_path": "path/to/file",
                        "function_name": "function name",
                        "complexity": "high|medium|low",
                        "type": "business_logic|api|data_access|security|error_handling|etc",
                        "importance": "critical|high|medium|low",
                        "suggested_test_approach": "description"
                    }
                ],
                "suggested_mocks": [
                    {
                        "component": "component to mock",
                        "purpose": "purpose of mocking",
                        "suggested_implementation": "brief description"
                    }
                ],
                "edge_cases": [
                    {
                        "scenario": "description",
                        "location": "file/function",
                        "importance": "high|medium|low"
                    }
                ]
            }
            """,
            input_variables=["code_content"]
        )
    
    def _create_pytest_template(self) -> PromptTemplate:
        """Create template for pytest test generation"""
        return PromptTemplate(
            template="""
            You are an expert pytest test developer. Create comprehensive pytest tests for the following code:

            **Code to Test:**
            {code_content}
            
            **Business Requirements:**
            {requirements}
            
            **Test Coverage Analysis:**
            {test_coverage_analysis}
            
            **Instructions:**
            Create pytest tests with these characteristics:
            - Use pytest fixtures for setup/teardown
            - Use parametrization for testing multiple scenarios
            - Include appropriate mocks/patches
            - Add docstrings explaining test purpose
            - Follow pytest best practices
            - Use pytest.mark.* decorators where appropriate
            - Target line coverage of 90%+
            
            **Generate this file:**
            {test_file_path}

            Return ONLY the complete test file content with no additional explanation.
            """,
            input_variables=["code_content", "requirements", "test_coverage_analysis", "test_file_path"]
        )
    
    def _create_jest_template(self) -> PromptTemplate:
        """Create template for Jest (JavaScript) test generation"""
        return PromptTemplate(
            template="""
            You are an expert Jest test developer. Create comprehensive Jest tests for the following code:

            **Code to Test:**
            {code_content}
            
            **Business Requirements:**
            {requirements}
            
            **Test Coverage Analysis:**
            {test_coverage_analysis}
            
            **Instructions:**
            Create Jest tests with these characteristics:
            - Use describe/it structure
            - Use beforeEach/afterEach for setup/teardown
            - Use Jest mocks appropriately
            - Include snapshot tests where appropriate
            - Test async code correctly using await/resolves/rejects
            - Add comments explaining test purpose
            - Test happy paths and edge cases
            
            **Generate this file:**
            {test_file_path}

            Return ONLY the complete test file content with no additional explanation.
            """,
            input_variables=["code_content", "requirements", "test_coverage_analysis", "test_file_path"]
        )
    
    def _create_junit_template(self) -> PromptTemplate:
        """Create template for JUnit (Java) test generation"""
        return PromptTemplate(
            template="""
            You are an expert JUnit test developer. Create comprehensive JUnit tests for the following code:

            **Code to Test:**
            {code_content}
            
            **Business Requirements:**
            {requirements}
            
            **Test Coverage Analysis:**
            {test_coverage_analysis}
            
            **Instructions:**
            Create JUnit tests with these characteristics:
            - Use @Before/@After for setup/teardown
            - Use appropriate assertions
            - Use Mockito for mocking dependencies
            - Add Javadoc comments explaining test purpose
            - Organize tests with @Category when appropriate
            - Include parameterized tests for multiple scenarios
            - Test exceptions using expected or assertThrows
            
            **Generate this file:**
            {test_file_path}

            Return ONLY the complete test file content with no additional explanation.
            """,
            input_variables=["code_content", "requirements", "test_coverage_analysis", "test_file_path"]
        )
    
    def _create_mocha_template(self) -> PromptTemplate:
        """Create template for Mocha (JavaScript) test generation"""
        return PromptTemplate(
            template="""
            You are an expert Mocha/Chai test developer. Create comprehensive Mocha tests for the following code:

            **Code to Test:**
            {code_content}
            
            **Business Requirements:**
            {requirements}
            
            **Test Coverage Analysis:**
            {test_coverage_analysis}
            
            **Instructions:**
            Create Mocha tests with these characteristics:
            - Use describe/it structure
            - Use before/after hooks for setup/teardown
            - Use Chai assertions with appropriate style (expect/should)
            - Use Sinon for mocks and spies
            - Test async code correctly using done callback or promises
            - Add comments explaining test purpose
            - Organize tests logically by feature area
            
            **Generate this file:**
            {test_file_path}

            Return ONLY the complete test file content with no additional explanation.
            """,
            input_variables=["code_content", "requirements", "test_coverage_analysis", "test_file_path"]
        )
    
    def _create_django_test_template(self) -> PromptTemplate:
        """Create template for Django test generation"""
        return PromptTemplate(
            template="""
            You are an expert Django test developer. Create comprehensive Django tests for the following code:

            **Code to Test:**
            {code_content}
            
            **Business Requirements:**
            {requirements}
            
            **Test Coverage Analysis:**
            {test_coverage_analysis}
            
            **Instructions:**
            Create Django tests with these characteristics:
            - Use TestCase for model/view tests
            - Use TransactionTestCase where appropriate
            - Set up test data in setUp method
            - Use appropriate assertions
            - Test both GET and POST requests for views
            - Check templates, context data, and redirects
            - Use Django's test client correctly
            - Add docstrings explaining test purpose
            
            **Generate this file:**
            {test_file_path}

            Return ONLY the complete test file content with no additional explanation.
            """,
            input_variables=["code_content", "requirements", "test_coverage_analysis", "test_file_path"]
        )
    
    def run(self, code_generation_result: dict, brd_analysis: dict, tech_stack_recommendation: dict) -> Dict[str, Any]:
        """
        Enhanced multi-stage test case generation with specialized test framework templates,
        test coverage analysis, and comprehensive test strategy.
        """
        monitoring.log_agent_activity(self.agent_name, "Starting multi-stage test generation", "START")
        self.log_info("Starting multi-stage test case generation...")
        
        # Validate inputs
        if not all([code_generation_result, brd_analysis, tech_stack_recommendation]):
            self.log_warning("Missing required inputs for test generation")
            return self.get_default_response()
        
        # Extract generated files from the structured response
        generated_files = code_generation_result.get("generated_files", {})
        if not generated_files:
            self.log_warning("No generated files found for test creation")
            return self.get_default_response()
        
        try:
            # STAGE 1: Create BRD summary for test strategy
            self.log_info("Stage 1: Creating BRD summary for test strategy")
            brd_summary = self._create_brd_summary(brd_analysis)
            
            # STAGE 2: Analyze code files to prepare code summary
            self.log_info("Stage 2: Analyzing code files and creating summary")
            code_files_summary = self._prepare_enhanced_code_summary(generated_files)
            
            # STAGE 3: Generate test strategy
            self.log_info("Stage 3: Generating comprehensive test strategy")
            test_strategy = self._generate_test_strategy(brd_summary, tech_stack_recommendation, code_files_summary)
            
            # STAGE 4: Perform test coverage analysis on key files
            self.log_info("Stage 4: Performing test coverage analysis")
            test_coverage_analysis = self._analyze_test_coverage(generated_files, test_strategy)
            
            # STAGE 5: Get framework-specific RAG context
            self.log_info("Stage 5: Retrieving framework-specific test patterns")
            test_framework = self._determine_test_framework(tech_stack_recommendation)
            rag_context = self._get_enhanced_rag_context(test_framework, tech_stack_recommendation)
            
            # STAGE 6: Generate specialized test files
            self.log_info(f"Stage 6: Generating specialized {test_framework} tests")
            test_files = self._generate_specialized_tests(
                generated_files, 
                brd_analysis, 
                tech_stack_recommendation,
                test_strategy,
                test_coverage_analysis,
                test_framework,
                rag_context
            )
            
            if not test_files:
                # Fallback to general approach if specialized generation fails
                self.log_info("Specialized test generation failed, falling back to general approach")
                test_files = self._generate_general_tests(
                    generated_files, 
                    brd_analysis, 
                    tech_stack_recommendation,
                    rag_context
                )
            
            # STAGE 7: Save and validate generated test files
            self.log_info("Stage 7: Saving and validating test files")
            saved_files = self._save_test_files(test_files)
            
            # STAGE 8: Generate test execution guide
            self.log_info("Stage 8: Generating test execution guide")
            test_guide = self._generate_test_execution_guide(saved_files, test_framework, test_strategy)
            
            # Create final response with detailed information
            test_count = len(saved_files)
            coverage_areas = self._extract_coverage_areas(saved_files, test_strategy)
            
            if saved_files:
                self.log_success(f"Generated {test_count} test files using {test_framework}")
                response = {
                    "status": "success",
                    "test_files": saved_files,
                    "test_count": test_count,
                    "testing_framework": test_framework,
                    "output_directory": self.output_dir,
                    "coverage_areas": coverage_areas,
                    "test_strategy": test_strategy,
                    "test_guide": test_guide,
                    "summary": f"Successfully generated {test_count} test files for {test_framework} project"
                }
                
                self.log_execution_summary(response)
                return response
            else:
                self.log_warning("No test files were generated")
                return self.get_default_response()

        except Exception as e:
            self.log_error(f"Test generation failed: {e}")
            return self.get_default_response()
    
    def _create_brd_summary(self, brd_analysis: dict) -> str:
        """Create a focused summary of BRD analysis for test strategy generation."""
        summary_parts = []
        
        # Extract project overview
        if "project_overview" in brd_analysis:
            po = brd_analysis["project_overview"]
            summary_parts.append("## PROJECT OVERVIEW")
            summary_parts.append(f"Project: {po.get('project_name', 'Unknown')}")
            summary_parts.append(f"Description: {po.get('description', 'Not specified')}")
            if "objectives" in po:
                objectives = po.get("objectives", [])
                summary_parts.append("Objectives:")
                for obj in objectives[:5]:  # Limit to top 5
                    summary_parts.append(f"- {obj}")
        
        # Extract functional requirements
        if "functional_requirements" in brd_analysis:
            summary_parts.append("\n## FUNCTIONAL REQUIREMENTS")
            for req in brd_analysis["functional_requirements"][:10]:  # Limit to top 10
                req_id = req.get("id", "Unknown")
                desc = req.get("description", "No description")
                priority = req.get("priority", "Medium")
                summary_parts.append(f"- [{priority}] {req_id}: {desc}")
        
        # Extract user roles
        if "user_roles" in brd_analysis:
            summary_parts.append("\n## USER ROLES")
            for role in brd_analysis["user_roles"][:5]:  # Limit to top 5
                role_name = role.get("role_name", "Unknown")
                desc = role.get("description", "No description")
                summary_parts.append(f"- {role_name}: {desc}")
        
        # Extract non-functional requirements
        if "non_functional_requirements" in brd_analysis:
            nfr = brd_analysis["non_functional_requirements"]
            summary_parts.append("\n## NON-FUNCTIONAL REQUIREMENTS")
            
            for category in ["performance", "security", "reliability", "usability"]:
                if category in nfr:
                    requirements = nfr[category]
                    if requirements:
                        summary_parts.append(f"\n### {category.upper()}")
                        for req in requirements[:3]:  # Limit to top 3
                            summary_parts.append(f"- {req}")
        
        return "\n".join(summary_parts)
    
    def _prepare_enhanced_code_summary(self, generated_code_files: dict) -> str:
        """Create an enhanced summary of code files with structural information."""
        if not generated_code_files:
            return "No code files available"
        
        summary_parts = []
        
        # Group files by type/directory
        grouped_files = {}
        for file_path in generated_code_files.keys():
            dir_path = os.path.dirname(file_path)
            if dir_path not in grouped_files:
                grouped_files[dir_path] = []
            grouped_files[dir_path].append(file_path)
        
        # Summarize by directory
        for dir_path, files in grouped_files.items():
            summary_parts.append(f"\n## {dir_path or 'Root directory'}")
            for file_path in sorted(files):
                content = generated_code_files[file_path]
                lines = content.count('\n') + 1
                
                # Extract key structural elements
                structure_info = self._extract_code_structure(file_path, content)
                summary_parts.append(f"- {os.path.basename(file_path)}: {lines} lines{structure_info}")
        
        # Add overall statistics
        total_files = len(generated_code_files)
        total_lines = sum(generated_code_files[f].count('\n') + 1 for f in generated_code_files)
        summary_parts.insert(0, f"# CODE SUMMARY: {total_files} files, {total_lines} total lines")
        
        return "\n".join(summary_parts)
    
    def _extract_code_structure(self, file_path: str, content: str) -> str:
        """Extract structural information from code files."""
        structure_parts = []
        
        # Python files
        if file_path.endswith('.py'):
            classes = len(re.findall(r'^\s*class\s+\w+', content, re.MULTILINE))
            functions = len(re.findall(r'^\s*def\s+\w+', content, re.MULTILINE))
            if classes > 0:
                structure_parts.append(f"{classes} classes")
            if functions > 0:
                structure_parts.append(f"{functions} functions")
        
        # JavaScript/TypeScript files
        elif file_path.endswith(('.js', '.ts', '.jsx', '.tsx')):
            classes = len(re.findall(r'class\s+\w+', content))
            functions = len(re.findall(r'function\s+\w+', content)) + len(re.findall(r'=>', content))
            if classes > 0:
                structure_parts.append(f"{classes} classes")
            if functions > 0:
                structure_parts.append(f"{functions} functions/methods")
                
        # Java files
        elif file_path.endswith('.java'):
            classes = len(re.findall(r'class\s+\w+', content))
            methods = len(re.findall(r'\s\w+\s*\([^\)]*\)\s*(\{|throws)', content))
            if classes > 0:
                structure_parts.append(f"{classes} classes")
            if methods > 0:
                structure_parts.append(f"{methods} methods")
        
        if structure_parts:
            return f" ({', '.join(structure_parts)})"
        return ""
    
    def _generate_test_strategy(self, brd_summary: str, tech_stack: dict, code_summary: str) -> Dict[str, Any]:
        """Generate comprehensive test strategy based on BRD and code structure."""
        self.log_info("Generating test strategy with temperature 0.3 for creative test approaches")
        
        try:
            # Use slightly higher temperature for creative test strategy generation
            llm_with_temp = self.llm.bind(temperature=0.3)
            
            # Format inputs
            tech_stack_str = json.dumps(tech_stack, indent=2)
            
            # Generate test strategy
            prompt = self.test_strategy_template.format(
                brd_summary=brd_summary,
                tech_stack=tech_stack_str,
                code_files_summary=code_summary
            )
            
            response = llm_with_temp.invoke(prompt)
            
            try:
                # Parse the strategy JSON from the response
                strategy_text = response.content
                strategy = json.loads(strategy_text)
                return strategy
            except Exception as parse_e:
                self.log_warning(f"Failed to parse test strategy: {parse_e}")
                return self._get_default_test_strategy()
                
        except Exception as e:
            self.log_warning(f"Test strategy generation failed: {e}")
            return self._get_default_test_strategy()
    
    def _get_default_test_strategy(self) -> Dict[str, Any]:
        """Get default test strategy when generation fails."""
        return {
            "test_coverage_priorities": [
                {"area": "Core business logic", "priority": "high", "rationale": "Critical for application correctness"}
            ],
            "test_distribution": {
                "unit_tests": 60,
                "integration_tests": 25,
                "functional_tests": 10,
                "ui_tests": 0,
                "security_tests": 5,
                "performance_tests": 0
            },
            "critical_user_flows": [
                {"flow_name": "Main application flow", "description": "Basic happy path of the application", "priority": "high"}
            ],
            "security_testing_areas": [],
            "performance_testing_requirements": [],
            "test_environment_requirements": [
                {"requirement": "Standard testing environment", "purpose": "Run basic tests"}
            ]
        }
    
    def _analyze_test_coverage(self, generated_files: dict, test_strategy: dict) -> Dict[str, Any]:
        """Analyze code files to determine test coverage needs."""
        self.log_info("Analyzing code for test coverage targets")
        
        if not generated_files:
            return {"test_coverage_targets": [], "suggested_mocks": [], "edge_cases": []}
        
        try:
            # Use low temperature for analytical task
            llm_with_temp = self.llm.bind(temperature=0.1)
            
            # Select most important files to analyze
            key_files = self._select_important_files_for_testing(generated_files, test_strategy)
            
            # Combine content of key files
            combined_code = self._combine_files_for_analysis(key_files)
            
            # Run analysis
            prompt = self.test_coverage_template.format(
                code_content=combined_code
            )
            
            response = llm_with_temp.invoke(prompt)
            
            try:
                # Parse the coverage analysis JSON
                coverage_text = response.content
                coverage_analysis = json.loads(coverage_text)
                return coverage_analysis
            except Exception as parse_e:
                self.log_warning(f"Failed to parse test coverage analysis: {parse_e}")
                return {"test_coverage_targets": [], "suggested_mocks": [], "edge_cases": []}
                
        except Exception as e:
            self.log_warning(f"Test coverage analysis failed: {e}")
            return {"test_coverage_targets": [], "suggested_mocks": [], "edge_cases": []}
    
    def _select_important_files_for_testing(self, generated_files: dict, test_strategy: dict) -> List[Tuple[str, str]]:
        """Select the most important files for test coverage analysis."""
        # Priority patterns for test-critical files
        test_priority_patterns = [
            # Core business logic
            'service', 'controller', 'manager', 'handler', 'processor',
            # Data handling
            'model', 'repository', 'dao', 'store',
            # API endpoints
            'api', 'route', 'endpoint', 'view', 'resource',
            # Security
            'auth', 'security', 'permission', 'access'
        ]
        
        # Score each file based on testing importance
        scored_files = []
        
        for path, content in generated_files.items():
            # Skip non-code files
            if not self._is_testable_file(path):
                continue
                
            score = 0
            lower_path = path.lower()
            
            # Check filename for priority patterns
            for pattern in test_priority_patterns:
                if pattern in lower_path:
                    score += 3
            
            # Check content for testable elements
            lower_content = content.lower()
            if 'class' in lower_content:
                score += 2
            if 'function' in lower_content or 'def ' in lower_content:
                score += 2
            if 'test' in lower_content:
                score -= 1  # Likely already a test file
            if 'public' in lower_content:
                score += 1  # Public methods are important to test
            if 'throw' in lower_content or 'exception' in lower_content or 'error' in lower_content:
                score += 2  # Error handling is important to test
            
            # Look for areas mentioned in test strategy priorities
            for priority_area in test_strategy.get("test_coverage_priorities", []):
                area = priority_area.get("area", "").lower()
                if area and area in lower_path or area in lower_content:
                    if priority_area.get("priority") == "high":
                        score += 5
                    elif priority_area.get("priority") == "medium":
                        score += 3
            
            scored_files.append((path, content, score))
        
        # Sort by score descending and take top 5
        scored_files.sort(key=lambda x: x[2], reverse=True)
        return [(path, content) for path, content, _ in scored_files[:5]]
    
    def _is_testable_file(self, file_path: str) -> bool:
        """Check if a file should be included in test coverage analysis."""
        testable_extensions = ['.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.rb', '.php', '.cs', '.go']
        
        # Skip test files themselves
        if 'test_' in file_path or 'spec.' in file_path:
            return False
            
        return any(file_path.endswith(ext) for ext in testable_extensions)
    
    def _combine_files_for_analysis(self, files: List[Tuple[str, str]]) -> str:
        """Combine multiple files into a single string for analysis."""
        combined_parts = []
        
        for file_path, content in files:
            combined_parts.append(f"## FILE: {file_path}\n```\n{content}\n```\n")
        
        return "\n".join(combined_parts)
    
    def _get_enhanced_rag_context(self, test_framework: str, tech_stack: dict) -> str:
        """Get enhanced RAG context with multiple targeted queries for testing."""
        context_parts = []
        
        # Get framework-specific test patterns
        framework_query = f"{test_framework} best practices test patterns examples"
        context_parts.append(self.get_rag_context(framework_query))
        
        # Get language-specific test patterns
        language = tech_stack.get('backend', {}).get('language', '')
        if language:
            language_query = f"{language} {test_framework} testing mocks fixtures examples"
            context_parts.append(self.get_rag_context(language_query))
        
        # Get testing patterns for the specific architecture
        architecture = tech_stack.get('architecture_pattern', '')
        if architecture:
            arch_query = f"testing {architecture} architecture patterns best practices"
            context_parts.append(self.get_rag_context(arch_query))
        
        # Combine contexts with headers
        combined_context = "\n\n".join(context_parts)
        return combined_context
    
    def _determine_test_framework(self, tech_stack: dict) -> str:
        """Determine the appropriate test framework based on tech stack."""
        language = tech_stack.get('backend', {}).get('language', '').lower()
        framework = tech_stack.get('backend', {}).get('framework', '').lower()
        
        # Map language/framework to test framework
        if language == 'python' or framework == 'flask' or framework == 'fastapi':
            return 'pytest'
        elif framework == 'django':
            return 'django'
        elif language == 'javascript' or language == 'typescript':
            if 'react' in framework or 'vue' in framework or 'angular' in framework:
                return 'jest'
            else:
                return 'mocha'
        elif language == 'java' or framework == 'spring':
            return 'junit'
        
        # Default to pytest as a fallback
        return 'pytest'
    
    def _generate_specialized_tests(
        self, 
        generated_files: dict,
        brd_analysis: dict,
        tech_stack: dict,
        test_strategy: dict,
        coverage_analysis: dict,
        test_framework: str,
        rag_context: str
    ) -> dict:
        """Generate tests using framework-specific templates."""
        self.log_info(f"Generating specialized {test_framework} tests")
        
        if test_framework not in self.framework_templates:
            self.log_warning(f"No specialized template for {test_framework}, falling back")
            return {}
        
        try:
            # Get the appropriate template
            template = self.framework_templates[test_framework]
            
            # Use appropriate temperature for test generation
            llm_with_temp = self.llm.bind(temperature=0.2)
            
            test_files = {}
            test_targets = coverage_analysis.get("test_coverage_targets", [])
            
            # If no targets identified, use default approach
            if not test_targets:
                return self._generate_general_tests(generated_files, brd_analysis, tech_stack, rag_context)
            
            # Group targets by file
            targets_by_file = {}
            for target in test_targets:
                file_path = target.get("file_path", "")
                if file_path not in targets_by_file:
                    targets_by_file[file_path] = []
                targets_by_file[file_path].append(target)
            
            # Group file types for batch testing (e.g., all models together)
            file_groups = self._group_similar_files(targets_by_file.keys())
            
            # Process each file or file group
            for file_group in file_groups:
                # Combine target info
                combined_targets = []
                for file_path in file_group:
                    if file_path in targets_by_file:
                        combined_targets.extend(targets_by_file[file_path])
                
                if not combined_targets:
                    continue
                
                # Get main file in the group
                main_file = file_group[0]
                if main_file not in generated_files:
                    continue
                
                # Extract requirements relevant to this file
                file_requirements = self._extract_relevant_requirements(brd_analysis, main_file, combined_targets)
                
                # Generate test file path
                test_file_path = self._generate_test_file_path(main_file, test_framework)
                
                # Format code coverage for this file
                coverage_json = json.dumps({
                    "test_coverage_targets": combined_targets,
                    "suggested_mocks": coverage_analysis.get("suggested_mocks", []),
                    "edge_cases": coverage_analysis.get("edge_cases", [])
                }, indent=2)
                
                # Generate specialized test
                prompt = template.format(
                    code_content=generated_files[main_file],
                    requirements=file_requirements,
                    test_coverage_analysis=coverage_json,
                    test_file_path=test_file_path
                )
                
                response = llm_with_temp.invoke(prompt)
                test_content = response.content
                
                # Add to test files
                test_files[test_file_path] = test_content
            
            return test_files
            
        except Exception as e:
            self.log_error(f"Specialized test generation failed: {e}")
            return {}
    
    def _generate_general_tests(
        self,
        generated_files: dict,
        brd_analysis: dict,
        tech_stack: dict,
        rag_context: str
    ) -> dict:
        """Generate tests using the general approach when specialized fails."""
        self.log_info("Using general test generation approach")
        
        try:
            # Prepare inputs
            code_files_summary = self._prepare_code_summary(generated_files)
            brd_summary = json.dumps(brd_analysis, indent=2)
            tech_stack_summary = json.dumps(tech_stack, indent=2)
            
            # Use base agent's execute_llm_chain with our standard template
            response = self.execute_llm_chain({
                "brd_analysis": brd_summary,
                "tech_stack": tech_stack_summary,
                "code_files_summary": code_files_summary,
                "rag_context": rag_context
            })
            
            return response
            
        except Exception as e:
            self.log_error(f"General test generation failed: {e}")
            return {}
    
    def _prepare_code_summary(self, generated_code_files: dict) -> str:
        """Prepare concise summary of generated code files."""
        if not generated_code_files:
            return "No code files available"
        
        summary_parts = []
        for file_path, content in list(generated_code_files.items())[:10]:  # Limit for tokens
            lines = content.count('\n') + 1
            summary_parts.append(f"- {file_path}: {lines} lines")
        
        if len(generated_code_files) > 10:
            summary_parts.append(f"... and {len(generated_code_files) - 10} more files")
        
        return "\n".join(summary_parts)
    
    def _generate_test_file_path(self, source_file_path: str, test_framework: str) -> str:
        """Generate appropriate test file path based on source file and framework."""
        dir_path, filename = os.path.split(source_file_path)
        base_name, ext = os.path.splitext(filename)
        
        # Different frameworks have different conventions
        if test_framework == 'pytest':
            return os.path.join('tests', f'test_{filename}')
        elif test_framework == 'django':
            app_dir = os.path.basename(dir_path) if dir_path else 'main'
            return os.path.join(app_dir, 'tests', f'test_{filename}')
        elif test_framework == 'jest':
            return os.path.join(dir_path, f'{base_name}.test{ext}')
        elif test_framework == 'mocha':
            test_dir = os.path.join('test', dir_path) if dir_path else 'test'
            return os.path.join(test_dir, f'{base_name}.test{ext}')
        elif test_framework == 'junit':
            if dir_path:
                test_dir = dir_path.replace('src/main', 'src/test')
                return os.path.join(test_dir, f'{base_name}Test.java')
            else:
                return f'src/test/java/{base_name}Test.java'
        
        # Default fallback
        return os.path.join('tests', f'test_{filename}')
    
    def _group_similar_files(self, file_paths: List[str]) -> List[List[str]]:
        """Group similar files that should be tested together."""
        # Initialize groups
        groups = []
        
        # Group by directory and naming pattern
        grouped = {}
        for file_path in file_paths:
            dir_name = os.path.dirname(file_path)
            file_name = os.path.basename(file_path)
            
            # Try to extract component type from name
            component_type = None
            for type_pattern in ['model', 'service', 'controller', 'repository', 'view', 'util']:
                if type_pattern in file_name.lower() or type_pattern in dir_name.lower():
                    component_type = type_pattern
                    break
            
            if not component_type:
                component_type = dir_name if dir_name else 'other'
                
            if component_type not in grouped:
                grouped[component_type] = []
                
            grouped[component_type].append(file_path)
        
        # Convert dictionary to list of groups
        for _, files in grouped.items():
            groups.append(files)
            
        return groups
    
    def _extract_relevant_requirements(
        self, 
        brd_analysis: dict, 
        file_path: str, 
        targets: List[Dict[str, Any]]
    ) -> str:
        """Extract requirements relevant to the file being tested."""
        if not brd_analysis:
            return "No specific requirements provided"
            
        requirements_parts = []
        file_name = os.path.basename(file_path).lower()
        
        # Look for functional requirements that might match this file
        if "functional_requirements" in brd_analysis:
            relevant_reqs = []
            
            for req in brd_analysis["functional_requirements"]:
                req_desc = req.get("description", "").lower()
                
                # Check if requirement might be related to this file
                is_relevant = False
                
                # Check file name against requirement
                file_tokens = re.findall(r'[a-z]+', file_name)
                for token in file_tokens:
                    if token and len(token) > 3 and token in req_desc:
                        is_relevant = True
                        break
                
                # Check function names against requirement
                for target in targets:
                    func_name = target.get("function_name", "").lower()
                    if func_name and len(func_name) > 3 and func_name in req_desc:
                        is_relevant = True
                        break
                
                if is_relevant:
                    req_id = req.get("id", "")
                    priority = req.get("priority", "")
                    relevant_reqs.append(f"- [{priority}] {req_id}: {req.get('description', '')}")
            
            if relevant_reqs:
                requirements_parts.append("## Relevant Functional Requirements")
                requirements_parts.extend(relevant_reqs)
        
        # Add non-functional requirements related to the file content
        if "non_functional_requirements" in brd_analysis:
            nfr = brd_analysis["non_functional_requirements"]
            
            # Check for security requirements for security-related files
            if any(term in file_path.lower() for term in ["security", "auth", "login", "password"]):
                security_reqs = nfr.get("security", [])
                if security_reqs:
                    requirements_parts.append("\n## Security Requirements")
                    requirements_parts.extend([f"- {req}" for req in security_reqs])
            
            # Check for performance requirements for core functionality
            for target in targets:
                if target.get("importance") == "critical" or target.get("importance") == "high":
                    performance_reqs = nfr.get("performance", [])
                    if performance_reqs:
                        requirements_parts.append("\n## Performance Requirements")
                        requirements_parts.extend([f"- {req}" for req in performance_reqs])
                    break
        
        # Default text if no relevant requirements found
        if not requirements_parts:
            return "No specific requirements identified for this component"
            
        return "\n".join(requirements_parts)
    
    def _save_test_files(self, test_files: dict) -> dict:
        """Save generated test files to disk."""
        saved_files = {}
        
        for file_path, content in test_files.items():
            try:
                full_path = os.path.join(self.output_dir, file_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                saved_files[file_path] = content
                self.log_info(f"Saved test file: {file_path}")
                
            except Exception as e:
                self.log_warning(f"Failed to save test file {file_path}: {e}")
        
        return saved_files
    
    def _extract_coverage_areas(self, test_files: dict, test_strategy: dict) -> List[str]:
        """Extract test coverage areas from the test files and strategy."""
        coverage_areas = set()
        
        # Look for test files and infer coverage areas
        for file_path in test_files.keys():
            file_path_lower = file_path.lower()
            content_lower = test_files[file_path].lower()
            
            if 'unit' in file_path_lower or '@test' in content_lower or 'test_' in content_lower:
                coverage_areas.add("Unit Tests")
            if 'integration' in file_path_lower or 'integration' in content_lower:
                coverage_areas.add("Integration Tests")
            if 'functional' in file_path_lower or 'functional' in content_lower:
                coverage_areas.add("Functional Tests")
            if 'api' in file_path_lower or 'endpoint' in file_path_lower or 'api' in content_lower:
                coverage_areas.add("API Tests")
            if 'e2e' in file_path_lower or 'end-to-end' in content_lower:
                coverage_areas.add("End-to-End Tests")
            if 'performance' in file_path_lower or 'benchmark' in content_lower:
                coverage_areas.add("Performance Tests")
        
        # Add areas from test strategy if available
        if test_strategy and "test_distribution" in test_strategy:
            dist = test_strategy["test_distribution"]
            if dist.get("unit_tests", 0) > 0:
                coverage_areas.add("Unit Tests")
            if dist.get("integration_tests", 0) > 0:
                coverage_areas.add("Integration Tests")
            if dist.get("functional_tests", 0) > 0:
                coverage_areas.add("Functional Tests")
            if dist.get("security_tests", 0) > 0:
                coverage_areas.add("Security Tests")
            if dist.get("performance_tests", 0) > 0:
                coverage_areas.add("Performance Tests")
        
        return list(coverage_areas) if coverage_areas else ["General Tests"]
    
    def _generate_test_execution_guide(self, test_files: dict, test_framework: str, test_strategy: dict) -> Dict[str, Any]:
        """Generate a guide for executing and understanding the test suite."""
        self.log_info("Generating test execution guide")
        
        # Determine command to run tests based on framework
        run_command = self._get_test_run_command(test_framework)
        
        # Group tests by type
        test_groups = self._group_tests_by_type(test_files)
        
        # Create guide sections
        guide_sections = [
            {
                "title": "Test Execution Commands",
                "content": [
                    f"Run all tests: `{run_command}`",
                    f"Run with coverage: `{self._get_coverage_command(test_framework)}`"
                ]
            },
            {
                "title": "Test Structure",
                "content": [f"{group}: {len(files)} tests" for group, files in test_groups.items()]
            }
        ]
        
        # Add test priorities if available in test strategy
        if test_strategy and "test_coverage_priorities" in test_strategy:
            priority_content = []
            for priority in test_strategy["test_coverage_priorities"]:
                area = priority.get("area", "Unknown")
                level = priority.get("priority", "medium")
                priority_content.append(f"{area}: {level} priority")
                
            if priority_content:
                guide_sections.append({
                    "title": "Testing Priorities",
                    "content": priority_content
                })
        
        # Add critical flows to test if available
        if test_strategy and "critical_user_flows" in test_strategy:
            flow_content = []
            for flow in test_strategy["critical_user_flows"]:
                flow_name = flow.get("flow_name", "Unknown")
                flow_desc = flow.get("description", "")
                flow_priority = flow.get("priority", "medium")
                flow_content.append(f"{flow_name} ({flow_priority}): {flow_desc}")
                
            if flow_content:
                guide_sections.append({
                    "title": "Critical User Flows",
                    "content": flow_content
                })
        
        return {
            "test_framework": test_framework,
            "setup_instructions": self._get_framework_setup_instructions(test_framework),
            "sections": guide_sections
        }
    
    def _get_test_run_command(self, test_framework: str) -> str:
        """Get the command to run tests for the given framework."""
        framework_commands = {
            "pytest": "python -m pytest",
            "django": "python manage.py test",
            "jest": "npm test",
            "mocha": "npx mocha",
            "junit": "mvn test"
        }
        return framework_commands.get(test_framework, "python -m pytest")
    
    def _get_coverage_command(self, test_framework: str) -> str:
        """Get the command to run tests with coverage for the given framework."""
        coverage_commands = {
            "pytest": "python -m pytest --cov=.",
            "django": "coverage run manage.py test",
            "jest": "npm test -- --coverage",
            "mocha": "nyc npx mocha",
            "junit": "mvn test jacoco:report"
        }
        return coverage_commands.get(test_framework, "python -m pytest --cov=.")
    
    def _get_framework_setup_instructions(self, test_framework: str) -> List[str]:
        """Get setup instructions for the test framework."""
        setup_instructions = {
            "pytest": [
                "Install required packages: `pip install pytest pytest-cov`",
                "Tests should be in the 'tests' directory or named 'test_*.py'"
            ],
            "django": [
                "Install required packages: `pip install coverage`",
                "Tests should be in app/tests/ directories"
            ],
            "jest": [
                "Install required packages: `npm install --save-dev jest`",
                "Configure Jest in package.json",
                "Tests should be named '*.test.js' or in '__tests__' directories"
            ],
            "mocha": [
                "Install required packages: `npm install --save-dev mocha chai nyc`",
                "Tests should be in the 'test' directory"
            ],
            "junit": [
                "Configure JUnit in pom.xml",
                "Tests should be in 'src/test/java' directory"
            ]
        }
        return setup_instructions.get(test_framework, ["No specific setup instructions available"])
    
    def _group_tests_by_type(self, test_files: dict) -> Dict[str, List[str]]:
        """Group test files by test type."""
        groups = {
            "Unit Tests": [],
            "Integration Tests": [],
            "Functional Tests": [],
            "API Tests": [],
            "Other Tests": []
        }
        
        for file_path in test_files:
            file_path_lower = file_path.lower()
            content_lower = test_files[file_path].lower()
            
            if 'unit' in file_path_lower or ('test_' in file_path_lower and not any(t in file_path_lower for t in ['integration', 'functional', 'api'])):
                groups["Unit Tests"].append(file_path)
            elif 'integration' in file_path_lower:
                groups["Integration Tests"].append(file_path)
            elif 'functional' in file_path_lower:
                groups["Functional Tests"].append(file_path)
            elif 'api' in file_path_lower or 'endpoint' in file_path_lower:
                groups["API Tests"].append(file_path)
            else:
                groups["Other Tests"].append(file_path)
        
        # Remove empty groups
        return {group: files for group, files in groups.items() if files}
    
    def get_default_response(self) -> Dict[str, Any]:
        """ENHANCED: Get structured default response when test generation fails."""
        return {
            "status": "error",
            "test_files": {},
            "test_count": 0,
            "testing_framework": "Unknown",
            "output_directory": self.output_dir,
            "coverage_areas": [],
            "summary": "Test generation failed due to unexpected error",
            "error": "Test generation process encountered critical errors"
        }
    
    def log_execution_summary(self, response: Dict[str, Any]):
        """Log detailed execution summary for test generation."""
        test_count = response.get("test_count", 0)
        framework = response.get("testing_framework", "Unknown")
        coverage_areas = response.get("coverage_areas", [])
        
        monitoring.log_agent_activity(
            self.agent_name,
            f"Test generation complete - {test_count} tests using {framework}, Coverage: {', '.join(coverage_areas)}",
            "SUCCESS"
        )
        
        self.log_success(f"Test generation complete")
        self.log_info(f"   Generated files: {test_count}")
        self.log_info(f"   Framework: {framework}")
        self.log_info(f"   Coverage areas: {', '.join(coverage_areas)}")
        
        # Log test strategy information if available
        test_strategy = response.get("test_strategy", {})
        if test_strategy and "test_distribution" in test_strategy:
            dist = test_strategy["test_distribution"]
            self.log_info("   Test distribution:")
            for test_type, percentage in dist.items():
                if percentage > 0:
                    self.log_info(f"      - {test_type}: {percentage}%")