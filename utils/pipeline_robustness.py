"""
Pipeline Robustness Utilities

This module provides robust error handling, input validation, and retry mechanisms 
for the multi-agent development pipeline to prevent failures from invalid inputs,
parsing errors, and transient issues.
"""

import json
import logging
import time
from functools import wraps
from typing import Dict, Any, Optional, Callable, List, Union
from dataclasses import dataclass
import traceback

logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """Result of input validation with detailed error information."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    sanitized_input: Optional[Dict[str, Any]] = None

class RobustInputParser:
    """Handles robust parsing of various input formats from ReAct agents."""
    
    @staticmethod
    def parse_react_agent_input(tool_input: Any, expected_fields: List[str]) -> ValidationResult:
        """
        Parse input from ReAct agents with robust error handling.
        
        Args:
            tool_input: Raw input from ReAct agent (string, dict, or object)
            expected_fields: List of expected field names
            
        Returns:
            ValidationResult with parsed and validated input
        """
        errors = []
        warnings = []
        sanitized_input = {}
        
        try:
            # Handle different input types
            if isinstance(tool_input, dict):
                logger.debug("Received dict input - extracting fields directly")
                sanitized_input = tool_input.copy()
                
            elif isinstance(tool_input, str):
                logger.debug("Received string input - attempting JSON parsing")
                sanitized_input = RobustInputParser._parse_string_input(tool_input)
                
            elif hasattr(tool_input, '__dict__'):
                logger.debug("Received object input - converting to dict")
                sanitized_input = tool_input.__dict__.copy()
                
            else:
                errors.append(f"Unsupported input type: {type(tool_input)}")
                return ValidationResult(False, errors, warnings)
            
            # Validate expected fields
            missing_fields = [field for field in expected_fields if field not in sanitized_input]
            if missing_fields:
                warnings.append(f"Missing expected fields: {missing_fields}")
            
            # Clean up common issues
            sanitized_input = RobustInputParser._sanitize_input(sanitized_input)
            
            return ValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                sanitized_input=sanitized_input
            )
            
        except Exception as e:
            errors.append(f"Input parsing failed: {str(e)}")
            return ValidationResult(False, errors, warnings)
    
    @staticmethod
    def _parse_string_input(input_str: str) -> Dict[str, Any]:
        """Parse string input with multiple fallback strategies."""
        # Clean up common formatting issues
        cleaned = input_str.strip()
        
        # Handle escaped quotes from ReAct agents
        if '\\"' in cleaned:
            logger.debug("Detected escaped quotes - cleaning up")
            cleaned = cleaned.replace('\\"', '"')
            if cleaned.startswith('"') and cleaned.endswith('"'):
                cleaned = cleaned[1:-1]
        
        # Try parsing as JSON
        try:
            parsed = json.loads(cleaned)
            
            # Handle ReAct agent action_input format
            if isinstance(parsed, dict) and "action_input" in parsed:
                logger.debug("Found ReAct action_input format")
                action_input = parsed["action_input"]
                
                if isinstance(action_input, str):
                    try:
                        return json.loads(action_input)
                    except json.JSONDecodeError:
                        # Fallback: treat as raw string
                        return {"raw_input": action_input}
                else:
                    return action_input if isinstance(action_input, dict) else {"raw_input": str(action_input)}
            
            return parsed if isinstance(parsed, dict) else {"raw_input": cleaned}
            
        except json.JSONDecodeError:
            logger.debug("JSON parsing failed - treating as raw string")
            # Try to extract key-value pairs from comma-separated format
            if ',' in cleaned and '=' in cleaned:
                try:
                    pairs = {}
                    for pair in cleaned.split(','):
                        if '=' in pair:
                            key, value = pair.split('=', 1)
                            pairs[key.strip()] = value.strip()
                    return pairs
                except Exception:
                    pass
            
            return {"raw_input": cleaned}
    
    @staticmethod
    def _sanitize_input(input_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize input dictionary by cleaning common issues."""
        sanitized = {}
        
        for key, value in input_dict.items():
            # Clean key names
            clean_key = key.strip().lower().replace(' ', '_')
            
            # Handle different value types
            if isinstance(value, str):
                # Clean string values
                clean_value = value.strip()
                # Try to parse JSON strings
                if clean_value.startswith('{') or clean_value.startswith('['):
                    try:
                        clean_value = json.loads(clean_value)
                    except json.JSONDecodeError:
                        pass
                sanitized[clean_key] = clean_value
            else:
                sanitized[clean_key] = value
        
        return sanitized

