"""
Enhanced monitoring system for the Multi-AI Development System.
Provides real-time tracking of API calls, agent activity, and performance metrics.
"""

# Define this at the top of the file with other imports
import datetime
import json
import time
import os
import threading
import sqlite3
import asyncio
import aiofiles
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Generator, Callable
from collections import defaultdict, Counter
from contextlib import contextmanager
from functools import wraps
import logging
import logging.handlers

# --- FIX: Add imports for Windows-safe logging ---
import sys
try:
    from utils.windows_safe_console import replace_emojis_with_text
    IS_WINDOWS = sys.platform.startswith('win')
except ImportError:
    # Fallback if the utility is not found
    def replace_emojis_with_text(text: str) -> str:
        return text
    IS_WINDOWS = False

# Base logs directory - consistent with MetricsCollector
LOG_DIR = Path("logs")

class SafeFormatter(logging.Formatter):
    """Custom logging formatter to handle Unicode characters on Windows."""
    def format(self, record):
        # First, format the message as usual
        message = super().format(record)
        # Then, replace emojis if on Windows
        if IS_WINDOWS:
            return replace_emojis_with_text(message)
        return message

def setup_logging(
    log_level: str = None,
    console_output: bool = True,
    file_logging: bool = True
):
    """
    Setup logging for the Multi-AI Development System.
    
    Args:
        log_level: Log level (QUIET, NORMAL, VERBOSE, DEBUG) or standard logging levels
        console_output: Whether to output logs to console
        file_logging: Whether to output logs to files
    """
    # Get log level from environment or parameter
    log_level = log_level or os.environ.get("LOG_LEVEL", "NORMAL")
    console_output = os.environ.get("CONSOLE_OUTPUT", "true").lower() == "true" if console_output is None else console_output
    file_logging = os.environ.get("FILE_LOGGING", "true").lower() == "true" if file_logging is None else file_logging
    
    # Convert custom log levels to standard levels
    level_mapping = {
        "QUIET": logging.WARNING,
        "NORMAL": logging.INFO,
        "VERBOSE": logging.DEBUG,
        "DEBUG": logging.DEBUG
    }
    
    # Get numerical level
    numeric_level = level_mapping.get(log_level.upper(), logging.INFO)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Clear existing handlers to avoid duplicate logs
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Define log format
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    # --- FIX: Use the new SafeFormatter ---
    formatter = SafeFormatter(log_format)
    
    # Add console handler if enabled
    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(numeric_level)
        root_logger.addHandler(console_handler)
    
    # Add file handler if enabled
    if file_logging:
        # Create logs directory
        log_dir = Path("logs/system")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Current date for log filename
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        log_file = log_dir / f"system_{current_date}.log"
        
        # Create rotating file handler for daily logs
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, 
            maxBytes=10*1024*1024,  # 10 MB
            backupCount=5
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(numeric_level)
        root_logger.addHandler(file_handler)
    
    # Log startup information
    logging.info(f"Logging initialized: level={log_level}, console={console_output}, file={file_logging}")
    
    return root_logger

# Initialize logging
setup_logging()

