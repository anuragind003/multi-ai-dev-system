import os
import json
import re
import logging
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Union
from pathlib import Path

# Ensure correct import paths
from langchain_core.language_models import BaseLanguageModel
from langchain_core.retrievers import BaseRetriever
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser

# MODIFIED: Fix import paths - use absolute imports instead of relative imports
import os
import sys
# Add project root to Python path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import proper dependencies
from models.data_contracts import GeneratedFile, CodeGenerationOutput, WorkItem
from tools.code_generation_utils import parse_llm_output_into_files
from agents.code_generation.base_code_generator import BaseCodeGeneratorAgent
import monitoring
from tools.code_execution_tool import CodeExecutionTool
from message_bus import MessageBus
from enhanced_memory_manager import create_memory_manager, EnhancedSharedProjectMemory
from rag_manager import get_rag_manager

class CodeOptimizerAgent(BaseCodeGeneratorAgent):
    """
    Specialized agent that optimizes and refines generated code for quality and performance
    using a comprehensive, multi-file approach.
    """
    
    def __init__(self, llm: BaseLanguageModel, memory, 
                 temperature: float,
                 output_dir: str,
                 code_execution_tool: Optional[CodeExecutionTool] = None, 
                 rag_retriever: Optional[BaseRetriever] = None,
                 message_bus: Optional[MessageBus] = None):
        """
        Initialize the code optimizer agent with properly aligned inheritance.
        """
        # Call super().__init__ with all required parameters
        super().__init__(
            llm=llm,
            memory=memory,
            agent_name="Code Optimizer Agent",
            temperature=temperature,
            output_dir=output_dir,
            code_execution_tool=code_execution_tool,
            rag_retriever=rag_retriever,
            message_bus=message_bus
        )
        
        # Initialize optimization metrics
        self.optimization_metrics = {
            "files_processed": 0,
            "optimized_files": 0,
            "token_usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            }
        }
        
        # Initialize prompt templates
        self._initialize_prompt_templates()
        
        # Track optimized files
        self.optimized_files_count = 0
        
        # Initialize working memory for inter-message state
        self.working_memory = {}
        
        # Configure maximum tokens and context lengths
        self.max_tokens = 8192
        self.max_context_chars = {
            "rag": 2000,
            "code_file": 8000,
            "tech_stack": 1000,
        }
        
        # Initialize enhanced memory
        self._init_enhanced_memory()

        # Initialize RAG context
        self.rag_manager = get_rag_manager()
        if self.rag_manager:
            self.logger.info("RAG manager available for code optimization patterns")
        else:
            self.logger.warning("RAG manager not available")
        
        # Subscribe to relevant messages if message bus is available
        if self.message_bus:
            self._setup_message_subscriptions()
        
        # Initialize language-specific best practices
        self.language_best_practices = self._initialize_language_best_practices()
    
    def _initialize_prompt_templates(self):
        """Initializes a single, comprehensive prompt for optimizing multiple code files."""
        
        multi_file_format = """
        CRITICAL OUTPUT FORMAT:
        You MUST provide your response as a single block of text. For each file you optimize, 
        you MUST use the following format. Do not add any other text or explanations.

        ### FILE: path/to/your/file.ext
        ```filetype
        // The *full*, optimized content of the file goes here.
        ```

        After each file, include a brief explanation of the changes you made:
        ### EXPLANATION: path/to/your/file.ext
        - First change description
        - Second change description
        - ...
        """

        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", 
             "You are an expert software engineer specializing in code optimization. Your task is to analyze and "
             "refactor the provided code files to improve their quality, performance, and maintainability, "
             "while strictly preserving all original functionality. Apply language-specific best practices "
             "to each file based on its type and purpose."),
            ("human", 
             """
             # Code Optimization Task
             
             ## Project Context
             Technology Stack: {tech_stack_summary}
             Architecture Pattern: {architecture_pattern}
             
             ## Files to Optimize
             {files_to_optimize_str}
             
             ## Optimization Goals
             1. **Performance:** Optimize algorithms, reduce unnecessary computations, and improve resource usage.
             2. **Readability:** Improve variable names, add comments, and simplify complex logic.
             3. **Best Practices:** Refactor the code to align with modern best practices for each language:
                - Python: PEP 8, type hints, docstrings, f-strings, list/dict comprehensions
                - JavaScript/TypeScript: ES6+ features, async/await, destructuring, modules
                - Java: Clean code principles, streams API, Optional<>
                - Other languages: Apply relevant modern best practices
             4. **Security:** Identify and patch potential security vulnerabilities.
             5. **Error handling:** Improve error handling and add validation where needed.
             
             ## Code Review Feedback (Address these issues)
             {feedback_context}
             
             ## RAG Context (Examples & Best Practices)
             {rag_context}
             
             Return the complete, optimized versions of ALL provided files using the specified multi-file format.
             For each file, explain the key improvements you made.
             
             {format_instructions}
             """)
        ])
        
        self.prompt_template = self.prompt_template.partial(format_instructions=multi_file_format)
        
        # Single file optimization template for focused improvements
        self.single_file_optimization_prompt = ChatPromptTemplate.from_messages([
            ("system", 
             "You are an expert software engineer specializing in code optimization for {language}. "
             "Your task is to improve a single file's code quality, performance, and readability "
             "while preserving the original functionality."
            ),
            ("human", 
             """
             # File to Optimize
             Path: {file_path}
             
             ```{language_tag}
             {original_code}
             ```
             
             # Tech Stack Context
             {tech_stack}
             
             # Optimization Goals
             Primary: {primary_goal}
             Secondary: {secondary_goal}
             Tertiary: {tertiary_goal}
             
             # Focus Area
             {optimization_focus}
             
             {rag_context}
             
             {related_files}
             
             # Instructions
             1. Optimize the code following best practices for {language}
             2. Maintain all existing functionality
             3. Return the optimized code in this format:
             
             ### FILE: {file_path}
             ```{language_tag}
             // Optimized code here
             ```
             
             ### EXPLANATION: {file_path}
             - First improvement description
             - Second improvement description
             - Additional improvements...
             
             Be thorough but focused on important improvements only.
             """
            )
        ])
    
    def _generate_code(self, llm: BaseLanguageModel, 
                      invoke_config: Dict, 
                      **kwargs) -> Dict[str, Any]:
        """
        Optimizes a batch of generated code files in a single, comprehensive step.
        
        Args:
            llm: Language model to use for optimization
            invoke_config: Configuration for LLM invocation
            **kwargs: Additional arguments including tech_stack, system_design, etc.
            
        Returns:
            Dictionary conforming to the CodeGenerationOutput model
        """
        with monitoring.agent_trace_span(self.agent_name, "code_optimization"):
            self.log_info("Starting comprehensive code optimization process")
            start_time = time.time()
            
            # Extract inputs from kwargs
            tech_stack = kwargs.get('tech_stack', {})
            system_design = kwargs.get('system_design', {})
            code_review_feedback = kwargs.get('code_review_feedback')
            
            # Track if this is a revision based on feedback
            is_revision = code_review_feedback is not None
            
            # Collect all generated files
            all_generated_files = self._collect_all_generated_files(kwargs)
            
            if not all_generated_files:
                self.log_warning("No generated files found to optimize.")
                return self._create_empty_output("No files found to optimize")
            
            try:
                # Prepare context for the single prompt
                tech_stack_summary = self._create_tech_stack_summary(tech_stack)
                architecture_pattern = self._extract_architecture_pattern(tech_stack, system_design)
                
                # Select a representative subset of files to optimize to manage token limits
                files_to_optimize = self._select_files_to_optimize(
                    self._categorize_files(all_generated_files),
                    max_files=15  # Adjust based on the LLM's context window
                )
                
                # Prioritize files based on feedback if available
                if code_review_feedback:
                    files_to_optimize = self._prioritize_files_by_feedback(
                        files_to_optimize, code_review_feedback
                    )
                
                # Format files for the prompt
                files_to_optimize_str = self._format_files_for_prompt(files_to_optimize)
                
                # Prepare feedback context
                feedback_context = self._prepare_feedback_context(code_review_feedback, files_to_optimize)
                
                # Get optimization RAG context
                rag_context = ""
                # Check for multiple programming languages in files
                languages = set(self._determine_file_language(path) for path in files_to_optimize.keys())
                for language in languages:
                    if language != "unknown":
                        lang_rag = self._get_optimization_rag_context(language, architecture_pattern)
                        if lang_rag:
                            rag_context += f"\n\n## {language.capitalize()} Best Practices\n{lang_rag}"
                
                # Adjust temperature based on complexity and revision status
                adjusted_temp = 0.1  # Default for code optimization
                if is_revision:
                    adjusted_temp += 0.02  # Slightly higher for revisions
                
                # Use binding pattern for temperature 
                llm_with_temp = llm.bind(
                    temperature=adjusted_temp,
                    max_tokens=self.max_tokens
                )
                
                # Add monitoring context
                local_invoke_config = invoke_config.copy()
                local_invoke_config["agent_context"] = f"{self.agent_name}:batch_optimization"
                local_invoke_config["temperature_used"] = adjusted_temp
                
                self.log_info(f"Optimizing {len(files_to_optimize)} files with temperature {adjusted_temp}")
                
                # Invoke the LLM with the comprehensive prompt
                response = llm_with_temp.invoke(
                    self.prompt_template.format(
                        tech_stack_summary=tech_stack_summary,
                        architecture_pattern=architecture_pattern,
                        files_to_optimize_str=files_to_optimize_str,
                        feedback_context=feedback_context,
                        rag_context=rag_context,
                    ),
                    config=local_invoke_config
                )
                content = response.content if hasattr(response, 'content') else str(response)
                
                # Parse the multi-file output
                optimized_files = parse_llm_output_into_files(content)
                
                if not optimized_files:
                    self.log_warning("LLM did not produce any parsable optimized files.")
                    return self._create_empty_output("Failed to parse optimized files from LLM output")
                
                # Extract explanations from response
                explanations = {}
                matches = re.finditer(r'### EXPLANATION: (.*?)$(.*?)(?=###|\Z)', content, re.MULTILINE | re.DOTALL)
                
                for match in matches:
                    file_path = match.group(1).strip()
                    explanation = match.group(2).strip()
                    explanations[file_path] = explanation
                
                # Enhance the GeneratedFile objects with explanations
                for file in optimized_files:
                    if file.file_path in explanations:
                        file.purpose = f"Optimized: {explanations[file.file_path]}"
                    else:
                        file.purpose = "Optimized file"
                    
                    # Set status to success
                    file.status = "success"
                
                # Create directories and save files
                self._create_directories_from_files(optimized_files)
                self._save_files(optimized_files)
                
                # Create the final output object
                output = CodeGenerationOutput(
                    generated_files=[GeneratedFile(**f) for f in optimized_files],
                    summary=f"Successfully optimized {len(optimized_files)} files.",
                    status="success",
                    metadata={
                        "optimization_count": len(optimized_files),
                        "total_files_available": len(all_generated_files),
                        "files_selected": len(files_to_optimize),
                        "languages_optimized": list(languages),
                        "agent": self.agent_name,
                        "is_revision": is_revision,
                        "execution_time": time.time() - start_time
                    }                )
                
                # Store optimization results in enhanced memory
                optimization_results = {
                    "optimized_files_count": len(optimized_files),
                    "languages_optimized": list(languages),
                    "optimization_time": time.time() - start_time,
                    "files_optimized": [file.file_path for file in optimized_files]
                }
                self.enhanced_set("optimization_results", optimization_results, context="code_optimization")
                self.store_cross_tool_data("optimization_results", optimization_results, 
                                         "Code optimization results for use by other agents")
                
                # Publish optimization completion message
                if self.message_bus:
                    self.message_bus.publish("code.optimization.complete", {
                        "agent": self.agent_name,
                        "optimized_files": [file.file_path for file in optimized_files],
                        "languages": list(languages),
                        "timestamp": datetime.now().isoformat()
                    })
                
                self.log_success(f"Code optimization complete: {len(optimized_files)} files optimized")
                return output.dict()
                
            except Exception as e:
                self.log_error(f"Code optimization failed: {e}", exc_info=True)
                return self._create_empty_output(f"Error during code optimization: {str(e)}")
    
    def _setup_message_subscriptions(self) -> None:
        """Set up message bus subscriptions if available"""
        if self.message_bus:
            self.message_bus.subscribe('code_generation.complete', self._handle_code_generation_complete)
            self.message_bus.subscribe('tech_stack.updated', self._handle_tech_stack_updated)
            self.message_bus.subscribe('optimization.priority.update', self._handle_optimization_priority)
            self.message_bus.subscribe('code.quality.analysis.completed', self._handle_quality_analysis_completed)
            self.message_bus.subscribe('implementation_plan_created', self._handle_implementation_plan_created)
            self.log_info(f"{self.agent_name} subscribed to relevant messages")
    
    def _handle_code_generation_complete(self, message: Dict[str, Any]) -> None:
        """Handle code generation completion messages"""
        self.log_info("Received code generation completion message")
        
        # Extract files from message payload
        files = self._extract_files_from_message(message)
        
        if files:
            self.log_info(f"Found {len(files)} files to optimize from code generation")
            self.working_memory["pending_files"] = files
            
            # Start optimization if we have tech stack info
            if "tech_stack" in self.working_memory:
                self._start_optimization_job()
        else:
            self.log_warning("No files found in code generation message")
    
    def _handle_tech_stack_updated(self, message: Dict[str, Any]) -> None:
        """Handle tech stack update messages"""
        self.log_info("Received tech stack update message")
        
        if 'tech_stack' in message and isinstance(message['tech_stack'], dict):
            self.working_memory["tech_stack"] = message['tech_stack']
            
            # Start optimization if we have pending files
            if "pending_files" in self.working_memory:
                self._start_optimization_job()
    
    def _handle_optimization_priority(self, message: Dict[str, Any]) -> None:
        """Handle optimization priority update messages"""
        if "priority_files" in message:
            self.log_info(f"Received optimization priority for {len(message['priority_files'])} files")
            self.working_memory["priority_files"] = message["priority_files"]
    
    def _handle_quality_analysis_completed(self, message: Dict[str, Any]) -> None:
        """Handle quality analysis completion messages"""
        self.log_info("Received quality analysis completion message")
        
        payload = message.get("payload", {})
        if payload.get("quality_score", 10) < 7:  # If quality is below 7/10
            self.log_info(f"Quality analysis shows room for improvement (score: {payload.get('quality_score', 'unknown')})")
            # Could trigger additional optimization here
    
    def _handle_implementation_plan_created(self, message: Dict[str, Any]) -> None:
        """Handle implementation plan creation messages"""
        self.log_info("Received implementation plan creation message")
        
        payload = message.get("payload", {})
        if "plan" in payload:
            self.working_memory["implementation_plan"] = payload["plan"]
            self.log_info("Stored implementation plan for optimization context")
    
    def _start_optimization_job(self) -> None:
        """Start optimization job with pending files and tech stack"""
        if "pending_files" in self.working_memory and "tech_stack" in self.working_memory:
            files = self.working_memory["pending_files"]
            tech_stack = self.working_memory["tech_stack"]
            
            self.log_info(f"Starting optimization job for {len(files)} files")
            
            # Create minimal system_design to satisfy interface
            system_design = {"architecture_pattern": tech_stack.get("architecture_pattern", "MVC")}
            
            # Start optimization
            self._generate_code(
                llm=self.llm,
                invoke_config={"agent_context": f"{self.agent_name}:scheduled_optimization"},
                tech_stack=tech_stack,
                system_design=system_design,
                generated_files=files
            )
            
            # Clear pending files
            del self.working_memory["pending_files"]
    
    def _create_empty_output(self, message: str) -> Dict[str, Any]:
        """Create empty output when no files can be optimized"""
        return CodeGenerationOutput(
            generated_files=[],
            summary=message,
            status="error",
            metadata={
                "error": message,
                "agent": self.agent_name,
                "timestamp": datetime.now().isoformat()
            }
        ).dict()
    
    def _extract_files_from_message(self, message: Dict[str, Any]) -> Dict[str, str]:
        """Extract files from message format"""
        files = {}
        
        # Check various possible locations
        if "payload" in message:
            payload = message["payload"]
            
            # Check for standard format
            if "generated_files" in payload:
                files_data = payload["generated_files"]
                if isinstance(files_data, list):
                    for file_entry in files_data:
                        if isinstance(file_entry, dict) and "file_path" in file_entry and "content" in file_entry:
                            files[file_entry["file_path"]] = file_entry["content"]
            
            # Check for legacy/alternate formats
            elif "files" in payload and isinstance(payload["files"], dict):
                files = payload["files"]
            
            # Check component-specific keys
            component_keys = ["backend_files", "frontend_files", "database_files"]
            for key in component_keys:
                if key in payload and isinstance(payload[key], dict):
                    files.update(payload[key])
        
        return files
    
    def _collect_all_generated_files(self, kwargs: Dict[str, Any]) -> Dict[str, str]:
        """Collect all generated files from various sources in kwargs"""
        all_files = {}
        
        # Check for the main generated_files parameter
        if "generated_files" in kwargs:
            files_data = kwargs["generated_files"]
            if isinstance(files_data, dict):
                all_files.update(files_data)
            elif isinstance(files_data, list):
                for file_entry in files_data:
                    if isinstance(file_entry, dict) and "file_path" in file_entry and "content" in file_entry:
                        all_files[file_entry["file_path"]] = file_entry["content"]
        
        # Check for component-specific result objects
        component_keys = [
            "architecture_generation_result",
            "database_generation_result",
            "backend_code_generation_result",
            "frontend_code_generation_result",
            "integration_generation_result"
        ]
        
        for component_key in component_keys:
            if component_key in kwargs and isinstance(kwargs[component_key], dict):
                component_results = kwargs[component_key]
                
                if "generated_files" in component_results:
                    files_data = component_results["generated_files"]
                    
                    if isinstance(files_data, list):
                        for file_entry in files_data:
                            if isinstance(file_entry, dict) and "file_path" in file_entry and "content" in file_entry:
                                all_files[file_entry["file_path"]] = file_entry["content"]
        
        return all_files
    
    def _extract_architecture_pattern(self, tech_stack: Dict[str, Any], system_design: Dict[str, Any]) -> str:
        """Extract architecture pattern from tech stack or system design"""
        # Check tech stack first
        if isinstance(tech_stack, dict) and "architecture_pattern" in tech_stack:
            return tech_stack["architecture_pattern"]
        
        # Check system design next
        if isinstance(system_design, dict):
            if "architecture_pattern" in system_design:
                return system_design["architecture_pattern"]
            elif "architecture" in system_design and isinstance(system_design["architecture"], dict):
                arch = system_design["architecture"]
                if "pattern" in arch:
                    return arch["pattern"]
                elif "type" in arch:
                    return arch["type"]
                elif "style" in arch:
                    return arch["style"]
        
        # Default value
        return "MVC"
    
    def _categorize_files(self, files: Dict[str, str]) -> Dict[str, Dict[str, str]]:
        """Categorize files by type for targeted optimization"""
        categories = {
            "backend": {},
            "frontend": {},
            "database": {},
            "config": {},
            "other": {}
        }
        
        for file_path, content in files.items():
            # Extract file extension
            ext = os.path.splitext(file_path)[1].lower()
            
            # Categorize by extension and path patterns
            if any(pattern in file_path.lower() for pattern in [
                "model", "repository", "dao", "entity", "database", "schema", "migration"
            ]) or ext in [".sql"]:
                categories["database"][file_path] = content
            
            elif any(pattern in file_path.lower() for pattern in [
                "component", "view", "page", "screen", "ui", "widget"
            ]) or ext in [".jsx", ".tsx", ".vue", ".svelte", ".html", ".css", ".scss"]:
                categories["frontend"][file_path] = content
            
            elif any(pattern in file_path.lower() for pattern in [
                "controller", "service", "api", "handler", "middleware", "route", "util"
            ]):
                categories["backend"][file_path] = content
            
            elif any(pattern in file_path.lower() for pattern in [
                "config", "setting", "env"
            ]) or ext in [".json", ".yml", ".yaml", ".toml", ".ini", ".properties"]:
                categories["config"][file_path] = content
            
            else:
                # Default category
                categories["other"][file_path] = content
        
        return categories
    
    def _select_files_to_optimize(self, categorized_files: Dict[str, Dict[str, str]], 
                                max_files: int = 20) -> Dict[str, str]:
        """Select high-priority files for optimization"""
        selected_files = {}
        
        # Define quota per category to ensure balanced optimization
        quotas = {
            "backend": int(max_files * 0.4),  # 40% backend focus
            "frontend": int(max_files * 0.3),  # 30% frontend focus
            "database": int(max_files * 0.2),  # 20% database focus
            "config": int(max_files * 0.05),   # 5% config focus
            "other": int(max_files * 0.05)     # 5% other files
        }
        
        # Fill any remaining slots to backend
        remaining = max_files - sum(quotas.values())
        if remaining > 0:
            quotas["backend"] += remaining
        
        # Priority patterns to look for in each category
        priority_patterns = {
            "backend": ["service", "controller", "api", "main"],
            "frontend": ["app", "main", "index", "component", "container"],
            "database": ["model", "entity", "repository"],
            "config": ["config", "settings"],
            "other": ["util", "helper", "common"]
        }
        
        # For each category, select files up to quota, prioritizing by patterns
        for category, files in categorized_files.items():
            # Get limit for this category
            limit = quotas[category]
            
            if not files or limit <= 0:
                continue
                
            # Get priority files first
            priority_files = {}
            for pattern in priority_patterns[category]:
                for file_path, content in files.items():
                    if pattern in file_path.lower() and len(priority_files) < limit:
                        priority_files[file_path] = content
            
            # If we still have quota, add other files
            remaining_quota = limit - len(priority_files)
            
            if remaining_quota > 0:
                # Add non-priority files up to quota
                for file_path, content in files.items():
                    if file_path not in priority_files and len(priority_files) < limit:
                        priority_files[file_path] = content
                        if len(priority_files) >= limit:
                            break
            
            # Add selected files to result
            selected_files.update(priority_files)
        
        return selected_files
    
    def _prioritize_files_by_feedback(self, files: Dict[str, str], 
                                   feedback: Dict[str, Any]) -> Dict[str, str]:
        """Reorder files based on code review feedback"""
        if not feedback or not isinstance(feedback, dict):
            return files
        
        # Extract file paths mentioned in feedback
        feedback_files = []
        
        # Look for file paths in various feedback structures
        for key, value in feedback.items():
            if isinstance(value, dict) and "file_path" in value:
                feedback_files.append(value["file_path"])
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and "file_path" in item:
                        feedback_files.append(item["file_path"])
                    elif isinstance(item, str) and "/" in item:
                        # Assume strings with / might be file paths
                        feedback_files.append(item)
        
        # Create a new ordered dict with feedback files first
        ordered_files = {}
        
        # First add files mentioned in feedback
        for file_path in feedback_files:
            if file_path in files:
                ordered_files[file_path] = files[file_path]
                
        # Then add remaining files
        for file_path, content in files.items():
            if file_path not in ordered_files:
                ordered_files[file_path] = content
                
        return ordered_files
    
    def _group_files_by_language(self, files: Dict[str, str]) -> Dict[str, Dict[str, str]]:
        """Group files by programming language"""
        grouped = {}
        
        for file_path, content in files.items():
            language = self._determine_file_language(file_path)
            
            if language not in grouped:
                grouped[language] = {}
                
            grouped[language][file_path] = content
            
        return grouped
    
    def _determine_file_language(self, file_path: str) -> str:
        """Determine programming language from file extension"""
        ext = os.path.splitext(file_path)[1].lower()
        
        language_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.cs': 'csharp',
            '.go': 'go',
            '.rb': 'ruby',
            '.php': 'php',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.rs': 'rust',
            '.html': 'html',
            '.css': 'css',
            '.scss': 'scss',
            '.json': 'json',
            '.yml': 'yaml',
            '.yaml': 'yaml',
            '.sql': 'sql',
            '.md': 'markdown'
        }
        
        return language_map.get(ext, 'unknown')
    
    def _get_language_best_practices(self, language: str) -> str:
        """Get language-specific best practices"""
        best_practices = self.language_best_practices.get(language.lower(), "")
        
        if not best_practices:
            return "standard code quality and performance best practices"
            
        return best_practices
    
    def _initialize_language_best_practices(self) -> Dict[str, str]:
        """Initialize language-specific best practices"""
        return {
            "python": "PEP 8 style guide, type hints, docstrings, list/dict comprehensions, f-strings, context managers",
            "javascript": "ES6+ features, const/let over var, arrow functions, destructuring, async/await, modules",
            "typescript": "Strong typing, interfaces, type guards, readonly properties, generics, ESLint rules",
            "java": "Clean code principles, immutable objects, try-with-resources, streams API, Optional<>",
            "csharp": "SOLID principles, nullable reference types, pattern matching, expression-bodied members, LINQ",
            "go": "Error handling, defer statements, slices over arrays, goroutines with proper synchronization",
            "html": "Semantic HTML5 elements, accessibility attributes, responsive design patterns",
            "css": "BEM naming convention, CSS variables, flexbox/grid layouts, responsive design",
            "scss": "Nested selectors, variables, mixins, partial files, CSS modules"
        }
    
    def _get_optimization_rag_context(self, language: str, architecture_pattern: str) -> str:
        """Get RAG context for optimization based on language and architecture"""
        if not self.rag_retriever:
            return ""
            
        try:
            # Create targeted query for more relevant results
            query = f"{language} code optimization best practices {architecture_pattern} architecture"
            
            # Get RAG context
            docs = self.rag_retriever.get_relevant_documents(query, k=3)
            
            if not docs:
                return ""
                
            # Combine context with size limit
            context = []
            total_chars = 0
            
            for doc in docs:
                content = doc.page_content
                
                # Check if adding this would exceed our limit
                if total_chars + len(content) > self.max_context_chars["rag"]:
                    # Only add a portion if we're over limit
                    remaining = self.max_context_chars["rag"] - total_chars
                    if remaining > 100:  # Only add if we can include meaningful content
                        context.append(content[:remaining] + "...")
                    break
                    
                context.append(content)
                total_chars += len(content)
            
            if context:
                return "## Best Practices Context\n" + "\n\n".join(context)
            else:
                return ""
                
        except Exception as e:
            self.log_warning(f"Error retrieving RAG context: {str(e)}")
            return ""
    
    def _create_tech_stack_summary(self, tech_stack: Dict[str, Any]) -> str:
        """Create a concise summary of the tech stack for prompts"""
        if not tech_stack:
            return "Standard web application stack"
            
        summary_parts = []
        
        try:
            # Extract backend info
            if "backend" in tech_stack:
                backend = tech_stack["backend"]
                if isinstance(backend, dict):
                    lang = backend.get("language", "")
                    framework = backend.get("framework", "")
                    if lang and framework:
                        summary_parts.append(f"{lang.capitalize()} {framework.capitalize()} backend")
                    elif framework:
                        summary_parts.append(f"{framework.capitalize()} backend")
                    elif lang:
                        summary_parts.append(f"{lang.capitalize()} backend")
                elif isinstance(backend, str):
                    summary_parts.append(f"{backend} backend")
            
            # Extract frontend info
            if "frontend" in tech_stack:
                frontend = tech_stack["frontend"]
                if isinstance(frontend, dict):
                    framework = frontend.get("framework", frontend.get("name", ""))
                    if framework:
                        summary_parts.append(f"{framework.capitalize()} frontend")
                elif isinstance(frontend, str):
                    summary_parts.append(f"{frontend} frontend")
            
            # Extract database info
            if "database" in tech_stack:
                db = tech_stack["database"]
                if isinstance(db, dict):
                    db_type = db.get("type", db.get("name", ""))
                    if db_type:
                        summary_parts.append(f"{db_type.capitalize()} database")
                elif isinstance(db, str):
                    summary_parts.append(f"{db} database")
            
            if summary_parts:
                return ", ".join(summary_parts)
            else:
                return "Standard web application stack"
                
        except Exception as e:
            self.log_warning(f"Error creating tech stack summary: {str(e)}")
            return "Standard web application stack"
    
    def _create_optimization_goals(self, tech_stack: Dict[str, Any], 
                                system_design: Dict[str, Any],
                                requirements_analysis: Dict[str, Any]) -> str:
        """Create optimization goals based on project context"""
        # Default optimization goals
        default_goals = """
        1. Performance improvement - Optimize code for better execution speed
        2. Code quality - Improve readability, maintainability, and adherence to best practices
        3. Bug prevention - Fix potential bugs and edge cases
        4. Security improvements - Address security vulnerabilities
        5. Resource efficiency - Optimize memory usage and resource management
        """
        
        try:
            # Extract project type for specialized goals
            project_type = "web"  # default
            
            if "project_type" in system_design:
                project_type = system_design["project_type"]
            elif "project_type" in requirements_analysis:
                project_type = requirements_analysis["project_type"]
            elif "application_type" in system_design:
                project_type = system_design["application_type"]
            
            # Set specialized goals based on project type
            if project_type.lower() in ["web", "webapp", "website"]:
                return """
                1. Performance optimization - Improve page load times and response speed
                2. Security hardening - Address common web vulnerabilities (XSS, CSRF, etc.)
                3. Frontend optimization - Enhance component reusability and state management
                4. API efficiency - Optimize API calls and data handling
                5. Responsive design - Ensure proper responsive behavior
                """
            
            elif project_type.lower() in ["mobile", "app", "android", "ios"]:
                return """
                1. Mobile performance - Optimize for battery life and resource constraints
                2. UI responsiveness - Ensure smooth user interactions
                3. Data efficiency - Minimize network usage and optimize local storage
                4. API integration - Improve error handling and offline capabilities
                5. Cross-platform compatibility - Ensure consistent behavior
                """
                
            elif project_type.lower() in ["data", "analytics", "ml", "ai"]:
                return """
                1. Algorithm efficiency - Optimize data processing algorithms
                2. Memory optimization - Reduce memory footprint for data operations
                3. Error handling - Improve robustness against malformed or missing data
                4. Parallelization - Enhance parallel processing capabilities
                5. Code readability - Improve documentation of complex logic
                """
                
            elif project_type.lower() in ["iot", "embedded"]:
                return """
                1. Resource efficiency - Optimize for limited hardware resources
                2. Power consumption - Reduce unnecessary operations
                3. Reliability - Improve error recovery and fault tolerance
                4. Connectivity - Enhance connection handling and recovery
                5. Security - Address IoT-specific security concerns
                """
            
            else:
                return default_goals
                
        except Exception as e:
            self.log_warning(f"Error creating optimization goals: {str(e)}")
            return default_goals
    
    def _format_files_for_prompt(self, files: Dict[str, str]) -> str:
        """Format files for inclusion in the prompt"""
        # We need to balance showing enough code with token limits
        formatted_files = []
        total_chars = 0
        max_chars = self.max_context_chars["code_file"]
        
        for file_path, content in files.items():
            # Add file path
            formatted_file = f"### {file_path}\n"
            
            # Truncate content if it's too large
            if len(content) > max_chars / len(files):
                # Truncate smartly - keep beginning and end
                chars_per_file = int(max_chars / len(files))
                first_part = int(chars_per_file * 0.6)  # 60% for beginning
                last_part = int(chars_per_file * 0.4)   # 40% for end
                
                truncated = content[:first_part] + "\n\n[...truncated...]\n\n" + content[-last_part:]
                formatted_file += f"```\n{truncated}\n```"
            else:
                formatted_file += f"```\n{content}\n```"
            
            # Check if adding this file would exceed our limit
            if total_chars + len(formatted_file) > max_chars:
                # We're over limit, just add file path with note
                formatted_files.append(f"### {file_path}\n```\n[Content too large for context]\n```")
            else:
                formatted_files.append(formatted_file)
                total_chars += len(formatted_file)
        
        return "\n\n".join(formatted_files)
    
    def _prepare_feedback_context(self, code_review_feedback: Optional[Dict[str, Any]], 
                               files: Dict[str, str]) -> str:
        """Prepare feedback context for the optimization prompt"""
        if not code_review_feedback:
            return ""
            
        feedback_lines = ["## Code Review Feedback"]
        
        try:
            # Look for feedback specifically about files we're optimizing
            file_specific_feedback = {}
            
            # First look for direct file mapping
            for file_path in files.keys():
                if file_path in code_review_feedback:
                    feedback = code_review_feedback[file_path]
                    file_specific_feedback[file_path] = feedback
            
            # Look in common structures
            if "issues" in code_review_feedback:
                issues = code_review_feedback["issues"]
                if isinstance(issues, list):
                    for issue in issues:
                        if isinstance(issue, dict) and "file_path" in issue:
                            file_path = issue["file_path"]
                            if file_path in files:
                                if file_path not in file_specific_feedback:
                                    file_specific_feedback[file_path] = []
                                file_specific_feedback[file_path].append(issue)
            
            # Format file-specific feedback
            for file_path, feedback in file_specific_feedback.items():
                feedback_lines.append(f"\n### {file_path}")
                
                if isinstance(feedback, list):
                    for item in feedback:
                        if isinstance(item, dict):
                            issue = item.get("issue", item.get("description", ""))
                            severity = item.get("severity", "")
                            feedback_lines.append(f"- {severity + ': ' if severity else ''}{issue}")
                        elif isinstance(item, str):
                            feedback_lines.append(f"- {item}")
                elif isinstance(feedback, dict):
                    for key, value in feedback.items():
                        feedback_lines.append(f"- {key}: {value}")
                elif isinstance(feedback, str):
                    feedback_lines.append(f"- {feedback}")
            
            # Add general feedback if we have it
            if "general" in code_review_feedback:
                feedback_lines.append("\n### General Feedback")
                general = code_review_feedback["general"]
                
                if isinstance(general, list):
                    for item in general:
                        feedback_lines.append(f"- {item}")
                elif isinstance(general, str):
                    feedback_lines.append(f"- {general}")
                elif isinstance(general, dict):
                    for key, value in general.items():
                        feedback_lines.append(f"- {key}: {value}")
            
            return "\n".join(feedback_lines)
            
        except Exception as e:
            self.log_warning(f"Error preparing feedback context: {str(e)}")
            return ""
    
    def _get_adjusted_temperature(self, language: str, is_revision: bool) -> float:
        """Get adjusted temperature based on language and revision status"""
        # Base temperature - relatively low for code optimization
        base_temp = 0.1
        
        # Language adjustments - some languages need more creativity in optimization
        language_adjustments = {
            "python": 0.00,      # Python has very clear best practices (PEP 8)
            "javascript": 0.02,  # JavaScript has more style variations
            "typescript": 0.01,  # TypeScript is more strict than JS but less than Python
            "java": -0.01,       # Java is very standardized
            "csharp": -0.01,     # C# is very standardized
            "html": 0.00,         
            "css": 0.02,         # CSS has many ways to achieve the same thing
            "scss": 0.02,
            "unknown": 0.03      # Unknown languages might need more creative approaches
        }
        
        # Get language adjustment with default
        adjustment = language_adjustments.get(language.lower(), 0.0)
        
        # If this is a revision based on feedback, increase temperature slightly
        # to encourage more creative solutions to identified problems
        if is_revision:
            adjustment += 0.02
            
        # Apply adjustment with bounds
        return max(0.05, min(base_temp + adjustment, 0.2))
    
    def _parse_optimizer_response(self, response: str) -> List[GeneratedFile]:
        """Parse optimizer response into GeneratedFile objects"""
        # Use the standard parse_llm_output_into_files utility
        parsed_files = parse_llm_output_into_files(response)
        
        # Extract explanation for each file
        explanations = {}
        matches = re.finditer(r'### EXPLANATION: (.*?)$(.*?)(?=###|\Z)', response, re.MULTILINE | re.DOTALL)
        
        for match in matches:
            file_path = match.group(1).strip()
            explanation = match.group(2).strip()
            explanations[file_path] = explanation
        
        # Enhance the GeneratedFile objects with explanations
        for file in parsed_files:
            if file.file_path in explanations:
                file.purpose = f"Optimized: {explanations[file.file_path]}"
            else:
                file.purpose = "Optimized file"
            
            # Set status to success
            file.status = "success"
        
        return parsed_files
    
    def _create_directories_from_files(self, generated_files: List[GeneratedFile]) -> None:
        """Create all necessary directories based on file paths"""
        directories = set()
        
        for file_data in generated_files:
            dir_path = os.path.dirname(file_data.file_path)
            
            if dir_path:
                directories.add(dir_path)
        
        # Create all unique directories
        for directory in directories:
            try:
                full_path = os.path.join(self.output_dir, directory)
                os.makedirs(full_path, exist_ok=True)
                self.log_info(f"Created directory: {directory}")
            except Exception as e:
                self.log_error(f"Failed to create directory {directory}: {str(e)}")
    
    def _save_files(self, generated_files: List[GeneratedFile]) -> None:
        """Save all generated files to disk"""
        for file in generated_files:
            try:
                # Ensure the directory exists
                file_path = os.path.join(self.output_dir, file.file_path)
                directory = os.path.dirname(file_path)
                os.makedirs(directory, exist_ok=True)
                
                # Write file content
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(file.content)
                    
                self.log_info(f"Saved optimized file: {file.file_path}")
                
            except Exception as e:
                self.log_error(f"Failed to save file {file.file_path}: {str(e)}")

    def run(self, work_item: WorkItem, state: Dict[str, Any]) -> CodeGenerationOutput:
        """
        Optimizes specific code files based on a work item.
        """
        logger.info(f"CodeOptimizerAgent starting work item: {work_item.id}")

        # The optimizer needs context of the whole project so far.
        # We can collect all previously generated files from the completed work items.
        all_files = []
        for completed_item in state.get("completed_work_items", []):
            code_gen_result = completed_item.get("code_generation_result", {})
            all_files.extend(code_gen_result.get("generated_files", []))
        
        # Create a dictionary of file paths to content for easier access
        project_context_files = {f['path']: f['content'] for f in all_files}

        prompt = self._create_work_item_prompt(work_item, project_context_files, state)

        response = self.llm.invoke(prompt)
        content = response.content if hasattr(response, 'content') else str(response)
        
        # The optimizer's output will contain the full, modified files.
        optimized_files = parse_llm_output_into_files(content)

        return CodeGenerationOutput(
            generated_files=[GeneratedFile(**f) for f in optimized_files],
            summary=f"Optimized {len(optimized_files)} files for work item {work_item.id}."
        )

    def _create_work_item_prompt(self, work_item: WorkItem, project_files: Dict[str, str], state: Dict[str, Any]) -> str:
        
        files_to_optimize_str = ""
        # The work item's acceptance criteria should list the files to optimize.
        files_to_optimize_paths = work_item.acceptance_criteria
        
        for path in files_to_optimize_paths:
            if path in project_files:
                files_to_optimize_str += f"### FILE: {path}\n```\n{project_files[path]}\n```\n\n"

        if not files_to_optimize_str:
            return "No files found to optimize for this work item."

        return f"""
        You are a world-class software engineer specializing in code optimization.
        Your task is to analyze the provided code snippet and rewrite it to be more performant, readable, and maintainable, without altering its core functionality.
        You should consider algorithm complexity, memory usage, and best practices for the given language.

        {files_to_optimize_str}

        **Technology Context:**
        - Language/Framework: {self._determine_file_language(files_to_optimize_paths[0])}

        **Optimization Goals:**
        1. **Performance:** Optimize algorithms, reduce unnecessary computations.
        2. **Readability:** Improve variable names, add comments where necessary, simplify logic.
        3. **Best Practices:** Refactor to align with modern best practices for the language.
        4. **Security:** Patch any obvious security vulnerabilities.

        **Instructions:**
        - Return the COMPLETE, optimized versions of the files listed above.
        - Do NOT modify any other files.
        - Use the multi-file output format.

        CRITICAL OUTPUT FORMAT - FOLLOW EXACTLY:
        ### FILE: path/to/optimized/file.ext
        ```filetype
        // The *full*, optimized content of the file goes here.
        ```
        """

    def get_default_response(self) -> Dict[str, Any]:
        """Returns a default error response."""
        return self._create_empty_output("Failed to optimize code files")