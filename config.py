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
from langchain_huggingface import HuggingFaceEmbeddings

# Other dependencies
from pydantic import Field, PrivateAttr
from langsmith import Client as LangSmithClient

# Remove this import if you're defining response_cache locally
# from llm_cache import response_cache

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
            print("⚠️ LANGSMITH_API_KEY not set in environment")
            return None
            
        client = LangSmithClient(api_key=api_key)
        # Simple API call to test connection
        client.list_projects(limit=1)
        print("✅ LangSmith connection successful")
        return client
    except Exception as e:
        print(f"⚠️ LangSmith connection test failed: {str(e)}")
        print("⚠️ Continuing with local tracing only")
        return None

def setup_langgraph_server(enable_server=True):
    """Configure LangGraph server for development and monitoring."""
    if enable_server:
        # Use the centralized initialization function
        return initialize_langsmith()
    else:
        print("⚠️ LangSmith tracing disabled (server not enabled)")
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
        
        print("\n" + "="*80)
        print("ADVANCED WORKFLOW CONFIGURATION")
        print("="*80)
        print(f"Configuration Source: {self._config_source.value}")
        print(f"Environment: {self.environment}")
        
        print(f"\n📊 Quality Thresholds:")
        print(f"   Minimum Quality Score: {self.min_quality_score}/10")
        print(f"   Minimum Success Rate: {self.min_success_rate:.2%}")
        print(f"   Minimum Coverage: {self.min_coverage_percentage}%")
        
        print(f"\n🔄 Retry Settings:")
        print(f"   Code Generation Retries: {self.max_code_gen_retries}")
        print(f"   Test Generation Retries: {self.max_test_retries}")
        print(f"   Quality Analysis Retries: {self.max_quality_retries}")
        
        print(f"\n⏱️ Timeout Settings:")
        print(f"   Agent Timeout: {self.agent_timeout}s")
        print(f"   Code Execution Timeout: {self.code_execution_timeout}s")
        print(f"   LLM Timeout: {self.llm_timeout}s")
        
        print(f"\n🚀 Performance:")
        print(f"   Max Concurrent Agents: {self.max_concurrent_agents}")
        print(f"   API Rate Limit: {self.api_rate_limit}/s")
        print(f"   Memory Limit: {self.memory_limit_mb}MB")
        
        print(f"\n🔧 Behavior:")
        print(f"   Fail Fast: {'Enabled' if self.fail_fast else 'Disabled'}")
        print(f"   Skip Quality Check: {'Yes' if self.skip_quality_check else 'No'}")
        print(f"   Skip Test Validation: {'Yes' if self.skip_test_validation else 'No'}")
        print(f"   Parallel Execution: {'Enabled' if self.parallel_execution else 'Disabled'}")
        
        print(f"\n🔍 Logging:")
        print(f"   Debug Mode: {'Enabled' if self.debug_mode else 'Disabled'}")
        print(f"   Verbose Logging: {'Enabled' if self.verbose_logging else 'Disabled'}")
        print(f"   Telemetry: {'Enabled' if self.telemetry_enabled else 'Disabled'}")
        
        if self._validation_errors:
            print(f"\n⚠️ Validation Issues:")
            for error in self._validation_errors:
                print(f"   • {error}")
        
        print("="*80)

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
        print("\n" + "="*60)
        print("WORKFLOW CONFIGURATION")
        print("="*60)
        print(f"Max Code Generation Retries: {self.max_code_gen_retries}")
        print(f"Max Test Retries: {self.max_test_retries}")
        print(f"Minimum Quality Score: {self.min_quality_score}/10")
        print(f"Minimum Success Rate: {self.min_success_rate*100}%")
        print(f"Minimum Coverage: {self.min_coverage_percentage}%")
        print(f"Fail Fast Mode: {'Enabled' if self.fail_fast else 'Disabled'}")
        print(f"Skip Quality Check: {'Yes' if self.skip_quality_check else 'No'}")
        print(f"Skip Test Validation: {'Yes' if self.skip_test_validation else 'No'}")
        print("="*60)

