"""
Manual test script for evaluate_all_technologies with different input formats.
This script demonstrates how the function handles various input types 
that might come from ReAct agents or direct function calls.
"""
import sys
import os
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger("evaluate_all_test")

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.data_contracts import BatchTechnologyEvaluationInput
import tools.tech_stack_tools as tech_tools

def main():
    """Test evaluate_all_technologies with different input formats."""
    # Get the function directly (not through the tool decorator)
    evaluate_all = tech_tools.evaluate_all_technologies.func
    
    # Test with different input formats
    test_cases = [
        {
            "name": "Standard Pydantic model",
            "input": BatchTechnologyEvaluationInput(
                requirements_summary="A web application with user authentication, data visualization, and high scalability needs",
                evaluate_backend=True,
                evaluate_frontend=True,
                evaluate_database=True,
                ux_focus="Modern responsive UI with interactive charts"
            )
        },
        {
            "name": "JSON string (ReAct agent style)",
            "input": json.dumps({
                "requirements_summary": "E-commerce platform with product catalog, shopping cart, and payment processing",
                "evaluate_backend": True, 
                "evaluate_frontend": True,
                "evaluate_database": True
            })
        },
        {
            "name": "Plain string (requirements only)",
            "input": "CRM system for tracking customer interactions, generating reports, and managing sales pipeline"
        }
    ]
    
    # Run the tests
    for i, test in enumerate(test_cases):
        logger.info(f"Test #{i+1}: {test['name']}")
        logger.info("=" * 80)
        logger.info(f"Input type: {type(test['input'])}")
        
        try:
            result = evaluate_all(test["input"])
            logger.info(f"Result keys: {result.keys()}")
            
            if "backend" in result:
                backend = result["backend"]
                logger.info(f"Backend recommendation: {backend.get('recommendation', {}).get('name', 'Unknown')} / "
                           f"{backend.get('recommendation', {}).get('framework', 'Unknown')}")
                
            if "frontend" in result:
                frontend = result["frontend"]
                logger.info(f"Frontend recommendation: {frontend.get('recommendation', {}).get('name', 'Unknown')} / "
                           f"{frontend.get('recommendation', {}).get('framework', 'Unknown')}")
                
            if "database" in result:
                database = result["database"]
                logger.info(f"Database recommendation: {database.get('recommendation', {}).get('type', 'Unknown')}")
            
        except Exception as e:
            logger.error(f"Test failed: {e}")
        
        logger.info("-" * 80)
    
    logger.info("All tests completed")

if __name__ == "__main__":
    main()
