"""
Shared utility functions for tools to ensure consistency across the system.
"""

import logging
import json
import re
from typing import Dict, Any

logger = logging.getLogger(__name__)

def clean_and_parse_json(response_text: str, context: str = "tool") -> Dict[str, Any]:
    """
    Centralized JSON parsing utility for consistent handling across all tools.
    
    Args:
        response_text: Raw LLM response text
        context: Context for error logging (e.g., "system design", "planning")
        
    Returns:
        Parsed JSON dict
        
    Raises:
        json.JSONDecodeError: If JSON cannot be parsed
    """
    try:
        # Check for empty response first
        if not response_text or len(response_text.strip()) == 0:
            logger.error(f"Empty response received for {context}")
            raise json.JSONDecodeError(f"Empty response received for {context}", response_text or "", 0)
        
        # Log response for debugging
        logger.info(f"Parsing {context} response ({len(response_text)} chars)")
        if len(response_text) < 200:
            logger.debug(f"{context} response preview: {response_text[:200]}")
        
        # Handle markdown code blocks and extract JSON
        if '```json' in response_text:
            # Extract JSON from markdown code block
            json_start = response_text.find('```json') + 7
            json_end = response_text.find('```', json_start)
            if json_end != -1:
                clean_json_str = response_text[json_start:json_end].strip()
            else:
                # Fallback to finding the JSON object
                json_start_index = response_text.index('{')
                json_end_index = response_text.rindex('}') + 1
                clean_json_str = response_text[json_start_index:json_end_index]
        elif '```' in response_text and '{' in response_text:
            # Handle generic code blocks
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            clean_json_str = response_text[json_start:json_end]
        else:
            # Standard JSON extraction
            if '{' not in response_text:
                logger.error(f"No JSON object found in {context} response")
                raise json.JSONDecodeError(f"No JSON object markers found in {context} response", response_text, 0)
            
            json_start_index = response_text.index('{')
            json_end_index = response_text.rindex('}') + 1
            clean_json_str = response_text[json_start_index:json_end_index]
        
        # Validate extracted JSON string
        if not clean_json_str or len(clean_json_str.strip()) == 0:
            logger.error(f"Extracted JSON string is empty for {context}")
            raise json.JSONDecodeError(f"Extracted JSON string is empty for {context}", response_text, 0)
        
        # Use a more robust method to clean up the JSON string
        # Remove trailing commas from objects and arrays
        clean_json_str = re.sub(r',\s*([}\]])', r'\1', clean_json_str)
        
        # Fix missing commas between JSON objects/arrays - common LLM error
        clean_json_str = re.sub(r'"\s*\n\s*"', '",\n    "', clean_json_str)
        clean_json_str = re.sub(r'}\s*\n\s*"', '},\n    "', clean_json_str)
        clean_json_str = re.sub(r']\s*\n\s*"', '],\n    "', clean_json_str)
        
        # Log cleaned JSON for debugging
        logger.debug(f"Cleaned {context} JSON length: {len(clean_json_str)}")
        
        # Try to parse the cleaned JSON
        parsed_json = json.loads(clean_json_str)
        logger.info(f"Successfully parsed {context} JSON with {len(parsed_json)} top-level keys")
        return parsed_json
        
    except (ValueError, IndexError) as e:
        logger.error(f"Failed to extract JSON from {context} response: {str(e)}")
        logger.debug(f"Response text preview: {response_text[:500]}...")
        raise json.JSONDecodeError(f"Could not find or parse JSON object in {context} response", response_text, 0)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing failed for {context}: {str(e)}")
        logger.debug(f"Failed JSON string preview: {clean_json_str[:500] if 'clean_json_str' in locals() else 'N/A'}...")
        raise e

def standardize_pydantic_input(input_data: Any) -> Dict[str, Any]:
    """
    Standardize input data to dictionary format for processing.
    
    Args:
        input_data: Input that might be a Pydantic model or dict
        
    Returns:
        Dictionary representation of the input
    """
    if hasattr(input_data, 'model_dump'):
        return input_data.model_dump()
    elif hasattr(input_data, 'dict'):
        return input_data.dict()
    elif isinstance(input_data, dict):
        return input_data
    else:
        # Convert to string representation and wrap in dict
        try:
            if isinstance(input_data, str):
                return json.loads(input_data)
            else:
                return {"content": str(input_data), "type": type(input_data).__name__}
        except (json.JSONDecodeError, Exception):
            return {"content": str(input_data), "type": type(input_data).__name__}

def create_error_response(error_msg: str, context: str, default_structure: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Create standardized error response across all tools.
    
    Args:
        error_msg: Error message to include
        context: Context where error occurred
        default_structure: Optional default structure to merge with error
        
    Returns:
        Standardized error response dict
    """
    base_error = {
        "status": "error",
        "error": error_msg,
        "context": context,
        "timestamp": json.dumps({"error_time": "now"}),  # Simple timestamp
    }
    
    if default_structure:
        # Merge default structure with error info
        result = {**default_structure, **base_error}
        return result
    
    return base_error

def validate_and_convert_pydantic(data: Dict[str, Any], model_class, context: str = "tool") -> Dict[str, Any]:
    """
    Try to validate data against a Pydantic model and return as dict.
    
    Args:
        data: Dictionary data to validate
        model_class: Pydantic model class to validate against
        context: Context for logging
        
    Returns:
        Dictionary representation (validated if possible, raw if not)
    """
    try:
        validated_obj = model_class(**data)
        logger.info(f"Successfully validated {context} data against {model_class.__name__}")
        return validated_obj.model_dump()
    except Exception as validation_error:
        logger.warning(f"{context} validation failed for {model_class.__name__}: {validation_error}")
        logger.info(f"Returning raw dict for {context}")
        return data

def log_tool_execution(tool_name: str, success: bool = True, error_msg: str = None, metadata: Dict[str, Any] = None):
    """
    Standardized logging for tool execution.
    
    Args:
        tool_name: Name of the tool being executed
        success: Whether execution was successful
        error_msg: Error message if failed
        metadata: Additional metadata to log
    """
    if success:
        logger.info(f" Tool '{tool_name}' executed successfully")
        if metadata:
            logger.debug(f"Tool '{tool_name}' metadata: {metadata}")
    else:
        logger.error(f" Tool '{tool_name}' failed: {error_msg}")
        if metadata:
            logger.debug(f"Tool '{tool_name}' failure metadata: {metadata}") 