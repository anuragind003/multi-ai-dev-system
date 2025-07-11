#!/usr/bin/env python3
"""
Start Server with LangSmith Fix
This script applies the LangSmith fix and then starts the server
"""

import os
import subprocess
import sys

def apply_langsmith_fix():
    """Apply LangSmith fix before starting server"""
    print("🔧 Applying LangSmith fix before server start...")
    
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
        
        print("✅ Environment variables loaded successfully")
        
        # Test LangSmith connection
        try:
            from utils.langsmith_utils import test_langsmith_connection
            if test_langsmith_connection():
                print("✅ LangSmith connection verified")
            else:
                print("⚠️ LangSmith connection failed - tracing will be disabled")
                os.environ["LANGCHAIN_TRACING_V2"] = "false"
        except Exception as e:
            print(f"⚠️ Could not test LangSmith: {e}")
            os.environ["LANGCHAIN_TRACING_V2"] = "false"
            
        return True
            
    except Exception as e:
        print(f"❌ Error loading environment: {e}")
        return False

def start_server():
    """Start the server with proper environment"""
    print("🚀 Starting development server...")
    
    try:
        # Use the virtual environment's Python executable
        venv_python = os.path.join("venv", "Scripts", "python.exe")
        if os.path.exists(venv_python):
            python_cmd = venv_python
        else:
            python_cmd = sys.executable
        
        cmd = [
            python_cmd, "-m", "uvicorn", 
            "app.server_refactored:app", 
            "--reload", 
            "--host", "0.0.0.0", 
            "--port", "8001"
        ]
        
        print(f"Using Python: {python_cmd}")
        print(f"Running: {' '.join(cmd)}")
        subprocess.run(cmd, env=os.environ.copy())
        
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")

def main():
    """Main function"""
    print("🚀 LangSmith-Fixed Server Starter")
    print("=" * 50)
    
    # Apply LangSmith fix
    if apply_langsmith_fix():
        # Start server
        start_server()
    else:
        print("❌ Failed to apply LangSmith fix")
        sys.exit(1)

if __name__ == "__main__":
    main()
