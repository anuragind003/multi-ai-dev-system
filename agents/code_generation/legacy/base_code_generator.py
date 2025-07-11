"""
Abstract base class for all code generation agents.
Provides common functionality and standardized interfaces for code generation.
"""

import os
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime
from pathlib import Path

from langchain_core.language_models import BaseLanguageModel
from langchain_core.retrievers import BaseRetriever
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.callbacks import BaseCallbackHandler

from agents.base_agent import BaseAgent
from models.data_contracts import GeneratedFile, CodeGenerationOutput, WorkItem
from tools.code_generation_utils import parse_llm_output_into_files
from tools.json_handler import JsonHandler
from tools.code_execution_tool import CodeExecutionTool
from message_bus import MessageBus

# Enhanced memory and RAG imports
try:
    from enhanced_memory_manager import create_memory_manager, EnhancedSharedProjectMemory
    ENHANCED_MEMORY_AVAILABLE = True
except ImportError:
    ENHANCED_MEMORY_AVAILABLE = False

try:
    from rag_manager import get_rag_manager
    RAG_MANAGER_AVAILABLE = True
except ImportError:
    RAG_MANAGER_AVAILABLE = False

# Import monitoring if available
try:
    import monitoring
    # Check if monitoring has init method before calling
    if hasattr(monitoring, 'init'):
        monitoring.init()
except (ImportError, AttributeError):
    pass

logger = logging.getLogger(__name__)

