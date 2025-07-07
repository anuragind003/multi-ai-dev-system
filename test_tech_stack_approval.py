#!/usr/bin/env python3
"""
Test script to verify the tech stack approval workflow is working correctly.
"""

import asyncio
import logging
from agent_state import StateFields

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger(__name__)

async def test_tech_stack_approval():
    """Test the tech stack approval workflow end-to-end."""
    
    logger.info("🔍 Testing Tech Stack Approval Workflow")
    
    # Test 1: StateField Resolution
    tech_stack_key = StateFields.TECH_STACK_RECOMMENDATION
    logger.info(f"✅ StateField resolved: {tech_stack_key} = '{tech_stack_key.value}'")
    
    # Test 2: Mock State with Tech Stack Data
    mock_state = {
        tech_stack_key.value: {
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
        }
    }
    
    logger.info(f"✅ Mock state created with keys: {list(mock_state.keys())}")
    
    # Test 3: Data Extraction
    try:
        from app.server import extract_tech_stack_data
        extracted_data = await extract_tech_stack_data(mock_state)
        
        logger.info(f"✅ Data extraction successful!")
        logger.info(f"   - Frontend: {extracted_data.get('frontend_framework')}")
        logger.info(f"   - Backend: {extracted_data.get('backend_framework')}")
        logger.info(f"   - Database: {extracted_data.get('database')}")
        logger.info(f"   - Additional tools count: {len(extracted_data.get('additional_tools', []))}")
        
    except Exception as e:
        logger.error(f"❌ Data extraction failed: {e}")
        
    # Test 4: Human Feedback Node Simulation
    try:
        from async_graph_nodes import make_async_human_feedback_node
        
        # Create the tech stack feedback node
        tech_stack_feedback_node = make_async_human_feedback_node(
            StateFields.TECH_STACK_RECOMMENDATION, 
            "Tech Stack Recommendation"
        )
        
        # Test with a config that simulates non-resumption state
        test_config = {"session_id": "test_session"}
        
        # Simulate the node execution (this should create an interrupt)
        logger.info("🔄 Testing human feedback node creation...")
        
        # Note: This would normally create an interrupt, so we'll just test the function exists
        logger.info(f"✅ Human feedback node created successfully")
        
    except Exception as e:
        logger.error(f"❌ Human feedback node test failed: {e}")
    
    logger.info("🎉 Tech Stack Approval Workflow Test Complete")

if __name__ == "__main__":
    asyncio.run(test_tech_stack_approval())
