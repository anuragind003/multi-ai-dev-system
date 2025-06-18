"""
Abstract base class for all code generation agents.
Provides common functionality and standardized interfaces for code generation.
"""

import os
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

from langchain_core.language_models import BaseLanguageModel
from langchain_core.retrievers import BaseRetriever
from langchain_core.prompts import ChatPromptTemplate

from agents.base_agent import BaseAgent
from agents.code_generation.models import GeneratedFile, CodeGenerationOutput
from tools.code_generation_utils import parse_llm_output_into_files
from tools.json_handler import JsonHandler

logger = logging.getLogger(__name__)

class BaseCodeGeneratorAgent(BaseAgent, ABC):
    """
    Abstract base class for all code generation agents with standardized I/O.
    Provides common functionality for structured code generation and management.
    """

    def __init__(self, 
                 llm: BaseLanguageModel, 
                 memory, 
                 agent_name: str, 
                 temperature: float,
                 output_dir: str, 
                 code_execution_tool=None, 
                 rag_retriever: Optional[BaseRetriever] = None,
                 message_bus=None):
        """
        Initialize the base code generator agent.
        
        Args:
            llm: The language model to use for generation
            memory: The memory instance for the agent
            agent_name: The name of the agent
            temperature: The temperature to use for generation
            output_dir: Directory to save generated files
            code_execution_tool: Tool for executing code if needed
            rag_retriever: Retriever for augmenting generation with relevant context
            message_bus: Message bus for inter-agent communication
        """
        super().__init__(
            llm=llm,
            memory=memory,
            agent_name=agent_name,
            temperature=temperature,
            rag_retriever=rag_retriever,
            message_bus=message_bus
        )
        self.output_dir = output_dir
        self.code_execution_tool = code_execution_tool
        os.makedirs(self.output_dir, exist_ok=True)
        self.log_info(f"Initialized {agent_name} with output directory: {output_dir}")

    def run(self, **kwargs) -> Dict[str, Any]:
        """
        Main execution method for the code generator agent.
        This method prepares the environment and calls the concrete `_generate_code` implementation.
        
        Returns:
            Dictionary conforming to the CodeGenerationOutput model
        """
        self.log_start(f"Starting code generation with agent: {self.agent_name}")
        
        try:
            # Prepare LLM and invoke_config for the generation process
            binding_args = {"temperature": self.temperature}
            llm_with_temp = self.llm.bind(**binding_args)
            
            invoke_config = {
                "agent_context": self.agent_name,
                "temperature_used": self.temperature,
                "model_name": getattr(self.llm, "model_name", "unknown")
            }

            # Call the subclass's specific generation logic
            generation_result = self._generate_code(
                llm=llm_with_temp,
                invoke_config=invoke_config,
                **kwargs  # Pass all other arguments like requirements_analysis, etc.
            )

            # Ensure the output is a dictionary
            if not isinstance(generation_result, dict):
                 self.log_error("Code generation did not return a dictionary. Returning default.")
                 return self.get_default_response()

            # Save files if any were generated
            generated_files = generation_result.get("generated_files", [])
            if generated_files:
                self.log_info(f"Saving {len(generated_files)} generated files to disk.")
                self._save_files(generated_files)

            return generation_result

        except Exception as e:
            self.log_error(f"An unhandled exception occurred in {self.agent_name}: {e}", exc_info=True)
            return self.get_default_response()

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
            Dictionary conforming to the CodeGenerationOutput model
        """
        raise NotImplementedError("Subclasses must implement _generate_code method")

    def _save_files(self, generated_files: List[Dict]) -> None:
        """
        Saves the generated files to the specified output directory.
        
        Args:
            generated_files: List of file dictionaries to save
        """
        if not generated_files:
            self.log_info("No files to save.")
            return

        for file_data_dict in generated_files:
            try:
                # Create a GeneratedFile object for validation and easy access
                file_obj = GeneratedFile(**file_data_dict)
                
                # Create the full path safely
                full_path = os.path.join(self.output_dir, file_obj.file_path)
                
                # Create parent directories if they don't exist
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(file_obj.content)
                
                self.log_info(f"Successfully saved file: {file_obj.file_path}")
            except Exception as e:
                self.log_error(f"Failed to save file from data {file_data_dict}: {e}")
    
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
                    
                documents = self.rag_retriever.get_relevant_documents(query)
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
            generated_files=[],
            summary=f"Code generation failed in agent: {self.agent_name}",
            status="error",
            metadata={ 
                "error": "An unhandled exception occurred.",
                "timestamp": datetime.now().isoformat(),
                "agent": self.agent_name
            }
        ).dict()