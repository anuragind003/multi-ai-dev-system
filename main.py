#!/usr/bin/env python
"""
Multi-AI Development System - Command line interface
"""

# Fix Windows Unicode logging issues FIRST before any other imports
import sys
import os

# Configure Windows-safe console output immediately
from utils.windows_safe_console import configure_safe_console
configure_safe_console()

# Apply Windows console encoding fix immediately (improved version)
if sys.platform.startswith('win'):
    import io
    import codecs
    
    # Only apply encoding fix if stdout/stderr are not already wrapped or redirected
    try:
        # Check if stdout needs encoding fix
        if (hasattr(sys.stdout, 'buffer') and 
            not isinstance(sys.stdout, io.TextIOWrapper) and
            sys.stdout.isatty()):
            sys.stdout = io.TextIOWrapper(
                sys.stdout.buffer,
                encoding='utf-8',
                errors='replace'
            )
        
        # Check if stderr needs encoding fix
        if (hasattr(sys.stderr, 'buffer') and 
            not isinstance(sys.stderr, io.TextIOWrapper) and
            sys.stderr.isatty()):
            sys.stderr = io.TextIOWrapper(
                sys.stderr.buffer,
                encoding='utf-8',
                errors='replace'
            )
    except (AttributeError, OSError):
        # If encoding fix fails, continue without it
        pass

# Now safe to import other modules
import logging
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

# Load .env file at the very beginning
load_dotenv()

# Initialize Windows-compatible logging
try:
    from utils.windows_logging_fix import setup_windows_compatible_logging
    setup_windows_compatible_logging()
    logging.info("Windows-compatible logging initialized")
except ImportError:
    logging.warning("Windows logging fix not available")
except Exception as e:
    logging.warning(f"Failed to setup Windows logging fix: {e}")

# Verify LangSmith variables are loaded
for key in ["LANGCHAIN_API_KEY", "LANGSMITH_API_KEY", "LANGCHAIN_TRACING_V2", "LANGCHAIN_PROJECT"]:
    if key in os.environ:
        logging.info(f"{key} found in environment variables")
    else:
        logging.warning(f"{key} NOT found in environment variables")

# Now import project modules
from utils.langsmith_utils import configure_logging
configure_logging(silent_mode=True)

# Rest of your imports
import time
import json
import argparse
import uuid
import atexit
import threading
from datetime import datetime, timedelta
from pathlib import Path
from langchain_google_genai import HarmCategory, HarmBlockThreshold
from langchain.globals import set_llm_cache
from langchain_community.cache import SQLiteCache

# Now your other imports
from config import (
    get_llm,
    get_embedding_model,
    AdvancedWorkflowConfig,
    initialize_system_config  # Add this import
)
from tools.document_parser import DocumentParser
from graph import get_workflow, create_phased_workflow, create_iterative_workflow, validate_workflow_configuration  # Added validate_workflow_configuration

# Enhanced A2A Communication imports
try:
    from enhanced_workflow_integration import (
        create_enhanced_workflow, 
        get_default_enhancement_config,
        get_conservative_enhancement_config,
        get_aggressive_enhancement_config
    )
    ENHANCED_A2A_AVAILABLE = True
except ImportError:
    # Use logging module directly since logger isn't defined yet
    import logging
    logging.getLogger(__name__).warning("Enhanced A2A communication not available. Using standard workflows.")
    ENHANCED_A2A_AVAILABLE = False

import monitoring
from agent_state import create_initial_agent_state, StateFields  # Add this import
from enhanced_memory_manager import EnhancedSharedProjectMemory as SharedProjectMemory
from checkpoint_manager import CheckpointManager
from rag_manager import ProjectRAGManager
from message_bus import MessageBus
from tools.code_execution_tool import CodeExecutionTool
from agent_temperatures import get_default_temperatures  # Add this import

# Add this after the existing imports, around line 28
import hashlib

