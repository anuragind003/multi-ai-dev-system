"""
LangServe API Server for Multi-AI Development System

This script launches a FastAPI server with LangServe routes that expose the
temperature-optimized agent workflow (0.1-0.4) as an API.
"""

import os
import sys
import asyncio
import logging
from typing import Dict, Any

# Fix Windows console output issues before any other imports
if sys.platform.startswith('win'):
    import io
    import codecs
    
    # Ensure stdout and stderr are not closed and use UTF-8 encoding
    try:
        # Only wrap if not already wrapped
        if not isinstance(sys.stdout, io.TextIOWrapper):
            if hasattr(sys.stdout, 'buffer'):
                sys.stdout = io.TextIOWrapper(
                    sys.stdout.buffer,
                    encoding='utf-8',
                    errors='replace',
                    line_buffering=True
                )
        if not isinstance(sys.stderr, io.TextIOWrapper):
            if hasattr(sys.stderr, 'buffer'):
                sys.stderr = io.TextIOWrapper(
                    sys.stderr.buffer,
                    encoding='utf-8',
                    errors='replace',
                    line_buffering=True
                )
    except Exception as e:
        # If wrapping fails, continue with original streams
        pass

import time
import uvicorn
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
    logging.error(f"Critical import error: {e}")
    logging.error("Please ensure all required dependencies are installed:")
    logging.error("  pip install -r requirements.txt")
    sys.exit(1)

# --- Logging Setup ---
# Initialize custom logging. This provides more control over format and output.

# initialize_logging(console=True, file=True)

# Use standard logger; Uvicorn will handle the configuration.
logger = logging.getLogger(__name__)

# --- System Initializer ---
# This call handles all complex setup (config, memory, RAG).
# It returns a status report and the initialized memory hub.
try:
    from system_initializer import initialize_multi_ai_system
except ImportError as e:
    # Use basic error output instead of logging.basicConfig() which conflicts with uvicorn
    print(f"CRITICAL ERROR: Failed to import system_initializer: {e}", file=sys.stderr)
    sys.exit(1)

def main():
    """Launch the LangServe API server for Multi-AI Development System."""
    start_time = time.time()
    
    # Configure logging first - REMOVED basicConfig to allow uvicorn to manage logging
    # logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
    logger = logging.getLogger(__name__)
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Multi-AI Development System API Server")
    parser.add_argument("--config-file", type=str, help="Path to configuration file")
    parser.add_argument("--env", type=str, default="development", 
                        help="Environment (development, staging, production)")
    parser.add_argument("--port", type=int, default=8001, help="Port to run the server on")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()

    # --- Use the centralized system initializer ---
    logger.info("--- Initializing Full System for API Server ---")
    
    try:
        # This single call will load the config, initialize the memory hub,
        # set up LangSmith, and initialize the RAG manager.
        status_report = initialize_multi_ai_system()
        
        # Check if the system is ready before proceeding
        if not status_report.get("initialization_summary", {}).get("system_ready", False):
            logger.error("System initialization failed. Please check the logs. Server cannot start.")
            sys.exit(1)

        logger.info("--- System Initialization Complete ---")
        
    except Exception as e:
        logger.error(f"Failed to initialize system: {e}")
        sys.exit(1)
    
    # Use port from command line arguments or default
    port = args.port
    
    # --- FIX: Pass the initialized memory hub to the FastAPI app ---
    try:
        logger.info("About to import FastAPI app...")
        
        from app.server_refactored import app
        
        logger.info("FastAPI app imported successfully")
        
        app.state.memory_hub = status_report.get("memory_hub_instance")
        logger.info("Memory hub assigned to app.state")
        
    except Exception as e:
        logger.error(f"Failed to configure FastAPI app: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)

    # Start the FastAPI server
    logger.info(f"Starting Multi-AI Development System API (startup: {time.time() - start_time:.2f}s)")
    logger.info(f"API Documentation: http://localhost:{port}/docs")
    logger.info(f"API Endpoint: http://localhost:{port}/api/workflow")
    logger.info(f"Examples page: http://localhost:{port}/static/examples.html")
    
    # The app is imported here to ensure all initialization happens first
    try:
        uvicorn.run(
            app, # Pass the app instance directly
            host="0.0.0.0",
            port=port,
            reload=False,
            log_config=None,  # Disable uvicorn's logging configuration
            access_log=False  # Disable access logging to prevent conflicts
        )
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()