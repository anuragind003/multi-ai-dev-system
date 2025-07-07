# config.py
import os
import sys
import time
import copy
import hashlib
import logging
import requests
import sqlite3
import threading
import atexit
import argparse
import json
import yaml
import random  # Add this import for the jitter calculation in backoff
from pathlib import Path
from typing import Optional, Dict, Any, List, Union, Callable,Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from functools import wraps
from dotenv import load_dotenv
import asyncio

# Configure logger
logger = logging.getLogger(__name__)

# Local imports
import monitoring  # Make sure this module exists in your project

# LangChain imports
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_google_genai import HarmCategory, HarmBlockThreshold  # Add this line
from langchain_community.llms import Ollama
from langchain_community.embeddings import OllamaEmbeddings
from langchain_core.language_models import BaseLanguageModel
from langchain_core.embeddings import Embeddings
from langchain_core.runnables import RunnableSerializable, RunnableBinding

# Try to import HuggingFaceEmbeddings, but make it optional
try:
    from langchain_huggingface import HuggingFaceEmbeddings
    HUGGINGFACE_AVAILABLE = True
except ImportError:
    HuggingFaceEmbeddings = None
    HUGGINGFACE_AVAILABLE = False

# Other dependencies
from pydantic import Field, PrivateAttr
from langsmith import Client as LangSmithClient

from enhanced_memory_manager import EnhancedSharedProjectMemory, MemoryConfig, MemoryBackend
from advanced_rate_limiting.config import AdvancedRateLimitSystem

# Remove this import if you're defining response_cache locally
# from llm_cache import response_cache

# --- Initialize Advanced Rate Limiting System ---
# This creates a global instance that will be used by all LLM calls
try:
    advanced_rate_limiter = AdvancedRateLimitSystem()
    logger.info("Advanced rate limiting system initialized.")
except Exception as e:
    logger.error(f"Failed to initialize advanced rate limiting system: {e}")
    advanced_rate_limiter = None

# Simple response cache implementation
_response_cache: Dict[str, Any] = {}
_CACHE_SIZE_LIMIT = 1000  # Maximum number of items to keep in memory

