import os
import dotenv
import sys
import re  # Added missing import
from typing import Literal, Optional

def switch_llm(provider: Literal["GEMINI", "OLLAMA", "DEEPSEEK"], 
               model: Optional[str] = None) -> bool:
    """
    Switch between LLM providers in .env file
    
    Args:
        provider: LLM provider to use
        model: Optional specific model to use
        
    Returns:
        bool: True if successful, False otherwise
    """
    valid_providers = ["GEMINI", "OLLAMA", "DEEPSEEK"]  # Remove OPENROUTER
    if provider not in valid_providers:
        print(f"❌ Invalid provider: {provider}. Use one of {', '.join(valid_providers)}")
        return False
    
    dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    
    try:
        # Load current environment
        dotenv.load_dotenv(dotenv_path)
        
        # Read current content
        with open(dotenv_path, 'r') as file:
            content = file.read()
        
        # Replace provider setting
        if 'LLM_PROVIDER=' in content:
            content = re.sub(
                r'LLM_PROVIDER="[^"]*"',
                f'LLM_PROVIDER="{provider}"',
                content
            )
        else:
            content += f'\nLLM_PROVIDER="{provider}"\n'
        
        # Update model if provided
        if model:
            if provider == "OPENROUTER":
                model_var = "OPENROUTER_MODEL"
            elif provider == "GEMINI":
                model_var = "GEMINI_MODEL_NAME"
            elif provider == "OLLAMA":
                model_var = "OLLAMA_MODEL_NAME"
            elif provider == "DEEPSEEK":
                model_var = "DEEPSEEK_MODEL_NAME"
            else:
                model_var = f"{provider}_MODEL"
                
            if f'{model_var}=' in content:
                content = re.sub(
                    f'{model_var}="[^"]*"',
                    f'{model_var}="{model}"',
                    content
                )
            else:
                content += f'\n{model_var}="{model}"\n'
        
        # When switching to DeepSeek, also set embedding provider
        if provider == "DEEPSEEK":
            if "EMBEDDING_PROVIDER=" in content:
                content = re.sub(
                    r'EMBEDDING_PROVIDER="[^"]*"',
                    f'EMBEDDING_PROVIDER="DEEPSEEK"',
                    content
                )
            else:
                content += f'\nEMBEDDING_PROVIDER="DEEPSEEK"\n'
    
        # Write updated content
        with open(dotenv_path, 'w') as file:
            file.write(content)
        
        model_info = f" with model {model}" if model else ""
        print(f"✅ Successfully switched LLM provider to {provider}{model_info}")
        return True
    except Exception as e:
        print(f"❌ Failed to switch LLM provider: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python switch_llm.py [GEMINI|OLLAMA|DEEPSEEK|OPENROUTER] [optional_model]")
        sys.exit(1)
    
    provider = sys.argv[1].upper()
    model = sys.argv[2] if len(sys.argv) > 2 else None
    success = switch_llm(provider, model)
    sys.exit(0 if success else 1)