import json
import os
from google.generativeai.types import HarmBlockThreshold, HarmCategory
from tools.code_execution_tool import CodeExecutionTool

class CodeQualityAgent:
    def __init__(self, llm, memory, code_execution_tool: CodeExecutionTool):
        self.llm = llm
        self.memory = memory
        self.code_execution_tool = code_execution_tool

    def run(self, project_path: str, tech_stack: dict) -> dict:
        """
        Runs code quality checks and summarizes the findings.
        """
        print("Code Quality Agent: Running code quality checks...")

        backend_name = tech_stack.get("backend", {}).get("name", "").lower()
        quality_issues_summary = []
        has_critical_issues = False

        # Run Linter
        print("  Running linter...")
        success, lint_output = self.code_execution_tool.run_lint_check(project_path, tech_stack)
        if success:
            if lint_output.strip(): # If there's any output, it means issues were found
                quality_issues_summary.append(f"Linting issues detected:\n{lint_output}")
                has_critical_issues = True # Consider any linting error as critical for MVP
            else:
                quality_issues_summary.append("No linting issues found.")
        else:
            quality_issues_summary.append(f"Linter tool failed to run: {lint_output}")
            has_critical_issues = True # Tool failure is critical

        # (Optional) Run other static analysis tools here (e.g., Bandit for Python security)
        # For simplicity, we'll stick to linting for now in Phase 2.

        # Ask LLM to summarize and categorize findings
        prompt = f"""
        You are an expert Code Quality Analyst AI.
        You have analyzed a project's code using static analysis tools.
        Here are the outputs from the tools:

        --- Linting Report ---
        {quality_issues_summary[0] if quality_issues_summary else "No linting report."}
        --- End Linting Report ---

        Please summarize the code quality findings in a structured JSON object.
        Identify if there are any critical issues that would prevent the code from being considered production-ready (even for MVP).
        Focus on syntax errors, unhandled exceptions, obvious security flaws, and severe style violations.

        Output must be ONLY a valid JSON object.

        Example JSON format:
        ```json
        {{
            "summary": "Overall summary of code quality.",
            "has_critical_issues": true, // true if major issues, false otherwise
            "details": [
                {{"type": "Linting", "issue": "Missing docstrings", "severity": "Minor"}},
                {{"type": "Syntax", "issue": "IndentationError", "severity": "Critical"}}
            ],
            "recommendations": [
                "Fix all critical linting errors.",
                "Add proper error handling."
            ]
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

            quality_report = json.loads(raw_json_output)
            # Override has_critical_issues if linting directly found issues
            if lint_output.strip():
                 quality_report["has_critical_issues"] = True
                 if not any(d.get("type") == "Linting" for d in quality_report.get("details",[])):
                     quality_report.get("details",[]).append({"type": "Linting", "issue": "Linting errors detected (see raw output in memory).", "severity": "Critical"})
                     quality_report.get("recommendations",[]).append("Review and fix linting errors for code style and potential bugs.")


            print("Code Quality Agent: Quality check complete.")
            return quality_report

        except json.JSONDecodeError as e:
            print(f"JSON Decode Error in Code Quality Agent: {e}")
            print(f"Problematic raw output: {raw_json_output}")
            raise
        except Exception as e:
            print(f"Error in Code Quality Agent: {e}")
            raise