import json
import os
import shutil
import time
from typing import Dict, Any, List, Optional, Tuple
import google.api_core.exceptions
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from tools.code_execution_tool import CodeExecutionTool
from langchain_core.retrievers import BaseRetriever

# Add monitoring import
import monitoring
from .base_agent import BaseAgent

class CodeGenerationAgent(BaseAgent):
    
    def __init__(self, llm: BaseLanguageModel, memory, output_dir: str, code_execution_tool: CodeExecutionTool, rag_retriever: BaseRetriever = None):
        super().__init__(
            llm=llm,
            memory=memory,
            agent_name="Code Generation Agent",
            temperature=0.1,  # Very low for deterministic code
            rag_retriever=rag_retriever
        )
        self.output_dir = output_dir
        self.code_execution_tool = code_execution_tool
        
        # Track dependencies between files
        self.file_dependencies = {}
        # Track successful compilations
        self.successful_compilations = set()
        
        # Initialize prompt templates
        self.file_structure_template = PromptTemplate(
            template="""
            You are an expert Software Engineer AI specializing in creating optimal file structures.
            Based on the project analysis, propose a comprehensive file and directory structure.

            **Project Summary:**
            Backend: {backend_name} with {backend_framework}
            Database: {database_type}
            Architecture: {architecture_pattern}
            
            **Key Requirements:**
            {requirements_summary}

            **System Design Modules:**
            {modules_summary}

            **Guidelines:**
            1. Follow standard practices for the selected technology stack
            2. Include configurations, documentation, and tests
            3. Organize modules according to the architecture pattern
            4. Include necessary boilerplate files (gitignore, README, etc.)
            5. Structure the project for maintainability and clear separation of concerns

            {format_instructions} 

            Output a JSON object where:
            - Keys are file paths (use "/" for directories)
            - Values describe the purpose of each file
            - End directory paths with "/"
            - Include detailed descriptions for key files
            """,
            input_variables=["backend_name", "backend_framework", "database_type", "architecture_pattern", 
                            "requirements_summary", "modules_summary"],
            partial_variables={"format_instructions": self.json_parser.get_format_instructions()}
        )
        
        self.code_generation_template = PromptTemplate(
            template="""
            You are an expert Software Engineer AI specialized in writing high-quality, production-grade code.
            
            **Your task:** Generate complete code for: `{file_path}`

            **Project Context:**
            {context_summary}

            **Technology Stack:**
            - Backend: {backend_stack}
            - Database: {database_type}
            - Architecture: {architecture_pattern}

            **File Purpose:**
            {file_purpose}

            **Related Files:**
            {related_files}

            **Dependencies:**
            {dependencies}

            **Additional Context:**
            {rag_context}

            **Previous Errors/Feedback:**
            {error_feedback}

            **Instructions:**
            1. Generate ONLY the complete code for `{file_path}` with no explanations outside the code
            2. Include proper imports, error handling, and documentation
            3. Follow established patterns for the technology stack
            4. Ensure the code is directly runnable without modifications
            5. Include thorough comments explaining complex sections
            
            Write ONLY THE CODE with no markdown formatting. Do not include ```python or ``` tags.
            """,
            input_variables=["file_path", "context_summary", "backend_stack", "database_type", 
                           "architecture_pattern", "file_purpose", "related_files", 
                           "dependencies", "rag_context", "error_feedback"]
        )
        
        self.dependency_analysis_template = PromptTemplate(
            template="""
            You are an expert Software Architect AI.
            Analyze the given file structure and identify dependencies between files.

            **File Structure:**
            {file_structure}

            **Technology Stack:**
            Backend: {backend_stack}
            Database: {database_type}
            Architecture: {architecture_pattern}

            {format_instructions}

            Identify dependencies between files and output a JSON where:
            - Keys are file paths
            - Values are arrays of file paths that the key depends on
            - Only include actual code files (ignore documentation, config files that don't affect code execution)
            - Focus on import/include dependencies and execution order
            """,
            input_variables=["file_structure", "backend_stack", "database_type", "architecture_pattern"],
            partial_variables={"format_instructions": self.json_parser.get_format_instructions()}
        )
        
        self.code_refinement_template = PromptTemplate(
            template="""
            You are an expert Code Refinement AI.
            Review and improve the following code for `{file_path}`.

            **Original Code:**
            {original_code}

            **Error/Issue:**
            {error_message}

            **Project Context:**
            {context_summary}

            **Related Files Content:**
            {related_files_content}

            **Instructions:**
            1. Fix all errors and issues mentioned
            2. Maintain the same functionality
            3. Optimize and improve code quality
            4. Ensure compatibility with related files
            
            Generate ONLY the improved code with no explanations. Do not include markdown formatting.
            """,
            input_variables=["file_path", "original_code", "error_message", 
                           "context_summary", "related_files_content"]
        )
    
    def _generate_file_structure(self, brd_analysis: dict, tech_stack_recommendation: dict, system_design: dict) -> dict:
        """Generate comprehensive project file structure with detailed context."""
        self.log_info("Generating project file structure")
        
        # Extract key information for file structure generation
        backend_name = tech_stack_recommendation.get('backend', {}).get('language', 'Python')
        backend_framework = tech_stack_recommendation.get('backend', {}).get('framework', 'Flask')
        database_type = tech_stack_recommendation.get('database', {}).get('type', 'SQLite')
        architecture_pattern = tech_stack_recommendation.get('architecture_pattern', 'MVC')
        
        # Create concise requirements summary
        requirements_summary = self._create_requirements_summary(brd_analysis)
        
        # Create modules summary from system design
        modules_summary = self._create_modules_summary(system_design)

        try:
            # Set the prompt template for this specific operation
            self.prompt_template = self.file_structure_template
            
            # Use BaseAgent's execute_llm_chain with improved context
            response = self.execute_llm_chain({
                "backend_name": backend_name,
                "backend_framework": backend_framework,
                "database_type": database_type,
                "architecture_pattern": architecture_pattern,
                "requirements_summary": requirements_summary,
                "modules_summary": modules_summary
            })
            
            # Validate file structure response
            if not response or not isinstance(response, dict):
                self.log_warning("Invalid file structure format returned, using default")
                return self._get_default_file_structure(backend_name, backend_framework)
                
            # Clean up file paths (normalize slashes, handle directories)
            cleaned_structure = self._normalize_file_paths(response)
            
            # Analyze dependencies between files
            self.file_dependencies = self._analyze_file_dependencies(cleaned_structure, 
                                                                   backend_name, 
                                                                   backend_framework,
                                                                   database_type,
                                                                   architecture_pattern)
            
            self.log_info(f"Generated file structure with {len(cleaned_structure)} files/directories")
            return cleaned_structure
        except Exception as e:
            self.log_error(f"File structure generation failed: {e}")
            return self._get_default_file_structure(backend_name, backend_framework)
    
    def _normalize_file_paths(self, file_structure: dict) -> dict:
        """Normalize file paths and ensure directories are properly marked."""
        normalized = {}
        for path, description in file_structure.items():
            # Normalize slashes
            norm_path = path.replace('\\', '/')
            
            # Handle directories
            if norm_path.endswith('/') or (isinstance(description, str) and 
                                         any(term in description.lower() for term in ["directory", "folder", "module"])):
                if not norm_path.endswith('/'):
                    norm_path = f"{norm_path}/"
                
            normalized[norm_path] = description
        
        return normalized
    
    def _analyze_file_dependencies(self, file_structure: dict, backend_name: str, 
                                 backend_framework: str, database_type: str,
                                 architecture_pattern: str) -> dict:
        """Analyze and determine dependencies between files."""
        try:
            self.prompt_template = self.dependency_analysis_template
            
            # Convert file structure to readable format for the LLM
            file_structure_text = json.dumps(file_structure, indent=2)
            
            # Execute dependency analysis
            dependencies = self.execute_llm_chain({
                "file_structure": file_structure_text,
                "backend_stack": f"{backend_name} + {backend_framework}",
                "database_type": database_type,
                "architecture_pattern": architecture_pattern
            })
            
            if not dependencies or not isinstance(dependencies, dict):
                self.log_warning("Invalid dependency analysis result, using empty dependencies")
                return {}
                
            self.log_info(f"Identified dependencies between {len(dependencies)} files")
            return dependencies
        except Exception as e:
            self.log_warning(f"Dependency analysis failed: {e}")
            return {}
    
    def _create_requirements_summary(self, brd_analysis: dict) -> str:
        """Create structured requirements summary from BRD analysis."""
        summary_parts = []
        
        # Project name and description
        project_name = brd_analysis.get('project_overview', {}).get('project_name', 'Unknown Project')
        project_desc = brd_analysis.get('project_overview', {}).get('description', '')
        summary_parts.append(f"Project: {project_name} - {project_desc[:150]}...")
        
        # Key functional requirements (limit to 5)
        func_reqs = brd_analysis.get('functional_requirements', [])[:5]
        if func_reqs:
            summary_parts.append("Functional Requirements:")
            for req in func_reqs:
                summary_parts.append(f"- {req.get('description', '')[:100]}")
        
        # Non-functional requirements (main categories)
        nfr = brd_analysis.get('non_functional_requirements', {})
        nfr_summary = []
        for category, reqs in nfr.items():
            if reqs and isinstance(reqs, list) and len(reqs) > 0:
                nfr_summary.append(f"{category.capitalize()}: {reqs[0][:50]}...")
        
        if nfr_summary:
            summary_parts.append("Non-Functional Requirements:")
            summary_parts.extend([f"- {item}" for item in nfr_summary[:3]])
        
        # Data requirements (key entities)
        data_reqs = brd_analysis.get('data_requirements', [])[:3]
        if data_reqs:
            entities = [entity.get('entity', '') for entity in data_reqs]
            summary_parts.append(f"Key Data Entities: {', '.join(entities)}")
        
        return '\n'.join(summary_parts)
    
    def _create_modules_summary(self, system_design: dict) -> str:
        """Create summary of system design modules."""
        modules = system_design.get('main_modules', [])
        if not modules:
            return "No specific modules defined in system design."
            
        summary_parts = ["Modules:"]
        for module in modules:
            name = module.get('name', '')
            purpose = module.get('purpose', '')[:100]
            components = ', '.join(module.get('components', [])[:3])
            
            if name:
                summary_parts.append(f"- {name}: {purpose}")
                if components:
                    summary_parts.append(f"  Components: {components}")
        
        return '\n'.join(summary_parts)
    
    def _get_file_purpose(self, file_path: str, file_structure: dict) -> str:
        """Get the purpose of a file from the file structure."""
        # Try exact path match
        if file_path in file_structure:
            return str(file_structure[file_path])
            
        # Try normalized path
        normalized = file_path.replace('\\', '/')
        if normalized in file_structure:
            return str(file_structure[normalized])
            
        return "No specific purpose defined"
    
    def _get_related_files(self, file_path: str) -> list:
        """Get files related to the specified file based on dependencies."""
        related = []
        
        # Files that this file depends on
        if file_path in self.file_dependencies:
            related.extend(self.file_dependencies[file_path])
            
        # Files that depend on this file
        for dep_file, dependencies in self.file_dependencies.items():
            if file_path in dependencies:
                related.append(dep_file)
                
        return related
    
    def _generate_code_with_context(self, file_path: str, context_summary: str, tech_stack: dict, 
                                  system_design: dict, file_structure: dict, error_feedback: str = "") -> str:
        """Generate code for a file with comprehensive context."""
        
        # Get related files
        related_files = self._get_related_files(file_path)
        related_files_text = "\n".join(related_files)
        
        # Get file purpose 
        file_purpose = self._get_file_purpose(file_path, file_structure)
        
        # Extract tech stack details
        backend = f"{tech_stack.get('backend', {}).get('language', 'Python')} + {tech_stack.get('backend', {}).get('framework', 'Flask')}"
        database = tech_stack.get('database', {}).get('type', 'SQLite')
        architecture = tech_stack.get('architecture_pattern', 'MVC')
        
        # Get specific dependencies for this file
        dependencies = ", ".join(self.file_dependencies.get(file_path, []))
        
        # Get relevant RAG context
        file_extension = os.path.splitext(file_path)[1]
        tech_string = f"{backend} {database} {architecture}"
        rag_query = f"code {file_path} {file_extension} {tech_string} {file_purpose[:50]}"
        rag_context = self.get_rag_context(rag_query)
        
        try:
            # Use temperature binding for code generation
            llm_with_temp = self.llm.bind(temperature=self.temperature)
            
            # Format prompt with context
            prompt = self.code_generation_template.format(
                file_path=file_path,
                context_summary=context_summary,
                backend_stack=backend,
                database_type=database,
                architecture_pattern=architecture,
                file_purpose=file_purpose,
                related_files=related_files_text,
                dependencies=dependencies,
                rag_context=rag_context,
                error_feedback=error_feedback
            )
            
            # Invoke the model
            start_time = time.time()
            response = llm_with_temp.invoke(prompt)
            generation_time = time.time() - start_time
            
            # Extract content from response
            if hasattr(response, 'content'):
                code_content = response.content
            else:
                code_content = str(response)
            
            # Clean the code content
            cleaned_code = self._clean_code_response(code_content)
            
            self.log_info(f"Generated {len(cleaned_code)} bytes for {file_path} in {generation_time:.2f}s")
            return cleaned_code
            
        except Exception as e:
            self.log_error(f"Code generation failed for {file_path}: {e}")
            return ""
    
    def _refine_code(self, file_path: str, original_code: str, error_message: str, 
                   context_summary: str, related_files_content: dict) -> str:
        """Refine code based on error feedback and related files."""
        try:
            # Format related files content for context
            related_content = "\n".join([
                f"### {path}:\n{content[:500]}..." 
                for path, content in related_files_content.items()
            ])
            
            # Use temperature binding for refinement
            llm_with_temp = self.llm.bind(temperature=0.1)
            
            # Format prompt
            prompt = self.code_refinement_template.format(
                file_path=file_path,
                original_code=original_code,
                error_message=error_message,
                context_summary=context_summary,
                related_files_content=related_content
            )
            
            # Invoke the model
            response = llm_with_temp.invoke(prompt)
            
            # Extract content
            if hasattr(response, 'content'):
                refined_code = response.content
            else:
                refined_code = str(response)
            
            # Clean the code
            cleaned_code = self._clean_code_response(refined_code)
            
            self.log_info(f"Successfully refined code for {file_path}")
            return cleaned_code
            
        except Exception as e:
            self.log_warning(f"Code refinement failed for {file_path}: {e}")
            return original_code
    
    def _test_and_refine_code(self, file_path: str, code_content: str, context_summary: str, 
                           file_structure: dict) -> Tuple[str, bool]:
        """Test code and refine if there are errors."""
        full_file_path = os.path.join(self.output_dir, file_path)
        
        # Skip testing for certain file types
        if not self._should_test_file(file_path):
            return code_content, True
        
        try:
            # Write code to file for testing
            os.makedirs(os.path.dirname(full_file_path), exist_ok=True)
            with open(full_file_path, 'w', encoding='utf-8') as f:
                f.write(code_content)
            
            # Test the code
            test_result = self.code_execution_tool.test_file(full_file_path)
            
            if test_result.get("success", False):
                self.log_info(f"Code validation successful for {file_path}")
                self.successful_compilations.add(file_path)
                return code_content, True
            else:
                # Get error message
                error_message = test_result.get("error", "Unknown error")
                self.log_warning(f"Code validation failed for {file_path}: {error_message}")
                
                # Get content of related files for context
                related_files = self._get_related_files(file_path)
                related_files_content = {}
                
                for related_file in related_files:
                    if related_file in self.successful_compilations:
                        try:
                            related_path = os.path.join(self.output_dir, related_file)
                            if os.path.exists(related_path):
                                with open(related_path, 'r', encoding='utf-8') as f:
                                    related_files_content[related_file] = f.read()
                        except Exception:
                            pass
                
                # Refine code
                refined_code = self._refine_code(
                    file_path, 
                    code_content, 
                    error_message, 
                    context_summary, 
                    related_files_content
                )
                
                # Test again with refined code
                with open(full_file_path, 'w', encoding='utf-8') as f:
                    f.write(refined_code)
                
                refined_result = self.code_execution_tool.test_file(full_file_path)
                
                if refined_result.get("success", False):
                    self.log_success(f"Code refinement fixed issues in {file_path}")
                    self.successful_compilations.add(file_path)
                    return refined_code, True
                else:
                    self.log_warning(f"Code refinement still has issues in {file_path}")
                    return refined_code, False
        except Exception as e:
            self.log_error(f"Error during code testing for {file_path}: {e}")
            return code_content, False
            
    def _should_test_file(self, file_path: str) -> bool:
        """Determine if a file should be tested based on its extension and type."""
        # Skip binary files, assets, etc.
        skip_extensions = ['.md', '.txt', '.json', '.yaml', '.yml', '.css', '.svg', 
                          '.png', '.jpg', '.jpeg', '.gif', '.ico', '.env']
        
        # Skip configuration files
        skip_patterns = ['config', 'readme', 'license', 'gitignore', '.env']
        
        file_extension = os.path.splitext(file_path)[1].lower()
        file_name = os.path.basename(file_path).lower()
        
        # Skip based on extension
        if file_extension in skip_extensions:
            return False
            
        # Skip based on filename patterns
        for pattern in skip_patterns:
            if pattern in file_name:
                return False
                
        return True
    
    def _generate_and_refine_code(self, file_path: str, context_summary: str, 
                               tech_stack: dict, system_design: dict, 
                               file_structure: dict, max_retries: int = 3) -> Tuple[str, bool]:
        """Generate code for a single file with built-in testing and refinement."""
        
        code_content = ""
        is_success = False
        error_feedback = ""
        
        for attempt in range(max_retries):
            try:
                # Generate code with context
                code_content = self._generate_code_with_context(
                    file_path, 
                    context_summary, 
                    tech_stack, 
                    system_design,
                    file_structure,
                    error_feedback
                )
                
                if not code_content.strip():
                    error_feedback = f"Empty code generated on attempt {attempt + 1}"
                    continue
                
                # Test and refine the code
                code_content, is_success = self._test_and_refine_code(
                    file_path, 
                    code_content, 
                    context_summary, 
                    file_structure
                )
                
                if is_success:
                    break
                    
                # Update error feedback for next attempt
                error_feedback = f"Code validation failed on attempt {attempt + 1}"
                
            except Exception as e:
                error_feedback = f"Generation error on attempt {attempt + 1}: {str(e)}"
                self.log_warning(f"Code generation attempt {attempt + 1} failed for {file_path}: {e}")
        
        return code_content, is_success
    
    def _clean_code_response(self, code_content: str) -> str:
        """Clean code response by removing markdown fences and extra formatting."""
        cleaned = code_content.strip()
        
        # Remove markdown code blocks
        if cleaned.startswith("```"):
            lines = cleaned.split('\n')
            
            # Find start and end of code block
            start_idx = 0
            end_idx = len(lines)
            
            for i, line in enumerate(lines):
                if line.startswith("```"):
                    start_idx = i
                    break
            
            for i in range(start_idx + 1, len(lines)):
                if lines[i].strip() == "```":
                    end_idx = i
                    break
            
            # Extract code between fences
            cleaned = '\n'.join(lines[start_idx + 1:end_idx])
        
        return cleaned.strip()
    
    def _process_dependencies_order(self, file_structure: dict) -> List[str]:
        """Process files in dependency order for better compilation success."""
        # Start with files that have no dependencies
        processed = []
        remaining = set(k for k in file_structure.keys() if not k.endswith('/'))
        
        # Process files with no dependencies first
        no_deps = []
        for file in remaining:
            if file not in self.file_dependencies or not self.file_dependencies[file]:
                no_deps.append(file)
                
        processed.extend(no_deps)
        remaining -= set(no_deps)
        
        # Process remaining files based on dependency count
        while remaining:
            # Find file with fewest unprocessed dependencies
            best_file = None
            min_deps = float('inf')
            
            for file in remaining:
                deps = self.file_dependencies.get(file, [])
                unprocessed_deps = len([d for d in deps if d in remaining])
                
                if unprocessed_deps < min_deps:
                    min_deps = unprocessed_deps
                    best_file = file
            
            if best_file:
                processed.append(best_file)
                remaining.remove(best_file)
            else:
                # If we can't find a file, add all remaining files
                processed.extend(list(remaining))
                break
                
        # Add directories at the beginning
        directories = [k for k in file_structure.keys() if k.endswith('/')]
        
        return directories + processed
    
    def run(self, brd_analysis: dict, tech_stack_recommendation: dict, system_design: dict, 
            implementation_plan: dict, current_phase: str = None) -> Dict[str, Any]:
        """Generate codebase by phase or as a whole based on implementation plan."""
        self.log_start(f"Starting code generation{f' for phase {current_phase}' if current_phase else ''}")
        
        try:
            # Generate file structure with comprehensive context
            file_structure = self._generate_file_structure(
                brd_analysis, 
                tech_stack_recommendation, 
                system_design
            )
            
            # Filter files by phase if a phase is specified
            if current_phase:
                file_structure = self._filter_files_by_phase(
                    file_structure,
                    current_phase,
                    implementation_plan
                )
                
                if not file_structure:
                    self.log_warning(f"No files identified for phase {current_phase}")
                    return {
                        "status": "warning",
                        "generated_files": {},
                        "file_details": {},
                        "file_count": 0,
                        "success_count": 0,
                        "success_rate": 0.0,
                        "output_directory": self.output_dir,
                        "phase": current_phase,
                        "summary": f"No files to generate for phase {current_phase}"
                    }
            
            # Create consolidated context summary once
            context_summary = self._create_requirements_summary(brd_analysis)
            
            # Process files in dependency order
            item_order = self._process_dependencies_order(file_structure)
            total_items = len(item_order)
            
            # Track generated files and created directories
            generated_files = {}
            created_dirs = set()
            successful_files = 0
            
            self.log_info(f"Processing {total_items} items in dependency order")
            
            for i, item_path in enumerate(item_order, 1):
                full_item_path = os.path.join(self.output_dir, item_path)
                
                # Normalize path
                normalized_item_path = os.path.normpath(item_path)
                
                # Handle directories
                if item_path.endswith('/'):
                    try:
                        os.makedirs(full_item_path, exist_ok=True)
                        created_dirs.add(full_item_path)
                        self.log_info(f"[{i}/{total_items}] Created directory: {normalized_item_path}")
                    except Exception as e:
                        self.log_error(f"Failed to create directory {full_item_path}: {e}")
                    continue
                
                self.log_info(f"[{i}/{total_items}] Generating: {normalized_item_path}")
                
                # Ensure parent directory exists
                parent_dir = os.path.dirname(full_item_path)
                if parent_dir and parent_dir not in created_dirs:
                    try:
                        os.makedirs(parent_dir, exist_ok=True)
                        created_dirs.add(parent_dir)
                    except Exception as e:
                        self.log_error(f"Failed to create parent directory {parent_dir}: {e}")
                        continue
                
                try:
                    # Generate and refine code
                    code_content, is_success = self._generate_and_refine_code(
                        normalized_item_path,
                        context_summary,
                        tech_stack_recommendation,
                        system_design,
                        file_structure
                    )
                    
                    # Write to file regardless of success
                    file_content_to_write = code_content if code_content.strip() else f"# Placeholder for {normalized_item_path}"
                    
                    with open(full_item_path, 'w', encoding='utf-8') as f:
                        f.write(file_content_to_write)
                    
                    # Update tracking
                    generated_files[normalized_item_path] = {
                        "content": file_content_to_write,
                        "success": is_success,
                        "path": full_item_path
                    }
                    
                    if is_success:
                        successful_files += 1
                        self.log_success(f"Successfully generated: {normalized_item_path}")
                    else:
                        self.log_warning(f"Generated with issues: {normalized_item_path}")
                    
                except Exception as e:
                    self.log_error(f"Failed to generate {normalized_item_path}: {e}")
                    
                    # Try to write placeholder on error
                    try:
                        placeholder = f"# Error generating {normalized_item_path}: {str(e)}"
                        with open(full_item_path, 'w', encoding='utf-8') as f:
                            f.write(placeholder)
                        generated_files[normalized_item_path] = {
                            "content": placeholder,
                            "success": False,
                            "path": full_item_path
                        }
                    except Exception:
                        pass
            
            # Generate summary
            success_rate = (successful_files / max(1, len(generated_files))) * 100
            status = "success" if success_rate >= 70 else "partial" if success_rate > 0 else "failure"
            
            self.log_success(f"Code generation complete: {successful_files}/{len(generated_files)} files successful ({success_rate:.1f}%)")
            
            # Add phase information to the result
            return {
                "status": status,
                "generated_files": {k: v["content"] for k, v in generated_files.items()},
                "file_details": {k: {"success": v["success"], "path": v["path"]} for k, v in generated_files.items()},
                "file_count": len(generated_files),
                "success_count": successful_files,
                "success_rate": success_rate,
                "output_directory": self.output_dir,
                "phase": current_phase,
                "summary": f"Generated {len(generated_files)} files with {successful_files} successful ({success_rate:.1f}%){f' for phase {current_phase}' if current_phase else ''}"
            }
            
        except Exception as e:
            self.log_error(f"Code generation failed: {e}")
            import traceback
            self.log_error(traceback.format_exc())
            return self.get_default_response(current_phase)
            
    def _filter_files_by_phase(self, file_structure: dict, phase_id: str, implementation_plan: dict) -> dict:
        """Filter file structure to only include files relevant to the current phase."""
        self.log_info(f"Filtering files for phase: {phase_id}")
        
        # Extract phase information from implementation plan
        phases = implementation_plan.get("development_phases", [])
        current_phase = next((p for p in phases if p.get("phase_id") == phase_id), None)
        
        if not current_phase:
            self.log_warning(f"Phase {phase_id} not found in implementation plan")
            return {}
        
        # Get phase components, modules, and deliverables
        components = current_phase.get("components", [])
        deliverables = current_phase.get("deliverables", [])
        modules = current_phase.get("modules", [])
        
        # Convert all to lowercase for case-insensitive matching
        components_lower = [c.lower() for c in components]
        deliverables_lower = [d.lower() for d in deliverables]
        modules_lower = [m.lower() for m in modules]
        
        # Filter file structure
        filtered_structure = {}
        
        for path, description in file_structure.items():
            path_lower = path.lower()
            
            # Always include directories
            if path.endswith('/'):
                filtered_structure[path] = description
                continue
                
            # Check if file matches any component, deliverable, or module
            if any(c in path_lower for c in components_lower) or \
               any(d in path_lower for d in deliverables_lower) or \
               any(m in path_lower for m in modules_lower):
                filtered_structure[path] = description
                continue
                
            # Check description for matches
            desc_lower = description.lower()
            if any(c in desc_lower for c in components_lower) or \
               any(d in desc_lower for d in deliverables_lower) or \
               any(m in desc_lower for m in modules_lower):
                filtered_structure[path] = description
                continue
        
        self.log_info(f"Identified {len(filtered_structure)} files/directories for phase {phase_id}")
        return filtered_structure
        
    def get_default_response(self, current_phase: str = None) -> Dict[str, Any]:
        """Get structured default response when code generation fails completely."""
        return {
            "status": "error",
            "generated_files": {},
            "file_details": {},
            "file_count": 0,
            "success_count": 0,
            "success_rate": 0.0,
            "output_directory": self.output_dir,
            "phase": current_phase,
            "summary": f"Code generation failed due to critical errors{f' for phase {current_phase}' if current_phase else ''}"
        }