import json
import os
import re
from typing import Dict, Any, Optional, List, Tuple
from langchain_core.language_models import BaseLanguageModel
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.retrievers import BaseRetriever
from tools.code_execution_tool import CodeExecutionTool
import monitoring
from .base_agent import BaseAgent

class TestValidationAgent(BaseAgent):
    """Enhanced Test Validation Agent with multi-stage analysis, specialized test frameworks,
    and comprehensive quality assessment."""
    
    def __init__(self, llm: BaseLanguageModel, memory, code_execution_tool: CodeExecutionTool, 
                 rag_retriever: Optional[BaseRetriever] = None):
        super().__init__(
            llm=llm,
            memory=memory,
            agent_name="TestValidationAgent",
            temperature=0.1,  # Very low for factual analysis
            rag_retriever=rag_retriever
        )
        
        self.code_execution_tool = code_execution_tool
        
        # Initialize main prompt template
        self.prompt_template = PromptTemplate(
            template="""
            You are an expert Test Results Analyst and Quality Assurance specialist.
            Your task is to analyze test execution results and provide comprehensive assessment.

            **Test Execution Results:**
            {test_results}

            **Coverage Report:**
            {coverage_report}

            **Project Context:**
            {project_context}

            **Historical Test Data:**
            {historical_data}

            **Test Analysis:**
            {test_analysis}

            {format_instructions}

            Generate a JSON object with:
            {{
                "test_success_rate": "number - Percentage of tests that passed",
                "coverage_percentage": "number - Code coverage percentage",
                "tests_run": "number - Total tests executed",
                "tests_passed": "number - Tests that passed",
                "tests_failed": "number - Tests that failed",
                "overall_assessment": "string - 'Excellent', 'Good', 'Acceptable', 'Marginal', or 'Unacceptable'",
                "critical_issues": ["List of critical issues"],
                "failed_tests": [
                    {{

                        "test_name": "name of failed test",
                        "module": "module containing the test",
                        "failure_reason": "why the test failed",
                        "severity": "high|medium|low"
                    }}
                ],
                "uncovered_areas": ["List of code areas with insufficient coverage"],
                "test_quality_assessment": {{
                    "completeness": "high|medium|low - Do tests cover all major functionality",
                    "reliability": "high|medium|low - How consistently tests pass/fail",
                    "maintenance_score": "high|medium|low - How easy tests are to maintain",
                    "execution_time": "fast|moderate|slow - Test suite execution speed"
                }},
                "recommendations": [
                    {{
                        "area": "specific area to improve",
                        "recommendation": "what should be done",
                        "priority": "high|medium|low"
                    }}
                ],
                "summary": "Brief summary of test validation results"
            }}
            """,
            input_variables=["test_results", "coverage_report", "project_context", "historical_data", "test_analysis"],
            partial_variables={"format_instructions": self.json_parser.get_format_instructions()},
        )
        
        # Framework-specific test result analysis templates
        self.framework_templates = {
            "pytest": self._create_pytest_analysis_template(),
            "jest": self._create_jest_analysis_template(),
            "junit": self._create_junit_analysis_template(),
            "django": self._create_django_analysis_template(),
            "mocha": self._create_mocha_analysis_template()
        }
        
        # Coverage analysis template
        self.coverage_analysis_template = PromptTemplate(
            template="""
            You are an expert Test Coverage Analyst.
            Analyze the provided code coverage report to identify areas with insufficient coverage.

            **Coverage Report:**
            {coverage_report}

            **Project Structure:**
            {project_structure}

            {format_instructions}

            Generate a JSON object with:
            {{
                "overall_coverage_percentage": "number - overall coverage percentage",
                "module_coverage": [
                    {{
                        "module": "name of module",
                        "coverage_percentage": "number - percentage coverage",
                        "assessment": "good|moderate|poor"
                    }}
                ],
                "uncovered_code_areas": [
                    {{
                        "file": "file path",
                        "lines": "line ranges, e.g. 10-15, 30-35",
                        "function": "function/class name if applicable",
                        "importance": "high|medium|low - how critical this code is"
                    }}
                ],
                "coverage_trend": "improving|stable|declining",
                "critical_uncovered_areas": ["List of critical areas with no coverage"],
                "recommendations": ["List of specific recommendations to improve coverage"]
            }}
            """,
            input_variables=["coverage_report", "project_structure"],
            partial_variables={"format_instructions": self.json_parser.get_format_instructions()},
        )
        
        # Test quality assessment template
        self.test_quality_template = PromptTemplate(
            template="""
            You are an expert Test Quality Analyst.
            Analyze the test execution results and test code to assess test quality.

            **Test Execution Results:**
            {test_results}

            **Test Code Samples:**
            {test_code_samples}

            **Project Context:**
            {project_context}

            {format_instructions}

            Generate a JSON object with:
            {{
                "test_quality_score": "number (1-10) - overall test quality score",
                "test_structure_assessment": {{
                    "organization": "good|moderate|poor",
                    "naming_conventions": "good|moderate|poor",
                    "test_isolation": "good|moderate|poor",
                    "setup_teardown": "good|moderate|poor",
                    "assertion_quality": "good|moderate|poor"
                }},
                "test_effectiveness": {{
                    "boundary_testing": "good|moderate|poor",
                    "edge_case_coverage": "good|moderate|poor",
                    "negative_testing": "good|moderate|poor",
                    "mock_usage": "good|moderate|poor"
                }},
                "performance_metrics": {{
                    "average_test_time": "time in seconds",
                    "slowest_tests": ["list of slow tests"],
                    "resource_usage": "high|moderate|low"
                }},
                "flaky_tests": ["list of inconsistent tests"],
                "recommended_improvements": ["list of specific improvements"]
            }}
            """,
            input_variables=["test_results", "test_code_samples", "project_context"],
            partial_variables={"format_instructions": self.json_parser.get_format_instructions()},
        )
        
        # Test failure pattern analysis template
        self.failure_pattern_template = PromptTemplate(
            template="""
            You are an expert Test Failure Pattern Analyst.
            Analyze the failed tests to identify common patterns and root causes.

            **Failed Test Details:**
            {failed_tests}

            **Error Messages:**
            {error_messages}

            **Project Context:**
            {project_context}

            {format_instructions}

            Generate a JSON object with:
            {{
                "common_failure_patterns": [
                    {{
                        "pattern": "description of pattern",
                        "affected_tests": ["list of affected tests"],
                        "probable_cause": "description of likely cause",
                        "frequency": "number of occurrences"
                    }}
                ],
                "root_cause_categories": {{
                    "code_bugs": ["list of failures likely due to actual bugs"],
                    "environment_issues": ["list of failures due to environment"],
                    "test_code_issues": ["list of failures due to test implementation"],
                    "data_issues": ["list of failures due to test data problems"],
                    "timing_issues": ["list of failures due to race conditions/timing"]
                }},
                "severity_assessment": [
                    {{
                        "failure": "test name",
                        "severity": "critical|high|medium|low",
                        "impact": "description of business impact"
                    }}
                ],
                "recommendations": ["list of recommended actions"]
            }}
            """,
            input_variables=["failed_tests", "error_messages", "project_context"],
            partial_variables={"format_instructions": self.json_parser.get_format_instructions()},
        )

    def _create_pytest_analysis_template(self) -> PromptTemplate:
        """Create a template for analyzing pytest results"""
        return PromptTemplate(
            template="""
            You are an expert pytest Test Results Analyst.
            Analyze these pytest test results:

            **Test Results:**
            {test_results}

            {format_instructions}

            Generate a JSON object with:
            {{
                "tests_total": number,
                "tests_passed": number,
                "tests_failed": number,
                "tests_skipped": number,
                "execution_time": "time in seconds",
                "failed_tests": [
                    {{
                        "test_name": "name of test",
                        "file_path": "path to file",
                        "line_number": number,
                        "error_message": "error message",
                        "error_type": "assertion|exception|etc"
                    }}
                ],
                "warning_messages": ["list of warning messages"],
                "test_patterns": {{
                    "test_categories": ["unittest", "functional", "integration", "etc"],
                    "most_tested_modules": ["most frequently tested modules"]
                }}
            }}
            """,
            input_variables=["test_results"],
            partial_variables={"format_instructions": self.json_parser.get_format_instructions()},
        )
    
    def _create_jest_analysis_template(self) -> PromptTemplate:
        """Create a template for analyzing Jest results"""
        return PromptTemplate(
            template="""
            You are an expert Jest Test Results Analyst.
            Analyze these Jest test results:

            **Test Results:**
            {test_results}

            {format_instructions}

            Generate a JSON object with:
            {{
                "tests_total": number,
                "tests_passed": number,
                "tests_failed": number,
                "tests_skipped": number,
                "test_suites_total": number,
                "test_suites_passed": number,
                "test_suites_failed": number,
                "execution_time": "time in seconds",
                "failed_tests": [
                    {{
                        "test_name": "name of test",
                        "suite_name": "name of test suite",
                        "file_path": "path to file",
                        "error_message": "error message"
                    }}
                ],
                "snapshots": {{
                    "total": number,
                    "passed": number,
                    "failed": number,
                    "updated": number,
                    "added": number
                }}
            }}
            """,
            input_variables=["test_results"],
            partial_variables={"format_instructions": self.json_parser.get_format_instructions()},
        )
    
    def _create_junit_analysis_template(self) -> PromptTemplate:
        """Create a template for analyzing JUnit results"""
        return PromptTemplate(
            template="""
            You are an expert JUnit Test Results Analyst.
            Analyze these JUnit test results:

            **Test Results:**
            {test_results}

            {format_instructions}

            Generate a JSON object with:
            {{
                "tests_total": number,
                "tests_passed": number,
                "tests_failed": number,
                "tests_skipped": number,
                "test_classes_total": number,
                "execution_time": "time in seconds",
                "failed_tests": [
                    {{
                        "test_name": "name of test",
                        "class_name": "name of test class",
                        "error_message": "error message",
                        "error_type": "assertion|exception|etc"
                    }}
                ],
                "test_categories": ["list of test categories based on class names"]
            }}
            """,
            input_variables=["test_results"],
            partial_variables={"format_instructions": self.json_parser.get_format_instructions()},
        )
    
    def _create_django_analysis_template(self) -> PromptTemplate:
        """Create a template for analyzing Django test results"""
        return PromptTemplate(
            template="""
            You are an expert Django Test Results Analyst.
            Analyze these Django test results:

            **Test Results:**
            {test_results}

            {format_instructions}

            Generate a JSON object with:
            {{
                "tests_total": number,
                "tests_passed": number,
                "tests_failed": number,
                "tests_skipped": number,
                "execution_time": "time in seconds",
                "failed_tests": [
                    {{
                        "test_name": "name of test",
                        "app_name": "Django app name",
                        "error_message": "error message",
                        "error_type": "assertion|exception|etc"
                    }}
                ],
                "database_queries": {{"count": number, "time": "time in seconds"}},
                "tested_apps": ["list of tested Django apps"]
            }}
            """,
            input_variables=["test_results"],
            partial_variables={"format_instructions": self.json_parser.get_format_instructions()},
        )
    
    def _create_mocha_analysis_template(self) -> PromptTemplate:
        """Create a template for analyzing Mocha results"""
        return PromptTemplate(
            template="""
            You are an expert Mocha/Chai Test Results Analyst.
            Analyze these Mocha test results:

            **Test Results:**
            {test_results}

            {format_instructions}

            Generate a JSON object with:
            {{
                "tests_total": number,
                "tests_passed": number,
                "tests_failed": number,
                "tests_pending": number,
                "test_suites": number,
                "execution_time": "time in seconds",
                "failed_tests": [
                    {{
                        "test_name": "name of test",
                        "suite_path": "describe path",
                        "error_message": "error message",
                        "error_type": "assertion|exception|etc"
                    }}
                ],
                "slow_tests": ["list of slow tests"]
            }}
            """,
            input_variables=["test_results"],
            partial_variables={"format_instructions": self.json_parser.get_format_instructions()},
        )
    
    def run(self, project_dir: str, tech_stack: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Enhanced multi-stage test validation with specialized framework analysis,
        coverage parsing, and comprehensive quality assessment.
        """
        monitoring.log_agent_activity(self.agent_name, "Starting multi-stage test validation", "START")
        self.log_info("Starting multi-stage test validation...")
        
        # Validate input
        if not os.path.exists(project_dir):
            self.log_warning(f"Project directory does not exist: {project_dir}")
            return self.get_default_response()
        
        try:
            # STAGE 1: Execute tests and get results
            self.log_info("Stage 1: Executing tests and collecting results")
            test_results, coverage_report = self._execute_tests(project_dir)
            
            # STAGE 2: Extract project structure information
            self.log_info("Stage 2: Analyzing project structure")
            project_structure = self._analyze_project_structure(project_dir)
            
            # STAGE 3: Determine the test framework used
            self.log_info("Stage 3: Identifying test framework")
            test_framework = self._detect_test_framework(project_dir, test_results, tech_stack)
            
            # STAGE 4: Framework-specific test result analysis
            self.log_info(f"Stage 4: Performing specialized {test_framework} test result analysis")
            framework_analysis = self._analyze_test_results_by_framework(test_results, test_framework)
            
            # STAGE 5: Coverage report analysis
            self.log_info("Stage 5: Analyzing code coverage")
            coverage_analysis = self._analyze_coverage(coverage_report, project_structure)
            
            # STAGE 6: Analyze test code quality
            self.log_info("Stage 6: Assessing test code quality")
            test_code_samples = self._extract_test_code_samples(project_dir, test_framework)
            test_quality_assessment = self._analyze_test_quality(test_results, test_code_samples, project_dir)
            
            # STAGE 7: Analyze failure patterns
            self.log_info("Stage 7: Identifying failure patterns")
            failed_tests, error_messages = self._extract_failed_tests(test_results, framework_analysis)
            failure_pattern_analysis = self._analyze_failure_patterns(failed_tests, error_messages, project_dir)
            
            # STAGE 8: Get RAG context for best practices
            self.log_info("Stage 8: Retrieving testing best practices")
            testing_rag_context = self._get_enhanced_rag_context(test_framework, tech_stack)
            
            # STAGE 9: Generate historical test data context
            self.log_info("Stage 9: Generating historical context")
            historical_data = self._get_historical_test_context(project_dir)
            
            # STAGE 10: Comprehensive analysis with all previous results
            self.log_info("Stage 10: Compiling comprehensive analysis")
            
            # Combine all analyses into a structured format
            test_analysis = {
                "framework": test_framework,
                "framework_analysis": framework_analysis,
                "coverage_analysis": coverage_analysis,
                "test_quality_assessment": test_quality_assessment,
                "failure_pattern_analysis": failure_pattern_analysis,
                "testing_best_practices": testing_rag_context
            }
            
            # Get project context
            project_context = {
                "project_directory": project_dir,
                "project_structure": project_structure,
                "test_framework": test_framework,
                "tech_stack": tech_stack or {}
            }
            
            # Execute main analysis with all context
            self.log_info("Stage 11: Executing final validation analysis")
            analysis_result = self.execute_llm_chain({
                "test_results": test_results,
                "coverage_report": coverage_report,
                "project_context": json.dumps(project_context, indent=2),
                "historical_data": historical_data,
                "test_analysis": json.dumps(test_analysis, indent=2)
            })
            
            # Log summary and return results
            test_success_rate = analysis_result.get("test_success_rate", 0)
            coverage_percentage = analysis_result.get("coverage_percentage", 0)
            overall_assessment = analysis_result.get("overall_assessment", "Unknown")
            
            self.log_success(
                f"Validation complete - Success Rate: {test_success_rate}%, "
                f"Coverage: {coverage_percentage}%, Assessment: {overall_assessment}"
            )
            
            self.log_execution_summary(analysis_result)
            
            return analysis_result
            
        except Exception as e:
            self.log_error(f"Test validation failed: {e}")
            return self.get_default_response()
    
    def _execute_tests(self, project_dir: str) -> Tuple[str, str]:
        """Execute tests and capture test results and coverage reports."""
        self.log_info(f"Executing tests in {project_dir}")
        
        test_results = ""
        coverage_report = ""
        
        if not self.code_execution_tool:
            self.log_warning("No code execution tool available")
            return "No code execution tool available for running tests.", "No coverage data available."
        
        try:
            # Run tests with coverage
            test_result = self.code_execution_tool.run_tests(project_dir)
            test_results = test_result.get('output', 'No test output available')
            
            # Check if coverage is included in test results
            if 'coverage' in test_results.lower():
                coverage_report = self._extract_coverage_from_output(test_results)
            else:
                # Try to run coverage separately
                self.log_info("Running coverage analysis separately")
                coverage_result = self.code_execution_tool.run_command(
                    f"cd {project_dir} && python -m coverage report -m", 
                    project_dir
                )
                coverage_report = coverage_result.get('output', 'No coverage data available')
            
            return test_results, coverage_report
            
        except Exception as e:
            self.log_warning(f"Error executing tests: {e}")
            return f"Error executing tests: {e}", "No coverage data available due to test execution error."
    
    def _extract_coverage_from_output(self, test_output: str) -> str:
        """Extract coverage report section from test output."""
        # Common patterns for coverage report sections
        patterns = [
            r"(?s)(?:===+\s*coverage\s*report\s*===+)(.+?)(?:===+|$)",  # === coverage report === pattern
            r"(?s)(?:-------\s*coverage\s*-------+)(.+?)(?:-------+|$)",  # ------- coverage ------- pattern
            r"(?s)(?:Coverage\s*Summary\s*:)(.+?)(?:\n\n|\Z)",  # Coverage Summary: pattern
            r"(?s)(?:TOTAL.+?\d+\s+\d+\s+(\d+)%?.+?)(?:\n\n|\Z)"  # TOTAL line with percentages
        ]
        
        for pattern in patterns:
            match = re.search(pattern, test_output, re.IGNORECASE)
            if match:
                return match.group(0)  # Return the entire matched section
        
        # If no specific coverage section found, return the last part of output
        # which often contains coverage information
        lines = test_output.split('\n')
        if len(lines) > 20:
            return '\n'.join(lines[-20:])  # Return last 20 lines
        
        return test_output
    
    def _analyze_project_structure(self, project_dir: str) -> Dict[str, Any]:
        """Analyze project structure to understand code organization."""
        self.log_info("Analyzing project structure")
        
        # Initialize structure information
        structure_info = {
            "directories": [],
            "file_counts": {"total": 0},
            "key_modules": [],
            "test_organization": ""
        }
        
        try:
            # Walk the directory structure
            for root, dirs, files in os.walk(project_dir):
                # Skip hidden directories and common build/env directories
                dirs[:] = [d for d in dirs if not d.startswith('.') and 
                           d not in ['node_modules', 'venv', '__pycache__', '.git']]
                
                # Skip empty directories
                if not files:
                    continue
                
                # Get relative path
                rel_path = os.path.relpath(root, project_dir)
                if rel_path == '.':
                    rel_path = 'root'
                
                # Count files by extension
                path_files = {}
                for file in files:
                    ext = os.path.splitext(file)[1].lower()
                    if not ext:
                        ext = 'no_extension'
                    else:
                        ext = ext[1:]  # Remove the dot
                    
                    if ext not in path_files:
                        path_files[ext] = 0
                    path_files[ext] += 1
                    
                    # Update total files by extension
                    if ext not in structure_info["file_counts"]:
                        structure_info["file_counts"][ext] = 0
                    structure_info["file_counts"][ext] += 1
                    structure_info["file_counts"]["total"] += 1
                
                # Add directory information
                structure_info["directories"].append({
                    "path": rel_path,
                    "file_count": len(files),
                    "files_by_extension": path_files
                })
                
                # Check if this directory contains tests
                test_files = [f for f in files if 'test' in f.lower()]
                if test_files:
                    if structure_info["test_organization"]:
                        structure_info["test_organization"] += ", "
                    structure_info["test_organization"] += rel_path
            
            # Identify key modules based on file counts and patterns
            candidate_modules = []
            for dir_info in structure_info["directories"]:
                path = dir_info["path"]
                
                # Skip very deep paths, likely not main modules
                if path.count('/') > 3 or path.count('\\') > 3:
                    continue
                
                # Skip test directories
                if 'test' in path.lower():
                    continue
                
                # Check if directory has Python/JS/Java files
                has_code_files = any(ext in dir_info["files_by_extension"] 
                                     for ext in ['py', 'js', 'ts', 'java'])
                
                if has_code_files:
                    candidate_modules.append({
                        "name": os.path.basename(path) if path != 'root' else 'root',
                        "path": path,
                        "file_count": dir_info["file_count"]
                    })
            
            # Sort by file count and take top 5
            candidate_modules.sort(key=lambda x: x["file_count"], reverse=True)
            structure_info["key_modules"] = candidate_modules[:5]
            
            return structure_info
            
        except Exception as e:
            self.log_warning(f"Error analyzing project structure: {e}")
            return {"error": str(e)}
    
    def _detect_test_framework(self, project_dir: str, test_results: str, 
                             tech_stack: Optional[Dict[str, Any]] = None) -> str:
        """Detect the test framework used in the project."""
        self.log_info("Detecting test framework")
        
        # Check test results output for framework-specific patterns
        framework_patterns = {
            "pytest": ["collected", "PASSED", "FAILED", "pytest", ".py::"],
            "jest": ["PASS", "FAIL", "Test Suites:", "Tests:", "Snapshots:", "Jest"],
            "junit": ["JUnit", "Tests run:", "Failures:", "Time elapsed:", "testcase"],
            "django": ["Ran", "tests in", "OK", "system checks", "Creating test database"],
            "mocha": ["passing", "failing", "pending", "mocha", "chai"]
        }
        
        # Count occurrences of each framework's patterns
        framework_scores = {framework: 0 for framework in framework_patterns}
        
        for framework, patterns in framework_patterns.items():
            for pattern in patterns:
                if pattern in test_results:
                    framework_scores[framework] += 1
        
        # Check project files for framework-specific files
        try:
            for root, dirs, files in os.walk(project_dir):
                for file in files:
                    lower_file = file.lower()
                    if "pytest.ini" in lower_file or "conftest.py" in lower_file:
                        framework_scores["pytest"] += 3
                    elif "jest.config" in lower_file:
                        framework_scores["jest"] += 3
                    elif "pom.xml" in lower_file and any("junit" in f.lower() for f in files):
                        framework_scores["junit"] += 2
                    elif "manage.py" in lower_file and "settings.py" in ' '.join(files).lower():
                        framework_scores["django"] += 2
                    elif "mocha" in lower_file or "package.json" in lower_file and "mocha" in open(os.path.join(root, file), 'r').read().lower():
                        framework_scores["mocha"] += 2
        except Exception as e:
            self.log_warning(f"Error checking project files for framework detection: {e}")
        
        # Check tech stack if available
        if tech_stack:
            language = tech_stack.get('backend', {}).get('language', '').lower()
            framework = tech_stack.get('backend', {}).get('framework', '').lower()
            
            if language == 'python':
                framework_scores["pytest"] += 1
                if framework == 'django':
                    framework_scores["django"] += 2
            elif language in ['javascript', 'typescript']:
                framework_scores["jest"] += 1
                if 'react' in framework:
                    framework_scores["jest"] += 1
                elif 'node' in framework:
                    framework_scores["mocha"] += 1
            elif language == 'java':
                framework_scores["junit"] += 2
        
        # Get framework with highest score
        max_score = 0
        detected_framework = "pytest"  # Default to pytest
        
        for framework, score in framework_scores.items():
            if score > max_score:
                max_score = score
                detected_framework = framework
        
        self.log_info(f"Detected test framework: {detected_framework}")
        return detected_framework
    
    def _analyze_test_results_by_framework(self, test_results: str, test_framework: str) -> Dict[str, Any]:
        """Analyze test results using framework-specific templates."""
        self.log_info(f"Analyzing {test_framework} test results")
        
        if test_framework not in self.framework_templates:
            self.log_warning(f"No specific template for {test_framework}, using general analysis")
            return self._generic_test_results_analysis(test_results)
        
        try:
            # Get appropriate framework template
            template = self.framework_templates[test_framework]
            
            # Use low temperature for analytical task
            llm_with_temp = self.llm.bind(temperature=0.1)
            
            # Execute analysis
            prompt = template.format(test_results=test_results)
            response = llm_with_temp.invoke(prompt)
            
            try:
                # Parse the analysis JSON
                analysis = self.json_parser.parse(response.content)
                return analysis
            except Exception as parse_e:
                self.log_warning(f"Failed to parse {test_framework} analysis: {parse_e}")
                return self._generic_test_results_analysis(test_results)
                
        except Exception as e:
            self.log_warning(f"Framework-specific analysis failed: {e}")
            return self._generic_test_results_analysis(test_results)
    
    def _generic_test_results_analysis(self, test_results: str) -> Dict[str, Any]:
        """Generic analysis when framework-specific analysis fails."""
        # Simple regex-based extraction of test numbers
        tests_total = 0
        tests_passed = 0
        tests_failed = 0
        
        # Try to find total tests
        total_match = re.search(r'(\d+)\s+tests?', test_results)
        if total_match:
            tests_total = int(total_match.group(1))
        
        # Try to find passed tests
        passed_match = re.search(r'(\d+)\s+pass(ed|ing)?', test_results, re.IGNORECASE)
        if passed_match:
            tests_passed = int(passed_match.group(1))
        
        # Try to find failed tests
        failed_match = re.search(r'(\d+)\s+fail(ed|ing)?', test_results, re.IGNORECASE)
        if failed_match:
            tests_failed = int(failed_match.group(1))
        
        # If we found passed and failed but not total, compute total
        if tests_passed > 0 and tests_failed > 0 and tests_total == 0:
            tests_total = tests_passed + tests_failed
        
        # If we found total and passed but not failed, compute failed
        if tests_total > 0 and tests_passed > 0 and tests_failed == 0:
            tests_failed = tests_total - tests_passed
        
        # If we found total and failed but not passed, compute passed
        if tests_total > 0 and tests_failed > 0 and tests_passed == 0:
            tests_passed = tests_total - tests_failed
        
        return {
            "tests_total": tests_total,
            "tests_passed": tests_passed,
            "tests_failed": tests_failed,
            "tests_skipped": 0,  # No generic way to determine skipped tests
            "execution_time": self._extract_execution_time(test_results),
            "failed_tests": []  # No parsing of specific failed tests in generic analysis
        }
    
    def _extract_execution_time(self, test_results: str) -> str:
        """Extract execution time from test results."""
        # Common patterns for test execution time
        time_patterns = [
            r'Ran \d+ tests? in ([\d\.]+)s',
            r'Time: ([\d\.]+)s',
            r'Finished in ([\d\.]+)s',
            r'Tests.+?(\d+\.\d+) seconds',
            r'Time elapsed: ([\d\.]+)'
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, test_results)
            if match:
                return match.group(1)
        
        return "unknown"
    
    def _analyze_coverage(self, coverage_report: str, project_structure: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze code coverage report."""
        self.log_info("Analyzing code coverage")
        
        try:
            # Use low temperature for analytical task
            llm_with_temp = self.llm.bind(temperature=0.1)
            
            # Format inputs
            project_structure_str = json.dumps(project_structure, indent=2)
            
            # Execute analysis
            prompt = self.coverage_analysis_template.format(
                coverage_report=coverage_report,
                project_structure=project_structure_str
            )
            
            response = llm_with_temp.invoke(prompt)
            
            try:
                # Parse the analysis JSON
                analysis = self.json_parser.parse(response.content)
                return analysis
            except Exception as parse_e:
                self.log_warning(f"Failed to parse coverage analysis: {parse_e}")
                return self._extract_basic_coverage(coverage_report)
                
        except Exception as e:
            self.log_warning(f"Coverage analysis failed: {e}")
            return self._extract_basic_coverage(coverage_report)
    
    def _extract_basic_coverage(self, coverage_report: str) -> Dict[str, Any]:
        """Extract basic coverage information when detailed analysis fails."""
        # Try to extract overall coverage percentage
        overall_percentage = 0
        percentage_match = re.search(r'TOTAL.+?(\d+)%', coverage_report)
        if percentage_match:
            overall_percentage = int(percentage_match.group(1))
        
        # Extract module coverage if possible
        module_coverage = []
        for line in coverage_report.split('\n'):
            # Match lines like: module_name    35     10    71%
            match = re.search(r'^([^\s]+)\s+\d+\s+\d+\s+(\d+)%', line)
            if match and match.group(1) != 'TOTAL':
                module_name = match.group(1)
                coverage_pct = int(match.group(2))
                assessment = "good" if coverage_pct >= 80 else "moderate" if coverage_pct >= 50 else "poor"
                module_coverage.append({
                    "module": module_name,
                    "coverage_percentage": coverage_pct,
                    "assessment": assessment
                })
        
        return {
            "overall_coverage_percentage": overall_percentage,
            "module_coverage": module_coverage,
            "uncovered_code_areas": [],  # Basic extraction can't determine this
            "coverage_trend": "unknown",
            "critical_uncovered_areas": [],
            "recommendations": ["Automated coverage analysis limited - manual review recommended"]
        }
    
    def _extract_test_code_samples(self, project_dir: str, test_framework: str) -> str:
        """Extract representative samples of test code for quality assessment."""
        self.log_info("Extracting test code samples")
        
        samples = []
        test_file_patterns = {
            "pytest": ["test_*.py", "*_test.py"],
            "jest": ["*.test.js", "*.test.ts", "*.spec.js", "*.spec.ts"],
            "junit": ["*Test.java"],
            "django": ["test*.py"],
            "mocha": ["*test.js", "*spec.js"]
        }
        
        # Use appropriate patterns for framework
        patterns = test_file_patterns.get(test_framework, ["test_*.py", "*.test.js"])
        
        try:
            # Walk directory to find test files
            max_samples = 3  # Limit number of samples
            sample_count = 0
            
            for root, dirs, files in os.walk(project_dir):
                if sample_count >= max_samples:
                    break
                    
                # Skip common non-test directories
                if any(excluded in root for excluded in ['node_modules', 'venv', '__pycache__']):
                    continue
                
                # Look for files matching patterns
                for pattern in patterns:
                    for file in files:
                        if sample_count >= max_samples:
                            break
                            
                        # Use glob-style pattern matching
                        if self._matches_pattern(file, pattern):
                            file_path = os.path.join(root, file)
                            try:
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    content = f.read()
                                    # Add sample with relative path
                                    rel_path = os.path.relpath(file_path, project_dir)
                                    samples.append(f"## {rel_path}\n```\n{content}\n```\n")
                                    sample_count += 1
                            except Exception as e:
                                self.log_warning(f"Error reading test file {file_path}: {e}")
            
            if not samples:
                return "No test code samples found"
            
            return "\n".join(samples)
            
        except Exception as e:
            self.log_warning(f"Error extracting test code samples: {e}")
            return "Error extracting test code samples"
    
    def _matches_pattern(self, filename: str, pattern: str) -> bool:
        """Check if filename matches a glob-style pattern."""
        # Convert glob pattern to regex
        regex_pattern = pattern.replace(".", "\\.").replace("*", ".*")
        return bool(re.match(f"^{regex_pattern}$", filename))
    
    def _analyze_test_quality(self, test_results: str, test_code_samples: str, project_dir: str) -> Dict[str, Any]:
        """Analyze test code quality."""
        self.log_info("Analyzing test code quality")
        
        try:
            # Use low temperature for analytical task
            llm_with_temp = self.llm.bind(temperature=0.1)
            
            # Execute analysis
            prompt = self.test_quality_template.format(
                test_results=test_results,
                test_code_samples=test_code_samples,
                project_context=json.dumps({"project_directory": project_dir}, indent=2)
            )
            
            response = llm_with_temp.invoke(prompt)
            
            try:
                # Parse the analysis JSON
                analysis = self.json_parser.parse(response.content)
                return analysis
            except Exception as parse_e:
                self.log_warning(f"Failed to parse test quality analysis: {parse_e}")
                return {"test_quality_score": 5, "error": "Analysis parsing failed"}
                
        except Exception as e:
            self.log_warning(f"Test quality analysis failed: {e}")
            return {"test_quality_score": 5, "error": str(e)}
    
    def _extract_failed_tests(self, test_results: str, framework_analysis: Dict[str, Any]) -> Tuple[str, str]:
        """Extract detailed information about failed tests."""
        self.log_info("Extracting failed test information")
        
        # Check if framework analysis already has failed tests info
        failed_tests = framework_analysis.get("failed_tests", [])
        
        if failed_tests:
            # Format the failed tests JSON
            failed_tests_str = json.dumps(failed_tests, indent=2)
            
            # Extract error messages
            error_messages = []
            for test in failed_tests:
                if "error_message" in test:
                    error_messages.append(f"{test.get('test_name', 'Unknown test')}: {test['error_message']}")
            
            error_messages_str = "\n".join(error_messages)
            return failed_tests_str, error_messages_str
        
        # Fallback: Extract failed test information directly from test results
        failed_sections = []
        error_messages = []
        
        # Extract failed test sections using common patterns
        section_patterns = [
            r'(?s)FAIL.+?(?=FAIL|\Z)',  # Jest/Mocha pattern
            r'(?s)FAILED.+?(?=FAILED|\Z)',  # pytest pattern
            r'(?s)ERROR.+?(?=ERROR|\Z)',  # general error pattern
            r'(?s)Failures:.+?(?=\n\n|\Z)'  # JUnit pattern
        ]
        
        for pattern in section_patterns:
            matches = re.finditer(pattern, test_results)
            for match in matches:
                failed_sections.append(match.group(0))
                
                # Try to extract error message
                error_match = re.search(r'Error:\s*(.+?)(?:\n|$)', match.group(0))
                if error_match:
                    error_messages.append(error_match.group(1))
        
        failed_tests_str = "\n".join(failed_sections)
        error_messages_str = "\n".join(error_messages)
        
        return failed_tests_str, error_messages_str
    
    def _analyze_failure_patterns(self, failed_tests: str, error_messages: str, 
                               project_dir: str) -> Dict[str, Any]:
        """Analyze patterns in test failures."""
        self.log_info("Analyzing test failure patterns")
        
        # If no failed tests, return empty analysis
        if not failed_tests or failed_tests.strip() == "[]":
            return {
                "common_failure_patterns": [],
                "root_cause_categories": {
                    "code_bugs": [],
                    "environment_issues": [],
                    "test_code_issues": [],
                    "data_issues": [],
                    "timing_issues": []
                },
                "severity_assessment": [],
                "recommendations": []
            }
        
        try:
            # Use low temperature for analytical task
            llm_with_temp = self.llm.bind(temperature=0.1)
            
            # Execute analysis
            prompt = self.failure_pattern_template.format(
                failed_tests=failed_tests,
                error_messages=error_messages,
                project_context=json.dumps({"project_directory": project_dir}, indent=2)
            )
            
            response = llm_with_temp.invoke(prompt)
            
            try:
                # Parse the analysis JSON
                analysis = self.json_parser.parse(response.content)
                return analysis
            except Exception as parse_e:
                self.log_warning(f"Failed to parse failure pattern analysis: {parse_e}")
                return {
                    "common_failure_patterns": [],
                    "error": "Analysis parsing failed"
                }
                
        except Exception as e:
            self.log_warning(f"Failure pattern analysis failed: {e}")
            return {
                "common_failure_patterns": [],
                "error": str(e)
            }
    
    def _get_enhanced_rag_context(self, test_framework: str, 
                                tech_stack: Optional[Dict[str, Any]] = None) -> str:
        """Get enhanced RAG context with multiple targeted queries for testing best practices."""
        context_parts = []
        
        # Framework-specific testing best practices
        framework_query = f"{test_framework} testing best practices common failures"
        context_parts.append(self.get_rag_context(framework_query))
        
        # Test coverage best practices
        coverage_query = "code coverage best practices test coverage improvement"
        context_parts.append(self.get_rag_context(coverage_query))
        
        # Language-specific testing if available in tech stack
        if tech_stack:
            language = tech_stack.get('backend', {}).get('language', '')
            if language:
                language_query = f"{language} {test_framework} testing patterns"
                context_parts.append(self.get_rag_context(language_query))
        else:
            # Default language-specific query based on framework
            default_language_query = {
                "pytest": "python pytest testing patterns",
                "jest": "javascript jest testing patterns",
                "junit": "java junit testing patterns",
                "django": "python django testing patterns",
                "mocha": "javascript mocha testing patterns"
            }.get(test_framework, "")
            
            if default_language_query:
                context_parts.append(self.get_rag_context(default_language_query))
        
        # Combine contexts with headers
        combined_context = "\n\n".join(context_parts)
        if not combined_context or combined_context.strip() == "":
            return "No specific testing best practices available"
            
        return combined_context
    
    def _get_historical_test_context(self, project_dir: str) -> str:
        """Get historical test execution data if available."""
        history_file = os.path.join(project_dir, '.test_history.json')
        
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r') as f:
                    history_data = json.load(f)
                return json.dumps(history_data, indent=2)
            except Exception as e:
                self.log_warning(f"Error reading test history: {e}")
        
        return "No historical test data available"
    
    def get_default_response(self) -> Dict[str, Any]:
        """Get default response when validation fails."""
        return {
            "test_success_rate": 0,
            "coverage_percentage": 0,
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "overall_assessment": "Unacceptable",
            "critical_issues": ["Test validation failed due to system error"],
            "failed_tests": [],
            "uncovered_areas": ["Unable to determine uncovered areas"],
            "test_quality_assessment": {
                "completeness": "low",
                "reliability": "low",
                "maintenance_score": "low",
                "execution_time": "unknown"
            },
            "recommendations": ["Manual test review required"],
            "summary": "Test validation failed due to system error"
        }
    
    def log_execution_summary(self, response: Dict[str, Any]):
        """Log detailed execution summary for test validation."""
        test_success_rate = response.get("test_success_rate", 0)
        coverage_percentage = response.get("coverage_percentage", 0)
        tests_run = response.get("tests_run", 0)
        overall_assessment = response.get("overall_assessment", "Unknown")
        
        monitoring.log_agent_activity(
            self.agent_name,
            f"Validation complete - Success Rate: {test_success_rate}%, "
            f"Coverage: {coverage_percentage}%, Tests: {tests_run}, Assessment: {overall_assessment}",
            "SUCCESS"
        )
        
        self.log_success(f"Test validation complete")
        self.log_info(f"   Success rate: {test_success_rate}%")
        self.log_info(f"   Coverage: {coverage_percentage}%")
        self.log_info(f"   Tests run: {tests_run}")
        self.log_info(f"   Assessment: {overall_assessment}")
        
        # Log critical issues if any
        critical_issues = response.get("critical_issues", [])
        if critical_issues:
            self.log_info(f"   Critical issues: {len(critical_issues)}")
            for issue in critical_issues[:3]:  # Log first 3 issues
                self.log_warning(f"      - {issue}")