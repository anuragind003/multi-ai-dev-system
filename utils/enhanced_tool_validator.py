"""
Enhanced Tool Validation Wrapper for Multi-Agent System

This module provides enhanced validation for tools used by ReAct agents,
with API token optimization and hybrid validation integration.

Key Features:
- Hybrid validation integration
- API token usage tracking and optimization
- ReAct agent input handling
- Comprehensive error recovery
- Performance monitoring
"""

import functools
import time
import logging
from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass, field

from .hybrid_validator import HybridValidator, HybridValidationResult, ValidationLevel

logger = logging.getLogger(__name__)

@dataclass
class ToolPerformanceMetrics:
    """Track performance metrics for tool calls."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    avg_response_time: float = 0.0
    api_tokens_used: int = 0
    validation_stats: Dict[str, int] = field(default_factory=dict)
    
    def update_call(self, success: bool, response_time: float, tokens_used: int = 0, validation_level: str = "unknown"):
        """Update metrics for a tool call."""
        self.total_calls += 1
        if success:
            self.successful_calls += 1
        else:
            self.failed_calls += 1
        
        # Update average response time
        self.avg_response_time = ((self.avg_response_time * (self.total_calls - 1)) + response_time) / self.total_calls
        self.api_tokens_used += tokens_used
        
        # Update validation stats
        if validation_level not in self.validation_stats:
            self.validation_stats[validation_level] = 0
        self.validation_stats[validation_level] += 1
    
    def get_success_rate(self) -> float:
        """Get the success rate as a percentage."""
        if self.total_calls == 0:
            return 0.0
        return (self.successful_calls / self.total_calls) * 100
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of performance metrics."""
        return {
            "total_calls": self.total_calls,
            "success_rate": f"{self.get_success_rate():.1f}%",
            "avg_response_time": f"{self.avg_response_time:.2f}s",
            "api_tokens_used": self.api_tokens_used,
            "validation_distribution": self.validation_stats
        }

