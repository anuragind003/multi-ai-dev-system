"""
Utility functions for code generation tasks, including parsing structured LLM outputs.
"""

import re
from typing import List, Dict, Any, Optional
import logging
from agents.code_generation.models import GeneratedFile

logger = logging.getLogger(__name__)

def parse_llm_output_into_files(llm_output: str) -> List[GeneratedFile]:
    """
    Parses the LLM's multi-file output format into a list of GeneratedFile objects.
    
    Expected format:
    ### FILE: path/to/file.ext
    ```language
    file content
    ```
    
    Args:
        llm_output: The raw text output from the LLM containing multiple file blocks
        
    Returns:
        List of GeneratedFile objects
    """
    files = []
    
    # Regex to find all file blocks: captures path and content
    pattern = r"### FILE: (.*?)\n\n```[a-z]*\n(.*?)\n```"
    matches = re.findall(pattern, llm_output, re.DOTALL)
    
    if not matches:
        # Try alternative format without language specifier
        pattern = r"### FILE: (.*?)\n\n```\n(.*?)\n```"
        matches = re.findall(pattern, llm_output, re.DOTALL)
        
    if not matches:
        # Try another common format (without code blocks)
        pattern = r"### FILE: (.*?)\n\n(.*?)(?=\n### FILE:|$)"
        matches = re.findall(pattern, llm_output, re.DOTALL)
    
    for path, content in matches:
        path = path.strip()
        content = content.strip()
        
        files.append(
            GeneratedFile(
                file_path=path,
                content=content,
                purpose=f"Generated file: {path}",
                status="generated"
            )
        )
    
    if not files:
        logger.warning(f"Failed to parse any files from LLM output. Output length: {len(llm_output)}")
        
    return files