# Configuration class for better management
class SystemConfig:
    def __init__(self, workflow_config: AdvancedWorkflowConfig = None):
        self.llm_provider = os.getenv("LLM_PROVIDER", "GEMINI").upper()
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.gemini_model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash-preview-05-20") # Default
        print(f"DEBUG: SystemConfig.__init__ - GEMINI_MODEL_NAME from env: {os.getenv('GEMINI_MODEL_NAME')}") # DEBUG
        print(f"DEBUG: SystemConfig.__init__ - self.gemini_model_name set to: {self.gemini_model_name}") # DEBUG
        self.gemini_embedding_model = os.getenv("GEMINI_EMBEDDING_MODEL", "models/embedding-001") # Default
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.ollama_model_name = os.getenv("OLLAMA_MODEL_NAME", "codellama:7b")
        
        # Use imported agent temperatures
        from agent_temperatures import AGENT_TEMPERATURES  # ADDED: Import agent temperatures
        self.agent_temperatures = AGENT_TEMPERATURES  # CHANGED: Use imported temperatures
        
        # Add workflow configuration - use AdvancedWorkflowConfig for consistency
        self.workflow = workflow_config or AdvancedWorkflowConfig()  # CHANGED: Use AdvancedWorkflowConfig
        
        self.validate_config()
    
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
            if hasattr(self.workflow, key):
                setattr(self.workflow, key, value)
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
    except AttributeError:
        # Fallback if log_agent_activity doesn't exist either
        print(f"INFO: SystemConfig initialized with LLM provider: {_system_config.llm_provider}")

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
        monitoring.log_global(error_msg, "ERROR")
        raise RuntimeError(error_msg)
    
    return _system_config

def get_workflow_config() -> AdvancedWorkflowConfig:  # CHANGED: Return type to AdvancedWorkflowConfig
    """Get the workflow configuration."""
    return get_system_config().workflow

