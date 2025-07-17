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
    Robust parser for LLM output into files with error-proof pattern matching.
    
    Uses a systematic approach to extract files from various LLM output formats:
    1. ### FILE: path/to/file.ext
    2. ### path/to/file.ext (standalone filename)
    3. **path/to/file.ext**
    4. Files in code blocks with headers
    
    Args:
        llm_output: The raw text output from the LLM containing multiple file blocks
        
    Returns:
        List of GeneratedFile objects
    """
    files = []
    
    if not llm_output or not llm_output.strip():
        logger.warning("Empty or whitespace-only LLM output received")
        return files
    
    try:
        llm_output = llm_output.strip()
        logger.info(f"Parsing LLM output of {len(llm_output)} characters")
        
        # Use a multi-strategy approach with error handling for each strategy
        parsers = [
            _parse_file_colon_format,
            _parse_filename_header_format, 
            _parse_bold_filename_format,
            _parse_code_blocks_with_headers,
            _parse_filename_before_code_blocks,
            _parse_aggressive_code_inference
        ]
        
        for parser_func in parsers:
            try:
                parser_files = parser_func(llm_output)
                if parser_files:
                    files.extend(parser_files)
                    logger.info(f"Parser {parser_func.__name__} found {len(parser_files)} files")
                    break  # Use first successful parser
            except Exception as e:
                logger.warning(f"Parser {parser_func.__name__} failed: {e}")
                continue
        
        # Final validation and cleanup
        validated_files = []
        for file in files:
            if _validate_generated_file(file):
                validated_files.append(file)
            else:
                logger.warning(f"Discarded invalid file: {file.file_path}")
        
        if not validated_files:
            logger.warning(f"No valid files parsed from LLM output. Attempting emergency parsing...")
            validated_files = _emergency_parse_fallback(llm_output)
        
        logger.info(f"Successfully parsed {len(validated_files)} valid files from LLM output")
        return validated_files
        
    except Exception as e:
        logger.error(f"Critical error in parse_llm_output_into_files: {e}")
        logger.debug(f"LLM output causing error (first 1000 chars): {llm_output[:1000] if len(llm_output) > 1000 else llm_output}")
        
        # Last resort emergency parsing
        try:
            emergency_files = _emergency_parse_fallback(llm_output)
            if emergency_files:
                logger.info(f"Emergency parsing created {len(emergency_files)} files")
                return emergency_files
        except Exception as fallback_error:
            logger.error(f"Even emergency parsing failed: {fallback_error}")
        
        return []

def _parse_file_colon_format(llm_output: str) -> List[GeneratedFile]:
    """Parse ### FILE: path format."""
    files = []
    pattern = r"### FILE:\s*([^\n]+)\s*\n```[a-zA-Z]*\s*\n(.*?)(?=\n```)"
    matches = re.findall(pattern, llm_output, re.DOTALL)
    
    for filepath, content in matches:
        filepath = _clean_file_path(filepath)
        content = _clean_file_content(content)
        if filepath and content:
            files.append(GeneratedFile(
                file_path=filepath,
                content=content,
                purpose=f"Generated file: {filepath}",
                status="generated"
            ))
    
    return files

def _parse_filename_header_format(llm_output: str) -> List[GeneratedFile]:
    """Parse ### filename.ext format."""
    files = []
    # More robust pattern that handles file paths with directories
    pattern = r"### ([^\n]+\.[a-zA-Z0-9]+)\s*\n```[a-zA-Z]*\s*\n(.*?)(?=\n```)"
    matches = re.findall(pattern, llm_output, re.DOTALL)
    
    for filepath, content in matches:
        filepath = _clean_file_path(filepath)
        content = _clean_file_content(content)
        if filepath and content and _is_valid_filename(filepath):
            files.append(GeneratedFile(
                file_path=filepath,
                content=content,
                purpose=f"Generated file: {filepath}",
                status="generated"
            ))
    
    return files

def _parse_bold_filename_format(llm_output: str) -> List[GeneratedFile]:
    """Parse **filename.ext** format."""
    files = []
    pattern = r"\*\*([^\n]+\.[a-zA-Z0-9]+)\*\*\s*\n```[a-zA-Z]*\s*\n(.*?)(?=\n```)"
    matches = re.findall(pattern, llm_output, re.DOTALL)
    
    for filepath, content in matches:
        filepath = _clean_file_path(filepath)
        content = _clean_file_content(content)
        if filepath and content and _is_valid_filename(filepath):
            files.append(GeneratedFile(
                file_path=filepath,
                content=content,
                purpose=f"Generated file: {filepath}",
                status="generated"
            ))
    
    return files

