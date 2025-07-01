#!/usr/bin/env python3
"""
Real-Time Performance Monitor for Multi-AI Development System

This module provides comprehensive performance monitoring and analytics:
- Real-time system metrics collection
- Performance trend analysis
- Bottleneck detection
- Resource usage optimization alerts
- Interactive dashboard display
"""

import os
import sys
import time
import json
import psutil
import threading
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import deque, defaultdict
import sqlite3

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from enhanced_memory_manager import create_memory_manager
    from rag_manager import get_rag_manager
    from advanced_rate_limiting.api_tracker import APITracker
    from monitoring import log_agent_activity
    DEPENDENCIES_AVAILABLE = True
except ImportError:
    DEPENDENCIES_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class SystemMetrics:
    """System performance metrics snapshot."""
    timestamp: float = field(default_factory=time.time)
    
    # System resources
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_available_mb: float = 0.0
    disk_usage_percent: float = 0.0
    disk_free_gb: float = 0.0
    
    # Application metrics
    enhanced_memory_hit_ratio: float = 0.0
    enhanced_memory_ops_per_sec: float = 0.0
    rag_index_size_mb: float = 0.0
    rag_documents_count: int = 0
    
    # API performance
    api_cache_hit_rate: float = 0.0
    api_response_time_avg: float = 0.0
    api_error_rate: float = 0.0
    
    # File system metrics
    output_dir_size_mb: float = 0.0
    cache_dir_size_mb: float = 0.0
    log_dir_size_mb: float = 0.0
    
    # Process metrics
    process_count: int = 0
    thread_count: int = 0
    open_files: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class PerformanceAlert:
    """Performance alert definition."""
    metric_name: str
    threshold: float
    operator: str  # 'gt', 'lt', 'eq'
    severity: str  # 'low', 'medium', 'high', 'critical'
    message: str
    cooldown_minutes: int = 5
    
    def check_alert(self, value: float, last_alert_time: Optional[float] = None) -> bool:
        """Check if alert should be triggered."""
        # Check cooldown
        if last_alert_time and (time.time() - last_alert_time) < (self.cooldown_minutes * 60):
            return False
        
        # Check threshold
        if self.operator == 'gt':
            return value > self.threshold
        elif self.operator == 'lt':
            return value < self.threshold
        elif self.operator == 'eq':
            return abs(value - self.threshold) < 0.01
        
        return False


