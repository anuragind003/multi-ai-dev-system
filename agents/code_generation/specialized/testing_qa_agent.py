"""
Testing QA Agent - Specialized for testing infrastructure
Focuses on unit testing, integration testing, and performance testing.
"""

import json
import os
import time
from typing import Dict, Any, List, Optional, Set

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

class TestingQAAgent(BaseCodeGeneratorAgent):
    """Testing QA Agent for comprehensive testing infrastructure."""
    
    def __init__(self, 
                 llm: BaseLanguageModel, 
                 memory, 
                 temperature: float,
                 output_dir: str, 
                 code_execution_tool: CodeExecutionTool,
                 rag_retriever: Optional[BaseRetriever] = None,
                 message_bus: Optional[MessageBus] = None):
        """Initialize Testing QA Agent."""
        
        super().__init__(
            llm=llm,
            memory=memory,
            agent_name="Testing QA Agent",
            temperature=temperature,
            output_dir=output_dir,
            code_execution_tool=code_execution_tool,
            rag_retriever=rag_retriever,
            message_bus=message_bus
        )
        
        # Testing-specific prompt template
        self.testing_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert Testing QA Engineer specializing in comprehensive testing infrastructure.

Your expertise includes:
- Unit testing frameworks and best practices
- Integration testing strategies
- Performance and load testing
- Test automation and CI/CD integration
- Test data management and mocking
- API testing and contract testing
- Security testing fundamentals
- Test coverage analysis and reporting

Industry best practices:
- Follow testing pyramid: Unit tests (70%), Integration tests (20%), E2E tests (10%)
- Write descriptive test names that explain the scenario
- Use proper test structure: Arrange, Act, Assert (AAA)
- Implement proper test isolation and cleanup
- Use factory patterns for test data generation
- Implement proper error handling and edge case testing
- Follow test-driven development (TDD) principles when applicable
- Ensure tests are maintainable and readable

For Python projects, use pytest as the primary framework with coverage reporting.
For JavaScript/Node.js projects, use Jest or Mocha with appropriate assertion libraries.
For Java projects, use JUnit 5 with proper test annotations.

Generate production-ready testing infrastructure that includes:
1. Unit test files for models, services, and utilities
2. Integration test files for APIs and database operations
3. Configuration files (pytest.ini, jest.config.js, etc.)
4. Test fixtures and factories
5. Mock configurations and test data
6. Performance test scripts
7. CI/CD test automation scripts
8. Test documentation and guidelines

Ensure all tests follow naming conventions, have proper documentation, and include both positive and negative test cases."""),
            ("human", """Generate comprehensive testing infrastructure for a {domain} application.

Requirements:
- Domain: {domain}
- Programming Language: {language}
- Framework: {framework}
- Scale: {scale}
- Features: {features}
- Additional Requirements: {additional_requirements}

Generate a complete testing suite including:
1. Unit tests for core business logic
2. Integration tests for API endpoints
3. Database testing with test fixtures
4. Performance and load testing scripts
5. Test configuration files
6. Mock data and factories
7. CI/CD test automation
8. Test documentation

For each test file, provide:
- Proper test structure and organization
- Comprehensive test coverage
- Both positive and negative test cases
- Proper assertions and error handling
- Test data management
- Clear documentation

