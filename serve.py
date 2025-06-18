"""
LangServe API Server for Multi-AI Development System

This script launches a FastAPI server with LangServe routes that expose the
temperature-optimized agent workflow (0.1-0.4) as an API.
"""

import os
import sys
import uvicorn
import time
import argparse
from pathlib import Path

try:
    from config import (
        AdvancedWorkflowConfig,
        initialize_system_config,
        setup_langgraph_server
    )
    import json
    from monitoring import metrics_collector
except ImportError as e:
    print(f"❌ Critical import error: {e}")
    print("Please ensure all required dependencies are installed:")
    print("  pip install -r requirements.txt")
    sys.exit(1)

def main():
    """Launch the LangServe API server for Multi-AI Development System."""
    start_time = time.time()
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Multi-AI Development System API Server")
    parser.add_argument("--config-file", type=str, help="Path to configuration file")
    parser.add_argument("--env", type=str, default="development", 
                        help="Environment (development, staging, production)")
    parser.add_argument("--port", type=int, default=8001, help="Port to run the server on")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()
    
    # Load configuration - similar to main.py but with API-specific defaults
    api_config = AdvancedWorkflowConfig.load_from_multiple_sources(
        config_file=args.config_file,
        args=args
    )
    # Apply any API-specific adjustments
    api_config._validate_and_adjust()
    api_config.print_detailed_summary()
    
    # Initialize global system configuration
    initialize_system_config(api_config)
    
    # Initialize LangSmith for tracing
    langsmith_enabled = setup_langgraph_server(enable_server=True)
    
    if langsmith_enabled:
        print("✅ LangSmith tracing enabled for API monitoring")
        # Configure temperature categories for agent specialization
        os.environ["LANGSMITH_TEMPERATURE_CATEGORIES"] = json.dumps({
            "code_generation": 0.1,  # Deterministic code output
            "analytical": 0.2,       # Analysis tasks (tech stack, test validation)
            "creative": 0.3,         # BRD analysis 
            "planning": 0.4          # Implementation planning
        })
    
    # Create output directories if they don't exist
    api_output_dir = os.path.join(os.getcwd(), "output", "api_workflow")
    os.makedirs(api_output_dir, exist_ok=True)
    
    # Ensure static directory exists for examples.html
    static_dir = os.path.join(os.path.dirname(__file__), "app", "static")
    os.makedirs(static_dir, exist_ok=True)
    
    # Register shutdown handler for metrics saving
    def save_metrics_on_exit():
        print("\n📊 Saving API metrics...")
        metrics_collector.save_metrics_to_file()
    import atexit
    atexit.register(save_metrics_on_exit)
    
    # Use port from command line arguments or default
    port = args.port
    
    # Start the FastAPI server
    print(f"🚀 Starting Multi-AI Development System API (startup: {time.time() - start_time:.2f}s)")
    print(f"📚 API Documentation: http://localhost:{port}/docs")
    print(f"🔗 API Endpoint: http://localhost:{port}/api/workflow")
    print(f"📖 Examples page: http://localhost:{port}/static/examples.html")
    
    # The app is imported here to ensure all initialization happens first
    uvicorn.run(
        "app.server:app",
        host="0.0.0.0",
        port=port,
        reload=False
    )

if __name__ == "__main__":
    main()