"""
LangGraph Platform configuration for the Multi-AI Development System.
"""
import os
from dotenv import load_dotenv
import logging
from types import SimpleNamespace

# Load environment variables
load_dotenv()

def get_platform_client():
    """Configure LangGraph Platform integration."""
    try:
        # Get API key from environment variables
        api_key = os.getenv("LANGGRAPH_API_KEY")
        api_url = os.getenv("LANGGRAPH_API_URL", "https://api.langchain.cloud")
        
        if not api_key:
            logging.warning("LANGGRAPH_API_KEY not found. Platform integration disabled.")
            return None
        
        # Configure tracing via environment variables
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = api_key
        os.environ["LANGCHAIN_ENDPOINT"] = api_url
        
        logging.info(f"LangGraph Platform integration configured with endpoint: {api_url}")
        # Return as an object with attributes instead of a dictionary
        return SimpleNamespace(enabled=True, api_url=api_url)
        
    except Exception as e:
        logging.error(f"Failed to configure LangGraph Platform: {str(e)}")
        return None