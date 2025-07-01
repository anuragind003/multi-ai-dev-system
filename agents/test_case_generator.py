import json
import os
import re
import time
from typing import Dict, Any, List, Optional, Tuple
from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.retrievers import BaseRetriever
import monitoring
from datetime import datetime

# Import proper dependencies
from .code_generation.base_code_generator import BaseCodeGeneratorAgent
from models.data_contracts import GeneratedFile, CodeGenerationOutput
from tools.code_generation_utils import parse_llm_output_into_files
from tools.code_execution_tool import CodeExecutionTool
from message_bus import MessageBus

# Enhanced memory and RAG imports
from enhanced_memory_manager import create_memory_manager, EnhancedSharedProjectMemory
from rag_manager import get_rag_manager

class TestCaseGeneratorAgent(BaseCodeGeneratorAgent):
    """
    Generates a comprehensive test suite for the generated codebase in a single, structured step.
    """
    
    def __init__(self, llm: BaseLanguageModel, memory, temperature: float, 
                 output_dir: str, 
                 code_execution_tool: Optional[CodeExecutionTool] = None,
                 rag_retriever: Optional[BaseRetriever] = None,
                 message_bus: Optional[MessageBus] = None):
        
        super().__init__(
            llm=llm,
            memory=memory,
            agent_name="Test Case Generator Agent",
            temperature=temperature,
            output_dir=output_dir,
            code_execution_tool=code_execution_tool,
            rag_retriever=rag_retriever,
            message_bus=message_bus
        )
        
        # Store temperature as an instance variable for the run method in base_code_generator.py
        self.temperature = temperature
        
        # Enhanced memory is already initialized in BaseCodeGeneratorAgent
        # Initialize RAG context if not already done by parent
        if not hasattr(self, 'rag_manager'):
            self.rag_manager = get_rag_manager()
            if self.rag_manager:
                self.logger.info("RAG manager available for enhanced test generation")
            else:
                self.logger.warning("RAG manager not available - proceeding with basic test generation")
        
        # Token optimization configurations
        self.max_tokens = {
            "test_generation": 8192,
            "context": 3000
        }
        
        # Maximum characters for different contexts
        self.max_context_chars = {
            "rag": 1200,
            "code_file": 8000,
            "brd_summary": 1500,
            "code_summary": 2000
        }
        
        self._initialize_prompt_templates()
    
    def _initialize_prompt_templates(self):
        """Initializes a single, comprehensive prompt for generating all test files."""
        
        multi_file_format = """
        CRITICAL OUTPUT FORMAT:
        You MUST provide your response as a single block of text. For each file you generate, 
        you MUST use the following format. Do not add any other text or explanations.

        ### FILE: path/to/your/first/test_file.ext
        ```filetype
        # The full content of the test file goes here.
        ```
        """

        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", 
             "You are an expert Test Engineer specializing in creating comprehensive and robust test suites. "
             "Your task is to generate all necessary test files for the provided codebase, covering unit, "
             "integration, and functional tests."),
            ("human", 
             """
             # PROJECT CONTEXT
             
             ## Business Requirements Summary
             {brd_summary}
             
             ## Technology Stack
             {tech_stack}
             
             ## Code Files Summary
             {code_files_summary}
             
             ## RELEVANT CODE TO TEST
             {code_to_test}
             
             ## BEST PRACTICES & EXAMPLES
             {rag_context}
             
             # INSTRUCTIONS
             
             Generate a complete test suite for the provided code. Ensure you cover:
             
             1. **Unit Tests**: For individual functions/methods
             2. **Integration Tests**: For component interactions and API endpoints
             3. **Functional Tests**: For key business logic and user workflows
             4. **Edge Cases**: For error handling and boundary conditions
             
             Use the appropriate testing framework for the tech stack ({test_framework}).
             Consider testing priorities based on the business requirements.
             
             Follow this multi-file format EXACTLY:
             {format_instructions}
             """)
        ])
        
        self.prompt_template = self.prompt_template.partial(format_instructions=multi_file_format)

    def _generate_code(self, llm: BaseLanguageModel, invoke_config: Dict, **kwargs) -> Dict[str, Any]:
        """
        Generates all test files in a single, structured LLM call.
        
        Args:
            llm: Language model for generating test code
            invoke_config: Configuration for LLM invocation
            **kwargs: Additional arguments including code_generation_result, brd_analysis, etc.
            
        Returns:
            Dictionary conforming to the CodeGenerationOutput model
        """
        with monitoring.agent_trace_span(self.agent_name, "test_generation"):
            self.log_info("Starting comprehensive test case generation")
            start_time = time.time()
            
            # Extract necessary inputs from kwargs
            code_generation_result = kwargs.get('code_generation_result', {})
            brd_analysis = kwargs.get('brd_analysis', {})
            tech_stack = kwargs.get('tech_stack_recommendation', {})
            
            if not code_generation_result or not 'generated_files' in code_generation_result:
                self.log_warning("No code generation results found to create tests for")
                return self._create_empty_output("No code files available for test generation")
            
            try:
                # Prepare context for the prompt
                brd_summary = self._create_brd_summary(brd_analysis)
                
                # Extract generated files
                if isinstance(code_generation_result.get("generated_files"), list):
                    # Handle the case where generated_files is a list of dictionaries
                    file_list = code_generation_result.get("generated_files", [])
                    generated_files = {item.get("file_path"): item.get("content") for item in file_list 
                                     if isinstance(item, dict) and "file_path" in item and "content" in item}
                else:
                    # Handle the case where generated_files is a dictionary
                    generated_files = code_generation_result.get("generated_files", {})
                
                if not generated_files:
                    self.log_warning("No valid generated files found in code generation result")
                    return self._create_empty_output("No valid code files found for test generation")
                
                code_files_summary = self._prepare_enhanced_code_summary(generated_files)
                test_framework = self._determine_test_framework(tech_stack)
                rag_context = self.get_enhanced_rag_context(test_framework, tech_stack)
                
                # Select most important files to include in the prompt to avoid context overload
                key_files_content = self._get_key_files_for_testing(generated_files)
                
                self.log_info(f"Preparing to generate tests using {test_framework} framework")
                
                # Use base temperature
                llm_with_temp = llm.bind(
                    temperature=self.temperature,
                    max_tokens=self.max_tokens["test_generation"]
                )
                
                # Update invoke config with agent details
                local_invoke_config = invoke_config.copy()
                local_invoke_config["agent_context"] = f"{self.agent_name}:test_generation"
                local_invoke_config["temperature_used"] = self.temperature
                
                # Format the prompt
                prompt = self.prompt_template.format(
                    brd_summary=brd_summary,
                    tech_stack=json.dumps(tech_stack, indent=2),
                    code_files_summary=code_files_summary,
                    code_to_test=key_files_content,
                    rag_context=rag_context,
                    test_framework=test_framework
                )

                # Invoke the LLM
                response = llm_with_temp.invoke(prompt, config=local_invoke_config)
                content = response.content if hasattr(response, 'content') else str(response)

                # Parse the multi-file output
                generated_files_list = parse_llm_output_into_files(content)

                if not generated_files_list:
                    self.log_warning("LLM did not produce any parsable test files")
                    return self._create_empty_output("Failed to generate valid test files")
                
                # Process and save test files
                test_count = len(generated_files_list)
                execution_time = time.time() - start_time
                
                # Create the final output object
                output = CodeGenerationOutput(
                    generated_files=generated_files_list,
                    summary=f"Successfully generated {test_count} test files using {test_framework}",
                    status="success",
                    metadata={
                        "test_count": test_count,
                        "testing_framework": test_framework,
                        "test_categories": self._categorize_test_files(generated_files_list),
                        "execution_time": execution_time
                    }
                )
                
                # Store result in enhanced memory for cross-tool access
                output_dict = output.dict()
                self.enhanced_set("test_generation_result", output_dict, context="test_generation")
                self.store_cross_tool_data("test_files", generated_files_list, f"Test files generated with {test_framework}")
                
                # Store test patterns for reuse
                self.enhanced_set("test_patterns", {
                    "framework": test_framework,
                    "test_count": test_count,
                    "categories": self._categorize_test_files(generated_files_list),
                    "execution_time": execution_time
                }, context="test_patterns")
                
                self.log_success(f"Generated {test_count} test files in {execution_time:.2f}s")
                return output_dict

            except Exception as e:
                execution_time = time.time() - start_time
                self.log_error(f"Test case generation failed: {e}", exc_info=True)
                return self._create_empty_output(f"Error during test generation: {str(e)}")
    
    def _create_empty_output(self, message: str) -> Dict[str, Any]:
        """Create an empty output with an error message"""
        return CodeGenerationOutput(
            files=[],
            summary=message,
            status="error",
            metadata={
                "error": message,
                "test_count": 0,
                "timestamp": datetime.now().isoformat()
            }
        ).dict()
    
    def _create_brd_summary(self, brd_analysis: dict) -> str:
        """Create a focused summary of BRD analysis for test strategy generation."""
        summary_parts = []
        
        # Extract project overview
        if "project_overview" in brd_analysis:
            po = brd_analysis["project_overview"]
            summary_parts.append("## PROJECT OVERVIEW")
            summary_parts.append(f"Project: {po.get('project_name', 'Unknown')}")
            summary_parts.append(f"Description: {po.get('description', 'Not specified')}")
            if "objectives" in po:
                objectives = po.get("objectives", [])
                summary_parts.append("Objectives:")
                for obj in objectives[:5]:  # Limit to top 5
                    summary_parts.append(f"- {obj}")
        
        # Extract functional requirements
        if "functional_requirements" in brd_analysis:
            summary_parts.append("\n## FUNCTIONAL REQUIREMENTS")
            for req in brd_analysis["functional_requirements"][:10]:  # Limit to top 10
                req_id = req.get("id", "Unknown")
                desc = req.get("description", "No description")
                priority = req.get("priority", "Medium")
                summary_parts.append(f"- [{priority}] {req_id}: {desc}")
        
        # Extract non-functional requirements
        if "non_functional_requirements" in brd_analysis:
            nfr = brd_analysis["non_functional_requirements"]
            summary_parts.append("\n## NON-FUNCTIONAL REQUIREMENTS")
            
            for category in ["performance", "security", "reliability", "usability"]:
                if category in nfr:
                    requirements = nfr[category]
                    if requirements:
                        summary_parts.append(f"\n### {category.upper()}")
                        for req in requirements[:3]:  # Limit to top 3
                            summary_parts.append(f"- {req}")
        
        return "\n".join(summary_parts)
    
    def _prepare_enhanced_code_summary(self, generated_code_files: dict) -> str:
        """Create an enhanced summary of code files with structural information."""
        if not generated_code_files:
            return "No code files available"
        
        summary_parts = []
        
        # Group files by type/directory
        grouped_files = {}
        for file_path in generated_code_files.keys():
            dir_path = os.path.dirname(file_path)
            if dir_path not in grouped_files:
                grouped_files[dir_path] = []
            grouped_files[dir_path].append(file_path)
        
        # Summarize by directory
        for dir_path, files in grouped_files.items():
            summary_parts.append(f"\n## {dir_path or 'Root directory'}")
            for file_path in sorted(files):
                content = generated_code_files[file_path]
                lines = content.count('\n') + 1
                
                # Extract key structural elements
                structure_info = self._extract_code_structure(file_path, content)
                summary_parts.append(f"- {os.path.basename(file_path)}: {lines} lines{structure_info}")
        
        # Add overall statistics
        total_files = len(generated_code_files)
        total_lines = sum(generated_code_files[f].count('\n') + 1 for f in generated_code_files)
        summary_parts.insert(0, f"# CODE SUMMARY: {total_files} files, {total_lines} total lines")
        
        return "\n".join(summary_parts)
    
    def _extract_code_structure(self, file_path: str, content: str) -> str:
        """Extract structural information from code files."""
        structure_parts = []
        
        # Python files
        if file_path.endswith('.py'):
            classes = len(re.findall(r'^\s*class\s+\w+', content, re.MULTILINE))
            functions = len(re.findall(r'^\s*def\s+\w+', content, re.MULTILINE))
            if classes > 0:
                structure_parts.append(f"{classes} classes")
            if functions > 0:
                structure_parts.append(f"{functions} functions")
        
        # JavaScript/TypeScript files
        elif file_path.endswith(('.js', '.ts', '.jsx', '.tsx')):
            classes = len(re.findall(r'class\s+\w+', content))
            functions = len(re.findall(r'function\s+\w+', content)) + len(re.findall(r'=>', content))
            if classes > 0:
                structure_parts.append(f"{classes} classes")
            if functions > 0:
                structure_parts.append(f"{functions} functions/methods")
                
        # Java files
        elif file_path.endswith('.java'):
            classes = len(re.findall(r'class\s+\w+', content))
            methods = len(re.findall(r'\s\w+\s*\([^\)]*\)\s*(\{|throws)', content))
            if classes > 0:
                structure_parts.append(f"{classes} classes")
            if methods > 0:
                structure_parts.append(f"{methods} methods")
        
        if structure_parts:
            return f" ({', '.join(structure_parts)})"
        return ""
    
    def _get_key_files_for_testing(self, all_files: Dict[str, str], max_chars: int = 10000) -> str:
        """Selects and concatenates the content of the most important files for the prompt."""
        # Skip test files themselves
        non_test_files = [(path, content) for path, content in all_files.items() 
                         if 'test' not in path.lower() and '/tests/' not in path]
        
        if not non_test_files:
            return "No testable files found"
        
        # Priority patterns for test-critical files
        test_priority_patterns = [
            # Core business logic
            'service', 'controller', 'manager', 'handler', 'processor',
            # Data handling
            'model', 'repository', 'dao', 'store',
            # API endpoints
            'api', 'route', 'endpoint', 'view', 'resource',
            # Security
            'auth', 'security', 'permission', 'access'
        ]
        
        # Score each file based on testing importance
        scored_files = []
        
        for path, content in non_test_files:
            score = 0
            lower_path = path.lower()
            
            # Check filename for priority patterns
            for pattern in test_priority_patterns:
                if pattern in lower_path:
                    score += 3
            
            # Check code complexity
            lines = content.count('\n') + 1
            if lines > 200:
                score += 2  # Complex files are important to test
            elif lines < 20:
                score -= 1  # Very small files less important
            
            scored_files.append((path, content, score))
        
        # Sort by score descending
        scored_files.sort(key=lambda x: x[2], reverse=True)
        
        # Combine content with limits
        combined_content = ""
        total_chars = 0
        
        for path, content, _ in scored_files:
            file_header = f"\n\n--- FILE: {path} ---\n\n"
            file_content = content[:2000] if len(content) > 2000 else content  # Limit individual file size
            
            if total_chars + len(file_header) + len(file_content) > max_chars:
                break
                
            combined_content += file_header + file_content
            total_chars += len(file_header) + len(file_content)
        
        if not combined_content:
            return "Files too large to include in context"
        
        return combined_content

    def _determine_test_framework(self, tech_stack: dict) -> str:
        """Determine the appropriate test framework based on tech stack."""
        # Get backend details
        backend = tech_stack.get("backend", {})
        language = backend.get("language", "").lower()
        framework = backend.get("framework", "").lower()
        
        # Map language and framework to test framework
        if language == "python":
            if framework in ["django", "flask"]:
                return "pytest"
            else:
                return "pytest"
        elif language in ["javascript", "typescript"]:
            if framework in ["react", "vue", "angular"]:
                return "jest"
            elif framework == "express":
                return "mocha"
            else:
                return "jest"
        elif language == "java":
            return "junit"
        else:
            # Default to pytest as fallback
            return "pytest"

    def get_enhanced_rag_context(self, test_framework: str, tech_stack: dict, test_type: Optional[str] = None) -> str:
        """Get enhanced RAG context with multiple targeted queries and dynamic token allocation."""
        if not self.rag_retriever:
            return ""
        
        self.log_info(f"Retrieving RAG context for {test_framework} testing")
        context_parts = []
        
        # Default if RAG fails
        default_context = {
            "pytest": "Use pytest fixtures for setup/teardown. Use parametrize for multiple test cases.",
            "jest": "Use describe/it blocks. Mock dependencies with jest.mock().",
            "junit": "Use @Before/@After annotations. Use Mockito for mocks.",
            "mocha": "Use describe/it with chai assertions and sinon for mocks."
        }
        
        try:
            # Get framework-specific test patterns
            framework_query = f"{test_framework} best practices test patterns examples"
            framework_context = self._get_rag_context(
                query=framework_query, 
                task_goal=f"Generate {test_framework} tests"
            )
            
            if framework_context:
                context_parts.append(f"## {test_framework.upper()} TESTING PATTERNS\n{framework_context}")
            
            # Get language-specific test patterns
            language = tech_stack.get('backend', {}).get('language', '')
            if language:
                language_query = f"{language} {test_framework} testing mocks fixtures examples"
                language_context = self._get_rag_context(
                    query=language_query,
                    task_goal=f"Generate {language} tests with {test_framework}"
                )
                
                if language_context:
                    context_parts.append(f"## {language.upper()} TESTING PATTERNS\n{language_context}")
            
            combined_context = "\n\n".join(context_parts)
            
            if combined_context:
                return combined_context
            else:
                return f"## {test_framework.upper()} TESTING BEST PRACTICES\n\n{default_context.get(test_framework, '')}"
                
        except Exception as e:
            self.log_warning(f"Error retrieving RAG context: {str(e)}")
            return f"## {test_framework.upper()} TESTING BEST PRACTICES\n\n{default_context.get(test_framework, '')}"

    def _get_rag_context(self, query: str, task_goal: str, max_docs: int = 3) -> str:
        """Helper method to get RAG context with character limits."""
        if not self.rag_retriever:
            return ""
            
        try:
            # Get documents from retriever
            docs = self.rag_retriever.get_relevant_documents(query, limit=max_docs)
            
            if not docs:
                return ""
                
            # Format retrieved context with character limits
            context_parts = []
            total_chars = 0
            
            for doc in docs:
                content = doc.page_content
                
                # Check if adding this document would exceed the character limit
                if total_chars + len(content) > self.max_context_chars["rag"]:
                    # If we're about to exceed the limit, truncate
                    chars_left = self.max_context_chars["rag"] - total_chars
                    if chars_left > 100:
                        truncated_content = content[:chars_left] + "... [truncated]"
                        context_parts.append(truncated_content)
                    break
                
                # Add the full document if within limits
                context_parts.append(content)
                total_chars += len(content)
            
            return "\n\n".join(context_parts)
            
        except Exception as e:
            self.log_warning(f"RAG retrieval error: {str(e)}")
            return ""
    
    def _categorize_test_files(self, generated_files: List[GeneratedFile]) -> Dict[str, int]:
        """Categorize generated test files by test type."""
        categories = {
            "unit_tests": 0,
            "integration_tests": 0,
            "functional_tests": 0,
            "other_tests": 0
        }
        
        for test_file in generated_files:
            file_path = test_file.file_path.lower()
            content = test_file.content.lower()
            
            # Categorize based on filename and content
            if "unit" in file_path or "unit" in content[:200]:
                categories["unit_tests"] += 1
            elif "integration" in file_path or "integration" in content[:200]:
                categories["integration_tests"] += 1
            elif "functional" in file_path or "functional" in content[:200] or "e2e" in file_path:
                categories["functional_tests"] += 1
            else:
                categories["other_tests"] += 1
        
        return categories

