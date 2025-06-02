# config.py
import os
import time
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
from enum import Enum
import yaml
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.llms import Ollama
from langchain_community.embeddings import OllamaEmbeddings
from langchain_core.language_models import BaseLanguageModel
from langchain_core.embeddings import Embeddings
from langchain_core.runnables import RunnableSerializable
from pydantic import Field, PrivateAttr
import monitoring
import argparse
from langsmith import Client as LangSmithClient

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
        """Validate configuration settings"""
        if self.llm_provider == "GEMINI" and not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required when using Gemini provider")
    
    def update_workflow_config(self, **kwargs):
        """Update workflow configuration parameters."""
        for key, value in kwargs.items():
            if hasattr(self.workflow, key):
                setattr(self.workflow, key, value)
                monitoring.log_global(f"Updated workflow config: {key} = {value}")
            else:
                monitoring.log_global(f"Unknown workflow config parameter: {key}", "WARNING")

# Global configuration instance
_system_config = None

def get_system_config() -> SystemConfig:
    """Get the global system configuration."""
    global _system_config
    if _system_config is None:
        # Initialize with AdvancedWorkflowConfig instead of WorkflowConfig
        _system_config = SystemConfig(workflow_config=AdvancedWorkflowConfig())
    return _system_config

def get_workflow_config() -> AdvancedWorkflowConfig:  # CHANGED: Return type to AdvancedWorkflowConfig
    """Get the workflow configuration."""
    return get_system_config().workflow

