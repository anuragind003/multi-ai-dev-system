#!/usr/bin/env python3
"""
Script to fix Pydantic v2 deprecation warnings in tech_stack_tools.py
Replaces .dict() with .model_dump() and .json() with .model_dump_json()
"""

import re
import os

def fix_pydantic_deprecations(file_path):
    """Fix Pydantic v2 deprecation warnings in the given file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Replace .dict() with .model_dump()
    # Handle various patterns
    patterns_dict = [
        (r'\.dict\(\)', '.model_dump()'),
        (r'result\.dict\(\)', 'result.model_dump()'),
        (r'opt\.dict\(\)', 'opt.model_dump()'),
        (r'hasattr\((\w+), "dict"\)', r'hasattr(\1, "model_dump")'),
    ]
    
    for pattern, replacement in patterns_dict:
        content = re.sub(pattern, replacement, content)
    
    # Replace .json() with .model_dump_json()
    patterns_json = [
        (r'\.json\(\)', '.model_dump_json()'),
        (r'result\.json\(\)', 'result.model_dump_json()'),
        (r'hasattr\((\w+), "json"\)', r'hasattr(\1, "model_dump_json")'),
    ]
    
    for pattern, replacement in patterns_json:
        content = re.sub(pattern, replacement, content)
    
    # Special case for the complex return statements
    complex_patterns = [
        (
            r'return result\.model_dump\(\) if hasattr\(result, "model_dump"\) else \(result\.model_dump_json\(\) if hasattr\(result, "model_dump_json"\) else str\(result\)\)',
            'return result.model_dump() if hasattr(result, "model_dump") else str(result)'
        ),
        (
            r'return _json\.loads\(result\.model_dump_json\(\)\)',
            'return result.model_dump()'
        )
    ]
    
    for pattern, replacement in complex_patterns:
        content = re.sub(pattern, replacement, content)
    
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed Pydantic deprecations in {file_path}")
        return True
    else:
        print(f"No changes needed in {file_path}")
        return False

if __name__ == "__main__":
    file_path = "c:/Users/50101733/BRD_Recommendation/multi-ai-dev-system/tools/tech_stack_tools.py"
    fix_pydantic_deprecations(file_path)
