import os
import dotenv
import sys

def switch_to_ollama():
    """Immediately switch to Ollama for testing"""
    dotenv_file = os.path.join(os.path.dirname(__file__), '.env')
    
    if os.path.exists(dotenv_file):
        # Load current env
        dotenv.load_dotenv(dotenv_file)
        
        # Read file
        with open(dotenv_file, 'r') as file:
            content = file.read()
            
        # Update LLM_PROVIDER
        if 'LLM_PROVIDER=' in content:
            content = content.replace(
                f'LLM_PROVIDER="{os.getenv("LLM_PROVIDER")}"',
                'LLM_PROVIDER="OLLAMA"'
            )
        else:
            content += '\nLLM_PROVIDER="OLLAMA"\n'
            
        # Write changes
        with open(dotenv_file, 'w') as file:
            file.write(content)
            
        print("✅ Switched to OLLAMA for local testing")
        print("   Run your command with: python main.py --brd brds\\Sample.txt --workflow phased")
    else:
        print("❌ .env file not found!")
        return False
        
    return True

if __name__ == "__main__":
    switch_to_ollama()