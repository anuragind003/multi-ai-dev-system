"""
LangServe API Server for Multi-AI Development System

This script launches a FastAPI server with LangServe routes that expose the
temperature-optimized agent workflow (0.1-0.4) as an API.
"""

import os
import sys
import uvicorn
import time
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

try:
    from config import setup_langgraph_server
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
    
    # Use port 8001 consistently
    port = 8001
    
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