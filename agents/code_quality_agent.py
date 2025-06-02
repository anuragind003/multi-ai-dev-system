"""
Code Quality Agent for the Multi-AI Development System.
Performs comprehensive code quality analysis on generated code.
"""

import json
import os
import re  # Add this import
from typing import Dict, Any, Optional, List, Tuple
from langchain_core.language_models import BaseLanguageModel
from langchain_core.retrievers import BaseRetriever
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
import monitoring

from .base_agent import BaseAgent
from tools.code_execution_tool import CodeExecutionTool

class CodeQualityAgent(BaseAgent):
    """
    Enhanced agent that analyzes code quality using a multi-stage LLM approach with specialized
    analysis for different languages and quality dimensions, integrated with automated tools.
    """
    
    def __init__(self, llm: BaseLanguageModel, memory, code_execution_tool: CodeExecutionTool, 
                 run_output_dir: str, rag_retriever: Optional[BaseRetriever] = None):
        # Initialize base agent with proper temperature for code quality analysis
        super().__init__(
            llm=llm, 
            memory=memory, 
            agent_name="CodeQualityAgent", 
            temperature=0.1,  # Low temperature for deterministic quality analysis
            rag_retriever=rag_retriever
        )
        
        self.code_execution_tool = code_execution_tool
        self.run_output_dir = run_output_dir
        
        # Setup main analysis prompt template
        self.prompt_template = PromptTemplate(
            input_variables=["generated_files", "tech_stack", "rag_context", "automated_results"],
            partial_variables={"format_instructions": self.json_parser.get_format_instructions()},
            template="""
            You are an expert code quality analyst specializing in identifying structural and quality issues in code.
            
            # CODE TO ANALYZE
            {generated_files}
            
            # TECHNOLOGY STACK
            {tech_stack}
            
            # AUTOMATED TOOL RESULTS
            {automated_results}
            
            # BEST PRACTICES CONTEXT
            {rag_context}
            
            {format_instructions}
            
            ## ANALYSIS INSTRUCTIONS
            1. Analyze code structure, organization, and architecture
            2. Evaluate naming conventions and code style consistency
            3. Check for proper error handling and edge cases
            4. Assess documentation completeness and quality
            5. Identify security vulnerabilities and anti-patterns
            6. Evaluate performance bottlenecks and optimizations
            7. Consider maintainability and technical debt
            
            ## LANGUAGE-SPECIFIC GUIDANCE
            - For Python: Check PEP 8 compliance, proper docstrings, error handling, and avoid anti-patterns
            - For JavaScript/TypeScript: Check for proper async handling, type usage, and modern ES features
            - For HTML/CSS: Evaluate semantic structure, accessibility, and responsive design
            
            ## OUTPUT FORMAT
            {
                "overall_quality_score": <score from 1-10>,
                "code_structure_analysis": {
                    "organization": <analysis>,
                    "modularity": <analysis>,
                    "reusability": <analysis>
                },
                "code_standards_compliance": {
                    "naming_conventions": <analysis>,
                    "documentation": <analysis>,
                    "formatting": <analysis>
                },
                "security_analysis": {
                    "vulnerabilities": [<list of security issues>],
                    "recommendations": [<list of security recommendations>]
                },
                "performance_analysis": {
                    "efficiency": <analysis>,
                    "scalability": <analysis>,
                    "optimization_suggestions": [<list of optimizations>]
                },
                "maintainability": {
                    "readability": <analysis>,
                    "complexity": <analysis>,
                    "dependencies": <analysis>
                },
                "specific_issues": [
                    {
                        "file": <filename>,
                        "line": <line number if applicable>,
                        "issue": <description>,
                        "severity": <"low"|"medium"|"high"|"critical">,
                        "suggestion": <fix suggestion>
                    }
                ],
                "recommendations": [<list of general recommendations>],
                "summary": <overall summary>
            }
            """
        )
        
        # Language-specific analysis templates
        self.language_analysis_templates = {
            "python": self._create_python_analysis_template(),
            "javascript": self._create_javascript_analysis_template(),
            "typescript": self._create_typescript_analysis_template(),
            "web": self._create_web_analysis_template(),
        }
        
        # Security focused analysis template
        self.security_analysis_template = PromptTemplate(
            input_variables=["code_content", "language", "tech_stack"],
            partial_variables={"format_instructions": self.json_parser.get_format_instructions()},
            template="""
            You are an expert security analyst specializing in code security vulnerabilities.
            Analyze the following code for security issues like:
            - Injection vulnerabilities
            - Authentication weaknesses
            - Authorization flaws
            - Data exposure risks
            - CSRF/XSS vulnerabilities
            - Insecure dependencies
            - Hardcoded credentials
            - Inadequate error handling that may expose sensitive information
            
            # CODE TO ANALYZE
            ```{language}
            {code_content}
            ```
            
            # TECH STACK
            {tech_stack}
            
            {format_instructions}
            
            Return a JSON with the following structure:
            {
                "vulnerabilities": [
                    {
                        "type": <vulnerability type>,
                        "location": <file and line number if applicable>,
                        "description": <detailed explanation>,
                        "severity": <"low"|"medium"|"high"|"critical">,
                        "remediation": <specific fix recommendation>
                    }
                ],
                "security_score": <score from 1-10>,
                "summary": <brief security assessment>
            }
            """
        )
        
        # Tool interpretation template
        self.tool_results_template = PromptTemplate(
            input_variables=["tool_results", "tech_stack"],
            partial_variables={"format_instructions": self.json_parser.get_format_instructions()},
            template="""
            You are an expert at interpreting code quality tool results.
            Analyze the following automated tool outputs to extract meaningful insights.
            
            # TOOL RESULTS
            {tool_results}
            
            # TECH STACK
            {tech_stack}
            
            {format_instructions}
            
            Based on these results, provide interpretation in the following JSON format:
            {
                "syntax_issues": [<list of syntax issues with file, line, and explanation>],
                "linting_issues": [<list of linting/style issues with file, line, and explanation>],
                "metrics_interpretation": <interpretation of any code metrics>,
                "tool_accuracy_assessment": <assessment of how reliable the tool results are>,
                "priority_issues": [<list of most important issues to address>]
            }
            """
        )
    
    def _create_python_analysis_template(self) -> PromptTemplate:
        """Create a Python-specific analysis template"""
        return PromptTemplate(
            input_variables=["code_content", "file_path"],
            partial_variables={"format_instructions": self.json_parser.get_format_instructions()},
            template="""
            You are an expert Python code quality analyst. Analyze this Python code for quality issues:
            
            # FILE: {file_path}
            ```python
            {code_content}
            ```
            
            {format_instructions}
            
            Focus specifically on:
            1. PEP 8 compliance
            2. Proper exception handling
            3. Idiomatic Python usage
            4. Function and class design
            5. Import organization
            6. Type annotations usage
            7. Documentation quality
            
            Return your analysis as JSON:
            {
                "quality_score": <1-10>,
                "issues": [
                    {
                        "line": <line number>,
                        "issue": <description>,
                        "severity": <"low"|"medium"|"high"|"critical">,
                        "fix": <suggestion>
                    }
                ],
                "patterns": {
                    "good": [<list of good patterns used>],
                    "bad": [<list of anti-patterns or issues>]
                },
                "summary": <brief quality assessment>
            }
            """
        )
    
    def _create_javascript_analysis_template(self) -> PromptTemplate:
        """Create a JavaScript-specific analysis template"""
        return PromptTemplate(
            input_variables=["code_content", "file_path"],
            partial_variables={"format_instructions": self.json_parser.get_format_instructions()},
            template="""
            You are an expert JavaScript code quality analyst. Analyze this JavaScript code for quality issues:
            
            # FILE: {file_path}
            ```javascript
            {code_content}
            ```
            
            {format_instructions}
            
            Focus specifically on:
            1. Modern JavaScript features usage
            2. Async/await and Promise handling
            3. Variable declarations (const/let)
            4. Error handling
            5. DOM manipulation efficiency
            6. Memory leaks potential
            7. Code organization
            
            Return your analysis as JSON:
            {
                "quality_score": <1-10>,
                "issues": [
                    {
                        "line": <line number>,
                        "issue": <description>,
                        "severity": <"low"|"medium"|"high"|"critical">,
                        "fix": <suggestion>
                    }
                ],
                "patterns": {
                    "good": [<list of good patterns used>],
                    "bad": [<list of anti-patterns or issues>]
                },
                "summary": <brief quality assessment>
            }
            """
        )
    
    def _create_typescript_analysis_template(self) -> PromptTemplate:
        """Create a TypeScript-specific analysis template"""
        return PromptTemplate(
            input_variables=["code_content", "file_path"],
            partial_variables={"format_instructions": self.json_parser.get_format_instructions()},
            template="""
            You are an expert TypeScript code quality analyst. Analyze this TypeScript code for quality issues:
            
            # FILE: {file_path}
            ```typescript
            {code_content}
            ```
            
            {format_instructions}
            
            Focus specifically on:
            1. Type definitions and usage
            2. Interface and type design
            3. Modern TypeScript features
            4. Async/await and Promise handling
            5. Error handling with proper typing
            6. Code organization
            7. Type safety at boundaries
            
            Return your analysis as JSON:
            {
                "quality_score": <1-10>,
                "issues": [
                    {
                        "line": <line number>,
                        "issue": <description>,
                        "severity": <"low"|"medium"|"high"|"critical">,
                        "fix": <suggestion>
                    }
                ],
                "patterns": {
                    "good": [<list of good patterns used>],
                    "bad": [<list of anti-patterns or issues>]
                },
                "summary": <brief quality assessment>
            }
            """
        )
    
    def _create_web_analysis_template(self) -> PromptTemplate:
        """Create an HTML/CSS-specific analysis template"""
        return PromptTemplate(
            input_variables=["code_content", "file_path"],
            partial_variables={"format_instructions": self.json_parser.get_format_instructions()},
            template="""
            You are an expert web frontend code quality analyst. Analyze this HTML/CSS code for quality issues:
            
            # FILE: {file_path}
            ```
            {code_content}
            ```
            
            {format_instructions}
            
            Focus specifically on:
            1. HTML semantic structure
            2. Accessibility compliance
            3. Responsive design principles
            4. CSS organization and specificity
            5. CSS naming conventions
            6. Performance considerations
            7. Cross-browser compatibility
            
            Return your analysis as JSON:
            {
                "quality_score": <1-10>,
                "issues": [
                    {
                        "line": <line number>,
                        "issue": <description>,
                        "severity": <"low"|"medium"|"high"|"critical">,
                        "fix": <suggestion>
                    }
                ],
                "patterns": {
                    "good": [<list of good patterns used>],
                    "bad": [<list of anti-patterns or issues>]
                },
                "summary": <brief quality assessment>
            }
            """
        )
    
    def get_default_response(self) -> Dict[str, Any]:
        """Get default response when quality analysis fails."""
        return {
            "overall_quality_score": 5.0,
            "code_structure_analysis": {
                "organization": "Unable to analyze",
                "modularity": "Unable to analyze",
                "reusability": "Unable to analyze" 
            },
            "code_standards_compliance": {
                "naming_conventions": "Unable to analyze",
                "documentation": "Unable to analyze",
                "formatting": "Unable to analyze"
            },
            "security_analysis": {
                "vulnerabilities": [],
                "recommendations": ["Manual security review recommended"]
            },
            "performance_analysis": {
                "efficiency": "Unable to analyze", 
                "scalability": "Unable to analyze",
                "optimization_suggestions": []
            },
            "maintainability": {
                "readability": "Unable to analyze",
                "complexity": "Unable to analyze", 
                "dependencies": "Unable to analyze",
            },
            "specific_issues": [],
            "recommendations": ["Code quality analysis failed - manual review required"],
            "summary": "Code quality analysis failed due to unexpected error"
        }
    
    def run(self, code_generation_result: dict, tech_stack_recommendation: dict) -> Dict[str, Any]:
        """
        Enhanced multi-stage code quality analysis with specialized LLM analysis per language and category.
        """
        monitoring.log_agent_activity(self.agent_name, "Starting enhanced code quality analysis", "START")
        self.log_info("Starting multi-stage code quality analysis...")
        
        # Validate input
        if not isinstance(code_generation_result, dict):
            self.log_warning("Invalid code generation result input")
            return self.get_default_response()
            
        # Extract generated files
        generated_files = code_generation_result.get("generated_files", {})
        if not generated_files:
            self.log_warning("No generated files found for quality analysis")
            return self.get_default_response()
        
        try:
            # STAGE 1: Run automated tools first
            self.log_info("Stage 1: Running automated quality checks")
            automated_checks = self.run_automated_quality_checks(generated_files, tech_stack_recommendation)
            
            # STAGE 2: LLM interpretation of automated results
            self.log_info("Stage 2: Processing automated check results")
            tool_interpretation = self.interpret_tool_results(automated_checks, tech_stack_recommendation)
            
            # STAGE 3: Language-specific analysis for key files
            self.log_info("Stage 3: Running language-specific analysis")
            language_analyses = self.run_language_specific_analyses(generated_files, tech_stack_recommendation)
            
            # STAGE 4: Security-focused analysis
            self.log_info("Stage 4: Running security analysis")
            security_analysis = self.run_security_analysis(generated_files, tech_stack_recommendation)
            
            # STAGE 5: Generate RAG context for best practices
            self.log_info("Stage 5: Retrieving best practice context")
            rag_context = self.get_enhanced_rag_context(tech_stack_recommendation)
            
            # STAGE 6: Primary analysis with all previous results as context
            self.log_info("Stage 6: Running comprehensive analysis")
            files_summary = self.summarize_generated_files(generated_files)
            
            # Prepare rich automated results context
            automated_results_json = {
                "tool_results": automated_checks,
                "tool_interpretation": tool_interpretation,
                "language_specific_analyses": language_analyses,
                "security_analysis": security_analysis
            }
            
            # Execute main analysis with all context
            analysis_result = self.execute_llm_chain({
                "generated_files": files_summary,
                "tech_stack": json.dumps(tech_stack_recommendation, indent=2),
                "rag_context": rag_context,
                "automated_results": json.dumps(automated_results_json, indent=2)
            })
            
            # STAGE 7: Generate recommendation priorities (slightly higher temp for creative solutions)
            self.log_info("Stage 7: Prioritizing recommendations")
            enhanced_result = self.enhance_recommendations(analysis_result)
            
            self.log_success(f"Multi-stage code quality analysis completed - Overall score: {enhanced_result.get('overall_quality_score', 'N/A')}")
            self.log_execution_summary(enhanced_result)
            
            return enhanced_result
            
        except Exception as e:
            self.log_error(f"Code quality analysis failed: {e}")
            return self.get_default_response()
    
    def interpret_tool_results(self, automated_checks: dict, tech_stack: dict) -> Dict[str, Any]:
        """Use LLM to interpret automated tool results for better insights"""
        try:
            llm_with_temp = self.llm.bind(temperature=0.1)  # Analytical task
            
            tool_results_str = json.dumps(automated_checks, indent=2)
            tech_stack_str = json.dumps(tech_stack, indent=2)
            
            prompt = self.tool_results_template.format(
                tool_results=tool_results_str,
                tech_stack=tech_stack_str
            )
            
            response = llm_with_temp.invoke(prompt)
            results = self.json_parser.parse(response.content)
            return results
            
        except Exception as e:
            self.log_warning(f"Tool results interpretation failed: {e}")
            return {"interpretation_error": str(e)}
    
    def run_language_specific_analyses(self, generated_files: dict, tech_stack: dict) -> Dict[str, List[Dict]]:
        """Run specialized analysis for different language types"""
        results = {
            "python": [],
            "javascript": [],
            "typescript": [],
            "web": []
        }
        
        # Limit to a reasonable number of files per language
        max_files_per_language = 3
        
        try:
            llm_with_temp = self.llm.bind(temperature=0.1)
            
            # Group files by language
            python_files = [(path, content) for path, content in generated_files.items() if path.endswith('.py')][:max_files_per_language]
            js_files = [(path, content) for path, content in generated_files.items() if path.endswith('.js')][:max_files_per_language]
            ts_files = [(path, content) for path, content in generated_files.items() if path.endswith('.ts') or path.endswith('.tsx')][:max_files_per_language]
            web_files = [(path, content) for path, content in generated_files.items() 
                         if path.endswith('.html') or path.endswith('.css')][:max_files_per_language]
            
            # Analyze Python files
            for file_path, content in python_files:
                prompt = self.language_analysis_templates["python"].format(
                    code_content=content,
                    file_path=file_path
                )
                response = llm_with_temp.invoke(prompt)
                try:
                    analysis = self.json_parser.parse(response.content)
                    results["python"].append({"file": file_path, "analysis": analysis})
                except Exception:
                    self.log_warning(f"Failed to parse Python analysis for {file_path}")
            
            # Analyze JavaScript files
            for file_path, content in js_files:
                prompt = self.language_analysis_templates["javascript"].format(
                    code_content=content,
                    file_path=file_path
                )
                response = llm_with_temp.invoke(prompt)
                try:
                    analysis = self.json_parser.parse(response.content)
                    results["javascript"].append({"file": file_path, "analysis": analysis})
                except Exception:
                    self.log_warning(f"Failed to parse JavaScript analysis for {file_path}")
            
            # Analyze TypeScript files
            for file_path, content in ts_files:
                prompt = self.language_analysis_templates["typescript"].format(
                    code_content=content,
                    file_path=file_path
                )
                response = llm_with_temp.invoke(prompt)
                try:
                    analysis = self.json_parser.parse(response.content)
                    results["typescript"].append({"file": file_path, "analysis": analysis})
                except Exception:
                    self.log_warning(f"Failed to parse TypeScript analysis for {file_path}")
            
            # Analyze Web files
            for file_path, content in web_files:
                prompt = self.language_analysis_templates["web"].format(
                    code_content=content,
                    file_path=file_path
                )
                response = llm_with_temp.invoke(prompt)
                try:
                    analysis = self.json_parser.parse(response.content)
                    results["web"].append({"file": file_path, "analysis": analysis})
                except Exception:
                    self.log_warning(f"Failed to parse web file analysis for {file_path}")
            
            return results
            
        except Exception as e:
            self.log_warning(f"Language-specific analysis failed: {e}")
            return results
    
    def run_security_analysis(self, generated_files: dict, tech_stack: dict) -> Dict[str, Any]:
        """Run specialized security analysis on the code"""
        security_results = {
            "vulnerabilities": [],
            "security_score": 8.0,  # Default if analysis fails
            "analysis_coverage": "partial"
        }
        
        # Select most important files for security analysis
        key_files = self._select_security_critical_files(generated_files)
        tech_stack_str = json.dumps(tech_stack, indent=2)
        
        try:
            llm_with_temp = self.llm.bind(temperature=0.1)
            
            for file_path, content in key_files:
                # Determine language for syntax highlighting
                language = self._determine_file_language(file_path)
                
                # Run security analysis on this file
                prompt = self.security_analysis_template.format(
                    code_content=content,
                    language=language,
                    tech_stack=tech_stack_str
                )
                
                response = llm_with_temp.invoke(prompt)
                
                try:
                    analysis = self.json_parser.parse(response.content)
                    
                    # Add file path to each vulnerability if not present
                    for vuln in analysis.get("vulnerabilities", []):
                        if "location" not in vuln or not vuln["location"]:
                            vuln["location"] = file_path
                    
                    # Merge vulnerabilities into main results
                    security_results["vulnerabilities"].extend(analysis.get("vulnerabilities", []))
                    
                    # Update security score (take the minimum)
                    security_results["security_score"] = min(
                        security_results["security_score"], 
                        analysis.get("security_score", 10.0)
                    )
                except Exception as parse_e:
                    self.log_warning(f"Failed to parse security analysis for {file_path}: {parse_e}")
            
            # Set final analysis attributes
            security_results["analysis_coverage"] = "comprehensive" if len(key_files) > 5 else "partial"
            security_results["files_analyzed"] = len(key_files)
            
            return security_results
            
        except Exception as e:
            self.log_warning(f"Security analysis failed: {e}")
            return security_results
    
    def _select_security_critical_files(self, generated_files: dict) -> List[Tuple[str, str]]:
        """Select files that are most critical for security analysis"""
        # Priority patterns for security-critical files
        security_patterns = [
            # Authentication
            'auth', 'login', 'password', 'credential', 'token', 'session',
            # Data handling
            'user', 'admin', 'account', 'payment', 'credit', 'database', 'db', 
            # Entry points
            'api', 'controller', 'route', 'endpoint', 'handler',
            # Configuration
            'config', 'setting', 'env'
        ]
        
        # Score each file based on security importance
        scored_files = []
        
        for path, content in generated_files.items():
            # Skip non-code files
            if not self._is_code_file(path):
                continue
                
            score = 0
            lower_path = path.lower()
            
            # Check filename for security patterns
            for pattern in security_patterns:
                if pattern in lower_path:
                    score += 5
            
            # Check content for security-related terms
            lower_content = content.lower()
            if 'password' in lower_content:
                score += 3
            if 'token' in lower_content:
                score += 2
            if 'user' in lower_content and ('role' in lower_content or 'permission' in lower_content):
                score += 3
            if 'admin' in lower_content:
                score += 2
            if 'api' in lower_content and ('key' in lower_content or 'secret' in lower_content):
                score += 4
            if 'authentication' in lower_content or 'authorization' in lower_content:
                score += 3
            
            scored_files.append((path, content, score))
        
        # Sort by score descending and take top 5
        scored_files.sort(key=lambda x: x[2], reverse=True)
        return [(path, content) for path, content, _ in scored_files[:5]]
    
    def _is_code_file(self, file_path: str) -> bool:
        """Check if a file is a code file that should be analyzed"""
        code_extensions = ['.py', '.js', '.ts', '.tsx', '.jsx', '.html', '.css', 
                          '.php', '.java', '.rb', '.go', '.c', '.cpp', '.h', '.cs']
        return any(file_path.endswith(ext) for ext in code_extensions)
    
    def _determine_file_language(self, file_path: str) -> str:
        """Determine language name for code highlighting"""
        ext = os.path.splitext(file_path)[1].lower()
        
        language_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.jsx': 'javascript',
            '.html': 'html',
            '.css': 'css',
            '.php': 'php',
            '.java': 'java',
            '.rb': 'ruby',
            '.go': 'go',
            '.c': 'c',
            '.cpp': 'cpp',
            '.h': 'c',
            '.cs': 'csharp',
        }
        
        return language_map.get(ext, 'text')
    
    def get_enhanced_rag_context(self, tech_stack: dict) -> str:
        """Get enhanced RAG context with multiple targeted queries"""
        context_parts = []
        
        # Get backend-specific best practices
        backend = tech_stack.get('backend', {}).get('name', '')
        if backend:
            backend_query = f"code quality standards {backend} best practices"
            context_parts.append(self.get_rag_context(backend_query))
        
        # Get language-specific best practices
        if 'language' in tech_stack.get('backend', {}):
            language = tech_stack.get('backend', {}).get('language', '')
            language_query = f"{language} code quality standards clean code principles"
            context_parts.append(self.get_rag_context(language_query))
        
        # Get framework-specific best practices
        if 'framework' in tech_stack.get('backend', {}):
            framework = tech_stack.get('backend', {}).get('framework', '')
            framework_query = f"{framework} development best practices architecture patterns"
            context_parts.append(self.get_rag_context(framework_query))
        
        # Get security best practices
        security_query = f"security best practices {backend} common vulnerabilities"
        context_parts.append(self.get_rag_context(security_query))
        
        # Combine contexts with headers
        combined_context = "\n\n".join(context_parts)
        return combined_context
    
    def summarize_generated_files(self, generated_files: dict) -> str:
        """Generate an enhanced summary of the generated files for analysis."""
        summary_parts = []
        
        # Group files by type for better organization
        files_by_type = {}
        for file_path, content in generated_files.items():
            ext = os.path.splitext(file_path)[1].lower()
            if ext not in files_by_type:
                files_by_type[ext] = []
            files_by_type[ext].append((file_path, content))
        
        # Generate summary by file type
        for ext, files in files_by_type.items():
            summary_parts.append(f"## {ext.upper()[1:] if ext else 'OTHER'} FILES ({len(files)})")
            
            for file_path, content in files:
                line_count = content.count('\n') + 1
                char_count = len(content)
                
                # Extract code structure info
                structure_info = self._extract_code_structure(file_path, content)
                
                summary_parts.append(f"### {file_path}")
                summary_parts.append(f"- Lines: {line_count}, Size: {char_count} chars")
                if structure_info:
                    summary_parts.append(f"- Structure: {structure_info}")
                
                # Include limited preview with focus on key parts
                preview = self._generate_smart_preview(file_path, content)
                summary_parts.append(f"```\n{preview}\n```\n")
        
        return "\n".join(summary_parts)
    
    def _extract_code_structure(self, file_path: str, content: str) -> str:
        """Extract high-level structural information from code"""
        # For Python files
        if file_path.endswith('.py'):
            class_count = content.count('class ')
            function_count = content.count('def ')
            return f"{class_count} classes, {function_count} functions"
        
        # For JavaScript/TypeScript files
        elif file_path.endswith(('.js', '.ts', '.jsx', '.tsx')):
            class_count = content.count('class ')
            function_count = content.count('function ')
            arrow_funcs = content.count('=>')
            component_count = 0
            if "React" in content or "react" in file_path.lower():
                component_count = content.count('Component') + content.count('function') + content.count('<')
            return f"{class_count} classes, {function_count + arrow_funcs} functions, ~{component_count} components"
        
        return ""
    
    def _generate_smart_preview(self, file_path: str, content: str) -> str:
        """Generate a smart preview focusing on important parts of the code"""
        lines = content.split('\n')
        
        # If file is small enough, show it completely
        if len(lines) <= 30:
            return content
        
        # Start with imports/includes
        import_lines = []
        for i, line in enumerate(lines[:20]):  # Check first 20 lines for imports
            if any(imp in line for imp in ['import ', 'from ', 'require(', '#include']):
                import_lines.append(f"{i+1}: {line}")
        
        # Find key structural elements (class/function definitions)
        structure_lines = []
        for i, line in enumerate(lines):
            if re.search(r'^(class |def |function |interface |enum |struct |module )', line):
                structure_lines.append(f"{i+1}: {line}")
                # Add a few lines of context
                for j in range(1, min(4, len(lines) - i - 1)):
                    if i+j < len(lines):
                        structure_lines.append(f"{i+j+1}: {lines[i+j]}")
                structure_lines.append("...")
        
        # Include some beginning lines
        beginning = [f"{i+1}: {line}" for i, line in enumerate(lines[:10])]
        
        # Build the preview
        preview_parts = []
        if beginning:
            preview_parts.append("# FILE START")
            preview_parts.extend(beginning)
            preview_parts.append("...")
        
        if import_lines:
            preview_parts.append("\n# IMPORTS/INCLUDES")
            preview_parts.extend(import_lines)
        
        if structure_lines:
            preview_parts.append("\n# KEY STRUCTURES")
            preview_parts.extend(structure_lines)
        
        # Add file end
        if len(lines) > 5:
            preview_parts.append("\n# FILE END")
            preview_parts.extend([f"{i+1}: {line}" for i, line in enumerate(lines[-5:], len(lines)-5)])
        
        return "\n".join(preview_parts)
    
    def enhance_recommendations(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance recommendations with prioritization and more specific fixes"""
        try:
            # Use slightly higher temperature for creative recommendations
            llm_with_temp = self.llm.bind(temperature=0.2)
            
            # Extract current recommendations and issues
            recommendations = analysis_result.get("recommendations", [])
            issues = analysis_result.get("specific_issues", [])
            
            # If there are enough recommendations and issues, enhance them
            if len(recommendations) > 0 or len(issues) > 0:
                prompt = f"""
                You are an expert code quality analyst.
                
                Based on this code quality analysis, enhance and prioritize the recommendations:
                
                # CURRENT ANALYSIS
                Specific Issues: {json.dumps(issues, indent=2)}
                Current Recommendations: {json.dumps(recommendations, indent=2)}
                
                Create:
                1. Enhanced priority-ordered recommendations (most impactful first)
                2. Group recommendations by category (security, performance, maintainability)
                3. For each recommendation, provide estimated impact (high/medium/low)
                4. For critical issues, provide more specific fix instructions
                
                Return JSON with this structure:
                {
                    "prioritized_recommendations": [
                        {
                            "description": "recommendation text",
                            "category": "security|performance|maintainability|etc",
                            "impact": "high|medium|low",
                            "implementation_guidance": "specific steps to implement"
                        }
                    ],
                    "quick_wins": ["list of easy high-impact fixes"],
                    "technical_debt_items": ["list of long-term issues to address"]
                }
                """
                
                response = llm_with_temp.invoke(prompt)
                
                try:
                    enhanced = json.loads(response.content)
                    
                    # Merge enhanced recommendations into the analysis
                    analysis_result["prioritized_recommendations"] = enhanced.get("prioritized_recommendations", [])
                    analysis_result["quick_wins"] = enhanced.get("quick_wins", [])
                    analysis_result["technical_debt_items"] = enhanced.get("technical_debt_items", [])
                    
                    # Keep original recommendations for compatibility
                    if "recommendations" not in analysis_result:
                        analysis_result["recommendations"] = []
                        
                except Exception as e:
                    self.log_warning(f"Failed to parse enhanced recommendations: {e}")
            
            return analysis_result
            
        except Exception as e:
            self.log_warning(f"Recommendation enhancement failed: {e}")
            return analysis_result
    
    def run_automated_quality_checks(self, generated_files: dict, tech_stack: dict) -> dict:
        """Run automated quality checks on the generated code."""
        results = {
            "syntax_checks": [],  # Store results for each file
            "syntax": {"passed": True, "issues": []},  # Overall syntax check result
            "linting": {"passed": True, "issues": []},  # Overall linting
            "security": {"passed": True, "issues": []},
            "metrics": {}
        }
        
        try:
            # FIXED: Syntax Check per file instead of whole directory
            all_syntax_valid = True
            for file_path, code_content in generated_files.items():
                # Skip non-code files or files we can't check
                if not any(file_path.endswith(ext) for ext in ['.py', '.js', '.ts', '.html', '.css', '.jsx', '.tsx']):
                    continue
                
                # Call run_syntax_check with the actual file content and path
                syntax_result = self.code_execution_tool.run_syntax_check(code_content, file_path)
                results["syntax_checks"].append({
                    "file": file_path,
                    "valid": syntax_result.get("valid", False),
                    "errors": syntax_result.get("errors", [])
                })
                
                if not syntax_result.get("valid", False):
                    all_syntax_valid = False
                    results["syntax"]["issues"].extend(syntax_result.get("errors", []))
            
            results["syntax"]["passed"] = all_syntax_valid
            
            # Linting (for the whole project directory)
            lint_result = self.code_execution_tool.run_lint_check(self.run_output_dir, tech_stack)
            results["linting"] = lint_result
            
            # Basic security check (if tools are available)
            # This would integrate with security scanning tools
            
            return results
            
        except Exception as e:
            self.log_warning(f"Automated quality checks failed: {e}")
            return results
    
    def combine_quality_analysis(self, llm_analysis: dict, automated_checks: dict) -> dict:
        """Combine LLM analysis with automated checks for a comprehensive report."""
        combined = llm_analysis.copy()
        
        # Adjust score based on automated checks
        base_score = combined.get("overall_quality_score", 7.0)
        
        # FIXED: Adjusted to match the new structure from run_automated_quality_checks
        # Lower score for syntax errors
        if not automated_checks.get("syntax", {}).get("passed", True):
            # Get list of files with syntax errors
            files_with_errors = [
                check["file"] for check in automated_checks.get("syntax_checks", [])
                if not check.get("valid", True)
            ]
            
            combined.setdefault("specific_issues", []).append({
                "file": ", ".join(files_with_errors) if files_with_errors else "multiple",
                "issue": "Syntax errors detected",
                "severity": "critical",
                "suggestion": "Fix syntax errors before proceeding"
            })
            base_score -= 2.0
            
        # Lower score for linting issues
        linting_result = automated_checks.get("linting", {})
        if linting_result.get("issues_found", False) or not linting_result.get("passed", True):
            combined.setdefault("specific_issues", []).append({
                "file": "multiple",
                "issue": "Linting issues found",
                "severity": "medium",
                "suggestion": "Address style and linting issues"
            })
            base_score -= 1.0
            
        # Ensure score is in valid range
        combined["overall_quality_score"] = max(1.0, min(10.0, base_score))
        
        return combined
    
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