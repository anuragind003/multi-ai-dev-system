"""
SimpleCodeQualityAgent - Streamlined code quality analysis
Replaces the complex 1,512-line CodeQualityAgent with essential functionality.
"""

import os
import json
import time
from typing import Dict, Any, Optional, List
from langchain_core.language_models import BaseLanguageModel
from langchain_core.retrievers import BaseRetriever
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage

from models.data_contracts import WorkItem
from agent_state import StateFields
from .base_agent import BaseAgent


class SimpleCodeQualityAgent(BaseAgent):
    """Simplified code quality agent for essential analysis and feedback."""
    
    def __init__(self, llm: BaseLanguageModel, memory, temperature: float, 
                 code_execution_tool, run_output_dir: str, 
                 rag_retriever: Optional[BaseRetriever] = None):
        super().__init__(
            llm=llm,
            memory=memory, 
            agent_name="SimpleCodeQualityAgent",
            temperature=temperature,
            rag_retriever=rag_retriever
        )
        
        self.code_execution_tool = code_execution_tool
        self.run_output_dir = run_output_dir
        self._init_templates()
    
    def _init_templates(self):
        """Initialize enhanced prompt templates for detailed quality review."""
        self.quality_review_template = ChatPromptTemplate.from_messages([
            SystemMessage(content="""You are a senior code quality analyst performing a comprehensive review.

            Analyze the provided code for the following:
            1.  **Critical Issues**: Security vulnerabilities, major bugs, runtime errors.
            2.  **Code Quality**: Structure, naming conventions, adherence to best practices.
            3.  **Maintainability**: Documentation, readability, code complexity.
            4.  **Performance**: Obvious bottlenecks, inefficient algorithms.
            5.  **Adherence to Requirements**: Does the code meet the work item description?

            Provide your response in JSON format with this exact structure:
            {
              "approved": boolean,
              "quality_score": float (0.0-10.0),
              "summary": "string (one-sentence summary of the review)",
              "issues": [
                {
                  "severity": "critical|high|medium|low",
                  "file": "string (filename)",
                  "line": number,
                  "message": "string (clear description of the issue)",
                  "suggestion": "string (actionable recommendation for fixing the issue)"
                }
              ],
              "recommendations": ["list of general improvement suggestions"]
            }"""),
            HumanMessage(content="""Review the following {language} code based on the provided context.

            **Work Item Description:**
            {work_item_description}

            **Generated Files:**
            {generated_files}

            **Tech Stack:**
            {tech_stack}

            **Automated Check Results:**
            {automated_results}

            Focus on providing actionable feedback to improve code quality, security, and maintainability.""")
        ])
    
    def run(self, work_item: WorkItem, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhanced code quality analysis workflow with detailed feedback.
        
        Args:
            work_item: The work item being analyzed
            state: Current workflow state
            
        Returns:
            Dict with quality analysis results
        """
        try:
            work_item_id = work_item.id if isinstance(work_item, WorkItem) else work_item.get('id', 'Unknown')
            self.logger.info(f"Starting quality analysis for {work_item_id}")
            
            # Get code generation results
            code_gen_result = state.get(StateFields.CODE_GENERATION_RESULT, {})
            if code_gen_result.get("status") == "error":
                return self._create_error_response("Skipped due to code generation failure")
            
            generated_files_raw = code_gen_result.get("generated_files", [])
            if not generated_files_raw:
                return self._create_error_response("No files to analyze")
            
            # Convert to dict format for processing
            generated_files = self._convert_files_to_dict(generated_files_raw)
            
            # Get tech stack and work item description
            tech_stack = state.get(StateFields.TECH_STACK_RECOMMENDATION, {})
            work_item_description = work_item.description if isinstance(work_item, WorkItem) else work_item.get('description', '')

            # Run automated checks
            automated_results = self._run_automated_checks(generated_files, tech_stack)
            
            # Run LLM-based quality analysis
            quality_analysis = self._analyze_code_quality(
                generated_files, tech_stack, automated_results, work_item_description
            )
            
            # Create final assessment
            final_result = self._create_quality_assessment(quality_analysis, automated_results)
            
            self.logger.info(f"Quality analysis complete for {work_item_id}: "
                           f"{'APPROVED' if final_result['approved'] else 'NEEDS REVISION'}")
            
            return final_result
            
        except Exception as e:
            work_item_id = work_item.id if isinstance(work_item, WorkItem) else work_item.get('id', 'Unknown')
            self.logger.error(f"Quality analysis failed for {work_item_id}: {str(e)}")
            return self._create_error_response(f"Analysis failed: {str(e)}")
    
    def _run_automated_checks(self, generated_files: Dict[str, str], 
                            tech_stack: Dict[str, Any]) -> Dict[str, Any]:
        """Run basic automated checks on generated files."""
        if not self.code_execution_tool:
            return {"status": "no_tools", "message": "No automated tools available"}
        
        try:
            results = {"syntax_checks": [], "lint_results": "", "basic_stats": {}}
            
            # Basic syntax checking for each file
            for file_path, content in generated_files.items():
                if content and isinstance(content, str):
                    syntax_check = self.code_execution_tool.run_syntax_check(content, file_path)
                    results["syntax_checks"].append({
                        "file": file_path,
                        "valid": syntax_check.get("valid", True),
                        "error": syntax_check.get("error", "")
                    })
            
            # Basic statistics
            results["basic_stats"] = {
                "total_files": len(generated_files),
                "total_lines": sum(len(content.split('\n')) if isinstance(content, str) else 0 
                                 for content in generated_files.values()),
                "syntax_errors": len([c for c in results["syntax_checks"] if not c["valid"]])
            }
            
            return results
            
        except Exception as e:
            self.logger.warning(f"Automated checks failed: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    def _analyze_code_quality(self, generated_files: Dict[str, str], 
                            tech_stack: Dict[str, Any], automated_results: Dict[str, Any],
                            work_item_description: str) -> Dict[str, Any]:
        """Run LLM-based code quality analysis."""
        try:
            # Determine primary language
            language = self._detect_primary_language(generated_files, tech_stack)
            
            # Create compact file summary for LLM
            files_summary = self._create_files_summary(generated_files)
            
            # Prepare prompt
            prompt = self.quality_review_template.format(
                language=language,
                work_item_description=work_item_description,
                generated_files=files_summary,
                tech_stack=json.dumps(tech_stack, indent=2),
                automated_results=json.dumps(automated_results, indent=2)
            )
            
            # Get LLM analysis
            response = self.llm.invoke(prompt)
            
            # Parse JSON response
            try:
                analysis = json.loads(response.content)
                return analysis
            except json.JSONDecodeError:
                # Fallback parsing for non-JSON responses
                return self._parse_fallback_response(response.content)
                
        except Exception as e:
            self.logger.error(f"LLM quality analysis failed: {str(e)}")
            return {
                "approved": False,
                "quality_score": 3.0,
                "summary": f"LLM analysis failed: {str(e)}",
                "issues": [],
                "recommendations": []
            }
    
    def _detect_primary_language(self, generated_files: Dict[str, str], 
                               tech_stack: Dict[str, Any]) -> str:
        """Detect the primary programming language."""
        # Check tech stack first
        backend = tech_stack.get("backend_language", "").lower()
        frontend = tech_stack.get("frontend_framework", "").lower()
        
        if "python" in backend or "django" in backend or "flask" in backend:
            return "Python"
        elif "javascript" in backend or "node" in backend or "react" in frontend:
            return "JavaScript"
        elif "typescript" in backend or "typescript" in frontend:
            return "TypeScript"
        
        # Check file extensions
        extensions = [os.path.splitext(f)[1].lower() for f in generated_files.keys()]
        if ".py" in extensions:
            return "Python"
        elif ".js" in extensions or ".jsx" in extensions:
            return "JavaScript"
        elif ".ts" in extensions or ".tsx" in extensions:
            return "TypeScript"
        
        return "General"
    
    def _create_files_summary(self, generated_files: Dict[str, str], max_chars: int = 5000) -> str:
        """Create a compact summary of generated files for LLM analysis."""
        summary_parts = []
        char_count = 0
        
        # Sort files by importance (main files first)
        important_files = sorted(generated_files.items(), 
                               key=lambda x: self._get_file_priority(x[0]))
        
        for file_path, content in important_files:
            if not isinstance(content, str):
                continue
                
            # Create file header
            header = f"\n### FILE: {file_path}\n"
            
            # Truncate content if needed
            remaining_chars = max_chars - char_count - len(header)
            if remaining_chars <= 150:
                summary_parts.append("\n... [more files truncated]")
                break
                
            if len(content) > remaining_chars:
                content = content[:remaining_chars-50] + "\n... [truncated]"
            
            file_summary = header + content
            summary_parts.append(file_summary)
            char_count += len(file_summary)
        
        return "".join(summary_parts)
    
    def _get_file_priority(self, file_path: str) -> int:
        """Get priority for file analysis (lower number = higher priority)."""
        filename = os.path.basename(file_path).lower()
        
        # High priority files
        if filename in ["main.py", "app.py", "index.js", "app.js", "server.js"]:
            return 1
        elif any(f in file_path.lower() for f in ["route", "controller", "service"]):
            return 2
        elif filename.endswith((".py", ".js", ".ts", ".jsx", ".tsx")):
            return 3
        elif filename in ["package.json", "requirements.txt", "dockerfile", "docker-compose.yml"]:
            return 4
        else:
            return 5
    
    def _create_quality_assessment(self, quality_analysis: Dict[str, Any], 
                                 automated_results: Dict[str, Any]) -> Dict[str, Any]:
        """Create final quality assessment combining LLM and automated results."""
        # Start with LLM analysis
        approved = quality_analysis.get("approved", False)
        quality_score = quality_analysis.get("quality_score", 5.0)
        issues = quality_analysis.get("issues", [])
        
        # Add automated check issues
        syntax_errors = automated_results.get("basic_stats", {}).get("syntax_errors", 0)
        if syntax_errors > 0:
            approved = False
            quality_score = min(quality_score, 3.0)
            issues.append({
                "severity": "critical",
                "file": "multiple",
                "line": 0,
                "message": f"Found {syntax_errors} critical syntax errors",
                "suggestion": "Fix all syntax errors before proceeding. Code is non-functional."
            })
        
        # Create summary
        summary_parts = [quality_analysis.get("summary", "Code quality analysis completed")]
        if syntax_errors > 0:
            summary_parts.append(f"{syntax_errors} syntax errors found.")
        
        return {
            "approved": approved,
            "quality_score": round(quality_score, 1),
            "summary": ". ".join(summary_parts),
            "feedback": issues,
            "recommendations": quality_analysis.get("recommendations", []),
            "automated_checks": automated_results
        }
    
    def _convert_files_to_dict(self, generated_files_raw) -> Dict[str, str]:
        """Convert generated files from list/object format to dict format."""
        files_dict = {}
        
        if isinstance(generated_files_raw, list):
            # Handle list of GeneratedFile objects or dicts
            for file_obj in generated_files_raw:
                if hasattr(file_obj, 'file_path') and hasattr(file_obj, 'content'):
                    files_dict[file_obj.file_path] = file_obj.content
                elif isinstance(file_obj, dict):
                    file_path = file_obj.get('file_path', '')
                    content = file_obj.get('content', '')
                    if file_path:
                        files_dict[file_path] = content
        elif isinstance(generated_files_raw, dict):
            # Already in dict format
            files_dict = generated_files_raw
        
        return files_dict

    def _create_error_response(self, reason: str) -> Dict[str, Any]:
        """Create a standardized error response when analysis cannot run."""
        return {
            "approved": False,
            "quality_score": 0.0,
            "summary": reason,
            "feedback": [],
            "recommendations": [],
            "automated_checks": {}
        }
    
    def _parse_fallback_response(self, response_text: str) -> Dict[str, Any]:
        """Parse non-JSON response as fallback."""
        return {
            "approved": "critical" not in response_text.lower() and "error" not in response_text.lower(),
            "quality_score": 5.0,
            "summary": "Quality review completed (non-structured response).",
            "issues": [{"severity": "medium", "file": "unknown", "line": 0, "message": response_text, "suggestion": "Review the full text output."}],
            "recommendations": []
        }
    
    async def arun(self, work_item: WorkItem, state: Dict[str, Any]) -> Dict[str, Any]:
        """Async version of run method."""
        return self.run(work_item, state)
    
    def get_default_response(self, reason: str = "Default response") -> Dict[str, Any]:
        """Get default response for error cases."""
        return self._create_error_response(reason) 