class AsyncMetricsCollector:
    """Enhanced async-compatible metrics collector for agent monitoring."""
    
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
        
        # Queue for async logging
        self._log_queue = asyncio.Queue()
        
        # Start log processor if running in async environment
        try:
            loop = asyncio.get_running_loop()
            asyncio.create_task(self._process_log_queue())
        except RuntimeError:
            # Not in an async context, will use sync methods
            pass
    
    def setup_logging_directories(self):
        """Create logging directories if they don't exist."""
        self.logs_dir = LOG_DIR
        self.api_logs_dir = self.logs_dir / "api_calls"
        self.agent_logs_dir = self.logs_dir / "agent_logs"
        self.workflow_logs_dir = self.logs_dir / "workflow"
        
        # Create dirs if they don't exist
        for directory in [self.logs_dir, self.api_logs_dir, self.agent_logs_dir, self.workflow_logs_dir]:
            directory.mkdir(exist_ok=True, parents=True)
    
    async def _process_log_queue(self):
        """Process log entries from the queue asynchronously."""
        while True:
            log_func, log_entry, log_dir, prefix = await self._log_queue.get()
            try:
                await log_func(log_entry, log_dir, prefix)
            except Exception as e:
                logging.error(f"Error processing log: {e}")
            finally:
                self._log_queue.task_done()
    
    async def _log_to_file_async(self, log_entry: Dict[str, Any], log_dir: Path, prefix: str):
        """Async method to log to a file with standardized format."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d")
        log_file = log_dir / f"{prefix}_{timestamp}.jsonl"
        
        try:
            async with aiofiles.open(log_file, "a") as f:
                await f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            logging.error(f"Failed to write async log: {e}")
    
    def _log_to_file_sync(self, log_entry: Dict[str, Any], log_dir: Path, prefix: str):
        """Synchronous method to log to a file when async is unavailable."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d")
        log_file = log_dir / f"{prefix}_{timestamp}.jsonl"
        
        try:
            with open(log_file, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            logging.error(f"Failed to write sync log: {e}")
    
    def log_entry(self, log_entry: Dict[str, Any], log_dir: Path, prefix: str):
        """Log an entry using async when possible, falling back to sync."""
        try:
            loop = asyncio.get_running_loop()
            # In async context, add to queue
            self._log_queue.put_nowait((self._log_to_file_async, log_entry, log_dir, prefix))
        except RuntimeError:
            # Not in async context, use sync method
            self._log_to_file_sync(log_entry, log_dir, prefix)

    # The rest of your existing methods with minimal changes to use the new log_entry method
    
    def increment_api_call(self, model_name: str):
        """Increment counter for specific model API call."""
        with self._lock:
            self.api_calls[model_name] += 1
    
    def increment_agent_activity(self, agent_name: str):
        """Increment counter for agent activity."""
        with self._lock:
            self.agent_activities[agent_name] += 1
    
    def log_api_call(self, log_entry: Dict[str, Any]):
        """Log API call details to file."""
        self.log_entry(log_entry, self.api_logs_dir, "api")
    
    def log_agent(self, log_entry: Dict[str, Any]):
        """Log agent activity to file."""
        self.log_entry(log_entry, self.agent_logs_dir, "agent")
    
    def log_workflow(self, log_entry: Dict[str, Any]):
        """Log workflow event to file."""
        self.log_entry(log_entry, self.workflow_logs_dir, "workflow")
    
    def get_summary_metrics(self) -> Dict[str, Any]:
        """Get summary metrics for reporting."""
        with self._lock:
            elapsed_time = time.time() - self.start_time
            return {
                "session_id": self.session_id,
                "elapsed_time": elapsed_time,
                "total_api_calls": sum(self.api_calls.values()),
                "api_calls_by_model": dict(self.api_calls),
                "agent_activities": dict(self.agent_activities),
                "total_errors": sum(self.errors.values()),
                "total_tokens": self.total_tokens,
                "total_cost": self.total_cost,
                "timestamp": datetime.datetime.now().isoformat()
            }
    
    async def save_metrics_to_file_async(self):
        """Save all metrics to a JSON file asynchronously."""
        metrics_file = self.logs_dir / f"metrics_{self.session_id}.json"
        
        try:
            async with aiofiles.open(metrics_file, "w") as f:
                await f.write(json.dumps(self.get_summary_metrics(), indent=2))
            logging.info(f"Metrics saved to {metrics_file}")
            
        except Exception as e:
            logging.error(f"Failed to save metrics: {e}")
    
    def save_metrics_to_file(self):
        """Save all metrics to a JSON file, attempting async if possible."""
        try:
            loop = asyncio.get_running_loop()
            asyncio.create_task(self.save_metrics_to_file_async())
        except RuntimeError:
            # Not in async context, use sync approach
            metrics_file = self.logs_dir / f"metrics_{self.session_id}.json"
            try:
                with open(metrics_file, "w") as f:
                    json.dump(self.get_summary_metrics(), f, indent=2)
                logging.info(f"Metrics saved to {metrics_file}")
            except Exception as e:
                logging.error(f"Failed to save metrics: {e}")

    async def shutdown(self):
        """Gracefully shut down the metrics collector."""
        # Wait for remaining logs to be processed
        if hasattr(self, '_log_queue'):
            await self._log_queue.join()
        
        # Save final metrics
        await self.save_metrics_to_file_async()

# Initialize metrics collector with async support
metrics_collector = AsyncMetricsCollector()

# Adapt your log functions to be async-compatible
async def log_api_call_realtime_async(
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
    """Async version of log_api_call_realtime"""
    log_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "session_id": metrics_collector.session_id,
        "model": model,
        "type": call_type,
        "input_preview": input_preview[:100] + "..." if len(input_preview) > 100 else input_preview,
        "output_preview": output_preview[:100] + "..." if len(output_preview) > 100 else output_preview,
        "duration": duration,
        "success": success,
        "error": error_msg if not success else "",
        "temperature": temperature,
        "agent_context": agent_context
    }
    
    metrics_collector.increment_api_call(model)
    await asyncio.to_thread(metrics_collector.log_api_call, log_entry)

# Sync version that delegates to async when possible
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
    """Log API call details in real-time, adapting to sync or async context."""
    log_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "session_id": metrics_collector.session_id,
        "model": model,
        "type": call_type,
        "input_preview": input_preview[:100] + "..." if len(input_preview) > 100 else input_preview,
        "output_preview": output_preview[:100] + "..." if len(output_preview) > 100 else output_preview,
        "duration": duration,
        "success": success,
        "error": error_msg if not success else "",
        "temperature": temperature,
        "agent_context": agent_context
    }
    
    metrics_collector.increment_api_call(model)
    metrics_collector.log_api_call(log_entry)