def _parse_code_blocks_with_headers(llm_output: str) -> List[GeneratedFile]:
    """Parse code blocks that contain multiple files with ### headers inside."""
    files = []
    
    # Find all code blocks
    code_block_pattern = r'```[a-zA-Z]*\s*\n(.*?)(?=\n```|$)'
    code_blocks = re.findall(code_block_pattern, llm_output, re.DOTALL)
    
    for block_content in code_blocks:
        # Look for ### headers within the block
        file_sections = re.split(r'\n### ', block_content)
        
        for section in file_sections:
            if not section.strip():
                continue
                
            # Extract filename from the start of the section
            lines = section.split('\n')
            if not lines:
                continue
                
            potential_filename = lines[0].strip()
            if _is_valid_filename(potential_filename):
                content = '\n'.join(lines[1:]).strip()
                if content and len(content) > 20:
                    files.append(GeneratedFile(
                        file_path=potential_filename,
                        content=content,
                        purpose=f"Generated file: {potential_filename}",
                        status="generated"
                    ))
    
    return files

def _parse_filename_before_code_blocks(llm_output: str) -> List[GeneratedFile]:
    """Parse filenames that appear before code blocks."""
    files = []
    
    # Split by code block boundaries
    parts = re.split(r'```[a-zA-Z]*\s*\n', llm_output)
    
    for i in range(1, len(parts)):
        # Get code content (everything until next ``` or end)
        content_match = re.match(r'(.*?)(?=\n```|$)', parts[i], re.DOTALL)
        if not content_match:
            continue
            
        content = content_match.group(1).strip()
        if len(content) < 20:
            continue
            
        # Look for filename in the previous part
        prev_text = parts[i-1] if i > 0 else ""
        
        # Check last few lines for filename patterns
        last_lines = prev_text.split('\n')[-3:]  # Check last 3 lines
        filename = None
        
        for line in reversed(last_lines):
            line = line.strip()
            if _is_valid_filename(line):
                filename = line
                break
            
            # Remove common prefixes and try again
            cleaned_line = re.sub(r'^[#*\-\d\.\s]+', '', line).strip()
            if _is_valid_filename(cleaned_line):
                filename = cleaned_line
                break
        
        if filename:
            files.append(GeneratedFile(
                file_path=filename,
                content=content,
                purpose=f"Generated file: {filename}",
                status="generated"
            ))
    
    return files

def _parse_aggressive_code_inference(llm_output: str) -> List[GeneratedFile]:
    """Aggressively parse any code blocks and infer filenames."""
    files = []
    
    # Find all code blocks regardless of language specification
    pattern = r'```[a-zA-Z]*\s*\n(.*?)(?=\n```|$)'
    code_blocks = re.findall(pattern, llm_output, re.DOTALL)
    
    for i, content in enumerate(code_blocks):
        content = content.strip()
        if len(content) > 50:  # Substantial content only
            inferred_filename = _infer_filename_from_content(content, i)
            if inferred_filename:
                files.append(GeneratedFile(
                    file_path=inferred_filename,
                    content=content,
                    purpose=f"Inferred file: {inferred_filename}",
                    status="generated"
                ))
    
    return files

def _emergency_parse_fallback(llm_output: str) -> List[GeneratedFile]:
    """Emergency fallback parser when all else fails."""
    files = []
    
    try:
        # Look for any substantial text blocks that might be code
        chunks = re.split(r'\n\n+', llm_output)
        
        file_index = 0
        for chunk in chunks:
            chunk = chunk.strip()
            if len(chunk) > 100:  # Substantial content
                # Check if it looks like code or structured content
                if any(indicator in chunk.lower() for indicator in [
                    'import ', 'function', 'def ', 'class ', 'const ', 'var ', 'let ',
                    'from ', 'export', '{', '}', '()', 'return', 'if ', 'for ', 'while ',
                    '"name":', '"version":', '"dependencies":', 'CREATE TABLE', 'SELECT',
                    'FROM', 'WHERE', 'INSERT', 'UPDATE', 'DELETE'
                ]):
                    filename = _infer_filename_from_content(chunk, file_index)
                    if filename:
                        files.append(GeneratedFile(
                            file_path=filename,
                            content=chunk,
                            purpose=f"Emergency parsed file: {filename}",
                            status="generated"
                        ))
                        file_index += 1
                        
                        if len(files) >= 5:  # Limit emergency files
                            break
    
    except Exception as e:
        logger.error(f"Emergency parsing failed: {e}")
    
    return files

