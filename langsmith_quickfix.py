#!/usr/bin/env python3
"""
LangSmith Quick Fix
Apply this fix whenever you encounter LangSmith authentication issues
"""

import os

def quick_fix_langsmith():
    """Quick fix for LangSmith environment variables"""
    print("🔧 Applying LangSmith quick fix...")
    
    # Clear any cached environment variables
    for key in ["LANGSMITH_API_KEY", "LANGCHAIN_API_KEY", "LANGCHAIN_TRACING_V2", "LANGCHAIN_PROJECT"]:
        if key in os.environ:
            del os.environ[key]
    
    # Force reload from .env file
    try:
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Clean the value (remove quotes)
                    clean_value = value.strip().strip('"').strip("'")
                    os.environ[key] = clean_value
        
        print("✅ Environment variables refreshed")
        
        # Test connection
        from utils.langsmith_utils import test_langsmith_connection
        if test_langsmith_connection():
            print("🎉 LangSmith is working perfectly!")
            return True
        else:
            print("❌ Still having issues with LangSmith")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def apply_runtime_langsmith_fix():
    """Apply LangSmith fix at runtime for running applications"""
    print("🔧 Applying runtime LangSmith fix...")
    
    # Clear any cached environment variables
    for key in ["LANGSMITH_API_KEY", "LANGCHAIN_API_KEY", "LANGCHAIN_TRACING_V2", "LANGCHAIN_PROJECT"]:
        if key in os.environ:
            del os.environ[key]
    
    # Force reload from .env file
    try:
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Clean the value (remove quotes)
                    clean_value = value.strip().strip('"').strip("'")
                    os.environ[key] = clean_value
        
        print("✅ Runtime environment variables refreshed")
        return True
            
    except Exception as e:
        print(f"❌ Error applying runtime fix: {e}")
        return False

# Apply the fix immediately when this module is imported
apply_runtime_langsmith_fix()

if __name__ == "__main__":
    quick_fix_langsmith()
