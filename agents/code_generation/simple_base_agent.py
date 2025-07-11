"""
SimpleBaseAgent - Minimal base class for simplified code generation agents
Replaces the complex BaseCodeGeneratorAgent with essential functionality only.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from langchain_core.language_models import BaseLanguageModel
from langchain_core.retrievers import BaseRetriever

from agents.base_agent import BaseAgent
from models.data_contracts import GeneratedFile, CodeGenerationOutput, WorkItem

logger = logging.getLogger(__name__)


class SimpleBaseAgent(BaseAgent):
    """Minimal base class for simplified code generation agents."""
    
    def __init__(self, llm: BaseLanguageModel, memory, temperature: float, 
                 output_dir: str, code_execution_tool, **kwargs):
        super().__init__(
            llm=llm,
            memory=memory,
            agent_name=kwargs.get('agent_name', 'SimpleAgent'),
            temperature=temperature,
            rag_retriever=kwargs.get('rag_retriever')
        )
        
        self.output_dir = output_dir
        self.code_execution_tool = code_execution_tool
        os.makedirs(self.output_dir, exist_ok=True)
        
        logger.info(f"Initialized {self.agent_name} with output directory: {self.output_dir}")
    
    def _save_files(self, files: List[GeneratedFile]) -> None:
        """Save generated files to output directory."""
        if not files:
            logger.info("No files to save")
            return
        
        for file_obj in files:
            try:
                # Handle GeneratedFile objects
                if hasattr(file_obj, 'file_path') and hasattr(file_obj, 'content'):
                    file_path = file_obj.file_path.strip()
                    content = file_obj.content
                else:
                    # Handle dict format
                    file_path = file_obj.get('file_path', '').strip()
                    content = file_obj.get('content', '')
                
                if not file_path:
                    logger.warning("Empty file path, skipping")
                    continue
                
                # Create full path
                full_path = os.path.join(self.output_dir, file_path)
                
                # Create directory if needed
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                
                # Write file
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                logger.info(f"Saved file: {file_path}")
                
            except Exception as e:
                logger.error(f"Failed to save file {getattr(file_obj, 'file_path', 'unknown')}: {e}")
    
    def run(self, work_item: WorkItem, state: Dict[str, Any]) -> CodeGenerationOutput:
        """Default run method - subclasses should override this."""
        return CodeGenerationOutput(
            generated_files=[],
            summary="Base agent - no implementation",
            status="error"
        )
    
    def get_default_response(self) -> Dict[str, Any]:
        """Default response for simplified agents."""
        return {
            "generated_files": [],
            "summary": "Default response from simplified agent",
            "status": "success"
        }
    
    async def arun(self, **kwargs) -> Any:
        """Async run method - simplified agents use sync run."""
        work_item = kwargs.get('work_item')
        state = kwargs.get('state', {})
        if work_item:
            return self.run(work_item, state)
        return self.get_default_response() 