# Enhanced tracked models with proper temperature handling
class TrackedChatModel(RunnableSerializable):
    """
    Enhanced wrapper for ChatGoogleGenerativeAI that tracks API calls.
    Uses direct attribute access instead of Pydantic's PrivateAttr for better compatibility.
    """
    # --- Pydantic Fields ---
    model_name: str 
    google_api_key: Optional[str] = None
    init_kwargs: Dict[str, Any] = Field(default_factory=dict)
    model_instance: BaseLanguageModel = Field(default=None, exclude=True)

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, model: str, google_api_key: Optional[str] = None, **kwargs):
        """
        Initializes the TrackedChatModel with the underlying LLM instance.
        """
        # Create the actual underlying LLM instance
        actual_llm_instance = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=google_api_key,
            **kwargs
        )
        
        # Initialize Pydantic fields via super().__init__
        super().__init__(
            model_name=model, 
            google_api_key=google_api_key, 
            init_kwargs=kwargs,
            model_instance=actual_llm_instance
        )
        
        # Use object.__setattr__ to bypass Pydantic's attribute machinery
        object.__setattr__(self, '_total_calls', 0)
        object.__setattr__(self, '_total_duration', 0.0)

    @property
    def total_calls(self):
        return object.__getattribute__(self, '_total_calls')
    
    @property
    def total_duration(self):
        return object.__getattribute__(self, '_total_duration')

    def bind(self, **kwargs_to_bind: Any) -> "TrackedChatModel":
        """Returns a bound model that preserves tracking capabilities."""
        # Extract generation parameters that need special handling
        generation_params = {}
        other_params = {}
        
        # Separate generation parameters from other parameters
        for key, value in kwargs_to_bind.items():
            if key in ["temperature", "top_p", "top_k", "max_output_tokens", 
                      "candidate_count", "stop_sequences"]:
                generation_params[key] = value
            else:
                other_params[key] = value
        
        # If we have generation params, create a generation_config dict
        if generation_params:
            other_params["generation_config"] = generation_params
        
        # Bind the underlying LLM with properly formatted parameters
        bound_actual_llm = self.model_instance.bind(**other_params)
        
        # Create a new wrapper with the original initialization arguments
        new_wrapper = self.__class__(
            model=self.model_name,
            google_api_key=self.google_api_key,
            **self.init_kwargs
        )
        
        # Replace its model_instance with the bound one
        new_wrapper.model_instance = bound_actual_llm
        
        # Copy tracking state using object.__setattr__ to bypass Pydantic
        total_calls = object.__getattribute__(self, '_total_calls')
        total_duration = object.__getattribute__(self, '_total_duration')
        object.__setattr__(new_wrapper, '_total_calls', total_calls)
        object.__setattr__(new_wrapper, '_total_duration', total_duration)
        
        return new_wrapper

    def invoke(self, input: Any, config: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Any:
        """Invoke with tracking and proper attribute handling."""
        start_time = time.perf_counter()
        success = False
        output_preview = ""
        error_msg = ""
        
        # Extract temperature for logging (improved temperature detection)
        logged_temperature = None
        temperature_category = None
        underlying_llm = self.model_instance
        
        # More robust temperature extraction
        if config and isinstance(config, dict):
            if "configurable" in config and isinstance(config["configurable"], dict):
                agent_name = config["configurable"].get("agent_name", "")
                if agent_name:
                    # Use temperature strategy from agent_temperatures.py
                    cfg = get_system_config()
                    logged_temperature = cfg.agent_temperatures.get(agent_name, 0.2)
                    
                    # Categorize temperature for LangSmith
                    if logged_temperature <= 0.1:
                        temperature_category = "code_generation"
                    elif logged_temperature <= 0.2:
                        temperature_category = "analytical"
                    elif logged_temperature <= 0.4:
                        temperature_category = "creative"
        
        # Extract agent_context for logging
        agent_context = ""
        if config and isinstance(config, dict):
            if "configurable" in config:  # LangGraph style config
                agent_context = config.get("configurable", {}).get('agent_context', '')
            else:  # Standard config
                agent_context = config.get('agent_context', '')
                
        input_preview = str(input)[:200] + "..." if len(str(input)) > 200 else str(input)
        
        try:
            result = self.model_instance.invoke(input, config=config, **kwargs)
            success = True
            output_content = getattr(result, 'content', str(result))
            output_preview = output_content[:200] + "..." if len(output_content) > 200 else output_content
            # Update calls counter using object.__setattr__
            total_calls = object.__getattribute__(self, '_total_calls')
            object.__setattr__(self, '_total_calls', total_calls + 1)
            return result
        except Exception as e:
            error_msg = str(e)
            monitoring.log_agent_activity(
                getattr(self, 'agent_name', "TrackedChatModel"), 
                f"LLM invoke exception: {e}", 
                "ERROR"
            )
            raise
        finally:
            duration = time.perf_counter() - start_time
            # Update duration counter using object.__setattr__
            total_duration = object.__getattribute__(self, '_total_duration')
            object.__setattr__(self, '_total_duration', total_duration + duration)
            
            monitoring.metrics_collector.increment_api_call(self.model_name)
            monitoring.log_api_call_realtime(
                model=self.model_name,
                call_type=f"{self.model_instance.__class__.__name__}_invoke",
                input_preview=input_preview,
                output_preview=output_preview,
                duration=duration,
                success=success,
                error_msg=error_msg,
                temperature=logged_temperature,
                agent_context=agent_context
            )

    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to the wrapped model with better error handling."""
        if name.startswith('_'):
            # Let standard attribute access handle private attributes
            # This prevents recursion in __getattr__ for attributes like _total_calls
            raise AttributeError(f"'{type(self).__name__}' attribute '{name}' not found")
        
        try:
            return getattr(self.model_instance, name)
        except AttributeError:
            raise AttributeError(f"'{type(self).__name__}' (or its wrapped model_instance) has no attribute '{name}'")

class TrackedGoogleGenerativeAIEmbeddings(GoogleGenerativeAIEmbeddings):
    """Tracked version of GoogleGenerativeAIEmbeddings for monitoring."""
    
    def __init__(self, model: str, **kwargs):
        # Initialize parent class with explicit model parameter
        super().__init__(model=model, **kwargs)
        
        # FIXED: Use object.__setattr__ to bypass Pydantic validation
        object.__setattr__(self, '_total_calls', 0)
        object.__setattr__(self, '_total_duration', 0.0)
    
    @property
    def total_calls(self):
        return self._total_calls
    
    @property
    def total_duration(self):
        return self._total_duration

    def embed_documents(self, texts, **kwargs):
        start_time = time.perf_counter()
        success = False
        error_msg = ""
        
        try:
            result = super().embed_documents(texts, **kwargs)
            success = True
            # FIXED: Use object.__setattr__ to update counter
            object.__setattr__(self, '_total_calls', self._total_calls + 1)
            return result
        except Exception as e:
            error_msg = str(e)
            raise
        finally:
            duration = time.perf_counter() - start_time
            # FIXED: Use object.__setattr__ to update duration
            object.__setattr__(self, '_total_duration', self._total_duration + duration)
            
            monitoring.metrics_collector.increment_api_call(f"embedding-{self.model}")
            monitoring.log_api_call_realtime(
                model=f"embedding-{self.model}",
                call_type="embedding_documents",
                input_preview=f"{len(texts)} documents",
                output_preview=f"embeddings generated",
                duration=duration,
                success=success,
                error_msg=error_msg
            )

    def embed_query(self, text, **kwargs):
        start_time = time.perf_counter()
        success = False
        error_msg = ""
        
        try:
            result = super().embed_query(text, **kwargs)
            success = True
            # FIXED: Use object.__setattr__ to update counter
            object.__setattr__(self, '_total_calls', self._total_calls + 1)
            return result
        except Exception as e:
            error_msg = str(e)
            raise
        finally:
            duration = time.perf_counter() - start_time
            # FIXED: Use object.__setattr__ to update duration
            object.__setattr__(self, '_total_duration', self._total_duration + duration)
            
            monitoring.metrics_collector.increment_api_call(f"embedding-{self.model}")
            monitoring.log_api_call_realtime(
                model=f"embedding-{self.model}",
                call_type="embedding_query",
                input_preview=text[:100] + "..." if len(text) > 100 else text,
                output_preview="query embedding generated",
                duration=duration,
                success=success,
                error_msg=error_msg
            )

class TrackedOllama(Ollama):
    """Tracked version of Ollama for monitoring."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        object.__setattr__(self, 'total_calls', 0)
        object.__setattr__(self, 'total_duration', 0.0)

    def invoke(self, input, config=None, **kwargs):
        start_time = time.perf_counter()
        success = False
        output_preview = ""
        error_msg = ""
        temperature = None
        agent_context = ""
        
        # Extract configuration
        if config and isinstance(config, dict):
            temperature = config.get('temperature')
            agent_context = config.get('agent_context', '')
        
        # Prepare input preview
        input_preview = str(input)[:200] + "..." if len(str(input)) > 200 else str(input)
        
        try:
            result = super().invoke(input, config, **kwargs)
            success = True
            output_preview = str(result)[:200] + "..." if len(str(result)) > 200 else str(result)
            object.__setattr__(self, 'total_calls', self.total_calls + 1) # Use object.__setattr__ if total_calls was set with it
            return result
            
        except Exception as e:
            error_msg = str(e)
            raise
        finally:
            duration = time.perf_counter() - start_time
            object.__setattr__(self, 'total_duration', self.total_duration + duration) # Use object.__setattr__
            
            monitoring.metrics_collector.increment_api_call(self.model)
            monitoring.log_api_call_realtime(
                model=self.model,
                call_type="ollama_invoke",
                input_preview=input_preview,
                output_preview=output_preview,
                duration=duration,
                success=success,
                error_msg=error_msg,
                temperature=temperature,
                agent_context=agent_context
            )

# Factory functions with error handling
def get_llm() -> BaseLanguageModel:
    """Get the configured language model with enhanced error handling"""
    cfg = get_system_config()
    print(f"DEBUG: get_llm() - cfg.llm_provider: {cfg.llm_provider}") # DEBUG
    print(f"DEBUG: get_llm() - cfg.gemini_model_name: {cfg.gemini_model_name}") # DEBUG
    print(f"DEBUG: get_llm() - cfg.gemini_api_key is set: {bool(cfg.gemini_api_key)}") # DEBUG
    try:
        if cfg.llm_provider == "GEMINI":
            if not cfg.gemini_model_name: # Explicit check
                raise ValueError("GEMINI_MODEL_NAME is not set or is empty.")
            if not cfg.gemini_api_key: # Explicit check
                raise ValueError("GEMINI_API_KEY is not set or is empty.")
            return TrackedChatModel(
                model=cfg.gemini_model_name,
                google_api_key=cfg.gemini_api_key
            )
        elif cfg.llm_provider == "OLLAMA":
            return TrackedOllama(
                model=cfg.ollama_model_name,
                base_url=cfg.ollama_base_url
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {cfg.llm_provider}")
    except Exception as e:
        print(f"❌ Failed to initialize LLM: {e}")
        raise

def get_embedding_model() -> Embeddings:
    """Get the configured embedding model with enhanced error handling"""
    cfg = get_system_config()  # Get config instance when needed
    try:
        if cfg.llm_provider == "GEMINI":
            return TrackedGoogleGenerativeAIEmbeddings(
                model=cfg.gemini_embedding_model,
                google_api_key=cfg.gemini_api_key
            )
        elif cfg.llm_provider == "OLLAMA":
            return OllamaEmbeddings(
                model=cfg.ollama_model_name,
                base_url=cfg.ollama_base_url
            )
        else:
            raise ValueError(f"Unsupported embedding provider: {cfg.llm_provider}")
    except Exception as e:
        print(f"❌ Failed to initialize embeddings: {e}")
        raise

# Initialize configuration
# config = get_system_config()  # COMMENT THIS OUT

# Project paths
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECT_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")

# Ensure output directory exists
os.makedirs(PROJECT_OUTPUT_DIR, exist_ok=True)

# NEW: Environment-based security configuration
RAG_SECURITY_MODE = os.getenv('RAG_SECURITY_MODE', 'development')

# Security configuration for different environments
SECURITY_CONFIG = {
    'development': {
        'allow_dangerous_deserialization': True,
        'require_encryption': False,
        'enable_integrity_checks': False,
        'enable_access_logging': False,
        'backup_required': False
    },
    'staging': {
        'allow_dangerous_deserialization': True,  # Still needed for FAISS
        'require_encryption': False,
        'enable_integrity_checks': True,
        'enable_access_logging': True,
        'backup_required': False
    },
    'production': {
        'allow_dangerous_deserialization': True,  # Still needed for FAISS but with safeguards
        'require_encryption': True,
        'enable_integrity_checks': True,
        'enable_access_logging': True,
        'backup_required': True
    }
}

def get_security_config(environment: str = None) -> Dict[str, Any]:
    """Get security configuration for the specified environment."""
    env = environment or RAG_SECURITY_MODE
    return SECURITY_CONFIG.get(env, SECURITY_CONFIG['development'])

def is_production_environment(environment: str = None) -> bool:
    """Check if running in production environment."""
    env = environment or RAG_SECURITY_MODE
    return env == 'production'

def validate_security_requirements(environment: str = None) -> List[str]:
    """Validate security requirements for the environment."""
    env = environment or RAG_SECURITY_MODE
    config = get_security_config(env)
    issues = []
    
    if config['require_encryption']:
        try:
            import cryptography
        except ImportError:
            issues.append("Cryptography package required for encryption. Install with: pip install cryptography")
    
    if env == 'production':
        if os.getenv('FAISS_ENCRYPTION_PASSWORD') in [None, 'default-dev-password']:
            issues.append("Set FAISS_ENCRYPTION_PASSWORD environment variable for production")
        
        if os.getenv('FAISS_ENCRYPTION_SALT') in [None, 'default-salt']:
            issues.append("Set FAISS_ENCRYPTION_SALT environment variable for production")
    
    return issues

def initialize_langsmith():
    """
    Initialize LangSmith with proper error handling and environment setup.
    This centralizes all LangSmith configuration to avoid conflicts.
    
    Returns:
        bool: True if LangSmith was successfully enabled
    """
    print("🔄 Initializing LangSmith connection...")
    
    # Check for API key first
    api_key = os.getenv("LANGSMITH_API_KEY")
    if not api_key:
        print("⚠️ LangSmith tracing disabled (API key not found)")
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
        return False
    
    # Set up environment variables for LangSmith
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com" 
    os.environ["LANGCHAIN_API_KEY"] = api_key
    os.environ["LANGCHAIN_PROJECT"] = "Multi-AI-Dev-System"
    
    print("🔍 LangSmith tracing enabled - testing connection...")
    
    # Test connection
    try:
        client = LangSmithClient(api_key=api_key)
        # Simple API call to test connection
        client.list_projects(limit=1)
        print("✅ LangSmith connection successful")
        
        # Add temperature categories for specialized agents
        temperature_categories = {
            "code_generation": 0.1,  # Deterministic code output
            "analytical": 0.2,       # Analysis tasks (tech stack, test validation)
            "creative": 0.3,         # BRD analysis 
            "planning": 0.4          # Implementation planning
        }
        os.environ["LANGSMITH_TEMPERATURE_CATEGORIES"] = json.dumps(temperature_categories)
        print("📊 Temperature categories configured for agent specialization")
        
        return True
    except Exception as e:
        print(f"⚠️ LangSmith connection test failed: {str(e)}")
        print("⚠️ Continuing with local tracing only")
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
        return False