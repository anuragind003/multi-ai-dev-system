"""Utilities for LangSmith integration"""
import os
from typing import Optional, Dict, Any, List
import json

def configure_langsmith():
    """
    Configure LangSmith with correct API endpoints
    """
    # Use API endpoint instead of web UI endpoint
    os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
    
    # Set batch size to avoid 413 errors
    os.environ["LANGCHAIN_BATCH_SIZE"] = "5"

    # Configure tracing project
    if "LANGCHAIN_PROJECT" not in os.environ:
        os.environ["LANGCHAIN_PROJECT"] = "Multi-AI-Dev-System"
        
    return True

def create_langsmith_client():
    """
    Create a properly configured LangSmith client with optimal settings.
    
    Returns:
        langsmith.Client: Configured LangSmith client
    """
    from langsmith import Client
    
    # Configure LangSmith environment variables first
    configure_langsmith()
    
    # Create client with smaller batch sizes to avoid 413 errors
    client = Client(
        api_url=os.environ.get("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com"),
        api_key=os.environ.get("LANGSMITH_API_KEY") or os.environ.get("LANGCHAIN_API_KEY"),
        max_batch_size=5,  # Smaller batches to avoid 413 errors
        project_name=os.environ.get("LANGCHAIN_PROJECT", "Multi-AI-Dev-System")
    )
    
    return client

def configure_logging(silent_mode=False):
    """
    Configure logging to suppress noisy debug messages.
    
    Args:
        silent_mode (bool): Whether to suppress all non-essential logs
    """
    import logging
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Suppress noisy modules
    noisy_loggers = [
        "urllib3.connectionpool",
        "langsmith.client",
        "httpx",
        "httpcore",
        "openai",
        "tenacity",
        "urllib3",  # Add parent module to fully suppress
        "requests",
        "asyncio",
        "aiohttp",
        "grpc"
    ]
    
    for logger_name in noisy_loggers:
        logging.getLogger(logger_name).setLevel(logging.ERROR)  # Use ERROR instead of WARNING
    
    # In silent mode, suppress all but critical logs
    if silent_mode:
        root_logger.setLevel(logging.ERROR)
        logging.getLogger("langsmith").setLevel(logging.ERROR)

def configure_tracing(graph, project_name=None):
    """Configure tracing for LangSmith visualization"""
    import os
    from langsmith import Client
    
    # Explicitly set environment variables in code
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    
    # IMPORTANT: Add both environment variable names for compatibility
    if "LANGCHAIN_API_KEY" in os.environ and "LANGSMITH_API_KEY" not in os.environ:
        os.environ["LANGSMITH_API_KEY"] = os.environ["LANGCHAIN_API_KEY"]
    
    # Set project name
    if project_name:
        os.environ["LANGCHAIN_PROJECT"] = project_name
    
    # Print debug info
    print(f"LangSmith API Key: {os.environ.get('LANGSMITH_API_KEY', '')[:5]}...")
    print(f"LangSmith Project: {os.environ.get('LANGCHAIN_PROJECT', 'default')}")
    
    try:
        # Create client to verify connectivity
        client = Client()
        print(f"Successfully connected to LangSmith API: {client.base_url}")
    except Exception as e:
        print(f"Error connecting to LangSmith: {e}")
        
    return graph

def test_langsmith_connection():
    """Test connection to LangSmith API"""
    import os
    import sys
    
    try:
        from langsmith import Client
        
        # Try to connect with explicit API key
        api_key = os.environ.get("LANGSMITH_API_KEY") or os.environ.get("LANGCHAIN_API_KEY")
        
        if not api_key:
            print("⚠️ No LangSmith API key found in environment variables")
            return False
            
        client = Client(
            api_url="https://api.smith.langchain.com",
            api_key=api_key
        )
        
        # Test API connection with a simple request
        response = client.list_projects(limit=1)
        print(f"✅ Successfully connected to LangSmith API")
        print(f"    API URL: {client.base_url}")
        print(f"    API Key: {api_key[:5]}...")
        return True
    except Exception as e:
        print(f"❌ Error connecting to LangSmith: {e}")
        return False