#!/usr/bin/env python3
"""
API Optimization Strategies

This module provides advanced strategies for optimizing API usage:
- Intelligent caching with context awareness
- Request deduplication and batching
- Predictive pre-loading
- Smart retry strategies
"""

import time
import hashlib
import pickle
import threading
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, OrderedDict
from functools import wraps

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Entry in the intelligent cache."""
    value: Any
    timestamp: float
    access_count: int = 0
    last_access: float = field(default_factory=time.time)
    context_tags: List[str] = field(default_factory=list)
    size_bytes: int = 0


class IntelligentCache:
    """Context-aware caching with smart eviction policies."""
    
    def __init__(self, max_size_mb: int = 100, max_entries: int = 1000):
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.max_entries = max_entries
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.lock = threading.RLock()
        
        # Context tracking
        self.context_usage = defaultdict(int)
        self.related_contexts = defaultdict(set)
        
        # Performance metrics
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        
    def _calculate_size(self, obj: Any) -> int:
        """Calculate approximate size of object in bytes."""
        try:
            return len(pickle.dumps(obj))
        except:
            # Fallback estimation
            if isinstance(obj, str):
                return len(obj.encode('utf-8'))
            elif isinstance(obj, (list, tuple)):
                return sum(self._calculate_size(item) for item in obj[:10])  # Sample first 10
            elif isinstance(obj, dict):
                sample_items = list(obj.items())[:10]
                return sum(self._calculate_size(k) + self._calculate_size(v) for k, v in sample_items)
            else:
                return 1024  # Default estimate
    
    def _generate_key(self, func_name: str, args: tuple, kwargs: dict, context: str = "") -> str:
        """Generate a unique cache key."""
        # Create a hashable representation
        key_data = {
            'func': func_name,
            'args': str(args),
            'kwargs': str(sorted(kwargs.items())),
            'context': context
        }
        
        key_string = str(key_data)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _should_evict(self) -> bool:
        """Determine if cache eviction is needed."""
        if len(self.cache) >= self.max_entries:
            return True
        
        total_size = sum(entry.size_bytes for entry in self.cache.values())
        return total_size >= self.max_size_bytes
    
    def _evict_entries(self):
        """Evict entries using intelligent strategy."""
        if not self.cache:
            return
        
        # Calculate eviction scores (lower = more likely to evict)
        eviction_candidates = []
        current_time = time.time()
        
        for key, entry in self.cache.items():
            # Factors for eviction score:
            # 1. Age (older = higher eviction probability)
            # 2. Access frequency (less accessed = higher eviction probability)
            # 3. Recency of access (less recent = higher eviction probability)
            # 4. Size (larger = slightly higher eviction probability)
            
            age_factor = current_time - entry.timestamp
            access_factor = 1.0 / (entry.access_count + 1)
            recency_factor = current_time - entry.last_access
            size_factor = entry.size_bytes / (1024 * 1024)  # Size in MB
            
            # Weighted score (lower = more likely to evict)
            score = (age_factor * 0.3 + 
                    access_factor * 100 * 0.4 + 
                    recency_factor * 0.2 + 
                    size_factor * 0.1)
            
            eviction_candidates.append((score, key))
        
        # Sort by score (highest score = least likely to evict)
        eviction_candidates.sort(reverse=True)
        
        # Evict bottom 25% or until we're under limits
        entries_to_evict = max(1, len(eviction_candidates) // 4)
        
        for _, key in eviction_candidates[-entries_to_evict:]:
            if key in self.cache:
                del self.cache[key]
                self.evictions += 1
                
                # Stop if we're back under limits
                if not self._should_evict():
                    break
    
    def get(self, func_name: str, args: tuple, kwargs: dict, context: str = "") -> Optional[Any]:
        """Get value from cache if available."""
        key = self._generate_key(func_name, args, kwargs, context)
        
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                entry.access_count += 1
                entry.last_access = time.time()
                
                # Move to end (most recently used)
                self.cache.move_to_end(key)
                
                # Update context tracking
                if context:
                    self.context_usage[context] += 1
                
                self.hits += 1
                logger.debug(f"Cache hit for {func_name} (context: {context})")
                return entry.value
            
            self.misses += 1
            return None
    
    def put(self, func_name: str, args: tuple, kwargs: dict, value: Any, context: str = "",
           context_tags: List[str] = None):
        """Store value in cache."""
        key = self._generate_key(func_name, args, kwargs, context)
        
        with self.lock:
            # Calculate size
            size_bytes = self._calculate_size(value)
            
            # Check if we need to evict
            if self._should_evict():
                self._evict_entries()
            
            # Create cache entry
            entry = CacheEntry(
                value=value,
                timestamp=time.time(),
                access_count=1,
                context_tags=context_tags or [],
                size_bytes=size_bytes
            )
            
            self.cache[key] = entry
            
            # Update context tracking
            if context:
                self.context_usage[context] += 1
                
                # Track related contexts
                for tag in (context_tags or []):
                    self.related_contexts[context].add(tag)
            
            logger.debug(f"Cached result for {func_name} (context: {context}, size: {size_bytes} bytes)")
    
    def invalidate_context(self, context: str):
        """Invalidate all cache entries for a specific context."""
        with self.lock:
            keys_to_remove = []
            
            for key, entry in self.cache.items():
                if context in entry.context_tags:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self.cache[key]
            
            logger.info(f"Invalidated {len(keys_to_remove)} cache entries for context: {context}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        with self.lock:
            total_requests = self.hits + self.misses
            hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
            
            total_size = sum(entry.size_bytes for entry in self.cache.values())
            
            return {
                'hit_rate': hit_rate,
                'total_entries': len(self.cache),
                'total_size_mb': total_size / (1024 * 1024),
                'hits': self.hits,
                'misses': self.misses,
                'evictions': self.evictions,
                'context_usage': dict(self.context_usage),
                'utilization': len(self.cache) / self.max_entries * 100
            }


class RequestDeduplicator:
    """Deduplicates identical requests within a time window."""
    
    def __init__(self, dedup_window: float = 1.0):
        self.dedup_window = dedup_window
        self.pending_requests: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()
    
    def _generate_request_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """Generate key for request deduplication."""
        request_data = {
            'func': func_name,
            'args': str(args),
            'kwargs': str(sorted(kwargs.items()))
        }
        return hashlib.md5(str(request_data).encode()).hexdigest()
    
    def deduplicate_request(self, func_name: str, args: tuple, kwargs: dict,
                          executor: Callable) -> Any:
        """Deduplicate request or execute if unique."""
        request_key = self._generate_request_key(func_name, args, kwargs)
        current_time = time.time()
        
        with self.lock:
            # Check if there's a pending request
            if request_key in self.pending_requests:
                pending = self.pending_requests[request_key]
                
                # If within deduplication window, wait for existing request
                if current_time - pending['start_time'] < self.dedup_window:
                    logger.debug(f"Deduplicating request for {func_name}")
                    
                    # Wait for the pending request to complete
                    while request_key in self.pending_requests:
                        if current_time - pending['start_time'] > self.dedup_window * 2:
                            # Timeout - remove and proceed
                            break
                        time.sleep(0.1)
                        current_time = time.time()
                    
                    # If result is available, return it
                    if 'result' in pending:
                        return pending['result']
            
            # Mark request as pending
            self.pending_requests[request_key] = {
                'start_time': current_time,
                'func_name': func_name
            }
        
        try:
            # Execute the request
            result = executor()
            
            with self.lock:
                if request_key in self.pending_requests:
                    self.pending_requests[request_key]['result'] = result
                    
                    # Keep result available for a short time for other requests
                    def cleanup():
                        time.sleep(self.dedup_window)
                        with self.lock:
                            if request_key in self.pending_requests:
                                del self.pending_requests[request_key]
                    
                    threading.Thread(target=cleanup, daemon=True).start()
            
            return result
            
        except Exception as e:
            # Remove pending request on error
            with self.lock:
                if request_key in self.pending_requests:
                    del self.pending_requests[request_key]
            raise e


class SmartRetryStrategy:
    """Intelligent retry strategy with adaptive backoff."""
    
    def __init__(self):
        self.retry_history = defaultdict(list)
        self.lock = threading.Lock()
    
    def should_retry(self, func_name: str, error: Exception, attempt: int) -> bool:
        """Determine if request should be retried."""
        error_type = type(error).__name__
        
        # Don't retry certain error types
        non_retryable_errors = {
            'ValueError', 'TypeError', 'KeyError', 'AttributeError',
            'SyntaxError', 'ImportError', 'ModuleNotFoundError'
        }
        
        if error_type in non_retryable_errors:
            return False
        
        # Limit retry attempts
        if attempt >= 3:
            return False
        
        # Check retry history for this function
        with self.lock:
            recent_failures = [
                t for t in self.retry_history[func_name]
                if time.time() - t < 300  # Last 5 minutes
            ]
            
            # If too many recent failures, be more conservative
            if len(recent_failures) > 5:
                return attempt < 2
        
        return True
    
    def calculate_backoff(self, func_name: str, attempt: int, error: Exception) -> float:
        """Calculate backoff time for retry."""
        base_delay = 1.0
        max_delay = 30.0
        
        # Different strategies based on error type
        error_type = type(error).__name__
        
        if 'rate' in str(error).lower() or '429' in str(error):
            # Rate limit errors - longer backoff
            base_delay = 5.0
            max_delay = 120.0
        elif 'timeout' in str(error).lower():
            # Timeout errors - moderate backoff
            base_delay = 2.0
            max_delay = 60.0
        
        # Exponential backoff with jitter
        delay = base_delay * (2 ** attempt)
        delay = min(delay, max_delay)
        
        # Add jitter (±20%)
        jitter = delay * 0.2 * (0.5 - time.time() % 1)
        delay += jitter
        
        return max(delay, 0.1)
    
    def record_failure(self, func_name: str):
        """Record a failure for retry strategy adjustment."""
        with self.lock:
            self.retry_history[func_name].append(time.time())
            
            # Keep only recent failures
            cutoff = time.time() - 3600  # Last hour
            self.retry_history[func_name] = [
                t for t in self.retry_history[func_name] if t > cutoff
            ]


class OptimizationStrategies:
    """Main class combining all optimization strategies."""
    
    def __init__(self, cache_size_mb: int = 100, cache_entries: int = 1000):
        self.cache = IntelligentCache(cache_size_mb, cache_entries)
        self.deduplicator = RequestDeduplicator()
        self.retry_strategy = SmartRetryStrategy()
        
        # Performance tracking
        self.optimization_stats = {
            'cache_saves': 0,
            'dedup_saves': 0,
            'successful_retries': 0,
            'failed_retries': 0
        }
    
    def optimized_call(self, func: Callable, func_name: str, args: tuple = (), 
                      kwargs: dict = None, context: str = "", 
                      context_tags: List[str] = None,
                      cache_enabled: bool = True,
                      dedup_enabled: bool = True,
                      retry_enabled: bool = True) -> Any:
        """Make an optimized API call with all strategies applied."""
        kwargs = kwargs or {}
        
        # 1. Try cache first
        if cache_enabled:
            cached_result = self.cache.get(func_name, args, kwargs, context)
            if cached_result is not None:
                self.optimization_stats['cache_saves'] += 1
                return cached_result
        
        # 2. Deduplicate request
        def execute_request():
            attempt = 0
            last_error = None
            
            while attempt < 3:  # Max 3 attempts
                try:
                    result = func(*args, **kwargs)
                    
                    # Cache successful result
                    if cache_enabled:
                        self.cache.put(func_name, args, kwargs, result, context, context_tags)
                    
                    if attempt > 0:
                        self.optimization_stats['successful_retries'] += 1
                    
                    return result
                    
                except Exception as e:
                    last_error = e
                    
                    if not retry_enabled or not self.retry_strategy.should_retry(func_name, e, attempt):
                        if attempt > 0:
                            self.optimization_stats['failed_retries'] += 1
                        self.retry_strategy.record_failure(func_name)
                        raise e
                    
                    # Calculate backoff and wait
                    backoff_time = self.retry_strategy.calculate_backoff(func_name, attempt, e)
                    logger.warning(f"Retrying {func_name} after {backoff_time:.2f}s (attempt {attempt + 1})")
                    time.sleep(backoff_time)
                    
                    attempt += 1
            
            # All retries failed
            self.retry_strategy.record_failure(func_name)
            self.optimization_stats['failed_retries'] += 1
            raise last_error
        
        if dedup_enabled:
            result = self.deduplicator.deduplicate_request(func_name, args, kwargs, execute_request)
            if result != execute_request():  # If deduplication occurred
                self.optimization_stats['dedup_saves'] += 1
            return result
        else:
            return execute_request()
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive optimization statistics."""
        cache_stats = self.cache.get_stats()
        
        return {
            'cache': cache_stats,
            'optimization': self.optimization_stats.copy(),
            'total_api_saves': (
                self.optimization_stats['cache_saves'] + 
                self.optimization_stats['dedup_saves']
            ),
            'retry_success_rate': (
                self.optimization_stats['successful_retries'] / 
                max(1, self.optimization_stats['successful_retries'] + self.optimization_stats['failed_retries'])
            ) * 100
        }
    
    def invalidate_cache_by_context(self, context: str):
        """Invalidate cache entries for a specific context."""
        self.cache.invalidate_context(context)
    
    def clear_all_caches(self):
        """Clear all caches and reset optimization data."""
        self.cache.cache.clear()
        self.deduplicator.pending_requests.clear()
        self.retry_strategy.retry_history.clear()
        
        # Reset stats
        for key in self.optimization_stats:
            self.optimization_stats[key] = 0


# Decorator for easy optimization
def optimize_api_call(func_name: str = None, context: str = "", 
                     context_tags: List[str] = None,
                     cache_enabled: bool = True,
                     dedup_enabled: bool = True,
                     retry_enabled: bool = True):
    """Decorator to automatically optimize API calls."""
    
    def decorator(func: Callable) -> Callable:
        actual_func_name = func_name or func.__name__
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get global optimization strategies instance
            # This should be initialized in your main config
            global optimization_strategies
            
            return optimization_strategies.optimized_call(
                func, actual_func_name, args, kwargs, context, context_tags,
                cache_enabled, dedup_enabled, retry_enabled
            )
        
        return wrapper
    return decorator


# Global instance (should be initialized in main config)
optimization_strategies = OptimizationStrategies()
