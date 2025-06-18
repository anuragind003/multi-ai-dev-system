import os
import time
import logging
from dotenv import load_dotenv

# Import core system components
from config import get_llm
from shared_memory import SharedMemory
from monitoring import setup_logging
from agents.brd_analyst import BRDAnalystAgent

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)
load_dotenv()

def test_gemini_temperature_binding():
    """Test temperature binding with Gemini API."""
    # Ensure environment variable is set for Gemini
    os.environ["LLM_PROVIDER"] = "GEMINI"
    
    logger.info("\n=== Testing Gemini Temperature Binding ===")
    
    # Get base LLM
    llm_instance = get_llm()
    memory_instance = SharedMemory()
    
    # Create test agent
    test_agent = BRDAnalystAgent(llm=llm_instance, memory=memory_instance)
    
    # Sample BRD excerpt for testing
    sample_brd = """
    Business Requirements Document
    
    Project: Customer Portal Enhancement
    
    Requirements:
    1. User login with 2FA
    2. Dashboard with customer activity summary
    3. Document upload and sharing functionality
    4. Notification system for updates
    """
    
    # Test different temperatures
    temperatures_to_test = [0.1, 0.4, 0.7]
    
    logger.info("\n--- Testing Direct LLM Binding with Simple Prompt ---")
    simple_prompt = "Summarize the key benefits of microservices architecture in one paragraph."
    
    for temp_val in temperatures_to_test:
        logger.info(f"\nTesting with temperature: {temp_val}")
        try:
            # Test direct binding
            bound_llm = test_agent.llm.bind(temperature=temp_val)
            
            # Log the bound parameters
            logger.info(f"Bound LLM with temperature={temp_val}")
            
            # Simple invocation
            response = bound_llm.invoke(simple_prompt)
            content = response.content if hasattr(response, "content") else str(response)
            
            logger.info(f"Response with temp={temp_val}: {content[:100]}...")
            
            # Respect rate limits
            time.sleep(2)
            
        except Exception as e:
            logger.error(f"Error testing direct binding with temperature {temp_val}: {str(e)}")
    
    # Now test execute_llm_chain with different temperatures
    logger.info("\n--- Testing execute_llm_chain with Different Temperatures ---")
    
    # Set prompt template
    test_agent.prompt_template = test_agent.initial_assessment_template
    
    for temp_val in temperatures_to_test:
        logger.info(f"\nTesting execute_llm_chain with temperature: {temp_val}")
        try:
            result = test_agent.execute_llm_chain(
                inputs={
                    "brd_excerpt": sample_brd, 
                    "format_instructions": test_agent.json_parser.get_format_instructions()
                },
                task_specific_temp=temp_val,
                additional_llm_params={"max_output_tokens": 500} 
            )
            
            # Log a portion of the result
            result_str = str(result)
            logger.info(f"Result with temp={temp_val}: {result_str[:200]}...")
            
            # Respect rate limits
            time.sleep(3)
            
        except Exception as e:
            logger.error(f"Error testing execute_llm_chain with temperature {temp_val}: {str(e)}")

if __name__ == "__main__":
    test_gemini_temperature_binding()