Output as a structured JSON with file paths, content, and descriptions for industrial deployment.""")
        ])
        
        # New prompt for generating specific test code
        self.testing_code_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert Testing QA Engineer capable of generating specific test files and configurations.
Your goal is to generate the content for a single test file based on the provided requirements and context.
Ensure the generated code is syntactically correct, follows best practices for the specified language and framework,
and addresses the given test type (unit, integration, performance, config, etc.).

Output the content as a raw string without any JSON or markdown wrappers, unless the content itself is a JSON/markdown file.
For Python, use `pytest`. For JavaScript/TypeScript, use `Jest`. For Java, use `JUnit 5`.
"""),
            ("human", """Generate the content for a {file_name} file.

Context:
- Domain: {domain}
- Language: {language}
- Framework: {framework}
- Scale: {scale}
- Features: {features}
- Test Type: {test_type}
- File Path: {file_path}
- Description: {description}
- Additional Details: {additional_details}

Generate the content for this file.
""")
        ])
        
        logger.info("Testing QA Agent initialized with LLM-powered generation")
    
    def generate_testing_infrastructure(self, 
                                      domain: str,
                                      language: str,
                                      framework: str,
                                      scale: str,
                                      features: Set[str],
                                      additional_requirements: str = "") -> Dict[str, Any]:
        """Generate comprehensive testing infrastructure using LLM."""
        
        start_time = time.time()
        
        try:
            logger.info(f"Generating LLM-powered testing infrastructure for {domain}")
            
            # Prepare context for LLM
            context = {
                "domain": domain,
                "language": language,
                "framework": framework,
                "scale": scale,
                "features": ", ".join(features),
                "additional_requirements": additional_requirements or "Standard testing practices"
            }
            
            # Generate testing infrastructure using LLM
            chain = self.testing_prompt | self.llm
            response = chain.invoke(context)
            
            # Parse LLM response
            try:
                if hasattr(response, 'content'):
                    content = response.content
                else:
                    content = str(response)
                
                # Extract JSON from response
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                
                if json_start != -1 and json_end > json_start:
                    json_content = content[json_start:json_end]
                    parsed_response = json.loads(json_content)
                else:
                    # Fallback: Create structured response
                    parsed_response = self._create_fallback_testing_structure(context)
                
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"Failed to parse LLM response as JSON: {e}")
                parsed_response = self._create_fallback_testing_structure(context)
            
            # Save generated files
            saved_files = []
            if "files" in parsed_response:
                for file_info in parsed_response["files"]:
                    file_path = os.path.join(self.output_dir, file_info["path"])
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(file_info["content"])
                    
                    saved_files.append({
                        "name": file_info["name"],
                        "path": file_info["path"],
                        "type": file_info.get("type", "test"),
                        "size": len(file_info["content"]),
                        "description": file_info.get("description", "")
                    })
            
            execution_time = time.time() - start_time
            
            # Update memory with generation details
            self.memory.add_interaction({
                "agent": self.agent_name,
                "action": "generate_testing_infrastructure",
                "domain": domain,
                "language": language,
                "framework": framework,
                "files_generated": len(saved_files),
                "execution_time": execution_time
            })
            
            return {
                "status": "success",
                "files": saved_files,
                "execution_time": execution_time,
                "summary": {
                    "files_count": len(saved_files),
                    "test_types": self._extract_test_types(saved_files),
                    "coverage_areas": self._extract_coverage_areas(saved_files),
                    "framework_specific": language
                },
                "cost_optimization": {
                    "tokens_used": self._estimate_tokens_used(content),
                    "generation_method": "LLM-powered",
                    "efficiency_score": "high"
                }
            }
            
        except Exception as e:
            logger.error(f"Testing infrastructure generation failed: {str(e)}")
            return {
                "status": "error", 
                "error": str(e),
                "execution_time": time.time() - start_time
            }
    
    def _create_fallback_testing_structure(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create fallback testing structure when LLM parsing fails."""
        
        language = context["language"].lower()
        framework = context["framework"].lower()
        
        if language == "python":
            return self._create_python_testing_structure(context)
        elif language in ["javascript", "typescript", "node.js"]:
            return self._create_javascript_testing_structure(context)
        elif language == "java":
            return self._create_java_testing_structure(context)
        else:
            return self._create_generic_testing_structure(context)
    
    def _create_python_testing_structure(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create Python-specific testing structure using LLM."""
        domain = context["domain"]
        language = context["language"]
        framework = context["framework"]
        scale = context["scale"]
        features = context["features"]
        
        files_to_generate = [
            {
                "name": "pytest.ini",
                "path": "pytest.ini",
                "type": "config",
                "description": "Pytest configuration file",
                "additional_details": "Includes minversion, addopts for coverage, testpaths, markers, and naming conventions."
            },
            {
                "name": "conftest.py",
                "path": "tests/conftest.py",
                "type": "fixture_config",
                "description": "Pytest fixtures and configuration",
                "additional_details": "Includes session-scoped fixtures for database, API mocking, and common utilities."
            },
            {
                "name": "test_models.py",
                "path": f"tests/unit/{domain.lower()}_app/test_models.py",
                "type": "unit_test",
                "description": f"Unit tests for {domain} models",
                "additional_details": "Tests model creation, validation, and relationships. Includes positive and negative cases."
            },
            {
                "name": "test_api.py",
                "path": f"tests/integration/{domain.lower()}_app/test_api.py",
                "type": "integration_test",
                "description": f"Integration tests for {domain} API endpoints",
                "additional_details": "Tests API CRUD operations, authentication, and error handling. Uses mocked external services if necessary."
            },
            {
                "name": "test_performance.py",
                "path": f"tests/performance/{domain.lower()}_app/test_performance.py",
                "type": "performance_test",
                "description": f"Performance tests for {domain} application",
                "additional_details": "Uses locust or similar for load testing key endpoints, measuring response times and throughput."
            }
        ]
        
        generated_files = []
        for file_info in files_to_generate:
            prompt_context = {
                "file_name": file_info["name"],
                "domain": domain,
                "language": language,
                "framework": framework,
                "scale": scale,
                "features": features,
                "test_type": file_info["type"],
                "file_path": file_info["path"],
                "description": file_info["description"],
                "additional_details": file_info["additional_details"]
            }
            chain = self.testing_code_prompt | self.llm
            response = chain.invoke(prompt_context)
            
            generated_content = response.content if hasattr(response, 'content') else str(response)
            
            generated_files.append({
                "name": file_info["name"],
                "path": file_info["path"],
                "type": file_info["type"],
                "description": file_info["description"],
                "content": generated_content
            })
            
        return {"files": generated_files}
    
    def _create_javascript_testing_structure(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create JavaScript/Node.js testing structure using LLM."""
        domain = context["domain"]
        language = context["language"]
        framework = context["framework"]
        scale = context["scale"]
        features = context["features"]
        
        files_to_generate = [
            {
                "name": "jest.config.js",
                "path": "jest.config.js",
                "type": "config",
                "description": "Jest configuration file",
                "additional_details": "Includes test environment, coverage settings, and test match patterns."
            },
            {
                "name": "setup.js",
                "path": "tests/setup.js",
                "type": "fixture_config",
                "description": "Test setup and teardown for database connections (e.g., MongoDB memory server)",
                "additional_details": "Sets up and tears down mock database for isolated tests."
            },
            {
                "name": "user.test.js",
                "path": f"tests/unit/{domain.lower()}_app/user.test.js",
                "type": "unit_test",
                "description": f"Unit tests for {domain} user model",
                "additional_details": "Tests user creation, password hashing, and validation."
            },
            {
                "name": "api.test.js",
                "path": f"tests/integration/{domain.lower()}_app/api.test.js",
                "type": "integration_test",
                "description": f"Integration tests for {domain} API routes",
                "additional_details": "Tests API endpoints for user management (CRUD) with valid and invalid data."
            }
        ]
        
        generated_files = []
        for file_info in files_to_generate:
            prompt_context = {
                "file_name": file_info["name"],
                "domain": domain,
                "language": language,
                "framework": framework,
                "scale": scale,
                "features": features,
                "test_type": file_info["type"],
                "file_path": file_info["path"],
                "description": file_info["description"],
                "additional_details": file_info["additional_details"]
            }
            chain = self.testing_code_prompt | self.llm
            response = chain.invoke(prompt_context)
            
            generated_content = response.content if hasattr(response, 'content') else str(response)
            
            generated_files.append({
                "name": file_info["name"],
                "path": file_info["path"],
                "type": file_info["type"],
                "description": file_info["description"],
                "content": generated_content
            })
            
        return {"files": generated_files}
    
    def _create_java_testing_structure(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create Java testing structure using LLM."""
        domain = context["domain"]
        language = context["language"]
        framework = context["framework"]
        scale = context["scale"]
        features = context["features"]
        
        files_to_generate = [
            {
                "name": "pom.xml",
                "path": "pom.xml",
                "type": "config",
                "description": "Maven Project Object Model for dependencies and build configuration",
                "additional_details": "Includes JUnit 5, Mockito, and other testing dependencies."
            },
            {
                "name": "UserTest.java",
                "path": f"src/test/java/com/example/{domain.lower()}/model/UserTest.java",
                "type": "unit_test",
                "description": f"JUnit tests for {domain} User model",
                "additional_details": "Tests user creation, validation, and password hashing using JUnit 5 and Mockito."
            },
            {
                "name": "ApiServiceTest.java",
                "path": f"src/test/java/com/example/{domain.lower()}/service/ApiServiceTest.java",
                "type": "integration_test",
                "description": f"Integration tests for {domain} API services",
                "additional_details": "Tests API endpoint interactions and service layer logic."
            }
        ]
        
        generated_files = []
        for file_info in files_to_generate:
            prompt_context = {
                "file_name": file_info["name"],
                "domain": domain,
                "language": language,
                "framework": framework,
                "scale": scale,
                "features": features,
                "test_type": file_info["type"],
                "file_path": file_info["path"],
                "description": file_info["description"],
                "additional_details": file_info["additional_details"]
            }
            chain = self.testing_code_prompt | self.llm
            response = chain.invoke(prompt_context)
            
            generated_content = response.content if hasattr(response, 'content') else str(response)
            
            generated_files.append({
                "name": file_info["name"],
                "path": file_info["path"],
                "type": file_info["type"],
                "description": file_info["description"],
                "content": generated_content
            })
            
        return {"files": generated_files}
    
    def _create_generic_testing_structure(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create generic testing structure for other languages using LLM."""
        domain = context["domain"]
        language = context["language"]
        framework = context["framework"]
        scale = context["scale"]
        features = context["features"]
        
        files_to_generate = [
            {
                "name": "README.md",
                "path": "tests/README.md",
                "type": "documentation",
                "description": "Testing documentation for generic projects",
                "additional_details": "Provides an overview of the testing suite, structure, running instructions, and coverage requirements."
            },
            {
                "name": "CONTRIBUTING.md",
                "path": "tests/CONTRIBUTING.md",
                "type": "documentation",
                "description": "Contribution guidelines for tests",
                "additional_details": "Explains how to add new tests, run existing ones, and maintain the test suite."
            }
        ]
        
        generated_files = []
        for file_info in files_to_generate:
            prompt_context = {
                "file_name": file_info["name"],
                "domain": domain,
                "language": language,
                "framework": framework,
                "scale": scale,
                "features": features,
                "test_type": file_info["type"],
                "file_path": file_info["path"],
                "description": file_info["description"],
                "additional_details": file_info["additional_details"]
            }
            chain = self.testing_code_prompt | self.llm
            response = chain.invoke(prompt_context)
            
            generated_content = response.content if hasattr(response, 'content') else str(response)
            
            generated_files.append({
                "name": file_info["name"],
                "path": file_info["path"],
                "type": file_info["type"],
                "description": file_info["description"],
                "content": generated_content
            })
            
        return {"files": generated_files}
    
    def _extract_test_types(self, files: List[Dict[str, Any]]) -> List[str]:
        """Extract test types from generated files."""
        test_types = set()
        for file_info in files:
            if "type" in file_info:
                test_types.add(file_info["type"])
        return list(test_types)
    
    def _extract_coverage_areas(self, files: List[Dict[str, Any]]) -> List[str]:
        """Extract coverage areas from generated files."""
        coverage_areas = []
        for file_info in files:
            if "test" in file_info.get("type", ""):
                if "unit" in file_info["path"]:
                    coverage_areas.append("unit_testing")
                elif "integration" in file_info["path"]:
                    coverage_areas.append("integration_testing")
                elif "performance" in file_info["path"]:
                    coverage_areas.append("performance_testing")
        return list(set(coverage_areas))
    
    def _estimate_tokens_used(self, content: str) -> int:
        """Estimate tokens used in generation."""
        # Rough estimation: ~4 characters per token
        return len(content) // 4 

    def run(self, context: Dict[str, Any]) -> CodeGenerationOutput:
        """
        Generates unit tests for a single work item based on its implementation.
        """
        work_item: WorkItem = context["work_item"]
        tech_stack = context.get("tech_stack", {})
        language = tech_stack.get("language", "python")
        framework = tech_stack.get("backend_framework", "fastapi")
        generated_code = context.get("generated_code", [])

        logger.info(f"TestingQAAgent starting tests for work item: {work_item['id']}")

        prompt = self._create_work_item_test_prompt(work_item, language, framework, generated_code)
        
        response = self.llm.invoke(prompt)
        content = response.content if hasattr(response, 'content') else str(response)

        generated_files = parse_llm_output_into_files(content)

        return CodeGenerationOutput(
            generated_files=[FileOutput(**f) for f in generated_files],
            summary=f"Generated {len(generated_files)} test files for work item {work_item['id']}."
        )

    def _create_work_item_test_prompt(self, work_item: Dict[str, Any], language: str, framework: str, generated_code: List[Dict[str, Any]]) -> str:
        
        code_str = ""
        for file_data in generated_code:
            code_str += f"### FILE: {file_data['path']}\n```{file_data.get('file_type', '')}\n{file_data['content']}\n```\n\n"

        return f"""
        You are an expert Testing QA Engineer for {language} using the {framework} framework.
        Your task is to write comprehensive unit tests for the provided code, ensuring all acceptance criteria for the work item are met.

        **Work Item to Test: {work_item['id']}**
        - **Description:** {work_item['description']}
        - **Acceptance Criteria:**
        {chr(10).join(f'  - {c}' for c in work_item['acceptance_criteria'])}

        **Code to be Tested:**
        ```
        {code_str}
        ```

        **Instructions:**
        1. Write unit tests that thoroughly cover the provided code.
        2. Specifically, create tests that validate EACH acceptance criterion listed above.
        3. Use standard testing libraries for the ecosystem (e.g., `pytest` for Python, `Jest` for Node.js/TypeScript).
        4. Place the test files in an appropriate directory (e.g., a `tests/` directory at the root or alongside the source code).
        5. Your output must be in the multi-file format.

        CRITICAL OUTPUT FORMAT - FOLLOW EXACTLY:
        ### FILE: path/to/your/test_file.ext
        ```filetype
        # Complete test file content here
        ```
        """ 