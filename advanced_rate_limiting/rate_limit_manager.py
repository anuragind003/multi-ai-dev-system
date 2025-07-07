#!/usr/bin/env python3
"""
Advanced Rate Limit Configuration and Management

This module provides sophisticated rate limiting with:
- Exponential backoff with jitter
- Auto-escalation based on error rates
- Intelligent batching strategies
- Real-time monitoring and statistics
"""

import os
import time
import json
import sqlite3
import threading
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum, auto
from collections import deque, defaultdict

logger = logging.getLogger(__name__)


class RateLimitMode(Enum):
    """Defines the operational modes for the rate limiter."""
    NORMAL = auto()
    REDUCED = auto()
    EMERGENCY = auto()
    ADAPTIVE = auto()
    HALT = auto()  # New mode to stop all calls


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting strategies."""
    
    # Basic rate limits
    calls_per_minute: int = 60
    calls_per_hour: int = 1000
    
    # Delay configuration
    base_delay: float = 1.0
    max_delay: float = 30.0
    backoff_multiplier: float = 2.0
    jitter_factor: float = 0.1
    
    # Error thresholds for auto-escalation
    error_threshold_15min: int = 5
    error_threshold_1hour: int = 20
    
    # Mode-specific settings
    mode_configs: Dict[RateLimitMode, Dict[str, Any]] = field(default_factory=lambda: {
        RateLimitMode.NORMAL: {
            "calls_per_minute": 60,
            "base_delay": 1.0,
            "max_delay": 30.0,
            "enable_batching": True
        },
        RateLimitMode.REDUCED: {
            "calls_per_minute": 30,
            "base_delay": 2.0,
            "max_delay": 60.0,
            "enable_batching": True
        },
        RateLimitMode.EMERGENCY: {
            "calls_per_minute": 10,
            "base_delay": 5.0,
            "max_delay": 120.0,
            "enable_batching": True
        },
        RateLimitMode.ADAPTIVE: {
            "calls_per_minute": 45,
            "base_delay": 1.5,
            "max_delay": 45.0,
            "enable_batching": True
        }
    })


class APICallTracker:
    """Tracks API calls and errors for rate limiting decisions."""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or "cache/api_tracker.db"
        self.lock = threading.Lock()
        self._init_db()
        
        # In-memory tracking for recent activity
        self.recent_calls = deque(maxlen=1000)
        self.recent_errors = deque(maxlen=500)
        
    def _init_db(self):
        """Initialize SQLite database for persistent tracking."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS api_calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    endpoint TEXT,
                    success BOOLEAN,
                    error_type TEXT,
                    response_time REAL,
                    tokens_used INTEGER
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON api_calls(timestamp)
            """)
    
    def record_call(self, endpoint: str, success: bool, error_type: str = None,
                   response_time: float = 0.0, tokens_used: int = 0):
        """Record an API call with details."""
        timestamp = time.time()
        
        with self.lock:
            # Add to in-memory tracking
            self.recent_calls.append({
                'timestamp': timestamp,
                'endpoint': endpoint,
                'success': success,
                'error_type': error_type,
                'response_time': response_time,
                'tokens_used': tokens_used
            })
            
            if not success:
                self.recent_errors.append({
                    'timestamp': timestamp,
                    'endpoint': endpoint,
                    'error_type': error_type
                })
            
            # Persist to database
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO api_calls 
                    (timestamp, endpoint, success, error_type, response_time, tokens_used)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (timestamp, endpoint, success, error_type, response_time, tokens_used))
    
    def get_recent_stats(self, minutes: int = 15) -> Dict[str, Any]:
        """Get statistics for recent time period."""
        cutoff = time.time() - (minutes * 60)
        
        with self.lock:
            recent_calls = [c for c in self.recent_calls if c['timestamp'] > cutoff]
            recent_errors = [e for e in self.recent_errors if e['timestamp'] > cutoff]
            
            total_calls = len(recent_calls)
            total_errors = len(recent_errors)
            error_rate = (total_errors / total_calls * 100) if total_calls > 0 else 0
            
            # Error breakdown by type
            error_types = defaultdict(int)
            for error in recent_errors:
                if error['error_type']:
                    error_types[error['error_type']] += 1
            
            # Average response time
            response_times = [c['response_time'] for c in recent_calls if c['response_time'] > 0]
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            
            return {
                'period_minutes': minutes,
                'total_calls': total_calls,
                'total_errors': total_errors,
                'error_rate': error_rate,
                'error_types': dict(error_types),
                'avg_response_time': avg_response_time,
                'calls_per_minute': total_calls / minutes if minutes > 0 else 0
            }
    
    def should_escalate_mode(self, config: RateLimitConfig) -> bool:
        """Determine if rate limiting mode should be escalated."""
        stats_15min = self.get_recent_stats(15)
        stats_1hour = self.get_recent_stats(60)
        
        # Check 15-minute error threshold
        if stats_15min['total_errors'] >= config.error_threshold_15min:
            logger.warning(f"15-minute error threshold exceeded: {stats_15min['total_errors']}")
            return True
        
        # Check 1-hour error threshold
        if stats_1hour['total_errors'] >= config.error_threshold_1hour:
            logger.warning(f"1-hour error threshold exceeded: {stats_1hour['total_errors']}")
            return True
        
        # Check error rate
        if stats_15min['error_rate'] > 20:  # More than 20% error rate
            logger.warning(f"High error rate detected: {stats_15min['error_rate']:.1f}%")
            return True
        
        return False


class RateLimitManager:
    """Advanced rate limiting with adaptive strategies."""
    
    def __init__(self, config: RateLimitConfig = None):
        self.config = config or RateLimitConfig()
        self.tracker = APICallTracker()
        self.current_mode = RateLimitMode.NORMAL
        self.lock = threading.Lock()
        
        # Call timing tracking
        self.call_times = deque(maxlen=1000)
        self.last_call_time = 0
        
        # Mode change tracking
        self.mode_changed_at = time.time()
        self.mode_change_cooldown = 300  # 5 minutes
        
    def _calculate_delay(self, attempt: int = 0) -> float:
        """Calculate delay with exponential backoff and jitter."""
        mode_config = self.config.mode_configs[self.current_mode]
        base_delay = mode_config["base_delay"]
        max_delay = mode_config["max_delay"]
        
        # Exponential backoff
        delay = base_delay * (self.config.backoff_multiplier ** attempt)
        delay = min(delay, max_delay)
        
        # Add jitter to prevent thundering herd
        jitter = delay * self.config.jitter_factor * (0.5 - time.time() % 1)
        delay += jitter
        
        return max(delay, 0.1)  # Minimum 100ms delay
    
    def _check_rate_limit(self) -> float:
        """Check if we're hitting rate limits and return required delay."""
        now = time.time()
        mode_config = self.config.mode_configs[self.current_mode]
        calls_per_minute = mode_config["calls_per_minute"]
        
        with self.lock:
            # Remove old call times (older than 1 minute)
            minute_ago = now - 60
            while self.call_times and self.call_times[0] < minute_ago:
                self.call_times.popleft()
            
            # Check if we're at the limit
            if len(self.call_times) >= calls_per_minute:
                # Calculate delay until oldest call expires
                oldest_call = self.call_times[0]
                delay_needed = 60 - (now - oldest_call)
                return max(delay_needed, 0)
            
            return 0
    
    def _auto_escalate_mode(self):
        """Automatically escalate rate limiting mode based on errors."""
        # Don't change modes too frequently
        if time.time() - self.mode_changed_at < self.mode_change_cooldown:
            return
        
        if not self.tracker.should_escalate_mode(self.config):
            return
        
        # Escalate mode
        if self.current_mode == RateLimitMode.NORMAL:
            self.set_mode(RateLimitMode.REDUCED)
            logger.warning("Auto-escalated to REDUCED mode due to errors")
        elif self.current_mode == RateLimitMode.REDUCED:
            self.set_mode(RateLimitMode.EMERGENCY)
            logger.error("Auto-escalated to EMERGENCY mode due to errors")
        elif self.current_mode == RateLimitMode.ADAPTIVE:
            self.set_mode(RateLimitMode.EMERGENCY)
            logger.error("Auto-escalated from ADAPTIVE to EMERGENCY mode")
    
    def set_mode(self, mode: RateLimitMode):
        """Set the rate limiting mode."""
        if mode in RateLimitMode:
            if self.current_mode != mode:
                self.current_mode = mode
                logger.warning(f"Rate limiting mode changed to {mode.name}")
        else:
            logger.error(f"Invalid rate limiting mode: {mode}")
    
    def wait_if_needed(self, attempt: int = 0) -> float:
        """Wait if needed to respect rate limits. Returns actual delay."""
        # Check for auto-escalation
        self._auto_escalate_mode()
        
        # Check if the system is in HALT mode
        if self.current_mode == RateLimitMode.HALT:
            logger.error("System is in HALT mode due to persistent unrecoverable errors. No new calls will be made.")
            raise SystemExit("Rate limit quota likely exhausted. System halted.")
        
        # Calculate delays
        backoff_delay = self._calculate_delay(attempt)
        rate_limit_delay = self._check_rate_limit()
        
        # Use the maximum required delay
        total_delay = max(backoff_delay, rate_limit_delay)
        
        if total_delay > 0:
            logger.debug(f"Rate limiting delay: {total_delay:.2f}s (mode: {self.current_mode.value})")
            time.sleep(total_delay)
        
        # Record this call time
        now = time.time()
        with self.lock:
            self.call_times.append(now)
            self.last_call_time = now
        
        return total_delay
    
    def record_success(self, endpoint: str, response_time: float = 0, tokens_used: int = 0):
        """Record a successful API call."""
        self.tracker.record_call(endpoint, True, None, response_time, tokens_used)
    
    def record_error(self, endpoint: str, error_type: str, response_time: float = 0):
        """Record a failed API call."""
        self.tracker.record_call(endpoint, False, error_type, response_time)
        
        # Immediate escalation for certain error types
        if error_type in ['rate_limit', '429', 'quota_exceeded']:
            if self.current_mode == RateLimitMode.NORMAL:
                self.set_mode(RateLimitMode.REDUCED)
            elif self.current_mode == RateLimitMode.REDUCED:
                self.set_mode(RateLimitMode.EMERGENCY)
    
    def get_current_stats(self) -> Dict[str, Any]:
        """Get current rate limiting statistics."""
        stats_15min = self.tracker.get_recent_stats(15)
        stats_1hour = self.tracker.get_recent_stats(60)
        
        return {
            'current_mode': self.current_mode.value,
            'mode_duration_minutes': (time.time() - self.mode_changed_at) / 60,
            'recent_calls_15min': stats_15min['total_calls'],
            'recent_errors_15min': stats_15min['total_errors'],
            'error_rate_15min': stats_15min['error_rate'],
            'total_calls_1hour': stats_1hour['total_calls'],
            'total_errors_1hour': stats_1hour['total_errors'],
            'error_rate_1hour': stats_1hour['error_rate'],
            'current_calls_per_minute': len([t for t in self.call_times if time.time() - t < 60]),
            'last_call_seconds_ago': time.time() - self.last_call_time if self.last_call_time > 0 else None
        }