# Create async version of log_agent_activity
async def log_agent_activity_async(agent_name: str, message: str, level: str = "INFO", metadata: Optional[Dict[str, Any]] = None):
    """Log agent activity asynchronously."""
    log_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "session_id": metrics_collector.session_id,
        "agent": agent_name,
        "message": message,
        "level": level,
        "metadata": metadata or {}
    }
    
    metrics_collector.increment_agent_activity(agent_name)
    await asyncio.to_thread(metrics_collector.log_agent, log_entry)

# Regular version that adapts to async when possible
def log_agent_activity(agent_name: str, message: str, level: str = "INFO", metadata: Optional[Dict[str, Any]] = None):
    """Log agent activity with standardized format."""
    log_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "session_id": metrics_collector.session_id,
        "agent": agent_name,
        "message": message,
        "level": level,
        "metadata": metadata or {}
    }
    
    metrics_collector.increment_agent_activity(agent_name)
    metrics_collector.log_agent(log_entry)
    
    # Print to console for visibility using logger instead of print to avoid Unicode errors
    if level in ["ERROR", "WARNING", "SUCCESS"]:
        if level == "ERROR":
            logging.error(f"[{agent_name}] {message}")
        elif level == "WARNING":
            logging.warning(f"[{agent_name}] {message}")
        elif level == "SUCCESS":
            logging.info(f"[{agent_name}] {message}")

# Add the async version of SimpleTracer
class AsyncSimpleTracer:
    """Async-compatible tracer for workflow spans."""
    
    def __init__(self):
        self.spans = {}
    
    @contextmanager
    async def start_span_async(self, span_name: str, attributes: Dict[str, Any] = None) -> Generator:
        """Start a tracing span asynchronously."""
        span_id = f"span_{int(time.time() * 1000)}"
        start_time = time.time()
        
        await log_agent_activity_async(span_name, f"Starting span", "INFO", 
                           metadata={"span_id": span_id, **(attributes or {})})
        
        try:
            yield span_id
            duration = time.time() - start_time
            await log_agent_activity_async(span_name, f"Span completed in {duration:.2f}s", "INFO", 
                               metadata={"span_id": span_id, "duration": duration, **(attributes or {})})
        except Exception as e:
            # Log error in span
            duration = time.time() - start_time
            await log_agent_activity_async(span_name, f"Span failed after {duration:.2f}s: {str(e)}", "ERROR",
                               metadata={"span_id": span_id, "duration": duration, "error": str(e), **(attributes or {})})
            raise

