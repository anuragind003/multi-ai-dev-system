#!/usr/bin/env python3
"""
Emergency LangSmith Disable
This script disables LangSmith tracing to stop the 403 errors immediately
"""

import os

def emergency_disable_langsmith():
    """Emergency disable of LangSmith tracing"""
    print("🚨 Emergency LangSmith disable...")
    
    # Disable tracing immediately
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    
    # Clear problematic API keys from memory
    for key in ["LANGSMITH_API_KEY", "LANGCHAIN_API_KEY"]:
        if key in os.environ:
            del os.environ[key]
    
    print("✅ LangSmith tracing disabled")
    print("💡 Restart your server to re-enable with the correct API key")
    
    # Update .env file to disable tracing temporarily
    try:
        with open('.env', 'r') as f:
            content = f.read()
        
        # Temporarily disable tracing in .env
        updated_content = content.replace(
            'LANGCHAIN_TRACING_V2=true',
            'LANGCHAIN_TRACING_V2=false'
        )
        
        if updated_content != content:
            with open('.env.backup', 'w') as f:
                f.write(content)
            
            with open('.env', 'w') as f:
                f.write(updated_content)
            
            print("✅ Temporarily disabled tracing in .env file")
            print("📝 Original .env backed up to .env.backup")
        
    except Exception as e:
        print(f"⚠️ Could not update .env file: {e}")

def restore_langsmith():
    """Restore LangSmith tracing from backup"""
    print("🔄 Restoring LangSmith configuration...")
    
    try:
        if os.path.exists('.env.backup'):
            with open('.env.backup', 'r') as f:
                content = f.read()
            
            with open('.env', 'w') as f:
                f.write(content)
            
            os.remove('.env.backup')
            print("✅ LangSmith configuration restored")
            print("🔄 Please restart your server to apply changes")
        else:
            print("❌ No backup found")
            
    except Exception as e:
        print(f"❌ Error restoring configuration: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "restore":
        restore_langsmith()
    else:
        emergency_disable_langsmith()
        print("\nTo restore LangSmith later, run:")
        print("python emergency_langsmith_disable.py restore")
