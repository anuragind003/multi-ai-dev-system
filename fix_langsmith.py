#!/usr/bin/env python3
"""
Automatic LangSmith Configuration Fix
This script applies safe LangSmith configuration to prevent 403 errors
"""

import os
import sys

def apply_safe_langsmith_config():
    """Apply safe LangSmith configuration to prevent 403 errors"""
    
    # Import the updated utils
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    
    try:
        from utils.langsmith_utils import safe_configure_langsmith, disable_langsmith_tracing
        
        print("🔧 Applying safe LangSmith configuration...")
        
        # Try to configure LangSmith safely
        success = safe_configure_langsmith()
        
        if success:
            print("✅ LangSmith configured successfully!")
        else:
            print("⚠️ LangSmith tracing disabled due to authentication issues")
            print("\nTo enable LangSmith:")
            print("1. Get your API key from: https://smith.langchain.com/settings")
            print("2. Set environment variable: $env:LANGSMITH_API_KEY = 'your-api-key'")
            print("3. Run this script again")
        
        return success
        
    except ImportError as e:
        print(f"❌ Failed to import LangSmith utilities: {e}")
        return False
    except Exception as e:
        print(f"❌ Error configuring LangSmith: {e}")
        return False

def show_current_status():
    """Show current LangSmith configuration status"""
    print("\n📊 Current LangSmith Status:")
    print("=" * 40)
    
    env_vars = {
        "LANGSMITH_API_KEY": os.getenv("LANGSMITH_API_KEY"),
        "LANGCHAIN_API_KEY": os.getenv("LANGCHAIN_API_KEY"),
        "LANGCHAIN_TRACING_V2": os.getenv("LANGCHAIN_TRACING_V2"),
        "LANGCHAIN_PROJECT": os.getenv("LANGCHAIN_PROJECT")
    }
    
    for var, value in env_vars.items():
        if value:
            if "API_KEY" in var:
                print(f"  ✅ {var}: {value[:8]}... (masked)")
            else:
                print(f"  ✅ {var}: {value}")
        else:
            print(f"  ❌ {var}: Not set")

def main():
    """Main function"""
    print("🚀 LangSmith Configuration Fix Tool")
    print("=" * 50)
    
    # Show current status
    show_current_status()
    
    # Apply safe configuration
    success = apply_safe_langsmith_config()
    
    # Show updated status
    show_current_status()
    
    if success:
        print("\n🎉 LangSmith is now properly configured!")
    else:
        print("\n💡 LangSmith tracing is disabled to prevent errors.")
        print("   Set up your API key to enable tracing.")

if __name__ == "__main__":
    main()