# Enhanced tracked models with proper temperature handling
class TrackedChatModel(RunnableSerializable):
    """
    Enhanced wrapper for ChatGoogleGenerativeAI that tracks API calls and properly handles temperature binding.
    Provides robust parameter management for Gemini's specific needs.
    """
    # --- Pydantic Fields ---
    model_name: str 
    google_api_key: Optional[str] = None
    model_instance: Union[BaseLanguageModel, RunnableBinding] = Field(default=None, exclude=True)
    
    # Private attributes for tracking
    _llm_init_kwargs: Dict[str, Any] = PrivateAttr(default_factory=dict)
    _total_calls: int = PrivateAttr(default=0)
    _total_duration: float = PrivateAttr(default=0.0)

    class Config:
        arbitrary_types_allowed = True

    def __init__(
        self, 
        model_instance: Union[BaseLanguageModel, RunnableBinding],
        model_name: str, 
        google_api_key: Optional[str] = None, 
        llm_init_kwargs: Optional[Dict[str, Any]] = None,
        _total_calls: int = 0,
        _total_duration: float = 0.0
    ):
        """
        Initialize TrackedChatModel with an existing LLM instance and tracking metadata.
        
        Args:
            model_instance: The LLM instance to wrap (ChatGoogleGenerativeAI or RunnableBinding)
            model_name: Name of the model for logging
            google_api_key: API key for Gemini
            llm_init_kwargs: Original kwargs used to create the model_instance
            _total_calls: Number of API calls made (for preserving state during bind)
            _total_duration: Total duration of API calls (for preserving state during bind)
        """
        # Initialize Pydantic fields
        super().__init__(
            model_name=model_name, 
            google_api_key=google_api_key, 
            model_instance=model_instance
        )
        
        # Store init kwargs and tracking data
        self._llm_init_kwargs = llm_init_kwargs or {}
        self._total_calls = _total_calls
        self._total_duration = _total_duration

    @property
    def total_calls(self) -> int:
        """Return the total number of API calls made."""
        return self._total_calls
    
    @property
    def total_duration(self) -> float:
        """Return the total duration of API calls in seconds."""
        return self._total_duration

    def bind(self, **kwargs_to_bind: Any) -> "TrackedChatModel":
        """
        Returns a new TrackedChatModel with bound parameters.
        Properly handles Gemini's parameter structure, especially generation_config.
        
        Args:
            **kwargs_to_bind: Parameters to bind to the model
            
        Returns:
            New TrackedChatModel instance with bound parameters
        """
        # Extract the 'config' parameter which is meant for LangChain's runtime
        # and not for the underlying LLM model
        config = kwargs_to_bind.pop("config", None)
        
        # Deep copy the remaining kwargs to avoid modifying the original
        new_kwargs = copy.deepcopy(kwargs_to_bind)
        
        # FIXED: Explicitly define Gemini generation config keys
        gemini_gen_config_keys = {
            "temperature", "top_p", "top_k", "max_output_tokens",
            "candidate_count", "stop_sequences"
        }
        
        # Standard LangChain bindable parameters
        standard_bind_keys = {"stop", "callbacks", "tags", "metadata", "run_name", "remote"}
        
        # Split the parameters for different destinations
        lc_binding_params = {}      # For LangChain binding
        gemini_gen_config_params = {}  # For Gemini generation_config
        gemini_safety_settings = None  # For Gemini safety_settings
        unknown_params = {}         # Track unrecognized parameters
        
        # ADDED: Special handling for directly provided generation_config
        directly_provided_gen_config = new_kwargs.pop("generation_config", None)
        
        # Process parameters based on destination
        for key, value in new_kwargs.items():
            # Debug log to identify parameter issues
            logger.debug(f"TrackedChatModel.bind processing parameter: '{key}'")
            
            if key in standard_bind_keys:
                lc_binding_params[key] = value
            elif key == "safety_settings":
                gemini_safety_settings = value
            elif key in gemini_gen_config_keys:
                gemini_gen_config_params[key] = value
            # FIXED: Special handling for max_tokens -> max_output_tokens conversion
            elif key == "max_tokens":
                # Convert max_tokens to max_output_tokens for Gemini compatibility
                logger.info(f"Converting 'max_tokens' to 'max_output_tokens' for Gemini compatibility")
                gemini_gen_config_params["max_output_tokens"] = value
            else:
                unknown_params[key] = value
        
        if unknown_params:
            logger.warning(
                f"TrackedChatModel.bind: Received unknown parameters: {list(unknown_params.keys())}"
            )
        
        # Prepare final binding parameters
        final_bind_kwargs = {}
        
        # Add standard LangChain bindable parameters
        for key, value in lc_binding_params.items():
            final_bind_kwargs[key] = value
        
        # Handle generation_config parameters - start with base config
        base_gen_config = {}
        if "generation_config" in self._llm_init_kwargs:
            orig_config = self._llm_init_kwargs["generation_config"]
            if isinstance(orig_config, dict):
                base_gen_config = orig_config.copy()
            else:
                base_gen_config = orig_config.to_dict() if hasattr(orig_config, "to_dict") else {}
        
        # Merge configurations in priority order:
        # 1. Base config (lowest priority)
        # 2. Individual parameters (middle priority)
        # 3. Directly provided generation_config (highest priority)
        merged_gen_config = base_gen_config.copy()
        
        # Add individual parameters
        if gemini_gen_config_params:
            merged_gen_config.update(gemini_gen_config_params)
        
        # Add directly provided generation_config (highest priority)
        if directly_provided_gen_config and isinstance(directly_provided_gen_config, dict):
            merged_gen_config.update(directly_provided_gen_config)
            
        # Preserve special configurations like response_mime_type if not overwritten
        response_mime_type = base_gen_config.get("response_mime_type")
        if response_mime_type and "response_mime_type" not in merged_gen_config:
            merged_gen_config["response_mime_type"] = response_mime_type
        
        # Only add generation_config if we have parameters to add
        if merged_gen_config:
            final_bind_kwargs["generation_config"] = merged_gen_config
        
        # Add safety_settings if provided
        if gemini_safety_settings:
            final_bind_kwargs["safety_settings"] = gemini_safety_settings
        
        # Log the actual binding parameters for debugging
        logger.debug(f"TrackedChatModel binding with: {final_bind_kwargs}")
        
        try:
            # Create bound version of the model
            bound_model = self.model_instance.bind(**final_bind_kwargs)
            
            # Create a new TrackedChatModel with the bound model
            return TrackedChatModel(
                model_instance=bound_model,
                model_name=self.model_name,
                google_api_key=self.google_api_key,
                llm_init_kwargs=self._llm_init_kwargs,
                _total_calls=self._total_calls,
                _total_duration=self._total_duration
            )
        except Exception as e:
            logger.error(f"Error while binding parameters: {str(e)}")
            raise

    def invoke(self, input: Any, config: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Any:
        """
        Invoke the model with input, tracking API calls and parameters.
        Extracts and logs the effective temperature actually used by Gemini.
        """
        start_time = time.perf_counter()
        success = False
        output_preview = ""
        error_msg = ""
        
        # Extract effective temperature for logging
        effective_temp_for_log: Optional[float] = None
        
        # Attempt to extract temperature from multiple possible locations
        # 1. From kwargs if passed directly to invoke
        if 'temperature' in kwargs:
            effective_temp_for_log = kwargs['temperature']
        
        # 2. From the model instance itself or its binding
        current_model_instance = self.model_instance
        if effective_temp_for_log is None:
            if isinstance(current_model_instance, RunnableBinding):
                # Check bound kwargs
                if 'temperature' in current_model_instance.kwargs:
                    effective_temp_for_log = current_model_instance.kwargs['temperature']
                elif 'generation_config' in current_model_instance.kwargs and \
                     isinstance(current_model_instance.kwargs['generation_config'], dict) and \
                     'temperature' in current_model_instance.kwargs['generation_config']:
                    effective_temp_for_log = current_model_instance.kwargs['generation_config']['temperature']
                
                # If still not found, check the bound LLM instance itself
                if effective_temp_for_log is None and hasattr(current_model_instance.bound, 'temperature'):
                    effective_temp_for_log = current_model_instance.bound.temperature
                elif effective_temp_for_log is None and hasattr(current_model_instance.bound, 'generation_config') and \
                     hasattr(current_model_instance.bound.generation_config, 'temperature'):
                     effective_temp_for_log = current_model_instance.bound.generation_config.temperature

            elif hasattr(current_model_instance, 'temperature'): # Direct attribute on the LLM
                effective_temp_for_log = current_model_instance.temperature
            elif hasattr(current_model_instance, 'generation_config') and \
                 hasattr(current_model_instance.generation_config, 'temperature'): # For Gemini models
                 effective_temp_for_log = current_model_instance.generation_config.temperature
        
        # 3. From the initial _llm_init_kwargs if nothing else found
        if effective_temp_for_log is None and self._llm_init_kwargs:
            effective_temp_for_log = self._llm_init_kwargs.get('temperature')
            if effective_temp_for_log is None:
                gen_config = self._llm_init_kwargs.get('generation_config', {})
                if isinstance(gen_config, dict):
                    effective_temp_for_log = gen_config.get('temperature')
        
        # Safely extract agent context
        agent_context = ""
        if config:
            if isinstance(config, dict):
                if "configurable" in config:  # LangGraph style
                    agent_context = config.get("configurable", {}).get('agent_context', '')
                else:  # Standard config
                    agent_context = config.get('agent_context', '')
            else:  # Handle if config is not a dict (e.g. RunnableConfig object)
                if hasattr(config, 'configurable'):
                    agent_context = getattr(config.configurable, 'agent_context', 'TrackedChatModel')
                elif hasattr(config, 'agent_context'):
                    agent_context = getattr(config, 'agent_context', 'TrackedChatModel')
        
        # Use a default context if not specified
        if not agent_context:
            agent_context = "TrackedChatModel"
        
        # Prepare input preview for logging with better truncation
        input_preview = (str(input)[:197] + "...") if len(str(input)) > 200 else str(input)
        
        try:
            # Invoke the model
            result = self.model_instance.invoke(input, config=config, **kwargs)
            success = True
            
            # Extract output content for logging with better handling
            if hasattr(result, 'content'):
                output_content = result.content
            elif isinstance(result, str):
                output_content = result
            else:
                output_content = str(result)
            
            output_preview = (output_content[:197] + "...") if len(output_content) > 200 else output_content
            
            # Update call counter
            self._total_calls += 1
            return result
            
        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            
            # More detailed error logging
            monitoring.log_agent_activity(
                agent_context, 
                f"LLM invoke exception: [{error_type}] {error_msg}", 
                "ERROR"
            )
            
            # Re-raise with context
            raise
        finally:
            # Calculate and update duration
            duration = time.perf_counter() - start_time
            self._total_duration += duration
            
            # Log API call with safe monitoring access
            try:
                monitoring.metrics_collector.increment_api_call(self.model_name)
                monitoring.log_api_call_realtime(
                    model=self.model_name,
                    call_type=f"{self.model_instance.__class__.__name__}_invoke",
                    input_preview=input_preview,
                    output_preview=output_preview,
                    duration=duration,
                    success=success,
                    error_msg=error_msg,
                    temperature=effective_temp_for_log,  # Now this should have a value
                    agent_context=agent_context
                )
            except (AttributeError, ImportError) as e:
                # Fallback logging if monitoring module has issues
                print(f"API Call: {self.model_name} | Temp: {effective_temp_for_log} | " 
                      f"Success: {success} | Duration: {duration:.2f}s")
                print(f"Monitoring error: {e}")

# Enhanced get_llm function for Gemini
def get_llm(temperature: Optional[float] = None, 
            model: Optional[str] = None,
            llm_specific_kwargs: Optional[Dict[str, Any]] = None):
    """
    Get LLM instance based on environment configuration with improved error resilience.
    
    Args:
        temperature: Default temperature for the LLM (overrides environment defaults)
        model: Model name to use (overrides environment defaults)
        llm_specific_kwargs: Additional provider-specific parameters
        
    Returns:
        A tracked LLM instance configured with the specified parameters
    """
    llm_provider = os.getenv("LLM_PROVIDER", "GEMINI").upper()
    logger.info(f"Initializing LLM with provider: {llm_provider}")
    
    # Get global retry configuration with smart defaults
    RETRY_CONFIG = {
        "max_retries": int(os.getenv("LLM_MAX_RETRIES", "8")),  # Increased from default 4
        "initial_delay": float(os.getenv("LLM_INITIAL_DELAY", "1.0")),  # Start with 1 second
        "max_delay": float(os.getenv("LLM_MAX_DELAY", "60.0")),  # Cap at 60 seconds
        "backoff_factor": float(os.getenv("LLM_BACKOFF_FACTOR", "1.5")),  # More gradual backoff
        "jitter": bool(os.getenv("LLM_JITTER", "True").lower() == "true"),  # Add randomness
        # Retry on these specific status codes and timeout errors
        "retry_on": [408, 429, 500, 502, 503, 504]
    }
    
    try:
        if llm_provider == "GEMINI":
            # Get API key with secure handling
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY not found in environment variables")
            
            # Log that key exists but don't show any part of it for security
            logger.info(f"Gemini API Key loaded: {bool(api_key)}")
            
            # Get model name and temperature
            model_name = model or os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash-preview-05-20")
            
            # Validate and set temperature
            temp = temperature
            if temp is None:
                temp = float(os.getenv("DEFAULT_TEMPERATURE", 0.1))
            
            # Ensure temperature is within valid range
            if not (0.0 <= temp <= 1.0):
                logger.warning(f"Temperature {temp} outside valid range [0.0, 1.0]. Clamping to valid range.")
                temp = max(0.0, min(1.0, temp))
            
            # Prepare initialization kwargs for ChatGoogleGenerativeAI with enhanced retry logic
            gemini_init_kwargs = {
                "model": model_name,
                "temperature": temp,
                "google_api_key": api_key,
                # REMOVED: "convert_system_message_to_human": True - Now deprecated
                # Gemini now natively supports system messages without conversion
                "retry_config": {
                    "retry": {
                        "timeout": float(os.getenv("LLM_REQUEST_TIMEOUT", "120.0")),
                        "attempts": RETRY_CONFIG["max_retries"],
                        "backoff_factor": RETRY_CONFIG["backoff_factor"],
                        "initial_delay": RETRY_CONFIG["initial_delay"],
                        "maximum_delay": RETRY_CONFIG["max_delay"],
                        "jitter": RETRY_CONFIG["jitter"],
                        "retry_on_exceptions": (
                            TimeoutError, 
                            ConnectionError,
                            requests.exceptions.RequestException
                        ),
                        "retry_on_status_codes": RETRY_CONFIG["retry_on"]
                    }
                },
                # Increased token limits for complex tasks
                "max_output_tokens": int(os.getenv("MAX_OUTPUT_TOKENS", "8192")),
                # Smart request throttling
                "request_parallelism": int(os.getenv("LLM_REQUEST_PARALLELISM", "4")),
                # Replace the string-based safety settings with enum-based settings:
                "safety_settings": {
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH
                }
            }
            
            # Add any additional specific kwargs
            if llm_specific_kwargs:
                # Special handling for generation_config
                if "generation_config" in llm_specific_kwargs:
                    gen_config = gemini_init_kwargs.get("generation_config", {})
                    if isinstance(gen_config, dict):
                        gen_config.update(llm_specific_kwargs.pop("generation_config"))
                    gemini_init_kwargs["generation_config"] = gen_config
                
                # Add remaining kwargs
                filtered_kwargs = {k: v for k, v in llm_specific_kwargs.items() if v is not None}
                gemini_init_kwargs.update(filtered_kwargs)
            
            logger.info(f"Creating ChatGoogleGenerativeAI with model={model_name}, temp={temp}, retries={RETRY_CONFIG['max_retries']}")
            from langchain_google_genai import ChatGoogleGenerativeAI
            
            # Create the LLM with improved error handling
            try:
                actual_llm = ChatGoogleGenerativeAI(**gemini_init_kwargs)
                
                # Return a tracked model that wraps the LLM instance
                return TrackedChatModel(
                    model_instance=actual_llm,
                    model_name=model_name,
                    google_api_key=api_key,
                    llm_init_kwargs=gemini_init_kwargs
                )
            except Exception as e:
                # Enhanced error handling with more detailed fallback strategy
                error_type = type(e).__name__
                error_msg = str(e)
                logger.warning(f"Error initializing {model_name}: [{error_type}] {error_msg}")
                
                # Step 1: Try reducing complexity (lower temperature)
                if temperature and temperature > 0.2:
                    logger.info("Attempting fallback with lower temperature (0.2)")
                    try:
                        gemini_init_kwargs["temperature"] = 0.2
                        actual_llm = ChatGoogleGenerativeAI(**gemini_init_kwargs)
                        return TrackedChatModel(
                            model_instance=actual_llm,
                            model_name=model_name,
                            google_api_key=api_key,
                            llm_init_kwargs=gemini_init_kwargs
                        )
                    except Exception:
                        pass  # Continue to next fallback
                
                # Step 2: Try fallback to a more stable model
                fallback_model = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-1.5-pro")
                logger.warning(f"Trying fallback model: {fallback_model}")
                
                # Update model in kwargs
                gemini_init_kwargs["model"] = fallback_model
                
                # Try again with fallback model
                actual_llm = ChatGoogleGenerativeAI(**gemini_init_kwargs)
                return TrackedChatModel(
                    model_instance=actual_llm,
                    model_name=fallback_model,
                    google_api_key=api_key,
                    llm_init_kwargs=gemini_init_kwargs
                )
        
        # Add support for other providers here...
        
        else:
            raise ValueError(f"Unsupported LLM provider: {llm_provider}")
            
    except Exception as e:
        # Comprehensive error handling
        error_msg = f"Error initializing LLM: {str(e)}"
        logger.error(error_msg)
        
        # Try to use monitoring if available
        try:
            monitoring.log_global(error_msg, "ERROR")
        except:
            pass
        
        # Re-raise the exception
        raise

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
            from langchain_huggingface import HuggingFaceEmbeddings
            
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
                     **kwargs) -> TrackedChatModel:
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
        TrackedChatModel: LLM instance with appropriate temperature binding
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