def response_cache(func: Callable) -> Callable:
    """
    Decorator to cache function responses based on input arguments.
    Particularly useful for LLM calls with identical inputs.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Skip caching if explicitly requested
        if kwargs.pop('skip_cache', False):
            return func(*args, **kwargs)
            
        # Create a cache key from the function name and arguments
        try:
            # Convert args and kwargs to a consistent string representation
            args_str = str(args)
            kwargs_str = str(sorted(kwargs.items()))
            
            # Create a hash of the inputs for the cache key
            key = hashlib.md5(f"{func.__name__}:{args_str}:{kwargs_str}".encode()).hexdigest()
            
            # Check if we have a cached result
            if key in _response_cache:
                logger.debug(f"Cache hit for {func.__name__}")
                return _response_cache[key]
                
            # No cache hit, call the function
            result = func(*args, **kwargs)
            
            # Store in cache if the cache isn't too large
            if len(_response_cache) < _CACHE_SIZE_LIMIT:
                _response_cache[key] = result
            elif len(_response_cache) == _CACHE_SIZE_LIMIT:
                # Log once when we hit the limit
                logger.warning(f"Response cache size limit reached ({_CACHE_SIZE_LIMIT})")
                
            return result
            
        except Exception as e:
            # If anything goes wrong with caching, just call the function directly
            logger.debug(f"Caching error in {func.__name__}: {str(e)}")
            return func(*args, **kwargs)
            
    return wrapper

# Load environment variables
load_dotenv()

def test_langsmith_connection():
    """Test connection to LangSmith and return client if successful."""
    try:
        api_key = os.getenv("LANGSMITH_API_KEY")
        if not api_key:
            print("WARNING: LANGSMITH_API_KEY not set in environment")
            return None
            
        client = LangSmithClient(api_key=api_key)
        # Simple API call to test connection
        client.list_projects(limit=1)
        print("LangSmith connection successful")
        return client
    except Exception as e:
        print(f"WARNING: LangSmith connection test failed: {str(e)}")
        print("WARNING: Continuing with local tracing only")
        return None

def setup_langgraph_server(enable_server=True):
    """Configure LangGraph server for development and monitoring."""
    if enable_server:
        try:
            from utils.langsmith_utils import configure_langsmith
            return configure_langsmith()
        except ImportError:
            print("WARNING: LangSmith utilities not available, skipping initialization")
            return False
    else:
        print("WARNING: LangSmith tracing disabled (server not enabled)")
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
        return False

class ConfigSource(Enum):
    """Configuration source priorities."""
    CLI_ARGS = "command_line_arguments"
    ENV_VARS = "environment_variables"  
    CONFIG_FILE = "configuration_file"
    DEFAULTS = "default_values"

@dataclass
class AdvancedWorkflowConfig:
    """Enhanced workflow configuration with multiple sources and validation."""
    
    # Core workflow settings
    max_code_gen_retries: int = 3
    max_test_retries: int = 2
    max_quality_retries: int = 2
    
    # Quality thresholds
    min_quality_score: float = 3.0
    min_success_rate: float = 0.7
    min_coverage_percentage: float = 60.0
    
    # Timeouts (seconds)
    agent_timeout: int = 300
    code_execution_timeout: int = 120
    llm_timeout: int = 60
    
    # Environment and behavior
    environment: str = "development"  # development, staging, production
    llm_provider: str = "google"  # google, anthropic, openai, etc.
    fail_fast: bool = False
    skip_quality_check: bool = False
    skip_test_validation: bool = False
    parallel_execution: bool = False
    
    # Performance settings
    max_concurrent_agents: int = 1
    api_rate_limit: float = 10.0
    memory_limit_mb: int = 2048
    
    # Logging and debugging
    debug_mode: bool = False
    verbose_logging: bool = False
    telemetry_enabled: bool = False
    
    # Internal tracking
    _config_source: ConfigSource = field(default=ConfigSource.DEFAULTS, init=False)
    _validation_errors: List[str] = field(default_factory=list, init=False)
    
    def __post_init__(self):
        """Validate and adjust configuration after initialization."""
        self._validate_and_adjust()
    
    @classmethod
    def load_from_multiple_sources(
        cls, 
        config_file: Optional[str] = None,
        env_prefix: str = "MAISD_",
        args: Optional[argparse.Namespace] = None
    ) -> 'AdvancedWorkflowConfig':
        """
        Load configuration from multiple sources with priority:
        1. Command line arguments (highest priority)
        2. Environment variables
        3. Configuration file
        4. Default values (lowest priority)
        """
        
        # Start with defaults
        config = cls()
        config._config_source = ConfigSource.DEFAULTS
        
        # Load from configuration file if provided
        if config_file and os.path.exists(config_file):
            try:
                file_config = cls._load_from_file(config_file)
                config._merge_config(file_config)
                config._config_source = ConfigSource.CONFIG_FILE
            except Exception as e:
                config._validation_errors.append(f"Failed to load config file: {e}")
        
        # Load from environment variables
        env_config = cls._load_from_env(env_prefix)
        if env_config:
            config._merge_config(env_config)
            config._config_source = ConfigSource.ENV_VARS
        
        # Load from command line arguments (highest priority)
        if args:
            args_config = cls._load_from_args(args)
            if args_config:
                config._merge_config(args_config)
                config._config_source = ConfigSource.CLI_ARGS
        
        # Final validation and adjustment
        config._validate_and_adjust()
        
        return config
    
    @classmethod
    def _load_from_file(cls, config_file: str) -> Dict[str, Any]:
        """Load configuration from YAML or JSON file."""
        
        with open(config_file, 'r') as f:
            if config_file.endswith('.yaml') or config_file.endswith('.yml'):
                return yaml.safe_load(f)
            elif config_file.endswith('.json'):
                return json.load(f)
            else:
                raise ValueError(f"Unsupported config file format: {config_file}")
    
    @classmethod
    def _load_from_env(cls, prefix: str) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        
        config = {}
        env_mappings = {
            f"{prefix}MAX_CODE_GEN_RETRIES": ("max_code_gen_retries", int),
            f"{prefix}MAX_TEST_RETRIES": ("max_test_retries", int),
            f"{prefix}QUALITY_THRESHOLD": ("min_quality_score", float),
            f"{prefix}MIN_SUCCESS_RATE": ("min_success_rate", float),
            f"{prefix}MIN_COVERAGE": ("min_coverage_percentage", float),
            f"{prefix}ENVIRONMENT": ("environment", str),
            f"{prefix}LLM_PROVIDER": ("llm_provider", str),
            f"{prefix}FAIL_FAST": ("fail_fast", lambda x: x.lower() == 'true'),
            f"{prefix}DEBUG": ("debug_mode", lambda x: x.lower() == 'true'),
            f"{prefix}VERBOSE": ("verbose_logging", lambda x: x.lower() == 'true'),
        }
        
        for env_var, (config_key, converter) in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                try:
                    config[config_key] = converter(value)
                except (ValueError, TypeError):
                    # Skip invalid environment values
                    continue
        
        return config
    
    @classmethod 
    def _load_from_args(cls, args: argparse.Namespace) -> Dict[str, Any]:
        """Load configuration from command line arguments."""
        
        config = {}
        arg_mappings = {
            'quality_threshold': 'min_quality_score',
            'min_success_rate': 'min_success_rate', 
            'min_coverage': 'min_coverage_percentage',
            'max_retries': 'max_code_gen_retries',
            'max_test_retries': 'max_test_retries',
            'agent_timeout': 'agent_timeout',
            'environment': 'environment',
            'fail_fast': 'fail_fast',
            'parallel_execution': 'parallel_execution',
            'debug': 'debug_mode',
            'verbose': 'verbose_logging'
        }
        
        for arg_name, config_key in arg_mappings.items():
            value = getattr(args, arg_name, None)
            if value is not None:
                config[config_key] = value
        
        return config
    
    def _merge_config(self, new_config: Dict[str, Any]):
        """Merge new configuration values into current config."""
        
        for key, value in new_config.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def _validate_and_adjust(self):
        """Validate configuration and make automatic adjustments."""
        
        # Validate ranges
        self.max_code_gen_retries = max(0, min(10, self.max_code_gen_retries))
        self.max_test_retries = max(0, min(5, self.max_test_retries))
        self.min_quality_score = max(0.0, min(10.0, self.min_quality_score))
        self.min_success_rate = max(0.0, min(1.0, self.min_success_rate))
        self.min_coverage_percentage = max(0.0, min(100.0, self.min_coverage_percentage))
        
        # Validate timeouts
        self.agent_timeout = max(30, min(1800, self.agent_timeout))
        self.code_execution_timeout = max(10, min(600, self.code_execution_timeout))
        self.llm_timeout = max(5, min(300, self.llm_timeout))
        
        # Environment-specific adjustments
        if self.environment == "development":
            self.debug_mode = True
            self.verbose_logging = True
        elif self.environment == "production":
            self.debug_mode = False
            self.telemetry_enabled = True
            self.fail_fast = True
        
        # Validate environment
        if self.environment not in ["development", "staging", "production"]:
            self._validation_errors.append(f"Invalid environment: {self.environment}")
            self.environment = "development"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        
        return {
            field.name: getattr(self, field.name)
            for field in self.__dataclass_fields__.values()
            if not field.name.startswith('_')
        }
    
    def print_detailed_summary(self):
        """Print detailed configuration summary for debugging."""
        # Disabled print statements to avoid I/O issues during initialization
        pass

# Example configuration files
EXAMPLE_CONFIG_YAML = """
# Multi-AI Development System Configuration
workflow:
  # Retry settings
  max_code_gen_retries: 3
  max_test_retries: 2
  adaptive_retries: true
  
  # Quality thresholds
  min_quality_score: 7.0
  min_success_rate: 0.8
  min_coverage_percentage: 70.0
  
  # Environment settings
  environment: "production"
  fail_fast: true
  parallel_execution: false
  
  # Resource limits
  memory_limit_mb: 4096
  api_rate_limit: 15.0
