"""
Test script for LangSmith connectivity.
Run this directly with "python test_langsmith.py" to verify your LangSmith setup.
"""

from config import initialize_langsmith
import os
from dotenv import load_dotenv

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    print("=== LangSmith Connection Test ===")
    print(f"API Key found: {'Yes' if os.getenv('LANGSMITH_API_KEY') else 'No'}")
    
    # Try initializing LangSmith
    result = initialize_langsmith()
    
    if result:
        print("\n✅ LangSmith is properly configured!")
        print("You can now use LangSmith for visualizing your agent workflow.")
        print("Your agent temperature strategy (0.1-0.4) will be tracked in LangSmith.")
    else:
        print("\n❌ LangSmith configuration failed")
        print("Check your API key and network connectivity.")
        
    print("\nEnvironment variables:")
    print(f"LANGCHAIN_TRACING_V2: {os.getenv('LANGCHAIN_TRACING_V2')}")
    print(f"LANGCHAIN_PROJECT: {os.getenv('LANGCHAIN_PROJECT')}")