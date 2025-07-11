#!/usr/bin/env python3
"""
Test LangSmith API Key and Re-enable Tracing
"""

import os
from dotenv import load_dotenv

def main():
    """Test the API key and enable tracing if successful"""
    
    # Load environment variables from .env
    load_dotenv()
    
    print("🧪 Testing LangSmith API Key from .env file...")
    
    # Import the safe configuration function
    try:
        from utils.langsmith_utils import safe_configure_langsmith, test_langsmith_connection
        
        # Test the connection
        if test_langsmith_connection():
            print("\n✅ API key is valid! Re-enabling LangSmith tracing...")
            
            # Re-enable tracing in .env file
            with open('.env', 'r') as f:
                content = f.read()
            
            # Update the .env file to enable tracing
            updated_content = content.replace(
                'LANGCHAIN_TRACING_V2=false',
                'LANGCHAIN_TRACING_V2=true'
            )
            
            with open('.env', 'w') as f:
                f.write(updated_content)
            
            # Update environment variable for current session
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            
            print("✅ LangSmith tracing re-enabled in .env file")
            print("🎉 Your application should now work without 403 errors!")
            
        else:
            print("\n❌ API key is not working. Keeping tracing disabled.")
            print("💡 Check your API key at: https://smith.langchain.com/settings")
            
    except Exception as e:
        print(f"❌ Error testing API key: {e}")

if __name__ == "__main__":
    main()