class PipelineRetryManager:
    """Manages retry logic for pipeline operations."""
    
    @staticmethod
    def with_retry(max_retries: int = 3, backoff_factor: float = 1.0, 
                   exceptions: tuple = (Exception,)):
        """
        Decorator for retrying operations with exponential backoff.
        
        Args:
            max_retries: Maximum number of retry attempts
            backoff_factor: Exponential backoff multiplier
            exceptions: Tuple of exceptions to catch and retry
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                last_exception = None
                
                for attempt in range(max_retries + 1):
                    try:
                        return func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e
                        if attempt == max_retries:
                            logger.error(f"Function {func.__name__} failed after {max_retries} retries: {str(e)}")
                            raise
                        
                        wait_time = backoff_factor * (2 ** attempt)
                        logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {str(e)}. Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                
                raise last_exception
            return wrapper
        return decorator

class PipelineErrorHandler:
    """Centralized error handling for pipeline operations."""
    
    @staticmethod
    def safe_execute(func: Callable, fallback_result: Any = None, 
                    log_errors: bool = True) -> Dict[str, Any]:
        """
        Safely execute a function with comprehensive error handling.
        
        Args:
            func: Function to execute
            fallback_result: Result to return if function fails
            log_errors: Whether to log errors
            
        Returns:
            Dictionary with execution result and status
        """
        try:
            result = func()
            return {
                "success": True,
                "result": result,
                "error": None
            }
        except Exception as e:
            error_details = {
                "exception_type": type(e).__name__,
                "message": str(e),
                "traceback": traceback.format_exc() if log_errors else None
            }
            
            if log_errors:
                logger.error(f"Safe execution failed: {error_details}")
            
            return {
                "success": False,
                "result": fallback_result,
                "error": error_details
            }

def robust_tool_wrapper(expected_fields: List[str] = None, 
                       fallback_result: Any = None):
    """
    Decorator to make tools more robust against input validation failures.
    
    Args:
        expected_fields: List of expected input fields
        fallback_result: Result to return if validation fails
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                # Extract tool_input from kwargs
                tool_input = kwargs.get('tool_input', kwargs)
                
                # Validate and parse input if expected_fields provided
                if expected_fields:
                    validation_result = RobustInputParser.parse_react_agent_input(
                        tool_input, expected_fields
                    )
                    
                    if not validation_result.is_valid:
                        error_msg = f"Input validation failed: {validation_result.errors}"
                        logger.error(error_msg)
                        
                        if fallback_result is not None:
                            return fallback_result
                        else:
                            return {"error": error_msg}
                    
                    # Update kwargs with sanitized input
                    if validation_result.sanitized_input:
                        kwargs.update(validation_result.sanitized_input)
                
                # Execute the original function
                return func(*args, **kwargs)
                
            except Exception as e:
                error_msg = f"Tool execution failed: {str(e)}"
                logger.error(error_msg, exc_info=True)
                
                if fallback_result is not None:
                    return fallback_result
                else:
                    return {"error": error_msg}
        
        return wrapper
    return decorator

class PipelineHealthMonitor:
    """Monitors pipeline health and provides diagnostics."""
    
    def __init__(self):
        self.error_counts = {}
        self.success_counts = {}
        self.last_errors = {}
    
    def record_execution(self, agent_name: str, success: bool, error: str = None):
        """Record execution result for monitoring."""
        if success:
            self.success_counts[agent_name] = self.success_counts.get(agent_name, 0) + 1
        else:
            self.error_counts[agent_name] = self.error_counts.get(agent_name, 0) + 1
            if error:
                self.last_errors[agent_name] = error
    
    def get_health_report(self) -> Dict[str, Any]:
        """Generate health report for the pipeline."""
        total_executions = {}
        success_rates = {}
        
        all_agents = set(self.success_counts.keys()) | set(self.error_counts.keys())
        
        for agent in all_agents:
            success = self.success_counts.get(agent, 0)
            errors = self.error_counts.get(agent, 0)
            total = success + errors
            
            total_executions[agent] = total
            success_rates[agent] = (success / total * 100) if total > 0 else 0
        
        return {
            "total_executions": total_executions,
            "success_rates": success_rates,
            "recent_errors": self.last_errors,
            "healthy_agents": [agent for agent, rate in success_rates.items() if rate >= 80],
            "problematic_agents": [agent for agent, rate in success_rates.items() if rate < 50]
        }

# Global pipeline health monitor instance
pipeline_monitor = PipelineHealthMonitor() 