class EnhancedToolValidator:
    """
    Enhanced tool validator with hybrid validation and performance tracking.
    Designed specifically for React agents with API token optimization.
    """
    
    def __init__(self):
        self.hybrid_validator = HybridValidator(logger)
        self.tool_metrics: Dict[str, ToolPerformanceMetrics] = {}
        self.api_call_tracker = {}
        
    def create_validated_tool(
        self,
        tool_function: Callable,
        tool_name: str,
        expected_schema: Optional[type] = None,
        required_fields: Optional[List[str]] = None,
        fallback_extractors: Optional[List[Callable]] = None,
        enable_caching: bool = True,
        max_retries: int = 2
    ) -> Callable:
        """
        Create a validated version of a tool with hybrid validation and performance tracking.
        
        Args:
            tool_function: The original tool function
            tool_name: Name of the tool for tracking
            expected_schema: Pydantic schema for validation (optional)
            required_fields: List of required field names
            fallback_extractors: Custom extraction functions
            enable_caching: Whether to enable response caching
            max_retries: Maximum number of retries on failure
        
        Returns:
            Enhanced tool function with validation and tracking
        """
        
        # Initialize metrics for this tool
        if tool_name not in self.tool_metrics:
            self.tool_metrics[tool_name] = ToolPerformanceMetrics()
        
        @functools.wraps(tool_function)
        def validated_tool_wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            metrics = self.tool_metrics[tool_name]
            
            try:
                # Log the call
                logger.debug(f"Enhanced tool '{tool_name}' called with args: {args}, kwargs: {kwargs}")
                
                # Check for cached response if enabled
                if enable_caching:
                    cache_key = self._generate_cache_key(tool_name, args, kwargs)
                    cached_response = self._get_cached_response(cache_key)
                    if cached_response is not None:
                        logger.debug(f"Cache hit for tool '{tool_name}'")
                        return cached_response
                
                # Validate inputs if schema is provided
                validation_result = None
                if expected_schema and required_fields:
                    # Combine args and kwargs for validation
                    combined_input = self._combine_inputs(args, kwargs)
                    
                    validation_result = self.hybrid_validator.validate_progressive(
                        raw_input=combined_input,
                        pydantic_model=expected_schema,
                        required_fields=required_fields,
                        fallback_extractors=fallback_extractors,
                        context=f"Tool: {tool_name}"
                    )
                    
                    if not validation_result.success:
                        error_msg = f"Tool '{tool_name}' validation failed: {validation_result.errors}"
                        logger.error(error_msg)
                        
                        # Update metrics for failed validation
                        response_time = time.time() - start_time
                        metrics.update_call(False, response_time, 0, "validation_failed")
                        
                        return {
                            "error": error_msg,
                            "validation_details": {
                                "errors": validation_result.errors,
                                "warnings": validation_result.warnings,
                                "confidence": validation_result.confidence_score
                            }
                        }
                    
                    # Use validated data for tool call
                    if validation_result.data:
                        kwargs.update(validation_result.data)
                
                # Call the original tool function with retry logic
                result = self._call_with_retries(tool_function, args, kwargs, max_retries, tool_name)
                
                # Cache the result if enabled
                if enable_caching and result:
                    self._cache_response(cache_key, result)
                
                # Update metrics for successful call
                response_time = time.time() - start_time
                validation_level = validation_result.level_used.value if validation_result else "no_validation"
                metrics.update_call(True, response_time, 0, validation_level)
                
                # Add validation metadata to result if available
                if validation_result and isinstance(result, dict):
                    result["_validation_metadata"] = {
                        "level_used": validation_result.level_used.value,
                        "confidence": validation_result.confidence_score,
                        "warnings": validation_result.warnings
                    }
                
                logger.debug(f"Tool '{tool_name}' completed successfully in {response_time:.2f}s")
                return result
                
            except Exception as e:
                response_time = time.time() - start_time
                metrics.update_call(False, response_time, 0, "exception")
                
                logger.error(f"Tool '{tool_name}' failed with exception: {str(e)}")
                
                return {
                    "error": f"Tool execution failed: {str(e)}",
                    "tool_name": tool_name,
                    "execution_time": response_time
                }
        
        return validated_tool_wrapper
    
    def _combine_inputs(self, args: tuple, kwargs: dict) -> Dict[str, Any]:
        """Combine args and kwargs into a single dictionary for validation."""
        combined = kwargs.copy()
        
        # If there are positional args, add them with generic names
        for i, arg in enumerate(args):
            if isinstance(arg, dict):
                combined.update(arg)
            else:
                combined[f"arg_{i}"] = arg
        
        return combined
    
    def _call_with_retries(
        self, tool_function: Callable, args: tuple, kwargs: dict, 
        max_retries: int, tool_name: str
    ) -> Any:
        """Call tool function with retry logic for API failures."""
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    # Add exponential backoff for retries
                    wait_time = min(2 ** attempt, 10)  # Max 10 seconds
                    logger.info(f"Retrying tool '{tool_name}' in {wait_time}s (attempt {attempt + 1}/{max_retries + 1})")
                    time.sleep(wait_time)
                
                result = tool_function(*args, **kwargs)
                
                if attempt > 0:
                    logger.info(f"Tool '{tool_name}' succeeded on retry {attempt}")
                
                return result
                
            except Exception as e:
                last_exception = e
                error_str = str(e).lower()
                
                # Check if it's a retryable error (API rate limits, network issues, etc.)
                retryable_errors = [
                    "rate limit", "quota", "429", "503", "502", "timeout",
                    "connection", "network", "resource exhausted"
                ]
                
                is_retryable = any(error in error_str for error in retryable_errors)
                
                if not is_retryable or attempt >= max_retries:
                    break
                
                logger.warning(f"Tool '{tool_name}' failed with retryable error (attempt {attempt + 1}): {e}")
        
        # All retries exhausted
        raise last_exception
    
    def _generate_cache_key(self, tool_name: str, args: tuple, kwargs: dict) -> str:
        """Generate a cache key for the tool call."""
        import hashlib
        
        # Create a string representation of the inputs
        key_data = f"{tool_name}:{str(args)}:{str(sorted(kwargs.items()))}"
        
        # Use hash to create a fixed-length key
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _get_cached_response(self, cache_key: str) -> Optional[Any]:
        """Get cached response if available and not expired."""
        # Simple in-memory cache with 5-minute expiration
        cache_entry = self.api_call_tracker.get(cache_key)
        if cache_entry:
            cache_time, response = cache_entry
            if time.time() - cache_time < 300:  # 5 minutes
                return response
            else:
                # Remove expired entry
                del self.api_call_tracker[cache_key]
        
        return None
    
    def _cache_response(self, cache_key: str, response: Any) -> None:
        """Cache the response with timestamp."""
        self.api_call_tracker[cache_key] = (time.time(), response)
        
        # Simple cache size management
        if len(self.api_call_tracker) > 100:  # Keep max 100 entries
            # Remove oldest entries
            sorted_entries = sorted(self.api_call_tracker.items(), key=lambda x: x[1][0])
            for key, _ in sorted_entries[:20]:  # Remove 20 oldest
                del self.api_call_tracker[key]
    
    def get_tool_performance_report(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """Get performance report for a specific tool or all tools."""
        if tool_name:
            if tool_name in self.tool_metrics:
                return {
                    "tool": tool_name,
                    "metrics": self.tool_metrics[tool_name].get_summary()
                }
            else:
                return {"error": f"No metrics found for tool '{tool_name}'"}
        
        # Return report for all tools
        report = {
            "total_tools": len(self.tool_metrics),
            "tools": {}
        }
        
        for name, metrics in self.tool_metrics.items():
            report["tools"][name] = metrics.get_summary()
        
        # Add overall statistics
        total_calls = sum(m.total_calls for m in self.tool_metrics.values())
        total_successful = sum(m.successful_calls for m in self.tool_metrics.values())
        total_tokens = sum(m.api_tokens_used for m in self.tool_metrics.values())
        
        report["overall"] = {
            "total_calls": total_calls,
            "overall_success_rate": f"{(total_successful / total_calls * 100):.1f}%" if total_calls > 0 else "0%",
            "total_api_tokens": total_tokens,
            "cache_entries": len(self.api_call_tracker)
        }
        
        return report
    
    def clear_cache(self) -> None:
        """Clear the response cache."""
        self.api_call_tracker.clear()
        logger.info("Tool response cache cleared")
    
    def reset_metrics(self, tool_name: Optional[str] = None) -> None:
        """Reset performance metrics for a specific tool or all tools."""
        if tool_name:
            if tool_name in self.tool_metrics:
                self.tool_metrics[tool_name] = ToolPerformanceMetrics()
                logger.info(f"Metrics reset for tool '{tool_name}'")
        else:
            self.tool_metrics.clear()
            logger.info("All tool metrics reset")

# Global instance for use across the system
enhanced_tool_validator = EnhancedToolValidator()

def robust_tool_wrapper(
    expected_fields: Optional[List[str]] = None,
    pydantic_schema: Optional[type] = None,
    fallback_extractors: Optional[List[Callable]] = None,
    enable_caching: bool = True,
    max_retries: int = 2
):
    """
    Decorator for creating robust tools with hybrid validation.
    
    Usage:
        @robust_tool_wrapper(expected_fields=["section_titles"], enable_caching=True)
        @tool
        def my_tool(**kwargs):
            # Tool implementation
            pass
    """
    def decorator(func):
        # Handle both regular functions and already-decorated tools
        if hasattr(func, 'name'):
            tool_name = func.name  # For StructuredTool objects
        elif hasattr(func, '__name__'):
            tool_name = func.__name__  # For regular functions
        else:
            tool_name = str(func)  # Fallback
        
        # Create the validated wrapper
        validated_wrapper = enhanced_tool_validator.create_validated_tool(
            tool_function=func,
            tool_name=tool_name,
            expected_schema=pydantic_schema,
            required_fields=expected_fields,
            fallback_extractors=fallback_extractors,
            enable_caching=enable_caching,
            max_retries=max_retries
        )
        
        # If the original function was a LangChain tool, preserve its tool attributes
        if hasattr(func, 'name') and hasattr(func, 'description') and hasattr(func, 'args_schema'):
            # Copy tool attributes to the wrapper
            validated_wrapper.name = func.name
            validated_wrapper.description = func.description
            validated_wrapper.args_schema = func.args_schema
            
            # Copy any other tool-specific attributes
            for attr in ['tool_call_id', 'return_direct', 'tags', 'metadata']:
                if hasattr(func, attr):
                    setattr(validated_wrapper, attr, getattr(func, attr))
        
        return validated_wrapper
    
    return decorator 