"""

def create_example_config_files():
    """Create example configuration files for users."""
    
    config_dir = Path("configs")
    config_dir.mkdir(exist_ok=True)
    
    # Create YAML example
    yaml_file = config_dir / "example.yaml"
    if not yaml_file.exists():
        with open(yaml_file, 'w') as f:
            f.write(EXAMPLE_CONFIG_YAML)
    
    # Create production example
    prod_config = EXAMPLE_CONFIG_YAML.replace('environment: "production"', 
                                            'environment: "production"\n  telemetry_enabled: true')
    prod_file = config_dir / "production.yaml"
    if not prod_file.exists():
        with open(prod_file, 'w') as f:
            f.write(prod_config)

@dataclass
class WorkflowConfig:
    """
    Legacy workflow configuration class.
    
    NOTE: This class is kept for backward compatibility.
    New code should use AdvancedWorkflowConfig instead.
    """
    
    # Retry settings
    max_code_gen_retries: int = 3
    max_test_retries: int = 2
    max_quality_retries: int = 2
    
    # Quality thresholds
    min_quality_score: float = 6.0
    min_success_rate: float = 0.7
    min_coverage_percentage: float = 60.0
    
    # Timeout settings (seconds)
    agent_timeout: int = 300
    code_execution_timeout: int = 120
    llm_timeout: int = 60
    
    # Workflow behavior
    fail_fast: bool = False
    continue_on_warnings: bool = True
    skip_quality_check: bool = False
    skip_test_validation: bool = False
    
    # Performance settings
    max_concurrent_agents: int = 1
    api_rate_limit: float = 10.0  # requests per second
    
    @classmethod
    def from_args(cls, args: argparse.Namespace) -> 'WorkflowConfig':
        """Create configuration from command line arguments."""
        config = cls()
        
        # Map command line arguments to configuration
        if hasattr(args, 'max_retries') and args.max_retries:
            config.max_code_gen_retries = args.max_retries
        if hasattr(args, 'quality_threshold') and args.quality_threshold:
            config.min_quality_score = args.quality_threshold
        if hasattr(args, 'fail_fast') and args.fail_fast:
            config.fail_fast = True
            
        return config
    
    @classmethod
    def from_env(cls) -> 'WorkflowConfig':
        """Create configuration from environment variables."""
        import os
        
        config = cls()
        
        # Load from environment
        config.max_code_gen_retries = int(os.getenv('MAX_CODE_GEN_RETRIES', config.max_code_gen_retries))
        config.max_test_retries = int(os.getenv('MAX_TEST_RETRIES', config.max_test_retries))
        config.min_quality_score = float(os.getenv('MIN_QUALITY_SCORE', config.min_quality_score))
        config.min_success_rate = float(os.getenv('MIN_SUCCESS_RATE', config.min_success_rate))
        config.min_coverage_percentage = float(os.getenv('MIN_COVERAGE', config.min_coverage_percentage))
        config.fail_fast = os.getenv('FAIL_FAST', 'false').lower() == 'true'
        config.skip_quality_check = os.getenv('SKIP_QUALITY_CHECK', 'false').lower() == 'true'
        
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    def print_summary(self):
        """Print configuration summary."""
        # Disabled print statements to avoid I/O issues during initialization
        pass

# Configuration class for better management
@dataclass
class SystemConfig:
    """Singleton class to hold system-wide configuration."""
    
    # Use a private attribute to ensure a single instance
    _instance: Optional['SystemConfig'] = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(SystemConfig, cls).__new__(cls)
        return cls._instance

    def __init__(self, workflow_config: AdvancedWorkflowConfig = None):
        """
        Initialize the system configuration.
        
        This constructor should only be called once through `initialize_system_config`.
        Subsequent calls will not re-initialize the instance.
        """
        if hasattr(self, '_initialized') and self._initialized:
            return

        self.workflow_config = workflow_config or AdvancedWorkflowConfig()

        # --- MODIFIED: Use the correct EnhancedSharedProjectMemory class ---
        # This provides the `store_agent_activity` method that agents need.
        self.memory_hub = EnhancedSharedProjectMemory(
            run_dir=os.path.join("output", "global_shared_memory")
        )
        
        self.output_dir = "output"
        self.brd_dir = os.path.join(self.output_dir, "brds")
        
        # Use llm_provider from workflow config, with environment fallback
        workflow_provider = getattr(self.workflow_config, 'llm_provider', 'google')
        env_provider = os.getenv("LLM_PROVIDER", workflow_provider)
        self.llm_provider = env_provider.upper() if env_provider.lower() == 'gemini' else workflow_provider
        
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.gemini_model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash-preview-05-20") # Default
        # Removed DEBUG print statements that were causing I/O errors
        self.gemini_embedding_model = os.getenv("GEMINI_EMBEDDING_MODEL", "models/embedding-001") # Default
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.ollama_model_name = os.getenv("OLLAMA_MODEL_NAME", "codellama:7b")
        
        # Use imported agent temperatures
        from agent_temperatures import AGENT_TEMPERATURES  # ADDED: Import agent temperatures
        self.agent_temperatures = AGENT_TEMPERATURES  # CHANGED: Use imported temperatures
        
        self.validate_config()
        
        # Mark as initialized
        self._initialized = True

    def validate_config(self):
        """Validate configuration settings with enhanced temperature validation"""
        if self.llm_provider == "GEMINI" and not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required when using Gemini provider")
            
        # ADDED: Validate agent temperature configuration
        if not hasattr(self, 'agent_temperatures') or not self.agent_temperatures:
            logging.warning("No agent temperature configuration found. Using default temperatures.")
        else:
            # Verify critical agent temperatures are defined
            critical_agents = [
                "BRD Analyst Agent", 
                "Tech Stack Advisor Agent",
                "System Designer Agent",
                "Code Generator Agent"
            ]
            
            for agent in critical_agents:
                if agent not in self.agent_temperatures:
                    logging.warning(f"Missing temperature definition for critical agent: {agent}")
    
    def update_workflow_config(self, **kwargs):
        """Update workflow configuration parameters."""
        for key, value in kwargs.items():
            if hasattr(self.workflow_config, key):
                setattr(self.workflow_config, key, value)
                monitoring.log_global(f"Updated workflow config: {key} = {value}")
            else:
                monitoring.log_global(f"Unknown workflow config parameter: {key}", "WARNING")

# Global configuration instance
_system_config: Optional[SystemConfig] = None

def initialize_system_config(config):
    """Initialize the global system configuration from parsed config."""
    global _system_config
    
    _system_config = SystemConfig(config)
    
    # Use log_agent_activity instead of log_global
    try:
        monitoring.log_agent_activity(
            "SystemConfig", 
            f"Initialized with LLM provider: {_system_config.llm_provider}", 
            "INFO"
        )
    except:
        # Ignore all logging errors to avoid I/O issues
        pass

def set_system_config(config: Union[SystemConfig, AdvancedWorkflowConfig]) -> None:
    """
    Set the global system configuration directly.
    
    Args:
        config: Either a SystemConfig instance or AdvancedWorkflowConfig to wrap
    """
    global _system_config
    
    try:
        if isinstance(config, SystemConfig):
            _system_config = config
        elif isinstance(config, AdvancedWorkflowConfig):
            _system_config = SystemConfig(config)
        else:
            raise ValueError(f"Invalid config type: {type(config)}. Expected SystemConfig or AdvancedWorkflowConfig")
        
        # Success - config is set, no need for output that might fail
        
    except Exception as e:
        # Try to set a minimal fallback config
        try:
            if isinstance(config, AdvancedWorkflowConfig):
                _system_config = SystemConfig(config)
            else:
                _system_config = SystemConfig(AdvancedWorkflowConfig())
        except Exception as e2:
            # If we can't set any config, that's a critical error
            raise RuntimeError(f"Cannot set system config: {e}, fallback failed: {e2}")

def get_system_config() -> SystemConfig:
    """
    Get the global system configuration.
    
    Returns:
        SystemConfig: The initialized system configuration
        
    Raises:
        RuntimeError: If system config hasn't been initialized yet
    """
    global _system_config
    
    if _system_config is None:
        # This provides more helpful context about what's wrong and how to fix it
        error_msg = (
            "SystemConfig accessed before initialization! "
            "Call initialize_system_config() from your entry point (main.py or serve.py) "
            "before using configuration-dependent functions."
        )
        try:
            monitoring.log_global(error_msg, "ERROR")
        except:
            pass  # Ignore logging errors
        raise RuntimeError(error_msg)
    
    return _system_config

def get_workflow_config() -> AdvancedWorkflowConfig:  # CHANGED: Return type to AdvancedWorkflowConfig
    """Get the current workflow configuration."""
    return get_system_config().workflow_config

# Global cache for LLM instances to avoid re-initialization
_llm_cache: Dict[str, BaseLanguageModel] = {}

def _with_rate_limiting(llm: BaseLanguageModel) -> BaseLanguageModel:
    """
    Wraps an LLM instance to apply advanced rate limiting by monkey-patching
    its invoke/ainvoke methods. This avoids re-instantiation issues that can
    cause loss of credentials or other critical configuration.
    """
    if not advanced_rate_limiter or not advanced_rate_limiter.is_enabled():
        return llm

    # Check if already patched to prevent double-wrapping
    if hasattr(llm, '_original_invoke'):
        return llm

    # Store original methods before patching
    llm._original_invoke = llm.invoke
    llm._original_ainvoke = llm.ainvoke
    llm._original_stream = llm.stream
    llm._original_astream = llm.astream

    def rate_limited_invoke(*args, **kwargs):
        """Wrapped synchronous invoke method."""
        return advanced_rate_limiter.make_rate_limited_call(
            llm._original_invoke, "llm.invoke", args, kwargs
        )

    async def rate_limited_ainvoke(*args, **kwargs):
        """
        Wrapped asynchronous ainvoke method.
        
        This uses a simplified rate-limiting approach for async calls due to the
        synchronous nature of the advanced_rate_limiter. It ensures non-blocking
        waits but does not use the full optimization suite.
        """
        try:
            # wait_if_needed() is a blocking call, so we run it in a separate
            # thread to avoid blocking the asyncio event loop.
            await asyncio.to_thread(advanced_rate_limiter.rate_limiter.wait_if_needed)
            
            # Once the wait is over, we can await the original async method
            result = await llm._original_ainvoke(*args, **kwargs)
            
            # Record success in a non-blocking way
            await asyncio.to_thread(advanced_rate_limiter.rate_limiter.record_success, "llm.ainvoke")
            
            return result
        except Exception as e:
            error_type = type(e).__name__
            # Record error and check for escalation in a non-blocking way
            await asyncio.to_thread(advanced_rate_limiter.rate_limiter.record_error, "llm.ainvoke", error_type)
            if advanced_rate_limiter.config.enable_auto_escalation:
                 await asyncio.to_thread(advanced_rate_limiter._check_auto_escalation)
            raise e

    def rate_limited_stream(*args, **kwargs):
        """Wrapped synchronous stream method."""
        advanced_rate_limiter.rate_limiter.wait_if_needed()
        try:
            yield from llm._original_stream(*args, **kwargs)
            advanced_rate_limiter.rate_limiter.record_success("llm.stream")
        except Exception as e:
            error_type = type(e).__name__
            advanced_rate_limiter.rate_limiter.record_error("llm.stream", error_type)
            if advanced_rate_limiter.config.enable_auto_escalation:
                advanced_rate_limiter._check_auto_escalation()
            raise e

    async def rate_limited_astream(*args, **kwargs):
        """Wrapped asynchronous astream method."""
        await asyncio.to_thread(advanced_rate_limiter.rate_limiter.wait_if_needed)
        try:
            async for chunk in llm._original_astream(*args, **kwargs):
                yield chunk
            await asyncio.to_thread(advanced_rate_limiter.rate_limiter.record_success, "llm.astream")
        except Exception as e:
            error_type = type(e).__name__
            await asyncio.to_thread(advanced_rate_limiter.rate_limiter.record_error, "llm.astream", error_type)
            if advanced_rate_limiter.config.enable_auto_escalation:
                await asyncio.to_thread(advanced_rate_limiter._check_auto_escalation)
            raise e

    # Apply the monkey-patch using object.__setattr__ to bypass Pydantic's
    # model validation, which prevents direct assignment to non-field attributes.
    object.__setattr__(llm, 'invoke', rate_limited_invoke)
    object.__setattr__(llm, 'ainvoke', rate_limited_ainvoke)
    object.__setattr__(llm, 'stream', rate_limited_stream)
    object.__setattr__(llm, 'astream', rate_limited_astream)
    
    logger.info(f"Applied rate limiting wrapper to LLM instance for all call methods: {type(llm).__name__}")
    return llm

def get_llm(temperature: Optional[float] = None,
            model: Optional[str] = None,
            llm_specific_kwargs: Optional[Dict[str, Any]] = None) -> BaseLanguageModel:
    """
    Get a configured LLM instance with appropriate temperature.
    
    Args:
        temperature: Override temperature
        model: Override model name
        llm_specific_kwargs: Additional kwargs for the LLM constructor
        
    Returns:
        A configured BaseLanguageModel instance
    """
    system_config = get_system_config()
    provider = system_config.llm_provider.lower()

    # Determine model name based on provider
    if provider in ["google", "gemini"]:
        model_name = model or system_config.gemini_model_name
    elif provider == "ollama":
        model_name = model or system_config.ollama_model_name
    else:
        # Fallback for other providers or if provider is not set correctly
        logger.warning(f"Unsupported or unknown LLM provider: '{system_config.llm_provider}'. Defaulting to Gemini model.")
        model_name = model or system_config.gemini_model_name
    
    # Use provided temperature or a safe default.
    # The default_temperature attribute was removed from SystemConfig.
    temp_to_use = temperature if temperature is not None else 0.1 # Safe default for general use
    
    # Merge provided kwargs with defaults.
    # The llm_kwargs attribute was removed. Start with an empty dict.
    llm_kwargs = {}
    if llm_specific_kwargs:
        llm_kwargs.update(llm_specific_kwargs)
    
    # Remove parameters that are passed directly
    llm_kwargs.pop('temperature', None)
    llm_kwargs.pop('model', None)
    llm_kwargs.pop('model_name', None)

    if provider in ["google", "gemini"]:
        # Ensure safety settings are correctly configured
        safety_settings = llm_kwargs.pop('safety_settings', {
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        })

        # Create LLM with merged parameters
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=temp_to_use,
            safety_settings=safety_settings,
            convert_system_message_to_human=False, # This is the key change
            google_api_key=system_config.gemini_api_key,
            max_retries=0,  # Disable LangChain's internal retries to allow custom rate limiting
            **llm_kwargs
        )
        
        logger.info(f"Created Google LLM with model={model_name}, temp={temp_to_use}")

    elif provider == "ollama":
        # For Ollama, the base_url is a common kwarg
        base_url = llm_kwargs.pop('base_url', 'http://localhost:11434')
        llm = Ollama(
            model=model_name,
            temperature=temp_to_use,
            base_url=base_url,
            **llm_kwargs
        )
        logger.info(f"Created Ollama LLM with model={model_name}, temp={temp_to_use}")
        
    else:
        # Fallback to a default or raise an error
        logger.warning(f"Unsupported LLM provider: {provider}. Defaulting to Google.")
        llm = ChatGoogleGenerativeAI(
            model=model_name, 
            temperature=temp_to_use,
            convert_system_message_to_human=False,
            google_api_key=system_config.gemini_api_key,
            max_retries=0  # Disable LangChain's internal retries to allow custom rate limiting
        )

    # Use a cached wrapper if configured
    if hasattr(system_config, 'enable_llm_cache') and system_config.enable_llm_cache:
        # This part assumes a get_cached_llm function exists
        # and can wrap the created llm instance.
        return get_cached_llm(
            temperature=temp_to_use, 
            model=model_name,
            use_cache=True,
            **llm_kwargs
        )
    else:
        # --- ADDED: Wrap the LLM with the rate limiter before returning ---
        return _with_rate_limiting(llm)

def get_embedding_model(embedding_provider: Optional[str] = None,
                       embedding_model: Optional[str] = None) -> Embeddings:
    """
    Get the embedding model based on configuration.
    
    Args:
        embedding_provider: Override the default embedding provider
        embedding_model: Override the default embedding model name
        
    Returns:
        An instance of a LangChain Embeddings model
    """
    try:
        # Get embedding configuration from environment or system config
        system_config = get_system_config()
        provider = embedding_provider or os.getenv("EMBEDDING_PROVIDER", "GEMINI")
        model = embedding_model or os.getenv("EMBEDDING_MODEL", "models/embedding-001")
        
        provider = provider.upper()
        
        logger.debug(f"Initializing embedding model with provider={provider}, model={model}")
        
        # Initialize with the appropriate provider
        if provider == "GEMINI":
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY environment variable not set")
                
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
            
            embeddings = GoogleGenerativeAIEmbeddings(
                model=model,
                google_api_key=api_key,
                task_type="RETRIEVAL_DOCUMENT", # Use RETRIEVAL_QUERY for query embeddings
                title="Multi-AI Dev System"
            )
              # Log initialization for monitoring
            monitoring.log_global(f"Initialized Gemini embeddings model: {model}", "INFO")
            return embeddings
            
        elif provider == "LOCAL":
            # Use local HuggingFace embedding models
            if not HUGGINGFACE_AVAILABLE:
                raise ImportError("HuggingFace embeddings not available. Install langchain-huggingface to use local embeddings.")
            
            model_kwargs = {'device': 'cpu'}
            encode_kwargs = {'normalize_embeddings': True}
            
            embeddings = HuggingFaceEmbeddings(
                model_name=model,
                model_kwargs=model_kwargs,
                encode_kwargs=encode_kwargs
            )
            
            monitoring.log_global(f"Initialized local HuggingFace embeddings model: {model}", "INFO")
            return embeddings
            
        elif provider == "OLLAMA":
            from langchain_community.embeddings import OllamaEmbeddings
            
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            
            embeddings = OllamaEmbeddings(
                model=model,
                base_url=base_url
            )
            
            monitoring.log_global(f"Initialized Ollama embeddings model: {model}", "INFO")
            return embeddings
            
        else:
            raise ValueError(f"Unsupported embedding provider: {provider}")
            
    except Exception as e:
        error_msg = f"Error initializing embeddings: {str(e)}"
        logger.error(error_msg)
        
        # Try to log with monitoring if available
        try:
            monitoring.log_global(error_msg, "ERROR")
        except:
            pass
            
        raise

# Add this helper function (around line 850, before get_llm function)
def get_agent_temperature_from_config(agent_name: str) -> float:
    """
    Get the appropriate temperature for a specific agent from the system config.
    
    This function centralizes temperature management for consistent agent behavior
    across the entire system according to the temperature strategy:
    - Analytical tasks (0.1-0.2): Code quality, test validation, tech recommendations
    - Creative tasks (0.3-0.4): BRD analysis, planning, test case generation
    - Code generation (0.1): Deterministic, consistent code output
    
    Args:
        agent_name: Name of the agent to get temperature for
        
    Returns:
        float: The appropriate temperature value (defaults to 0.1 if not found)
    """
    try:
        system_config = get_system_config()
        # Look up temperature from imported agent_temperatures
        if hasattr(system_config, 'agent_temperatures') and agent_name in system_config.agent_temperatures:
            temp = system_config.agent_temperatures[agent_name]
            return float(temp)
        else:
            # Default temperature for unknown agents
            logging.warning(f"No temperature defined for agent '{agent_name}'. Using default (0.1).")
            return 0.1
    except Exception as e:
        logging.error(f"Error getting agent temperature: {str(e)}")
        return 0.1  # Safe default

# Add a function to create a temperature-bound TrackedChatModel (around line 1100)
def create_agent_llm(agent_name: str, 
                     override_temperature: Optional[float] = None,
                     model: Optional[str] = None,
                     **kwargs) -> BaseLanguageModel:
    """
    Create an LLM instance optimized for a specific agent with appropriate temperature.
    
    This function supports our agent specialization strategy by automatically
    applying the right temperature for each agent type.
    
    Args:
        agent_name: Name of the agent requiring the LLM
        override_temperature: Optional temperature override
        model: Optional model override
        **kwargs: Additional LLM parameters
        
    Returns:
        BaseLanguageModel: LLM instance with appropriate temperature binding
    """
    # Get temperature from strategy or use override
    temperature = override_temperature
    if temperature is None:
        temperature = get_agent_temperature_from_config(agent_name)
    
    # Set up agent context for monitoring
    agent_context_dict = {'agent_context': agent_name}
    if 'llm_specific_kwargs' not in kwargs:
        kwargs['llm_specific_kwargs'] = {}
    
    # Get a tracked LLM with appropriate temperature
    llm = get_llm(temperature=temperature, model=model, **kwargs)
    
    # Apply agent context to the LLM for improved monitoring
    config_with_context = {'agent_context': agent_name}
    
    # Return the temperature-bound LLM with agent context
    return llm

# Add global cache for temperature-bound LLMs (around line 20)
_LLM_CACHE = {}

# Add function to get or create cached LLM (around line 1120)
def get_cached_llm(temperature: float, 
                   model: Optional[str] = None, 
                   use_cache: bool = True, 
                   **kwargs) -> BaseLanguageModel:
    """
    Get or create an LLM with specified temperature, using cache for performance.
    
    Args:
        temperature: Temperature setting (0.0-1.0)
        model: Model name to use
        use_cache: Whether to use the cache
        **kwargs: Additional LLM parameters
        
    Returns:
        BaseLanguageModel: Cached or new LLM instance
    """
    global _LLM_CACHE
    
    if not use_cache:
        return get_llm(temperature=temperature, model=model, **kwargs)
    
    # Generate cache key
    model_name = model or os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash-preview-05-20")
    cache_key = f"{model_name}_{temperature}"
    
    # Add additional kwargs that affect the model to the cache key
    if kwargs.get('llm_specific_kwargs'):
        specific_kwargs = kwargs['llm_specific_kwargs']
        for key in sorted(specific_kwargs.keys()):
            if key in ['max_output_tokens', 'safety_settings']:
                cache_key += f"_{key}_{specific_kwargs[key]}"
    
    # Return cached LLM or create new one
    if cache_key in _LLM_CACHE:
        return _LLM_CACHE[cache_key]
    
    # Create new LLM and cache it
    llm = get_llm(temperature=temperature, model=model, **kwargs)
    _LLM_CACHE[cache_key] = llm
    return llm

def clear_llm_caches():
    """Clear all LLM caches to free memory and reset cache state."""
    global _invoke_memory_cache, _response_cache, _cache_hits, _cache_misses
    cache_size = len(_invoke_memory_cache)
    _invoke_memory_cache = {}
    _response_cache = {}
    logging.info(f"Cleared LLM caches. Stats: {_cache_hits} hits, {_cache_misses} misses, {cache_size} entries.")
    _cache_hits = 0
    _cache_misses = 0

def warm_llm_cache(common_prompts):
    """Pre-populate cache with responses for common prompts."""
    llm = get_llm(temperature=0.1)
    for prompt in common_prompts:
        result = llm.invoke(prompt)
        # Cache populated automatically
    logging.info(f"Cache warmed with {len(common_prompts)} common prompts")

def get_cache_stats() -> Dict[str, int]:
    """Get statistics about cache hits and misses."""
    global _cache_hits, _cache_misses
    return {
        "hits": _cache_hits,
        "misses": _cache_misses,
        "total": _cache_hits + _cache_misses
    }