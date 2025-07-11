#!/usr/bin/env python3
"""
Debug LangSmith Environment Variables
This script helps debug environment variable loading issues
"""

import os
import sys

def debug_env_vars():
    """Debug current environment variables"""
    print("🔍 Debugging Environment Variables")
    print("=" * 50)
    
    # Check current environment variables
    print("Current Environment Variables:")
    langsmith_vars = {
        "LANGSMITH_API_KEY": os.environ.get("LANGSMITH_API_KEY"),
        "LANGCHAIN_API_KEY": os.environ.get("LANGCHAIN_API_KEY"),
        "LANGCHAIN_TRACING_V2": os.environ.get("LANGCHAIN_TRACING_V2"),
        "LANGCHAIN_PROJECT": os.environ.get("LANGCHAIN_PROJECT")
    }
    
    for var, value in langsmith_vars.items():
        if value:
            if "API_KEY" in var:
                print(f"  {var}: {value[:12]}... (length: {len(value)})")
            else:
                print(f"  {var}: {value}")
        else:
            print(f"  {var}: NOT SET")
    
    print("\n" + "=" * 50)

def read_env_file():
    """Read the .env file directly"""
    print("📄 Reading .env file directly:")
    print("=" * 50)
    
    try:
        with open('.env', 'r') as f:
            lines = f.readlines()
        
        langchain_lines = [line.strip() for line in lines if 'LANGCHAIN' in line or 'LANGSMITH' in line]
        
        for line in langchain_lines:
            if line and not line.startswith('#'):
                if 'API_KEY' in line:
                    if '=' in line:
                        key, value = line.split('=', 1)
                        # Clean the value
                        clean_value = value.strip().strip('"').strip("'")
                        print(f"  {key}={clean_value[:12]}... (length: {len(clean_value)})")
                else:
                    print(f"  {line}")
                    
    except Exception as e:
        print(f"❌ Error reading .env file: {e}")

def force_reload_env():
    """Force reload environment variables from .env"""
    print("\n🔄 Force reloading .env file...")
    
    try:
        # Clear existing LangSmith variables
        for key in ["LANGSMITH_API_KEY", "LANGCHAIN_API_KEY", "LANGCHAIN_TRACING_V2", "LANGCHAIN_PROJECT"]:
            if key in os.environ:
                del os.environ[key]
        
        # Manually parse and load .env file
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Clean the value (remove quotes)
                    clean_value = value.strip().strip('"').strip("'")
                    os.environ[key] = clean_value
        
        print("✅ Environment variables reloaded")
        
    except Exception as e:
        print(f"❌ Error reloading .env: {e}")

def test_api_key():
    """Test the API key after reload"""
    print("\n🧪 Testing API key after reload...")
    
    try:
        from utils.langsmith_utils import test_langsmith_connection
        
        # Show current API key
        api_key = os.environ.get("LANGSMITH_API_KEY") or os.environ.get("LANGCHAIN_API_KEY")
        if api_key:
            print(f"Using API key: {api_key[:12]}... (length: {len(api_key)})")
        
        if test_langsmith_connection():
            print("🎉 API key is working!")
            return True
        else:
            print("❌ API key still not working")
            return False
            
    except Exception as e:
        print(f"❌ Error testing API key: {e}")
        return False

def main():
    """Main debugging function"""
    print("🚀 LangSmith Environment Debug Tool")
    print("=" * 50)
    
    # Step 1: Show current environment
    debug_env_vars()
    
    # Step 2: Read .env file directly
    read_env_file()
    
    # Step 3: Force reload
    force_reload_env()
    
    # Step 4: Show updated environment
    print("\n🔍 After reload:")
    debug_env_vars()
    
    # Step 5: Test API key
    test_api_key()

if __name__ == "__main__":
    main()
