#!/usr/bin/env python3
"""
Test script to debug the tech stack approval issue.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import logging
from agent_state import StateFields

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_tech_stack_extraction():
    """Test extracting tech stack data from a mock state."""
    
    # Mock state like what's in the logs
    mock_state = {
        "tech_stack_recommendation": {
            "recommended_stack": {
                "frontend": {
                    "framework": "React 18",
                    "state_management": "Redux Toolkit",
                    "styling": "Tailwind CSS",
                    "build_tool": "Vite",
                    "ui_library": "Material-UI or Ant Design"
                },
                "backend": {
                    "runtime": "Node.js 18+",
                    "framework": "Express.js",
                    "orm": "Prisma",
                    "validation": "Joi or Zod",
                    "authentication": "JWT with refresh tokens",
                    "api_documentation": "Swagger/OpenAPI"
                },
                "database": {
                    "primary": "PostgreSQL 14+",
                    "caching": "Redis",
                    "search": "Elasticsearch (if full-text search needed)",
                    "file_storage": "AWS S3 or equivalent"
                }
            },
            "justification": {
                "frontend": "React provides excellent developer experience",
                "backend": "Node.js enables full-stack JavaScript development"
            },
            "alternatives": {
                "frontend": {
                    "frameworks": ["Vue.js 3", "Angular 15+", "Svelte"]
                }
            }
        }
    }
    
    # Test the StateField value
    step_key = StateFields.TECH_STACK_RECOMMENDATION
    logger.info(f"Step key: {step_key} = '{step_key.value}'")
    
    # Test extraction
    step_output = mock_state.get(step_key, {"error": f"Data for Tech Stack not found in state."})
    logger.info(f"Step output keys: {list(step_output.keys())}")
    logger.info(f"Has recommended_stack: {'recommended_stack' in step_output}")
    
    # Test the server's extract_tech_stack_data function
    try:
        import asyncio
        from app.server import extract_tech_stack_data
        
        async def test_extract():
            result = await extract_tech_stack_data(mock_state)
            logger.info(f"Extracted data keys: {list(result.keys())}")
            logger.info(f"Frontend framework: {result.get('frontend_framework')}")
            logger.info(f"Backend framework: {result.get('backend_framework')}")
            return result
        
        return asyncio.run(test_extract())
        
    except Exception as e:
        logger.error(f"Error testing extraction: {e}")
        return None

if __name__ == "__main__":
    test_tech_stack_extraction()
