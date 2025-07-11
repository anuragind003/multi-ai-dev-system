#!/usr/bin/env python3
"""
Start Server with Fixed LangSmith Configuration
This script ensures LangSmith is properly configured before starting the server
"""

import os
import sys
import subprocess

def fix_langsmith_config():
    """Fix LangSmith configuration before starting server"""
    print("🔧 Fixing LangSmith configuration...")
    
    # Restore the working configuration if backup exists
    if os.path.exists('.env.backup'):
        print("📄 Restoring working LangSmith configuration...")
        
        try:
            with open('.env.backup', 'r') as f:
                content = f.read()
            
            with open('.env', 'w') as f:
                f.write(content)
            
            print("✅ LangSmith configuration restored")
            
        except Exception as e:
            print(f"❌ Error restoring configuration: {e}")
            return False
    
    # Clear any cached environment variables and reload
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
        
        print("✅ Environment variables loaded")
        
        # Test LangSmith connection
        try:
            from utils.langsmith_utils import test_langsmith_connection
            if test_langsmith_connection():
                print("🎉 LangSmith is working perfectly!")
                return True
            else:
                print("⚠️ LangSmith test failed - disabling tracing for safety")
                os.environ["LANGCHAIN_TRACING_V2"] = "false"
                return True
        except Exception as e:
            print(f"⚠️ Could not test LangSmith: {e}")
            os.environ["LANGCHAIN_TRACING_V2"] = "false"
            return True
            
    except Exception as e:
        print(f"❌ Error loading environment: {e}")
        return False

def start_server():
    """Start the development server"""
    print("\n🚀 Starting development server...")
    
    try:
        # Start the server using the task defined in your workspace
        cmd = [
            "python", "-m", "uvicorn", 
            "app.server_refactored:app", 
            "--reload", 
            "--host", "0.0.0.0", 
            "--port", "8001"
        ]
        
        print(f"Running: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
        
    except KeyboardInterrupt:
        print("\n⏹️ Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")

def main():
    """Main function"""
    print("🚀 Multi-AI Dev System Startup")
    print("=" * 50)
    
    # Fix LangSmith configuration
    if fix_langsmith_config():
        # Start the server
        start_server()
    else:
        print("❌ Failed to configure LangSmith. Please check your configuration.")
        sys.exit(1)

if __name__ == "__main__":
    main()