class PerformanceMonitor:
    """Real-time performance monitoring system."""
    
    def __init__(self, 
                 project_root: str = None,
                 metrics_retention_hours: int = 24,
                 collection_interval_sec: int = 30,
                 enable_alerts: bool = True):
        """
        Initialize the performance monitor.
        
        Args:
            project_root: Root directory of the project
            metrics_retention_hours: How long to retain metrics data
            collection_interval_sec: How often to collect metrics
            enable_alerts: Enable performance alerting
        """
        self.project_root = Path(project_root or PROJECT_ROOT)
        self.metrics_retention_hours = metrics_retention_hours
        self.collection_interval_sec = collection_interval_sec
        self.enable_alerts = enable_alerts
        
        # Metrics storage (in-memory ring buffer)
        max_metrics = int((metrics_retention_hours * 3600) / collection_interval_sec)
        self.metrics_history: deque[SystemMetrics] = deque(maxlen=max_metrics)
        
        # Performance tracking
        self.trend_analysis = defaultdict(list)
        self.bottleneck_detection = defaultdict(int)
        
        # Alert system
        self.alerts = self._setup_default_alerts()
        self.alert_history = deque(maxlen=100)
        self.last_alert_times = {}
        
        # Monitoring control
        self.monitoring_active = False
        self.monitor_thread = None
        
        # Database for persistent storage
        self.db_path = self.project_root / "cache" / "performance_metrics.db"
        self._init_database()
        
        logger.info(f"Performance Monitor initialized for {self.project_root}")
    
    def _setup_default_alerts(self) -> List[PerformanceAlert]:
        """Setup default performance alerts."""
        return [
            PerformanceAlert("cpu_percent", 80.0, "gt", "medium", 
                           "High CPU usage detected: {value:.1f}%"),
            PerformanceAlert("memory_percent", 85.0, "gt", "high", 
                           "High memory usage detected: {value:.1f}%"),
            PerformanceAlert("disk_usage_percent", 90.0, "gt", "high", 
                           "High disk usage detected: {value:.1f}%"),
            PerformanceAlert("enhanced_memory_hit_ratio", 0.5, "lt", "medium", 
                           "Low memory cache hit ratio: {value:.1%}"),
            PerformanceAlert("api_error_rate", 10.0, "gt", "high", 
                           "High API error rate: {value:.1f}%"),
            PerformanceAlert("output_dir_size_mb", 1000.0, "gt", "medium", 
                           "Large output directory size: {value:.1f}MB"),
            PerformanceAlert("process_count", 50, "gt", "low", 
                           "High process count: {value}")
        ]
    
    def _init_database(self):
        """Initialize SQLite database for persistent metrics storage."""
        try:
            os.makedirs(self.db_path.parent, exist_ok=True)
            
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp REAL NOT NULL,
                        metrics_json TEXT NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_metrics_timestamp 
                    ON metrics(timestamp)
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS alerts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp REAL NOT NULL,
                        metric_name TEXT NOT NULL,
                        value REAL NOT NULL,
                        threshold REAL NOT NULL,
                        severity TEXT NOT NULL,
                        message TEXT NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to initialize performance database: {e}")
    
    def start_monitoring(self):
        """Start real-time monitoring in background thread."""
        if self.monitoring_active:
            logger.warning("Monitoring already active")
            return
        
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        
        logger.info(f"Performance monitoring started (interval: {self.collection_interval_sec}s)")
    
    def stop_monitoring(self):
        """Stop real-time monitoring."""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
        
        logger.info("Performance monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop that runs in background."""
        while self.monitoring_active:
            try:
                # Collect metrics
                metrics = self.collect_metrics()
                
                # Store in memory and database
                self.metrics_history.append(metrics)
                self._store_metrics_to_db(metrics)
                
                # Check alerts
                if self.enable_alerts:
                    self._check_alerts(metrics)
                
                # Update trend analysis
                self._update_trend_analysis(metrics)
                
                # Sleep until next collection
                time.sleep(self.collection_interval_sec)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.collection_interval_sec)
    
    def collect_metrics(self) -> SystemMetrics:
        """Collect comprehensive system metrics."""
        metrics = SystemMetrics()
        
        try:
            # System resource metrics
            metrics.cpu_percent = psutil.cpu_percent(interval=1)
            
            memory = psutil.virtual_memory()
            metrics.memory_percent = memory.percent
            metrics.memory_available_mb = memory.available / (1024 * 1024)
            
            disk = psutil.disk_usage(str(self.project_root))
            metrics.disk_usage_percent = (disk.used / disk.total) * 100
            metrics.disk_free_gb = disk.free / (1024 * 1024 * 1024)
            
            # Process metrics
            process = psutil.Process()
            metrics.process_count = len(psutil.pids())
            metrics.thread_count = process.num_threads()
            try:
                metrics.open_files = len(process.open_files())
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                metrics.open_files = 0
            
            # Application-specific metrics
            if DEPENDENCIES_AVAILABLE:
                self._collect_app_metrics(metrics)
            
            # File system metrics
            self._collect_filesystem_metrics(metrics)
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
        
        return metrics
    
    def _collect_app_metrics(self, metrics: SystemMetrics):
        """Collect application-specific metrics."""
        try:
            # Enhanced memory metrics
            memory_manager = create_memory_manager()
            if memory_manager:
                stats = memory_manager.get_stats()
                metrics.enhanced_memory_hit_ratio = stats.hit_ratio
                metrics.enhanced_memory_ops_per_sec = stats.operations_per_second
            
            # RAG metrics
            rag_manager = get_rag_manager()
            if rag_manager:
                rag_info = rag_manager.get_vector_store_info()
                metrics.rag_documents_count = rag_info.get("document_count", 0)
                
                # Get RAG store size
                rag_store_path = self.project_root / ".rag_store"
                if rag_store_path.exists():
                    metrics.rag_index_size_mb = self._get_directory_size(rag_store_path)
            
            # API metrics (if API tracker available)
            try:
                api_tracker = APITracker()
                # This would require API tracker to expose metrics
                # For now, we'll skip this or implement basic tracking
            except:
                pass
                
        except Exception as e:
            logger.debug(f"Error collecting app metrics: {e}")
    
    def _collect_filesystem_metrics(self, metrics: SystemMetrics):
        """Collect file system related metrics."""
        try:
            # Output directory size
            output_dir = self.project_root / "output"
            if output_dir.exists():
                metrics.output_dir_size_mb = self._get_directory_size(output_dir)
            
            # Cache directory size
            cache_dir = self.project_root / "cache"
            if cache_dir.exists():
                metrics.cache_dir_size_mb = self._get_directory_size(cache_dir)
            
            # Logs directory size
            logs_dir = self.project_root / "logs"
            if logs_dir.exists():
                metrics.log_dir_size_mb = self._get_directory_size(logs_dir)
                
        except Exception as e:
            logger.debug(f"Error collecting filesystem metrics: {e}")
    
    def _get_directory_size(self, directory: Path) -> float:
        """Get directory size in MB."""
        if not directory.exists() or not directory.is_dir():
            return 0.0
        
        total_size = 0
        try:
            for file_path in directory.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        except (OSError, PermissionError):
            pass
        
        return total_size / (1024 * 1024)
    
    def _store_metrics_to_db(self, metrics: SystemMetrics):
        """Store metrics to persistent database."""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute(
                    "INSERT INTO metrics (timestamp, metrics_json) VALUES (?, ?)",
                    (metrics.timestamp, json.dumps(metrics.to_dict()))
                )
                conn.commit()
                
        except Exception as e:
            logger.debug(f"Error storing metrics to database: {e}")
    
    def _check_alerts(self, metrics: SystemMetrics):
        """Check for performance alerts."""
        metrics_dict = metrics.to_dict()
        
        for alert in self.alerts:
            if alert.metric_name in metrics_dict:
                value = metrics_dict[alert.metric_name]
                
                if alert.check_alert(value, self.last_alert_times.get(alert.metric_name)):
                    # Trigger alert
                    alert_message = alert.message.format(value=value)
                    
                    alert_record = {
                        "timestamp": time.time(),
                        "metric_name": alert.metric_name,
                        "value": value,
                        "threshold": alert.threshold,
                        "severity": alert.severity,
                        "message": alert_message
                    }
                    
                    self.alert_history.append(alert_record)
                    self.last_alert_times[alert.metric_name] = time.time()
                    
                    # Log alert
                    log_level = {
                        "low": "INFO",
                        "medium": "WARNING", 
                        "high": "ERROR",
                        "critical": "CRITICAL"
                    }.get(alert.severity, "WARNING")
                    
                    logger.log(getattr(logging, log_level), f"PERFORMANCE ALERT: {alert_message}")
                    
                    # Store alert to database
                    self._store_alert_to_db(alert_record)
    
    def _store_alert_to_db(self, alert_record: Dict[str, Any]):
        """Store alert to persistent database."""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute(
                    """INSERT INTO alerts 
                       (timestamp, metric_name, value, threshold, severity, message) 
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        alert_record["timestamp"],
                        alert_record["metric_name"], 
                        alert_record["value"],
                        alert_record["threshold"],
                        alert_record["severity"],
                        alert_record["message"]
                    )
                )
                conn.commit()
                
        except Exception as e:
            logger.debug(f"Error storing alert to database: {e}")
    
    def _update_trend_analysis(self, metrics: SystemMetrics):
        """Update trend analysis with new metrics."""
        if len(self.metrics_history) < 2:
            return
        
        # Calculate trends for key metrics
        key_metrics = ['cpu_percent', 'memory_percent', 'disk_usage_percent', 
                      'enhanced_memory_hit_ratio', 'output_dir_size_mb']
        
        previous_metrics = self.metrics_history[-2]
        current_metrics = metrics
        
        for metric_name in key_metrics:
            try:
                prev_value = getattr(previous_metrics, metric_name)
                curr_value = getattr(current_metrics, metric_name)
                
                if prev_value > 0:  # Avoid division by zero
                    change_percent = ((curr_value - prev_value) / prev_value) * 100
                    self.trend_analysis[metric_name].append(change_percent)
                    
                    # Keep only recent trends
                    if len(self.trend_analysis[metric_name]) > 20:
                        self.trend_analysis[metric_name] = self.trend_analysis[metric_name][-20:]
                        
            except AttributeError:
                pass
    
    def get_current_metrics(self) -> Optional[SystemMetrics]:
        """Get the most recent metrics."""
        return self.metrics_history[-1] if self.metrics_history else None
    
    def get_metrics_history(self, hours: int = 1) -> List[SystemMetrics]:
        """Get metrics history for the specified number of hours."""
        cutoff_time = time.time() - (hours * 3600)
        return [m for m in self.metrics_history if m.timestamp >= cutoff_time]
    
    def get_trend_analysis(self) -> Dict[str, Dict[str, float]]:
        """Get trend analysis summary."""
        analysis = {}
        
        for metric_name, changes in self.trend_analysis.items():
            if changes:
                analysis[metric_name] = {
                    "avg_change_percent": sum(changes) / len(changes),
                    "max_change_percent": max(changes),
                    "min_change_percent": min(changes),
                    "volatility": max(changes) - min(changes),
                    "trend_direction": "increasing" if sum(changes) > 0 else "decreasing"
                }
        
        return analysis
    
    def get_recent_alerts(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent alerts."""
        cutoff_time = time.time() - (hours * 3600)
        return [alert for alert in self.alert_history if alert["timestamp"] >= cutoff_time]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        current = self.get_current_metrics()
        if not current:
            return {"error": "No metrics available"}
        
        # Get historical averages
        history_1h = self.get_metrics_history(1)
        history_24h = self.get_metrics_history(24)
        
        def avg_metric(metrics_list: List[SystemMetrics], attr: str) -> float:
            if not metrics_list:
                return 0.0
            values = [getattr(m, attr) for m in metrics_list]
            return sum(values) / len(values)
        
        summary = {
            "timestamp": current.timestamp,
            "current": current.to_dict(),
            "averages_1h": {
                "cpu_percent": avg_metric(history_1h, "cpu_percent"),
                "memory_percent": avg_metric(history_1h, "memory_percent"),
                "disk_usage_percent": avg_metric(history_1h, "disk_usage_percent"),
                "enhanced_memory_hit_ratio": avg_metric(history_1h, "enhanced_memory_hit_ratio")
            },
            "averages_24h": {
                "cpu_percent": avg_metric(history_24h, "cpu_percent"),
                "memory_percent": avg_metric(history_24h, "memory_percent"),
                "disk_usage_percent": avg_metric(history_24h, "disk_usage_percent"),
                "enhanced_memory_hit_ratio": avg_metric(history_24h, "enhanced_memory_hit_ratio")
            },
            "trends": self.get_trend_analysis(),
            "recent_alerts": self.get_recent_alerts(1),
            "health_score": self._calculate_health_score(current)
        }
        
        return summary
    
    def _calculate_health_score(self, metrics: SystemMetrics) -> float:
        """Calculate overall system health score (0-100)."""
        score_components = []
        
        # CPU health (25%)
        cpu_score = max(0, 100 - metrics.cpu_percent)
        score_components.append(cpu_score * 0.25)
        
        # Memory health (25%)
        memory_score = max(0, 100 - metrics.memory_percent)
        score_components.append(memory_score * 0.25)
        
        # Disk health (20%)
        disk_score = max(0, 100 - metrics.disk_usage_percent)
        score_components.append(disk_score * 0.20)
        
        # Application health (30%)
        app_score = 50  # Base score
        if metrics.enhanced_memory_hit_ratio > 0:
            app_score = min(100, metrics.enhanced_memory_hit_ratio * 100)
        score_components.append(app_score * 0.30)
        
        return sum(score_components)
    
    def generate_report(self, output_file: str = None) -> str:
        """Generate comprehensive performance report."""
        summary = self.get_performance_summary()
        
        report = f"""
# Performance Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Current System Status
- CPU Usage: {summary['current']['cpu_percent']:.1f}%
- Memory Usage: {summary['current']['memory_percent']:.1f}%
- Disk Usage: {summary['current']['disk_usage_percent']:.1f}%
- Health Score: {summary['health_score']:.1f}/100

## Application Performance
- Enhanced Memory Hit Ratio: {summary['current']['enhanced_memory_hit_ratio']:.1%}
- RAG Index Size: {summary['current']['rag_index_size_mb']:.1f}MB
- RAG Documents: {summary['current']['rag_documents_count']}

## Storage Usage
- Output Directory: {summary['current']['output_dir_size_mb']:.1f}MB
- Cache Directory: {summary['current']['cache_dir_size_mb']:.1f}MB
- Logs Directory: {summary['current']['log_dir_size_mb']:.1f}MB

## Recent Alerts ({len(summary['recent_alerts'])})
"""
        
        for alert in summary['recent_alerts'][-5:]:  # Show last 5 alerts
            alert_time = datetime.fromtimestamp(alert['timestamp']).strftime('%H:%M:%S')
            report += f"- {alert_time} [{alert['severity'].upper()}] {alert['message']}\n"
        
        if not summary['recent_alerts']:
            report += "- No recent alerts\n"
        
        report += "\n## Trend Analysis\n"
        for metric, trend in summary['trends'].items():
            direction = "📈" if trend['trend_direction'] == 'increasing' else "📉"
            report += f"- {metric}: {direction} {trend['avg_change_percent']:.1f}% avg change\n"
        
        if output_file:
            try:
                with open(output_file, 'w') as f:
                    f.write(report)
                logger.info(f"Performance report saved to {output_file}")
            except Exception as e:
                logger.error(f"Failed to save report to {output_file}: {e}")
        
        return report
    
    def cleanup_old_data(self, retention_days: int = 7):
        """Clean up old performance data."""
        cutoff_time = time.time() - (retention_days * 24 * 3600)
        
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                # Clean old metrics
                result = conn.execute("DELETE FROM metrics WHERE timestamp < ?", (cutoff_time,))
                metrics_deleted = result.rowcount
                
                # Clean old alerts
                result = conn.execute("DELETE FROM alerts WHERE timestamp < ?", (cutoff_time,))
                alerts_deleted = result.rowcount
                
                conn.commit()
                
                logger.info(f"Cleaned up old performance data: {metrics_deleted} metrics, {alerts_deleted} alerts")
                
        except Exception as e:
            logger.error(f"Failed to cleanup old performance data: {e}")


def main():
    """Run performance monitor from command line."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Performance Monitor")
    parser.add_argument("--project-root", default=".", help="Project root directory")
    parser.add_argument("--interval", type=int, default=30, help="Collection interval in seconds")
    parser.add_argument("--retention", type=int, default=24, help="Metrics retention in hours")
    parser.add_argument("--no-alerts", action="store_true", help="Disable alerts")
    parser.add_argument("--report", help="Generate report and save to file")
    parser.add_argument("--summary", action="store_true", help="Show performance summary")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    monitor = PerformanceMonitor(
        project_root=args.project_root,
        metrics_retention_hours=args.retention,
        collection_interval_sec=args.interval,
        enable_alerts=not args.no_alerts
    )
    
    if args.summary:
        # Show current summary
        summary = monitor.get_performance_summary()
        print(json.dumps(summary, indent=2))
        return
    
    if args.report:
        # Generate report
        report = monitor.generate_report(args.report)
        print(report)
        return
    
    # Start monitoring
    monitor.start_monitoring()
    
    if args.daemon:
        print("Performance monitoring started as daemon. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            print("\nStopping performance monitor...")
            monitor.stop_monitoring()
    else:
        # Run for 60 seconds then show summary
        print(f"Collecting metrics for 60 seconds (interval: {args.interval}s)...")
        time.sleep(60)
        
        summary = monitor.get_performance_summary()
        print("\nPerformance Summary:")
        print(json.dumps(summary, indent=2))
        
        monitor.stop_monitoring()


if __name__ == "__main__":
    main() 