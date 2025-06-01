import json
import logging
import traceback
from typing import Dict, Any, Optional, Callable
from functools import wraps
import monitoring

logger = logging.getLogger(__name__)

class AgentError(Exception):
    """Custom exception for agent-specific errors."""
    def __init__(self, agent_name: str, message: str, original_error: Exception = None):
        self.agent_name = agent_name
        self.message = message
        self.original_error = original_error
        super().__init__(f"{agent_name}: {message}")

class ValidationError(AgentError):
    """Exception for input validation failures."""
    pass

class LLMError(AgentError):
    """Exception for LLM-related failures."""
    pass

class ProcessingError(AgentError):
    """Exception for general processing failures."""
    pass

def agent_error_handler(agent_name: str, fallback_response: Optional[Dict[str, Any]] = None):
    """Decorator for consistent agent error handling with fallbacks."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
                
            except json.JSONDecodeError as e:
                error_msg = f"JSON parsing failed: {e}"
                monitoring.log_agent_activity(agent_name, error_msg, "ERROR")
                logger.error(f"{agent_name} JSON parsing error: {e}")
                
                if fallback_response:
                    return fallback_response
                return create_error_response(agent_name, error_msg)
                
            except ValidationError as e:
                error_msg = f"Input validation failed: {e.message}"
                monitoring.log_agent_activity(agent_name, error_msg, "ERROR")
                logger.error(f"{agent_name} validation error: {e}")
                
                if fallback_response:
                    return fallback_response
                return create_error_response(agent_name, error_msg)
                
            except LLMError as e:
                error_msg = f"LLM processing failed: {e.message}"
                monitoring.log_agent_activity(agent_name, error_msg, "ERROR")
                logger.error(f"{agent_name} LLM error: {e}")
                
                if fallback_response:
                    return fallback_response
                return create_error_response(agent_name, error_msg)
                
            except Exception as e:
                error_msg = f"Unexpected error: {str(e)}"
                monitoring.log_agent_activity(agent_name, error_msg, "ERROR")
                logger.error(f"{agent_name} unexpected error: {e}", exc_info=True)
                
                if fallback_response:
                    return fallback_response
                return create_error_response(agent_name, error_msg)
                
        return wrapper
    return decorator

def validate_agent_response(response: Dict[str, Any], required_keys: list, agent_name: str) -> bool:
    """Validates that agent response contains required keys."""
    missing_keys = [key for key in required_keys if key not in response]
    if missing_keys:
        error_msg = f"Response missing required keys: {missing_keys}"
        monitoring.log_agent_activity(agent_name, error_msg, "WARNING")
        logger.warning(f"{agent_name} {error_msg}")
        return False
    return True

def create_error_response(agent_name: str, error_message: str) -> Dict[str, Any]:
    """Creates standardized error response for failed agents."""
    return {
        "status": "error",
        "agent": agent_name,
        "error_message": error_message,
        "timestamp": monitoring.datetime.datetime.now().isoformat(),
        "success": False,
        "data": None
    }

def log_agent_performance(agent_name: str, start_time: float, success: bool = True):
    """Logs agent performance metrics."""
    duration = monitoring.time.time() - start_time
    status = "SUCCESS" if success else "FAILED"
    monitoring.log_agent_activity(
        agent_name, 
        f"Execution completed in {duration:.2f}s", 
        status
    )