def _is_valid_filename(filename: str) -> bool:
    """Check if a string is a valid filename with more flexible validation."""
    if not filename or len(filename) < 3:
        return False
    
    # Get the basename for checking known files without extensions
    basename = filename.split('/')[-1].lower()
    
    # Check known files without extensions first (like Makefile, Dockerfile)
    known_files_no_ext = {
        'dockerfile', 'makefile', 'rakefile', 'procfile', 'license', 'readme', 
        'changelog', 'cmakelists', 'vagrantfile', 'buildfile', 'jakefile'
    }
    
    if basename in known_files_no_ext:
        return True
    
    # Must have an extension for other files
    if '.' not in filename:
        return False
    
    # Expanded list of valid file extensions - much more inclusive
    valid_extensions = {
        # Programming languages
        'py', 'js', 'ts', 'jsx', 'tsx', 'java', 'cpp', 'c', 'h', 'hpp', 'cs', 'go', 'rs', 'php', 'rb', 'swift', 'kt',
        # Web technologies
        'html', 'css', 'scss', 'sass', 'less', 'vue', 'svelte',
        # Data formats
        'json', 'yaml', 'yml', 'xml', 'csv', 'tsv', 'toml', 'ini', 'conf', 'cfg', 'properties',
        # Documentation
        'md', 'txt', 'rst', 'adoc', 'tex',
        # Database
        'sql', 'db', 'sqlite', 'mdb',
        # Scripts and executables
        'sh', 'bash', 'zsh', 'fish', 'ps1', 'bat', 'cmd',
        # Infrastructure and DevOps
        'tf', 'tfvars', 'dockerfile', 'dockerignore', 'env', 'envrc',
        # CI/CD and automation
        'jenkinsfile', 'gitlab-ci', 'github', 'actions',
        # Package managers
        'lock', 'sum', 'mod', 'gradle', 'maven', 'pom',
        # Version control
        'gitignore', 'gitattributes', 'gitmodules',
        # Other common extensions
        'log', 'tmp', 'bak', 'backup', 'example', 'template', 'spec', 'test',
        # No extension files (common in Unix/Linux)
        'makefile', 'rakefile', 'cmakelists', 'procfile', 'license', 'readme', 'changelog'
    }
    
    # Get the extension, handling files without traditional extensions
    if '.' in filename:
        extension = filename.split('.')[-1].lower()
    else:
        # Handle files without extensions (like Dockerfile, Makefile, etc.)
        extension = filename.lower()
    
    # Check against valid extensions
    if extension in valid_extensions:
        return True
    
    # Also check if the full filename (without path) is a known file
    basename = filename.split('/')[-1].lower()
    known_files = {
        'dockerfile', 'makefile', 'rakefile', 'procfile', 'license', 'readme', 
        'changelog', 'cmakelists.txt', 'requirements.txt', 'package.json',
        'tsconfig.json', 'webpack.config.js', 'babel.config.js', '.env',
        '.gitignore', '.dockerignore', '.editorconfig', '.eslintrc', '.prettierrc'
    }
    
    if basename in known_files:
        return True
    
    # More lenient filename validation - allow common DevOps and infrastructure patterns
    if re.match(r'^[a-zA-Z0-9_/.-]+$', filename):
        return True
    
    # Allow files with common prefixes/suffixes even if extension not recognized
    filename_lower = filename.lower()
    if any(pattern in filename_lower for pattern in [
        'docker', 'config', 'setup', 'deploy', 'build', 'test', 'spec',
        'terraform', 'ansible', 'kubernetes', 'k8s', 'helm'
    ]):
        return True
    
    return False

