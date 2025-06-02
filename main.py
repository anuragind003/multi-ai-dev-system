"""
Multi-AI Development System - Main Entry Point

This module orchestrates the complete software development automation workflow
using specialized AI agents and LangGraph for workflow management.
ENHANCED: Uses AdvancedWorkflowConfig for comprehensive configuration management.
"""

import os
import sys
import argparse
import time
from pathlib import Path
import atexit
import json

# Add project root to Python path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

try:
    # FIXED: Import get_embedding_model instead of get_embeddings
    from config import get_llm, get_embedding_model, TrackedChatModel, AdvancedWorkflowConfig, setup_langgraph_server
    from shared_memory import SharedProjectMemory
    from tools.code_execution_tool import CodeExecutionTool
    from rag_manager import ProjectRAGManager  # Clean import without debugging
    from tools.document_parser import DocumentParser
    from graph import get_workflow
    import monitoring
    
    # Import graph nodes
    from graph_nodes import (
        brd_analysis_node,
        tech_stack_recommendation_node,
        system_design_node,
        planning_node,
        code_generation_node,
        test_case_generation_node,
        code_quality_analysis_node,
        test_validation_node,
        finalize_workflow
    )
    
except ImportError as e:
    print(f"❌ Critical import error: {e}")
    print("Please ensure all required dependencies are installed:")
    print("  pip install -r requirements.txt")
    sys.exit(1)

# Initialize LangSmith at startup - MUST be before any agent instantiation
langsmith_enabled = setup_langgraph_server(enable_server=True)
if langsmith_enabled:
    print("🔍 Using LangSmith for tracing and observability")
    # Set up temperature categories appropriate for your agents
    os.environ["LANGSMITH_TEMPERATURE_CATEGORIES"] = json.dumps({
        "code_generation": 0.1,
        "analytical": 0.2, 
        "creative": 0.3,
        "planning": 0.4
    })
else:
    print("ℹ️ Using local tracing only")