import time
from functools import wraps

# Add a global variable to track API calls
_last_api_call_time = 0
_api_call_count = 0
_min_delay_between_calls = 6.0  # 1 call every 6 seconds (10 calls per minute)

# Store the original invoke method before we patch it
_original_invoke = TrackedChatModel.invoke

# Add simple memory-based caching for frequently repeated identical calls
_invoke_memory_cache = {}
_MAX_INVOKE_CACHE_SIZE = 100  # Limit memory usage

# Add near the top with other global variables
_cache_hits = 0
_cache_misses = 0

# Define your model-specific rate limits in the global scope
_model_rate_limits = {
    # model_family: seconds_per_call
    "gemini-pro": 3.0,  # 20 calls per minute
    "gemini-1.5": 3.0,
    "gemini-flash": 2.0, # Faster model, maybe higher limit (30/min)
    "default": 4.0      # Default safe limit (15/min)
}

# Agent-specific overrides (these are more important than the model)
_agent_rate_limit_overrides = {
    # agent_name: seconds_per_call
    "System Designer Agent": 6.0, # This agent is chatty, slow it down to 10 calls/min
    "Plan Compiler Agent": 5.0,   # This one can also be chatty
}

# Replace the ENTIRE rate_limited_invoke function with this new one
def rate_limited_invoke(self, input: Any, config: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Any:
    """
    Advanced rate-limited invoke with adaptive backoff and fallback mechanisms.
    """
    global _last_api_call_time, _api_call_count, _invoke_memory_cache

    # 1. In-memory Caching for repeated inputs within the same run
    cache_key = None
    if isinstance(input, str):
        cache_key = hashlib.md5(input.encode()).hexdigest()
        if cache_key in _invoke_memory_cache:
            logging.debug(f"RateLimiter: In-memory cache hit for input.")
            return _invoke_memory_cache[cache_key]

    # 2. Extract model and agent information
    agent_context = ""
    if config and isinstance(config, dict):
        if "configurable" in config:
            agent_context = config.get("configurable", {}).get('agent_context', '')
        else:
            agent_context = config.get('agent_context', '')

    # Get model family for rate limiting
    try:
        model_key = '-'.join(self.model_name.split('-')[:2])
    except (AttributeError, IndexError):
        model_key = "default"

    # 3. Apply adaptive rate limiting
    sleep_time = adaptive_limiter.should_delay(model_key, agent_context)
    if sleep_time > 0:
        logging.info(f"Rate limiting active for '{agent_context or model_key}'. Sleeping for {sleep_time:.2f}s")
        time.sleep(sleep_time)

    _api_call_count += 1
    if _api_call_count % 10 == 0:
        logging.info(f"Total API calls this run: {_api_call_count}")

    # 4. Call the original function with retry logic
    max_retries = 5
    retry_count = 0
    
    while retry_count <= max_retries:
        try:
            result = _original_invoke(self, input, config=config, **kwargs)
            
            # Success! Update the rate limiter and cache the result
            adaptive_limiter.report_success(model_key)
            
            if cache_key and len(_invoke_memory_cache) < _MAX_INVOKE_CACHE_SIZE:
                _invoke_memory_cache[cache_key] = result
                
            return result
            
        except Exception as e:
            error_str = str(e).lower()
            is_rate_limit = any(indicator in error_str for indicator in 
                               ["rate limit", "quota", "429", "resource exhausted"])
            
            # If it's a rate limit error, we can retry with backoff
            if is_rate_limit and retry_count < max_retries:
                retry_count += 1
                adaptive_limiter.report_failure(model_key, is_rate_limit=True)
                
                # Calculate backoff time with exponential increase and jitter
                backoff_time = min(2 ** retry_count, 60) * (0.8 + 0.4 * random.random())
                
                logging.warning(
                    f"Rate limit hit for {agent_context or model_key}. "
                    f"Retrying in {backoff_time:.2f}s (attempt {retry_count}/{max_retries})"
                )
                
                time.sleep(backoff_time)
                continue
                
            # For non-rate limit errors or if we've exhausted retries, raise the exception
            if is_rate_limit:
                logging.error(f"Rate limit persists after {max_retries} retries. Consider reducing request frequency.")
            raise

# Replace the existing rate_limited_invoke with this improved version
TrackedChatModel.invoke = rate_limited_invoke

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

# Add to config.py after the model_rate_limits definition
class AdaptiveRateLimiter:
    """Adaptive rate limiter that adjusts based on API responses"""
    
    def __init__(self):
        self.base_delays = _model_rate_limits.copy()
        self.current_delays = _model_rate_limits.copy()
        self.consecutive_failures = {}
        self.last_call_time = {}
        self.lock = threading.Lock()
        self.max_backoff = 60.0  # Maximum 60 second delay
    
    def should_delay(self, model_key, agent_context=None):
        """Determine if we should delay and for how long"""
        with self.lock:
            # Get the appropriate delay for this model/agent
            if agent_context in _agent_rate_limit_overrides:
                base_delay = _agent_rate_limit_overrides[agent_context]
            else:
                base_delay = self.current_delays.get(model_key, self.current_delays["default"])
            
            # Get current time and last call time
            current_time = time.time()
            last_time = self.last_call_time.get(model_key, 0)
            elapsed = current_time - last_time
            
            # If enough time has passed, update and return no delay
            if elapsed >= base_delay:
                self.last_call_time[model_key] = current_time
                return 0.0
                
            # Need to wait
            sleep_time = base_delay - elapsed
            self.last_call_time[model_key] = current_time + sleep_time
            return sleep_time
    
    def report_failure(self, model_key, is_rate_limit=True):
        """Report a failure and increase backoff"""
        with self.lock:
            # Increment consecutive failures
            self.consecutive_failures[model_key] = self.consecutive_failures.get(model_key, 0) + 1
            
            if is_rate_limit:
                # Increase the delay for this model
                base = self.base_delays.get(model_key, self.base_delays["default"])
                backoff_factor = min(2 ** self.consecutive_failures[model_key], 10)  # Cap at 2^10
                self.current_delays[model_key] = min(base * backoff_factor, self.max_backoff)
                logging.warning(f"Rate limit hit for {model_key}. Increased delay to {self.current_delays[model_key]:.2f}s")
    
    def report_success(self, model_key):
        """Report a successful call and gradually reduce delay"""
        with self.lock:
            # Reset consecutive failures
            self.consecutive_failures[model_key] = 0
            
            # Gradually decrease delay back toward base delay
            current = self.current_delays.get(model_key, self.current_delays["default"])
            base = self.base_delays.get(model_key, self.base_delays["default"])
            
            if current > base:
                # Reduce by 10% each successful call, but not below base
                self.current_delays[model_key] = max(base, current * 0.9)


adaptive_rate_limiter = AdaptiveRateLimiter()
# After line 1506 where adaptive_rate_limiter is defined, add:
adaptive_limiter = adaptive_rate_limiter  # Create alias for compatibility with rate_limited_invoke

def create_fallback_chain(providers=None):
    """Create a chain of provider fallbacks to try when rate limits are hit"""
    if providers is None:
        providers = ["GEMINI", "OPENAI", "ANTHROPIC"]
        
    # Filter to only providers with configured API keys
    available_providers = []
    for provider in providers:
        if provider == "GEMINI" and os.getenv("GEMINI_API_KEY"):
            available_providers.append(provider)
        elif provider == "OPENAI" and os.getenv("OPENAI_API_KEY"):
            available_providers.append(provider)
        elif provider == "ANTHROPIC" and os.getenv("ANTHROPIC_API_KEY"):
            available_providers.append(provider)
    
    return available_providers

fallback_providers = create_fallback_chain()

class TokenBucketRateLimiter:
    """Token bucket algorithm for rate limiting"""
    
    def __init__(self, rate=10.0, capacity=20.0):
        """
        Initialize with tokens per second rate and bucket capacity
        
        Args:
            rate: Tokens per second to add
            capacity: Maximum tokens the bucket can hold
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_refill = time.time()
        self.lock = threading.Lock()
    
    def consume(self, tokens=1):
        """
        Consume tokens from the bucket
        
        Args:
            tokens: Number of tokens to consume (default: 1)
            
        Returns:
            Tuple of (success, wait_time)
        """
        with self.lock:
            self._refill()
            
            if self.tokens >= tokens:
                # We have enough tokens
                self.tokens -= tokens
                return True, 0.0
                
            # Not enough tokens - calculate wait time
            deficit = tokens - self.tokens
            wait_time = deficit / self.rate
            return False, wait_time
    
    def _refill(self):
        """Refill tokens based on elapsed time"""
        now = time.time()
        elapsed = now - self.last_refill
        
        # Add tokens based on elapsed time
        if elapsed > 0:
            new_tokens = elapsed * self.rate
            self.tokens = min(self.capacity, self.tokens + new_tokens)
            self.last_refill = now

# Create global rate limiters
gemini_limiter = TokenBucketRateLimiter(rate=10.0, capacity=20.0)  # 10 tokens/second, burst of 20