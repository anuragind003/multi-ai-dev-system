"""
Advanced Rate Limiting Module

This module provides sophisticated rate limiting, API optimization,
and error recovery strategies for the Multi-AI Development System.

Key Components:
- RateLimitManager: Adaptive rate limiting with exponential backoff
- CallBatcher: Intelligent API call batching
- APITracker: Real-time monitoring and statistics
- OptimizationStrategies: Advanced caching and call optimization
"""

from .rate_limit_manager import RateLimitManager, CallBatcher
from .api_tracker import APITracker
from .optimization_strategies import OptimizationStrategies
from .config import AdvancedRateLimitConfig, AdvancedRateLimitSystem, get_advanced_rate_limiter, make_optimized_llm_call

__all__ = [
    'RateLimitManager',
    'CallBatcher', 
    'APITracker',
    'OptimizationStrategies',
    'AdvancedRateLimitConfig',
    'AdvancedRateLimitSystem',
    'get_advanced_rate_limiter',
    'make_optimized_llm_call'
]

__version__ = "1.0.0"