def parse_arguments():
    """ENHANCED: Parse command line arguments for AdvancedWorkflowConfig integration."""
    
    parser = argparse.ArgumentParser(
        description="Multi-AI Development System - Automated Software Development",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage with default configuration
  python main.py requirements.pdf
  
  # Production deployment with configuration file
  python main.py requirements.pdf --config configs/production.yaml --environment production
  
  # Development with debugging and custom thresholds
  python main.py requirements.pdf --environment development --debug --quality-threshold 7.0
  
Configuration Sources (in order of precedence):
  1. Command line arguments (highest priority)
  2. Environment variables (prefix: MAISD_)
  3. Configuration file (YAML/JSON)
  4. Default values (lowest priority)
  
Environment Variables:
  RAG_SECURITY_MODE: Set to 'development', 'staging', or 'production'
  MAISD_QUALITY_THRESHOLD: Minimum code quality score (0-10)
  MAISD_MAX_CODE_GEN_RETRIES: Maximum code generation retries
  FAISS_ENCRYPTION_PASSWORD: Custom encryption password for production
        """
    )
    
    # Required arguments
    parser.add_argument("brd_file", help="Path to Business Requirements Document")
    
    # Configuration file
    parser.add_argument("--config", help="Path to configuration file (YAML/JSON)")
    parser.add_argument("--output-dir", help="Custom output directory")
    
    # Workflow settings
    parser.add_argument("--workflow-type", default="iterative", 
                       choices=["basic", "iterative", "phased", "modular", "resumable"],
                       help="Type of workflow to run")
    parser.add_argument("--environment", choices=["development", "staging", "production"],
                       help="Deployment environment (affects security and behavior)")
    
    # Quality thresholds (will be merged with config file)
    parser.add_argument("--quality-threshold", type=float,
                       help="Minimum code quality score (0-10)")
    parser.add_argument("--min-success-rate", type=float,
                       help="Minimum test success rate (0.0-1.0)")
    parser.add_argument("--min-coverage", type=float,
                       help="Minimum code coverage percentage")
    
    # Retry settings
    parser.add_argument("--max-retries", type=int,
                       help="Maximum code generation retries")
    parser.add_argument("--max-test-retries", type=int,
                       help="Maximum test generation retries")
    
    # Performance settings
    parser.add_argument("--agent-timeout", type=int,
                       help="Agent execution timeout in seconds")
    parser.add_argument("--parallel-execution", action="store_true",
                       help="Enable parallel agent execution (experimental)")
    
    # System settings
    parser.add_argument("--skip-rag", action="store_true",
                       help="Skip RAG system initialization")
    parser.add_argument("--fail-fast", action="store_true",
                       help="Stop execution on first critical error")
    parser.add_argument("--verbose", action="store_true",
                       help="Enable verbose output")
    parser.add_argument("--debug", action="store_true",
                       help="Enable debug mode")
    
    # Add to your argparse arguments
    parser.add_argument(
        "--platform",
        action="store_true",
        help="Enable LangGraph Platform integration"
    )
    parser.add_argument(
        "--server",
        action="store_true",
        help="Enable LangGraph Server for workflow visualization and debugging"
    )
    
    return parser.parse_args()

def load_brd_content(brd_file_path: str) -> str:
    """Load and parse Business Requirements Document."""
    
    if not os.path.exists(brd_file_path):
        raise FileNotFoundError(f"BRD file not found: {brd_file_path}")
    
    try:
        parser = DocumentParser()
        content = parser.parse_document(brd_file_path)
        
        if not content or len(content.strip()) < 100:
            raise ValueError("BRD content is too short or empty")
        
        print(f"✅ BRD loaded successfully: {len(content)} characters")
        return content
        
    except Exception as e:
        raise Exception(f"Failed to parse BRD file: {e}")

def setup_output_directory(project_name: str, custom_output_dir: str = None) -> str:
    """Setup output directory for generated code."""
    
    if custom_output_dir:
        output_dir = Path(custom_output_dir)
    else:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_dir = Path("output") / f"{project_name}_{timestamp}"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create subdirectories
    (output_dir / "src").mkdir(exist_ok=True)
    (output_dir / "tests").mkdir(exist_ok=True)
    (output_dir / "docs").mkdir(exist_ok=True)
    (output_dir / "logs").mkdir(exist_ok=True)
    
    return str(output_dir)

def initialize_rag_system(project_root: str, skip_rag: bool = False, environment: str = "development") -> ProjectRAGManager:
    """Initialize the RAG system with security considerations."""
    
    if skip_rag:
        print("⏭️ Skipping RAG initialization as requested")
        return None
    
    try:
        print(f"🔍 Initializing RAG system (security mode: {environment})...")
        
        # ENHANCED: Use environment parameter for security mode
        rag_manager = ProjectRAGManager(project_root, environment=environment)
        
        # Display security status
        security_status = rag_manager.get_security_status()
        print(f"🔒 Security mode: {security_status['security_mode']}")
        
        if security_status['recommendations']:
            print("💡 Security recommendations:")
            for rec in security_status['recommendations'][:3]:  # Show top 3
                print(f"   • {rec}")
        
        # Try to load existing index first
        if rag_manager.load_existing_index():
            print("✅ Loaded existing RAG index with security verification")
            
            # Show active security features
            active_features = security_status.get('features_enabled', {})
            enabled_features = [feature for feature, enabled in active_features.items() if enabled]
            if enabled_features:
                print(f"🛡️  Active security features: {', '.join(enabled_features)}")
        else:
            print("📚 Creating new RAG index from project code...")
            if rag_manager.index_project_code():
                print("✅ RAG index created successfully with security integration")
            else:
                print("⚠️ RAG indexing failed, continuing without RAG")
                return None
        
        return rag_manager
        
    except Exception as e:
        print(f"⚠️ RAG initialization failed: {e}")
        print("Continuing without RAG support...")
        return None

def create_initial_state(brd_content: str, workflow_config: AdvancedWorkflowConfig) -> dict:
    """
    SIMPLIFIED: Create initial state using the enhanced agent_state.py functionality.
    This function now delegates to the proper state creation function.
    """
    from agent_state import create_initial_agent_state
    
    # Use the enhanced state creation function
    return create_initial_agent_state(brd_content, workflow_config)

def display_results(final_state, run_output_dir):
    """Enhanced result display with trace URL."""
    print("\n" + "="*50)
    print("📊 WORKFLOW EXECUTION SUMMARY")
    print("="*50)
    
    # Add the trace viewer URL
    trace_url = monitoring.get_trace_viewer_url()
    print(f"\n🔍 View detailed execution trace: {trace_url}")
    
    # Print workflow summary
    print_workflow_summary(final_state)
    
    # Show state summary for debugging
    if final_state.get("debug", False):
        from agent_state import get_state_summary
        state_summary = get_state_summary(final_state)
        print("\n" + "="*60)
        print("DEBUG: WORKFLOW STATE SUMMARY")
        print("="*60)
        print(f"Progress: {state_summary['workflow_progress']['progress_percentage']:.1f}% complete")
        print(f"Elapsed Time: {state_summary['workflow_progress']['elapsed_time']:.2f}s")
        print(f"Quality Score: {state_summary['current_metrics']['quality_score']:.1f}/10")
        print(f"Test Success Rate: {state_summary['current_metrics']['test_success_rate']:.2%}")
        print(f"Coverage: {state_summary['current_metrics']['coverage_percentage']:.1f}%")
        print(f"Retries Used: Code({state_summary['retry_status']['code_gen_retries']}), Tests({state_summary['retry_status']['test_retries']})")
        print(f"Errors: {state_summary['errors_count']}")
    
    # Show output directory contents
    print(f"\n📁 Generated files in: {run_output_dir}")
    try:
        for root, dirs, files in os.walk(run_output_dir):
            level = root.replace(run_output_dir, '').count(os.sep)
            indent = ' ' * 2 * level
            print(f"{indent}{os.path.basename(root)}/")
            subindent = ' ' * 2 * (level + 1)
            for file in files:
                print(f"{subindent}{file}")
    except Exception as e:
        print(f"⚠️ Could not list output directory: {e}")

def print_workflow_summary(final_state: dict):
    """ENHANCED: Print workflow summary with better state field access."""
    
    print("\n" + "="*80)
    print("WORKFLOW EXECUTION SUMMARY")
    print("="*80)
    
    # Import state field constants for consistency
    from agent_state import StateFields
    
    # Basic information
    workflow_summary = final_state.get(StateFields.WORKFLOW_SUMMARY, {})
    total_time = workflow_summary.get("total_execution_time", 0)
    status = workflow_summary.get("status", "unknown")
    
    print(f"Status: {status.upper()}")
    print(f"Total Execution Time: {total_time:.2f} seconds")
    
    # Configuration summary
    workflow_config = final_state.get(StateFields.WORKFLOW_CONFIG, {})
    environment = workflow_config.get("environment", "unknown")
    print(f"Environment: {environment}")
    
    # Agent execution times
    execution_times = final_state.get(StateFields.AGENT_EXECUTION_TIMES, {})
    if execution_times:
        print(f"\n📊 Agent Performance:")
        for agent, time_taken in execution_times.items():
            print(f"   {agent}: {time_taken:.2f}s")
    
    # Quality metrics using standardized field names
    quality_score = final_state.get(StateFields.OVERALL_QUALITY_SCORE, 0)
    test_success_rate = final_state.get(StateFields.TEST_SUCCESS_RATE, 0)
    coverage_percentage = final_state.get(StateFields.CODE_COVERAGE_PERCENTAGE, 0)
    
    print(f"\n📈 Quality Metrics:")
    print(f"   Quality Score: {quality_score:.1f}/10")
    print(f"   Test Success Rate: {test_success_rate:.2%}")
    print(f"   Code Coverage: {coverage_percentage:.1f}%")
    
    # Errors
    errors = final_state.get(StateFields.ERRORS, [])
    if errors:
        print(f"\n⚠️ Errors Encountered: {len(errors)}")
        for i, error in enumerate(errors[:3], 1):  # Show first 3 errors
            print(f"   {i}. {error.get('agent', 'Unknown')}: {error.get('error', 'Unknown error')}")
        if len(errors) > 3:
            print(f"   ... and {len(errors) - 3} more errors")
    
    # Configuration details
    config_summary = {
        "Quality Threshold": final_state.get(StateFields.QUALITY_THRESHOLD, 0),
        "Min Success Rate": final_state.get(StateFields.MIN_SUCCESS_RATE, 0),
        "Min Coverage": final_state.get(StateFields.MIN_COVERAGE_PERCENTAGE, 0),
        "Max Retries": final_state.get(StateFields.MAX_CODE_GEN_RETRIES, 0)
    }
    
    print(f"\n⚙️ Configuration Used:")
    for key, value in config_summary.items():
        if isinstance(value, float) and 0 < value < 1:
            print(f"   {key}: {value:.2%}")
        else:
            print(f"   {key}: {value}")
    
    print("="*80)

def main():
    """ENHANCED: Main entry point using AdvancedWorkflowConfig."""
    
    try:
        # Parse command line arguments
        args = parse_arguments()
        
        # ENHANCED: Create sophisticated workflow configuration
        print("🔧 Loading workflow configuration...")
        
        try:
            workflow_config = AdvancedWorkflowConfig.load_from_multiple_sources(
                config_file=args.config,  # None if not provided
                env_prefix="MAISD_",      # Environment variable prefix
                args=args                 # Command line arguments
            )
            
            # Print configuration summary
            if args.debug:
                workflow_config.print_detailed_summary()
            else:
                print(f"✅ Configuration loaded from: {workflow_config._config_source.name}")
                print(f"   Environment: {workflow_config.environment}")
                print(f"   Quality threshold: {workflow_config.min_quality_score}/10")
                print(f"   Max retries: {workflow_config.max_code_gen_retries}")
        
        except Exception as e:
            print(f"⚠️ Configuration loading failed: {e}")
            print("Using default configuration...")
            workflow_config = AdvancedWorkflowConfig()
            workflow_config.environment = args.environment or "development"
            workflow_config.debug_mode = args.debug or False
            workflow_config.verbose_logging = args.verbose or False
        
        # Set up output directory
        run_output_dir = setup_output_directory("project", args.output_dir)
        print(f"📁 Output directory: {run_output_dir}")
        
        # Load BRD content
        try:
            brd_content = load_brd_content(args.brd_file)
        except Exception as e:
            print(f"❌ Error loading BRD: {e}")
            return 1
        
        # Initialize components
        try:
            # Initialize LLM
            llm = get_llm()
            
            # Initialize RAG system with environment-based security
            rag_manager = initialize_rag_system(
                project_root=PROJECT_ROOT,
                skip_rag=args.skip_rag,
                environment=workflow_config.environment
            )
            
            # Initialize code execution tool
            code_execution_tool = CodeExecutionTool(run_output_dir)
            
            print("✅ All components initialized successfully")
            
        except Exception as e:
            print(f"❌ Error initializing components: {e}")
            return 1
        
        # ENHANCED: Create initial state with sophisticated configuration
        initial_state = create_initial_state(brd_content, workflow_config)
        
        # Get and run workflow
        try:
            workflow = get_workflow(
                workflow_type=args.workflow_type,
                platform_enabled=args.platform
            )
            print(f"🚀 Starting {args.workflow_type} workflow with {workflow_config.environment} configuration...")
            
            # Initialize shared memory - MOVED THIS UP
            shared_memory = SharedProjectMemory(run_output_dir)
            
            # Register cleanup for application exit
            atexit.register(shared_memory.close)
            
            # Create workflow configuration - USING shared_memory
            config = {
                "configurable": {
                    "llm": llm,
                    "memory": shared_memory,  # FIXED: Use shared_memory variable
                    "rag_manager": rag_manager,
                    "code_execution_tool": code_execution_tool,
                    "run_output_dir": run_output_dir,
                    "environment": workflow_config.environment,
                    "workflow_config": workflow_config
                }
            }
            
            # Run the workflow
            final_state = workflow.invoke(initial_state, config=config)
            
            # Display results
            display_results(final_state, run_output_dir)
            
            # Determine exit code based on workflow status
            workflow_status = final_state.get("workflow_summary", {}).get("status", "unknown")
            if workflow_status == "completed_successfully":
                return 0
            elif workflow_status in ["completed_with_issues", "completed_with_warnings"]:
                return 1  # Warning exit code
            else:
                return 2  # Error exit code
            
        except Exception as e:
            print(f"❌ Workflow execution failed: {e}")
            if workflow_config.debug_mode:
                import traceback
                traceback.print_exc()
            return 2
    
    except KeyboardInterrupt:
        print("\n⏹️ Execution interrupted by user")
        return 130  # Standard interrupt exit code
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