class CallBatcher:
    """Intelligent API call batching for efficiency."""
    
    def __init__(self, batch_size: int = 5, max_wait_time: float = 2.0):
        self.batch_size = batch_size
        self.max_wait_time = max_wait_time
        self.pending_calls = []
        self.lock = threading.Lock()
        self.batch_results = {}
        
    def add_call(self, call_id: str, call_func, *args, **kwargs):
        """Add a call to the batch queue."""
        with self.lock:
            self.pending_calls.append({
                'id': call_id,
                'func': call_func,
                'args': args,
                'kwargs': kwargs,
                'timestamp': time.time()
            })
            
            # Process batch if we hit the size limit or max wait time
            if (len(self.pending_calls) >= self.batch_size or 
                (self.pending_calls and 
                 time.time() - self.pending_calls[0]['timestamp'] > self.max_wait_time)):
                self._process_batch()
    
    def _process_batch(self):
        """Process the current batch of calls."""
        if not self.pending_calls:
            return
        
        batch = self.pending_calls.copy()
        self.pending_calls.clear()
        
        logger.debug(f"Processing batch of {len(batch)} calls")
        
        # Execute calls in batch
        for call in batch:
            try:
                result = call['func'](*call['args'], **call['kwargs'])
                self.batch_results[call['id']] = {'success': True, 'result': result}
            except Exception as e:
                self.batch_results[call['id']] = {'success': False, 'error': str(e)}
    
    def get_result(self, call_id: str, timeout: float = 10.0) -> Any:
        """Get the result of a batched call."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if call_id in self.batch_results:
                result = self.batch_results.pop(call_id)
                if result['success']:
                    return result['result']
                else:
                    raise Exception(f"Batched call failed: {result['error']}")
            
            time.sleep(0.1)
        
        raise TimeoutError(f"Batched call {call_id} timed out")


# Global instances
rate_limit_manager = RateLimitManager()
call_batcher = CallBatcher()
api_tracker = APICallTracker()
