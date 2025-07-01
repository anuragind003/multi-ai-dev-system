"""
Universal ReAct Tool Wrapper

This module provides a decorator that automatically handles JSON string inputs
from ReAct agents, converting them to proper function arguments.
"""

import json
import logging
import functools
from typing import Any, Dict, Callable, Union
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

def react_compatible_tool(func: Callable) -> Callable:
    """
    Decorator that makes any tool compatible with ReAct agents by automatically
    parsing JSON string inputs and converting them to proper function arguments.
    
    Usage:
        @react_compatible_tool
        @tool  
        def my_tool(param1: str, param2: list) -> str:
            # Tool implementation
            pass
    """
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger.debug(f"ReAct tool wrapper called for {func.__name__} with args: {args}, kwargs: {kwargs}")
        
        # Handle any string arguments that might be JSON
        processed_kwargs = {}
        for key, value in kwargs.items():
            if isinstance(value, str):
                value = value.strip()
                
                # Skip empty strings
                if not value:
                    logger.debug(f"Empty string for {key}, skipping")
                    continue
                
                # Try to parse as JSON first
                try:
                    if (value.startswith('{') and value.endswith('}')) or \
                       (value.startswith('[') and value.endswith(']')):
                        parsed_value = json.loads(value)
                        logger.debug(f"Parsed JSON for {key}: {type(parsed_value)} = {parsed_value}")
                        processed_kwargs[key] = parsed_value
                    else:
                        # Check if the string contains JSON-like content even without proper delimiters
                        if '"' in value and ':' in value and any(marker in value for marker in ['{', '}', '[', ']']):
                            logger.debug(f"String for {key} contains JSON-like content, attempting robust parsing")
                            try:
                                # Use JsonHandler for robust parsing
                                from tools.json_handler import JsonHandler
                                parsed_value = JsonHandler.extract_json_from_text(value)
                                if parsed_value:
                                    processed_kwargs[key] = parsed_value
                                    logger.debug(f"Successfully parsed with JsonHandler for {key}")
                                else:
                                    processed_kwargs[key] = value
                            except Exception as e:
                                logger.debug(f"JsonHandler parsing failed for {key}: {e}, using as string")
                                processed_kwargs[key] = value
                        else:
                            processed_kwargs[key] = value
                except json.JSONDecodeError as e:
                    logger.debug(f"JSON parsing failed for {key}: {e}, using as string: {value[:100]}...")
                    processed_kwargs[key] = value
                except Exception as e:
                    logger.warning(f"Unexpected error parsing {key}: {e}, using as string")
                    processed_kwargs[key] = value
            else:
                processed_kwargs[key] = value
        
        # Special handling for functions that expect **kwargs (like tech stack tools)
        import inspect
        sig = inspect.signature(func)
        if any(param.kind == param.VAR_KEYWORD for param in sig.parameters.values()):
            # Function accepts **kwargs, pass everything through
            logger.debug(f"Function {func.__name__} accepts **kwargs, passing all parameters")
            return func(*args, **processed_kwargs)
        
        # Handle the case where all args come as a single JSON object
        if len(processed_kwargs) == 1 and len(args) == 0:
            key, value = next(iter(processed_kwargs.items()))
            
            # If the single argument is a dict, try to expand it
            if isinstance(value, dict):
                logger.debug(f"Expanding dict argument for {func.__name__}: {value}")
                try:
                    return func(**value)
                except TypeError as e:
                    logger.warning(f"Failed to expand dict for {func.__name__}: {e}, trying as single argument")
                    return func(value)
        
        # Use the processed kwargs
        logger.debug(f"Calling {func.__name__} with processed kwargs: {processed_kwargs}")
        try:
            return func(*args, **processed_kwargs)
        except Exception as e:
            logger.error(f"Error calling {func.__name__}: {e}")
            # Log the arguments for debugging
            logger.error(f"Arguments were: args={args}, kwargs={processed_kwargs}")
            raise
    
    return wrapper

def smart_react_tool(description: str = None, **tool_kwargs):
    """
    Combined decorator that creates a ReAct-compatible tool in one step.
    
    Usage:
        @smart_react_tool("Tool description")
        def my_tool(param1: str, param2: list) -> str:
            # Tool implementation
            pass
    """
    def decorator(func):
        # Apply the react compatibility wrapper first
        wrapped_func = react_compatible_tool(func)
        
        # Then apply the @tool decorator
        if description:
            return tool(description, **tool_kwargs)(wrapped_func)
        else:
            return tool(**tool_kwargs)(wrapped_func)
    
    return decorator 