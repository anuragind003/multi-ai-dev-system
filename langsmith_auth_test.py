#!/usr/bin/env python3
"""
LangSmith Authentication Test and Fix Script
This script helps diagnose and fix LangSmith 403 Forbidden errors
"""

import os
import sys
from typing import Optional

def check_environment_variables():
    """Check if LangSmith environment variables are set"""
    print("🔍 Checking LangSmith Environment Variables...")
    
    variables = {
        "LANGSMITH_API_KEY": os.getenv("LANGSMITH_API_KEY"),
        "LANGCHAIN_API_KEY": os.getenv("LANGCHAIN_API_KEY"), 
        "LANGCHAIN_TRACING_V2": os.getenv("LANGCHAIN_TRACING_V2"),
        "LANGCHAIN_PROJECT": os.getenv("LANGCHAIN_PROJECT"),
        "LANGCHAIN_ENDPOINT": os.getenv("LANGCHAIN_ENDPOINT")
    }
    
    for var, value in variables.items():
        if value:
            if "API_KEY" in var:
                print(f"  ✅ {var}: {value[:8]}... (masked)")
            else:
                print(f"  ✅ {var}: {value}")
        else:
            print(f"  ❌ {var}: Not set")
    
    return bool(variables["LANGSMITH_API_KEY"] or variables["LANGCHAIN_API_KEY"])

def test_langsmith_connection():
    """Test connection to LangSmith API with detailed error handling"""
    print("\n🔗 Testing LangSmith Connection...")
    
    try:
        from langsmith import Client
        
        # Get API key from environment
        api_key = os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY")
        
        if not api_key:
            print("  ❌ No API key found in environment variables")
            return False
        
        # Create client with explicit configuration
        client = Client(
            api_url="https://api.smith.langchain.com",
            api_key=api_key,
            max_batch_size=1  # Use minimal batch size for testing
        )
        
        print(f"  🌐 API URL: {client.api_url}")
        print(f"  🔑 API Key: {api_key[:8]}... (masked)")
        
        # Test with a simple API call
        try:
            projects = list(client.list_projects(limit=1))
            print(f"  ✅ Successfully connected to LangSmith!")
            print(f"  📊 Found {len(projects)} project(s)")
            return True
            
        except Exception as api_error:
            print(f"  ❌ API Error: {api_error}")
            
            # Check for specific error types
            if "403" in str(api_error) or "Forbidden" in str(api_error):
                print("  🚨 403 Forbidden Error - This indicates:")
                print("     1. Invalid API key")
                print("     2. API key doesn't have required permissions")
                print("     3. Account/project access issues")
                
            elif "401" in str(api_error) or "Unauthorized" in str(api_error):
                print("  🚨 401 Unauthorized Error - Invalid API key")
                
            return False
            
    except ImportError:
        print("  ❌ LangSmith package not installed")
        print("  💡 Run: pip install langsmith")
        return False
    except Exception as e:
        print(f"  ❌ Unexpected error: {e}")
        return False

def fix_langsmith_configuration():
    """Provide steps to fix LangSmith configuration"""
    print("\n🔧 LangSmith Configuration Fix Steps:")
    print("\n1. Get your LangSmith API Key:")
    print("   - Go to https://smith.langchain.com/settings")
    print("   - Sign in to your LangChain account")
    print("   - Navigate to 'API Keys' section")
    print("   - Create a new API key or copy existing one")
    
    print("\n2. Set environment variables (choose one method):")
    print("\n   Method A - PowerShell (current session):")
    print("   $env:LANGSMITH_API_KEY = 'your-api-key-here'")
    print("   $env:LANGCHAIN_TRACING_V2 = 'true'")
    print("   $env:LANGCHAIN_PROJECT = 'Multi-AI-Dev-System'")
    
    print("\n   Method B - Create .env file:")
    print("   LANGSMITH_API_KEY=your-api-key-here")
    print("   LANGCHAIN_TRACING_V2=true")
    print("   LANGCHAIN_PROJECT=Multi-AI-Dev-System")
    
    print("\n   Method C - Windows System Environment Variables:")
    print("   - Open System Properties → Environment Variables")
    print("   - Add LANGSMITH_API_KEY with your API key")
    print("   - Add LANGCHAIN_TRACING_V2=true")
    print("   - Add LANGCHAIN_PROJECT=Multi-AI-Dev-System")

def create_env_file_template():
    """Create a .env template file"""
    env_content = """# LangSmith Configuration
# Get your API key from: https://smith.langchain.com/settings

LANGSMITH_API_KEY=your-api-key-here
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=Multi-AI-Dev-System
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com

# Optional: Batch size to avoid 413 errors
LANGCHAIN_BATCH_SIZE=5
"""
    
    env_path = ".env.template"
    try:
        with open(env_path, "w") as f:
            f.write(env_content)
        print(f"\n📝 Created {env_path} template file")
        print("   Copy this to .env and add your actual API key")
        return True
    except Exception as e:
        print(f"❌ Failed to create .env template: {e}")
        return False

def test_improved_configuration():
    """Test the improved LangSmith configuration"""
    print("\n🧪 Testing Improved Configuration...")
    
    # Configure environment variables for optimal performance
    os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
    os.environ["LANGCHAIN_BATCH_SIZE"] = "1"  # Very small for testing
    
    if not os.getenv("LANGCHAIN_PROJECT"):
        os.environ["LANGCHAIN_PROJECT"] = "Multi-AI-Dev-System"
    
    try:
        from langsmith import Client
        
        api_key = os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY")
        if not api_key:
            print("  ⚠️ API key still not configured")
            return False
        
        # Test with minimal configuration
        client = Client(
            api_url="https://api.smith.langchain.com",
            api_key=api_key,
            max_batch_size=1,
            timeout_ms=30000  # 30 second timeout
        )
        
        # Simple test
        try:
            info = client.info
            print(f"  ✅ LangSmith connection successful!")
            print(f"  📊 Server info: {info}")
            return True
        except Exception as e:
            print(f"  ❌ Connection test failed: {e}")
            return False
            
    except Exception as e:
        print(f"  ❌ Configuration test failed: {e}")
        return False

def main():
    """Main diagnostic and fix function"""
    print("🚀 LangSmith Authentication Diagnostic Tool")
    print("=" * 50)
    
    # Step 1: Check environment variables
    has_api_key = check_environment_variables()
    
    # Step 2: Test connection if API key exists
    if has_api_key:
        connection_success = test_langsmith_connection()
        if connection_success:
            print("\n🎉 LangSmith is properly configured!")
            return
    
    # Step 3: Provide fix instructions
    fix_langsmith_configuration()
    
    # Step 4: Create template file
    create_env_file_template()
    
    print("\n" + "=" * 50)
    print("After setting up your API key, run this script again to test the connection.")

if __name__ == "__main__":
    main()
