"""
Utility functions for code generation tasks, including parsing structured LLM outputs.
"""

import re
from typing import List, Dict, Any, Optional
import logging
from models.data_contracts import GeneratedFile

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
    
    try:
        # Clean the input - remove excessive whitespace but preserve structure
        llm_output = llm_output.strip()
        
        # Pattern 1: ### FILE: path with code blocks (most strict)
        pattern1 = r"### FILE:\s*(.*?)\s*\n```[a-zA-Z]*\s*\n(.*?)\n```"
        matches = re.findall(pattern1, llm_output, re.DOTALL)
        
        if not matches:
            # Pattern 2: Alternative format without specific language in code blocks
            pattern2 = r"### FILE:\s*(.*?)\s*\n```\s*\n(.*?)\n```"
            matches = re.findall(pattern2, llm_output, re.DOTALL)
            
        if not matches:
            # Pattern 3: Without code blocks at all
            pattern3 = r"### FILE:\s*(.*?)\s*\n(.*?)(?=\n### FILE:|$)"
            matches = re.findall(pattern3, llm_output, re.DOTALL)
        
        if not matches:
            # Pattern 4: Handle cases where filetype is mentioned
            pattern4 = r"### FILE:\s*(.*?)\s*\n```filetype\s*\n(.*?)(?=\n```|$)"
            matches = re.findall(pattern4, llm_output, re.DOTALL)
        
        if not matches:
            # Pattern 5: Try to extract from any header that mentions a file path
            pattern5 = r"(?:FILE|file):\s*([^\n]+)\s*\n```[a-zA-Z]*\s*\n(.*?)(?=\n```|$)"
            matches = re.findall(pattern5, llm_output, re.DOTALL | re.IGNORECASE)
        
        if not matches:
            # Pattern 6: Look for any file-like patterns with common extensions
            pattern6 = r"([a-zA-Z_][a-zA-Z0-9_/.-]*\.(py|js|java|cpp|c|h|html|css|json|yaml|yml|md|txt))\s*\n```[a-zA-Z]*\s*\n(.*?)(?=\n```|$)"
            matches = re.findall(pattern6, llm_output, re.DOTALL)
            if matches:
                # For pattern 6, the match structure is different - first element is path, third is content
                matches = [(match[0], match[2]) for match in matches]
        
        if not matches:
            # Pattern 7: More flexible file detection - look for numbered sections or bullet points with filenames
            pattern7 = r"(?:\d+\.\s*|\*\s*|\-\s*)`?([a-zA-Z_][a-zA-Z0-9_/.-]*\.(py|js|java|cpp|c|h|html|css|json|yaml|yml|md|txt))`?\s*:?\s*\n```[a-zA-Z]*\s*\n(.*?)(?=\n```|$)"
            matches = re.findall(pattern7, llm_output, re.DOTALL)
            if matches:
                # For pattern 7, adjust the match structure
                matches = [(match[0], match[2]) for match in matches]
        
        if not matches:
            # Pattern 8: NEW - Handle inline mentions of files with code blocks (more liberal)
            # This pattern looks for filenames followed by code blocks anywhere in the text
            pattern8 = r"(?:^|\n)(?:[*\-\d\.]+\s*)?(?:`)?([a-zA-Z_][a-zA-Z0-9_/.-]*\.(py|js|java|cpp|c|h|html|css|json|yaml|yml|md|txt))(?:`)?[:\s]*\n```(?:[a-zA-Z]*\s*)?\n(.*?)(?=\n```)"
            matches = re.findall(pattern8, llm_output, re.DOTALL | re.MULTILINE)
            if matches:
                matches = [(match[0], match[2]) for match in matches]
        
        if not matches:
            # Pattern 9: NEW - Handle section headers with filenames 
            # Looking for patterns like "**filename.ext**" or "## filename.ext" followed by code
            pattern9 = r"(?:^|\n)(?:\*\*|##\s*|###\s*)([a-zA-Z_][a-zA-Z0-9_/.-]*\.(py|js|java|cpp|c|h|html|css|json|yaml|yml|md|txt))(?:\*\*)?[:\s]*\n```(?:[a-zA-Z]*\s*)?\n(.*?)(?=\n```)"
            matches = re.findall(pattern9, llm_output, re.DOTALL | re.MULTILINE)
            if matches:
                matches = [(match[0], match[2]) for match in matches]
        
        if not matches:
            # Pattern 10: NEW - Very liberal pattern for any filename near a code block
            # Split by code blocks and try to find filenames in the text before each block
            code_blocks = re.split(r'```[a-zA-Z]*\s*\n', llm_output)
            for i in range(1, len(code_blocks)):  # Skip first split (before any code block)
                # Get the content of this code block
                content_match = re.match(r'(.*?)(?=\n```|$)', code_blocks[i], re.DOTALL)
                if content_match:
                    content = content_match.group(1).strip()
                    
                    # Look for filename in the text before this code block
                    prev_text = code_blocks[i-1] if i > 0 else ""
                    # Look for filename patterns in the last few lines of previous text
                    last_lines = '\n'.join(prev_text.split('\n')[-3:]) if prev_text else ""
                    filename_match = re.search(r'([a-zA-Z_][a-zA-Z0-9_/.-]*\.(py|js|java|cpp|c|h|html|css|json|yaml|yml|md|txt))\s*$', last_lines, re.MULTILINE)
                    if not filename_match:
                        # Try broader search in the previous text
                        filename_match = re.search(r'([a-zA-Z_][a-zA-Z0-9_/.-]*\.(py|js|java|cpp|c|h|html|css|json|yaml|yml|md|txt))', prev_text[-200:] if prev_text else "")
                    
                    if filename_match and content and len(content) > 10:
                        matches.append((filename_match.group(1), content))
        
        # Process matches
        for path, content in matches:
            # Clean the file path - remove any trailing whitespace, newlines, or unwanted characters
            path = path.strip().strip('\n').strip()
            
            # Remove any markdown artifacts that might have leaked into the path
            if '```' in path:
                path = path.split('```')[0].strip()
            if '\n' in path:
                path = path.split('\n')[0].strip()
            
            # Remove common prefixes that might appear
            for prefix in ['**', '*', '`', '"', "'", '(', ')', '[', ']']:
                path = path.strip(prefix)
            
            # Clean content - remove excess whitespace at start/end but preserve internal formatting
            content = content.strip()
            
            # Remove common content artifacts
            if content.startswith('```'):
                content = content[3:].strip()
            if content.endswith('```'):
                content = content[:-3].strip()
            
            # Ensure we have a valid file path and content
            if path and content and len(content) > 10:  # Minimum content length
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
            # Enhanced debugging information
            sample = llm_output[:2000] if len(llm_output) > 2000 else llm_output
            logger.info(f"Sample LLM output for debugging:\n{sample}")
            
            # Try to identify if there are any file-like patterns at all
            file_mentions = re.findall(r'FILE:', llm_output, re.IGNORECASE)
            code_blocks = re.findall(r'```', llm_output)
            filename_patterns = re.findall(r'\w+\.(py|js|java|cpp|c|h|html|css|json|yaml|yml|md|txt)', llm_output, re.IGNORECASE)
            
            logger.info(f"Found {len(file_mentions)} 'FILE:' mentions, {len(code_blocks)} code block markers, {len(filename_patterns)} filename patterns")
            logger.info(f"Filename patterns found: {filename_patterns[:10]}")  # Show first 10
            
            # Show where the code blocks are located
            code_block_locations = [m.start() for m in re.finditer(r'```', llm_output)]
            logger.info(f"Code block positions: {code_block_locations[:10]}")  # Show first 10 positions
            
    except Exception as e:
        logger.error(f"Error parsing LLM output: {e}")
        logger.info(f"LLM output causing error (first 1000 chars): {llm_output[:1000]}")
        
    return files
