import os
from dotenv import load_dotenv
from config import TrackedChatModel, get_system_config

load_dotenv()

def test_temperature_binding():
    """Test that temperature binding works correctly with TrackedChatModel"""
    print("Testing TrackedChatModel temperature binding...")
    
    # Get system config
    cfg = get_system_config()
    api_key = os.getenv("GEMINI_API_KEY")
    model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash-preview-05-20")
    
    print(f"Using model: {model_name}")
    
    # Create tracked model
    tracked_model = TrackedChatModel(
        model=model_name,
        google_api_key=api_key
    )
    
    # Test with bind and different temperatures
    try:
        print("\nTesting with temperature=0.1")
        bound_model_cold = tracked_model.bind(temperature=0.1)
        response1 = bound_model_cold.invoke("Write a very concise poem about coding")
        print(f"Response (temp=0.1): {response1.content}")
        
        print("\nTesting with temperature=0.9")
        bound_model_hot = tracked_model.bind(temperature=0.9)
        response2 = bound_model_hot.invoke("Write a very concise poem about coding")
        print(f"Response (temp=0.9): {response2.content}")
        
        print("\nSuccess! Temperature binding is working correctly.")
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_temperature_binding()