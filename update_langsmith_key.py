#!/usr/bin/env python3
"""
LangSmith API Key Update Tool
This script helps you safely update your LangSmith API key
"""

import os
import re

def get_new_api_key():
    """Get new API key from user input"""
    print("🔑 LangSmith API Key Update")
    print("=" * 40)
    print("Get your API key from: https://smith.langchain.com/settings")
    print()
    
    while True:
        api_key = input("Enter your new LangSmith API key: ").strip()
        
        if not api_key:
            print("❌ Please enter a valid API key")
            continue
            
        # Basic validation for LangSmith API key format
        if not api_key.startswith("lsv2_"):
            print("⚠️ Warning: LangSmith API keys typically start with 'lsv2_'")
            confirm = input("Continue with this key? (y/n): ").strip().lower()
            if confirm != 'y':
                continue
        
        if len(api_key) < 20:
            print("❌ API key seems too short. Please check and try again.")
            continue
            
        return api_key

def update_env_file(new_api_key):
    """Update the .env file with the new API key"""
    env_file = ".env"
    
    if not os.path.exists(env_file):
        print(f"❌ {env_file} file not found")
        return False
    
    try:
        # Read current content
        with open(env_file, 'r') as f:
            content = f.read()
        
        # Update the API key line
        # Handle both quoted and unquoted values
        patterns = [
            r'LANGCHAIN_API_KEY=.*',
            r'LANGSMITH_API_KEY=.*'
        ]
        
        updated = False
        for pattern in patterns:
            if re.search(pattern, content):
                content = re.sub(pattern, f'LANGCHAIN_API_KEY={new_api_key}', content)
                updated = True
                break
        
        # If no existing API key line found, add it
        if not updated:
            if not content.endswith('\n'):
                content += '\n'
            content += f'LANGCHAIN_API_KEY={new_api_key}\n'
        
        # Write updated content
        with open(env_file, 'w') as f:
            f.write(content)
            
        print(f"✅ Updated {env_file} with new API key")
        return True
        
    except Exception as e:
        print(f"❌ Error updating {env_file}: {e}")
        return False

def test_new_api_key():
    """Test the new API key"""
    print("\n🧪 Testing new API key...")
    
    # Reload environment variables
    from dotenv import load_dotenv
    load_dotenv(override=True)  # Override existing env vars
    
    try:
        from utils.langsmith_utils import test_langsmith_connection
        
        if test_langsmith_connection():
            print("🎉 New API key is working!")
            
            # Re-enable tracing
            with open('.env', 'r') as f:
                content = f.read()
            
            updated_content = content.replace(
                'LANGCHAIN_TRACING_V2=false',
                'LANGCHAIN_TRACING_V2=true'
            )
            
            with open('.env', 'w') as f:
                f.write(updated_content)
            
            print("✅ LangSmith tracing re-enabled")
            return True
        else:
            print("❌ New API key is not working")
            return False
            
    except Exception as e:
        print(f"❌ Error testing API key: {e}")
        return False

def show_current_env():
    """Show current environment configuration"""
    print("\n📊 Current .env Configuration:")
    print("=" * 40)
    
    try:
        with open('.env', 'r') as f:
            lines = f.readlines()
        
        langsmith_lines = [line.strip() for line in lines if 'LANGCHAIN' in line or 'LANGSMITH' in line]
        
        for line in langsmith_lines:
            if 'API_KEY' in line:
                # Mask the API key for security
                if '=' in line:
                    key, value = line.split('=', 1)
                    if len(value) > 8:
                        masked_value = value[:8] + "..." + " (masked)"
                    else:
                        masked_value = "..." + " (masked)"
                    print(f"  {key}={masked_value}")
            else:
                print(f"  {line}")
                
    except Exception as e:
        print(f"❌ Error reading .env file: {e}")

def main():
    """Main function"""
    print("🚀 LangSmith API Key Update Tool")
    print("=" * 50)
    
    # Show current configuration
    show_current_env()
    
    # Get new API key
    new_api_key = get_new_api_key()
    
    # Update .env file
    if update_env_file(new_api_key):
        # Test the new key
        if test_new_api_key():
            print("\n🎉 API key updated successfully!")
            print("Your LangSmith integration is now working.")
        else:
            print("\n⚠️ API key updated but not working properly.")
            print("Please check your API key at: https://smith.langchain.com/settings")
    else:
        print("❌ Failed to update API key")

if __name__ == "__main__":
    main()
