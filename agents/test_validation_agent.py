import json
import os
from google.generativeai.types import HarmBlockThreshold, HarmCategory
from tools.code_execution_tool import CodeExecutionTool

class TestValidationAgent:
    def __init__(self, llm, memory, code_execution_tool: CodeExecutionTool):
        self.llm = llm
        self.memory = memory
        self.code_execution_tool = code_execution_tool

    def run(self, project_path: str) -> dict:
        """
        Executes generated tests and reports results, including code coverage.
        """
        print("Test Validation Agent: Executing tests...")

        tech_stack = self.memory.get("tech_stack_recommendation", {})
        
        all_tests_passed = False
        coverage_report = {}
        test_output_summary = ""

        success, output = self.code_execution_tool.run_tests(project_path, tech_stack)
        
        # Check if pytest (or similar) generated a coverage report (e.g., .coverage.json)
        coverage_json_path = os.path.join(project_path, ".coverage.json") # Pytest-cov default
        if os.path.exists(coverage_json_path):
            try:
                with open(coverage_json_path, 'r', encoding='utf-8') as f:
                    coverage_data = json.load(f)
                # Extract relevant coverage percentage, e.g., for Python
                if 'totals' in coverage_data and 'percent_covered' in coverage_data['totals']:
                    coverage_report['percentage'] = coverage_data['totals']['percent_covered']
                    print(f"  Code coverage: {coverage_report['percentage']}%")
                else:
                    coverage_report['percentage'] = "N/A"
                coverage_report['raw_data'] = coverage_data # Store raw data for more detail
            except json.JSONDecodeError:
                print("  Warning: Could not parse .coverage.json.")
        else:
            print("  No .coverage.json found.")
            coverage_report['percentage'] = "N/A (No report generated)"

        # Analyze test runner output
        if success:
            test_output_summary = "All tests ran successfully."
            # For pytest, if success is True, it means all tests passed.
            if "collected 0 items" in output:
                all_tests_passed = False # No tests were found/executed
                test_output_summary = "No tests were collected/executed. This might indicate missing tests or misconfiguration."
            elif "== no tests ran in" in output:
                all_tests_passed = False
                test_output_summary = "No tests were run. This might indicate missing tests or misconfiguration."
            elif "failed" in output: # Even if command exited with 0, check output for "failed" if pytest didn't use --strict-markers etc.
                all_tests_passed = False
                test_output_summary = "Some tests failed. See detailed output in logs."
            else:
                all_tests_passed = True
        else:
            test_output_summary = f"Test execution failed with errors:\n{output}"
            all_tests_passed = False

        # Ask LLM to summarize and determine next steps
        prompt = f"""
        You are an expert Test Results Analyst AI.
        You have just executed the test suite for a project.
        Here are the results and context:

        --- Test Execution Output ---
        {output}
        --- End Test Execution Output ---

        --- Code Coverage Report ---
        {json.dumps(coverage_report, indent=2)}
        --- End Code Coverage Report ---

        **Instructions:**
        1.  **Overall Status:** Determine if all tests passed and if the code coverage is acceptable (for MVP, aim for >50% or if all crucial functional tests passed).
        2.  **Summary:** Provide a concise summary of the test run.
        3.  **Failing Tests:** If tests failed, list the names of the failing tests or a clear description of the failures.
        4.  **Actionable Feedback:** If tests failed or coverage is too low, suggest next steps (e.g., "Code needs fixing to pass tests", "Tests need to be expanded", "Review database interactions").

        Output must be ONLY a valid JSON object.

        Example JSON format:
        ```json
        {{
            "all_tests_passed": true, // true or false
            "coverage_percentage": 75.5, // N/A if not available
            "summary": "All unit and integration tests passed with 75.5% coverage.",
            "failing_tests": [], // List of failing test names/descriptions
            "feedback_for_code_agent": "N/A", // Specific feedback if code needs fixing
            "feedback_for_test_agent": "N/A" // Specific feedback if tests need improving
        }}
        ```
        """

        try:
            response = self.llm.generate_content(
                prompt,
                generation_config={
                    "response_mime_type": "application/json",
                    "temperature": 0.1
                },
                safety_settings={
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                }
            )
            raw_json_output = response.text.strip()
            if raw_json_output.startswith("```json"):
                raw_json_output = raw_json_output.split("```json", 1)[1]
            if raw_json_output.endswith("```"):
                raw_json_output = raw_json_output.rsplit("```", 1)[0]
            raw_json_output = raw_json_output.strip()

            test_results_report = json.loads(raw_json_output)
            test_results_report["all_tests_passed"] = all_tests_passed # Override with actual run result
            test_results_report["coverage_percentage"] = coverage_report.get('percentage', 'N/A')

            print("Test Validation Agent: Test execution analysis complete.")
            return test_results_report

        except json.JSONDecodeError as e:
            print(f"JSON Decode Error in Test Validation Agent: {e}")
            print(f"Problematic raw output: {raw_json_output}")
            raise
        except Exception as e:
            print(f"Error in Test Validation Agent: {e}")
            raise