# Maintain the original for backward compatibility
class SimpleTracer:
    """Simple tracer for workflow spans."""
    
    def __init__(self):
        self.spans = {}
    
    @contextmanager
    def start_span(self, span_name: str, attributes: Dict[str, Any] = None) -> Generator:
        """Start a tracing span, will use async when possible."""
        span_id = f"span_{int(time.time() * 1000)}"
        start_time = time.time()
        
        log_agent_activity(span_name, f"Starting span", "INFO", 
                           metadata={"span_id": span_id, **(attributes or {})})
        
        try:
            yield span_id
            duration = time.time() - start_time
            log_agent_activity(span_name, f"Span completed in {duration:.2f}s", "INFO", 
                               metadata={"span_id": span_id, "duration": duration, **(attributes or {})})
        except Exception as e:
            # Log error in span
            duration = time.time() - start_time
            log_agent_activity(span_name, f"Span failed after {duration:.2f}s: {str(e)}", "ERROR",
                               metadata={"span_id": span_id, "duration": duration, "error": str(e), **(attributes or {})})
            raise

# Add the tracer instance
tracer = SimpleTracer()
async_tracer = AsyncSimpleTracer()

# Update the async version of agent_trace_span
@contextmanager
async def agent_trace_span_async(agent_name: str, temperature: float, metadata: Optional[Dict[str, Any]] = None):
    """
    Async context manager for tracing agent execution with temperature metrics.
    
    Args:
        agent_name: Name of the agent (e.g., "BRD Analyst")
        temperature: Temperature setting for this agent (0.1-0.4)
        metadata: Additional metadata
    """
    # Create combined metadata with temperature information
    trace_metadata = {
        "agent_type": agent_name,
        "temperature": temperature,
        "temperature_category": _categorize_temperature(temperature),
        **(metadata or {})
    }
    
    async with async_tracer.start_span_async(
        span_name=f"{agent_name} Execution",
        attributes=trace_metadata
    ):
        yield

# Helper function for temperature categorization (following your temperature strategy)
def _categorize_temperature(temperature):
    """Categorize temperature value for monitoring."""
    # Convert to float if it's a string
    if isinstance(temperature, str):
        try:
            temperature = float(temperature)
        except ValueError:
            return "unknown"
    
    # Now do the comparisons
    if temperature <= 0.1:
        return "code_generation"
    elif temperature <= 0.2:
        return "analytical"
    elif temperature <= 0.4:
        return "creative"
    else:
        return "other"

# Update the sync version to adapt to async when possible
@contextmanager
def agent_trace_span(agent_name: str, temperature: float, metadata: Optional[Dict[str, Any]] = None):
    """
    Context manager for tracing agent execution with temperature metrics.
    Will use async when in an async context.
    
    Args:
        agent_name: Name of the agent (e.g., "BRD Analyst")
        temperature: Temperature setting for this agent (0.1-0.4)
        metadata: Additional metadata
    """
    # Try to detect if in async context and use appropriate implementation
    try:
        loop = asyncio.get_running_loop()
        # We're in an async context, but this is being called synchronously
        # Issue a gentle warning
        logging.debug(f"agent_trace_span called synchronously in async context. "
                     f"Consider using agent_trace_span_async for {agent_name}")
    except RuntimeError:
        # Not in async context, continue with sync approach
        pass
    
    # Create combined metadata with temperature information
    trace_metadata = {
        "agent_type": agent_name,
        "temperature": temperature,
        "temperature_category": _categorize_temperature(temperature),
        **(metadata or {})
    }
    
    with tracer.start_span(
        span_name=f"{agent_name} Execution",
        attributes=trace_metadata
    ):
        yield

