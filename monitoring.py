"""
Enhanced monitoring system for the Multi-AI Development System.
Provides real-time tracking of API calls, agent activity, and performance metrics.
"""

import datetime
import json
import time
import os
import threading
import sqlite3
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from collections import defaultdict, Counter

# Base logs directory - consistent with MetricsCollector
LOG_DIR = Path("logs")

class MetricsCollector:
    """Enhanced metrics collector with structured logging and performance tracking."""
    
    def __init__(self):
        """Initialize metrics collector with counters and setup logging."""
        # Initialize counters
        self.api_calls = Counter()
        self.agent_activities = Counter()
        self.errors = Counter()
        self.total_tokens = 0
        self.total_cost = 0.0
        self.start_time = time.time()
        
        # Session ID for grouping logs
        self.session_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Setup directories
        self.setup_logging_directories()
        
        # Initialize lock for thread safety
        self._lock = threading.Lock()
    
    def setup_logging_directories(self):
        """Create log directories if they don't exist."""
        self.logs_dir = Path("logs")
        self.api_logs_dir = self.logs_dir / "api_calls"
        self.agent_logs_dir = self.logs_dir / "agent_activity"
        self.workflow_logs_dir = self.logs_dir / "workflow"
        self.security_logs_dir = self.logs_dir / "security"  # ADDED: Security logs subdirectory
        
        # Create directories
        self.logs_dir.mkdir(exist_ok=True)
        self.api_logs_dir.mkdir(exist_ok=True)
        self.agent_logs_dir.mkdir(exist_ok=True)
        self.workflow_logs_dir.mkdir(exist_ok=True)
        self.security_logs_dir.mkdir(exist_ok=True)  # ADDED: Create security logs directory
    
    def increment_api_call(self, model_name: str):
        """Increment API call counter for the specified model."""
        with self._lock:
            self.api_calls[model_name] += 1
    
    def increment_agent_activity(self, agent_name: str, activity_type: str):
        """Increment agent activity counter."""
        with self._lock:
            self.agent_activities[f"{agent_name}:{activity_type}"] += 1
    
    def increment_error(self, error_type: str):
        """Increment error counter."""
        with self._lock:
            self.errors[error_type] += 1
    
    def record_token_usage(self, input_tokens: int, output_tokens: int, model_name: str):
        """Record token usage and estimate cost."""
        with self._lock:
            self.total_tokens += (input_tokens + output_tokens)
            
            # Very rough cost estimation (customize based on your models)
            input_cost = input_tokens * 0.00001  # $0.01 per 1000 tokens
            output_cost = output_tokens * 0.00002  # $0.02 per 1000 tokens
            self.total_cost += (input_cost + output_cost)
    
    def get_elapsed_time(self) -> float:
        """Get elapsed time since metrics collector was initialized."""
        return time.time() - self.start_time
    
    def get_summary_metrics(self) -> Dict[str, Any]:
        """Get summary metrics for the current session."""
        with self._lock:
            return {
                "session_id": self.session_id,
                "elapsed_time": self.get_elapsed_time(),
                "api_calls": dict(self.api_calls),
                "agent_activities": dict(self.agent_activities),
                "errors": dict(self.errors),
                "total_tokens": self.total_tokens,
                "estimated_cost": self.total_cost,
                "timestamp": datetime.datetime.now().isoformat()
            }
    
    def save_metrics_to_file(self):
        """Save all metrics to a JSON file."""
        metrics_file = self.logs_dir / f"metrics_{self.session_id}.json"
        
        try:
            with open(metrics_file, "w") as f:
                json.dump(self.get_summary_metrics(), f, indent=2)
            print(f"✅ Metrics saved to {metrics_file}")
            
        except Exception as e:
            print(f"❌ Failed to save metrics: {e}")
    
    def log_workflow_phase(self, phase_name: str, status: str, details: Dict[str, Any] = None):
        """Log workflow phase transitions."""
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "session_id": self.session_id,
            "phase": phase_name,
            "status": status,
            "details": details or {}
        }
        
        self._log_to_file(log_entry, self.workflow_logs_dir, "workflow")
    
    def _log_to_file(self, log_entry: Dict[str, Any], log_dir: Path, prefix: str):
        """Internal method to log to a file with standardized format."""
        today = datetime.datetime.now().strftime("%Y%m%d")
        log_file = log_dir / f"{prefix}_{today}.jsonl"  # FIXED: Use .jsonl extension
        
        try:
            with open(log_file, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
                
        except Exception as e:
            print(f"❌ Failed to write to log file {log_file}: {e}")

# Initialize metrics collector
metrics_collector = MetricsCollector()

def log_api_call_realtime(
    model: str, 
    call_type: str, 
    input_preview: str, 
    output_preview: str = "", 
    duration: float = 0.0,
    success: bool = True,
    error_msg: str = "",
    temperature: Optional[float] = None,
    agent_context: str = ""
):
    """Log API call details in real-time to a file."""
    log_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "session_id": metrics_collector.session_id,
        "model": model,
        "call_type": call_type,
        "input_preview": input_preview,
        "output_preview": output_preview,
        "duration_seconds": duration,
        "success": success,
        "error": error_msg,
        "temperature": temperature,
        "agent_context": agent_context
    }
    
    # FIXED: Use the appropriate logs directory and .jsonl extension
    log_file = metrics_collector.api_logs_dir / f"api_calls_{datetime.datetime.now().strftime('%Y%m%d')}.jsonl"
    
    try:
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
            
    except Exception as e:
        print(f"❌ Failed to write API log: {e}")

