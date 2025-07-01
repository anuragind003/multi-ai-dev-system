#!/usr/bin/env python3
"""
Advanced Rate Limiting Configuration

Central configuration for all advanced rate limiting features.
This module ties together all the advanced components and provides
a unified interface for the multi-AI development system.
"""

import os
import time
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path

from .rate_limit_manager import RateLimitManager, CallBatcher, RateLimitConfig, RateLimitMode
from .api_tracker import APITracker
from .optimization_strategies import OptimizationStrategies

logger = logging.getLogger(__name__)


@dataclass
class AdvancedRateLimitConfig:
    """Configuration for advanced rate limiting system."""
    
    # Enable/disable features
    enable_advanced_rate_limiting: bool = True
    enable_intelligent_caching: bool = True
    enable_request_deduplication: bool = True
    enable_smart_retries: bool = True
    enable_auto_escalation: bool = True
    
    # Performance settings
    cache_size_mb: int = 100
    max_cache_entries: int = 1000
    dedup_window_seconds: float = 1.0
    
    # Monitoring settings
    stats_retention_hours: int = 24
    cleanup_interval_hours: int = 6
    
    # Emergency thresholds
    emergency_error_rate_threshold: float = 30.0
    emergency_error_count_threshold: int = 10
    reduced_error_rate_threshold: float = 15.0
    reduced_error_count_threshold: int = 5
    
    @classmethod
    def from_environment(cls) -> 'AdvancedRateLimitConfig':
        """Create configuration from environment variables."""
        return cls(
            enable_advanced_rate_limiting=os.getenv("MAISD_ENABLE_ADVANCED_RATE_LIMITING", "true").lower() == "true",
            enable_intelligent_caching=os.getenv("MAISD_ENABLE_INTELLIGENT_CACHING", "true").lower() == "true",
            enable_request_deduplication=os.getenv("MAISD_ENABLE_REQUEST_DEDUPLICATION", "true").lower() == "true",
            enable_smart_retries=os.getenv("MAISD_ENABLE_SMART_RETRIES", "true").lower() == "true",
            enable_auto_escalation=os.getenv("MAISD_ENABLE_AUTO_ESCALATION", "true").lower() == "true",
            
            cache_size_mb=int(os.getenv("MAISD_CACHE_SIZE_MB", "100")),
            max_cache_entries=int(os.getenv("MAISD_MAX_CACHE_ENTRIES", "1000")),
            dedup_window_seconds=float(os.getenv("MAISD_DEDUP_WINDOW_SECONDS", "1.0")),
            
            stats_retention_hours=int(os.getenv("MAISD_STATS_RETENTION_HOURS", "24")),
            cleanup_interval_hours=int(os.getenv("MAISD_CLEANUP_INTERVAL_HOURS", "6")),
            
            emergency_error_rate_threshold=float(os.getenv("MAISD_EMERGENCY_ERROR_RATE_THRESHOLD", "30.0")),
            emergency_error_count_threshold=int(os.getenv("MAISD_EMERGENCY_ERROR_COUNT_THRESHOLD", "10")),
            reduced_error_rate_threshold=float(os.getenv("MAISD_REDUCED_ERROR_RATE_THRESHOLD", "15.0")),
            reduced_error_count_threshold=int(os.getenv("MAISD_REDUCED_ERROR_COUNT_THRESHOLD", "5"))
        )