# Add at the top after imports
os.environ["DEBUG_JSON_PARSING"] = "true"  # Enable detailed JSON parsing logs

# Create cache directory if it doesn't exist
os.makedirs(".cache", exist_ok=True)

# Get rate limiting settings from environment or use defaults
_min_delay_seconds = float(os.environ.get("LLM_RATE_LIMIT_DELAY", "4.0"))
_max_calls_per_minute = int(os.environ.get("LLM_MAX_CALLS_PER_MINUTE", "15"))
logging.info(f"Rate limiting: {_min_delay_seconds}s delay ({_max_calls_per_minute} calls/minute maximum)")

# Set up caching for LLM calls with additional debug options
set_llm_cache(SQLiteCache(database_path=".cache/langchain.db"))
logging.info("LLM caching enabled with SQLite backend")

# Register a function to report cache stats on exit
def report_cache_stats():
    """Report cache performance statistics when application exits"""
    from config import get_cache_stats  # Import here to avoid circular imports
    stats = get_cache_stats()
    hits = stats.get("hits", 0)
    misses = stats.get("misses", 0)
    total = hits + misses
    hit_rate = (hits / total * 100) if total > 0 else 0
    logging.info(f"Cache performance: {hits} hits, {misses} misses ({hit_rate:.1f}% hit rate)")
    logging.info(f"Estimated API calls saved: {hits}")
    
atexit.register(report_cache_stats)

# Add this near the beginning of main() function
# Report cache stats periodically during long runs
def report_cache_stats_periodically():
    """Report cache stats periodically during long runs"""
    current_time = time.time()
    if current_time - _cache_stats["last_report_time"] > 300:  # Every 5 minutes
        from config import get_cache_stats
        stats = get_cache_stats()
        hits = stats.get("hits", 0)
        misses = stats.get("misses", 0)
        total = hits + misses
        hit_rate = (hits / total * 100) if total > 0 else 0
        
        monitoring.log_global(
            f"Cache performance: {hits} hits, {misses} misses ({hit_rate:.1f}% hit rate)",
            "INFO"
        )
        _cache_stats["last_report_time"] = current_time

# Register the periodic reporter with atexit to ensure it runs
timer = threading.Timer(300.0, report_cache_stats_periodically)
timer.daemon = True
timer.start()

def validate_initial_state(state: Dict) -> List[str]:
    """Validate that the initial state contains all required keys."""
    required_keys = [
        "brd_content",
        "workflow_id", 
        "workflow_start_time",
        "temperature_strategy"
    ]
    
    missing_keys = [key for key in required_keys if key not in state]
    return missing_keys

# Add timing measurements:
def log_timed_activity(activity_name, func, *args, **kwargs):
    """Execute a function with timing and logging."""
    start = time.time()
    monitoring.log_agent_activity("System", f"Starting {activity_name}", "START")
    try:
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        monitoring.log_agent_activity("System", f"{activity_name} completed in {elapsed:.2f}s", "SUCCESS")
        return result
    except Exception as e:
        elapsed = time.time() - start
        monitoring.log_agent_activity("System", f"{activity_name} failed after {elapsed:.2f}s: {e}", "ERROR")
        raise

def warm_llm_cache(common_prompts):
    """Pre-populate cache with responses for common prompts."""
    if not common_prompts:
        return 0
    
    llm = get_llm(temperature=0.1)
    count = 0
    logging.info(f"Warming cache with {len(common_prompts)} common prompts...")
    
    for prompt in common_prompts:
        try:
            _ = llm.invoke(prompt)
            count += 1
            # Add small delay to avoid hitting rate limits during warming
            time.sleep(0.5)
        except Exception as e:
            logging.warning(f"Error warming cache for prompt: {str(e)}")
    
    logging.info(f"Cache warmed with {count} common prompts")
    return count

