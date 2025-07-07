#!/usr/bin/env python3
"""
Debug script to test the exact interrupt payload generation for tech stack approval.
"""

import asyncio
import logging
from agent_state import StateFields, AgentState

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger(__name__)

async def debug_interrupt_payload():
    """Debug the exact interrupt payload generation."""
    
    logger.info("🔍 Debugging Interrupt Payload Generation")
    
    # Create a mock state that simulates what would be available after tech stack node runs
    mock_state = AgentState({
        # BRD analysis (this works according to logs)
        StateFields.REQUIREMENTS_ANALYSIS: {
            "summary": "Create a simple web server",
            "key_features": ["RESTful API", "Database integration"]
        },
        
        # Tech stack recommendation (this is what we're testing)
        StateFields.TECH_STACK_RECOMMENDATION: {
            "recommended_stack": {
                "frontend": {
                    "framework": "React 18",
                    "language": "JavaScript",
                    "reasoning": "Excellent ecosystem and performance"
                },
                "backend": {
                    "framework": "FastAPI", 
                    "language": "Python",
                    "reasoning": "Fast, modern, and easy to use"
                },
                "database": {
                    "type": "PostgreSQL",
                    "reasoning": "Reliable and feature-rich"
                }
            },
            "justification": {
                "frontend": "React provides excellent developer experience",
                "backend": "Python with FastAPI is ideal for rapid development"
            },
            "estimated_complexity": "Medium"
        },
        
        # Workflow control variables
        "human_decision": "",
        "resume_from_approval": False
    })
    
    logger.info(f"📋 Mock state keys: {list(mock_state.keys())}")
    
    # Import and test the human feedback node creation
    from async_graph_nodes import make_async_human_feedback_node
    
    # Create the exact same node that would be used for tech stack approval
    tech_stack_feedback_node = make_async_human_feedback_node(
        StateFields.TECH_STACK_RECOMMENDATION,  # This should be "tech_stack_recommendation"
        "Tech Stack Recommendation"
    )
    
    # Test with a realistic config
    test_config = {"session_id": "debug_session"}
    
    try:
        logger.info("🔄 Calling tech stack feedback node...")
        result = await tech_stack_feedback_node(mock_state, test_config)
        
        # Check if it's an interrupt
        if hasattr(result, '__class__') and 'interrupt' in str(type(result).__name__).lower():
            logger.info(f"✅ Interrupt created successfully!")
            logger.info(f"   Type: {type(result)}")
            
            # Try to extract the payload
            if hasattr(result, 'value'):
                payload = result.value
                logger.info(f"   Payload keys: {list(payload.keys()) if isinstance(payload, dict) else 'Not a dict'}")
                if isinstance(payload, dict):
                    if 'details' in payload:
                        details = payload['details']
                        logger.info(f"   Details type: {type(details)}")
                        logger.info(f"   Details keys: {list(details.keys()) if isinstance(details, dict) else 'Not a dict'}")
                    if 'data' in payload:
                        data = payload['data']
                        logger.info(f"   Data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
            else:
                logger.warning("   No 'value' attribute found on interrupt")
                
        else:
            logger.error(f"❌ Expected interrupt, got: {type(result)}")
            logger.error(f"   Result: {result}")
            
    except Exception as e:
        logger.error(f"❌ Error calling feedback node: {e}")
        import traceback
        traceback.print_exc()
    
    # Also test the state field resolution directly
    logger.info(f"🔧 StateField test:")
    logger.info(f"   StateFields.TECH_STACK_RECOMMENDATION = '{StateFields.TECH_STACK_RECOMMENDATION}'")
    logger.info(f"   StateFields.TECH_STACK_RECOMMENDATION.value = '{StateFields.TECH_STACK_RECOMMENDATION.value}'")
    
    # Test what key the node is actually looking for vs what's in state
    step_key = StateFields.TECH_STACK_RECOMMENDATION
    logger.info(f"🔍 Key lookup test:")
    logger.info(f"   Looking for key: '{step_key}' (type: {type(step_key)})")
    logger.info(f"   Available in state: {step_key in mock_state}")
    logger.info(f"   Value found: {mock_state.get(step_key, 'KEY NOT FOUND')}")
    
    logger.info("🎉 Debug Complete")

if __name__ == "__main__":
    asyncio.run(debug_interrupt_payload())
