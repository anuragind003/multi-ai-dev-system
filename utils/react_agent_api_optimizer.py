"""
React Agent API Token Optimizer

This module provides specialized API token optimization for React agents,
integrating with the advanced rate limiting system and hybrid validation.

Key Features:
- Intelligent request batching for tool calls
- Smart caching with context awareness
- API token usage tracking and optimization
- Integration with advanced rate limiting
- React agent specific optimizations
"""

import logging
import time
import hashlib
from typing import Dict, Any, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta

# Import advanced rate limiting components
try:
    from advanced_rate_limiting.config import get_advanced_rate_limiter, make_optimized_llm_call
    ADVANCED_RATE_LIMITING_AVAILABLE = True
except ImportError:
    ADVANCED_RATE_LIMITING_AVAILABLE = False
    logging.warning("Advanced rate limiting not available - using basic optimization")

logger = logging.getLogger(__name__)

@dataclass
class APITokenMetrics:
    """Track API token usage and optimization metrics."""
    total_requests: int = 0
    cached_requests: int = 0
    batched_requests: int = 0
    tokens_used: int = 0
    tokens_saved: int = 0
    avg_response_time: float = 0.0
    rate_limit_hits: int = 0
    optimization_score: float = 0.0
    
    def update_request(self, tokens_used: int, cached: bool = False, batched: bool = False, 
                      response_time: float = 0.0, rate_limited: bool = False):
        """Update metrics for a request."""
        self.total_requests += 1
        
        if cached:
            self.cached_requests += 1
            self.tokens_saved += tokens_used  # Tokens we didn't use
        else:
            self.tokens_used += tokens_used
        
        if batched:
            self.batched_requests += 1
        
        if rate_limited:
            self.rate_limit_hits += 1
        
        # Update average response time
        if response_time > 0:
            total_time = self.avg_response_time * (self.total_requests - 1) + response_time
            self.avg_response_time = total_time / self.total_requests
        
        # Calculate optimization score
        self._calculate_optimization_score()
    
    def _calculate_optimization_score(self):
        """Calculate optimization effectiveness score (0-100)."""
        if self.total_requests == 0:
            self.optimization_score = 0.0
            return
        
        cache_rate = self.cached_requests / self.total_requests
        batch_rate = self.batched_requests / self.total_requests
        rate_limit_penalty = min(self.rate_limit_hits / max(self.total_requests, 1), 0.3)
        
        # Score based on cache hits, batching, and rate limit avoidance
        self.optimization_score = max(0, min(100, 
            (cache_rate * 40) + (batch_rate * 30) + ((1 - rate_limit_penalty) * 30)
        ))
    
    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary."""
        total_tokens = self.tokens_used + self.tokens_saved
        efficiency = (self.tokens_saved / total_tokens * 100) if total_tokens > 0 else 0
        
        return {
            "total_requests": self.total_requests,
            "cache_hit_rate": f"{(self.cached_requests / max(self.total_requests, 1)) * 100:.1f}%",
            "batch_rate": f"{(self.batched_requests / max(self.total_requests, 1)) * 100:.1f}%",
            "tokens_used": self.tokens_used,
            "tokens_saved": self.tokens_saved,
            "efficiency": f"{efficiency:.1f}%",
            "avg_response_time": f"{self.avg_response_time:.2f}s",
            "rate_limit_hits": self.rate_limit_hits,
            "optimization_score": f"{self.optimization_score:.1f}/100"
        }

class ReactAgentAPIOptimizer:
    """
    Specialized API optimizer for React agents with intelligent batching and caching.
    
    Features:
    - Smart request batching based on tool call patterns
    - Context-aware caching with expiration
    - Integration with advanced rate limiting
    - React agent specific optimizations
    """
    
    def __init__(self, agent_name: str = "default", enable_batching: bool = True, 
                 enable_caching: bool = True, cache_ttl_minutes: int = 60, 
                 cache_ttl_hours: Optional[int] = None):
        self.agent_name = agent_name
        self.enable_batching = enable_batching
        self.enable_caching = enable_caching
        
        # Handle both cache_ttl_minutes and cache_ttl_hours parameters
        if cache_ttl_hours is not None:
            self.cache_ttl = timedelta(hours=cache_ttl_hours)
        else:
            self.cache_ttl = timedelta(minutes=cache_ttl_minutes)
        
        # Metrics tracking
        self.metrics = APITokenMetrics()
        
        # Caching system
        self.cache: Dict[str, Tuple[Any, datetime]] = {}
        self.cache_access_log: Dict[str, int] = {}
        
        # Batching system
        self.batch_queue: List[Dict[str, Any]] = []
        self.batch_timeout = 2.0  # seconds
        self.last_batch_time = time.time()
        
        # Rate limiting integration
        self.rate_limiter = None
        if ADVANCED_RATE_LIMITING_AVAILABLE:
            try:
                self.rate_limiter = get_advanced_rate_limiter()
                logger.info(f"Advanced rate limiting enabled for {agent_name}")
            except Exception as e:
                logger.warning(f"Could not initialize advanced rate limiter: {e}")
    
    def optimize_llm_call(self, llm_instance, prompt: str, context: str = "", 
                         cache_key_suffix: str = "", **kwargs) -> Any:
        """
        Optimize an LLM call with caching, batching, and rate limiting.
        
        Args:
            llm_instance: The LLM instance to call
            prompt: The prompt text
            context: Context for caching and optimization
            cache_key_suffix: Additional suffix for cache key
            **kwargs: Additional arguments for the LLM call
            
        Returns:
            LLM response with optimization metadata
        """
        start_time = time.time()
        
        # Generate cache key
        cache_key = self._generate_cache_key(prompt, context, cache_key_suffix)
        
        # Check cache first
        if self.enable_caching:
            cached_result = self._get_cached_result(cache_key)
            if cached_result is not None:
                response_time = time.time() - start_time
                self.metrics.update_request(
                    tokens_used=100,  # Estimated tokens we saved
                    cached=True,
                    response_time=response_time
                )
                logger.debug(f"Cache hit for {self.agent_name}: {cache_key[:16]}...")
                return cached_result
        
        # Try advanced rate limiting first
        if self.rate_limiter and ADVANCED_RATE_LIMITING_AVAILABLE:
            try:
                result = make_optimized_llm_call(
                    func=llm_instance.invoke,
                    func_name=f"{self.agent_name}_llm_call",
                    args=(prompt,),
                    kwargs=kwargs,
                    context=context
                )
                
                response_time = time.time() - start_time
                self.metrics.update_request(
                    tokens_used=self._estimate_tokens(prompt, str(result)),
                    response_time=response_time
                )
                
                # Cache the result
                if self.enable_caching:
                    self._cache_result(cache_key, result)
                
                return result
                
            except Exception as e:
                logger.warning(f"Advanced rate limiting failed, falling back: {e}")
        
        # Fallback to basic optimization
        return self._basic_optimized_call(llm_instance, prompt, cache_key, start_time, **kwargs)
    
    def optimize_tool_batch(self, tool_calls: List[Dict[str, Any]]) -> List[Any]:
        """
        Optimize a batch of tool calls with intelligent grouping.
        
        Args:
            tool_calls: List of tool call dictionaries with 'tool', 'input', etc.
            
        Returns:
            List of tool call results
        """
        if not self.enable_batching or len(tool_calls) <= 1:
            return [self._execute_single_tool_call(call) for call in tool_calls]
        
        # Group similar tool calls for batching
        batched_groups = self._group_tool_calls_for_batching(tool_calls)
        
        results = []
        for group in batched_groups:
            if len(group) > 1:
                # Execute as batch
                batch_results = self._execute_tool_batch(group)
                results.extend(batch_results)
                
                self.metrics.update_request(
                    tokens_used=len(group) * 50,  # Estimate
                    batched=True
                )
            else:
                # Execute individually
                result = self._execute_single_tool_call(group[0])
                results.append(result)
        
        return results
    
    def _generate_cache_key(self, prompt: str, context: str, suffix: str) -> str:
        """Generate a cache key for the request."""
        # Use hash of prompt + context for cache key
        content = f"{prompt[:500]}{context}{suffix}"  # Limit prompt length for key
        return hashlib.md5(content.encode()).hexdigest()
    
    def _get_cached_result(self, cache_key: str) -> Optional[Any]:
        """Get cached result if available and not expired."""
        if cache_key not in self.cache:
            return None
        
        result, timestamp = self.cache[cache_key]
        
        # Check expiration
        if datetime.now() - timestamp > self.cache_ttl:
            del self.cache[cache_key]
            if cache_key in self.cache_access_log:
                del self.cache_access_log[cache_key]
            return None
        
        # Update access log
        self.cache_access_log[cache_key] = self.cache_access_log.get(cache_key, 0) + 1
        
        return result
    
    def _cache_result(self, cache_key: str, result: Any) -> None:
        """Cache a result with timestamp."""
        self.cache[cache_key] = (result, datetime.now())
        self.cache_access_log[cache_key] = 1
        
        # Clean up old cache entries if needed
        if len(self.cache) > 100:  # Max cache size
            self._cleanup_cache()
    
    def _cleanup_cache(self) -> None:
        """Clean up old or least-used cache entries."""
        # Remove expired entries first
        now = datetime.now()
        expired_keys = [
            key for key, (_, timestamp) in self.cache.items()
            if now - timestamp > self.cache_ttl
        ]
        
        for key in expired_keys:
            del self.cache[key]
            if key in self.cache_access_log:
                del self.cache_access_log[key]
        
        # If still too many, remove least accessed
        if len(self.cache) > 80:
            # Sort by access count and remove least used
            sorted_by_access = sorted(
                self.cache_access_log.items(),
                key=lambda x: x[1]
            )
            
            for key, _ in sorted_by_access[:20]:  # Remove 20 least used
                if key in self.cache:
                    del self.cache[key]
                del self.cache_access_log[key]
    
    def _basic_optimized_call(self, llm_instance, prompt: str, cache_key: str, 
                            start_time: float, **kwargs) -> Any:
        """Basic optimization without advanced rate limiting."""
        try:
            # Simple rate limiting delay
            time.sleep(0.5)  # Basic delay
            
            result = llm_instance.invoke(prompt, **kwargs)
            
            response_time = time.time() - start_time
            self.metrics.update_request(
                tokens_used=self._estimate_tokens(prompt, str(result)),
                response_time=response_time
            )
            
            # Cache the result
            if self.enable_caching:
                self._cache_result(cache_key, result)
            
            return result
            
        except Exception as e:
            response_time = time.time() - start_time
            self.metrics.update_request(
                tokens_used=0,
                response_time=response_time,
                rate_limited="rate" in str(e).lower()
            )
            raise
    
    def _estimate_tokens(self, prompt: str, response: str) -> int:
        """Estimate token usage for a request."""
        # Simple estimation: ~4 characters per token
        return (len(prompt) + len(response)) // 4
    
    def _group_tool_calls_for_batching(self, tool_calls: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Group tool calls that can be batched together."""
        groups = []
        current_group = []
        
        # Simple grouping by tool type
        for call in tool_calls:
            tool_name = call.get('tool', '')
            
            # Check if this call can be batched with current group
            if (current_group and 
                current_group[0].get('tool') == tool_name and
                len(current_group) < 5):  # Max batch size
                current_group.append(call)
            else:
                if current_group:
                    groups.append(current_group)
                current_group = [call]
        
        if current_group:
            groups.append(current_group)
        
        return groups
    
    def _execute_tool_batch(self, tool_calls: List[Dict[str, Any]]) -> List[Any]:
        """Execute a batch of similar tool calls efficiently."""
        # This would need to be implemented based on specific tool capabilities
        # For now, execute individually but with reduced delays
        results = []
        for call in tool_calls:
            result = self._execute_single_tool_call(call)
            results.append(result)
            time.sleep(0.1)  # Reduced delay for batched calls
        
        return results
    
    def _execute_single_tool_call(self, tool_call: Dict[str, Any]) -> Any:
        """Execute a single tool call."""
        # This would integrate with the actual tool execution system
        # Placeholder implementation
        tool_name = tool_call.get('tool', '')
        tool_input = tool_call.get('input', {})
        
        logger.debug(f"Executing tool call: {tool_name}")
        
        # Simulate tool execution
        time.sleep(0.2)
        return {"tool": tool_name, "result": "executed", "input": tool_input}
    
    def get_optimization_report(self) -> Dict[str, Any]:
        """Get comprehensive optimization report."""
        return {
            "agent_name": self.agent_name,
            "optimization_enabled": {
                "caching": self.enable_caching,
                "batching": self.enable_batching,
                "advanced_rate_limiting": ADVANCED_RATE_LIMITING_AVAILABLE and self.rate_limiter is not None
            },
            "metrics": self.metrics.get_summary(),
            "cache_status": {
                "entries": len(self.cache),
                "max_size": 100,
                "cleanup_frequency": "auto"
            },
            "recommendations": self._generate_optimization_recommendations()
        }
    
    def _generate_optimization_recommendations(self) -> List[str]:
        """Generate optimization recommendations based on metrics."""
        recommendations = []
        
        if self.metrics.total_requests == 0:
            return ["No requests recorded yet"]
        
        cache_rate = self.metrics.cached_requests / self.metrics.total_requests
        if cache_rate < 0.2:
            recommendations.append("Consider increasing cache TTL or improving cache key generation")
        
        if self.metrics.rate_limit_hits > self.metrics.total_requests * 0.1:
            recommendations.append("High rate limit hits - consider enabling advanced rate limiting")
        
        if self.metrics.optimization_score < 50:
            recommendations.append("Overall optimization score is low - review caching and batching settings")
        
        if not ADVANCED_RATE_LIMITING_AVAILABLE:
            recommendations.append("Install advanced rate limiting for better optimization")
        
        return recommendations or ["Optimization performance looks good"]
    
    def clear_cache(self) -> None:
        """Clear the optimization cache."""
        self.cache.clear()
        self.cache_access_log.clear()
        logger.info(f"Cache cleared for {self.agent_name}")
    
    def reset_metrics(self) -> None:
        """Reset optimization metrics."""
        self.metrics = APITokenMetrics()
        logger.info(f"Metrics reset for {self.agent_name}")

# Global optimizers for React agents
_react_optimizers: Dict[str, ReactAgentAPIOptimizer] = {}

def get_react_agent_optimizer(agent_name: str, **kwargs) -> ReactAgentAPIOptimizer:
    """Get or create an API optimizer for a React agent."""
    if agent_name not in _react_optimizers:
        _react_optimizers[agent_name] = ReactAgentAPIOptimizer(agent_name, **kwargs)
    
    return _react_optimizers[agent_name]

def get_all_optimizer_reports() -> Dict[str, Dict[str, Any]]:
    """Get optimization reports for all React agents."""
    return {
        name: optimizer.get_optimization_report()
        for name, optimizer in _react_optimizers.items()
    }

def clear_all_caches() -> None:
    """Clear all React agent optimizer caches."""
    for optimizer in _react_optimizers.values():
        optimizer.clear_cache()
    logger.info("All React agent optimizer caches cleared")

def reset_all_metrics() -> None:
    """Reset all React agent optimizer metrics."""
    for optimizer in _react_optimizers.values():
        optimizer.reset_metrics()
    logger.info("All React agent optimizer metrics reset") 