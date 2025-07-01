import json
import os
import re
import time
from typing import Dict, Any, Optional, List
from pathlib import Path
from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.retrievers import BaseRetriever
from tools.code_execution_tool import CodeExecutionTool
import monitoring
from datetime import datetime

from .base_agent import BaseAgent
from models.data_contracts import TestValidationOutput, TestResult

# Enhanced memory and RAG imports
from enhanced_memory_manager import create_memory_manager, EnhancedSharedProjectMemory
from rag_manager import get_rag_manager

class TestValidationAgent(BaseAgent):
    """
    Enhanced Test Validation Agent with comprehensive analysis of test execution results
    and code coverage in a single structured step.
    """
    
    def __init__(self, llm: BaseLanguageModel, memory, temperature: float,
                 code_execution_tool: CodeExecutionTool, 
                 rag_retriever: Optional[BaseRetriever] = None, 
                 message_bus=None):
        
        super().__init__(
            llm=llm,
            memory=memory,
            agent_name="Test Validation Agent",
            temperature=temperature,
            rag_retriever=rag_retriever
        )
        
        self.code_execution_tool = code_execution_tool
        self.message_bus = message_bus
        
        # Initialize enhanced memory (inherits from BaseAgent)
        self._init_enhanced_memory()
        
        # Initialize RAG context
        self.rag_manager = get_rag_manager()
        if self.rag_manager:
            self.logger.info("RAG manager available for enhanced test validation")
        else:
            self.logger.warning("RAG manager not available - proceeding with basic test validation")
        
        # Maximum characters for different contexts
        self.max_context_chars = {
            "test_results": 12000,
            "coverage_report": 8000,
            "rag": 1200,
        }
        
        # Token optimization configurations
        self.max_tokens = 4096
        
        # Initialize token usage tracking
        self.token_metrics = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "api_calls": 0
        }
        
        # Initialize prompt templates
        self._initialize_prompt_templates()
    
    def _initialize_prompt_templates(self):
        """Initializes a single, comprehensive prompt for analyzing test results."""
        
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", 
             "You are a senior QA Engineer specializing in test result analysis and quality assessment. "
             "Your task is to analyze test execution results and coverage reports to provide a comprehensive "
             "assessment of test quality, coverage, and actionable recommendations."),
            ("human", 
             """
             # TEST VALIDATION TASK
             
             ## Test Framework: {framework}
             
             ## Test Execution Results
             ```
             {test_results}
             ```
             
             ## Coverage Report
             ```
             {coverage_report}
             ```
             
             ## Project Context
             {project_context}
             
             ## Best Practices and Examples
             {rag_context}
             
             # ANALYSIS INSTRUCTIONS
             
             Please analyze the test results and coverage report to provide a comprehensive assessment including:
             
             1. Test statistics summary (passed, failed, skipped tests)
             2. Overall test success rate and code coverage percentage
             3. Identification of critical failures or issues
             4. Assessment of coverage gaps and untested areas
             5. Quality assessment of the test suite
             6. Actionable recommendations for improving test coverage and quality
             
             # RESPONSE FORMAT
             
             Structure your analysis as JSON with the following fields:
             - passed: Number of tests that passed
             - failed: Number of tests that failed
             - skipped: Number of tests that were skipped
             - success_rate: The percentage of tests that passed (0-100)
             - coverage_percentage: The overall code coverage percentage (0-100)
             - summary: A concise summary of the test results
             - recommendations: List of actionable recommendations
             - issues: List of specific issues found in tests
             - coverage_gaps: List of areas with insufficient test coverage
             
             Ensure all numeric values are properly formatted as numbers, not strings.
             For success_rate and coverage_percentage, express as a number between 0 and 100.
             """
            )
        ])
        
        # Format instructions for clear JSON output
        self.format_instructions = """
        RESPONSE FORMAT:
        ```json
        {
            "passed": 42,
            "failed": 3,
            "skipped": 1,
            "success_rate": 91.3,
            "coverage_percentage": 78.5,
            "summary": "The test suite shows good overall success rate...",
            "recommendations": [
                "Add more tests for the X module...",
                "Improve error handling tests..."
            ],
            "issues": [
                {
                    "location": "test_module.py",
                    "description": "Failing authentication tests",
                    "severity": "high"
                }
            ],
            "coverage_gaps": [
                {
                    "module": "payment_processor.py",
                    "lines": "45-60",
                    "description": "Error handling code not tested"
                }
            ]
        }
        ```
        
        Return ONLY a valid JSON object with these fields, no additional text.
        """

    def run(self, project_dir: str, test_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Runs tests, code coverage, and analyzes the results in a single structured step.
        
        Args:
            project_dir: Directory containing the project code
            test_dir: Optional directory containing tests (if different from project_dir/tests)
            
        Returns:
            Dict[str, Any]: Validation results conforming to TestValidationOutput schema
        """
        with monitoring.agent_trace_span(self.agent_name, "test_validation"):
            self.log_info(f"Starting test validation for project in {project_dir}")
            start_time = time.time()
            
            try:
                # Determine test directory if not provided
                if not test_dir:
                    test_dir = self._find_test_directory(project_dir)
                    self.log_info(f"Using test directory: {test_dir}")
                
                # Detect framework based on project structure
                framework = self._detect_test_framework(project_dir, test_dir)
                self.log_info(f"Detected test framework: {framework}")
                
                # Execute tests with token-optimized results capture
                self.log_info("Executing tests...")
                test_results = self._execute_tests(project_dir, test_dir, framework)
                
                # Generate coverage report if possible
                self.log_info("Generating coverage report...")
                coverage_report = self._execute_coverage(project_dir, test_dir, framework)
                
                # Get project context (structure, organization)
                self.log_info("Gathering project context...")
                project_context = self._get_optimized_project_context(project_dir)
                
                # Get RAG context for improved analysis
                self.log_info("Retrieving best practices context...")
                rag_context = self._get_rag_context(framework)
                
                # Apply token optimization to test results and coverage report
                optimized_results = self._truncate_test_results(test_results)
                optimized_coverage = self._truncate_coverage_report(coverage_report)
                
                # Use slightly lower temperature for analytical task
                adjusted_temp = max(0.1, self.default_temperature - 0.05)
                
                # Use binding pattern for temperature and tokens
                llm_with_temp = self.llm.bind(
                    temperature=adjusted_temp,
                    max_tokens=self.max_tokens
                )
                
                # Add monitoring context
                invoke_config = {
                    "agent_context": f"{self.agent_name}:test_analysis",
                    "temperature_used": adjusted_temp
                }
                
                self.log_info(f"Analyzing test results with temperature {adjusted_temp}")
                
                # Make a single LLM call with the comprehensive prompt
                prompt = self.prompt_template.format(
                    framework=framework,
                    test_results=optimized_results,
                    coverage_report=optimized_coverage,
                    project_context=project_context,
                    rag_context=rag_context
                ) + self.format_instructions
                
                # Invoke LLM for analysis
                response = llm_with_temp.invoke(prompt, config=invoke_config)
                content = response.content if hasattr(response, 'content') else str(response)
                
                # Try to extract JSON from response
                try:
                    # Find JSON in the response
                    json_match = re.search(r'```json\s*([\s\S]*?)\s*```|`([\s\S]*?)`|\{[\s\S]*\}', content)
                    if json_match:
                        json_str = json_match.group(1) or json_match.group(2) or json_match.group(0)
                        analysis_result = json.loads(json_str)
                    else:
                        # Try direct parsing if no explicit JSON block
                        analysis_result = json.loads(content)
                    
                    # Update token metrics if available
                    if hasattr(response, 'llm_output') and response.llm_output:
                        token_usage = response.llm_output.get('token_usage', {})
                        self._update_token_metrics(token_usage)
                    
                    # Add execution metrics
                    execution_time = time.time() - start_time
                    analysis_result["execution_time"] = execution_time
                    analysis_result["timestamp"] = datetime.now().isoformat()
                    analysis_result["status"] = "success"
                    
                    # Transform the analysis result to match TestValidationOutput model
                    # Create TestResult objects from the analysis
                    results = []
                    passed_count = analysis_result.get("passed", 0)
                    failed_count = analysis_result.get("failed", 0)
                    skipped_count = analysis_result.get("skipped", 0)
                    
                    # Create synthetic test results if we have counts
                    for i in range(passed_count):
                        results.append(TestResult(
                            test_case_id=f"test_{i+1}",
                            passed=True,
                            output="Test passed"
                        ))
                    for i in range(failed_count):
                        results.append(TestResult(
                            test_case_id=f"failed_test_{i+1}",
                            passed=False,
                            output="Test failed"
                        ))
                    for i in range(skipped_count):
                        results.append(TestResult(
                            test_case_id=f"skipped_test_{i+1}",
                            passed=False,
                            output="Test skipped"
                        ))
                    
                    # Create the properly formatted data for TestValidationOutput
                    validation_data = {
                        "results": results,
                        "coverage": analysis_result.get("coverage_percentage", 0.0),
                        "summary": analysis_result.get("summary", "Test validation completed")
                    }
                    
                    # Validate with Pydantic model
                    validated_output = TestValidationOutput(**validation_data)
                    
                    # Add the extra fields back for logging and memory storage
                    result_dict = validated_output.dict()
                    result_dict["passed"] = passed_count
                    result_dict["failed"] = failed_count
                    result_dict["skipped"] = skipped_count
                    result_dict["success_rate"] = analysis_result.get("success_rate", 0.0)
                    result_dict["coverage_percentage"] = analysis_result.get("coverage_percentage", 0.0)
                    result_dict["execution_time"] = execution_time
                    result_dict["timestamp"] = analysis_result["timestamp"]
                    result_dict["status"] = analysis_result["status"]
                    result_dict["recommendations"] = analysis_result.get("recommendations", [])
                    result_dict["issues"] = analysis_result.get("issues", [])
                    
                    # Store activity in memory
                    self.memory.store_agent_activity(
                        agent_name=self.agent_name,
                        activity_type="test_analysis",
                        prompt="[Test validation prompt]",
                        response="[Test validation response]",
                        metadata={
                            "framework": framework,
                            "test_count": passed_count + failed_count + skipped_count,
                            "pass_rate": result_dict["success_rate"],
                            "coverage": result_dict["coverage_percentage"],
                            "execution_time": execution_time
                        }
                    )
                    
                    # Store result in enhanced memory for cross-tool access
                    self.enhanced_set("test_validation_result", result_dict, context="test_validation")
                    self.store_cross_tool_data("validation_metrics", {
                        "success_rate": result_dict["success_rate"],
                        "coverage_percentage": result_dict["coverage_percentage"],
                        "passed": result_dict["passed"],
                        "failed": result_dict["failed"],
                        "skipped": result_dict["skipped"],
                        "framework": framework
                    }, f"Test validation metrics for {framework}")
                    
                    # Publish test validation completion message
                    if hasattr(self, 'message_bus') and self.message_bus:
                        self.message_bus.publish("test.validation.complete", {
                            "agent": self.agent_name,
                            "status": "completed",
                            "framework": framework,
                            "metrics": {
                                "success_rate": result_dict["success_rate"],
                                "coverage_percentage": result_dict["coverage_percentage"],
                                "total_tests": passed_count + failed_count + skipped_count,
                                "execution_time": execution_time
                            }
                        })
                    
                    self.log_success(
                        f"Test validation completed in {execution_time:.2f}s " +
                        f"with {result_dict['success_rate']:.1f}% success rate and " +
                        f"{result_dict['coverage_percentage']:.1f}% coverage"
                    )
                    
                    return result_dict
                    
                except Exception as json_e:
                    self.log_error(f"Failed to parse analysis result: {str(json_e)}")
                    return self._create_default_output(
                        error_message=f"Failed to parse analysis result: {str(json_e)}",
                        execution_time=time.time() - start_time,
                        framework=framework
                    )
                
            except Exception as e:
                execution_time = time.time() - start_time
                self.log_error(f"Test validation failed: {str(e)}")
                return self._create_default_output(
                    error_message=f"Test validation failed: {str(e)}",
                    execution_time=execution_time
                )
    
    def _find_test_directory(self, project_dir: str) -> str:
        """Find the test directory within the project."""
        # Common test directory patterns
        test_dirs = ['tests', 'test', 'src/tests', 'src/test', '__tests__']
        
        for test_dir in test_dirs:
            full_path = os.path.join(project_dir, test_dir)
            if os.path.isdir(full_path):
                return full_path
        
        # Default to tests directory if none found
        default_dir = os.path.join(project_dir, 'tests')
        os.makedirs(default_dir, exist_ok=True)
        return default_dir
    
    def _detect_test_framework(self, project_dir: str, test_dir: str) -> str:
        """Detect test framework based on project structure with minimal file scanning."""
        # Quick checks based on configuration files
        if os.path.exists(os.path.join(project_dir, 'pytest.ini')):
            return 'pytest'
        if os.path.exists(os.path.join(project_dir, 'jest.config.js')):
            return 'jest'
        if os.path.exists(os.path.join(project_dir, 'karma.conf.js')):
            return 'mocha'
        
        # Check package.json for JS frameworks
        package_json = os.path.join(project_dir, 'package.json')
        if os.path.exists(package_json):
            try:
                with open(package_json, 'r') as f:
                    data = json.load(f)
                    deps = {**data.get('dependencies', {}), **data.get('devDependencies', {})}
                    if 'jest' in deps:
                        return 'jest'
                    if 'mocha' in deps:
                        return 'mocha'
            except:
                pass
                
        # Check for Java frameworks
        pom_xml = os.path.join(project_dir, 'pom.xml')
        if os.path.exists(pom_xml):
            return 'junit'
            
        # Check by examining test files (limited number to save tokens)
        if os.path.exists(test_dir):
            file_count = 0
            for root, _, files in os.walk(test_dir):
                for file in files:
                    if file_count >= 5:  # Limit file checks
                        break
                        
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read(1000)  # Read just the beginning
                            if 'import pytest' in content or 'from pytest' in content:
                                return 'pytest'
                            if 'import django' in content and 'TestCase' in content:
                                return 'django'
                                
                    elif file.endswith('.js') or file.endswith('.ts'):
                        file_path = os.path.join(root, file)
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read(1000)
                            if 'describe(' in content and 'it(' in content:
                                if 'expect(' in content and 'toBe(' in content:
                                    return 'jest'
                                else:
                                    return 'mocha'
                                    
                    elif file.endswith('.java'):
                        return 'junit'
                        
                    file_count += 1
        
        # Default to pytest as fallback
        return 'pytest'
    
    def _execute_tests(self, project_dir: str, test_dir: str, framework: str) -> str:
        """Execute tests with the appropriate command based on framework."""
        self.log_info(f"Executing {framework} tests in {test_dir}")
        
        # Create appropriate test command based on framework
        if framework == 'pytest':
            command = f"cd {project_dir} && python -m pytest {test_dir} -v"
        elif framework == 'django':
            command = f"cd {project_dir} && python manage.py test"
        elif framework == 'jest':
            command = f"cd {project_dir} && npx jest --verbose"
        elif framework == 'mocha':
            command = f"cd {project_dir} && npx mocha"
        elif framework == 'junit':
            command = f"cd {project_dir} && mvn test"
        else:
            # Default fallback
            command = f"cd {project_dir} && python -m pytest {test_dir}"
        
        try:
            # Execute the test command with the tool
            result = self.code_execution_tool.execute_command(command, working_dir=project_dir)
            self.log_info(f"Test execution completed, output length: {len(result.get('output', ''))}")
            return result.get('output', 'No test output received')
        except Exception as e:
            self.log_warning(f"Error executing tests: {str(e)}")
            return f"Error executing tests: {str(e)}"
    
    def _execute_coverage(self, project_dir: str, test_dir: str, framework: str) -> str:
        """Execute coverage analysis with the appropriate command based on framework."""
        self.log_info(f"Generating coverage report for {framework}")
        
        # Create appropriate coverage command based on framework
        if framework == 'pytest':
            command = f"cd {project_dir} && python -m pytest {test_dir} --cov=. --cov-report term"
        elif framework == 'django':
            command = f"cd {project_dir} && coverage run manage.py test && coverage report"
        elif framework == 'jest':
            command = f"cd {project_dir} && npx jest --coverage"
        elif framework == 'mocha':
            command = f"cd {project_dir} && npx nyc mocha"
        elif framework == 'junit':
            command = f"cd {project_dir} && mvn test jacoco:report && cat target/site/jacoco/index.html"
        else:
            # Default fallback for pytest
            command = f"cd {project_dir} && python -m pytest {test_dir} --cov=."
        
        try:
            # Execute the coverage command
            result = self.code_execution_tool.execute_command(command, working_dir=project_dir)
            self.log_info(f"Coverage report generated, length: {len(result.get('output', ''))}")
            return result.get('output', 'No coverage data received')
        except Exception as e:
            self.log_warning(f"Error generating coverage report: {str(e)}")
            return f"Coverage report unavailable: {str(e)}"
    
    def _get_optimized_project_context(self, project_dir: str) -> str:
        """Get optimized project context with minimal file scanning."""
        self.log_info("Generating optimized project context")
        
        # Limit the depth and number of files to scan
        max_dirs = 10
        max_files_per_dir = 5
        context_parts = []
        dir_count = 0
        
        try:
            # Get project structure with limits
            for root, dirs, files in os.walk(project_dir):
                if dir_count >= max_dirs:
                    break
                
                # Skip hidden directories and common non-code directories
                dirs[:] = [d for d in dirs if not d.startswith('.') and 
                         d not in ['node_modules', 'venv', '.git', '__pycache__', '.pytest_cache']]
                
                # Skip if too deep
                rel_path = os.path.relpath(root, project_dir)
                if rel_path.count(os.sep) > 2:
                    continue
                    
                # Get files with limits
                file_samples = [f for f in files if not f.startswith('.') and 
                              f.endswith(('.py', '.js', '.ts', '.java', '.cs', '.rb'))][:max_files_per_dir]
                
                if file_samples:
                    context_parts.append(f"Directory: {rel_path}")
                    context_parts.append(f"Files: {', '.join(file_samples)}")
                    dir_count += 1
            
            # Ensure we don't exceed token limits
            result = "\n".join(context_parts)
            if len(result) > 1000:
                result = result[:950] + "...[truncated]"
                
            return result
            
        except Exception as e:
            self.log_warning(f"Error generating project context: {str(e)}")
            return "Project context unavailable due to error"
    
    def _get_rag_context(self, framework: str) -> str:
        """Get RAG context for test validation best practices."""
        if not self.rag_retriever:
            return ""
            
        default_context = {
            "pytest": "Look for test coverage of core functionality. Ensure test isolation with fixtures.",
            "jest": "Check for component rendering tests and proper mocking of dependencies.",
            "mocha": "Verify proper describe/it nesting and chai assertions.",
            "junit": "Ensure proper test class organization and use of annotations."
        }
            
        try:
            query = f"{framework} test quality best practices code coverage"
            docs = self.rag_retriever.get_relevant_documents(query, limit=2)
            
            if not docs:
                return default_context.get(framework, "")
                
            context_parts = []
            total_chars = 0
            
            for doc in docs:
                content = doc.page_content
                
                if total_chars + len(content) > self.max_context_chars["rag"]:
                    chars_left = self.max_context_chars["rag"] - total_chars
                    if chars_left > 100:
                        context_parts.append(content[:chars_left] + "... [truncated]")
                    break
                
                context_parts.append(content)
                total_chars += len(content)
            
            result = "\n\n".join(context_parts)
            return result if result else default_context.get(framework, "")
            
        except Exception as e:
            self.log_warning(f"Error retrieving RAG context: {str(e)}")
            return default_context.get(framework, "")
    
    def _truncate_test_results(self, test_results: str) -> str:
        """Intelligently truncate test results to fit within token limits."""
        if not test_results:
            return ""
            
        # If already within limits, return as is
        if len(test_results) <= self.max_context_chars["test_results"]:
            return test_results
            
        # Try to identify and preserve the summary section (usually at beginning or end)
        lines = test_results.split('\n')
        summary_section = []
        details_section = []
        errors_section = []
        
        # Extract summary (usually contains test counts and overall stats)
        in_summary = True
        in_errors = False
        
        for line in lines:
            # Detect transitions between sections
            if "FAILURES" in line or "FAILED TESTS" in line or "ERROR" in line:
                in_summary = False
                in_errors = True
                errors_section.append(line)
            elif in_summary and ('test' in line.lower() or 'pass' in line.lower() or 
                              'fail' in line.lower() or 'seconds' in line.lower()):
                summary_section.append(line)
            elif in_errors:
                errors_section.append(line)
            else:
                details_section.append(line)
        
        # Prioritize sections: full summary + full errors + truncated details
        result_parts = []
        chars_used = 0
        
        # Add summary section first
        summary_text = '\n'.join(summary_section)
        result_parts.append(summary_text)
        chars_used += len(summary_text)
        
        # Add errors section next (highest priority)
        if errors_section:
            error_text = '\n'.join(errors_section)
            error_chars = len(error_text)
            
            # If errors section is too large, truncate it
            if chars_used + error_chars > self.max_context_chars["test_results"]:
                chars_left = self.max_context_chars["test_results"] - chars_used - 50
                error_text = error_text[:chars_left] + "\n... [error details truncated] ..."
            
            result_parts.append(error_text)
            chars_used += len(error_text)
        
        # Use remaining space for details
        if details_section and chars_used < self.max_context_chars["test_results"]:
            details_text = '\n'.join(details_section)
            if chars_used + len(details_text) > self.max_context_chars["test_results"]:
                chars_left = self.max_context_chars["test_results"] - chars_used - 50
                details_text = details_text[:chars_left] + "\n... [details truncated] ..."
            
            result_parts.append(details_text)
        
        result = '\n\n'.join(result_parts)
        self.log_info(f"Truncated test results from {len(test_results)} to {len(result)} characters")
        return result
    
    def _truncate_coverage_report(self, coverage_report: str) -> str:
        """Intelligently truncate coverage report to fit within token limits."""
        if not coverage_report:
            return ""
            
        # If already within limits, return as is
        if len(coverage_report) <= self.max_context_chars["coverage_report"]:
            return coverage_report
            
        # Extract and prioritize important parts
        lines = coverage_report.split('\n')
        summary_lines = []
        missing_lines = []
        details_lines = []
        
        # Identify different sections
        in_summary = True
        in_missing = False
        
        for line in lines:
            line_lower = line.lower()
            # Detect summary section
            if 'missing' in line_lower or 'uncovered' in line_lower:
                in_summary = False
                in_missing = True
                missing_lines.append(line)
            elif in_summary and any(x in line_lower for x in ['total', 'coverage', '%', 'percent']):
                summary_lines.append(line)
            elif in_missing:
                missing_lines.append(line)
            else:
                details_lines.append(line)
        
        # Prioritize sections: summary + missing lines + partial details
        result_parts = []
        chars_used = 0
        
        # Add summary section first
        summary_text = '\n'.join(summary_lines)
        result_parts.append(summary_text)
        chars_used += len(summary_text)
        
        # Add missing lines section next (highest priority for coverage analysis)
        if missing_lines:
            missing_text = '\n'.join(missing_lines)
            missing_chars = len(missing_text)
            
            if chars_used + missing_chars > self.max_context_chars["coverage_report"]:
                chars_left = self.max_context_chars["coverage_report"] - chars_used - 50
                missing_text = missing_text[:chars_left] + "\n... [missing lines truncated] ..."
            
            result_parts.append(missing_text)
            chars_used += len(missing_text)
        
        # Add details with remaining space
        if details_lines and chars_used < self.max_context_chars["coverage_report"]:
            details_text = '\n'.join(details_lines)
            if chars_used + len(details_text) > self.max_context_chars["coverage_report"]:
                chars_left = self.max_context_chars["coverage_report"] - chars_used - 50
                details_text = details_text[:chars_left] + "\n... [details truncated] ..."
            
            result_parts.append(details_text)
        
        result = '\n\n'.join(result_parts)
        self.log_info(f"Truncated coverage report from {len(coverage_report)} to {len(result)} characters")
        return result
    
    def get_default_response(self) -> Dict[str, Any]:
        """
        Returns a default response when the agent fails to execute properly.
        Required by BaseAgent abstract class.
        """
        return self._create_default_output(
            error_message="Test validation agent failed to execute",
            execution_time=0.0,
            framework="unknown"
        )

    def _update_token_metrics(self, usage: Dict[str, int]) -> None:
        """Update token usage metrics."""
        self.token_metrics["prompt_tokens"] += usage.get("prompt_tokens", 0)
        self.token_metrics["completion_tokens"] += usage.get("completion_tokens", 0)
        self.token_metrics["total_tokens"] += usage.get("total_tokens", 0)
        self.token_metrics["api_calls"] += 1
    
    def _create_default_output(self, error_message: str = None, execution_time: float = 0.0, 
                            framework: str = "unknown") -> Dict[str, Any]:
        """Create default output when analysis fails."""
        return TestValidationOutput(
            results=[],  # Empty list of TestResult objects
            coverage=0.0,  # Coverage percentage as float
            summary=error_message or "Test validation failed"
        ).dict()
