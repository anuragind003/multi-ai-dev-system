import json
import os
from google.generativeai.types import HarmBlockThreshold, HarmCategory
from tools.code_execution_tool import CodeExecutionTool
import time # NEW IMPORT
import google.api_core.exceptions # NEW IMPORT for catching Google API errors


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
        has_critical_issues_flag = False # Use a distinct variable to avoid confusion with LLM's flag

        # Run Linter
        print("  Running linter...")
        success, lint_output = self.code_execution_tool.run_lint_check(project_path, tech_stack)
        if success:
            if lint_output.strip(): 
                quality_issues_summary.append(f"Linting issues detected:\n{lint_output}")
                has_critical_issues_flag = True # Consider any linting error as critical for MVP
            else:
                quality_issues_summary.append("No linting issues found.")
        else:
            quality_issues_summary.append(f"Linter tool failed to run: {lint_output}")
            has_critical_issues_flag = True # Tool failure is critical

        # Prepare linting report for LLM: truncate if too long
        full_lint_report_content = quality_issues_summary[0] if quality_issues_summary else "No linting report."
        max_lint_report_chars = 5000 # Cap input to LLM to avoid context window issues
        if len(full_lint_report_content) > max_lint_report_chars:
            truncated_lint_report = full_lint_report_content[:max_lint_report_chars] + "\n... (report truncated due to length)"
            print(f"  Linting report truncated for LLM input (original length: {len(full_lint_report_content)}, sent: {len(truncated_lint_report)}).")
        else:
            truncated_lint_report = full_lint_report_content

        # Ask LLM to summarize and categorize findings - NOW WITH RETRY LOGIC
        prompt = f"""
        You are an expert Code Quality Analyst AI.
        You have analyzed a project's code using static analysis tools.
        Here are the outputs from the tools:

        --- Linting Report ---
        {truncated_lint_report}
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
        
        quality_report = {}
        max_llm_retries = 3
        base_delay = 5 # seconds for exponential backoff

        for attempt in range(max_llm_retries):
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
                
                # IMPORTANT: Consolidate has_critical_issues. If our tool found issues, it's critical.
                if has_critical_issues_flag:
                     quality_report["has_critical_issues"] = True
                     if not any(d.get("type") == "Linting" for d in quality_report.get("details",[])):
                         quality_report.get("details",[]).append({"type": "Linting", "issue": "Linting errors detected (see raw output in memory).", "severity": "Critical"})
                         quality_report.get("recommendations",[]).append("Review and fix linting errors for code style and potential bugs.")

                print("Code Quality Agent: Quality check complete.")
                return quality_report # Successfully returned

            except google.api_core.exceptions.ResourceExhausted as e:
                delay = base_delay * (2 ** attempt)
                print(f"Code Quality Agent: API quota exhausted (429). Retrying LLM call in {delay} seconds (Attempt {attempt+1}/{max_llm_retries}). Error: {e}")
                time.sleep(delay)
            except google.api_core.exceptions.InternalServerError as e: # Catch 500 errors specifically
                delay = base_delay * (2 ** attempt)
                print(f"Code Quality Agent: API internal error (500). Retrying LLM call in {delay} seconds (Attempt {attempt+1}/{max_llm_retries}). Error: {e}")
                time.sleep(delay)
            except json.JSONDecodeError as e:
                print(f"JSON Decode Error in Code Quality Agent (Attempt {attempt+1}/{max_llm_retries}): {e}")
                print(f"Problematic raw output: {raw_json_output}")
                # If LLM produces malformed JSON, add feedback to prompt for next iteration.
                # For now, just retry and then fail.
                delay = base_delay * (2 ** attempt)
                print(f"Retrying LLM call in {delay} seconds (Attempt {attempt+1}/{max_llm_retries}).")
                time.sleep(delay)
            except Exception as e:
                print(f"An unexpected error occurred in Code Quality Agent LLM call (Attempt {attempt+1}/{max_llm_retries}): {e}")
                raise # Re-raise if it's not a known API or JSON error after retries
        
        # If loop finishes without returning, it means all retries failed
        print("Code Quality Agent: Failed to get valid quality report from LLM after multiple retries.")
        # Return a default failure report
        return {
            "summary": "Failed to get a quality report from AI due to persistent API errors or malformed responses.",
            "has_critical_issues": True,
            "details": [{"type": "API Error", "issue": "Failed to summarize quality report from LLM.", "severity": "Critical"}],
            "recommendations": ["Check API quotas and retry. Inspect logs for LLM output issues."]
        }