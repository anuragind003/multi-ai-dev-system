"""
Enhanced Multi-Layer Logging System for Multi-AI Development System
Provides organized, real-time, and detailed logging with minimal terminal noise.
"""

import os
import sys
import json
import time
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from collections import defaultdict
import threading
import sqlite3
from contextlib import contextmanager

class EnhancedLoggingSystem:
    """
    Multi-layer logging system that separates:
    1. Terminal: Only major milestones and errors
    2. Real-time files: Detailed logs organized by category
    3. Dashboard: Live web interface for monitoring
    """
    
    def __init__(self, session_id: str = None):
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.start_time = time.time()
        
        # Create directory structure
        self.setup_directories()
        
        # Initialize loggers
        self.setup_loggers()
        
        # Initialize live dashboard data
        self.live_data = {
            "agents": defaultdict(dict),
            "workflow": {"status": "starting", "phase": "initialization"},
            "api_calls": defaultdict(int),
            "performance": defaultdict(list),
            "errors": []
        }
        
        # Thread lock for live data
        self._lock = threading.Lock()
        
        # Start background dashboard updater
        self.start_dashboard_updater()
        
    def setup_directories(self):
        """Create organized logging directory structure."""
        base_dir = Path("logs")
        session_dir = base_dir / "sessions" / self.session_id
        
        self.dirs = {
            "base": base_dir,
            "session": session_dir,
            "agents": session_dir / "agents",
            "workflow": session_dir / "workflow", 
            "api": session_dir / "api_calls",
            "performance": session_dir / "performance",
            "errors": session_dir / "errors",
            "dashboard": session_dir / "dashboard"
        }
        
        # Create all directories
        for dir_path in self.dirs.values():
            dir_path.mkdir(parents=True, exist_ok=True)
            
        # Create session info file
        session_info = {
            "session_id": self.session_id,
            "start_time": datetime.now().isoformat(),
            "status": "active"
        }
        
        with open(self.dirs["session"] / "session_info.json", "w") as f:
            json.dump(session_info, f, indent=2)
    
    def setup_loggers(self):
        """Setup different loggers for different purposes."""
        
        # 1. Terminal Logger - Only major events
        self.terminal_logger = logging.getLogger("terminal")
        self.terminal_logger.setLevel(logging.INFO)
        
        # Clear existing handlers
        for handler in self.terminal_logger.handlers[:]:
            self.terminal_logger.removeHandler(handler)
        
        # Console handler with custom formatter
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = TerminalFormatter()
        console_handler.setFormatter(console_formatter)
        self.terminal_logger.addHandler(console_handler)
        
        # 2. File Loggers - Detailed logging by category
        self.file_loggers = {}
        
        categories = ["agents", "workflow", "api", "performance", "errors"]
        for category in categories:
            logger = logging.getLogger(f"file.{category}")
            logger.setLevel(logging.DEBUG)
            
            # Clear existing handlers
            for handler in logger.handlers[:]:
                logger.removeHandler(handler)
            
            # File handler with rotation
            log_file = self.dirs[category] / f"{category}_{self.session_id}.log"
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            )
            
            file_formatter = DetailedFormatter()
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
            
            self.file_loggers[category] = logger
            
        # 3. JSON Structured Loggers - For dashboard and analysis
        self.json_loggers = {}
        for category in categories:
            log_file = self.dirs[category] / f"{category}_{self.session_id}.jsonl"
            self.json_loggers[category] = log_file
    
    def log_terminal(self, level: str, message: str, category: str = "SYSTEM"):
        """Log major events to terminal only."""
        # Enhanced formatting for React agents
        if "react" in category.lower() or "agent" in category.lower():
            formatted_message = f"🤖 [{category}] {message}"
        else:
            formatted_message = f"[{category}] {message}"
        getattr(self.terminal_logger, level.lower())(formatted_message)
        
    def log_detailed(self, category: str, level: str, agent: str, message: str, 
                    metadata: Dict[str, Any] = None):
        """Log detailed information to category-specific files."""
        
        # Log to text file
        if category in self.file_loggers:
            full_message = f"[{agent}] {message}"
            if metadata:
                full_message += f" | Metadata: {json.dumps(metadata, default=str)}"
            getattr(self.file_loggers[category], level.lower())(full_message)
        
        # Log to JSON file for structured analysis
        if category in self.json_loggers:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "level": level,
                "category": category,
                "agent": agent,
                "message": message,
                "metadata": metadata or {},
                "session_id": self.session_id
            }
            
            with open(self.json_loggers[category], "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        
        # Update live dashboard data
        self.update_live_data(category, agent, message, level, metadata)
    
    def update_live_data(self, category: str, agent: str, message: str, 
                        level: str, metadata: Dict[str, Any] = None):
        """Update live dashboard data."""
        with self._lock:
            timestamp = datetime.now().isoformat()
            
            if category == "agents":
                self.live_data["agents"][agent] = {
                    "last_activity": timestamp,
                    "last_message": message,
                    "status": level
                }
            elif category == "workflow":
                self.live_data["workflow"].update({
                    "last_update": timestamp,
                    "last_message": message,
                    "status": level
                })
            elif category == "api":
                if metadata and "model" in metadata:
                    self.live_data["api_calls"][metadata["model"]] += 1
            elif category == "errors" and level == "ERROR":
                self.live_data["errors"].append({
                    "timestamp": timestamp,
                    "agent": agent,
                    "message": message,
                    "metadata": metadata
                })
                # Keep only last 50 errors
                self.live_data["errors"] = self.live_data["errors"][-50:]
    
    def start_dashboard_updater(self):
        """Start background thread to update dashboard files."""
        def update_dashboard():
            while True:
                try:
                    # Update dashboard data every 5 seconds
                    with self._lock:
                        dashboard_data = {
                            "session_info": {
                                "session_id": self.session_id,
                                "start_time": self.start_time,
                                "current_time": time.time(),
                                "duration": time.time() - self.start_time
                            },
                            "live_data": dict(self.live_data)
                        }
                    
                    # Write to dashboard file
                    dashboard_file = self.dirs["dashboard"] / "live_status.json"
                    with open(dashboard_file, "w") as f:
                        json.dump(dashboard_data, f, indent=2, default=str)
                    
                    # Update HTML dashboard
                    self.update_html_dashboard(dashboard_data)
                    
                except Exception as e:
                    print(f"Dashboard update error: {e}")
                
                time.sleep(5)
        
        dashboard_thread = threading.Thread(target=update_dashboard, daemon=True)
        dashboard_thread.start()
    
    def update_html_dashboard(self, data: Dict[str, Any]):
        """Update HTML dashboard for real-time viewing."""
        html_content = self.generate_dashboard_html(data)
        dashboard_file = self.dirs["dashboard"] / "live_dashboard.html"
        
        with open(dashboard_file, "w") as f:
            f.write(html_content)
    
    def generate_dashboard_html(self, data: Dict[str, Any]) -> str:
        """Generate HTML dashboard content."""
        session_info = data["session_info"]
        live_data = data["live_data"]
        
        duration_mins = int(session_info["duration"] / 60)
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Multi-AI Development System - Live Dashboard</title>
    <meta http-equiv="refresh" content="5">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
        .card {{ background: white; padding: 15px; margin: 10px 0; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .status-active {{ color: #27ae60; }}
        .status-error {{ color: #e74c3c; }}
        .status-warning {{ color: #f39c12; }}
        .agents-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px; }}
        .agent-card {{ background: #ecf0f1; padding: 10px; border-radius: 3px; }}
        .metric {{ display: inline-block; background: #3498db; color: white; padding: 5px 10px; margin: 5px; border-radius: 3px; }}
        .error-item {{ background: #fadbd8; border-left: 4px solid #e74c3c; padding: 10px; margin: 5px 0; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f2f2f2; }}
        .log-link {{ display: inline-block; background: #34495e; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px; margin: 2px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>[AI] Multi-AI Development System</h1>
            <p>Session: {session_info['session_id']} | Duration: {duration_mins} minutes | Status: <span class="status-active">Active</span></p>
        </div>
        
        <div class="card">
            <h2>[METRICS] Quick Metrics</h2>
            <span class="metric">Active Agents: {len(live_data['agents'])}</span>
            <span class="metric">API Calls: {sum(live_data['api_calls'].values())}</span>
            <span class="metric">Errors: {len(live_data['errors'])}</span>
            <span class="metric">Workflow: {live_data['workflow'].get('status', 'Unknown')}</span>
        </div>
        
        <div class="card">
            <h2>[WORKFLOW] Current Workflow Status</h2>
            <p><strong>Status:</strong> {live_data['workflow'].get('status', 'Unknown')}</p>
            <p><strong>Phase:</strong> {live_data['workflow'].get('phase', 'Unknown')}</p>
            <p><strong>Last Update:</strong> {live_data['workflow'].get('last_update', 'Never')}</p>
            <p><strong>Message:</strong> {live_data['workflow'].get('last_message', 'No recent activity')}</p>
        </div>
        
        <div class="card">
            <h2>[AGENTS] Agent Activities</h2>
            <div class="agents-grid">
"""
        
        for agent_name, agent_data in live_data['agents'].items():
            status_class = {
                'ERROR': 'status-error',
                'WARNING': 'status-warning',
                'INFO': 'status-active'
            }.get(agent_data.get('status', 'INFO'), 'status-active')
            
            html += f"""
                <div class="agent-card">
                    <h4>{agent_name}</h4>
                    <p><strong>Status:</strong> <span class="{status_class}">{agent_data.get('status', 'Unknown')}</span></p>
                    <p><strong>Last Activity:</strong> {agent_data.get('last_activity', 'Never')}</p>
                    <p><strong>Message:</strong> {agent_data.get('last_message', 'No recent activity')[:100]}...</p>
                </div>
"""
        
        html += """
            </div>
        </div>
        
        <div class="card">
            <h2>[API] API Call Statistics</h2>
            <table>
                <tr><th>Model</th><th>Calls</th></tr>
"""
        
        for model, count in live_data['api_calls'].items():
            html += f"<tr><td>{model}</td><td>{count}</td></tr>"
        
        html += """
            </table>
        </div>
"""
        
        if live_data['errors']:
            html += """
        <div class="card">
            <h2>[ERROR] Recent Errors</h2>
"""
            for error in live_data['errors'][-10:]:  # Show last 10 errors
                html += f"""
            <div class="error-item">
                <strong>{error['agent']}</strong> - {error['timestamp']}<br>
                {error['message']}
            </div>
"""
            html += "</div>"
        
        html += f"""
        <div class="card">
            <h2>[FILES] Log Files</h2>
            <p>Detailed logs are available in the session directory:</p>
            <p><code>{self.dirs['session']}</code></p>
            <div>
                <a href="../../agents/agents_{self.session_id}.log" class="log-link">Agent Logs</a>
                <a href="../../workflow/workflow_{self.session_id}.log" class="log-link">Workflow Logs</a>
                <a href="../../api/api_{self.session_id}.log" class="log-link">API Logs</a>
                <a href="../../performance/performance_{self.session_id}.log" class="log-link">Performance Logs</a>
                <a href="../../errors/errors_{self.session_id}.log" class="log-link">Error Logs</a>
            </div>
        </div>
        
        <div class="card">
            <p><small>Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Auto-refresh every 5 seconds</small></p>
        </div>
    </div>
</body>
</html>
"""
        return html


class TerminalFormatter(logging.Formatter):
    """Custom formatter for terminal output - only major events."""
    
    def format(self, record):
        # Add colors and emojis for different levels
        colors = {
            'DEBUG': '\033[36m',    # Cyan
            'INFO': '\033[32m',     # Green  
            'WARNING': '\033[33m',  # Yellow
            'ERROR': '\033[31m',    # Red
            'CRITICAL': '\033[35m'  # Magenta
        }
        
        emojis = {
            'DEBUG': '[DEBUG]',
            'INFO': '[INFO]', 
            'WARNING': '[WARN]',
            'ERROR': '[ERROR]',
            'CRITICAL': '[CRITICAL]'
        }
        
        color = colors.get(record.levelname, '')
        emoji = emojis.get(record.levelname, '[LOG]')
        reset = '\033[0m'
        
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')
        
        return f"{color}{emoji} [{timestamp}] {record.getMessage()}{reset}"


class DetailedFormatter(logging.Formatter):
    """Detailed formatter for file logging."""
    
    def format(self, record):
        return f"[{datetime.fromtimestamp(record.created).isoformat()}] [{record.levelname}] {record.getMessage()}"


# Global logging system instance
_logging_system = None

def get_logging_system() -> EnhancedLoggingSystem:
    """Get or create the global logging system."""
    global _logging_system
    if _logging_system is None:
        _logging_system = EnhancedLoggingSystem()
    return _logging_system

def log_terminal(level: str, message: str, category: str = "SYSTEM"):
    """Log major events to terminal."""
    get_logging_system().log_terminal(level, message, category)

def log_agent_activity(agent_name: str, message: str, level: str = "INFO", metadata: Dict[str, Any] = None):
    """Log agent activity with detailed logging."""
    system = get_logging_system()
    
    # Only log major events to terminal
    if level in ["ERROR", "WARNING"] or any(keyword in message.lower() for keyword in 
                                           ["starting", "completed", "failed", "generated", "validated"]):
        system.log_terminal(level, f"{agent_name}: {message}", "AGENT")
    
    # Always log detailed information to files
    system.log_detailed("agents", level, agent_name, message, metadata)

def log_workflow_event(message: str, level: str = "INFO", metadata: Dict[str, Any] = None):
    """Log workflow events."""
    system = get_logging_system()
    
    # Major workflow events to terminal
    if level in ["ERROR", "WARNING"] or any(keyword in message.lower() for keyword in 
                                           ["phase", "workflow", "starting", "completed", "failed"]):
        system.log_terminal(level, message, "WORKFLOW")
    
    # Detailed logging to files
    system.log_detailed("workflow", level, "WorkflowEngine", message, metadata)

def log_api_call(model: str, call_type: str, duration: float = 0.0, 
                success: bool = True, error_msg: str = "", metadata: Dict[str, Any] = None):
    """Log API calls."""
    system = get_logging_system()
    
    # Combine metadata
    full_metadata = {
        "model": model,
        "call_type": call_type,
        "duration": duration,
        "success": success,
        "error_msg": error_msg,
        **(metadata or {})
    }
    
    message = f"API call to {model} ({call_type}) - {duration:.2f}s"
    if not success:
        message += f" - ERROR: {error_msg}"
        level = "ERROR"
        # Log API errors to terminal
        system.log_terminal(level, message, "API")
    else:
        level = "INFO"
    
    # Always log to files
    system.log_detailed("api", level, "APIManager", message, full_metadata)

def log_performance(agent: str, metric: str, value: float, metadata: Dict[str, Any] = None):
    """Log performance metrics."""
    system = get_logging_system()
    
    full_metadata = {
        "metric": metric,
        "value": value,
        **(metadata or {})
    }
    
    message = f"Performance: {metric} = {value}"
    system.log_detailed("performance", "INFO", agent, message, full_metadata)

def log_error(agent: str, error_msg: str, metadata: Dict[str, Any] = None):
    """Log errors with special handling."""
    system = get_logging_system()
    
    # Always log errors to terminal
    system.log_terminal("ERROR", f"{agent}: {error_msg}", "ERROR")
    
    # Detailed error logging
    system.log_detailed("errors", "ERROR", agent, error_msg, metadata)

def get_dashboard_url() -> str:
    """Get the URL for the live dashboard."""
    system = get_logging_system()
    dashboard_file = system.dirs["dashboard"] / "live_dashboard.html"
    return f"file://{dashboard_file.absolute()}"

def print_logging_info():
    """Print information about logging setup."""
    system = get_logging_system()
    print("\n" + "="*70)
    print("[LOG] ENHANCED LOGGING SYSTEM ACTIVE")
    print("="*70)
    print(f"[FILES] Session Directory: {system.dirs['session']}")
    print(f"[DASHBOARD] Live Dashboard: {get_dashboard_url()}")
    print(f"[SESSION] Session ID: {system.session_id}")
    print("\n[CATEGORIES] Log Categories:")
    print(f"  • Agents: {system.dirs['agents']}")
    print(f"  • Workflow: {system.dirs['workflow']}")
    print(f"  • API Calls: {system.dirs['api']}")
    print(f"  • Performance: {system.dirs['performance']}")
    print(f"  • Errors: {system.dirs['errors']}")
    print(f"  • Dashboard: {system.dirs['dashboard']}")
    print("\n[INFO] Terminal shows only major events. Check files for detailed logs.")
    print("="*70 + "\n")

# Backward compatibility - Update monitoring.py functions to use new system
def log_global(message: str, level: str = "INFO"):
    """Global logging function for backward compatibility."""
    log_workflow_event(message, level)

# Enhanced Flow Visibility Functions (File-only logging to keep terminal clean)
def log_message_bus_flow(from_agent: str, to_agent: str, message_type: str, 
                        data_size: int = 0, metadata: Dict[str, Any] = None):
    """Log message bus communication flow between agents (file-only logging)."""
    flow_message = f"[MESSAGE BUS] {from_agent} -> {to_agent} | Type: {message_type} | Size: {data_size}B"
    
    # Only log to files - no terminal output to keep it clean
    get_logging_system().log_detailed(
        "workflow", "INFO", "MessageBus", flow_message,
        {
            "flow_type": "message_bus",
            "from_agent": from_agent,
            "to_agent": to_agent,
            "message_type": message_type,
            "data_size": data_size,
            **(metadata or {})
        }
    )

def log_rag_operation(operation: str, query_type: str, results_count: int = 0, 
                     processing_time: float = 0.0, metadata: Dict[str, Any] = None):
    """Log RAG system operations and performance (file-only logging)."""
    rag_message = f"[RAG] {operation} | Query: {query_type} | Results: {results_count} | Time: {processing_time:.2f}s"
    
    # Only log to files - no terminal output to keep it clean
    get_logging_system().log_detailed(
        "performance", "INFO", "RAGSystem", rag_message,
        {
            "flow_type": "rag_operation",
            "operation": operation,
            "query_type": query_type,
            "results_count": results_count,
            "processing_time": processing_time,
            **(metadata or {})
        }
    )

def log_memory_operation(operation: str, key: str, context: str = None, 
                        backend: str = "hybrid", success: bool = True, 
                        metadata: Dict[str, Any] = None):
    """Log enhanced memory system operations (file-only logging)."""
    memory_message = f"[MEMORY] {operation} | Key: {key} | Context: {context or 'default'} | Backend: {backend} | Success: {success}"
    
    # Only log failures to terminal, successes only to files
    if not success:
        log_terminal("ERROR", memory_message, "MEMORY")
    
    # Always log detailed information to files
    get_logging_system().log_detailed(
        "performance", "INFO", "EnhancedMemory", memory_message,
        {
            "flow_type": "memory_operation",
            "operation": operation,
            "key": key,
            "context": context,
            "backend": backend,
            "success": success,
            **(metadata or {})
        }
    )

def log_integration_flow(component_from: str, component_to: str, data_type: str, 
                        operation: str, success: bool = True, 
                        metadata: Dict[str, Any] = None):
    """Log integration flow between major system components (file-only logging)."""
    flow_message = f"[INTEGRATION] {component_from} -> {component_to} | Data: {data_type} | Op: {operation} | Success: {success}"
    
    # Only log failures to terminal, successes only to files
    if not success:
        log_terminal("ERROR", flow_message, "INTEGRATION")
    
    # Always log detailed information to files
    get_logging_system().log_detailed(
        "workflow", "INFO", "Integration", flow_message,
        {
            "flow_type": "integration",
            "component_from": component_from,
            "component_to": component_to,
            "data_type": data_type,
            "operation": operation,
            "success": success,
            **(metadata or {})
        }
    )

def log_agent_coordination(agent_name: str, coordination_type: str, target_agents: List[str] = None,
                          shared_data: str = None, metadata: Dict[str, Any] = None):
    """Log agent coordination activities (file-only logging)."""
    targets = ", ".join(target_agents) if target_agents else "broadcast"
    coord_message = f"[COORDINATION] {agent_name} | Type: {coordination_type} | Targets: {targets} | Data: {shared_data or 'none'}"
    
    # Only log to files - no terminal output to keep it clean
    get_logging_system().log_detailed(
        "agents", "INFO", agent_name, coord_message,
        {
            "flow_type": "agent_coordination",
            "coordination_type": coordination_type,
            "target_agents": target_agents or [],
            "shared_data": shared_data,
            **(metadata or {})
        }
    )

# Initialize the logging system when module is imported
if __name__ != "__main__":
    print_logging_info()
