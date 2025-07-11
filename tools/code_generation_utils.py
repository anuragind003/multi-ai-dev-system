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
    
    ENHANCED to handle multiple common LLM output formats:
    1. ### FILE: path/to/file.ext
    2. ### path/to/file.ext  (standalone filename)
    3. **path/to/file.ext**
    4. Files in single code blocks with ### headers
    5. Various markdown and text patterns
    
    Args:
        llm_output: The raw text output from the LLM containing multiple file blocks
        
    Returns:
        List of GeneratedFile objects
    """
    files = []
    
    try:
        # Clean the input - remove excessive whitespace but preserve structure
        llm_output = llm_output.strip()
        logger.info(f"Parsing LLM output of {len(llm_output)} characters")
        
        # ENHANCED PATTERN 1: ### FILE: path format (original)
        pattern1 = r"### FILE:\s*(.*?)\s*\n```[a-zA-Z]*\s*\n(.*?)\n```"
        matches = re.findall(pattern1, llm_output, re.DOTALL)
        if matches:
            logger.info(f"Found {len(matches)} files using pattern '### FILE: path'")
        
        if not matches:
            # ENHANCED PATTERN 2: ### filename.ext format (what LLMs actually generate)
            pattern2 = r"### ([a-zA-Z_][a-zA-Z0-9_/.-]*\.(py|js|java|cpp|c|h|html|css|json|yaml|yml|md|txt|sql|sh|dockerfile|env))\s*\n```[a-zA-Z]*\s*\n(.*?)(?=\n```|### [a-zA-Z_][a-zA-Z0-9_/.-]*\.|$)"
            matches = re.findall(pattern2, llm_output, re.DOTALL | re.MULTILINE)
            if matches:
                # Adjust match structure for this pattern
                matches = [(match[0], match[2]) for match in matches]
                logger.info(f"Found {len(matches)} files using pattern '### filename.ext'")
        
        if not matches:
            # ENHANCED PATTERN 3: Alternative format without specific language in code blocks
            pattern3 = r"### FILE:\s*(.*?)\s*\n```\s*\n(.*?)\n```"
            matches = re.findall(pattern3, llm_output, re.DOTALL)
            if matches:
                logger.info(f"Found {len(matches)} files using pattern '### FILE:' without language")
        
        if not matches:
            # ENHANCED PATTERN 4: ### filename without code blocks
            pattern4 = r"### ([a-zA-Z_][a-zA-Z0-9_/.-]*\.(py|js|java|cpp|c|h|html|css|json|yaml|yml|md|txt|sql|sh|dockerfile|env))\s*\n((?:(?!### [a-zA-Z_]).)*?)(?=### [a-zA-Z_][a-zA-Z0-9_/.-]*\.|$)"
            matches = re.findall(pattern4, llm_output, re.DOTALL | re.MULTILINE)
            if matches:
                matches = [(match[0], match[2]) for match in matches]
                logger.info(f"Found {len(matches)} files using pattern '### filename' without code blocks")
        
        if not matches:
            # ENHANCED PATTERN 5: **filename.ext** format
            pattern5 = r"\*\*([a-zA-Z_][a-zA-Z0-9_/.-]*\.(py|js|java|cpp|c|h|html|css|json|yaml|yml|md|txt|sql|sh|dockerfile|env))\*\*\s*\n```[a-zA-Z]*\s*\n(.*?)(?=\n```)"
            matches = re.findall(pattern5, llm_output, re.DOTALL)
            if matches:
                matches = [(match[0], match[2]) for match in matches]
                logger.info(f"Found {len(matches)} files using pattern '**filename.ext**'")
        
        if not matches:
            # ENHANCED PATTERN 6: Handle multiple files inside one big code block with ### headers
            single_block_pattern = r'```[a-zA-Z]*\s*\n(.*?)```'
            single_block_matches = re.findall(single_block_pattern, llm_output, re.DOTALL)
            for block_content in single_block_matches:
                # Split by ### headers and extract files
                file_sections = re.split(r'\n###\s+', block_content)
                if len(file_sections) > 1:  # Only if we found ### headers
                    for section in file_sections:
                        if not section.strip():
                            continue
                        # Look for filename at the start of the section
                        filename_match = re.match(r'([a-zA-Z_][a-zA-Z0-9_/.-]*\.(py|js|java|cpp|c|h|html|css|json|yaml|yml|md|txt|sql|sh|dockerfile|env))\s*\n(.*)', section, re.DOTALL)
                        if filename_match:
                            filename = filename_match.group(1).strip()
                            content = filename_match.group(3).strip()
                            if filename and content and len(content) > 20:
                                matches.append((filename, content))
            if matches:
                logger.info(f"Found {len(matches)} files using pattern 'single code block with ### headers'")
        
        if not matches:
            # ENHANCED PATTERN 7: Look for any file-like patterns with common extensions near code blocks
            pattern7 = r"(?:^|\n)(?:[*\-\d\.]+\s*)?(?:`)?([a-zA-Z_][a-zA-Z0-9_/.-]*\.(py|js|java|cpp|c|h|html|css|json|yaml|yml|md|txt|sql|sh|dockerfile|env))(?:`)?[:\s]*\n```(?:[a-zA-Z]*\s*)?\n(.*?)(?=\n```)"
            matches = re.findall(pattern7, llm_output, re.DOTALL | re.MULTILINE)
            if matches:
                matches = [(match[0], match[2]) for match in matches]
                logger.info(f"Found {len(matches)} files using pattern 'filename near code blocks'")
        
        if not matches:
            # ENHANCED PATTERN 8: More liberal pattern for filenames followed by code
            # Split by code blocks and try to find filenames in the text before each block
            code_blocks = re.split(r'```[a-zA-Z]*\s*\n', llm_output)
            for i in range(1, len(code_blocks)):
                # Get the content of this code block
                content_match = re.match(r'(.*?)(?=\n```|$)', code_blocks[i], re.DOTALL)
                if content_match:
                    content = content_match.group(1).strip()
                    
                    # Look for filename in the text before this code block
                    prev_text = code_blocks[i-1] if i > 0 else ""
                    # Look for filename patterns in the last few lines of previous text
                    last_lines = '\n'.join(prev_text.split('\n')[-5:]) if prev_text else ""
                    filename_match = re.search(r'([a-zA-Z_][a-zA-Z0-9_/.-]*\.(py|js|java|cpp|c|h|html|css|json|yaml|yml|md|txt|sql|sh|dockerfile|env))\s*$', last_lines, re.MULTILINE)
                    if not filename_match:
                        # Try broader search in the previous text
                        filename_match = re.search(r'([a-zA-Z_][a-zA-Z0-9_/.-]*\.(py|js|java|cpp|c|h|html|css|json|yaml|yml|md|txt|sql|sh|dockerfile|env))', prev_text[-300:] if prev_text else "")
                    
                    if filename_match and content and len(content) > 20:
                        matches.append((filename_match.group(1), content))
            if matches:
                logger.info(f"Found {len(matches)} files using pattern 'filename before code blocks'")
        
        # ENHANCED PATTERN 9: NEW - Very aggressive pattern to find any substantial code content
        if not matches:
            # Look for any code blocks that might contain substantial code, even without clear filenames
            aggressive_pattern = r'```(?:python|javascript|typescript|java|cpp|c|html|css|json|yaml|sql|shell|bash)?\s*\n(.*?)(?=\n```|$)'
            code_candidates = re.findall(aggressive_pattern, llm_output, re.DOTALL | re.IGNORECASE)
            
            for i, content in enumerate(code_candidates):
                content = content.strip()
                if len(content) > 50:  # Substantial content
                    # Try to infer filename from content
                    inferred_filename = _infer_filename_from_content(content, i)
                    if inferred_filename:
                        matches.append((inferred_filename, content))
            
            if matches:
                logger.info(f"Found {len(matches)} files using aggressive pattern with filename inference")
        
        # Process all matches
        for path, content in matches:
            # Clean the file path
            path = _clean_file_path(path)
            
            # Clean content
            content = _clean_file_content(content)
            
            # Ensure we have valid file path and content
            if path and content and len(content) > 20:  # Minimum content length
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
            
            # Try to identify patterns for debugging
            file_mentions = re.findall(r'FILE:', llm_output, re.IGNORECASE)
            code_blocks = re.findall(r'```', llm_output)
            filename_patterns = re.findall(r'\w+\.(py|js|java|cpp|c|h|html|css|json|yaml|yml|md|txt|sql|sh)', llm_output, re.IGNORECASE)
            hash_headers = re.findall(r'### [a-zA-Z_]', llm_output)
            
            logger.info(f"Debug info: {len(file_mentions)} 'FILE:' mentions, {len(code_blocks)} code blocks, {len(filename_patterns)} filename patterns, {len(hash_headers)} ### headers")
            
            # FALLBACK: Create emergency files if we found substantial content but no parseable files
            if len(llm_output) > 1000 and len(code_blocks) >= 2:
                logger.info("Creating emergency fallback files from substantial content")
                emergency_files = _create_emergency_files_from_content(llm_output)
                files.extend(emergency_files)
        
        logger.info(f"Successfully parsed {len(files)} files from LLM output")
        return files
        
    except Exception as e:
        logger.error(f"Error parsing LLM output: {e}")
        logger.info(f"LLM output causing error (first 1000 chars): {llm_output[:1000]}")
        
        # Even in error cases, try to create fallback files
        try:
            if len(llm_output) > 500:
                emergency_files = _create_emergency_files_from_content(llm_output)
                logger.info(f"Created {len(emergency_files)} emergency files despite parsing error")
                return emergency_files
        except Exception as fallback_error:
            logger.error(f"Even emergency file creation failed: {fallback_error}")
        
    return files

def _clean_file_path(path: str) -> str:
    """Clean and validate file path."""
    # Remove any markdown artifacts that might have leaked into the path
    path = path.strip().strip('\n').strip()
    
    if '```' in path:
        path = path.split('```')[0].strip()
    if '\n' in path:
        path = path.split('\n')[0].strip()
    
    # Remove common prefixes that might appear
    for prefix in ['**', '*', '`', '"', "'", '(', ')', '[', ']']:
        path = path.strip(prefix)
    
    return path

def _clean_file_content(content: str) -> str:
    """Clean and validate file content."""
    content = content.strip()
    
    # Remove common content artifacts
    if content.startswith('```'):
        content = content[3:].strip()
    if content.endswith('```'):
        content = content[:-3].strip()
    
    # Remove language specifiers that might be left at the start
    lines = content.split('\n')
    if lines and lines[0].strip() in ['python', 'javascript', 'typescript', 'java', 'cpp', 'c', 'html', 'css', 'json', 'yaml', 'sql', 'shell', 'bash']:
        content = '\n'.join(lines[1:]).strip()
    
    return content

def _infer_filename_from_content(content: str, index: int) -> str:
    """Infer appropriate filename from code content."""
    content_lower = content.lower()
    
    # Python patterns
    if any(pattern in content_lower for pattern in ['import ', 'def ', 'class ', 'from ', 'fastapi', 'flask', 'django']):
        if 'fastapi' in content_lower or 'app' in content_lower:
            return f"main.py"
        elif 'test' in content_lower:
            return f"test_{index}.py"
        elif 'config' in content_lower:
            return f"config.py"
        elif 'model' in content_lower or 'schema' in content_lower:
            return f"models.py"
        else:
            return f"module_{index}.py"
    
    # JavaScript/TypeScript patterns
    elif any(pattern in content_lower for pattern in ['function', 'const ', 'let ', 'var ', 'export', 'import']):
        if 'react' in content_lower or 'component' in content_lower:
            return f"Component{index}.tsx"
        elif 'test' in content_lower:
            return f"test{index}.js"
        else:
            return f"module{index}.js"
    
    # Config files
    elif any(pattern in content_lower for pattern in ['database_url', 'secret_key', 'api_key', 'host', 'port']):
        return f".env"
    
    # SQL patterns
    elif any(pattern in content_lower for pattern in ['create table', 'select', 'insert', 'update', 'delete']):
        return f"schema_{index}.sql"
    
    # Docker patterns
    elif any(pattern in content_lower for pattern in ['from ', 'run ', 'copy ', 'expose']):
        return f"Dockerfile"
    
    # YAML patterns
    elif any(pattern in content_lower for pattern in ['version:', 'services:', 'volumes:', 'networks:']):
        return f"docker-compose.yml"
    
    # Default
    else:
        return f"generated_file_{index}.txt"

def _create_emergency_files_from_content(llm_output: str) -> List[GeneratedFile]:
    """Create emergency files when normal parsing fails but we have substantial content."""
    files = []
    
    try:
        # Split by common separators and try to find code-like content
        chunks = re.split(r'\n\n+', llm_output)
        
        file_index = 0
        for chunk in chunks:
            chunk = chunk.strip()
            if len(chunk) > 100:  # Substantial content
                # Check if it looks like code
                if any(pattern in chunk.lower() for pattern in [
                    'import ', 'def ', 'class ', 'function', 'const ', 'var ', 'let ',
                    'from ', 'export', 'create table', 'select ', 'insert ', 'update '
                ]):
                    filename = _infer_filename_from_content(chunk, file_index)
                    files.append(
                        GeneratedFile(
                            file_path=filename,
                            content=chunk,
                            purpose=f"Emergency generated file: {filename}",
                            status="generated"
                        )
                    )
                    file_index += 1
                    
                    if len(files) >= 3:  # Limit emergency files
                        break
    
    except Exception as e:
        logger.error(f"Error creating emergency files: {e}")
    
    return files