class AdvancedRateLimitSystem:
    """Main system that coordinates all advanced rate limiting components."""
    
    def __init__(self, config: AdvancedRateLimitConfig = None):
        self.config = config or AdvancedRateLimitConfig.from_environment()
        
        # Initialize components based on configuration
        self.rate_limiter = None
        self.api_tracker = None
        self.optimizer = None
        self.call_batcher = None
        
        if self.config.enable_advanced_rate_limiting:
            self._initialize_components()
    
    def _initialize_components(self):
        """Initialize all advanced rate limiting components."""
        try:
            # Initialize rate limiting configuration
            rate_config = RateLimitConfig()
            
            # Initialize core components
            self.rate_limiter = RateLimitManager(rate_config)
            self.api_tracker = APITracker()
            self.call_batcher = CallBatcher()
            
            # Initialize optimization strategies
            if (self.config.enable_intelligent_caching or 
                self.config.enable_request_deduplication or 
                self.config.enable_smart_retries):
                
                self.optimizer = OptimizationStrategies(
                    cache_size_mb=self.config.cache_size_mb,
                    cache_entries=self.config.max_cache_entries
                )
            
            logger.info("Advanced rate limiting system initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize advanced rate limiting: {e}")
            self.config.enable_advanced_rate_limiting = False
    
    def is_enabled(self) -> bool:
        """Check if advanced rate limiting is enabled and working."""
        return (self.config.enable_advanced_rate_limiting and 
                self.rate_limiter is not None)
    
    def make_rate_limited_call(self, func, func_name: str, args: tuple = (), 
                              kwargs: dict = None, context: str = "",
                              attempt: int = 0) -> Any:
        """Make a rate-limited API call with all optimizations."""
        kwargs = kwargs or {}
        
        if not self.is_enabled():
            # Fallback to simple rate limiting
            return self._simple_rate_limited_call(func, args, kwargs)
        
        try:
            # Apply rate limiting
            delay = self.rate_limiter.wait_if_needed(attempt)
            
            # Use optimizer if available
            if self.optimizer:
                result = self.optimizer.optimized_call(
                    func, func_name, args, kwargs, context,
                    cache_enabled=self.config.enable_intelligent_caching,
                    dedup_enabled=self.config.enable_request_deduplication,
                    retry_enabled=self.config.enable_smart_retries
                )
            else:
                result = func(*args, **kwargs)
            
            # Record successful call
            self.rate_limiter.record_success(func_name, 0, 0)  # TODO: Add response time and tokens
            
            return result
            
        except Exception as e:
            # Record error
            error_type = type(e).__name__
            self.rate_limiter.record_error(func_name, error_type)
            
            # Check for auto-escalation
            if self.config.enable_auto_escalation:
                self._check_auto_escalation()
            
            raise e
    
    def _simple_rate_limited_call(self, func, args: tuple, kwargs: dict) -> Any:
        """Simple fallback rate limiting."""
        # Basic delay based on environment variable
        delay = float(os.getenv("RATE_LIMIT_DELAY", "1.0"))
        time.sleep(delay)
        return func(*args, **kwargs)
    
    def _check_auto_escalation(self):
        """Check if mode should be auto-escalated based on recent errors."""
        if not self.api_tracker:
            return
        
        # Check for emergency mode trigger
        if self.api_tracker.should_trigger_emergency_mode():
            self.rate_limiter.set_mode(RateLimitMode.EMERGENCY)
            logger.warning("Auto-escalated to EMERGENCY mode")
            return
        
        # Check for reduced mode trigger
        if self.api_tracker.should_trigger_reduced_mode():
            current_mode = self.rate_limiter.current_mode
            if current_mode == RateLimitMode.NORMAL:
                self.rate_limiter.set_mode(RateLimitMode.REDUCED)
                logger.warning("Auto-escalated to REDUCED mode")
    
    def set_mode(self, mode: str):
        """Set rate limiting mode manually."""
        if not self.is_enabled():
            logger.warning("Advanced rate limiting not enabled, cannot set mode")
            return
        
        mode_map = {
            'normal': RateLimitMode.NORMAL,
            'reduced': RateLimitMode.REDUCED,
            'emergency': RateLimitMode.EMERGENCY,
            'adaptive': RateLimitMode.ADAPTIVE
        }
        
        if mode.lower() in mode_map:
            self.rate_limiter.set_mode(mode_map[mode.lower()])
            logger.info(f"Manually set rate limiting mode to: {mode.upper()}")
        else:
            logger.error(f"Unknown rate limiting mode: {mode}")
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics from all components."""
        if not self.is_enabled():
            return {
                'enabled': False,
                'reason': 'Advanced rate limiting not available'
            }
        
        stats = {
            'enabled': True,
            'config': {
                'cache_enabled': self.config.enable_intelligent_caching,
                'dedup_enabled': self.config.enable_request_deduplication,
                'retry_enabled': self.config.enable_smart_retries,
                'auto_escalation_enabled': self.config.enable_auto_escalation
            }
        }
        
        # Rate limiter stats
        if self.rate_limiter:
            stats['rate_limiting'] = self.rate_limiter.get_current_stats()
        
        # API tracker stats
        if self.api_tracker:
            stats['api_tracking'] = {
                'stats_15min': self.api_tracker.get_stats_for_period(15),
                'stats_1hour': self.api_tracker.get_stats_for_period(60)
            }
        
        # Optimization stats
        if self.optimizer:
            stats['optimization'] = self.optimizer.get_comprehensive_stats()
        
        return stats
    
    def invalidate_cache(self, context: str = None):
        """Invalidate cache entries."""
        if self.optimizer and context:
            self.optimizer.invalidate_cache_by_context(context)
        elif self.optimizer:
            self.optimizer.clear_all_caches()
    
    def cleanup(self):
        """Cleanup old data and perform maintenance."""
        if self.api_tracker:
            self.api_tracker.cleanup_old_records(days_to_keep=7)
        
        logger.info("Advanced rate limiting cleanup completed")
    
    def export_analytics(self) -> Dict[str, Any]:
        """Export detailed analytics for analysis."""
        if not self.is_enabled():
            return {'enabled': False}
        
        analytics = {
            'timestamp': time.time(),
            'enabled': True,
            'comprehensive_stats': self.get_comprehensive_stats()
        }
        
        # Add detailed API tracking if available
        if self.api_tracker:
            analytics['detailed_tracking'] = self.api_tracker.export_stats_to_json(hours=24)
        
        return analytics


# Global instance
advanced_rate_limit_system = AdvancedRateLimitSystem()


def get_advanced_rate_limiter():
    """Get the global advanced rate limiting system."""
    return advanced_rate_limit_system


def make_optimized_llm_call(func, func_name: str, args: tuple = (), 
                           kwargs: dict = None, context: str = "") -> Any:
    """Convenience function for making optimized LLM calls."""
    return advanced_rate_limit_system.make_rate_limited_call(
        func, func_name, args, kwargs, context
    )