def clear_llm_caches():
    """Clear all LLM caches to free memory and reset cache state."""
    from config import clear_caches  # Import here to avoid circular imports
    import sqlite3
    
    try:
        # Try to clear the SQLite cache
        if os.path.exists(".cache/langchain.db"):
            try:
                conn = sqlite3.connect(".cache/langchain.db")
                cursor = conn.cursor()
                cursor.execute("DELETE FROM llm_cache")
                conn.commit()
                conn.close()
                logging.info("SQLite cache cleared")
            except Exception as e:
                logging.warning(f"Failed to clear SQLite cache: {e}")
        
        # Clear in-memory caches from config
        stats = clear_caches()
        logging.info(f"Memory caches cleared. Stats: {stats.get('entries_cleared', 0)} entries removed")
        
    except Exception as e:
        logging.error(f"Error clearing caches: {str(e)}")

_cache_stats = {
    "hits": 0,
    "misses": 0,
    "last_report_time": time.time()
}

def main():
    """Main entry point for the Multi-AI Development System."""
    import argparse
    import json
    import time
    import logging
    import os
    import monitoring
    from datetime import datetime
    
    # Setup argument parser
    parser = argparse.ArgumentParser(description='Multi-AI Development System')
    parser.add_argument('--brd', type=str, help='Path to Business Requirements Document')
    parser.add_argument('--workflow', type=str, default='phased', 
                        choices=['basic', 'iterative', 'phased', 'modular', 'resumable'],
                        help='Workflow type to use (default: phased with robust fallback logic)')
    parser.add_argument('--output', type=str, help='Output directory')
    parser.add_argument('--config', type=str, help='Path to configuration file')
    parser.add_argument('--platform', action='store_true', 
                        help='Enable LangGraph Platform integration')
    # Add new argument for LangGraph Dev console
    parser.add_argument('--dev', action='store_true', 
                        help='Register workflows with LangGraph Dev visualization console')
    # Add argument for tracing
    parser.add_argument('--trace-all', action='store_true',
                   help='Execute all workflow types with tracing for LangSmith visibility')    # Add to the existing argument parser
    parser.add_argument('--rate-limit', type=float, default=4.0,
                   help='Minimum delay between API calls in seconds (default: 4.0)')
    parser.add_argument('--no-cache', action='store_true',
                   help='Disable LLM response caching')
    parser.add_argument('--clear-cache', action='store_true',
                   help='Clear all LLM caches before running')
    
    # Enhanced A2A Communication arguments
    parser.add_argument('--enhanced-a2a', action='store_true',
                       help='Enable enhanced agent-to-agent communication')
    parser.add_argument('--a2a-config', type=str, default='conservative',
                       choices=['conservative', 'default', 'aggressive'],
                       help='A2A enhancement configuration (default: conservative)')
    parser.add_argument('--enable-cross-validation', action='store_true',
                       help='Enable cross-validation between related agents')
    parser.add_argument('--enable-error-recovery', action='store_true', 
                       help='Enable intelligent error recovery with A2A context')
    parser.add_argument('--a2a-analytics', action='store_true',
                       help='Enable detailed A2A communication analytics')
    
    args = parser.parse_args()
    
    # Configure logging
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    
    # FIXED: Helper function definition moved to before its usage
    def get_llm_specific_configuration(provider: str) -> dict:
        """Returns provider-specific LLM configuration."""
        if provider == "google":
            return {
                "safety_settings": {
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                },
                "generation_config": {
                    "top_k": 40,
                    "top_p": 0.95,
                    "max_output_tokens": 8192
                }
            }
        elif provider == "anthropic":
            return {
                "temperature": 0.2,
                "max_tokens": 4096
            }
        return {}
    
    # Load system config - Add error handling and default config
    logger.info("Initializing system configuration...")
    
    # Initialize with a safe default first to prevent access issues
    workflow_config = AdvancedWorkflowConfig()
    workflow_config.llm_provider = 'google'
    workflow_config.environment = 'development'
    
    # Now try to load from file if provided
    if args.config:
        try:
            # Load configuration from file 
            if os.path.exists(args.config):
                workflow_config = AdvancedWorkflowConfig.load_from_multiple_sources(
                    config_file=args.config,
                    args=args
                )
                logger.info("Configuration loaded from file successfully")
            else:
                logger.warning(f"Configuration file {args.config} not found, using defaults")
        except Exception as config_error:
            logger.error(f"Error loading configuration from file: {config_error}")
            logger.warning("Using default configuration")
    else:
        logger.info("No configuration file specified, using defaults")
        # Load configuration from command line args and environment
        workflow_config = AdvancedWorkflowConfig.load_from_multiple_sources(args=args)

    # Set the global system config FIRST before calling any functions that depend on it
    try:
        from config import set_system_config
        set_system_config(workflow_config)
        logger.info("Global system configuration set successfully")
    except ImportError as e:
        logger.warning("set_system_config function not available")
    except Exception as e:
        logger.warning(f"Failed to set global system configuration: {e}")
        # Try a direct fallback
        try:
            from config import SystemConfig
            import config
            config._system_config = SystemConfig(workflow_config)
            logger.info("Direct fallback SystemConfig set")
        except Exception as e2:
            logger.error(f"Direct fallback also failed: {e2}")
            # If we can't set the config at all, we need to stop
            return 1

    # Safely access the configuration
    provider = getattr(workflow_config, 'llm_provider', 'google')
    logger.info(f"Using configuration with LLM provider: {provider}")
    
    # Parse BRD file
    if not args.brd or not os.path.exists(args.brd):
        logger.error("Business Requirements Document not provided or does not exist")
        return 1
        
    brd_path = args.brd
    parser = DocumentParser()
    brd_content = parser.parse(brd_path)
    
    if not brd_content:
        logger.error(f"Failed to parse BRD document: {brd_path}")
        return 1
        
    logger.info(f"Successfully parsed BRD document: {brd_path}")
    
    # Setup output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_id = f"run_{timestamp}"
    
    if args.output:
        run_output_dir = os.path.abspath(args.output)
    else:
        run_output_dir = os.path.join(os.getcwd(), "output", run_id)
        
    os.makedirs(run_output_dir, exist_ok=True)
    logger.info(f"Using output directory: {run_output_dir}")
    
    # Initialize LLM
    logger.info(f"Initializing LLM with provider: {workflow_config.llm_provider}")
    
    llm_specific_kwargs = get_llm_specific_configuration(workflow_config.llm_provider)
    llm = get_llm(llm_specific_kwargs=llm_specific_kwargs)
    embedding_model = get_embedding_model()
    
    # Initialize components
    memory = SharedProjectMemory(run_dir=run_output_dir)
    message_bus = MessageBus()
    checkpoint_manager = CheckpointManager(output_dir=run_output_dir)
    code_execution_tool = CodeExecutionTool(output_dir=run_output_dir)
    
    # Initialize RAG
    rag_manager = ProjectRAGManager(
        project_root=os.getcwd(),
        embeddings=embedding_model,
        environment=workflow_config.environment
    )
    
    # Set as global RAG manager for tools to access
    from rag_manager import set_rag_manager
    set_rag_manager(rag_manager)
    
    # Add this section to properly initialize the vector store
    logger.info("Initializing RAG vector store...")
    if rag_manager:
        if rag_manager.vector_store is None:
            try:
                logger.info("No existing RAG index found. Creating new index from project code...")
                # This will use the optimized implementation
                indexed_count = rag_manager.index_project_code()
                logger.info(f"Indexed {indexed_count} documents with optimized indexing")
                
                # Check if indexing was successful
                if indexed_count == 0:
                    # Fallback: Create an empty vector store
                    logger.info("No documents indexed. Creating empty RAG vector store as fallback...")
                    empty_success = rag_manager.initialize_empty_vector_store()
                    if empty_success:
                        logger.info("Empty vector store initialized successfully")
                    else:
                        logger.warning("Failed to initialize empty vector store")
            except AttributeError as e:
                logger.error(f"RAG method not found: {e}")
                logger.info("Checking alternative method names...")
                # Try alternative method names if they exist
                if hasattr(rag_manager, 'initialize_index_from_project'):
                    logger.info("Found initialize_index_from_project method, using as fallback...")
                    rag_manager.initialize_index_from_project()
                else:
                    logger.warning("No suitable indexing method found")
            except Exception as e:
                logger.warning(f"Failed to create RAG index from project code: {e}")
                try:
                    # Fallback: Create an empty vector store
                    logger.info("Creating empty RAG vector store as fallback...")
                    rag_manager.initialize_empty_vector_store()
                except Exception as e2:
                    logger.error(f"Failed to initialize empty RAG vector store: {e2}")
                    rag_manager = None  # Set to None so we can check later
        else:
            logger.info("Using existing RAG vector store")
    else:
        logger.warning("RAG manager not initialized, proceeding without RAG capabilities")
    
    # Register start of run
    monitoring.log_agent_activity("System", f"Starting {args.workflow} workflow run: {run_id}", "START")
    
    # Define temperature strategy for logging, monitoring, and API responses.
    # NOTE: This dictionary doesn't directly control LLM temperature settings.
    # Actual LLM temperatures are managed by agent_temperatures.py and used via 
    # get_agent_temperature() in graph_nodes.py's create_agent_with_temperature().
    temperature_strategy = get_default_temperatures()

    # Log the temperature strategy for this run
    logger.info("Temperature Strategy for AI Agents:")
    for agent, temp in temperature_strategy.items():
        logger.info(f"  {agent}: {temp}")

    # Monitor temperature usage
    monitoring.log_global(f"Using temperature strategy with {len(temperature_strategy)} agent profiles", "INFO")
    
    # Define global LLM-specific kwargs (e.g., for Gemini safety settings, context limits)
    global_llm_specific_kwargs = {}
    
    # For Gemini models, add safety settings if applicable
    if workflow_config.llm_provider == "google":
        global_llm_specific_kwargs = {
            "safety_settings": {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            },
            "generation_config": {
                "top_k": 40,
                "top_p": 0.95,
                "max_output_tokens": 8192
            }
        }
        logger.info("Applied Google Gemini-specific configuration settings (new safety_settings format)")
    elif workflow_config.llm_provider == "anthropic":
        global_llm_specific_kwargs = {
            "temperature": 0.2,  # Base temperature, will be overridden by agent-specific settings
            "max_tokens": 4096
        }
        logger.info("Applied Anthropic Claude-specific configuration settings")
    
    # Create configurable components dictionary for LangGraph
    configurable_components = {
        "llm": llm,
        "memory": memory,
        "rag_manager": rag_manager,
        "code_execution_tool": code_execution_tool,
        "run_output_dir": run_output_dir,
        "message_bus": message_bus,
        "checkpoint_manager": checkpoint_manager,
        "workflow_id": run_id,
        "global_llm_specific_kwargs": global_llm_specific_kwargs,
        "temperature_strategy": temperature_strategy
    }
      # Validate workflow configuration
    workflow_type = args.workflow
    issues = validate_workflow_configuration({"configurable": configurable_components})
    
    if issues:
        logger.warning("Workflow configuration has issues:")
        for issue in issues:
            logger.warning(f"  - {issue}")
        
        # Continue with warning or exit based on severity
        if any("missing" in issue for issue in issues):
            logger.error("Critical configuration issues detected. Exiting.")
            return 1
      # Create workflow with enhanced A2A support if requested
    try:
        if args.enhanced_a2a and ENHANCED_A2A_AVAILABLE:
            logger.info(f"Creating enhanced workflow with A2A communication ({args.a2a_config} configuration)")
            
            # Get enhancement configuration based on user choice
            if args.a2a_config == "conservative":
                enhancement_config = get_conservative_enhancement_config()
            elif args.a2a_config == "aggressive":
                enhancement_config = get_aggressive_enhancement_config()
            else:  # default
                enhancement_config = get_default_enhancement_config()
            
            # Override specific settings from command line arguments
            if args.enable_cross_validation:
                enhancement_config['enable_cross_validation'] = True
                logger.info("Cross-validation enabled via command line")
            
            if args.enable_error_recovery:
                enhancement_config['enable_error_recovery'] = True
                logger.info("Error recovery enabled via command line")
            
            if args.a2a_analytics:
                enhancement_config['log_level'] = 'DEBUG'
                enhancement_config['enable_analytics'] = True
                logger.info("A2A analytics enabled via command line")
              # Create enhanced workflow
            workflow = create_enhanced_workflow(workflow_type, enhancement_config)
            logger.info("Enhanced A2A workflow created successfully")
            
            # Log the configuration being used
            logger.info("Enhanced A2A Configuration:")
            for key, value in enhancement_config.items():
                logger.info(f"  {key}: {value}")
            
            # Monitor A2A usage
            monitoring.log_global(f"Enhanced A2A workflow created with {args.a2a_config} configuration", "INFO")
            monitoring.log_agent_activity("System", f"A2A features enabled: {list(enhancement_config.keys())}", "CONFIG")
                
        else:
            if args.enhanced_a2a and not ENHANCED_A2A_AVAILABLE:
                logger.warning("Enhanced A2A requested but not available. Using standard workflow.")
            
            # Use standard workflow
            workflow = get_workflow(workflow_type, args.platform)
            logger.info(f"Created standard {workflow_type} workflow")
            
    except Exception as e:
        logger.error(f"Failed to create workflow: {e}")
        return 1
      # Create initial agent state
    initial_state = create_initial_agent_state(
        brd_content=brd_content,
        workflow_config=workflow_config
    )
    initial_state[StateFields.WORKFLOW_ID] = run_id
    initial_state[StateFields.TEMPERATURE_STRATEGY] = temperature_strategy
    
    # Add A2A-specific state if enhanced mode is enabled
    if args.enhanced_a2a and ENHANCED_A2A_AVAILABLE:
        initial_state["enhanced_a2a_enabled"] = True
        initial_state["a2a_config_type"] = args.a2a_config
        initial_state["cross_validation_enabled"] = args.enable_cross_validation
        initial_state["error_recovery_enabled"] = args.enable_error_recovery
        initial_state["a2a_analytics_enabled"] = args.a2a_analytics
    
    # Add the missing workflow_start_time to fix the finalizer error
    start_time = time.time()
    initial_state[StateFields.WORKFLOW_START_TIME] = start_time
    
    # Validate initial state
    missing_keys = validate_initial_state(initial_state)
    if missing_keys:
        logger.warning(f"Initial state is missing required keys: {', '.join(missing_keys)}")
        # Add missing keys with default values
        for key in missing_keys:
            if key == "workflow_start_time":
                initial_state[key] = time.time()
            elif key == "workflow_id":
                initial_state[key] = run_id
            # Add other defaults as needed
    
    try:
        # Execute workflow
        final_state = workflow.invoke(
            initial_state,
            config={"configurable": configurable_components}
        )
        
        elapsed_time = time.time() - start_time
        logger.info(f"Workflow completed in {elapsed_time:.2f} seconds")
          # Output final state summary
        summary_path = os.path.join(run_output_dir, "summary.json")
        with open(summary_path, "w") as f:
            summary = {
                "workflow_type": workflow_type,
                "run_id": run_id,
                "elapsed_time": elapsed_time,
                "requirements_analysis": final_state.get("requirements_analysis", {}),
                "tech_stack": final_state.get("tech_stack_recommendation", {}),
                "temperature_strategy": temperature_strategy,
                "enhanced_a2a": {
                    "enabled": args.enhanced_a2a and ENHANCED_A2A_AVAILABLE,
                    "config_type": args.a2a_config if args.enhanced_a2a else None,
                    "features": {
                        "cross_validation": args.enable_cross_validation,
                        "error_recovery": args.enable_error_recovery,
                        "analytics": args.a2a_analytics
                    } if args.enhanced_a2a else {}
                },
                "metrics": {
                    "total_files": len(final_state.get("code_generation_result", {}).get("generated_files", {})),
                    "test_success_rate": final_state.get("test_success_rate", 0),
                    "overall_quality_score": final_state.get("overall_quality_score", 0)
                }
            }
            json.dump(summary, f, indent=2)
            
        logger.info(f"Summary written to {summary_path}")
        monitoring.log_agent_activity("System", f"Workflow completed successfully: {run_id}", "SUCCESS")
        
    except Exception as e:
        logger.error(f"Workflow execution failed: {e}")
        monitoring.log_agent_activity("System", f"Workflow failed: {str(e)}", "ERROR")
        return 1
    
    finally:
        # Clean up resources
        if 'memory' in locals():
            memory.close()
        if 'rag_manager' in locals() and rag_manager:
            try:
                # Close vector store if available
                if hasattr(rag_manager, 'close') and callable(rag_manager.close):
                    rag_manager.close()
            except Exception as e:
                logger.warning(f"Error closing RAG manager: {e}")

    # Add this near the end of main(), right before workflow execution
    if args.dev:
        try:
            from langgraph.dev import dev_console
            from graph import (
                create_basic_workflow,
                create_iterative_workflow,
                create_phased_workflow,
                create_modular_workflow,
                create_resumable_workflow,
                create_implementation_workflow
            )
            
            # Add async workflow imports
            try:
                from async_graph import (
                    create_async_basic_workflow,
                    create_async_iterative_workflow,
                    create_async_phased_workflow,
                    create_async_modular_workflow,
                    create_async_resumable_workflow,
                    create_async_implementation_workflow
                )
                has_async = True
                logger.info("Async workflow modules loaded successfully")
            except ImportError:
                has_async = False
                logger.warning("Async workflow modules not available")
            
            logger.info("Registering all workflows with LangGraph Dev")            # Create and register all synchronous workflows
            sync_workflows = {
                "basic": create_basic_workflow(),
                "iterative": create_iterative_workflow(),
                "phased": create_phased_workflow(),
                "modular": create_modular_workflow(),
                "resumable": create_resumable_workflow(),
                "implementation": create_implementation_workflow()
            }
            
            # Register synchronous workflows
            registered_count = 0
            for name, workflow in sync_workflows.items():
                try:
                    dev_console.register_workflow(name, workflow)
                    logger.info(f"[OK] Registered synchronous {name} workflow")
                    registered_count += 1
                except Exception as e:
                    logger.error(f"Failed to register {name} workflow: {str(e)}")
            
            # Register async workflows if available
            if has_async:
                # We need to create the async workflows within an async context
                import asyncio
                
                async def register_async_workflows():
                    async_workflows = {
                        "async_basic": create_async_basic_workflow(),
                        "async_iterative": create_async_iterative_workflow(),
                        "async_phased": create_async_phased_workflow(),
                        "async_modular": create_async_modular_workflow(),
                        "async_resumable": create_async_resumable_workflow(),
                        "async_implementation": create_async_implementation_workflow()
                    }
                    
                    async_count = 0
                    for name, workflow_coro in async_workflows.items():
                        try:
                            # Await the coroutine to get the actual workflow
                            workflow = await workflow_coro
                            dev_console.register_workflow(name, workflow)
                            logger.info(f"[OK] Registered {name} workflow")
                            nonlocal registered_count
                            registered_count += 1
                            async_count += 1
                        except Exception as e:
                            logger.error(f"Failed to register {name} workflow: {str(e)}")
                    
                    return async_count
                
                # Execute the async registration
                try:
                    async_registered = asyncio.run(register_async_workflows())
                    logger.info(f"Registered {async_registered} async workflows")
                except Exception as e:
                    logger.error(f"Failed to register async workflows: {str(e)}")
            
            logger.info(f"LangGraph Dev console initialized with {registered_count} workflows")
        except Exception as e:
            logger.warning(f"Failed to initialize LangGraph Dev console: {e}")
    
    # Tracing option: Execute workflows on demand
    if args.trace_all:
        from utils.langsmith_utils import configure_tracing
        
        # Synchronous workflow tracing
        for wtype in ["basic", "iterative", "phased", "modular", "resumable", "implementation"]:
            try:
                logger.info(f"Running {wtype} workflow for LangSmith visualization")
                test_workflow = get_workflow(wtype)
                # Create minimal state with required fields
                test_state = initialize_workflow_state()
                # Add minimal required content
                test_state["brd_content"] = "This is a test BRD for tracing visualization."
                test_state["workflow_id"] = f"trace_{wtype}_{uuid.uuid4().hex[:8]}"
                test_state["workflow_start_time"] = time.time()
                test_state["temperature_strategy"] = temperature_strategy
                
                # Configure tracing
                configure_tracing(test_workflow, project_name="multi-ai-dev-system")
                
                # Run with minimal execution to generate trace
                logger.info(f"Executing trace for {wtype} workflow")
                test_workflow.invoke(
                    test_state,
                    config={"configurable": configurable_components}
                )
                logger.info(f"[OK] Generated trace for {wtype} workflow")
            except Exception as e:
                logger.warning(f"Failed to trace {wtype} workflow: {e}")
        
        # Async workflow tracing if available
        if 'has_async' in locals() and has_async:
            import asyncio
            from async_graph import get_async_workflow
            
            async def trace_async_workflows():
                for wtype in ["basic", "iterative", "phased", "modular", "resumable", "implementation"]:
                    try:
                        logger.info(f"Running async_{wtype} workflow for LangSmith visualization")
                        test_workflow = await get_async_workflow(wtype)
                        # Create minimal state with required fields
                        test_state = initialize_workflow_state()
                        # Add minimal required content
                        test_state["brd_content"] = "This is a test BRD for async tracing visualization."
                        test_state["workflow_id"] = f"trace_async_{wtype}_{uuid.uuid4().hex[:8]}"
                        test_state["workflow_start_time"] = time.time()
                        test_state["temperature_strategy"] = temperature_strategy
                        
                        # Configure tracing
                        configure_tracing(test_workflow, project_name="multi-ai-dev-system-async")
                        
                        # Run with minimal execution to generate trace
                        logger.info(f"Executing trace for async_{wtype} workflow")
                        await test_workflow.ainvoke(
                            test_state,
                            config={"configurable": configurable_components}
                        )
                        logger.info(f"[OK] Generated trace for async_{wtype} workflow")
                    except Exception as e:
                        logger.warning(f"Failed to trace async_{wtype} workflow: {e}")
            
            try:
                asyncio.run(trace_async_workflows())
            except Exception as e:
                logger.error(f"Failed to trace async workflows: {e}")
    
    return 0

def initialize_workflow_state():
    """Initialize the workflow state with default values."""
    from agent_state import StateFields
    
    state = {}
    
    # Initialize revision counters
    state[StateFields.ARCHITECTURE_REVISION_COUNT] = 0
    state[StateFields.DATABASE_REVISION_COUNT] = 0
    state[StateFields.BACKEND_REVISION_COUNT] = 0
    state[StateFields.FRONTEND_REVISION_COUNT] = 0
    state[StateFields.INTEGRATION_REVISION_COUNT] = 0
    
    # Add other necessary initialization
    
    return state

# Only run if executed directly
if __name__ == "__main__":
    main()
