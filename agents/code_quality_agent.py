"""
Code Quality Agent for the Multi-AI Development System.
Performs comprehensive code quality analysis on generated code.
"""

import json
import os
import re
import time
from typing import Dict, Any, Optional, List, Tuple
from langchain_core.language_models import BaseLanguageModel
from langchain_core.retrievers import BaseRetriever
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser, PydanticOutputParser
from datetime import datetime
import monitoring
from agent_temperatures import get_agent_temperature
from .base_agent import BaseAgent
from tools.code_execution_tool import CodeExecutionTool
from models.data_contracts import (
    CodeQualityAnalysisInput, 
    CodeQualityAnalysisOutput,
    CodeQualityReviewInput,
    CodeQualityReviewOutput,
    CodeIssue,
    SecurityVulnerability,
    WorkItem,
    CodeGenerationOutput,
    GeneratedFile
)

# Enhanced memory and RAG imports
from enhanced_memory_manager import create_memory_manager, EnhancedSharedProjectMemory
from rag_manager import get_rag_manager


class CodeQualityAgent(BaseAgent):
    """Agent for reviewing code quality across multiple languages and frameworks."""
    
    def __init__(self, llm: BaseLanguageModel, memory, temperature: float, code_execution_tool: CodeExecutionTool, 
     run_output_dir: str, rag_retriever: Optional[BaseRetriever] = None, message_bus=None):
    
        # Initialize base agent with the passed temperature
        super().__init__(
            llm=llm, 
            memory=memory, 
            agent_name="CodeQualityAgent", 
            temperature=temperature,
            rag_retriever=rag_retriever
        )
        
        self.code_execution_tool = code_execution_tool
        self.run_output_dir = run_output_dir
        self.json_parser = JsonOutputParser()
        self.message_bus = message_bus
        
        # Initialize enhanced memory (inherits from BaseAgent)
        self._init_enhanced_memory()
        
        # Initialize RAG context
        self.rag_manager = get_rag_manager()
        if self.rag_manager:
            self.logger.info("RAG manager available for enhanced code quality analysis")
        else:
            self.logger.warning("RAG manager not available - proceeding with basic code quality analysis")
        
        # Initialize Pydantic output parsers
        self.analysis_output_parser = PydanticOutputParser(pydantic_object=CodeQualityAnalysisOutput)
        self.review_output_parser = PydanticOutputParser(pydantic_object=CodeQualityReviewOutput)
          # Initialize templates first
        self._initialize_prompt_templates()
        
        # Setup message bus subscriptions
        self._setup_message_subscriptions()

    def _initialize_prompt_templates(self):
        """Initialize all prompt templates with consistent format instructions from Pydantic models."""
        # Get format instructions from Pydantic output parsers
        analysis_format_instructions = self.analysis_output_parser.get_format_instructions()
        review_format_instructions = self.review_output_parser.get_format_instructions()
        
        # Base JSON directive for consistent formatting
        json_directive = "Return ONLY valid JSON with no additional text or explanations.\n"
        
        # Main analysis template
        self.prompt_template = ChatPromptTemplate.from_messages([
            SystemMessage(content="Expert code quality analyst focusing on structure, quality, security, and performance."),
            HumanMessage(content="""
                # CODE
                {generated_files}
                
                # STACK
                {tech_stack}
                
                # AUTOMATED RESULTS
                {automated_results}
                
                # BEST PRACTICES
                {rag_context}
                
                # OUTPUT FORMAT
                {format_instructions}
                
                Analyze:
                1. Code structure and organization
                2. Naming conventions and style
                3. Error handling patterns
                4. Documentation quality
                5. Security vulnerabilities
                6. Performance bottlenecks
                7. Maintainability factors
                
                Language guidance:
                - Python: PEP 8, docstrings, error handling
                - JavaScript/TypeScript: async handling, types
                - HTML/CSS: semantics, accessibility
            """)
        ])
        
        # Review template (for quick feedback)
        self.review_template = ChatPromptTemplate.from_messages([
            SystemMessage(content="Code quality reviewer evaluating code against best practices."),
            HumanMessage(content="""
                I need to review this {code_type} code for quality issues.
                
                # CODE
                {generated_files}
                
                # TECH STACK
                {tech_stack_info}
                
                # OUTPUT FORMAT
                {format_instructions}
                
                Provide a quality review focusing on:
                1. Critical issues that must be fixed (security, major bugs)
                2. Important recommendations (performance, maintainability)
                3. Minor suggestions (style, documentation)
                
                For each issue, provide specific file, line numbers when possible, and recommended fixes.
            """)
        ])
        
        # Language-specific templates
        self.python_analysis_template = self._create_python_analysis_template(analysis_format_instructions)
        self.javascript_analysis_template = self._create_javascript_analysis_template(analysis_format_instructions)
        self.typescript_analysis_template = self._create_typescript_analysis_template(analysis_format_instructions)
        self.web_analysis_template = self._create_web_analysis_template(analysis_format_instructions)
        
        # Security analysis template
        self.security_template = ChatPromptTemplate.from_messages([
            SystemMessage(content="Security analyst identifying vulnerabilities in code."),
            HumanMessage(content="""
                Analyze these code files for security vulnerabilities:
                
                # CODE
                {code}
                
                # TECH STACK
                {tech_stack}
                
                # OUTPUT FORMAT
                {format_instructions}
                
                Focus on:
                1. Authentication weaknesses
                2. Authorization flaws
                3. Input validation issues
                4. Code injection vulnerabilities
                5. Data exposure risks
                6. Insecure dependencies
                7. Common security anti-patterns
                
                For each identified vulnerability, provide:
                - Vulnerability type
                - Location (file, function, line if possible)
                - Severity (Critical, High, Medium, Low)
                - Impact assessment
                - Recommended fix
            """)
        ])
        
        # Tool analysis template
        self.tool_interpretation_template = ChatPromptTemplate.from_messages([
            SystemMessage(content="Code quality analyst interpreting automated tool results."),
            HumanMessage(content="""
                Analyze these automated tool results:
                
                # AUTOMATED TOOL RESULTS
                {automated_results}
                
                # TECH STACK
                {tech_stack}
                
                # OUTPUT FORMAT
                {format_instructions}
                
                Interpret these automated tool results to identify:
                1. Pattern of issues
                2. Root causes
                3. Prioritized recommendations
                4. False positives (if any)
                
                Focus on actionable insights rather than repeating individual issues.
            """)
        ])
    
    def get_default_response(self) -> Dict[str, Any]:
        """Returns a default code quality analysis when analysis fails."""
        # Create a valid default using the Pydantic model
        default_response = CodeQualityAnalysisOutput(
            overall_quality_score=5.0,
            has_critical_issues=False,
            code_structure_analysis={
                "organization": "Default structure follows standard practices",
                "modularity": "Components have appropriate separation",
                "reusability": "Some components can be reused",
                "improvement_areas": ["Review architecture for modularity"]
            },
            code_standards_compliance={
                "naming_conventions": "Follow language-specific conventions",
                "documentation": "Add comments to complex sections",
                "formatting": "Use consistent indentation and spacing",
                "specific_violations": []
            },
            security_analysis={
                "vulnerabilities": [],
                "recommendations": ["Review authentication mechanisms", "Validate all inputs"]
            },
            performance_analysis={
                "efficiency": "Acceptable for most use cases",
                "scalability": "May need optimization for high load",
                "optimization_suggestions": ["Profile application under load", "Cache frequent queries"]
            },
            specific_issues=[],
            recommendations=["Conduct a thorough code review", "Add more comprehensive tests"],
            status="error"
        )
        
        return default_response.dict()
    
    def run(self, work_item: WorkItem, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Performs a focused code quality review for a single work item.
        """
        logger.info(f"CodeQualityAgent reviewing work item: {work_item.id}")
        
        code_gen_result = state.get("code_generation_result", {})
        generated_files = code_gen_result.get("generated_files", [])

        if not generated_files:
            logger.warning(f"No files provided for quality review of work item {work_item.id}.")
            return {"approved": True, "feedback": ["No files to review."]}

        prompt = self._create_work_item_review_prompt(work_item, generated_files, state.get("tech_stack_recommendation", {}))

        # Define the desired output structure
        output_schema = {
            "title": "Code Quality Review",
            "description": "A review of the generated code for a single work item.",
            "type": "object",
            "properties": {
                "approved": {
                    "title": "Approval Status",
                    "description": "True if the code passes quality checks, False otherwise.",
                    "type": "boolean"
                },
                "feedback": {
                    "title": "Feedback Items",
                    "description": "A list of specific feedback points, suggestions, or required changes.",
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": ["approved", "feedback"]
        }

        chain = self.llm.with_structured_output(output_schema)
        review_result = chain.invoke(prompt)

        logger.info(f"Review for {work_item.id} complete. Approved: {review_result.get('approved')}")
        return review_result

    def _create_work_item_review_prompt(self, work_item: WorkItem, generated_files: List[Dict[str, Any]], tech_stack: Dict[str, Any]) -> str:
        code_str = ""
        for file_data in generated_files:
            code_str += f"### FILE: {file_data['path']}\n```\n{file_data['content']}\n```\n\n"

        return f"""
        You are a senior developer acting as a code reviewer. Your task is to perform a quality and security review on the code generated for a specific work item.

        **Work Item Context:**
        - **ID:** {work_item.id}
        - **Description:** {work_item.description}
        - **Acceptance Criteria:**
        {chr(10).join(f'  - {c}' for c in work_item.acceptance_criteria)}

        **Tech Stack:**
        {json.dumps(tech_stack, indent=2)}

        **Code to Review:**
        {code_str}

        **Review Instructions:**
        1.  **Check against Acceptance Criteria**: Does the code fully implement all acceptance criteria?
        2.  **Security Analysis**: Look for common vulnerabilities (e.g., hardcoded secrets, injection risks, insecure dependencies).
        3.  **Code Quality**: Check for code smells, anti-patterns, maintainability issues, and adherence to best practices for the given tech stack.
        4.  **Decision**: Based on your review, decide if the code is `approved`. It should only be approved if there are no critical issues.

        Provide your feedback as a JSON object with two keys: `approved` (boolean) and `feedback` (a list of strings explaining your reasoning and any required changes).
        """

    def run_comprehensive_analysis(self, code_generation_result: dict, tech_stack_recommendation: dict) -> Dict[str, Any]:
        """
        DEPRECATED: This method is part of the old, phase-based workflow.
        The new workflow uses the `run` method for work-item-based review.
        """
        logger.warning("run_comprehensive_analysis is deprecated and should not be used in the new workflow.")
        # Create and validate the input with Pydantic
        try:
            input_data = CodeQualityAnalysisInput(
                code_generation_result=code_generation_result,
                tech_stack_recommendation=tech_stack_recommendation
            )
        except Exception as e:
            self.log_warning(f"Invalid input data: {e}")
            return self.get_default_response()
            
        monitoring.log_agent_activity(self.agent_name, "Starting code quality analysis", "START")
        self.log_info("Starting multi-stage code quality analysis...")
        
        start_time = time.time()
        
        # Extract generated files
        generated_files = input_data.code_generation_result.get("generated_files", {})
        if not generated_files:
            self.log_warning("No generated files found for quality analysis")
            return self.get_default_response()
        
        try:
            # Initialize analysis stages with proper temperature binding
            llm_analytical = self._get_llm_with_temperature(0.1).bind(max_output_tokens=2048)
            llm_summary = self._get_llm_with_temperature(0.2).bind(max_output_tokens=4096)
            
            # STAGE 1: Run automated tools first (token efficient - doesn't use LLM)
            self.log_info("Stage 1: Running automated quality checks")
            automated_checks = self.run_automated_quality_checks(generated_files, tech_stack_recommendation)
            
            # STAGE 2: LLM interpretation of automated results (analytical)
            self.log_info("Stage 2: Processing automated check results")
            tool_interpretation = self.run_tool_interpretation(automated_checks, tech_stack_recommendation, llm_analytical)
            
            # STAGE 3: Targeted language-specific analysis for key files (analytical)
            self.log_info("Stage 3: Running language-specific analysis")
            language_analyses = self.run_language_specific_analyses(generated_files, tech_stack_recommendation, llm_analytical)
            
            # STAGE 4: Targeted security-focused analysis (analytical)
            self.log_info("Stage 4: Running security analysis")
            security_analysis = self.run_security_analysis(generated_files, tech_stack_recommendation, llm_analytical)
            
            # STAGE 5: Generate focused RAG context (token efficient)
            self.log_info("Stage 5: Retrieving best practice context")
            rag_context = self.get_focused_rag_context(tech_stack_recommendation)
            
            # STAGE 6: Primary analysis with preprocessed context (summary)
            self.log_info("Stage 6: Running comprehensive analysis")
            files_summary = self.create_efficient_files_summary(generated_files)
            
            # Prepare focused context
            automated_results_summary = self.create_focused_results_summary(
                automated_checks, tool_interpretation, language_analyses, security_analysis)
            
            # Execute main analysis with optimized context
            analysis_result = self.execute_llm_chain(
                llm=llm_summary,
                params={
                    "generated_files": files_summary,
                    "tech_stack": json.dumps(tech_stack_recommendation, indent=2),
                    "rag_context": rag_context,
                    "automated_results": automated_results_summary
                }
            )
            
            # STAGE 7: Generate recommendation priorities (slightly higher temp for creative solutions)
            self.log_info("Stage 7: Prioritizing recommendations")
            enhanced_result = self.enhance_recommendations(analysis_result)
            
            # Ensure final result conforms to the Pydantic model
            try:
                # Validate the enhanced result using Pydantic
                validated_result = CodeQualityAnalysisOutput(**enhanced_result)
                
                # Add execution time calculation
                execution_time = time.time() - start_time
                validated_result.execution_metrics = {
                    "total_time": execution_time,
                    "files_analyzed": len(generated_files),
                    "timestamp": datetime.now().isoformat()
                }
                
                self.log_success(f"Multi-stage code quality analysis completed - Overall score: {validated_result.overall_quality_score}/10")
                self.log_execution_summary(validated_result.dict())
                  # Add message bus publishing
                if hasattr(self, "message_bus") and self.message_bus:
                    self.message_bus.publish("code.quality.analysis.completed", {
                        "quality_score": validated_result.overall_quality_score,
                        "issues_count": len(validated_result.specific_issues),
                        "vulnerabilities_count": len(validated_result.security_analysis.get("vulnerabilities", [])),
                        "timestamp": datetime.now().isoformat(),
                        "execution_time": execution_time
                    })
                    
                    # Publish optimization priority update if critical issues found
                    critical_issues = [issue for issue in validated_result.specific_issues 
                                     if issue.get("severity", "").lower() in ["critical", "high"]]
                    
                    if critical_issues or validated_result.overall_quality_score < 6:
                        priority_files = []
                        for issue in critical_issues:
                            if "file" in issue:
                                priority_files.append(issue["file"])
                        
                        self.message_bus.publish("optimization.priority.update", {
                            "priority_files": list(set(priority_files)),  # Remove duplicates
                            "critical_issues_count": len(critical_issues),
                            "quality_score": validated_result.overall_quality_score,
                            "urgency": "high" if validated_result.overall_quality_score < 5 else "medium",
                            "timestamp": datetime.now().isoformat()
                        })
                        self.log_info(f"Published optimization priority update for {len(priority_files)} files with critical issues")
                
                return validated_result.dict()
                
            except Exception as validation_error:
                self.log_warning(f"Result validation error: {validation_error}")
                # Try to salvage what we can from the enhanced_result
                return enhanced_result
            
        except Exception as e:
            self.log_error(f"Code quality analysis failed: {e}")
            return self.get_default_response()
    
    def run_tool_interpretation(self, automated_checks: dict, tech_stack: dict, llm) -> Dict[str, Any]:
        """Token-optimized tool results interpretation"""
        try:
            # Add proper monitoring context
            invoke_config = {
                "agent_context": f"{self.agent_name}:tool_interpretation",
                "temperature_used": 0.1
            }
            
            # Create focused context with only essential information
            tool_results_str = json.dumps(self.prune_tool_results(automated_checks), indent=2)
            tech_stack_str = self.prune_tech_stack(tech_stack)
            
            # Format and execute prompt
            format_instructions = "Return ONLY valid JSON with no additional text or explanations.\n" + self.json_parser.get_format_instructions()
            prompt = self.tool_results_template.format(
                tool_results=tool_results_str,
                tech_stack=tech_stack_str,
                format_instructions=format_instructions
            )
            
            # Execute with monitoring config
            response = llm.invoke(prompt, config=invoke_config)
            results = self.json_parser.parse(response.content)
            return results
        
        except Exception as e:
            self.log_warning(f"Tool results interpretation failed: {e}")
            return {"interpretation_error": str(e)}
    
    def prune_tool_results(self, automated_checks: dict) -> dict:
        """Create a token-efficient version of automated tool results"""
        pruned = {}
        
        # Keep high-level stats
        if "overall_stats" in automated_checks:
            pruned["overall_stats"] = automated_checks["overall_stats"]
        
        # Limit output lines for each linting category
        for category in ["linting", "complexity", "type_checking", "security_scans"]:
            if category in automated_checks:
                pruned[category] = {}
                for lang, output in automated_checks[category].items():
                    if isinstance(output, str):
                        # Keep only first 20 lines of output
                        lines = output.splitlines()[:20]
                        if len(lines) < len(output.splitlines()):
                            lines.append(f"[...{len(output.splitlines()) - 20} more lines truncated...]")
                        pruned[category][lang] = "\n".join(lines)
                    else:
                        pruned[category][lang] = output
        
        return pruned
    
    def prune_tech_stack(self, tech_stack: dict) -> str:
        """Create a token-efficient version of tech stack info"""
        if not tech_stack:
            return "{}"
            
        # Extract only needed keys for code quality analysis
        essentials = {
            "backend": tech_stack.get("backend", {}),
            "frontend": tech_stack.get("frontend", {}),
            "database": tech_stack.get("database", {})
        }
        return json.dumps(essentials, indent=2)
    
    def run_language_specific_analyses(self, generated_files: dict, tech_stack: dict, llm) -> Dict[str, List[Dict]]:
        """Token-efficient language-specific analysis"""
        results = {
            "python": [],
            "javascript": [],
            "typescript": [],
            "web": []
        }
        
        # Reduce number of files per language for token efficiency
        max_files_per_language = 2
        
        try:
            # Select most important files by language
            python_files = self.select_key_files(generated_files, ['.py'], max_files_per_language)
            js_files = self.select_key_files(generated_files, ['.js', '.jsx'], max_files_per_language)
            ts_files = self.select_key_files(generated_files, ['.ts', '.tsx'], max_files_per_language)
            web_files = self.select_key_files(generated_files, ['.html', '.css'], max_files_per_language)
            
            # Function to analyze a single file with proper error handling
            def analyze_file(file_path, content, language_key, language_name):
                try:
                    # Get complexity-based temperature
                    file_size = len(content)
                    adjusted_temp = self._get_complexity_based_temperature(file_size, language_name)
                    
                    # Prepare focused context
                    format_instructions = "Return ONLY valid JSON with no additional text.\n" + self.json_parser.get_format_instructions()
                    
                    # Add proper monitoring context
                    invoke_config = {
                        "agent_context": f"{self.agent_name}:{language_name}_analysis",
                        "temperature_used": adjusted_temp,
                        "file_path": file_path
                    }
                    
                    # For large files, truncate content (beginning, middle, end sections)
                    if len(content) > 5000:
                        content = self.create_representative_code_sample(content)
                    
                    # Format and execute prompt
                    prompt = self.language_analysis_templates[language_key].format(
                        code_content=content,
                        file_path=file_path,
                        format_instructions=format_instructions
                    )
                    
                    response = self._get_llm_with_temperature(adjusted_temp).invoke(prompt, config=invoke_config)
                    analysis = self.json_parser.parse(response.content)
                    return {"file": file_path, "analysis": analysis}
                except Exception as e:
                    self.log_warning(f"Failed to analyze {language_name} file {file_path}: {str(e)}")
                    return {"file": file_path, "analysis": {"error": str(e)}}
            
            # Analyze files in parallel (if we had async support)
            for file_path, content in python_files:
                results["python"].append(analyze_file(file_path, content, "python", "python"))
            
            for file_path, content in js_files:
                results["javascript"].append(analyze_file(file_path, content, "javascript", "javascript"))
            
            for file_path, content in ts_files:
                results["typescript"].append(analyze_file(file_path, content, "typescript", "typescript"))
            
            for file_path, content in web_files:
                results["web"].append(analyze_file(file_path, content, "web", "html" if file_path.endswith('.html') else "css"))
        
        except Exception as e:
            self.log_warning(f"Language-specific analysis failed: {e}")
        
        return results
    
    def create_representative_code_sample(self, content: str) -> str:
        """Create a representative sample of large code files for token efficiency"""
        lines = content.splitlines()
        if len(lines) <= 150:  # Not large enough to sample
            return content
            
        # Get important sections: beginning (imports, class defs), middle, end (main execution)
        beginning = lines[:50]  # First 50 lines
        
        # For middle, try to find interesting sections like function definitions
        middle_start = len(lines) // 2 - 25
        middle = lines[middle_start:middle_start+50]  # 50 lines from middle
        
        # For end, get last 50 lines
        end = lines[-50:]
        
        # Combine with markers
        return (
            "# BEGINNING OF FILE\n" + 
            "\n".join(beginning) + 
            "\n\n# [...code omitted...]\n\n" + 
            "# MIDDLE SECTION\n" + 
            "\n".join(middle) + 
            "\n\n# [...code omitted...]\n\n" + 
            "# END OF FILE\n" + 
            "\n".join(end)
        )
    
    def select_key_files(self, generated_files: dict, extensions: List[str], max_files: int) -> List[Tuple[str, str]]:
        """Select key files for analysis based on importance"""
        # Filter files by extension
        matching_files = [(path, content) for path, content in generated_files.items() 
                         if any(path.endswith(ext) for ext in extensions)]
        
        if len(matching_files) <= max_files:
            return matching_files
            
        # Otherwise, score files by importance
        scored_files = []
        for path, content in matching_files:
            # Calculate importance score:
            # 1. Main/entry files score higher
            # 2. Larger files score higher (but with a cap)
            # 3. Files with important keywords score higher
            
            score = 0
            # Check filename importance
            basename = os.path.basename(path)
            if any(name in basename.lower() for name in ['main', 'app', 'index', 'server']):
                score += 30
            if any(name in basename.lower() for name in ['core', 'base', 'utils', 'config']):
                score += 20
            if any(name in basename.lower() for name in ['controller', 'service', 'model']):
                score += 15
                
            # Check file size (larger files might be more complex/important)
            lines = content.count('\n') + 1
            score += min(20, lines // 50)  # Cap at 20 points for size
            
            # Check content for important components
            if 'class' in content.lower():
                score += 10
            if 'def ' in content.lower() or 'function' in content.lower():
                score += 10
            if 'import' in content.lower():
                score += 5
                
            scored_files.append((path, content, score))
            
        # Sort by score (descending) and take top max_files
        scored_files.sort(key=lambda x: x[2], reverse=True)
        return [(path, content) for path, content, _ in scored_files[:max_files]]
    
    def run_security_analysis(self, generated_files: dict, tech_stack: dict, llm) -> Dict[str, Any]:
        """Run focused security analysis on critical files"""
        # Initialize with an empty structured result
        security_results = {
            "vulnerabilities": [],
            "security_score": 8.0,  # Default if analysis fails
            "analysis_coverage": "partial"
        }
        
        # Select security-critical files only
        key_files = self._select_security_critical_files(generated_files)
        tech_stack_summary = self.prune_tech_stack(tech_stack)
        
        try:            # For security, use very low temperature for deterministic results
            security_llm = self._get_llm_with_temperature(0.1).bind(max_output_tokens=2048)
            
            for file_path, content in key_files:
                # Determine language for syntax highlighting
                language = self._determine_file_language(file_path)
                
                # For large files, create security-focused sample
                if len(content) > 5000:
                    content = self.create_security_focused_sample(content)
                
                # Add context for monitoring
                invoke_config = {
                    "agent_context": f"{self.agent_name}:security_analysis",
                    "temperature_used": 0.1,
                    "file_path": file_path
                }
                
                # Add strict JSON format instructions
                format_instructions = "Return ONLY valid JSON with no additional text or explanations.\n" + self.json_parser.get_format_instructions()
                
                # Format and execute prompt
                prompt = self.security_analysis_template.format(
                    code_content=content,
                    language=language,
                    tech_stack=tech_stack_summary,
                    format_instructions=format_instructions
                )
                
                response = security_llm.invoke(prompt, config=invoke_config)
                
                try:
                    analysis = self.json_parser.parse(response.content)
                    
                    # Format results when adding vulnerabilities
                    for vuln in analysis.get("vulnerabilities", []):
                        # Validate with model if possible
                        try:
                            validated_vuln = SecurityVulnerability(
                                vulnerability_type=vuln.get("type", "Unknown"),
                                location=vuln.get("location", file_path),
                                description=vuln.get("description", vuln.get("issue", "Unknown issue")),
                                severity=vuln.get("severity", "Medium"),
                                impact=vuln.get("impact", None),
                                remediation=vuln.get("fix", vuln.get("remediation", None))
                            )
                            # Convert to dict and add to results
                            security_results["vulnerabilities"].append(validated_vuln.dict())
                        except Exception:
                            # Fall back to original if validation fails
                            if "location" not in vuln or not vuln["location"]:
                                vuln["location"] = file_path
                            security_results["vulnerabilities"].append(vuln)
                    
                    # Update security score (take the minimum)
                    security_results["security_score"] = min(
                        security_results["security_score"], 
                        analysis.get("security_score", 10.0)
                    )
                except Exception as parse_e:
                    self.log_warning(f"Failed to parse security analysis for {file_path}: {parse_e}")
        
            security_results["analysis_coverage"] = "comprehensive" if len(key_files) > 5 else "partial"
            security_results["files_analyzed"] = len(key_files)
            return security_results
        
        except Exception as e:
            self.log_warning(f"Security analysis failed: {e}")
            return security_results
    
    def create_security_focused_sample(self, content: str) -> str:
        """Create a security-focused sample of code, targeting potentially vulnerable sections"""
        # Look for security-sensitive patterns
        security_patterns = [
            r'auth', r'login', r'password', r'token', r'jwt', r'oauth',
            r'crypto', r'hash', r'encrypt', r'decrypt', r'permission',
            r'user', r'admin', r'api', r'sql', r'query', r'exec',
            r'eval', r'sanitize', r'validate', r'input', r'request'
        ]
        
        pattern = re.compile("|".join(security_patterns), re.IGNORECASE)
        
        lines = content.splitlines()
        security_sections = []
        
        # First get standard beginning section
        security_sections.extend(lines[:30])
        
        # Then find security-related sections
        in_security_section = False
        security_buffer = []
        security_line_count = 0
        max_security_sections = 3
        
        for i, line in enumerate(lines):
            if pattern.search(line):
                in_security_section = True
                
                # Get context around this line (10 lines before, 20 after)
                start_idx = max(0, i - 10)
                end_idx = min(len(lines), i + 20)
                
                if security_line_count < 100:  # Limit total security lines
                    section = lines[start_idx:end_idx]
                    security_buffer.extend(section)
                    security_line_count += len(section)
                    
                    # Add a marker
                    security_buffer.append("\n# --- SECURITY SECTION BREAK ---\n")
                    
                    max_security_sections -= 1
                    if max_security_sections <= 0:
                        break
        
        # Add security sections if found
        if security_buffer:
            security_sections.append("# SECURITY-SENSITIVE SECTIONS")
            security_sections.extend(security_buffer)
        
        # Add end section
        security_sections.append("# END OF FILE")
        security_sections.extend(lines[-30:])
        
        return "\n".join(security_sections)
    
    def get_focused_rag_context(self, tech_stack: dict) -> str:
        """Get focused RAG context optimized for token efficiency"""
        if not self.rag_retriever:
            return ""
        
        # Extract only key technologies for targeted retrieval
        tech_keys = []
        
        # Backend
        backend = tech_stack.get('backend', {})
        backend_lang = backend.get('language', '')
        backend_framework = backend.get('framework', '')
        if backend_lang:
            tech_keys.append(backend_lang)
        if backend_framework:
            tech_keys.append(backend_framework)
            
        # Database
        database = tech_stack.get('database', {}).get('type', '')
        if database:
            tech_keys.append(database)
            
        # Frontend
        frontend = tech_stack.get('frontend', {}).get('framework', '')
        if frontend:
            tech_keys.append(frontend)
            
        # Get top technologies (limit to 3 for efficiency)
        top_techs = tech_keys[:3]
        
        # Focused query - prioritize security and code quality
        query = f"code quality best practices for {' '.join(top_techs)} security performance"
        
        # Limit retrieved context
        context = self.get_rag_context(
            query=query,
            max_docs=3,  # Reduced from original for token efficiency
            task_goal="Code quality analysis"
        )
        
        # Further prune context if needed
        if len(context) > 4000:
            paragraphs = context.split('\n\n')
            selected_paragraphs = paragraphs[:5]  # Take only first 5 paragraphs
            context = "\n\n".join(selected_paragraphs)
            
        return context
    
    def _determine_language(self, code_type: str, tech_stack: Dict[str, Any]) -> str:
        """Determine the primary language based on code type and tech stack"""
        if not tech_stack:
            return "python"  # Default
            
        # Extract language from tech stack
        if code_type == "backend" and "backend" in tech_stack:
            backend = tech_stack["backend"]
            if isinstance(backend, dict):
                return backend.get("language", "python").lower()
            elif isinstance(backend, list) and backend:
                return backend[0].get("language", "python").lower()
        elif code_type == "frontend" and "frontend" in tech_stack:
            frontend = tech_stack["frontend"]
            if isinstance(frontend, dict):
                return frontend.get("language", "javascript").lower()
            elif isinstance(frontend, list) and frontend:
                return frontend[0].get("language", "javascript").lower()
        
        # Fallback to common defaults
        if code_type in ["backend", "database"]:
            return "python"
        elif code_type == "frontend":
            return "javascript"
        else:
            return "python"
    
    def _determine_file_language(self, file_path: str) -> str:
        """Determine file language from extension"""
        ext = os.path.splitext(file_path)[1].lower()
        
        language_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.jsx': 'javascript',
            '.html': 'html',
            '.css': 'css',
            '.scss': 'css',
            '.sass': 'css',
            '.less': 'css',
            '.php': 'php',
            '.java': 'java',
            '.c': 'c',
            '.cpp': 'cpp',
            '.cs': 'csharp',
            '.go': 'go',
            '.rb': 'ruby',
            '.rs': 'rust',
            '.swift': 'swift',
            '.kotlin': 'kotlin'
        }
        
        return language_map.get(ext, 'plaintext')
    
    def run_automated_quality_checks(self, generated_files: dict, tech_stack: dict) -> Dict[str, Any]:
        """Run automated tools with optimized output handling"""
        results = {
            "linting": {},
            "complexity": {},
            "type_checking": {},
            "security_scans": {},
            "overall_stats": {
                "files_analyzed": len(generated_files),
                "issues_found": 0,
                "execution_status": "success"
            }
        }
        
        if not self.code_execution_tool:
            self.log_warning("Code execution tool not available, skipping automated checks")
            results["overall_stats"]["execution_status"] = "skipped"
            return results
            
        try:
            # Limit to important files only
            python_files = [f for f in generated_files.keys() if f.endswith('.py')]
            js_files = [f for f in generated_files.keys() if f.endswith('.js') or f.endswith('.jsx')]
            ts_files = [f for f in generated_files.keys() if f.endswith('.ts') or f.endswith('.tsx')]
            
            # Select at most 5 files per language for focused analysis
            if len(python_files) > 5:
                python_files = self.select_important_files(python_files, 5)
            if len(js_files) > 5:
                js_files = self.select_important_files(js_files, 5)
            if len(ts_files) > 5:
                ts_files = self.select_important_files(ts_files, 5)
            
            # Python linting - focus only on main logic paths
            if python_files:
                self.log_info(f"Running Python linting on {len(python_files)} files")
                try:
                    python_lint_result = self.code_execution_tool.execute_command(
                        "flake8 " + " ".join(python_files),
                        working_dir=self.run_output_dir,
                        timeout=30
                    )
                    results["linting"]["python"] = python_lint_result.output
                    
                    # Minimal additional tools with limited scope
                    try:
                        # Focus on main files only for complexity
                        main_py_files = self.select_important_files(python_files, 2)
                        complexity_result = self.code_execution_tool.execute_command(
                            "radon cc " + " ".join(main_py_files),
                            working_dir=self.run_output_dir,
                            timeout=20
                        )
                        results["complexity"]["python"] = complexity_result.output
                    except Exception:
                        self.log_warning("Radon not available for Python complexity analysis")
                    
                except Exception as e:
                    self.log_warning(f"Python linting failed: {e}")
                    results["linting"]["python"] = f"Error: {str(e)}"
            
            # JS/TS linting - focus on key files
            if js_files or ts_files:
                # Limit scope for efficiency
                total_files = len(js_files) + len(ts_files)
                self.log_info(f"Running JS/TS linting on {total_files} files")
                try:
                    # Focus on main entry points
                    main_js_files = self.select_important_files(js_files + ts_files, 5)
                    lint_command = "npx eslint " + " ".join(main_js_files)
                    js_lint_result = self.code_execution_tool.execute_command(
                        lint_command,
                        working_dir=self.run_output_dir,
                        timeout=30
                    )
                    results["linting"]["javascript"] = js_lint_result.output
                except Exception as e:
                    self.log_warning(f"JavaScript linting failed: {e}")
                    results["linting"]["javascript"] = f"Error: {str(e)}"
        
        except Exception as e:
            self.log_error(f"Automated quality checks failed: {e}")
            results["overall_stats"]["execution_status"] = "failed"
            results["overall_stats"]["error"] = str(e)
            return results
        
        # Count issues found
        issue_count = 0
        for category, lang_results in results.items():
            if category not in ["overall_stats"]:
                for _, output in lang_results.items():
                    if isinstance(output, str):
                        # Count non-empty lines as issues
                        issue_count += len([line for line in output.splitlines() if line.strip()])
        
        results["overall_stats"]["issues_found"] = issue_count
        return results
    
    def select_important_files(self, files: List[str], max_files: int) -> List[str]:
        """Select important files based on naming patterns"""
        # Score files by importance
        file_scores = []
        important_patterns = ['main', 'app', 'index', 'server', 'auth', 'user', 'security']
        
        for file in files:
            basename = os.path.basename(file).lower()
            score = 0
            
            # Score by importance patterns
            for pattern in important_patterns:
                if pattern in basename:
                    score += 10
            
            # Files in root directories often more important
            path_parts = file.split(os.sep)
            if len(path_parts) <= 2:
                score += 5
                
            file_scores.append((file, score))
            
        # Sort by score (descending)
        file_scores.sort(key=lambda x: x[1], reverse=True)
        return [f for f, _ in file_scores[:max_files]]
    
    def log_execution_summary(self, response: Dict[str, Any]):
        """Log detailed execution summary for code quality analysis."""
        quality_score = response.get("overall_quality_score", "N/A")
        issues_count = len(response.get("specific_issues", []))
        recommendations = response.get("recommendations", [])
        prioritized_recommendations = response.get("prioritized_recommendations", [])
        quick_wins = response.get("quick_wins", [])
        
        monitoring.log_agent_activity(
            self.agent_name,
            f"Analysis complete - Quality score: {quality_score}/10, Issues: {issues_count}, "
            f"Recommendations: {len(prioritized_recommendations or recommendations)}",
            "SUCCESS"
        )
        
        self.log_success(f"Code quality analysis complete")
        self.log_info(f"   Quality score: {quality_score}/10")
        self.log_info(f"   Issues identified: {issues_count}")
        self.log_info(f"   Primary recommendations: {len(prioritized_recommendations or recommendations)}")
        if quick_wins:
            self.log_info(f"   Quick wins identified: {len(quick_wins)}")
    
    def _select_security_critical_files(self, generated_files: dict) -> List[Tuple[str, str]]:
        """Select files critical for security analysis"""
        # Heuristic: prioritize files with 'auth', 'login', 'password', 'token' in the path or content
        critical_files = []
        
        for path, content in generated_files.items():
            if any(keyword in path.lower() for keyword in ['auth', 'login', 'password', 'token']):
                critical_files.append((path, content))
            else:
                # Check content for sensitive patterns
                if re.search(r'(?i)\b(auth|login|password|token|secret|key|credential)\b', content):
                    critical_files.append((path, content))
        
        # Limit to top 5 critical files for focused analysis
        return critical_files[:5]
    
    def _get_complexity_based_temperature(self, file_size: int, language: str) -> float:
        """Determine analysis temperature based on code complexity (file size as proxy)"""
        if language == "python":
            # Python: lower temp for larger files (more complex)
            return max(0.1, min(0.5, 0.5 - (file_size / 10000)))
        elif language in ["javascript", "typescript"]:
            # JS/TS: moderate temp for medium complexity
            return max(0.2, min(0.7, 0.5 - (file_size / 20000)))
        else:
            # Default: use base temperature
            return 0.2
    
    def _setup_message_subscriptions(self) -> None:
        """Set up message bus subscriptions if available"""
        if self.message_bus:
            # Subscribe to all code generation events to trigger quality analysis
            self.message_bus.subscribe("architecture.generated", self._handle_code_generated)
            self.message_bus.subscribe("database.generated", self._handle_code_generated)
            self.message_bus.subscribe("backend.generated", self._handle_code_generated)
            self.message_bus.subscribe("frontend.generated", self._handle_code_generated)
            self.message_bus.subscribe("integration.generated", self._handle_code_generated)
            self.log_info(f"{self.agent_name} subscribed to all *.generated events for proactive quality analysis")
    
    def _handle_code_generated(self, message: Dict[str, Any]) -> None:
        """Handle code generation completion messages for proactive quality analysis"""
        message_type = message.get("type", "unknown")
        self.log_info(f"Received {message_type} event for quality analysis")
        
        payload = message.get("payload", {})
        if payload.get("status") == "success" and "files" in payload:
            # Queue files for quality analysis
            if "pending_quality_analysis" not in self.working_memory:
                self.working_memory["pending_quality_analysis"] = []
            
            # Add files with metadata about their source
            file_batch = {
                "files": payload["files"],
                "source": message_type,
                "timestamp": payload.get("timestamp", "unknown"),
                "agent": payload.get("agent", "unknown")
            }
            self.working_memory["pending_quality_analysis"].append(file_batch)
            
            self.log_info(f"Queued {len(payload['files'])} files from {message_type} for quality analysis")
        else:
            self.log_warning(f"Received {message_type} event but no files to analyze")