def _validate_generated_file(file: GeneratedFile) -> bool:
    """Validate a generated file object with more flexible criteria."""
    try:
        if not file or not file.file_path or not file.content:
            return False
        
        if not _is_valid_filename(file.file_path):
            logger.debug(f"File rejected due to invalid filename: {file.file_path}")
            return False
        
        # More lenient content validation - allow smaller files for config/infrastructure
        content_length = len(file.content.strip())
        
        # Different minimum lengths based on file type
        filename_lower = file.file_path.lower()
        
        if any(ext in filename_lower for ext in ['.env', '.gitignore', '.dockerignore']):
            # Environment and ignore files can be very short
            min_length = 1
        elif any(ext in filename_lower for ext in ['.tf', '.yml', '.yaml', '.json']):
            # Infrastructure and config files can be short but meaningful
            min_length = 5
        elif any(pattern in filename_lower for pattern in ['dockerfile', 'makefile', 'requirements']):
            # Build files can be short
            min_length = 3  # Even shorter for build files
        else:
            # Default minimum for code files
            min_length = 10
        
        if content_length < min_length:
            logger.debug(f"File rejected due to insufficient content: {file.file_path} ({content_length} chars, min: {min_length})")
            return False
        
        return True
    
    except Exception as e:
        logger.warning(f"Error validating file: {e}")
        return False

def _clean_file_path(path: str) -> str:
    """Clean and validate file path with robust error handling."""
    if not path:
        return ""
    
    try:
        # Remove any markdown artifacts that might have leaked into the path
        path = str(path).strip()
        
        # Remove code block markers
        if '```' in path:
            path = path.split('```')[0].strip()
        
        # Take only the first line (filename should be on one line)
        if '\n' in path:
            path = path.split('\n')[0].strip()
        
        # Remove common markdown/formatting artifacts
        cleanup_patterns = [
            r'^\*+\s*',  # Leading asterisks
            r'^\#+\s*',  # Leading hashes
            r'^`+\s*',   # Leading backticks
            r'\s*`+$',   # Trailing backticks
            r'^["\'\[\(]+',  # Leading quotes/brackets
            r'["\'\]\)]+$',  # Trailing quotes/brackets
            r'^\s*-\s*',     # Leading dash
            r'^\s*\d+\.\s*', # Leading numbers with dots
        ]
        
        for pattern in cleanup_patterns:
            path = re.sub(pattern, '', path)
        
        # Final cleanup
        path = path.strip()
        
        # Ensure we don't have weird characters
        if not re.match(r'^[a-zA-Z0-9_/.-]+$', path):
            # Try to extract valid filename from the string
            filename_match = re.search(r'([a-zA-Z0-9_/.-]+\.[a-zA-Z0-9]+)', path)
            if filename_match:
                path = filename_match.group(1)
            else:
                return ""
        
        return path
    
    except Exception as e:
        logger.warning(f"Error cleaning file path '{path}': {e}")
        return ""

def _clean_file_content(content: str) -> str:
    """Clean and validate file content with robust error handling."""
    if not content:
        return ""
    
    try:
        content = str(content).strip()
        
        # Remove code block markers from start/end
        if content.startswith('```'):
            # Find the end of the language specifier line
            lines = content.split('\n')
            if len(lines) > 1:
                content = '\n'.join(lines[1:])
            else:
                content = content[3:]
        
        if content.endswith('```'):
            content = content[:-3].strip()
        
        # Remove language specifiers that might be at the start
        lines = content.split('\n')
        if lines and len(lines[0].strip()) < 20:  # Language specifiers are usually short
            first_line = lines[0].strip().lower()
            known_languages = {
                'python', 'javascript', 'typescript', 'java', 'cpp', 'c', 'c++',
                'html', 'css', 'json', 'yaml', 'yml', 'sql', 'shell', 'bash',
                'js', 'ts', 'jsx', 'tsx', 'xml', 'dockerfile'
            }
            
            if first_line in known_languages:
                content = '\n'.join(lines[1:]) if len(lines) > 1 else ""
        
        # Final cleanup
        content = content.strip()
        
        return content
    
    except Exception as e:
        logger.warning(f"Error cleaning file content: {e}")
        return ""

