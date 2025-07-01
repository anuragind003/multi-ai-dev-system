#!/usr/bin/env python3
"""
API Tracker for Advanced Rate Limiting

This module provides real-time tracking and monitoring of API calls,
errors, and performance metrics for intelligent rate limiting decisions.
"""

import time
import sqlite3
import threading
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import deque, defaultdict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class APICallRecord:
    """Record of a single API call."""
    timestamp: float
    endpoint: str
    success: bool
    error_type: Optional[str] = None
    response_time: float = 0.0
    tokens_used: int = 0
    retry_count: int = 0


class APITracker:
    """Advanced API call tracking and analysis."""
    
    def __init__(self, db_path: Optional[str] = None, max_memory_records: int = 2000):
        self.db_path = db_path or "cache/api_tracker_advanced.db"
        self.max_memory_records = max_memory_records
        self.lock = threading.Lock()
        
        # In-memory tracking for fast access
        self.call_history = deque(maxlen=max_memory_records)
        self.error_history = deque(maxlen=max_memory_records // 2)
        
        # Performance tracking
        self.endpoint_stats = defaultdict(lambda: {
            'total_calls': 0,
            'total_errors': 0,
            'total_response_time': 0.0,
            'avg_response_time': 0.0,
            'error_rate': 0.0
        })
        
        self._init_database()
        self._load_recent_history()
    
    def _init_database(self):
        """Initialize SQLite database for persistent tracking."""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS api_calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    endpoint TEXT NOT NULL,
                    success BOOLEAN NOT NULL,
                    error_type TEXT,
                    response_time REAL DEFAULT 0.0,
                    tokens_used INTEGER DEFAULT 0,
                    retry_count INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON api_calls(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_endpoint ON api_calls(endpoint)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_success ON api_calls(success)")
            
            # Create aggregated stats table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS hourly_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    hour_start DATETIME NOT NULL,
                    endpoint TEXT NOT NULL,
                    total_calls INTEGER DEFAULT 0,
                    total_errors INTEGER DEFAULT 0,
                    avg_response_time REAL DEFAULT 0.0,
                    total_tokens INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(hour_start, endpoint)
                )
            """)
    
    def _load_recent_history(self):
        """Load recent call history from database into memory."""
        cutoff_time = time.time() - (24 * 3600)  # Last 24 hours
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT timestamp, endpoint, success, error_type, 
                           response_time, tokens_used, retry_count
                    FROM api_calls 
                    WHERE timestamp > ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (cutoff_time, self.max_memory_records))
                
                for row in cursor:
                    record = APICallRecord(
                        timestamp=row[0],
                        endpoint=row[1],
                        success=bool(row[2]),
                        error_type=row[3],
                        response_time=row[4],
                        tokens_used=row[5],
                        retry_count=row[6]
                    )
                    
                    self.call_history.appendleft(record)
                    if not record.success:
                        self.error_history.appendleft(record)
                        
        except Exception as e:
            logger.error(f"Failed to load call history: {e}")
    
    def record_call(self, endpoint: str, success: bool, error_type: str = None,
                   response_time: float = 0.0, tokens_used: int = 0, retry_count: int = 0):
        """Record an API call with comprehensive details."""
        timestamp = time.time()
        
        record = APICallRecord(
            timestamp=timestamp,
            endpoint=endpoint,
            success=success,
            error_type=error_type,
            response_time=response_time,
            tokens_used=tokens_used,
            retry_count=retry_count
        )
        
        with self.lock:
            # Add to memory tracking
            self.call_history.append(record)
            if not success:
                self.error_history.append(record)
            
            # Update endpoint statistics
            stats = self.endpoint_stats[endpoint]
            stats['total_calls'] += 1
            if not success:
                stats['total_errors'] += 1
            
            if response_time > 0:
                stats['total_response_time'] += response_time
                stats['avg_response_time'] = stats['total_response_time'] / stats['total_calls']
            
            stats['error_rate'] = (stats['total_errors'] / stats['total_calls']) * 100
            
            # Persist to database (async to avoid blocking)
            self._persist_call_async(record)
    
    def _persist_call_async(self, record: APICallRecord):
        """Persist call record to database (should be called async)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO api_calls 
                    (timestamp, endpoint, success, error_type, response_time, tokens_used, retry_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    record.timestamp, record.endpoint, record.success, 
                    record.error_type, record.response_time, record.tokens_used, record.retry_count
                ))
        except Exception as e:
            logger.error(f"Failed to persist API call record: {e}")
    
    def get_stats_for_period(self, minutes: int) -> Dict[str, Any]:
        """Get comprehensive statistics for a time period."""
        cutoff_time = time.time() - (minutes * 60)
        
        with self.lock:
            # Filter records for the time period
            period_calls = [r for r in self.call_history if r.timestamp > cutoff_time]
            period_errors = [r for r in self.error_history if r.timestamp > cutoff_time]
            
            total_calls = len(period_calls)
            total_errors = len(period_errors)
            
            if total_calls == 0:
                return {
                    'period_minutes': minutes,
                    'total_calls': 0,
                    'total_errors': 0,
                    'error_rate': 0.0,
                    'calls_per_minute': 0.0,
                    'avg_response_time': 0.0,
                    'total_tokens': 0,
                    'endpoint_breakdown': {},
                    'error_breakdown': {},
                    'performance_trend': 'stable'
                }
            
            # Calculate basic metrics
            error_rate = (total_errors / total_calls) * 100
            calls_per_minute = total_calls / minutes if minutes > 0 else 0
            
            # Response time analysis
            response_times = [r.response_time for r in period_calls if r.response_time > 0]
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            
            # Token usage
            total_tokens = sum(r.tokens_used for r in period_calls)
            
            # Endpoint breakdown
            endpoint_breakdown = defaultdict(lambda: {'calls': 0, 'errors': 0, 'error_rate': 0.0})
            for record in period_calls:
                endpoint_breakdown[record.endpoint]['calls'] += 1
                if not record.success:
                    endpoint_breakdown[record.endpoint]['errors'] += 1
            
            for endpoint, stats in endpoint_breakdown.items():
                if stats['calls'] > 0:
                    stats['error_rate'] = (stats['errors'] / stats['calls']) * 100
            
            # Error type breakdown
            error_breakdown = defaultdict(int)
            for error in period_errors:
                if error.error_type:
                    error_breakdown[error.error_type] += 1
            
            # Performance trend analysis
            performance_trend = self._analyze_performance_trend(period_calls)
            
            return {
                'period_minutes': minutes,
                'total_calls': total_calls,
                'total_errors': total_errors,
                'error_rate': error_rate,
                'calls_per_minute': calls_per_minute,
                'avg_response_time': avg_response_time,
                'total_tokens': total_tokens,
                'endpoint_breakdown': dict(endpoint_breakdown),
                'error_breakdown': dict(error_breakdown),
                'performance_trend': performance_trend,
                'retry_analysis': self._analyze_retries(period_calls)
            }
    
    def _analyze_performance_trend(self, records: List[APICallRecord]) -> str:
        """Analyze performance trend from recent records."""
        if len(records) < 10:
            return 'insufficient_data'
        
        # Split into first and second half
        mid_point = len(records) // 2
        first_half = records[:mid_point]
        second_half = records[mid_point:]
        
        # Calculate average response times
        first_half_times = [r.response_time for r in first_half if r.response_time > 0]
        second_half_times = [r.response_time for r in second_half if r.response_time > 0]
        
        if not first_half_times or not second_half_times:
            return 'insufficient_data'
        
        first_avg = sum(first_half_times) / len(first_half_times)
        second_avg = sum(second_half_times) / len(second_half_times)
        
        # Calculate error rates
        first_errors = sum(1 for r in first_half if not r.success)
        second_errors = sum(1 for r in second_half if not r.success)
        
        first_error_rate = (first_errors / len(first_half)) * 100
        second_error_rate = (second_errors / len(second_half)) * 100
        
        # Determine trend
        response_time_change = ((second_avg - first_avg) / first_avg) * 100
        error_rate_change = second_error_rate - first_error_rate
        
        if response_time_change > 20 or error_rate_change > 5:
            return 'degrading'
        elif response_time_change < -10 and error_rate_change < -2:
            return 'improving'
        else:
            return 'stable'
    
    def _analyze_retries(self, records: List[APICallRecord]) -> Dict[str, Any]:
        """Analyze retry patterns in the records."""
        retry_counts = [r.retry_count for r in records if r.retry_count > 0]
        
        if not retry_counts:
            return {
                'total_retries': 0,
                'avg_retries': 0.0,
                'max_retries': 0,
                'retry_success_rate': 0.0
            }
        
        total_retries = sum(retry_counts)
        avg_retries = total_retries / len(retry_counts)
        max_retries = max(retry_counts)
        
        # Calculate retry success rate
        retry_records = [r for r in records if r.retry_count > 0]
        successful_retries = sum(1 for r in retry_records if r.success)
        retry_success_rate = (successful_retries / len(retry_records)) * 100 if retry_records else 0
        
        return {
            'total_retries': total_retries,
            'avg_retries': avg_retries,
            'max_retries': max_retries,
            'retry_success_rate': retry_success_rate
        }
    
    def get_endpoint_performance(self, endpoint: str) -> Dict[str, Any]:
        """Get detailed performance statistics for a specific endpoint."""
        with self.lock:
            if endpoint not in self.endpoint_stats:
                return {
                    'endpoint': endpoint,
                    'total_calls': 0,
                    'error_rate': 0.0,
                    'avg_response_time': 0.0
                }
            
            stats = self.endpoint_stats[endpoint].copy()
            stats['endpoint'] = endpoint
            return stats
    
    def should_trigger_emergency_mode(self) -> bool:
        """Determine if emergency mode should be triggered based on recent activity."""
        # Check last 15 minutes for critical errors
        stats_15min = self.get_stats_for_period(15)
        
        # Trigger emergency mode if:
        # 1. Error rate > 30% in last 15 minutes
        # 2. More than 10 errors in last 15 minutes
        # 3. Performance trend is degrading and error rate > 15%
        
        if stats_15min['error_rate'] > 30:
            logger.warning(f"Emergency mode triggered: High error rate {stats_15min['error_rate']:.1f}%")
            return True
        
        if stats_15min['total_errors'] > 10:
            logger.warning(f"Emergency mode triggered: Too many errors {stats_15min['total_errors']}")
            return True
        
        if (stats_15min['performance_trend'] == 'degrading' and 
            stats_15min['error_rate'] > 15):
            logger.warning("Emergency mode triggered: Degrading performance with elevated errors")
            return True
        
        return False
    
    def should_trigger_reduced_mode(self) -> bool:
        """Determine if reduced call mode should be triggered."""
        stats_15min = self.get_stats_for_period(15)
        stats_1hour = self.get_stats_for_period(60)
        
        # Trigger reduced mode if:
        # 1. Error rate > 15% in last 15 minutes
        # 2. More than 5 errors in last 15 minutes
        # 3. Consistent errors over the last hour (>20 total)
        
        if stats_15min['error_rate'] > 15:
            return True
        
        if stats_15min['total_errors'] > 5:
            return True
        
        if stats_1hour['total_errors'] > 20:
            return True
        
        return False
    
    def cleanup_old_records(self, days_to_keep: int = 7):
        """Clean up old records from database to maintain performance."""
        cutoff_time = time.time() - (days_to_keep * 24 * 3600)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Delete old records
                result = conn.execute("DELETE FROM api_calls WHERE timestamp < ?", (cutoff_time,))
                deleted_count = result.rowcount
                
                # Vacuum to reclaim space
                conn.execute("VACUUM")
                
                logger.info(f"Cleaned up {deleted_count} old API call records")
                
        except Exception as e:
            logger.error(f"Failed to cleanup old records: {e}")
    
    def export_stats_to_json(self, hours: int = 24) -> Dict[str, Any]:
        """Export comprehensive statistics to JSON format."""
        stats_1hour = self.get_stats_for_period(60)
        stats_24hour = self.get_stats_for_period(60 * 24)
        
        return {
            'export_timestamp': time.time(),
            'export_date': datetime.now().isoformat(),
            'stats_1hour': stats_1hour,
            'stats_24hour': stats_24hour,
            'endpoint_performance': {
                endpoint: self.get_endpoint_performance(endpoint)
                for endpoint in self.endpoint_stats.keys()
            },
            'database_info': {
                'path': self.db_path,
                'memory_records': len(self.call_history),
                'error_records': len(self.error_history)
            }
        }
