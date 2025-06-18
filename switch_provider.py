import os
import sys
import dotenv

def switch_llm_provider(provider):
    """Switch between LLM providers in .env file"""
    if provider not in ["GEMINI", "OLLAMA"]:
        print(f"Invalid provider: {provider}. Use GEMINI or OLLAMA")
        return False
        
    # Load environment variables
    dotenv.load_dotenv()
    
    # Read .env file
    with open(".env", "r") as f:
        env_content = f.read()
        
    # Replace provider line
    if "LLM_PROVIDER=" in env_content:
        env_content = env_content.replace(
            f'LLM_PROVIDER="{os.getenv("LLM_PROVIDER")}"', 
            f'LLM_PROVIDER="{provider}"'
        )
    else:
        env_content += f'\nLLM_PROVIDER="{provider}"\n'
        
    # Write back to .env
    with open(".env", "w") as f:
        f.write(env_content)
        
    print(f"✅ Switched LLM provider to {provider}")
    return True

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python switch_provider.py [GEMINI|OLLAMA]")
        sys.exit(1)
        
    provider = sys.argv[1].upper()
    if switch_llm_provider(provider):
        sys.exit(0)
    else:
        sys.exit(1)