def log_global(message: str, level: str = "INFO"):
    """
    Log a global system message with the specified level.
    
    Args:
        message: The message to log
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Use existing logging function with a system identifier
    log_agent_activity("System", message, level)

def track_json_parse_error(agent: str, error_type: str, position: int, 
                          snippet: str, model_name: str) -> None:
    """Track JSON parsing errors to identify patterns."""
    from datetime import datetime
    
    # Get the current JSON parsing error stats
    json_errors = get_json_parsing_stats()
    
    # Update position frequency counter
    position_key = f"position_{position}"
    json_errors["positions"][position_key] = json_errors["positions"].get(position_key, 0) + 1
    
    # Update agent frequency counter
    json_errors["agents"][agent] = json_errors["agents"].get(agent, 0) + 1
    
    # Update model frequency counter
    json_errors["models"][model_name] = json_errors["models"].get(model_name, 0) + 1
    
    # Store detailed error record
    json_errors["recent_errors"].append({
        "timestamp": datetime.now().isoformat(),
        "agent": agent,
        "error_type": error_type,
        "position": position,
        "snippet": snippet,
        "model": model_name
    })
    
    # Keep only last 100 errors
    json_errors["recent_errors"] = json_errors["recent_errors"][-100:]
    
    # Update total count
    json_errors["total_count"] += 1
    
    # Save updated stats
    _save_json_parsing_stats(json_errors)
    
    # Alert if this is a frequently occurring issue (same position)
    if json_errors["positions"][position_key] > 10:
        log_agent_activity("SYSTEM", 
                           f"Persistent JSON parsing error at position {position} detected ({json_errors['positions'][position_key]} occurrences)", 
                           "ALERT")

def get_json_parsing_stats():
    """Get the current JSON parsing error statistics."""
    import os
    import json
    
    stats_file = os.path.join(os.path.dirname(__file__), "data", "json_parse_errors.json")
    
    # Create default stats structure
    default_stats = {
        "total_count": 0,
        "positions": {},
        "agents": {},
        "models": {},
        "recent_errors": []
    }
    
    # Ensure data directory exists
    os.makedirs(os.path.dirname(stats_file), exist_ok=True)
    
    # Load existing stats if available
    try:
        if os.path.exists(stats_file):
            with open(stats_file, 'r') as f:
                return json.load(f)
    except Exception as e:
        log_agent_activity("SYSTEM", f"Error loading JSON parsing stats: {e}", "ERROR")
    
    return default_stats

def _save_json_parsing_stats(stats):
    """Save the updated JSON parsing error statistics."""
    import os
    import json
    
    stats_file = os.path.join(os.path.dirname(__file__), "data", "json_parse_errors.json")
    
    try:
        # Ensure data directory exists
        os.makedirs(os.path.dirname(stats_file), exist_ok=True)
        
        with open(stats_file, 'w') as f:
            json.dump(stats, f, indent=2)
    except Exception as e:
        log_agent_activity("SYSTEM", f"Error saving JSON parsing stats: {e}", "ERROR")

# Add API call tracking
class ApiCallMonitor:
    def __init__(self):
        self.call_count = 0
        self.call_times = []
        self.rate_warnings = 0
        
    def record_call(self):
        self.call_count += 1
        current_time = time.time()
        self.call_times.append(current_time)
        
        # Clean up old calls (older than 60 seconds)
        self.call_times = [t for t in self.call_times if current_time - t < 60]
        
        # Check if we're approaching the rate limit
        if len(self.call_times) > 50:  # 50 calls in last minute is getting close to limit
            self.rate_warnings += 1
            logging.warning(f"API call rate warning: {len(self.call_times)} calls in last minute")
            
    def get_stats(self):
        return {
            "total_calls": self.call_count,
            "calls_last_minute": len(self.call_times),
            "rate_warnings": self.rate_warnings
        }

# Initialize the monitor
api_monitor = ApiCallMonitor()