def log_agent_activity(agent_name: str, message: str, level: str = "INFO"):
    """Log agent activity with standardized format."""
    log_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "session_id": metrics_collector.session_id,
        "agent": agent_name,
        "level": level,
        "message": message
    }
    
    # Increment counter for agent activity
    if level in ["ERROR", "WARNING"]:
        metrics_collector.increment_error(f"{agent_name}:{level}")
    
    metrics_collector.increment_agent_activity(agent_name, level)
    
    # Console output for visibility
    level_markers = {
        "ERROR": "❌",
        "WARNING": "⚠️",
        "INFO": "ℹ️",
        "SUCCESS": "✅",
        "START": "🚀"
    }
    marker = level_markers.get(level, "ℹ️")
    print(f"{marker} [{agent_name}] {message}")
    
    # FIXED: Use the appropriate logs directory and .jsonl extension
    log_file = metrics_collector.agent_logs_dir / f"agent_activity_{datetime.datetime.now().strftime('%Y%m%d')}.jsonl"
    
    try:
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
            
    except Exception as e:
        print(f"❌ Failed to write agent log: {e}")

def log_security_event(event_type: str, details: Dict[str, Any], severity: str = "INFO"):
    """Log security-related events."""
    log_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "session_id": metrics_collector.session_id,
        "event_type": event_type,
        "severity": severity,
        "details": details
    }
    
    # FIXED: Use the security logs directory and .jsonl extension
    log_file = metrics_collector.security_logs_dir / f"security_{datetime.datetime.now().strftime('%Y%m%d')}.jsonl"
    
    try:
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
            
    except Exception as e:
        print(f"❌ Failed to write security log: {e}")
        
    # Increment counter for security events
    if severity in ["HIGH", "CRITICAL"]:
        metrics_collector.increment_error(f"security:{event_type}")
        
    # Console output for high-severity events
    if severity in ["HIGH", "CRITICAL"]:
        print(f"🔒 SECURITY {severity}: {event_type} - {details.get('message', '')}")

# Global convenience logging functions
def log_global(message: str, level: str = "INFO"):
    """Global logging function for system-wide events."""
    log_agent_activity("System", message, level)

def log_info(message: str):
    """Convenience function for INFO level logging."""
    log_global(message, "INFO")

def log_warning(message: str):
    """Convenience function for WARNING level logging."""
    log_global(message, "WARNING")

def log_error(message: str):
    """Convenience function for ERROR level logging."""
    log_global(message, "ERROR")

def initialize_logging(agent_name: str = "System"):
    """Initialize logging system."""
    log_agent_activity(agent_name, "Logging system initialized", "START")
    return metrics_collector

def save_final_metrics():
    """Save final metrics at the end of execution."""
    metrics_collector.save_metrics_to_file()
    log_global("Final metrics saved", "SUCCESS")