def _infer_filename_from_content(content: str, index: int) -> str:
    """Infer appropriate filename from code content with improved accuracy."""
    if not content:
        return f"generated_file_{index}.txt"
    
    try:
        content_lower = content.lower()
        content_lines = content.split('\n')
        
        # Look for explicit filename hints in comments
        for line in content_lines[:10]:  # Check first 10 lines
            line_clean = line.strip().lower()
            if any(hint in line_clean for hint in ['filename:', 'file:', 'name:']):
                filename_match = re.search(r'([a-zA-Z0-9_/.-]+\.[a-zA-Z0-9]+)', line)
                if filename_match:
                    return filename_match.group(1)
        
        # Python patterns - be more specific
        if any(pattern in content_lower for pattern in ['import ', 'def ', 'class ', 'from ']):
            if 'fastapi' in content_lower and any(word in content_lower for word in ['app', 'router', 'endpoint']):
                return "main.py"
            elif 'flask' in content_lower and any(word in content_lower for word in ['app', 'route']):
                return "app.py"
            elif 'django' in content_lower:
                if 'models' in content_lower:
                    return "models.py"
                elif 'views' in content_lower:
                    return "views.py"
                else:
                    return "django_app.py"
            elif any(test_word in content_lower for test_word in ['test_', 'unittest', 'pytest']):
                return f"test_{index}.py"
            elif any(config_word in content_lower for config_word in ['config', 'settings', 'database_url']):
                return "config.py"
            elif any(model_word in content_lower for model_word in ['class ', 'schema', 'pydantic']):
                return "models.py"
            elif 'requirements' in content_lower or all(line.strip() and '==' in line for line in content_lines[:5]):
                return "requirements.txt"
            else:
                return f"module_{index}.py"
        
        # JavaScript/TypeScript patterns
        elif any(pattern in content_lower for pattern in ['function', 'const ', 'let ', 'var ', 'export', 'import']):
            if any(react_word in content_lower for react_word in ['react', 'component', 'jsx', 'tsx']):
                if 'test' in content_lower or 'spec' in content_lower:
                    return f"Component{index}.test.tsx"
                else:
                    return f"Component{index}.tsx"
            elif 'node' in content_lower or 'express' in content_lower:
                if 'server' in content_lower:
                    return "server.js"
                elif 'app' in content_lower:
                    return "app.js"
                else:
                    return f"module{index}.js"
            elif 'test' in content_lower or 'spec' in content_lower:
                return f"test{index}.js"
            elif 'package' in content_lower and '"name"' in content:
                return "package.json"
            else:
                return f"module{index}.js"
        
        # JSON patterns
        elif content.strip().startswith('{') and content.strip().endswith('}'):
            try:
                # Try to parse as JSON to verify
                import json
                json.loads(content)
                
                if '"name"' in content and '"version"' in content:
                    return "package.json"
                elif '"dependencies"' in content or '"scripts"' in content:
                    return "package.json"
                elif 'config' in content_lower or 'settings' in content_lower:
                    return "config.json"
                else:
                    return f"data_{index}.json"
            except:
                return f"data_{index}.json"
        
        # SQL patterns
        elif any(pattern in content_lower for pattern in ['create table', 'select', 'insert', 'update', 'delete', 'alter table']):
            if 'create table' in content_lower:
                return f"schema_{index}.sql"
            else:
                return f"query_{index}.sql"
        
        # Docker patterns
        elif any(pattern in content_lower for pattern in ['from ', 'run ', 'copy ', 'expose', 'cmd ']):
            if 'docker-compose' in content_lower or 'services:' in content_lower:
                return "docker-compose.yml"
            else:
                return "Dockerfile"
        
        # YAML patterns
        elif any(pattern in content_lower for pattern in ['version:', 'services:', 'volumes:', 'networks:']):
            if 'docker-compose' in content_lower or 'services:' in content_lower:
                return "docker-compose.yml"
            else:
                return f"config_{index}.yml"
        
        # Environment file patterns
        elif any(pattern in content for pattern in ['=', 'export ', 'DATABASE_URL', 'API_KEY', 'SECRET']):
            lines_with_equals = [line for line in content_lines if '=' in line and not line.strip().startswith('#')]
            if len(lines_with_equals) > 2:  # Multiple environment variables
                return ".env"
        
        # HTML patterns
        elif any(pattern in content_lower for pattern in ['<html', '<body', '<div', '<head', '<!doctype']):
            return f"index_{index}.html"
        
        # CSS patterns
        elif any(pattern in content_lower for pattern in ['{', '}', 'margin', 'padding', 'color:', 'background']):
            if '{' in content and '}' in content:  # Looks like CSS
                return f"styles_{index}.css"
        
        # Markdown patterns
        elif any(pattern in content for pattern in ['# ', '## ', '### ', '```', '[', '](']):
            return f"README_{index}.md"
        
        # Default based on content characteristics
        else:
            if len(content) > 500:  # Large content
                return f"large_file_{index}.txt"
            else:
                return f"generated_file_{index}.txt"
    
    except Exception as e:
        logger.warning(f"Error inferring filename from content: {e}")
        return f"error_file_{index}.txt"