class BaseCodeGeneratorAgent(BaseAgent, ABC):
    """
    Abstract base class for all code generation agents with standardized I/O.
    Provides common functionality for structured code generation and management.
    """

    def __init__(self, 
                 llm: BaseLanguageModel, 
                 memory, 
                 **kwargs):
        """
        Initialize the base code generator agent.
        
        Args:
            llm: The language model to use for generation
            memory: The memory instance for the agent
            **kwargs: Additional arguments including agent_name, temperature, output_dir, etc.
        """
        super().__init__(
            llm=llm,
            memory=memory,
            **kwargs
        )
        self.output_dir = kwargs.get("output_dir", "output")
        self.code_execution_tool = kwargs.get("code_execution_tool")
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Initialize enhanced memory (inherits from BaseAgent)
        self._init_enhanced_memory()
        
        self.log_info(f"Initialized {self.agent_name} with output directory: {self.output_dir}")

    def run(self, work_item: WorkItem, state: Dict[str, Any]) -> CodeGenerationOutput:
        """
        Standardized run method for all code generation agents.
        
        Args:
            work_item: The specific work item to process
            state: The current workflow state containing context
            
        Returns:
            CodeGenerationOutput: Structured code generation results
        """
        logger.info(f"BaseCodeGeneratorAgent processing work item: {work_item.id}")
        
        try:
            # Extract context from state
            tech_stack = state.get('tech_stack_recommendation', {})
            system_design = state.get('system_design', {})
            requirements_analysis = state.get('requirements_analysis', {})
            
            # Call the specialized _generate_code method with standardized parameters
            result = self._generate_code(
                llm=self.llm,
                invoke_config={"temperature": self.temperature},
                work_item=work_item,
                tech_stack=tech_stack,
                system_design=system_design,
                requirements_analysis=requirements_analysis,
                state=state
            )
            
            # Convert to CodeGenerationOutput if needed
            if isinstance(result, dict):
                return CodeGenerationOutput(
                    generated_files=result.get('generated_files', []),
                    summary=result.get('summary', f'Generated code for work item {work_item.id}'),
                    status=result.get('status', 'success'),
                    metadata=result.get('metadata', {})
                )
            
            return result
            
        except Exception as e:
            logger.error(f"BaseCodeGeneratorAgent failed for {work_item.id}: {str(e)}")
            return CodeGenerationOutput(
                generated_files=[],
                summary=f"Code generation failed for {work_item.id}: {str(e)}",
                status="error",
                metadata={"error": str(e)}
            )

    @abstractmethod
    def _generate_code(self, llm: BaseLanguageModel, invoke_config: Dict, **kwargs) -> Dict:
        """
        Abstract method for code generation logic. Subclasses must implement this.
        This method is responsible for creating the prompt and invoking the LLM.

        It must return a dictionary that can be parsed by the CodeGenerationOutput model.
        
        Args:
            llm: The temperature-bound language model to use
            invoke_config: Configuration for the LLM invocation
            **kwargs: Additional inputs like requirements_analysis, tech_stack, etc.
            
        Returns:
            Dictionary conforming to the CodeGenerationOutput model        """
        raise NotImplementedError("Subclasses must implement _generate_code method")
    
    def _save_files(self, files) -> None:
        """
        Saves the generated files to the specified output directory.
        
        Args:
            files: List of file objects (CodeFile or GeneratedFile) to save
        """
        if not files:
            self.log_info("No files to save.")
            return

        for file_obj in files:
            try:
                # Handle both CodeFile and GeneratedFile objects
                if hasattr(file_obj, 'code'):
                    # CodeFile object
                    file_path = file_obj.file_path
                    content = file_obj.code
                elif hasattr(file_obj, 'content'):
                    # GeneratedFile object
                    file_path = file_obj.file_path
                    content = file_obj.content
                else:
                    # Dictionary format (legacy)
                    file_path = file_obj.get('file_path', '')
                    content = file_obj.get('content', file_obj.get('code', ''))
                
                # Validate and clean the file path
                if not file_path:
                    self.log_error("File path is empty, skipping file")
                    continue
                
                # Clean the file path of any unwanted characters
                file_path = file_path.strip().strip('\n').strip()
                
                # Remove any markdown artifacts that might have leaked into the path
                if '```' in file_path:
                    file_path = file_path.split('```')[0].strip()
                if '\n' in file_path:
                    file_path = file_path.split('\n')[0].strip()
                
                # Skip if path still contains invalid characters after cleaning
                if '\n' in file_path or '```' in file_path:
                    self.log_error(f"Invalid file path after cleaning: '{file_path}', skipping")
                    continue
                
                # Normalize path separators for Windows
                file_path = file_path.replace('\\', '/')
                
                # Create the full path safely
                full_path = os.path.join(self.output_dir, file_path)
                
                # Additional validation for Windows path length and characters
                if len(full_path) > 260:  # Windows path limit
                    self.log_error(f"File path too long: {full_path}")
                    continue
                
                # Create parent directories if they don't exist
                try:
                    parent_dir = os.path.dirname(full_path)
                    if parent_dir:  # Only create if parent_dir is not empty
                        os.makedirs(parent_dir, exist_ok=True)
                except Exception as dir_error:
                    self.log_error(f"Failed to create directory {parent_dir}: {dir_error}")
                    continue
                
                # Write the file
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                self.log_info(f"Successfully saved file: {file_path}")
                
            except Exception as e:
                error_path = getattr(file_obj, 'file_path', 'unknown')
                self.log_error(f"Failed to save file {error_path}: {e}")                # Log additional debug info for troubleshooting
                if hasattr(file_obj, 'file_path'):
                    newline_char = '\n'
                    backticks = '```'
                    self.log_debug(f"Raw file path: '{repr(file_obj.file_path)}'")
                    self.log_debug(f"File path length: {len(file_obj.file_path)}")
                    self.log_debug(f"File path contains newline: {newline_char in file_obj.file_path}")
                    self.log_debug(f"File path contains backticks: {backticks in file_obj.file_path}")
    
    def _prune_system_design_for_relevance(self, system_design: Dict[str, Any], 
                                          relevant_keys: List[str]) -> Dict[str, Any]:
        """
        Prunes the system design to only include relevant sections.
        
        Args:
            system_design: The complete system design
            relevant_keys: List of top-level keys to preserve
            
        Returns:
            Pruned system design dictionary
        """
        if not isinstance(system_design, dict):
            self.log_warning("System design is not a dictionary. Cannot prune.")
            return {}
            
        pruned = {}
        for key in relevant_keys:
            if key in system_design:
                pruned[key] = system_design[key]
                
        return pruned
    
    def _get_rag_context(self, query: str, use_case: str = None) -> str:
        """
        Retrieves RAG context for code generation.
        
        Args:
            query: The query to use for retrieval
            use_case: Optional use case context
              Returns:
            String containing RAG context
        """
        context = ""
        if self.rag_retriever:
            try:
                if use_case:
                    query = f"[{use_case}] {query}"
                    
                documents = self.rag_retriever.invoke(query)
                context = "\n\n".join([doc.page_content for doc in documents])
                
                if context:
                    self.log_info(f"Retrieved {len(documents)} relevant documents for RAG context")
            except Exception as e:
                self.log_warning(f"Failed to retrieve RAG context: {e}")
                
        return context
                
    def get_default_response(self) -> Dict[str, Any]:
        """
        Provide default response in case of errors.
        Returns a dictionary conforming to the CodeGenerationOutput model.
        
        Returns:
            Default CodeGenerationOutput as dictionary
        """
        return CodeGenerationOutput(
            files=[],
            summary=f"Code generation failed in agent: {self.agent_name}"
        ).dict()